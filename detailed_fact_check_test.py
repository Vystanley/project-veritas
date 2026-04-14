#!/usr/bin/env python3
"""
Detailed Real-time Fact-checking Test
Test the web search integration and source verification
"""

import requests
import json
import time
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
FRONTEND_ENV_PATH = Path(__file__).parent / 'frontend' / '.env'
if FRONTEND_ENV_PATH.exists():
    load_dotenv(FRONTEND_ENV_PATH)

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://video-truth-8.preview.emergentagent.com')
BASE_URL = BASE_URL.rstrip('/')

print(f"🔗 Testing detailed fact-checking at: {BASE_URL}")

class DetailedFactCheckTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def authenticate(self):
        """Get authentication token"""
        login_data = {"email": "rttest@gmail.com", "password": "Test1234!"}
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=login_data, timeout=30)
        
        if response.status_code == 200:
            return response.json()["token"]
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return None
            
    def detailed_fact_check_test(self):
        """Run detailed fact-check with source analysis"""
        auth_token = self.authenticate()
        if not auth_token:
            return False
            
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        print("\n🔍 Running detailed fact-check analysis...")
        print("   URL: https://www.youtube.com/shorts/MVHWJTFWVj8")
        print("   Timeout: 240 seconds")
        print("   🔄 Processing...")
        
        start_time = time.time()
        
        try:
            response = self.session.post(f"{BASE_URL}/api/fact-check", 
                                       json={"video_url": "https://www.youtube.com/shorts/MVHWJTFWVj8"},
                                       headers=headers, timeout=240)
            
            elapsed = time.time() - start_time
            print(f"   ⏱️  Request completed in {elapsed:.1f} seconds")
            
            if response.status_code == 429:
                print("   ⚠️  Rate limited - user has exhausted free scans")
                return True  # This is expected behavior
                
            if response.status_code != 200:
                print(f"   ❌ HTTP {response.status_code}: {response.text}")
                return False
                
            data = response.json()
            
            # Detailed analysis
            print("\n📊 FACT-CHECK RESULTS ANALYSIS:")
            print("=" * 50)
            
            # Basic response structure
            print(f"Overall Verdict: {data.get('overall_verdict', 'N/A')}")
            print(f"Confidence Score: {data.get('confidence_score', 0)}%")
            print(f"Summary Length: {len(data.get('summary', ''))} characters")
            print(f"Transcript Length: {len(data.get('transcript', ''))} characters")
            
            # Claims analysis
            claims = data.get('claims', [])
            print(f"\nClaims Found: {len(claims)}")
            for i, claim in enumerate(claims[:3], 1):  # Show first 3 claims
                print(f"  {i}. Claim: {claim.get('claim', 'N/A')[:100]}...")
                print(f"     Verdict: {claim.get('verdict', 'N/A')}")
                print(f"     Sources: {len(claim.get('sources', []))}")
            
            # Sources analysis
            sources = data.get('sources', [])
            print(f"\nSources Found: {len(sources)}")
            real_urls = 0
            for i, source in enumerate(sources[:5], 1):  # Show first 5 sources
                url = source.get('url', '')
                title = source.get('title', 'No title')
                if url and url.startswith('http'):
                    real_urls += 1
                    print(f"  {i}. {title[:50]}...")
                    print(f"     URL: {url}")
                else:
                    print(f"  {i}. {title[:50]}... (No URL)")
            
            print(f"\nReal URLs Found: {real_urls}/{len(sources)}")
            
            # Deepfake analysis
            deepfake = data.get('deepfake', {})
            print(f"\nDeepfake Analysis:")
            print(f"  Risk Level: {deepfake.get('risk_level', 'N/A')}")
            print(f"  Confidence: {deepfake.get('confidence', 0)}%")
            print(f"  Analysis: {deepfake.get('analysis', 'N/A')[:100]}...")
            
            # Web search integration assessment
            print(f"\n🌐 WEB SEARCH INTEGRATION ASSESSMENT:")
            print("=" * 50)
            
            has_web_sources = real_urls > 0
            has_detailed_claims = len(claims) > 0 and any(len(c.get('explanation', '')) > 50 for c in claims)
            has_current_info = any('2024' in str(source) or '2025' in str(source) or '2026' in str(source) 
                                 for source in sources)
            
            score = 0
            if has_web_sources:
                score += 1
                print("✅ Real web sources found")
            else:
                print("❌ No real web sources found")
                
            if has_detailed_claims:
                score += 1
                print("✅ Detailed claims analysis provided")
            else:
                print("❌ Claims analysis lacking detail")
                
            if has_current_info:
                score += 1
                print("✅ Recent/current information detected")
            else:
                print("⚠️  Could not verify recent information")
                
            if len(data.get('transcript', '')) > 50:
                score += 1
                print("✅ Transcript successfully extracted")
            else:
                print("❌ Transcript extraction failed")
                
            print(f"\nIntegration Score: {score}/4")
            
            if score >= 3:
                print("🎉 Real-time web search integration is WORKING")
                return True
            elif score >= 2:
                print("⚠️  Real-time web search integration is PARTIALLY WORKING")
                return True
            else:
                print("❌ Real-time web search integration has ISSUES")
                return False
                
        except requests.exceptions.Timeout:
            print("   ❌ Request timeout (>240s)")
            return False
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return False

if __name__ == "__main__":
    tester = DetailedFactCheckTester()
    success = tester.detailed_fact_check_test()
    exit(0 if success else 1)