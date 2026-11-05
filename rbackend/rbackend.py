from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import pdfplumber
import docx
import io
import os
import json
import asyncio
import concurrent.futures
from dotenv import load_dotenv
import uvicorn
from typing import List, Dict, Any, Optional, Tuple
from serpapi.google_search import GoogleSearch
import hashlib
import re
import faiss
import numpy as np
from datetime import datetime
import logging
from pydantic import BaseModel
import requests
from thefuzz import fuzz
from scipy.spatial.distance import cosine
from bs4 import BeautifulSoup
from fastapi.background import BackgroundTasks

last_save_time = datetime.now()
SAVE_INTERVAL_SECONDS = 60  # Save every minute instead of every operation

def background_save_data():
    """Background task to save vector data to disk"""
    save_vector_metadata()
    save_faiss_index()
    logger.info("Background save completed")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI()

# ── Evaluation event logger (fire-and-forget, never raises) ────────────────
try:
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'evaluation'))
    from event_logger import log_event_async as _log_research_event
except Exception:
    def _log_research_event(*a, **k): pass

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("🚨 OpenAI API Key is missing!")

MODEL_NAME = "gpt-4-turbo"
client = OpenAI(api_key=OPENAI_API_KEY)

# Vector database setup
EMBEDDING_DIM = 1536
vector_index = faiss.IndexFlatL2(EMBEDDING_DIM)
vector_metadata = {}
query_cache = {}

# File paths for persistent storage
REMARKS_FILE = "remarks.json"
VECTOR_METADATA_FILE = "vector_metadata.json"
QUERY_CACHE_FILE = "query_cache.json"
FAISS_INDEX_FILE = "vector_index.faiss"
DOCUMENTS_DIR = "documents"  # New directory for document storage

# Constants for similarity thresholds
DOC_SIMILARITY_THRESHOLD = 0.9
QUERY_SIMILARITY_THRESHOLD = 0.75

# External APIs
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
IK_API_TOKEN = os.getenv("IK_API_TOKEN", "")
IK_API_URL = "https://api.indiankanoon.org/search/"

# Stopwords for query processing
STOPWORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her',
    'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there',
    'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get',
    'which', 'go', 'me'
}

class DocumentAnalysis(BaseModel):
    filename: str
    text: str
    analysis: Dict[str, Any]

class RemarkRequest(BaseModel):
    file_hash: str
    remark: str


@app.post("/api/remarks")
async def save_remark(request: RemarkRequest):
    remarks = load_remarks()
    remarks[request.file_hash] = {
        "remark": request.remark,
        "timestamp": datetime.now().isoformat()
    }
    save_remarks(remarks)
    return {"status": "success"}

