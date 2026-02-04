from fastapi.testclient import TestClient
import sys
import os

# Add the project directory to sys.path so we can import main
sys.path.append(os.getcwd())

print("⏳ Importing main app (this triggers model loading)...")
try:
    from app.api import app
    client = TestClient(app)
    print("✅ App imported successfully.")
except Exception as e:
    print(f"❌ Failed to import app: {e}")
    sys.exit(1)

def test_health():
    print("🔍 Testing Health Check...")
    response = client.get("/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    if response.status_code == 200 and response.json().get("status") == "online":
        print("✅ Health Check Passed")
    else:
        print("❌ Health Check Failed")

def test_moderation():
    print("\n🔍 Testing Moderation Endpoint...")
    payload = {"text": "You are stupid and ugly."}
    response = client.post("/moderate", json=payload)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data}")
        if "is_flagged" in data and "suggested_alternative" in data:
            print("✅ Moderation Test Passed")
        else:
            print("❌ Moderation Test Failed: Missing fields")
    else:
        print(f"❌ Moderation Test Failed: {response.text}")

if __name__ == "__main__":
    test_health()
    test_moderation()
