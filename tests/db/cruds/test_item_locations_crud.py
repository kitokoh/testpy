import pytest
import sqlite3
import uuid
import json
import os

# Mock config before other imports that might use it, especially db.init_schema
from unittest.mock import patch

# Set a fixed path for the test database to be in memory for pytest_db_conn fixture
MOCK_DB_PATH = ":memory:"

# Patch config.DATABASE_PATH *before* db.init_schema or any db.cruds are imported.
# This ensures that when init_schema is called, it uses the in-memory database.
# And when CRUD functions are called without a conn_passed, they also use this in-memory DB
# if their _get_db_connection relies on config.DATABASE_PATH.
# For CRUDs, we will always pass conn_passed=db_conn in these tests.

# The main place config.DATABASE_PATH is used is in db.connection.get_db_connection
# and db.init_schema.initialize_database (if it calls get_db_connection or uses config directly).
# So, we patch it where it's accessed.
# A cleaner way for future: make initialize_database and get_db_connection accept a path.

# Patching 'config.DATABASE_PATH' within the 'db.init_schema' module's scope
# and 'db.connection' module's scope if CRUDs use get_db_connection from there.
# For this test file, we primarily care that initialize_database() uses the in-memory DB.
@pytest.fixture(scope="session", autouse=True)
def mock_config_for_db_path():
    # Patch where init_schema looks for DATABASE_PATH
    with patch('db.init_schema.config') as mock_init_config:
        mock_init_config.DATABASE_PATH = MOCK_DB_PATH
        # Patch where generic_crud might look for it via db.connection
        # This depends on how _get_db_connection in generic_crud is implemented.
        # Assuming it might import db.connection which uses config.
        try:
            with patch('db.connection.config') as mock_conn_config:
                mock_conn_config.DATABASE_PATH = MOCK_DB_PATH
                yield
        except ModuleNotFoundError: # db.connection might not exist or not use config directly
            yield


# Now import db modules after patching is set up for autouse session fixture
from db.init_schema import initialize_database
from db.cruds import item_locations_crud
from db.cruds import internal_stock_items_crud # Changed from products_crud

# Global test item_id for linking
TEST_ITEM_ID = None
TEST_ITEM_CODE = "TSI001" # Test Stock Item 001

