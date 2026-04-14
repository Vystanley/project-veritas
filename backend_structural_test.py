#!/usr/bin/env python3
"""
Backend Structural Testing for Veritas AI Fact-Checker - Review Request Testing
Tests 3 specific structural fixes and regression cases as per review request
"""

import asyncio
import aiohttp
import json
import time
import sys
import random
from datetime import datetime

# Backend URL from review request
BASE_URL = "https://video-truth-8.preview.emergentagent.com"

def generate_test_email():
    """Generate a random test email to avoid conflicts"""
    return f"structtest{random.randint(100000, 999999)}@gmail.com"

class StructuralTester:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        
    async def test_fix1_json_responses(self):
        """
        Fix 1: Backend ALWAYS returns JSON (no raw text errors)
        Tests specific error scenarios from review request
        """
        print("\n🔧 Testing Fix 1: Backend ALWAYS returns JSON (no raw text errors)")
        
        async with aiohttp.ClientSession() as session:
            # Test 1a: No auth header on protected endpoint
            print("Test 1a: No auth header on protected endpoint...")
            fact_check_data = {"video_url": "https://example.com"}
            
            async with session.post(f"{self.api_url}/fact-check", json=fact_check_data) as resp:
                content_type = resp.headers.get('content-type', '')
                response_text = await resp.text()
                
                # Should return JSON, not raw text
                if 'application/json' not in content_type:
                    print(f"❌ Response not JSON. Content-Type: {content_type}")
                    print(f"   Raw response: {response_text}")
                    return False
                
                try:
                    response_json = json.loads(response_text)
                    if "detail" not in response_json:
                        print(f"❌ JSON response missing 'detail' field: {response_json}")
                        return False
                    
                    print(f"✅ No auth header returns JSON with detail: {response_json['detail']}")
                except json.JSONDecodeError:
                    print(f"❌ Response is not valid JSON: {response_text}")
                    return False
            
            # Test 1b: Invalid video URL with auth
            print("Test 1b: Invalid video URL with auth...")
            
            # First login to get token
            login_data = {"email": "aitest@gmail.com", "password": "Test1234!"}
            async with session.post(f"{self.api_url}/auth/login", json=login_data) as resp:
                if resp.status != 200:
                    print(f"❌ Could not login test user: {resp.status}")
                    return False
                
                login_resp = await resp.json()
                token = login_resp["token"]
                headers = {"Authorization": f"Bearer {token}"}
            
            # Test invalid video URL (120 second timeout as requested)
            invalid_video_data = {"video_url": "https://example.com/not-a-real-video.mp4"}
            timeout = aiohttp.ClientTimeout(total=120)
            
            async with aiohttp.ClientSession(timeout=timeout) as timeout_session:
                try:
                    async with timeout_session.post(f"{self.api_url}/fact-check", json=invalid_video_data, headers=headers) as resp:
                        content_type = resp.headers.get('content-type', '')
                        response_text = await resp.text()
                        
                        # Should return JSON, not raw text or 500
                        if resp.status == 500:
                            print(f"❌ Got 500 status code instead of 400")
                            return False
                        
                        if 'application/json' not in content_type:
                            print(f"❌ Response not JSON. Content-Type: {content_type}")
                            print(f"   Raw response: {response_text}")
                            return False
                        
                        try:
                            response_json = json.loads(response_text)
                            if "detail" not in response_json:
                                print(f"❌ JSON response missing 'detail' field: {response_json}")
                                return False
                            
                            print(f"✅ Invalid video URL returns {resp.status} JSON with detail: {response_json['detail']}")
                        except json.JSONDecodeError:
                            print(f"❌ Response is not valid JSON: {response_text}")
                            return False
                            
                except asyncio.TimeoutError:
                    print("❌ Invalid video URL test timed out after 120 seconds")
                    return False
            
            # Test 1c: Health check returns JSON
            print("Test 1c: Health check returns JSON...")
            async with session.get(f"{self.api_url}/health") as resp:
                if resp.status != 200:
                    print(f"❌ Health check failed: {resp.status}")
                    return False
                
                content_type = resp.headers.get('content-type', '')
                if 'application/json' not in content_type:
                    print(f"❌ Health check not JSON. Content-Type: {content_type}")
                    return False
                
                try:
                    health_resp = await resp.json()
                    print(f"✅ Health check returns JSON: {health_resp}")
                except json.JSONDecodeError:
                    print("❌ Health check response is not valid JSON")
                    return False
            
            return True
    
    async def test_fix2_stripe_checkout(self):
        """
        Fix 2: Stripe checkout returns valid URL
        Tests exact scenario from review request
        """
        print("\n💳 Testing Fix 2: Stripe checkout returns valid URL")
        
        async with aiohttp.ClientSession() as session:
            # Login first
            login_data = {"email": "aitest@gmail.com", "password": "Test1234!"}
            async with session.post(f"{self.api_url}/auth/login", json=login_data) as resp:
                if resp.status != 200:
                    print(f"❌ Could not login test user: {resp.status}")
                    return False
                
                login_resp = await resp.json()
                token = login_resp["token"]
                headers = {"Authorization": f"Bearer {token}"}
            
            # Test Stripe checkout with exact data from review request
            checkout_data = {
                "plan": "premium_monthly",
                "origin_url": "https://video-truth-8.preview.emergentagent.com"
            }
            
            async with session.post(f"{self.api_url}/payments/checkout", json=checkout_data, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"❌ Checkout failed: {resp.status} - {error_text}")
                    return False
                
                content_type = resp.headers.get('content-type', '')
                if 'application/json' not in content_type:
                    print(f"❌ Checkout response not JSON. Content-Type: {content_type}")
                    return False
                
                try:
                    checkout_resp = await resp.json()
                    
                    # Verify response structure
                    if "url" not in checkout_resp:
                        print(f"❌ No URL in checkout response: {checkout_resp}")
                        return False
                    
                    checkout_url = checkout_resp["url"]
                    
                    if not checkout_url.startswith("https://checkout.stripe.com/"):
                        print(f"❌ Invalid checkout URL: {checkout_url}")
                        return False
                    
                    print(f"✅ Stripe checkout returns valid URL:")
                    print(f"   URL: {checkout_url}")
                    print(f"   Session ID: {checkout_resp.get('session_id', 'N/A')}")
                    return True
                    
                except json.JSONDecodeError:
                    print("❌ Checkout response is not valid JSON")
                    return False
    
    async def test_fix3_tiktok_robust_download(self):
        """
        Fix 3: Robust video download (TikTok with retry)
        Tests exact TikTok URL from review request with 240s timeout
        """
        print("\n🎵 Testing Fix 3: Robust video download (TikTok with retry)")
        
        async with aiohttp.ClientSession() as session:
            # Login first
            login_data = {"email": "aitest@gmail.com", "password": "Test1234!"}
            async with session.post(f"{self.api_url}/auth/login", json=login_data) as resp:
                if resp.status != 200:
                    print(f"❌ Could not login test user: {resp.status}")
                    return False
                
                login_resp = await resp.json()
                token = login_resp["token"]
                headers = {"Authorization": f"Bearer {token}"}
            
            # Test TikTok video with 240 second timeout as requested
            print("Testing TikTok video processing (timeout: 240 seconds)...")
            tiktok_data = {"video_url": "https://www.tiktok.com/@a3noticias/video/7613811959649144086?lang=en"}
            
            start_time = time.time()
            timeout = aiohttp.ClientTimeout(total=240)  # 4 minutes as requested
            
            async with aiohttp.ClientSession(timeout=timeout) as tiktok_session:
                try:
                    async with tiktok_session.post(f"{self.api_url}/fact-check", json=tiktok_data, headers=headers) as resp:
                        elapsed = time.time() - start_time
                        print(f"⏱️  Response received in {elapsed:.1f} seconds")
                        
                        content_type = resp.headers.get('content-type', '')
                        response_text = await resp.text()
                        
                        # Check if rate limited (429)
                        if resp.status == 429:
                            if 'application/json' not in content_type:
                                print(f"❌ Rate limit response not JSON. Content-Type: {content_type}")
                                return False
                            
                            try:
                                rate_resp = json.loads(response_text)
                                if "detail" not in rate_resp:
                                    print(f"❌ Rate limit response missing 'detail' field: {rate_resp}")
                                    return False
                                
                                print(f"✅ Rate limited (429) returns JSON with detail: {rate_resp['detail']}")
                                return True
                            except json.JSONDecodeError:
                                print(f"❌ Rate limit response is not valid JSON: {response_text}")
                                return False
                        
                        if resp.status != 200:
                            print(f"❌ TikTok fact-check failed: {resp.status} - {response_text}")
                            return False
                        
                        if 'application/json' not in content_type:
                            print(f"❌ TikTok response not JSON. Content-Type: {content_type}")
                            return False
                        
                        try:
                            fact_resp = json.loads(response_text)
                            
                            # Verify full analysis structure
                            required_fields = ["overall_verdict", "confidence_score", "claims", "deepfake", "transcript"]
                            missing_fields = []
                            for field in required_fields:
                                if field not in fact_resp:
                                    missing_fields.append(field)
                            
                            if missing_fields:
                                print(f"❌ Missing fields in TikTok response: {missing_fields}")
                                return False
                            
                            print(f"✅ TikTok analysis completed successfully:")
                            print(f"   Verdict: {fact_resp.get('overall_verdict')}")
                            print(f"   Confidence: {fact_resp.get('confidence_score')}%")
                            print(f"   Claims: {len(fact_resp.get('claims', []))}")
                            print(f"   Deepfake risk: {fact_resp.get('deepfake', {}).get('risk_level')}")
                            print(f"   Transcript length: {len(fact_resp.get('transcript', ''))}")
                            print(f"   Processing time: {elapsed:.1f}s")
                            return True
                            
                        except json.JSONDecodeError:
                            print(f"❌ TikTok response is not valid JSON: {response_text}")
                            return False
                            
                except asyncio.TimeoutError:
                    print("❌ TikTok fact-check timed out after 240 seconds")
                    return False
                except Exception as e:
                    print(f"❌ TikTok fact-check error: {e}")
                    return False
    
    async def test_regression_email_verification(self):
        """
        Regression: Email verification still works
        Tests exact flow from review request
        """
        print("\n📧 Testing Regression: Email verification still works")
        
        async with aiohttp.ClientSession() as session:
            # Step 1: Register with exact data from review request
            register_data = {
                "name": "StructTest",
                "email": "structtest@gmail.com",
                "password": "Test1234!",
                "consent_accepted": True
            }
            
            # Try to register (might already exist)
            async with session.post(f"{self.api_url}/auth/register", json=register_data) as resp:
                if resp.status == 400:
                    # User might already exist, continue with verification test...
                    print("User might already exist, continuing with verification test...")
                    # Try to login to get token for delete
                    login_data = {"email": "structtest@gmail.com", "password": "Test1234!"}
                    async with session.post(f"{self.api_url}/auth/login", json=login_data) as login_resp:
                        if login_resp.status == 200:
                            # User exists and verified, need to delete first
                            login_result = await login_resp.json()
                            token = login_result["token"]
                            headers = {"Authorization": f"Bearer {token}"}
                            
                            # Delete account first
                            async with session.delete(f"{self.api_url}/auth/delete-account", headers=headers) as del_resp:
                                if del_resp.status == 200:
                                    print("Deleted existing account, waiting cooldown...")
                                    # Wait a bit then retry registration
                                    await asyncio.sleep(2)
                                    
                                    # Try registration again
                                    async with session.post(f"{self.api_url}/auth/register", json=register_data) as retry_resp:
                                        if retry_resp.status != 200:
                                            error_text = await retry_resp.text()
                                            print(f"❌ Registration failed after deletion: {retry_resp.status} - {error_text}")
                                            return False
                                        register_resp = await retry_resp.json()
                                else:
                                    print(f"Could not delete existing account: {del_resp.status}")
                                    # Create new random email instead
                                    new_email = generate_test_email()
                                    register_data["email"] = new_email
                                    async with session.post(f"{self.api_url}/auth/register", json=register_data) as new_resp:
                                        if new_resp.status != 200:
                                            error_text = await new_resp.text()
                                            print(f"❌ Registration failed: {new_resp.status} - {error_text}")
                                            return False
                                        register_resp = await new_resp.json()
                        else:
                            # User doesn't exist or wrong password, try with new email
                            new_email = generate_test_email()
                            register_data["email"] = new_email
                            async with session.post(f"{self.api_url}/auth/register", json=register_data) as new_resp:
                                if new_resp.status != 200:
                                    error_text = await new_resp.text()
                                    print(f"❌ Registration failed: {new_resp.status} - {error_text}")
                                    return False
                                register_resp = await new_resp.json()
                elif resp.status != 200:
                    error_text = await resp.text()
                    print(f"❌ Registration failed: {resp.status} - {error_text}")
                    return False
                else:
                    register_resp = await resp.json()
            
            # Step 2: Verify response has verification_code
            verification_code = register_resp.get("verification_code")
            if not verification_code:
                print("❌ No verification code in registration response")
                return False
            
            print(f"✅ Registration successful, verification_code: {verification_code}")
            token = register_resp["token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Step 3: Verify email with code
            verify_data = {"code": verification_code}
            async with session.post(f"{self.api_url}/auth/verify-email", json=verify_data, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"❌ Email verification failed: {resp.status} - {error_text}")
                    return False
                
                verify_resp = await resp.json()
                if not verify_resp.get("success"):
                    print(f"❌ Verification failed: {verify_resp}")
                    return False
                
                print("✅ Email verification successful: {'success': true}")
                return True
    
    async def test_regression_login(self):
        """
        Regression: Login still works
        Tests exact login from review request
        """
        print("\n🔐 Testing Regression: Login")
        
        async with aiohttp.ClientSession() as session:
            # Test exact login data from review request
            login_data = {"email": "aitest@gmail.com", "password": "Test1234!"}
            
            async with session.post(f"{self.api_url}/auth/login", json=login_data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"❌ Login failed: {resp.status} - {error_text}")
                    return False
                
                content_type = resp.headers.get('content-type', '')
                if 'application/json' not in content_type:
                    print(f"❌ Login response not JSON. Content-Type: {content_type}")
                    return False
                
                try:
                    login_resp = await resp.json()
                    
                    # Verify response has token
                    if "token" not in login_resp:
                        print(f"❌ No token in login response: {login_resp}")
                        return False
                    
                    token = login_resp["token"]
                    if not token or len(token) < 10:
                        print(f"❌ Invalid token: {token}")
                        return False
                    
                    print(f"✅ Login successful, token received (length: {len(token)})")
                    return True
                    
                except json.JSONDecodeError:
                    print("❌ Login response is not valid JSON")
                    return False

async def main():
    """Run all structural tests as per review request"""
    base_url = BASE_URL
    
    print("🚀 Starting Veritas AI Backend Structural Testing - Review Request")
    print(f"📡 Backend URL: {base_url}")
    print("=" * 70)
    
    tester = StructuralTester(base_url)
    
    results = {}
    
    try:
        # Test Fix 1: Backend ALWAYS returns JSON (no raw text errors)
        results["fix1_json_responses"] = await tester.test_fix1_json_responses()
        
        # Test Fix 2: Stripe checkout returns valid URL
        results["fix2_stripe_checkout"] = await tester.test_fix2_stripe_checkout()
        
        # Test Fix 3: Robust video download (TikTok with retry)
        results["fix3_tiktok_robust"] = await tester.test_fix3_tiktok_robust_download()
        
        # Test Regression: Email verification still works
        results["regression_email_verification"] = await tester.test_regression_email_verification()
        
        # Test Regression: Login
        results["regression_login"] = await tester.test_regression_login()
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("📊 STRUCTURAL TEST RESULTS SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<35}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("🎉 ALL STRUCTURAL TESTS PASSED!")
        return True
    else:
        print("⚠️  SOME STRUCTURAL TESTS FAILED!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)