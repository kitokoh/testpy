import sqlite3
import uuid
# hashlib has been removed as it's no longer used in this file
from datetime import datetime
import json
import os # Added os import

from db.db_config import DATABASE_NAME, APP_ROOT_DIR_CONTEXT, LOGO_SUBDIR_CONTEXT, get_db_connection
from db.db_schema import initialize_database
from db.db_crud_users import (
    add_user, get_user_by_id, get_user_by_username, update_user, verify_user_password, delete_user,
    add_team_member, get_team_member_by_id, get_all_team_members, update_team_member, delete_team_member,
    add_company, get_company_by_id, get_all_companies, update_company, delete_company, set_default_company, get_default_company,
    add_company_personnel, get_personnel_for_company, update_company_personnel, delete_company_personnel,
    add_smtp_config, get_smtp_config_by_id, get_default_smtp_config, get_all_smtp_configs,
    update_smtp_config, delete_smtp_config, set_default_smtp_config,
    get_setting, set_setting
)
from db.db_crud_clients import (
    add_client, get_client_by_id, get_all_clients, update_client, delete_client,
    add_client_note, get_client_notes,
    add_contact, get_contact_by_id, get_contact_by_email, get_all_contacts, update_contact, delete_contact,
    link_contact_to_client, unlink_contact_from_client, get_contacts_for_client, get_clients_for_contact,
    get_specific_client_contact_link_details, update_client_contact_link,
    get_all_countries, get_country_by_id, get_country_by_name, add_country,
    get_all_cities, add_city, get_city_by_name_and_country_id, get_city_by_id
)
from db.db_crud_projects import (
    add_project, get_project_by_id, get_projects_by_client_id, get_all_projects, update_project, delete_project,
    add_task, get_task_by_id, get_tasks_by_project_id, update_task, delete_task,
    add_kpi, get_kpi_by_id, get_kpis_for_project, update_kpi, delete_kpi,
    get_all_status_settings, get_status_setting_by_id, get_status_setting_by_name,
    get_all_tasks, get_tasks_by_assignee_id
)
from db.db_crud_products import (
    add_product, get_product_by_id, get_product_by_name, get_all_products,
    update_product, delete_product, add_product_equivalence,
    get_equivalent_products, get_all_product_equivalencies, remove_product_equivalence,
    add_product_to_client_or_project, get_products_for_client_or_project,
    update_client_project_product, remove_product_from_client_or_project,
    get_products_by_name_pattern, get_all_products_for_selection,
    get_all_products_for_selection_filtered
)
from db.db_crud_templates import (
    add_template_category, get_template_category_by_id, get_template_category_by_name,
    get_all_template_categories, update_template_category, delete_template_category,
    add_template, get_template_by_id, get_templates_by_type, update_template,
    delete_template, add_client_document, get_document_by_id,
    get_documents_for_client, get_documents_for_project, update_client_document,
    delete_client_document, get_template_details_for_preview,
    get_template_path_info, delete_template_and_get_file_info,
    set_default_template_by_id, add_default_template_if_not_exists,
    get_distinct_languages_for_template_type, get_all_file_based_templates,
    get_templates_by_category_id
)