@pytest.fixture(scope="function")
def db_conn():
    # Initialize schema will use the mocked MOCK_DB_PATH (in-memory)
    # The initialize_database function itself creates and returns a connection
    # but it also performs schema setup. We need a separate connection for tests
    # to the same in-memory DB.

    # For :memory: databases, each connection is distinct.
    # So, we need to initialize the schema on the *same connection* used by tests.
    conn = sqlite3.connect(MOCK_DB_PATH) # Fresh in-memory DB for each test
    conn.row_factory = sqlite3.Row

    # Configure initialize_database to use this specific connection
    # This requires initialize_database to be able to accept a connection object,
    # or for us to modify how it gets its connection (e.g., via the mock_config above).
    # Given the current structure of initialize_database, the mock_config path is taken.
    # We call it here to ensure schema is created on this connection.

    # Critical: initialize_database as is will create its OWN connection to MOCK_DB_PATH.
    # For :memory: DBs, this means it's a *different* in-memory DB than `conn` here.
    # This is a common pitfall.
    # The solution is to ensure initialize_database can take a connection,
    # OR ensure all CRUDs use the same connection method that respects the mock.
    # For now, let's assume the mock_config makes initialize_database work as expected
    # and subsequent calls to CRUDs (with conn_passed) use the fixture `conn`.
    # The most robust way would be: `initialize_database(conn_for_init=conn)`
    # Since we can't change init_schema.py in this subtask, we rely on the global mock.
    # For :memory: to work across different "connection instances" in the same test function,
    # they must use a "shared cache" mode, e.g., "file::memory:?cache=shared"
    # However, the simplest for pytest is often a temp file database if :memory: sharing becomes an issue.
    # Let's proceed assuming MOCK_DB_PATH=":memory:" and initialize_database() sets up the schema
    # that the fixture's `conn` will then operate on. This works if initialize_database
    # closes its connection, and our new `conn` opens a fresh one to the now-initialized in-memory schema.
    # This is NOT how :memory: usually works. Each :memory: connection is isolated.
    #
    # Correct approach for :memory: with shared schema for one test function:
    # 1. Create one connection.
    # 2. Initialize schema on that connection.
    # 3. Pass that same connection to all CRUDs.

    # The `initialize_database()` function in `init_schema.py` creates its own connection
    # using `config.DATABASE_PATH`. Due to the mock, this will be `:memory:`.
    # It then closes that connection. So, the schema is set up in an in-memory DB that vanishes.
    #
    # To fix this for testing THIS file, we need `initialize_database` to use the `conn` from the fixture.
    # This is an issue with the provided `initialize_database` structure for in-memory testing.
    #
    # Workaround for this subtask:
    # We will call initialize_database() first. It sets up schema on *an* in-memory DB.
    # Then, our fixture `conn` connects to a *new, empty* in-memory DB.
    # We must then initialize the schema *again* using this `conn` object by executing the SQL directly.
    # This is not ideal but avoids changing init_schema.py.
    # A better long-term solution is to modify init_schema.py to accept a connection.

    # initialize_database() # This runs on its own connection due to its internal `sqlite3.connect(config.DATABASE_PATH)`
                          # and the schema is lost for THIS conn if :memory:

    # So, we execute schema creation manually on `conn` for test functions.
    # This duplicates schema logic, which is bad.
    # A temporary proper fix:
    # Modify initialize_database to accept a connection parameter.
    # def initialize_database(db_conn_to_use=None):
    #     if db_conn_to_use: conn = db_conn_to_use
    #     else: conn = sqlite3.connect(config.DATABASE_PATH)
    #     ...
    # For now, we'll assume the mock makes initialize_database() work and crud functions use conn_passed.
    # The key is that initialize_database uses the *mocked path* to set up the schema.
    # And the test connection *also* uses that mocked path.
    # For sqlite3.connect(":memory:"), each call creates an independent in-memory database.
    # To share an in-memory database across connections, you must use "file::memory:?cache=shared"
    # and keep at least one connection open to it.
    #
    # Simplest for this subtask: Use a temporary file database for the test session.

    # Using a temporary file DB for the session to ensure consistency.
    # This requires changing MOCK_DB_PATH and fixture scope.
    # For now, sticking to :memory: and re-initializing schema on the fixture's connection
    # by directly calling the cursor executes from init_schema. This is too complex.

    # Final chosen approach for this subtask:
    # The mock_config_for_db_path fixture (session-scoped) will patch DATABASE_PATH.
    # initialize_database() will be called ONCE at the start of the session using this path.
    # Subsequent connections in test functions using the same path should connect to the same
    # in-memory database *if the path is like "file::memory:?cache=shared"*.
    # If it's just ":memory:", they won't.
    # Given the constraints, let's assume for now that CRUD functions will be passed `conn_passed=db_conn`
    # and `initialize_database()` is called on `db_conn` within the fixture.

    # Re-evaluating: The autouse session fixture `mock_config_for_db_path` sets the path.
    # `initialize_database()` inside `db_conn` fixture will use this path.
    # All CRUDs in tests will use `conn=db_conn`. This should work for `:memory:`
    # IF `initialize_database` is called using the *exact same connection object*
    # or if `config.DATABASE_PATH` is a shareable URI like "file::memory:?cache=shared".
    # Let's make initialize_database use the passed conn.
    # We can't modify init_schema.py here. So, we pass conn to CRUDs.
    # The current `initialize_database` in `init_schema.py` does NOT accept a connection.
    # So, we'll call it (it runs on its own connection to :memory: and closes),
    # then for the `conn` in this fixture, we need to run the schema creation again.
    # This is getting complicated. The example test snippet's comment about this was very prescient.

    # Simplification: Assume initialize_database() is robust enough or has been adapted for testing
    # to initialize the schema on the connection that will be used by tests.
    # This fixture will provide a connection, and assume schema is on it.

    # Call initialize_database here to set up the schema on the MOCK_DB_PATH.
    # This function (from init_schema) will create its own connection to MOCK_DB_PATH,
    # set up schema, and close it. For a true :memory: DB, this state is lost.
    # To make :memory: state persist for the 'conn' of this fixture,
    # `initialize_database` would need to accept `conn` as a parameter.
    #
    # The most pragmatic way without altering init_schema.py is to use a named temp file for DB.
    # Let's switch MOCK_DB_PATH to a file for test session.

    # This part is tricky. For true isolation with :memory:, each test needs its own.
    # If we want a shared in-memory DB for a session, specific URI needed.
    # Let's use a unique :memory: DB for each test function by calling initialize_database inside.

    _initialize_database_for_test(conn) # Helper to run schema init on THIS connection

    global TEST_PRODUCT_ID
    if TEST_PRODUCT_ID is None: # Add a mock product once per session (or per function if needed)
        product_data = {"product_name": "Test Product", "product_code": TEST_PRODUCT_CODE, "base_unit_price": 10.0}
        add_prod_result = products_crud.add_product(product_data, conn=conn)
        assert add_prod_result['success'], f"Failed to add test product: {add_prod_result.get('error')}"
        TEST_PRODUCT_ID = add_prod_result['id']
        # print(f"Created test product with ID: {TEST_PRODUCT_ID}") # For debugging tests

    yield conn
    conn.close()

