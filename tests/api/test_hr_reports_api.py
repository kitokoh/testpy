import pytest
from fastapi import FastAPI, Depends, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional, Any, Dict, Callable, List as PyList
from datetime import date, datetime, timedelta

# Adjust these imports based on your project structure
from api.models import (
    Base, UserInDB, Employee, LeaveType, LeaveRequest, LeaveRequestStatusEnum,
    HeadcountReportResponse, AnniversaryReportResponse, LeaveSummaryReportResponse
)
from api.hr_reports import router as hr_reports_router # The router to test
from api.dependencies import get_db         # The actual DB dependency
from api.auth import get_current_active_user # The actual auth dependency

# Import CRUD modules for setting up test data
from db.cruds import employees_crud, leave_crud, users_crud, hr_reports_crud

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
current_mock_user: Optional[UserInDB] = None # Global variable

def mock_get_current_active_user() -> Optional[UserInDB]:
    if current_mock_user is None: raise Exception("Mock user not set for test")
    return current_mock_user

@pytest.fixture
def mock_user_factory() -> Callable[[str, str], UserInDB]:
    def _create_mock_user(user_id: str, role: str) -> UserInDB:
        return UserInDB(user_id=user_id, username=f"user_{user_id}", email=f"user_{user_id}@example.com", role=role, is_active=True, full_name=f"User {user_id}")
    return _create_mock_user

@pytest.fixture
def create_test_user_in_db(test_db_session: Session) -> Callable[[str, str], User]:
    def _create_user(user_id: str, role: str) -> User:
        # Simplified User creation for testing
        user = User(id=user_id, username=f"db_user_{user_id}", email=f"db_{user_id}@example.com", role=role, password_hash="test", salt="test", is_active=True)
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        return user
    return _create_user

@pytest.fixture
def create_test_employee_in_db(test_db_session: Session) -> Callable[[str, str, Optional[str], date], Employee]:
    def _create_employee(emp_id: str, name_suffix: str, department: Optional[str], start_date: date) -> Employee:
        from api.models import EmployeeCreate # Ensure EmployeeCreate is available if needed by CRUD
        # Using direct model for simplicity here if EmployeeCreate isn't strictly needed or adds complexity
        emp = Employee(id=emp_id, first_name=f"Emp{name_suffix}", last_name="Test",
                       email=f"emp_hr_api{name_suffix}@example.com",
                       department=department, start_date=start_date, is_active=True)
        test_db_session.add(emp)
        test_db_session.commit()
        test_db_session.refresh(emp)
        return emp
    return _create_employee

# --- TestClient Setup ---
@pytest.fixture(scope="function")
def client(test_db_session: Session) -> Generator[TestClient, None, None]:
    global current_mock_user
    app = FastAPI(title="Test HR Reports API")
    app.include_router(hr_reports_router)
    app.dependency_overrides[get_db] = lambda: test_db_session
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    current_mock_user = None

# --- Common Test Users Setup ---
@pytest.fixture
def hr_user_setup(test_db_session: Session, mock_user_factory: Callable, create_test_user_in_db, create_test_employee_in_db):
    hr_db_user = create_test_user_in_db("hr_rep_uid", "hr_manager")
    create_test_employee_in_db(hr_db_user.id, "_hr_rep", "HR", date(2019,1,1)) # Ensure HR user is also an employee if needed
    return mock_user_factory(hr_db_user.id, "hr_manager")

@pytest.fixture
def employee_user_setup(test_db_session: Session, mock_user_factory: Callable, create_test_user_in_db, create_test_employee_in_db):
    emp_db_user = create_test_user_in_db("emp_rep_uid", "employee")
    create_test_employee_in_db(emp_db_user.id, "_emp_rep", "Tech", date(2020,1,1))
    return mock_user_factory(emp_db_user.id, "employee")


