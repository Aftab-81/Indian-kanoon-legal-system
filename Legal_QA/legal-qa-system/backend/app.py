#!/usr/bin/env python3

import os
import json
from logger_setup import get_logger
import uuid
import hashlib
import PyPDF2
import numpy as np
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

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

# Load SerpAPI Key with fallback
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

if not SERPAPI_KEY:
    # ⚠️ HARDCODED API KEY - REPLACE WITH YOUR ACTUAL KEY OR USE .env
    SERPAPI_KEY = "9653fcf7650ed7562ceae3b9f149656731bc934a9940c740395c8751f7611e30"
    logger.info("🔑 Using hardcoded SERPAPI_KEY fallback (update this in app.py or .env)")

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

VECTOR_DB_FILE = "legal_vectors.faiss"
CASES_FILE = "cases_metadata.json"   # stores chunks + case metadata
STORE_FILE = "qa_store.json"         # stores questions, answers, reviews, cache
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

def save_cases_data(cases_data):
    with open(CASES_FILE, "w", encoding="utf-8") as f:
        json.dump(cases_data, f, indent=2, ensure_ascii=False)

# ======================
# PDF PARSER
# ======================
def extract_pdf_text(file_path):
    """Extract text with page markers."""
    text = ""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n[PAGE {page_num}]\n{page_text}\n"
    except Exception as e:
        logger.error(f"PDF Error: {e}", exc_info=True)
    return text

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
        faiss.write_index(index, VECTOR_DB_FILE)
        logger.info(f"✅ Saved {index.ntotal} vectors")
    except Exception as e:
        logger.error(f"❌ Save FAISS error: {e}", exc_info=True)

def load_vector_db():
    """
    Cached FAISS index + cases to avoid repeated disk load.
    Checks for sync between vectors and metadata.
    """
    global _faiss_index, _cases_cache
    try:
        # Check memory sync before returning memory cache
        if _faiss_index is not None and _cases_cache is not None:
            if _faiss_index.ntotal == len(_cases_cache.get("chunks", [])):
                return _faiss_index, _cases_cache
            else:
                logger.warning(f"⚠️ FAISS memory desync detected! Resetting memory and disk DB...")
                _faiss_index = None
                _cases_cache = None
                if os.path.exists(VECTOR_DB_FILE): os.remove(VECTOR_DB_FILE)
                if os.path.exists(CASES_FILE): os.remove(CASES_FILE)
                return None, {"chunks": []}

        if os.path.exists(VECTOR_DB_FILE):
            index = faiss.read_index(VECTOR_DB_FILE)
            cases_data = load_cases_data()
            
            # Check for desync between FAISS and metadata
            if index.ntotal != len(cases_data.get("chunks", [])):
                logger.warning(f"⚠️ FAISS disk desync detected! Vectors: {index.ntotal}, Metadata: {len(cases_data.get('chunks', []))}. Resetting DB...")
                if os.path.exists(VECTOR_DB_FILE): os.remove(VECTOR_DB_FILE)
                if os.path.exists(CASES_FILE): os.remove(CASES_FILE)
                return None, {"chunks": []}

            _faiss_index = index
            _cases_cache = cases_data
            logger.info(f"✅ Loaded {index.ntotal} vectors")
            return index, cases_data
    except Exception as e:
        logger.error(f"❌ Load FAISS error: {e}", exc_info=True)
    return None, {"chunks": []}