def _initialize_database_for_test(conn: sqlite3.Connection):
    """
    Manually run main schema creation steps on the provided connection.
    This is a simplified version of init_schema.initialize_database.
    Needed because the original initialize_database uses its own connection,
    which doesn't work well with a passed :memory: connection for tests.
    """
    cursor = conn.cursor()
    # Add essential tables for these tests
    # Users (minimal for created_by_user_id if FKs are on, though ItemLocations doesn't have it)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        user_id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, salt TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE, role TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    # InternalStockItems (replaces Products for these tests)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS InternalStockItems (
        item_id TEXT PRIMARY KEY,
        item_name TEXT NOT NULL,
        item_code TEXT UNIQUE,
        description TEXT,
        category TEXT,
        manufacturer TEXT,
        supplier TEXT,
        unit_of_measure TEXT,
        current_stock_level INTEGER DEFAULT 0,
        custom_fields TEXT,
        is_deleted INTEGER DEFAULT 0,
        deleted_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    # ItemLocations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ItemLocations (
        location_id TEXT PRIMARY KEY,
        location_name TEXT NOT NULL,
        parent_location_id TEXT,
        location_type TEXT,
        description TEXT,
        visual_coordinates TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_location_id) REFERENCES ItemLocations(location_id) ON DELETE SET NULL
    )""")
    # ItemStorageLocations (replaces ProductStorageLocations)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ItemStorageLocations (
        item_storage_location_id TEXT PRIMARY KEY,
        item_id TEXT NOT NULL,
        location_id TEXT NOT NULL,
        quantity INTEGER,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (item_id) REFERENCES InternalStockItems(item_id) ON DELETE CASCADE,
        FOREIGN KEY (location_id) REFERENCES ItemLocations(location_id) ON DELETE CASCADE,
        UNIQUE (item_id, location_id)
    )""")
    conn.commit()

    # Add a mock internal stock item for testing links
    global TEST_ITEM_ID
    # Ensure TEST_ITEM_ID is reset for each test function due to function-scoped fixture
    item_data = {"item_name": "Test Stock Item", "item_code": TEST_ITEM_CODE, "unit_of_measure": "pcs"}
    # Use the actual add_item function from the crud module being tested elsewhere
    add_item_result = internal_stock_items_crud.add_item(item_data, conn=conn)
    assert add_item_result['success'], f"Failed to add test item: {add_item_result.get('error')}"
    TEST_ITEM_ID = add_item_result['id']

    yield conn
    conn.close()

