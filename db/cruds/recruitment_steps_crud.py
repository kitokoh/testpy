import sqlite3
import uuid
from datetime import datetime # Though not directly used in timestamps for this table
from db.connection import get_db_connection

# TODO: Validate job_opening_id - ensure it exists in JobOpenings table.

def add_recruitment_step(step_data: dict) -> str | None:
    """
    Adds a new recruitment step for a job opening.
    Expected keys: 'job_opening_id', 'step_name', 'step_order', 'description'.
    Returns the new recruitment_step_id (UUID string) or None if an error occurs.
    """
    recruitment_step_id = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO RecruitmentSteps (
                recruitment_step_id, job_opening_id, step_name, step_order, description
            ) VALUES (?, ?, ?, ?, ?)
        """
        cursor.execute(query, (
            recruitment_step_id,
            step_data.get('job_opening_id'),
            step_data.get('step_name'),
            step_data.get('step_order'),
            step_data.get('description')
        ))
        conn.commit()
        return recruitment_step_id
    except sqlite3.Error as e:
        # UNIQUE constraint (job_opening_id, step_order) or (job_opening_id, step_name) might be violated
        print(f"Database error in add_recruitment_step: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_recruitment_step_by_id(recruitment_step_id: str) -> dict | None:
    """
    Retrieves a recruitment step by its ID.
    """
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM RecruitmentSteps WHERE recruitment_step_id = ?"
        cursor.execute(query, (recruitment_step_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_recruitment_step_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_recruitment_steps_for_job_opening(job_opening_id: str, order_by: str = "step_order ASC") -> list[dict]:
    """
    Retrieves all recruitment steps for a specific job opening, ordered by step_order.
    order_by: a string like "step_order ASC" or "step_name DESC"
    """
    conn = get_db_connection()
    steps_list = []
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Basic validation for order_by to prevent injection on column name
        allowed_order_columns = ["step_order", "step_name"]
        order_column_name = order_by.split(" ")[0]
        if order_column_name not in allowed_order_columns:
            order_by_clause = "step_order ASC" # Default ordering
        else:
            order_by_clause = order_by


        query = f"SELECT * FROM RecruitmentSteps WHERE job_opening_id = ? ORDER BY {order_by_clause}"
        cursor.execute(query, (job_opening_id,))
        rows = cursor.fetchall()
        for row in rows:
            steps_list.append(dict(row))
        return steps_list
    except sqlite3.Error as e:
        print(f"Database error in get_recruitment_steps_for_job_opening: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_recruitment_step(recruitment_step_id: str, update_data: dict) -> bool:
    """
    Updates an existing recruitment step.
    Allowed fields in update_data: 'step_name', 'step_order', 'description'.
    job_opening_id is generally not updated for a step; a new step would be created.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        update_fields = []
        params = []

        allowed_fields = ['step_name', 'step_order', 'description']

        for key, value in update_data.items():
            if key in allowed_fields:
                update_fields.append(f"{key} = ?")
                params.append(value)

        if not update_fields:
            print("No valid fields provided for update in update_recruitment_step.")
            return False

        query = f"UPDATE RecruitmentSteps SET {', '.join(update_fields)} WHERE recruitment_step_id = ?"
        params.append(recruitment_step_id)

        cursor.execute(query, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        # UNIQUE constraint might be violated if changing step_order or step_name to an existing one for the same job_opening_id
        print(f"Database error in update_recruitment_step: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_recruitment_step(recruitment_step_id: str) -> bool:
    """
    Deletes a recruitment step.
    (Note: CandidateProgress and Interviews referencing this step might be affected by ON DELETE CASCADE)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # ON DELETE CASCADE in CandidateProgress and Interviews for recruitment_step_id will handle children.
        query = "DELETE FROM RecruitmentSteps WHERE recruitment_step_id = ?"
        cursor.execute(query, (recruitment_step_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_recruitment_step: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("Running example usage for recruitment_steps_crud.py")
    # Dependency: A JobOpening needs to exist.
    # We'll use a dummy job_opening_id for this example.
    # In real tests, create one using recruitment_job_openings_crud.py.

    _dummy_job_opening_id_for_steps = str(uuid.uuid4()) # Assume this job opening exists

    # 1. Add Recruitment Step
    step1_data = {
        'job_opening_id': _dummy_job_opening_id_for_steps,
        'step_name': 'Application Review',
        'step_order': 1,
        'description': 'Initial screening of applications.'
    }
    print(f"\nAttempting to add recruitment step: {step1_data.get('step_name')}")
    new_step1_id = add_recruitment_step(step1_data)

    if new_step1_id:
        print(f"Recruitment Step '{step1_data.get('step_name')}' added with ID: {new_step1_id}")

        # Add a second step
        step2_data = {
            'job_opening_id': _dummy_job_opening_id_for_steps,
            'step_name': 'Phone Screen',
            'step_order': 2,
            'description': 'First call with the candidate.'
        }
        print(f"\nAttempting to add recruitment step: {step2_data.get('step_name')}")
        new_step2_id = add_recruitment_step(step2_data)
        if new_step2_id:
            print(f"Recruitment Step '{step2_data.get('step_name')}' added with ID: {new_step2_id}")

        # 2. Get Recruitment Step by ID
        print(f"\nAttempting to retrieve step with ID: {new_step1_id}")
        step = get_recruitment_step_by_id(new_step1_id)
        if step:
            print(f"Retrieved: {step.get('step_name')}, Order: {step.get('step_order')}")
        else:
            print(f"Could not retrieve step with ID: {new_step1_id}")

        # 3. Get Recruitment Steps for Job Opening
        print(f"\nAttempting to retrieve all steps for job opening ID: {_dummy_job_opening_id_for_steps}")
        all_steps = get_recruitment_steps_for_job_opening(_dummy_job_opening_id_for_steps)
        if all_steps:
            print(f"Found {len(all_steps)} steps for job opening ID {_dummy_job_opening_id_for_steps}:")
            for s in all_steps:
                print(f"  - Name: {s.get('step_name')}, Order: {s.get('step_order')} (ID: {s.get('recruitment_step_id')})")
        else:
            print(f"No steps found for job opening ID {_dummy_job_opening_id_for_steps}.")

        # Test ordering
        print(f"\nAttempting to retrieve all steps for job opening ID: {_dummy_job_opening_id_for_steps} ordered by name DESC")
        all_steps_name_desc = get_recruitment_steps_for_job_opening(_dummy_job_opening_id_for_steps, order_by="step_name DESC")
        if all_steps_name_desc:
            print(f"Found {len(all_steps_name_desc)} steps (ordered by name DESC):")
            for s_desc in all_steps_name_desc:
                print(f"  - Name: {s_desc.get('step_name')}, Order: {s_desc.get('step_order')}")


        # 4. Update Recruitment Step
        update_s_data = {
            'description': 'Initial screening of all submitted applications and resumes.',
            'step_name': 'CV Review' # Also testing unique constraint violation potential if not careful
        }
        # To avoid accidental unique constraint violation on (job_id, step_name) if "CV Review" already exists for this job_id
        # For this test, we assume it's a safe update or the first step.
        print(f"\nAttempting to update step ID: {new_step1_id} with data: {update_s_data}")
        if update_recruitment_step(new_step1_id, update_s_data):
            print("Recruitment Step updated successfully.")
            updated_s = get_recruitment_step_by_id(new_step1_id)
            print(f"Updated Data: Name - {updated_s.get('step_name')}, Desc - {updated_s.get('description')}")
        else:
            print("Failed to update recruitment step.")

        # Test unique constraint by trying to add a step with the same order for the same job
        duplicate_step_data = {
            'job_opening_id': _dummy_job_opening_id_for_steps,
            'step_name': 'Duplicate Order Step',
            'step_order': 1, # Same as step1_data initially
            'description': 'This should fail due to unique order for the job.'
        }
        # Ensure step1 name is different from this to test order constraint primarily
        if get_recruitment_step_by_id(new_step1_id).get('step_order') == 1:
             print(f"\nAttempting to add a step with duplicate order: {duplicate_step_data.get('step_name')}")
             duplicate_id = add_recruitment_step(duplicate_step_data)
             if not duplicate_id:
                 print("Correctly failed to add step with duplicate order for the same job opening.")
             else:
                 print(f"Error: Added step with duplicate order. ID: {duplicate_id}. Deleting it.")
                 delete_recruitment_step(duplicate_id)


        # 5. Delete Recruitment Steps (if they were created)
        if new_step1_id:
            print(f"\nAttempting to delete step ID: {new_step1_id}")
            if delete_recruitment_step(new_step1_id):
                print(f"Step ID {new_step1_id} deleted successfully.")
                if not get_recruitment_step_by_id(new_step1_id):
                    print(f"Verified: Step ID {new_step1_id} no longer exists.")
                else:
                    print(f"Error: Step ID {new_step1_id} still exists.")
            else:
                print(f"Failed to delete step ID {new_step1_id}.")

        if new_step2_id:
            print(f"\nAttempting to delete step ID: {new_step2_id}")
            if delete_recruitment_step(new_step2_id):
                print(f"Step ID {new_step2_id} deleted successfully.")
            else:
                print(f"Failed to delete step ID {new_step2_id}.")
    else:
        print("Failed to add initial recruitment step, skipping dependent tests.")

    print("\nExample usage for recruitment_steps_crud.py finished.")
    # Note: Assumes JobOpenings table exists for the foreign key.
    # The dummy job_opening_id is used for demonstration. In a real test environment,
    # you would first create a job opening and use its actual ID.
    # The ON DELETE CASCADE behavior for CandidateProgress and Interviews is mentioned
    # but not explicitly tested here.
```
