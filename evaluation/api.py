"""
evaluation/api.py
────────────────
FastAPI micro-service on port 8005.
Serves evaluation results and allows triggering evaluation runs.

Start:
    python -m uvicorn evaluation.api:app --port 8005 --reload
OR (from project root):
    venv\\Scripts\\python.exe -m uvicorn evaluation.api:app --port 8005
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── path setup ────────────────────────────────────────────────
EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))
from config import RESULT_DIR, DATASET_DIR, RAGAS_VERSION, JUDGE_MODEL, SAMPLE_LIMIT
from event_logger import event_counts, read_events
from config import EVAL_PORT  # noqa: F401 (imported for reference)

app = FastAPI(
    title="Legal System Evaluation API",
    description="Ragas evaluation results and job runner for the Judicial Insight Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODULES = ["legal_qa", "research", "summary", "comprehension"]
_running_jobs: dict[str, dict] = {}
_PYTHON = sys.executable  # use same venv python


# ─────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────

@app.get("/api/eval/health")
def health():
    return {
        "status": "ok",
        "ragas_version": RAGAS_VERSION,
        "judge_model": JUDGE_MODEL,
        "sample_limit": SAMPLE_LIMIT,
        "result_dir": str(RESULT_DIR),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ─────────────────────────────────────────────
# Results endpoints
# ─────────────────────────────────────────────

def _read_result(module: str) -> Optional[dict]:
    path = RESULT_DIR / f"{module}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/eval/results")
def all_results():
    """Return aggregated scores for all modules (for dashboard overview)."""
    out = {}
    for mod in MODULES:
        data = _read_result(mod)
        if data:
            out[mod] = {
                "module": mod,
                "metadata": data.get("metadata", {}),
                "aggregate": data.get("aggregate", {}),
                "notes": data.get("notes", []),
                "n_samples": data.get("metadata", {}).get("n_samples", 0),
                "run_timestamp": data.get("metadata", {}).get("run_timestamp"),
            }
        else:
            out[mod] = None
    return out


@app.get("/api/eval/results/{module}")
def module_result(module: str):
    """Return full result (including all samples) for a single module."""
    if module not in MODULES:
        raise HTTPException(status_code=404, detail=f"Unknown module: {module}")
    data = _read_result(module)
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"No results for '{module}'. Run evaluation first.",
        )
    return data


@app.get("/api/eval/results/{module}/samples")
def module_samples(module: str, flag: Optional[str] = None, limit: int = 100):
    """Return individual samples, optionally filtered by flag ('ok' or 'low')."""
    if module not in MODULES:
        raise HTTPException(status_code=404, detail=f"Unknown module: {module}")
    data = _read_result(module)
    if not data:
        raise HTTPException(status_code=404, detail=f"No results for '{module}'.")
    samples = data.get("samples", [])
    if flag:
        samples = [s for s in samples if s.get("flag") == flag]
    return {"samples": samples[:limit], "total": len(data.get("samples", []))}


@app.get("/api/eval/status")
def eval_status():
    """Return which modules have datasets and results ready."""
    status = {}
    for mod in MODULES:
        has_dataset = (DATASET_DIR / f"{mod}.json").exists()
        has_result = (RESULT_DIR / f"{mod}.json").exists()
        job = _running_jobs.get(mod)
        status[mod] = {
            "has_dataset": has_dataset,
            "has_result": has_result,
            "job": job,
        }
    return status


# ─────────────────────────────────────────────
# Job runner (background tasks)
# ─────────────────────────────────────────────

def _run_job(module: str, step: str):
    """Launch build_datasets or run_eval as subprocess. Updates _running_jobs."""
    script_map = {
        "build": EVAL_DIR / "build_datasets.py",
        "eval": EVAL_DIR / "run_eval.py",
    }
    script = script_map.get(step)
    if not script or not script.exists():
        _running_jobs[module] = {"status": "error", "message": f"Script not found: {script}"}
        return

    job_key = f"{step}_{module}"
    _running_jobs[module] = {
        "status": "running",
        "step": step,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "job_key": job_key,
    }

    try:
        result = subprocess.run(
            [_PYTHON, str(script), "--module", module],
            capture_output=True,
            text=True,
            timeout=1800,  # 30 min max
        )
        if result.returncode == 0:
            _running_jobs[module] = {
                "status": "done",
                "step": step,
                "finished_at": datetime.utcnow().isoformat() + "Z",
                "stdout_tail": result.stdout[-2000:],
            }
        else:
            _running_jobs[module] = {
                "status": "error",
                "step": step,
                "returncode": result.returncode,
                "stderr_tail": result.stderr[-2000:],
                "stdout_tail": result.stdout[-1000:],
            }
    except subprocess.TimeoutExpired:
        _running_jobs[module] = {"status": "timeout", "step": step}
    except Exception as e:
        _running_jobs[module] = {"status": "error", "step": step, "message": str(e)}


@app.post("/api/eval/run/{module}")
def run_evaluation(module: str, background_tasks: BackgroundTasks):
    """
    POST /api/eval/run/<module>
    Triggers: build_datasets (if needed) then run_eval for the module.
    """
    if module not in MODULES and module != "all":
        raise HTTPException(status_code=400, detail=f"Unknown module: {module}")

    # Prevent duplicate runs
    mods_to_run = MODULES if module == "all" else [module]
    for mod in mods_to_run:
        job = _running_jobs.get(mod)
        if job and job.get("status") == "running":
            return JSONResponse(
                status_code=409,
                content={"detail": f"Evaluation for '{mod}' is already running."},
            )

    def _pipeline(mod: str):
        has_dataset = (DATASET_DIR / f"{mod}.json").exists()
        if not has_dataset:
            _run_job(mod, "build")
            # check if build succeeded
            if not (DATASET_DIR / f"{mod}.json").exists():
                return
        _run_job(mod, "eval")

    for mod in mods_to_run:
        background_tasks.add_task(_pipeline, mod)

    return {
        "status": "started",
        "modules": mods_to_run,
        "message": f"Evaluation pipeline started for {mods_to_run}. Check /api/eval/status.",
    }


@app.post("/api/eval/build/{module}")
def build_dataset(module: str, background_tasks: BackgroundTasks):
    """POST /api/eval/build/<module> — only runs dataset building step."""
    if module not in MODULES and module != "all":
        raise HTTPException(status_code=400, detail=f"Unknown module: {module}")
    mods_to_run = MODULES if module == "all" else [module]
    for mod in mods_to_run:
        background_tasks.add_task(_run_job, mod, "build")
    return {"status": "started", "modules": mods_to_run}


# ─────────────────────────────────────────────
# Metrics glossary (for the UI tooltip)
# ─────────────────────────────────────────────

METRIC_GLOSSARY = {
    "faithfulness": "Measures whether the answer is factually consistent with the retrieved contexts. Score 0–1 (higher=better).",
    "response_relevancy": "Measures how relevant the answer is to the question. Score 0–1.",
    "llm_context_precision_with_reference": "Measures whether relevant information in the context is ranked highly. Score 0–1.",
    "context_recall": "Measures how much of the reference answer is covered by the retrieved contexts. Score 0–1.",
    "factual_correctness": "Measures the factual accuracy of the response against the reference answer. Score 0–1.",
    "semantic_similarity": "Cosine similarity between the response embedding and reference embedding. Score 0–1.",
    "context_entity_recall": "Measures whether named entities in the reference appear in the context. Score 0–1.",
    "cites_page_numbers": "Custom: whether the response cites specific page numbers from the source. 1=yes, 0=no.",
    "covers_core_elements": "Custom: whether the summary covers facts, legal issue, and final decision. 1=yes, 0=no.",
    "no_invented_details": "Custom: whether the summary avoids invented parties or sections. 1=yes, 0=no.",
    "field_is_complete": "Custom: whether the extracted field fully captures the judgment content. 1=yes, 0=no.",
}


@app.get("/api/eval/glossary")
def glossary():
    return METRIC_GLOSSARY


# ─────────────────────────────────────────────
# Live evaluation (real user interactions)
# ─────────────────────────────────────────────

@app.get("/api/eval/live/events")
def live_event_counts():
    """
    Returns the number of real user interactions logged per module.
    Used by the dashboard to show 'N real interactions logged'.
    """
    counts = event_counts()
    preview = {}
    for mod in MODULES:
        events = read_events(mod, last_n=3)
        preview[mod] = [
            {"user_input": e.get("user_input", "")[:80],
             "ts": e.get("ts", "")}
            for e in events
        ]
    return {"counts": counts, "recent_preview": preview}


_live_running: dict[str, bool] = {}

def _run_live_eval(module: str):
    """Background worker: runs live_eval for one module."""
    global _live_running
    _live_running[module] = True
    try:
        result = subprocess.run(
            [_PYTHON, str(EVAL_DIR / "live_eval.py"),
             "--module", module,
             "--max-samples", str(SAMPLE_LIMIT)],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(EVAL_DIR.parent),
        )
        _running_jobs[f"live_{module}"] = {
            "status": "done" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-1000:],
            "stderr_tail": result.stderr[-500:],
            "finished_at": datetime.utcnow().isoformat() + "Z",
        }
    except subprocess.TimeoutExpired:
        _running_jobs[f"live_{module}"] = {"status": "timeout"}
    except Exception as e:
        _running_jobs[f"live_{module}"] = {"status": "error", "message": str(e)}
    finally:
        _live_running[module] = False


@app.post("/api/eval/live/run/{module}")
def run_live_evaluation(module: str, background_tasks: BackgroundTasks):
    """
    POST /api/eval/live/run/<module>
    Scores real user interaction events with reference-free Ragas metrics.
    Requires at least 3 real interactions to have been logged.
    Does NOT call build_datasets or need pre-built datasets.
    """
    if module not in MODULES and module != "all":
        raise HTTPException(status_code=400, detail=f"Unknown module: {module}")

    mods = MODULES if module == "all" else [module]

    counts = event_counts()
    skipped = [m for m in mods if counts.get(m, 0) < 3]
    runnable = [m for m in mods if counts.get(m, 0) >= 3]

    for mod in runnable:
        if not _live_running.get(mod):
            background_tasks.add_task(_run_live_eval, mod)

    return {
        "status": "started" if runnable else "insufficient_data",
        "running": runnable,
        "skipped": skipped,
        "event_counts": {m: counts.get(m, 0) for m in mods},
        "message": (
            f"Live scoring started for {runnable}. Results appear in 1-3 min."
            if runnable else
            "Not enough real user interactions yet. Use the system first, then re-run."
        ),
    }


@app.get("/api/eval/live/status")
def live_status():
    """Returns event counts + whether live scoring is in progress."""
    counts = event_counts()
    return {
        "event_counts": counts,
        "scoring_in_progress": {m: _live_running.get(m, False) for m in MODULES},
        "min_events_required": 3,
        "ready_modules": [m for m in MODULES if counts.get(m, 0) >= 3],
    }
