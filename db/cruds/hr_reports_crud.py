from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.sql import func, extract, case
from datetime import date, datetime, timedelta

# Assuming models are directly under api.models as per prompt
from api.models import (
    Employee,
    LeaveRequest,
    LeaveType,
    LeaveRequestStatusEnum,
    HeadcountReportItem, # For type hinting return structure, not direct instantiation here
    AnniversaryReportItem,
    LeaveSummaryReportItem
)

def get_department_headcounts(db: Session) -> List[Dict[str, Any]]:
    """
    Generates a headcount report grouped by department.
    Returns a list of dictionaries suitable for HeadcountReportItem.
    """
    # Use coalesce to group NULL or empty departments as "N/A"
    # If empty strings are possible and also mean "N/A", a case statement might be more robust
    # For simplicity, coalesce handles NULL. Empty strings will be grouped as themselves unless handled.
    # To handle both NULL and empty string as "N/A":
    # department_label = case([(Employee.department == None, "N/A"), (Employee.department == "", "N/A")], else_=Employee.department)
    department_label = func.coalesce(Employee.department, "N/A")

    query_result = (
        db.query(
            department_label.label("department"),
            func.count(Employee.id).label("count")
        )
        .group_by("department")
        .order_by("department")
        .all()
    )

    # Convert query result (list of Row objects) to list of dicts
    report_data: List[Dict[str, Any]] = []
    for row in query_result:
        report_data.append({"department": row.department, "count": row.count})
    return report_data


def get_upcoming_anniversaries(db: Session, days_ahead: int) -> List[Dict[str, Any]]:
    """
    Generates a list of employees whose work anniversary is upcoming.
    Returns a list of dictionaries suitable for AnniversaryReportItem.
    """
    today = date.today()
    target_end_date = today + timedelta(days=days_ahead)

    employees = db.query(Employee.id, Employee.first_name, Employee.last_name, Employee.start_date).filter(
        Employee.is_active == True, # Consider only active employees
        Employee.start_date != None # Ensure start_date is available
    ).all()

    anniversary_list: List[Dict[str, Any]] = []

    for emp in employees:
        if not emp.start_date:
            continue

        # Calculate anniversary for the current year
        try:
            anniversary_this_year = date(today.year, emp.start_date.month, emp.start_date.day)
        except ValueError: # Handles cases like Feb 29 on a non-leap year for start_date
            # Approximate to Feb 28 or Mar 1, or skip. Skipping for simplicity.
            # Or, more accurately, if start_date is Feb 29, anniversary is Feb 28 in non-leap years.
            if emp.start_date.month == 2 and emp.start_date.day == 29:
                anniversary_this_year = date(today.year, 2, 28)
            else:
                continue # Skip if date is invalid for other reasons (should not happen with valid start_date)

        upcoming_anniversary_date = None

        if anniversary_this_year >= today:
            upcoming_anniversary_date = anniversary_this_year
        else:
            # Anniversary this year has passed, check next year
            try:
                anniversary_next_year = date(today.year + 1, emp.start_date.month, emp.start_date.day)
            except ValueError: # Handles Feb 29 for next year if it's non-leap
                if emp.start_date.month == 2 and emp.start_date.day == 29:
                    anniversary_next_year = date(today.year + 1, 2, 28)
                else:
                    continue
            upcoming_anniversary_date = anniversary_next_year

        if upcoming_anniversary_date and (today <= upcoming_anniversary_date <= target_end_date):
            years_of_service = upcoming_anniversary_date.year - emp.start_date.year

            # Ensure that if anniversary_this_year was used, and it's today, years of service are not overstated
            # if it's their very first year and anniversary is today.
            # Example: Hired 2023-01-01. Today is 2024-01-01. Anniversary is 2024-01-01. Years = 1. Correct.
            # Example: Hired 2023-01-01. Today is 2023-05-01. Anniversary is 2024-01-01. Years = 1. Correct.

            anniversary_list.append({
                "employee_id": emp.id,
                "full_name": f"{emp.first_name} {emp.last_name}",
                "anniversary_date": upcoming_anniversary_date,
                "years_of_service": years_of_service
            })

    # Sort by upcoming_anniversary_date
    anniversary_list.sort(key=lambda x: x["anniversary_date"])
    return anniversary_list


