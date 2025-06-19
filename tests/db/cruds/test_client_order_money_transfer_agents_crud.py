import pytest
import sqlite3
import uuid
from datetime import datetime, timezone
import os

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from db.init_schema import initialize_database
from db.cruds.client_order_money_transfer_agents_crud import (
    assign_agent_to_client_order,
    get_assigned_agents_for_client_order,
    get_assigned_agents_for_client,
    update_assignment_details,
    unassign_agent_from_client_order
)
from db.cruds.money_transfer_agents_crud import add_money_transfer_agent
from db.cruds.clients_crud import add_client
from db.cruds.projects_crud import add_project
from db.cruds.users_crud import add_user_direct # Assuming a simple user add for created_by
from db.cruds.locations_crud import add_country, add_city # For agent prerequisites

ORIGINAL_DB_PATH_COMA = None
TEST_DB_PATH_COMA = ":memory:"

def setup_module(module):
    global ORIGINAL_DB_PATH_COMA
    try:
        from config import DATABASE_PATH as DBP
        ORIGINAL_DB_PATH_COMA = DBP
        import config
        config.DATABASE_PATH = TEST_DB_PATH_COMA
    except ImportError:
        print("COMA Tests: config.py or DATABASE_PATH not found.")

def teardown_module(module):
    global ORIGINAL_DB_PATH_COMA
    if ORIGINAL_DB_PATH_COMA:
        import config
        config.DATABASE_PATH = ORIGINAL_DB_PATH_COMA

@pytest.fixture
def db_connection_coma() -> sqlite3.Connection:
    conn = sqlite3.connect(TEST_DB_PATH_COMA)
    conn.row_factory = sqlite3.Row
    try:
        import config
        original_init_db_path = config.DATABASE_PATH
        config.DATABASE_PATH = TEST_DB_PATH_COMA
        initialize_database()
    except AttributeError:
        initialize_database() # Fallback
    finally:
        if 'original_init_db_path' in locals():
             config.DATABASE_PATH = original_init_db_path
    yield conn
    conn.close()

# --- Helper function to create prerequisite data for COMA tests ---
def create_coma_prerequisites(conn, client_name="Test Client COMA", project_name="Test Project COMA", agent_name="Test Agent COMA"):
    # User (for created_by_user_id in client)
    user_data = {
        "username": f"testuser_{str(uuid.uuid4())[:8]}", "password": "password",
        "email": f"user_{str(uuid.uuid4())[:4]}@example.com", "full_name": "Test User", "role": "admin"
    }
    user_res = add_user_direct(user_data['username'], user_data['password'], user_data['email'], user_data['full_name'], user_data['role'], conn=conn)
    user_id = user_res['user_id'] if user_res['success'] else None
    assert user_id is not None, "Failed to create user for COMA tests"

    # Client
    client_data = {"client_name": client_name, "project_identifier": project_name.replace(" ", "_"), "created_by_user_id": user_id}
    client_res = add_client(client_data, conn=conn)
    client_id = client_res.get('client_id')
    assert client_id is not None, "Failed to create client for COMA tests"

    # Project (Order)
    project_data = {"client_id": client_id, "project_name": project_name, "description": "Test project for COMA"}
    project_res = add_project(project_data, conn=conn)
    project_id = project_res.get('project_id') # This is our order_id
    assert project_id is not None, "Failed to create project for COMA tests"

    # Country & City for Agent
    country_data = {"country_name": f"Testland_{str(uuid.uuid4())[:4]}"}
    add_country(country_data, conn=conn)
    country_id = conn.execute("SELECT country_id FROM Countries WHERE country_name = ?", (country_data["country_name"],)).fetchone()['country_id']

    city_data = {"country_id": country_id, "city_name": f"Testville_{str(uuid.uuid4())[:4]}"}
    add_city(city_data, conn=conn)
    city_id = conn.execute("SELECT city_id FROM Cities WHERE city_name = ?", (city_data["city_name"],)).fetchone()['city_id']

    # Money Transfer Agent
    mta_data = {"name": agent_name, "agent_type": "Bank", "country_id": country_id, "city_id": city_id}
    mta_res = add_money_transfer_agent(mta_data, conn=conn)
    agent_id = mta_res.get('agent_id')
    assert agent_id is not None, "Failed to create money transfer agent for COMA tests"

    return {"client_id": client_id, "project_id": project_id, "agent_id": agent_id, "user_id": user_id}


