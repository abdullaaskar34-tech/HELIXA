# -*- coding: utf-8 -*-
"""
HELIXA — API layer.   KBU-MedLab · Turning Genomics into Decisions

ASGI service (Starlette) that exposes the project's REAL scientific pipeline to
the web frontend. It owns no science of its own: analysis is delegated to
`helixa_engine`, which wraps the frozen model artifacts produced by
NEW_START_RESULTS/10_Prediction_Model/.

Run:
    pip install -r requirements.txt
    uvicorn app:app --port 8000

Endpoints
    GET  /api/health              service + engine status
    GET  /api/engine              model artifact metadata
    GET  /api/<dataset>           real exported results (see DATASETS below)
    GET  /api/patients/{id}       one patient record
    POST /api/analyze             start a real analysis job  -> {job_id}
    GET  /api/analyze/{job_id}    poll live stage-by-stage progress
    POST /api/analyze-sync        blocking analysis (test harness)
"""
from __future__ import annotations
import os, json, uuid, threading, time
from typing import Dict, Any

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

import helixa_engine as eng

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('HELIXA_DATA', os.path.join(HERE, '..', 'frontend', 'public', 'data'))
PLOTS_DIR = os.environ.get('HELIXA_PLOTS',
                           os.path.join(HERE, '..', 'frontend', 'public', 'assets', 'plots'))
RESULTS_ROOT = eng.RESULTS_ROOT
MAX_UPLOAD_MB = 40

# The API serves only public, already-published scientific results and a stateless
# classifier, and is intended to run on the researcher's own machine. The default is
# therefore permissive so the frontend works from any local port or from the deployed
# static site. Set HELIXA_CORS to a comma-separated allowlist to restrict it.
ORIGINS = [o.strip() for o in os.environ.get('HELIXA_CORS', '*').split(',') if o.strip()]

STAGE_ORDER = ['ingest', 'qc', 'batch', 'features', 'embed',
               'model', 'confidence', 'validate', 'insight']

DATASETS = {
    'project': 'project.json', 'clusters': 'clusters.json', 'patients': 'patients.json',
    'metrics': 'global_metrics.json', 'model': 'model.json',
    'confusion': 'confusion_matrix.json', 'markers': 'markers.json',
    'biology': 'biology.json', 'external-validation': 'external_validation.json',
    'k-selection': 'k_selection.json', 'sweep': 'sweep_summary.json',
    'batch-diagnosis': 'batch_diagnosis.json', 'embedding': 'embedding.json',
    'plots': 'plots.json', 'pipeline': 'pipeline.json',
}

JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {}