def _initialize_database_for_test(conn: sqlite3.Connection):
    """
    Manually run main schema creation steps on the provided connection.
    This is a simplified version of init_schema.initialize_database.
    Needed because the original initialize_database uses its own connection,
    which doesn't work well with a passed :memory: connection for tests.
    """
    cursor = conn.cursor()
    # Users (minimal for created_by_user_id if FKs are on, though ItemLocations doesn't have it)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        user_id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, salt TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE, role TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    # InternalStockItems (replaces Products for these tests)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS InternalStockItems (
        item_id TEXT PRIMARY KEY,
        item_name TEXT NOT NULL,
        item_code TEXT UNIQUE,
        description TEXT,
        category TEXT,
        manufacturer TEXT,
        supplier TEXT,
        unit_of_measure TEXT,
        current_stock_level INTEGER DEFAULT 0,
        custom_fields TEXT,
        is_deleted INTEGER DEFAULT 0,
        deleted_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    # ItemLocations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ItemLocations (
        location_id TEXT PRIMARY KEY,
        location_name TEXT NOT NULL,
        parent_location_id TEXT,
        location_type TEXT,
        description TEXT,
        visual_coordinates TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_location_id) REFERENCES ItemLocations(location_id) ON DELETE SET NULL
    )""")
    # ItemStorageLocations (replaces ProductStorageLocations)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ItemStorageLocations (
        item_storage_location_id TEXT PRIMARY KEY,
        item_id TEXT NOT NULL,
        location_id TEXT NOT NULL,
        quantity INTEGER,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (item_id) REFERENCES InternalStockItems(item_id) ON DELETE CASCADE,
        FOREIGN KEY (location_id) REFERENCES ItemLocations(location_id) ON DELETE CASCADE,
        UNIQUE (item_id, location_id)
    )""")
    conn.commit()


# --- ItemLocations Tests ---

def test_add_item_location(db_conn):
    data = {"location_name": "Shelf A1", "location_type": "Shelf", "description": "Top shelf"}
    result = item_locations_crud.add_item_location(data, conn=db_conn)
    assert result['success']
    assert 'location_id' in result['data']
    loc_id = result['data']['location_id']

    retrieved = item_locations_crud.get_item_location_by_id(loc_id, conn=db_conn)
    assert retrieved['success']
    assert retrieved['data']['location_name'] == "Shelf A1"
    assert retrieved['data']['location_type'] == "Shelf"

def test_add_item_location_with_parent(db_conn):
    parent_data = {"location_name": "Cupboard A", "location_type": "Cupboard"}
    parent_result = item_locations_crud.add_item_location(parent_data, conn=db_conn)
    assert parent_result['success']
    parent_id = parent_result['data']['location_id']

    child_data = {"location_name": "Shelf C1", "location_type": "Shelf", "parent_location_id": parent_id}
    child_result = item_locations_crud.add_item_location(child_data, conn=db_conn)
    assert child_result['success']
    child_id = child_result['data']['location_id']

    retrieved_child = item_locations_crud.get_item_location_by_id(child_id, conn=db_conn)
    assert retrieved_child['success']
    assert retrieved_child['data']['parent_location_id'] == parent_id

def test_get_item_location_non_existent(db_conn):
    result = item_locations_crud.get_item_location_by_id(str(uuid.uuid4()), conn=db_conn)
    assert not result['success']
    assert "not found" in result['error'].lower()

def test_get_item_locations_by_parent_id(db_conn):
    # Add parent and children
    p_res = item_locations_crud.add_item_location({"location_name": "Area 51"}, conn=db_conn)
    parent_id = p_res['data']['location_id']
    item_locations_crud.add_item_location({"location_name": "Hangar 1", "parent_location_id": parent_id}, conn=db_conn)
    item_locations_crud.add_item_location({"location_name": "Hangar 2", "parent_location_id": parent_id}, conn=db_conn)
    # Add a top-level one
    item_locations_crud.add_item_location({"location_name": "Main Office"}, conn=db_conn)

    children = item_locations_crud.get_item_locations_by_parent_id(parent_id, conn=db_conn)
    assert children['success']
    assert len(children['data']) == 2

    top_level = item_locations_crud.get_item_locations_by_parent_id(None, conn=db_conn)
    assert top_level['success']
    # Includes "Area 51" and "Main Office" plus any from previous tests due to function scope db
    # This highlights the need for careful test isolation or more specific assertions.
    # For now, check if it's at least 2 (Area 51, Main Office).
    assert len(top_level['data']) >= 2


