#!/usr/bin/env python3
"""
VERITAS Async Job Queue - Full Completion Test
Testing that a job actually completes successfully
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

def test_full_completion():
    """Test that a job actually completes successfully"""
    print("🚀 VERITAS Async Job Queue - Full Completion Test")
    print("=" * 60)
    
    # Login
    login_data = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json().get("token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Submit job
    print(f"🎬 Submitting fact-check job for: {TIKTOK_URL}")
    fact_check_data = {"video_url": TIKTOK_URL}
    response = requests.post(f"{API_BASE}/fact-check", json=fact_check_data, headers=headers, timeout=10)
    
    if response.status_code != 202:
        print(f"❌ Job submit failed: {response.status_code} - {response.text}")
        return False
    
    job_id = response.json().get("job_id")
    print(f"✅ Job submitted - ID: {job_id}")
    
    # Poll for completion with longer timeout
    print("📊 Polling for completion (max 3 minutes)...")
    max_polls = 36  # 36 polls * 5 seconds = 3 minutes
    poll_interval = 5
    
    for poll_count in range(max_polls):
        try:
            response = requests.get(f"{API_BASE}/fact-check/{job_id}/status", headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                progress = data.get("progress", 0)
                message = data.get("progress_message", "")
                
                print(f"   Poll {poll_count + 1}: {status} ({progress}%) - {message}")
                
                if status == "completed":
                    result = data.get("result")
                    if result:
                        print("\n🎉 JOB COMPLETED SUCCESSFULLY!")
                        print(f"   - Overall Verdict: {result.get('overall_verdict')}")
                        print(f"   - Confidence Score: {result.get('confidence_score')}%")
                        print(f"   - Summary: {result.get('summary', '')[:100]}...")
                        print(f"   - Transcript Length: {len(result.get('transcript', ''))} chars")
                        print(f"   - Claims Count: {len(result.get('claims', []))}")
                        print(f"   - Deepfake Risk: {result.get('deepfake', {}).get('risk_level')}")
                        print(f"   - Sources Count: {len(result.get('sources', []))}")
                        
                        # Verify all expected fields are present
                        expected_fields = ["id", "overall_verdict", "confidence_score", "summary", "transcript", "claims", "deepfake", "video_url", "created_at"]
                        missing_fields = [field for field in expected_fields if field not in result]
                        
                        if missing_fields:
                            print(f"⚠️  Missing fields in result: {missing_fields}")
                        else:
                            print("✅ All expected fields present in result")
                        
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
                print(f"❌ Status check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Polling error: {str(e)}")
            return False
    
    print(f"❌ Job did not complete within {max_polls * poll_interval} seconds")
    return False

if __name__ == "__main__":
    success = test_full_completion()
    if success:
        print("\n✅ FULL ASYNC JOB COMPLETION TEST PASSED!")
    else:
        print("\n❌ FULL ASYNC JOB COMPLETION TEST FAILED!")
    sys.exit(0 if success else 1)