import pytest
from fastapi import FastAPI, Depends, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional, Any, Dict, Callable, List as PyList
from datetime import date, datetime

# Adjust these imports based on your project structure
from api.models import (
    Base, UserInDB, Employee,
    Goal, GoalCreate, GoalResponse, GoalUpdate, GoalStatusEnum,
    ReviewCycle, ReviewCycleCreate, ReviewCycleResponse, ReviewCycleUpdate,
    PerformanceReview, PerformanceReviewCreate, PerformanceReviewResponse, PerformanceReviewUpdate, PerformanceReviewStatusEnum,
    performance_review_goals_link
)
from api.performance import router as performance_router
from api.dependencies import get_db
from api.auth import get_current_active_user

from db.cruds import employees_crud, performance_crud, users_crud # Added users_crud

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

# --- Mock User and Authentication ---
current_mock_user: Optional[UserInDB] = None

def mock_get_current_active_user() -> Optional[UserInDB]:
    if current_mock_user is None:
        raise Exception("Mock user not set for test")
    return current_mock_user

@pytest.fixture
def mock_user_factory() -> Callable[[str, str, Optional[str]], UserInDB]:
    def _create_mock_user(user_id: str, role: str, email_suffix: Optional[str] = None) -> UserInDB:
        email = f"user_{user_id}{'_' + email_suffix if email_suffix else ''}@example.com"
        return UserInDB(user_id=user_id, username=f"user_{user_id}", email=email, role=role, is_active=True, full_name=f"User {user_id}")
    return _create_mock_user

@pytest.fixture
def create_test_user_in_db(test_db_session: Session) -> Callable[[str, str, Optional[str]], User]:
    def _create_user(user_id: str, role: str, username_suffix: str = "") -> User:
        # Use users_crud if available and fits, else direct model.
        # Assuming UserCreate Pydantic model for users_crud if it exists
        # For now, direct User model creation for simplicity in this test setup.
        user = User(
            id=user_id, username=f"db_user_{user_id}{username_suffix}",
            email=f"db_user_{user_id}{username_suffix}@example.com", role=role,
            password_hash="test_hash", salt="test_salt", is_active=True
        )
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        return user
    return _create_user

# --- TestClient Setup ---
@pytest.fixture(scope="function")
def client(test_db_session: Session) -> Generator[TestClient, None, None]:
    global current_mock_user
    app = FastAPI()
    app.include_router(performance_router)
    app.dependency_overrides[get_db] = lambda: test_db_session
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    current_mock_user = None

# --- Helper Functions for Test Data ---
def create_test_employee(db: Session, user_id: str, first_name: str, last_name: str, email_suffix: str) -> Employee:
    employee = Employee(id=user_id, first_name=first_name, last_name=last_name, email=f"{user_id}{email_suffix}@example.com", start_date=date(2020,1,1), is_active=True)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee

@pytest.fixture
def common_users(test_db_session: Session, mock_user_factory: Callable, create_test_user_in_db: Callable):
    db_admin_user = create_test_user_in_db("admin_uid", "admin", "_comm")
    db_hr_user = create_test_user_in_db("hr_uid", "hr_manager", "_comm")
    db_manager_user = create_test_user_in_db("mgr_uid", "manager", "_comm")
    db_emp_user = create_test_user_in_db("emp1_uid", "employee", "_comm_e1")
    db_emp2_user = create_test_user_in_db("emp2_uid", "employee", "_comm_e2")

    admin_emp = create_test_employee(test_db_session, db_admin_user.id, "Admin", "Global", "_comm_admin")
    hr_emp = create_test_employee(test_db_session, db_hr_user.id, "HR", "Global", "_comm_hr")
    manager_emp = create_test_employee(test_db_session, db_manager_user.id, "Manager", "Leads", "_comm_mgr")
    emp = create_test_employee(test_db_session, db_emp_user.id, "Employee", "One", "_common_e1")
    emp2 = create_test_employee(test_db_session, db_emp2_user.id, "Employee", "Two", "_common_e2")

    return {
        "admin": mock_user_factory(db_admin_user.id, "admin"),
        "hr": mock_user_factory(db_hr_user.id, "hr_manager"),
        "manager": mock_user_factory(db_manager_user.id, "manager"),
        "employee": mock_user_factory(db_emp_user.id, "employee"),
        "employee2": mock_user_factory(db_emp2_user.id, "employee"),
        "db_admin_user": db_admin_user, "db_hr_user": db_hr_user,
        "db_manager_user": db_manager_user, "db_emp_user": db_emp_user, "db_emp2_user": db_emp2_user,
        "admin_emp": admin_emp, "hr_emp": hr_emp, "manager_emp": manager_emp,
        "emp": emp, "emp2": emp2
    }

