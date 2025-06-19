import os
import shutil
import uuid
import pathlib
from typing import List, Optional

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    UploadFile, File, Form, Path as FastAPIPath # Renamed Path to FastAPIPath to avoid conflict
)
from starlette.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Project-specific imports
from api.dependencies import get_db
from api.auth import get_current_active_user # Assuming UserInDB is returned
from api.models import (
    UserInDB,
    DocumentCategory, DocumentCategoryCreate, DocumentCategoryResponse, DocumentCategoryBase,
    EmployeeDocument, EmployeeDocumentCreate, EmployeeDocumentResponse, EmployeeDocumentUpdate,
    Employee # For checking employee existence
)
from db.cruds import employee_documents_crud, employees_crud

# --- Configuration for Local File Storage ---
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent # Assuming this file is in api/
UPLOAD_DIRECTORY = BASE_DIR / "employee_uploads"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)


router = APIRouter(
    prefix="/employee-documents",
    tags=["Employee Documents"],
)

# --- Helper for Permissions (Basic Example) ---
def check_doc_permission(
    user: UserInDB,
    employee_id_of_document: Optional[str] = None,
    is_admin_or_hr_role_sufficient: bool = False
):
    """
    Checks if user has permission.
    - Admin/HR can always access if is_admin_or_hr_role_sufficient is True.
    - User can access their own documents if employee_id_of_document matches user.user_id.
    """
    if user.role in ["admin", "hr_manager"] and is_admin_or_hr_role_sufficient:
        return True
    if employee_id_of_document and user.user_id == employee_id_of_document:
        return True
    # Add manager check if applicable: if user is manager of employee_id_of_document

    action = "perform this action"
    if employee_id_of_document and user.user_id != employee_id_of_document:
        action = f"access documents for employee {employee_id_of_document}"

    if not (user.role in ["admin", "hr_manager"]): # If not admin/hr and other conditions failed
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not enough permissions to {action}.")
    elif not is_admin_or_hr_role_sufficient and not employee_id_of_document : # Admin/HR only but no employee context
         pass # Allow if admin_or_hr is sufficient for the operation (e.g. listing all categories)
    elif not (user.role in ["admin", "hr_manager"]): # Fallback if logic is missed
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not enough permissions to {action}.")


def _construct_download_url(document_id: str) -> str:
    # In a real app, use request.url_for if request object is available
    # For now, hardcoding path structure based on router prefix
    return f"/api/v1/employee-documents/documents/download/{document_id}" # Assuming /api/v1 prefix from main app

# --- API Endpoints for Document Categories (`/categories`) --- (Admin/HR)

