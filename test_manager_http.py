import requests
import json
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

url = "http://127.0.0.1:8000/api/v1/manager"
payload = {
    "prompt": "What are the project accomplishments, active blockers, and decisions required for Himaya, Ganesh, and Dakshinya?",
    "target_member": ""
}
headers = {
    "Content-Type": "application/json",
    "X-User-Role": "manager",
    "X-User-ID": "USR-OWNER-01"
}

try:
    resp = requests.post(url, json=payload, headers=headers, timeout=15)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print("\n--- MANAGER RESPONSE ---")
        print(data.get("response"))
        print(f"\nLatency: {data.get('latency')}s")
    else:
        print(resp.text)
except Exception as e:
    print(f"HTTP Test Exception: {e}")
