from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func # For server_default, though not directly used in CRUD logic much
from datetime import date, datetime

# Assuming your project structure allows these imports
# Adjust if your models are located elsewhere
from api.models import (
    Goal, GoalCreate, GoalUpdate, GoalStatusEnum,
    ReviewCycle, ReviewCycleCreate, ReviewCycleUpdate,
    PerformanceReview, PerformanceReviewCreate, PerformanceReviewUpdate, PerformanceReviewStatusEnum,
    Employee, User # Needed for relationships and context
)

# --- Goal CRUD ---

def create_goal(db: Session, goal_data: GoalCreate, current_user_id: Optional[str] = None) -> Goal:
    db_goal_data = goal_data.model_dump()
    if 'set_by_id' not in db_goal_data or db_goal_data['set_by_id'] is None:
        db_goal_data['set_by_id'] = current_user_id

    db_goal = Goal(**db_goal_data)
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal

def get_goal(db: Session, goal_id: int) -> Optional[Goal]:
    return db.query(Goal).filter(Goal.id == goal_id).first()

def get_goals_for_employee(
    db: Session, employee_id: str, status: Optional[GoalStatusEnum] = None, skip: int = 0, limit: int = 100
) -> List[Goal]:
    query = db.query(Goal).filter(Goal.employee_id == employee_id)
    if status:
        query = query.filter(Goal.status == status)
    return query.order_by(Goal.due_date.asc().nulls_last(), Goal.created_at.desc()).offset(skip).limit(limit).all()

def update_goal(db: Session, goal_id: int, goal_update_data: GoalUpdate) -> Optional[Goal]:
    db_goal = get_goal(db, goal_id)
    if db_goal:
        update_data = goal_update_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_goal, key, value)
        db_goal.updated_at = datetime.utcnow() # Manually update timestamp if not using server_onupdate
        db.commit()
        db.refresh(db_goal)
    return db_goal

def delete_goal(db: Session, goal_id: int) -> Optional[Goal]:
    db_goal = get_goal(db, goal_id)
    if db_goal:
        db.delete(db_goal)
        db.commit()
    return db_goal

# --- ReviewCycle CRUD ---

def create_review_cycle(db: Session, rc_data: ReviewCycleCreate) -> ReviewCycle:
    db_rc = ReviewCycle(**rc_data.model_dump())
    try:
        db.add(db_rc)
        db.commit()
        db.refresh(db_rc)
    except IntegrityError: # Handles unique name
        db.rollback()
        raise
    return db_rc

def get_review_cycle(db: Session, rc_id: int) -> Optional[ReviewCycle]:
    return db.query(ReviewCycle).filter(ReviewCycle.id == rc_id).first()

def get_review_cycles(
    db: Session, is_active: Optional[bool] = None, skip: int = 0, limit: int = 100
) -> List[ReviewCycle]:
    query = db.query(ReviewCycle)
    if is_active is not None:
        query = query.filter(ReviewCycle.is_active == is_active)
    return query.order_by(ReviewCycle.start_date.desc()).offset(skip).limit(limit).all()

def update_review_cycle(db: Session, rc_id: int, rc_update_data: ReviewCycleUpdate) -> Optional[ReviewCycle]:
    db_rc = get_review_cycle(db, rc_id)
    if db_rc:
        update_data = rc_update_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_rc, key, value)
        try:
            db.commit()
            db.refresh(db_rc)
        except IntegrityError: # Handles unique name
            db.rollback()
            raise
    return db_rc

def delete_review_cycle(db: Session, rc_id: int) -> Optional[ReviewCycle]:
    db_rc = get_review_cycle(db, rc_id)
    if db_rc:
        # Consider implications: what happens to reviews linked to this cycle?
        # Might need a soft delete or check for linked reviews.
        # For now, direct delete.
        db.delete(db_rc)
        db.commit()
    return db_rc

# --- PerformanceReview CRUD & Logic ---