# CRUD functions for Projects
def add_project(project_data: dict) -> str | None:
    """
    Adds a new project to the database.
    Returns the new project_id if successful, otherwise None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        new_project_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat() + "Z"

        sql = """
            INSERT INTO Projects (
                project_id, client_id, project_name, description, start_date, 
                deadline_date, budget, status_id, progress_percentage, 
                manager_team_member_id, priority, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_project_id,
            project_data.get('client_id'),
            project_data.get('project_name'),
            project_data.get('description'),
            project_data.get('start_date'),
            project_data.get('deadline_date'),
            project_data.get('budget'),
            project_data.get('status_id'),
            project_data.get('progress_percentage', 0),
            project_data.get('manager_team_member_id'),
            project_data.get('priority', 0),
            now,  # created_at
            now   # updated_at
        )
        
        cursor.execute(sql, params)
        conn.commit()
        return new_project_id
    except sqlite3.Error as e:
        print(f"Database error in add_project: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_project_by_id(project_id: str) -> dict | None:
    """Retrieves a project by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Projects WHERE project_id = ?", (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_project_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_projects_by_client_id(client_id: str) -> list[dict]:
    """Retrieves all projects for a given client_id."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Projects WHERE client_id = ?", (client_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_projects_by_client_id: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_all_projects(filters: dict = None) -> list[dict]:
    """
    Retrieves all projects, optionally applying filters.
    Allowed filters: client_id, status_id, manager_team_member_id, priority.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM Projects"
        params = []
        
        if filters:
            where_clauses = []
            allowed_filters = ['client_id', 'status_id', 'manager_team_member_id', 'priority']
            for key, value in filters.items():
                if key in allowed_filters:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
                
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_projects: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_project(project_id: str, project_data: dict) -> bool:
    """
    Updates an existing project. Sets updated_at.
    Returns True if update was successful, False otherwise.
    """
    conn = None
    if not project_data:
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat() + "Z"
        project_data['updated_at'] = now
        
        set_clauses = []
        params = []
        
        # Ensure only valid columns are updated
        valid_columns = [
            'client_id', 'project_name', 'description', 'start_date', 'deadline_date', 
            'budget', 'status_id', 'progress_percentage', 'manager_team_member_id', 
            'priority', 'updated_at'
        ]
        for key, value in project_data.items():
            if key in valid_columns:
                 set_clauses.append(f"{key} = ?")
                 params.append(value)
        
        if not set_clauses:
            return False 
            
        sql = f"UPDATE Projects SET {', '.join(set_clauses)} WHERE project_id = ?"
        params.append(project_id)
        
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_project: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_project(project_id: str) -> bool:
    """Deletes a project. Returns True if deletion was successful."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # ON DELETE CASCADE for Tasks related to this project will be handled by SQLite
        cursor.execute("DELETE FROM Projects WHERE project_id = ?", (project_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_project: {e}")
        return False
    finally:
        if conn:
            conn.close()

# CRUD functions for Tasks
def add_task(task_data: dict) -> int | None:
    """
    Adds a new task to the database. Returns the task_id if successful.
    Sets created_at and updated_at.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"

        sql = """
            INSERT INTO Tasks (
                project_id, task_name, description, status_id, assignee_team_member_id,
                reporter_team_member_id, due_date, priority, estimated_hours,
                actual_hours_spent, parent_task_id, created_at, updated_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            task_data.get('project_id'),
            task_data.get('task_name'),
            task_data.get('description'),
            task_data.get('status_id'),
            task_data.get('assignee_team_member_id'),
            task_data.get('reporter_team_member_id'),
            task_data.get('due_date'),
            task_data.get('priority', 0),
            task_data.get('estimated_hours'),
            task_data.get('actual_hours_spent'),
            task_data.get('parent_task_id'),
            now,  # created_at
            now,  # updated_at
            task_data.get('completed_at') # Explicitly set if provided
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_task: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_task_by_id(task_id: int) -> dict | None:
    """Retrieves a task by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_task_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_tasks_by_project_id(project_id: str, filters: dict = None) -> list[dict]:
    """
    Retrieves tasks for a given project_id, optionally applying filters.
    Allowed filters: assignee_team_member_id, status_id, priority.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM Tasks WHERE project_id = ?"
        params = [project_id]
        
        if filters:
            where_clauses = []
            allowed_filters = ['assignee_team_member_id', 'status_id', 'priority']
            for key, value in filters.items():
                if key in allowed_filters:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
            if where_clauses:
                sql += " AND " + " AND ".join(where_clauses)
                
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_tasks_by_project_id: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_task(task_id: int, task_data: dict) -> bool:
    """
    Updates an existing task. Sets updated_at.
    If 'completed_at' is in task_data, it will be updated.
    (Logic for setting 'completed_at' based on status change should ideally be handled by calling code).
    Returns True on success.
    """
    conn = None
    if not task_data:
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        task_data['updated_at'] = now
        
        set_clauses = []
        params = []
        
        valid_columns = [
            'project_id', 'task_name', 'description', 'status_id', 'assignee_team_member_id',
            'reporter_team_member_id', 'due_date', 'priority', 'estimated_hours',
            'actual_hours_spent', 'parent_task_id', 'updated_at', 'completed_at'
        ]
        for key, value in task_data.items():
            if key in valid_columns: # Ensure key is a valid column
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
            
        sql = f"UPDATE Tasks SET {', '.join(set_clauses)} WHERE task_id = ?"
        params.append(task_id)
        
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_task: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_task(task_id: int) -> bool:
    """Deletes a task. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Tasks WHERE task_id = ?", (task_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_task: {e}")
        return False
    finally:
        if conn:
            conn.close()

# CRUD functions for ClientDocuments
def add_client_document(doc_data: dict) -> str | None:
    """Adds a new client document. Returns document_id (UUID) or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        doc_id = uuid.uuid4().hex

        sql = """
            INSERT INTO ClientDocuments (
                document_id, client_id, project_id, document_name, file_name_on_disk,
                file_path_relative, document_type_generated, source_template_id,
                version_tag, notes, created_at, updated_at, created_by_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            doc_id, doc_data.get('client_id'), doc_data.get('project_id'),
            doc_data.get('document_name'), doc_data.get('file_name_on_disk'),
            doc_data.get('file_path_relative'), doc_data.get('document_type_generated'),
            doc_data.get('source_template_id'), doc_data.get('version_tag'),
            doc_data.get('notes'), now, now, doc_data.get('created_by_user_id')
        )
        cursor.execute(sql, params)
        conn.commit()
        return doc_id
    except sqlite3.Error as e:
        print(f"Database error in add_client_document: {e}")
        return None
    finally:
        if conn: conn.close()

def get_document_by_id(document_id: str) -> dict | None:
    """Retrieves a document by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ClientDocuments WHERE document_id = ?", (document_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_document_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_documents_for_client(client_id: str, filters: dict = None) -> list[dict]:
    """
    Retrieves documents for a client. 
    Filters by 'document_type_generated' (exact) or 'project_id' (exact).
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM ClientDocuments WHERE client_id = ?"
        params = [client_id]
        
        if filters:
            if 'document_type_generated' in filters:
                sql += " AND document_type_generated = ?"
                params.append(filters['document_type_generated'])
            if 'project_id' in filters: # Can be None to filter for client-general docs
                if filters['project_id'] is None:
                    sql += " AND project_id IS NULL"
                else:
                    sql += " AND project_id = ?"
                    params.append(filters['project_id'])
            
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_documents_for_client: {e}")
        return []
    finally:
        if conn: conn.close()

def get_documents_for_project(project_id: str, filters: dict = None) -> list[dict]:
    """
    Retrieves documents for a project. 
    Filters by 'document_type_generated' (exact).
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM ClientDocuments WHERE project_id = ?"
        params = [project_id]
        
        if filters and 'document_type_generated' in filters:
            sql += " AND document_type_generated = ?"
            params.append(filters['document_type_generated'])
            
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_documents_for_project: {e}")
        return []
    finally:
        if conn: conn.close()

def update_client_document(document_id: str, doc_data: dict) -> bool:
    """Updates an existing client document. Sets updated_at."""
    conn = None
    if not doc_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        doc_data['updated_at'] = now
        
        # Exclude primary key from update set
        valid_columns = [
            'client_id', 'project_id', 'document_name', 'file_name_on_disk', 
            'file_path_relative', 'document_type_generated', 'source_template_id', 
            'version_tag', 'notes', 'updated_at', 'created_by_user_id'
        ]
        current_doc_data = {k: v for k, v in doc_data.items() if k in valid_columns}

        if not current_doc_data: return False

        set_clauses = [f"{key} = ?" for key in current_doc_data.keys()]
        params = list(current_doc_data.values())
        params.append(document_id)
        
        sql = f"UPDATE ClientDocuments SET {', '.join(set_clauses)} WHERE document_id = ?"
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_client_document: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_client_document(document_id: str) -> bool:
    """Deletes a client document."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ClientDocuments WHERE document_id = ?", (document_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_client_document: {e}")
        return False
    finally:
        if conn: conn.close()

# --- ScheduledEmails Functions ---
def add_scheduled_email(email_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """INSERT INTO ScheduledEmails (recipient_email, subject, body_html, body_text, 
                                           scheduled_send_at, status, related_client_id, 
                                           related_project_id, created_by_user_id, created_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (
            email_data.get('recipient_email'), email_data.get('subject'),
            email_data.get('body_html'), email_data.get('body_text'),
            email_data.get('scheduled_send_at'), email_data.get('status', 'pending'),
            email_data.get('related_client_id'), email_data.get('related_project_id'),
            email_data.get('created_by_user_id'), now
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"DB error in add_scheduled_email: {e}")
        return None
    finally:
        if conn: conn.close()

def get_scheduled_email_by_id(scheduled_email_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ScheduledEmails WHERE scheduled_email_id = ?", (scheduled_email_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_scheduled_email_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_pending_scheduled_emails(before_time: str = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM ScheduledEmails WHERE status = 'pending'"
        params = []
        if before_time:
            sql += " AND scheduled_send_at <= ?"
            params.append(before_time)
        sql += " ORDER BY scheduled_send_at ASC"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_pending_scheduled_emails: {e}")
        return []
    finally:
        if conn: conn.close()

def update_scheduled_email_status(scheduled_email_id: int, status: str, sent_at: str = None, error_message: str = None) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "UPDATE ScheduledEmails SET status = ?, sent_at = ?, error_message = ? WHERE scheduled_email_id = ?"
        params = (status, sent_at, error_message, scheduled_email_id)
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in update_scheduled_email_status: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_scheduled_email(scheduled_email_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # ON DELETE CASCADE handles EmailReminders
        cursor.execute("DELETE FROM ScheduledEmails WHERE scheduled_email_id = ?", (scheduled_email_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in delete_scheduled_email: {e}")
        return False
    finally:
        if conn: conn.close()

# --- EmailReminders Functions ---
def add_email_reminder(reminder_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """INSERT INTO EmailReminders (scheduled_email_id, reminder_type, reminder_send_at, status)
                 VALUES (?, ?, ?, ?)"""
        params = (
            reminder_data.get('scheduled_email_id'), reminder_data.get('reminder_type'),
            reminder_data.get('reminder_send_at'), reminder_data.get('status', 'pending')
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"DB error in add_email_reminder: {e}")
        return None
    finally:
        if conn: conn.close()

def get_pending_reminders(before_time: str = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM EmailReminders WHERE status = 'pending'"
        params = []
        if before_time:
            sql += " AND reminder_send_at <= ?"
            params.append(before_time)
        sql += " ORDER BY reminder_send_at ASC"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows] # Consider joining with ScheduledEmails for context
    except sqlite3.Error as e:
        print(f"DB error in get_pending_reminders: {e}")
        return []
    finally:
        if conn: conn.close()

def update_reminder_status(reminder_id: int, status: str) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "UPDATE EmailReminders SET status = ? WHERE reminder_id = ?"
        cursor.execute(sql, (status, reminder_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in update_reminder_status: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_email_reminder(reminder_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM EmailReminders WHERE reminder_id = ?", (reminder_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in delete_email_reminder: {e}")
        return False
    finally:
        if conn: conn.close()

# --- ContactLists & ContactListMembers Functions ---
def add_contact_list(list_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """INSERT INTO ContactLists (list_name, description, created_by_user_id, created_at, updated_at)
                 VALUES (?, ?, ?, ?, ?)"""
        params = (
            list_data.get('list_name'), list_data.get('description'),
            list_data.get('created_by_user_id'), now, now
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"DB error in add_contact_list: {e}")
        return None
    finally:
        if conn: conn.close()

def get_contact_list_by_id(list_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ContactLists WHERE list_id = ?", (list_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_contact_list_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_contact_lists() -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ContactLists ORDER BY list_name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_all_contact_lists: {e}")
        return []
    finally:
        if conn: conn.close()

def update_contact_list(list_id: int, list_data: dict) -> bool:
    conn = None
    if not list_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        list_data['updated_at'] = datetime.utcnow().isoformat() + "Z"
        set_clauses = [f"{key} = ?" for key in list_data.keys()]
        params = list(list_data.values())
        params.append(list_id)
        sql = f"UPDATE ContactLists SET {', '.join(set_clauses)} WHERE list_id = ?"
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in update_contact_list: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_contact_list(list_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # ON DELETE CASCADE handles ContactListMembers
        cursor.execute("DELETE FROM ContactLists WHERE list_id = ?", (list_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in delete_contact_list: {e}")
        return False
    finally:
        if conn: conn.close()

def add_contact_to_list(list_id: int, contact_id: int) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO ContactListMembers (list_id, contact_id) VALUES (?, ?)"
        cursor.execute(sql, (list_id, contact_id))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e: # Handles unique constraint violation
        print(f"DB error in add_contact_to_list: {e}")
        return None
    finally:
        if conn: conn.close()

def remove_contact_from_list(list_id: int, contact_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM ContactListMembers WHERE list_id = ? AND contact_id = ?"
        cursor.execute(sql, (list_id, contact_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in remove_contact_from_list: {e}")
        return False
    finally:
        if conn: conn.close()

def get_contacts_in_list(list_id: int) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """SELECT c.*, clm.added_at 
                 FROM Contacts c 
                 JOIN ContactListMembers clm ON c.contact_id = clm.contact_id 
                 WHERE clm.list_id = ?"""
        cursor.execute(sql, (list_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_contacts_in_list: {e}")
        return []
    finally:
        if conn: conn.close()

# CRUD functions for KPIs
def add_kpi(kpi_data: dict) -> int | None:
    """Adds a new KPI. Returns kpi_id or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO KPIs (
                project_id, name, value, target, trend, unit, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            kpi_data.get('project_id'),
            kpi_data.get('name'),
            kpi_data.get('value'),
            kpi_data.get('target'),
            kpi_data.get('trend'),
            kpi_data.get('unit'),
            now,  # created_at
            now   # updated_at
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_kpi: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_kpi_by_id(kpi_id: int) -> dict | None:
    """Retrieves a KPI by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM KPIs WHERE kpi_id = ?", (kpi_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_kpi_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_kpis_for_project(project_id: str) -> list[dict]:
    """Retrieves all KPIs for a given project_id."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM KPIs WHERE project_id = ?", (project_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_kpis_for_project: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_kpi(kpi_id: int, kpi_data: dict) -> bool:
    """Updates an existing KPI. Sets updated_at. Returns True on success."""
    conn = None
    if not kpi_data:
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        kpi_data['updated_at'] = now

        set_clauses = []
        params = []

        valid_columns = ['project_id', 'name', 'value', 'target', 'trend', 'unit', 'updated_at']
        for key, value in kpi_data.items():
            if key in valid_columns:
                set_clauses.append(f"{key} = ?")
                params.append(value)

        if not set_clauses:
            return False

        sql = f"UPDATE KPIs SET {', '.join(set_clauses)} WHERE kpi_id = ?"
        params.append(kpi_id)

        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_kpi: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_kpi(kpi_id: int) -> bool:
    """Deletes a KPI. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM KPIs WHERE kpi_id = ?", (kpi_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_kpi: {e}")
        return False
    finally:
        if conn:
            conn.close()

# --- ActivityLog Functions ---
def add_activity_log(log_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """INSERT INTO ActivityLog (user_id, action_type, details, related_entity_type, 
                                        related_entity_id, related_client_id, ip_address, user_agent)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (
            log_data.get('user_id'), log_data.get('action_type'), log_data.get('details'),
            log_data.get('related_entity_type'), log_data.get('related_entity_id'),
            log_data.get('related_client_id'), log_data.get('ip_address'), log_data.get('user_agent')
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"DB error in add_activity_log: {e}")
        return None
    finally:
        if conn: conn.close()

def get_activity_logs(limit: int = 50, filters: dict = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM ActivityLog"
        params = []
        where_clauses = []
        if filters:
            allowed = ['user_id', 'action_type', 'related_entity_type', 'related_entity_id', 'related_client_id']
            for key, value in filters.items():
                if key in allowed and value is not None:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
        
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_activity_logs: {e}")
        return []
    finally:
        if conn: conn.close()

# --- CoverPageTemplates CRUD ---
def add_cover_page_template(template_data: dict) -> str | None:
    """Adds a new cover page template. Returns template_id or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        new_template_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat() + "Z"

        style_config = template_data.get('style_config_json')
        if isinstance(style_config, dict): # Ensure it's a JSON string
            style_config = json.dumps(style_config)

        sql = """
            INSERT INTO CoverPageTemplates (
                template_id, template_name, description, default_title, default_subtitle,
                default_author, style_config_json, is_default_template,
                created_at, updated_at, created_by_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_template_id,
            template_data.get('template_name'),
            template_data.get('description'),
            template_data.get('default_title'),
            template_data.get('default_subtitle'),
            template_data.get('default_author'),
            style_config,
            template_data.get('is_default_template', 0), # Handle new field, default to 0
            now, now,
            template_data.get('created_by_user_id')
        )
        cursor.execute(sql, params)
        conn.commit()
        return new_template_id
    except sqlite3.Error as e:
        print(f"Database error in add_cover_page_template: {e}")
        return None
    finally:
        if conn: conn.close()

def get_cover_page_template_by_id(template_id: str) -> dict | None:
    """Retrieves a cover page template by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CoverPageTemplates WHERE template_id = ?", (template_id,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            if data.get('style_config_json'):
                try:
                    data['style_config_json'] = json.loads(data['style_config_json'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse style_config_json for template {template_id}")
                    # Keep as string or set to default dict? For now, keep as is.
            return data
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_cover_page_template_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_cover_page_template_by_name(template_name: str) -> dict | None:
    """Retrieves a cover page template by its unique name."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CoverPageTemplates WHERE template_name = ?", (template_name,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            if data.get('style_config_json'):
                try:
                    data['style_config_json'] = json.loads(data['style_config_json'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse style_config_json for template {template_name}")
            return data
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_cover_page_template_by_name: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_cover_page_templates(is_default: bool = None, limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Retrieves all cover page templates, optionally filtered by is_default.
    Includes pagination.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = "SELECT * FROM CoverPageTemplates"
        params = []

        if is_default is not None:
            sql += " WHERE is_default_template = ?"
            params.append(1 if is_default else 0)

        sql += " ORDER BY template_name LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        templates = []
        for row in rows:
            data = dict(row)
            if data.get('style_config_json'):
                try:
                    data['style_config_json'] = json.loads(data['style_config_json'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse style_config_json for template ID {data['template_id']}")
            templates.append(data)
        return templates
    except sqlite3.Error as e:
        print(f"Database error in get_all_cover_page_templates: {e}")
        return []
    finally:
        if conn: conn.close()

def update_cover_page_template(template_id: str, update_data: dict) -> bool:
    """Updates an existing cover page template."""
    conn = None
    if not update_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        update_data['updated_at'] = datetime.utcnow().isoformat() + "Z"

        if 'style_config_json' in update_data and isinstance(update_data['style_config_json'], dict):
            update_data['style_config_json'] = json.dumps(update_data['style_config_json'])

        # Ensure boolean/integer fields are correctly formatted for SQL if needed
        if 'is_default_template' in update_data:
            update_data['is_default_template'] = 1 if update_data['is_default_template'] else 0

        valid_columns = [
            'template_name', 'description', 'default_title', 'default_subtitle',
            'default_author', 'style_config_json', 'is_default_template', 'updated_at'
            # created_by_user_id is typically not updated this way
        ]

        set_clauses = []
        sql_params = []

        for key, value in update_data.items():
            if key in valid_columns:
                set_clauses.append(f"{key} = ?")
                sql_params.append(value)

        if not set_clauses:
            return False # Nothing valid to update

        sql_params.append(template_id)
        sql = f"UPDATE CoverPageTemplates SET {', '.join(set_clauses)} WHERE template_id = ?"

        cursor.execute(sql, sql_params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_cover_page_template: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_cover_page_template(template_id: str) -> bool:
    """Deletes a cover page template."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Consider impact on CoverPages using this template (ON DELETE SET NULL)
        cursor.execute("DELETE FROM CoverPageTemplates WHERE template_id = ?", (template_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_cover_page_template: {e}")
        return False
    finally:
        if conn: conn.close()

# --- CoverPages CRUD ---
def add_cover_page(cover_data: dict) -> str | None:
    """Adds a new cover page instance. Returns cover_page_id or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        new_cover_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat() + "Z"

        custom_style_config = cover_data.get('custom_style_config_json')
        if isinstance(custom_style_config, dict):
            custom_style_config = json.dumps(custom_style_config)

        sql = """
            INSERT INTO CoverPages (
                cover_page_id, cover_page_name, client_id, project_id, template_id,
                title, subtitle, author_text, institution_text, department_text,
                document_type_text, document_version, creation_date,
                logo_name, logo_data, custom_style_config_json,
                created_at, updated_at, created_by_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_cover_id,
            cover_data.get('cover_page_name'),
            cover_data.get('client_id'),
            cover_data.get('project_id'),
            cover_data.get('template_id'),
            cover_data.get('title'),
            cover_data.get('subtitle'),
            cover_data.get('author_text'),
            cover_data.get('institution_text'),
            cover_data.get('department_text'),
            cover_data.get('document_type_text'),
            cover_data.get('document_version'),
            cover_data.get('creation_date'),
            cover_data.get('logo_name'),
            cover_data.get('logo_data'),
            custom_style_config,
            now, now,
            cover_data.get('created_by_user_id')
        )
        cursor.execute(sql, params)
        conn.commit()
        return new_cover_id
    except sqlite3.Error as e:
        print(f"Database error in add_cover_page: {e}")
        return None
    finally:
        if conn: conn.close()

def get_cover_page_by_id(cover_page_id: str) -> dict | None:
    """Retrieves a cover page instance by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CoverPages WHERE cover_page_id = ?", (cover_page_id,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            if data.get('custom_style_config_json'):
                try:
                    data['custom_style_config_json'] = json.loads(data['custom_style_config_json'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse custom_style_config_json for cover page {cover_page_id}")
            return data
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_cover_page_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_cover_pages_for_client(client_id: str) -> list[dict]:
    """Retrieves all cover pages for a specific client."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CoverPages WHERE client_id = ? ORDER BY created_at DESC", (client_id,))
        rows = cursor.fetchall()
        cover_pages = []
        for row in rows:
            data = dict(row)
            # JSON parsing similar to get_cover_page_by_id if needed
            cover_pages.append(data)
        return cover_pages
    except sqlite3.Error as e:
        print(f"Database error in get_cover_pages_for_client: {e}")
        return []
    finally:
        if conn: conn.close()

def get_cover_pages_for_project(project_id: str) -> list[dict]:
    """Retrieves all cover pages for a specific project."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CoverPages WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
        rows = cursor.fetchall()
        cover_pages = []
        for row in rows:
            data = dict(row)
            # JSON parsing similar to get_cover_page_by_id if needed
            cover_pages.append(data)
        return cover_pages
    except sqlite3.Error as e:
        print(f"Database error in get_cover_pages_for_project: {e}")
        return []
    finally:
        if conn: conn.close()

def update_cover_page(cover_page_id: str, update_data: dict) -> bool:
    """Updates an existing cover page instance."""
    conn = None
    if not update_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        update_data['updated_at'] = datetime.utcnow().isoformat() + "Z"

        if 'custom_style_config_json' in update_data and isinstance(update_data['custom_style_config_json'], dict):
            update_data['custom_style_config_json'] = json.dumps(update_data['custom_style_config_json'])

        set_clauses = [f"{key} = ?" for key in update_data.keys() if key != 'cover_page_id']
        params = [update_data[key] for key in update_data.keys() if key != 'cover_page_id']
        params.append(cover_page_id)

        sql = f"UPDATE CoverPages SET {', '.join(set_clauses)} WHERE cover_page_id = ?"
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_cover_page: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_cover_page(cover_page_id: str) -> bool:
    """Deletes a cover page instance."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM CoverPages WHERE cover_page_id = ?", (cover_page_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_cover_page: {e}")
        return False
    finally:
        if conn: conn.close()

def get_cover_pages_for_user(user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Retrieves cover pages created by a specific user, with pagination."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Querying by 'created_by_user_id' as per the CoverPages table schema
        sql = "SELECT * FROM CoverPages WHERE created_by_user_id = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params = (user_id, limit, offset)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        # It's good practice to parse JSON fields here if any, similar to other get functions
        cover_pages = []
        for row in rows:
            data = dict(row)
            if data.get('custom_style_config_json'):
                try:
                    data['custom_style_config_json'] = json.loads(data['custom_style_config_json'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse custom_style_config_json for cover page {data['cover_page_id']}")
            cover_pages.append(data)
        return cover_pages
    except sqlite3.Error as e:
        print(f"Database error in get_cover_pages_for_user: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_all_templates(template_type_filter: str = None, language_code_filter: str = None) -> list[dict]:
    """
    Retrieves all templates, optionally filtered by template_type and/or language_code.
    If template_type_filter is None, retrieves all templates regardless of type.
    If language_code_filter is None, retrieves for all languages.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM Templates"
        params = []
        where_clauses = []

        if template_type_filter:
            where_clauses.append("template_type = ?")
            params.append(template_type_filter)
        if language_code_filter:
            where_clauses.append("language_code = ?")
            params.append(language_code_filter)

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY template_name, language_code"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_templates: {e}")
        return []
    finally:
        if conn: conn.close()

def get_distinct_languages_for_template_type(template_type: str) -> list[str]:
    """
    Retrieves a list of distinct language codes available for a given template type.
    """
    conn = None
    languages = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT language_code FROM Templates WHERE template_type = ? ORDER BY language_code ASC", (template_type,))
        rows = cursor.fetchall()
        languages = [row['language_code'] for row in rows if row['language_code']] # Ensure not None
    except sqlite3.Error as e:
        print(f"Database error in get_distinct_languages_for_template_type for type '{template_type}': {e}")
        # Return empty list on error
    finally:
        if conn:
            conn.close()
    return languages

def get_all_file_based_templates() -> list[dict]:
    """Retrieves all templates that have a base_file_name, suitable for document creation."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Selects templates that are likely file-based documents
        # Changed 'category' to 'category_id'.
        # If category_name is needed here, a JOIN with TemplateCategories would be required.
        sql = "SELECT template_id, template_name, language_code, base_file_name, description, category_id FROM Templates WHERE base_file_name IS NOT NULL AND base_file_name != '' ORDER BY template_name, language_code"
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_file_based_templates: {e}")
        return []
    finally:
        if conn: conn.close()

def get_templates_by_category_id(category_id: int) -> list[dict]:
    """Retrieves all templates for a given category_id."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Templates WHERE category_id = ? ORDER BY template_name, language_code", (category_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_templates_by_category_id: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_all_tasks(active_only: bool = False, project_id_filter: str = None) -> list[dict]:
    """
    Retrieves all tasks, optionally filtering for active tasks only and/or by project_id.
    Active tasks are those not linked to a status marked as completion or archival.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT t.* FROM Tasks t"
        params = []
        where_clauses = []

        if active_only:
            sql += """
                LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id
            """
            where_clauses.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")

        if project_id_filter:
            where_clauses.append("t.project_id = ?")
            params.append(project_id_filter)

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY t.created_at DESC" # Or some other meaningful order

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_tasks: {e}")
        return []
    finally:
        if conn: conn.close()

def get_tasks_by_assignee_id(assignee_team_member_id: int, active_only: bool = False) -> list[dict]:
    """
    Retrieves tasks assigned to a specific team member, optionally filtering for active tasks.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT t.* FROM Tasks t"
        params = []
        where_clauses = ["t.assignee_team_member_id = ?"]
        params.append(assignee_team_member_id)

        if active_only:
            sql += """
                LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id
            """
            where_clauses.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")

        if where_clauses: # Will always be true because of assignee_team_member_id
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY t.due_date ASC, t.priority DESC"

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_tasks_by_assignee_id: {e}")
        return []
    finally:
        if conn: conn.close()

def get_all_status_settings(status_type: str = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT status_id, status_name, status_type, color_hex, icon_name, default_duration_days, is_archival_status, is_completion_status FROM StatusSettings" # Ensure icon_name is fetched
        params = []
        if status_type:
            sql += " WHERE status_type = ?"
            params.append(status_type)
        sql += " ORDER BY status_type, status_name"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_all_status_settings: {e}")
        return []
    finally:
        if conn: conn.close()

def get_status_setting_by_id(status_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status_id, status_name, status_type, color_hex, icon_name, default_duration_days, is_archival_status, is_completion_status FROM StatusSettings WHERE status_id = ?", (status_id,)) # Ensure icon_name is fetched
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_status_setting_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_status_setting_by_name(status_name: str, status_type: str) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status_id, status_name, status_type, color_hex, icon_name, default_duration_days, is_archival_status, is_completion_status FROM StatusSettings WHERE status_name = ? AND status_type = ?", (status_name, status_type)) # Ensure icon_name is fetched
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_status_setting_by_name: {e}")
        return None
    finally:
        if conn: conn.close()

# --- Document Context Data Function ---

def format_currency(amount: float | None, symbol: str = "€", precision: int = 2) -> str:
    """Formats a numerical amount into a currency string."""
    if amount is None:
        return ""
    return f"{symbol}{amount:,.{precision}f}"

def get_document_context_data(
    client_id: str,
    company_id: str, # For seller info
    target_language_code: str, # New parameter
    project_id: str = None,
    # product_ids: list[int] = None, # This might be ClientProjectProducts IDs if only specific items are part of the proforma
    linked_product_ids_for_doc: list[int] = None, # Use this for specific ClientProjectProducts line items
    additional_context: dict = None
) -> dict:
    """
    Gathers and structures data for document generation, with product language resolution.
    and specific handling for packing list details if provided in additional_context.

    """
    context = {
        "doc": {}, "client": {}, "seller": {}, "project": {}, "products": [],
        "additional": additional_context if isinstance(additional_context, dict) else {}
    }
    now_dt = datetime.now()

    # Initialize common document fields
    context["doc"]["current_date"] = now_dt.strftime("%Y-%m-%d")
    context["doc"]["current_year"] = str(now_dt.year)
    context["doc"]["document_title"] = context["additional"].get("document_title", "Document") # Default title
    context["doc"]["document_subtitle"] = context["additional"].get("document_subtitle", "")
    context["doc"]["document_version"] = context["additional"].get("document_version", "1.0")

    # Initialize financial/terms fields (primarily for proforma/invoice but can be overridden)
    context["doc"]["currency_symbol"] = context["additional"].get("currency_symbol", "€")
    context["doc"]["vat_rate_percentage"] = context["additional"].get("vat_rate_percentage", 20.0)
    context["doc"]["discount_rate_percentage"] = context["additional"].get("discount_rate_percentage", 0.0)
    context["doc"]["proforma_id"] = context["additional"].get("proforma_id", f"PRO-{now_dt.strftime('%Y%m%d-%H%M%S')}")
    context["doc"]["invoice_id"] = context["additional"].get("invoice_id", f"INV-{now_dt.strftime('%Y%m%d-%H%M%S')}")
    context["doc"]["payment_terms"] = context["additional"].get("payment_terms", "Net 30 Days")
    context["doc"]["delivery_terms"] = context["additional"].get("delivery_terms", "FOB Port of Loading")
    context["doc"]["incoterms"] = context["additional"].get("incoterms", "FOB")
    context["doc"]["named_place_of_delivery"] = context["additional"].get("named_place_of_delivery", "Port of Loading")

    # Initialize packing list specific fields (will be populated if packing_details are provided)
    context["doc"]["packing_list_id"] = context["additional"].get("packing_list_id", f"PL-{now_dt.strftime('%Y%m%d-%H%M%S')}")
    context["doc"]["notify_party_name"] = "N/A"
    context["doc"]["notify_party_address"] = "N/A"
    context["doc"]["vessel_flight_no"] = "N/A"
    context["doc"]["port_of_loading"] = "N/A"
    context["doc"]["port_of_discharge"] = "N/A"
    context["doc"]["final_destination_country"] = "N/A"
    context["doc"]["total_packages"] = "N/A"
    context["doc"]["total_net_weight"] = "N/A"
    context["doc"]["total_gross_weight"] = "N/A"
    context["doc"]["total_volume_cbm"] = "N/A"
    context["doc"]["packing_list_items"] = f"<tr><td colspan='7'>Packing details not provided.</td></tr>" # Default HTML for table body

    # Warranty specific placeholders (can be overridden by additional_context)
    context["doc"]["warranty_certificate_id"] = context["additional"].get("warranty_id", f"WAR-{now_dt.strftime('%Y%m%d-%H%M%S')}")
    context["doc"]["warranty_period_months"] = context["additional"].get("warranty_period_months", "12")
    # ... (other warranty fields as before, using .get from context['additional'] or context['doc'] if already set)

    # --- Fetch Seller (Our User's Company) Information ---
    seller_company_data = get_company_by_id(company_id)
    if seller_company_data:
        context["seller"]["name"] = seller_company_data.get('company_name', "N/A")
        context["seller"]["company_name"] = seller_company_data.get('company_name', "N/A")
        raw_address = seller_company_data.get('address', "N/A")
        context["seller"]["address"] = raw_address
        context["seller"]["address_line1"] = raw_address # Simplistic, assumes address is single line
        context["seller"]["city_zip_country"] = "N/A (Structure adr. manquante)" # Placeholder
        # TODO: Parse raw_address or add structured fields (city, zip, country) to Companies table
        context["seller"]["full_address"] = raw_address # For templates that use a single full address block

        context["seller"]["payment_info"] = seller_company_data.get('payment_info')
        context["seller"]["other_info"] = seller_company_data.get('other_info')

        logo_path_relative = seller_company_data.get('logo_path')
        context["seller"]["logo_path_relative"] = logo_path_relative
        if logo_path_relative:
            abs_logo_path = os.path.join(APP_ROOT_DIR_CONTEXT, LOGO_SUBDIR_CONTEXT, logo_path_relative)
            if os.path.exists(abs_logo_path):
                 context["seller"]["logo_path_absolute"] = abs_logo_path
                 context["seller"]["company_logo_path"] = f"file:///{abs_logo_path.replace(os.sep, '/')}"
            else:
                 context["seller"]["logo_path_absolute"] = None
                 context["seller"]["company_logo_path"] = None # Or a default/placeholder logo URL
                 print(f"Warning: Seller logo file not found at {abs_logo_path}")
        else:
            context["seller"]["logo_path_absolute"] = None
            context["seller"]["company_logo_path"] = None

        # More specific seller details (assuming they might be in 'other_info' or need new schema fields)
        # For now, providing placeholders or deriving from existing if possible.
        context["seller"]["phone"] = context["additional"].get("seller_phone", "N/A Seller Phone")
        context["seller"]["email"] = context["additional"].get("seller_email", "N/A Seller Email")
        context["seller"]["vat_id"] = context["additional"].get("seller_vat_id", "N/A Seller VAT ID")
        context["seller"]["registration_number"] = context["additional"].get("seller_registration_number", "N/A Seller Reg No.")

        context["seller"]["bank_details_raw"] = seller_company_data.get('payment_info', "N/A")
        context["seller"]["bank_name"] = context["additional"].get("seller_bank_name", "N/A Bank")
        context["seller"]["bank_account_number"] = context["additional"].get("seller_bank_account_number", "N/A Account No.")
        context["seller"]["bank_swift_bic"] = context["additional"].get("seller_bank_swift_bic", "N/A SWIFT/BIC")
        context["seller"]["bank_address"] = context["additional"].get("seller_bank_address", "N/A Bank Address")
        context["seller"]["bank_account_holder_name"] = context["seller"]["company_name"] # Default to company name

        context["seller"]["footer_company_name"] = context["seller"]["company_name"]
        context["seller"]["footer_contact_info"] = f"{context['seller']['phone']} | {context['seller']['email']}"
        context["seller"]["footer_additional_info"] = seller_company_data.get('other_info', "")

    # --- Fetch Seller Personnel (from CompanyPersonnel) ---
    # Using a general personnel dictionary within seller context
    context["seller"]["personnel"] = {}
    seller_personnel_list = get_personnel_for_company(company_id) # Get all personnel
    if seller_personnel_list:
        # Example: find first person with role 'seller' or default to first person
        main_seller_contact = next((p for p in seller_personnel_list if p.get('role') == 'seller'), seller_personnel_list[0])
        context["seller"]["personnel"]["representative_name"] = main_seller_contact.get('name')
        context["seller"]["personnel"]["representative_title"] = main_seller_contact.get('role') # Or a more specific title if available

        # For specific roles mentioned in templates
        context["seller"]["personnel"]["sales_person_name"] = next((p.get('name') for p in seller_personnel_list if p.get('role') == 'seller'), "N/A")
        context["seller"]["personnel"]["technical_manager_name"] = next((p.get('name') for p in seller_personnel_list if p.get('role') == 'technical_manager'), "N/A")
        # Generic authorized signatory for some docs (can be overridden by additional_context)
        context["seller"]["personnel"]["authorized_signature_name"] = context["seller"]["personnel"]["sales_person_name"]
        context["seller"]["personnel"]["authorized_signature_title"] = next((p.get('role') for p in seller_personnel_list if p.get('name') == context["seller"]["personnel"]["authorized_signature_name"]), "N/A")

    else: # No personnel found
        context["seller"]["personnel"]["representative_name"] = "N/A"
        context["seller"]["personnel"]["representative_title"] = "N/A"
        context["seller"]["personnel"]["sales_person_name"] = "N/A"
        context["seller"]["personnel"]["technical_manager_name"] = "N/A"
        context["seller"]["personnel"]["authorized_signature_name"] = "N/A"
        context["seller"]["personnel"]["authorized_signature_title"] = "N/A"

    # --- Fetch Client Information (The Buyer/Consignee) ---
    # This is 'client_id' passed to the function
    client_data = get_client_by_id(client_id)
    if client_data:
        context["client"]["id"] = client_data.get('client_id')
        # Distinguish between contact person name and company name
        context["client"]["contact_person_name"] = client_data.get('client_name') # client_name from Clients table is often a person
        context["client"]["company_name"] = client_data.get('company_name', client_data.get('client_name')) # Fallback to client_name if company_name is empty

        context["client"]["project_identifier"] = client_data.get('project_identifier')
        context["client"]["primary_need"] = client_data.get('primary_need_description')
        context["client"]["notes"] = client_data.get('notes')
        context["client"]["price_formatted"] = format_currency(client_data.get('price'), context["doc"]["currency_symbol"])
        context["client"]["raw_price"] = client_data.get('price')

        client_country_name, client_city_name = "N/A", "N/A"
        if client_data.get('country_id'):
            country = get_country_by_id(client_data['country_id'])
            if country: client_country_name = country.get('country_name', "N/A")
        if client_data.get('city_id'):
            city = get_city_by_id(client_data['city_id'])
            if city: client_city_name = city.get('city_name', "N/A")

        context["client"]["country_name"] = client_country_name
        context["client"]["city_name"] = client_city_name
        # Construct full_address (assuming 'address' field in Clients table is missing, using city/country)
        # This would be improved if Clients table had a full 'address' field or structured address.
        address_parts = [part for part in [client_city_name, client_country_name] if part != "N/A"]
        context["client"]["address"] = ", ".join(address_parts) if address_parts else "N/A (Adresse manquante)"
        context["client"]["city_zip_country"] = context["client"]["address"] # Simplified

        # Client contact details (primary contact from Contacts table)
        client_contacts = get_contacts_for_client(client_id)
        primary_client_contact = next((c for c in client_contacts if c.get('is_primary_for_client')), None)
        if not primary_client_contact and client_contacts: primary_client_contact = client_contacts[0]

        if primary_client_contact:
            # Override client.contact_person_name if a more specific primary contact exists
            context["client"]["contact_person_name"] = primary_client_contact.get('name', client_data.get('client_name')) # Fallback to client_name if primary contact name is empty
            context["client"]["contact_email"] = primary_client_contact.get('email', "N/A")
            context["client"]["contact_phone"] = primary_client_contact.get('phone', "N/A")
            context["client"]["contact_position"] = primary_client_contact.get('position', "N/A")
        else:
            context["client"]["contact_email"] = "N/A"
            context["client"]["contact_phone"] = "N/A"
            context["client"]["contact_position"] = "N/A"

        context["client"]["vat_id"] = context["additional"].get("client_vat_id", "N/A Client VAT ID")
        context["client"]["registration_number"] = context["additional"].get("client_registration_number", "N/A Client Reg No.")
        context["client"]["full_address"] = context["client"]["address"] # For templates that use a single full address block


        # Buyer representative details (often the primary contact)
        context["client"]["representative_name"] = context["client"].get("contact_person_name", client_data.get('client_name'))
        context["client"]["representative_title"] = context["client"]["contact_position"]

    # --- Fetch Project Information (if project_id is provided) ---
    if project_id:
        project_data = get_project_by_id(project_id)
        if project_data:
            context["project"]["name"] = project_data.get('project_name')
            context["project"]["id"] = project_data.get('project_id')
            context["project"]["description"] = project_data.get('description')
            context["project"]["start_date"] = project_data.get('start_date')
            context["project"]["deadline_date"] = project_data.get('deadline_date')
            context["project"]["budget_formatted"] = format_currency(project_data.get('budget'), context["doc"]["currency_symbol"])
            context["project"]["raw_budget"] = project_data.get('budget')
            context["project"]["progress_percentage"] = project_data.get('progress_percentage')
            context["project"]["manager_id"] = project_data.get('manager_team_member_id') # Needs fetch for name

            status_id = project_data.get('status_id')
            status_info = get_status_setting_by_id(status_id) if status_id else None
            context["project"]["status_name"] = status_info.get('status_name') if status_info else "N/A"
    else: # No project_id, provide defaults for project fields
        context["project"]["name"] = context["additional"].get("project_name", client_data.get('project_identifier', "N/A") if client_data else "N/A") # Fallback to project_identifier
        context["project"]["description"] = context["additional"].get("project_description", client_data.get('primary_need_description', "") if client_data else "")

    # --- Contact Page Specific Details from additional_context ---
    contact_page_details_from_context = context["additional"].get('contact_page_details', {})
    if contact_page_details_from_context: # Check if contact_page_details key exists
        # Override document title if provided
        doc_title_override = contact_page_details_from_context.get('document_title_override')
        if doc_title_override:
            context["doc"]["document_title"] = doc_title_override

        # Override project name if provided
        project_name_override = contact_page_details_from_context.get('project_name_override')
        if project_name_override:
            context["project"]["name"] = project_name_override # Overrides previous project name

        # Populate contact_list_items_html
        contacts_for_page = contact_page_details_from_context.get('contacts', [])
        if contacts_for_page:
            html_rows = []
            for contact_detail in contacts_for_page:
                row_html = "<tr>"
                row_html += f"<td>{contact_detail.get('role_org', '')}</td>"
                row_html += f"<td>{contact_detail.get('name', '')}</td>"
                row_html += f"<td>{contact_detail.get('title', '')}</td>"
                row_html += f"<td>{contact_detail.get('email', '')}</td>"
                row_html += f"<td>{contact_detail.get('phone', '')}</td>"
                row_html += "</tr>"
                html_rows.append(row_html)
            context['doc']['contact_list_items_html'] = "".join(html_rows)
        else:
            context['doc']['contact_list_items_html'] = '<tr><td colspan="5">Contact details not provided.</td></tr>'
    else:
        # Ensure the field exists even if no contact_page_details were provided, for templates that might use it
        context['doc']['contact_list_items_html'] = '<tr><td colspan="5">Contact page details not applicable or not provided.</td></tr>'


    # --- Fetch Products and Generate HTML Rows ---
    # This section will be skipped if contact_page_details dictates a different flow,
    # or product processing might be different for contact pages (e.g. no products).
    # For now, assuming contact pages might not typically list products in the same way.
    # The existing logic for packing_details and standard products will follow.
    fetched_products_data = []
    # ... (rest of the initial context["doc"] setup as before) ...
    now_dt = datetime.now()
    context["doc"]["current_date"] = now_dt.strftime("%Y-%m-%d")
    context["doc"]["current_year"] = str(now_dt.year)
    context["doc"]["currency_symbol"] = context["additional"].get("currency_symbol", "€")
    context["doc"]["vat_rate_percentage"] = context["additional"].get("vat_rate_percentage", 20.0)
    context["doc"]["discount_rate_percentage"] = context["additional"].get("discount_rate_percentage", 0.0)
    # ... (other context["doc"] fields) ...

    # --- Fetch Seller (Our User's Company) Information ---
    # ... (seller info fetching as before) ...
    seller_company_data = get_company_by_id(company_id)
    if seller_company_data:
        context["seller"]["name"] = seller_company_data.get('company_name', "N/A")
        # ... (populate rest of seller fields) ...
        # Simplified for brevity
        context["seller"]["company_logo_path"] = f"file:///{os.path.join(APP_ROOT_DIR_CONTEXT, LOGO_SUBDIR_CONTEXT, seller_company_data.get('logo_path',''))}" if seller_company_data.get('logo_path') else ""


    # --- Fetch Client Information (The Buyer/Consignee) ---
    # ... (client info fetching as before) ...
    client_data = get_client_by_id(client_id)
    if client_data:
        context["client"]["id"] = client_data.get('client_id')
        # ... (populate rest of client fields) ...


    # --- Fetch Project Information (if project_id is provided) ---
    # ... (project info fetching as before) ...
    if project_id:
        project_data = get_project_by_id(project_id)
        if project_data:
            context["project"]["name"] = project_data.get('project_name')
            # ... (populate rest of project fields) ...
    else:
        context["project"]["name"] = client_data.get('project_identifier', "N/A") if client_data else "N/A"


    # --- Enhanced Product Fetching and Language Resolution ---
    linked_products_query_result = []
    if linked_product_ids_for_doc: # Fetch specific linked products if IDs are provided
        conn_temp = get_db_connection()
        cursor_temp = conn_temp.cursor()
        for link_id in linked_product_ids_for_doc:
            cursor_temp.execute("""
                SELECT cpp.*, p.product_name AS original_product_name, p.description AS original_description,
                       p.language_code AS original_language_code, p.weight, p.dimensions,
                       p.base_unit_price, p.unit_of_measure
                FROM ClientProjectProducts cpp
                JOIN Products p ON cpp.product_id = p.product_id
                WHERE cpp.client_project_product_id = ?
            """, (link_id,))
            row = cursor_temp.fetchone()
            if row:
                linked_products_query_result.append(dict(row))
        conn_temp.close()
    else: # Fetch all for client/project
        linked_products_query_result = get_products_for_client_or_project(client_id, project_id)
        # get_products_for_client_or_project already joins with Products and fetches its columns.
        # We need to ensure it fetches original_language_code, original_product_name, original_description
        # and the new weight/dimensions. The alias for Products table is 'p'.
        # The previous subtask updated get_products_for_client_or_project to include p.weight, p.dimensions.
        # It also implicitly included p.language_code, p.product_name, p.description.

    products_table_html_rows = ""
    subtotal_amount_calculated = 0.0
    item_counter = 0

    for linked_prod_data in linked_products_query_result:
        item_counter += 1
        original_product_id = linked_prod_data['product_id'] # This is the ID of the product in its original language
        original_lang_code = linked_prod_data.get('language_code') # Language of the product in Products table for this link

        product_name_for_doc = linked_prod_data.get('product_name') # Default to original
        product_description_for_doc = linked_prod_data.get('product_description') # Default to original
        is_language_match = (original_lang_code == target_language_code)

        if not is_language_match:
            equivalents = get_equivalent_products(original_product_id)
            found_equivalent_in_target_lang = False
            for eq_prod in equivalents:
                if eq_prod.get('language_code') == target_language_code:
                    product_name_for_doc = eq_prod.get('product_name')
                    product_description_for_doc = eq_prod.get('description')
                    is_language_match = True # Now it's a match because we found an equivalent
                    found_equivalent_in_target_lang = True
                    break
            if not found_equivalent_in_target_lang:
                # No equivalent found in target language, is_language_match remains False.
                # product_name_for_doc and product_description_for_doc retain original language values.
                print(f"Warning: No equivalent found for product ID {original_product_id} in target language {target_language_code}.")


        quantity = linked_prod_data.get('quantity', 1)
        unit_price_override = linked_prod_data.get('unit_price_override')
        base_unit_price = linked_prod_data.get('base_unit_price')

        effective_unit_price = unit_price_override if unit_price_override is not None else base_unit_price
        try:
            unit_price_float = float(effective_unit_price) if effective_unit_price is not None else 0.0
        except ValueError:
            unit_price_float = 0.0

        total_price = quantity * unit_price_float
        subtotal_amount_calculated += total_price

        products_table_html_rows += f"""<tr>
            <td>{item_counter}</td>
            <td>{product_name_for_doc if product_name_for_doc else 'N/A'}</td>
            <td>{quantity}</td>
            <td>{format_currency(unit_price_float, context["doc"]["currency_symbol"])}</td>
            <td>{format_currency(total_price, context["doc"]["currency_symbol"])}</td>
        </tr>"""

        context["products"].append({
            "id": original_product_id,
            "name": product_name_for_doc,
            "description": product_description_for_doc,
            "quantity": quantity,
            "unit_price_formatted": format_currency(unit_price_float, context["doc"]["currency_symbol"]),
            "total_price_formatted": format_currency(total_price, context["doc"]["currency_symbol"]),
            "raw_unit_price": unit_price_float,
            "raw_total_price": total_price,
            "unit_of_measure": linked_prod_data.get('unit_of_measure'),
            "weight": linked_prod_data.get('weight'), # From joined Products table
            "dimensions": linked_prod_data.get('dimensions'), # From joined Products table
            "is_language_match": is_language_match
        })

    context["doc"]["products_table_rows"] = products_table_html_rows
    context["doc"]["subtotal_amount"] = format_currency(subtotal_amount_calculated, context["doc"]["currency_symbol"])
    # ... (rest of currency calculations and context population as before) ...

    discount_rate = context["doc"]["discount_rate_percentage"] / 100.0
    discount_amount_calculated = subtotal_amount_calculated * discount_rate
    context["doc"]["discount_amount"] = format_currency(discount_amount_calculated, context["doc"]["currency_symbol"])

    amount_after_discount = subtotal_amount_calculated - discount_amount_calculated

    vat_rate = context["doc"]["vat_rate_percentage"] / 100.0
    vat_amount_calculated = amount_after_discount * vat_rate
    context["doc"]["vat_amount"] = format_currency(vat_amount_calculated, context["doc"]["currency_symbol"])

    grand_total_amount_calculated = amount_after_discount + vat_amount_calculated
    context["doc"]["grand_total_amount"] = format_currency(grand_total_amount_calculated, context["doc"]["currency_symbol"])
    context["doc"]["grand_total_amount_words"] = "N/A (Number to words not implemented)" # Placeholder

    # ... (packing list and warranty specific placeholders as before) ...
    # ... (common template placeholder mappings as before) ...

    fetched_products_data = []
    # ... (rest of the initial context["doc"] setup as before) ...
    now_dt = datetime.now()
    context["doc"]["current_date"] = now_dt.strftime("%Y-%m-%d")
    context["doc"]["current_year"] = str(now_dt.year)
    context["doc"]["currency_symbol"] = context["additional"].get("currency_symbol", "€")
    context["doc"]["vat_rate_percentage"] = context["additional"].get("vat_rate_percentage", 20.0)
    context["doc"]["discount_rate_percentage"] = context["additional"].get("discount_rate_percentage", 0.0)
    # ... (other context["doc"] fields) ...

    # --- Fetch Seller (Our User's Company) Information ---
    # ... (seller info fetching as before, simplified for brevity) ...
    seller_company_data = get_company_by_id(company_id)
    if seller_company_data:
        context["seller"]["company_name"] = seller_company_data.get('company_name', "N/A")
        context["seller"]["full_address"] = seller_company_data.get('address', "N/A")
        context["seller"]["company_phone"] = context["additional"].get("seller_phone", "N/A") # Assuming these are passed if needed
        context["seller"]["company_email"] = context["additional"].get("seller_email", "N/A")
        context["seller"]["vat_id"] = context["additional"].get("seller_vat_id", "N/A")
        logo_path_relative = seller_company_data.get('logo_path')
        context["seller"]["company_logo_path"] = f"file:///{os.path.join(APP_ROOT_DIR_CONTEXT, LOGO_SUBDIR_CONTEXT, logo_path_relative)}" if logo_path_relative and os.path.exists(os.path.join(APP_ROOT_DIR_CONTEXT, LOGO_SUBDIR_CONTEXT, logo_path_relative)) else ""
        # ... other seller fields
        seller_personnel_list = get_personnel_for_company(company_id)
        if seller_personnel_list:
             main_seller_contact = next((p for p in seller_personnel_list if p.get('role') == 'seller'), seller_personnel_list[0])
             context["seller"]["personnel"] = {"representative_name": main_seller_contact.get('name', 'N/A')} # Simplified
        else:
            context["seller"]["personnel"] = {"representative_name": "N/A"}


    # --- Fetch Client Information ---
    client_data = get_client_by_id(client_id)
    if client_data:
        context["client"]["name"] = client_data.get('client_name') # Typically person name
        context["client"]["company_name"] = client_data.get('company_name', client_data.get('client_name'))
        # ... other client fields ...
        client_country_name, client_city_name = "N/A", "N/A"
        if client_data.get('country_id'):
            country = get_country_by_id(client_data['country_id'])
            if country: client_country_name = country.get('country_name', "N/A")
        if client_data.get('city_id'):
            city = get_city_by_id(client_data['city_id'])
            if city: client_city_name = city.get('city_name', "N/A")
        address_parts = [part for part in [client_data.get('company_name', client_data.get('client_name')), client_city_name, client_country_name] if part and part != "N/A"]
        context["client"]["full_address"] = ", ".join(address_parts) if address_parts else "N/A"

        client_contacts = get_contacts_for_client(client_id)
        primary_client_contact = next((c for c in client_contacts if c.get('is_primary_for_client')), client_contacts[0] if client_contacts else None)
        if primary_client_contact:
            context["client"]["contact_person_name"] = primary_client_contact.get('name', client_data.get('client_name'))
            context["client"]["contact_position"] = primary_client_contact.get('position', "N/A")
            context["client"]["contact_phone"] = primary_client_contact.get('phone', "N/A")
            context["client"]["contact_email"] = primary_client_contact.get('email', "N/A")
        context["client"]["vat_id"] = context["additional"].get("client_vat_id", "N/A")


    # --- Fetch Project Information ---
    if project_id:
        project_data = get_project_by_id(project_id)
        if project_data:
            context["project"]["id"] = project_data.get('project_id')
            context["project"]["name"] = project_data.get('project_name', client_data.get('project_identifier', 'N/A') if client_data else 'N/A')
    else:
        context["project"]["id"] = client_data.get('project_identifier', 'N/A') if client_data else 'N/A'
        context["project"]["name"] = client_data.get('project_identifier', 'N/A') if client_data else 'N/A'


    # --- Packing List Specific Fields from additional_context ---
    packing_details_from_context = context["additional"].get('packing_details', {})
    context["doc"]["notify_party_name"] = packing_details_from_context.get('notify_party_name', 'N/A')
    context["doc"]["notify_party_address"] = packing_details_from_context.get('notify_party_address', 'N/A')
    context["doc"]["vessel_flight_no"] = packing_details_from_context.get('vessel_flight_no', 'N/A')
    context["doc"]["port_of_loading"] = packing_details_from_context.get('port_of_loading', 'N/A')
    context["doc"]["port_of_discharge"] = packing_details_from_context.get('port_of_discharge', 'N/A')
    context["doc"]["final_destination_country"] = packing_details_from_context.get('final_destination_country', 'N/A')

    context["doc"]["total_packages"] = packing_details_from_context.get('total_packages', 'N/A')
    context["doc"]["total_net_weight"] = str(packing_details_from_context.get('total_net_weight_kg', 'N/A')) + ' kg'
    context["doc"]["total_gross_weight"] = str(packing_details_from_context.get('total_gross_weight_kg', 'N/A')) + ' kg'
    context["doc"]["total_volume_cbm"] = str(packing_details_from_context.get('total_volume_cbm', 'N/A')) + ' CBM'

    # --- Process Products for Proforma/Invoice (if not a packing list specific flow) OR Packing List Items ---
    packing_list_items_html_accumulator = ""
    if 'packing_details' in context["additional"] and 'items' in context["additional"]['packing_details']:
        # This is a Packing List, build HTML rows from packing_details.items
        for item_idx, item_detail in enumerate(context["additional"]['packing_details']['items']):
            product_name_for_item = item_detail.get('product_name_override', 'N/A')
            is_item_lang_match = True # Assume override is in target lang, or it's not language sensitive

            if not product_name_for_item and item_detail.get('product_id'):
                original_item_product_details = get_product_by_id(item_detail['product_id'])
                if original_item_product_details:
                    product_name_for_item = original_item_product_details.get('product_name')
                    item_original_lang_code = original_item_product_details.get('language_code')
                    is_item_lang_match = (item_original_lang_code == target_language_code)
                    if not is_item_lang_match:
                        item_equivalents = get_equivalent_products(item_detail['product_id'])
                        for eq_item_prod in item_equivalents:
                            if eq_item_prod.get('language_code') == target_language_code:
                                product_name_for_item = eq_item_prod.get('product_name')
                                # Description for packing list item usually comes from quantity_description
                                is_item_lang_match = True
                                break

            desc_for_packing_list = product_name_for_item
            if item_detail.get('quantity_description'):
                desc_for_packing_list += f" ({item_detail.get('quantity_description')})"
            if not is_item_lang_match and item_detail.get('product_id'): # Add warning if name is not in target lang
                 desc_for_packing_list += f" <em style='font-size:8pt; color:red;'>(lang: {original_item_product_details.get('language_code', '?')})</em>"


            packing_list_items_html_accumulator += f"""<tr>
                <td>{item_detail.get('marks_nos', '')}</td>
                <td>{desc_for_packing_list}</td>
                <td class="number">{item_detail.get('num_packages', '')}</td>
                <td>{item_detail.get('package_type', '')}</td>
                <td class="number">{item_detail.get('net_weight_kg_item', '')}</td>
                <td class="number">{item_detail.get('gross_weight_kg_item', '')}</td>
                <td>{item_detail.get('dimensions_cm_item', '')}</td>
            </tr>"""
        context['doc']['packing_list_items'] = packing_list_items_html_accumulator if packing_list_items_html_accumulator else "<tr><td colspan='7'>Aucun détail d'article de colisage fourni.</td></tr>"

    else: # Standard product processing (e.g., for Proforma, Invoice, general specs)
        # ... (existing product processing logic for proforma/invoice/general specs) ...
        # This part remains largely the same as before, fetching products based on client/project/linked_product_ids
        # and then doing language resolution for name/description and populating context['products'] and context['doc']['products_table_rows']
        # This section should NOT overwrite context['doc']['packing_list_items'] if already populated.

        # Standard product fetching (if not a packing list with specific items)
        standard_fetched_products = []
        if linked_product_ids_for_doc: # If specific ClientProjectProduct IDs are given
            conn_temp_std = get_db_connection()
            cursor_temp_std = conn_temp_std.cursor()
            for link_id in linked_product_ids_for_doc:
                 cursor_temp_std.execute("""
                    SELECT cpp.*, p.product_name, p.description, p.language_code, p.weight, p.dimensions,
                           p.base_unit_price, p.unit_of_measure
                    FROM ClientProjectProducts cpp
                    JOIN Products p ON cpp.product_id = p.product_id
                    WHERE cpp.client_project_product_id = ?
                """, (link_id,))
                 row_std = cursor_temp_std.fetchone()
                 if row_std: standard_fetched_products.append(dict(row_std))
            conn_temp_std.close()
        else:
            standard_fetched_products = get_products_for_client_or_project(client_id, project_id)

        products_table_html_rows = ""
        subtotal_amount_calculated = 0.0
        item_counter = 0
        # Clear context products before repopulating for standard documents
        context["products"] = []

        for prod_data in standard_fetched_products:
            item_counter += 1
            original_product_id = prod_data['product_id']
            original_lang_code = prod_data.get('language_code')

            product_name_for_doc = prod_data.get('product_name')
            product_description_for_doc = prod_data.get('description')
            is_language_match = (original_lang_code == target_language_code)

            if not is_language_match:
                equivalents = get_equivalent_products(original_product_id)
                for eq_prod in equivalents:
                    if eq_prod.get('language_code') == target_language_code:
                        product_name_for_doc = eq_prod.get('product_name')
                        product_description_for_doc = eq_prod.get('description')
                        is_language_match = True
                        break

            quantity = prod_data.get('quantity', 1)
            unit_price_override = prod_data.get('unit_price_override')
            base_unit_price = prod_data.get('base_unit_price')
            effective_unit_price = unit_price_override if unit_price_override is not None else base_unit_price
            unit_price_float = float(effective_unit_price) if effective_unit_price is not None else 0.0
            total_price = quantity * unit_price_float
            subtotal_amount_calculated += total_price

            products_table_html_rows += f"""<tr>
                <td>{item_counter}</td>
                <td>{product_name_for_doc if product_name_for_doc else 'N/A'}</td>
                <td>{quantity}</td>
                <td>{format_currency(unit_price_float, context["doc"]["currency_symbol"])}</td>
                <td>{format_currency(total_price, context["doc"]["currency_symbol"])}</td>
            </tr>"""

            context["products"].append({
                "id": original_product_id, "name": product_name_for_doc, "description": product_description_for_doc,
                "quantity": quantity,
                "unit_price_formatted": format_currency(unit_price_float, context["doc"]["currency_symbol"]),
                "total_price_formatted": format_currency(total_price, context["doc"]["currency_symbol"]),
                "raw_unit_price": unit_price_float, "raw_total_price": total_price,
                "unit_of_measure": prod_data.get('unit_of_measure'),
                "weight": prod_data.get('weight'), "dimensions": prod_data.get('dimensions'),
                "is_language_match": is_language_match
            })

        context["doc"]["products_table_rows"] = products_table_html_rows
        context["doc"]["subtotal_amount"] = format_currency(subtotal_amount_calculated, context["doc"]["currency_symbol"])

        discount_rate = context["doc"]["discount_rate_percentage"] / 100.0
        discount_amount_calculated = subtotal_amount_calculated * discount_rate
        context["doc"]["discount_amount"] = format_currency(discount_amount_calculated, context["doc"]["currency_symbol"])
        amount_after_discount = subtotal_amount_calculated - discount_amount_calculated
        vat_rate = context["doc"]["vat_rate_percentage"] / 100.0
        vat_amount_calculated = amount_after_discount * vat_rate
        context["doc"]["vat_amount"] = format_currency(vat_amount_calculated, context["doc"]["currency_symbol"])
        grand_total_amount_calculated = amount_after_discount + vat_amount_calculated
        context["doc"]["grand_total_amount"] = format_currency(grand_total_amount_calculated, context["doc"]["currency_symbol"])
        context["doc"]["grand_total_amount_words"] = "N/A (Number to words not implemented)" # Placeholder

    # Common footer and other document details (already set or from additional_context)
    # ... (packing list and warranty specific placeholders as before) ...
    # ... (common template placeholder mappings as before) ...
    context["doc"]["product_model_warranty"] = context["additional"].get("product_model_warranty", "N/A")
    context["doc"]["product_serial_numbers_warranty"] = context["additional"].get("product_serial_numbers_warranty", "N/A")
    context["doc"]["purchase_supply_date"] = context["additional"].get("purchase_supply_date", context["doc"]["current_date"])
    context["doc"]["original_invoice_id_warranty"] = context["additional"].get("original_invoice_id_warranty", context["doc"]["invoice_id"])
    context["doc"]["warranty_period_text"] = context["additional"].get("warranty_period_text", f"{context['doc']['warranty_period_months']} months")
    context["doc"]["warranty_start_point_text"] = context["additional"].get("warranty_start_point_text", "date of purchase")
    context["doc"]["warranty_coverage_details"] = context["additional"].get("warranty_coverage_details", "Standard parts and labor.")
    context["doc"]["other_exclusions_list"] = context["additional"].get("other_exclusions_list", "<li>Damage due to natural disasters.</li>")
    context["doc"]["warranty_claim_contact_info"] = context["additional"].get("warranty_claim_contact_info", context['seller'].get('email', 'N/A'))
    context["doc"]["warranty_claim_procedure_detail"] = context["additional"].get("warranty_claim_procedure_detail", "Contact us with proof of purchase.")

    # --- Map to common template placeholder patterns (already populated above or directly in context["doc"]) ---
    context["buyer_name"] = context["client"].get("company_name", context["client"].get("contact_person_name", "N/A"))
    context["buyer_address"] = context["client"].get("address", "N/A")
    context["buyer_city_zip_country"] = context["client"].get("city_zip_country", "N/A")
    context["buyer_phone"] = context["client"].get("contact_phone", "N/A")
    context["buyer_email"] = context["client"].get("contact_email", "N/A")
    context["buyer_vat_number"] = context["client"].get("vat_id", "N/A")
    context["buyer_company_name"] = context["client"].get("company_name", "N/A")
    context["buyer_company_address"] = context["client"].get("address", "N/A") # Assuming same as client address
    context["buyer_company_registration_number"] = context["client"].get("registration_number", "N/A")
    context["buyer_representative_name"] = context["client"].get("representative_name", "N/A")
    context["buyer_representative_title"] = context["client"].get("representative_title", "N/A")

    context["seller_company_logo_path"] = context["seller"].get("company_logo_path", "") # Default to empty if None
    context["seller_company_name"] = context["seller"].get("name", "N/A")
    context["seller_company_address"] = context["seller"].get("address", "N/A")
    context["seller_address_line1"] = context["seller"].get("address_line1", context["seller"].get("address", "N/A")) # Use specific if available
    context["seller_city_zip_country"] = context["seller"].get("city_zip_country", "N/A")
    context["seller_company_phone"] = context["seller"].get("phone", "N/A")
    context["seller_company_email"] = context["seller"].get("email", "N/A")
    context["seller_vat_id"] = context["seller"].get("vat_id", "N/A")
    context["seller_company_registration_number"] = context["seller"].get("registration_number", "N/A")
    context["seller_representative_name"] = context["seller"].get("personnel", {}).get("representative_name", "N/A")
    context["seller_representative_title"] = context["seller"].get("personnel", {}).get("representative_title", "N/A")
    context["seller_bank_name"] = context["seller"].get("bank_name", "N/A")
    context["seller_bank_address"] = context["seller"].get("bank_address", "N/A")
    context["seller_bank_iban"] = context["seller"].get("bank_iban", "N/A")
    context["seller_bank_swift_bic"] = context["seller"].get("bank_swift_bic", "N/A")
    context["seller_bank_account_holder_name"] = context["seller"].get("bank_account_holder_name", context["seller"].get("name", "N/A"))
    context["seller_full_address"] = context["seller"].get("address", "N/A")


    context["project_description"] = context["project"].get("description", "")
    context["project_id"] = context["project"].get("id", client_data.get("project_identifier", "N/A") if client_data else "N/A") # Ensure PROJECT_ID is available

    # Packing List specific mappings
    context["company_logo_path_for_stamp"] = context["seller_company_logo_path"]
    context["exporter_company_name"] = context["seller_company_name"]
    context["exporter_address"] = context["seller_company_address"]
    context["exporter_contact_person"] = context["seller_representative_name"]
    context["exporter_phone"] = context["seller_company_phone"]
    context["exporter_email"] = context["seller_company_email"]

    context["consignee_name"] = context["buyer_name"]
    context["consignee_address"] = context["buyer_address"]
    context["consignee_contact_person"] = context["buyer_representative_name"]
    context["consignee_phone"] = context["buyer_phone"]
    context["consignee_email"] = context["buyer_email"]

    context["primary_contact_name"] = context["client"].get("contact_person_name", "N/A") # For general use
    context["primary_contact_email"] = context["client"].get("contact_email", "N/A")
    context["primary_contact_position"] = context["client"].get("contact_position", "N/A")


    context["authorized_signature_name"] = context["seller"].get("personnel",{}).get("authorized_signature_name", "N/A")
    context["authorized_signature_title"] = context["seller"].get("personnel",{}).get("authorized_signature_title", "N/A")

    # Warranty Document specific mappings
    context["beneficiary_name"] = context["buyer_name"]
    context["beneficiary_address"] = context["buyer_address"]
    context["beneficiary_contact_person"] = context["buyer_representative_name"]
    context["beneficiary_phone"] = context["buyer_phone"]
    context["beneficiary_email"] = context["buyer_email"]

    context["warrantor_company_name"] = context["seller_company_name"]
    context["warrantor_address"] = context["seller_company_address"]
    context["warrantor_contact_person"] = context["seller"].get("personnel",{}).get("technical_manager_name", context["seller_representative_name"])
    context["warrantor_phone"] = context["seller_company_phone"]
    context["warrantor_email"] = context["seller_company_email"]

    # Cover Page specific mappings
    context["company_logo_path"] = context["seller_company_logo_path"] # Already mapped
    context["client_name"] = context["buyer_name"] # Already mapped for consistency
    context["client_company_name"] = context["client"].get("company_name", "")
    context["client_full_address"] = context["client"].get("full_address", "N/A")
    context["project_name"] = context["project"].get("name", "N/A")
    context["author_name"] = context["seller"].get("personnel",{}).get("sales_person_name", context["seller_company_name"])
    context["date"] = context["doc"]["current_date"] # General date
    context["current_year"] = context["doc"]["current_year"]


    # Fill from additional_context, providing defaults for some common ones
    # These are already in context["doc"] or context["project"] etc.
    # No need to re-assign unless overriding logic is intended.
    # context["document_title"] = context["additional"].get("document_title", "Document")
    # ... and so on

    return context


if __name__ == '__main__':
    initialize_database()
    print(f"Database '{DATABASE_NAME}' initialized successfully with all tables, including Products, ClientProjectProducts, and Contacts PK/FK updates.")

    # Example Usage (Illustrative - uncomment and adapt to test)

    # --- Test Companies and CompanyPersonnel ---
    print("\n--- Testing Companies and CompanyPersonnel ---")
    comp1_id = add_company({'company_name': 'Default Corp', 'address': '123 Main St', 'is_default': True})
    if comp1_id:
        print(f"Added company 'Default Corp' with ID: {comp1_id}")
        set_default_company(comp1_id) # Ensure it's default
        ret_comp1 = get_company_by_id(comp1_id)
        print(f"Retrieved company: {ret_comp1['company_name']}, Default: {ret_comp1['is_default']}")

        pers1_id = add_company_personnel({'company_id': comp1_id, 'name': 'John Doe', 'role': 'seller'})
        if pers1_id:
            print(f"Added personnel 'John Doe' with ID: {pers1_id} to {comp1_id}")

        pers2_id = add_company_personnel({'company_id': comp1_id, 'name': 'Jane Smith', 'role': 'technical_manager'})
        if pers2_id:
            print(f"Added personnel 'Jane Smith' with ID: {pers2_id} to {comp1_id}")

        all_personnel = get_personnel_for_company(comp1_id)
        print(f"All personnel for Default Corp: {len(all_personnel)}")
        sellers = get_personnel_for_company(comp1_id, role='seller')
        print(f"Sellers for Default Corp: {len(sellers)}")

        if pers1_id:
            update_company_personnel(pers1_id, {'name': 'Johnathan Doe', 'role': 'senior_seller'})
            updated_pers1 = get_personnel_for_company(comp1_id, role='senior_seller') # Check if update worked
            if updated_pers1: print(f"Updated personnel: {updated_pers1[0]['name']}")

    comp2_id = add_company({'company_name': 'Second Ent.', 'address': '456 Side Ave'})
    if comp2_id:
        print(f"Added company 'Second Ent.' with ID: {comp2_id}")
        set_default_company(comp1_id) # Try setting first one as default again
        ret_comp2 = get_company_by_id(comp2_id)
        if ret_comp2: print(f"Company 'Second Ent.' is_default: {ret_comp2['is_default']}")
        ret_comp1_after = get_company_by_id(comp1_id)
        if ret_comp1_after: print(f"Company 'Default Corp' is_default after re-set: {ret_comp1_after['is_default']}")


    all_companies = get_all_companies()
    print(f"Total companies: {len(all_companies)}")

    # Cleanup (optional, for testing)
    # if pers1_id: delete_company_personnel(pers1_id)
    # if pers2_id: delete_company_personnel(pers2_id)
    # if comp1_id: delete_company(comp1_id) # This would cascade delete personnel
    # if comp2_id: delete_company(comp2_id)


    # --- Pre-populate base data for FK constraints (Countries, Cities, StatusSettings) ---
    # (This setup code is largely the same as the previous step, ensuring essential lookup data)
    conn_main_setup = get_db_connection()
    try:
        cursor_main_setup = conn_main_setup.cursor()
        # ... (Country, City, StatusSettings insertions as before) ...
        cursor_main_setup.execute("INSERT OR IGNORE INTO Countries (country_id, country_name) VALUES (1, 'Default Country')")
        cursor_main_setup.execute("INSERT OR IGNORE INTO Cities (city_id, country_id, city_name) VALUES (1, 1, 'Default City')")
        cursor_main_setup.execute("INSERT OR IGNORE INTO StatusSettings (status_id, status_name, status_type) VALUES (1, 'Active Client', 'Client')")
        cursor_main_setup.execute("INSERT OR IGNORE INTO StatusSettings (status_id, status_name, status_type, is_completion_status) VALUES (10, 'Project Planning', 'Project', FALSE)")
        cursor_main_setup.execute("INSERT OR IGNORE INTO StatusSettings (status_id, status_name, status_type, is_completion_status) VALUES (22, 'Task Done', 'Task', TRUE)")

        conn_main_setup.commit()
        print("Default data for Countries, Cities, StatusSettings ensured for testing.")
    except sqlite3.Error as e_setup:
        print(f"Error ensuring default lookup data in __main__: {e_setup}")
    finally:
        if conn_main_setup:
            conn_main_setup.close()

    # --- Setup common entities for tests: User, Client, Project, Template ---
    test_user_id = add_user({'username': 'docuser', 'password': 'password', 'full_name': 'Doc User', 'email': 'doc@example.com', 'role': 'editor'})
    if test_user_id: print(f"Created user 'docuser' (ID: {test_user_id}) for document tests.")

    test_client_id_for_docs = None
    existing_doc_clients = get_all_clients({'client_name': 'Doc Test Client'})
    if not existing_doc_clients:
        test_client_id_for_docs = add_client({'client_name': 'Doc Test Client', 'created_by_user_id': test_user_id})
        if test_client_id_for_docs: print(f"Added 'Doc Test Client' (ID: {test_client_id_for_docs})")
    else:
        test_client_id_for_docs = existing_doc_clients[0]['client_id']
        print(f"Using existing 'Doc Test Client' (ID: {test_client_id_for_docs})")
    
    test_project_id_for_docs = None
    if test_client_id_for_docs and test_user_id:
        client_projects_for_docs = get_projects_by_client_id(test_client_id_for_docs)
        if not client_projects_for_docs:
            test_project_id_for_docs = add_project({
                'client_id': test_client_id_for_docs, 
                'project_name': 'Doc Test Project', 
                'manager_team_member_id': test_user_id, 
                'status_id': 10
            })
            if test_project_id_for_docs: print(f"Added 'Doc Test Project' (ID: {test_project_id_for_docs})")
        else:
            test_project_id_for_docs = client_projects_for_docs[0]['project_id']
            print(f"Using existing 'Doc Test Project' (ID: {test_project_id_for_docs})")

    test_template_id = None
    # Assuming a template might be needed for source_template_id
    templates = get_templates_by_type('general_document') # or some relevant type
    if not templates:
        test_template_id = add_template({
            'template_name': 'General Document Template for Docs', 
            'template_type': 'general_document', 
            'language_code': 'en_US',
            'created_by_user_id': test_user_id
        })
        if test_template_id: print(f"Added a test template (ID: {test_template_id}) for documents.")
    else:
        test_template_id = templates[0]['template_id']
        print(f"Using existing test template (ID: {test_template_id}) for documents.")


    print("\n--- ClientDocuments CRUD Examples ---")
    doc1_id = None
    if test_client_id_for_docs and test_user_id:
        doc1_id = add_client_document({
            'client_id': test_client_id_for_docs,
            'project_id': test_project_id_for_docs, # Optional
            'document_name': 'Initial Proposal.pdf',
            'file_name_on_disk': 'proposal_v1_final.pdf',
            'file_path_relative': f"{test_client_id_for_docs}/{test_project_id_for_docs if test_project_id_for_docs else '_client'}/proposal_v1_final.pdf",
            'document_type_generated': 'Proposal',
            'source_template_id': test_template_id, # Optional
            'created_by_user_id': test_user_id
        })
        if doc1_id:
            print(f"Added client document 'Initial Proposal.pdf' with ID: {doc1_id}")
            ret_doc = get_document_by_id(doc1_id)
            print(f"Retrieved document by ID: {ret_doc['document_name'] if ret_doc else 'Not found'}")

            update_doc_success = update_client_document(doc1_id, {'notes': 'Client approved.', 'version_tag': 'v1.1'})
            print(f"Client document update successful: {update_doc_success}")
        else:
            print("Failed to add client document.")

    if test_client_id_for_docs:
        client_docs = get_documents_for_client(test_client_id_for_docs, filters={'document_type_generated': 'Proposal'})
        print(f"Proposal documents for client {test_client_id_for_docs}: {len(client_docs)}")
        
        # Test fetching client-general documents (project_id IS NULL)
        client_general_doc_id = add_client_document({
            'client_id': test_client_id_for_docs,
            'document_name': 'Client Onboarding Checklist.docx',
            'file_name_on_disk': 'client_onboarding.docx',
            'file_path_relative': f"{test_client_id_for_docs}/client_onboarding.docx",
            'document_type_generated': 'Checklist',
            'created_by_user_id': test_user_id
        })
        if client_general_doc_id: print(f"Added client-general document ID: {client_general_doc_id}")
        
        client_general_docs = get_documents_for_client(test_client_id_for_docs, filters={'project_id': None})
        print(f"Client-general documents for client {test_client_id_for_docs}: {len(client_general_docs)}")


    if test_project_id_for_docs:
        project_docs = get_documents_for_project(test_project_id_for_docs)
        print(f"Documents for project {test_project_id_for_docs}: {len(project_docs)}")


    print("\n--- SmtpConfigs CRUD Examples ---")
    # Assuming password is encrypted elsewhere before calling add/update
    encrypted_pass = "dummy_encrypted_password_string" 
    
    smtp1_id = add_smtp_config({
        'config_name': 'Primary Gmail', 'smtp_server': 'smtp.gmail.com', 'smtp_port': 587,
        'username': 'user@gmail.com', 'password_encrypted': encrypted_pass, 
        'use_tls': True, 'is_default': True, 
        'sender_email_address': 'user@gmail.com', 'sender_display_name': 'My Gmail Account'
    })
    if smtp1_id:
        print(f"Added SMTP config 'Primary Gmail' with ID: {smtp1_id}")
        ret_smtp = get_smtp_config_by_id(smtp1_id)
        print(f"Retrieved SMTP by ID: {ret_smtp['config_name'] if ret_smtp else 'Not found'}, Default: {ret_smtp.get('is_default') if ret_smtp else ''}")
    else:
        print("Failed to add 'Primary Gmail' SMTP config.")

    smtp2_id = add_smtp_config({
        'config_name': 'Secondary Outlook', 'smtp_server': 'smtp.office365.com', 'smtp_port': 587,
        'username': 'user@outlook.com', 'password_encrypted': encrypted_pass, 
        'is_default': False, # Explicitly false
        'sender_email_address': 'user@outlook.com', 'sender_display_name': 'My Outlook Account'
    })
    if smtp2_id:
        print(f"Added SMTP config 'Secondary Outlook' with ID: {smtp2_id}")
        default_conf = get_default_smtp_config()
        print(f"Current default SMTP config: {default_conf['config_name'] if default_conf else 'None'}") # Should still be Gmail
    else:
        print("Failed to add 'Secondary Outlook' SMTP config.")

    if smtp2_id: # Set Outlook as default
        set_default_success = set_default_smtp_config(smtp2_id)
        print(f"Set 'Secondary Outlook' as default successful: {set_default_success}")
        default_conf_after_set = get_default_smtp_config()
        print(f"New default SMTP config: {default_conf_after_set['config_name'] if default_conf_after_set else 'None'}")
        
        # Verify Gmail is no longer default
        gmail_conf_after_set = get_smtp_config_by_id(smtp1_id)
        if gmail_conf_after_set:
            print(f"'Primary Gmail' is_default status: {gmail_conf_after_set['is_default']}")


    all_smtps = get_all_smtp_configs()
    print(f"Total SMTP configs: {len(all_smtps)}")

    if smtp1_id:
        update_smtp_success = update_smtp_config(smtp1_id, {'sender_display_name': 'Updated Gmail Name', 'is_default': True})
        print(f"SMTP config update for Gmail (set default again) successful: {update_smtp_success}")
        updated_smtp1 = get_smtp_config_by_id(smtp1_id)
        print(f"Updated Gmail display name: {updated_smtp1['sender_display_name'] if updated_smtp1 else ''}, Default: {updated_smtp1.get('is_default') if updated_smtp1 else ''}")
        
        # Verify Outlook is no longer default
        outlook_conf_after_gmail_default = get_smtp_config_by_id(smtp2_id)
        if outlook_conf_after_gmail_default:
            print(f"'Secondary Outlook' is_default status: {outlook_conf_after_gmail_default['is_default']}")


    # Cleanup examples (use with caution)
    # if doc1_id: delete_client_document(doc1_id)
    # if client_general_doc_id: delete_client_document(client_general_doc_id)
    # if smtp1_id: delete_smtp_config(smtp1_id)
    # if smtp2_id: delete_smtp_config(smtp2_id)
    # # test_project_id_for_docs, test_client_id_for_docs, test_user_id, test_template_id might be deleted by previous test block's commented out deletions
    # # Consider re-fetching or ensuring they exist before these deletions if running sequentially multiple times
    # if test_project_id_for_docs and get_project_by_id(test_project_id_for_docs): delete_project(test_project_id_for_docs)
    # if test_client_id_for_docs and get_client_by_id(test_client_id_for_docs): delete_client(test_client_id_for_docs)
    # if test_template_id and get_template_by_id(test_template_id): delete_template(test_template_id)
    # if test_user_id and get_user_by_id(test_user_id): delete_user(test_user_id)

    print("\n--- TeamMembers Extended Fields and KPIs CRUD Examples ---")

    # --- Cover Page Templates and Cover Pages Test ---
    print("\n--- Testing Cover Page Templates and Cover Pages ---")
    cpt_user_id = add_user({'username': 'cpt_user', 'password': 'password123', 'full_name': 'Cover Template User', 'email': 'cpt@example.com', 'role': 'designer'})
    if not cpt_user_id: cpt_user_id = get_user_by_username('cpt_user')['user_id']

    cpt_custom_id = add_cover_page_template({ # Renamed to avoid confusion with defaults
        'template_name': 'My Custom Report',
        'description': 'A custom template for special reports.',
        'default_title': 'Custom Report Title',
        'style_config_json': {'font': 'Georgia', 'primary_color': '#AA00AA'},
        'created_by_user_id': cpt_user_id,
        'is_default_template': 0 # Explicitly not default
    })
    if cpt_custom_id: print(f"Added Custom Cover Page Template 'My Custom Report' ID: {cpt_custom_id}, IsDefault: 0")

    if cpt_custom_id:
        ret_cpt_custom = get_cover_page_template_by_id(cpt_custom_id)
        print(f"Retrieved Custom CPT by ID: {ret_cpt_custom['template_name'] if ret_cpt_custom else 'Not found'}, IsDefault: {ret_cpt_custom.get('is_default_template') if ret_cpt_custom else 'N/A'}")

        # Test update: make it a default template (then change back for other tests)
        update_cpt_success = update_cover_page_template(cpt_custom_id, {'description': 'Updated custom description.', 'is_default_template': 1})
        print(f"Update Custom CPT 'My Custom Report' to be default success: {update_cpt_success}")
        ret_cpt_custom_updated = get_cover_page_template_by_id(cpt_custom_id)
        print(f"Retrieved updated Custom CPT: {ret_cpt_custom_updated['template_name'] if ret_cpt_custom_updated else 'N/A'}, IsDefault: {ret_cpt_custom_updated.get('is_default_template') if ret_cpt_custom_updated else 'N/A'}")
        assert ret_cpt_custom_updated.get('is_default_template') == 1

        # Change it back to not default
        update_cpt_success_back = update_cover_page_template(cpt_custom_id, {'is_default_template': 0})
        print(f"Update Custom CPT 'My Custom Report' back to NOT default success: {update_cpt_success_back}")
        ret_cpt_custom_final = get_cover_page_template_by_id(cpt_custom_id)
        print(f"Retrieved final Custom CPT: {ret_cpt_custom_final['template_name'] if ret_cpt_custom_final else 'N/A'}, IsDefault: {ret_cpt_custom_final.get('is_default_template') if ret_cpt_custom_final else 'N/A'}")
        assert ret_cpt_custom_final.get('is_default_template') == 0


    print(f"\n--- Testing get_all_cover_page_templates with is_default filter ---")
    all_tmpls = get_all_cover_page_templates() # No filter
    print(f"Total templates (no filter): {len(all_tmpls)}")

    default_tmpls = get_all_cover_page_templates(is_default=True)
    print(f"Default templates (is_default=True): {len(default_tmpls)}")
    for t in default_tmpls:
        print(f"  - Default: {t['template_name']} (IsDefault: {t['is_default_template']})")
        assert t['is_default_template'] == 1, f"Template '{t['template_name']}' should be default!"

    non_default_tmpls = get_all_cover_page_templates(is_default=False)
    print(f"Non-default templates (is_default=False): {len(non_default_tmpls)}")
    if cpt_custom_id and ret_cpt_custom_final and ret_cpt_custom_final.get('is_default_template') == 0:
        found_in_non_default = any(t['template_id'] == cpt_custom_id for t in non_default_tmpls)
        assert found_in_non_default, "'My Custom Report' was set to non-default but NOT found in non-defaults."
        print(f"'My Custom Report' correctly found in non-default list.")
    for t in non_default_tmpls:
         print(f"  - Non-Default: {t['template_name']} (IsDefault: {t['is_default_template']})")
         assert t['is_default_template'] == 0, f"Template '{t['template_name']}' should be non-default!"

    # Test get_cover_page_template_by_name for a default template
    standard_report_template = get_cover_page_template_by_name('Standard Report Cover')
    if standard_report_template:
        print(f"Retrieved 'Standard Report Cover' by name. IsDefault: {standard_report_template.get('is_default_template')}")
        assert standard_report_template.get('is_default_template') == 1, "'Standard Report Cover' should be default by name."
    else:
        print("Could not retrieve 'Standard Report Cover' by name for is_default check.")

    # Cover Page instance
    cp_client_id = add_client({'client_name': 'CoverPage Client', 'project_identifier': 'CP_Test_001'})
    if not cp_client_id: cp_client_id = get_all_clients({'client_name': 'CoverPage Client'})[0]['client_id']

    cp1_id = None
    if cp_client_id and cpt1_id and cpt_user_id:
        cp1_id = add_cover_page({
            'cover_page_name': 'Client X - Proposal Cover V1',
            'client_id': cp_client_id,
            'template_id': cpt1_id,
            'title': 'Specific Project Proposal',
            'subtitle': 'For CoverPage Client',
            'author_text': 'Sales Team', # Updated field name
            'institution_text': 'Our Company LLC',
            'department_text': 'Sales Department',
            'document_type_text': 'Proposal',
            'document_version': '1.0',
            'creation_date': datetime.utcnow().date().isoformat(),
            'logo_name': 'specific_logo.png', # Updated field name
            'logo_data': b'somedummyimagedata',   # Added field
            'custom_style_config_json': {'secondary_color': '#FF0000'},
            'created_by_user_id': cpt_user_id
        })
        if cp1_id: print(f"Added Cover Page instance ID: {cp1_id}")

    if cp1_id:
        ret_cp1 = get_cover_page_by_id(cp1_id)
        print(f"Retrieved Cover Page by ID: {ret_cp1['title'] if ret_cp1 else 'Not found'}")
        print(f"  Custom Style: {ret_cp1.get('custom_style_config_json') if ret_cp1 else ''}")

    if cp_client_id:
        client_cover_pages = get_cover_pages_for_client(cp_client_id)
        print(f"Cover pages for client {cp_client_id}: {len(client_cover_pages)}")

    # Clean up Cover Page related test data
    if cp1_id and get_cover_page_by_id(cp1_id): delete_cover_page(cp1_id) # cp1_id is a cover page instance
    if cpt_custom_id and get_cover_page_template_by_id(cpt_custom_id): # cpt_custom_id is a template
        delete_cover_page_template(cpt_custom_id)
        print(f"Cleaned up custom template ID {cpt_custom_id}")
    # Default templates (like 'Classic Formal' referenced by cpt2_id) should not be deleted here by tests.

    # Test get_cover_pages_for_user (using cpt_user_id for whom defaults were made)
    if cpt_user_id:
        # Add a cover page specifically for this user to test retrieval
        # Ensure cp_client_id is still valid or re-fetch/re-create.
        # For simplicity, assume cp_client_id created earlier is still usable for this test.
        # If cp_client_id was deleted, this part needs adjustment or ensure it's created before this block.

        # Let's ensure a client exists for this test section
        test_get_user_pages_client_id = cp_client_id # Try to reuse if available
        if not test_get_user_pages_client_id or not get_client_by_id(test_get_user_pages_client_id):
            test_get_user_pages_client_id = add_client({'client_name': 'ClientForUserPageTest', 'project_identifier': 'CPUPT_001', 'created_by_user_id': cpt_user_id})

        temp_cp_for_user_test_id = None
        if test_get_user_pages_client_id and cpt_user_id:
             temp_cp_for_user_test_id = add_cover_page({
                'cover_page_name': 'User Specific Cover Test for Get',
                'client_id': test_get_user_pages_client_id,
                'title': 'User Test Document - Get Test',
                'created_by_user_id': cpt_user_id
            })

        if temp_cp_for_user_test_id:
            print(f"\n--- Testing get_cover_pages_for_user for user: {cpt_user_id} ---")
            user_cover_pages = get_cover_pages_for_user(cpt_user_id)
            print(f"Found {len(user_cover_pages)} cover page(s) for user {cpt_user_id}.")
            if user_cover_pages:
                print(f"First cover page found: '{user_cover_pages[0]['cover_page_name']}' with title '{user_cover_pages[0]['title']}'")
            delete_cover_page(temp_cp_for_user_test_id) # Cleanup
            print(f"Cleaned up temporary cover page ID: {temp_cp_for_user_test_id}")
        else:
            print(f"\nCould not create a temporary cover page for user {cpt_user_id} for get_cover_pages_for_user test.")

        if test_get_user_pages_client_id and test_get_user_pages_client_id != cp_client_id: # If we created a new one for this test
             delete_client(test_get_user_pages_client_id)


    if cp_client_id and get_client_by_id(cp_client_id): delete_client(cp_client_id)
    if cpt_user_id and get_user_by_id(cpt_user_id): delete_user(cpt_user_id)
    print("--- Cover Page testing completed and cleaned up. ---")

    initialize_database() # Ensure tables are created with new schema

    # --- Populate Default Cover Page Templates ---
    # This should be called AFTER initialize_database() to ensure tables exist.
    _populate_default_cover_page_templates()

    # Test TeamMembers
    print("\nTesting TeamMembers...")
    tm_email = "new.teammember@example.com"
    # Clean up if exists from previous failed run
    existing_tm_list = get_all_team_members()
    for tm in existing_tm_list:
        if tm['email'] == tm_email:
            delete_team_member(tm['team_member_id'])
            print(f"Deleted existing test team member with email {tm_email}")

    team_member_id = add_team_member({
        'full_name': 'New Member',
        'email': tm_email,
        'role_or_title': 'Developer',
        'department': 'Engineering',
        'hire_date': '2024-01-15',
        'performance': 8,
        'skills': 'Python, SQL, FastAPI'
    })
    if team_member_id:
        print(f"Added team member 'New Member' with ID: {team_member_id}")
        member = get_team_member_by_id(team_member_id)
        print(f"Retrieved member: {member}")

        updated = update_team_member(team_member_id, {
            'performance': 9,
            'skills': 'Python, SQL, FastAPI, Docker'
        })
        print(f"Team member update successful: {updated}")
        member = get_team_member_by_id(team_member_id)
        print(f"Updated member: {member}")
    else:
        print("Failed to add team member.")

    # Test KPIs - Requires a project
    print("\nTesting KPIs...")
    # Need a client and user for project
    kpi_test_user_id = add_user({'username': 'kpi_user', 'password': 'password', 'full_name': 'KPI User', 'email': 'kpi@example.com', 'role': 'manager'})
    if not kpi_test_user_id:
        # Attempt to get existing user if add failed due to uniqueness
        kpi_user_existing = get_user_by_username('kpi_user')
        if kpi_user_existing:
            kpi_test_user_id = kpi_user_existing['user_id']
            print(f"Using existing user 'kpi_user' (ID: {kpi_test_user_id})")
        else:
            print("Failed to create or find user 'kpi_user' for KPI tests. Aborting KPI tests.")
            kpi_test_user_id = None

    kpi_test_client_id = None
    if kpi_test_user_id:
        kpi_test_client_id = add_client({'client_name': 'KPI Test Client', 'created_by_user_id': kpi_test_user_id})
        if not kpi_test_client_id:
            existing_kpi_client = get_all_clients({'client_name': 'KPI Test Client'})
            if existing_kpi_client:
                kpi_test_client_id = existing_kpi_client[0]['client_id']
                print(f"Using existing client 'KPI Test Client' (ID: {kpi_test_client_id})")
            else:
                print("Failed to create or find client 'KPI Test Client'. Aborting KPI tests.")
                kpi_test_client_id = None

    test_project_for_kpi_id = None
    if kpi_test_client_id and kpi_test_user_id:
        # Clean up existing project if any
        existing_projects = get_projects_by_client_id(kpi_test_client_id)
        for p in existing_projects:
            if p['project_name'] == 'KPI Test Project':
                # Need to delete KPIs associated with this project first
                kpis_to_delete = get_kpis_for_project(p['project_id'])
                for kpi_del in kpis_to_delete:
                    delete_kpi(kpi_del['kpi_id'])
                delete_project(p['project_id'])
                print(f"Deleted existing 'KPI Test Project' and its KPIs.")

        test_project_for_kpi_id = add_project({
            'client_id': kpi_test_client_id,
            'project_name': 'KPI Test Project',
            'manager_team_member_id': kpi_test_user_id, # Assuming user_id can be used here as per schema
            'status_id': 10 # Assuming status_id 10 exists ('Project Planning')
        })
        if test_project_for_kpi_id:
            print(f"Added 'KPI Test Project' with ID: {test_project_for_kpi_id} for KPI tests.")
        else:
            print("Failed to add project for KPI tests.")

    if test_project_for_kpi_id:
        kpi_id = add_kpi({
            'project_id': test_project_for_kpi_id,
            'name': 'Customer Satisfaction',
            'value': 85.5,
            'target': 90.0,
            'trend': 'up',
            'unit': '%'
        })
        if kpi_id:
            print(f"Added KPI 'Customer Satisfaction' with ID: {kpi_id}")

            ret_kpi = get_kpi_by_id(kpi_id)
            print(f"Retrieved KPI by ID: {ret_kpi}")

            kpis_for_proj = get_kpis_for_project(test_project_for_kpi_id)
            print(f"KPIs for project {test_project_for_kpi_id}: {kpis_for_proj}")

            updated_kpi = update_kpi(kpi_id, {'value': 87.0, 'trend': 'stable'})
            print(f"KPI update successful: {updated_kpi}")
            ret_kpi_updated = get_kpi_by_id(kpi_id)
            print(f"Updated KPI: {ret_kpi_updated}")

            deleted_kpi = delete_kpi(kpi_id)
            print(f"KPI delete successful: {deleted_kpi}")
        else:
            print("Failed to add KPI.")
    else:
        print("Skipping KPI tests as project setup failed.")

    # Clean up test data
    print("\nCleaning up test data...")
    if team_member_id and get_team_member_by_id(team_member_id):
        delete_team_member(team_member_id)
        print(f"Deleted team member ID: {team_member_id}")

    if test_project_for_kpi_id and get_project_by_id(test_project_for_kpi_id):
        # Ensure KPIs are deleted if any test failed mid-way
        kpis_left = get_kpis_for_project(test_project_for_kpi_id)
        for kpi_left_obj in kpis_left:
            delete_kpi(kpi_left_obj['kpi_id'])
            print(f"Cleaned up leftover KPI ID: {kpi_left_obj['kpi_id']}")
        delete_project(test_project_for_kpi_id)
        print(f"Deleted project ID: {test_project_for_kpi_id}")

    if kpi_test_client_id and get_client_by_id(kpi_test_client_id):
        delete_client(kpi_test_client_id)
        print(f"Deleted client ID: {kpi_test_client_id}")

    if kpi_test_user_id and get_user_by_id(kpi_test_user_id):
        delete_user(kpi_test_user_id)
        print(f"Deleted user ID: {kpi_test_user_id}")

    print("\n--- Schema changes and basic tests completed. ---")

    print("\n--- Testing get_default_company ---")
    initialize_database() # Ensure tables are fresh or correctly set up

    company_name1 = "Test Default Co"
    company_name2 = "New Default Co"
    test_comp1_id = None
    test_comp2_id = None

    # Clean up any previous test companies with the same names to ensure test idempotency
    all_comps_initial = get_all_companies()
    for comp_init in all_comps_initial:
        if comp_init['company_name'] == company_name1:
            print(f"Deleting pre-existing company: {comp_init['company_name']} (ID: {comp_init['company_id']})")
            delete_company(comp_init['company_id'])
        if comp_init['company_name'] == company_name2:
            print(f"Deleting pre-existing company: {comp_init['company_name']} (ID: {comp_init['company_id']})")
            delete_company(comp_init['company_id'])

    # 1. Add first company
    test_comp1_id = add_company({'company_name': company_name1, 'address': '1 First St'})
    if test_comp1_id:
        print(f"Added company '{company_name1}' with ID: {test_comp1_id}")
    else:
        print(f"Failed to add company '{company_name1}'")
        # Cannot proceed with test if this fails
        exit()

    # 2. Set first company as default
    print(f"Setting '{company_name1}' as default...")
    set_default_company(test_comp1_id)

    # 3. Get default company and assert it's the first one
    default_co = get_default_company()
    if default_co:
        print(f"Retrieved default company: {default_co['company_name']} (ID: {default_co['company_id']})")
        assert default_co['company_name'] == company_name1, f"Assertion Failed: Expected default company name to be '{company_name1}', got '{default_co['company_name']}'"
        assert default_co['company_id'] == test_comp1_id, f"Assertion Failed: Expected default company ID to be '{test_comp1_id}', got '{default_co['company_id']}'"
        print(f"SUCCESS: '{company_name1}' is correctly set and retrieved as default.")
    else:
        print(f"Assertion Failed: Expected to retrieve '{company_name1}' as default, but got None.")
        # Cannot proceed reliably if this fails
        if test_comp1_id: delete_company(test_comp1_id)
        exit()

    # 4. Add second company
    test_comp2_id = add_company({'company_name': company_name2, 'address': '2 Second St'})
    if test_comp2_id:
        print(f"Added company '{company_name2}' with ID: {test_comp2_id}")
    else:
        print(f"Failed to add company '{company_name2}'")
        if test_comp1_id: delete_company(test_comp1_id) # Clean up first company
        exit()

    # 5. Set second company as default
    print(f"Setting '{company_name2}' as default...")
    set_default_company(test_comp2_id)

    # 6. Get default company and assert it's the second one
    default_co_new = get_default_company()
    if default_co_new:
        print(f"Retrieved new default company: {default_co_new['company_name']} (ID: {default_co_new['company_id']})")
        assert default_co_new['company_name'] == company_name2, f"Assertion Failed: Expected new default company name to be '{company_name2}', got '{default_co_new['company_name']}'"
        assert default_co_new['company_id'] == test_comp2_id, f"Assertion Failed: Expected new default company ID to be '{test_comp2_id}', got '{default_co_new['company_id']}'"
        print(f"SUCCESS: '{company_name2}' is correctly set and retrieved as new default.")
    else:
        print(f"Assertion Failed: Expected to retrieve '{company_name2}' as new default, but got None.")
        # Clean up both companies before exiting
        if test_comp1_id: delete_company(test_comp1_id)
        if test_comp2_id: delete_company(test_comp2_id)
        exit()

    # 7. Assert that the first company is no longer the default
    comp1_check = get_company_by_id(test_comp1_id)
    if comp1_check:
        assert not comp1_check['is_default'], f"Assertion Failed: Company '{company_name1}' should no longer be default, but 'is_default' is {comp1_check['is_default']}"
        print(f"SUCCESS: Company '{company_name1}' is_default is correctly False after '{company_name2}' became default.")
    else:
        print(f"Error: Could not retrieve company '{company_name1}' for final check.")
        # Fallback check: ensure get_default_company doesn't return it
        current_default_still_comp2 = get_default_company()
        if current_default_still_comp2 and current_default_still_comp2['company_id'] == test_comp2_id:
             print(f"Fallback check: Current default is still '{company_name2}', so '{company_name1}' is not default. This is acceptable.")
        else:
            print(f"Fallback check failed: Default company is not '{company_name2}' or is None.")


    # 8. Clean up
    print("Cleaning up test companies...")
    if test_comp1_id:
        delete_company(test_comp1_id)
        print(f"Deleted company '{company_name1}' (ID: {test_comp1_id})")
    if test_comp2_id:
        delete_company(test_comp2_id)
        print(f"Deleted company '{company_name2}' (ID: {test_comp2_id})")

    final_default_check = get_default_company()
    if final_default_check is None:
        print("SUCCESS: Default company is None after cleanup, as expected.")
    else:
        print(f"Warning: A default company still exists after cleanup: {final_default_check['company_name']}. This might indicate issues in other tests or test setup.")


    print("--- Finished testing get_default_company ---")
