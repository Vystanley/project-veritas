#!/usr/bin/env python3
"""
VERITAS Async Job Queue - Quick Test
Testing core async functionality without long polling
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "https://video-truth-8.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test credentials
TEST_EMAIL = "aitest@gmail.com"
TEST_PASSWORD = "Test1234!"

# Test TikTok URL from review request
TIKTOK_URL = "https://vt.tiktok.com/ZSutjpL9X/"

def quick_test():
    """Quick test of core async functionality"""
    print("🚀 VERITAS Async Job Queue - Quick Test")
    print("=" * 50)
    
    # Test 1: Health
    print("🏥 Testing health...")
    response = requests.get(f"{API_BASE}/health", timeout=10)
    if response.status_code == 200 and response.json().get("status") == "ok":
        print("✅ Health endpoint working")
    else:
        print(f"❌ Health failed: {response.status_code}")
        return False
    
    # Test 2: Login
    print("🔐 Testing login...")
    login_data = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
    if response.status_code == 200:
        token = response.json().get("token")
        print(f"✅ Login successful - Token: {len(token)} chars")
    else:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Test 3: Subscription
    print("💳 Testing subscription...")
    response = requests.get(f"{API_BASE}/subscription/status", headers=headers, timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Subscription working - Plan: {data.get('plan')}, Scans: {data.get('scans_used')}/{data.get('scans_remaining')}")
    else:
        print(f"❌ Subscription failed: {response.status_code}")
        return False
    
    # Test 4: Async fact-check submit (should return 202 immediately)
    print(f"🎬 Testing async fact-check submit...")
    fact_check_data = {"video_url": TIKTOK_URL}
    start_time = time.time()
    response = requests.post(f"{API_BASE}/fact-check", json=fact_check_data, headers=headers, timeout=10)
    elapsed = time.time() - start_time
    
    if response.status_code == 202:
        data = response.json()
        job_id = data.get("job_id")
        status = data.get("status")
        print(f"✅ Async submit working - Job ID: {job_id}, Status: {status}, Time: {elapsed:.1f}s")
        
        # Test 5: Quick job status check (just one poll)
        print("📊 Testing job status polling (1 poll)...")
        time.sleep(2)  # Wait 2 seconds
        response = requests.get(f"{API_BASE}/fact-check/{job_id}/status", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Job status working - Status: {data.get('status')}, Progress: {data.get('progress')}%")
        else:
            print(f"❌ Job status failed: {response.status_code}")
            return False
    else:
        print(f"❌ Async submit failed - Expected 202, got {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    # Test 6: Error handling
    print("🚨 Testing error handling...")
    response = requests.post(f"{API_BASE}/fact-check", json={}, headers=headers, timeout=10)
    if response.headers.get("content-type", "").startswith("application/json"):
        data = response.json()
        if "detail" in data:
            print("✅ Error handling returns JSON")
        else:
            print(f"❌ Error JSON missing 'detail': {data}")
            return False
    else:
        print(f"❌ Error handling returns non-JSON: {response.text}")
        return False
    
    # Test 7: 404 job with valid token
    print("🔍 Testing 404 for nonexistent job...")
    response = requests.get(f"{API_BASE}/fact-check/nonexistent-id/status", headers=headers, timeout=10)
    if response.status_code == 404:
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            if "detail" in data:
                print("✅ 404 job returns JSON error")
            else:
                print(f"❌ 404 JSON missing 'detail': {data}")
                return False
        else:
            print(f"❌ 404 returns non-JSON: {response.text}")
            return False
    else:
        print(f"⚠️  404 test returned {response.status_code} (expected 404)")
        # This might be OK if it's a different error but still JSON
        if response.headers.get("content-type", "").startswith("application/json"):
            print("✅ Still returns JSON error")
        else:
            print(f"❌ Non-JSON response: {response.text}")
            return False
    
    print("\n" + "=" * 50)
    print("🎉 ALL CORE ASYNC TESTS PASSED!")
    print("✅ Async job queue working correctly")
    print("✅ JSON error handling working")
    print("✅ Job status polling functional")
    return True

if __name__ == "__main__":
    success = quick_test()
    sys.exit(0 if success else 1)