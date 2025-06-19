from typing import Optional, List
from sqlalchemy.orm import Session
from uuid import UUID

# Adjust the import path based on your project structure.
# This assumes 'api' is a sibling directory to 'db' or installed as a package.
# If 'api' is at the root, it might be 'from ..api.models import Employee, EmployeeCreate, EmployeeUpdate'
# or if your project root is directly in PYTHONPATH, 'from api.models import ...'
from api.models import Employee, EmployeeCreate, EmployeeUpdate # Assuming api.models is accessible

def create_employee(db: Session, employee: EmployeeCreate) -> Employee:
    """
    Creates a new employee in the database.
    """
    db_employee = Employee(**employee.model_dump())
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

def get_employee(db: Session, employee_id: str) -> Optional[Employee]:
    """
    Retrieves an employee by their ID.
    """
    # Assuming employee_id is a string representation of a UUID.
    # If your Employee model's ID column is directly UUID type, ensure conversion if needed.
    return db.query(Employee).filter(Employee.id == employee_id).first()

def get_employees(db: Session, skip: int = 0, limit: int = 100) -> List[Employee]:
    """
    Retrieves a list of employees with pagination.
    """
    return db.query(Employee).offset(skip).limit(limit).all()

def update_employee(db: Session, employee_id: str, employee_update: EmployeeUpdate) -> Optional[Employee]:
    """
    Updates an existing employee's information.
    """
    db_employee = get_employee(db, employee_id)
    if db_employee:
        update_data = employee_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_employee, key, value)
        db.commit()
        db.refresh(db_employee)
    return db_employee

def delete_employee(db: Session, employee_id: str) -> Optional[Employee]:
    """
    Deletes an employee from the database.
    """
    db_employee = get_employee(db, employee_id)
    if db_employee:
        db.delete(db_employee)
        db.commit()
    return db_employee
