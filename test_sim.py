import json
from sentence_transformers import SentenceTransformer
import numpy as np

# Load model
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')

# Load chunks
with open('d:/Multiple Projects/Legal_System-main/Legal_QA/legal-qa-system/backend/cases_metadata.json', encoding='utf-8') as f:
    data = json.load(f)
    
saraya_chunks = [c['text'] for c in data['chunks'] if 'Saraya' in c.get('case_name', '')]

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

queries = [p['q'] for p in QA_PAIRS]
q_embeddings = model.encode(queries)
c_embeddings = model.encode(saraya_chunks)

for i, q in enumerate(queries):
    q_emb = q_embeddings[i]
    # L2 distance squared
    distances = np.sum((c_embeddings - q_emb) ** 2, axis=1)
    similarities = 1 / (1 + distances)
    
    best_idx = np.argmax(similarities)
    best_sim = similarities[best_idx]
    
    print(f"Q: {q}")
    print(f"Max Similarity: {best_sim:.4f}")
    
