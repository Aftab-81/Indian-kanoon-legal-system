import requests
import json

def test_legal_qa():
    print("==================================================")
    print("LEGAL QA VALIDATION")
    print("==================================================")
    questions = [
        "What is the procedure for arrest under Section 41A CrPC?",
        "What is the punishment for cheating under IPC?",
        "Can a confession made to a police officer be proved against the accused?",
        "What is the doctrine of basic structure in Indian Constitution?",
        "What are the essentials of a valid contract under Indian Contract Act?"
    ]
    for q in questions:
        print(f"\nQUESTION: {q}")
        try:
            resp = requests.post("http://localhost:8002/api/ask", json={"question": q, "context": ""})
            data = resp.json()
            if "contexts" in data:
                for i, chunk in enumerate(data["contexts"][:3], 1):
                    print(f"RETRIEVED CHUNK {i}: {chunk[:100]}...")
            print(f"GENERATED ANSWER: {data.get('answer', '')[:150]}...")
        except Exception as e:
            print(f"Error: {e}")

def test_research():
    print("\n==================================================")
    print("DOCUMENT RESEARCH VALIDATION")
    print("==================================================")
    queries = [
        "precedents on anticipatory bail in dowry cases",
        "guidelines for maintenance under Section 125 CrPC",
        "Supreme court cases on right to privacy"
    ]
    for q in queries:
        print(f"\nQUERY: {q}")
        try:
            resp = requests.post("http://localhost:8001/api/search/query", data={"query": q})
            data = resp.json()
            if "results" in data:
                for i, res in enumerate(data["results"][:3], 1):
                    print(f"RETRIEVED DOCUMENT {i}: Title: {res.get('title')}")
                    print(f"Snippet: {res.get('snippet', '')[:100]}...")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    test_legal_qa()
    test_research()