# --- Tests for Headcount Report ---
def test_get_headcount_report_endpoint(client: TestClient, test_db_session: Session, hr_user_setup, create_test_employee_in_db):
    global current_mock_user
    current_mock_user = hr_user_setup

    create_test_employee_in_db("hc_e1", "HC1", "Engineering", date(2021,1,1))
    create_test_employee_in_db("hc_e2", "HC2", "Engineering", date(2022,1,1))
    create_test_employee_in_db("hc_e3", "HC3", "Sales", date(2021,5,1))
    create_test_employee_in_db("hc_e4", "HC4", None, date(2020,3,1)) # No department
    create_test_employee_in_db("hc_e5", "HC5", "", date(2020,3,1)) # Empty string department (becomes "N/A" via coalesce in current CRUD)
                                                                # Or, if coalesce(field, "N/A") doesn't treat "" as NULL, it'll be a separate group.
                                                                # The CRUD uses `func.coalesce(Employee.department, "N/A")`
                                                                # which treats NULL as N/A. Empty string "" is a valid value and will be its own group.
                                                                # To make "" also "N/A", query needs: `case([(Employee.department == None, "N/A"), (Employee.department == "", "N/A")], else_=Employee.department)`
                                                                # For now, assume "" is distinct or test current behavior.
                                                                # The Pydantic model HeadcountReportItem defaults department to "N/A",
                                                                # so if query returns None for dept, Pydantic handles it.
                                                                # If query returns "" for dept, Pydantic takes it as is.

    response = client.get("/hr-reports/headcount-by-department")
    assert response.status_code == status.HTTP_200_OK
    data = HeadcountReportResponse(**response.json())
    assert data.report_name == "Department Headcount"
    assert isinstance(data.generated_at, datetime)

    # Convert list of Pydantic items to list of dicts for easier comparison if order is not guaranteed
    report_items = sorted([item.model_dump() for item in data.data], key=lambda x: x["department"])

    expected_departments = sorted([
        {"department": "Engineering", "count": 2},
        {"department": "Sales", "count": 1},
        {"department": "N/A", "count": 1}, # For the NULL department employee
        {"department": "", "count": 1}     # For the empty string department employee
    ], key=lambda x: x["department"])

    assert report_items == expected_departments

def test_get_headcount_report_unauthorized(client: TestClient, employee_user_setup):
    global current_mock_user
    current_mock_user = employee_user_setup # Regular employee
    response = client.get("/hr-reports/headcount-by-department")
    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- Tests for Upcoming Anniversaries Report ---
@pytest.fixture
def mock_anniversary_date_today(monkeypatch):
    fixed_today = date(2024, 5, 15) # May 15, 2024
    class MockDate(date):
        @classmethod
        def today(cls): return fixed_today
    monkeypatch.setattr(datetime, 'date', MockDate) # Patch datetime.date used by FastAPI/Pydantic
    monkeypatch.setattr(hr_reports_crud, 'date', MockDate) # Patch date used in CRUD
    return fixed_today

def test_get_upcoming_anniversaries_report_endpoint(client: TestClient, test_db_session: Session, hr_user_setup, create_test_employee_in_db, mock_anniversary_date_today):
    global current_mock_user
    current_mock_user = hr_user_setup
    fixed_today = mock_anniversary_date_today

    # Anniv in 20 days (June 4, 2024) -> YOS based on 2024-06-04
    create_test_employee_in_db("anniv_e1", "Anniv1", "HR", date(2020, 6, 4)) # 4 years
    # Anniv in 5 days (May 20, 2024)
    create_test_employee_in_db("anniv_e2", "Anniv2", "HR", date(2021, 5, 20)) # 3 years
    # Anniv passed (May 1, 2024)
    create_test_employee_in_db("anniv_e3", "Anniv3", "HR", date(2019, 5, 1))
    # Anniv too far (e.g. 40 days for default 30 days_ahead window) (June 24, 2024)
    create_test_employee_in_db("anniv_e4", "Anniv4", "HR", date(2018, 6, 24))

    # Test with default days_ahead=30 (May 15 to June 14)
    response = client.get("/hr-reports/upcoming-anniversaries")
    assert response.status_code == status.HTTP_200_OK
    data = AnniversaryReportResponse(**response.json())
    assert data.time_window_days == 30
    assert len(data.data) == 2 # e1 and e2
    emp_ids_in_report = {item.employee_id for item in data.data}
    assert "anniv_e1" in emp_ids_in_report
    assert "anniv_e2" in emp_ids_in_report
    for item in data.data:
        if item.employee_id == "anniv_e1": assert item.years_of_service == 4
        if item.employee_id == "anniv_e2": assert item.years_of_service == 3


    # Test with days_ahead=40 (May 15 to June 24)
    response_60 = client.get("/hr-reports/upcoming-anniversaries?days_ahead=40")
    assert response_60.status_code == status.HTTP_200_OK
    data_60 = AnniversaryReportResponse(**response_60.json())
    assert data_60.time_window_days == 40
    assert len(data_60.data) == 3 # e1, e2, e4
    assert "anniv_e4" in {item.employee_id for item in data_60.data}

    # Test invalid days_ahead
    assert client.get("/hr-reports/upcoming-anniversaries?days_ahead=5").status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert client.get("/hr-reports/upcoming-anniversaries?days_ahead=400").status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_get_anniversary_report_unauthorized(client: TestClient, employee_user_setup):
    global current_mock_user
    current_mock_user = employee_user_setup
    assert client.get("/hr-reports/upcoming-anniversaries").status_code == status.HTTP_403_FORBIDDEN

