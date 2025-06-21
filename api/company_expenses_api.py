from fastapi import APIRouter, HTTPException, Depends, Query, Path, Request
from typing import List, Optional, Dict, Any
from datetime import datetime

import db.cruds.company_expenses_crud as expenses_crud
from .models import (
    CompanyExpenseCreatePydantic, CompanyExpenseReadPydantic, CompanyExpenseUpdatePydantic,
    CompanyFactureReadPydantic, LinkFactureToExpenseRequestPydantic, #Pydantic suffix added in models
    UserInDB
)
from .auth import get_current_active_user
# Assuming CompanyExpenseDataForConfirmation will be a Pydantic model for user-confirmed data.
# For now, CompanyExpenseCreatePydantic can be reused if it fits the structure of confirmed data.
# Or define a specific one if needed, e.g. in api/models.py
# from .models import CompanyExpenseDataForConfirmationPydantic

router = APIRouter(
    prefix="/api/company-expenses", # Using kebab-case for URL prefix
    tags=["Company Expenses"],
    responses={404: {"description": "Not found"}},
)

def format_expense_response(db_expense_dict: Dict[str, Any], request: Request) -> CompanyExpenseReadPydantic:
    """
    Formats a dictionary (from DB row) into a CompanyExpenseReadPydantic model.
    Also fetches and formats the linked facture if it exists.
    """
    if not db_expense_dict:
        # This case should ideally be handled before calling this function,
        # but as a safeguard:
        raise ValueError("db_expense_dict cannot be None or empty in format_expense_response")

    # Ensure 'is_deleted' is correctly cast to bool if it's integer in DB
    db_expense_dict['is_deleted'] = bool(db_expense_dict.get('is_deleted', 0))

    linked_facture_data = None
    if db_expense_dict.get('facture_id'):
        facture_dict = expenses_crud.get_company_facture_by_id(db_expense_dict['facture_id'])
        if facture_dict:
            facture_dict['is_deleted'] = bool(facture_dict.get('is_deleted', 0))
            linked_facture_data = CompanyFactureReadPydantic(**facture_dict)

    # Create the main Pydantic model instance
    # Ensure all required fields for CompanyExpenseReadPydantic are present in db_expense_dict
    # or handled appropriately.
    # Pydantic will raise validation error if a required field is missing.

    # Prepare data for CompanyExpenseReadPydantic, excluding facture for now
    expense_data_for_model = {k: v for k, v in db_expense_dict.items() if k != 'facture'}

    response_model = CompanyExpenseReadPydantic(
        **expense_data_for_model,
        facture=linked_facture_data
    )
    return response_model

