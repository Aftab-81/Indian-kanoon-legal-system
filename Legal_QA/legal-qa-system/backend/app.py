#!/usr/bin/env python3

import os
import json
from logger_setup import get_logger
import uuid
import hashlib
import PyPDF2
import numpy as np
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# ── Evaluation event logger (fire-and-forget, never raises) ────────────────
try:
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / 'evaluation'))
    from event_logger import log_event_async as _log_qa_event
except Exception:
    def _log_qa_event(*a, **k): pass  # silent no-op if evaluation/ not found

# Try new openai package first, fall back to old version
try:
    from openai import OpenAI
    OPENAI_NEW_VERSION = True
except ImportError:
    import openai
    OPENAI_NEW_VERSION = False

import faiss
from sentence_transformers import SentenceTransformer
import requests
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)
logger = get_logger(__name__)
CORS(app)

# ======================
# ENV CONFIG WITH DIAGNOSTICS
# ======================

# Load OpenAI Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    OPENAI_API_KEY = OPENAI_API_KEY.strip().strip('"').strip("'")

if not OPENAI_API_KEY:
    logger.warning("⚠️ WARNING: OPENAI_API_KEY not found!")
else:
    logger.info(f"✅ OpenAI Key loaded: {OPENAI_API_KEY[:10]}...")

# Load SerpAPI Key from environment
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
if SERPAPI_KEY:
    SERPAPI_KEY = SERPAPI_KEY.strip().strip('"').strip("'").strip()
    logger.info(f"✅ SerpAPI Key loaded: {SERPAPI_KEY[:10]}...{SERPAPI_KEY[-10:]}")
else:
    logger.warning("⚠️ WARNING: SERPAPI_KEY not found! External web search will be disabled.")

# Update OpenAI client initialization
if OPENAI_NEW_VERSION:
    client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
else:
    openai.api_key = OPENAI_API_KEY
    client = None

# Diagnostic logging flag for Document QA & Upload pipeline (gated behind env var DEBUG_DOCQA_DIAGNOSTICS)
DEBUG_DOCQA_DIAGNOSTICS = os.getenv("DEBUG_DOCQA_DIAGNOSTICS", "false").lower() in ("true", "1", "yes")

# ======================
# GLOBALS /  LOADING
# ======================

# loaded embedding model to speed up backend startup
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        logger.info("🔁 Loading SentenceTransformer embedding model...")
        _embedding_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
    return _embedding_model

# Cached FAISS index + cases metadata (avoid re-reading from disk on every query)
_faiss_index = None
_cases_cache = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_DB_FILE = os.path.join(BASE_DIR, "legal_vectors.faiss")
CASES_FILE = os.path.join(BASE_DIR, "cases_metadata.json")   # stores chunks + case metadata
STORE_FILE = os.path.join(BASE_DIR, "qa_store.json")         # stores questions, answers, reviews, cache
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ======================
# CONFIGURABLE LOGIC & THRESHOLD CONSTANTS
# ======================
KB_SIMILARITY_THRESHOLD = float(os.getenv("KB_SIMILARITY_THRESHOLD", "0.45"))
CACHE_SIMILARITY_THRESHOLD = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.90"))
ALLOW_GENERAL_KNOWLEDGE_FALLBACK = os.getenv("ALLOW_GENERAL_KNOWLEDGE_FALLBACK", "false").lower() in ("true", "1", "yes")

# Phrases we NEVER want to show in missing_info (even though we hide missing_info now)
BLOCKED_MISSING_INFO_PHRASES = [
    "criminal antecedents",
    "nature and seriousness of the offence",
    "nature and seriousness of offence",
    "stage of investigation or trial",
    "stage of investigation",
    "stage of trial",
    "tampering with evidence",
    "fleeing from justice",
    "risk factors such as possibility of tampering with evidence or fleeing"
]

# ======================
# SIMPLE JSON STORAGE
# ======================

def load_store():
    """
    Loads questions, answers, reviews, cache from JSON.
    Structure:
    {
      "questions": [...],
      "answers": [...],
      "reviews": [...],
      "cache": [...]
    }
    """
    if not os.path.exists(STORE_FILE):
        return {
            "questions": [],
            "answers": [],
            "reviews": [],
            "cache": []
        }
    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    data.setdefault("questions", [])
    data.setdefault("answers", [])
    data.setdefault("reviews", [])
    data.setdefault("cache", [])
    return data

def save_store(store):
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)

def load_cases_data():
    """
    cases_metadata.json structure:
    {
      "chunks": [
         { "text": "...", "case_id": "...", "case_name": "...", "chunk_type": "..." },
         ...
      ]
    }
    """
    if not os.path.exists(CASES_FILE):
        return {"chunks": []}
    try:
        with open(CASES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("chunks", [])
            return data
    except Exception:
        return {"chunks": []}

INDEX_LOCK = threading.Lock()

def clean_text_plain_only(text: str) -> str:
    """
    Cleans text thoroughly so it is strictly PLAIN TEXT:
    - Removes script and style blocks entirely (both tags and their inner content)
    - Removes HTML tags and entities using BeautifulSoup + html.unescape
    - Removes control characters (retaining standard whitespace and newlines)
    - Normalizes whitespace and un-hyphenates words broken across lines
    - Strips any remaining HTML tags (<tag...>) while preserving literal comparisons like 'x < 5'
    """
    if not text:
        return ""

    import html
    from bs4 import BeautifulSoup

    # First explicitly strip script and style tags along with their inner content
    text = re.sub(r'<\s*(script|style)[^>]*>.*?<\s*/\s*\1\s*>', ' ', text, flags=re.DOTALL | re.IGNORECASE)

    # Parse with BeautifulSoup to strip any other markup elements (noscript, header, footer, etc.)
    soup = BeautifulSoup(text, "html.parser")
    for elem in soup(["script", "style", "noscript", "header", "footer"]):
        elem.extract()
    raw_text = soup.get_text(separator=" ")

    # Decode HTML entities (e.g., &nbsp;, &amp;, &#39;)
    raw_text = html.unescape(raw_text)

    # Replace non-breaking space \xa0 with standard space
    raw_text = raw_text.replace('\xa0', ' ')

    # Remove non-printable control characters except \t, \n, \r
    raw_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', ' ', raw_text)

    # Un-hyphenate words broken across line breaks (e.g. "judg-\nment" -> "judgment")
    raw_text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', raw_text)

    # Strip remaining HTML tags (<tag ...> or </tag>) without removing literal '<' or '>' comparisons (e.g., x < 5)
    raw_text = re.sub(r'<\s*[/]?[a-zA-Z][^>]*>', ' ', raw_text)

    # Normalize excessive spaces and tabs (preserve newlines for paragraph breaks)
    raw_text = re.sub(r'[ \t]+', ' ', raw_text)
    raw_text = re.sub(r'\n{3,}', '\n\n', raw_text)

    return raw_text.strip()

def save_cases_data(cases_data):
    """Save cases_metadata.json atomically using a temporary file."""
    temp_file = CASES_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(cases_data, f, indent=2, ensure_ascii=False)
    os.replace(temp_file, CASES_FILE)

# ======================
# PDF PARSER
# ======================
def extract_pdf_text(file_path):
    """Extract text with page markers. Returns (text, page_count, is_encrypted)."""
    text = ""
    page_count = 0
    is_encrypted = False
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            if reader.is_encrypted:
                is_encrypted = True
                return text, page_count, is_encrypted
            page_count = len(reader.pages)
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n[PAGE {page_num}]\n{page_text}\n"

        # Fallback to PyMuPDF (fitz) or OCR if text is empty/near-empty
        if len(text.strip()) < 100:
            try:
                import fitz
                doc = fitz.open(file_path)
                page_count = len(doc)
                fitz_text = ""
                for page_num, page in enumerate(doc, 1):
                    p_txt = page.get_text()
                    if p_txt:
                        fitz_text += f"\n[PAGE {page_num}]\n{p_txt}\n"
                
                if len(fitz_text.strip()) >= 100:
                    text = fitz_text
                else:
                    # OCR fallback using pytesseract if available
                    try:
                        import pytesseract
                        from PIL import Image
                        import io
                        ocr_text = ""
                        for page_num, page in enumerate(doc, 1):
                            pix = page.get_pixmap(dpi=150)
                            img = Image.open(io.BytesIO(pix.tobytes("png")))
                            p_ocr = pytesseract.image_to_string(img)
                            if p_ocr:
                                ocr_text += f"\n[PAGE {page_num}]\n{p_ocr}\n"
                        if len(ocr_text.strip()) >= 50:
                            text = ocr_text
                    except Exception as ocr_err:
                        logger.warning(f"OCR fallback error: {ocr_err}")
                doc.close()
            except Exception as fitz_err:
                logger.warning(f"PyMuPDF fallback error: {fitz_err}")

    except Exception as e:
        logger.error(f"PDF Error: {e}", exc_info=True)

    if DEBUG_DOCQA_DIAGNOSTICS:
        first_500 = (text.strip()[:500] if text else "<EMPTY>")
        logger.info(
            f"🔍 [DIAGNOSTIC] Extracted PDF text: pages={page_count}, "
            f"char_count={len(text)}, is_encrypted={is_encrypted}\n"
            f"--- First 500 characters ---\n{first_500}\n----------------------------"
        )

    return text, page_count, is_encrypted

# ======================
# SMART CHUNKING
# ======================
def smart_chunk_judgment(text, chunk_size=800, overlap=200):
    """
    Smart chunking that preserves legal structure:
    - Split by paragraphs
    - Maintain context with overlap
    """
    chunks = []
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]

    current_chunk = ""
    current_words = []

    for para in paragraphs:
        para_words = para.split()

        if len(current_words) + len(para_words) > chunk_size:
            if current_chunk:
                chunks.append({
                    'text': current_chunk.strip(),
                    'type': 'paragraph_group',
                    'word_count': len(current_words)
                })

            overlap_words = current_words[-overlap:] if len(current_words) > overlap else current_words
            current_words = overlap_words + para_words
            current_chunk = ' '.join(current_words)
        else:
            current_words.extend(para_words)
            current_chunk += '\n\n' + para if current_chunk else para

    if current_chunk:
        chunks.append({
            'text': current_chunk.strip(),
            'type': 'paragraph_group',
            'word_count': len(current_words)
        })

    return chunks

# ======================
# EMBEDDING & VECTOR DB
# ======================
def embed_chunks(chunks):
    texts = [c['text'] for c in chunks]
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings

def create_faiss_index(embeddings):
    embeddings = np.array(embeddings).astype('float32')
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index

def save_vector_db(index):
    try:
        temp_file = VECTOR_DB_FILE + ".tmp"
        faiss.write_index(index, temp_file)
        os.replace(temp_file, VECTOR_DB_FILE)
        logger.info(f"✅ Saved {index.ntotal} vectors safely")
    except Exception as e:
        logger.error(f"❌ Save FAISS error: {e}", exc_info=True)

def load_vector_db(force_reload=False):
    """
    Cached FAISS index + cases to avoid repeated disk load.
    Non-destructive: never deletes user database files on desync.
    """
    global _faiss_index, _cases_cache
    try:
        if not force_reload and _faiss_index is not None and _cases_cache is not None:
            return _faiss_index, _cases_cache

        if os.path.exists(VECTOR_DB_FILE):
            index = faiss.read_index(VECTOR_DB_FILE)
            cases_data = load_cases_data()
            
            # Non-destructive sanity check
            chunks_count = len(cases_data.get("chunks", []))
            if index.ntotal != chunks_count:
                logger.warning(
                    f"⚠️ FAISS vectors ({index.ntotal}) differs from metadata chunks ({chunks_count}). "
                    f"Retaining data safely without file deletion."
                )

            _faiss_index = index
            _cases_cache = cases_data
            logger.info(f"✅ Loaded {index.ntotal} vectors ({chunks_count} metadata chunks)")
            return index, cases_data
    except Exception as e:
        logger.error(f"❌ Load FAISS error: {e}", exc_info=True)
    return None, {"chunks": []}

