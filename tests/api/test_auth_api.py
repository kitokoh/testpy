import pytest
from fastapi.testclient import TestClient
from api.main import app # Import the FastAPI app from api.main
import db as db_manager # For mocking or setting up users
from unittest.mock import patch, MagicMock

client = TestClient(app)

# Test user credentials (ensure a test user exists or is mocked)
TEST_USERNAME = "testuser_api"
TEST_PASSWORD = "testpassword_api"
TEST_USER_ID = "test_user_api_uuid" # Example UUID

@pytest.fixture(scope="module", autouse=True)
def setup_test_user():
    # This fixture will run once per module to set up and tear down the test user.
    # Check if user exists
    user = db_manager.get_user_by_username(TEST_USERNAME)
    if not user:
        # Add a test user for authentication tests
        # In a real scenario, you might use a separate test database or more complex setup/teardown.
        # Hashing should be handled by add_user or a utility.
        # db_manager.add_user directly hashes the password.
        print(f"Attempting to add test user: {TEST_USERNAME}")
        added_user_id = db_manager.add_user({
            'user_id': TEST_USER_ID, # Provide a UUID if your add_user expects it or generates it
            'username': TEST_USERNAME,
            'password': TEST_PASSWORD, # db_manager.add_user will hash this
            'full_name': 'API Test User',
            'email': f'{TEST_USERNAME}@example.com',
            'role': 'user', # Or whatever role is appropriate
            'is_active': True
        })
        if not added_user_id:
            # Try to fetch again in case of race or if add_user returns None on pre-existence but doesn't error
            user_check = db_manager.get_user_by_username(TEST_USERNAME)
            if not user_check:
                 pytest.fail(f"Failed to create or find test user '{TEST_USERNAME}' for API tests.")
            else:
                 print(f"Found user {TEST_USERNAME} after initial add returned None.")
        else:
            print(f"Test user '{TEST_USERNAME}' added with ID: {added_user_id}")
    else:
        print(f"Test user '{TEST_USERNAME}' already exists.")
        # Ensure user is active for tests
        if not user.get('is_active'):
            db_manager.update_user(user['user_id'], {'is_active': True})
            print(f"Activated existing test user '{TEST_USERNAME}'.")


    yield # This is where the testing happens

    # Teardown: remove the test user
    # print(f"Attempting to remove test user: {TEST_USERNAME}")
    # user_to_delete = db_manager.get_user_by_username(TEST_USERNAME)
    # if user_to_delete:
    #     deleted = db_manager.delete_user(user_to_delete['user_id'])
    #     if deleted:
    #         print(f"Test user '{TEST_USERNAME}' removed successfully.")
    #     else:
    #         print(f"Failed to remove test user '{TEST_USERNAME}'. Manual cleanup might be needed.")
    # else:
    #     print(f"Test user '{TEST_USERNAME}' not found for deletion during teardown.")
    # For now, let's skip auto-deletion to avoid issues if tests fail mid-way or if user is needed across test files.
    # Manual cleanup or a separate cleanup script might be better for CI.
    pass


def test_login_for_access_token_success():
    response = client.post(
        "/api/auth/token",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    json_response = response.json()
    assert "access_token" in json_response
    assert json_response["token_type"] == "bearer"

def test_login_for_access_token_invalid_username():
    response = client.post(
        "/api/auth/token",
        data={"username": "wronguser", "password": TEST_PASSWORD}
    )
    assert response.status_code == 401 # Unauthorized
    json_response = response.json()
    assert json_response["detail"] == "Incorrect username or password"

def test_login_for_access_token_invalid_password():
    response = client.post(
        "/api/auth/token",
        data={"username": TEST_USERNAME, "password": "wrongpassword"}
    )
    assert response.status_code == 401 # Unauthorized
    json_response = response.json()
    assert json_response["detail"] == "Incorrect username or password"

# Helper to get a valid token for other tests
def get_auth_token(test_client, username, password) -> str:
    response = test_client.post(
        "/api/auth/token",
        data={"username": username, "password": password}
    )
    response.raise_for_status() # Raise an exception for bad status codes
    return response.json()["access_token"]
