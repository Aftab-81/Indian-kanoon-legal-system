"""
app.py — Flask Web UI Backend & MCP Client
Acts as the bridge between the browser UI and the MCP Server.

Run: python app.py
Open: http://localhost:5000
"""

import os
import sys
import json
import time
import uuid
import queue
import logging
import threading
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS

# Add MCP server path
BASE_DIR = Path(__file__).parent.parent
MCP_SERVER_DIR = BASE_DIR / "mcp_server"
DOWNLOADS_DIR = BASE_DIR / "downloads"
sys.path.insert(0, str(MCP_SERVER_DIR))

# Import scraper directly (same logic the MCP server uses)
from scraper import (
    fetch_all_judgements,
    download_judgement,
    fetch_judgement_count,
    COURT_TYPES,
    MONTH_MAP,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Track active download tasks: task_id → {"status", "progress", "total", "files", "errors", "done"}
download_tasks: dict[str, dict] = {}
task_events: dict[str, queue.Queue] = {}  # SSE event queues


# ───────────────────────────────────────────
# Helper: push SSE event to a task's queue
# ───────────────────────────────────────────
def push_event(task_id: str, event_type: str, data: dict):
    if task_id in task_events:
        payload = json.dumps({"type": event_type, **data})
        task_events[task_id].put(payload)


# ───────────────────────────────────────────
# Background download worker
# ───────────────────────────────────────────
def download_worker(task_id: str, year: int, month: str, court: str, max_count: int, use_pdf: bool):
    task = download_tasks[task_id]
    task["status"] = "running"

    save_dir = str(DOWNLOADS_DIR / str(year) / month)
    os.makedirs(save_dir, exist_ok=True)

    push_event(task_id, "start", {"message": f"Searching for {month} {year} judgements..."})

    try:
        # Step 1: Fetch judgement list
        judgements = fetch_all_judgements(
            year=year,
            month_name=month,
            court=court,
            max_count=max_count,
            delay_seconds=1.2,
            progress_callback=lambda fetched, total: push_event(
                task_id, "search_progress",
                {"fetched": fetched, "total": total, "message": f"Found {fetched} / {total} judgements..."}
            ),
        )

        total = len(judgements)
        task["total"] = total
        push_event(task_id, "search_done", {
            "total": total,
            "message": f"Found {total} judgements. Starting downloads...",
        })

        downloaded_files = []
        errors = []

        # Step 2: Download each judgement
        for i, j in enumerate(judgements):
            if task.get("cancelled"):
                push_event(task_id, "cancelled", {"message": "Download cancelled by user."})
                break

            push_event(task_id, "download_progress", {
                "current": i + 1,
                "total": total,
                "title": j["title"][:80],
                "percentage": round(((i + 1) / total) * 100),
            })

            result = download_judgement(
                doc_id=j["id"],
                title=j["title"],
                output_dir=save_dir,
                use_pdf=use_pdf,
                delay_seconds=1.0,
            )

            if result["success"]:
                file_entry = {
                    "id": j["id"],
                    "title": j["title"],
                    "court": j["court"],
                    "date": j["date"],
                    "path": result["path"],
                    "filename": os.path.basename(result["path"]),
                    "skipped": result.get("skipped", False),
                    "type": "PDF" if result["path"].endswith(".pdf") else "HTML",
                }
                downloaded_files.append(file_entry)
                push_event(task_id, "file_done", file_entry)
            else:
                err = {"id": j["id"], "title": j["title"], "error": result.get("error", "Unknown")}
                errors.append(err)
                push_event(task_id, "file_error", err)

        # Done!
        task["status"] = "done"
        task["files"] = downloaded_files
        task["errors"] = errors
        push_event(task_id, "done", {
            "downloaded": len(downloaded_files),
            "failed": len(errors),
            "save_dir": save_dir,
            "message": f"✅ Complete! {len(downloaded_files)} downloaded, {len(errors)} failed.",
        })

    except Exception as e:
        logger.error(f"Download worker error: {e}", exc_info=True)
        task["status"] = "error"
        push_event(task_id, "error", {"message": str(e)})
    finally:
        task["done"] = True


# ───────────────────────────────────────────
# Routes
# ───────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html", courts=list(COURT_TYPES.keys()), months=list(MONTH_MAP.keys()))


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json()
    year = int(data.get("year", 2025))
    month = data.get("month", "January")
    court = data.get("court", "All Courts")
    max_count = int(data.get("max_count", 50))
    use_pdf = data.get("use_pdf", True)

    if month not in MONTH_MAP:
        return jsonify({"error": "Invalid month"}), 400

    task_id = str(uuid.uuid4())
    download_tasks[task_id] = {
        "task_id": task_id,
        "year": year,
        "month": month,
        "court": court,
        "max_count": max_count,
        "status": "queued",
        "progress": 0,
        "total": 0,
        "files": [],
        "errors": [],
        "done": False,
        "created_at": datetime.now().isoformat(),
    }
    task_events[task_id] = queue.Queue()

    thread = threading.Thread(
        target=download_worker,
        args=(task_id, year, month, court, max_count, use_pdf),
        daemon=True,
    )
    thread.start()

    return jsonify({"task_id": task_id})


@app.route("/api/count", methods=["POST"])
def get_count():
    data = request.get_json()
    year = int(data.get("year", 2025))
    month = data.get("month", "January")
    court = data.get("court", "All Courts")

    if month not in MONTH_MAP:
        return jsonify({"error": "Invalid month"}), 400

    try:
        count = fetch_judgement_count(year, month, court)
        return jsonify({"count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stream/<task_id>")
def stream_events(task_id):
    """Server-Sent Events endpoint for real-time progress updates."""
    if task_id not in task_events:
        return jsonify({"error": "Task not found"}), 404

    def generate():
        q = task_events[task_id]
        while True:
            try:
                data = q.get(timeout=30)
                yield f"data: {data}\n\n"
                parsed = json.loads(data)
                if parsed.get("type") in ("done", "error", "cancelled"):
                    break
            except queue.Empty:
                # Send keepalive ping
                yield ": keepalive\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/cancel/<task_id>", methods=["POST"])
def cancel_task(task_id):
    if task_id in download_tasks:
        download_tasks[task_id]["cancelled"] = True
        return jsonify({"status": "cancelling"})
    return jsonify({"error": "Task not found"}), 404


@app.route("/api/status/<task_id>")
def task_status(task_id):
    if task_id not in download_tasks:
        return jsonify({"error": "Task not found"}), 404
    task = download_tasks[task_id].copy()
    return jsonify(task)


@app.route("/api/open_folder", methods=["POST"])
def open_folder():
    data = request.get_json()
    folder = data.get("path", str(DOWNLOADS_DIR))
    try:
        os.startfile(folder)
        return jsonify({"status": "opened"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    logger.info("=" * 60)
    logger.info("  Indian Kanoon Judgement Downloader")
    logger.info("  Open: http://localhost:8004")
    logger.info("=" * 60)
    app.run(host="0.0.0.0", port=8004, debug=False, threaded=True)
