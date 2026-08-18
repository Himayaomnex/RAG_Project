import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

print(f"Loaded GROQ_API_KEY: {'Found' if api_key else 'Missing'}")
print(f"Model: {model}")

if api_key:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are the Enterprise RAG Assistant."},
            {"role": "user", "content": "Say 'Groq API is connected successfully!' in 1 line."}
        ],
        "temperature": 0.1
    }
    try:
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            print("Response:", resp.json()["choices"][0]["message"]["content"])
        else:
            print("Error Status:", resp.status_code, resp.text)
    except Exception as e:
        print("Exception:", e)
