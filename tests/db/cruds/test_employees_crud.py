import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from typing import Generator

# Assuming your project structure allows these imports
# Adjust if your Base and models are located elsewhere
from api.models import Base, Employee, EmployeeCreate, EmployeeUpdate
from db.cruds import employees_crud

# Use an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Pytest fixture to set up an in-memory SQLite database session with the
    Employee table for each test function.
    Creates tables, yields a session, and rolls back transactions after each test.
    """
    Base.metadata.create_all(bind=engine) # Create all tables defined in Base
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback() # Ensure test isolation
        db.close()
        Base.metadata.drop_all(bind=engine) # Drop tables after tests


# --- Test Cases ---

def test_create_employee(db_session: Session):
    """Test creating an employee."""
    employee_data = EmployeeCreate(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        start_date="2023-01-15" # Pydantic will convert to date object
    )
    created_employee = employees_crud.create_employee(db=db_session, employee=employee_data)

    assert created_employee is not None
    assert created_employee.id is not None
    assert created_employee.email == employee_data.email
    assert created_employee.first_name == employee_data.first_name
    assert created_employee.last_name == employee_data.last_name
    assert created_employee.is_active is True # Default value

    db_employee = db_session.query(Employee).filter(Employee.id == created_employee.id).first()
    assert db_employee is not None
    assert db_employee.email == employee_data.email

def test_get_employee(db_session: Session):
    """Test retrieving an employee by ID."""
    employee_data = EmployeeCreate(
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        start_date="2023-02-01"
    )
    created_employee = employees_crud.create_employee(db=db_session, employee=employee_data)

    # Test retrieving existing employee
    retrieved_employee = employees_crud.get_employee(db=db_session, employee_id=created_employee.id)
    assert retrieved_employee is not None
    assert retrieved_employee.id == created_employee.id
    assert retrieved_employee.email == employee_data.email

    # Test retrieving non-existent employee
    non_existent_employee = employees_crud.get_employee(db=db_session, employee_id="non_existent_id")
    assert non_existent_employee is None

def test_get_employees(db_session: Session):
    """Test retrieving multiple employees with pagination."""
    employee1_data = EmployeeCreate(first_name="Alice", last_name="Smith", email="alice.smith@example.com", start_date="2023-03-01")
    employee2_data = EmployeeCreate(first_name="Bob", last_name="Johnson", email="bob.johnson@example.com", start_date="2023-03-15")
    employee3_data = EmployeeCreate(first_name="Charlie", last_name="Brown", email="charlie.brown@example.com", start_date="2023-04-01")

    employees_crud.create_employee(db=db_session, employee=employee1_data)
    employees_crud.create_employee(db=db_session, employee=employee2_data)
    employees_crud.create_employee(db=db_session, employee=employee3_data)

    # Test get all
    all_employees = employees_crud.get_employees(db=db_session)
    assert len(all_employees) == 3

    # Test with limit
    limited_employees = employees_crud.get_employees(db=db_session, limit=2)
    assert len(limited_employees) == 2

    # Test with skip and limit
    paginated_employees = employees_crud.get_employees(db=db_session, skip=1, limit=1)
    assert len(paginated_employees) == 1
    assert paginated_employees[0].email == employee2_data.email # Should be Bob

    # Test skip beyond total
    skipped_employees = employees_crud.get_employees(db=db_session, skip=5, limit=5)
    assert len(skipped_employees) == 0

def test_update_employee(db_session: Session):
    """Test updating an employee's information."""
    employee_data = EmployeeCreate(
        first_name="Eva",
        last_name="Core",
        email="eva.core@example.com",
        position="Developer",
        start_date="2022-01-01"
    )
    created_employee = employees_crud.create_employee(db=db_session, employee=employee_data)

    update_data = EmployeeUpdate(
        first_name="Eva Maria",
        position="Senior Developer",
        salary=75000.00
    )
    updated_employee = employees_crud.update_employee(db=db_session, employee_id=created_employee.id, employee_update=update_data)

    assert updated_employee is not None
    assert updated_employee.id == created_employee.id
    assert updated_employee.first_name == "Eva Maria"
    assert updated_employee.position == "Senior Developer"
    assert updated_employee.salary == 75000.00
    assert updated_employee.email == "eva.core@example.com" # Not updated

    db_employee = db_session.query(Employee).filter(Employee.id == created_employee.id).first()
    assert db_employee.first_name == "Eva Maria"
    assert db_employee.position == "Senior Developer"

    # Test updating non-existent employee
    non_existent_update = employees_crud.update_employee(db=db_session, employee_id="non_existent_id", employee_update=update_data)
    assert non_existent_update is None

def test_delete_employee(db_session: Session):
    """Test deleting an employee."""
    employee_data = EmployeeCreate(
        first_name="Mark",
        last_name="Spencer",
        email="mark.spencer@example.com",
        start_date="2023-05-01"
    )
    created_employee = employees_crud.create_employee(db=db_session, employee=employee_data)

    # Delete the employee
    deleted_employee_obj = employees_crud.delete_employee(db=db_session, employee_id=created_employee.id)
    assert deleted_employee_obj is not None
    assert deleted_employee_obj.id == created_employee.id
    assert deleted_employee_obj.email == employee_data.email

    # Verify it's deleted from DB
    db_employee = db_session.query(Employee).filter(Employee.id == created_employee.id).first()
    assert db_employee is None

    # Test deleting non-existent employee
    non_existent_delete = employees_crud.delete_employee(db=db_session, employee_id="non_existent_id")
    assert non_existent_delete is None

def test_create_employee_duplicate_email(db_session: Session):
    """Test creating an employee with a duplicate email raises IntegrityError."""
    employee1_data = EmployeeCreate(
        first_name="Sam",
        last_name="Blue",
        email="sam.blue@example.com",
        start_date="2023-06-01"
    )
    employees_crud.create_employee(db=db_session, employee=employee1_data)

    employee2_data = EmployeeCreate(
        first_name="Samuel",
        last_name="Red",
        email="sam.blue@example.com", # Same email
        start_date="2023-06-02"
    )
    with pytest.raises(IntegrityError):
        employees_crud.create_employee(db=db_session, employee=employee2_data)
    db_session.rollback() # Important after an integrity error to allow further session use

    # Ensure only one employee with this email exists
    count = db_session.query(Employee).filter(Employee.email == "sam.blue@example.com").count()
    assert count == 1
