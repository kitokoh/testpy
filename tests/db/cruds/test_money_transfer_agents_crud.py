import pytest
import sqlite3
import uuid
from datetime import datetime, timezone
import os

# Adjust path to import from the root of the project
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from db.init_schema import initialize_database
from db.cruds.money_transfer_agents_crud import (
    add_money_transfer_agent,
    get_money_transfer_agent_by_id,
    get_all_money_transfer_agents,
    update_money_transfer_agent,
    delete_money_transfer_agent
)
from db.cruds.clients_crud import add_client
from db.cruds.projects_crud import add_project
from db.cruds.locations_crud import add_country, add_city

# Store the original DATABASE_PATH and override it for tests
ORIGINAL_DB_PATH = None
TEST_DB_PATH = ":memory:" # Use in-memory SQLite database for tests

def setup_module(module):
    """ setup any state specific to the execution of the given module."""
    global ORIGINAL_DB_PATH
    try:
        from config import DATABASE_PATH as DBP
        ORIGINAL_DB_PATH = DBP
        # Override DATABASE_PATH in config for the duration of the tests
        import config
        config.DATABASE_PATH = TEST_DB_PATH
    except ImportError:
        # If config.py doesn't exist or DATABASE_PATH is not there, handle it.
        # This might mean we need to mock 'config.DATABASE_PATH' if init_schema relies on it.
        # For now, assume init_schema can be made to work with a passed connection or TEST_DB_PATH.
        print("config.py or DATABASE_PATH not found. Tests might behave unexpectedly if init_schema depends on it directly.")


def teardown_module(module):
    """ teardown any state that was previously setup with a setup_module
    function.
    """
    global ORIGINAL_DB_PATH
    if ORIGINAL_DB_PATH:
        import config
        config.DATABASE_PATH = ORIGINAL_DB_PATH


