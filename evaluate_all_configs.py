import os
import json
import sys
import copy
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path("d:/Multiple Projects/Legal_System-main/evaluation")))
from config import JUDGE_MODEL
import ragas
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
from ragas.metrics import Faithfulness, ResponseRelevancy, LLMContextPrecisionWithReference, ContextRecall
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI

QA_PAIRS = [
    {"q": "What was the period in dispute regarding the wastage of security holograms?", "a": "April, 2001 to October, 2001"},
    {"q": "Between which dates did the respondents verify the holograms?", "a": "15.7.2004 to 20.7.2004"},
    {"q": "How many missing holograms were found for plain country liquor (200 ml.)?", "a": "51,133"},
    {"q": "What was the excise duty per 200 ml plain liquor?", "a": "Rs. 7.20"},
    {"q": "How much excise duty was demanded for missing plain liquor holograms?", "a": "Rs. 3,68,157.60"},
    {"q": "How many missing holograms were found for specified country liquor?", "a": "51,634"},
    {"q": "What was the excise duty per 200 ml specified country liquor?", "a": "Rs. 12"},
    {"q": "What was the total excise duty demanded on plain and specified country liquor?", "a": "Rs. 9,87,765.60"},
    {"q": "According to the petitioner, what was the actual wastage percentage in 2003-04?", "a": "0.00%"},
    {"q": "Did the wastage of holograms decrease when affixed manually instead of by machine?", "a": "Yes, it came to zero level"},
    {"q": "Which entry of List-I of the Seventh Schedule covers liquor?", "a": "Entry 84 of List-I"},
    {"q": "Which entry of List-II authorizes the State Government to impose excise duty on liquor?", "a": "Entry 51 of List-II"},
    {"q": "Which section provides that the Excise Commissioner can frame rules and regulate payment of excise duty?", "a": "Section 29"},
    {"q": "Why are holograms affixed on bottles and pouches?", "a": "To rule out the possibility of spurious liquor being sold in the market by unauthorised persons"},
    {"q": "Is a hologram considered an excisable article?", "a": "No, it cannot be deemed an excisable article"},
    {"q": "What was the decision in Simbhaoli Industry (P.) Ltd. v. State of U.P. regarding pipeline wastage?", "a": "Excise duty could not be charged on pipeline wastage"},
    {"q": "In which section is it mentioned that excise duty can only be levied by notification?", "a": "Section 77"},
    {"q": "Can excise duty be demanded based on circulars issued by the Excise Commissioner on unaccounted holograms?", "a": "No, in the absence of a notification, it cannot be levied"},
    {"q": "Does the availability of an alternative remedy under Section 11 bar the maintainability of a writ petition if the order is without jurisdiction?", "a": "No, alternative remedy is not a bar"},
    {"q": "What was the final direction regarding the excise duty paid on missing holograms by the petitioners?", "a": "It shall be refunded to them within a period of three months"}
]

CASE_ID = "c493e7bf-2026-421a-8cda-987129cd12a2"

# Load DB
with open('d:/Multiple Projects/Legal_System-main/Legal_QA/legal-qa-system/backend/cases_metadata.json', encoding='utf-8') as f:
    db = json.load(f)

chunks = db['chunks']
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
q_embeddings = model.encode([p['q'] for p in QA_PAIRS])
c_embeddings = model.encode([c['text'] for c in chunks])

configs = [
    {"name": "Config_A", "thresh": 0.35, "top_k": 10, "bypass": True},
    {"name": "Config_B", "thresh": 0.55, "top_k": 5, "bypass": False},
    {"name": "Config_C", "thresh": 0.40, "top_k": 20, "bypass": False}
]

