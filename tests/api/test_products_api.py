import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends, HTTPException
import sqlite3
import os
import sys

# Add project root to sys.path to allow importing project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from api.products import router as products_router
from api.auth import get_current_active_user # Import the dependency
from db.cruds import products_crud # To interact with DB directly for setup/assertions
from models import ProductCreate, ProductResponse, ProductUpdate, UserInDB # Pydantic models

# Global variable for the database connection
DATABASE_URL = ":memory:"
conn = None
client = None
app = None

# --- Mock Authentication ---
async def override_get_current_active_user() -> UserInDB:
    # Return a mock/test user
    return UserInDB(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        role="admin",
        is_active=True,
        user_id="test_user_uuid" # Example UUID
    )

# --- Test Setup & Teardown ---
def setup_module(module):
    global conn, client, app

    # Create an in-memory SQLite database
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create Products table (schema similar to db/init_schema.py for Products)
    cursor.execute("""
        CREATE TABLE Products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            product_code TEXT UNIQUE,
            description TEXT,
            category TEXT,
            language_code TEXT DEFAULT 'fr',
            base_unit_price REAL NOT NULL,
            unit_of_measure TEXT,
            weight REAL,
            dimensions TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TEXT
        )
    """)
    # Create ProductMediaLinks table as it's used by products_crud.get_product_by_id and others implicitly
    # to return media_links. If not present, those calls might fail.
    cursor.execute("""
        CREATE TABLE ProductMediaLinks (
            link_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            media_item_id TEXT NOT NULL,
            display_order INTEGER DEFAULT 0,
            alt_text TEXT,
            created_at TEXT,
            FOREIGN KEY (product_id) REFERENCES Products(product_id) ON DELETE CASCADE,
            UNIQUE (product_id, media_item_id)
        )
    """)
    # Mock MediaItems table if product_media_links_crud.get_media_links_for_product joins with it
    cursor.execute("""
        CREATE TABLE MediaItems (
            media_item_id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            item_type TEXT,
            filepath TEXT,
            thumbnail_path TEXT,
            uploader_user_id TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    conn.commit()

    # Pass the connection to the CRUD instance if it expects it (it uses @_manage_conn)
    # products_crud.products_crud_instance.conn = conn # Not needed due to @_manage_conn

    # Setup FastAPI app and TestClient
    app = FastAPI()
    app.include_router(products_router)

    # Override the dependency for authentication
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    client = TestClient(app)

    # Monkeypatch products_crud to use the test_conn for its @_manage_conn decorator
    # This is crucial for CRUD operations to use the in-memory DB
    original_get_db_connection = products_crud.get_db_connection
    def get_test_db_connection():
        return conn
    products_crud.get_db_connection = get_test_db_connection

    # Also patch for product_media_links_crud if it's used for media_links formatting
    if hasattr(products_crud, 'product_media_links_crud') and \
       hasattr(products_crud.product_media_links_crud, 'get_db_connection'):
        products_crud.product_media_links_crud.get_db_connection = get_test_db_connection


def teardown_module(module):
    global conn
    if conn:
        conn.close()
    # Restore original get_db_connection if necessary, though for module scope, not strictly needed.


# --- Helper function to add a product directly to DB for testing GET/PUT/DELETE ---
def add_product_direct_db(name="Direct Product", code="DP001", price=10.0, lang="en"):
    data = {
        "product_name": name,
        "product_code": code,
        "base_unit_price": price,
        "language_code": lang,
        "description": "Test desc",
    }
    result = products_crud.add_product(data, conn=conn)
    assert result['success'], f"Failed to add product directly to DB: {result.get('error')}"
    return result['id']

# --- Test Cases ---

def test_create_product_api():
    product_data = {
        "product_name": "API Test Product",
        "product_code": "API001",
        "base_unit_price": 99.99,
        "description": "Tested via API",
        "language_code": "en",
        "category": "API_TEST"
    }
    response = client.post("/api/products", json=product_data)
    assert response.status_code == 201
    data = response.json()
    assert data["product_name"] == product_data["product_name"]
    assert data["product_code"] == product_data["product_code"]
    assert data["base_unit_price"] == product_data["base_unit_price"]
    assert "product_id" in data
    # Check if it's in the DB
    db_product = products_crud.get_product_by_id(data["product_id"], conn=conn)
    assert db_product is not None
    assert db_product["product_code"] == product_data["product_code"]

def test_create_product_duplicate_code_api():
    product_data1 = {
        "product_name": "API Unique Product 1",
        "product_code": "API_DUP001",
        "base_unit_price": 10.00,
        "language_code": "en"
    }
    response1 = client.post("/api/products", json=product_data1)
    assert response1.status_code == 201

    product_data2 = {
        "product_name": "API Unique Product 2",
        "product_code": "API_DUP001", # Same code
        "base_unit_price": 20.00,
        "language_code": "fr"
    }
    response2 = client.post("/api/products", json=product_data2)
    # CRUD add_product returns error for unique constraint violation,
    # and API endpoint converts this to HTTP 400
    assert response2.status_code == 400
    assert "violated" in response2.json()["detail"].lower() # Or specific message

def test_get_product_by_code_api_exists():
    product_code = "GET_BY_CODE_001"
    # Add product directly to DB for this test
    product_id = add_product_direct_db(name="Product for Code Get", code=product_code, price=25.0)

    response = client.get(f"/api/products/code/{product_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == product_id
    assert data["product_code"] == product_code
    assert data["product_name"] == "Product for Code Get"

def test_get_product_by_code_api_not_exists():
    response = client.get("/api/products/code/NON_EXISTENT_CODE_XYZ")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_update_product_api():
    product_id = add_product_direct_db(name="Product to Update", code="PU001", price=50.0)

    update_payload = {
        "product_name": "Updated Product Name via API",
        "product_code": "PU001_UPDATED",
        "base_unit_price": 55.55,
        "description": "Updated Description"
        # language_code is not made optional in ProductUpdate in models.py, so it should be there or test will fail
        # Assuming models.py ProductUpdate makes most fields optional
    }
    response = client.put(f"/api/products/{product_id}", json=update_payload)
    assert response.status_code == 200 # Assuming PUT returns 200 on success
    data = response.json()
    assert data["product_name"] == update_payload["product_name"]
    assert data["product_code"] == update_payload["product_code"]
    assert data["base_unit_price"] == update_payload["base_unit_price"]
    assert data["description"] == update_payload["description"]

    # Verify in DB
    db_product = products_crud.get_product_by_id(product_id, conn=conn)
    assert db_product["product_name"] == update_payload["product_name"]
    assert db_product["product_code"] == update_payload["product_code"]

def test_update_product_api_non_existent():
    update_payload = {"product_name": "Trying to Update Non-existent"}
    response = client.put("/api/products/99999", json=update_payload) # Assuming 99999 doesn't exist
    assert response.status_code == 404 # API should return 404 if product not found for update

# Placeholder for more tests (e.g., specific field validations, edge cases)

# Example of how to run with pytest:
# Ensure pytest is installed: pip install pytest
# Run from the project root directory: pytest tests/api/test_products_api.py
