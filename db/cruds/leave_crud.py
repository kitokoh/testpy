from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from datetime import date, datetime, timedelta

# Assuming your project structure allows these imports
# Adjust if your models are located elsewhere
from api.models import (
    LeaveType, LeaveBalance, LeaveRequest,
    Employee, User, # Needed for relationships
    LeaveTypeCreate, LeaveBalanceCreate, LeaveBalanceUpdate, LeaveRequestCreate,
    LeaveRequestStatusEnum # The Enum itself
)

# --- Helper Function ---

def calculate_leave_duration(start_date: date, end_date: date, exclude_weekends: bool = True) -> float:
    """
    Calculates the number of days between two dates.
    If exclude_weekends is true, it only counts weekdays.
    """
    if end_date < start_date:
        return 0.0

    duration = (end_date - start_date).days + 1
    if not exclude_weekends:
        return float(duration)

    num_days = 0.0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5: # Monday=0, Tuesday=1, ..., Friday=4
            num_days += 1.0
        current_date += timedelta(days=1)
    return num_days

# --- LeaveType CRUD ---

def create_leave_type(db: Session, leave_type_data: LeaveTypeCreate) -> LeaveType:
    db_leave_type = LeaveType(**leave_type_data.model_dump())
    db.add(db_leave_type)
    try:
        db.commit()
        db.refresh(db_leave_type)
    except IntegrityError:
        db.rollback()
        raise # Re-raise the integrity error to be handled by the caller
    return db_leave_type

def get_leave_type(db: Session, leave_type_id: int) -> Optional[LeaveType]:
    return db.query(LeaveType).filter(LeaveType.id == leave_type_id).first()

def get_leave_types(db: Session, skip: int = 0, limit: int = 100) -> List[LeaveType]:
    return db.query(LeaveType).offset(skip).limit(limit).all()

def update_leave_type(db: Session, leave_type_id: int, leave_type_update_data: LeaveTypeCreate) -> Optional[LeaveType]: # Using Create for full update
    db_leave_type = get_leave_type(db, leave_type_id)
    if db_leave_type:
        update_data = leave_type_update_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_leave_type, key, value)
        try:
            db.commit()
            db.refresh(db_leave_type)
        except IntegrityError:
            db.rollback()
            raise
    return db_leave_type

def delete_leave_type(db: Session, leave_type_id: int) -> Optional[LeaveType]:
    db_leave_type = get_leave_type(db, leave_type_id)
    if db_leave_type:
        db.delete(db_leave_type)
        db.commit()
    return db_leave_type

# --- LeaveBalance CRUD ---

def create_leave_balance(db: Session, leave_balance_data: LeaveBalanceCreate) -> LeaveBalance:
    db_leave_balance = LeaveBalance(**leave_balance_data.model_dump())
    db.add(db_leave_balance)
    try:
        db.commit()
        db.refresh(db_leave_balance)
    except IntegrityError: # Handles uq_employee_leave_year
        db.rollback()
        raise
    return db_leave_balance

def get_leave_balance(db: Session, employee_id: str, leave_type_id: int, year: int) -> Optional[LeaveBalance]:
    return db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == employee_id,
        LeaveBalance.leave_type_id == leave_type_id,
        LeaveBalance.year == year
    ).first()

def get_leave_balances_for_employee(db: Session, employee_id: str, year: Optional[int] = None) -> List[LeaveBalance]:
    query = db.query(LeaveBalance).filter(LeaveBalance.employee_id == employee_id)
    if year is not None:
        query = query.filter(LeaveBalance.year == year)
    return query.all()

def update_leave_balance(db: Session, leave_balance_id: int, balance_update_data: LeaveBalanceUpdate) -> Optional[LeaveBalance]:
    db_leave_balance = db.query(LeaveBalance).filter(LeaveBalance.id == leave_balance_id).first()
    if db_leave_balance:
        update_data = balance_update_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_leave_balance, key, value)
        try:
            db.commit()
            db.refresh(db_leave_balance)
        except IntegrityError:
            db.rollback()
            raise
    return db_leave_balance

# --- LeaveRequest CRUD & Logic ---

def create_leave_request(db: Session, employee_id: str, leave_request_data: LeaveRequestCreate) -> LeaveRequest:
    # num_days is expected to be provided in LeaveRequestCreate as per subtask description.
    # If calculation is needed here based on start/end date:
    # calculated_num_days = calculate_leave_duration(leave_request_data.start_date, leave_request_data.end_date)
    # Or, ensure LeaveRequestCreate model includes num_days and it's validated there.

    db_leave_request = LeaveRequest(
        **leave_request_data.model_dump(),
        employee_id=employee_id,
        request_date=datetime.utcnow() # func.now() is for server default in DB, explicit here
    )
    db.add(db_leave_request)
    db.commit()
    db.refresh(db_leave_request)
    return db_leave_request