# --- Tests for Goals Endpoints ---

def test_create_goal_endpoint(client: TestClient, test_db_session: Session, common_users):
    global current_mock_user
    current_mock_user = common_users["manager"]
    goal_payload = {"employee_id": common_users["emp"].id, "title": "New Goal for Emp1"}
    response = client.post("/performance/goals/", json=goal_payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["employee_id"] == common_users["emp"].id
    assert data["set_by_id"] == common_users["manager"].user_id

    current_mock_user = common_users["employee"]
    goal_payload_self = {"employee_id": common_users["employee"].user_id, "title": "My Goal"}
    response_self = client.post("/performance/goals/", json=goal_payload_self)
    assert response_self.status_code == status.HTTP_201_CREATED
    assert response_self.json()["set_by_id"] == common_users["employee"].user_id

    current_mock_user = common_users["admin"]
    response_ghost = client.post("/performance/goals/", json={"employee_id": "ghost-emp", "title": "Ghost Goal"})
    assert response_ghost.status_code == status.HTTP_404_NOT_FOUND

    current_mock_user = common_users["employee"]
    response_unauth_set_by = client.post("/performance/goals/", json={
        "employee_id": common_users["employee2"].id,
        "title": "Goal for Emp2",
        "set_by_id": common_users["manager"].user_id # Emp1 tries to set goal for Emp2 as if they are manager
    })
    assert response_unauth_set_by.status_code == status.HTTP_403_FORBIDDEN


def test_read_employee_goals_endpoint(client: TestClient, test_db_session: Session, common_users):
    global current_mock_user
    manager, emp, emp2 = common_users["manager"], common_users["emp"], common_users["employee2"]
    performance_crud.create_goal(test_db_session, GoalCreate(employee_id=emp.id, title="Emp1 Goal1"), manager.user_id)
    performance_crud.create_goal(test_db_session, GoalCreate(employee_id=emp.id, title="Emp1 Goal2", status=GoalStatusEnum.COMPLETED.value), manager.user_id)

    current_mock_user = common_users["employee"] # Emp1
    response = client.get(f"/performance/goals/employee/{emp.id}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2

    current_mock_user = manager
    response_mgr_filter = client.get(f"/performance/goals/employee/{emp.id}?status_filter=completed")
    assert response_mgr_filter.status_code == status.HTTP_200_OK
    assert len(response_mgr_filter.json()) == 1

    current_mock_user = emp2
    response_unauth = client.get(f"/performance/goals/employee/{emp.id}")
    assert response_unauth.status_code == status.HTTP_403_FORBIDDEN

def test_read_goal_endpoint(client: TestClient, test_db_session: Session, common_users):
    global current_mock_user
    manager, emp, emp2 = common_users["manager"], common_users["emp"], common_users["employee2"]
    goal = performance_crud.create_goal(test_db_session, GoalCreate(employee_id=emp.id, title="Specific Goal"), manager.user_id)

    # Owner, setter (manager), HR can read
    current_mock_user = emp; assert client.get(f"/performance/goals/{goal.id}").status_code == status.HTTP_200_OK
    current_mock_user = manager; assert client.get(f"/performance/goals/{goal.id}").status_code == status.HTTP_200_OK
    current_mock_user = common_users["hr"]; assert client.get(f"/performance/goals/{goal.id}").status_code == status.HTTP_200_OK

    # Unauthorized employee
    current_mock_user = emp2
    assert client.get(f"/performance/goals/{goal.id}").status_code == status.HTTP_403_FORBIDDEN

    # Not found
    current_mock_user = common_users["admin"]
    assert client.get("/performance/goals/9999").status_code == status.HTTP_404_NOT_FOUND

def test_update_goal_endpoint(client: TestClient, test_db_session: Session, common_users):
    global current_mock_user
    manager, emp, emp2 = common_users["manager"], common_users["emp"], common_users["employee2"]
    goal = performance_crud.create_goal(test_db_session, GoalCreate(employee_id=emp.id, title="Original Goal Title"), manager.user_id)
    update_payload = {"title": "Updated Goal Title", "status": "in_progress"}

    # Owner (employee) updates
    current_mock_user = emp
    response_owner = client.put(f"/performance/goals/{goal.id}", json=update_payload)
    assert response_owner.status_code == status.HTTP_200_OK
    assert response_owner.json()["title"] == "Updated Goal Title"
    assert response_owner.json()["status"] == "in_progress"

    # Setter (manager) updates
    current_mock_user = manager
    response_setter = client.put(f"/performance/goals/{goal.id}", json={"description": "Manager updated desc"})
    assert response_setter.status_code == status.HTTP_200_OK
    assert response_setter.json()["description"] == "Manager updated desc"

    # Unauthorized update
    current_mock_user = emp2
    response_unauth = client.put(f"/performance/goals/{goal.id}", json={"title": "Attempted Hack"})
    assert response_unauth.status_code == status.HTTP_403_FORBIDDEN

    # Update non-existent
    current_mock_user = manager
    response_404 = client.put("/performance/goals/9999", json=update_payload)
    assert response_404.status_code == status.HTTP_404_NOT_FOUND

    # Invalid status string
    response_invalid_status = client.put(f"/performance/goals/{goal.id}", json={"status": "invalid_enum_value"})
    assert response_invalid_status.status_code == status.HTTP_400_BAD_REQUEST # API validates status string

def test_delete_goal_endpoint(client: TestClient, test_db_session: Session, common_users):
    global current_mock_user
    manager, emp, emp2 = common_users["manager"], common_users["emp"], common_users["employee2"]
    goal_to_delete_by_mgr = performance_crud.create_goal(test_db_session, GoalCreate(employee_id=emp.id, title="Mgr Deletes This"), manager.user_id)
    goal_to_delete_by_emp = performance_crud.create_goal(test_db_session, GoalCreate(employee_id=emp.id, title="Emp Deletes This"), manager.user_id)

    # Manager deletes
    current_mock_user = manager
    response_mgr_del = client.delete(f"/performance/goals/{goal_to_delete_by_mgr.id}")
    assert response_mgr_del.status_code == status.HTTP_204_NO_CONTENT

    # Employee (owner) deletes
    current_mock_user = emp
    response_emp_del = client.delete(f"/performance/goals/{goal_to_delete_by_emp.id}")
    assert response_emp_del.status_code == status.HTTP_204_NO_CONTENT

    # Unauthorized delete
    goal_unauth_del = performance_crud.create_goal(test_db_session, GoalCreate(employee_id=emp.id, title="Cannot Delete"), manager.user_id)
    current_mock_user = emp2
    response_unauth = client.delete(f"/performance/goals/{goal_unauth_del.id}")
    assert response_unauth.status_code == status.HTTP_403_FORBIDDEN

    # Delete non-existent
    current_mock_user = common_users["admin"]
    response_404 = client.delete("/performance/goals/9999")
    assert response_404.status_code == status.HTTP_404_NOT_FOUND


# --- Tests for Review Cycles Endpoints ---

def test_review_cycle_crud_endpoints(client: TestClient, test_db_session: Session, common_users):
    global current_mock_user
    admin, hr, employee = common_users["admin"], common_users["hr"], common_users["employee"]

    # POST (Create)
    current_mock_user = admin
    rc_payload1 = {"name": "Annual 2024", "start_date": "2024-01-01", "end_date": "2024-12-31"}
    response_create1 = client.post("/performance/review-cycles/", json=rc_payload1)
    assert response_create1.status_code == status.HTTP_201_CREATED
    rc1_id = response_create1.json()["id"]

    current_mock_user = hr # HR can also create
    rc_payload2 = {"name": "Mid-Year 2024", "start_date": "2024-06-01", "end_date": "2024-06-30", "is_active": False}
    client.post("/performance/review-cycles/", json=rc_payload2)

    response_create_dup = client.post("/performance/review-cycles/", json=rc_payload1) # Duplicate name
    assert response_create_dup.status_code == status.HTTP_409_CONFLICT

    current_mock_user = employee # Unauthorized creation
    response_create_unauth = client.post("/performance/review-cycles/", json={"name": "Emp Cycle", "start_date": "2024-01-01", "end_date": "2024-01-15"})
    assert response_create_unauth.status_code == status.HTTP_403_FORBIDDEN

    # GET List (assumed public or minimally restricted for GET)
    current_mock_user = employee # Any authenticated user can list
    response_list = client.get("/performance/review-cycles/")
    assert response_list.status_code == status.HTTP_200_OK
    assert len(response_list.json()) == 2

    response_list_active = client.get("/performance/review-cycles/?is_active=true")
    assert len(response_list_active.json()) == 1
    assert response_list_active.json()[0]["name"] == "Annual 2024"

    # GET One
    response_get_one = client.get(f"/performance/review-cycles/{rc1_id}")
    assert response_get_one.status_code == status.HTTP_200_OK
    assert response_get_one.json()["name"] == "Annual 2024"
    assert client.get("/performance/review-cycles/999").status_code == status.HTTP_404_NOT_FOUND

    # PUT (Update)
    current_mock_user = admin
    update_payload = {"name": "Annual 2024 Updated", "is_active": False}
    response_update = client.put(f"/performance/review-cycles/{rc1_id}", json=update_payload)
    assert response_update.status_code == status.HTTP_200_OK
    assert response_update.json()["name"] == "Annual 2024 Updated"
    assert response_update.json()["is_active"] is False

    response_update_dup = client.put(f"/performance/review-cycles/{rc1_id}", json={"name": "Mid-Year 2024"})
    assert response_update_dup.status_code == status.HTTP_409_CONFLICT
    assert client.put("/performance/review-cycles/999", json=update_payload).status_code == status.HTTP_404_NOT_FOUND

    current_mock_user = employee # Unauthorized update
    assert client.put(f"/performance/review-cycles/{rc1_id}", json={"name": "Emp Update Attempt"}).status_code == status.HTTP_403_FORBIDDEN

    # DELETE
    current_mock_user = admin
    assert client.delete(f"/performance/review-cycles/{rc1_id}").status_code == status.HTTP_204_NO_CONTENT
    assert client.delete("/performance/review-cycles/999").status_code == status.HTTP_404_NOT_FOUND

    current_mock_user = employee # Unauthorized delete
    rc2_id = client.get("/performance/review-cycles/").json()[0]["id"] # Get remaining one
    assert client.delete(f"/performance/review-cycles/{rc2_id}").status_code == status.HTTP_403_FORBIDDEN


# --- Tests for Performance Reviews Endpoints ---

@pytest.fixture
def setup_review_data(test_db_session: Session, common_users):
    manager = common_users["manager"]
    emp = common_users["emp"]
    admin = common_users["admin"] # For cycle creation

    global current_mock_user # To allow cycle creation by admin
    current_mock_user = admin
    rc_resp = client(test_db_session).post("/performance/review-cycles/", json={"name": "Q2 PR Cycle", "start_date": "2024-04-01", "end_date": "2024-06-30"})
    rc = rc_resp.json()

    current_mock_user = manager # Manager creates goals and review
    goal1 = performance_crud.create_goal(test_db_session, GoalCreate(employee_id=emp.id, title="PR Test Goal 1"), manager.user_id)
    goal2 = performance_crud.create_goal(test_db_session, GoalCreate(employee_id=emp.id, title="PR Test Goal 2"), manager.user_id)

    return {"manager": manager, "employee": emp, "admin": admin, "review_cycle": rc, "goal1": GoalResponse(**goal1.as_dict()), "goal2": GoalResponse(**goal2.as_dict())}


def test_create_performance_review_endpoint(client: TestClient, test_db_session: Session, common_users, setup_review_data):
    global current_mock_user
    manager, emp, admin, rc = common_users["manager"], common_users["emp"], common_users["admin"], setup_review_data["review_cycle"]

    current_mock_user = manager
    pr_payload = {"employee_id": emp.id, "reviewer_id": manager.user_id, "review_cycle_id": rc["id"]}
    response = client.post("/performance/reviews/", json=pr_payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["employee_id"] == emp.id
    assert data["reviewer_id"] == manager.user_id
    assert data["status"] == PerformanceReviewStatusEnum.DRAFT.value

    # Unauthorized (employee tries to create for self)
    current_mock_user = emp
    response_unauth = client.post("/performance/reviews/", json=pr_payload)
    assert response_unauth.status_code == status.HTTP_403_FORBIDDEN

    # Non-existent employee
    current_mock_user = manager
    response_no_emp = client.post("/performance/reviews/", json={**pr_payload, "employee_id": "ghost_emp_pr"})
    assert response_no_emp.status_code == status.HTTP_404_NOT_FOUND

    # Non-existent cycle
    response_no_cycle = client.post("/performance/reviews/", json={**pr_payload, "review_cycle_id": 9998})
    assert response_no_cycle.status_code == status.HTTP_404_NOT_FOUND # API checks cycle existence

def test_read_reviews_employee_and_reviewer(client: TestClient, test_db_session: Session, common_users, setup_review_data):
    global current_mock_user
    manager, emp, emp2, rc = common_users["manager"], common_users["emp"], common_users["employee2"], setup_review_data["review_cycle"]

    # Manager creates review for emp
    current_mock_user = manager
    pr_resp = client.post("/performance/reviews/", json={"employee_id": emp.id, "reviewer_id": manager.user_id, "review_cycle_id": rc["id"]})
    pr_id = pr_resp.json()["id"]

    # Employee reads their own reviews
    current_mock_user = emp
    response_emp = client.get(f"/performance/reviews/employee/{emp.id}")
    assert response_emp.status_code == status.HTTP_200_OK
    assert len(response_emp.json()) == 1
    assert response_emp.json()[0]["id"] == pr_id

    # Manager reads reviews they manage (as reviewer)
    current_mock_user = manager
    response_mgr_me = client.get("/performance/reviews/reviewer/me")
    assert response_mgr_me.status_code == status.HTTP_200_OK
    assert len(response_mgr_me.json()) == 1
    assert response_mgr_me.json()[0]["id"] == pr_id

    # Test cycle_id filter for reviewer/me
    response_mgr_me_cycle = client.get(f"/performance/reviews/reviewer/me?cycle_id={rc['id']}")
    assert len(response_mgr_me_cycle.json()) == 1
    response_mgr_me_wrong_cycle = client.get(f"/performance/reviews/reviewer/me?cycle_id=999") # Non-existent cycle
    assert len(response_mgr_me_wrong_cycle.json()) == 0


    # Emp2 (unauthorized) tries to read Emp1's reviews
    current_mock_user = emp2
    response_unauth = client.get(f"/performance/reviews/employee/{emp.id}")
    assert response_unauth.status_code == status.HTTP_403_FORBIDDEN

def test_read_specific_performance_review(client: TestClient, test_db_session: Session, common_users, setup_review_data):
    global current_mock_user
    manager, emp, emp2, hr, rc = common_users["manager"], common_users["emp"], common_users["employee2"], common_users["hr"], setup_review_data["review_cycle"]

    current_mock_user = manager
    pr_resp = client.post("/performance/reviews/", json={"employee_id": emp.id, "reviewer_id": manager.user_id, "review_cycle_id": rc["id"]})
    pr_id = pr_resp.json()["id"]

    # Employee (subject of review)
    current_mock_user = emp; assert client.get(f"/performance/reviews/{pr_id}").status_code == status.HTTP_200_OK
    # Reviewer (manager)
    current_mock_user = manager; assert client.get(f"/performance/reviews/{pr_id}").status_code == status.HTTP_200_OK
    # HR
    current_mock_user = hr; assert client.get(f"/performance/reviews/{pr_id}").status_code == status.HTTP_200_OK
    # Other employee (unauthorized)
    current_mock_user = emp2; assert client.get(f"/performance/reviews/{pr_id}").status_code == status.HTTP_403_FORBIDDEN
    # Not found
    current_mock_user = common_users["admin"]; assert client.get("/performance/reviews/9999").status_code == status.HTTP_404_NOT_FOUND

def test_update_performance_review_fields_and_goals(client: TestClient, test_db_session: Session, common_users, setup_review_data):
    global current_mock_user
    manager, emp, emp2, hr, rc, goal1, goal2 = common_users["manager"], common_users["emp"], common_users["employee2"], common_users["hr"], setup_review_data["review_cycle"], setup_review_data["goal1"], setup_review_data["goal2"]

    current_mock_user = manager
    pr_resp = client.post("/performance/reviews/", json={"employee_id": emp.id, "reviewer_id": manager.user_id, "review_cycle_id": rc["id"]})
    pr_id = pr_resp.json()["id"]

    # Manager updates manager_comments, rating, status, and links goals
    update_payload_mgr = {
        "manager_comments": "Good progress by manager.", "overall_rating": 4, "status": "pending_final_discussion",
        "goal_ids_to_link": [goal1.id, goal2.id]
    }
    response_mgr_update = client.put(f"/performance/reviews/{pr_id}", json=update_payload_mgr)
    assert response_mgr_update.status_code == status.HTTP_200_OK
    data = response_mgr_update.json()
    assert data["manager_comments"] == "Good progress by manager."
    assert data["overall_rating"] == 4
    assert data["status"] == "pending_final_discussion"
    assert len(data["goals_reviewed"]) == 2

    # Employee updates employee_comments (assuming review is in a state that allows this, e.g. PENDING_EMPLOYEE_INPUT)
    # Need to set review to PENDING_EMPLOYEE_INPUT first by manager/HR for this test
    current_mock_user = manager
    client.put(f"/performance/reviews/{pr_id}", json={"status": PerformanceReviewStatusEnum.PENDING_EMPLOYEE_INPUT.value})

    current_mock_user = emp
    update_payload_emp = {"employee_comments": "My thoughts."}
    response_emp_update = client.put(f"/performance/reviews/{pr_id}", json=update_payload_emp)
    assert response_emp_update.status_code == status.HTTP_200_OK
    assert response_emp_update.json()["employee_comments"] == "My thoughts."

    # Employee tries to update manager_comments (unauthorized field)
    update_payload_emp_unauth_field = {"manager_comments": "Employee trying to set manager comments."}
    response_emp_unauth_field = client.put(f"/performance/reviews/{pr_id}", json=update_payload_emp_unauth_field)
    assert response_emp_unauth_field.status_code == status.HTTP_403_FORBIDDEN

    # Link non-existent goal
    current_mock_user = manager
    response_link_bad_goal = client.put(f"/performance/reviews/{pr_id}", json={"goal_ids_to_link": [9999]})
    assert response_link_bad_goal.status_code == status.HTTP_404_NOT_FOUND # API checks goal existence

    # Invalid status string
    response_invalid_status = client.put(f"/performance/reviews/{pr_id}", json={"status": "weird_status"})
    assert response_invalid_status.status_code == status.HTTP_400_BAD_REQUEST

def test_delete_performance_review_endpoint(client: TestClient, test_db_session: Session, common_users, setup_review_data):
    global current_mock_user
    manager, emp, hr, rc = common_users["manager"], common_users["emp"], common_users["hr"], setup_review_data["review_cycle"]

    current_mock_user = manager
    pr_resp = client.post("/performance/reviews/", json={"employee_id": emp.id, "reviewer_id": manager.user_id, "review_cycle_id": rc["id"]})
    pr_id = pr_resp.json()["id"]

    # HR deletes
    current_mock_user = hr
    response_del = client.delete(f"/performance/reviews/{pr_id}")
    assert response_del.status_code == status.HTTP_204_NO_CONTENT

    # Verify deleted
    assert client.get(f"/performance/reviews/{pr_id}").status_code == status.HTTP_404_NOT_FOUND

    # Unauthorized delete (e.g., by manager if only HR/Admin can delete)
    # Assuming manager cannot delete, only HR/Admin as per prompt for DELETE.
    # Let's create another one for this test.
    current_mock_user = manager
    pr2_resp = client.post("/performance/reviews/", json={"employee_id": emp.id, "reviewer_id": manager.user_id, "review_cycle_id": rc["id"]})
    pr2_id = pr2_resp.json()["id"]
    current_mock_user = manager # Manager tries to delete
    response_del_unauth = client.delete(f"/performance/reviews/{pr2_id}")
    assert response_del_unauth.status_code == status.HTTP_403_FORBIDDEN # Based on API's check_admin_hr_permission

    # Delete non-existent
    current_mock_user = hr
    assert client.delete("/performance/reviews/9999").status_code == status.HTTP_404_NOT_FOUND