@router.post("/categories/", response_model=DocumentCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_document_category_endpoint(
    category_data: DocumentCategoryCreate,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    check_doc_permission(current_user, is_admin_or_hr_role_sufficient=True) # Admin/HR only
    try:
        return employee_documents_crud.create_document_category(db=db, category_data=category_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document category with this name already exists.")

@router.get("/categories/", response_model=List[DocumentCategoryResponse])
def list_document_categories_endpoint(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user) # Auth for consistency, maybe public for some apps
):
    # check_doc_permission(current_user, is_admin_or_hr_role_sufficient=True) # Or allow broader access
    return employee_documents_crud.get_document_categories(db=db, skip=skip, limit=limit)

@router.get("/categories/{category_id}", response_model=DocumentCategoryResponse)
def get_document_category_endpoint(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    # check_doc_permission(current_user, is_admin_or_hr_role_sufficient=True)
    db_category = employee_documents_crud.get_document_category(db, category_id=category_id)
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document category not found")
    return db_category

@router.put("/categories/{category_id}", response_model=DocumentCategoryResponse)
def update_document_category_endpoint(
    category_id: int,
    category_data: DocumentCategoryBase,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    check_doc_permission(current_user, is_admin_or_hr_role_sufficient=True)
    try:
        updated_category = employee_documents_crud.update_document_category(
            db=db, category_id=category_id, category_update_data=category_data
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Another document category with this name already exists.")

    if updated_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document category not found for update")
    return updated_category

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_category_endpoint(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    check_doc_permission(current_user, is_admin_or_hr_role_sufficient=True)
    # Consider implications on existing documents (FK constraint or manual update)
    deleted_category = employee_documents_crud.delete_document_category(db=db, category_id=category_id)
    if deleted_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document category not found for deletion")
    return None

# --- API Endpoints for Employee Documents (`/documents`) ---

@router.post("/documents/upload/", response_model=EmployeeDocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_employee_document_endpoint(
    employee_id: str = Form(...), # Changed from File(...) to Form(...) for non-file fields
    document_category_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    # Permission: HR/Admin, or employee themselves, or manager of employee
    check_doc_permission(current_user, employee_id_of_document=employee_id, is_admin_or_hr_role_sufficient=True)

    if not employees_crud.get_employee(db, employee_id=employee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee with ID {employee_id} not found.")

    if document_category_id:
        if not employee_documents_crud.get_document_category(db, category_id=document_category_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document Category with ID {document_category_id} not found.")

    original_filename = file.filename if file.filename else "unknown_file"
    file_extension = pathlib.Path(original_filename).suffix
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    file_path = UPLOAD_DIRECTORY / unique_filename
    file_size = 0

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = file_path.stat().st_size # Get file size after writing
    except Exception as e:
        # Potentially delete partial file if error occurred
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not save uploaded file: {e}")
    finally:
        file.file.close()

    doc_metadata = EmployeeDocumentCreate(
        employee_id=employee_id,
        document_category_id=document_category_id,
        description=description
    )

    db_doc = employee_documents_crud.create_employee_document(
        db=db,
        doc_metadata=doc_metadata,
        file_name=original_filename,
        file_path_or_key=str(file_path), # Store as string
        file_type=file.content_type,
        file_size=file_size,
        uploaded_by_id=current_user.user_id
    )

    # Manually set download_url for the response, as the model doesn't store it.
    response_data = EmployeeDocumentResponse.model_validate(db_doc)
    response_data.download_url = _construct_download_url(db_doc.id)
    return response_data


@router.get("/documents/employee/{employee_id}", response_model=List[EmployeeDocumentResponse])
def list_employee_documents_endpoint(
    employee_id: str,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    check_doc_permission(current_user, employee_id_of_document=employee_id, is_admin_or_hr_role_sufficient=True)
    if not employees_crud.get_employee(db, employee_id=employee_id): # Check if employee exists
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee with ID {employee_id} not found.")

    documents = employee_documents_crud.get_employee_documents_for_employee(
        db=db, employee_id=employee_id, category_id=category_id
    )

    response_list = []
    for doc in documents:
        doc_resp = EmployeeDocumentResponse.model_validate(doc)
        doc_resp.download_url = _construct_download_url(doc.id)
        response_list.append(doc_resp)
    return response_list


@router.get("/documents/download/{document_id}", response_class=FileResponse)
async def download_employee_document_endpoint( # Made async for FileResponse best practice
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    db_doc = employee_documents_crud.get_employee_document(db, document_id=document_id)
    if db_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    check_doc_permission(current_user, employee_id_of_document=db_doc.employee_id, is_admin_or_hr_role_sufficient=True)

    file_path = pathlib.Path(db_doc.file_path_or_key)
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on server.")

    return FileResponse(
        path=str(file_path),
        filename=db_doc.file_name,
        media_type=db_doc.file_type or 'application/octet-stream'
    )

@router.get("/documents/{document_id}/metadata", response_model=EmployeeDocumentResponse)
def get_employee_document_metadata_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    db_doc = employee_documents_crud.get_employee_document(db, document_id=document_id)
    if db_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document metadata not found.")

    check_doc_permission(current_user, employee_id_of_document=db_doc.employee_id, is_admin_or_hr_role_sufficient=True)

    response_data = EmployeeDocumentResponse.model_validate(db_doc)
    response_data.download_url = _construct_download_url(db_doc.id)
    return response_data


@router.put("/documents/{document_id}/metadata", response_model=EmployeeDocumentResponse)
def update_employee_document_metadata_endpoint(
    document_id: str,
    metadata_update: EmployeeDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    db_doc_existing = employee_documents_crud.get_employee_document(db, document_id=document_id)
    if not db_doc_existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found for update.")

    check_doc_permission(current_user, employee_id_of_document=db_doc_existing.employee_id, is_admin_or_hr_role_sufficient=True) # Or stricter if only admin can update metadata

    if metadata_update.document_category_id:
        if not employee_documents_crud.get_document_category(db, category_id=metadata_update.document_category_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document Category with ID {metadata_update.document_category_id} not found.")

    updated_doc = employee_documents_crud.update_employee_document(
        db=db, document_id=document_id, doc_update_data=metadata_update
    )

    response_data = EmployeeDocumentResponse.model_validate(updated_doc)
    response_data.download_url = _construct_download_url(updated_doc.id)
    return response_data


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee_document_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    db_doc = employee_documents_crud.get_employee_document(db, document_id=document_id)
    if db_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    check_doc_permission(current_user, employee_id_of_document=db_doc.employee_id, is_admin_or_hr_role_sufficient=True) # Or stricter, only admin/hr

    # Delete physical file first
    try:
        file_to_delete = pathlib.Path(db_doc.file_path_or_key)
        if file_to_delete.is_file():
            os.remove(file_to_delete)
        elif file_to_delete.exists(): # It's a directory or something else, problem!
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stored path is not a file.")
        # If file_path_or_key points to cloud, this logic would be different (e.g., S3 client delete_object)
    except FileNotFoundError:
        # Log this, but proceed to delete DB record as file is already gone.
        print(f"Warning: File not found for deletion: {db_doc.file_path_or_key}") # Replace with actual logging
    except Exception as e:
        # Log error, but potentially proceed to delete DB record or handle as critical failure
        print(f"Error deleting file {db_doc.file_path_or_key}: {e}") # Replace with actual logging
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not delete file. Error: {e}")

    employee_documents_crud.delete_employee_document(db=db, document_id=document_id)
    return None
