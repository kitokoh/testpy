import os
import uuid
import shutil
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Path, Request
from typing import Optional

import db.cruds.company_expenses_crud as factures_crud # Reusing the CRUD from expenses for factures
from .models import (
    CompanyFactureReadPydantic,
    UserInDB
import json # For storing parsed data as JSON string

)
from .auth import get_current_active_user
import config # To get COMPANY_FACTURES_DIR_PATH
from utils.text_extraction import extract_text_from_pdf, parse_invoice_text # Import the new utility

router = APIRouter(
    prefix="/api/company-factures", # Using kebab-case for URL prefix
    tags=["Company Factures"],
    responses={404: {"description": "Not found"}},
)

def format_facture_response(db_facture_dict: dict, request: Request) -> CompanyFactureReadPydantic:
    """
    Formats a dictionary (from DB row) into a CompanyFactureReadPydantic model.
    """
    if not db_facture_dict:
        raise ValueError("db_facture_dict cannot be None or empty in format_facture_response")

    db_facture_dict['is_deleted'] = bool(db_facture_dict.get('is_deleted', 0))

    # Potentially construct a download URL if needed in the future
    # For now, stored_file_path is just the path on server.
    # db_facture_dict['download_url'] = f"{request.base_url}static/{db_facture_dict['stored_file_path']}"

    return CompanyFactureReadPydantic(**db_facture_dict)