@pytest.fixture
def db_connection() -> sqlite3.Connection:
    """
    Pytest fixture to set up an in-memory SQLite database with the schema
    for each test function.
    Creates tables, yields a connection, and closes it after each test.
    """
    # Ensure initialize_database uses the TEST_DB_PATH
    # This might require modifying how initialize_database gets its path,
    # or by temporarily patching config.DATABASE_PATH if it's read globally.
    # For simplicity, we assume initialize_database() will use the overridden config.DATABASE_PATH.

    conn = sqlite3.connect(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row # Important for accessing columns by name

    # Temporarily override config.DATABASE_PATH for initialize_database if it reads it globally
    # This is a bit of a hack. A better way would be for initialize_database to accept a path or conn.
    try:
        import config
        original_init_db_path = config.DATABASE_PATH
        config.DATABASE_PATH = TEST_DB_PATH
        initialize_database() # This will create tables in the in-memory DB
    except AttributeError: # If config module or DATABASE_PATH doesn't exist as expected
        # If config.DATABASE_PATH can't be patched, make sure initialize_database() itself
        # can be called in a way that it uses TEST_DB_PATH (e.g. by passing conn to it, not implemented here)
        # This part might need adjustment based on how initialize_database is actually structured.
        # For now, assuming it uses the globally set config.DATABASE_PATH
        initialize_database() # Fallback if config patching is not applicable/fails
    finally:
        if 'original_init_db_path' in locals(): # Check if it was defined
             config.DATABASE_PATH = original_init_db_path # Restore after init


    yield conn # Provide the connection to the test

    conn.close() # Close the connection after the test
    # No need to drop tables for in-memory, it's fresh each time.
    # If it were a file DB, os.remove(TEST_DB_PATH) might be here.


# --- Helper function to create prerequisite data ---
def create_prerequisites(conn):
    # Create a country
    country_data = {"country_name": "Testland"}
    country_res = add_country(country_data, conn=conn)
    country_id = conn.execute("SELECT country_id FROM Countries WHERE country_name = 'Testland'").fetchone()['country_id']

    # Create a city
    city_data = {"country_id": country_id, "city_name": "Testville"}
    city_res = add_city(city_data, conn=conn)
    city_id = conn.execute("SELECT city_id FROM Cities WHERE city_name = 'Testville'").fetchone()['city_id']

    return {"country_id": country_id, "city_id": city_id}


# --- Test Cases ---

def test_add_money_transfer_agent_success(db_connection):
    """Test successful addition of a money transfer agent."""
    prereqs = create_prerequisites(db_connection)
    agent_data = {
        "name": "Test Agent Bank",
        "agent_type": "Bank",
        "phone_number": "1234567890",
        "email": "bankagent@example.com",
        "country_id": prereqs["country_id"],
        "city_id": prereqs["city_id"]
    }
    result = add_money_transfer_agent(agent_data, conn=db_connection)
    assert result['success']
    assert 'agent_id' in result
    agent_id = result['agent_id']

    # Verify data in DB
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM MoneyTransferAgents WHERE agent_id = ?", (agent_id,))
    agent_db = cursor.fetchone()
    assert agent_db is not None
    assert agent_db['name'] == agent_data['name']
    assert agent_db['agent_type'] == agent_data['agent_type']
    assert agent_db['phone_number'] == agent_data['phone_number']
    assert agent_db['email'] == agent_data['email']
    assert agent_db['country_id'] == agent_data['country_id']
    assert agent_db['city_id'] == agent_data['city_id']
    assert agent_db['is_deleted'] == 0
    assert agent_db['created_at'] is not None
    assert agent_db['updated_at'] is not None
    # Check timestamp format (basic check)
    datetime.fromisoformat(agent_db['created_at'].replace('Z', '+00:00'))
    datetime.fromisoformat(agent_db['updated_at'].replace('Z', '+00:00'))


def test_add_money_transfer_agent_required_fields(db_connection):
    """Test adding agent with missing required fields."""
    # Missing name
    agent_data_no_name = {
        "agent_type": "Individual Agent",
    }
    result = add_money_transfer_agent(agent_data_no_name, conn=db_connection)
    assert not result['success']
    assert 'error' in result
    assert "Missing required field: name" in result['error']

    # Missing agent_type
    agent_data_no_type = {
        "name": "Agent No Type",
    }
    result = add_money_transfer_agent(agent_data_no_type, conn=db_connection)
    assert not result['success']
    assert 'error' in result
    assert "Missing required field: agent_type" in result['error']

    # Invalid agent_type
    agent_data_invalid_type = {
        "name": "Agent Invalid Type",
        "agent_type": "InvalidType"
    }
    result = add_money_transfer_agent(agent_data_invalid_type, conn=db_connection)
    assert not result['success']
    assert 'error' in result
    assert "Invalid agent_type" in result['error']


def test_get_money_transfer_agent_by_id(db_connection):
    """Test fetching an agent by its ID."""
    prereqs = create_prerequisites(db_connection)
    agent_data = {
        "name": "Fetch Me Agent", "agent_type": "Other",
        "country_id": prereqs["country_id"], "city_id": prereqs["city_id"]
    }
    add_result = add_money_transfer_agent(agent_data, conn=db_connection)
    agent_id = add_result['agent_id']

    # Fetch existing
    fetched_agent = get_money_transfer_agent_by_id(agent_id, conn=db_connection)
    assert fetched_agent is not None
    assert fetched_agent['agent_id'] == agent_id
    assert fetched_agent['name'] == agent_data['name']

    # Fetch non-existent
    non_existent_agent = get_money_transfer_agent_by_id(str(uuid.uuid4()), conn=db_connection)
    assert non_existent_agent is None

    # Test include_deleted for soft-deleted agent
    delete_money_transfer_agent(agent_id, conn=db_connection) # Soft delete

    fetched_deleted_not_included = get_money_transfer_agent_by_id(agent_id, conn=db_connection, include_deleted=False)
    assert fetched_deleted_not_included is None

    fetched_deleted_included = get_money_transfer_agent_by_id(agent_id, conn=db_connection, include_deleted=True)
    assert fetched_deleted_included is not None
    assert fetched_deleted_included['agent_id'] == agent_id
    assert fetched_deleted_included['is_deleted'] == 1


def test_get_all_money_transfer_agents(db_connection):
    """Test fetching all agents with filtering and soft delete considerations."""
    prereqs = create_prerequisites(db_connection)
    country1_id = prereqs["country_id"]
    city1_id = prereqs["city_id"]

    # Create another country and city for diverse filtering
    country_data2 = {"country_name": "Otherland"}
    add_country(country_data2, conn=db_connection)
    country2_id = db_connection.execute("SELECT country_id FROM Countries WHERE country_name = 'Otherland'").fetchone()['country_id']
    city_data2 = {"country_id": country2_id, "city_name": "Otherville"}
    add_city(city_data2, conn=db_connection)
    city2_id = db_connection.execute("SELECT city_id FROM Cities WHERE city_name = 'Otherville'").fetchone()['city_id']

    agent1_data = {"name": "Agent Alpha Bank", "agent_type": "Bank", "country_id": country1_id, "city_id": city1_id}
    agent2_data = {"name": "Agent Beta Individual", "agent_type": "Individual Agent", "country_id": country2_id, "city_id": city2_id}
    agent3_data = {"name": "Agent Gamma Other", "agent_type": "Other", "country_id": country1_id, "city_id": city1_id}

    agent1_id = add_money_transfer_agent(agent1_data, conn=db_connection)['agent_id']
    add_money_transfer_agent(agent2_data, conn=db_connection)
    add_money_transfer_agent(agent3_data, conn=db_connection)

    # Test get all (no filters, not including deleted)
    all_agents = get_all_money_transfer_agents(conn=db_connection)
    assert len(all_agents) == 3

    # Test filter by agent_type
    bank_agents = get_all_money_transfer_agents(filters={"agent_type": "Bank"}, conn=db_connection)
    assert len(bank_agents) == 1
    assert bank_agents[0]['name'] == "Agent Alpha Bank"

    # Test filter by country_id
    country1_agents = get_all_money_transfer_agents(filters={"country_id": country1_id}, conn=db_connection)
    assert len(country1_agents) == 2 # Alpha and Gamma

    # Test filter by city_id
    city2_agents = get_all_money_transfer_agents(filters={"city_id": city2_id}, conn=db_connection)
    assert len(city2_agents) == 1
    assert city2_agents[0]['name'] == "Agent Beta Individual"

    # Test filter by name (partial match)
    gamma_agents = get_all_money_transfer_agents(filters={"name": "Gamma"}, conn=db_connection)
    assert len(gamma_agents) == 1
    assert gamma_agents[0]['name'] == "Agent Gamma Other"

    # Test include_deleted
    delete_money_transfer_agent(agent1_id, conn=db_connection) # Soft delete Agent Alpha

    all_active_agents = get_all_money_transfer_agents(conn=db_connection, include_deleted=False)
    assert len(all_active_agents) == 2

    all_agents_including_deleted = get_all_money_transfer_agents(conn=db_connection, include_deleted=True)
    assert len(all_agents_including_deleted) == 3

    # Test pagination (if applicable - current CRUD doesn't explicitly show pagination args, but good to have)
    # Assuming get_all_money_transfer_agents is updated or this is a conceptual test for future
    # For now, the CRUD function get_all_money_transfer_agents has limit and offset

    paginated_agents_limit1 = get_all_money_transfer_agents(conn=db_connection, include_deleted=True, limit=1, offset=0)
    assert len(paginated_agents_limit1) == 1

    paginated_agents_limit2_offset1 = get_all_money_transfer_agents(conn=db_connection, include_deleted=True, limit=2, offset=1)
    assert len(paginated_agents_limit2_offset1) == 2 # Should get Beta and Gamma if Alpha was first


def test_update_money_transfer_agent(db_connection):
    """Test updating an existing money transfer agent."""
    prereqs = create_prerequisites(db_connection)
    agent_data = {"name": "Original Name", "agent_type": "Bank", "country_id": prereqs["country_id"]}
    add_result = add_money_transfer_agent(agent_data, conn=db_connection)
    agent_id = add_result['agent_id']

    # Fetch original created_at time
    original_agent_db = db_connection.execute("SELECT * FROM MoneyTransferAgents WHERE agent_id = ?", (agent_id,)).fetchone()
    original_created_at = original_agent_db['created_at']
    original_updated_at = original_agent_db['updated_at']


    update_payload = {
        "name": "Updated Name",
        "email": "updated@example.com",
        "phone_number": "0000000000"
    }
    # Make sure some time passes for updated_at to be different
    import time; time.sleep(0.01)

    update_result = update_money_transfer_agent(agent_id, update_payload, conn=db_connection)
    assert update_result['success']
    assert update_result['updated_count'] == 1

    updated_agent = get_money_transfer_agent_by_id(agent_id, conn=db_connection, include_deleted=True)
    assert updated_agent['name'] == "Updated Name"
    assert updated_agent['email'] == "updated@example.com"
    assert updated_agent['phone_number'] == "0000000000"
    assert updated_agent['created_at'] == original_created_at # Should not change
    assert updated_agent['updated_at'] > original_updated_at # Should change and be greater

    # Test updating non-existent agent
    non_existent_update = update_money_transfer_agent(str(uuid.uuid4()), {"name": "Ghost"}, conn=db_connection)
    assert not non_existent_update['success'] # Should be False if agent not found
    assert non_existent_update.get('updated_count', 0) == 0 # Or check specific error message if available

    # Test soft deleting via update
    soft_delete_payload = {"is_deleted": 1}
    time.sleep(0.01) # ensure updated_at changes
    soft_delete_result = update_money_transfer_agent(agent_id, soft_delete_payload, conn=db_connection)
    assert soft_delete_result['success']
    assert soft_delete_result['updated_count'] == 1

    deleted_agent = get_money_transfer_agent_by_id(agent_id, conn=db_connection, include_deleted=True)
    assert deleted_agent['is_deleted'] == 1
    assert deleted_agent['deleted_at'] is not None
    assert deleted_agent['updated_at'] > updated_agent['updated_at']

    # Test recovering via update
    recover_payload = {"is_deleted": 0}
    time.sleep(0.01)
    recover_result = update_money_transfer_agent(agent_id, recover_payload, conn=db_connection)
    assert recover_result['success']
    assert recover_result['updated_count'] == 1

    recovered_agent = get_money_transfer_agent_by_id(agent_id, conn=db_connection, include_deleted=True)
    assert recovered_agent['is_deleted'] == 0
    assert recovered_agent['deleted_at'] is None # deleted_at should be nulled out on recovery
    assert recovered_agent['updated_at'] > deleted_agent['updated_at']

    # Test invalid agent_type in update
    invalid_type_payload = {"agent_type": "SuperAgent"}
    invalid_type_result = update_money_transfer_agent(agent_id, invalid_type_payload, conn=db_connection)
    assert not invalid_type_result['success']
    assert "Invalid agent_type" in invalid_type_result.get('error', '')


def test_delete_money_transfer_agent(db_connection):
    """Test soft deleting an agent."""
    prereqs = create_prerequisites(db_connection)
    agent_data = {"name": "To Be Deleted", "agent_type": "Individual Agent", "country_id": prereqs["country_id"]}
    add_result = add_money_transfer_agent(agent_data, conn=db_connection)
    agent_id = add_result['agent_id']

    original_agent = get_money_transfer_agent_by_id(agent_id, conn=db_connection, include_deleted=True)
    original_updated_at = original_agent['updated_at']

    time.sleep(0.01) # Ensure time difference for updated_at

    delete_result = delete_money_transfer_agent(agent_id, conn=db_connection)
    assert delete_result['success']

    # Verify it's soft-deleted
    deleted_agent = get_money_transfer_agent_by_id(agent_id, conn=db_connection, include_deleted=True)
    assert deleted_agent is not None
    assert deleted_agent['is_deleted'] == 1
    assert deleted_agent['deleted_at'] is not None
    datetime.fromisoformat(deleted_agent['deleted_at'].replace('Z', '+00:00')) # Check format
    assert deleted_agent['updated_at'] > original_updated_at # updated_at should also change

    # Try fetching without include_deleted
    should_be_none = get_money_transfer_agent_by_id(agent_id, conn=db_connection, include_deleted=False)
    assert should_be_none is None

    # Test deleting a non-existent agent
    non_existent_delete_result = delete_money_transfer_agent(str(uuid.uuid4()), conn=db_connection)
    assert not non_existent_delete_result['success'] # Should indicate failure if agent not found
    # The specific error message or updated_count might depend on implementation details in delete_money_transfer_agent
    # (which internally calls update_money_transfer_agent)
    assert non_existent_delete_result.get('updated_count', 0) == 0

    # Test deleting an already soft-deleted agent (should effectively do nothing or report 0 updated)
    already_deleted_result = delete_money_transfer_agent(agent_id, conn=db_connection)
    # Depending on how update handles "no change", this might be success:True, updated_count:0
    # or success:False if it checks if already in target state.
    # Current update_money_transfer_agent will return success:True, updated_count:1 if values are re-set,
    # or success:True, updated_count:0 if it detects no actual change needed.
    # Let's assume it will try to set is_deleted=1 again.
    assert already_deleted_result['success']
    # If it re-applies the same values, updated_count might be 1. If it's smarter, 0.
    # The key is that it doesn't error and the state remains deleted.
    final_check_deleted_agent = get_money_transfer_agent_by_id(agent_id, conn=db_connection, include_deleted=True)
    assert final_check_deleted_agent['is_deleted'] == 1