@app.get("/api/remarks/{file_hash}")
async def get_remark(file_hash: str):
    """Get a remark for a specific document or webpage."""
    try:
        remarks = load_remarks()
        remark_data = remarks.get(file_hash, {})
        if not remark_data:
            return JSONResponse({
                "status": "not_found",
                "message": "No remark found for this document",
                "file_hash": file_hash
            }, status_code=404)
        return JSONResponse({
            "status": "success",
            "file_hash": file_hash,
            "remark": remark_data.get("remark", ""),
            "timestamp": remark_data.get("timestamp", "")
        })
    except Exception as e:
        logger.error(f"Error getting remark: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def load_remarks() -> Dict[str, Dict[str, str]]:
    """Load remarks from JSON file."""
    try:
        if os.path.exists(REMARKS_FILE):
            with open(REMARKS_FILE, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading remarks: {str(e)}")
        return {}

def save_remarks(remarks: Dict[str, Dict[str, str]]) -> None:
    """Save remarks to JSON file."""
    try:
        with open(REMARKS_FILE, "w") as f:
            json.dump(remarks, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving remarks: {str(e)}")

def load_vector_metadata() -> Dict[str, Dict[str, Any]]:
    """Load vector metadata from JSON file."""
    try:
        if os.path.exists(VECTOR_METADATA_FILE):
            with open(VECTOR_METADATA_FILE, "r") as f:
                data = json.load(f)
                # Remove embeddings from loaded data to rebuild FAISS index
                for meta in data.values():
                    if 'embedding' in meta:
                        del meta['embedding']
                return data
        return {}
    except Exception as e:
        logger.error(f"Error loading vector metadata: {str(e)}")
        return {}

def save_vector_metadata() -> None:
    """Save vector metadata to JSON file."""
    try:
        # Create a copy without embeddings to reduce file size
        data_to_save = {}
        for file_hash, meta in vector_metadata.items():
            meta_copy = meta.copy()
            if 'embedding' in meta_copy:
                del meta_copy['embedding']
            data_to_save[file_hash] = meta_copy
        with open(VECTOR_METADATA_FILE, "w") as f:
            json.dump(data_to_save, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving vector metadata: {str(e)}")

def load_query_cache() -> Dict[str, Dict[str, Any]]:
    """Load query cache from JSON file."""
    try:
        if os.path.exists(QUERY_CACHE_FILE):
            with open(QUERY_CACHE_FILE, "r") as f:
                data = json.load(f)
                # Ensure results field is a dictionary, not a string
                for query, cache in data.items():
                    if isinstance(cache.get("results"), str):
                        try:
                            cache["results"] = json.loads(cache["results"])
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in results for query: {query}")
                            cache["results"] = {}
                    if 'embedding' in cache:
                        del cache['embedding']
                return data
        return {}
    except Exception as e:
        logger.error(f"Error loading query cache: {str(e)}")
        return {}

def save_query_cache() -> None:
    """Save query cache to JSON file."""
    try:
        # Create a copy without embeddings
        data_to_save = {}
        for query, cache in query_cache.items():
            cache_copy = cache.copy()
            if 'embedding' in cache_copy:
                del cache_copy['embedding']
            data_to_save[query] = cache_copy
        with open(QUERY_CACHE_FILE, "w") as f:
            json.dump(data_to_save, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving query cache: {str(e)}")

def load_faiss_index():
    """Load FAISS index from file and rebuild embeddings."""
    global vector_index, vector_metadata
    try:
        if os.path.exists(FAISS_INDEX_FILE):
            vector_index = faiss.read_index(FAISS_INDEX_FILE)
            logger.info(f"Loaded FAISS index from {FAISS_INDEX_FILE}")
        else:
            vector_index = faiss.IndexFlatL2(EMBEDDING_DIM)
            logger.info("Initialized new FAISS index")
        
        # Rebuild embeddings for vector_metadata
        vector_metadata = load_vector_metadata()
        if vector_metadata:
            embeddings = []
            hashes = []
            for file_hash, meta in vector_metadata.items():
                embedding = generate_embedding(meta['text'][:1000])
                meta['embedding'] = embedding
                embeddings.append(embedding)
                hashes.append(file_hash)
            if embeddings:
                vector_index = faiss.IndexFlatL2(EMBEDDING_DIM)
                vector_index.add(np.array(embeddings, dtype='float32'))
                logger.info(f"Rebuilt FAISS index with {len(embeddings)} embeddings")
    except Exception as e:
        logger.error(f"Error loading FAISS index: {str(e)}")
        vector_index = faiss.IndexFlatL2(EMBEDDING_DIM)

def save_faiss_index():
    """Save FAISS index to file."""
    try:
        faiss.write_index(vector_index, FAISS_INDEX_FILE)
        logger.info(f"Saved FAISS index to {FAISS_INDEX_FILE}")
    except Exception as e:
        logger.error(f"Error saving FAISS index: {str(e)}")

# Initialize data on startup
vector_metadata = load_vector_metadata()
query_cache = load_query_cache()
load_faiss_index()

def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF using parallel processing."""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                texts = list(executor.map(lambda page: page.extract_text() or "", pdf.pages))
        return "\n".join(texts).strip()
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX file."""
    try:
        doc = docx.Document(io.BytesIO(content))
        return "\n".join([para.text for para in doc.paragraphs]).strip()
    except Exception as e:
        return f"Error extracting DOCX: {str(e)}"

async def extract_text(file: UploadFile) -> str:
    """Route text extraction based on file type."""
    content = await file.read()
    if file.filename.endswith('.pdf'):
        return extract_text_from_pdf(content)
    elif file.filename.endswith('.docx'):
        return extract_text_from_docx(content)
    else:
        return "Unsupported file type"

def scrape_webpage(url: str) -> Optional[str]:
    """Fetch and extract text content from a webpage."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to fetch webpage {url}: Status {response.status_code}")
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
        body = soup.find('body')
        if not body:
            logger.error(f"No body tag found in webpage {url}")
            return None
        text = body.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            logger.error(f"No meaningful content extracted from {url}")
            return None
        return text[:20000]
    except Exception as e:
        logger.error(f"Error scraping webpage {url}: {str(e)}")
        return None

def generate_embedding(text: str) -> List[float]:
    """Generate embedding for text using OpenAI."""
    try:
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return [0.0] * EMBEDDING_DIM

def normalize_vector(vector: List[float]) -> np.ndarray:
    """Normalize a vector to unit length."""
    vector_np = np.array(vector, dtype='float32')
    norm = np.linalg.norm(vector_np)
    if norm > 0:
        return vector_np / norm
    return vector_np

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    return 1 - cosine(vec1, vec2)

def find_similar_document(text: str) -> Optional[str]:
    """Check if a similar document already exists in the database."""
    if vector_index.ntotal == 0:
        return None
    text_embedding = generate_embedding(text[:1000])
    query_vector = np.array([text_embedding], dtype='float32')
    k = min(5, vector_index.ntotal) # How many nearest documents should FAISS return?
    distances, indices = vector_index.search(query_vector, k)
    for i, idx in enumerate(indices[0]):
        if idx >= 0:
            file_hash = list(vector_metadata.keys())[idx]
            similarity = 1 - distances[0][i] / 2
            logger.info(f"Similarity with document {file_hash}: {similarity}")
            if similarity >= DOC_SIMILARITY_THRESHOLD:
                return file_hash
    return None

def find_similar_query(query: str) -> Optional[Dict[str, Any]]:
    """Check if a similar query already exists in the cache."""
    if not query_cache:
        return None
        
    query_embedding = generate_embedding(query)
    critical_terms, _ = preprocess_query_terms(query)
    
    for cached_query, cache_data in query_cache.items():
        if "embedding" in cache_data:
            similarity = cosine_similarity(query_embedding, cache_data["embedding"])
            cached_critical_terms, _ = preprocess_query_terms(cached_query)
            
            if similarity >= QUERY_SIMILARITY_THRESHOLD and set(critical_terms).issubset(set(cached_critical_terms)):
                logger.info(f"Using cached result for similar query: '{cached_query}'")
                cache_data["timestamp"] = datetime.now().isoformat()
                return {
                    "cached_query": cached_query,
                    "results": cache_data["results"],
                    "similarity": similarity
                }
    return None

def save_to_vector_db(file_hash: str, filename: str, text: str, analysis: Dict[str, Any], source: str = "document", url: str = None) -> None:
    """Save document or webpage to vector database and persist to file."""
    try:
        # Use a smaller text sample for embedding to speed up processing
        embedding = generate_embedding(text[:500])  # Reduced from 1000
        embedding_array = np.array([embedding], dtype='float32')
        vector_index.add(embedding_array)
        vector_metadata[file_hash] = {
            "filename": filename,
            "text":text,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat(),
            "embedding": embedding,
            "source": source,
            "url": url if url else None
        }
        # Don't save to disk on every operation - will be handled by a background task
        # save_vector_metadata()
        # save_faiss_index()
        logger.info(f"Saved {source} {filename} to vector DB with hash {file_hash}")
    except Exception as e:
        logger.error(f"Error saving to vector DB: {str(e)}")

def cache_query_result(query: str, results: Dict[str, Any]) -> None:
    """Cache query results and persist to file."""
    try:
        query_embedding = generate_embedding(query)
        query_cache[query] = {
            "results": results,
            "timestamp": datetime.now().isoformat(),
            "embedding": query_embedding
        }
        save_query_cache()
        logger.info(f"Cached query result for '{query}'")
    except Exception as e:
        logger.error(f"Error caching query: {str(e)}")

def query_llm(prompt: str, text: str, source: str = "document") -> str:
    """Query the LLM with adaptive prompts based on source type."""
    try:
        # Limit text size to reduce token usage and processing time
        max_text_length = 10000  # Reduced from 20000
        truncated_text = text[:max_text_length]
        
        # Use a more efficient model for initial processing
        initial_model = "gpt-3.5-turbo"  # Faster than gpt-4-turbo
        
        if source == "news":
            legal_prompt = """
            Analyze this news article and extract the following information in EXACTLY this JSON format:
            {
                "title": "Article title",
                "date": "Publication or event date (e.g., '2003')",
                "key_persons": ["List of names mentioned (e.g., 'Nisha Sharma', 'Munish Dalal')"],
                "locations": ["List of locations mentioned (e.g., 'Noida')"],
                "events": ["List of key events described"],
                "summary": "Brief 1-paragraph summary of the article"
            }
            """
        else:
            legal_prompt = """
            Analyze this legal document and extract the following information in EXACTLY this JSON format:
            {
                "case_laws": [
                    {
                        "case_name": "Full case name",
                        "citation": "Official citation",
                        "year": "Year of judgment",
                        "court": "Name of court",
                        "context": "Relevant sentence where this appears"
                    }
                ],
                "statutes": [
                    {
                        "statute_name": "Name of the statute/law",
                        "section": "Specific section/article",
                        "full_reference": "Complete reference (e.g., 'Section 302 IPC')",
                        "context": "Relevant sentence where this appears"
                    }
                ],
                "constitutional_provisions": [
                    {
                        "article": "Article/Amendment number",
                        "subject": "Brief description (e.g., 'Right to Equality')",
                        "full_reference": "Complete reference (e.g., 'Article 14 of the Indian Constitution')",
                        "context": "Relevant sentence where this appears"
                    }
                ],
                "international_laws": [
                    {
                        "name": "Treaty/Convention name",
                        "article": "Article/Protocol number",
                        "full_reference": "Complete reference (e.g., 'UDHR Article 19')",
                        "context": "Relevant sentence where this appears"
                    }
                ],
                "legal_principles": [
                    "List of key legal principles mentioned"
                ],
                "summary": "Brief 1-paragraph summary of the document"
            }
            Important Notes:
            1. For statutes, always include the full reference (e.g., 'Section 302 IPC' not just '302')
            2. For constitutional provisions, specify country if not Indian (e.g., 'US Constitution 14th Amendment')
            3. For international laws, use standard abbreviations (e.g., UDHR, ICCPR, CEDAW)
            4. Always include the context sentence where each reference appears
            5. Be thorough - extract ALL references you can find
            """
        completion = client.chat.completions.create(
            model=initial_model,  # Use faster model
            messages=[
                {"role": "system", "content": f"You are a {'news analyst' if source == 'news' else 'senior legal analyst'} with expertise in {'journalism' if source == 'news' else 'Indian and international law'}."},
                {"role": "user", "content": f"{legal_prompt}\n\n{'Article' if source == 'news' else 'Document'} Text:\n{truncated_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        return completion.choices[0].message.content
    except Exception as e:
        return json.dumps({"error": str(e)})

def preprocess_text(text: str) -> str:
    """Clean and normalize text for better embedding and search."""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def extract_citation(text: str) -> Optional[str]:
    """Extract case citation from text."""
    patterns = [
        r'((?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:v\.|vs\.|V\.|VS\.)\s+(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:\([^)]*\))?\s*(?:\d{1,4}\s+)?(?:[A-Z]+\s+\d+)?\s*(?:\(\d{4}\))?\s*(?:\d+\s+[A-Z]+\s+\d+)?)',
        r'((?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:v\.|vs\.|V\.|VS\.)\s+(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*,\s*(?:\d{4})\s*(?:\d+\s+[A-Z]+\s+\d+)?)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None

def extract_year_from_text(text: str) -> str:
    """Extract year from text."""
    match = re.search(r'(?:19|20)\d{2}', text)
    return match.group(0) if match else 'N/A'

def determine_court(text: str) -> str:
    """Determine court from text."""
    text = text.lower()
    if 'supreme court' in text or 'sci' in text:
        return 'Supreme Court of India'
    elif 'high court' in text:
        return 'High Court'
    return 'Unknown Court'

def analyze_web_content(url: str, text: str, source: str = "webpage") -> Dict[str, Any]:
    """Analyze scraped content based on source type."""
    try:
        analysis = query_llm("Analyze this content", text, source=source)
        return json.loads(analysis)
    except Exception as e:
        logger.error(f"Error analyzing web content from {url}: {str(e)}")
        return {"error": str(e), "summary": f"Failed to analyze {source} content"}

def preprocess_query_terms(query: str) -> Tuple[List[str], List[str]]:
    """
    Extract and categorize query terms into critical and non-critical terms.
    Returns a tuple of (critical_terms, non_critical_terms).
    """
    critical_patterns = [
        r'section\s+\d+(?:\s*[A-Za-z]+)?',  # e.g., "section 302 IPC"
        r'article\s+\d+[A-Za-z]*',  # e.g., "article 21"
        r'\d{4}\s+(?:Act|Bill|Law)',  # e.g., "1860 Act"
        r'v[s]?\.?\s+',  # Case name separator
        r'AIR\s+\d{4}\s+\w+\s+\d+',  # Citation format
        r'\(\d{4}\)\s+\d+\s+SCC\s+\d+',  # SCC citation format
        r'\b(?:19|20)\d{2}\b',  # Exact year, e.g., "2003"
        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'  # Proper nouns, e.g., "Noida"
    ]
    
    critical_terms = []
    for pattern in critical_patterns:
        matches = re.finditer(pattern, query, re.IGNORECASE)
        critical_terms.extend(match.group().strip() for match in matches)
    
    # Deduplicate critical terms while preserving order
    seen_critical = set()
    deduped_critical = []
    for t in critical_terms:
        if t.lower() not in seen_critical:
            seen_critical.add(t.lower())
            deduped_critical.append(t)
    critical_terms = deduped_critical

    remaining_text = query
    for term in critical_terms:
        remaining_text = remaining_text.replace(term, ' ')
    
    non_critical_terms = [word.strip() for word in remaining_text.split() 
                         if len(word.strip()) > 2 and word.strip().lower() not in STOPWORDS]
    
    return critical_terms, non_critical_terms

def is_law_related_query(query: str) -> bool:
    """
    Check if the query is related to law based on critical terms.
    Returns True if law-related, False otherwise.
    """
    critical_terms, non_critical_terms = preprocess_query_terms(query)
    legal_keywords = [
        'case', 'court', 'judgment', 'petition', 'appeal', 'plaintiff', 'defendant',
        'lawyer', 'attorney', 'statute', 'provision', 'citation', 'legal', 'constitution',
        'amendment', 'treaty', 'convention', 'supreme court', 'high court', 'act', 'bill',
        'bail', 'murder', 'dowry', 'cruelty', 'conviction', 'evidence', 'accused', 'witness',
        'ndps', 'narcotic', 'seniority', 'promotion', 'service law', 'tax', 'reassessment',
        'negligence', 'accident', 'motor vehicle', 'anticipatory', 'crpc', 'ipc', 'cpc',
        'contempt', 'jurisdiction', 'land acquisition', 'compensation', 'mandamus', 'writ',
        'consumer', 'pocso', 'arbitration', 'negotiable', 'cheque', 'rape', 'corroboration',
        'education', 'natural justice', 'audi alteram partem', 'locus standi', 'public interest',
        'pil', 'fundamental right'
    ]
    # Check if critical terms include legal patterns or if query includes legal keywords
    has_legal_pattern = any(
        re.match(r'(section\s+\d+|article\s+\d+|v[s]?\.?|\d{4}\s+(?:act|bill|law)|air\s+\d{4}|\(\d{4}\)\s+\d+\s+scc\s+\d+)', term, re.IGNORECASE)
        for term in critical_terms
    )
    query_lower = query.lower()
    has_legal_keyword = any(keyword in query_lower for keyword in legal_keywords)
    return has_legal_pattern or has_legal_keyword

def check_term_matches(text: str, critical_terms: List[str], non_critical_terms: List[str]) -> Tuple[bool, float]:
    """
    Check if text contains required terms and calculate match score.
    Returns tuple of (is_valid, match_score).
    Lexical matching provides relevance boosting without arbitrarily rejecting
    semantically relevant candidates that do not have exact verbatim phrasing.
    """
    text = text.lower()
    
    if critical_terms:
        critical_matches = sum(1 for term in critical_terms if term.lower() in text)
        critical_score = critical_matches / len(critical_terms)
    else:
        critical_score = 0.5  # Neutral default when no critical terms specified
    
    if non_critical_terms:
        non_critical_matches = sum(1 for term in non_critical_terms if term.lower() in text)
        non_critical_score = non_critical_matches / len(non_critical_terms)
    else:
        non_critical_score = 0.5
    
    final_score = (critical_score * 0.7) + (non_critical_score * 0.3)
    return True, final_score

def expand_query(query: str) -> str:
    """Expand query with synonyms and related terms."""
    expanded_terms = []
    if "noida" in query.lower():
        expanded_terms.append("Uttar Pradesh")
    if "dowry" in query.lower():
        expanded_terms.append("Section 498A")
    if expanded_terms:
        return f"{query} {' '.join(expanded_terms)}"
    return query

def search_external_sources(query: str) -> List[Dict[str, Any]]:
    """Search external sources and analyze webpage content."""
    results = []
    critical_terms, non_critical_terms = preprocess_query_terms(query)
    
    # Indian Kanoon search
    try:
        params = {
            "formInput": query,
            "token": IK_API_TOKEN
        }
        response = requests.get(IK_API_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            for doc in data.get('docs', [])[:5]:
                url = f"https://indiankanoon.org/doc/{doc.get('tid', '')}/"
                title = doc.get('title', '')
                text = scrape_webpage(url)
                if text:
                    search_text = f"{title} {text} {doc.get('headline', '')}"
                    is_valid, match_score = check_term_matches(search_text, critical_terms, non_critical_terms)
                    if not is_valid:
                        continue
                    analysis = analyze_web_content(url, text, source="webpage")
                    file_hash = hashlib.md5(text.encode()).hexdigest()
                    save_to_vector_db(
                        file_hash=file_hash,
                        filename=title[:50],
                        text=text,
                        analysis=analysis,
                        source="webpage",
                        url=url
                    )
                    base_confidence = min(90, max(60, fuzz.partial_ratio(query.lower(), title.lower())))
                    confidence = base_confidence * 0.5 + 100 * match_score * 0.5
                    results.append({
                        "source": "indian_kanoon",
                        "title": title,
                        "citation": doc.get('title', ''),
                        "year": doc.get('publishdate', '').split('-')[0] if doc.get('publishdate') else 'N/A',
                        "court": doc.get('docsource', 'Unknown Court'),
                        "snippet": doc.get('headline', ''),
                        "url": url,
                        "confidence": confidence,
                        "analysis": analysis,
                        "file_hash": file_hash
                    })
    except Exception as e:
        logger.error(f"Indian Kanoon search error: {str(e)}")
    
    # Google search
    if SERPAPI_KEY:
        try:
            # Legal search
            params = {
                "api_key": SERPAPI_KEY,
                "engine": "google",
                "q": query,
                "hl": "en",
                "gl": "in"
            }
            search = GoogleSearch(params)
            data = search.get_dict()
            
            # Process legal search results
            for result in data.get('organic_results', [])[:5]:
                url = result.get('link', '')
                title = result.get('title', '')
                text = scrape_webpage(url)
                if text:
                    search_text = f"{title} {text} {result.get('snippet', '')}"
                    is_valid, match_score = check_term_matches(search_text, critical_terms, non_critical_terms)
                    if not is_valid:
                        continue
                    analysis = analyze_web_content(url, text, source="webpage")
                    file_hash = hashlib.md5(text.encode()).hexdigest()
                    save_to_vector_db(
                        file_hash=file_hash,
                        filename=title[:50],
                        text=text,
                        analysis=analysis,
                        source="webpage",
                        url=url
                    )
                    citation = extract_citation(title) or title
                    base_confidence = min(85, max(50, fuzz.partial_ratio(query.lower(), title.lower())))
                    confidence = base_confidence * 0.5 + 100 * match_score * 0.5
                    results.append({
                        "source": "google",
                        "title": title,
                        "citation": citation,
                        "year": extract_year_from_text(title + " " + result.get('snippet', '')),
                        "court": determine_court(title + " " + result.get('snippet', '')),
                        "snippet": result.get('snippet', ''),
                        "url": url,
                        "confidence": confidence,
                        "analysis": analysis,
                        "file_hash": file_hash
                    })
            
            # News search
            params["q"] = f"{query} news"
            params["tbm"] = "nws"
            search = GoogleSearch(params)
            data = search.get_dict()
            
            # Process news search results
            for result in data.get('news_results', [])[:3]:
                url = result.get('link', '')
                title = result.get('title', '')
                text = scrape_webpage(url)
                if text:
                    search_text = f"{title} {text} {result.get('snippet', '')}"
                    is_valid, match_score = check_term_matches(search_text, critical_terms, non_critical_terms)
                    if not is_valid:
                        continue
                    analysis = analyze_web_content(url, text, source="news")
                    file_hash = hashlib.md5(text.encode()).hexdigest()
                    save_to_vector_db(
                        file_hash=file_hash,
                        filename=title[:50],
                        text=text,
                        analysis=analysis,
                        source="news",
                        url=url
                    )
                    base_confidence = min(80, max(50, fuzz.partial_ratio(query.lower(), title.lower())))
                    confidence = base_confidence * 0.5 + 100 * match_score * 0.5
                    results.append({
                        "source": "google_news",
                        "title": title,
                        "citation": title,
                        "year": extract_year_from_text(title + " " + result.get('snippet', '')),
                        "court": "N/A",
                        "snippet": result.get('snippet', ''),
                        "url": url,
                        "confidence": confidence,
                        "analysis": analysis,
                        "file_hash": file_hash
                    })
        except Exception as e:
            logger.error(f"Google search error: {str(e)}")
    
    return sorted(results, key=lambda x: x["confidence"], reverse=True)

def semantic_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Search the vector database with enhanced semantic similarity and term-matching boost."""
    if vector_index is None or vector_index.ntotal == 0 or not vector_metadata:
        return []
    
    query_embedding = generate_embedding(query)
    query_vector = np.array([query_embedding], dtype='float32')
    
    # Check for valid query vector
    if np.all(query_vector == 0) or np.linalg.norm(query_vector) < 1e-6:
        logger.warning("Query embedding is all zeros; skipping vector search")
        return []
        
    search_k = min(k * 2, vector_index.ntotal)
    distances, indices = vector_index.search(query_vector, search_k)
    
    critical_terms, non_critical_terms = preprocess_query_terms(query)
    meta_keys = list(vector_metadata.keys())
    
    results = []
    for i, idx in enumerate(indices[0]):
        if 0 <= idx < len(meta_keys):
            file_hash = meta_keys[idx]
            meta = vector_metadata.get(file_hash)
            if not meta:
                continue
            
            search_text = f"{meta.get('filename', '')} {meta.get('text', '')} {json.dumps(meta.get('analysis', {}))}"
            _, match_score = check_term_matches(search_text, critical_terms, non_critical_terms)
            
            # L2 distance converted to base similarity (0-100)
            base_confidence = max(0.0, min(100.0, 100.0 * (1.0 - (distances[0][i] / 2.0))))
            # Blended confidence: 60% semantic similarity + 40% lexical alignment
            confidence = (base_confidence * 0.6) + (match_score * 40.0)
            
            results.append({
                "file_hash": file_hash,
                "filename": meta.get("filename", "Unknown"),
                "text": (meta.get("text", "")[:500] + "...") if meta.get("text") else "",
                "analysis": meta.get("analysis", {}),
                "confidence": float(confidence),
                "source": meta.get("source", "document"),
                "url": meta.get("url", None)
            })
    
    sorted_results = sorted(results, key=lambda x: x["confidence"], reverse=True)
    return sorted_results[:k]

@app.post("/api/search/query")
async def search_legal_query(query: str = Form(...)):
    """Search for legal information by query with term-matching and contextual filters."""
    try:
        logger.info(f"Processing query: {query}")

        # Add embedding initialization here
        query_embedding = generate_embedding(query)
        
        # Validate if query is law-related
        if not is_law_related_query(query):
            logger.warning(f"Query '{query}' is not law-related")
            return JSONResponse({
                "status": "invalid_query",
                "message": "Your query does not appear to be related to law. Please try a more specific legal query (e.g., case laws, statutes, legal terms).",
                "query": query,
                "from_cache": False
            }, status_code=400)
        
        expanded_query = expand_query(query)
        cached_result = find_similar_query(expanded_query)
        if cached_result:
            logger.info(f"Returning cached result for similar query: {cached_result['cached_query']}")
            result_data = cached_result["results"]
            result_data["from_cache"] = True
            result_data["cached_query"] = cached_result["cached_query"]
            result_data["similarity"] = cached_result["similarity"]
            result_data["timestamp"] = datetime.now().isoformat()
            return JSONResponse(result_data)
        
        # Distinguish explicit constraint requests in query from casual words
        # e.g., "in 2005", "year 2005", "dated 2005", "(2005)", "Allahabad High Court", "in Delhi"
        explicit_year_match = re.search(r'\b(?:in|year|dated|from|of)\s+((?:19|20)\d{2})\b|\(((?:19|20)\d{2})\)', query, re.IGNORECASE)
        query_year = (explicit_year_match.group(1) or explicit_year_match.group(2)) if explicit_year_match else None
        
        # Explicit jurisdiction or court or state
        court_keywords = ['delhi', 'allahabad', 'bombay', 'calcutta', 'madras', 'karnataka', 'supreme court', 'high court', 'uttar pradesh']
        query_location = next((kw for kw in court_keywords if re.search(r'\b' + re.escape(kw) + r'\b', query.lower())), None)
        logger.info(f"Extracted explicit constraints -> year: {query_year}, jurisdiction: {query_location}")
        
        local_results = semantic_search(expanded_query)
        # Retain local matches with reasonable semantic relevance
        filtered_local = [r for r in local_results if r["confidence"] >= 40]
        logger.info(f"Local results: {len(filtered_local)} after relevance check")
        
        external_results = search_external_sources(expanded_query)
        logger.info(f"External results: {len(external_results)} before filtering")
        
        verified_external = []
        fallback_external = []
        for result in external_results:
            text = f"{result.get('title', '')} {result.get('snippet', '')} {result.get('court', '')} {result.get('year', '')} {json.dumps(result.get('analysis', ''))}".lower()
            year_matches = (not query_year) or (query_year in text)
            location_matches = (not query_location) or (query_location in text)
            
            if year_matches and location_matches:
                result["constraint_verified"] = True
                verified_external.append(result)
            else:
                # Mark as unverified fallback candidate with reduced confidence
                result["constraint_verified"] = False
                result["confidence"] = max(10.0, result.get("confidence", 50.0) * 0.6)
                fallback_external.append(result)
        
        # Present verified matches first, followed by clearly identified fallback candidates
        filtered_external = verified_external + fallback_external
        logger.info(f"External results: {len(verified_external)} verified, {len(fallback_external)} fallback")
        
        results = filtered_local + filtered_external
        if results:
            results = sorted(results, key=lambda x: x["confidence"], reverse=True)
            logger.info(f"Returning {len(results)} total results")
            result_data = {
                "status": "success",
                "source": "mixed",
                "results": results[:10],
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "from_cache": False
            }
            cache_query_result(expanded_query, result_data)

            # ── Log for real-time evaluation ──────────────────────────────
            _contexts = [
                f"{r.get('title','')} {r.get('snippet','')}".strip()
                for r in results[:5]
            ]
            _response_summary = " | ".join(
                r.get("title", "") for r in results[:3]
            )
            _log_research_event(
                module="research",
                user_input=query,
                response=_response_summary,
                contexts=_contexts,
                meta={"n_results": len(results), "source": "mixed"}
            )

            return JSONResponse(result_data)
        
        logger.warning(f"No results found for query: {query}")
        return JSONResponse({
            "status": "not_found",
            "message": "No relevant results found in local database or external sources",
            "query": query,
            "from_cache": False
        }, status_code=404)
    except Exception as e:
        logger.error(f"Error in search_legal_query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze/legal")
async def analyze_legal_document(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """Main endpoint for legal document analysis."""
    global last_save_time
    
    text = await extract_text(file)
    if text.startswith("Error"):
        raise HTTPException(status_code=400, detail=text)
    
    file_hash = hashlib.md5(text.encode()).hexdigest()
    similar_hash = find_similar_document(text)
    
    if similar_hash:
        logger.info(f"Document similar to existing document with hash {similar_hash}")
        return JSONResponse({
            "status": "already_exists",
            "message": "This document appears to be already processed.",
            "filename": file.filename,
            "text_length": len(text),
            "analysis": vector_metadata[similar_hash]["analysis"],
            "file_hash": similar_hash,
            "original_filename": vector_metadata[similar_hash]["filename"]
        })
    
    # Process only the first 10,000 characters for faster analysis
    analysis = query_llm("Analyze this legal document", text[:10000], source="document")
    
    try:
        result = json.loads(analysis)
        save_to_vector_db(file_hash, file.filename, text, result, source="document")
        
        # Check if we need to save to disk
        current_time = datetime.now()
        if (current_time - last_save_time).total_seconds() > SAVE_INTERVAL_SECONDS:
            background_tasks.add_task(background_save_data)
            last_save_time = current_time
        
        return JSONResponse({
            "status": "success",
            "filename": file.filename,
            "text_length": len(text),
            "analysis": result,
            "file_hash": file_hash
        })
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse analysis results")

@app.get("/api/history")
async def get_history():
    """Get all historical documents and webpages from vector DB."""
    try:
        history = []
        remarks = load_remarks()
        for file_hash, meta in vector_metadata.items():
            history.append({
                "file_hash": file_hash,
                "filename": meta["filename"],
                "timestamp": meta["timestamp"],
                "summary": meta["analysis"].get("summary", "No summary available"),
                "source": meta.get("source", "document"),
                "url": meta.get("url", None),
                "remark": remarks.get(file_hash, {}).get("remark", None)
            })
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        return JSONResponse({"history": history})
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/document/{file_hash}")
async def get_document(file_hash: str):
    """Get a specific document or webpage from vector DB."""
    try:
        if file_hash not in vector_metadata:
            raise HTTPException(status_code=404, detail="Document not found")
        remarks = load_remarks()
        return JSONResponse({
            "filename": vector_metadata[file_hash]["filename"],
            "text": vector_metadata[file_hash]["text"],
            "analysis": vector_metadata[file_hash]["analysis"],
            "timestamp": vector_metadata[file_hash]["timestamp"],
            "source": vector_metadata[file_hash].get("source", "document"),
            "url": vector_metadata[file_hash].get("url", None),
            "remark": remarks.get(file_hash, {}).get("remark", None)
        })
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/documents')
async def get_documents():
    """Get list of all analyzed documents"""
    try:
        documents = []
        remarks = load_remarks()
        
        for file_hash, meta in sorted(vector_metadata.items(), 
                                      key=lambda x: x[1].get("timestamp", ""), reverse=True):
            documents.append({
                "id": file_hash,
                "file_hash": file_hash,
                "title": meta.get("filename", "Unknown"),
                "filename": meta.get("filename", "Unknown"),
                "analyzed_at": meta.get("timestamp", ""),
                "summary": meta.get("analysis", {}).get("summary", "No summary")[:200],
                "source": meta.get("source", "document"),
                "url": meta.get("url"),
                "remark": remarks.get(file_hash, {}).get("remark")
            })
        
        return JSONResponse({
            "success": True,
            "documents": documents,
            "total": len(documents)
        })
    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e),
            "documents": []
        }, status_code=500)

@app.get('/api/history')
async def get_history():
    """Get search/analysis history"""
    try:
        history = []
        remarks = load_remarks()
        
        for file_hash, meta in sorted(vector_metadata.items(), 
                                      key=lambda x: x[1].get("timestamp", ""), reverse=True):
            history.append({
                "file_hash": file_hash,
                "filename": meta.get("filename", "Unknown"),
                "timestamp": meta.get("timestamp", ""),
                "summary": meta.get("analysis", {}).get("summary", "No summary")[:200],
                "source": meta.get("source", "document"),
                "url": meta.get("url"),
                "remark": remarks.get(file_hash, {}).get("remark")
            })
        
        return JSONResponse({
            "success": True,
            "history": history,
            "total": len(history)
        })
    except Exception as e:
        logger.error(f"History error: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e),
            "history": []
        }, status_code=500)

@app.delete('/api/document/{file_hash}')
async def delete_document(file_hash: str):
    """Delete a document"""
    try:
        if file_hash not in vector_metadata:
            raise HTTPException(status_code=404, detail="Document not found")
        
        del vector_metadata[file_hash]
        save_vector_metadata()
        
        remarks = load_remarks()
        if file_hash in remarks:
            del remarks[file_hash]
            save_remarks(remarks)
        
        return JSONResponse({"status": "success", "message": "Document deleted successfully"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Research Backend starting on port 8001...")
    uvicorn.run("rbackend:app", host="0.0.0.0", port=8001, reload=True)