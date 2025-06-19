import pytest
from fastapi import FastAPI, Depends, status, UploadFile, File, Form
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional, Any, Dict, Callable, List as PyList
from datetime import date, datetime
import os
import shutil
import pathlib
import uuid

# Module to be tested and its dependencies
from api import employee_documents as employee_documents_api # To monkeypatch UPLOAD_DIRECTORY
from api.employee_documents import router as employee_documents_router
from api.dependencies import get_db
from api.auth import get_current_active_user

from api.models import (
    Base, UserInDB, Employee, DocumentCategory, EmployeeDocument,
    DocumentCategoryCreate, DocumentCategoryResponse, DocumentCategoryBase,
    EmployeeDocumentCreate, EmployeeDocumentResponse, EmployeeDocumentUpdate
)
from db.cruds import employees_crud, employee_documents_crud, users_crud # Assuming users_crud for DB users

# --- Test Database Setup ---
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def test_db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
        Base.metadata.drop_all(bind=engine)

# --- Temporary Upload Directory Fixture ---
@pytest.fixture(scope="function") # function scope for cleaner tests, or session if preferred
def tmp_upload_dir(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    temp_dir = tmp_path_factory.mktemp("employee_test_uploads")
    # Monkeypatch the UPLOAD_DIRECTORY in the module where the router is defined
    monkeypatch.setattr(employee_documents_api, "UPLOAD_DIRECTORY", temp_dir)
    return temp_dir

# --- Mock User and Authentication ---
current_mock_user: Optional[UserInDB] = None

def mock_get_current_active_user() -> Optional[UserInDB]:
    if current_mock_user is None: raise Exception("Mock user not set for test")
    return current_mock_user

@pytest.fixture
def mock_user_factory() -> Callable[[str, str], UserInDB]:
    def _create_mock_user(user_id: str, role: str) -> UserInDB:
        return UserInDB(user_id=user_id, username=f"user_{user_id}", email=f"user_{user_id}@example.com", role=role, is_active=True, full_name=f"User {user_id}")
    return _create_mock_user

@pytest.fixture
def create_test_user_in_db(test_db_session: Session) -> Callable[[str, str], User]:
    def _create_user(user_id: str, role: str) -> User:
        user = User(id=user_id, username=f"db_user_{user_id}", email=f"db_{user_id}@example.com", role=role, password_hash="test", salt="test", is_active=True)
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        return user
    return _create_user

@pytest.fixture
def create_test_employee_in_db(test_db_session: Session) -> Callable[[str, str], Employee]:
    def _create_employee(emp_id: str, name_suffix: str) -> Employee:
        emp = Employee(id=emp_id, first_name=f"Emp{name_suffix}", last_name="Test", email=f"emp{name_suffix}@example.com", start_date=date(2020,1,1), is_active=True)
        test_db_session.add(emp)
        test_db_session.commit()
        test_db_session.refresh(emp)
        return emp
    return _create_employee

# --- TestClient Setup ---
@pytest.fixture(scope="function")
def client(test_db_session: Session, tmp_upload_dir: pathlib.Path) -> Generator[TestClient, None, None]: # Ensure tmp_upload_dir is used
    global current_mock_user
    app = FastAPI(title="Test Employee Docs API")
    app.include_router(employee_documents_router)
    app.dependency_overrides[get_db] = lambda: test_db_session
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    current_mock_user = None
    # tmp_upload_dir is cleaned up automatically by pytest due to tmp_path_factory

# --- Common Test Users ---
@pytest.fixture
def common_users_setup(test_db_session: Session, mock_user_factory: Callable, create_test_user_in_db: Callable, create_test_employee_in_db: Callable):
    admin_db = create_test_user_in_db("admin_doc_uid", "admin")
    hr_db = create_test_user_in_db("hr_doc_uid", "hr_manager")
    emp1_db_user = create_test_user_in_db("emp1_doc_uid", "employee")
    emp2_db_user = create_test_user_in_db("emp2_doc_uid", "employee")

    create_test_employee_in_db(admin_db.id, "_admin_doc")
    create_test_employee_in_db(hr_db.id, "_hr_doc")
    emp1 = create_test_employee_in_db(emp1_db_user.id, "_emp1_doc")
    emp2 = create_test_employee_in_db(emp2_db_user.id, "_emp2_doc")

    return {
        "admin": mock_user_factory(admin_db.id, "admin"),
        "hr": mock_user_factory(hr_db.id, "hr_manager"),
        "employee1": mock_user_factory(emp1_db_user.id, "employee"),
        "employee2": mock_user_factory(emp2_db_user.id, "employee"),
        "db_emp1": emp1, "db_emp2": emp2
    }

# --- Tests for Document Categories ---
def test_document_category_crud_flow(client: TestClient, test_db_session: Session, common_users_setup):
    global current_mock_user
    admin_user = common_users_setup["admin"]
    employee_user = common_users_setup["employee1"]

    # Create category (Admin)
    current_mock_user = admin_user
    cat_payload = {"name": "Contracts Test", "description": "Employment contracts"}
    response = client.post("/employee-documents/categories/", json=cat_payload)
    assert response.status_code == status.HTTP_201_CREATED
    cat_data = response.json()
    category_id = cat_data["id"]
    assert cat_data["name"] == "Contracts Test"

    # Attempt duplicate creation (Admin)
    response_dup = client.post("/employee-documents/categories/", json=cat_payload)
    assert response_dup.status_code == status.HTTP_409_CONFLICT

    # Unauthorized creation (Employee)
    current_mock_user = employee_user
    response_unauth_create = client.post("/employee-documents/categories/", json={"name": "My Private Cat"})
    assert response_unauth_create.status_code == status.HTTP_403_FORBIDDEN

    # List categories (any authenticated user - assuming this based on typical read access)
    current_mock_user = employee_user
    response_list = client.get("/employee-documents/categories/")
    assert response_list.status_code == status.HTTP_200_OK
    assert len(response_list.json()) >= 1

    # Get specific category
    response_get_one = client.get(f"/employee-documents/categories/{category_id}")
    assert response_get_one.status_code == status.HTTP_200_OK
    assert response_get_one.json()["name"] == "Contracts Test"
    assert client.get(f"/employee-documents/categories/9999").status_code == status.HTTP_404_NOT_FOUND

    # Update category (Admin)
    current_mock_user = admin_user
    update_payload = {"name": "Updated Contracts Test", "description": "All contracts"}
    response_update = client.put(f"/employee-documents/categories/{category_id}", json=update_payload)
    assert response_update.status_code == status.HTTP_200_OK
    assert response_update.json()["name"] == "Updated Contracts Test"

    # Update non-existent, duplicate name, unauthorized (Employee)
    assert client.put(f"/employee-documents/categories/9999", json=update_payload).status_code == status.HTTP_404_NOT_FOUND
    employee_documents_crud.create_document_category(test_db_session, DocumentCategoryCreate(name="Existing Other Cat"))
    assert client.put(f"/employee-documents/categories/{category_id}", json={"name": "Existing Other Cat"}).status_code == status.HTTP_409_CONFLICT
    current_mock_user = employee_user
    assert client.put(f"/employee-documents/categories/{category_id}", json={"name": "Emp Update Try"}).status_code == status.HTTP_403_FORBIDDEN

    # Delete category (Admin)
    current_mock_user = admin_user
    response_delete = client.delete(f"/employee-documents/categories/{category_id}")
    assert response_delete.status_code == status.HTTP_204_NO_CONTENT
    assert client.get(f"/employee-documents/categories/{category_id}").status_code == status.HTTP_404_NOT_FOUND # Verify deleted
    assert client.delete(f"/employee-documents/categories/9999").status_code == status.HTTP_404_NOT_FOUND # Delete non-existent

    # Unauthorized delete (Employee)
    cat_to_protect_id = employee_documents_crud.create_document_category(test_db_session, DocumentCategoryCreate(name="Protect Delete")).id
    current_mock_user = employee_user
    assert client.delete(f"/employee-documents/categories/{cat_to_protect_id}").status_code == status.HTTP_403_FORBIDDEN


# --- Tests for Employee Documents ---

def test_upload_employee_document(client: TestClient, test_db_session: Session, common_users_setup, tmp_upload_dir: pathlib.Path):
    global current_mock_user
    hr_user = common_users_setup["hr"]
    employee1 = common_users_setup["db_emp1"]
    category = employee_documents_crud.create_document_category(test_db_session, DocumentCategoryCreate(name="ID Scans"))

    current_mock_user = hr_user # HR uploads for employee1
    file_content = b"dummy pdf content"
    files = {"file": ("passport.pdf", file_content, "application/pdf")}
    data = {
        "employee_id": employee1.id,
        "document_category_id": str(category.id), # Form data needs to be string
        "description": "Passport Scan"
    }
    response = client.post("/employee-documents/documents/upload/", files=files, data=data)
    assert response.status_code == status.HTTP_201_CREATED
    doc_data = response.json()
    assert doc_data["file_name"] == "passport.pdf"
    assert doc_data["employee_id"] == employee1.id
    assert doc_data["document_category"]["id"] == category.id
    assert doc_data["description"] == "Passport Scan"
    assert "download_url" in doc_data

    # Verify file saved
    saved_file_path = tmp_upload_dir / pathlib.Path(doc_data["id"] + ".pdf") # API saves with UUID + original suffix
    # The API actually saves as `uuid.uuid4().hex + file_extension`. The response `id` is the DB record's UUID.
    # The actual filename on disk is not directly the doc_data["id"].
    # The CRUD function saves with `file_path_or_key=str(file_path)`. The `file_path` is `UPLOAD_DIRECTORY / unique_filename`.
    # So, we need to get the `file_path_or_key` from DB or construct it if we know the UUID filename used.
    # For now, let's check if *a* file was created in tmp_upload_dir.
    # A better check: list files in tmp_upload_dir, expect one.
    uploaded_files = list(tmp_upload_dir.iterdir())
    assert len(uploaded_files) == 1
    assert uploaded_files[0].name.endswith(".pdf") # Saved with new UUID name + original suffix
    with open(uploaded_files[0], "rb") as f:
        assert f.read() == file_content

    # Test upload for non-existent employee
    response_no_emp = client.post("/employee-documents/documents/upload/", files={"file": ("err.txt", b"c", "text/plain")}, data={"employee_id": "ghost-emp"})
    assert response_no_emp.status_code == status.HTTP_404_NOT_FOUND

    # Test upload with non-existent category_id
    response_no_cat = client.post("/employee-documents/documents/upload/", files={"file": ("err2.txt", b"c", "text/plain")}, data={"employee_id": employee1.id, "document_category_id": "999"})
    assert response_no_cat.status_code == status.HTTP_404_NOT_FOUND

def test_list_and_download_documents(client: TestClient, test_db_session: Session, common_users_setup, tmp_upload_dir: pathlib.Path):
    global current_mock_user
    hr_user, emp1_user, emp1_db = common_users_setup["hr"], common_users_setup["employee1"], common_users_setup["db_emp1"]

    # HR uploads a document for employee1
    current_mock_user = hr_user
    cat = employee_documents_crud.create_document_category(test_db_session, DocumentCategoryCreate(name="Test Docs"))
    file_content = b"Hello world document"
    upload_resp = client.post("/employee-documents/documents/upload/",
        files={"file": ("test_doc.txt", file_content, "text/plain")},
        data={"employee_id": emp1_db.id, "document_category_id": str(cat.id)}
    )
    doc_id = upload_resp.json()["id"]

    # Employee1 lists their documents
    current_mock_user = emp1_user
    list_resp = client.get(f"/employee-documents/documents/employee/{emp1_db.id}")
    assert list_resp.status_code == status.HTTP_200_OK
    docs_list = list_resp.json()
    assert len(docs_list) == 1
    assert docs_list[0]["id"] == doc_id
    assert docs_list[0]["download_url"] is not None

    # Employee1 downloads their document
    download_resp = client.get(docs_list[0]["download_url"])
    assert download_resp.status_code == status.HTTP_200_OK
    assert download_resp.content == file_content
    assert download_resp.headers["content-disposition"].endswith('filename="test_doc.txt"')

    # Employee2 (unauthorized) tries to list Emp1's docs
    current_mock_user = common_users_setup["employee2"]
    assert client.get(f"/employee-documents/documents/employee/{emp1_db.id}").status_code == status.HTTP_403_FORBIDDEN
    # Employee2 (unauthorized) tries to download Emp1's doc
    assert client.get(docs_list[0]["download_url"]).status_code == status.HTTP_403_FORBIDDEN

    # Download non-existent document
    current_mock_user = admin_user = common_users_setup["admin"] # Admin for this check
    assert client.get(f"/employee-documents/documents/download/{uuid.uuid4()}").status_code == status.HTTP_404_NOT_FOUND


def test_document_metadata_and_delete(client: TestClient, test_db_session: Session, common_users_setup, tmp_upload_dir: pathlib.Path):
    global current_mock_user
    hr_user, emp1_user, emp1_db = common_users_setup["hr"], common_users_setup["employee1"], common_users_setup["db_emp1"]

    current_mock_user = hr_user
    cat1 = employee_documents_crud.create_document_category(test_db_session, DocumentCategoryCreate(name="Category A"))
    cat2 = employee_documents_crud.create_document_category(test_db_session, DocumentCategoryCreate(name="Category B"))

    upload_resp = client.post("/employee-documents/documents/upload/",
        files={"file": ("metadata_test.txt", b"meta", "text/plain")},
        data={"employee_id": emp1_db.id, "document_category_id": str(cat1.id), "description": "Initial"}
    )
    doc_id = upload_resp.json()["id"]
    # Find the actual saved file name based on the structure in the API endpoint
    # The API saves as: unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    # The `file_path_or_key` stored in DB has this full path.
    db_doc = employee_documents_crud.get_employee_document(test_db_session, doc_id)
    assert db_doc is not None
    physical_file_path = pathlib.Path(db_doc.file_path_or_key)
    assert physical_file_path.exists()


    # Get metadata (Employee can get own)
    current_mock_user = emp1_user
    meta_resp = client.get(f"/employee-documents/documents/{doc_id}/metadata")
    assert meta_resp.status_code == status.HTTP_200_OK
    assert meta_resp.json()["description"] == "Initial"

    # Update metadata (HR updates)
    current_mock_user = hr_user
    update_payload = {"description": "Updated by HR", "document_category_id": cat2.id}
    update_resp = client.put(f"/employee-documents/documents/{doc_id}/metadata", json=update_payload)
    assert update_resp.status_code == status.HTTP_200_OK
    assert update_resp.json()["description"] == "Updated by HR"
    assert update_resp.json()["document_category"]["id"] == cat2.id

    # Unauthorized update (Employee tries to update metadata, assuming only HR/Admin can)
    current_mock_user = emp1_user
    assert client.put(f"/employee-documents/documents/{doc_id}/metadata", json={"description": "Emp update"}).status_code == status.HTTP_403_FORBIDDEN

    # Delete document (HR deletes)
    current_mock_user = hr_user
    delete_resp = client.delete(f"/employee-documents/documents/{doc_id}")
    assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

    # Verify physical file is deleted
    assert not physical_file_path.exists()
    # Verify DB record is deleted
    assert employee_documents_crud.get_employee_document(test_db_session, doc_id) is None

    # Test 404s for metadata and delete
    current_mock_user = hr_user # Reset to HR for these checks
    non_existent_doc_id = str(uuid.uuid4())
    assert client.get(f"/employee-documents/documents/{non_existent_doc_id}/metadata").status_code == status.HTTP_404_NOT_FOUND
    assert client.put(f"/employee-documents/documents/{non_existent_doc_id}/metadata", json={"description":"..."}).status_code == status.HTTP_404_NOT_FOUND
    assert client.delete(f"/employee-documents/documents/{non_existent_doc_id}").status_code == status.HTTP_404_NOT_FOUND