@router.get("", response_model=List[CompanyFactureReadPydantic])
async def list_company_factures_api(
    request: Request,
    original_file_name_like: Optional[str] = Query(None, description="Filter by original file name (case-insensitive, partial match)"),
    extraction_status: Optional[str] = Query(None, description="Filter by extraction status (e.g., 'pending_extraction', 'data_extracted')"),
    upload_date_from: Optional[str] = Query(None, description="Filter by upload date from (YYYY-MM-DD)"),
    upload_date_to: Optional[str] = Query(None, description="Filter by upload date to (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    List company factures with pagination and filtering.
    """
    db_factures_list = factures_crud.get_all_company_factures(
        limit=limit,
        offset=skip,
        original_file_name_like=original_file_name_like,
        extraction_status=extraction_status,
        upload_date_from=upload_date_from,
        upload_date_to=upload_date_to
    )
    if not db_factures_list:
        return []

    return [format_facture_response(facture_dict, request) for facture_dict in db_factures_list]


@router.post("/upload", response_model=CompanyFactureReadPydantic, status_code=201)
async def upload_company_facture_api(
    request: Request,
    file: UploadFile = File(..., description="The facture file to upload (PDF, JPG, PNG)"),
    # Optional metadata, could be expanded
    original_file_name_override: Optional[str] = Form(None, description="Optional override for the original file name stored in DB"),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Upload a company facture file.
    The file will be saved to a configured directory, and a record will be created in the database.
    """
    # Ensure the upload directory exists
    os.makedirs(config.COMPANY_FACTURES_DIR_PATH, exist_ok=True)

    # Validate file type (basic validation based on content type or extension)
    allowed_mime_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
    file_extension = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = [".pdf", ".jpeg", ".jpg", ".png"]

    if file.content_type not in allowed_mime_types or file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: PDF, JPEG, PNG. Received: {file.content_type} or extension {file_extension}"
        )

    # Generate a unique filename for storage to prevent collisions
    # Using original extension, ensuring it's one of the allowed ones.
    safe_extension = file_extension if file_extension in allowed_extensions else ".dat" # Fallback, though validation should prevent this
    stored_file_name = f"{uuid.uuid4()}{safe_extension}"
    stored_file_path = os.path.join(config.COMPANY_FACTURES_DIR_PATH, stored_file_name)

    try:
        with open(stored_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail=f"Could not save uploaded file: {str(e)}")
    finally:
        file.file.close()

    db_original_file_name = original_file_name_override if original_file_name_override else file.filename

    # Add record to database
    facture_id = factures_crud.add_company_facture(
        original_file_name=db_original_file_name,
        stored_file_path=stored_file_path, # Store the full path or relative path based on system design
        file_mime_type=file.content_type,
        extraction_status='pending_extraction'
    )

    if facture_id is None:
        # Attempt to clean up saved file if DB record fails
        if os.path.exists(stored_file_path):
            os.remove(stored_file_path)
        raise HTTPException(status_code=500, detail="Failed to create facture record in database after file upload.")

    # Attempt text extraction and parsing if it's a PDF
    parsed_data_json_str = None
    new_extraction_status = 'pending_review' # Default status

    if file.content_type == "application/pdf":
        raw_text = extract_text_from_pdf(stored_file_path)
        if raw_text:
            parsed_data = parse_invoice_text(raw_text)
            parsed_data_json_str = json.dumps(parsed_data) # Store the dict as a JSON string

            # Determine status based on parsing results
            if parsed_data.get("primary_amount") or parsed_data.get("primary_date") or parsed_data.get("primary_vendor"):
                new_extraction_status = 'data_extracted_pending_confirmation'
            else:
                new_extraction_status = 'extraction_successful_needs_review' # Text extracted, but key fields not found
        else:
            new_extraction_status = 'extraction_failed' # PDF text extraction yielded nothing
            # Store empty parsing result or just raw_text:None
            parsed_data_json_str = json.dumps({"raw_text": None, "detected_dates": [], "detected_amounts": [], "potential_vendors": []})


        factures_crud.update_company_facture(
            facture_id=facture_id,
            extracted_data_json=parsed_data_json_str,
            extraction_status=new_extraction_status
        )

    elif file_extension in [".jpeg", ".jpg", ".png"]:
        new_extraction_status = 'pending_ocr' # Mark for OCR if it's an image
        # Store empty parsing result initially for images
        parsed_data_json_str = json.dumps({"raw_text": None, "detected_dates": [], "detected_amounts": [], "potential_vendors": []})
        factures_crud.update_company_facture(
                facture_id=facture_id,
                extracted_data_json=parsed_data_json_str,
                extraction_status=new_extraction_status
            )
    else:
        new_extraction_status = 'manual_review_required' # For other file types
        parsed_data_json_str = json.dumps({"raw_text": "File type not processable for automated extraction.", "detected_dates": [], "detected_amounts": [], "potential_vendors": []})
        factures_crud.update_company_facture(
                facture_id=facture_id,
                extracted_data_json=parsed_data_json_str,
                extraction_status=new_extraction_status
            )

    db_facture = factures_crud.get_company_facture_by_id(facture_id)
    if not db_facture:
        # This should not happen if previous steps were successful
        raise HTTPException(status_code=500, detail="Facture record created/updated but could not be retrieved.")

    return format_facture_response(db_facture, request)


@router.get("/{facture_id}", response_model=CompanyFactureReadPydantic)
async def get_company_facture_api(
    facture_id: int = Path(..., description="The ID of the company facture to retrieve"),
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Retrieve a specific company facture by its ID.
    """
    db_facture = factures_crud.get_company_facture_by_id(facture_id)
    if db_facture is None:
        raise HTTPException(status_code=404, detail="Company facture not found.")
    return format_facture_response(db_facture, request)


@router.delete("/{facture_id}", status_code=204)
async def delete_company_facture_api(
    facture_id: int = Path(..., description="The ID of the company facture to soft delete"),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Soft delete a company facture record.
    Note: This currently does not delete the file from storage.
    File deletion would require additional logic (e.g., a background job or specific admin action).
    """
    existing_facture = factures_crud.get_company_facture_by_id(facture_id)
    if not existing_facture:
        raise HTTPException(status_code=404, detail="Company facture not found.")

    # Before soft deleting, check if it's linked to any non-deleted expense.
    # This requires a new CRUD function: get_expenses_by_facture_id(facture_id)
    # For now, we'll proceed with soft delete. Business logic for handling linked expenses
    # upon facture deletion (e.g., unlinking, preventing deletion) can be added.
    # Current DB schema for company_expenses.facture_id is ON DELETE SET NULL,
    # but that's for physical DB deletion of the facture, not soft delete.

    if not factures_crud.soft_delete_company_facture(facture_id):
        raise HTTPException(status_code=500, detail="Failed to soft delete company facture.")

    # Physical file cleanup is not handled here to prevent accidental data loss on soft delete.
    # A separate process or admin action should manage orphaned files if physical deletion is required.

    return # No content response for 204

# To integrate this router into the main FastAPI application:
# In your main.py or wherever FastAPI app is defined:
# from api.company_factures_api import router as company_factures_router
# app.include_router(company_factures_router)
