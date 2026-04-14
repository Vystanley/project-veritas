#!/usr/bin/env python3
"""
VERITAS Async Job Queue Test
Testing the new async fact-checking with job polling and global JSON error handlers
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

def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok" and data.get("service") == "veritas-api":
                print("✅ Health endpoint working correctly")
                return True
            else:
                print(f"❌ Health endpoint returned unexpected data: {data}")
                return False
        else:
            print(f"❌ Health endpoint failed - Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint error: {str(e)}")
        return False

def test_login():
    """Test login and get JWT token"""
    print("🔐 Testing login...")
    
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    try:
        response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            user = data.get("user")
            if token and user:
                print(f"✅ Login successful - Token length: {len(token)}, User: {user.get('email')}")
                return token
            else:
                print(f"❌ Login failed - Missing token or user in response: {data}")
                return None
        else:
            print(f"❌ Login failed - Status: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return None

def test_subscription_status(token):
    """Test subscription status endpoint"""
    print("💳 Testing subscription status...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{API_BASE}/subscription/status", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["plan", "scans_used", "scans_remaining", "is_premium"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                print(f"❌ Subscription status missing fields: {missing_fields}")
                return False
            
            print(f"✅ Subscription status working - Plan: {data.get('plan')}, Scans: {data.get('scans_used')}/{data.get('scans_remaining')}")
            return True
        else:
            print(f"❌ Subscription status failed - Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Subscription status error: {str(e)}")
        return False

def test_async_fact_check_submit(token):
    """Test async fact-check submit - should return 202 with job_id immediately"""
    print(f"🎬 Testing async fact-check submit with TikTok URL: {TIKTOK_URL}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    fact_check_data = {
        "video_url": TIKTOK_URL
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{API_BASE}/fact-check", json=fact_check_data, headers=headers, timeout=30)
        elapsed_time = time.time() - start_time
        
        print(f"⏱️  Submit request completed in {elapsed_time:.1f} seconds")
        
        if response.status_code == 202:
            data = response.json()
            job_id = data.get("job_id")
            status = data.get("status")
            
            if job_id and status == "pending":
                print(f"✅ Async fact-check submit working - Job ID: {job_id}, Status: {status}")
                return job_id
            else:
                print(f"❌ Async fact-check submit failed - Missing job_id or wrong status: {data}")
                return None
        else:
            print(f"❌ Async fact-check submit failed - Expected 202, got {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Async fact-check submit error: {str(e)}")
        return None

def test_job_status_polling(token, job_id):
    """Test job status polling until completion"""
    print(f"📊 Testing job status polling for job: {job_id}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    max_polls = 60  # 60 polls * 3 seconds = 180 seconds max
    poll_interval = 3
    
    for poll_count in range(max_polls):
        try:
            response = requests.get(f"{API_BASE}/fact-check/{job_id}/status", headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                progress = data.get("progress", 0)
                progress_message = data.get("progress_message", "")
                
                print(f"   Poll {poll_count + 1}: Status={status}, Progress={progress}%, Message={progress_message}")
                
                if status == "completed":
                    result = data.get("result")
                    if result:
                        print("✅ Job completed successfully!")
                        print(f"   - Overall Verdict: {result.get('overall_verdict')}")
                        print(f"   - Confidence Score: {result.get('confidence_score')}%")
                        print(f"   - Transcript Length: {len(result.get('transcript', ''))} chars")
                        print(f"   - Claims Count: {len(result.get('claims', []))}")
                        print(f"   - Deepfake Risk: {result.get('deepfake', {}).get('risk_level')}")
                        return True
                    else:
                        print("❌ Job completed but no result data")
                        return False
                
                elif status == "failed":
                    error = data.get("error", "Unknown error")
                    print(f"❌ Job failed: {error}")
                    return False
                
                elif status in ["pending", "processing"]:
                    # Continue polling
                    if poll_count < max_polls - 1:
                        time.sleep(poll_interval)
                    continue
                else:
                    print(f"❌ Unknown job status: {status}")
                    return False
            else:
                print(f"❌ Job status polling failed - Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Job status polling error: {str(e)}")
            return False
    
    print(f"❌ Job polling timed out after {max_polls * poll_interval} seconds")
    return False

def test_error_handling(token):
    """Test error handling - should return JSON errors, never raw text"""
    print("🚨 Testing error handling...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Empty body
    print("   Testing empty body...")
    try:
        response = requests.post(f"{API_BASE}/fact-check", json={}, headers=headers, timeout=10)
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            if "detail" in data:
                print("   ✅ Empty body returns JSON error")
            else:
                print(f"   ❌ Empty body JSON missing 'detail' field: {data}")
                return False
        else:
            print(f"   ❌ Empty body returns non-JSON: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Empty body test error: {str(e)}")
        return False
    
    # Test 2: Invalid body
    print("   Testing invalid body...")
    try:
        response = requests.post(f"{API_BASE}/fact-check", json={"invalid": "data"}, headers=headers, timeout=10)
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            if "detail" in data:
                print("   ✅ Invalid body returns JSON error")
            else:
                print(f"   ❌ Invalid body JSON missing 'detail' field: {data}")
                return False
        else:
            print(f"   ❌ Invalid body returns non-JSON: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Invalid body test error: {str(e)}")
        return False
    
    print("✅ Error handling tests passed")
    return True

def test_404_job():
    """Test 404 for nonexistent job - should return 404 JSON error"""
    print("🔍 Testing 404 for nonexistent job...")
    
    # Use a fake token for this test
    headers = {
        "Authorization": f"Bearer fake_token",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{API_BASE}/fact-check/nonexistent-id/status", headers=headers, timeout=30)
        
        # Should return 401 for invalid token, but still JSON
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            if "detail" in data:
                print("✅ Nonexistent job returns JSON error (401 for invalid token)")
                return True
            else:
                print(f"❌ Nonexistent job JSON missing 'detail' field: {data}")
                return False
        else:
            print(f"❌ Nonexistent job returns non-JSON: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Nonexistent job test error: {str(e)}")
        return False

def main():
    """Main test execution"""
    print("🚀 VERITAS Async Job Queue Test")
    print("=" * 60)
    print(f"Testing async fact-checking, job polling, and JSON error handlers")
    print(f"Base URL: {BASE_URL}")
    print(f"Test URL: {TIKTOK_URL}")
    
    results = {}
    
    # Test 1: Health endpoint
    results["health"] = test_health()
    
    # Test 2: Login
    token = test_login()
    results["login"] = token is not None
    if not token:
        print("\n❌ Cannot proceed without valid authentication token")
        sys.exit(1)
    
    # Test 3: Subscription status
    results["subscription"] = test_subscription_status(token)
    
    # Test 4: Async fact-check submit
    job_id = test_async_fact_check_submit(token)
    results["async_submit"] = job_id is not None
    
    # Test 5: Job status polling (only if submit worked)
    if job_id:
        results["job_polling"] = test_job_status_polling(token, job_id)
    else:
        results["job_polling"] = False
        print("⏭️  Skipping job polling test (submit failed)")
    
    # Test 6: Error handling
    results["error_handling"] = test_error_handling(token)
    
    # Test 7: 404 job
    results["404_job"] = test_404_job()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST RESULTS SUMMARY:")
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
        if result:
            passed += 1
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Async job queue working correctly!")
        return True
    else:
        print("💥 SOME TESTS FAILED - Check backend logs for details")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)