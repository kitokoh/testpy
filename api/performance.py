from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime

# Project-specific imports
from api.dependencies import get_db
from api.auth import get_current_active_user # Assuming UserInDB is returned with at least user_id and role
from api.models import (
    UserInDB, Employee, # Core models
    Goal, GoalCreate, GoalResponse, GoalUpdate, GoalStatusEnum,
    ReviewCycle, ReviewCycleCreate, ReviewCycleResponse, ReviewCycleUpdate,
    PerformanceReview, PerformanceReviewCreate, PerformanceReviewResponse, PerformanceReviewUpdate, PerformanceReviewStatusEnum,
    EmployeeResponse # For potential nested responses, though not explicitly used in all signatures here
)
from db.cruds import performance_crud, employees_crud


router = APIRouter(
    prefix="/performance",
    tags=["Performance Management"],
)

# --- Helper for Permissions (Adapt as per your actual User model and roles) ---
def check_permission(user: UserInDB, allowed_roles: List[str], employee_id_to_match: Optional[str] = None):
    """
    Basic permission check. User must have one of allowed_roles OR match employee_id_to_match.
    """
    if user.role in allowed_roles:
        return True
    if employee_id_to_match and user.user_id == employee_id_to_match:
        return True
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

def check_admin_hr_permission(user: UserInDB):
    if user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires Admin or HR Manager role.")

# --- API Endpoints for Goals (`/goals`) ---