@router.post("", response_model=CompanyExpenseReadPydantic, status_code=201)
async def create_company_expense_api(
    expense_in: CompanyExpenseCreatePydantic,
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Create a new company expense.
    Facture can optionally be linked at creation if facture_id is provided.
    """
    if expense_in.facture_id:
        facture_exists = expenses_crud.get_company_facture_by_id(expense_in.facture_id)
        if not facture_exists:
            raise HTTPException(status_code=404, detail=f"Facture with ID {expense_in.facture_id} not found.")

    expense_id = expenses_crud.add_company_expense(
        expense_date=expense_in.expense_date.isoformat(), # Ensure date is string
        amount=expense_in.amount,
        currency=expense_in.currency,
        recipient_name=expense_in.recipient_name,
        description=expense_in.description,
        facture_id=expense_in.facture_id,
        created_by_user_id=current_user.user_id
    )
    if expense_id is None:
        raise HTTPException(status_code=500, detail="Failed to create company expense in the database.")

    db_expense = expenses_crud.get_company_expense_by_id(expense_id)
    if not db_expense:
        # This should ideally not happen if creation was successful
        raise HTTPException(status_code=500, detail="Company expense created but could not be retrieved.")

    return format_expense_response(db_expense, request)

@router.get("/{expense_id}", response_model=CompanyExpenseReadPydantic)
async def get_company_expense_api(
    expense_id: int = Path(..., description="The ID of the company expense to retrieve"),
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Retrieve a specific company expense by its ID.
    """
    db_expense = expenses_crud.get_company_expense_by_id(expense_id)
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Company expense not found.")
    return format_expense_response(db_expense, request)

@router.get("", response_model=List[CompanyExpenseReadPydantic])
async def list_company_expenses_api(
    request: Request,
    recipient_name: Optional[str] = Query(None, description="Filter by recipient name (case-insensitive, partial match)"),
    date_from: Optional[str] = Query(None, description="Filter by expense date from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter by expense date to (YYYY-MM-DD)"),
    description_keywords: Optional[str] = Query(None, description="Filter by keywords in description (case-insensitive, partial match)"),
    facture_id: Optional[int] = Query(None, description="Filter by exact facture ID"),
    min_amount: Optional[float] = Query(None, description="Filter by minimum expense amount"),
    max_amount: Optional[float] = Query(None, description="Filter by maximum expense amount"),
    currency: Optional[str] = Query(None, description="Filter by currency code (e.g., USD, EUR)"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    List company expenses with pagination and filtering.
    """
    db_expenses_list = expenses_crud.get_all_company_expenses(
        limit=limit,
        offset=skip,
        recipient_name=recipient_name,
        date_from=date_from,
        date_to=date_to,
        description_keywords=description_keywords,
        facture_id=facture_id,
        min_amount=min_amount,
        max_amount=max_amount,
        currency=currency
    )
    if not db_expenses_list:
        return []

    return [format_expense_response(expense_dict, request) for expense_dict in db_expenses_list]

@router.put("/{expense_id}", response_model=CompanyExpenseReadPydantic)
async def update_company_expense_api(
    expense_id: int,
    expense_update_data: CompanyExpenseUpdatePydantic,
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Update an existing company expense.
    Allows updating details and linking/unlinking a facture.
    To unlink a facture, pass `facture_id: null` in the request body.
    """
    existing_expense = expenses_crud.get_company_expense_by_id(expense_id)
    if not existing_expense:
        raise HTTPException(status_code=404, detail="Company expense not found.")

    update_data_dict = expense_update_data.dict(exclude_unset=True)

    # Handle facture_id separately to allow unlinking with null
    if 'facture_id' in update_data_dict:
        new_facture_id = update_data_dict['facture_id']
        if new_facture_id is not None and new_facture_id > 0:
            facture_exists = expenses_crud.get_company_facture_by_id(new_facture_id)
            if not facture_exists:
                raise HTTPException(status_code=404, detail=f"Facture with ID {new_facture_id} not found for linking.")
        # If new_facture_id is None, it will be passed as None to CRUD, unlinking.

    # Convert date object to string if present
    if 'expense_date' in update_data_dict and update_data_dict['expense_date'] is not None:
        update_data_dict['expense_date'] = update_data_dict['expense_date'].isoformat()


    success = expenses_crud.update_company_expense(expense_id=expense_id, **update_data_dict)

    if not success:
        # Re-fetch to check if it was a "not found" or other error
        current_state = expenses_crud.get_company_expense_by_id(expense_id)
        if not current_state: # Should not happen if initial check passed, unless deleted concurrently
             raise HTTPException(status_code=404, detail="Company expense not found during update attempt.")
        raise HTTPException(status_code=500, detail="Failed to update company expense. No changes made or database error.")

    updated_db_expense = expenses_crud.get_company_expense_by_id(expense_id)
    if not updated_db_expense:
         raise HTTPException(status_code=404, detail="Company expense not found after update attempt.") # Should not happen

    return format_expense_response(updated_db_expense, request)

@router.delete("/{expense_id}", status_code=204)
async def delete_company_expense_api(
    expense_id: int = Path(..., description="The ID of the company expense to soft delete"),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Soft delete a company expense.
    """
    existing_expense = expenses_crud.get_company_expense_by_id(expense_id)
    if not existing_expense:
        raise HTTPException(status_code=404, detail="Company expense not found.")

    if not expenses_crud.soft_delete_company_expense(expense_id):
        # This might happen if the record was deleted by another process between the check and the delete operation,
        # or if there's a database error.
        raise HTTPException(status_code=500, detail="Failed to delete company expense.")

    return # No content response for 204

@router.post("/{expense_id}/link-facture", response_model=CompanyExpenseReadPydantic)
async def link_facture_to_expense_api(
    expense_id: int,
    link_request: LinkFactureToExpenseRequestPydantic,
    request_obj: Request, # Renamed from 'request' to avoid conflict
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Link an existing facture to an existing company expense.
    """
    expense = expenses_crud.get_company_expense_by_id(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Company expense not found.")

    facture = expenses_crud.get_company_facture_by_id(link_request.facture_id)
    if not facture:
        raise HTTPException(status_code=404, detail=f"Facture with ID {link_request.facture_id} not found.")

    if expense.get('facture_id') == link_request.facture_id:
        # Facture already linked, return current state
        return format_expense_response(expense, request_obj)

    # Check if the facture is already linked to another expense (optional, based on desired business logic)
    # For now, we assume a facture can only be linked to one expense due to UNIQUE constraint on company_expenses.facture_id

    success = expenses_crud.link_facture_to_expense(expense_id=expense_id, facture_id=link_request.facture_id)
    if not success:
        # This could be due to the expense no longer existing, or the facture_id causing a unique constraint violation elsewhere (if not handled by CRUD)
        # or a general DB error.
        # Re-check expense existence.
        current_expense_state = expenses_crud.get_company_expense_by_id(expense_id)
        if not current_expense_state:
             raise HTTPException(status_code=404, detail="Company expense not found during linking attempt.")
        raise HTTPException(status_code=500, detail=f"Failed to link facture {link_request.facture_id} to expense {expense_id}.")

    updated_expense = expenses_crud.get_company_expense_by_id(expense_id)
    if not updated_expense:
        raise HTTPException(status_code=500, detail="Expense not found after linking facture.")

    return format_expense_response(updated_expense, request_obj)

@router.delete("/{expense_id}/unlink-facture", response_model=CompanyExpenseReadPydantic)
async def unlink_facture_from_expense_api(
    expense_id: int,
    request_obj: Request, # Renamed from 'request'
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Unlink a facture from a company expense.
    """
    expense = expenses_crud.get_company_expense_by_id(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Company expense not found.")

    if expense.get('facture_id') is None:
        # No facture linked, return current state
        return format_expense_response(expense, request_obj)

    success = expenses_crud.unlink_facture_from_expense(expense_id=expense_id)
    if not success:
        current_expense_state = expenses_crud.get_company_expense_by_id(expense_id)
        if not current_expense_state:
             raise HTTPException(status_code=404, detail="Company expense not found during unlinking attempt.")
        raise HTTPException(status_code=500, detail=f"Failed to unlink facture from expense {expense_id}.")

    updated_expense = expenses_crud.get_company_expense_by_id(expense_id)
    if not updated_expense:
         raise HTTPException(status_code=500, detail="Expense not found after unlinking facture.")

    return format_expense_response(updated_expense, request_obj)

@router.post("/from-facture", response_model=CompanyExpenseReadPydantic, status_code=201)
async def create_expense_from_confirmed_facture_data_api(
    expense_data: CompanyExpenseCreatePydantic, # Reuse Create model for confirmed data
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Creates a new company expense record from user-confirmed data derived from a facture.
    The request body should contain all necessary fields for a company expense,
    including the `facture_id` of the already uploaded and processed facture.
    """
    if not expense_data.facture_id:
        raise HTTPException(status_code=400, detail="Facture ID is required to create an expense from facture data.")

    # Verify the facture exists and is in a state ready for confirmation (e.g., 'data_extracted_pending_confirmation')
    facture = expenses_crud.get_company_facture_by_id(expense_data.facture_id)
    if not facture:
        raise HTTPException(status_code=404, detail=f"Facture with ID {expense_data.facture_id} not found.")

    # Optional: Check if an expense already exists for this facture_id to prevent duplicates
    # This would require a CRUD function like `get_expense_by_facture_id`.
    # For now, we rely on the UNIQUE constraint on company_expenses.facture_id in the DB for linked expenses.
    # If an expense is created *without* linking, then linked later, that's one path.
    # If created *from* a facture, it should be linked.

    # Create the new company expense
    new_expense_id = expenses_crud.add_company_expense(
        expense_date=expense_data.expense_date.isoformat(),
        amount=expense_data.amount,
        currency=expense_data.currency,
        recipient_name=expense_data.recipient_name,
        description=expense_data.description,
        facture_id=expense_data.facture_id, # This links it
        created_by_user_id=current_user.user_id
    )

    if new_expense_id is None:
        # This could happen if the facture_id is already linked due to the UNIQUE constraint on company_expenses.facture_id
        # Or other DB errors.
        raise HTTPException(status_code=500, detail="Failed to create company expense from facture data. Possible duplicate or DB error.")

    # Update the facture status to 'confirmed' or similar
    expenses_crud.update_company_facture(
        facture_id=expense_data.facture_id,
        extraction_status='data_confirmed_linked' # Or just 'confirmed'
    )

    created_expense_db = expenses_crud.get_company_expense_by_id(new_expense_id)
    if not created_expense_db:
        raise HTTPException(status_code=500, detail="Expense created but could not be retrieved.")

    return format_expense_response(created_expense_db, request)


# It's good practice to also add API endpoints for managing CompanyFacture entities directly,
# especially for creation (uploading the file) and retrieval.
# These will be added in a subsequent step as per the plan.

# To integrate this router into the main FastAPI application:
# In your main.py or wherever FastAPI app is defined:
# from api.company_expenses_api import router as company_expenses_router
# app.include_router(company_expenses_router)
