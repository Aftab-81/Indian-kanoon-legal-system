import json
from sentence_transformers import SentenceTransformer
import faiss

# Load metadata
with open('d:/Multiple Projects/Legal_System-main/Legal_QA/legal-qa-system/backend/cases_metadata.json', 'r', encoding='utf-8') as f:
    cases_data = json.load(f)

chunks = cases_data.get('chunks', [])
print(f"Total metadata entries (chunks): {len(chunks)}")
if chunks:
    print(f"First chunk case_id: {chunks[0].get('case_id')}")
    print(f"First chunk length: {len(chunks[0].get('text', ''))}")
    print(f"First chunk (first 300 chars): {chunks[0].get('text', '')[:300]}")
    
# Load FAISS
try:
    index = faiss.read_index('d:/Multiple Projects/Legal_System-main/Legal_QA/legal-qa-system/backend/legal_vectors.faiss')
    print(f"Total FAISS vectors: {index.ntotal}")
except Exception as e:
    print(f"FAISS error: {e}")
