import json
with open('qa_store.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    print('Recent questions:')
    for q in data.get('questions', [])[-10:]:
        print(f"{q.get('asked_at')} - {q.get('question_text')}")
