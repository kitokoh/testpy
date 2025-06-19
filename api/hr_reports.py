from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, date # Ensure both are imported

# Project-specific imports
from api.dependencies import get_db
from api.auth import get_current_active_user # Assuming UserInDB is returned
from api.models import (
    UserInDB, # User model for dependency injection
    HeadcountReportResponse,
    AnniversaryReportResponse,
    LeaveSummaryReportResponse,
    LeaveRequestStatusEnum # The Enum itself for query param
)
from db.cruds import hr_reports_crud # The new CRUD module

router = APIRouter(
    prefix="/hr-reports",
    tags=["HR Reports"],
)

# --- Helper for Permissions (Basic Example) ---
def check_hr_reports_permission(user: UserInDB):
    """
    Checks if the user has permission to access HR reports.
    Typically restricted to HR/Admin roles.
    """
    # Adapt to your actual User model and role names/system
    if not user or user.role not in ["admin", "hr_manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access HR reports."
        )

# --- API Endpoints ---

@router.get("/headcount-by-department", response_model=HeadcountReportResponse)
def get_headcount_report_endpoint(
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Provides a headcount report grouped by department.
    """
    check_hr_reports_permission(current_user)

    headcount_data = hr_reports_crud.get_department_headcounts(db)

    return HeadcountReportResponse(
        generated_at=datetime.now(),
        data=headcount_data
    )

@router.get("/upcoming-anniversaries", response_model=AnniversaryReportResponse)
def get_upcoming_anniversaries_report_endpoint(
    days_ahead: int = Query(30, ge=7, le=365, description="Number of upcoming days to report on (min 7, max 365)."),
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Provides a report of employees with upcoming work anniversaries.
    """
    check_hr_reports_permission(current_user)

    anniversary_data = hr_reports_crud.get_upcoming_anniversaries(db, days_ahead=days_ahead)

    return AnniversaryReportResponse(
        generated_at=datetime.now(),
        time_window_days=days_ahead,
        data=anniversary_data
    )

@router.get("/leave-summary", response_model=LeaveSummaryReportResponse)
def get_leave_summary_report_endpoint(
    status_filter: Optional[LeaveRequestStatusEnum] = Query(None, description="Filter by leave request status (e.g., pending, approved)."),
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Provides a summary of leave requests, grouped by leave type.
    Can be filtered by leave request status.
    """
    check_hr_reports_permission(current_user)

    leave_summary_data = hr_reports_crud.get_leave_summary_by_type(db, status_filter=status_filter)

    return LeaveSummaryReportResponse(
        generated_at=datetime.now(),
        filter_status=status_filter.value if status_filter else None, # Store the string value of enum
        data=leave_summary_data
    )

# Note on LeaveRequestStatusEnum:
# FastAPI automatically converts query parameters to the specified enum type.
# So, a request like GET /leave-summary?status_filter=approved will correctly pass
# LeaveRequestStatusEnum.APPROVED to the CRUD function if the enum is defined with string values.
# The Pydantic response model `LeaveSummaryReportResponse` has `filter_status: Optional[str]`,
# so we store the .value of the enum if it was provided. This is consistent.
# The CRUD function `get_leave_summary_by_type` expects `Optional[LeaveRequestStatusEnum]`.
# All looks correct.