def _load(name: str):
    if name in _CACHE:
        return _CACHE[name]
    p = os.path.join(DATA_DIR, name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        _CACHE[name] = json.load(f)
    return _CACHE[name]


def err(msg, code=400, **extra):
    return JSONResponse({'error': msg, **extra}, status_code=code)


# ────────────────────────────────────────────────────────────── routes
async def root(_):
    return JSONResponse({'name': 'HELIXA API', 'team': 'KBU-MedLab',
                         'slogan': 'Turning Genomics into Decisions',
                         'health': '/api/health', 'datasets': sorted(DATASETS)})


async def health(_):
    st = eng.engine_status()
    return JSONResponse({'status': 'ok', 'engine': st,
                         'data_dir_present': os.path.isdir(DATA_DIR),
                         'results_root_present': os.path.isdir(RESULTS_ROOT),
                         'datasets_available': sorted(
                             k for k, v in DATASETS.items()
                             if os.path.exists(os.path.join(DATA_DIR, v)))})


async def engine_info(_):
    return JSONResponse(eng.engine_status())


async def dataset(request: Request):
    key = request.path_params['key']
    fname = DATASETS.get(key)
    if not fname:
        return err(f'unknown dataset "{key}"', 404, available=sorted(DATASETS))
    d = _load(fname)
    if d is None:
        return err(f'{fname} not found — run export_static_data.py first', 404)
    return JSONResponse(d)


async def patient(request: Request):
    pid = request.path_params['pid']
    ps = _load('patients.json') or []
    for p in ps:
        if pid in (p['id'], p['sample_id'], p['short_id']):
            return JSONResponse(p)
    return err(f'patient "{pid}" not found', 404)


def _run_job(job_id: str, raw: bytes, filename: str):
    def on_stage(sid, status, payload):
        with JOBS_LOCK:
            jb = JOBS[job_id]
            jb['stages'][sid] = {'status': status, **payload}
            jb['current'] = sid
            jb['completed'] = [s for s in STAGE_ORDER
                               if jb['stages'].get(s, {}).get('status') == 'done']
            jb['updated'] = time.time()
    try:
        res = eng.analyse(raw, filename, on_stage=on_stage)
        with JOBS_LOCK:
            JOBS[job_id].update({'state': 'done', 'result': res, 'updated': time.time()})
    except Exception as e:
        with JOBS_LOCK:
            JOBS[job_id].update({'state': 'error', 'error': str(e),
                                 'error_type': type(e).__name__, 'updated': time.time()})


async def _read_upload(request: Request):
    form = await request.form()
    up = form.get('file')
    if up is None:
        return None, None, err('no file field in the request (expected multipart field "file")')
    raw = await up.read() if hasattr(up, 'read') else bytes(up)
    name = getattr(up, 'filename', 'upload.tsv') or 'upload.tsv'
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return None, None, err(f'file larger than {MAX_UPLOAD_MB} MB', 413)
    if len(raw) < 1000:
        return None, None, err('file is too small to be a GDC expression file')
    return raw, name, None


async def analyze(request: Request):
    st = eng.engine_status()
    if not st['available']:
        return err(f"inference engine unavailable: {st.get('error')}", 503)
    raw, name, e = await _read_upload(request)
    if e is not None:
        return e
    job_id = uuid.uuid4().hex[:12]
    with JOBS_LOCK:
        JOBS[job_id] = {'id': job_id, 'state': 'running', 'file': name, 'stages': {},
                        'completed': [], 'current': None,
                        'started': time.time(), 'updated': time.time()}
    threading.Thread(target=_run_job, args=(job_id, raw, name), daemon=True).start()
    return JSONResponse({'job_id': job_id, 'state': 'running', 'stage_order': STAGE_ORDER})


async def job_status(request: Request):
    jid = request.path_params['jid']
    with JOBS_LOCK:
        jb = JOBS.get(jid)
        if not jb:
            return err('job not found', 404)
        return JSONResponse(json.loads(json.dumps(jb, default=str)))


async def analyze_sync(request: Request):
    st = eng.engine_status()
    if not st['available']:
        return err(f"inference engine unavailable: {st.get('error')}", 503)
    raw, name, e = await _read_upload(request)
    if e is not None:
        return e
    try:
        return JSONResponse(eng.analyse(raw, name))
    except ValueError as ex:
        return err(str(ex), 400)
    except Exception as ex:
        return err(f'{type(ex).__name__}: {ex}', 500)


routes = [
    Route('/', root),
    Route('/api/health', health),
    Route('/api/engine', engine_info),
    Route('/api/analyze', analyze, methods=['POST']),
    Route('/api/analyze-sync', analyze_sync, methods=['POST']),
    Route('/api/analyze/{jid}', job_status),
    Route('/api/patients/{pid}', patient),
    Route('/api/{key}', dataset),
]
if os.path.isdir(PLOTS_DIR):
    routes.append(Mount('/plots', app=StaticFiles(directory=PLOTS_DIR), name='plots'))

app = Starlette(
    debug=False, routes=routes,
    middleware=[Middleware(CORSMiddleware, allow_origins=ORIGINS or ['*'],
                           allow_methods=['*'], allow_headers=['*'])])
