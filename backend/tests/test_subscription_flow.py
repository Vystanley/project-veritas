import pytest
import requests
from datetime import datetime, timezone

# Test: Subscription management endpoints
class TestSubscriptionFlow:
    """Subscription status, upgrade, and cancellation tests."""

    def test_subscription_status_for_new_user(self, base_url, api_client):
        """Test GET /api/subscription/status returns free plan for new users."""
        # Register a fresh user for this test
        register_payload = {
            "name": "Sub Test User",
            "email": f"TEST_subscription_user_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        register_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        assert register_response.status_code == 200, f"Registration failed: {register_response.text}"
        token = register_response.json()["token"]
        
        # Get subscription status
        headers = {"Authorization": f"Bearer {token}"}
        response = api_client.get(f"{base_url}/api/subscription/status", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "plan" in data, "Response should contain 'plan' field"
        assert data["plan"] == "free", f"New user should have 'free' plan, got {data['plan']}"
        assert "scans_used" in data, "Response should contain 'scans_used' field"
        assert "scans_remaining" in data, "Response should contain 'scans_remaining' field"
        assert "is_premium" in data, "Response should contain 'is_premium' field"
        assert data["is_premium"] == False, "New user should not be premium"
        assert data["scans_remaining"] == 3, f"Free user should have 3 scans, got {data['scans_remaining']}"
        assert "period_resets_at" in data, "Response should contain 'period_resets_at' field"
        
        # Store token for later tests
        pytest.shared_sub_token = token
        print(f"✓ New user has free plan with {data['scans_remaining']} scans remaining")

    def test_subscribe_to_premium_monthly(self, base_url, api_client):
        """Test POST /api/subscription/subscribe with premium_monthly plan."""
        if not hasattr(pytest, 'shared_sub_token'):
            pytest.skip("No token available from previous test")
        
        headers = {"Authorization": f"Bearer {pytest.shared_sub_token}"}
        payload = {"plan": "premium_monthly"}
        
        response = api_client.post(f"{base_url}/api/subscription/subscribe", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response should contain 'success' field"
        assert data["success"] == True, "Subscription should be successful"
        assert "plan" in data, "Response should contain 'plan' field"
        assert data["plan"] == "premium_monthly", f"Expected 'premium_monthly', got {data['plan']}"
        assert "amount" in data, "Response should contain 'amount' field"
        assert data["amount"] == 13.99, f"Expected $13.99, got ${data['amount']}"
        assert "expires_at" in data, "Response should contain 'expires_at' field"
        print(f"✓ Premium monthly subscription activated: ${data['amount']}, expires {data['expires_at']}")

    def test_subscription_status_after_premium_upgrade(self, base_url, api_client):
        """Test GET /api/subscription/status returns premium_monthly after upgrade."""
        if not hasattr(pytest, 'shared_sub_token'):
            pytest.skip("No token available from previous test")
        
        headers = {"Authorization": f"Bearer {pytest.shared_sub_token}"}
        response = api_client.get(f"{base_url}/api/subscription/status", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["plan"] == "premium_monthly", f"Expected 'premium_monthly', got {data['plan']}"
        assert data["is_premium"] == True, "User should be premium"
        assert data["scans_remaining"] == 175, f"Premium user should have 175 scans cap, got {data['scans_remaining']}"
        assert "expires_at" in data, "Premium user should have expiration date"
        assert data["expires_at"] is not None, "Premium user should have non-null expiration"
        print(f"✓ User upgraded to premium: {data['scans_remaining']} scans remaining this month")

    def test_subscribe_to_premium_annual(self, base_url, api_client):
        """Test POST /api/subscription/subscribe with premium_annual plan."""
        # Create a new test user for annual plan
        register_payload = {
            "name": "Annual Test User",
            "email": f"TEST_annual_user_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        assert reg_response.status_code == 200, f"Registration failed: {reg_response.text}"
        token = reg_response.json()["token"]
        
        # Subscribe to annual plan
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"plan": "premium_annual"}
        
        response = api_client.post(f"{base_url}/api/subscription/subscribe", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True, "Subscription should be successful"
        assert data["plan"] == "premium_annual", f"Expected 'premium_annual', got {data['plan']}"
        assert data["amount"] == 119.00, f"Expected $119.00, got ${data['amount']}"
        assert "expires_at" in data, "Response should contain 'expires_at' field"
        print(f"✓ Premium annual subscription activated: ${data['amount']}, expires {data['expires_at']}")
        
        # Verify subscription status shows annual plan
        status_response = api_client.get(f"{base_url}/api/subscription/status", headers=headers)
        status_data = status_response.json()
        assert status_data["plan"] == "premium_annual", f"Expected 'premium_annual', got {status_data['plan']}"
        assert status_data["is_premium"] == True, "User should be premium"
        print(f"✓ Annual plan confirmed in status endpoint")

    def test_cancel_subscription(self, base_url, api_client):
        """Test POST /api/subscription/cancel downgrades to free plan."""
        if not hasattr(pytest, 'shared_sub_token'):
            pytest.skip("No token available from previous test")
        
        headers = {"Authorization": f"Bearer {pytest.shared_sub_token}"}
        response = api_client.post(f"{base_url}/api/subscription/cancel", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response should contain 'success' field"
        assert data["success"] == True, "Cancellation should be successful"
        assert data["plan"] == "free", f"Expected 'free' after cancellation, got {data['plan']}"
        print(f"✓ Subscription cancelled, downgraded to free plan")
        
        # Verify status shows free plan
        status_response = api_client.get(f"{base_url}/api/subscription/status", headers=headers)
        status_data = status_response.json()
        assert status_data["plan"] == "free", f"Expected 'free', got {status_data['plan']}"
        assert status_data["is_premium"] == False, "User should not be premium after cancellation"
        assert status_data["scans_remaining"] == 3, "Free user should have 3 scans remaining"
        print(f"✓ Free plan confirmed after cancellation: {status_data['scans_remaining']} scans")

    def test_invalid_plan_subscription_returns_400(self, base_url, api_client):
        """Test subscribing with invalid plan name returns 400."""
        if not hasattr(pytest, 'shared_sub_token'):
            pytest.skip("No token available from previous test")
        
        headers = {"Authorization": f"Bearer {pytest.shared_sub_token}"}
        payload = {"plan": "invalid_plan"}
        
        response = api_client.post(f"{base_url}/api/subscription/subscribe", json=payload, headers=headers)
        assert response.status_code == 400, f"Expected 400 for invalid plan, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Error response should contain 'detail' field"
        print(f"✓ Invalid plan correctly rejected: {data['detail']}")


# Test: Rate limiting and scan counter
class TestRateLimiting:
    """Test free user rate limits and scan counter functionality."""

    def test_free_user_scan_limit_reached(self, base_url, api_client, mongo_db):
        """Test free users get 429 error after 3 scans in a week."""
        # Create a fresh test user
        register_payload = {
            "name": "Rate Limit Test User",
            "email": f"TEST_ratelimit_user_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        assert reg_response.status_code == 200, f"Registration failed: {reg_response.text}"
        token = reg_response.json()["token"]
        user_id = reg_response.json()["user"]["id"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Manually create 3 scan_logs for this week
        from datetime import timedelta
        week_start = datetime.now(timezone.utc) - timedelta(days=datetime.now(timezone.utc).weekday())
        for i in range(3):
            mongo_db.scan_logs.insert_one({
                "user_id": user_id,
                "video_url": f"https://example.com/video{i}",
                "check_id": f"test_check_{i}",
                "created_at": (week_start + timedelta(days=i)).isoformat()
            })
        print(f"✓ Created 3 scan logs for user {user_id}")
        
        # Verify subscription status shows 0 scans remaining
        status_response = api_client.get(f"{base_url}/api/subscription/status", headers=headers)
        status_data = status_response.json()
        assert status_data["scans_used"] == 3, f"Expected 3 scans used, got {status_data['scans_used']}"
        assert status_data["scans_remaining"] == 0, f"Expected 0 scans remaining, got {status_data['scans_remaining']}"
        print(f"✓ Status shows scans_used=3, scans_remaining=0")
        
        # Try to perform a 4th scan - should get 429
        # NOTE: We're NOT actually calling fact-check with a real video (too slow)
        # Instead, we're testing the limit logic would trigger if we had 3 scans
        # The actual fact-check endpoint will call check_scan_limit() which will raise 429
        
        # To test the 429 response, we need to call fact-check endpoint
        # But we'll use an invalid URL to fail fast (we only care about the rate limit check)
        payload = {"video_url": "http://invalid-url-for-rate-limit-test.com/video"}
        response = api_client.post(f"{base_url}/api/fact-check", json=payload, headers=headers)
        assert response.status_code == 429, f"Expected 429 for rate limit, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data, "Error response should contain 'detail' field"
        assert "free scans" in data["detail"].lower(), f"Expected free scan limit message, got: {data['detail']}"
        print(f"✓ Rate limit enforced: {data['detail']}")

    def test_premium_user_high_scan_limit(self, base_url, api_client, mongo_db):
        """Test premium users have 175 scan cap per month."""
        # Create a premium test user
        register_payload = {
            "name": "Premium Scan Test User",
            "email": f"TEST_premium_scan_{datetime.now(timezone.utc).timestamp()}@example.com",
            "password": "testpass123"
        }
        reg_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        assert reg_response.status_code == 200, f"Registration failed: {reg_response.text}"
        token = reg_response.json()["token"]
        user_id = reg_response.json()["user"]["id"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Upgrade to premium
        subscribe_response = api_client.post(
            f"{base_url}/api/subscription/subscribe",
            json={"plan": "premium_monthly"},
            headers=headers
        )
        assert subscribe_response.status_code == 200, "Subscription failed"
        print(f"✓ User upgraded to premium")
        
        # Manually create 174 scan_logs for this month (just below cap)
        from datetime import timedelta
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for i in range(174):
            mongo_db.scan_logs.insert_one({
                "user_id": user_id,
                "video_url": f"https://example.com/video{i}",
                "check_id": f"test_check_{i}",
                "created_at": (month_start + timedelta(hours=i)).isoformat()
            })
        print(f"✓ Created 174 scan logs for premium user")
        
        # Verify subscription status shows 1 scan remaining
        status_response = api_client.get(f"{base_url}/api/subscription/status", headers=headers)
        status_data = status_response.json()
        assert status_data["scans_used"] == 174, f"Expected 174 scans used, got {status_data['scans_used']}"
        assert status_data["scans_remaining"] == 1, f"Expected 1 scan remaining, got {status_data['scans_remaining']}"
        print(f"✓ Premium user status: scans_used=174, scans_remaining=1")
        
        # Create 1 more scan log (reaching cap of 175)
        mongo_db.scan_logs.insert_one({
            "user_id": user_id,
            "video_url": "https://example.com/video_175",
            "check_id": "test_check_175",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Verify status shows 0 remaining
        status_response = api_client.get(f"{base_url}/api/subscription/status", headers=headers)
        status_data = status_response.json()
        assert status_data["scans_used"] == 175, f"Expected 175 scans used, got {status_data['scans_used']}"
        assert status_data["scans_remaining"] == 0, f"Expected 0 scans remaining, got {status_data['scans_remaining']}"
        print(f"✓ Premium user at cap: scans_used=175, scans_remaining=0")
        
        # Try to perform scan when at cap - should get 429
        payload = {"video_url": "http://invalid-url-for-rate-limit-test.com/video"}
        response = api_client.post(f"{base_url}/api/fact-check", json=payload, headers=headers)
        assert response.status_code == 429, f"Expected 429 for monthly cap, got {response.status_code}"
        
        data = response.json()
        assert "monthly scan limit" in data["detail"].lower(), f"Expected monthly limit message, got: {data['detail']}"
        print(f"✓ Premium monthly cap enforced: {data['detail']}")
