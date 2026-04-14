import pytest
import requests
import os
from datetime import datetime, timezone

# Backend tests for iteration 3 new features:
# - Stripe payment endpoints (checkout, status, webhook)
# - Referral program (info, apply)
# - Subscription cancel endpoint
# - Notification schedule endpoint

class TestStripePaymentEndpoints:
    """Stripe integration tests - checkout, status, webhook."""

    def test_checkout_creates_stripe_session_monthly(self, base_url, api_client):
        """Test POST /api/payments/checkout creates Stripe session for monthly plan."""
        # Register a new user
        register_payload = {
            "name": "Stripe Test User Monthly",
            "email": f"TEST_stripe_monthly_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        assert reg_response.status_code == 200, f"Registration failed: {reg_response.text}"
        token = reg_response.json()["token"]

        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "plan": "premium_monthly",
            "origin_url": "https://video-truth-8.preview.emergentagent.com"
        }

        response = api_client.post(f"{base_url}/api/payments/checkout", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "url" in data, "Response should contain 'url' field (Stripe checkout URL)"
        assert "session_id" in data, "Response should contain 'session_id' field"
        assert data["url"].startswith("https://"), f"URL should be HTTPS, got {data['url']}"
        assert "checkout.stripe.com" in data["url"] or "integrations.emergentagent.com" in data["url"], "URL should point to Stripe"
        
        # Store session_id for next test
        pytest.stripe_session_id = data["session_id"]
        print(f"✓ Stripe checkout session created: {data['session_id'][:20]}... URL: {data['url'][:60]}...")

    def test_checkout_creates_stripe_session_annual(self, base_url, api_client):
        """Test POST /api/payments/checkout creates Stripe session for annual plan."""
        # Register a new user
        register_payload = {
            "name": "Stripe Test User Annual",
            "email": f"TEST_stripe_annual_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        assert reg_response.status_code == 200, f"Registration failed: {reg_response.text}"
        token = reg_response.json()["token"]

        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "plan": "premium_annual",
            "origin_url": "https://video-truth-8.preview.emergentagent.com"
        }

        response = api_client.post(f"{base_url}/api/payments/checkout", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "url" in data, "Response should contain 'url' field"
        assert "session_id" in data, "Response should contain 'session_id' field"
        print(f"✓ Stripe annual checkout session created: {data['session_id'][:20]}...")

    def test_checkout_rejects_invalid_plan(self, base_url, api_client):
        """Test POST /api/payments/checkout rejects invalid plan names."""
        # Register a new user
        register_payload = {
            "name": "Invalid Plan Test User",
            "email": f"TEST_invalid_plan_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        token = reg_response.json()["token"]

        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "plan": "premium_lifetime",  # Invalid plan
            "origin_url": "https://video-truth-8.preview.emergentagent.com"
        }

        response = api_client.post(f"{base_url}/api/payments/checkout", json=payload, headers=headers)
        assert response.status_code == 400, f"Expected 400 for invalid plan, got {response.status_code}"

        data = response.json()
        assert "detail" in data, "Error response should contain 'detail' field"
        assert "invalid plan" in data["detail"].lower(), f"Expected 'Invalid plan' error, got: {data['detail']}"
        print(f"✓ Invalid plan correctly rejected: {data['detail']}")

    def test_payment_status_endpoint(self, base_url, api_client):
        """Test GET /api/payments/status/{session_id} returns payment status."""
        if not hasattr(pytest, 'stripe_session_id'):
            pytest.skip("No Stripe session_id available from checkout test")

        # Register a new user for this test
        register_payload = {
            "name": "Payment Status Test User",
            "email": f"TEST_payment_status_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        token = reg_response.json()["token"]

        headers = {"Authorization": f"Bearer {token}"}
        
        response = api_client.get(f"{base_url}/api/payments/status/{pytest.stripe_session_id}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "status" in data, "Response should contain 'status' field"
        assert "payment_status" in data, "Response should contain 'payment_status' field"
        assert "amount_total" in data, "Response should contain 'amount_total' field"
        assert "currency" in data, "Response should contain 'currency' field"
        
        # Payment won't be 'paid' without user completing checkout on Stripe's page
        assert data["payment_status"] in ["unpaid", "paid", "no_payment_required"], f"Unexpected payment_status: {data['payment_status']}"
        print(f"✓ Payment status retrieved: status={data['status']}, payment_status={data['payment_status']}, amount={data['amount_total']}")

    def test_webhook_stripe_endpoint_exists(self, base_url, api_client):
        """Test POST /api/webhook/stripe endpoint exists and responds."""
        # Webhook endpoint should handle POST requests
        # We won't test with real Stripe signature, just verify endpoint exists
        response = api_client.post(f"{base_url}/api/webhook/stripe", json={})
        
        # Endpoint should return 200 even for invalid webhook (graceful handling)
        # The actual webhook handler returns {"received": True} even on errors
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "received" in data, "Webhook response should contain 'received' field"
        assert data["received"] == True, "Webhook should acknowledge receipt"
        print(f"✓ Webhook endpoint exists and responds: {data}")


class TestReferralProgram:
    """Referral program tests - info, apply code, bonus scans."""

    def test_referral_info_returns_code(self, base_url, api_client):
        """Test GET /api/referral/info returns user's referral code."""
        # Register a new user
        register_payload = {
            "name": "Referral Test User",
            "email": f"TEST_referral_user_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        assert reg_response.status_code == 200, f"Registration failed: {reg_response.text}"
        token = reg_response.json()["token"]

        headers = {"Authorization": f"Bearer {token}"}
        response = api_client.get(f"{base_url}/api/referral/info", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "code" in data, "Response should contain 'code' field"
        assert "referred_count" in data, "Response should contain 'referred_count' field"
        assert "bonus_scans_earned" in data, "Response should contain 'bonus_scans_earned' field"
        assert len(data["code"]) == 8, f"Referral code should be 8 chars, got {len(data['code'])}"
        assert data["referred_count"] == 0, "New user should have 0 referrals"
        assert data["bonus_scans_earned"] == 0, "New user should have 0 bonus scans earned"
        
        # Store for next test
        pytest.referrer_code = data["code"]
        pytest.referrer_token = token
        print(f"✓ Referral code generated: {data['code']}, referred_count={data['referred_count']}, bonus_scans_earned={data['bonus_scans_earned']}")

    def test_apply_referral_code_gives_bonus(self, base_url, api_client):
        """Test POST /api/referral/apply gives bonus scans to both users."""
        if not hasattr(pytest, 'referrer_code'):
            pytest.skip("No referral code from previous test")

        # Create a NEW user who will use the referral code
        register_payload = {
            "name": "Referred User",
            "email": f"TEST_referred_user_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        assert reg_response.status_code == 200, f"Registration failed: {reg_response.text}"
        referred_token = reg_response.json()["token"]
        referred_user_id = reg_response.json()["user"]["id"]

        # Apply referral code
        headers = {"Authorization": f"Bearer {referred_token}"}
        payload = {"referral_code": pytest.referrer_code}
        response = api_client.post(f"{base_url}/api/referral/apply", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "success" in data, "Response should contain 'success' field"
        assert data["success"] == True, "Referral application should succeed"
        assert "bonus_scans" in data, "Response should contain 'bonus_scans' field"
        assert data["bonus_scans"] == 3, f"Expected 3 bonus scans, got {data['bonus_scans']}"
        assert "message" in data, "Response should contain 'message' field"
        print(f"✓ Referral code applied successfully: {data['message']}")

        # Verify referred user got bonus scans in subscription
        sub_response = api_client.get(f"{base_url}/api/subscription/status", headers=headers)
        sub_data = sub_response.json()
        assert sub_data["bonus_scans"] == 3, f"Referred user should have 3 bonus scans, got {sub_data['bonus_scans']}"
        assert sub_data["scans_remaining"] == 6, f"Referred user should have 6 total scans (3 free + 3 bonus), got {sub_data['scans_remaining']}"
        print(f"✓ Referred user has bonus scans: bonus_scans={sub_data['bonus_scans']}, total_remaining={sub_data['scans_remaining']}")

        # Verify referrer also got bonus scans
        referrer_headers = {"Authorization": f"Bearer {pytest.referrer_token}"}
        referrer_sub_response = api_client.get(f"{base_url}/api/subscription/status", headers=referrer_headers)
        referrer_sub_data = referrer_sub_response.json()
        assert referrer_sub_data["bonus_scans"] == 3, f"Referrer should have 3 bonus scans, got {referrer_sub_data['bonus_scans']}"
        print(f"✓ Referrer has bonus scans: bonus_scans={referrer_sub_data['bonus_scans']}")

        # Verify referrer's referral_info updated
        referrer_info_response = api_client.get(f"{base_url}/api/referral/info", headers=referrer_headers)
        referrer_info_data = referrer_info_response.json()
        assert referrer_info_data["referred_count"] == 1, f"Referrer should have 1 referral, got {referrer_info_data['referred_count']}"
        assert referrer_info_data["bonus_scans_earned"] == 3, f"Referrer should have earned 3 bonus scans, got {referrer_info_data['bonus_scans_earned']}"
        print(f"✓ Referrer info updated: referred_count={referrer_info_data['referred_count']}, bonus_scans_earned={referrer_info_data['bonus_scans_earned']}")

    def test_apply_own_referral_code_rejected(self, base_url, api_client):
        """Test POST /api/referral/apply rejects user's own referral code."""
        # Create a new user
        register_payload = {
            "name": "Self Referral Test User",
            "email": f"TEST_self_referral_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        token = reg_response.json()["token"]

        # Get user's own referral code
        headers = {"Authorization": f"Bearer {token}"}
        info_response = api_client.get(f"{base_url}/api/referral/info", headers=headers)
        own_code = info_response.json()["code"]

        # Try to apply own code
        payload = {"referral_code": own_code}
        response = api_client.post(f"{base_url}/api/referral/apply", json=payload, headers=headers)
        assert response.status_code == 400, f"Expected 400 for own code, got {response.status_code}"

        data = response.json()
        assert "detail" in data, "Error response should contain 'detail' field"
        assert "own referral code" in data["detail"].lower(), f"Expected 'own referral code' error, got: {data['detail']}"
        print(f"✓ Own referral code correctly rejected: {data['detail']}")

    def test_apply_referral_code_twice_rejected(self, base_url, api_client):
        """Test POST /api/referral/apply rejects duplicate application."""
        # Create fresh users for duplicate test
        # User 1: Creates referral code
        reg1_payload = {
            "name": "Referrer Duplicate Test",
            "email": f"TEST_referrer_dup_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg1_response = api_client.post(f"{base_url}/api/auth/register", json=reg1_payload)
        token1 = reg1_response.json()["token"]
        headers1 = {"Authorization": f"Bearer {token1}"}
        info_response = api_client.get(f"{base_url}/api/referral/info", headers=headers1)
        code = info_response.json()["code"]

        # User 2: Applies code first time
        reg2_payload = {
            "name": "Referred Duplicate Test",
            "email": f"TEST_referred_dup_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg2_response = api_client.post(f"{base_url}/api/auth/register", json=reg2_payload)
        token2 = reg2_response.json()["token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # First application - should succeed
        apply1_response = api_client.post(f"{base_url}/api/referral/apply", json={"referral_code": code}, headers=headers2)
        assert apply1_response.status_code == 200, "First application should succeed"
        print(f"✓ First referral application succeeded")

        # Second application - should fail
        apply2_response = api_client.post(f"{base_url}/api/referral/apply", json={"referral_code": code}, headers=headers2)
        assert apply2_response.status_code == 400, f"Expected 400 for duplicate application, got {apply2_response.status_code}"
        
        data = apply2_response.json()
        assert "detail" in data, "Error response should contain 'detail' field"
        assert "already used" in data["detail"].lower(), f"Expected 'already used' error, got: {data['detail']}"
        print(f"✓ Duplicate referral application correctly rejected: {data['detail']}")


class TestSubscriptionCancel:
    """Test subscription cancellation endpoint."""

    def test_cancel_subscription_downgrades_to_free(self, base_url, api_client, mongo_db):
        """Test POST /api/subscription/cancel downgrades premium to free."""
        # Create a user
        register_payload = {
            "name": "Cancel Test User",
            "email": f"TEST_cancel_user_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        token = reg_response.json()["token"]
        user_id = reg_response.json()["user"]["id"]

        headers = {"Authorization": f"Bearer {token}"}
        
        # First verify user is free
        status1 = api_client.get(f"{base_url}/api/subscription/status", headers=headers)
        assert status1.json()["plan"] == "free", "User should start as free"

        # Manually set user to premium in database (simulating successful Stripe payment)
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        mongo_db.subscriptions.update_one(
            {"user_id": user_id},
            {"$set": {
                "plan": "premium_monthly",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": expires_at.isoformat()
            }}
        )
        print(f"✓ User manually upgraded to premium in DB")

        # Verify premium status
        status2 = api_client.get(f"{base_url}/api/subscription/status", headers=headers)
        assert status2.json()["is_premium"] == True, "User should be premium"

        # Cancel subscription
        cancel_response = api_client.post(f"{base_url}/api/subscription/cancel", headers=headers)
        assert cancel_response.status_code == 200, f"Expected 200, got {cancel_response.status_code}: {cancel_response.text}"

        data = cancel_response.json()
        assert "success" in data, "Response should contain 'success' field"
        assert data["success"] == True, "Cancellation should succeed"
        assert data["plan"] == "free", f"Expected 'free' plan after cancel, got {data['plan']}"
        print(f"✓ Subscription cancelled: {data}")

        # Verify status shows free
        status3 = api_client.get(f"{base_url}/api/subscription/status", headers=headers)
        status3_data = status3.json()
        assert status3_data["plan"] == "free", f"User should be free after cancel, got {status3_data['plan']}"
        assert status3_data["is_premium"] == False, "User should not be premium"
        assert status3_data["expires_at"] is None, "Free user should have no expiration"
        print(f"✓ Status confirmed free plan: {status3_data['plan']}")


class TestNotificationSchedule:
    """Test notification schedule endpoint."""

    def test_notification_schedule_returns_next_reset(self, base_url, api_client):
        """Test GET /api/notifications/schedule returns next reset date."""
        # Create a new user
        register_payload = {
            "name": "Notification Test User",
            "email": f"TEST_notification_user_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        token = reg_response.json()["token"]

        headers = {"Authorization": f"Bearer {token}"}
        response = api_client.get(f"{base_url}/api/notifications/schedule", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "next_reset" in data, "Response should contain 'next_reset' field"
        assert "next_reset_day" in data, "Response should contain 'next_reset_day' field"
        
        # Verify next_reset is a valid ISO datetime string
        try:
            reset_date = datetime.fromisoformat(data["next_reset"].replace('Z', '+00:00'))
            assert reset_date > datetime.now(timezone.utc), "Next reset should be in the future"
        except ValueError:
            pytest.fail(f"next_reset is not a valid ISO datetime: {data['next_reset']}")
        
        # Verify next_reset_day is a readable string
        assert len(data["next_reset_day"]) > 0, "next_reset_day should not be empty"
        print(f"✓ Notification schedule: next_reset={data['next_reset']}, next_reset_day={data['next_reset_day']}")
