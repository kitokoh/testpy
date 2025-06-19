import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# Adjust these imports based on your project structure
from api.models import Base, Employee, EmployeeCreate, EmployeeResponse, EmployeeUpdate # SQLAlchemy model for direct checks
from api.employees import router as employees_router
from api.dependencies import get_db # The actual dependency to be overridden

# Use an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Fixture for the database session, ensures tables are created and dropped.
@pytest.fixture(scope="function")
def test_db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)  # Create tables
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
        Base.metadata.drop_all(bind=engine)  # Drop tables after each test


# Fixture for the TestClient, with get_db dependency overridden
@pytest.fixture(scope="function")
def client(test_db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield test_db_session
        finally:
            pass # Session is managed by test_db_session fixture

    app = FastAPI()
    app.include_router(employees_router)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

# --- Test Cases ---

def test_create_employee_endpoint(client: TestClient, test_db_session: Session):
    # Valid creation
    employee_data = {
        "first_name": "Test", "last_name": "User", "email": "test.user@example.com",
        "start_date": "2023-01-01", "position": "Tester"
    }
    response = client.post("/employees/", json=employee_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == employee_data["email"]
    assert data["first_name"] == employee_data["first_name"]
    assert "id" in data

    # Verify in DB
    db_employee = test_db_session.query(Employee).filter(Employee.id == data["id"]).first()
    assert db_employee is not None
    assert db_employee.email == employee_data["email"]

    # Duplicate email
    response_dup = client.post("/employees/", json=employee_data)
    assert response_dup.status_code == status.HTTP_409_CONFLICT
    assert "email already exists" in response_dup.json()["detail"].lower()

    # Invalid data (missing required field: first_name)
    invalid_data = {
        "last_name": "User", "email": "test.user.invalid@example.com",
        "start_date": "2023-01-01"
    }
    response_invalid = client.post("/employees/", json=invalid_data)
    assert response_invalid.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_read_employees_endpoint(client: TestClient, test_db_session: Session):
    # Setup: Create a couple of employees directly or via CRUD for simplicity here
    emp1_data = {"first_name": "Alice", "last_name": "Smith", "email": "alice@example.com", "start_date": "2022-01-01"}
    emp2_data = {"first_name": "Bob", "last_name": "Johnson", "email": "bob@example.com", "start_date": "2022-02-01"}
    client.post("/employees/", json=emp1_data) # Use API to create to ensure full processing
    client.post("/employees/", json=emp2_data)

    # Get all
    response = client.get("/employees/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert data[0]["email"] == emp1_data["email"]
    assert data[1]["email"] == emp2_data["email"]

    # Test pagination: limit
    response_limit = client.get("/employees/?limit=1")
    assert response_limit.status_code == status.HTTP_200_OK
    data_limit = response_limit.json()
    assert len(data_limit) == 1
    assert data_limit[0]["email"] == emp1_data["email"]

    # Test pagination: skip and limit
    response_skip_limit = client.get("/employees/?skip=1&limit=1")
    assert response_skip_limit.status_code == status.HTTP_200_OK
    data_skip_limit = response_skip_limit.json()
    assert len(data_skip_limit) == 1
    assert data_skip_limit[0]["email"] == emp2_data["email"]


def test_read_employee_endpoint(client: TestClient):
    # Create an employee
    employee_data = {"first_name": "Carol", "last_name": "Davis", "email": "carol@example.com", "start_date": "2021-03-01"}
    create_response = client.post("/employees/", json=employee_data)
    employee_id = create_response.json()["id"]

    # Get existing
    response = client.get(f"/employees/{employee_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == employee_id
    assert data["email"] == employee_data["email"]

    # Get non-existent
    response_not_found = client.get("/employees/non_existent_uuid")
    assert response_not_found.status_code == status.HTTP_404_NOT_FOUND

def test_update_employee_endpoint(client: TestClient, test_db_session: Session):
    # Create an employee
    employee_data = {"first_name": "Dave", "last_name": "Wilson", "email": "dave@example.com", "start_date": "2020-04-01"}
    create_response = client.post("/employees/", json=employee_data)
    employee_id = create_response.json()["id"]

    # Valid update
    update_data = {"first_name": "David", "position": "Lead Tester"}
    response = client.put(f"/employees/{employee_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["first_name"] == "David"
    assert data["position"] == "Lead Tester"
    assert data["email"] == employee_data["email"] # Email should not change unless specified

    # Verify in DB
    db_employee = test_db_session.query(Employee).filter(Employee.id == employee_id).first()
    assert db_employee.first_name == "David"
    assert db_employee.position == "Lead Tester"

    # Update non-existent
    response_not_found = client.put("/employees/non_existent_uuid", json=update_data)
    assert response_not_found.status_code == status.HTTP_404_NOT_FOUND

    # Invalid update data (e.g. email to non-email string, if EmployeeUpdate has strict EmailStr)
    # Note: EmployeeUpdate allows partial updates, so only test for truly invalid types if applicable
    # For example, if start_date was updated with a non-date string:
    invalid_update_data = {"start_date": "not-a-date"}
    response_invalid = client.put(f"/employees/{employee_id}", json=invalid_update_data)
    assert response_invalid.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_delete_employee_endpoint(client: TestClient, test_db_session: Session):
    # Create an employee
    employee_data = {"first_name": "Eve", "last_name": "Brown", "email": "eve@example.com", "start_date": "2019-05-01"}
    create_response = client.post("/employees/", json=employee_data)
    employee_id = create_response.json()["id"]

    # Delete existing
    response = client.delete(f"/employees/{employee_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == employee_id # API returns deleted employee data

    # Verify deleted from DB
    db_employee = test_db_session.query(Employee).filter(Employee.id == employee_id).first()
    assert db_employee is None

    # Try to get deleted employee (should be 404)
    get_response = client.get(f"/employees/{employee_id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND

    # Delete non-existent
    response_not_found = client.delete("/employees/non_existent_uuid")
    assert response_not_found.status_code == status.HTTP_404_NOT_FOUND

# Placeholder for more detailed validation tests (e.g., specific field constraints)
# e.g. test_create_employee_invalid_email_format, test_update_employee_invalid_date_format etc.
# if Pydantic models have more specific validations than just type.
# For now, relying on Pydantic's default type validation for 422s.
# The test "test_create_employee_endpoint" covers one missing field 422.
# The test "test_update_employee_endpoint" covers one type error 422 for date.
