from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

# Assuming your project structure allows these imports
from api.models import (
    DocumentCategory, DocumentCategoryCreate, DocumentCategoryBase, # DocumentCategoryBase for update
    EmployeeDocument, EmployeeDocumentCreate, EmployeeDocumentUpdate
)

# --- DocumentCategory CRUD ---

def create_document_category(db: Session, category_data: DocumentCategoryCreate) -> DocumentCategory:
    db_category = DocumentCategory(**category_data.model_dump())
    try:
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
    except IntegrityError: # Handles unique name
        db.rollback()
        raise
    return db_category

def get_document_category(db: Session, category_id: int) -> Optional[DocumentCategory]:
    return db.query(DocumentCategory).filter(DocumentCategory.id == category_id).first()

def get_document_categories(db: Session, skip: int = 0, limit: int = 100) -> List[DocumentCategory]:
    return db.query(DocumentCategory).order_by(DocumentCategory.name).offset(skip).limit(limit).all()

def update_document_category(
    db: Session, category_id: int, category_update_data: DocumentCategoryBase
) -> Optional[DocumentCategory]:
    db_category = get_document_category(db, category_id)
    if db_category:
        update_data = category_update_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_category, key, value)
        try:
            db.commit()
            db.refresh(db_category)
        except IntegrityError: # Handles unique name
            db.rollback()
            raise
    return db_category

def delete_document_category(db: Session, category_id: int) -> Optional[DocumentCategory]:
    db_category = get_document_category(db, category_id)
    if db_category:
        # If EmployeeDocuments are linked and the FK is restrictive without ON DELETE SET NULL,
        # this might fail. For now, attempting direct delete.
        # Policy for handling associated documents (e.g., setting their category_id to null)
        # would be implemented here or at the DB schema level.
        db.delete(db_category)
        db.commit()
    return db_category

# --- EmployeeDocument CRUD ---

def create_employee_document(
    db: Session,
    doc_metadata: EmployeeDocumentCreate,
    file_name: str,
    file_path_or_key: str,
    file_type: Optional[str],
    file_size: Optional[int],
    uploaded_by_id: str # User ID from current_user
) -> EmployeeDocument:

    db_employee_doc = EmployeeDocument(
        **doc_metadata.model_dump(), # employee_id, document_category_id, description
        file_name=file_name,
        file_path_or_key=file_path_or_key,
        file_type=file_type,
        file_size=file_size,
        uploaded_by_id=uploaded_by_id,
        uploaded_at=datetime.utcnow() # Explicitly set, though model has server_default
    )
    db.add(db_employee_doc)
    db.commit()
    db.refresh(db_employee_doc)
    return db_employee_doc

def get_employee_document(db: Session, document_id: str) -> Optional[EmployeeDocument]:
    return db.query(EmployeeDocument).filter(EmployeeDocument.id == document_id).first()

def get_employee_documents_for_employee(
    db: Session,
    employee_id: str,
    category_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[EmployeeDocument]:
    query = db.query(EmployeeDocument).filter(EmployeeDocument.employee_id == employee_id)
    if category_id is not None:
        query = query.filter(EmployeeDocument.document_category_id == category_id)
    return query.order_by(EmployeeDocument.uploaded_at.desc()).offset(skip).limit(limit).all()

def update_employee_document(
    db: Session, document_id: str, doc_update_data: EmployeeDocumentUpdate
) -> Optional[EmployeeDocument]:
    db_doc = get_employee_document(db, document_id)
    if db_doc:
        update_data = doc_update_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_doc, key, value)
        # uploaded_at is not typically updated, but if there was an 'updated_at' field for metadata changes:
        # db_doc.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_doc)
    return db_doc

def delete_employee_document(db: Session, document_id: str) -> Optional[EmployeeDocument]:
    db_doc = get_employee_document(db, document_id)
    if db_doc:
        # This only deletes the DB record. Actual file needs separate deletion logic.
        db.delete(db_doc)
        db.commit()
    return db_doc

# Note on `uploaded_at` in `create_employee_document`:
# The model `EmployeeDocument` has `uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)`.
# `func.now()` is intended for database server-side default generation.
# Explicitly setting `uploaded_at=datetime.utcnow()` in the CRUD function ensures the timestamp is set
# by the application, which can be more consistent across different database backends or if using SQLite
# where server-side defaults for dynamic values might behave differently.
# This is generally a safe practice.
# The explicit setting is kept.
# `update_document_category` uses `DocumentCategoryBase` for update data as specified.
# `create_document_category` uses `DocumentCategoryCreate`.
# `create_employee_document` uses `EmployeeDocumentCreate` for metadata.
# `update_employee_document` uses `EmployeeDocumentUpdate`.
# All seem to align with the request.
# For `delete_document_category`, the behavior with existing documents depends on DB schema (ON DELETE SET NULL etc.)
# The current code attempts deletion and will fail if constraints are violated and not handled by DB.
# This is acceptable for a basic CRUD implementation.
# All looks good.The file `db/cruds/employee_documents_crud.py` has been created with the specified CRUD functions.


# **Summary of Implementation:**

# *   **DocumentCategory CRUD**:
#     *   `create_document_category`, `get_document_category`, `get_document_categories`, `update_document_category`, `delete_document_category` are implemented.
#     *   `update_document_category` uses `DocumentCategoryBase` for input data as specified.
#     *   `delete_document_category` attempts direct deletion. The outcome for associated `EmployeeDocument` records (if any) depends on database schema definitions (e.g., `ON DELETE SET NULL` or foreign key constraints).
#     *   Handles `IntegrityError` for unique category names.
# *   **EmployeeDocument CRUD**:
#     *   `create_employee_document`: Takes metadata from `EmployeeDocumentCreate` and separate arguments for file properties (`file_name`, `file_path_or_key`, `file_type`, `file_size`) and `uploaded_by_id`. Explicitly sets `uploaded_at`.
#     *   `get_employee_document`, `get_employee_documents_for_employee` (with category filtering and sorting), `update_employee_document`, `delete_employee_document` are implemented.
#     *   `delete_employee_document` only removes the database record; actual file deletion is noted as an external responsibility.
# *   **Imports**: All necessary modules and models are imported.
# *   **Timestamp Handling**: `uploaded_at` in `create_employee_document` is explicitly set to `datetime.utcnow()`, ensuring application-set timestamps, which is robust.

# The implementation covers all requirements of the subtask, adhering to the specified function signatures and Pydantic models for data input.

# I will now submit the report.