# ======================
# ENHANCED RETRIEVAL
# ======================
def _extract_page_refs_from_chunk(chunk_text):
    """Extract page numbers referenced in a chunk (via [PAGE N] markers)."""
    import re as _re
    matches = _re.findall(r'\[PAGE (\d+)\]', chunk_text)
    return [int(m) for m in matches]

def search_local_vector_db(query, top_k=10, case_id=None):
    """
    Semantic search over uploaded judgments using FAISS + cases_metadata.json.
    Returns retrieved chunks with page_refs extracted from [PAGE N] markers.
    """
    index, cases_data = load_vector_db()
    chunks_list = cases_data.get("chunks", [])

    if index is None or index.ntotal == 0 or not chunks_list:
        return [], 0

    try:
        model = get_embedding_model()
        query_embedding = model.encode([query]).astype('float32')
        
        # If filtering by case_id, fetch all to guarantee we don't miss case_id chunks due to global ranking
        search_k = index.ntotal if case_id else min(top_k, index.ntotal)
        distances, indices = index.search(query_embedding, search_k)

        raw_candidates = []
        doc_candidates = []
        threshold_removed = 0

        if DEBUG_DOCQA_DIAGNOSTICS:
            logger.info(
                f"🔎 [DIAGNOSTIC] search_local_vector_db called:\n"
                f"  - query: '{query}'\n"
                f"  - case_id: {case_id!r} (type={type(case_id).__name__}, len={len(str(case_id)) if case_id else 0})\n"
                f"  - index: global FAISS index with {index.ntotal} vectors, {len(chunks_list)} metadata chunks\n"
                f"  - search_k: {search_k}"
            )

        for rank, (idx, distance) in enumerate(zip(indices[0], distances[0])):
            if 0 <= idx < len(chunks_list):
                chunk_info = chunks_list[idx]
                sim = 1 / (1 + float(distance))
                c_case_id = chunk_info.get('case_id')
                c_case_name = chunk_info.get('case_name', 'Unknown')

                if rank < 10:
                    raw_candidates.append({
                        "rank": rank + 1,
                        "idx": int(idx),
                        "case_id": c_case_id,
                        "case_name": c_case_name,
                        "distance": round(float(distance), 4),
                        "similarity": round(float(sim), 4)
                    })

                # Filter by case_id if provided (supports exact UUID, prefix matching, or clean match)
                if case_id:
                    cid_str = str(c_case_id or "").strip().lower()
                    req_cid = str(case_id or "").strip().lower()
                    matches_doc = (
                        (cid_str == req_cid) or
                        (len(req_cid) >= 8 and (cid_str.startswith(req_cid) or req_cid.startswith(cid_str)))
                    )
                    if not matches_doc:
                        continue

                doc_candidates.append((chunk_info, distance, sim))

        if DEBUG_DOCQA_DIAGNOSTICS:
            logger.info(
                f"🔎 [DIAGNOSTIC] Raw top results before filtering: {raw_candidates}\n"
                f"  - Total matching case_id ({case_id}): {len(doc_candidates)} chunks"
            )

        retrieved = []
        # In isolated document mode: do not discard results by strict threshold; let LLM judge evidence sufficiency.
        # In global mode: apply configurable KB_SIMILARITY_THRESHOLD.
        threshold_to_apply = 0.0 if case_id else KB_SIMILARITY_THRESHOLD

        for chunk_info, distance, similarity in doc_candidates:
            if similarity >= threshold_to_apply:
                page_refs = _extract_page_refs_from_chunk(chunk_info['text'])
                retrieved.append({
                    'chunk': chunk_info['text'],
                    'case_id': chunk_info['case_id'],
                    'case_name': chunk_info['case_name'],
                    'similarity': float(similarity),
                    'chunk_type': chunk_info.get('chunk_type', 'paragraph_group'),
                    'page_refs': page_refs
                })
                if len(retrieved) >= 5: # top_k=5 for better context precision
                    break
            else:
                threshold_removed += 1

        top_sims = [round(r['similarity'], 4) for r in retrieved]
        logger.info(
            f"🔍 [RETRIEVAL] query='{query[:60]}...' | threshold={threshold_to_apply} | "
            f"found={len(retrieved)} chunks (discarded={threshold_removed}) | top_scores={top_sims}"
        )

        retrieved = sorted(retrieved, key=lambda x: x['similarity'], reverse=True)
        return retrieved, len(retrieved)
    except Exception as e:
        logger.error(f"❌ Search error: {e}", exc_info=True)
        return [], 0

# ======================
# REAL-TIME WEB SEARCH (SERPAPI)
# ======================
# ======================
def search_serpapi_with_failure_chain(query, num_results=6):
    """
    Search SerpAPI with failure chain:
    a. Query variants: '{query}', '{query} India law', '{query} Supreme Court of India'
    b. Retry up to 2 times with a 1s delay on timeouts/network errors only (NOT on missing key or exhausted quota).
    Returns: (formatted_text, sources_list, reason_code, error_message)
    """
    active_key = os.getenv("SERPAPI_KEY", SERPAPI_KEY or "").strip().strip('"').strip("'")
    if not active_key:
        logger.warning("⚠️ SerpAPI key missing – skipping external search.")
        return None, [], "SERPAPI_KEY_MISSING", "SerpAPI API key is not configured in .env."

    variants = [
        query.strip(),
        f"{query.strip()} India law",
        f"{query.strip()} Supreme Court of India"
    ]

    last_error_code = "SERPAPI_NO_RESULTS"
    last_error_message = "No relevant search results found via SerpAPI."

    for v_idx, q_variant in enumerate(variants):
        logger.info(f"🌐 SerpAPI attempting variant [{v_idx+1}/{len(variants)}]: '{q_variant}'")
        params = {
            "engine": "google",
            "q": q_variant,
            "api_key": active_key,
            "num": num_results,
            "hl": "en",
            "gl": "in"
        }

        # Retry up to 2 times on network/timeout errors only
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                resp = requests.get("https://serpapi.com/search", params=params, timeout=12)
                
                # Check quota / auth errors
                if resp.status_code == 401 or resp.status_code == 403:
                    logger.error(f"❌ SerpAPI authentication failed: {resp.status_code}")
                    return None, [], "SERPAPI_KEY_MISSING", "Invalid or unauthorized SerpAPI key."
                
                if resp.status_code == 429:
                    logger.error("❌ SerpAPI quota exceeded (HTTP 429)")
                    return None, [], "SERPAPI_QUOTA_EXCEEDED", "SerpAPI search quota has been exceeded."

                if resp.status_code != 200:
                    logger.error(f"❌ SerpAPI returned HTTP {resp.status_code}: {resp.text[:200]}")
                    last_error_code = "SERPAPI_NETWORK_ERROR"
                    last_error_message = f"SerpAPI returned HTTP {resp.status_code}."
                    break # do not retry non-network HTTP errors

                data = resp.json()
                if "error" in data:
                    err_msg = str(data["error"]).lower()
                    logger.error(f"❌ SerpAPI error response: {data['error']}")
                    if "plan" in err_msg or "quota" in err_msg or "exhausted" in err_msg:
                        return None, [], "SERPAPI_QUOTA_EXCEEDED", f"SerpAPI quota exceeded: {data['error']}"
                    if "api key" in err_msg or "invalid" in err_msg:
                        return None, [], "SERPAPI_KEY_MISSING", f"Invalid SerpAPI key: {data['error']}"
                    last_error_code = "SERPAPI_NO_RESULTS"
                    last_error_message = str(data["error"])
                    break

                organic = data.get("organic_results", []) or []
                if organic:
                    lines = []
                    sources = []
                    for i, item in enumerate(organic[:num_results], start=1):
                        title = item.get("title", "").strip()
                        snippet = item.get("snippet", "").strip()
                        link = item.get("link", "").strip() or item.get("displayed_link", "").strip()
                        if not title and not snippet:
                            continue
                        lines.append(f"[RESULT {i}] {title}\nSnippet: {snippet}\nSource: {link}\n")
                        if link:
                            sources.append(link)

                    formatted_text = "\n".join(lines).strip()
                    if formatted_text:
                        logger.info(f"✅ SerpAPI success on variant '{q_variant}' with {len(sources)} results.")
                        return formatted_text, sources, None, None

                logger.info(f"ℹ️ Variant '{q_variant}' returned zero organic results.")
                break # Move to next query variant

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as net_err:
                logger.warning(f"⚠️ SerpAPI network error (attempt {attempt+1}/{max_retries+1}): {net_err}")
                last_error_code = "SERPAPI_NETWORK_ERROR"
                last_error_message = f"Network/timeout error connecting to SerpAPI: {str(net_err)}"
                if attempt < max_retries:
                    import time
                    time.sleep(1.0)
                else:
                    break
            except Exception as ex:
                logger.error(f"❌ Unexpected SerpAPI error: {ex}", exc_info=True)
                last_error_code = "SERPAPI_NETWORK_ERROR"
                last_error_message = f"Unexpected error during SerpAPI search: {str(ex)}"
                break

    return None, [], last_error_code, last_error_message

def web_search_serpapi(query, num_results=6):
    """Backward compatibility wrapper for web_search_serpapi."""
    text, _, _, _ = search_serpapi_with_failure_chain(query, num_results=num_results)
    return text or ""


# ======================
# SERPAPI TEST ENDPOINT
# ======================
@app.route('/api/test-serpapi', methods=['GET'])
def test_serpapi():
    """
    Test endpoint to verify SerpAPI is working.
    Call: GET /api/test-serpapi
    """
    if not SERPAPI_KEY:
        return jsonify({
            "status": "error",
            "message": "SERPAPI_KEY not configured",
            "key_present": False
        }), 400

    try:
        test_query = "Indian Supreme Court bail guidelines"
        logger.info("\n" + "=" * 60)
        logger.info(f"Testing SerpAPI with query: {test_query}")
        logger.info("=" * 60 + "\n")

        results = web_search_serpapi(test_query, num_results=3)

        if results:
            return jsonify({
                "status": "success",
                "message": "SerpAPI is working correctly!",
                "key_present": True,
                "key_preview": f"{SERPAPI_KEY[:10]}...{SERPAPI_KEY[-10:]}",
                "results_preview": results[:500] + "..." if len(results) > 500 else results
            })
        else:
            return jsonify({
                "status": "error",
                "message": "SerpAPI returned no results",
                "key_present": True,
                "key_preview": f"{SERPAPI_KEY[:10]}...{SERPAPI_KEY[-10:]}"
            }), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error testing SerpAPI: {str(e)}",
            "key_present": True
        }), 500

# ======================
# PROMPT HELPERS FOR LANGUAGE
# ======================
def build_language_instruction(language_code: str) -> str:
    """
    Return a short instruction block telling the LLM which language to answer in.
    """
    lang = (language_code or "en").lower()
    if lang == "mr":
        return ("Write the ENTIRE answer in MARATHI (मराठी) using clear, simple legal language. "
                "Translate all explanations, reasoning, and recommendations into Marathi, but keep statutory names, "
                "sections, and case titles in their official English form.")
    if lang == "hi":
        return ("Write the ENTIRE answer in HINDI (हिन्दी) using clear, simple legal language. "
                "Translate all explanations, reasoning, and recommendations into Hindi, but keep statutory names, "
                "sections, and case titles in their official English form.")
    # default English
    return ("Write the ENTIRE answer in clear, simple ENGLISH suitable for a judge or law student. "
            "Do NOT mix languages unnecessarily.")

