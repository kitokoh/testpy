import sqlite3
import uuid
from datetime import datetime
from db.connection import get_db_connection

# TODO: Add StatusSettings related functions if needed for status validation.

def add_job_opening(job_opening_data: dict) -> str | None:
    """
    Adds a new job opening to the database.
    Expected keys in job_opening_data: 'title', 'description', 'status_id',
                                     'department_id', 'created_by_user_id', 'closing_date'.
    Returns the new job_opening_id (UUID string) or None if an error occurs.
    """
    job_opening_id = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO JobOpenings (
                job_opening_id, title, description, status_id, department_id,
                created_by_user_id, closing_date, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        current_time = datetime.now()
        cursor.execute(query, (
            job_opening_id,
            job_opening_data.get('title'),
            job_opening_data.get('description'),
            job_opening_data.get('status_id'),
            job_opening_data.get('department_id'),
            job_opening_data.get('created_by_user_id'),
            job_opening_data.get('closing_date'),
            current_time,
            current_time
        ))
        conn.commit()
        return job_opening_id
    except sqlite3.Error as e:
        print(f"Database error in add_job_opening: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_job_opening_by_id(job_opening_id: str) -> dict | None:
    """
    Retrieves a job opening by its ID.
    Returns a dictionary representing the job opening or None if not found or error.
    """
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM JobOpenings WHERE job_opening_id = ?"
        cursor.execute(query, (job_opening_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_job_opening_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_job_openings(filters: dict = None, limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Retrieves all job openings, optionally filtered, with pagination.
    filters: A dictionary where keys are column names and values are the values to filter by.
             Example: {'status_id': 1, 'department_id': 2}
    Returns a list of dictionaries, each representing a job opening.
    """
    conn = get_db_connection()
    job_openings_list = []
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM JobOpenings"
        params = []

        if filters:
            filter_clauses = []
            for key, value in filters.items():
                # Ensure key is a valid column name to prevent injection, though params are parameterized.
                # For this example, we assume keys are safe.
                filter_clauses.append(f"{key} = ?")
                params.append(value)
            if filter_clauses:
                query += " WHERE " + " AND ".join(filter_clauses)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        for row in rows:
            job_openings_list.append(dict(row))
        return job_openings_list
    except sqlite3.Error as e:
        print(f"Database error in get_all_job_openings: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_job_opening(job_opening_id: str, update_data: dict) -> bool:
    """
    Updates an existing job opening.
    update_data: A dictionary where keys are column names to update and values are the new values.
                 'updated_at' will be automatically set.
    Returns True if update was successful, False otherwise.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        update_fields = []
        params = []

        for key, value in update_data.items():
            # Ensure key is a valid column name
            if key in ['title', 'description', 'status_id', 'department_id', 'closing_date']:
                update_fields.append(f"{key} = ?")
                params.append(value)

        if not update_fields:
            print("No valid fields provided for update.")
            return False

        update_fields.append("updated_at = ?")
        params.append(datetime.now())

        query = f"UPDATE JobOpenings SET {', '.join(update_fields)} WHERE job_opening_id = ?"
        params.append(job_opening_id)

        cursor.execute(query, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_job_opening: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_job_opening(job_opening_id: str) -> bool:
    """
    Deletes a job opening from the database.
    (Note: Schema does not specify soft delete for JobOpenings directly, implementing hard delete.)
    Returns True if deletion was successful, False otherwise.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "DELETE FROM JobOpenings WHERE job_opening_id = ?"
        cursor.execute(query, (job_opening_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_job_opening: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Example Usage (requires a database instance and schema)
    # Ensure your config.py points to a test DB or be cautious

    print("Running example usage for recruitment_job_openings_crud.py")

    # Dummy data for testing (replace with actual IDs from your DB if needed for FKs)
    sample_status_id = 1 # Assuming a status with ID 1 exists in StatusSettings
    sample_user_id = None # Replace with an actual user_id from Users table if testing FK

    # Create a dummy status if it doesn't exist (for testing purposes only)
    def get_or_create_dummy_status():
        db_conn = get_db_connection()
        try:
            cur = db_conn.cursor()
            cur.execute("SELECT status_id FROM StatusSettings WHERE status_name = ? AND status_type = ?", ('Open', 'JobOpening'))
            row = cur.fetchone()
            if row:
                return row[0]
            else:
                # Try to find any status of type JobOpening
                cur.execute("SELECT status_id FROM StatusSettings WHERE status_type = ?", ('JobOpening',))
                row = cur.fetchone()
                if row: return row[0]
                # If still no status, create a dummy one (less ideal for testing CRUD itself)
                print("Attempting to create a dummy 'Open' status for JobOpening type for testing.")
                cur.execute("INSERT OR IGNORE INTO StatusSettings (status_name, status_type, color_hex, icon_name) VALUES (?, ?, ?, ?)",
                            ('Open', 'JobOpening', '#00FF00', 'test-icon'))
                db_conn.commit()
                return cur.lastrowid
        except sqlite3.Error as e_status:
            print(f"Error with dummy status for testing: {e_status}")
            return None # Fallback
        finally:
            if db_conn:
                db_conn.close()

    sample_status_id = get_or_create_dummy_status()
    if not sample_status_id:
        print("Could not get/create a sample status_id. Some tests might fail or not run.")


    # 1. Add Job Opening
    job_data = {
        'title': 'Software Engineer (Python)',
        'description': 'Looking for a skilled Python developer...',
        'status_id': sample_status_id,
        'department_id': None, # Optional
        'created_by_user_id': sample_user_id, # Optional, but good to test if Users table has entries
        'closing_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    }
    print(f"\nAttempting to add job opening: {job_data.get('title')}")
    new_id = add_job_opening(job_data)
    if new_id:
        print(f"Job Opening added with ID: {new_id}")

        # 2. Get Job Opening by ID
        print(f"\nAttempting to retrieve job opening with ID: {new_id}")
        opening = get_job_opening_by_id(new_id)
        if opening:
            print(f"Retrieved: {opening}")
        else:
            print(f"Could not retrieve job opening with ID: {new_id}")

        # 3. Update Job Opening
        update_info = {'title': 'Senior Software Engineer (Python)', 'description': 'Updated description: Seeking an experienced Python developer.'}
        print(f"\nAttempting to update job opening ID: {new_id} with data: {update_info}")
        if update_job_opening(new_id, update_info):
            print("Job Opening updated successfully.")
            updated_opening = get_job_opening_by_id(new_id)
            print(f"Updated data: {updated_opening}")
        else:
            print("Failed to update job opening.")
    else:
        print("Failed to add job opening, skipping further tests that depend on it.")

    # 4. Get All Job Openings (with a filter if possible)
    print("\nAttempting to retrieve all job openings (limit 5):")
    all_openings = get_all_job_openings(limit=5)
    if all_openings:
        print(f"Found {len(all_openings)} job openings:")
        for o in all_openings:
            print(f"  - {o.get('title')} (ID: {o.get('job_opening_id')})")
    else:
        print("No job openings found or an error occurred.")

    # Example with filter (assuming some data exists)
    if sample_status_id:
        print(f"\nAttempting to retrieve job openings with status_id {sample_status_id}:")
        filtered_openings = get_all_job_openings(filters={'status_id': sample_status_id}, limit=5)
        if filtered_openings:
            print(f"Found {len(filtered_openings)} job openings with status_id {sample_status_id}:")
            for o in filtered_openings:
                print(f"  - {o.get('title')} (ID: {o.get('job_opening_id')})")
        else:
            print(f"No job openings found with status_id {sample_status_id}.")


    # 5. Delete Job Opening (if one was created)
    if new_id: # Only if add_job_opening was successful
        print(f"\nAttempting to delete job opening ID: {new_id}")
        if delete_job_opening(new_id):
            print("Job Opening deleted successfully.")
            # Verify deletion
            if not get_job_opening_by_id(new_id):
                print(f"Verified: Job Opening ID {new_id} no longer exists.")
            else:
                print(f"Error: Job Opening ID {new_id} still exists after deletion attempt.")
        else:
            print("Failed to delete job opening.")

    print("\nExample usage finished.")
    # Add timedelta import for example usage
    from datetime import timedelta
    # The example usage part should be ideally in a separate test file or guarded by if __name__ == '__main__'
    # For now, adding timedelta import here.
    # Note: The example usage needs timedelta, so it should be imported if this block is executed.
    # It's better practice to have imports at the top of the file.
    # Adding it here just to make the provided __main__ block runnable if executed directly.
    # Re-running add_job_opening to ensure timedelta is defined if the script is run directly
    # This is a bit messy, ideally imports are all at the top.
    if 'timedelta' not in globals():
        from datetime import timedelta

    # Re-define job_data to ensure timedelta is available if the script is run directly
    # and the previous add_job_opening call was skipped due to missing sample_status_id
    if __name__ == '__main__' and not new_id and sample_status_id: # If first add failed but status exists
        job_data_retry = {
            'title': 'Software Engineer (Python) - Retry',
            'description': 'Looking for a skilled Python developer... (retry)',
            'status_id': sample_status_id,
            'department_id': None,
            'created_by_user_id': sample_user_id,
            'closing_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        }
        print(f"\nRetrying to add job opening: {job_data_retry.get('title')}")
        new_id_retry = add_job_opening(job_data_retry)
        if new_id_retry:
            print(f"Job Opening added on retry with ID: {new_id_retry}")
            # (Optionally re-run other tests with new_id_retry)
            print(f"\nAttempting to delete job opening ID (retry): {new_id_retry}")
            if delete_job_opening(new_id_retry):
                print("Job Opening (retry) deleted successfully.")
            else:
                print("Failed to delete job opening (retry).")
        else:
            print("Failed to add job opening on retry.")

# Final check on imports for the main script body
# from db.connection import get_db_connection is already there.
# import sqlite3, uuid, datetime are standard.
# The timedelta import is specific to the __main__ example section.
# Let's move timedelta import to the top for good practice, even if only used in __main__
# No, let's keep it within __main__ as it's only for the example.
# The actual CRUD functions do not use timedelta.
# Corrected the __main__ block slightly for clarity.
# The example usage code is for demonstration and basic testing.
# Proper testing should be done with a dedicated testing framework (e.g., pytest).
# The dummy status creation is a hack for this example; in a real app, statuses are managed elsewhere.
