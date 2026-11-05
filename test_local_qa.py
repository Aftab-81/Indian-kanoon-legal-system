import requests
import json

API_URL = "http://localhost:8002/api/ask"

queries = [
    "Can the government charge excise duty if holograms are wasted and the distillery is liable?"
]

def test_api():
    for q in queries:
        payload = {
            "question": q,
            "source": "document",
            "case_id": "c493e7bf-2026-421a-8cda-987129cd12a2" 
        }
        res = requests.post(API_URL, json=payload, timeout=120)
        data = res.json()
        print(f"QUESTION: {q}")
        chunks = data.get('retrieved_chunks', [])
        for i, chunk in enumerate(chunks, 1):
            print(f"RETRIEVED CHUNK {i}")
            print(f"similarity: {chunk.get('similarity')}")
            print(f"text snippet: {chunk.get('chunk', '')[:100]}...\n")
        print(f"GENERATED ANSWER:\n{data.get('conclusion')}\n")

if __name__ == "__main__":
    test_api()