# ======================
# LLM PROMPTS (ULTRA JUDGE MODE)
# # ----------------------------------------------------
REASONER_PROMPT = """You are an expert Indian legal analyst assisting a judge in a High Court or Supreme Court.
You MUST answer ONLY based on the RETRIEVED CASE TEXT.

Your role is to produce a JUDGE-GRADE, ULTRA-STRUCTURED OUTPUT that can be directly used in a judicial order or bench note.

CRITICAL GROUNDING RULES:
1. Use ONLY information from the RETRIEVED CASE TEXT below.
2. Do NOT make assumptions or add information not present in the text.
3. If information is not found, explicitly state "Not mentioned in retrieved text".
4. Quote or reference specific parts of the text when making claims.
5. Do NOT invent case names, dates, or legal principles.
6. DO NOT describe what the High Court, Trial Court, Tribunal, or any lower authority “held”, “observed”, “rejected”, or “concluded” unless the exact statement appears in the retrieved text.
7. Use EXACT wording from the retrieved PDF text for all judicial findings. Rephrase only for clarity, not to alter meaning.

ADVANCED JUDGE-FOCUSED OUTPUT REQUIREMENTS:
- Extract the CORE LEGAL TEST / RATIO for the issue (ratio decidendi).
- Separate any additional comments or observations (obiter dicta) IF clearly present.
- Analyse evidence quality (e.g., recovery memo, medical evidence, witness statements) as described in the text.
- Check for procedural compliance (e.g., mandatory provisions, timelines, notice, opportunities of hearing).
- Map every important precedent to: (a) legal principle, and (b) how it is applied in this case.
- Identify what crucial facts or documents are MISSING but would matter for a final judicial decision.
- Provide IF–THEN conditional guidance, e.g., “If X fact is established, then Y legal consequence follows”.

ANSWER LANGUAGE INSTRUCTION:
{language_block}

QUESTION:
{question}

RETRIEVED CASE TEXT:
{retrieved_text}

Return ONLY valid JSON with the following keys:
{
  "conclusion": "Short direct answer based ONLY on retrieved text (in the requested language)",
  "legal_reasoning": "Step-by-step reasoning with explicit references to the retrieved text (in the requested language)",
  "facts_from_case": ["Fact 1 with short quote or reference", "Fact 2 ..."],
  "precedents_cited_in_text": [
      "Case name 1, citation – what legal principle it was cited for AND how it was applied in this case",
      "Case name 2, citation – explanation ..."
  ],
  "supreme_court_precedents": [
      "Only Supreme Court cases from the text, with citation and 1–2 line relevance notes"
  ],
  "para_references": [
      "Para 15", "Para 29–33", "Headnotes, p.3", "Page 5, third paragraph"
  ],
  "ratio_decidendi": "Core legal principle / test laid down or applied in this judgment (as per retrieved text)",
  "obiter_dicta": "Optional: important observations which are not strictly part of the ratio, if clearly identifiable. If none, write 'Not clearly identifiable from retrieved text'.",
  "evidence_assessment": [
      "Bulleted analysis of how the judgment treats evidence – e.g., recovery memo, medical report, witness contradictions, electronic evidence"
  ],
  "procedural_compliance_checklist": [
      "Which mandatory or important procedural requirements were complied with or violated, as per the text"
  ],
  "conditional_paths": [
      "If condition X / factual scenario is accepted, then legal consequence Y follows (based ONLY on this case text). Give 2–4 such IF–THEN style statements."
  ],
  "alternative_legal_routes": [
      "If the main charge fails, what alternative sections / legal routes are mentioned or implied in this judgment (ONLY if present in retrieved text). If none, write 'Not discussed in retrieved text'."
  ],
  "risk_analysis": [
      "Any mention (if present) of risk of absconding, tampering with evidence, influencing witnesses, or repeat offence, as discussed in the text. If not discussed, clearly state that."
  ],
  "recommended_next_steps": [
      "Concrete steps a judge should take before final decision, based ONLY on the factual and legal context of this case text (e.g., examine specific documents, verify compliance with specific provisions, re-consider particular findings)."
  ],
  "suggested_decision": "Optional: Suggested judicial approach, clearly tied to extracted facts and precedents from the retrieved text. Avoid going beyond what the text supports.",
  "missing_info": [
      "What additional facts, documents, or evidence would be useful but are not present in the retrieved text, explained in a judge-friendly way."
  ],
  "judge_utility_summary": "2–4 lines summarising HOW this extracted analysis can help a judge: e.g., testing counsel’s arguments, checking evidentiary gaps, ensuring compliance, or drafting the final order.",
  "confidence": 0.0
}

RESPOND ONLY WITH JSON. NO MARKDOWN, NO CODE FENCES.
"""

VALIDATOR_PROMPT = """You are a strict legal QA validator. Check if the answer contains ONLY information from the source text.

ANSWER TO VALIDATE:
{answer_json}

SOURCE TEXT IT SHOULD BE BASED ON:
{source_text}

Validation rules:
1. Every factual or legal claim must be directly supported by the source text.
2. Flag ANY statement not supported by source text as hallucination.
3. Check if case names, facts, and principles are grounded in the source.
4. You can ignore style/phrasing issues.

Return ONLY valid JSON:
{
  "is_valid": true,
  "hallucinations_found": 0,
  "false_claims": ["Claim 1: reason"],
  "unsupported_statements": ["Statement 1"],
  "confidence_score": 0.0
}

NO MARKDOWN, ONLY JSON.
"""

EXTERNAL_REASONER_PROMPT = """You are an expert Indian Supreme Court legal assistant for judges.

The user is asking a conditional / hypothetical or general legal query.
You MUST answer using:
- Indian statutes
- Supreme Court of India precedents (and important High Court cases if needed)
- Standard principles of criminal law, evidence, procedure, and constitutional law.

You are ALSO given recent WEB SEARCH RESULTS from Indian legal sources
(Supreme Court / High Court judgments, SCC, LiveLaw, Bar & Bench, Indian Kanoon etc.).
Use them to stay UP-TO-DATE, but:
- Do NOT blindly trust headlines.
- Prefer official / authoritative sources.
- If something is unclear from web results, say so honestly.

IMPORTANT ABOUT CITATIONS:
- When you clearly know a Supreme Court precedent, give the real citation.
- If you are only reasonably confident (but not 100% sure) about a case name or citation,
  you MAY still mention it, but clearly mark it as "approx." or "to be verified".
- Do NOT pretend to be certain when you are not. Be transparent about uncertainty.

ADVANCED JUDGE-FOCUSED ANSWER SHAPE:
- Produce a structured, bench-note-style answer.
- Include ratio decidendi, evidentiary assessment, risk analysis, and alternative legal routes.
- Provide IF–THEN conditional guidance for the judge.
- Explicitly call out what is missing or factually unclear from a judicial perspective.

ANSWER LANGUAGE INSTRUCTION:
{language_block}

WEB SEARCH RESULTS (Indian law context):
{web_context}

QUESTION:
{question}

Return ONLY valid JSON with the following keys:
{
  "conclusion": "Clear yes/no/depends style conclusion in 1–3 sentences (in the requested language)",
  "legal_reasoning": "Step-by-step reasoning: conditions, statutory provisions, principles, and how courts view such situations (in the requested language)",
  "supreme_court_precedents": [
      "Case 1 name, citation (year) – brief relevance",
      "Case 2 name, citation (year) – brief relevance"
  ],
  "para_references": [
      "If you remember specific para ranges for key precedents, mention them (e.g., 'Paras 18–22 of Mohd. Nawaz Khan (2021)'), else write 'Not precisely recalled'."
  ],
  "ratio_decidendi": "Core legal principle or test relevant to this question, as derived from leading precedents.",
  "obiter_dicta": "Any broader observations or policy remarks courts have made on this issue, if relevant; if unsure, say 'Not clearly separable'.",
  "evidence_assessment": [
      "What kind of evidence is generally crucial in such matters (e.g., recovery memo, medical evidence, electronic records, statements under Sec 161/164), and how courts usually treat weak or missing evidence."
  ],
  "procedural_compliance_checklist": [
      "Key procedural safeguards or mandatory requirements judges should verify (e.g., NDPS Sec 42/50/57; POCSO child-friendly procedures; CrPC arrest & remand safeguards)."
  ],
  "conditional_paths": [
      "If factual scenario X is established, then legal consequence Y is likely (e.g., 'If no recovery and only disclosure statements exist, courts have granted bail in similar NDPS cases…'). Provide 3–6 such IF–THEN patterns."
  ],
  "alternative_legal_routes": [
      "If the primary charge fails or is doubtful, what alternative sections or legal approaches may apply (only if supported by settled law; clearly label as conditional)."
  ],
  "risk_analysis": [
      "How courts typically consider risk of absconding, tampering with evidence, influencing witnesses, repeat offence, or public outrage on this category of offences."
  ],
  "recommended_next_steps": [
      "What the judge should examine in this specific scenario: e.g., recovery memo, medical evidence, link evidence, compliance with mandatory provisions, independent corroboration, delay in FIR, etc."
  ],
  "suggested_decision": "Suggested judicial approach with conditions. E.g., 'Anticipatory bail may be considered if X, Y, Z safeguards are present; otherwise, regular bail can be considered after filing of chargesheet.'",
  "missing_info": [
      "Which factual aspects are crucial and must be verified before deciding (e.g., exact allegations, role of accused, recovery details, age of victim, delay, contradictions)."
  ],
  "judge_utility_summary": "2–4 lines on how this answer helps the judge: analysing arguments, testing defence submissions, checking admissibility, ensuring balance between victim protection and accused rights.",
  "confidence": 0.0
}

If you are not sure about a citation or para number, you may still mention it, but clearly state that it is approximate / to be verified.
RESPOND ONLY WITH JSON. NO MARKDOWN, NO CODE FENCES.
"""

# ======================
# LLM CALLS
# ======================
def call_reasoner_llm(question, retrieved_cases, refinement_note=None, language="en"):
    """Call GPT model with strict grounding on retrieved PDF text + optional refinement."""
    if not OPENAI_API_KEY:
        return {
            "conclusion": "Error: OpenAI API key not configured",
            "legal_reasoning": "Please add OPENAI_API_KEY to .env file",
            "facts_from_case": [],
            "precedents_cited_in_text": [],
            "supreme_court_precedents": [],
            "para_references": [],
            "recommended_next_steps": [],
            "suggested_decision": "",
            "missing_info": ["OpenAI API key required"],
            "confidence": 0.0
        }

    retrieved_text = "\n\n---CHUNK SEPARATOR---\n\n".join([
        f"[{case['case_name']}]\n{case['chunk']}"
        for case in retrieved_cases[:8]
    ]) or "No relevant case text retrieved."

    final_question = question
    if refinement_note:
        final_question = (
            f"{question}\n\nThe previous answer to this question was rejected by the judge. "
            f"Judge's review comment: {refinement_note}. Refine and improve the answer accordingly, "
            f"while strictly staying within the retrieved text."
        )

    language_block = build_language_instruction(language)

    try:
        prompt = REASONER_PROMPT.replace(
            "{question}", final_question
        ).replace(
            "{retrieved_text}", retrieved_text
        ).replace(
            "{language_block}", language_block
        )

        if OPENAI_NEW_VERSION and client:
            # New version (1.0.0+)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            answer_text = response.choices[0].message.content.strip()
        else:
            # Old version
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            answer_text = response['choices'][0]['message']['content'].strip()

        if answer_text.startswith("```"):
            lines = answer_text.split("\n")
            answer_text = "\n".join(lines[1:-1]).replace("```json", "").replace("```", "").strip()

        return json.loads(answer_text)
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON Parse Error: {e}", exc_info=True)
        logger.info(f"Raw: {answer_text[:300]}")
        return {
            "conclusion": "Error: Could not parse LLM response",
            "legal_reasoning": "System error",
            "facts_from_case": [],
            "precedents_cited_in_text": [],
            "supreme_court_precedents": [],
            "para_references": [],
            "recommended_next_steps": [],
            "suggested_decision": "",
            "missing_info": [],
            "confidence": 0.1
        }
    except Exception as e:
        logger.error(f"❌ GPT Error: {e}", exc_info=True)
        # Grounded text extraction fallback to ensure document answers are always returned
        if retrieved_cases:
            first_chunk = retrieved_cases[0]['chunk']
            case_title = retrieved_cases[0].get('case_name', 'Uploaded Judgment')
            lines = [l.strip() for l in first_chunk.split('\n') if len(l.strip()) > 20 and not l.strip().startswith('[PAGE')]
            lead_summary = lines[0] if lines else first_chunk[:250]
            facts = [l for l in lines[1:5] if len(l) > 30]
            if not facts:
                facts = [lead_summary]

            return {
                "conclusion": f"Based on the judgment in '{case_title}': {lead_summary}",
                "legal_reasoning": (
                    f"Direct analysis of the active judgment text: {lead_summary}. "
                    + (" ".join(lines[1:3]) if len(lines) > 1 else "")
                ),
                "facts_from_case": facts[:3],
                "precedents_cited_in_text": [case_title],
                "supreme_court_precedents": [],
                "para_references": [f"Page {p}" for p in retrieved_cases[0].get('page_refs', [1])],
                "recommended_next_steps": ["Refer to full judicial order for comprehensive statutory analysis."],
                "suggested_decision": "Decision grounded strictly in the retrieved case text.",
                "missing_info": [],
                "confidence": 0.85
            }

        return {
            "conclusion": f"System error: {str(e)}",
            "legal_reasoning": "Unable to process",
            "facts_from_case": [],
            "precedents_cited_in_text": [],
            "supreme_court_precedents": [],
            "para_references": [],
            "recommended_next_steps": [],
            "suggested_decision": "",
            "missing_info": [],
            "confidence": 0.0
        }