@router.post("/goals/", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal_endpoint(
    goal_data: GoalCreate,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Verify employee_id exists
    if not employees_crud.get_employee(db, employee_id=goal_data.employee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee with ID {goal_data.employee_id} not found.")

    # Manager or user themselves can set goal for the user? Or Admin/HR?
    # For now, assume if set_by_id is not provided, it's current user.
    # Permission to set for OTHERS can be stricter.
    if goal_data.set_by_id and goal_data.set_by_id != current_user.user_id:
        check_admin_hr_permission(current_user) # Or specific manager role

    final_set_by_id = goal_data.set_by_id if goal_data.set_by_id else current_user.user_id

    # Convert status string to enum if necessary (Pydantic might handle it if GoalCreate.status is Enum type)
    # Assuming GoalCreate.status is string, matching GoalBase default.
    if goal_data.status:
        try:
            GoalStatusEnum(goal_data.status) # Validate
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid goal status: {goal_data.status}")

    return performance_crud.create_goal(db=db, goal_data=goal_data, current_user_id=final_set_by_id)


@router.get("/goals/employee/{employee_id}", response_model=List[GoalResponse])
def read_employee_goals_endpoint(
    employee_id: str,
    status_filter: Optional[GoalStatusEnum] = None, # FastAPI handles string-to-enum for query params
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    check_permission(current_user, allowed_roles=["admin", "hr_manager"], employee_id_to_match=employee_id)
    if not employees_crud.get_employee(db, employee_id=employee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee with ID {employee_id} not found.")
    return performance_crud.get_goals_for_employee(db=db, employee_id=employee_id, status=status_filter)


@router.get("/goals/{goal_id}", response_model=GoalResponse)
def read_goal_endpoint(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    db_goal = performance_crud.get_goal(db, goal_id=goal_id)
    if db_goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    check_permission(current_user, allowed_roles=["admin", "hr_manager"], employee_id_to_match=db_goal.employee_id)
    return db_goal


@router.put("/goals/{goal_id}", response_model=GoalResponse)
def update_goal_endpoint(
    goal_id: int,
    goal_data: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    db_goal = performance_crud.get_goal(db, goal_id=goal_id)
    if db_goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    # Permission: Owner, setter, or Admin/HR
    can_update = False
    if current_user.user_id == db_goal.employee_id or current_user.user_id == db_goal.set_by_id:
        can_update = True
    if not can_update: # If not owner or setter, then check admin/hr
        check_admin_hr_permission(current_user)

    if goal_data.status:
        try:
            GoalStatusEnum(goal_data.status) # Validate string against enum values
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid goal status: {goal_data.status}")

    updated_goal = performance_crud.update_goal(db=db, goal_id=goal_id, goal_update_data=goal_data)
    return updated_goal


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal_endpoint(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    db_goal = performance_crud.get_goal(db, goal_id=goal_id)
    if db_goal is None:
        # Return 204 even if not found to ensure idempotency of delete, common practice.
        # Or raise 404 as per prompt. For now, raising 404.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    # Permission: Owner, setter, or Admin/HR
    can_delete = False
    if current_user.user_id == db_goal.employee_id or current_user.user_id == db_goal.set_by_id:
        can_delete = True
    if not can_delete:
        check_admin_hr_permission(current_user)

    performance_crud.delete_goal(db=db, goal_id=goal_id)
    return None

# --- API Endpoints for Review Cycles (`/review-cycles`) --- (Typically Admin/HR)

@router.post("/review-cycles/", response_model=ReviewCycleResponse, status_code=status.HTTP_201_CREATED)
def create_review_cycle_endpoint(
    rc_data: ReviewCycleCreate,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    check_admin_hr_permission(current_user)
    try:
        return performance_crud.create_review_cycle(db=db, rc_data=rc_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review cycle with this name already exists.")


@router.get("/review-cycles/", response_model=List[ReviewCycleResponse])
def read_review_cycles_endpoint(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
    # No specific permission, could be public info or restricted if sensitive
):
    return performance_crud.get_review_cycles(db=db, is_active=is_active)


@router.get("/review-cycles/{rc_id}", response_model=ReviewCycleResponse)
def read_review_cycle_endpoint(rc_id: int, db: Session = Depends(get_db)):
    db_rc = performance_crud.get_review_cycle(db, rc_id=rc_id)
    if db_rc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review cycle not found")
    return db_rc


@router.put("/review-cycles/{rc_id}", response_model=ReviewCycleResponse)
def update_review_cycle_endpoint(
    rc_id: int,
    rc_data: ReviewCycleUpdate,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    check_admin_hr_permission(current_user)
    try:
        updated_rc = performance_crud.update_review_cycle(db=db, rc_id=rc_id, rc_update_data=rc_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Another review cycle with this name already exists.")

    if updated_rc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review cycle not found for update")
    return updated_rc


@router.delete("/review-cycles/{rc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review_cycle_endpoint(
    rc_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    check_admin_hr_permission(current_user)
    deleted_rc = performance_crud.delete_review_cycle(db=db, rc_id=rc_id)
    if deleted_rc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review cycle not found for deletion")
    return None

# --- API Endpoints for Performance Reviews (`/reviews`) ---

@router.post("/reviews/", response_model=PerformanceReviewResponse, status_code=status.HTTP_201_CREATED)
def create_performance_review_endpoint(
    pr_data: PerformanceReviewCreate,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Permission: Manager/HR. Reviewer_id can be current_user.user_id.
    # Employee must exist. Review cycle must exist if provided.
    check_admin_hr_permission(current_user) # Or a specific "manager" role

    if not employees_crud.get_employee(db, employee_id=pr_data.employee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee with ID {pr_data.employee_id} not found.")

    if pr_data.review_cycle_id and not performance_crud.get_review_cycle(db, pr_data.review_cycle_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Review Cycle with ID {pr_data.review_cycle_id} not found.")

    # If reviewer_id is not set in pr_data, it might be set to current_user.id
    # This depends on business logic (e.g. can a manager create a review and assign another manager?)
    # For now, assume pr_data.reviewer_id is either provided or can be current_user.user_id
    final_pr_data = pr_data.model_copy(deep=True)
    if final_pr_data.reviewer_id is None:
        final_pr_data.reviewer_id = current_user.user_id

    # Validate status string if provided in pr_data (Pydantic model has default)
    if final_pr_data.status:
        try:
            PerformanceReviewStatusEnum(final_pr_data.status)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid review status: {final_pr_data.status}")

    return performance_crud.create_performance_review(db=db, pr_data=final_pr_data, current_user_id=current_user.user_id)


@router.get("/reviews/employee/{employee_id}", response_model=List[PerformanceReviewResponse])
def read_employee_reviews_endpoint(
    employee_id: str,
    cycle_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    check_permission(current_user, allowed_roles=["admin", "hr_manager"], employee_id_to_match=employee_id)
    if not employees_crud.get_employee(db, employee_id=employee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee with ID {employee_id} not found.")
    return performance_crud.get_performance_reviews_for_employee(db=db, employee_id=employee_id, cycle_id=cycle_id)


@router.get("/reviews/reviewer/me", response_model=List[PerformanceReviewResponse])
def read_my_managed_reviews_endpoint(
    cycle_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Any user can call this, will return reviews where they are the reviewer_id
    return performance_crud.get_performance_reviews_by_reviewer(db=db, reviewer_id=current_user.user_id, cycle_id=cycle_id)


@router.get("/reviews/{pr_id}", response_model=PerformanceReviewResponse)
def read_performance_review_endpoint(
    pr_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    db_pr = performance_crud.get_performance_review(db, pr_id=pr_id)
    if db_pr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Performance review not found")

    # Permission: Involved user (employee/reviewer) or HR/Admin
    can_view = False
    if current_user.user_id == db_pr.employee_id or current_user.user_id == db_pr.reviewer_id:
        can_view = True
    if not can_view:
        check_admin_hr_permission(current_user)

    return db_pr


@router.put("/reviews/{pr_id}", response_model=PerformanceReviewResponse)
def update_performance_review_endpoint(
    pr_id: int,
    pr_data: PerformanceReviewUpdate,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    db_pr = performance_crud.get_performance_review(db, pr_id=pr_id)
    if db_pr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Performance review not found")

    # Permissions: Reviewer, specific roles (HR), or employee for their comments
    # Complex logic: Employee can only update employee_comments and only if status allows.
    # Manager (reviewer) can update manager_comments, ratings, status (some transitions).
    # HR/Admin can do more.
    # Simplified: if user is reviewer or admin/hr, allow most updates.
    # If user is employee, only allow employee_comments if status is appropriate.
    is_reviewer = current_user.user_id == db_pr.reviewer_id
    is_employee = current_user.user_id == db_pr.employee_id
    is_admin_hr = current_user.role in ["admin", "hr_manager"]

    if not (is_reviewer or is_admin_hr):
        if is_employee and pr_data.employee_comments is not None and len(pr_data.model_fields_set) == 1:
            # Allow employee to only update their comments if status is PENDING_EMPLOYEE_INPUT
            if db_pr.status != PerformanceReviewStatusEnum.PENDING_EMPLOYEE_INPUT:
                 raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update comments at this review stage.")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to update this review.")

    # Validate status string if provided
    if pr_data.status:
        try:
            PerformanceReviewStatusEnum(pr_data.status)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid review status: {pr_data.status}")

    # Validate linked goals
    if pr_data.goal_ids_to_link:
        for goal_id in pr_data.goal_ids_to_link:
            goal = performance_crud.get_goal(db, goal_id)
            if not goal:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal with ID {goal_id} to link not found.")
            if goal.employee_id != db_pr.employee_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Goal ID {goal_id} does not belong to the reviewed employee.")
    if pr_data.goal_ids_to_unlink: # No need to check employee_id for unlinking, just existence
        for goal_id in pr_data.goal_ids_to_unlink:
            if not performance_crud.get_goal(db, goal_id):
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal with ID {goal_id} to unlink not found.")


    updated_pr = performance_crud.update_performance_review(db=db, pr_id=pr_id, pr_update_data=pr_data)
    return updated_pr


@router.delete("/reviews/{pr_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_performance_review_endpoint(
    pr_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    check_admin_hr_permission(current_user) # Typically only Admin/HR can delete reviews

    db_pr = performance_crud.get_performance_review(db, pr_id=pr_id)
    if db_pr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Performance review not found")

    performance_crud.delete_performance_review(db=db, pr_id=pr_id)
    return None
