from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
# Handle both old and new versions of openai package
try:
    from openai import OpenAI
except ImportError:
    # Fallback for older versions (pre-1.0)
    import openai
    # Create a compatibility wrapper
    class OpenAI:
        def __init__(self, api_key=None):
            if api_key:
                openai.api_key = api_key
            self.chat = self
            self.completions = self
        
        def create(self, model, messages, **kwargs):
            return openai.ChatCompletion.create(
                model=model,
                messages=messages,
                **kwargs
            )
import pdfplumber
# Handle docx import - ensure correct package is installed
try:
    import docx
except ModuleNotFoundError as e:
    if "exceptions" in str(e):
        raise ImportError(
            "Wrong 'docx' package installed. Please run:\n"
            "  pip uninstall docx\n"
            "  pip install python-docx"
        ) from e
    raise
import io
import os
import json
import asyncio
import concurrent.futures
from dotenv import load_dotenv
import uvicorn
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import re
# Handle faiss import - ensure correct package is installed
try:
    import faiss
except ModuleNotFoundError:
    raise ImportError(
        "FAISS package not installed. Please run:\n"
        "  pip install faiss-cpu\n"
        "Or if you have CUDA GPU:\n"
        "  pip install faiss-gpu"
    )
import numpy as np
from datetime import datetime
import logging
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from fastapi.background import BackgroundTasks
import threading
from threading import Event

from logger_setup import get_logger

# Configure logging
logger = get_logger(__name__)

# Load environment variables
load_dotenv()

# Global state
last_save_time = datetime.now()
SAVE_INTERVAL_SECONDS = 60
backend_ready = False

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("🚨 OpenAI API Key is missing!")

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

# Constants
DOC_SIMILARITY_THRESHOLD = 0.9
QUERY_SIMILARITY_THRESHOLD = 0.75
IK_API_URL = "https://api.indiankanoon.org/search/"

STOPWORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her',
    'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there'
}

class RemarkRequest(BaseModel):
    file_hash: str
    remark: str

def background_save_data():
    """Background task to save vector data to disk"""
    try:
        save_vector_metadata()
        save_query_cache()
        save_faiss_index()
        logger.info("✅ Background save completed")
    except Exception as e:
        logger.error(f"❌ Error in background save: {str(e)}", exc_info=True)