# --- Test Cases ---

def test_assign_agent_to_client_order_success(db_connection_coma):
    prereqs = create_coma_prerequisites(db_connection_coma)
    assignment_details = "Urgent transfer for project phase 1"
    fee_estimate = 150.75

    result = assign_agent_to_client_order(
        client_id=prereqs["client_id"],
        order_id=prereqs["project_id"],
        agent_id=prereqs["agent_id"],
        assignment_details=assignment_details,
        fee_estimate=fee_estimate,
        conn=db_connection_coma
    )
    assert result['success']
    assert 'assignment_id' in result
    assignment_id = result['assignment_id']

    # Verify data in DB
    cursor = db_connection_coma.cursor()
    cursor.execute("SELECT * FROM ClientOrder_MoneyTransferAgents WHERE assignment_id = ?", (assignment_id,))
    assignment_db = cursor.fetchone()

    assert assignment_db is not None
    assert assignment_db['client_id'] == prereqs["client_id"]
    assert assignment_db['order_id'] == prereqs["project_id"]
    assert assignment_db['agent_id'] == prereqs["agent_id"]
    assert assignment_db['assignment_details'] == assignment_details
    assert assignment_db['fee_estimate'] == fee_estimate
    assert assignment_db['email_status'] == 'Pending'
    assert assignment_db['is_deleted'] == 0
    assert assignment_db['assigned_at'] is not None
    assert assignment_db['updated_at'] is not None # Should be set on creation too
    datetime.fromisoformat(assignment_db['assigned_at'].replace('Z', '+00:00'))
    datetime.fromisoformat(assignment_db['updated_at'].replace('Z', '+00:00'))

def test_assign_agent_to_client_order_invalid_fk(db_connection_coma):
    prereqs = create_coma_prerequisites(db_connection_coma)

    # Invalid agent_id
    result_invalid_agent = assign_agent_to_client_order(
        client_id=prereqs["client_id"], order_id=prereqs["project_id"], agent_id=str(uuid.uuid4()),
        conn=db_connection_coma
    )
    assert not result_invalid_agent['success']
    assert "integrity error" in result_invalid_agent.get('error', '').lower() # Check for FK violation message

def test_get_assigned_agents_for_client_order(db_connection_coma):
    prereqs = create_coma_prerequisites(db_connection_coma, agent_name="AgentForOrderTest")
    assign_agent_to_client_order(
        client_id=prereqs["client_id"], order_id=prereqs["project_id"], agent_id=prereqs["agent_id"],
        conn=db_connection_coma
    )

    assignments = get_assigned_agents_for_client_order(
        client_id=prereqs["client_id"], order_id=prereqs["project_id"], conn=db_connection_coma
    )
    assert len(assignments) == 1
    assignment = assignments[0]
    assert assignment['agent_id'] == prereqs["agent_id"]
    assert assignment['agent_name'] == "AgentForOrderTest" # Joined data
    assert assignment['project_name'] == "Test Project COMA" # Joined data

    # Test with non-existent order
    no_assignments = get_assigned_agents_for_client_order(
        client_id=prereqs["client_id"], order_id=str(uuid.uuid4()), conn=db_connection_coma
    )
    assert len(no_assignments) == 0

def test_get_assigned_agents_for_client(db_connection_coma):
    prereqs = create_coma_prerequisites(db_connection_coma, client_name="ClientWideTest", agent_name="AgentForClientTest")
    # Project 2 for the same client
    project_data2 = {"client_id": prereqs["client_id"], "project_name": "Other Project COMA", "description": "Another project"}
    project_res2 = add_project(project_data2, conn=db_connection_coma)
    project_id2 = project_res2['project_id']

    assign_agent_to_client_order(
        client_id=prereqs["client_id"], order_id=prereqs["project_id"], agent_id=prereqs["agent_id"],
        conn=db_connection_coma
    )
    assign_agent_to_client_order(
        client_id=prereqs["client_id"], order_id=project_id2, agent_id=prereqs["agent_id"],
        conn=db_connection_coma
    )

    client_assignments = get_assigned_agents_for_client(client_id=prereqs["client_id"], conn=db_connection_coma)
    assert len(client_assignments) == 2
    assert client_assignments[0]['agent_name'] == "AgentForClientTest"
    assert client_assignments[1]['agent_name'] == "AgentForClientTest"


