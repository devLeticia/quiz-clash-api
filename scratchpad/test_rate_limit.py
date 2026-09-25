import httpx

url = "http://127.0.0.1:8000/quiz/from-text"
payload = {"text": "Python is a programming language.", "num_questions": 3}

for i in range(1, 13):
    response = httpx.post(url, json=payload, timeout=30.0)
    print(f"Request {i}: {response.status_code}")
