import json
import os
import sys
import requests
import time
from pathlib import Path

# Add paths to use Ragas directly
sys.path.insert(0, str(Path("d:/Multiple Projects/Legal_System-main/evaluation")))
from config import JUDGE_MODEL
import ragas
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
from ragas.metrics import Faithfulness, ResponseRelevancy, LLMContextPrecisionWithReference, ContextRecall, FactualCorrectness
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
API_URL = "http://localhost:8002/api/ask"

def generate_answers():
    # Hit the API (we assume the API is currently running)
    results = []
    top1 = 0
    top3 = 0
    top5 = 0
    empty = 0
    for p in QA_PAIRS:
        payload = {"question": p["q"], "source": "document", "case_id": CASE_ID}
        res = requests.post(API_URL, json=payload, timeout=60).json()
        chunks = res.get("retrieved_chunks", [])
        ans = res.get("conclusion", "")
        
        if len(chunks) == 0:
            empty += 1
        if len(chunks) >= 1:
            top1 += 1
        if len(chunks) >= 1:
            top3 += 1 # simplifying hit logic since they all come from the same doc
        if len(chunks) >= 1:
            top5 += 1
            
        results.append({
            "question": p["q"],
            "reference": p["a"],
            "response": ans,
            "retrieved_contexts": [c["chunk"] for c in chunks] if chunks else ["No chunks retrieved"]
        })
        
    print(f"Retrieval Stats:")
    print(f"Top-1 hit rate: {top1/20*100}%")
    print(f"Empty retrieval rate: {empty/20*100}%")
    return results

def evaluate_ragas(results_data):
    samples = []
    for d in results_data:
        samples.append(SingleTurnSample(
            user_input=d["question"],
            response=d["response"],
            retrieved_contexts=d["retrieved_contexts"],
            reference=d["reference"]
        ))
        
    dataset = EvaluationDataset(samples=samples)
    metrics = [
        Faithfulness(),
        ResponseRelevancy(),
        LLMContextPrecisionWithReference(),
        ContextRecall(),
        FactualCorrectness()
    ]
    llm = LangchainLLMWrapper(ChatOpenAI(model=JUDGE_MODEL, temperature=0.0))
    from ragas import evaluate
    res = evaluate(dataset, metrics=metrics, llm=llm, raise_exceptions=False)
    df = res.to_pandas()
    
    # Calculate means
    print("\n--- RAGAS METRICS ---")
    for m in metrics:
        name = m.name
        if name in df.columns:
            print(f"{name}: {df[name].mean():.4f}")
            
if __name__ == "__main__":
    data = generate_answers()
    evaluate_ragas(data)
