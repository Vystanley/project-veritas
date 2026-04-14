import pytest
import requests

# Test: Health check endpoint
class TestHealthCheck:
    """Health check endpoint tests."""

    def test_health_endpoint_returns_200(self, base_url, api_client):
        """Test GET /api/health returns 200 OK."""
        response = api_client.get(f"{base_url}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Response should contain 'status' field"
        assert data["status"] == "ok", f"Expected status 'ok', got {data['status']}"
        assert "service" in data, "Response should contain 'service' field"
        print(f"✓ Health check passed: {data}")


# Test: User registration and login flow
class TestAuthFlow:
    """Authentication flow tests: register, login, token validation."""

    def test_user_registration_success(self, base_url, api_client, test_user_credentials):
        """Test POST /api/auth/register creates a new user and returns token."""
        payload = {
            "name": test_user_credentials["name"],
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        }
        
        response = api_client.post(f"{base_url}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token" in data, "Response should contain 'token' field"
        assert "user" in data, "Response should contain 'user' field"
        assert data["user"]["name"] == test_user_credentials["name"], "User name mismatch"
        assert data["user"]["email"] == test_user_credentials["email"], "User email mismatch"
        assert "id" in data["user"], "User should have 'id' field"
        
        # Store token for later tests
        pytest.shared_token = data["token"]
        pytest.shared_user_id = data["user"]["id"]
        print(f"✓ User registration successful: {data['user']['email']}")

    def test_duplicate_registration_returns_400(self, base_url, api_client, test_user_credentials):
        """Test duplicate registration returns 400 Bad Request."""
        payload = {
            "name": test_user_credentials["name"],
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        }
        
        response = api_client.post(f"{base_url}/api/auth/register", json=payload)
        assert response.status_code == 400, f"Expected 400 for duplicate registration, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Error response should contain 'detail' field"
        assert "already registered" in data["detail"].lower(), f"Expected 'already registered' error, got: {data['detail']}"
        print(f"✓ Duplicate registration correctly rejected: {data['detail']}")

    def test_user_login_success(self, base_url, api_client, test_user_credentials):
        """Test POST /api/auth/login with valid credentials returns token."""
        payload = {
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"]
        }
        
        response = api_client.post(f"{base_url}/api/auth/login", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token" in data, "Response should contain 'token' field"
        assert "user" in data, "Response should contain 'user' field"
        assert data["user"]["email"] == test_user_credentials["email"], "User email mismatch"
        print(f"✓ User login successful: {data['user']['email']}")

    def test_login_with_invalid_email_returns_401(self, base_url, api_client):
        """Test login with non-existent email returns 401."""
        payload = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        response = api_client.post(f"{base_url}/api/auth/login", json=payload)
        assert response.status_code == 401, f"Expected 401 for invalid email, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Error response should contain 'detail' field"
        print(f"✓ Invalid email login correctly rejected: {data['detail']}")

    def test_login_with_invalid_password_returns_401(self, base_url, api_client, test_user_credentials):
        """Test login with wrong password returns 401."""
        payload = {
            "email": test_user_credentials["email"],
            "password": "wrongpassword123"
        }
        
        response = api_client.post(f"{base_url}/api/auth/login", json=payload)
        assert response.status_code == 401, f"Expected 401 for invalid password, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Error response should contain 'detail' field"
        print(f"✓ Invalid password login correctly rejected: {data['detail']}")

    def test_auth_me_with_valid_token(self, base_url, api_client, test_user_credentials):
        """Test GET /api/auth/me with Bearer token returns user data."""
        # Skip if no token was created in previous tests
        if not hasattr(pytest, 'shared_token'):
            pytest.skip("No token available from registration test")
        
        headers = {"Authorization": f"Bearer {pytest.shared_token}"}
        response = api_client.get(f"{base_url}/api/auth/me", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain 'id' field"
        assert "name" in data, "Response should contain 'name' field"
        assert "email" in data, "Response should contain 'email' field"
        assert data["email"] == test_user_credentials["email"], "Email mismatch"
        assert data["id"] == pytest.shared_user_id, "User ID mismatch"
        print(f"✓ Token validation successful: {data}")

    def test_auth_me_without_token_returns_403(self, base_url, api_client):
        """Test GET /api/auth/me without token returns 403."""
        response = api_client.get(f"{base_url}/api/auth/me")
        # HTTPBearer dependency will return 403 when no Authorization header is present
        assert response.status_code == 403, f"Expected 403 for missing token, got {response.status_code}"
        print(f"✓ Missing token correctly rejected with 403")

    def test_auth_me_with_invalid_token_returns_401(self, base_url, api_client):
        """Test GET /api/auth/me with invalid token returns 401."""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = api_client.get(f"{base_url}/api/auth/me", headers=headers)
        
        assert response.status_code == 401, f"Expected 401 for invalid token, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Error response should contain 'detail' field"
        print(f"✓ Invalid token correctly rejected: {data['detail']}")
