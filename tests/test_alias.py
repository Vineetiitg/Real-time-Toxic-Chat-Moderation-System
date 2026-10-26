"""
Manual integration test script for analyze-message endpoint.
Run directly with: python tests/test_alias.py
"""

def main():
    import requests
    import time

    url = "http://localhost:8000/api/chats/analyze-message"
    payload = {"text": "You are stupid."}

    print("Attempting to connect to", url)
    for i in range(5):
        try:
            response = requests.post(url, json=payload, timeout=2.0)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            if response.status_code == 200:
                print("✅ Success!")
                break
        except Exception as e:
            print(f"Waiting for server... ({e})")
            time.sleep(1)


if __name__ == "__main__":
    main()
