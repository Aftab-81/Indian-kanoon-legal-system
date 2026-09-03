import json
with open('qa_store.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    print('Searching for recent answers...')
    for ans in data.get('answers', [])[-10:]:
        print('----------------')
        print(f"Question ID: {ans.get('question_id')}")
        print(f"Conclusion: {ans.get('conclusion')}")
        print(f"Legal Reasoning: {ans.get('legal_reasoning')}")