# ======================
# ENHANCED RETRIEVAL
# ======================
def search_local_vector_db(query, top_k=10, case_id=None):
    """
    Semantic search over uploaded judgments using FAISS + cases_metadata.json
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

        retrieved = []

        for idx, distance in zip(indices[0], distances[0]):
            if 0 <= idx < len(chunks_list):
                chunk_info = chunks_list[idx]
                
                # Filter by case_id if provided
                if case_id and chunk_info.get('case_id') != case_id:
                    continue

                similarity = 1 / (1 + float(distance))

                # loose filter here, strict threshold later (unless case_id provided)
                if similarity > 0.35 or case_id:
                    retrieved.append({
                        'chunk': chunk_info['text'],
                        'case_id': chunk_info['case_id'],
                        'case_name': chunk_info['case_name'],
                        'similarity': float(similarity),
                        'chunk_type': chunk_info.get('chunk_type', 'paragraph_group')
                    })
                    
                    if len(retrieved) >= top_k:
                        break

        retrieved = sorted(retrieved, key=lambda x: x['similarity'], reverse=True)
        return retrieved, len(retrieved)
    except Exception as e:
        logger.error(f"❌ Search error: {e}", exc_info=True)
        return [], 0

# ======================
# REAL-TIME WEB SEARCH (SERPAPI)
# ======================
def web_search_serpapi(query, num_results=6):
    """
    Use SerpAPI (Google Search) to fetch recent Indian legal content.
    Returns a plain-text summary of top results (title + snippet + source).
    Includes extra DEBUG logs and basic API error handling.
    """
    # Check if key is available
    if not SERPAPI_KEY:
        logger.info("🌐 SerpAPI key missing – skipping external search.")
        return ""

    # Optional sanity check on key length
    if len(SERPAPI_KEY) < 30:
        logger.warning(f"⚠️ SerpAPI key looks invalid (length: {len(SERPAPI_KEY)})")
        return ""

    try:
        logger.info(f"🌐 SerpAPI search triggered for query: {query[:100]!r}")

        params = {
            "engine": "google",
            "q": f"{query} Indian law Supreme Court judgment bail case CrPC IPC NDPS",
            "api_key": SERPAPI_KEY,
            "num": num_results,
            "hl": "en",
            "gl": "in"
        }

        logger.info("🔍 DEBUG - Making request to SerpAPI...")
        logger.info(f"🔍 DEBUG - Using API key: {SERPAPI_KEY[:10]}...{SERPAPI_KEY[-10:]}")

        resp = requests.get("https://serpapi.com/search", params=params, timeout=12)

        logger.info(f"🔍 DEBUG - Response status: {resp.status_code}")

        if resp.status_code != 200:
            logger.error(f"❌ SerpAPI returned status {resp.status_code}")
            logger.error(f"❌ Response body: {resp.text[:500]}")
            return ""

        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            logger.error(f"❌ SerpAPI error: {data['error']}")
            return ""

        logger.info("✅ SerpAPI search successful!")

    except requests.exceptions.Timeout:
        logger.error("❌ SerpAPI timeout after 12 seconds")
        return ""
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ SerpAPI request error: {e}", exc_info=True)
        return ""
    except json.JSONDecodeError as e:
        logger.error(f"❌ SerpAPI JSON decode error: {e}", exc_info=True)
        logger.info(f"   Response text: {resp.text[:500]}")
        return ""
    except Exception as e:
        logger.error(f"❌ SerpAPI unexpected error: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return ""

    # Parse results
    lines = []
    organic = data.get("organic_results", []) or []

    if not organic:
        logger.warning("⚠️ No organic results returned from SerpAPI")
        return ""

    logger.info(f"✅ Found {len(organic)} search results")

    for i, item in enumerate(organic[:num_results], start=1):
        title = item.get("title", "").strip()
        snippet = item.get("snippet", "").strip()
        source = item.get("displayed_link", "").strip() or item.get("link", "")
        if not title and not snippet:
            continue
        lines.append(f"[RESULT {i}] {title}\nSnippet: {snippet}\nSource: {source}\n")

    result_text = "\n".join(lines)
    logger.info(f"✅ Returning {len(lines)} formatted results")
    return result_text

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

    prompt = REASONER_PROMPT.format(
        question=final_question,
        retrieved_text=retrieved_text,
        language_block=language_block
    )

    try:
        if OPENAI_NEW_VERSION and client:
            # New version (1.0.0+)
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            answer_text = response.choices[0].message.content.strip()
        else:
            # Old version
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",
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
                model="gpt-4.1-mini" if "gpt-4.1-mini" in str(client) else "gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100
            )
            answer_text = response.choices[0].message.content.strip()
        else:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
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
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            answer_text = response.choices[0].message.content.strip()
        else:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
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
                model="gpt-4-turbo-preview" if "gpt-4" in str(client) else "gpt-3.5-turbo-16k",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000
            )
            answer_text = response.choices[0].message.content.strip()
        else:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
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

def call_external_legal_reasoner(question, refinement_note=None, language="en"):
    """Fallback when LOCAL_PDF retrieval is weak. Uses SerpAPI + judge-grade reasoning."""
    if not OPENAI_API_KEY:
        return {
            "conclusion": "Error: OpenAI API key not configured",
            "legal_reasoning": "Please add OPENAI_API_KEY to .env file",
            "supreme_court_precedents": [],
            "para_references": [],
            "recommended_next_steps": [],
            "suggested_decision": "",
            "missing_info": ["OpenAI API key required"],
            "confidence": 0.0
        }

    # 1) Real-time SerpAPI search
    web_context = web_search_serpapi(question)

    # 2) Refinement if judge rejected previous answer
    final_question = question
    if refinement_note:
        final_question = (
            f"{question}\n\nJudge Review Comment: {refinement_note}. "
            f"Improve clarity and reasoning accordingly."
        )

    # 3) Language selector
    language_block = build_language_instruction(language)

    # 4) Build prompt using f-string (NO .format → NO KeyError EVER)
    prompt = f"""
