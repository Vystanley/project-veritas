#!/usr/bin/env python3
"""
VERITAS Backend Regression Test - Review Request
Tests specific endpoints after frontend-only UI redesign to ensure backend functionality is intact.
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
TEST_EMAIL = "aitest@gmail.com"
TEST_PASSWORD = "Test1234!"

def generate_test_email():
    """Generate a random test email to avoid conflicts"""
    return f"regtest{random.randint(100000, 999999)}@gmail.com"

class RegressionTester:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        
    async def test_health_endpoint(self):
        """Test 1: Health endpoint - GET /api/health"""
        print("\n🏥 Testing Health Endpoint: GET /api/health")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.api_url}/health") as resp:
                    if resp.status != 200:
                        print(f"❌ Health check failed: {resp.status}")
                        return False
                    
                    health_resp = await resp.json()
                    
                    # Verify expected response structure
                    if health_resp.get("status") != "ok":
                        print(f"❌ Health check status not ok: {health_resp}")
                        return False
                    
                    if health_resp.get("service") != "veritas-api":
                        print(f"❌ Health check service name incorrect: {health_resp}")
                        return False
                    
                    print(f"✅ Health endpoint working correctly")
                    print(f"   Status: {health_resp.get('status')}")
                    print(f"   Service: {health_resp.get('service')}")
                    return True
                    
            except Exception as e:
                print(f"❌ Health endpoint error: {e}")
                return False
    
    async def test_auth_flow(self):
        """Test 2: Auth flow - POST /api/auth/register and POST /api/auth/login"""
        print("\n🔐 Testing Auth Flow: Register + Login")
        
        async with aiohttp.ClientSession() as session:
            # Test with existing user credentials first
            print("Step 1: Testing login with existing credentials...")
            login_data = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
            
            async with session.post(f"{self.api_url}/auth/login", json=login_data) as resp:
                if resp.status == 200:
                    login_resp = await resp.json()
                    
                    # Verify response structure
                    if "token" not in login_resp or "user" not in login_resp:
                        print(f"❌ Login response missing required fields: {login_resp}")
                        return False
                    
                    user_data = login_resp["user"]
                    required_user_fields = ["id", "name", "email", "email_verified"]
                    for field in required_user_fields:
                        if field not in user_data:
                            print(f"❌ User data missing field: {field}")
                            return False
                    
                    print(f"✅ Login successful with existing credentials")
                    print(f"   Email: {user_data['email']}")
                    print(f"   Email verified: {user_data['email_verified']}")
                    print(f"   Token length: {len(login_resp['token'])} chars")
                    
                    # Store token for later tests
                    self.auth_token = login_resp["token"]
                    return True
                    
                elif resp.status == 401:
                    print(f"⚠️  Existing credentials invalid, will test registration flow")
                else:
                    error_text = await resp.text()
                    print(f"❌ Login failed: {resp.status} - {error_text}")
                    return False
            
            # If login failed, test registration flow
            print("Step 2: Testing registration with new user...")
            test_email = generate_test_email()
            register_data = {
                "name": "Regression Test User",
                "email": test_email,
                "password": TEST_PASSWORD,
                "consent_accepted": True
            }
            
            async with session.post(f"{self.api_url}/auth/register", json=register_data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"❌ Registration failed: {resp.status} - {error_text}")
                    return False
                
                register_resp = await resp.json()
                
                # Verify response structure
                if "token" not in register_resp or "user" not in register_resp:
                    print(f"❌ Registration response missing required fields: {register_resp}")
                    return False
                
                user_data = register_resp["user"]
                if user_data.get("email") != test_email:
                    print(f"❌ Registration email mismatch: expected {test_email}, got {user_data.get('email')}")
                    return False
                
                print(f"✅ Registration successful")
                print(f"   Email: {user_data['email']}")
                print(f"   Email verified: {user_data.get('email_verified', False)}")
                print(f"   Token length: {len(register_resp['token'])} chars")
                
                # Store token for later tests
                self.auth_token = register_resp["token"]
                
                # Test login with new credentials
                print("Step 3: Testing login with new credentials...")
                login_data = {
                    "email": test_email,
                    "password": TEST_PASSWORD
                }
                
                async with session.post(f"{self.api_url}/auth/login", json=login_data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        print(f"❌ Login with new credentials failed: {resp.status} - {error_text}")
                        return False
                    
                    login_resp = await resp.json()
                    print(f"✅ Login with new credentials successful")
                    return True
    
    async def test_subscription_status(self):
        """Test 3: Subscription status - GET /api/subscription/status (with auth header)"""
        print("\n📊 Testing Subscription Status: GET /api/subscription/status")
        
        if not hasattr(self, 'auth_token'):
            print("❌ No auth token available from previous tests")
            return False
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            try:
                async with session.get(f"{self.api_url}/subscription/status", headers=headers) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        print(f"❌ Subscription status failed: {resp.status} - {error_text}")
                        return False
                    
                    sub_resp = await resp.json()
                    
                    # Verify expected response structure
                    required_fields = ["plan", "scans_used", "scans_remaining", "is_premium", "period_resets_at"]
                    for field in required_fields:
                        if field not in sub_resp:
                            print(f"❌ Subscription response missing field: {field}")
                            return False
                    
                    print(f"✅ Subscription status working correctly")
                    print(f"   Plan: {sub_resp.get('plan')}")
                    print(f"   Scans used: {sub_resp.get('scans_used')}")
                    print(f"   Scans remaining: {sub_resp.get('scans_remaining')}")
                    print(f"   Is premium: {sub_resp.get('is_premium')}")
                    print(f"   Bonus scans: {sub_resp.get('bonus_scans', 0)}")
                    return True
                    
            except Exception as e:
                print(f"❌ Subscription status error: {e}")
                return False
    
    async def test_stripe_checkout(self):
        """Test 4: Stripe checkout - POST /api/payments/checkout (with auth header)"""
        print("\n💳 Testing Stripe Checkout: POST /api/payments/checkout")
        
        if not hasattr(self, 'auth_token'):
            print("❌ No auth token available from previous tests")
            return False
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            checkout_data = {
                "plan": "premium_monthly",
                "origin_url": BASE_URL
            }
            
            try:
                async with session.post(f"{self.api_url}/payments/checkout", json=checkout_data, headers=headers) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        print(f"❌ Stripe checkout failed: {resp.status} - {error_text}")
                        return False
                    
                    checkout_resp = await resp.json()
                    
                    # Verify response structure
                    if "url" not in checkout_resp:
                        print(f"❌ Checkout response missing URL: {checkout_resp}")
                        return False
                    
                    checkout_url = checkout_resp["url"]
                    
                    # Verify it's a valid Stripe checkout URL
                    if not checkout_url.startswith("https://checkout.stripe.com/"):
                        print(f"❌ Invalid Stripe checkout URL: {checkout_url}")
                        return False
                    
                    print(f"✅ Stripe checkout working correctly")
                    print(f"   URL: {checkout_url}")
                    print(f"   Session ID: {checkout_resp.get('session_id', 'N/A')}")
                    return True
                    
            except Exception as e:
                print(f"❌ Stripe checkout error: {e}")
                return False
    
    async def test_unauthorized_access(self):
        """Test 5: Verify protected endpoints require authentication"""
        print("\n🔒 Testing Unauthorized Access Protection")
        
        async with aiohttp.ClientSession() as session:
            # Test subscription status without auth header
            async with session.get(f"{self.api_url}/subscription/status") as resp:
                if resp.status != 403:
                    print(f"❌ Expected 403 for unauthorized subscription access, got {resp.status}")
                    return False
                print("✅ Subscription status properly protected (403 without auth)")
            
            # Test checkout without auth header
            checkout_data = {
                "plan": "premium_monthly",
                "origin_url": BASE_URL
            }
            
            async with session.post(f"{self.api_url}/payments/checkout", json=checkout_data) as resp:
                if resp.status != 403:
                    print(f"❌ Expected 403 for unauthorized checkout access, got {resp.status}")
                    return False
                print("✅ Stripe checkout properly protected (403 without auth)")
            
            return True

async def main():
    """Run all regression tests"""
    print("🚀 Starting VERITAS Backend Regression Testing")
    print(f"📡 Backend URL: {BASE_URL}")
    print(f"🎯 Testing specific endpoints after frontend-only UI redesign")
    print("=" * 70)
    
    tester = RegressionTester(BASE_URL)
    
    results = {}
    
    try:
        # Test 1: Health endpoint
        results["health_endpoint"] = await tester.test_health_endpoint()
        
        # Test 2: Auth flow (register + login)
        results["auth_flow"] = await tester.test_auth_flow()
        
        # Test 3: Subscription status (requires auth)
        results["subscription_status"] = await tester.test_subscription_status()
        
        # Test 4: Stripe checkout (requires auth)
        results["stripe_checkout"] = await tester.test_stripe_checkout()
        
        # Test 5: Unauthorized access protection
        results["unauthorized_protection"] = await tester.test_unauthorized_access()
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("📊 REGRESSION TEST RESULTS SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("🎉 ALL REGRESSION TESTS PASSED!")
        print("✅ Backend functionality intact after frontend UI redesign")
        return True
    else:
        print("⚠️  SOME REGRESSION TESTS FAILED!")
        print("❌ Backend functionality may have been affected")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)