def test_unassign_agent_from_client_order(db_connection_coma):
    prereqs = create_coma_prerequisites(db_connection_coma)
    assign_res = assign_agent_to_client_order(
        client_id=prereqs["client_id"], order_id=prereqs["project_id"], agent_id=prereqs["agent_id"],
        conn=db_connection_coma
    )
    assignment_id = assign_res['assignment_id']

    unassign_result = unassign_agent_from_client_order(assignment_id, conn=db_connection_coma)
    assert unassign_result['success']

    # Verify soft delete
    cursor = db_connection_coma.cursor()
    cursor.execute("SELECT is_deleted, deleted_at FROM ClientOrder_MoneyTransferAgents WHERE assignment_id = ?", (assignment_id,))
    deleted_assignment_db = cursor.fetchone()
    assert deleted_assignment_db['is_deleted'] == 1
    assert deleted_assignment_db['deleted_at'] is not None

    # Check it's not returned by default getter
    assignments_after_delete = get_assigned_agents_for_client_order(
        client_id=prereqs["client_id"], order_id=prereqs["project_id"], conn=db_connection_coma
    )
    assert len(assignments_after_delete) == 0

    # Check it is returned with include_deleted=True
    assignments_with_deleted = get_assigned_agents_for_client_order(
        client_id=prereqs["client_id"], order_id=prereqs["project_id"], conn=db_connection_coma, include_deleted=True
    )
    assert len(assignments_with_deleted) == 1


def test_update_assignment_details(db_connection_coma):
    prereqs = create_coma_prerequisites(db_connection_coma)
    assign_res = assign_agent_to_client_order(
        client_id=prereqs["client_id"], order_id=prereqs["project_id"], agent_id=prereqs["agent_id"],
        assignment_details="Initial details", fee_estimate=100.0,
        conn=db_connection_coma
    )
    assignment_id = assign_res['assignment_id']

    original_assignment = db_connection_coma.execute("SELECT * FROM ClientOrder_MoneyTransferAgents WHERE assignment_id = ?", (assignment_id,)).fetchone()
    original_updated_at = original_assignment['updated_at']

    import time; time.sleep(0.01) # Ensure updated_at changes

    update_payload = {
        "details": "Updated assignment details",
        "fee": 200.50,
        "email_status": "Sent"
    }
    update_result = update_assignment_details(assignment_id, **update_payload, conn=db_connection_coma)
    assert update_result['success']
    assert update_result['updated_count'] == 1

    updated_assignment_db = db_connection_coma.execute("SELECT * FROM ClientOrder_MoneyTransferAgents WHERE assignment_id = ?", (assignment_id,)).fetchone()
    assert updated_assignment_db['assignment_details'] == "Updated assignment details"
    assert updated_assignment_db['fee_estimate'] == 200.50
    assert updated_assignment_db['email_status'] == "Sent"
    assert updated_assignment_db['updated_at'] > original_updated_at

    # Test updating only one field
    time.sleep(0.01)
    further_update_payload = {"email_status": "Failed"}
    further_update_result = update_assignment_details(assignment_id, **further_update_payload, conn=db_connection_coma)
    assert further_update_result['success']

    final_assignment_db = db_connection_coma.execute("SELECT * FROM ClientOrder_MoneyTransferAgents WHERE assignment_id = ?", (assignment_id,)).fetchone()
    assert final_assignment_db['email_status'] == "Failed"
    assert final_assignment_db['assignment_details'] == "Updated assignment details" # Should remain unchanged
    assert final_assignment_db['updated_at'] > updated_assignment_db['updated_at']

    # Test invalid email_status
    invalid_status_payload = {"email_status": "DefinitelyWrong"}
    invalid_status_result = update_assignment_details(assignment_id, **invalid_status_payload, conn=db_connection_coma)
    assert not invalid_status_result['success']
    assert "Invalid email_status" in invalid_status_result.get('error', '')

    # Test update non-existent assignment
    non_existent_update = update_assignment_details(str(uuid.uuid4()), details="Ghost update", conn=db_connection_coma)
    assert not non_existent_update['success']
    assert non_existent_update.get('updated_count', 0) == 0
    assert "not found" in non_existent_update.get('error', '').lower()