You are an AI legal assistant helping an Indian judge decide a case.

QUESTION:
{final_question}

WEB SEARCH RESULTS (Indian law context):
{web_context or "No useful web search results found."}

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
  "confidence": 0.0
}}
IMPORTANT:
- Provide judge-friendly reasoning.
- Cite real precedents (Supreme Court) when certain.
- If not fully sure, mark citation as “approx / to be verified”.
- NO markdown. NO commentary outside JSON.
"""

    # 5) Call LLM
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2200
        )

        answer_text = response.choices[0].message.content.strip()

        if answer_text.startswith("```"):
            lines = answer_text.split("\n")
            answer_text = "\n".join(lines[1:-1]).replace("```json", "").replace("```", "").strip()

        return json.loads(answer_text)
    except Exception as e:
        logger.error(f"❌ External Reasoner Error: {e}", exc_info=True)
        return {
            "conclusion": f"System error during external reasoning: {str(e)}",
            "legal_reasoning": "Unable to process external legal query",
            "supreme_court_precedents": [],
            "para_references": [],
            "recommended_next_steps": [],
            "suggested_decision": "",
            "missing_info": [],
            "confidence": 0.0
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

    prompt = VALIDATOR_PROMPT.format(
        answer_json=json.dumps(answer_json, indent=2, ensure_ascii=False),
        source_text=source_text[:3000]
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
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
def hash_question(question, language="en"):
    """
    Hash question + language so that English and Marathi/Hindi versions
    of the same query are treated as different cache keys.
    """
    lang = (language or "en").lower()
    base = f"{question.strip().lower()}|{lang}"
    return hashlib.md5(base.encode()).hexdigest()

def check_query_cache(question_hash):
    """
    Check query cache in JSON.
    Ignore cache if there are no chunks uploaded.
    Skip answers that were REJECTED.
    """
    cases_data = load_cases_data()
    if not cases_data.get("chunks"):
        return None

    store = load_store()
    cache_entries = store.get("cache", [])
    answers = store.get("answers", [])

    for entry in cache_entries:
        if entry.get("question_hash") == question_hash:
            answer_id = entry.get("answer_id")
            ans = next((a for a in answers if a.get("answer_id") == answer_id), None)
            if not ans:
                continue
            if ans.get("status") == "REJECTED":
                # Never serve rejected answers from cache
                continue

            # update hits + last_used
            entry["cache_hits"] = entry.get("cache_hits", 0) + 1
            entry["last_used"] = datetime.now().isoformat()
            save_store(store)

            return {
                "cached": True,
                "answer_id": ans["answer_id"],
                "question_id": ans["question_id"],
                "conclusion": ans.get("conclusion"),
                "legal_reasoning": ans.get("legal_reasoning"),
                "precedents": ans.get("precedents", []),
                "facts_from_case": ans.get("facts_from_case", []),
                "uncertainty_score": ans.get("uncertainty_score", 0.0),
                "status": ans.get("status", "PENDING_REVIEW"),
                "metrics": ans.get("metrics", {})
            }
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

@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    """Upload PDF and index it into FAISS + JSON metadata."""
    global _faiss_index, _cases_cache

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    case_name = request.form.get('case_name', file.filename.replace('.pdf', ''))

    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "Only PDF files allowed"}), 400

    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        text = extract_pdf_text(file_path)
        if not text or len(text) < 100:
            return jsonify({"error": "Could not extract text from PDF"}), 400

        chunks = smart_chunk_judgment(text, chunk_size=800, overlap=200)
        if not chunks:
            return jsonify({"error": "No valid chunks created"}), 400

        embeddings = embed_chunks(chunks)
        case_id = str(uuid.uuid4())

        # Load or create FAISS index
        index, cases_data = load_vector_db()
        if index is None:
            cases_data = {'chunks': []}
            index = create_faiss_index(embeddings)
        else:
            index.add(np.array(embeddings).astype('float32'))

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

        # update cache
        _faiss_index = index
        _cases_cache = cases_data

        return jsonify({
            "status": "success",
            "case_id": case_id,
            "case_name": case_name,
            "chunks_created": len(chunks),
            "message": f"✅ Indexed {len(chunks)} smart chunks from {case_name}"
        })

    except Exception as e:
        logger.error(f"❌ Upload error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

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
        case_id = data.get('case_id')
        language = (data.get('language') or 'en').lower()
        if language not in ('en', 'mr', 'hi'):
            language = 'en'

        if not question:
            return jsonify({"error": "No question provided"}), 400

        store = load_store()
        question_hash = hash_question(question, language=language)

        # 0️⃣ — Check if a previous answer was rejected → use its review_comment to refine
        last_rejected = get_latest_rejected_answer(store, question_hash)
        refinement_note = last_rejected.get("review_comment") if last_rejected else None

        # 1️⃣ — CACHE CHECK (only if no refinement needed)
        cached_answer = None
        if not refinement_note:
            cached_answer = check_query_cache(question_hash)

        if cached_answer:
            cached_answer["from_cache"] = True
            cached_answer["message"] = "⚡ Retrieved from cache (duplicate question)"
            logger.info("💾 Cache hit for question.")
            return jsonify(cached_answer)

        # 2️⃣ — Register new question record
        question_id = str(uuid.uuid4())
        answer_id = str(uuid.uuid4())

        store["questions"].append({
            "question_id": question_id,
            "question_text": question,
            "question_hash": question_hash,
            "language": language,
            "asked_at": datetime.now().isoformat()
        })

        # 3️⃣ — Intent Detection
        intent = detect_intent(question)
        logger.info(f"🧠 Detected Intent: {intent}")

        retrieved_cases = []
        retrieval_count = 0
        validator_result = None

        if intent == "GREETING":
            used_mode = "GREETING"
            answer_json = call_greeting_llm(question, language)
            final_confidence = answer_json.get("confidence", 1.0)
            
        elif intent == "SUMMARY":
            used_mode = "SUMMARY"
            retrieved_cases, retrieval_count = search_local_vector_db("summary of facts", top_k=15, case_id=case_id)
            if case_id and retrieval_count == 0:
                logger.warning(f"⚠️ Zero chunks retrieved for SUMMARY on case_id {case_id}.")
                answer_json = {
                    "conclusion": "I could not find any relevant information in the uploaded document to summarize.",
                    "legal_reasoning": "The semantic search returned zero chunks matching your query from the active document context.",
                    "confidence": 0.0
                }
            else:
                answer_json = call_summary_llm(retrieved_cases, language)
            final_confidence = answer_json.get("confidence", 0.9)
            
        else: # DOCUMENT_QA
            retrieved_cases, retrieval_count = search_local_vector_db(question, top_k=10, case_id=case_id)
            max_sim = max((rc["similarity"] for rc in retrieved_cases), default=0.0)
            logger.info(f"🔎 Retrieval_count={retrieval_count}, max_sim={max_sim:.3f}, case_id={case_id}")

            if case_id:
                # Document is active; NEVER fallback to SerpAPI
                use_local = True
            else:
                use_local = (retrieval_count >= 1 and max_sim >= 0.75)

            if use_local and case_id and retrieval_count == 0:
                logger.warning(f"⚠️ Zero chunks retrieved for DOCUMENT_QA on case_id {case_id}. Query: '{question}'")
                answer_json = {
                    "conclusion": "I could not find any relevant information in the uploaded document to answer your question.",
                    "legal_reasoning": "The semantic search returned zero chunks matching your query from the active document context.",
                    "confidence": 0.0
                }
                used_mode = "LOCAL_PDF"
                final_confidence = 0.0
            elif not use_local:
                used_mode = "EXTERNAL"
                logger.info("🌐 Using EXTERNAL reasoning (SerpAPI + general legal knowledge)")
                answer_json = call_external_legal_reasoner(
                    question, refinement_note=refinement_note, language=language
                )
                final_confidence = max(0.1, min(1.0, answer_json.get("confidence", 0.6)))
            else:
                used_mode = "LOCAL_PDF"
                logger.info("📚 Using LOCAL_PDF RAG reasoning (uploaded judgments)")
                answer_json = call_reasoner_llm(
                    question, retrieved_cases, refinement_note=refinement_note, language=language
                )

                source_text_for_validator = "\n\n".join([rc["chunk"] for rc in retrieved_cases[:5]])
                validator_result = call_validator_llm(answer_json, source_text_for_validator)

                base_conf = answer_json.get("confidence", 0.5)
                validator_conf = validator_result.get("confidence_score", 0.8)
                hallucinations = validator_result.get("hallucinations_found", 0)
                final_confidence = max(0.1, min(1.0, (base_conf * validator_conf) - (hallucinations * 0.1)))

        # 5️⃣ — Normalize fields
        precedents_list = (
            answer_json.get("precedents_cited_in_text")
            or answer_json.get("supreme_court_precedents")
            or []
        )

        facts_list = answer_json.get("facts_from_case", [])
        suggested_decision = answer_json.get("suggested_decision", "")
        recommended_next_steps = answer_json.get("recommended_next_steps", [])

        # 🚫 Hide missing_info completely from UI (but keep internal if needed)
        missing_info = []

        # 6️⃣ — Build performance metrics
        metrics = build_answer_metrics(
            used_mode=used_mode,
            retrieved_cases=retrieved_cases[:5] if used_mode == "LOCAL_PDF" else [],
            validator_result=validator_result,
            answer_json=answer_json
        )

        # 7️⃣ — Save answer + review + cache
        store["answers"].append({
            "answer_id": answer_id,
            "question_id": question_id,
            "language": language,
            "conclusion": answer_json.get("conclusion", "No conclusion"),
            "legal_reasoning": answer_json.get("legal_reasoning", "No reasoning"),
            "precedents": precedents_list,
            "facts_from_case": facts_list,
            "uncertainty_score": final_confidence,
            "retrieved_chunks": [
                {"case": rc["case_name"], "similarity": rc["similarity"]}
                for rc in (retrieved_cases[:5] if used_mode == "LOCAL_PDF" else [])
            ],
            "created_at": datetime.now().isoformat(),
            "status": "PENDING_REVIEW",
            "review_comment": "",
            "metrics": metrics
        })

        if used_mode == "LOCAL_PDF" and validator_result:
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

        store["cache"].append({
            "cache_id": str(uuid.uuid4()),
            "question_hash": question_hash,
            "answer_id": answer_id,
            "question_id": question_id,
            "cache_hits": 1,
            "last_used": datetime.now().isoformat()
        })

        save_store(store)

        # 8️⃣ — Final response
        return jsonify({
            "answer_id": answer_id,
            "question_id": question_id,
            "mode": used_mode,
            "language": language,
            "conclusion": answer_json.get("conclusion"),
            "legal_reasoning": answer_json.get("legal_reasoning"),
            "precedents": precedents_list,
            "facts_from_case": facts_list,
            "missing_info": missing_info,  # always empty for UI
            "suggested_decision": suggested_decision,
            "recommended_next_steps": recommended_next_steps,
            "uncertainty_score": round(final_confidence, 2),
            "retrieved_cases_count": retrieval_count if used_mode == "LOCAL_PDF" else 0,
            "retrieved_cases": retrieved_cases[:5] if used_mode == "LOCAL_PDF" else [],
            "validator_result": validator_result if validator_result else {
                "is_valid": used_mode == "EXTERNAL",
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
    """
    try:
        data = request.json or {}
        answer_id = data.get('answer_id')
        approved = data.get('approved', True)
        comment = data.get('comment', "")

        store = load_store()

        # Update answer status + review comment
        for ans in store.get("answers", []):
            if ans.get("answer_id") == answer_id:
                ans["status"] = "APPROVED" if approved else "REJECTED"
                ans["review_comment"] = comment or ""
                break

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
            "comment": comment or ""
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        store = load_store()
        questions = store.get("questions", [])
        answers = store.get("answers", [])

        # Build quick lookup map for answers by question_id
        ans_by_qid = {}
        for a in answers:
            qid = a.get("question_id")
            if qid and qid not in ans_by_qid:
                ans_by_qid[qid] = a

        # Sort questions by asked_at desc
        def parse_dt(s):
            try:
                return datetime.fromisoformat(s)
            except Exception:
                return datetime.min

        questions_sorted = sorted(
            questions,
            key=lambda q: parse_dt(q.get("asked_at", "")),
            reverse=True
        )

        history = []
        for q in questions_sorted[:50]:
            qid = q.get("question_id")
            ans = ans_by_qid.get(qid)
            history.append({
                "question_id": qid,
                "question": q.get("question_text"),
                "asked_at": q.get("asked_at"),
                "answer_id": ans.get("answer_id") if ans else None,
                "conclusion": ans.get("conclusion") if ans else None,
                "status": ans.get("status") if ans else None,
                "confidence": ans.get("uncertainty_score") if ans else None
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

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        cases_data = load_cases_data()
        store = load_store()

        total_cases_uploaded = len({c["case_id"] for c in cases_data.get("chunks", [])}) if cases_data.get("chunks") else 0
        total_questions_asked = len(store.get("questions", []))
        approved_answers = sum(1 for a in store.get("answers", []) if a.get("status") == "APPROVED")
        cached_queries = len(store.get("cache", []))

        return jsonify({
            "total_cases_uploaded": total_cases_uploaded,
            "total_questions_asked": total_questions_asked,
            "approved_answers": approved_answers,
            "cached_queries": cached_queries,
            "system_status": "operational"
        })
    except Exception as e:
        logger.error("Stats error:", e)
        return jsonify({
            "total_cases_uploaded": 0,
            "total_questions_asked": 0,
            "approved_answers": 0,
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
