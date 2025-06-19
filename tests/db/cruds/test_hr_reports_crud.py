import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, List as PyList, Optional
from datetime import date, datetime, timedelta

# Adjust imports based on your project structure
from api.models import (
    Base, Employee, LeaveType, LeaveRequest, LeaveRequestStatusEnum,
    HeadcountReportItem, AnniversaryReportItem, LeaveSummaryReportItem
)
from db.cruds import hr_reports_crud, employees_crud, leave_crud # For setting up data

# Use an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
        Base.metadata.drop_all(bind=engine)

# --- Helper Functions ---
def create_test_employee(db: Session, first_name: str, last_name: str, email_suffix: str,
                         department: Optional[str], start_date: date, is_active: bool = True) -> Employee:
    # Ensure unique email if many employees are created
    emp_id = f"emp-hrrep-{email_suffix}-{datetime.now().microsecond}"
    emp = Employee(
        id=emp_id,
        first_name=first_name, last_name=last_name,
        email=f"hr.rep.{email_suffix}@example.com",
        department=department, start_date=start_date, is_active=is_active
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp

def create_test_leave_type(db: Session, name: str) -> LeaveType:
    from api.models import LeaveTypeCreate # Local import to avoid circularity if models are split
    lt_data = LeaveTypeCreate(name=name, default_days_entitled=10) # default_days not used by report
    return leave_crud.create_leave_type(db, leave_type_data=lt_data)

def create_test_leave_request(db: Session, employee_id: str, leave_type_id: int,
                              start_date: date, end_date: date, num_days: float,
                              status: LeaveRequestStatusEnum) -> LeaveRequest:
    from api.models import LeaveRequestCreate # Local import
    # Need a user to be the requester, or handle approved_by_id if relevant for status
    # For this CRUD, employee_id is what matters from LeaveRequestCreate.
    lr_data = LeaveRequestCreate(
        leave_type_id=leave_type_id,
        start_date=start_date,
        end_date=end_date,
        num_days=num_days,
        reason="Test Request"
    )
    # Create request with PENDING status first
    created_lr = leave_crud.create_leave_request(db, employee_id=employee_id, leave_request_data=lr_data)
    # Then update status if not PENDING
    if status != LeaveRequestStatusEnum.PENDING:
        # Dummy approver_id, assuming User model exists if needed by update_leave_request_status
        # For simplicity, assuming User table exists and 'system_approver' is a valid ID or can be None.
        # The current leave_crud.update_leave_request_status takes processed_by_user_id
        # We need a dummy user for this.
        from api.models import User # Local import
        dummy_approver = db.query(User).filter(User.id == "system_approver").first()
        if not dummy_approver:
            dummy_approver = User(id="system_approver", username="sysapprover", email="sys@approver.com", role="system", password_hash="h", salt="s")
            db.add(dummy_approver)
            db.commit()
            db.refresh(dummy_approver)

        updated_lr = leave_crud.update_leave_request_status(db, created_lr.id, status, dummy_approver.id)
        if updated_lr: return updated_lr
        return created_lr # Should not happen if update is successful
    return created_lr


# --- I. get_department_headcounts Tests ---

def test_get_department_headcounts_empty(db_session: Session):
    result = hr_reports_crud.get_department_headcounts(db_session)
    assert result == []

def test_get_department_headcounts_single_department(db_session: Session):
    create_test_employee(db_session, "E1", "LN1", "e1", "Engineering", date(2022,1,1))
    create_test_employee(db_session, "E2", "LN2", "e2", "Engineering", date(2022,1,1))
    result = hr_reports_crud.get_department_headcounts(db_session)
    assert len(result) == 1
    assert result[0] == HeadcountReportItem(department="Engineering", count=2)

def test_get_department_headcounts_multiple_departments(db_session: Session):
    create_test_employee(db_session, "E1", "LN1", "e1", "Engineering", date(2022,1,1))
    create_test_employee(db_session, "E2", "LN2", "e2", "Marketing", date(2022,1,1))
    create_test_employee(db_session, "E3", "LN3", "e3", "Engineering", date(2022,1,1))
    result = hr_reports_crud.get_department_headcounts(db_session)
    assert len(result) == 2
    # Order might vary based on DB, so check content
    expected = [HeadcountReportItem(department="Engineering", count=2), HeadcountReportItem(department="Marketing", count=1)]
    assert all(item in result for item in expected) and all(item in expected for item in result)


def test_get_department_headcounts_with_null_or_empty_department(db_session: Session):
    create_test_employee(db_session, "E1", "LN1", "e1", None, date(2022,1,1))
    create_test_employee(db_session, "E2", "LN2", "e2", "Sales", date(2022,1,1))
    create_test_employee(db_session, "E3", "LN3", "e3", None, date(2022,1,1)) # Another None
    # create_test_employee(db_session, "E4", "LN4", "e4", "", date(2022,1,1)) # Test empty string if coalesce handles it
    # The current coalesce(Employee.department, "N/A") handles NULL. Empty string "" is treated as a distinct department.
    # If "" should also be "N/A", the query needs `case`. For now, testing coalesce behavior.
    result = hr_reports_crud.get_department_headcounts(db_session)

    # Expected: One group for "N/A" (2 employees), one for "Sales" (1 employee)
    na_count = 0
    sales_count = 0
    for item in result:
        if item.department == "N/A":
            na_count = item.count
        elif item.department == "Sales":
            sales_count = item.count

    assert na_count == 2
    assert sales_count == 1
    assert len(result) == 2


# --- II. get_upcoming_anniversaries Tests ---

@pytest.fixture
def mock_date_today(monkeypatch):
    """Fixture to mock date.today() for deterministic anniversary tests."""
    class MockDate(date):
        @classmethod
        def today(cls):
            return date(2024, 3, 10) # Fixed "today" for testing: March 10, 2024 (Sunday)
    monkeypatch.setattr(date, 'today', MockDate.today)
    monkeypatch.setattr(hr_reports_crud, 'date', MockDate) # Also patch where date is imported in CRUD module

def test_get_upcoming_anniversaries_empty(db_session: Session, mock_date_today):
    result = hr_reports_crud.get_upcoming_anniversaries(db_session, days_ahead=30)
    assert result == []

def test_get_upcoming_anniversaries_no_upcoming(db_session: Session, mock_date_today):
    create_test_employee(db_session, "Far", "Future", "far", "HR", date(2020, 12, 25)) # Anniversary Dec 25
    create_test_employee(db_session, "Past", "Anniv", "past", "HR", date(2020, 1, 5))   # Anniversary Jan 5 (passed for Mar 10)
    result = hr_reports_crud.get_upcoming_anniversaries(db_session, days_ahead=30) # Window: Mar 10 - Apr 9
    assert result == []

def test_get_upcoming_anniversaries_various_scenarios(db_session: Session, mock_date_today):
    # Today is Mar 10, 2024. days_ahead = 30. Window: Mar 10 - Apr 9, 2024
    days_ahead = 30

    # Anniversary tomorrow (Mar 11)
    emp_tmr = create_test_employee(db_session, "Tomorrow", "User", "tmr", "ENG", date(2020, 3, 11))
    # Anniversary days_ahead - 1 (Apr 8)
    emp_almost_end = create_test_employee(db_session, "Almost", "End", "almost", "ENG", date(2021, 4, 8))
    # Anniversary days_ahead (Apr 9)
    emp_at_end = create_test_employee(db_session, "At", "End", "at_end", "ENG", date(2022, 4, 9))
    # Anniversary yesterday (Mar 9) - Should NOT appear
    create_test_employee(db_session, "Yesterday", "User", "yst", "SALE", date(2019, 3, 9))
    # Anniversary days_ahead + 1 (Apr 10) - Should NOT appear
    create_test_employee(db_session, "Too", "Late", "late", "SALE", date(2018, 4, 10))
    # Anniversary today (Mar 10) - Should appear
    emp_today = create_test_employee(db_session, "Today", "User", "today", "FIN", date(2017, 3, 10))

    # Feb 29 scenario - Start date Feb 29, 2020 (leap year). Today is Mar 10, 2024 (leap year).
    # Anniversary this year: Feb 29, 2024 (passed). Next: Feb 28, 2025.
    # If days_ahead was ~360, this would be tested. For days_ahead=30, it won't show.
    # Let's make one that *would* show if logic is right for non-leap year handling.
    # Start date: Mar 15, 2020. Today: Mar 10, 2024. Anniversary: Mar 15, 2024 (upcoming)
    emp_mar15 = create_test_employee(db_session, "Mar15", "Test", "mar15", "ACC", date(2020, 3, 15))

    # Test Feb 29 specifically for the logic in CRUD (approximates to Feb 28 in non-leap for next anniversary)
    # Start date Feb 29, 2020. Today is Mar 10, 2024.
    # Anniversary 2024 was Feb 29 (passed).
    # Next anniversary is Feb 28, 2025 (as 2025 is not leap).
    # This won't fall in 30 day window.
    # To test Feb 29 logic: set today to e.g. Feb 25, 2025. Anniversary: Feb 28, 2025.
    # This requires more complex mock_date_today or separate test. For now, rely on CRUD's internal logic.

    result = hr_reports_crud.get_upcoming_anniversaries(db_session, days_ahead=days_ahead)

    assert len(result) == 4 # emp_tmr, emp_almost_end, emp_at_end, emp_today, emp_mar15

    result_emp_ids = {item.employee_id for item in result}
    assert emp_tmr.id in result_emp_ids
    assert emp_almost_end.id in result_emp_ids
    assert emp_at_end.id in result_emp_ids
    assert emp_today.id in result_emp_ids
    assert emp_mar15.id in result_emp_ids # Added this, so count should be 5

    # Re-verify counts based on logic
    # Today: 2024-03-10. Window: 2024-03-10 to 2024-04-09
    # emp_tmr (2020-03-11) -> Anniv: 2024-03-11 (In window). YOS: 4
    # emp_almost_end (2021-04-08) -> Anniv: 2024-04-08 (In window). YOS: 3
    # emp_at_end (2022-04-09) -> Anniv: 2024-04-09 (In window). YOS: 2
    # emp_today (2017-03-10) -> Anniv: 2024-03-10 (In window). YOS: 7
    # emp_mar15 (2020-03-15) -> Anniv: 2024-03-15 (In window). YOS: 4
    assert len(result) == 5

    for item in result:
        if item.employee_id == emp_tmr.id:
            assert item.anniversary_date == date(2024, 3, 11)
            assert item.years_of_service == 4
        if item.employee_id == emp_today.id:
            assert item.anniversary_date == date(2024, 3, 10)
            assert item.years_of_service == 7


# --- III. get_leave_summary_by_type Tests ---

@pytest.fixture
def setup_leave_data(db_session: Session):
    emp1 = create_test_employee(db_session, "LSum", "Emp1", "lsum1", "HR", date(2020,1,1))
    lt_vac = create_test_leave_type(db_session, "Vacation Days")
    lt_sick = create_test_leave_type(db_session, "Sick Days")
    lt_unpaid = create_test_leave_type(db_session, "Unpaid Time Off") # Type with no requests

    # Approved Vacation
    create_test_leave_request(db_session, emp1.id, lt_vac.id, date(2023,1,5), date(2023,1,6), 2.0, LeaveRequestStatusEnum.APPROVED)
    create_test_leave_request(db_session, emp1.id, lt_vac.id, date(2023,2,10), date(2023,2,10), 1.0, LeaveRequestStatusEnum.APPROVED)
    # Pending Vacation
    create_test_leave_request(db_session, emp1.id, lt_vac.id, date(2023,3,5), date(2023,3,5), 1.0, LeaveRequestStatusEnum.PENDING)
    # Approved Sick
    create_test_leave_request(db_session, emp1.id, lt_sick.id, date(2023,4,1), date(2023,4,1), 1.0, LeaveRequestStatusEnum.APPROVED)
    # Rejected Sick
    create_test_leave_request(db_session, emp1.id, lt_sick.id, date(2023,5,1), date(2023,5,1), 1.0, LeaveRequestStatusEnum.REJECTED)
    return {"lt_vac_name": lt_vac.name, "lt_sick_name": lt_sick.name, "lt_unpaid_name": lt_unpaid.name}

def test_get_leave_summary_empty(db_session: Session):
    result = hr_reports_crud.get_leave_summary_by_type(db_session)
    assert result == []

def test_get_leave_summary_no_filter(db_session: Session, setup_leave_data):
    result = hr_reports_crud.get_leave_summary_by_type(db_session)
    # Expecting all non-rejected/non-cancelled requests to be summed up if no status filter means "active"
    # The CRUD currently does not filter by default if status_filter is None. So it sums all.
    # Vacation: 2+1+1=4 days, 3 requests
    # Sick: 1+1=2 days, 2 requests
    assert len(result) == 2
    for item in result:
        if item.leave_type_name == setup_leave_data["lt_vac_name"]:
            assert item.total_days_taken_or_requested == 4.0
            assert item.number_of_requests == 3
        elif item.leave_type_name == setup_leave_data["lt_sick_name"]:
            assert item.total_days_taken_or_requested == 2.0
            assert item.number_of_requests == 2

def test_get_leave_summary_with_status_filter_approved(db_session: Session, setup_leave_data):
    result = hr_reports_crud.get_leave_summary_by_type(db_session, status_filter=LeaveRequestStatusEnum.APPROVED)
    # Vacation: 2+1=3 days, 2 requests
    # Sick: 1 day, 1 request
    assert len(result) == 2
    for item in result:
        if item.leave_type_name == setup_leave_data["lt_vac_name"]:
            assert item.total_days_taken_or_requested == 3.0
            assert item.number_of_requests == 2
        elif item.leave_type_name == setup_leave_data["lt_sick_name"]:
            assert item.total_days_taken_or_requested == 1.0
            assert item.number_of_requests == 1

def test_get_leave_summary_with_status_filter_pending(db_session: Session, setup_leave_data):
    result = hr_reports_crud.get_leave_summary_by_type(db_session, status_filter=LeaveRequestStatusEnum.PENDING)
    # Vacation: 1 day, 1 request
    # Sick: 0 days, 0 requests
    assert len(result) == 1 # Only vacation has pending
    item = result[0]
    assert item.leave_type_name == setup_leave_data["lt_vac_name"]
    assert item.total_days_taken_or_requested == 1.0
    assert item.number_of_requests == 1

def test_get_leave_summary_type_with_no_requests_for_filter(db_session: Session, setup_leave_data):
    # Unpaid Time Off has no requests. It should not appear in the summary.
    result_approved = hr_reports_crud.get_leave_summary_by_type(db_session, status_filter=LeaveRequestStatusEnum.APPROVED)
    assert setup_leave_data["lt_unpaid_name"] not in [item.leave_type_name for item in result_approved]

    result_pending = hr_reports_crud.get_leave_summary_by_type(db_session, status_filter=LeaveRequestStatusEnum.PENDING)
    assert setup_leave_data["lt_unpaid_name"] not in [item.leave_type_name for item in result_pending]

    result_no_filter = hr_reports_crud.get_leave_summary_by_type(db_session)
    assert setup_leave_data["lt_unpaid_name"] not in [item.leave_type_name for item in result_no_filter]
