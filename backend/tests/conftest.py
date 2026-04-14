import pytest
import requests
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

@pytest.fixture(scope="session")
def base_url():
    """Get base URL from environment variable."""
    # Try EXPO_PUBLIC_BACKEND_URL first (from frontend .env)
    url = os.environ.get('EXPO_PUBLIC_BACKEND_URL')
    
    # If not set, try loading from frontend .env file
    if not url:
        frontend_env_path = Path(__file__).parent.parent.parent / 'frontend' / '.env'
        if frontend_env_path.exists():
            load_dotenv(frontend_env_path)
            url = os.environ.get('EXPO_PUBLIC_BACKEND_URL')
    
    if not url:
        pytest.fail("EXPO_PUBLIC_BACKEND_URL environment variable not set in backend or frontend .env")
    return url.rstrip('/')

@pytest.fixture
def api_client():
    """Shared requests session for API calls."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="session")
def test_user_credentials():
    """Test user credentials for authenticated requests."""
    return {
        "name": "TEST_User_Pytest",
        "email": f"TEST_pytest_user_{os.getpid()}@example.com",
        "password": "testpass123456"
    }

@pytest.fixture(scope="session")
def mongo_db():
    """MongoDB client for direct database operations (e.g., creating scan_logs for testing)."""
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    if not mongo_url or not db_name:
        pytest.fail("MONGO_URL or DB_NAME environment variable not set")
    
    client = MongoClient(mongo_url)
    db = client[db_name]
    yield db
    client.close()
