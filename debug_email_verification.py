#!/usr/bin/env python3

import asyncio
import aiohttp
import json

BASE_URL = "https://video-truth-8.preview.emergentagent.com"
API_URL = f"{BASE_URL}/api"

async def debug_email_verification():
    """Debug the email verification issue"""
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Register user
        register_data = {
            "name": "DebugUser",
            "email": "debugverify3@gmail.com",
            "password": "Test1234!",
            "consent_accepted": True
        }
        
        print("1. Registering user...")
        async with session.post(f"{API_URL}/auth/register", json=register_data) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                print(f"❌ Registration failed: {resp.status} - {error_text}")
                return
            
            register_resp = await resp.json()
            verification_code = register_resp.get("verification_code")
            token = register_resp["token"]
            
            print(f"✅ Registered: email_verified={register_resp['user']['email_verified']}, code={verification_code}")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 2: Verify email
        print("2. Verifying email...")
        verify_data = {"code": verification_code}
        
        async with session.post(f"{API_URL}/auth/verify-email", json=verify_data, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                print(f"❌ Verification failed: {resp.status} - {error_text}")
                return
            
            verify_resp = await resp.json()
            print(f"✅ Verification response: {verify_resp}")
        
        # Step 3: Check /auth/me immediately after verification
        print("3. Checking /auth/me after verification...")
        
        async with session.get(f"{API_URL}/auth/me", headers=headers) as resp:
            if resp.status != 200:
                print(f"❌ /auth/me failed: {resp.status}")
                return
            
            me_resp = await resp.json()
            print(f"✅ /auth/me: email_verified={me_resp.get('email_verified')}")
        
        # Step 4: Login again to see what happens
        print("4. Logging in again...")
        login_data = {"email": "debugverify3@gmail.com", "password": "Test1234!"}
        
        async with session.post(f"{API_URL}/auth/login", json=login_data) as resp:
            if resp.status != 200:
                print(f"❌ Login failed: {resp.status}")
                return
            
            login_resp = await resp.json()
            user_data = login_resp.get("user", {})
            has_verification_code = "verification_code" in login_resp
            verification_code_value = login_resp.get("verification_code")
            
            print(f"✅ Login response:")
            print(f"   email_verified: {user_data.get('email_verified')}")
            print(f"   has verification_code: {has_verification_code}")
            print(f"   verification_code: {verification_code_value}")
            print(f"   Full user data: {user_data}")
            
        # Let's also clean up
        async with session.delete(f"{API_URL}/account/delete", headers=headers) as resp:
            print(f"✅ Cleanup: {resp.status}")

if __name__ == "__main__":
    asyncio.run(debug_email_verification())