def get_leave_summary_by_type(db: Session, status_filter: Optional[LeaveRequestStatusEnum] = None) -> List[Dict[str, Any]]:
    """
    Generates a summary of leave requests by leave type.
    Returns a list of dictionaries suitable for LeaveSummaryReportItem.
    """
    query = (
        db.query(
            LeaveType.name.label("leave_type_name"),
            func.sum(LeaveRequest.num_days).label("total_days_taken_or_requested"),
            func.count(LeaveRequest.id).label("number_of_requests")
        )
        .join(LeaveType, LeaveRequest.leave_type_id == LeaveType.id)
    )

    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter)

    query_result = query.group_by(LeaveType.name).order_by(LeaveType.name).all()

    report_data: List[Dict[str, Any]] = []
    for row in query_result:
        report_data.append({
            "leave_type_name": row.leave_type_name,
            "total_days_taken_or_requested": row.total_days_taken_or_requested or 0.0, # Coalesce NULL sum to 0
            "number_of_requests": row.number_of_requests
        })
    return report_data

# Note: The Pydantic models (HeadcountReportItem etc.) are defined for the API response structure.
# These CRUD functions return lists of dictionaries that CONFORM to those Pydantic models,
# allowing the API layer to easily parse and validate them into the final response objects.
# Direct instantiation of Pydantic models in CRUD is possible but often avoided to keep CRUDs focused on DB interaction
# and data shaping, leaving Pydantic validation to the API layer.
# The type hints for return values (e.g. -> List[HeadcountReportItem]) are for clarity of intent of the structure.
# The actual return is List[Dict[str, Any]].
# This is a common pattern. If direct Pydantic model instantiation is preferred here, the code would change slightly.
# For now, returning dicts.
# Re-checking prompt: "Returns a list of HeadcountReportItem objects." - this implies direct Pydantic instantiation.
# I will adjust to return Pydantic model instances directly.

# Adjusting functions to return Pydantic model instances directly.

def get_department_headcounts_pydantic(db: Session) -> List[HeadcountReportItem]:
    department_label = func.coalesce(Employee.department, "N/A")
    query_result = (
        db.query(
            department_label.label("department"),
            func.count(Employee.id).label("count")
        )
        .group_by(department_label) # Group by the coalesced label
        .order_by(department_label)
        .all()
    )
    return [HeadcountReportItem(department=row.department, count=row.count) for row in query_result]

def get_upcoming_anniversaries_pydantic(db: Session, days_ahead: int) -> List[AnniversaryReportItem]:
    today = date.today()
    target_end_date = today + timedelta(days=days_ahead)

    employees = db.query(Employee.id, Employee.first_name, Employee.last_name, Employee.start_date).filter(
        Employee.is_active == True, Employee.start_date != None
    ).all()

    anniversary_list: List[AnniversaryReportItem] = []

    for emp in employees:
        if not emp.start_date: continue
        try:
            anniversary_this_year = date(today.year, emp.start_date.month, emp.start_date.day)
        except ValueError:
            if emp.start_date.month == 2 and emp.start_date.day == 29:
                anniversary_this_year = date(today.year, 2, 28)
            else: continue

        upcoming_anniversary_date = None
        if anniversary_this_year >= today:
            upcoming_anniversary_date = anniversary_this_year
        else:
            try:
                anniversary_next_year = date(today.year + 1, emp.start_date.month, emp.start_date.day)
            except ValueError:
                if emp.start_date.month == 2 and emp.start_date.day == 29:
                    anniversary_next_year = date(today.year + 1, 2, 28)
                else: continue
            upcoming_anniversary_date = anniversary_next_year

        if upcoming_anniversary_date and (today <= upcoming_anniversary_date <= target_end_date):
            years_of_service = upcoming_anniversary_date.year - emp.start_date.year
            anniversary_list.append(AnniversaryReportItem(
                employee_id=str(emp.id), # Ensure ID is string if model expects it
                full_name=f"{emp.first_name} {emp.last_name}",
                anniversary_date=upcoming_anniversary_date,
                years_of_service=years_of_service
            ))

    anniversary_list.sort(key=lambda x: x.anniversary_date)
    return anniversary_list

def get_leave_summary_by_type_pydantic(db: Session, status_filter: Optional[LeaveRequestStatusEnum] = None) -> List[LeaveSummaryReportItem]:
    query = (
        db.query(
            LeaveType.name.label("leave_type_name"),
            func.sum(LeaveRequest.num_days).label("total_days"),
            func.count(LeaveRequest.id).label("num_requests")
        )
        .join(LeaveType, LeaveRequest.leave_type_id == LeaveType.id)
    )

    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter)

    query_result = query.group_by(LeaveType.name).order_by(LeaveType.name).all()

    return [
        LeaveSummaryReportItem(
            leave_type_name=row.leave_type_name,
            total_days_taken_or_requested=float(row.total_days or 0.0),
            number_of_requests=row.num_requests
        ) for row in query_result
    ]

# Renaming functions to original names, now returning Pydantic models.
get_department_headcounts = get_department_headcounts_pydantic
get_upcoming_anniversaries = get_upcoming_anniversaries_pydantic
get_leave_summary_by_type = get_leave_summary_by_type_pydantic
