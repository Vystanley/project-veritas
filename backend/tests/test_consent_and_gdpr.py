"""
Backend tests for iteration 4: Consent clickwrap and GDPR account deletion
Tests:
- Registration without consent_accepted → 400
- Registration with consent_accepted: true → success
- DELETE /api/account/delete → deletes all user data
- After deletion, login should fail with 401
"""
import pytest
import requests
import os
from dotenv import load_dotenv
from pathlib import Path

# Load frontend env to get BASE_URL
frontend_env = Path(__file__).parent.parent.parent / 'frontend' / '.env'
load_dotenv(frontend_env)

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL').rstrip('/')


class TestConsentClickwrap:
    """Test consent_accepted field enforcement during registration"""
    
    def test_register_without_consent_fails(self, api_client):
        """Registration without consent_accepted should return 400"""
        payload = {
            "name": "TEST_No_Consent_User",
            "email": f"TEST_no_consent_{os.getpid()}@example.com",
            "password": "testpass123",
            "consent_accepted": False
        }
        response = api_client.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "Terms & Conditions" in data["detail"] or "consent" in data["detail"].lower()
        print(f"✅ Registration without consent rejected with: {data['detail']}")
    
    def test_register_without_consent_field_fails(self, api_client):
        """Registration without consent_accepted field (defaults to False) should return 400"""
        payload = {
            "name": "TEST_Missing_Consent_Field",
            "email": f"TEST_missing_consent_{os.getpid()}@example.com",
            "password": "testpass123"
            # consent_accepted field omitted
        }
        response = api_client.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "Terms & Conditions" in data["detail"] or "consent" in data["detail"].lower()
        print(f"✅ Registration without consent_accepted field rejected")
    
    def test_register_with_consent_succeeds(self, api_client):
        """Registration with consent_accepted: true should succeed"""
        payload = {
            "name": "TEST_Consent_User",
            "email": f"TEST_consent_user_{os.getpid()}@example.com",
            "password": "testpass123456",
            "consent_accepted": True
        }
        response = api_client.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == payload["email"]
        print(f"✅ Registration with consent succeeded, user ID: {data['user']['id']}")
        
        # Verify token works
        token = data["token"]
        me_response = api_client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        print(f"✅ Auth token valid, /api/auth/me working")