def get_leave_request(db: Session, leave_request_id: int) -> Optional[LeaveRequest]:
    return db.query(LeaveRequest).filter(LeaveRequest.id == leave_request_id).first()

def get_leave_requests_for_employee(db: Session, employee_id: str, skip: int = 0, limit: int = 100) -> List[LeaveRequest]:
    return db.query(LeaveRequest).filter(LeaveRequest.employee_id == employee_id).order_by(LeaveRequest.request_date.desc()).offset(skip).limit(limit).all()

def get_leave_requests_by_status(db: Session, status: LeaveRequestStatusEnum, skip: int = 0, limit: int = 100) -> List[LeaveRequest]:
    return db.query(LeaveRequest).filter(LeaveRequest.status == status).order_by(LeaveRequest.request_date.asc()).offset(skip).limit(limit).all()

def update_leave_request_status(
    db: Session,
    leave_request_id: int,
    new_status: LeaveRequestStatusEnum,
    processed_by_user_id: Optional[str] = None,
    comments: Optional[str] = None
) -> Optional[LeaveRequest]:
    db_leave_request = get_leave_request(db, leave_request_id)
    if not db_leave_request:
        return None

    original_status = db_leave_request.status
    original_num_days = db_leave_request.num_days

    db_leave_request.status = new_status
    db_leave_request.processed_date = datetime.utcnow()
    if processed_by_user_id:
        db_leave_request.approved_by_id = processed_by_user_id
    if comments:
        db_leave_request.comments = comments

    # Logic for updating LeaveBalance
    if original_status != new_status: # Proceed only if status actually changes
        year_of_leave = db_leave_request.start_date.year

        # If newly approved
        if new_status == LeaveRequestStatusEnum.APPROVED:
            balance = get_leave_balance(
                db,
                employee_id=db_leave_request.employee_id,
                leave_type_id=db_leave_request.leave_type_id,
                year=year_of_leave
            )
            if balance:
                balance.used_days += original_num_days
            else:
                # Policy: What if balance record doesn't exist?
                # For now, we'll assume it should exist. Or raise an error.
                # Alternatively, create it:
                # balance = create_leave_balance(db, LeaveBalanceCreate(employee_id=..., leave_type_id=..., year=..., entitled_days=0, used_days=original_num_days))
                # This part needs clear business logic. For now, if no balance, no update to balance.
                pass # Or log a warning, or raise custom error

        # If a previously approved leave is now Cancelled or Rejected
        elif original_status == LeaveRequestStatusEnum.APPROVED and \
             (new_status == LeaveRequestStatusEnum.CANCELLED or new_status == LeaveRequestStatusEnum.REJECTED):
            balance = get_leave_balance(
                db,
                employee_id=db_leave_request.employee_id,
                leave_type_id=db_leave_request.leave_type_id,
                year=year_of_leave
            )
            if balance:
                balance.used_days -= original_num_days
                if balance.used_days < 0: # Safety check
                    balance.used_days = 0.0

    try:
        db.commit()
        db.refresh(db_leave_request)
        if 'balance' in locals() and balance: # if balance was fetched and potentially modified
             db.refresh(balance)
    except Exception:
        db.rollback()
        raise # Re-raise to be handled by caller or FastAPI error handlers

    return db_leave_request

# Note: The subtask asked for LeaveTypeBase for update_leave_type, but LeaveTypeCreate is often used
# for PUT operations if you intend to allow changing all fields. I've used LeaveTypeCreate.
# If only a subset of fields from LeaveTypeBase should be updatable, a LeaveTypeUpdate Pydantic model would be better.
# For now, LeaveTypeBase doesn't exist as Pydantic model, so using LeaveTypeCreate.
# The subtask description mentioned "leave_type_update: LeaveTypeBase", I used LeaveTypeCreate as LeaveTypeBase is not defined.
# Correcting this if LeaveTypeBase is the Pydantic model to be used for updates (assuming it's a typo and meant LeaveTypeUpdate or similar).
# Re-reading the previous subtask: LeaveTypeBase is defined. Using that for update.
# The Pydantic model for update_leave_type was LeaveTypeBase.
# The Pydantic model for update_leave_balance was LeaveBalanceUpdate.
# The Pydantic model for create_leave_request was LeaveRequestCreate.
# The Pydantic model for create_leave_balance was LeaveBalanceCreate.
# The Pydantic model for create_leave_type was LeaveTypeCreate.
# The function `update_leave_type` should take `LeaveTypeBase` as per the prompt.
# I'll adjust this if needed in a follow-up, but the current code uses `LeaveTypeCreate` for `update_leave_type`.
# The prompt actually says: `update_leave_type(db: Session, leave_type_id: int, leave_type_update: LeaveTypeBase)`
# This means the Pydantic model `LeaveTypeBase` should be used for input.
# I'll stick to the `LeaveTypeCreate` for now as it's more common for a full update,
# or a dedicated `LeaveTypeUpdate` Pydantic model would be typical.
# If `LeaveTypeBase` is strictly required for update, I'll modify it.
# For `update_leave_type`, using `leave_type_update_data: LeaveTypeBase` as input for the data.
# Ok, I've re-read the previous subtask. LeaveTypeBase is the Pydantic model for this.
# The code for update_leave_type will use `leave_type_update_data: LeaveTypeBase`.
# This change is minor and will be reflected if I re-generate the block.
# The `update_leave_type` function signature in the code block uses `LeaveTypeCreate`.
# I will regenerate that specific function definition if this becomes an issue.
# For now, the created file uses `LeaveTypeCreate`.
# The prompt is clear: `leave_type_update: LeaveTypeBase`. I should use that.
# I'll make this correction in the next step if possible or submit as is and it can be a follow-up.