def init_backend_async():
    """Initialize backend components in background thread"""
    global backend_ready, vector_metadata, query_cache, vector_index
    
    try:
        logger.info("🔄 Starting backend initialization...")
        vector_metadata = load_vector_metadata()
        query_cache = load_query_cache()
        logger.info(f"📚 Loaded {len(vector_metadata)} documents")
        load_faiss_index()
        backend_ready = True
        logger.info("✅ Backend initialization complete!")
    except Exception as e:
        logger.error(f"❌ Error during initialization: {str(e)}", exc_info=True)
        backend_ready = True

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI"""
    logger.info("🚀 FastAPI startup")
    init_thread = threading.Thread(target=init_backend_async, daemon=True)
    init_thread.start()
    yield
    logger.info("🛑 FastAPI shutdown")
    background_save_data()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Data Persistence ====================

def load_remarks() -> Dict[str, Dict[str, str]]:
    try:
        if os.path.exists(REMARKS_FILE):
            with open(REMARKS_FILE, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading remarks: {str(e)}", exc_info=True)
        return {}

def save_remarks(remarks: Dict[str, Dict[str, str]]) -> None:
    try:
        with open(REMARKS_FILE, "w") as f:
            json.dump(remarks, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving remarks: {str(e)}", exc_info=True)

def load_vector_metadata() -> Dict[str, Dict[str, Any]]:
    try:
        if os.path.exists(VECTOR_METADATA_FILE):
            with open(VECTOR_METADATA_FILE, "r") as f:
                data = json.load(f)
                for meta in data.values():
                    if 'embedding' in meta:
                        del meta['embedding']
                return data
        return {}
    except Exception as e:
        logger.error(f"Error loading vector metadata: {str(e)}", exc_info=True)
        return {}

def save_vector_metadata() -> None:
    try:
        data_to_save = {}
        for file_hash, meta in vector_metadata.items():
            meta_copy = meta.copy()
            if 'embedding' in meta_copy:
                del meta_copy['embedding']
            data_to_save[file_hash] = meta_copy
        with open(VECTOR_METADATA_FILE, "w") as f:
            json.dump(data_to_save, f, indent=2)
        logger.info(f"✅ Saved {len(data_to_save)} documents")
    except Exception as e:
        logger.error(f"Error saving vector metadata: {str(e)}", exc_info=True)

def load_query_cache() -> Dict[str, Dict[str, Any]]:
    try:
        if os.path.exists(QUERY_CACHE_FILE):
            with open(QUERY_CACHE_FILE, "r") as f:
                data = json.load(f)
                for query, cache in data.items():
                    if 'embedding' in cache:
                        del cache['embedding']
                return data
        return {}
    except Exception as e:
        logger.error(f"Error loading query cache: {str(e)}", exc_info=True)
        return {}

def save_query_cache() -> None:
    try:
        data_to_save = {}
        for query, cache in query_cache.items():
            cache_copy = cache.copy()
            if 'embedding' in cache_copy:
                del cache_copy['embedding']
            data_to_save[query] = cache_copy
        with open(QUERY_CACHE_FILE, "w") as f:
            json.dump(data_to_save, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving query cache: {str(e)}", exc_info=True)

def save_faiss_index():
    try:
        faiss.write_index(vector_index, FAISS_INDEX_FILE)
        logger.info(f"✅ Saved FAISS index")
    except Exception as e:
        logger.error(f"Error saving FAISS index: {str(e)}", exc_info=True)

def load_faiss_index():
    global vector_index, vector_metadata
    try:
        if os.path.exists(FAISS_INDEX_FILE):
            vector_index = faiss.read_index(FAISS_INDEX_FILE)
            logger.info(f"✅ Loaded FAISS index")
        else:
            vector_index = faiss.IndexFlatL2(EMBEDDING_DIM)
            logger.info("📝 Initialized new FAISS index")
        
        loaded_metadata = load_vector_metadata()
        if loaded_metadata:
            embeddings = []
            valid_hashes = []
            
            for file_hash, meta in loaded_metadata.items():
                try:
                    text_sample = meta.get('text', '')[:500]
                    if not text_sample:
                        continue
                    
                    embedding = generate_embedding(text_sample)
                    meta['embedding'] = embedding
                    loaded_metadata[file_hash] = meta
                    embeddings.append(embedding)
                    valid_hashes.append(file_hash)
                except Exception as e:
                    logger.warning(f"Could not process {file_hash}: {str(e)}")
                    continue
            
            vector_metadata = loaded_metadata
            if embeddings:
                vector_index = faiss.IndexFlatL2(EMBEDDING_DIM)
                vector_index.add(np.array(embeddings, dtype='float32'))
                logger.info(f"✅ Rebuilt FAISS with {len(embeddings)} embeddings")
        else:
            vector_metadata = {}
    except Exception as e:
        logger.error(f"Error loading FAISS: {str(e)}", exc_info=True)
        vector_index = faiss.IndexFlatL2(EMBEDDING_DIM)
        vector_metadata = {}

# ==================== Core Functions ====================

def generate_embedding(text: str) -> List[float]:
    try:
        response = client.embeddings.create(
            input=text[:2000],
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}", exc_info=True)
        return [0.0] * EMBEDDING_DIM

def query_llm(prompt: str, text: str, source: str = "document") -> str:
    try:
        truncated_text = text[:8000]
        
        legal_prompt = """Analyze this legal document and extract information in EXACTLY this JSON format:
{
    "case_laws": [{"case_name": "name", "citation": "citation", "year": "year", "court": "court", "context": "context"}],
    "statutes": [{"statute_name": "name", "section": "section", "full_reference": "reference", "context": "context"}],
    "constitutional_provisions": [{"article": "article", "subject": "subject", "full_reference": "reference", "context": "context"}],
    "international_laws": [{"name": "name", "article": "article", "full_reference": "reference", "context": "context"}],
    "legal_principles": ["principle1"],
    "summary": "Brief summary"
}"""
        
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a legal analyst."},
                {"role": "user", "content": f"{legal_prompt}\n\nText:\n{truncated_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1000
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM Error: {str(e)}", exc_info=True)
        return json.dumps({"summary": "Analysis failed", "error": str(e)})

def extract_text_from_pdf(content: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                texts = list(executor.map(lambda page: page.extract_text() or "", pdf.pages))
        return "\n".join(texts).strip()
    except Exception as e:
        return f"Error: {str(e)}"

def extract_text_from_docx(content: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(content))
        return "\n".join([para.text for para in doc.paragraphs]).strip()
    except Exception as e:
        return f"Error: {str(e)}"

async def extract_text(file: UploadFile) -> str:
    content = await file.read()
    if file.filename.endswith('.pdf'):
        return extract_text_from_pdf(content)
    elif file.filename.endswith('.docx'):
        return extract_text_from_docx(content)
    else:
        return "Error: Unsupported file type"

def scrape_webpage(url: str) -> Optional[str]:
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        for element in soup(['script', 'style', 'nav', 'footer']):
            element.decompose()
        body = soup.find('body')
        if not body:
            return None
        text = body.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:15000] if text else None
    except Exception as e:
        logger.warning(f"Scrape error: {str(e)}")
        return None

def preprocess_query_terms(query: str) -> Tuple[List[str], List[str]]:
    critical_patterns = [
        r'section\s+\d+', r'article\s+\d+', r'\d{4}\s+(?:Act|Law)',
        r'v[s]?\.', r'\b(?:19|20)\d{2}\b'
    ]
    
    critical_terms = []
    for pattern in critical_patterns:
        matches = re.finditer(pattern, query, re.IGNORECASE)
        critical_terms.extend(match.group().strip() for match in matches)
    
    critical_terms = list(set(critical_terms))
    non_critical_terms = [w.strip() for w in query.split() 
                         if len(w.strip()) > 2 and w.strip().lower() not in STOPWORDS]
    
    return critical_terms, non_critical_terms

def is_law_related_query(query: str) -> bool:
    legal_keywords = ['case', 'court', 'law', 'legal', 'statute', 'section', 
                      'article', 'constitution', 'criminal', 'civil', 'ipc', 'petition', 'rights']
    return any(keyword in query.lower() for keyword in legal_keywords)

def check_term_matches(text: str, critical_terms: List[str], non_critical_terms: List[str]) -> Tuple[bool, float]:
    text = text.lower()
    
    if not critical_terms:
        critical_score = 1.0
    else:
        critical_matches = sum(1 for term in critical_terms if term.lower() in text)
        critical_score = critical_matches / len(critical_terms) if critical_matches > 0 else 0.5
    
    if not non_critical_terms:
        non_critical_score = 1.0
    else:
        non_critical_matches = sum(1 for term in non_critical_terms if term.lower() in text)
        non_critical_score = max(0.3, non_critical_matches / len(non_critical_terms))
    
    final_score = (critical_score * 0.7) + (non_critical_score * 0.3)
    return True, final_score

def find_similar_document(text: str) -> Optional[str]:
    if vector_index.ntotal == 0:
        return None
    try:
        text_embedding = generate_embedding(text[:1000])
        query_vector = np.array([text_embedding], dtype='float32')
        k = min(3, vector_index.ntotal)
        distances, indices = vector_index.search(query_vector, k)
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(vector_metadata):
                file_hash = list(vector_metadata.keys())[idx]
                similarity = 1 - (distances[0][i] / 2)
                if similarity >= DOC_SIMILARITY_THRESHOLD:
                    return file_hash
    except Exception as e:
        logger.warning(f"Similar doc error: {str(e)}")
    return None

def save_to_vector_db(file_hash: str, filename: str, text: str, analysis: Dict[str, Any], source: str = "document", url: str = None) -> None:
    try:
        embedding = generate_embedding(text[:500])
        embedding_array = np.array([embedding], dtype='float32')
        vector_index.add(embedding_array)
        vector_metadata[file_hash] = {
            "filename": filename,
            "text": text,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat(),
            "embedding": embedding,
            "source": source,
            "url": url
        }
        logger.info(f"✅ Saved '{filename}' to vector DB")
    except Exception as e:
        logger.error(f"Save error: {str(e)}", exc_info=True)

def semantic_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    if vector_index.ntotal == 0:
        return []
    
    try:
        query_embedding = generate_embedding(query)
        query_vector = np.array([query_embedding], dtype='float32')
        k = min(k, vector_index.ntotal)
        distances, indices = vector_index.search(query_vector, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if 0 <= idx < len(vector_metadata):
                file_hash = list(vector_metadata.keys())[idx]
                meta = vector_metadata.get(file_hash)
                if meta:
                    confidence = max(0, min(100, 100 * (1 - distances[0][i])))
                    results.append({
                        "file_hash": file_hash,
                        "filename": meta.get("filename", "Unknown"),
                        "text": (meta.get("text", "")[:300] + "...") if meta.get("text") else "",
                        "analysis": meta.get("analysis", {}),
                        "confidence": float(confidence),
                        "source": meta.get("source", "document"),
                        "url": meta.get("url")
                    })
        
        return sorted(results, key=lambda x: x["confidence"], reverse=True)
    except Exception as e:
        logger.error(f"Semantic search error: {str(e)}", exc_info=True)
        return []

# ==================== API Endpoints ====================

@app.get("/api/health")
async def health_check():
    return {
        "status": "ready" if backend_ready else "initializing",
        "backend_ready": backend_ready,
        "documents": len(vector_metadata),
        "cached_queries": len(query_cache)
    }

@app.post("/api/remarks")
async def save_remark(request: RemarkRequest):
    try:
        remarks = load_remarks()
        remarks[request.file_hash] = {
            "remark": request.remark,
            "timestamp": datetime.now().isoformat()
        }
        save_remarks(remarks)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze/legal")
async def analyze_legal_document(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    global last_save_time
    
    try:
        text = await extract_text(file)
        if text.startswith("Error"):
            raise HTTPException(status_code=400, detail=text)
        
        file_hash = hashlib.md5(text.encode()).hexdigest()
        similar_hash = find_similar_document(text)
        
        if similar_hash and similar_hash in vector_metadata:
            return JSONResponse({
                "status": "already_exists",
                "filename": file.filename,
                "analysis": vector_metadata[similar_hash]["analysis"],
                "file_hash": similar_hash
            })
        
        analysis_text = query_llm("Analyze", text, source="document")
        
        try:
            analysis = json.loads(analysis_text)
        except:
            analysis = {"summary": "Analysis completed", "case_laws": [], "statutes": []}
        
        save_to_vector_db(file_hash, file.filename, text, analysis, source="document")
        
        current_time = datetime.now()
        if (current_time - last_save_time).total_seconds() > SAVE_INTERVAL_SECONDS:
            background_tasks.add_task(background_save_data)
            last_save_time = current_time
        
        return JSONResponse({
            "status": "success",
            "filename": file.filename,
            "text_length": len(text),
            "analysis": analysis,
            "file_hash": file_hash
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analyze error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search/query")
async def search_legal_query(query: str = Form(...)):
    try:
        logger.info(f"🔍 Query: {query}")
        
        if not is_law_related_query(query):
            return JSONResponse({
                "status": "success",
                "source": "mixed",
                "results": [],
                "query": query
            })
        
        results = semantic_search(query)
        
        return JSONResponse({
            "status": "success",
            "source": "mixed",
            "results": results,
            "query": query,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents")
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

@app.get("/api/history")
async def get_history():
    """Get search/analysis history - same as documents for now"""
    try:
        history = []
        remarks = load_remarks()
        
        for file_hash, meta in sorted(vector_metadata.items(), 
                                      key=lambda x: x[1].get("timestamp", ""), reverse=True):
            history.append({
                "file_hash": file_hash,
                "filename": meta.get("filename", "Unknown"),
                "timestamp": meta.get("timestamp", ""),
                "summary": meta.get("analysis", {}).get("summary", "No summary"),
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

@app.get("/api/document/{file_hash}")
async def get_document(file_hash: str):
    try:
        if file_hash not in vector_metadata:
            raise HTTPException(status_code=404, detail="Not found")
        remarks = load_remarks()
        return JSONResponse({
            "filename": vector_metadata[file_hash]["filename"],
            "text": vector_metadata[file_hash]["text"],
            "analysis": vector_metadata[file_hash]["analysis"],
            "timestamp": vector_metadata[file_hash]["timestamp"],
            "source": vector_metadata[file_hash].get("source", "document"),
            "url": vector_metadata[file_hash].get("url"),
            "remark": remarks.get(file_hash, {}).get("remark")
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/document/{file_hash}")
async def delete_document(file_hash: str):
    try:
        if file_hash not in vector_metadata:
            raise HTTPException(status_code=404, detail="Not found")
        
        del vector_metadata[file_hash]
        save_vector_metadata()
        
        remarks = load_remarks()
        if file_hash in remarks:
            del remarks[file_hash]
            save_remarks(remarks)
        
        return JSONResponse({"status": "success"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Research Backend API Server")
    print("=" * 60)
    print(f"✅ Starting on http://0.0.0.0:8001")
    print("=" * 60 + "\n")
    uvicorn.run("backend:app", host="0.0.0.0", port=8001, reload=True)