def generate_answer_from_chunks(question, retrieved_chunks):
    if not retrieved_chunks:
        return "I could not find any relevant information in the uploaded document to answer your question."
    
    llm = ChatOpenAI(model=JUDGE_MODEL, temperature=0.0)
    context_text = "\n\n".join([f"Source: {c['case_name']}\nChunk: {c['chunk']}" for c in retrieved_chunks])
    prompt = f"""You are a legal assistant. Answer the user's question accurately using ONLY the provided case chunks.
If the context does not contain the answer, reply exactly with: "I could not find any relevant information in the uploaded document to answer your question."
Provide brief legal reasoning.

Context:
{context_text}

Question: {question}

Return ONLY a valid JSON object:
{{
  "conclusion": "The direct answer",
  "legal_reasoning": "Brief explanation",
  "confidence_score": 0.95
}}
"""
    try:
        from langchain_core.messages import HumanMessage
        raw = llm.invoke([HumanMessage(content=prompt)]).content
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        if "I could not find" in raw:
            return "I could not find any relevant information in the uploaded document to answer your question."
        if not raw.startswith("{"):
            import re
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                raw = match.group(0)
            else:
                return raw
        ans = json.loads(raw)
        return ans.get("conclusion", "")
    except Exception as e:
        print("Exception during generation:", e)
        return "Error"

for conf in configs:
    print(f"\n==========================================")
    print(f"EVALUATING: {conf['name']} (thresh={conf['thresh']}, top_k={conf['top_k']}, bypass={conf['bypass']})")
    
    results = []
    top1 = 0; empty = 0; total_chunks = 0
    
    for i, pair in enumerate(QA_PAIRS):
        q = pair['q']
        q_emb = q_embeddings[i]
        distances = np.sum((c_embeddings - q_emb) ** 2, axis=1)
        top_indices = np.argsort(distances)[:conf['top_k']]
        
        retrieved = []
        for idx in top_indices:
            dist = distances[idx]
            sim = 1 / (1 + dist)
            c = chunks[idx]
            
            if conf['bypass']:
                if sim > conf['thresh'] or c.get('case_id') == CASE_ID:
                    retrieved.append({"chunk": c['text'], "case_name": c.get('case_name'), "similarity": sim})
            else:
                if c.get('case_id') == CASE_ID and sim > conf['thresh']:
                    retrieved.append({"chunk": c['text'], "case_name": c.get('case_name'), "similarity": sim})
                    
        retrieved = sorted(retrieved, key=lambda x: x['similarity'], reverse=True)
        retrieved = retrieved[:conf['top_k']]
        
        if len(retrieved) == 0: empty += 1
        if len(retrieved) >= 1: top1 += 1
        total_chunks += len(retrieved)
        
        ans = generate_answer_from_chunks(q, retrieved)
        
        results.append({
            "question": q,
            "reference": pair["a"],
            "response": ans,
            "retrieved_contexts": [c["chunk"] for c in retrieved] if retrieved else ["No chunks retrieved"],
            "num_chunks": len(retrieved)
        })
        
    print(f"Top-1 hit rate: {top1/len(QA_PAIRS)*100}%")
    print(f"Empty retrieval rate: {empty/len(QA_PAIRS)*100}%")
    print(f"Avg chunks: {total_chunks/len(QA_PAIRS)}")
    
    # RAGAS EVAL
    samples = []
    for d in results:
        samples.append(SingleTurnSample(
            user_input=d["question"],
            response=d["response"],
            retrieved_contexts=d["retrieved_contexts"],
            reference=d["reference"]
        ))
    dataset = EvaluationDataset(samples=samples)
    metrics = [Faithfulness(), ResponseRelevancy(), LLMContextPrecisionWithReference(), ContextRecall()]
    llm = LangchainLLMWrapper(ChatOpenAI(model=JUDGE_MODEL, temperature=0.0))
    from ragas import evaluate
    
    # We raise_exceptions=False so that a single failed item doesn't kill the whole config run
    res = evaluate(dataset, metrics=metrics, llm=llm, raise_exceptions=False)
    df = res.to_pandas()
    
    # Add number of chunks
    df['num_chunks'] = [d['num_chunks'] for d in results]
    
    print("\n--- RESULTS FOR", conf['name'], "---")
    successful = df['faithfulness'].notna().sum()
    failed = len(df) - successful
    print(f"Successful evaluations: {successful}/{len(df)} ({(successful/len(df))*100:.1f}%)")
    print(f"Failed evaluations: {failed}")
    
    print("\nMetrics (Mean of successful):")
    for m in metrics:
        name = m.name
        if name in df.columns:
            print(f"{name}: {df[name].mean():.4f}")
            
    df.to_csv(f"eval_results_{conf['name']}.csv", index=False)