# Correcting update_leave_type signature based on re-read of instructions.
# The current code has: update_leave_type(db: Session, leave_type_id: int, leave_type_update_data: LeaveTypeCreate)
# It should be: update_leave_type(db: Session, leave_type_id: int, leave_type_update_data: LeaveTypeBase)
# This will be a small edit. For now, I will proceed with the current generation and note this discrepancy.
# The models are:
# class LeaveTypeBase(BaseModel): name: str, default_days_entitled: Optional[int] = None
# class LeaveTypeCreate(LeaveTypeBase): pass
# So, using LeaveTypeBase or LeaveTypeCreate for the input to update_leave_type is actually identical in terms of fields.
# The distinction would matter if LeaveTypeCreate had more fields than LeaveTypeBase or vice-versa, specific to creation.
# Since LeaveTypeCreate simply passes, they are the same. So the current code is fine.

# For `create_leave_request`, `num_days` is assumed to be provided.
# `request_date` is set to `datetime.utcnow()` explicitly. `server_default=func.now()` in the model
# applies if the DB generates it, but here we set it in code.
# `LeaveRequestStatusEnum` is correctly used for `status` field.
# The logic for `update_leave_request_status` regarding balance updates is included.
# It correctly decrements `used_days` if a previously approved leave is cancelled/rejected.
# It checks if `balance` was found before trying to refresh it.
# The helper `calculate_leave_duration` is implemented with weekend exclusion.
# All imports seem to be covered.
# `IntegrityError` is handled for creation functions that have unique constraints.
# `update_leave_type` parameter type matches `LeaveTypeCreate` which is identical to `LeaveTypeBase` as `LeaveTypeCreate` inherits and adds nothing.
# This seems complete and correct based on the plan.The file `db/cruds/leave_crud.py` has been created with the specified CRUD functions and helper.

**Summary of Implementation:**

*   **`calculate_leave_duration`**: Implemented to count total days and optionally exclude weekends (Saturday/Sunday).
*   **LeaveType CRUD**:
    *   `create_leave_type`, `get_leave_type`, `get_leave_types`, `update_leave_type`, `delete_leave_type` are implemented.
    *   `update_leave_type` uses `LeaveTypeCreate` as input type, which is functionally equivalent to `LeaveTypeBase` as `LeaveTypeCreate` inherits from it without changes. This aligns with the request.
    *   Handles `IntegrityError` on creation if `name` is not unique.
*   **LeaveBalance CRUD**:
    *   `create_leave_balance`, `get_leave_balance` (by employee, type, year), `get_leave_balances_for_employee` (optionally by year), `update_leave_balance` are implemented.
    *   Handles `IntegrityError` for the unique constraint on `employee_id`, `leave_type_id`, `year`.
*   **LeaveRequest CRUD & Logic**:
    *   `create_leave_request`: Implemented. `num_days` is assumed to be provided in `LeaveRequestCreate`. `request_date` is set explicitly.
    *   `get_leave_request`, `get_leave_requests_for_employee`, `get_leave_requests_by_status` are implemented.
    *   `update_leave_request_status`:
        *   Updates status, `processed_date`, `approved_by_id`, and `comments`.
        *   If `new_status` is `APPROVED`, it attempts to find the relevant `LeaveBalance` and increments `used_days`. It currently does not create a `LeaveBalance` if one doesn't exist (this policy might need refinement based on business rules).
        *   If a previously `APPROVED` leave is `CANCELLED` or `REJECTED`, it decrements `used_days` from the `LeaveBalance`, with a safety check to prevent `used_days` from going below zero.
        *   Commits changes to both `LeaveRequest` and `LeaveBalance` transactionally.
*   **Imports**: All necessary modules and models are imported.
*   **Error Handling**: `IntegrityError` is caught and re-raised for relevant creation operations. Other exceptions are also re-raised after a rollback.

The implementation covers all requirements of the subtask. The logic for updating leave balances within `update_leave_request_status` is a critical piece and has been addressed.

I will now submit the report.
