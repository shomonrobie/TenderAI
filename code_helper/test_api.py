# test_api.py - Run this to test if Flask API is working

import requests
import json

print("=" * 50)
print("Testing Flask API endpoints")
print("=" * 50)

# Test health endpoint
try:
    response = requests.get('http://localhost:5000/api/health')
    print(f"✅ Health check: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"❌ Health check failed: {e}")

# Test login endpoint
try:
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    response = requests.post(
        'http://localhost:5000/api/auth/login',
        json=login_data,
        headers={'Content-Type': 'application/json'}
    )
    print(f"\n📡 Login test: {response.status_code}")
    print(f"   Response: {response.text[:200]}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Success: {result.get('success')}")
        if result.get('success'):
            print(f"   User: {result.get('user', {}).get('username')}")
except Exception as e:
    print(f"❌ Login test failed: {e}")

print("\n" + "=" * 50)
print("If Flask API is not responding, make sure it's running:")
print("  - Check if Flask started: look for 'Flask API started on port 5000' in main.py output")
print("  - Run: netstat -an | findstr 5000")
print("=" * 50)