"""
Manual Test Script for Legacy app/api.py
Run directly with: python tests/test_app.py
"""

def main():
    import sys
    import os
    from fastapi.testclient import TestClient

    sys.path.append(os.getcwd())

    print("⏳ Importing main app (this triggers model loading)...")
    try:
        from app.api import app
        client = TestClient(app)
        print("✅ App imported successfully.")
    except Exception as e:
        print(f"❌ Failed to import app: {e}")
        return

    print("🔍 Testing Health Check...")
    response = client.get("/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    print("\n🔍 Testing Moderation Endpoint...")
    payload = {"text": "You are stupid and ugly."}
    response = client.post("/moderate", json=payload)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")


if __name__ == "__main__":
    main()
