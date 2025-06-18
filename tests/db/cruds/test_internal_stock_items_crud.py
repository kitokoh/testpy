import pytest
import sqlite3
import uuid
import json
from datetime import datetime, timedelta

# Module to be tested
from db.cruds import internal_stock_items_crud

@pytest.fixture
def db_conn():
    """
    Pytest fixture to set up an in-memory SQLite database with the
    InternalStockItems table for each test function.
    Yields a database connection and closes it after the test.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row  # Access columns by name
    cursor = conn.cursor()

    # Create the InternalStockItems table schema
    cursor.execute("""
    CREATE TABLE InternalStockItems (
        item_id TEXT PRIMARY KEY,
        item_name TEXT NOT NULL,
        item_code TEXT UNIQUE,
        description TEXT,
        category TEXT,
        manufacturer TEXT,
        supplier TEXT,
        unit_of_measure TEXT,
        current_stock_level INTEGER DEFAULT 0,
        custom_fields TEXT, -- Store as JSON
        is_deleted INTEGER DEFAULT 0,
        deleted_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # Add relevant indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_internalstockitems_item_name ON InternalStockItems(item_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_internalstockitems_item_code ON InternalStockItems(item_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_internalstockitems_category ON InternalStockItems(category)")

    conn.commit()
    yield conn
    conn.close()

# --- Test Cases ---

def test_add_item_minimal(db_conn):
    """Test adding an item with only the required field (item_name)."""
    item_data_minimal = {"item_name": "Test Item Minimal"}
    result = internal_stock_items_crud.add_item(item_data_minimal, conn=db_conn)
    assert result['success']
    assert 'id' in result

    retrieved = internal_stock_items_crud.get_item_by_id(result['id'], conn=db_conn)
    assert retrieved is not None
    assert retrieved['item_name'] == "Test Item Minimal"
    assert retrieved['current_stock_level'] == 0 # Check default value
    assert retrieved['is_deleted'] == 0

def test_add_item_full(db_conn):
    """Test adding an item with all optional fields."""
    custom_fields_dict = {"voltage": "5V", "color": "blue"}
    item_data_full = {
        "item_name": "Test Item Full",
        "item_code": "TIF001",
        "description": "A comprehensive test item.",
        "category": "Testing",
        "manufacturer": "Pytest Inc.",
        "supplier": "Fixture Supplies",
        "unit_of_measure": "pcs",
        "current_stock_level": 100,
        "custom_fields": custom_fields_dict
    }
    result = internal_stock_items_crud.add_item(item_data_full, conn=db_conn)
    assert result['success']
    item_id = result['id']

    retrieved = internal_stock_items_crud.get_item_by_id(item_id, conn=db_conn)
    assert retrieved is not None
    assert retrieved['item_name'] == item_data_full['item_name']
    assert retrieved['item_code'] == item_data_full['item_code']
    assert retrieved['description'] == item_data_full['description']
    assert retrieved['category'] == item_data_full['category']
    assert retrieved['manufacturer'] == item_data_full['manufacturer']
    assert retrieved['supplier'] == item_data_full['supplier']
    assert retrieved['unit_of_measure'] == item_data_full['unit_of_measure']
    assert retrieved['current_stock_level'] == item_data_full['current_stock_level']
    assert retrieved['custom_fields'] == custom_fields_dict # Should be parsed back to dict

def test_add_item_duplicate_code(db_conn):
    """Test that adding an item with a duplicate item_code fails."""
    item_data1 = {"item_name": "Item A", "item_code": "CODE123"}
    internal_stock_items_crud.add_item(item_data1, conn=db_conn)

    item_data2 = {"item_name": "Item B", "item_code": "CODE123"}
    result = internal_stock_items_crud.add_item(item_data2, conn=db_conn)
    assert not result['success']
    assert "already exists" in result.get('error', '').lower()

def test_get_item_by_id(db_conn):
    """Test fetching an item by its ID, including custom_fields parsing."""
    custom_data = {"size": "L", "material": "cotton"}
    add_result = internal_stock_items_crud.add_item({
        "item_name": "Specific ID Item",
        "custom_fields": json.dumps(custom_data) # Store as JSON string initially
    }, conn=db_conn)
    item_id = add_result['id']

    retrieved = internal_stock_items_crud.get_item_by_id(item_id, conn=db_conn)
    assert retrieved is not None
    assert retrieved['item_id'] == item_id
    assert retrieved['item_name'] == "Specific ID Item"
    assert retrieved['custom_fields'] == custom_data

def test_get_item_by_id_non_existent(db_conn):
    """Test fetching a non-existent item by ID."""
    retrieved = internal_stock_items_crud.get_item_by_id(str(uuid.uuid4()), conn=db_conn)
    assert retrieved is None

def test_get_item_by_code(db_conn):
    """Test fetching an item by its unique item_code."""
    item_code = "CODE_XYZ"
    internal_stock_items_crud.add_item({"item_name": "Code Item", "item_code": item_code}, conn=db_conn)

    retrieved = internal_stock_items_crud.get_item_by_code(item_code, conn=db_conn)
    assert retrieved is not None
    assert retrieved['item_code'] == item_code
    assert retrieved['item_name'] == "Code Item"

def test_get_item_by_code_non_existent(db_conn):
    """Test fetching a non-existent item by code."""
    retrieved = internal_stock_items_crud.get_item_by_code("NON_EXISTENT_CODE", conn=db_conn)
    assert retrieved is None

# --- Soft Delete Tests ---
def test_soft_delete_and_get_item_by_id_with_deleted_flag(db_conn):
    """Test soft deleting an item and retrieving it with include_deleted=True."""
    add_result = internal_stock_items_crud.add_item({"item_name": "To Be Deleted"}, conn=db_conn)
    item_id = add_result['id']

    # Soft delete
    delete_result = internal_stock_items_crud.delete_item(item_id, conn=db_conn)
    assert delete_result['success']

    # Should not be found by default
    retrieved_default = internal_stock_items_crud.get_item_by_id(item_id, conn=db_conn)
    assert retrieved_default is None

    # Should be found when include_deleted is True
    retrieved_with_deleted = internal_stock_items_crud.get_item_by_id(item_id, include_deleted=True, conn=db_conn)
    assert retrieved_with_deleted is not None
    assert retrieved_with_deleted['item_id'] == item_id
    assert retrieved_with_deleted['is_deleted'] == 1
    assert retrieved_with_deleted['deleted_at'] is not None

def test_soft_delete_and_get_item_by_code_with_deleted_flag(db_conn):
    """Test soft deleting an item and retrieving it by code with include_deleted=True."""
    item_code = "DEL_CODE_001"
    add_result = internal_stock_items_crud.add_item({"item_name": "Deletable Code Item", "item_code": item_code}, conn=db_conn)
    item_id = add_result['id']

    delete_result = internal_stock_items_crud.delete_item(item_id, conn=db_conn)
    assert delete_result['success']

    retrieved_default = internal_stock_items_crud.get_item_by_code(item_code, conn=db_conn)
    assert retrieved_default is None

    retrieved_with_deleted = internal_stock_items_crud.get_item_by_code(item_code, include_deleted=True, conn=db_conn)
    assert retrieved_with_deleted is not None
    assert retrieved_with_deleted['item_code'] == item_code
    assert retrieved_with_deleted['is_deleted'] == 1

# --- Get Items (List) Tests ---
@pytest.fixture
def sample_items(db_conn):
    """Fixture to pre-populate the DB with a variety of items for list testing."""
    items_data = [
        {"item_name": "Alpha Widget", "category": "Widgets", "manufacturer": "Mfg A", "supplier": "Sup X"},
        {"item_name": "Beta Widget", "category": "Widgets", "manufacturer": "Mfg B", "supplier": "Sup Y", "is_deleted": 1, "deleted_at": datetime.utcnow().isoformat()},
        {"item_name": "Gamma Gadget", "category": "Gadgets", "manufacturer": "Mfg A", "supplier": "Sup X"},
        {"item_name": "Delta Component", "category": "Components", "manufacturer": "Mfg C", "supplier": "Sup Z"},
        {"item_name": "Epsilon Widget", "category": "Widgets", "manufacturer": "Mfg A", "supplier": "Sup Y"},
    ]
    item_ids = []
    for data in items_data:
        # Handle soft delete fields if present
        item_to_add = data.copy()
        is_del = item_to_add.pop('is_deleted', 0)
        del_at = item_to_add.pop('deleted_at', None)

        res = internal_stock_items_crud.add_item(item_to_add, conn=db_conn)
        item_id = res['id']
        item_ids.append(item_id)
        if is_del: # If this item was marked for soft deletion in sample data
             internal_stock_items_crud.update_item(item_id, {"is_deleted": 1, "deleted_at": del_at}, conn=db_conn)
    return item_ids

def test_get_items_no_filters(db_conn, sample_items):
    """Test retrieving all non-deleted items without filters."""
    items = internal_stock_items_crud.get_items(conn=db_conn)
    assert len(items) == 4 # One of the sample items is soft-deleted

def test_get_items_include_deleted(db_conn, sample_items):
    """Test retrieving all items including soft-deleted ones."""
    items = internal_stock_items_crud.get_items(include_deleted=True, conn=db_conn)
    assert len(items) == 5

def test_get_items_filter_category(db_conn, sample_items):
    """Test filtering items by category."""
    items = internal_stock_items_crud.get_items(filters={"category": "Widgets"}, conn=db_conn)
    assert len(items) == 2 # Alpha, Epsilon (Beta is deleted)
    for item in items:
        assert item['category'] == "Widgets"

def test_get_items_filter_item_name_like(db_conn, sample_items):
    """Test filtering items by item_name using LIKE."""
    items = internal_stock_items_crud.get_items(filters={"item_name": "Widget"}, conn=db_conn)
    assert len(items) == 2 # Alpha, Epsilon
    assert all("Widget" in item['item_name'] for item in items)

def test_get_items_filter_manufacturer(db_conn, sample_items):
    items = internal_stock_items_crud.get_items(filters={"manufacturer": "Mfg A"}, conn=db_conn)
    assert len(items) == 3 # Alpha, Gamma, Epsilon
    assert all(item['manufacturer'] == "Mfg A" for item in items)

def test_get_items_pagination(db_conn, sample_items):
    """Test pagination with limit and offset."""
    # Get all non-deleted items first to know total (should be 4)
    all_active_items = internal_stock_items_crud.get_items(conn=db_conn)
    assert len(all_active_items) == 4

    # Page 1: limit 2
    items_page1 = internal_stock_items_crud.get_items(limit=2, offset=0, conn=db_conn)
    assert len(items_page1) == 2

    # Page 2: limit 2, offset 2
    items_page2 = internal_stock_items_crud.get_items(limit=2, offset=2, conn=db_conn)
    assert len(items_page2) == 2

    # Ensure items from page 1 and page 2 are different
    ids_page1 = {item['item_id'] for item in items_page1}
    ids_page2 = {item['item_id'] for item in items_page2}
    assert not (ids_page1 & ids_page2) # No overlap

    # Page with offset exceeding items
    items_offset_too_high = internal_stock_items_crud.get_items(limit=2, offset=4, conn=db_conn)
    assert len(items_offset_too_high) == 0


# --- Update Item Tests ---
def test_update_item_fields(db_conn):
    """Test updating various fields of an item."""
    add_result = internal_stock_items_crud.add_item({"item_name": "Original Name", "category": "Old Cat"}, conn=db_conn)
    item_id = add_result['id']

    custom_fields_new = {"color": "red", "warranty": "1y"}
    update_data = {
        "item_name": "Updated Name",
        "item_code": "UPDCODE001",
        "description": "New description.",
        "category": "New Cat",
        "manufacturer": "Updated Mfg",
        "supplier": "New Supplier",
        "unit_of_measure": "kg",
        "current_stock_level": 55,
        "custom_fields": custom_fields_new
    }
    update_result = internal_stock_items_crud.update_item(item_id, update_data, conn=db_conn)
    assert update_result['success']

    updated_item = internal_stock_items_crud.get_item_by_id(item_id, conn=db_conn)
    assert updated_item['item_name'] == "Updated Name"
    assert updated_item['item_code'] == "UPDCODE001"
    assert updated_item['category'] == "New Cat"
    assert updated_item['current_stock_level'] == 55
    assert updated_item['custom_fields'] == custom_fields_new
    assert updated_item['updated_at'] > updated_item['created_at']

def test_update_item_soft_delete_and_restore(db_conn):
    """Test soft deleting and then restoring an item via update_item."""
    add_result = internal_stock_items_crud.add_item({"item_name": "Item for Restore Test"}, conn=db_conn)
    item_id = add_result['id']

    # Soft delete
    time_before_delete = datetime.utcnow().isoformat()
    soft_delete_data = {"is_deleted": 1, "deleted_at": time_before_delete}
    update_result_delete = internal_stock_items_crud.update_item(item_id, soft_delete_data, conn=db_conn)
    assert update_result_delete['success']

    deleted_item = internal_stock_items_crud.get_item_by_id(item_id, include_deleted=True, conn=db_conn)
    assert deleted_item['is_deleted'] == 1
    assert deleted_item['deleted_at'] == time_before_delete

    # Restore
    restore_data = {"is_deleted": 0, "deleted_at": None}
    update_result_restore = internal_stock_items_crud.update_item(item_id, restore_data, conn=db_conn)
    assert update_result_restore['success']

    restored_item = internal_stock_items_crud.get_item_by_id(item_id, conn=db_conn)
    assert restored_item is not None
    assert restored_item['is_deleted'] == 0
    assert restored_item['deleted_at'] is None

# --- Count Items Test ---
def test_get_total_items_count(db_conn, sample_items):
    """Test counting items, with and without including deleted."""
    # sample_items creates 4 active, 1 deleted
    active_count = internal_stock_items_crud.get_total_items_count(conn=db_conn, include_deleted=False)
    assert active_count == 4

    total_count = internal_stock_items_crud.get_total_items_count(conn=db_conn, include_deleted=True)
    assert total_count == 5

    # Add one more active item
    internal_stock_items_crud.add_item({"item_name": "Another Active"}, conn=db_conn)
    active_count_after_add = internal_stock_items_crud.get_total_items_count(conn=db_conn, include_deleted=False)
    assert active_count_after_add == 5
    total_count_after_add = internal_stock_items_crud.get_total_items_count(conn=db_conn, include_deleted=True)
    assert total_count_after_add == 6
```
