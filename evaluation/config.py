"""
evaluation/config.py
Central configuration for all evaluation jobs.
Edit SAMPLE_LIMIT and JUDGE_MODEL to control cost/quality.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# ── project root ─────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = Path(__file__).resolve().parent

# load keys from the project's root .env or any backend .env
_env_sources = [
    ROOT / "backend" / ".env",
    ROOT / "rbackend" / ".env",
    ROOT / "Legal_QA" / "legal-qa-system" / "backend" / ".env",
    ROOT / "Legal_Summary" / "backend" / ".env",
]
for _e in _env_sources:
    if _e.exists():
        load_dotenv(dotenv_path=_e, override=False)

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# ── backend URLs ─────────────────────────────────────────────
BACKEND_MAIN      = "http://localhost:8000"
BACKEND_RESEARCH  = "http://localhost:8001"
BACKEND_QA        = "http://localhost:8002"
BACKEND_SUMMARY   = "http://localhost:8003"

# ── evaluation service ───────────────────────────────────────
EVAL_PORT = 8005

# ── model & budget ───────────────────────────────────────────
JUDGE_MODEL   = "gpt-4o-mini"       # cheap judge; change to gpt-4o for accuracy
EMBED_MODEL   = "text-embedding-3-small"
SAMPLE_LIMIT  = 20                  # max samples per module (set lower during dev)
MAX_WORKERS   = 4                   # concurrent HTTP / LLM calls
HTTP_TIMEOUT  = 60                  # seconds

# ── corpus paths ─────────────────────────────────────────────
CORPUS_UPLOADS = ROOT / "Legal_QA" / "legal-qa-system" / "backend" / "uploads"
CORPUS_RESULTS = ROOT / "backend" / "Results"
CORPUS_DOWNLOADS = ROOT / "indiankanoon-mcp" / "downloads"

# ── result paths ─────────────────────────────────────────────
DATASET_DIR = EVAL_DIR / "datasets"
RESULT_DIR  = EVAL_DIR / "results"
DATASET_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

# 10 representative PDFs (filenames relative to CORPUS_UPLOADS)
SAMPLE_PDFS = [
    "1189512_U.P. State Sugar Corporation Ltd. vs The Presiding Officer, Labour Court, ... on 6 January, 2005.pdf",
    "1608496_Cit vs S. Kamaljeet Singh on 28 January, 2005.pdf",
    "1687189_District And Sessions Judge vs Ratnesh Kumar Srivastava And Anr. on 20 January, 2005.pdf",
    "1822728_Saraya Industries Ltd. vs State Of U.P. And Ors. on 6 January, 2005.pdf",
    "1898332_Vijendra Sharma Alias Vijendra Kumar ... vs State Of U.P., Smt. Vimlesh Daughter Of ... on 12 January, 2005.pdf",
    "1913281_Ex-Naik Upendra Kumar Tomar vs Union Of India (Uoi) And Ors. on 25 January, 2005.pdf",
    "103394330_Reserved On_ 13.03.2025 vs State Of H.P. & Another on 20 March, 2025.pdf",
    "185995005_Mohammed Siddique vs National Insurance Company Ltd on 8 January, 2020.pdf",
    "187771162_Shilpa Mittal vs State Of Nct Of Delhi on 9 January, 2020.pdf",
    "92625542_Directorate Of Revenue Intelligence vs Raj Kumar Arora on 17 April, 2025.pdf",
]

RAGAS_VERSION = "0.2.15"