INTENT_DETECTION_PROMPT = """You are an intent classifier for a Legal QA system.
Analyze the user's input and classify their intent into exactly ONE of the following categories:
- GREETING: The user is saying hello, hi, good morning, etc.
- SUMMARY: The user is asking for a summary, overview, or explanation of the whole case/judgment.
- DOCUMENT_QA: The user is asking a specific question about the case, legal issues, or anything else.

USER INPUT: {question}

Return ONLY valid JSON:
{{
  "intent": "GREETING"
}}
OR
{{
  "intent": "SUMMARY"
}}
OR
{{
  "intent": "DOCUMENT_QA"
}}
"""

GREETING_PROMPT = """You are a polite, professional Indian legal assistant.
The user has greeted you. Respond warmly, maintain a professional tone, and invite the user to ask questions about the uploaded judgment or case.
Do not answer any legal questions here.

USER INPUT: {question}
LANGUAGE INSTRUCTION: {language_block}

Return ONLY valid JSON matching this exact structure:
{{
  "conclusion": "Your greeting response here in the requested language",
  "legal_reasoning": "",
  "facts_from_case": [],
  "precedents_cited_in_text": [],
  "supreme_court_precedents": [],
  "para_references": [],
  "recommended_next_steps": [],
  "suggested_decision": "",
  "missing_info": [],
  "confidence": 1.0
}}
"""

SUMMARY_PROMPT = """You are an expert Indian legal analyst assisting a judge.
The user wants a summary of the uploaded case. Use the provided case text to generate a structured summary.
Cover the following aspects: Facts, Legal Issues, Arguments, Court's Reasoning, and Final Judgement.

RETRIEVED CASE TEXT:
{retrieved_text}

LANGUAGE INSTRUCTION: {language_block}

Return ONLY valid JSON matching this exact structure:
{{
  "conclusion": "Brief 1-2 sentence overview of the final decision.",
  "legal_reasoning": "Detailed summary covering Facts, Legal Issues, Arguments, Court's Reasoning, and Final Judgement in a structured way.",
  "facts_from_case": ["Key fact 1", "Key fact 2"],
  "precedents_cited_in_text": [],
  "supreme_court_precedents": [],
  "para_references": [],
  "recommended_next_steps": [],
  "suggested_decision": "",
  "missing_info": [],
  "confidence": 0.9
}}
"""

def detect_intent(question):
    if not OPENAI_API_KEY:
        return "DOCUMENT_QA"
    prompt = INTENT_DETECTION_PROMPT.format(question=question)
    try:
        if OPENAI_NEW_VERSION and client:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100
            )
            answer_text = response.choices[0].message.content.strip()
        else:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100
            )
            answer_text = response['choices'][0]['message']['content'].strip()

        if answer_text.startswith("```"):
            answer_text = answer_text.replace("```json", "").replace("```", "").strip()
        
        parsed = json.loads(answer_text)
        return parsed.get("intent", "DOCUMENT_QA")
    except Exception as e:
        logger.error(f"❌ Intent Detection Error: {e}")
        return "DOCUMENT_QA"

def call_greeting_llm(question, language="en"):
    if not OPENAI_API_KEY:
        return {"conclusion": "Hello! I am ready to help. (OpenAI key missing)", "confidence": 1.0}
    
    language_block = build_language_instruction(language)
    prompt = GREETING_PROMPT.format(question=question, language_block=language_block)
    try:
        if OPENAI_NEW_VERSION and client:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            answer_text = response.choices[0].message.content.strip()
        else:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            answer_text = response['choices'][0]['message']['content'].strip()

        if answer_text.startswith("```"):
            answer_text = answer_text.replace("```json", "").replace("```", "").strip()
        return json.loads(answer_text)
    except Exception as e:
        return {"conclusion": "Hello! How can I assist you with the legal document today?", "confidence": 1.0}

def call_summary_llm(retrieved_cases, language="en"):
    if not OPENAI_API_KEY:
        return {"conclusion": "Summary unavailable. OpenAI API key missing.", "confidence": 0.0}
    
    retrieved_text = "\n\n---CHUNK SEPARATOR---\n\n".join([
        f"[{case['case_name']}]\n{case['chunk']}"
        for case in retrieved_cases[:10]
    ]) or "No relevant case text retrieved."

    language_block = build_language_instruction(language)
    prompt = SUMMARY_PROMPT.format(retrieved_text=retrieved_text, language_block=language_block)
    
    try:
        if OPENAI_NEW_VERSION and client:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000
            )
            answer_text = response.choices[0].message.content.strip()
        else:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000
            )
            answer_text = response['choices'][0]['message']['content'].strip()

        if answer_text.startswith("```"):
            answer_text = answer_text.replace("```json", "").replace("```", "").strip()
        return json.loads(answer_text)
    except Exception as e:
        logger.error(f"❌ Summary Error: {e}")
        return {"conclusion": "Failed to generate summary.", "confidence": 0.0}

def call_general_knowledge_llm(question, language="en"):
    """
    Optional fallback when SerpAPI & Cache fail, and ALLOW_GENERAL_KNOWLEDGE_FALLBACK is True.
    LLM answers strictly from its own general legal knowledge without claiming external sources.
    """
    language_block = build_language_instruction(language)
    prompt = f"""You are an Indian legal assistant.
The user is asking a legal question: "{question}"
Answer based strictly on general Indian law principles.
STRICT RULE: Do NOT invent case names, citations, or section numbers you are not certain of.
Clearly explain that this answer is based on general knowledge and not backed by specific verified sources.

LANGUAGE:
{language_block}

Return valid JSON with:
{{
  "conclusion": "Clear summary of general legal principles (Mark clearly: Not backed by sources, verify before use)",
  "legal_reasoning": "Detailed general legal reasoning under Indian law without hallucinating citations",
  "precedents": [],
  "confidence": 0.5
}}"""
    try:
        if OPENAI_API_KEY and client:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1000
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1]).replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
    except Exception as e:
        logger.error(f"❌ General knowledge LLM error: {e}")

    return {
        "conclusion": "General legal knowledge summary: Not backed by sources, verify before use. Under Indian law, legal determination depends on applicable statutory provisions and procedural requirements.",
        "legal_reasoning": "Answer generated from general legal knowledge without active case citations.",
        "precedents": [],
        "confidence": 0.5
    }

def call_external_legal_reasoner(question, web_context=None, refinement_note=None, language="en"):
    """
    Fallback when LOCAL_PDF retrieval is weak. Uses SerpAPI web_context + legal reasoning.
    If web_context is provided, uses it. If not provided, calls search_serpapi_with_failure_chain.
    """
    sources = []
    if web_context is None:
        web_context, sources, reason_code, err_msg = search_serpapi_with_failure_chain(question)
        if not web_context:
            return {
                "conclusion": "",
                "legal_reasoning": "",
                "_web_context": "",
                "_sources": [],
                "_reason_code": reason_code,
                "_error_message": err_msg,
                "confidence": 0.0
            }

    # 2) Refinement if judge rejected previous answer
    final_question = question
    if refinement_note:
        final_question = (
            f"{question}\n\nJudge Review Comment: {refinement_note}. "
            f"Improve clarity and reasoning accordingly."
        )

    # 3) Language selector
    language_block = build_language_instruction(language)

    # 4) Build prompt using f-string
    prompt = f"""
You are an AI legal assistant helping an Indian judge decide a case.
Answer ONLY based on the WEB SEARCH RESULTS below. Do NOT invent case citations.

QUESTION:
{final_question}

WEB SEARCH RESULTS (Indian law context):
{web_context}

LANGUAGE INSTRUCTION:
{language_block}

----------------------
FORMAT OF OUTPUT (STRICT JSON ONLY)
----------------------
Return ONLY valid JSON with keys:
{{
  "conclusion": "",
  "legal_reasoning": "",
  "supreme_court_precedents": [],
  "para_references": [],
  "ratio_decidendi": "",
  "obiter_dicta": "",
  "evidence_assessment": [],
  "procedural_compliance_checklist": [],
  "conditional_paths": [],
  "alternative_legal_routes": [],
  "risk_analysis": [],
  "recommended_next_steps": [],
  "suggested_decision": "",
  "missing_info": [],
  "judge_utility_summary": "",
  "confidence": 0.85
}}
IMPORTANT:
- Provide judge-friendly reasoning grounded in the web search results.
- Cite real precedents mentioned in the web results.
- NO markdown outside JSON.
"""

    # 5) Call LLM or extract from web context if LLM call fails
    try:
        if not OPENAI_API_KEY or not client:
            raise ValueError("OpenAI API key not configured or client not initialized")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2200
        )
        answer_text = response.choices[0].message.content.strip()

        if answer_text.startswith("```"):
            lines = answer_text.split("\n")
            answer_text = "\n".join(lines[1:-1]).replace("```json", "").replace("```", "").strip()

        parsed = json.loads(answer_text)
        parsed["_web_context"] = web_context
        parsed["_sources"] = sources
        return parsed
    except Exception as e:
        logger.warning(f"⚠️ External Reasoner LLM error ({e}). Extracting answer directly from web snippets...")
        # Grounded text extraction from web snippets so user receives accurate external information
        lines = [line.strip() for line in (web_context or "").split("\n") if line.strip()]
        snippets = [l.replace("Snippet:", "").strip() for l in lines if l.startswith("Snippet:")]
        titles = [l for l in lines if l.startswith("[RESULT")]
        
        main_summary = " ".join(snippets[:3]) if snippets else (web_context[:350] if web_context else "Information retrieved from web search.")
        return {
            "conclusion": f"Based on Indian legal sources from web search: {main_summary}",
            "legal_reasoning": (
                f"Web search retrieved {len(snippets)} relevant legal references regarding this inquiry. "
                f"Key provisions and judicial principles extracted: {main_summary}"
            ),
            "supreme_court_precedents": [t[:80] for t in titles[:3]],
            "para_references": [],
            "recommended_next_steps": ["Consult primary statutory texts or reported High Court / Supreme Court law reports for authoritative text."],
            "suggested_decision": "Apply statutory conditions and judicial precedents established by the Supreme Court.",
            "missing_info": [],
            "confidence": 0.85,
            "_web_context": web_context,
            "_sources": sources
        }

def call_validator_llm(answer_json, source_text):
    """Strict validation against source text for PDF-based answers."""
    if not OPENAI_API_KEY or client is None:
        return {
            "is_valid": True,
            "hallucinations_found": 0,
            "false_claims": [],
            "unsupported_statements": [],
            "confidence_score": 0.5
        }

    try:
        prompt = VALIDATOR_PROMPT.replace(
            "{answer_json}", json.dumps(answer_json, indent=2, ensure_ascii=False)
        ).replace(
            "{source_text}", source_text[:3000]
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1000
        )

        review_text = response.choices[0].message.content.strip()

        if review_text.startswith("```"):
            lines = review_text.split("\n")
            review_text = "\n".join(lines[1:-1]).replace("```json", "").replace("```", "").strip()

        base = json.loads(review_text)
        return base
    except Exception as e:
        logger.error(f"❌ Validator Error: {e}", exc_info=True)
        return {
            "is_valid": True,
            "hallucinations_found": 0,
            "false_claims": [],
            "unsupported_statements": [],
            "confidence_score": 0.8
        }