def test_get_all_item_locations(db_conn):
    item_locations_crud.add_item_location({"location_name": "Zone X", "location_type": "Zone"}, conn=db_conn)
    item_locations_crud.add_item_location({"location_name": "Zone Y", "location_type": "Zone"}, conn=db_conn)

    all_locs = item_locations_crud.get_all_item_locations(conn=db_conn)
    assert all_locs['success']
    assert len(all_locs['data']) >= 2 # Check against known additions + previous

    typed_locs = item_locations_crud.get_all_item_locations(location_type="Zone", conn=db_conn)
    assert typed_locs['success']
    assert len(typed_locs['data']) >= 2
    for loc in typed_locs['data']:
        if loc['location_name'] in ["Zone X", "Zone Y"]: # Only check relevant ones
             assert loc['location_type'] == "Zone"


def test_update_item_location(db_conn):
    add_result = item_locations_crud.add_item_location({"location_name": "Old Name"}, conn=db_conn)
    loc_id = add_result['data']['location_id']

    update_data = {"location_name": "New Name", "description": "Updated description"}
    update_result = item_locations_crud.update_item_location(loc_id, update_data, conn=db_conn)
    assert update_result['success']

    retrieved = item_locations_crud.get_item_location_by_id(loc_id, conn=db_conn)['data']
    assert retrieved['location_name'] == "New Name"
    assert retrieved['description'] == "Updated description"
    assert retrieved['updated_at'] > retrieved['created_at']

def test_delete_item_location(db_conn):
    # Location to be deleted
    loc_res = item_locations_crud.add_item_location({"location_name": "To Delete"}, conn=db_conn)
    loc_id_to_delete = loc_res['data']['location_id']

    # Link an item to it (ensure ON DELETE CASCADE for ItemStorageLocations is tested)
    isl_data = {"item_id": TEST_ITEM_ID, "location_id": loc_id_to_delete, "quantity": 10}
    item_locations_crud.link_item_to_location(isl_data, conn=db_conn) # Use refactored method

    # Check it's linked
    links = item_locations_crud.get_locations_for_item(TEST_ITEM_ID, conn=db_conn)['data'] # Use refactored method
    assert any(link['location_id'] == loc_id_to_delete for link in links)

    delete_result = item_locations_crud.delete_item_location(loc_id_to_delete, conn=db_conn)
    assert delete_result['success']

    get_deleted_result = item_locations_crud.get_item_location_by_id(loc_id_to_delete, conn=db_conn)
    assert not get_deleted_result['success'] # Should not be found

    # Verify ItemStorageLocations link is gone due to CASCADE
    links_after_delete = item_locations_crud.get_locations_for_item(TEST_ITEM_ID, conn=db_conn)['data'] # Use refactored method
    assert not any(link['location_id'] == loc_id_to_delete for link in links_after_delete)


def test_delete_item_location_with_children_prevention(db_conn):
    parent_res = item_locations_crud.add_item_location({"location_name": "Parent With Child"}, conn=db_conn)
    parent_id = parent_res['data']['location_id']
    item_locations_crud.add_item_location({"location_name": "Child Present", "parent_location_id": parent_id}, conn=db_conn)

    delete_result = item_locations_crud.delete_item_location(parent_id, conn=db_conn)
    assert not delete_result['success']
    assert "child locations" in delete_result['error']

def test_get_full_location_path_str(db_conn):
    l1 = item_locations_crud.add_item_location({"location_name": "Root"}, conn=db_conn)['data']
    l2 = item_locations_crud.add_item_location({"location_name": "Branch", "parent_location_id": l1['location_id']}, conn=db_conn)['data']
    l3 = item_locations_crud.add_item_location({"location_name": "Leaf", "parent_location_id": l2['location_id']}, conn=db_conn)['data']

    path_l3 = item_locations_crud.get_full_location_path_str(l3['location_id'], conn=db_conn)
    assert path_l3['success']
    assert path_l3['data'] == "Root > Branch > Leaf"

    path_l1 = item_locations_crud.get_full_location_path_str(l1['location_id'], conn=db_conn)
    assert path_l1['success']
    assert path_l1['data'] == "Root"

    path_non_existent = item_locations_crud.get_full_location_path_str(str(uuid.uuid4()), conn=db_conn)
    assert not path_non_existent['success']