# --- Tests for Leave Summary Report ---
@pytest.fixture
def setup_api_leave_data(test_db_session: Session, hr_user_setup, create_test_employee_in_db):
    global current_mock_user # To allow leave type creation by hr_user
    current_mock_user = hr_user_setup

    emp1 = create_test_employee_in_db("lsr_e1", "LSR1", "FIN", date(2020,1,1))
    lt_vac = leave_crud.create_leave_type(test_db_session, LeaveTypeCreate(name="Vacation Days API"))
    lt_sick = leave_crud.create_leave_type(test_db_session, LeaveTypeCreate(name="Sick Days API"))

    # Create dummy user for approving requests
    approver = User(id="approver_api_uid", username="approver_api", email="approver_api@example.com", role="manager", password_hash="h", salt="s")
    test_db_session.add(approver)
    test_db_session.commit()

    # Approved Vacation
    lr1_data = LeaveRequestCreate(leave_type_id=lt_vac.id, start_date=date(2023,1,5), end_date=date(2023,1,6), num_days=2.0)
    lr1 = leave_crud.create_leave_request(test_db_session, emp1.id, lr1_data)
    leave_crud.update_leave_request_status(test_db_session, lr1.id, LeaveRequestStatusEnum.APPROVED, approver.id)
    # Pending Sick
    lr2_data = LeaveRequestCreate(leave_type_id=lt_sick.id, start_date=date(2023,3,5), end_date=date(2023,3,5), num_days=1.0)
    leave_crud.create_leave_request(test_db_session, emp1.id, lr2_data)

    return {"lt_vac_name": lt_vac.name, "lt_sick_name": lt_sick.name}


def test_get_leave_summary_report_endpoint(client: TestClient, hr_user_setup, setup_api_leave_data):
    global current_mock_user
    current_mock_user = hr_user_setup
    names = setup_api_leave_data

    # No filter
    response = client.get("/hr-reports/leave-summary")
    assert response.status_code == status.HTTP_200_OK
    data = LeaveSummaryReportResponse(**response.json())
    assert data.filter_status is None
    # Expecting Vacation (Approved 2 days, 1 req) and Sick (Pending 1 day, 1 req)
    # The CRUD sums all non-cancelled/rejected if no filter, or as per its logic.
    # Current CRUD `get_leave_summary_by_type` sums all if no filter.
    assert len(data.data) == 2
    for item in data.data:
        if item.leave_type_name == names["lt_vac_name"]:
            assert item.total_days_taken_or_requested == 2.0
            assert item.number_of_requests == 1
        elif item.leave_type_name == names["lt_sick_name"]:
            assert item.total_days_taken_or_requested == 1.0
            assert item.number_of_requests == 1

    # Filter by APPROVED
    response_approved = client.get("/hr-reports/leave-summary?status_filter=approved")
    assert response_approved.status_code == status.HTTP_200_OK
    data_approved = LeaveSummaryReportResponse(**response_approved.json())
    assert data_approved.filter_status == "approved"
    assert len(data_approved.data) == 1
    assert data_approved.data[0].leave_type_name == names["lt_vac_name"]
    assert data_approved.data[0].total_days_taken_or_requested == 2.0

    # Filter by PENDING
    response_pending = client.get("/hr-reports/leave-summary?status_filter=pending")
    assert response_pending.status_code == status.HTTP_200_OK
    data_pending = LeaveSummaryReportResponse(**response_pending.json())
    assert data_pending.filter_status == "pending"
    assert len(data_pending.data) == 1
    assert data_pending.data[0].leave_type_name == names["lt_sick_name"]
    assert data_pending.data[0].total_days_taken_or_requested == 1.0

    # Invalid status_filter
    response_invalid_status = client.get("/hr-reports/leave-summary?status_filter=weird_status")
    assert response_invalid_status.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_get_leave_summary_unauthorized(client: TestClient, employee_user_setup):
    global current_mock_user
    current_mock_user = employee_user_setup
    assert client.get("/hr-reports/leave-summary").status_code == status.HTTP_403_FORBIDDEN
