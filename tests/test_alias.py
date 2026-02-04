import requests
import time

url = "http://localhost:8000/api/chats/analyze-message"
payload = {"text": "You are stupid."}

print("Attempting to connect to", url)
for i in range(10):
    try:
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        if response.status_code == 200:
            print("✅ Success!")
            break
    except Exception as e:
        print(f"Waiting for server... ({e})")
        time.sleep(2)
