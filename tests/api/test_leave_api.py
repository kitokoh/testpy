import pytest
from fastapi import FastAPI, Depends, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional, Any, Dict, Callable, List as PyList # Renamed List to PyList
from datetime import date, datetime

# Adjust these imports based on your project structure
from api.models import (
    Base, UserInDB, Employee, LeaveType, LeaveBalance, LeaveRequest, # SQLAlchemy models
    LeaveTypeCreate, LeaveTypeResponse, LeaveTypeBase,
    LeaveBalanceCreate, LeaveBalanceResponse, LeaveBalanceUpdate,
    LeaveRequestCreate, LeaveRequestResponse, LeaveRequestUpdate,
    LeaveRequestStatusEnum
)
from api.leave import router as leave_router # The router to test
from api.dependencies import get_db         # The actual DB dependency
from api.auth import get_current_active_user # The actual auth dependency

from db.cruds import employees_crud, leave_crud # For setting up test data

# --- Test Database Setup ---
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def test_db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
        Base.metadata.drop_all(bind=engine)

# --- Mock User and Authentication ---
current_mock_user: Optional[UserInDB] = None # Global variable to hold the current mock user

def mock_get_current_active_user() -> Optional[UserInDB]:
    if current_mock_user is None: # Should not happen if tests set user appropriately
        raise Exception("Mock user not set for test")
    return current_mock_user

@pytest.fixture
def mock_user_factory() -> Callable[[str, str, Optional[str]], UserInDB]:
    def _create_mock_user(user_id: str, role: str, email_suffix: Optional[str] = None) -> UserInDB:
        email = f"user_{user_id}{'_' + email_suffix if email_suffix else ''}@example.com"
        return UserInDB(user_id=user_id, username=f"user_{user_id}", email=email, role=role, is_active=True, full_name=f"User {user_id}")
    return _create_mock_user

# --- TestClient Setup ---
@pytest.fixture(scope="function")
def client(test_db_session: Session) -> Generator[TestClient, None, None]: # Removed mock_user_factory from client fixture params
    global current_mock_user

    app = FastAPI()
    app.include_router(leave_router)
    app.dependency_overrides[get_db] = lambda: test_db_session
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    current_mock_user = None


# --- Helper Functions for Test Data ---
def create_test_employee(db: Session, user_id: str, first_name: str, last_name: str, email_suffix: str) -> Employee:
    employee = Employee(id=user_id, first_name=first_name, last_name=last_name, email=f"{user_id}{email_suffix}@example.com", start_date=date(2020,1,1))
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee

# --- Tests for Leave Types Endpoints ---

def test_create_leave_type_admin(client: TestClient, test_db_session: Session, mock_user_factory: Callable):
    global current_mock_user
    current_mock_user = mock_user_factory("admin_user_ct", "admin")
    response = client.post("/leave/types/", json={"name": "Vacation", "default_days_entitled": 20})
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Vacation"
    assert data["default_days_entitled"] == 20

def test_create_leave_type_duplicate(client: TestClient, test_db_session: Session, mock_user_factory: Callable):
    global current_mock_user
    current_mock_user = mock_user_factory("admin_user_ctd", "admin")
    client.post("/leave/types/", json={"name": "Sick Time"})
    response = client.post("/leave/types/", json={"name": "Sick Time"})
    assert response.status_code == status.HTTP_409_CONFLICT

