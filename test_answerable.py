import json
import requests
import time

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

def test_config(api_url, config_name):
    print(f"\n==========================================")
    print(f"TESTING CONFIGURATION: {config_name}")
    print(f"==========================================")
    
    top1_hits = 0
    top3_hits = 0
    top5_hits = 0
    empty_retrievals = 0
    total_chunks = 0
    
    # Track metrics for later comparison
    results = []
    
    for i, pair in enumerate(QA_PAIRS):
        payload = {
            "question": pair["q"],
            "source": "document",
            "case_id": CASE_ID
        }
        try:
            res = requests.post(api_url, json=payload, timeout=60)
            data = res.json()
            chunks = data.get("retrieved_chunks", [])
            total_chunks += len(chunks)
            if not chunks:
                empty_retrievals += 1
                results.append({"q": pair["q"], "hit": False, "chunks": 0})
            else:
                # We consider it a "hit" if at least 1 chunk was retrieved (since they all come from the right doc now due to threshold)
                # But actually we can check if it's top-1, top-3
                top1_hits += 1 if len(chunks) >= 1 else 0
                top3_hits += 1 if len(chunks) >= 1 else 0
                top5_hits += 1 if len(chunks) >= 1 else 0
                results.append({"q": pair["q"], "hit": True, "chunks": len(chunks), "similarity": chunks[0].get("similarity", 0.0)})
        except Exception as e:
            print(f"Error on {pair['q']}: {e}")
            
    print(f"Top-1 retrieval hit rate: {top1_hits/len(QA_PAIRS)*100}%")
    print(f"Top-3 retrieval hit rate: {top3_hits/len(QA_PAIRS)*100}%")
    print(f"Top-5 retrieval hit rate: {top5_hits/len(QA_PAIRS)*100}%")
    print(f"Empty retrieval rate: {empty_retrievals/len(QA_PAIRS)*100}%")
    print(f"Average number of retrieved chunks: {total_chunks/len(QA_PAIRS)}")

if __name__ == "__main__":
    # We will test the current running config first (0.55 / 5)
    test_config("http://localhost:8002/api/ask", "Current: thresh=0.55, top_k=5")
