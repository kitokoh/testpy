import sqlite3
import uuid
from datetime import datetime
from db.connection import get_db_connection

# TODO: Add StatusSettings related functions if needed for status validation.
# TODO: Consider how to handle file paths for resumes and cover letters.

def add_candidate(candidate_data: dict) -> str | None:
    """
    Adds a new candidate to the database.
    Expected keys: 'job_opening_id', 'first_name', 'last_name', 'email',
                   'phone', 'resume_path', 'cover_letter_path', 'application_source',
                   'current_status_id', 'notes', 'linked_contact_id'.
    Returns the new candidate_id (UUID string) or None if an error occurs.
    """
    candidate_id = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO Candidates (
                candidate_id, job_opening_id, first_name, last_name, email, phone,
                resume_path, cover_letter_path, application_source, current_status_id,
                application_date, notes, linked_contact_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        current_time = datetime.now()
        cursor.execute(query, (
            candidate_id,
            candidate_data.get('job_opening_id'),
            candidate_data.get('first_name'),
            candidate_data.get('last_name'),
            candidate_data.get('email'),
            candidate_data.get('phone'),
            candidate_data.get('resume_path'),
            candidate_data.get('cover_letter_path'),
            candidate_data.get('application_source'),
            candidate_data.get('current_status_id'),
            current_time, # application_date
            candidate_data.get('notes'),
            candidate_data.get('linked_contact_id')
        ))
        conn.commit()
        return candidate_id
    except sqlite3.Error as e:
        print(f"Database error in add_candidate: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_candidate_by_id(candidate_id: str) -> dict | None:
    """
    Retrieves a candidate by their ID.
    Returns a dictionary representing the candidate or None if not found or error.
    """
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM Candidates WHERE candidate_id = ?"
        cursor.execute(query, (candidate_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_candidate_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_candidates_by_job_opening(job_opening_id: str, limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Retrieves all candidates for a specific job opening.
    """
    conn = get_db_connection()
    candidates_list = []
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM Candidates WHERE job_opening_id = ? ORDER BY application_date DESC LIMIT ? OFFSET ?"
        cursor.execute(query, (job_opening_id, limit, offset))
        rows = cursor.fetchall()
        for row in rows:
            candidates_list.append(dict(row))
        return candidates_list
    except sqlite3.Error as e:
        print(f"Database error in get_candidates_by_job_opening: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_all_candidates(filters: dict = None, limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Retrieves all candidates, optionally filtered, with pagination.
    filters: Example: {'current_status_id': 1, 'email': 'test@example.com'}
    Returns a list of dictionaries, each representing a candidate.
    """
    conn = get_db_connection()
    candidates_list = []
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM Candidates"
        params = []

        if filters:
            filter_clauses = []
            for key, value in filters.items():
                filter_clauses.append(f"{key} = ?")
                params.append(value)
            if filter_clauses:
                query += " WHERE " + " AND ".join(filter_clauses)

        query += " ORDER BY last_name, first_name LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        for row in rows:
            candidates_list.append(dict(row))
        return candidates_list
    except sqlite3.Error as e:
        print(f"Database error in get_all_candidates: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_candidate(candidate_id: str, update_data: dict) -> bool:
    """
    Updates an existing candidate.
    update_data: Dictionary of fields to update. 'application_date' is not typically updated.
    Returns True if update was successful, False otherwise.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        update_fields = []
        params = []

        # Define fields that can be updated
        allowed_fields = ['first_name', 'last_name', 'email', 'phone', 'resume_path',
                          'cover_letter_path', 'application_source', 'current_status_id',
                          'notes', 'linked_contact_id']

        for key, value in update_data.items():
            if key in allowed_fields:
                update_fields.append(f"{key} = ?")
                params.append(value)

        if not update_fields:
            print("No valid fields provided for update in update_candidate.")
            return False

        # Add updated_at equivalent if schema had one, Candidates table does not currently.
        # If it did, it would be:
        # update_fields.append("updated_at = ?")
        # params.append(datetime.now())

        query = f"UPDATE Candidates SET {', '.join(update_fields)} WHERE candidate_id = ?"
        params.append(candidate_id)

        cursor.execute(query, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_candidate: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_candidate(candidate_id: str) -> bool:
    """
    Deletes a candidate from the database. (Hard delete as per current schema)
    Returns True if deletion was successful, False otherwise.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # ON DELETE CASCADE for CandidateProgress and Interviews should handle related records.
        query = "DELETE FROM Candidates WHERE candidate_id = ?"
        cursor.execute(query, (candidate_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_candidate: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("Running example usage for recruitment_candidates_crud.py")
    from db.cruds.recruitment_job_openings_crud import add_job_opening, delete_job_opening, get_job_opening_by_id
    from datetime import timedelta

    # --- Helper to get a dummy Job Opening ID and Status ID ---
    _test_job_opening_id = None
    _test_status_id_applied = None
    _test_status_id_screening = None

    def get_or_create_test_dependencies():
        global _test_job_opening_id, _test_status_id_applied, _test_status_id_screening
        conn_setup = get_db_connection()
        try:
            cur_setup = conn_setup.cursor()
            # Get or create JobOpening Status
            cur_setup.execute("SELECT status_id FROM StatusSettings WHERE status_name = ? AND status_type = ?", ('Open', 'JobOpening'))
            row = cur_setup.fetchone()
            job_opening_status_id = row[0] if row else None
            if not job_opening_status_id:
                cur_setup.execute("INSERT OR IGNORE INTO StatusSettings (status_name, status_type) VALUES (?, ?)", ('Open', 'JobOpening'))
                conn_setup.commit()
                job_opening_status_id = cur_setup.lastrowid

            # Get or create CandidateApplication Statuses
            cur_setup.execute("SELECT status_id FROM StatusSettings WHERE status_name = ? AND status_type = ?", ('Applied', 'CandidateApplication'))
            row = cur_setup.fetchone()
            _test_status_id_applied = row[0] if row else None
            if not _test_status_id_applied:
                cur_setup.execute("INSERT OR IGNORE INTO StatusSettings (status_name, status_type) VALUES (?, ?)", ('Applied', 'CandidateApplication'))
                conn_setup.commit()
                _test_status_id_applied = cur_setup.lastrowid

            cur_setup.execute("SELECT status_id FROM StatusSettings WHERE status_name = ? AND status_type = ?", ('Screening', 'CandidateApplication'))
            row = cur_setup.fetchone()
            _test_status_id_screening = row[0] if row else None
            if not _test_status_id_screening:
                cur_setup.execute("INSERT OR IGNORE INTO StatusSettings (status_name, status_type) VALUES (?, ?)", ('Screening', 'CandidateApplication'))
                conn_setup.commit()
                _test_status_id_screening = cur_setup.lastrowid

            # Create a dummy Job Opening for testing candidates
            temp_job_data = {
                'title': 'Temporary Test Job Opening for Candidates',
                'status_id': job_opening_status_id,
                'closing_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
            }
            # Need to use the actual add_job_opening from its CRUD
            _test_job_opening_id = add_job_opening(temp_job_data)
            if _test_job_opening_id:
                print(f"Created temporary Job Opening with ID: {_test_job_opening_id} for testing candidates.")
            else:
                print("Failed to create temporary job opening for candidate tests.")

        except sqlite3.Error as e_setup:
            print(f"Error setting up test dependencies: {e_setup}")
        finally:
            if conn_setup:
                conn_setup.close()

    get_or_create_test_dependencies()
    # --- End Helper ---

    if not _test_job_opening_id or not _test_status_id_applied:
        print("Critical test dependencies (job opening ID or status ID) missing. Aborting example usage.")
    else:
        # 1. Add Candidate
        candidate_data = {
            'job_opening_id': _test_job_opening_id,
            'first_name': 'John',
            'last_name': 'Doe',
            'email': f'john.doe.{uuid.uuid4()}@example.com', # Unique email
            'phone': '123-456-7890',
            'resume_path': '/path/to/john_doe_resume.pdf',
            'cover_letter_path': '/path/to/john_doe_cover_letter.pdf',
            'application_source': 'Website',
            'current_status_id': _test_status_id_applied,
            'notes': 'Initial application.',
            'linked_contact_id': None # Optional
        }
        print(f"\nAttempting to add candidate: {candidate_data.get('first_name')} {candidate_data.get('last_name')}")
        new_candidate_id = add_candidate(candidate_data)

        if new_candidate_id:
            print(f"Candidate added with ID: {new_candidate_id}")

            # 2. Get Candidate by ID
            print(f"\nAttempting to retrieve candidate with ID: {new_candidate_id}")
            candidate = get_candidate_by_id(new_candidate_id)
            if candidate:
                print(f"Retrieved: {candidate.get('first_name')} {candidate.get('last_name')}, Email: {candidate.get('email')}")
            else:
                print(f"Could not retrieve candidate with ID: {new_candidate_id}")

            # 3. Update Candidate
            update_c_data = {
                'phone': '987-654-3210',
                'notes': 'Updated contact number and a new note.',
                'current_status_id': _test_status_id_screening # Assuming screening status exists
            }
            print(f"\nAttempting to update candidate ID: {new_candidate_id} with data: {update_c_data}")
            if update_candidate(new_candidate_id, update_c_data):
                print("Candidate updated successfully.")
                updated_c = get_candidate_by_id(new_candidate_id)
                print(f"Updated data - Phone: {updated_c.get('phone')}, Status ID: {updated_c.get('current_status_id')}")
            else:
                print("Failed to update candidate.")
        else:
            print("Failed to add candidate, skipping further tests that depend on it.")

        # 4. Get Candidates by Job Opening
        print(f"\nAttempting to retrieve candidates for job opening ID: {_test_job_opening_id}")
        job_candidates = get_candidates_by_job_opening(_test_job_opening_id, limit=5)
        if job_candidates:
            print(f"Found {len(job_candidates)} candidates for job ID {_test_job_opening_id}:")
            for c in job_candidates:
                print(f"  - {c.get('first_name')} {c.get('last_name')} (ID: {c.get('candidate_id')})")
        else:
            print(f"No candidates found for job ID {_test_job_opening_id} or an error occurred.")

        # 5. Get All Candidates (with a filter if possible)
        print("\nAttempting to retrieve all candidates (limit 5):")
        all_candidates_list = get_all_candidates(limit=5)
        if all_candidates_list:
            print(f"Found {len(all_candidates_list)} total candidates:")
            for c in all_candidates_list:
                 print(f"  - {c.get('first_name')} {c.get('last_name')} (Email: {c.get('email')})")
        else:
            print("No candidates found or an error occurred.")

        if _test_status_id_screening:
            print(f"\nAttempting to retrieve candidates with status_id {_test_status_id_screening}:")
            filtered_candidates = get_all_candidates(filters={'current_status_id': _test_status_id_screening}, limit=5)
            if filtered_candidates:
                print(f"Found {len(filtered_candidates)} candidates with status_id {_test_status_id_screening}:")
                for fc in filtered_candidates:
                    print(f"  - {fc.get('first_name')} (ID: {fc.get('candidate_id')})")
            else:
                print(f"No candidates found with status_id {_test_status_id_screening}.")


        # 6. Delete Candidate (if one was created)
        if new_candidate_id:
            print(f"\nAttempting to delete candidate ID: {new_candidate_id}")
            if delete_candidate(new_candidate_id):
                print("Candidate deleted successfully.")
                if not get_candidate_by_id(new_candidate_id):
                    print(f"Verified: Candidate ID {new_candidate_id} no longer exists.")
                else:
                    print(f"Error: Candidate ID {new_candidate_id} still exists after deletion attempt.")
            else:
                print("Failed to delete candidate.")

    # Cleanup: Delete the temporary job opening
    if _test_job_opening_id:
        print(f"\nAttempting to delete temporary test job opening ID: {_test_job_opening_id}")
        if delete_job_opening(_test_job_opening_id): # Assuming this function exists and works
            print(f"Temporary job opening ID {_test_job_opening_id} deleted successfully.")
        else:
            print(f"Failed to delete temporary job opening ID {_test_job_opening_id}.")

    print("\nExample usage for recruitment_candidates_crud.py finished.")
    # Note: The example usage for this CRUD is more complex due to dependencies (JobOpenings, StatusSettings).
    # This __main__ block attempts to set up some of these dependencies for basic execution.
    # Proper testing would mock these dependencies or use a dedicated test database.
    # The add_job_opening and delete_job_opening are imported from the previously created CRUD file.
    # Ensure that recruitment_job_openings_crud.py is in the same directory or Python path.
    # The use of global variables for test IDs is a simplification for this example.
    # The helper function get_or_create_test_dependencies() is also a simplification.