def create_performance_review(
    db: Session, pr_data: PerformanceReviewCreate, current_user_id: Optional[str] = None
) -> PerformanceReview:
    db_pr_data = pr_data.model_dump()
    # If reviewer_id is not provided, it could default to current_user or be explicitly required.
    # For now, assume Pydantic model handles its optionality.
    # If pr_data.reviewer_id is None and current_user_id is manager of employee_id, set it.
    # This logic can be more complex and might belong in an API layer or service layer.
    # Here, we'll just use what's provided or leave it if None.

    db_pr = PerformanceReview(**db_pr_data)
    db.add(db_pr)
    db.commit()
    db.refresh(db_pr)
    return db_pr

def get_performance_review(db: Session, pr_id: int) -> Optional[PerformanceReview]:
    return db.query(PerformanceReview).options(
        # Eager load goals_reviewed to have them available immediately
        # from sqlalchemy.orm import joinedload
        # joinedload(PerformanceReview.goals_reviewed)
        # This is optional, depends on access pattern. Standard lazy loading works too.
    ).filter(PerformanceReview.id == pr_id).first()

def get_performance_reviews_for_employee(
    db: Session, employee_id: str, cycle_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[PerformanceReview]:
    query = db.query(PerformanceReview).filter(PerformanceReview.employee_id == employee_id)
    if cycle_id:
        query = query.filter(PerformanceReview.review_cycle_id == cycle_id)
    return query.order_by(PerformanceReview.created_at.desc()).offset(skip).limit(limit).all()

def get_performance_reviews_by_reviewer(
    db: Session, reviewer_id: str, cycle_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[PerformanceReview]:
    query = db.query(PerformanceReview).filter(PerformanceReview.reviewer_id == reviewer_id)
    if cycle_id:
        query = query.filter(PerformanceReview.review_cycle_id == cycle_id)
    return query.order_by(PerformanceReview.created_at.desc()).offset(skip).limit(limit).all()

def update_performance_review(
    db: Session, pr_id: int, pr_update_data: PerformanceReviewUpdate
) -> Optional[PerformanceReview]:
    db_pr = get_performance_review(db, pr_id)
    if not db_pr:
        return None

    update_data = pr_update_data.model_dump(exclude_unset=True)

    # Handle goal linking/unlinking
    if 'goal_ids_to_link' in update_data:
        goal_ids = update_data.pop('goal_ids_to_link', [])
        if goal_ids:
            goals_to_link = db.query(Goal).filter(Goal.id.in_(goal_ids)).all()
            for goal in goals_to_link:
                # Ensure goal belongs to the same employee and is not already linked
                if goal.employee_id == db_pr.employee_id and goal not in db_pr.goals_reviewed:
                    db_pr.goals_reviewed.append(goal)
                # Else: log warning or raise error? For now, silently ignore if mismatched.

    if 'goal_ids_to_unlink' in update_data:
        goal_ids = update_data.pop('goal_ids_to_unlink', [])
        if goal_ids:
            goals_to_unlink = db.query(Goal).filter(Goal.id.in_(goal_ids)).all()
            for goal in goals_to_unlink:
                if goal in db_pr.goals_reviewed:
                    db_pr.goals_reviewed.remove(goal)

    for key, value in update_data.items():
        setattr(db_pr, key, value)

    db_pr.updated_at = datetime.utcnow() # Manually update timestamp
    db.commit()
    db.refresh(db_pr)
    return db_pr

def delete_performance_review(db: Session, pr_id: int) -> Optional[PerformanceReview]:
    db_pr = get_performance_review(db, pr_id)
    if db_pr:
        # M2M links in performance_review_goals_link should be deleted automatically by SQLAlchemy
        # if the relationship is configured correctly (which it is by default with `secondary`).
        db.delete(db_pr)
        db.commit()
    return db_pr

# Note on `updated_at`: SQLAlchemy's `onupdate=func.now()` in the model definition
# usually handles this automatically at the DB level if the DB supports it well (e.g., PostgreSQL).
# For SQLite, `server_onupdate` is not directly supported for `func.now()`.
# Explicitly setting `updated_at = datetime.utcnow()` in update methods is a reliable cross-DB way
# if `onupdate` in the model doesn't cover all cases or if not using server-side defaults.
# The models have `onupdate=func.now()`, so explicit setting might be redundant for some DBs
# but ensures it for others or if ORM events aren't firing as expected.
# For this exercise, I've added manual `updated_at` for clarity in `update_goal` and `update_performance_review`.
# `create_goal` and `create_performance_review` rely on `server_default=func.now()` for `created_at` and `updated_at`.
# `create_review_cycle` does not have `created_at`/`updated_at` in its model.
# `update_review_cycle` also does not update such fields as they are not in its model.
# This is consistent with the provided models.
# `Goal` and `PerformanceReview` models have `updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)`
# This `onupdate=func.now()` should handle updates automatically. So manual setting of `updated_at` might be removed.
# I'll keep it for now as it doesn't harm and makes the intent explicit.
# If the DB and SQLAlchemy driver correctly handle `onupdate=func.now()`, the manual lines are not strictly needed.
# Removing manual `updated_at = datetime.utcnow()` as model's `onupdate` should handle it.

# Re-evaluating manual updated_at:
# The models `Goal` and `PerformanceReview` have `onupdate=func.now()`. This works well with databases that support
# `ON UPDATE` clauses triggered by the database server itself (like PostgreSQL, MySQL).
# For SQLite, this clause isn't directly translated into a DB-level trigger by SQLAlchemy by default.
# SQLAlchemy's `onupdate` for client-invoked Python functions (e.g., `onupdate=datetime.utcnow`) works during ORM operations.
# `func.now()` in `onupdate` is meant for the DB server.
# To be safe and ensure `updated_at` is modified during updates via ORM, it's better to explicitly set it if there's any doubt.
# However, if we rely on `onupdate=func.now()` being translated to a server-side mechanism, explicit setting is redundant.
# Given the prompt is about CRUD, relying on model definition is cleaner.
# I will remove the explicit `db_goal.updated_at = datetime.utcnow()` and `db_pr.updated_at = datetime.utcnow()`
# and trust the `onupdate=func.now()` in the SQLAlchemy models.
# This means the file generation should reflect this removal.
# The file has been generated with explicit `updated_at`. I will proceed and this can be a refinement.
# For now, the generated code includes the explicit `updated_at`. This is safer for SQLite compatibility if `onupdate` is not server-side.
# The current code is fine.The file `db/cruds/performance_crud.py` has been created with the specified CRUD functions.

**Summary of Implementation:**

*   **Goal CRUD**:
    *   `create_goal`: Sets `set_by_id` from `current_user_id` if not provided.
    *   `get_goal`, `get_goals_for_employee` (with status filter and sorting), `update_goal`, `delete_goal` are implemented.
    *   Explicit `updated_at` setting is included in `update_goal` for robustness, though model's `onupdate=func.now()` might handle it on some DBs.
*   **ReviewCycle CRUD**:
    *   `create_review_cycle`, `get_review_cycle`, `get_review_cycles` (with active filter and sorting), `update_review_cycle`, `delete_review_cycle` are implemented.
    *   Handles `IntegrityError` for unique `name` on create/update.
*   **PerformanceReview CRUD & Logic**:
    *   `create_performance_review`: Implemented.
    *   `get_performance_review`, `get_performance_reviews_for_employee` (with cycle filter), `get_performance_reviews_by_reviewer` (with cycle filter) are implemented.
    *   `update_performance_review`:
        *   Updates basic fields.
        *   Handles linking (`goal_ids_to_link`) and unlinking (`goal_ids_to_unlink`) of goals. It verifies that goals belong to the same employee before linking.
        *   Explicit `updated_at` setting is included.
    *   `delete_performance_review`: Implemented. SQLAlchemy's handling of M2M relationships via the `secondary` table is relied upon to clear links.
*   **Imports**: All necessary modules and models are imported.
*   **Error Handling**: `IntegrityError` is caught and re-raised for relevant operations.
*   **Timestamps (`updated_at`)**: Explicitly set in update functions to ensure the timestamp is updated, which is good practice especially if `onupdate=func.now()` in the model isn't consistently handled as a server-side trigger across all database backends (e.g., SQLite).

The implementation covers all requirements of the subtask, including the logic for managing the M2M relationship between performance reviews and goals.

I will now submit the report.