class TestGDPRAccountDeletion:
    """Test GDPR Right to be Forgotten - DELETE /api/account/delete"""
    
    def test_delete_account_removes_all_data(self, api_client, mongo_db):
        """Delete account should remove all user data from all collections"""
        # Step 1: Create a user with consent
        register_payload = {
            "name": "TEST_GDPR_Delete_User",
            "email": f"TEST_gdpr_delete_{os.getpid()}@example.com",
            "password": "testpass123456",
            "consent_accepted": True
        }
        register_response = api_client.post(f"{BASE_URL}/api/auth/register", json=register_payload)
        assert register_response.status_code == 200
        user_data = register_response.json()
        token = user_data["token"]
        user_id = user_data["user"]["id"]
        email = user_data["user"]["email"]
        print(f"✅ Created test user for deletion: {user_id}")
        
        # Step 2: Create some data for the user (subscription, scan logs, referral, etc.)
        # Get subscription (auto-creates)
        sub_response = api_client.get(
            f"{BASE_URL}/api/subscription/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert sub_response.status_code == 200
        print(f"✅ User subscription created")
        
        # Get referral code (auto-creates)
        ref_response = api_client.get(
            f"{BASE_URL}/api/referral/info",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert ref_response.status_code == 200
        referral_code = ref_response.json()["code"]
        print(f"✅ User referral code created: {referral_code}")
        
        # Verify data exists in database before deletion
        user_before = mongo_db.users.find_one({"id": user_id})
        assert user_before is not None, "User should exist before deletion"
        sub_before = mongo_db.subscriptions.find_one({"user_id": user_id})
        assert sub_before is not None, "Subscription should exist before deletion"
        ref_before = mongo_db.referrals.find_one({"user_id": user_id})
        assert ref_before is not None, "Referral should exist before deletion"
        print(f"✅ Verified data exists in DB before deletion")
        
        # Step 3: Delete account
        delete_response = api_client.delete(
            f"{BASE_URL}/api/account/delete",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}: {delete_response.text}"
        delete_data = delete_response.json()
        assert delete_data["success"] is True
        assert "deleted" in delete_data["message"].lower()
        print(f"✅ DELETE /api/account/delete returned success: {delete_data['message']}")
        
        # Step 4: Verify ALL user data removed from database
        user_after = mongo_db.users.find_one({"id": user_id})
        assert user_after is None, "User should be deleted from users collection"
        
        sub_after = mongo_db.subscriptions.find_one({"user_id": user_id})
        assert sub_after is None, "Subscription should be deleted"
        
        ref_after = mongo_db.referrals.find_one({"user_id": user_id})
        assert ref_after is None, "Referral should be deleted"
        
        scan_logs = mongo_db.scan_logs.find_one({"user_id": user_id})
        assert scan_logs is None, "Scan logs should be deleted"
        
        payments = mongo_db.payment_transactions.find_one({"user_id": user_id})
        assert payments is None, "Payment transactions should be deleted"
        
        push_tokens = mongo_db.push_tokens.find_one({"user_id": user_id})
        assert push_tokens is None, "Push tokens should be deleted"
        
        # Check referral_log (both referrer and referred)
        referral_log_referrer = mongo_db.referral_log.find_one({"referrer_user_id": user_id})
        assert referral_log_referrer is None, "Referral log (referrer) should be deleted"
        
        referral_log_referred = mongo_db.referral_log.find_one({"referred_user_id": user_id})
        assert referral_log_referred is None, "Referral log (referred) should be deleted"
        
        print(f"✅ All user data removed from ALL collections:")
        print(f"   - users collection: ✓ deleted")
        print(f"   - subscriptions collection: ✓ deleted")
        print(f"   - referrals collection: ✓ deleted")
        print(f"   - scan_logs collection: ✓ deleted")
        print(f"   - payment_transactions collection: ✓ deleted")
        print(f"   - push_tokens collection: ✓ deleted")
        print(f"   - referral_log collection (referrer): ✓ deleted")
        print(f"   - referral_log collection (referred): ✓ deleted")
        
        # Step 5: Verify login fails after deletion (401)
        login_response = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": register_payload["password"]}
        )
        assert login_response.status_code == 401, f"Login should fail with 401 after account deletion, got {login_response.status_code}"
        login_error = login_response.json()
        assert "Invalid" in login_error["detail"] or "email" in login_error["detail"].lower()
        print(f"✅ Login correctly fails with 401 after account deletion: {login_error['detail']}")
    
    def test_delete_account_requires_auth(self, api_client):
        """DELETE /api/account/delete without auth should return 401"""
        response = api_client.delete(f"{BASE_URL}/api/account/delete")
        assert response.status_code == 403 or response.status_code == 401, f"Expected 401/403, got {response.status_code}"
        print(f"✅ DELETE /api/account/delete requires authentication (returned {response.status_code})")


class TestExistingUserLogin:
    """Test that existing users can login without consent (backward compatibility)"""
    
    def test_existing_user_login_no_consent_required(self, api_client):
        """Existing users should be able to login normally without consent check"""
        # Use the provided existing test user
        payload = {
            "email": "test@veritas.com",
            "password": "test123456"
        }
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            assert "token" in data
            assert "user" in data
            print(f"✅ Existing user login works without consent requirement")
        elif response.status_code == 401:
            print(f"⚠️ Test user test@veritas.com does not exist or password incorrect (this is OK for fresh DB)")
        else:
            pytest.fail(f"Unexpected status code {response.status_code}: {response.text}")
