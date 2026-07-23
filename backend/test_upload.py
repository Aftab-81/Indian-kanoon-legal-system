import requests

url = "http://localhost:8000/api/upload"
with open("test_openai.py", "rb") as f:
    files = {"file": ("test_openai.pdf", f)}
    response = requests.post(url, files=files)
print(response.status_code)
print(response.text)