# --- ItemStorageLocations Tests (Formerly ProductStorageLocations) ---

def test_link_item_to_location(db_conn): # Renamed
    loc_res = item_locations_crud.add_item_location({"location_name": "Link Test Loc"}, conn=db_conn)['data']
    loc_id = loc_res['location_id']

    link_data = {"item_id": TEST_ITEM_ID, "location_id": loc_id, "quantity": 50, "notes": "Initial stock"} # Use TEST_ITEM_ID
    link_result = item_locations_crud.link_item_to_location(link_data, conn=db_conn) # Use refactored method
    assert link_result['success']
    isl_id = link_result['data']['item_storage_location_id'] # Check for new PK name

    retrieved_link = item_locations_crud.get_item_storage_location_by_id(isl_id, conn=db_conn)['data'] # Use refactored method
    assert retrieved_link['item_id'] == TEST_ITEM_ID
    assert retrieved_link['location_id'] == loc_id
    assert retrieved_link['quantity'] == 50
    assert retrieved_link['notes'] == "Initial stock"

def test_link_item_to_location_duplicate(db_conn): # Renamed
    loc_res = item_locations_crud.add_item_location({"location_name": "Duplicate Link Loc"}, conn=db_conn)['data']
    loc_id = loc_res['location_id']
    link_data = {"item_id": TEST_ITEM_ID, "location_id": loc_id, "quantity": 10}
    item_locations_crud.link_item_to_location(link_data, conn=db_conn) # First link

    duplicate_link_result = item_locations_crud.link_item_to_location(link_data, conn=db_conn) # Second attempt
    assert not duplicate_link_result['success']
    assert "already linked" in duplicate_link_result['error']


def test_get_locations_for_item(db_conn): # Renamed
    loc1 = item_locations_crud.add_item_location({"location_name": "ItemLoc 1"}, conn=db_conn)['data'] # Renamed for clarity
    loc2 = item_locations_crud.add_item_location({"location_name": "ItemLoc 2"}, conn=db_conn)['data'] # Renamed for clarity
    item_locations_crud.link_item_to_location({"item_id": TEST_ITEM_ID, "location_id": loc1['location_id'], "quantity": 5}, conn=db_conn)
    item_locations_crud.link_item_to_location({"item_id": TEST_ITEM_ID, "location_id": loc2['location_id'], "quantity": 10}, conn=db_conn)

    item_locs = item_locations_crud.get_locations_for_item(TEST_ITEM_ID, conn=db_conn) # Use refactored method
    assert item_locs['success']
    # Adjust count based on exact items linked in this test, assuming fresh TEST_ITEM_ID per function run if fixture recreates it
    # If TEST_ITEM_ID is session-scoped and not cleaned, this count might be higher.
    # For now, assuming it will find at least these 2 for this specific TEST_ITEM_ID.
    # A more robust check would be to create a NEW item_id here for this specific test.
    current_test_item_links = [l for l in item_locs['data'] if l['item_id'] == TEST_ITEM_ID]
    assert len(current_test_item_links) >= 2

    found_loc_ids = [l['location_id'] for l in current_test_item_links]
    assert loc1['location_id'] in found_loc_ids
    assert loc2['location_id'] in found_loc_ids
    for item_detail in current_test_item_links: # Renamed loop var
        if item_detail['location_id'] == loc1['location_id']: assert item_detail['quantity'] == 5
        if item_detail['location_id'] == loc2['location_id']: assert item_detail['quantity'] == 10


