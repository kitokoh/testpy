import pytest
from fastapi.testclient import TestClient
from api.main import app
from unittest.mock import patch, MagicMock
from .test_auth_api import get_auth_token, TEST_USERNAME, TEST_PASSWORD # Import helper and test user credentials

client = TestClient(app)

@pytest.fixture(scope="module")
def auth_headers():
    token = get_auth_token(client, TEST_USERNAME, TEST_PASSWORD)
    return {"Authorization": f"Bearer {token}"}

def test_list_templates_success_authenticated(auth_headers):
    # Mock the db_manager.get_all_templates call
    mock_db_templates = [
        {'template_id': 1, 'template_name': 'Test Template 1', 'description': 'Desc 1', 'template_type': 'type_a', 'language_code': 'en'},
        {'template_id': 2, 'template_name': 'Test Template 2', 'description': 'Desc 2', 'template_type': 'type_b', 'language_code': 'fr'},
    ]
    with patch('api.templates.db_manager.get_all_templates', MagicMock(return_value=mock_db_templates)) as mock_get_all:
        response = client.get("/api/templates", headers=auth_headers)
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 2
        assert json_response[0]['template_name'] == 'Test Template 1'
        mock_get_all.assert_called_once_with(template_type_filter=None, language_code_filter=None)

def test_list_templates_with_filters_authenticated(auth_headers):
    mock_db_templates_filtered = [
        {'template_id': 3, 'template_name': 'Filtered Template', 'description': 'Desc 3', 'template_type': 'type_c', 'language_code': 'de'},
    ]
    with patch('api.templates.db_manager.get_all_templates', MagicMock(return_value=mock_db_templates_filtered)) as mock_get_all:
        response = client.get("/api/templates?template_type=type_c&language_code=de", headers=auth_headers)
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 1
        assert json_response[0]['template_name'] == 'Filtered Template'
        mock_get_all.assert_called_once_with(template_type_filter='type_c', language_code_filter='de')

def test_list_templates_no_templates_found_authenticated(auth_headers):
    with patch('api.templates.db_manager.get_all_templates', MagicMock(return_value=[])) as mock_get_all: # Return empty list
        response = client.get("/api/templates", headers=auth_headers)
        assert response.status_code == 200 # Should still be 200, but with empty list
        assert response.json() == []
        mock_get_all.assert_called_once()

def test_list_templates_unauthenticated():
    response = client.get("/api/templates")
    assert response.status_code == 401 # Unauthorized
    assert response.json()['detail'] == "Not authenticated" # Default message from FastAPI for missing auth
