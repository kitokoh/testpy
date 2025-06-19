import sqlite3
import uuid
from datetime import datetime
from db.connection import get_db_connection

# TODO: Validate candidate_id, recruitment_step_id, status_id.

def add_candidate_progress(progress_data: dict) -> str | None:
    """
    Adds a new candidate progress record.
    Expected keys: 'candidate_id', 'recruitment_step_id', 'status_id',
                   'notes', 'completed_at'.
    'updated_at' is set automatically.
    Returns the new candidate_progress_id (UUID string) or None if an error occurs.
    """
    candidate_progress_id = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO CandidateProgress (
                candidate_progress_id, candidate_id, recruitment_step_id, status_id,
                notes, completed_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        current_time = datetime.now()
        cursor.execute(query, (
            candidate_progress_id,
            progress_data.get('candidate_id'),
            progress_data.get('recruitment_step_id'),
            progress_data.get('status_id'),
            progress_data.get('notes'),
            progress_data.get('completed_at'), # Can be None
            current_time # updated_at
        ))
        conn.commit()
        return candidate_progress_id
    except sqlite3.Error as e:
        # UNIQUE constraint (candidate_id, recruitment_step_id) might be violated
        print(f"Database error in add_candidate_progress: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_candidate_progress_by_id(candidate_progress_id: str) -> dict | None:
    """
    Retrieves a candidate progress record by its ID.
    """
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM CandidateProgress WHERE candidate_progress_id = ?"
        cursor.execute(query, (candidate_progress_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_candidate_progress_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_progress_for_candidate(candidate_id: str) -> list[dict]:
    """
    Retrieves all progress records for a specific candidate, ordered by updated_at.
    Joins with RecruitmentSteps to get step_name and step_order for context.
    """
    conn = get_db_connection()
    progress_list = []
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Joining with RecruitmentSteps to also fetch step_name and step_order
        query = """
            SELECT cp.*, rs.step_name, rs.step_order
            FROM CandidateProgress cp
            JOIN RecruitmentSteps rs ON cp.recruitment_step_id = rs.recruitment_step_id
            WHERE cp.candidate_id = ?
            ORDER BY rs.step_order ASC, cp.updated_at DESC
        """
        cursor.execute(query, (candidate_id,))
        rows = cursor.fetchall()
        for row in rows:
            progress_list.append(dict(row))
        return progress_list
    except sqlite3.Error as e:
        print(f"Database error in get_progress_for_candidate: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_progress_for_candidate_at_step(candidate_id: str, recruitment_step_id: str) -> dict | None:
    """
    Retrieves a specific progress record for a candidate at a given recruitment step.
    Since (candidate_id, recruitment_step_id) is UNIQUE, this should return one record.
    """
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM CandidateProgress WHERE candidate_id = ? AND recruitment_step_id = ?"
        cursor.execute(query, (candidate_id, recruitment_step_id))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_progress_for_candidate_at_step: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_candidate_progress(candidate_progress_id: str, update_data: dict) -> bool:
    """
    Updates an existing candidate progress record.
    Allowed fields: 'status_id', 'notes', 'completed_at'.
    'updated_at' is automatically set.
    Candidate_id and recruitment_step_id are generally not changed; a new record would be made.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        update_fields = []
        params = []

        allowed_fields = ['status_id', 'notes', 'completed_at']

        for key, value in update_data.items():
            if key in allowed_fields:
                update_fields.append(f"{key} = ?")
                params.append(value)

        if not update_fields:
            print("No valid fields provided for update in update_candidate_progress.")
            return False

        update_fields.append("updated_at = ?")
        params.append(datetime.now())

        query = f"UPDATE CandidateProgress SET {', '.join(update_fields)} WHERE candidate_progress_id = ?"
        params.append(candidate_progress_id)

        cursor.execute(query, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_candidate_progress: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_candidate_progress(candidate_progress_id: str) -> bool:
    """
    Deletes a candidate progress record.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "DELETE FROM CandidateProgress WHERE candidate_progress_id = ?"
        cursor.execute(query, (candidate_progress_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_candidate_progress: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("Running example usage for recruitment_candidate_progress_crud.py")
    # Dependencies: Candidate, RecruitmentStep, StatusSettings for CandidateProgress
    # For simplicity, using dummy IDs. Real tests need proper setup.

    _dummy_candidate_id_prog = str(uuid.uuid4()) # Assume candidate exists
    _dummy_step_id_prog = str(uuid.uuid4())      # Assume recruitment step exists
    _dummy_status_pending_prog = None            # Status "Pending" for CandidateProgress
    _dummy_status_completed_prog = None          # Status "Completed" for CandidateProgress


    def setup_progress_dependencies():
        global _dummy_status_pending_prog, _dummy_status_completed_prog
        conn_setup = get_db_connection()
        try:
            cur_setup = conn_setup.cursor()
            # Get or create CandidateProgress Status 'Pending'
            cur_setup.execute("SELECT status_id FROM StatusSettings WHERE status_name = ? AND status_type = ?", ('Pending', 'CandidateProgress'))
            row = cur_setup.fetchone()
            if row: _dummy_status_pending_prog = row[0]
            else:
                cur_setup.execute("INSERT OR IGNORE INTO StatusSettings (status_name, status_type) VALUES (?,?)", ('Pending', 'CandidateProgress'))
                conn_setup.commit()
                _dummy_status_pending_prog = cur_setup.lastrowid

            # Get or create CandidateProgress Status 'Completed'
            cur_setup.execute("SELECT status_id FROM StatusSettings WHERE status_name = ? AND status_type = ?", ('Completed', 'CandidateProgress'))
            row = cur_setup.fetchone()
            if row: _dummy_status_completed_prog = row[0]
            else:
                cur_setup.execute("INSERT OR IGNORE INTO StatusSettings (status_name, status_type) VALUES (?,?)", ('Completed', 'CandidateProgress'))
                conn_setup.commit()
                _dummy_status_completed_prog = cur_setup.lastrowid
            print(f"Setup: Pending Status ID: {_dummy_status_pending_prog}, Completed Status ID: {_dummy_status_completed_prog}")

            # For get_progress_for_candidate to work in example, a dummy recruitment step is needed
            # This is a hack for the example. Proper tests would use recruitment_steps_crud.
            # We only need this if we are testing get_progress_for_candidate which joins.
            # The current _dummy_step_id_prog is just a UUID. Let's try to insert a minimal step if not found by this UUID.
            cur_setup.execute("SELECT recruitment_step_id FROM RecruitmentSteps WHERE recruitment_step_id = ?", (_dummy_step_id_prog,))
            if not cur_setup.fetchone():
                # Need a dummy job opening ID for this step
                dummy_job_id_for_step_for_progress = str(uuid.uuid4())
                # Minimal job opening (not using CRUD for simplicity here, which is bad practice but for quick demo)
                # cur_setup.execute("INSERT OR IGNORE INTO JobOpenings (job_opening_id, title, status_id) VALUES (?,?,?)",
                #                   (dummy_job_id_for_step_for_progress, "Dummy Job for Progress Step", 1)) # Assuming status 1 exists
                # conn_setup.commit()
                # print(f"INFO: Created dummy job opening {dummy_job_id_for_step_for_progress} for step")

                print(f"INFO: Attempting to create dummy recruitment step {_dummy_step_id_prog} for testing get_progress_for_candidate.")
                # This job_opening_id likely doesn't exist, so this will fail if FKs are on.
                # This highlights the complexity of testing CRUDs with FKs without a full test setup.
                # For now, we'll assume this might fail silently or pass if FKs are deferred/off in test DB.
                cur_setup.execute("INSERT OR IGNORE INTO RecruitmentSteps (recruitment_step_id, job_opening_id, step_name, step_order) VALUES (?, ?, ?, ?)",
                                  (_dummy_step_id_prog, dummy_job_id_for_step_for_progress, 'Dummy Step for Progress Test', 1))
                conn_setup.commit()
                print(f"INFO: Dummy recruitment step {_dummy_step_id_prog} insertion attempted.")


        except sqlite3.Error as e_setup_prog:
            print(f"Error in candidate_progress dependency setup: {e_setup_prog}")
        finally:
            if conn_setup: conn_setup.close()

    setup_progress_dependencies()

    if not _dummy_status_pending_prog:
        print("Failed to get/create dummy 'Pending' status for CandidateProgress. Examples might fail.")
    else:
        # 1. Add Candidate Progress
        progress1_data = {
            'candidate_id': _dummy_candidate_id_prog,
            'recruitment_step_id': _dummy_step_id_prog,
            'status_id': _dummy_status_pending_prog,
            'notes': 'Candidate scheduled for initial review.',
            'completed_at': None
        }
        print(f"\nAttempting to add candidate progress for candidate: {_dummy_candidate_id_prog}")
        new_progress1_id = add_candidate_progress(progress1_data)

        if new_progress1_id:
            print(f"Candidate progress record added with ID: {new_progress1_id}")

            # 2. Get Candidate Progress by ID
            print(f"\nAttempting to retrieve progress record with ID: {new_progress1_id}")
            progress_record = get_candidate_progress_by_id(new_progress1_id)
            if progress_record:
                print(f"Retrieved: Candidate {_progress_record.get('candidate_id')}, Status ID: {progress_record.get('status_id')}")
            else:
                print(f"Could not retrieve progress record with ID: {new_progress1_id}")

            # 3. Get Progress for Candidate (Specific Step)
            print(f"\nAttempting to retrieve progress for candidate {_dummy_candidate_id_prog} at step {_dummy_step_id_prog}")
            specific_progress = get_progress_for_candidate_at_step(_dummy_candidate_id_prog, _dummy_step_id_prog)
            if specific_progress:
                print(f"Found specific progress: Status ID {specific_progress.get('status_id')}")
            else:
                print("No specific progress found for candidate at that step.")


            # 4. Update Candidate Progress
            update_p_data = {
                'status_id': _dummy_status_completed_prog, # Mark as completed
                'notes': 'Initial review completed. Moving to next phase.',
                'completed_at': datetime.now().isoformat()
            }
            print(f"\nAttempting to update progress record ID: {new_progress1_id}")
            if update_candidate_progress(new_progress1_id, update_p_data):
                print("Candidate progress updated successfully.")
                updated_p = get_candidate_progress_by_id(new_progress1_id)
                print(f"Updated Data: Status ID - {updated_p.get('status_id')}, Completed At - {updated_p.get('completed_at')}")
            else:
                print("Failed to update candidate progress.")
        else:
            print(f"Failed to add candidate progress for candidate {_dummy_candidate_id_prog} at step {_dummy_step_id_prog}. This might be due to UNIQUE constraint if this script run multiple times or FK violation if dummy step/candidate don't exist.")


        # 5. Get All Progress for Candidate
        # This test might be problematic if the dummy RecruitmentStep doesn't actually exist in the DB
        # due to FK constraints not being handled by the simplified setup_progress_dependencies.
        print(f"\nAttempting to retrieve all progress for candidate ID: {_dummy_candidate_id_prog}")
        all_progress_records = get_progress_for_candidate(_dummy_candidate_id_prog)
        if all_progress_records:
            print(f"Found {len(all_progress_records)} progress records for candidate ID {_dummy_candidate_id_prog}:")
            for pr in all_progress_records:
                print(f"  - Step: {pr.get('step_name')} (Order: {pr.get('step_order')}), Status ID: {pr.get('status_id')}, Notes: {pr.get('notes')}")
        else:
            print(f"No progress records found for candidate ID {_dummy_candidate_id_prog} (or the dummy step for join failed).")
            # Try adding one more progress for a different (dummy) step to see if list grows
            _dummy_step_2_id_prog = str(uuid.uuid4())
            setup_step2_for_progress(_dummy_step_2_id_prog, _dummy_candidate_id_prog, _dummy_status_pending_prog) # Helper to add another step and progress

            all_progress_records_retry = get_progress_for_candidate(_dummy_candidate_id_prog)
            if len(all_progress_records_retry) > len(all_progress_records):
                 print(f"After adding another step's progress, found {len(all_progress_records_retry)} records.")


        # 6. Delete Candidate Progress (if one was created)
        if new_progress1_id:
            print(f"\nAttempting to delete progress record ID: {new_progress1_id}")
            if delete_candidate_progress(new_progress1_id):
                print("Candidate progress record deleted successfully.")
                if not get_candidate_progress_by_id(new_progress1_id):
                    print(f"Verified: Progress ID {new_progress1_id} no longer exists.")
                else:
                    print(f"Error: Progress ID {new_progress1_id} still exists.")
            else:
                print("Failed to delete candidate progress record.")

    print("\nExample usage for recruitment_candidate_progress_crud.py finished.")

def setup_step2_for_progress(step_id, cand_id, status_id):
    # Simplified helper for the example usage to add a second progress record
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        dummy_job_id = str(uuid.uuid4())
        # cursor.execute("INSERT OR IGNORE INTO JobOpenings (job_opening_id, title, status_id) VALUES (?,?,?)", (dummy_job_id, "Dummy Job for Step 2", 1))
        cursor.execute("INSERT OR IGNORE INTO RecruitmentSteps (recruitment_step_id, job_opening_id, step_name, step_order) VALUES (?, ?, ?, ?)",
                       (step_id, dummy_job_id, 'Dummy Step 2 for Progress Test', 2))
        conn.commit()
        print(f"INFO: Helper - Dummy recruitment step {step_id} insertion attempted.")

        progress_data = {
            'candidate_id': cand_id,
            'recruitment_step_id': step_id,
            'status_id': status_id,
            'notes': 'Progress for dummy step 2'
        }
        add_candidate_progress(progress_data)
        print(f"INFO: Helper - Added progress for candidate {cand_id} at step {step_id}")

    except sqlite3.Error as e:
        print(f"Helper setup_step2_for_progress error: {e}")
    finally:
        if conn: conn.close()

# Note: The __main__ block for this CRUD is particularly complex due to its position
# in the dependency chain (Candidate -> RecruitmentStep -> CandidateProgress <- StatusSettings).
# The setup functions are hacks to make the example runnable.
# A robust test suite with proper test data management and mocking is essential.
# The example for get_progress_for_candidate which joins with RecruitmentSteps is tricky
# because the RecruitmentStep itself needs a valid job_opening_id.
# The current example might not fully function for that specific function if FKs are strictly enforced
# without creating all parent dummy records perfectly.
# ```