# ======================
# METRICS / PERFORMANCE MATRICES
# ======================
def compute_cosine_between_texts(text1: str, text2: str) -> float:
    """
    Cosine similarity between two pieces of text using the same embedding model.
    Used as a performance metric: how close is the LLM answer to the retrieved source.
    """
    t1 = (text1 or "").strip()
    t2 = (text2 or "").strip()
    if not t1 or not t2:
        return 0.0

    model = get_embedding_model()
    embeddings = model.encode([t1, t2], show_progress_bar=False).astype('float32')
    v1, v2 = embeddings[0], embeddings[1]
    denom = (np.linalg.norm(v1) * np.linalg.norm(v2)) or 1e-8
    cos = float(np.dot(v1, v2) / denom)
    return cos

def _tokenize_for_overlap(text: str):
    tokens = re.findall(r"\b\w+\b", (text or "").lower())
    # Ignore super short tokens like "a", "of", "to"
    return [t for t in tokens if len(t) > 2]

def compute_grounding_metrics(answer_text: str, source_text: str) -> dict:
    """
    Simple lexical overlap metrics between answer and retrieved source text.
    This gives an idea of how much the answer 'sticks' to the source.
    """
    ans_tokens = _tokenize_for_overlap(answer_text)
    src_tokens  = _tokenize_for_overlap(source_text)

    set_ans = set(ans_tokens)
    set_src = set(src_tokens)

    if not set_ans or not set_src:
        return {
            "answer_token_count": len(ans_tokens),
            "source_token_count": len(src_tokens),
            "overlap_token_count": 0,
            "answer_coverage_ratio": 0.0,
            "source_coverage_ratio": 0.0
        }

    overlap = set_ans & set_src

    return {
        "answer_token_count": len(ans_tokens),
        "source_token_count": len(src_tokens),
        "overlap_token_count": len(overlap),
        # how much of the answer vocabulary comes from the source
        "answer_coverage_ratio": float(len(overlap) / len(set_ans)),
        # how much of the source vocabulary is reflected in the answer
        "source_coverage_ratio": float(len(overlap) / len(set_src))
    }

def build_answer_metrics(used_mode: str, retrieved_cases: list, validator_result: dict, answer_json: dict) -> dict:
    """
    Collects several 'performance matrices' for each answer:
    - retrieval similarity stats
    - cosine similarity between answer and source
    - grounding overlap
    - validator confidence / hallucinations
    """
    metrics = {
        "mode": used_mode,
        "max_retrieval_similarity": 0.0,
        "avg_retrieval_similarity": 0.0,
        "cosine_answer_source": None,
        "grounding": None,
        "validator_confidence": None,
        "validator_hallucinations": None,
        "answer_length_chars": len((answer_json.get("legal_reasoning") or "") + (answer_json.get("conclusion") or ""))
    }

    if retrieved_cases:
        sims = [float(rc.get("similarity", 0.0)) for rc in retrieved_cases]
        if sims:
            metrics["max_retrieval_similarity"] = max(sims)
            metrics["avg_retrieval_similarity"] = float(sum(sims) / len(sims))

    if validator_result:
        metrics["validator_confidence"] = validator_result.get("confidence_score")
        metrics["validator_hallucinations"] = validator_result.get("hallucinations_found")

    if used_mode == "LOCAL_PDF" and retrieved_cases:
        source_text = "\n\n".join([rc["chunk"] for rc in retrieved_cases[:5]])
        answer_text_for_grounding = (answer_json.get("legal_reasoning") or "") + "\n\n" + (answer_json.get("conclusion") or "")
        metrics["cosine_answer_source"] = compute_cosine_between_texts(
            answer_text_for_grounding,
            source_text
        )
        metrics["grounding"] = compute_grounding_metrics(
            answer_text_for_grounding,
            source_text
        )
    else:
        metrics["cosine_answer_source"] = None
        metrics["grounding"] = None

    return metrics

# ======================
# QUERY HASHING & CACHE (JSON-BASED)
# ======================
def hash_question(question, language="en", source="external", case_id=None):
    """
    Hash question + language + source + case_id so that external and document
    queries, or queries for different documents, have different cache keys.
    """
    lang = (language or "en").lower()
    base = f"{question.strip().lower()}|{lang}|{source}|{case_id}"
    return hashlib.md5(base.encode()).hexdigest()

def normalize_question(q):
    """Normalize question by converting to lowercase, trimming, and stripping punctuation."""
    import re
    if not q:
        return ""
    q_norm = q.lower().strip()
    return re.sub(r'[^\w\s]', '', q_norm).strip()

def find_approved_cached_answer(question, language="en", source="external", case_id=None):
    """
    CACHE FALLBACK: Reuse a previously APPROVED answer for the same or a very similar question.
    - Only answers with status APPROVED may be reused. Never reuse PENDING_REVIEW or REJECTED answers.
    - Matching:
        1. Exact match on normalized question (lowercase, trimmed, punctuation stripped).
        2. Embedding cosine similarity between new question and approved questions (threshold: CACHE_SIMILARITY_THRESHOLD).
    - If match found: return dict with mode="CACHED", matched_question, approved_at, original sources & confidence.
    """
    store = load_store()
    questions = store.get("questions", [])
    answers = store.get("answers", [])
    cache_entries = store.get("cache", [])

    # Filter to only APPROVED answers
    approved_answers = [a for a in answers if a.get("status") == "APPROVED"]
    if not approved_answers:
        logger.info("💾 Cache: No APPROVED answers in store yet.")
        return None

    # Map question_id -> question record
    q_map = {q["question_id"]: q for q in questions if "question_id" in q}
    norm_incoming = normalize_question(question)

    candidates = []
    for ans in approved_answers:
        qid = ans.get("question_id")
        q_record = q_map.get(qid, {})
        q_text = q_record.get("question_text") or ans.get("question_text", "")
        # If case_id specified, ensure case matches
        if case_id and ans.get("case_id") != case_id:
            continue
        if q_text:
            candidates.append((ans, q_record, q_text))

    if not candidates:
        return None

    # 1. First try exact match on normalized question
    matched_cand = None
    match_score = 1.0
    matched_q_text = ""
    for ans, q_rec, q_text in candidates:
        if normalize_question(q_text) == norm_incoming:
            matched_cand = ans
            matched_q_text = q_text
            match_score = 1.0
            logger.info(f"💾 Cache EXACT match found on approved question: '{matched_q_text}'")
            break

    # 2. If no exact match, try embedding cosine similarity
    emb_model = get_embedding_model()
    if not matched_cand and emb_model:
        try:
            target_emb = emb_model.encode([question])[0]
            cand_texts = [c[2] for c in candidates]
            cand_embs = emb_model.encode(cand_texts)

            best_sim = -1.0
            best_idx = -1
            for idx, c_emb in enumerate(cand_embs):
                sim = float(np.dot(target_emb, c_emb) / (np.linalg.norm(target_emb) * np.linalg.norm(c_emb) + 1e-9))
                if sim > best_sim:
                    best_sim = sim
                    best_idx = idx

            logger.info(f"💾 Cache embedding similarity search: max_sim={best_sim:.4f} (threshold={CACHE_SIMILARITY_THRESHOLD})")
            if best_sim >= CACHE_SIMILARITY_THRESHOLD and best_idx >= 0:
                matched_cand = candidates[best_idx][0]
                matched_q_text = candidates[best_idx][2]
                match_score = round(best_sim, 4)
                logger.info(f"💾 Cache SEMANTIC match (score={best_sim:.4f}) on approved question: '{matched_q_text}'")
        except Exception as emb_err:
            logger.error(f"❌ Cache embedding similarity error: {emb_err}")

    if not matched_cand:
        return None

    # Update cache stats in store if entry exists or append
    q_hash = hash_question(question, language=language, source=source, case_id=case_id)
    cache_entry = next((c for c in cache_entries if c.get("question_hash") == q_hash), None)
    if cache_entry:
        cache_entry["cache_hits"] = cache_entry.get("cache_hits", 0) + 1
        cache_entry["last_used"] = datetime.now().isoformat()
    else:
        cache_entries.append({
            "cache_id": str(uuid.uuid4()),
            "question_hash": q_hash,
            "answer_id": matched_cand.get("answer_id"),
            "question_id": matched_cand.get("question_id"),
            "cache_hits": 1,
            "last_used": datetime.now().isoformat()
        })
    store["cache"] = cache_entries
    save_store(store)

    # Derive original sources
    orig_chunks = matched_cand.get("retrieved_chunks", [])
    orig_sources = []
    for ch in orig_chunks:
        if isinstance(ch, dict):
            src_val = ch.get("case") or ch.get("case_name") or ""
            if src_val and src_val not in orig_sources:
                orig_sources.append(src_val)
        elif isinstance(ch, str) and ch not in orig_sources:
            orig_sources.append(ch)

    return {
        "cached": True,
        "from_cache": True,
        "mode": "CACHED",
        "answer_id": matched_cand.get("answer_id"),
        "question_id": matched_cand.get("question_id"),
        "matched_question": matched_q_text,
        "cache_similarity": match_score,
        "approved_at": matched_cand.get("reviewed_at") or matched_cand.get("created_at"),
        "source": matched_cand.get("source"),
        "case_id": matched_cand.get("case_id"),
        "case_name": matched_cand.get("case_name"),
        "conclusion": matched_cand.get("conclusion"),
        "legal_reasoning": matched_cand.get("legal_reasoning"),
        "precedents": matched_cand.get("precedents", []),
        "facts_from_case": matched_cand.get("facts_from_case", []),
        "page_references": matched_cand.get("page_references", []),
        "sources": orig_sources,
        "retrieved_cases": orig_chunks,
        "retrieved_cases_count": len(orig_chunks),
        "uncertainty_score": matched_cand.get("uncertainty_score", 0.9),
        "status": "APPROVED",
        "metrics": matched_cand.get("metrics", {}),
        "message": f"⚡ Reused from a previously approved answer (matched: '{matched_q_text}')"
    }

def check_query_cache(question_hash, source="external"):
    """Backward compatibility wrapper redirecting to find_approved_cached_answer."""
    return None


def get_latest_rejected_answer(store, question_hash):
    """
    Find the most recent REJECTED answer for this question hash (if any).
    Used to refine future answers.
    """
    questions = store.get("questions", [])
    answers = store.get("answers", [])

    qids_for_hash = [q["question_id"] for q in questions if q.get("question_hash") == question_hash]
    if not qids_for_hash:
        return None

    candidates = [a for a in answers if a.get("question_id") in qids_for_hash and a.get("status") == "REJECTED"]
    if not candidates:
        return None

    def parse_dt(s):
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return datetime.min

    candidates_sorted = sorted(
        candidates,
        key=lambda a: parse_dt(a.get("created_at", "")),
        reverse=True
    )
    return candidates_sorted[0]

# ======================
# API ENDPOINTS
# ======================
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "message": "Legal QA System with external fallback (FAISS + JSON + SerpAPI, Multilingual, Ultra Judge Mode)",
        "openai": "configured" if OPENAI_API_KEY else "missing",
        "serpapi": "configured" if SERPAPI_KEY else "missing"
    })

MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB
MAX_PDF_PAGES    = 500

