"""
evaluation/event_logger.py
───────────────────────────
Lightweight, stdlib-only event logger.
Each backend imports this and calls log_event() after serving a request.

Design rules:
- NO third-party imports (no ragas, no langchain, no requests)
- Fire-and-forget: errors are silently suppressed so a logging failure
  NEVER breaks the backend response
- Thread-safe: uses threading.Lock for file writes
- Each event is a single JSON line (JSONL format)
- All backends write to the SAME events/ directory, resolvable from
  any CWD via the EVAL_EVENTS_DIR environment variable or auto-detection
"""

from __future__ import annotations
import json
import os
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ── Resolve events directory ─────────────────────────────────────────────────
# Priority: EVAL_EVENTS_DIR env var → fallback auto-detected relative to this file

def _find_events_dir() -> Path:
    env_path = os.getenv("EVAL_EVENTS_DIR")
    if env_path:
        p = Path(env_path)
        p.mkdir(parents=True, exist_ok=True)
        return p
    # This file lives at <project_root>/evaluation/event_logger.py
    # Walk up until we find the evaluation/ directory
    here = Path(__file__).resolve()
    for parent in [here.parent, here.parent.parent]:
        candidate = parent / "evaluation" / "events"
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except Exception:
            continue
    # Final fallback: relative to CWD
    fallback = Path("evaluation/events")
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


EVENTS_DIR: Path = _find_events_dir()
_lock = threading.Lock()

MODULE_FILES = {
    "legal_qa":      "legal_qa_events.jsonl",
    "research":      "research_events.jsonl",
    "summary":       "summary_events.jsonl",
    "comprehension": "comprehension_events.jsonl",
}


def log_event(
    module: str,
    user_input: str,
    response: str,
    contexts: list[str],
    meta: dict | None = None,
) -> None:
    """
    Append one interaction event to the module's JSONL file.
    Called by each backend after serving a user request.
    NEVER raises — all errors are silently suppressed.

    Parameters
    ----------
    module      : one of 'legal_qa', 'research', 'summary', 'comprehension'
    user_input  : the user's question, query, or task description
    response    : the system's text response
    contexts    : list of context strings (retrieved chunks, source paragraphs, etc.)
    meta        : optional dict of extra metadata (confidence score, case_id, etc.)
    """
    if module not in MODULE_FILES:
        return
    if not user_input or not response:
        return

    try:
        event = {
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "module": module,
            "user_input": str(user_input)[:2000],
            "response": str(response)[:4000],
            "contexts": [str(c)[:2000] for c in (contexts or [])[:10]],
            "meta": meta or {},
        }
        filepath = EVENTS_DIR / MODULE_FILES[module]
        with _lock:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        # Silent fail — a logging error must NEVER crash the backend
        pass


def log_event_async(
    module: str,
    user_input: str,
    response: str,
    contexts: list[str],
    meta: dict | None = None,
) -> None:
    """
    Same as log_event() but runs in a background thread.
    Use this for synchronous Flask backends to avoid any blocking.
    """
    t = threading.Thread(
        target=log_event,
        args=(module, user_input, response, contexts, meta),
        daemon=True,
    )
    t.start()


def read_events(module: str, last_n: int = 200) -> list[dict]:
    """Read the last N events for a module. Returns [] on error."""
    filepath = EVENTS_DIR / MODULE_FILES.get(module, "")
    if not filepath.exists():
        return []
    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
        events = []
        for line in reversed(lines[-last_n * 2:]):
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
            if len(events) >= last_n:
                break
        return list(reversed(events))
    except Exception:
        return []


def event_counts() -> dict[str, int]:
    """Return total logged event count per module."""
    counts = {}
    for module, fname in MODULE_FILES.items():
        filepath = EVENTS_DIR / fname
        if filepath.exists():
            try:
                counts[module] = sum(1 for l in filepath.read_text(encoding="utf-8").splitlines() if l.strip())
            except Exception:
                counts[module] = 0
        else:
            counts[module] = 0
    return counts
