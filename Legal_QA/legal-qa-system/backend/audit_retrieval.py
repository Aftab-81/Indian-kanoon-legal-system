import os
import sys
import json
import faiss
from sentence_transformers import SentenceTransformer

# Load environment
sys.path.append(os.path.abspath('.'))
from app import load_cases_data, get_embedding_model

queries = [
    "What is the procedure for arrest under Section 41A CrPC?",
    "What is the punishment for cheating under IPC?",
    "Can a confession made to a police officer be proved against the accused?",
    "What is the doctrine of basic structure in Indian Constitution?",
    "What are the essentials of a valid contract under Indian Contract Act?",
    "conditions for anticipatory bail",
    "guidelines for maintenance under Section 125 CrPC",
    "Supreme court cases on right to privacy",
    "dowry death under Section 304B",
    "medical negligence exceptions",
    "what is ratio decidendi",
    "evidential value of FIR",
    "dying declaration admissibility",
    "writ of habeas corpus grounds",
    "public interest litigation locus standi",
    "defamation exceptions under IPC",
    "specific performance of contract",
    "consumer protection act pecuniary jurisdiction",
    "arbitration agreement essentials",
    "Hindu marriage act divorce grounds"
]

def load_index():
    index = faiss.read_index("legal_vectors.faiss")
    cases_data = load_cases_data()
    return index, cases_data.get("chunks", [])

def audit():
    index, chunks_list = load_index()
    if index is None or index.ntotal == 0 or not chunks_list:
        print("Empty vector DB")
        return
    
    model = get_embedding_model()
    embeddings = model.encode(queries).astype('float32')
    
    configs = [
        ("A. Current config (thresh=0.35, bypass=True, top_k=10)", 0.35, True, 10),
        ("B. Current + fixed case bypass (thresh=0.35, bypass=False, top_k=10)", 0.35, False, 10),
        ("C. Higher threshold (thresh=0.55, bypass=False, top_k=10)", 0.55, False, 10),
        ("D. Higher threshold + reasonable top_k (thresh=0.55, bypass=False, top_k=5)", 0.55, False, 5)
    ]
    
    print("PHASE 1 & 4 - RETRIEVAL AUDIT\n")
    
    for name, threshold, bypass, top_k in configs:
        print(f"--- {name} ---")
        empty_count = 0
        total_chunks = 0
        
        for i, q in enumerate(queries):
            distances, indices = index.search(embeddings[i:i+1], index.ntotal)
            
            retrieved = []
            for idx, dist in zip(indices[0], distances[0]):
                if 0 <= idx < len(chunks_list):
                    sim = 1 / (1 + float(dist))
                    # Note: in real system, case_id bypass means "or case_id". Here we simulate case_id being passed for bypass=True
                    if bypass or sim > threshold:
                        retrieved.append(sim)
                        if len(retrieved) >= top_k:
                            break
                            
            if not retrieved:
                empty_count += 1
            total_chunks += len(retrieved)
            
        print(f"Empty Retrieval Rate: {empty_count/len(queries)*100:.1f}%")
        print(f"Avg Chunks per query: {total_chunks/len(queries):.2f}\n")

if __name__ == '__main__':
    audit()