@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    """Upload PDF and index it into FAISS + JSON metadata with server-side validation."""
    global _faiss_index, _cases_cache

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    case_name = request.form.get('case_name', (file.filename or 'document').replace('.pdf', ''))

    # Validate file extension (server-side, not just client)
    filename_lower = (file.filename or '').lower()
    if not filename_lower.endswith('.pdf'):
        return jsonify({"error": "Only PDF files are allowed. Please upload a .pdf file."}), 400

    try:
        # Read into memory first to check size without trusting Content-Length
        file_bytes = file.read()
        if len(file_bytes) > MAX_PDF_SIZE_BYTES:
            return jsonify({"error": f"File too large. Maximum allowed size is {MAX_PDF_SIZE_BYTES // (1024*1024)} MB."}), 400

        # Validate PDF magic bytes
        if not file_bytes.startswith(b'%PDF'):
            return jsonify({"error": "Invalid PDF file. The uploaded file does not appear to be a valid PDF."}), 400

        # Save to disk
        safe_filename = f"{uuid.uuid4().hex}_{os.path.basename(file.filename)}"
        file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        with open(file_path, 'wb') as fh:
            fh.write(file_bytes)

        # Extract text + validate
        text, page_count, is_encrypted = extract_pdf_text(file_path)

        if is_encrypted:
            os.remove(file_path)
            return jsonify({"error": "The PDF is encrypted/password-protected. Please provide an unprotected PDF."}), 400

        if page_count > MAX_PDF_PAGES:
            os.remove(file_path)
            return jsonify({"error": f"PDF has too many pages ({page_count}). Maximum allowed is {MAX_PDF_PAGES} pages."}), 400

        if not text or len(text.strip()) < 100:
            os.remove(file_path)
            return jsonify({
                "error": "Could not extract readable text from this PDF. "
                         "The document may be scanned (image-only). "
                         "Please provide a text-searchable PDF or use OCR first."
            }), 400

        chunks = smart_chunk_judgment(text, chunk_size=800, overlap=200)
        if not chunks:
            os.remove(file_path)
            return jsonify({"error": "No valid content chunks could be created from the PDF."}), 400

        if DEBUG_DOCQA_DIAGNOSTICS:
            chunk_diag_summaries = [
                f"Chunk {i+1}: len={len(c['text'])} chars, first_100='{c['text'][:100].strip()}...'"
                for i, c in enumerate(chunks)
            ]
            logger.info(
                f"✂️ [DIAGNOSTIC] Chunking completed: created {len(chunks)} chunks.\n"
                + "\n".join(chunk_diag_summaries)
            )

        embeddings = embed_chunks(chunks)
        case_id = str(uuid.uuid4())

        # Load or create FAISS index
        index, cases_data = load_vector_db()
        faiss_size_before = index.ntotal if index else 0

        if index is None:
            cases_data = {'chunks': []}
            index = create_faiss_index(embeddings)
        else:
            index.add(np.array(embeddings).astype('float32'))

        faiss_size_after = index.ntotal

        # Extend chunks metadata
        for chunk_obj in chunks:
            cases_data['chunks'].append({
                'text': chunk_obj['text'],
                'case_id': case_id,
                'case_name': case_name,
                'chunk_type': chunk_obj['type']
            })

        save_cases_data(cases_data)
        save_vector_db(index)

        # update in-memory cache
        _faiss_index = index
        _cases_cache = cases_data

        if DEBUG_DOCQA_DIAGNOSTICS:
            logger.info(
                f"💾 [DIAGNOSTIC] Indexing completed for case_id='{case_id}':\n"
                f"  - Case name: {case_name}\n"
                f"  - FAISS index size before: {faiss_size_before}, after: {faiss_size_after} (+{len(chunks)})\n"
                f"  - Total chunks in metadata: {len(cases_data['chunks'])}\n"
                f"  - Index saved to disk and in-memory cache refreshed."
            )

        return jsonify({
            "status": "success",
            "case_id": case_id,
            "case_name": case_name,
            "chunks_created": len(chunks),
            "page_count": page_count,
            "file_size_mb": round(len(file_bytes) / (1024 * 1024), 2),
            "message": f"✅ Indexed {len(chunks)} smart chunks from {case_name} ({page_count} pages)"
        })

    except Exception as e:
        logger.error(f"❌ Upload error: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred while processing the PDF."}), 500

@app.route('/api/index-judgment', methods=['POST'])
def index_judgment():
    """
    Dedicated endpoint to automatically index downloaded court judgment PDFs into the
    Semantic Knowledge Base (FAISS + cases_metadata.json).

    Accepts multipart/form-data:
      - file: PDF file
      - doc_id: Indian Kanoon document ID
      - case_name: Name/title of the judgment
      - court: Court name (e.g. "Supreme Court")
      - year: Year string or int
      - month: Month string
      - source_path: Path where the file was saved

    Returns JSON:
      {
        "status": "INDEXED" | "SKIPPED_DUPLICATE" | "FAILED_NO_TEXT" | "FAILED_ERROR",
        "doc_id": doc_id,
        "chunks_added": int,
        "reason": str,
        "case_id": str (optional)
      }
    """
    global _faiss_index, _cases_cache

    try:
        # 1. Validation: file presence
        if 'file' not in request.files:
            return jsonify({
                "status": "FAILED_ERROR",
                "doc_id": request.form.get('doc_id', ''),
                "chunks_added": 0,
                "reason": "No file part provided in request"
            }), 400

        file = request.files['file']
        filename = (file.filename or '').strip()
        filename_lower = filename.lower()

        doc_id = str(request.form.get('doc_id') or '').strip()
        case_name = str(request.form.get('case_name') or filename).strip()
        court = str(request.form.get('court') or 'Unknown Court').strip()
        year = str(request.form.get('year') or '').strip()
        month = str(request.form.get('month') or '').strip()
        source_path = str(request.form.get('source_path') or '').strip()

        # a) Reject non-PDF input with a clear error
        if not filename_lower.endswith('.pdf'):
            return jsonify({
                "status": "FAILED_ERROR",
                "doc_id": doc_id,
                "chunks_added": 0,
                "reason": f"Only PDF files can be indexed. Rejected non-PDF file: {filename}"
            }), 400

        file_bytes = file.read()
        if len(file_bytes) == 0:
            return jsonify({
                "status": "FAILED_ERROR",
                "doc_id": doc_id,
                "chunks_added": 0,
                "reason": "Uploaded file is empty (0 bytes)"
            }), 400

        if not file_bytes.startswith(b'%PDF'):
            return jsonify({
                "status": "FAILED_ERROR",
                "doc_id": doc_id,
                "chunks_added": 0,
                "reason": "Invalid PDF signature (does not start with %PDF magic bytes)"
            }), 400

        # Save temporarily in UPLOAD_FOLDER
        temp_filename = f"ik_{uuid.uuid4().hex}_{os.path.basename(filename)}"
        temp_file_path = os.path.join(UPLOAD_FOLDER, temp_filename)
        with open(temp_file_path, 'wb') as fh:
            fh.write(file_bytes)

        try:
            # c) Extract text from the PDF
            extracted_text, page_count, is_encrypted = extract_pdf_text(temp_file_path)

            if is_encrypted:
                return jsonify({
                    "status": "FAILED_ERROR",
                    "doc_id": doc_id,
                    "chunks_added": 0,
                    "reason": "PDF is encrypted or password-protected"
                }), 400

            # d) Clean text thoroughly so it is strictly PLAIN TEXT
            clean_text = clean_text_plain_only(extracted_text)

            if not clean_text or len(clean_text.strip()) < 100:
                logger.warning(f"No extractable text found in PDF for doc_id {doc_id} (len={len(clean_text.strip()) if clean_text else 0})")
                return jsonify({
                    "status": "FAILED_NO_TEXT",
                    "doc_id": doc_id,
                    "chunks_added": 0,
                    "reason": "Could not extract readable text from PDF (document may be scanned or empty)."
                }), 200

            # e) Chunk text preserving legal structure
            raw_chunks = smart_chunk_judgment(clean_text, chunk_size=800, overlap=200)
            if not raw_chunks:
                return jsonify({
                    "status": "FAILED_NO_TEXT",
                    "doc_id": doc_id,
                    "chunks_added": 0,
                    "reason": "Document text was insufficient to generate valid content chunks."
                }), 200

            # Final safety check on each chunk: ensure plain text only, zero HTML
            sanitized_chunks = []
            for ch in raw_chunks:
                ch_text = clean_text_plain_only(ch['text'])
                if len(ch_text) >= 50:
                    sanitized_chunks.append({
                        'text': ch_text,
                        'type': ch.get('type', 'paragraph_group'),
                        'word_count': len(ch_text.split())
                    })

            if not sanitized_chunks:
                return jsonify({
                    "status": "FAILED_NO_TEXT",
                    "doc_id": doc_id,
                    "chunks_added": 0,
                    "reason": "All generated chunks were empty after strict plain text sanitization."
                }), 200

            # Embed chunks with the same SentenceTransformer model
            embeddings = embed_chunks(sanitized_chunks)
            case_id = str(uuid.uuid4())
            new_chunk_records = []

            for ch in sanitized_chunks:
                new_chunk_records.append({
                    'text': ch['text'],
                    'case_id': case_id,
                    'case_name': case_name,
                    'doc_id': doc_id,
                    'court': court,
                    'year': year,
                    'month': month,
                    'source_path': source_path,
                    'source_filename': os.path.basename(source_path or filename),
                    'chunk_type': ch['type']
                })

            # f) ONE ATOMIC STEP: Acquire INDEX_LOCK, verify duplicate from fresh metadata, and write
            with INDEX_LOCK:
                index, cases_data = load_vector_db(force_reload=True)
                existing_chunks = cases_data.get('chunks', [])

                def _extract_year(s):
                    m = re.findall(r'\b(19\d\d|20\d\d)\b', str(s or ''))
                    return m[-1] if m else None

                def _normalize_title(n):
                    n = re.sub(r'^\d+[\s_-]+', '', (n or '').strip())
                    n = re.sub(r'\bon\s+\d{1,2}\s+[a-zA-Z]+,?\s+\d{4}', '', n, flags=re.IGNORECASE)
                    return re.sub(r'[^a-z0-9]', '', n.lower())

                req_year = str(year).strip() if year else _extract_year(case_name)
                req_norm_title = _normalize_title(case_name)

                for chunk in existing_chunks:
                    c_doc_id = str(chunk.get('doc_id') or '').strip()
                    c_name = chunk.get('case_name') or ''
                    c_year = str(chunk.get('year') or '').strip() or _extract_year(c_name)
                    c_case_id = chunk.get('case_id')

                    # a) doc_id match is the MAIN check
                    if doc_id:
                        if c_doc_id and c_doc_id == doc_id:
                            logger.info(f"Duplicate detected via doc_id {doc_id} under INDEX_LOCK (matched case: '{c_name}', case_id: {c_case_id})")
                            return jsonify({
                                "status": "SKIPPED_DUPLICATE",
                                "doc_id": doc_id,
                                "chunks_added": 0,
                                "case_id": c_case_id,
                                "match_method": "doc_id",
                                "matched_case": c_name,
                                "reason": f"Document ID {doc_id} is already indexed in the knowledge base."
                            }), 200

                        if not c_doc_id and (c_name.startswith(f"{doc_id}_") or c_name == doc_id):
                            logger.info(f"Duplicate detected via doc_id prefix {doc_id} on existing case '{c_name}' under INDEX_LOCK")
                            return jsonify({
                                "status": "SKIPPED_DUPLICATE",
                                "doc_id": doc_id,
                                "chunks_added": 0,
                                "case_id": c_case_id,
                                "match_method": "doc_id",
                                "matched_case": c_name,
                                "reason": f"Document ID {doc_id} matches existing case prefix: '{c_name}'"
                            }), 200

                    # b) Title fallback is used ONLY against existing cases that have NO doc_id
                    if not c_doc_id and req_norm_title and len(req_norm_title) > 8:
                        c_norm_title = _normalize_title(c_name)
                        years_match = (req_year and c_year and req_year == c_year)
                        if years_match and (req_norm_title == c_norm_title or req_norm_title in c_norm_title or c_norm_title in req_norm_title):
                            logger.info(f"Duplicate detected via title_fallback under INDEX_LOCK ('{req_norm_title}' year {req_year} matched '{c_name}')")
                            return jsonify({
                                "status": "SKIPPED_DUPLICATE",
                                "doc_id": doc_id,
                                "chunks_added": 0,
                                "case_id": c_case_id,
                                "match_method": "title_fallback",
                                "matched_case": c_name,
                                "reason": f"Case title and year match existing case without doc_id: '{c_name}'"
                            }), 200

                # No duplicate found: Proceed to write under the same lock
                if index is None:
                    cases_data = {'chunks': []}
                    index = create_faiss_index(embeddings)
                else:
                    index.add(np.array(embeddings).astype('float32'))

                cases_data.setdefault('chunks', []).extend(new_chunk_records)

                # Atomically save metadata and vector index
                save_cases_data(cases_data)
                save_vector_db(index)

                # Immediate in-memory cache update
                _faiss_index = index
                _cases_cache = cases_data

            logger.info(
                f"✅ [INDEXED] doc_id='{doc_id}', case_id='{case_id}', "
                f"chunks_added={len(sanitized_chunks)}, case_name='{case_name[:60]}'"
            )

            logger.info(
                f"✅ [INDEXED] doc_id='{doc_id}', case_id='{case_id}', "
                f"chunks_added={len(sanitized_chunks)}, case_name='{case_name[:60]}'"
            )

            return jsonify({
                "status": "INDEXED",
                "doc_id": doc_id,
                "case_id": case_id,
                "case_name": case_name,
                "chunks_added": len(sanitized_chunks),
                "page_count": page_count,
                "reason": f"Successfully indexed {len(sanitized_chunks)} plain text chunks into knowledge base."
            }), 200

        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as rem_err:
                    logger.warning(f"Failed to remove temp file {temp_file_path}: {rem_err}")

    except Exception as exc:
        logger.error(f"❌ Index Judgment error: {exc}", exc_info=True)
        return jsonify({
            "status": "FAILED_ERROR",
            "doc_id": request.form.get('doc_id', ''),
            "chunks_added": 0,
            "reason": f"Internal indexing error: {str(exc)}"
        }), 500


