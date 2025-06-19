import sqlite3
import uuid
from datetime import datetime
from db.connection import get_db_connection

# TODO: Add StatusSettings related functions for status_id validation.
# TODO: Consider validation for candidate_id, job_opening_id, recruitment_step_id, interviewer_team_member_id.

def add_interview(interview_data: dict) -> str | None:
    """
    Adds a new interview to the database.
    Expected keys: 'candidate_id', 'job_opening_id', 'recruitment_step_id',
                   'interviewer_team_member_id', 'scheduled_at', 'duration_minutes',
                   'interview_type', 'location_or_link', 'status_id',
                   'feedback_notes_overall', 'feedback_rating', 'created_by_user_id'.
    Returns the new interview_id (UUID string) or None if an error occurs.
    """
    interview_id = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO Interviews (
                interview_id, candidate_id, job_opening_id, recruitment_step_id,
                interviewer_team_member_id, scheduled_at, duration_minutes,
                interview_type, location_or_link, status_id,
                feedback_notes_overall, feedback_rating, created_by_user_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        current_time = datetime.now()
        cursor.execute(query, (
            interview_id,
            interview_data.get('candidate_id'),
            interview_data.get('job_opening_id'),
            interview_data.get('recruitment_step_id'),
            interview_data.get('interviewer_team_member_id'),
            interview_data.get('scheduled_at'), # Should be ISO format string or datetime object
            interview_data.get('duration_minutes'),
            interview_data.get('interview_type'),
            interview_data.get('location_or_link'),
            interview_data.get('status_id'),
            interview_data.get('feedback_notes_overall'),
            interview_data.get('feedback_rating'),
            interview_data.get('created_by_user_id'),
            current_time,
            current_time
        ))
        conn.commit()
        return interview_id
    except sqlite3.Error as e:
        print(f"Database error in add_interview: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_interview_by_id(interview_id: str) -> dict | None:
    """
    Retrieves an interview by its ID.
    Returns a dictionary representing the interview or None if not found or error.
    """
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM Interviews WHERE interview_id = ?"
        cursor.execute(query, (interview_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_interview_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_interviews_for_candidate(candidate_id: str, limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Retrieves all interviews for a specific candidate.
    """
    conn = get_db_connection()
    interviews_list = []
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM Interviews WHERE candidate_id = ? ORDER BY scheduled_at DESC LIMIT ? OFFSET ?"
        cursor.execute(query, (candidate_id, limit, offset))
        rows = cursor.fetchall()
        for row in rows:
            interviews_list.append(dict(row))
        return interviews_list
    except sqlite3.Error as e:
        print(f"Database error in get_interviews_for_candidate: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_interviews_for_job_opening(job_opening_id: str, limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Retrieves all interviews for a specific job opening.
    """
    conn = get_db_connection()
    interviews_list = []
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM Interviews WHERE job_opening_id = ? ORDER BY scheduled_at DESC LIMIT ? OFFSET ?"
        cursor.execute(query, (job_opening_id, limit, offset))
        rows = cursor.fetchall()
        for row in rows:
            interviews_list.append(dict(row))
        return interviews_list
    except sqlite3.Error as e:
        print(f"Database error in get_interviews_for_job_opening: {e}")
        return []
    finally:
        if conn:
            conn.close()


def update_interview(interview_id: str, update_data: dict) -> bool:
    """
    Updates an existing interview.
    'updated_at' will be automatically set.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        update_fields = []
        params = []

        allowed_fields = [
            'recruitment_step_id', 'interviewer_team_member_id', 'scheduled_at',
            'duration_minutes', 'interview_type', 'location_or_link', 'status_id',
            'feedback_notes_overall', 'feedback_rating'
        ]

        for key, value in update_data.items():
            if key in allowed_fields:
                update_fields.append(f"{key} = ?")
                params.append(value)

        if not update_fields:
            print("No valid fields provided for update in update_interview.")
            return False

        update_fields.append("updated_at = ?")
        params.append(datetime.now())

        query = f"UPDATE Interviews SET {', '.join(update_fields)} WHERE interview_id = ?"
        params.append(interview_id)

        cursor.execute(query, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_interview: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_interview(interview_id: str) -> bool:
    """
    Deletes an interview from the database. (Hard delete)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "DELETE FROM Interviews WHERE interview_id = ?"
        cursor.execute(query, (interview_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_interview: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("Running example usage for recruitment_interviews_crud.py")
    # This example usage will be more complex due to dependencies on:
    # JobOpenings, Candidates, RecruitmentSteps, TeamMembers, StatusSettings, Users
    # For simplicity, we will assume these IDs exist or are mocked.
    # Actual testing requires a proper setup or mocking framework.

    # --- Mock/Dummy IDs (replace with actual IDs from your test DB) ---
    # These would normally come from other CRUD operations or a fixed test dataset.
    _dummy_candidate_id = str(uuid.uuid4()) # Pretend this candidate exists
    _dummy_job_opening_id = str(uuid.uuid4()) # Pretend this job opening exists
    _dummy_recruitment_step_id = None # Optional, can be null
    _dummy_interviewer_id = None # Optional (e.g., from TeamMembers table)
    _dummy_user_id = None # Optional (from Users table for created_by_user_id)

    # Dummy Status ID for 'Scheduled' InterviewStatus
    # In a real test, you'd fetch this via status_settings_crud or ensure it's pre-populated.
    _dummy_interview_status_scheduled = None
    _dummy_interview_status_completed = None

    def setup_interview_dependencies():
        global _dummy_interview_status_scheduled, _dummy_interview_status_completed
        conn_setup = get_db_connection()
        try:
            cur_setup = conn_setup.cursor()
            # Get or create InterviewStatus 'Scheduled'
            cur_setup.execute("SELECT status_id FROM StatusSettings WHERE status_name = ? AND status_type = ?", ('Scheduled', 'InterviewStatus'))
            row = cur_setup.fetchone()
            if row: _dummy_interview_status_scheduled = row[0]
            else:
                cur_setup.execute("INSERT OR IGNORE INTO StatusSettings (status_name, status_type) VALUES (?,?)", ('Scheduled', 'InterviewStatus'))
                conn_setup.commit()
                _dummy_interview_status_scheduled = cur_setup.lastrowid

            # Get or create InterviewStatus 'Completed'
            cur_setup.execute("SELECT status_id FROM StatusSettings WHERE status_name = ? AND status_type = ?", ('Completed', 'InterviewStatus'))
            row = cur_setup.fetchone()
            if row: _dummy_interview_status_completed = row[0]
            else:
                cur_setup.execute("INSERT OR IGNORE INTO StatusSettings (status_name, status_type) VALUES (?,?)", ('Completed', 'InterviewStatus'))
                conn_setup.commit()
                _dummy_interview_status_completed = cur_setup.lastrowid
            print(f"Setup: Scheduled Status ID: {_dummy_interview_status_scheduled}, Completed Status ID: {_dummy_interview_status_completed}")
        except sqlite3.Error as e_setup:
            print(f"Error in interview dependency setup: {e_setup}")
        finally:
            if conn_setup: conn_setup.close()

    setup_interview_dependencies()

    if not _dummy_interview_status_scheduled:
        print("Failed to get/create dummy 'Scheduled' status for interviews. Examples might fail.")
    else:
        # 1. Add Interview
        interview_details = {
            'candidate_id': _dummy_candidate_id,
            'job_opening_id': _dummy_job_opening_id,
            'recruitment_step_id': _dummy_recruitment_step_id, # Can be None
            'interviewer_team_member_id': _dummy_interviewer_id, # Can be None
            'scheduled_at': datetime.now().isoformat(),
            'duration_minutes': 60,
            'interview_type': 'Phone Screen',
            'location_or_link': 'Phone call',
            'status_id': _dummy_interview_status_scheduled,
            'feedback_notes_overall': None,
            'feedback_rating': None,
            'created_by_user_id': _dummy_user_id # Can be None
        }
        print(f"\nAttempting to add interview for candidate ID: {_dummy_candidate_id}")
        new_interview_id = add_interview(interview_details)

        if new_interview_id:
            print(f"Interview added with ID: {new_interview_id}")

            # 2. Get Interview by ID
            print(f"\nAttempting to retrieve interview with ID: {new_interview_id}")
            interview = get_interview_by_id(new_interview_id)
            if interview:
                print(f"Retrieved: Type - {interview.get('interview_type')}, Scheduled at - {interview.get('scheduled_at')}")
            else:
                print(f"Could not retrieve interview with ID: {new_interview_id}")

            # 3. Update Interview
            update_i_data = {
                'status_id': _dummy_interview_status_completed, # Mark as completed (assuming status exists)
                'feedback_notes_overall': 'Candidate did well. Good technical skills.',
                'feedback_rating': 4, # Scale of 1-5
                'duration_minutes': 55
            }
            print(f"\nAttempting to update interview ID: {new_interview_id} with feedback.")
            if update_interview(new_interview_id, update_i_data):
                print("Interview updated successfully.")
                updated_i = get_interview_by_id(new_interview_id)
                print(f"Updated Data: Status ID - {updated_i.get('status_id')}, Rating - {updated_i.get('feedback_rating')}")
            else:
                print("Failed to update interview.")
        else:
            print("Failed to add interview, skipping further tests.")

        # 4. Get Interviews for Candidate
        print(f"\nAttempting to retrieve interviews for candidate ID: {_dummy_candidate_id}")
        candidate_interviews = get_interviews_for_candidate(_dummy_candidate_id, limit=5)
        if candidate_interviews:
            print(f"Found {len(candidate_interviews)} interviews for candidate ID {_dummy_candidate_id}:")
            for i in candidate_interviews:
                print(f"  - Type: {i.get('interview_type')}, Status ID: {i.get('status_id')} (ID: {i.get('interview_id')})")
        else:
            print(f"No interviews found for candidate ID {_dummy_candidate_id} or an error occurred.")

        # 5. Get Interviews for Job Opening
        print(f"\nAttempting to retrieve interviews for job opening ID: {_dummy_job_opening_id}")
        job_interviews = get_interviews_for_job_opening(_dummy_job_opening_id, limit=5)
        if job_interviews:
            print(f"Found {len(job_interviews)} interviews for job opening ID {_dummy_job_opening_id}:")
            for i_job in job_interviews:
                 print(f"  - Candidate: {i_job.get('candidate_id')}, Type: {i_job.get('interview_type')} (ID: {i_job.get('interview_id')})")
        else:
            print(f"No interviews found for job opening ID {_dummy_job_opening_id} or an error occurred.")


        # 6. Delete Interview (if one was created)
        if new_interview_id:
            print(f"\nAttempting to delete interview ID: {new_interview_id}")
            if delete_interview(new_interview_id):
                print("Interview deleted successfully.")
                if not get_interview_by_id(new_interview_id):
                    print(f"Verified: Interview ID {new_interview_id} no longer exists.")
                else:
                    print(f"Error: Interview ID {new_interview_id} still exists after deletion.")
            else:
                print("Failed to delete interview.")

    print("\nExample usage for recruitment_interviews_crud.py finished.")
    # Note: This example assumes that foreign key constraints would pass
    # if actual IDs were used. For these dummy IDs, errors might occur if the DB
    # has FK enforcement enabled and these dummy parent records don't exist.
    # The setup_interview_dependencies is a minimal attempt to create necessary status settings.
    # In a real scenario, ensure JobOpenings, Candidates, TeamMembers etc. exist for FKs.
```
