import os
import sys
sys.path.append(os.path.abspath('Legal_QA/legal-qa-system/backend'))
from app import load_vector_db, get_embedding_model

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

def audit():
    index, cases_data = load_vector_db()
    chunks_list = cases_data.get("chunks", [])
    if index is None or index.ntotal == 0 or not chunks_list:
        print("Empty vector DB")
        return
    
    model = get_embedding_model()
    embeddings = model.encode(queries).astype('float32')
    
    # Configuration A: threshold=0.35, top-k=10
    # Configuration B: threshold=0.35, top-k=20
    # Configuration C: threshold=0.25, top-k=10
    # Configuration D: threshold=0.25, top-k=20
    
    configs = [
        ("Config A (curr)", 0.35, 10),
        ("Config B (topk)", 0.35, 20),
        ("Config C (thresh)", 0.25, 10),
        ("Config D (combo)", 0.25, 20)
    ]
    
    for name, threshold, top_k in configs:
        print(f"\n--- {name} (Threshold: {threshold}, Top-K: {top_k}) ---")
        empty_count = 0
        total_chunks = 0
        for i, q in enumerate(queries):
            distances, indices = index.search(embeddings[i:i+1], top_k)
            retrieved = []
            for idx, dist in zip(indices[0], distances[0]):
                if 0 <= idx < len(chunks_list):
                    sim = 1 / (1 + float(dist))
                    if sim > threshold:
                        retrieved.append(sim)
            if not retrieved:
                empty_count += 1
            total_chunks += len(retrieved)
            
        print(f"Empty Retrieval Rate: {empty_count/len(queries)*100:.1f}%")
        print(f"Avg Chunks per query: {total_chunks/len(queries):.2f}")

    print("\n--- TOP 5 CHUNKS FOR FIRST 3 QUERIES (Raw Scores) ---")
    for i, q in enumerate(queries[:3]):
        print(f"\nQUERY: {q}")
        distances, indices = index.search(embeddings[i:i+1], 5)
        for rank, (idx, dist) in enumerate(zip(indices[0], distances[0]), 1):
            if 0 <= idx < len(chunks_list):
                sim = 1 / (1 + float(dist))
                chunk = chunks_list[idx]
                print(f"{rank}. SIMILARITY: {sim:.3f} | SOURCE: {chunk.get('case_name')}")
                print(f"TEXT: {chunk.get('text')[:100]}...")

if __name__ == '__main__':
    audit()