def test_create_leave_type_unauthorized(client: TestClient, mock_user_factory: Callable):
    global current_mock_user
    current_mock_user = mock_user_factory("employee_user_ctu", "employee")
    response = client.post("/leave/types/", json={"name": "Unauthorized Creation"})
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_read_leave_types(client: TestClient, test_db_session: Session, mock_user_factory: Callable):
    global current_mock_user
    current_mock_user = mock_user_factory("admin_user_rlt", "admin") # For creation
    leave_crud.create_leave_type(test_db_session, LeaveTypeCreate(name="Type Alpha"))

    current_mock_user = mock_user_factory("any_user_rlt", "employee") # Any authenticated user can read
    response = client.get("/leave/types/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 1
    assert response.json()[0]["name"] == "Type Alpha"

def test_read_one_leave_type(client: TestClient, test_db_session: Session, mock_user_factory: Callable):
    global current_mock_user
    current_mock_user = mock_user_factory("admin_user_rolt", "admin")
    lt = leave_crud.create_leave_type(test_db_session, LeaveTypeCreate(name="Specific Type"))

    current_mock_user = mock_user_factory("any_user_rolt", "employee")
    response = client.get(f"/leave/types/{lt.id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Specific Type"

    response_404 = client.get("/leave/types/9999")
    assert response_404.status_code == status.HTTP_404_NOT_FOUND

def test_update_leave_type(client: TestClient, test_db_session: Session, mock_user_factory: Callable):
    global current_mock_user
    current_mock_user = mock_user_factory("admin_user_ult", "admin")
    lt = leave_crud.create_leave_type(test_db_session, LeaveTypeCreate(name="Original Name"))
    leave_crud.create_leave_type(test_db_session, LeaveTypeCreate(name="Existing Name")) # For duplicate check

    # Successful update
    response = client.put(f"/leave/types/{lt.id}", json={"name": "Updated Name", "default_days_entitled": 15})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Updated Name"
    assert response.json()["default_days_entitled"] == 15

    # Update non-existent
    response_404 = client.put("/leave/types/9999", json={"name": "No Such Type"})
    assert response_404.status_code == status.HTTP_404_NOT_FOUND

    # Update causing duplicate name
    response_409 = client.put(f"/leave/types/{lt.id}", json={"name": "Existing Name"})
    assert response_409.status_code == status.HTTP_409_CONFLICT

    # Unauthorized update
    current_mock_user = mock_user_factory("employee_user_ult", "employee")
    response_403 = client.put(f"/leave/types/{lt.id}", json={"name": "Attempted Update"})
    assert response_403.status_code == status.HTTP_403_FORBIDDEN

def test_delete_leave_type(client: TestClient, test_db_session: Session, mock_user_factory: Callable):
    global current_mock_user
    current_mock_user = mock_user_factory("admin_user_dlt", "admin")
    lt = leave_crud.create_leave_type(test_db_session, LeaveTypeCreate(name="To Be Deleted"))

    # Successful deletion
    response = client.delete(f"/leave/types/{lt.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT # Or 200 if item returned

    # Delete non-existent
    response_404 = client.delete("/leave/types/9999")
    assert response_404.status_code == status.HTTP_404_NOT_FOUND

    # Unauthorized deletion
    lt2 = leave_crud.create_leave_type(test_db_session, LeaveTypeCreate(name="Delete Protected"))
    current_mock_user = mock_user_factory("employee_user_dlt", "employee")
    response_403 = client.delete(f"/leave/types/{lt2.id}")
    assert response_403.status_code == status.HTTP_403_FORBIDDEN

# --- Tests for Leave Balances Endpoints ---

def test_create_leave_balance(client: TestClient, test_db_session: Session, mock_user_factory: Callable):
    global current_mock_user
    admin_user = mock_user_factory("admin_clb", "admin")
    employee_user = mock_user_factory("emp_clb", "employee") # Target employee
    create_test_employee(test_db_session, employee_user.user_id, "Balance", "Emp", "_clb")
    lt = leave_crud.create_leave_type(test_db_session, LeaveTypeCreate(name="Balance Type CLB"))

    # Admin creates balance
    current_mock_user = admin_user
    payload = {"employee_id": employee_user.user_id, "leave_type_id": lt.id, "year": 2024, "entitled_days": 12}
    response = client.post("/leave/balances/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["employee_id"] == employee_user.user_id
    assert data["year"] == 2024

    # Duplicate creation
    response_409 = client.post("/leave/balances/", json=payload)
    assert response_409.status_code == status.HTTP_409_CONFLICT

    # Non-admin tries to create
    current_mock_user = employee_user # Regular employee
    response_403 = client.post("/leave/balances/", json={**payload, "year": 2025}) # Change year to avoid 409
    assert response_403.status_code == status.HTTP_403_FORBIDDEN

    # Non-existent employee
    current_mock_user = admin_user
    response_404_emp = client.post("/leave/balances/", json={**payload, "employee_id": "ghost_emp", "year": 2026})
    assert response_404_emp.status_code == status.HTTP_404_NOT_FOUND

    # Non-existent leave type
    response_404_lt = client.post("/leave/balances/", json={**payload, "leave_type_id": 9998, "year": 2026})
    assert response_404_lt.status_code == status.HTTP_404_NOT_FOUND

def test_read_employee_leave_balances(client: TestClient, test_db_session: Session, mock_user_factory: Callable):
    global current_mock_user
    admin_user = mock_user_factory("admin_rlb", "admin")
    emp1_user = mock_user_factory("emp1_rlb", "employee")
    emp2_user = mock_user_factory("emp2_rlb", "employee")
    create_test_employee(test_db_session, emp1_user.user_id, "EmpOne", "RLB", "_e1rlb")
    create_test_employee(test_db_session, emp2_user.user_id, "EmpTwo", "RLB", "_e2rlb")
    lt_rlb = leave_crud.create_leave_type(test_db_session, LeaveTypeCreate(name="Balance Type RLB"))

    # Create balances
    leave_crud.create_leave_balance(test_db_session, LeaveBalanceCreate(employee_id=emp1_user.user_id, leave_type_id=lt_rlb.id, year=2023, entitled_days=10))
    leave_crud.create_leave_balance(test_db_session, LeaveBalanceCreate(employee_id=emp1_user.user_id, leave_type_id=lt_rlb.id, year=2024, entitled_days=11))

    # Employee sees their own
    current_mock_user = emp1_user
    response_self = client.get(f"/leave/balances/employee/{emp1_user.user_id}")
    assert response_self.status_code == status.HTTP_200_OK
    assert len(response_self.json()) == 2

    # Employee sees their own for specific year
    response_self_year = client.get(f"/leave/balances/employee/{emp1_user.user_id}?year=2024")
    assert response_self_year.status_code == status.HTTP_200_OK
    assert len(response_self_year.json()) == 1
    assert response_self_year.json()[0]["year"] == 2024

    # Admin sees employee's balances
    current_mock_user = admin_user
    response_admin = client.get(f"/leave/balances/employee/{emp1_user.user_id}")
    assert response_admin.status_code == status.HTTP_200_OK
    assert len(response_admin.json()) == 2

    # Employee tries to see another's balances - FORBIDDEN
    current_mock_user = emp2_user
    response_other = client.get(f"/leave/balances/employee/{emp1_user.user_id}")
    assert response_other.status_code == status.HTTP_403_FORBIDDEN

def test_update_leave_balance(client: TestClient, test_db_session: Session, mock_user_factory: Callable):
    global current_mock_user
    admin_user = mock_user_factory("admin_ulb", "admin")
    emp_user = mock_user_factory("emp_ulb", "employee")
    create_test_employee(test_db_session, emp_user.user_id, "UpdateBal", "User", "_ulb")
    lt_ulb = leave_crud.create_leave_type(test_db_session, LeaveTypeCreate(name="Balance Type ULB"))
    balance = leave_crud.create_leave_balance(test_db_session, LeaveBalanceCreate(employee_id=emp_user.user_id, leave_type_id=lt_ulb.id, year=2024, entitled_days=15))

    # Admin updates
    current_mock_user = admin_user
    update_payload = {"entitled_days": 16.0, "used_days": 2.5}
    response = client.put(f"/leave/balances/{balance.id}", json=update_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["entitled_days"] == 16.0
    assert data["used_days"] == 2.5

    # Update non-existent
    response_404 = client.put("/leave/balances/99999", json=update_payload)
    assert response_404.status_code == status.HTTP_404_NOT_FOUND

    # Non-admin tries to update
    current_mock_user = emp_user
    response_403 = client.put(f"/leave/balances/{balance.id}", json={"used_days": 3.0})
    assert response_403.status_code == status.HTTP_403_FORBIDDEN

# --- Tests for Leave Requests Endpoints ---

@pytest.fixture
def setup_employee_and_leave_type(test_db_session: Session, mock_user_factory: Callable):
    global current_mock_user
    employee_user_id = "emp_lr_setup"
    current_mock_user = mock_user_factory(employee_user_id, "employee", "_lr_setup")
    employee = create_test_employee(test_db_session, employee_user_id, "LRSetup", "User", "_lr_setup")
    lt = leave_crud.create_leave_type(test_db_session, LeaveTypeCreate(name="Request Type Setup"))
    # Pre-create balance for the test employee and leave type for year 2024
    leave_crud.create_leave_balance(test_db_session, LeaveBalanceCreate(
        employee_id=employee.id, leave_type_id=lt.id, year=2024, entitled_days=10
    ))
    return employee, lt, current_mock_user # Return current_mock_user as it's set here

def test_submit_leave_request(client: TestClient, test_db_session: Session, setup_employee_and_leave_type):
    global current_mock_user
    employee, lt, current_mock_user = setup_employee_and_leave_type

    request_data = {"leave_type_id": lt.id, "start_date": "2024-08-05", "end_date": "2024-08-07", "num_days": 3.0, "reason": "Holiday"}
    response = client.post("/leave/requests/", json=request_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["employee_id"] == employee.id
    assert data["num_days"] == 3.0
    assert data["status"] == LeaveRequestStatusEnum.PENDING.value

    # Invalid num_days
    response_invalid_days = client.post("/leave/requests/", json={**request_data, "num_days": 0})
    assert response_invalid_days.status_code == status.HTTP_400_BAD_REQUEST

    # Non-existent leave type
    response_invalid_lt = client.post("/leave/requests/", json={**request_data, "leave_type_id": 999})
    assert response_invalid_lt.status_code == status.HTTP_404_NOT_FOUND


def test_read_my_leave_requests(client: TestClient, test_db_session: Session, setup_employee_and_leave_type):
    global current_mock_user
    employee, lt, current_mock_user = setup_employee_and_leave_type

    # Create some requests for this user
    client.post("/leave/requests/", json={"leave_type_id": lt.id, "start_date": "2024-09-02", "end_date": "2024-09-02", "num_days": 1.0})
    client.post("/leave/requests/", json={"leave_type_id": lt.id, "start_date": "2024-10-07", "end_date": "2024-10-07", "num_days": 1.0})

    response = client.get("/leave/requests/my")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2

def test_read_specific_leave_request(client: TestClient, test_db_session: Session, mock_user_factory: Callable, setup_employee_and_leave_type):
    global current_mock_user
    owner_employee, lt, owner_user = setup_employee_and_leave_type # owner_user is current_mock_user

    # Create a request as owner_user
    lr_response = client.post("/leave/requests/", json={"leave_type_id": lt.id, "start_date": "2024-11-04", "end_date": "2024-11-04", "num_days": 1.0})
    request_id = lr_response.json()["id"]

    # Owner reads their own request
    response_owner = client.get(f"/leave/requests/{request_id}")
    assert response_owner.status_code == status.HTTP_200_OK
    assert response_owner.json()["id"] == request_id

    # Admin reads it
    current_mock_user = mock_user_factory("admin_rsr", "admin")
    response_admin = client.get(f"/leave/requests/{request_id}")
    assert response_admin.status_code == status.HTTP_200_OK

    # Another employee tries to read it - FORBIDDEN
    current_mock_user = mock_user_factory("other_emp_rsr", "employee")
    create_test_employee(test_db_session, "other_emp_rsr", "Other", "Emp", "_otherrsr")
    response_other = client.get(f"/leave/requests/{request_id}")
    assert response_other.status_code == status.HTTP_403_FORBIDDEN

    # Non-existent request
    current_mock_user = owner_user # Switch back to owner for this check
    response_404 = client.get("/leave/requests/99999")
    assert response_404.status_code == status.HTTP_404_NOT_FOUND


def test_read_all_leave_requests_admin(client: TestClient, test_db_session: Session, mock_user_factory: Callable, setup_employee_and_leave_type):
    global current_mock_user
    employee, lt, _ = setup_employee_and_leave_type # Original employee who created some requests
    admin_user = mock_user_factory("admin_ralr", "admin")
    current_mock_user = admin_user # Set current user to admin for this test block

    # Create some requests as the initial employee (setup_employee_and_leave_type)
    client.post("/leave/requests/", json={"leave_type_id": lt.id, "start_date": "2024-07-15", "end_date": "2024-07-15", "num_days": 1.0})
    lr_pending_resp = client.post("/leave/requests/", json={"leave_type_id": lt.id, "start_date": "2024-07-16", "end_date": "2024-07-16", "num_days": 1.0})
    lr_to_approve_id = lr_pending_resp.json()["id"]

    # Admin approves one request to test status filter
    client.patch(f"/leave/requests/{lr_to_approve_id}/status", json={"status": "approved"})

    # Admin gets all requests (no filter) - should raise 400 as per current API spec
    response_all_nofilter = client.get("/leave/requests/")
    assert response_all_nofilter.status_code == status.HTTP_400_BAD_REQUEST # As per current spec

    # Admin filters by status: approved
    response_approved = client.get("/leave/requests/?status_filter=approved")
    assert response_approved.status_code == status.HTTP_200_OK
    assert len(response_approved.json()) == 1
    assert response_approved.json()[0]["status"] == "approved"

    # Admin filters by employee_id
    response_employee = client.get(f"/leave/requests/?employee_id={employee.id}")
    assert response_employee.status_code == status.HTTP_200_OK
    assert len(response_employee.json()) >= 2 # At least the two created here for this employee

    # Regular employee tries to access - FORBIDDEN
    current_mock_user = mock_user_factory("non_admin_ralr", "employee")
    create_test_employee(test_db_session, "non_admin_ralr", "NonAdmin", "User", "_nonadminralr")
    response_403 = client.get("/leave/requests/?status_filter=pending")
    assert response_403.status_code == status.HTTP_403_FORBIDDEN


def test_patch_leave_request_status(client: TestClient, test_db_session: Session, mock_user_factory: Callable, setup_employee_and_leave_type):
    global current_mock_user
    employee, lt, _ = setup_employee_and_leave_type
    admin_user = mock_user_factory("admin_patch_lr_status", "admin")

    # Create a PENDING request by the employee
    current_mock_user = setup_employee_and_leave_type[2] # The employee user
    lr_resp = client.post("/leave/requests/", json={"leave_type_id": lt.id, "start_date": "2024-12-02", "end_date": "2024-12-03", "num_days": 2.0})
    request_id = lr_resp.json()["id"]

    # Admin approves it
    current_mock_user = admin_user
    response_approve = client.patch(f"/leave/requests/{request_id}/status", json={"status": "approved", "comments": "Enjoy!"})
    assert response_approve.status_code == status.HTTP_200_OK
    assert response_approve.json()["status"] == "approved"
    balance = leave_crud.get_leave_balance(test_db_session, employee.id, lt.id, 2024)
    assert balance.used_days == 2.0 # Initial 0 + 2

    # Admin cancels the approved request
    response_cancel = client.patch(f"/leave/requests/{request_id}/status", json={"status": "cancelled", "comments": "User request"})
    assert response_cancel.status_code == status.HTTP_200_OK
    assert response_cancel.json()["status"] == "cancelled"
    test_db_session.refresh(balance) # Refresh balance after cancellation
    assert balance.used_days == 0.0 # 2 - 2

    # Admin tries to update non-existent request
    response_404 = client.patch("/leave/requests/99999/status", json={"status": "approved"})
    assert response_404.status_code == status.HTTP_404_NOT_FOUND

    # Admin tries to use invalid status string
    response_400_invalid_status = client.patch(f"/leave/requests/{request_id}/status", json={"status": "made_up_status"})
    assert response_400_invalid_status.status_code == status.HTTP_400_BAD_REQUEST # Or 422 from Pydantic if enum in body

    # Employee tries to change status - FORBIDDEN
    current_mock_user = setup_employee_and_leave_type[2] # The employee user
    response_403_emp_patch = client.patch(f"/leave/requests/{request_id}/status", json={"status": "approved"})
    assert response_403_emp_patch.status_code == status.HTTP_403_FORBIDDEN
