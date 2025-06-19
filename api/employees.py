from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Assuming 'api.dependencies' provides 'get_db'
# Adjust the import path if your project structure is different.
from api.dependencies import get_db
from api.models import Employee, EmployeeCreate, EmployeeResponse, EmployeeUpdate
from db.cruds import employees_crud

router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
)

@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee_endpoint(employee: EmployeeCreate, db: Session = Depends(get_db)):
    """
    Create a new employee.
    Handles potential IntegrityError if email already exists.
    """
    try:
        created_employee = employees_crud.create_employee(db=db, employee=employee)
        return created_employee
    except IntegrityError: # Specific to SQLAlchemy, usually for unique constraints
        db.rollback() # Rollback the session in case of error
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee with this email already exists.",
        )
    except Exception as e: # Catch other potential errors
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )

@router.get("/", response_model=List[EmployeeResponse])
def read_employees_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve a list of employees with pagination.
    """
    employees = employees_crud.get_employees(db=db, skip=skip, limit=limit)
    return employees

@router.get("/{employee_id}", response_model=EmployeeResponse)
def read_employee_endpoint(employee_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a specific employee by their ID.
    Raises 404 if not found.
    """
    db_employee = employees_crud.get_employee(db=db, employee_id=employee_id)
    if db_employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return db_employee

@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee_endpoint(employee_id: str, employee_update: EmployeeUpdate, db: Session = Depends(get_db)):
    """
    Update an existing employee's information.
    Raises 404 if not found.
    """
    db_employee = employees_crud.update_employee(db=db, employee_id=employee_id, employee_update=employee_update)
    if db_employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return db_employee

@router.delete("/{employee_id}", response_model=EmployeeResponse)
def delete_employee_endpoint(employee_id: str, db: Session = Depends(get_db)):
    """
    Delete an employee by their ID.
    Raises 404 if not found. Returns the deleted employee data.
    """
    db_employee = employees_crud.delete_employee(db=db, employee_id=employee_id)
    if db_employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return db_employee