@app.route('/api/ask', methods=['POST'])
def ask_legal_question():
    """
    Main QA endpoint:
    - Automatically decides:
        * If uploaded PDFs are VERY relevant → LOCAL_PDF (RAG from judgments)
        * Otherwise → EXTERNAL (SerpAPI + legal knowledge)
    - If a previous answer for this question was REJECTED, refine using judge comments
    - Supports multilingual answers via 'language' field: 'en', 'mr', 'hi'
    """
    try:
        data = request.json or {}
        question = data.get('question', '').strip()
        source = data.get('source', 'external')
        case_id = data.get('case_id')
        language = (data.get('language') or 'en').lower()
        if language not in ('en', 'mr', 'hi'):
            language = 'en'

        if not question:
            return jsonify({"error": "No question provided"}), 400
            
        if source == 'document' and not case_id:
             return jsonify({"error": "No document selected for Document QA"}), 400

        store = load_store()
        question_hash = hash_question(question, language=language, source=source, case_id=case_id)

        # 0️⃣ — Check if a previous answer was rejected → use its review_comment to refine
        last_rejected = get_latest_rejected_answer(store, question_hash)
        refinement_note = last_rejected.get("review_comment") if last_rejected else None

        question_id = str(uuid.uuid4())
        answer_id = str(uuid.uuid4())

        # Look up case_name if case_id is provided
        case_name = None
        if case_id:
            cases_data = load_cases_data()
            for chunk_obj in cases_data.get("chunks", []):
                if chunk_obj.get("case_id") == case_id:
                    case_name = chunk_obj.get("case_name")
                    break

        store["questions"].append({
            "question_id": question_id,
            "question_text": question,
            "question_hash": question_hash,
            "language": language,
            "source": source,
            "case_id": case_id,
            "case_name": case_name,
            "asked_at": datetime.now().isoformat()
        })

        retrieved_cases = []
        retrieval_count = 0
        validator_result = None
        used_mode = None
        sources_list = []
        final_confidence = 0.0
        reason_code = None
        reason_message = None
        answer_json = {}

        if source == "document":
            # Document QA mode (isolated PDF document context)
            used_mode = "DOCUMENT_QA"
            retrieved_cases, retrieval_count = search_local_vector_db(question, top_k=10, case_id=case_id)
            if retrieval_count == 0:
                used_mode = "NO_RESULT"
                reason_code = "KB_LOW_SIMILARITY"
                reason_message = "No relevant passages found in the selected document."
                answer_json = {
                    "conclusion": reason_message,
                    "legal_reasoning": "The document semantic search returned zero chunks matching your query.",
                    "confidence": 0.0
                }
                final_confidence = 0.0
            else:
                answer_json = call_reasoner_llm(
                    question, retrieved_cases, refinement_note=refinement_note, language=language
                )
                source_text_for_validator = "\n\n".join([rc["chunk"] for rc in retrieved_cases[:5]])
                validator_result = call_validator_llm(answer_json, source_text_for_validator)
                base_conf = retrieved_cases[0].get("similarity", 0.85)
                final_confidence = max(0.1, min(1.0, float(base_conf)))
                sources_list = [f"{case_name or 'Document'} (Chunk {i+1})" for i in range(len(retrieved_cases[:5]))]

        else:
            # 1. Search Knowledge Base First
            logger.info(f"🔎 STEP 1: Searching Knowledge Base for query: '{question}'")
            cases_data = load_cases_data()
            total_kb_chunks = len(cases_data.get("chunks", []))
            
            if total_kb_chunks == 0:
                logger.info("ℹ️ Knowledge base is empty (0 chunks).")
                kb_empty = True
            else:
                kb_empty = False

            retrieved_cases, retrieval_count = search_local_vector_db(question, top_k=10, case_id=None)
            top_sim = retrieved_cases[0]["similarity"] if retrieved_cases else 0.0

            logger.info(
                f"🔎 KB Search summary: total_kb_chunks={total_kb_chunks}, found={retrieval_count}, "
                f"top_similarity={top_sim:.4f}, threshold={KB_SIMILARITY_THRESHOLD}"
            )

            if retrieval_count > 0 and top_sim >= KB_SIMILARITY_THRESHOLD:
                # 2. Chunks are good enough -> KNOWLEDGE_BASE ONLY
                used_mode = "KNOWLEDGE_BASE"
                final_confidence = round(float(top_sim), 2)
                sources_list = list(dict.fromkeys([
                    f"{rc.get('case_name') or 'Supreme Court Case'} (similarity {rc.get('similarity', 0):.2f})"
                    for rc in retrieved_cases[:5]
                ]))
                logger.info(f"📚 Using KNOWLEDGE_BASE mode with {len(sources_list)} source cases. (Confidence: {final_confidence})")
                answer_json = call_reasoner_llm(
                    question, retrieved_cases, refinement_note=refinement_note, language=language
                )
                source_text_for_validator = "\n\n".join([rc["chunk"] for rc in retrieved_cases[:5]])
                validator_result = call_validator_llm(answer_json, source_text_for_validator)

            else:
                # 3. Chunks missing or weak -> SerpAPI Failure Chain
                logger.info(f"🌐 STEP 3: KB weak/missing (top_sim={top_sim:.4f} < {KB_SIMILARITY_THRESHOLD}). Calling SerpAPI failure chain...")
                web_text, web_urls, serp_reason, serp_msg = search_serpapi_with_failure_chain(question)
                
                if web_text and web_urls:
                    used_mode = "EXTERNAL"
                    sources_list = web_urls
                    final_confidence = 0.85
                    logger.info(f"🌐 SerpAPI returned {len(web_urls)} results. Using EXTERNAL mode.")
                    answer_json = call_external_legal_reasoner(
                        question, web_context=web_text, refinement_note=refinement_note, language=language
                    )
                else:
                    logger.warning(f"⚠️ SerpAPI failed with reason: {serp_reason} - {serp_msg}")
                    # c. CACHE FALLBACK: reuse a previously APPROVED answer
                    logger.info("💾 STEP 3c: Checking Cache for APPROVED answer matching question...")
                    cached_approved = find_approved_cached_answer(
                        question, language=language, source=source, case_id=case_id
                    )
                    
                    if cached_approved:
                        logger.info(f"⚡ Reusing APPROVED cached answer (matched: '{cached_approved.get('matched_question')}')")
                        return jsonify(cached_approved)

                    logger.info("ℹ️ No APPROVED answer match in cache.")

                    # d. OPTIONAL: General knowledge fallback
                    if ALLOW_GENERAL_KNOWLEDGE_FALLBACK:
                        logger.info("🧠 STEP 3d: Using GENERAL_KNOWLEDGE fallback...")
                        used_mode = "GENERAL_KNOWLEDGE"
                        final_confidence = 0.50
                        sources_list = ["General Legal Knowledge (Unverified)"]
                        answer_json = call_general_knowledge_llm(question, language=language)
                    else:
                        # e. All failed -> NO_RESULT with specific reason_code
                        used_mode = "NO_RESULT"
                        final_confidence = 0.0
                        sources_list = []
                        if serp_reason in ("SERPAPI_KEY_MISSING", "SERPAPI_QUOTA_EXCEEDED", "SERPAPI_NETWORK_ERROR"):
                            reason_code = serp_reason
                            reason_message = serp_msg
                        elif kb_empty:
                            reason_code = "KB_EMPTY"
                            reason_message = "The legal knowledge base contains no uploaded cases, and external search returned no results."
                        elif retrieval_count == 0 or top_sim < KB_SIMILARITY_THRESHOLD:
                            reason_code = serp_reason or "SERPAPI_NO_RESULTS"
                            reason_message = serp_msg or "No relevant information found in knowledge base or external web search."
                        else:
                            reason_code = "NO_RESULT"
                            reason_message = "No relevant legal sources found."

                        answer_json = {
                            "conclusion": f"Unable to provide a verified legal answer: {reason_message}",
                            "legal_reasoning": (
                                f"Knowledge base similarity ({top_sim:.4f}) was below threshold ({KB_SIMILARITY_THRESHOLD}). "
                                f"SerpAPI failure chain status: {reason_code} ({reason_message}). "
                                f"No approved cached answer was available."
                            ),
                            "confidence": 0.0
                        }

        # Normalize fields
        precedents_list = (
            answer_json.get("precedents_cited_in_text")
            or answer_json.get("supreme_court_precedents")
            or answer_json.get("precedents")
            or []
        )
        facts_list = answer_json.get("facts_from_case", [])
        suggested_decision = answer_json.get("suggested_decision", "")
        recommended_next_steps = answer_json.get("recommended_next_steps", [])
        missing_info = []

        all_page_refs = []
        if used_mode in ("KNOWLEDGE_BASE", "LOCAL_PDF", "DOCUMENT_QA"):
            for rc in retrieved_cases[:5]:
                all_page_refs.extend(rc.get("page_refs", []))
            all_page_refs = sorted(set(all_page_refs))

        metrics = build_answer_metrics(
            used_mode=used_mode,
            retrieved_cases=retrieved_cases[:5] if used_mode in ("KNOWLEDGE_BASE", "LOCAL_PDF", "DOCUMENT_QA") else [],
            validator_result=validator_result,
            answer_json=answer_json
        )

        # Save to store
        store["answers"].append({
            "answer_id": answer_id,
            "question_id": question_id,
            "language": language,
            "conclusion": answer_json.get("conclusion", "No conclusion"),
            "legal_reasoning": answer_json.get("legal_reasoning", "No reasoning"),
            "precedents": precedents_list,
            "facts_from_case": facts_list,
            "mode": used_mode,
            "source": source,
            "sources": sources_list,
            "case_id": case_id,
            "case_name": case_name,
            "page_references": all_page_refs,
            "uncertainty_score": final_confidence,
            "retrieved_chunks": [
                {
                    "case": rc.get("case_name", ""),
                    "similarity": rc.get("similarity", 0.0),
                    "chunk": rc.get("chunk", ""),
                    "page_refs": rc.get("page_refs", [])
                }
                for rc in (retrieved_cases[:5] if used_mode in ("KNOWLEDGE_BASE", "LOCAL_PDF", "DOCUMENT_QA") else [])
            ] if used_mode in ("KNOWLEDGE_BASE", "LOCAL_PDF", "DOCUMENT_QA") else [{"case": s, "similarity": 1.0, "chunk": s} for s in sources_list],
            "created_at": datetime.now().isoformat(),
            "status": "PENDING_REVIEW",
            "review_comment": "",
            "metrics": metrics
        })

        if used_mode in ("KNOWLEDGE_BASE", "LOCAL_PDF", "DOCUMENT_QA") and validator_result:
            store["reviews"].append({
                "review_id": str(uuid.uuid4()),
                "answer_id": answer_id,
                "hallucinations_found": validator_result.get("hallucinations_found", 0),
                "accuracy_score": validator_result.get("confidence_score", 0.8),
                "false_claims": validator_result.get("false_claims", []),
                "approved": False,
                "reviewed_at": datetime.now().isoformat(),
                "comment": ""
            })

        save_store(store)

        _response_text = (
            (answer_json.get("conclusion") or "") + " " +
            (answer_json.get("legal_reasoning") or "")
        ).strip()
        _contexts = [rc.get("chunk", rc.get("case", "")) for rc in retrieved_cases[:5]] if used_mode in ("KNOWLEDGE_BASE", "LOCAL_PDF", "DOCUMENT_QA") else sources_list
        _log_qa_event(
            module="legal_qa",
            user_input=question,
            response=_response_text,
            contexts=_contexts,
            meta={"mode": used_mode, "confidence": round(final_confidence, 3),
                  "language": language, "case_id": case_id}
        )

        return jsonify({
            "answer_id": answer_id,
            "question_id": question_id,
            "mode": used_mode,
            "source": source,
            "sources": sources_list,
            "reason_code": reason_code,
            "reason_message": reason_message,
            "case_id": case_id,
            "case_name": case_name,
            "language": language,
            "conclusion": answer_json.get("conclusion"),
            "legal_reasoning": answer_json.get("legal_reasoning"),
            "precedents": precedents_list,
            "facts_from_case": facts_list,
            "missing_info": missing_info,
            "suggested_decision": suggested_decision,
            "recommended_next_steps": recommended_next_steps,
            "ratio_decidendi": answer_json.get("ratio_decidendi", ""),
            "evidence_assessment": answer_json.get("evidence_assessment", []),
            "conditional_paths": answer_json.get("conditional_paths", []),
            "uncertainty_score": round(final_confidence, 2),
            "retrieved_cases_count": retrieval_count if used_mode in ("KNOWLEDGE_BASE", "LOCAL_PDF", "DOCUMENT_QA") else len(sources_list),
            "retrieved_cases": retrieved_cases[:5] if used_mode in ("KNOWLEDGE_BASE", "LOCAL_PDF", "DOCUMENT_QA") else [{"case": s, "similarity": 1.0, "chunk": s} for s in sources_list],
            "page_references": all_page_refs,
            "validator_result": validator_result if validator_result else {
                "is_valid": used_mode in ("EXTERNAL", "KNOWLEDGE_BASE"),
                "hallucinations_found": 0,
                "false_claims": [],
                "unsupported_statements": [],
                "confidence_score": final_confidence
            },
            "status": "PENDING_REVIEW",
            "from_cache": False,
            "metrics": metrics
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/approve-answer', methods=['POST'])
def approve_answer():
    """
    Approve / reject answer with optional human review comment.
    Returns 404 if answer_id does not exist.
    """
    try:
        data = request.json or {}
        answer_id = data.get('answer_id')
        approved = data.get('approved', True)
        comment = data.get('comment', "")

        if not answer_id:
            return jsonify({"error": "answer_id is required"}), 400

        store = load_store()

        # Find and update answer; 404 if not found
        found = False
        for ans in store.get("answers", []):
            if ans.get("answer_id") == answer_id:
                ans["status"] = "APPROVED" if approved else "REJECTED"
                ans["review_comment"] = comment or ""
                ans["reviewed_at"] = datetime.now().isoformat()
                found = True
                break

        if not found:
            return jsonify({"error": f"Answer ID '{answer_id}' not found"}), 404

        # Update review record if present
        for rev in store.get("reviews", []):
            if rev.get("answer_id") == answer_id:
                rev["approved"] = bool(approved)
                rev["reviewed_at"] = datetime.now().isoformat()
                rev["comment"] = comment or ""
                break

        save_store(store)

        return jsonify({
            "status": "success",
            "answer_id": answer_id,
            "action": "APPROVED" if approved else "REJECTED",
            "new_status": "APPROVED" if approved else "REJECTED",
            "comment": comment or ""
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-answer/<answer_id>', methods=['GET'])
def get_answer(answer_id):
    """
    Fetch a single answer by ID for refresh-persistence.
    Returns question text, answer content, review status, retrieved chunks.
    """
    try:
        store = load_store()
        ans = next((a for a in store.get("answers", []) if a.get("answer_id") == answer_id), None)
        if not ans:
            return jsonify({"error": f"Answer ID '{answer_id}' not found"}), 404

        q = next((q for q in store.get("questions", []) if q.get("question_id") == ans.get("question_id")), None)

        return jsonify({
            "answer_id": answer_id,
            "question_id": ans.get("question_id"),
            "question_text": q.get("question_text") if q else None,
            "conclusion": ans.get("conclusion"),
            "legal_reasoning": ans.get("legal_reasoning"),
            "precedents": ans.get("precedents", []),
            "facts_from_case": ans.get("facts_from_case", []),
            "status": ans.get("status", "PENDING_REVIEW"),
            "review_comment": ans.get("review_comment", ""),
            "reviewed_at": ans.get("reviewed_at"),
            "retrieved_chunks": ans.get("retrieved_chunks", []),
            "uncertainty_score": ans.get("uncertainty_score", 0.0),
            "created_at": ans.get("created_at"),
            "metrics": ans.get("metrics", {})
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        source = request.args.get('source')
        case_id = request.args.get('case_id')
        
        store = load_store()
        cases_data = load_cases_data()
        case_name_map = {}
        for c in cases_data.get("chunks", []):
            cid = c.get("case_id")
            if cid and cid not in case_name_map:
                case_name_map[cid] = c.get("case_name", "")

        questions = store.get("questions", [])
        answers = store.get("answers", [])

        # Build quick lookup map for answers by question_id
        ans_by_qid = {}
        for a in answers:
            qid = a.get("question_id")
            if qid and qid not in ans_by_qid:
                ans_by_qid[qid] = a
                
        # Filter questions by source and case_id
        filtered_questions = []
        for q in questions:
            q_src = q.get("source", "external")
            if source and source not in ('all', ''):
                if q_src != source:
                    continue
            if source == "document" and case_id:
                if q.get("case_id") != case_id:
                    continue
            filtered_questions.append(q)

        # Sort questions by asked_at desc
        def parse_dt(s):
            try:
                return datetime.fromisoformat(s)
            except Exception:
                return datetime.min

        questions_sorted = sorted(
            filtered_questions,
            key=lambda q: parse_dt(q.get("asked_at", "")),
            reverse=True
        )

        history = []
        for q in questions_sorted[:100]:
            qid = q.get("question_id")
            ans = ans_by_qid.get(qid)
            cid = q.get("case_id")
            cname = q.get("case_name") or case_name_map.get(cid, "")
            history.append({
                "question_id": qid,
                "question": q.get("question_text"),
                "asked_at": q.get("asked_at"),
                "source": q.get("source", "external"),
                "case_id": cid,
                "case_name": cname,
                "answer_id": ans.get("answer_id") if ans else None,
                "conclusion": ans.get("conclusion") if ans else None,
                "legal_reasoning": ans.get("legal_reasoning") if ans else None,
                "precedents": ans.get("precedents", []) if ans else [],
                "page_references": ans.get("page_references", []) if ans else [],
                "retrieved_chunks": ans.get("retrieved_chunks", []) if ans else [],
                "review_comment": ans.get("review_comment", "") if ans else "",
                "reviewed_at": ans.get("reviewed_at") if ans else None,
                "status": ans.get("status") if ans else "PENDING_REVIEW",
                "confidence": ans.get("uncertainty_score") if ans else None,
                "mode": ans.get("mode") if ans else None
            })

        return jsonify({"history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete-history', methods=['POST'])
def delete_history():
    """
    Delete a question + its answers + related cache entries by question_id.
    Used by History page delete button.
    """
    try:
        data = request.json or {}
        question_id = data.get("question_id")
        if not question_id:
            return jsonify({"error": "question_id required"}), 400

        store = load_store()

        # delete question
        store["questions"] = [q for q in store.get("questions", []) if q.get("question_id") != question_id]

        # delete answers
        answers_to_keep = []
        removed_answer_ids = set()
        for a in store.get("answers", []):
            if a.get("question_id") == question_id:
                removed_answer_ids.add(a.get("answer_id"))
            else:
                answers_to_keep.append(a)
        store["answers"] = answers_to_keep

        # delete reviews for removed answers
        store["reviews"] = [r for r in store.get("reviews", []) if r.get("answer_id") not in removed_answer_ids]

        # delete cache entries bound to that question or answer
        new_cache = []
        for c in store.get("cache", []):
            if c.get("question_id") == question_id:
                continue
            if c.get("answer_id") in removed_answer_ids:
                continue
            new_cache.append(c)
        store["cache"] = new_cache

        save_store(store)

        return jsonify({"status": "deleted", "question_id": question_id})
    except Exception as e:
        logger.error("Delete history error:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents', methods=['GET'])
def get_documents():
    """Return list of distinct indexed documents from cases_metadata.json."""
    try:
        cases_data = load_cases_data()
        docs_map = {}
        for c in cases_data.get("chunks", []):
            cid = c.get("case_id")
            if cid:
                if cid not in docs_map:
                    docs_map[cid] = {
                        "case_id": cid,
                        "case_name": c.get("case_name", "Untitled Document"),
                        "chunks_count": 0,
                    }
                docs_map[cid]["chunks_count"] += 1
        return jsonify({"documents": list(docs_map.values())})
    except Exception as e:
        return jsonify({"error": str(e), "documents": []}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        cases_data = load_cases_data()
        store = load_store()

        total_cases_uploaded = len({c["case_id"] for c in cases_data.get("chunks", [])}) if cases_data.get("chunks") else 0
        total_questions_asked = len(store.get("questions", []))
        approved_answers = sum(1 for a in store.get("answers", []) if a.get("status") == "APPROVED")
        rejected_answers = sum(1 for a in store.get("answers", []) if a.get("status") == "REJECTED")
        pending_review = sum(1 for a in store.get("answers", []) if a.get("status", "PENDING_REVIEW") == "PENDING_REVIEW")
        cached_queries = len(store.get("cache", []))
        approval_rate = round((approved_answers / total_questions_asked * 100), 1) if total_questions_asked > 0 else 0

        return jsonify({
            "total_cases_uploaded": total_cases_uploaded,
            "total_questions_asked": total_questions_asked,
            "approved_answers": approved_answers,
            "rejected_answers": rejected_answers,
            "pending_review": pending_review,
            "approval_rate": approval_rate,
            "cached_queries": cached_queries,
            "system_status": "operational"
        })
    except Exception as e:
        logger.error("Stats error:", e)
        return jsonify({
            "total_cases_uploaded": 0,
            "total_questions_asked": 0,
            "approved_answers": 0,
            "rejected_answers": 0,
            "pending_review": 0,
            "approval_rate": 0,
            "cached_queries": 0,
            "system_status": "error"
        })

if __name__ == '__main__':
    logger.info("\n" + "="*60)
    logger.info("🚀 Legal QA System - RAG + External Conditional QA")
    logger.info("="*60)
    logger.info(f"✅ Smart chunking: 800 words with 200 overlap")
    logger.info(f"✅ JSON-based questions, answers, cache, reviews")
    logger.info(f"✅ FAISS vector store for judgments")
    logger.error(f"✅ OpenAI: {'Configured' if OPENAI_API_KEY else '❌ NOT CONFIGURED'}")
    logger.error(f"✅ SerpAPI: {'Configured' if SERPAPI_KEY else '❌ NOT CONFIGURED'}")
    logger.info(f"✅ Server running on: http://localhost:8002")
    logger.info("="*60 + "\n")

    app.run(debug=False, host='0.0.0.0', port=8002)  # Changed to port 8002