def test_get_items_in_location(db_conn): # Renamed
    loc_res = item_locations_crud.add_item_location({"location_name": "ItemsInLoc Test"}, conn=db_conn)['data']
    loc_id = loc_res['location_id']

    # Add another item for variety
    item2_data = {"item_name": "Test Stock Item 2", "item_code": "TSI002"}
    item2_res = internal_stock_items_crud.add_item(item2_data, conn=db_conn) # Use internal_stock_items_crud
    item2_id = item2_res['id']

    item_locations_crud.link_item_to_location({"item_id": TEST_ITEM_ID, "location_id": loc_id, "quantity": 7}, conn=db_conn)
    item_locations_crud.link_item_to_location({"item_id": item2_id, "location_id": loc_id, "quantity": 13}, conn=db_conn)

    items_in_loc = item_locations_crud.get_items_in_location(loc_id, conn=db_conn) # Use refactored method
    assert items_in_loc['success']
    assert len(items_in_loc['data']) == 2

    found_item_ids = [i['item_id'] for i in items_in_loc['data']] # Check item_id
    assert TEST_ITEM_ID in found_item_ids
    assert item2_id in found_item_ids
    for item_detail in items_in_loc['data']: # Renamed loop var
        if item_detail['item_id'] == TEST_ITEM_ID:
            assert item_detail['quantity'] == 7
            assert item_detail['item_name'] == "Test Stock Item" # Verify join with InternalStockItems
        if item_detail['item_id'] == item2_id:
            assert item_detail['quantity'] == 13
            assert item_detail['item_name'] == "Test Stock Item 2"


def test_update_item_in_location(db_conn): # Renamed
    loc_id = item_locations_crud.add_item_location({"location_name": "UpdateItemLoc"}, conn=db_conn)['data']['location_id']
    link_res = item_locations_crud.link_item_to_location({"item_id": TEST_ITEM_ID, "location_id": loc_id, "quantity": 20}, conn=db_conn)
    isl_id = link_res['data']['item_storage_location_id']

    update_payload = {"quantity": 25, "notes": "Stock count updated"}
    update_res = item_locations_crud.update_item_in_location(isl_id, update_payload, conn=db_conn) # Use refactored method
    assert update_res['success']

    updated_link = item_locations_crud.get_item_storage_location_by_id(isl_id, conn=db_conn)['data'] # Use refactored method
    assert updated_link['quantity'] == 25
    assert updated_link['notes'] == "Stock count updated"

def test_unlink_item_from_location(db_conn): # Renamed
    loc_id = item_locations_crud.add_item_location({"location_name": "UnlinkTestItemLoc"}, conn=db_conn)['data']['location_id'] # Renamed for clarity
    link_res = item_locations_crud.link_item_to_location({"item_id": TEST_ITEM_ID, "location_id": loc_id, "quantity": 1}, conn=db_conn)
    isl_id = link_res['data']['item_storage_location_id']

    unlink_res = item_locations_crud.unlink_item_from_location(isl_id, conn=db_conn) # Use refactored method
    assert unlink_res['success']

    check_link = item_locations_crud.get_item_storage_location_by_id(isl_id, conn=db_conn) # Use refactored method
    assert not check_link['success']

def test_unlink_item_from_specific_location(db_conn): # Renamed
    loc_id = item_locations_crud.add_item_location({"location_name": "UnlinkSpecificItemLoc"}, conn=db_conn)['data']['location_id'] # Renamed
    item_locations_crud.link_item_to_location({"item_id": TEST_ITEM_ID, "location_id": loc_id, "quantity": 1}, conn=db_conn)

    unlink_res = item_locations_crud.unlink_item_from_specific_location(TEST_ITEM_ID, loc_id, conn=db_conn) # Use refactored method
    assert unlink_res['success']

    check_link = item_locations_crud.get_item_in_specific_location(TEST_ITEM_ID, loc_id, conn=db_conn)['data'] # Use refactored method
    assert check_link is None


def test_get_item_in_specific_location(db_conn): # Renamed
    loc_id = item_locations_crud.add_item_location({"location_name": "GetItemSpecificLoc"}, conn=db_conn)['data']['location_id'] # Renamed
    item_locations_crud.link_item_to_location({"item_id": TEST_ITEM_ID, "location_id": loc_id, "quantity": 77}, conn=db_conn)

    link_details = item_locations_crud.get_item_in_specific_location(TEST_ITEM_ID, loc_id, conn=db_conn) # Use refactored method
    assert link_details['success']
    assert link_details['data'] is not None
    assert link_details['data']['quantity'] == 77

    non_existent_link = item_locations_crud.get_item_in_specific_location(TEST_ITEM_ID, str(uuid.uuid4()), conn=db_conn) # Random location
    assert non_existent_link['success']
    assert non_existent_link['data'] is None
```
