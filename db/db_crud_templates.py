import sqlite3
from datetime import datetime
import uuid
import json # For functions that might handle JSON data
# import os # Not adding os for now, unless a function explicitly needs it.
from .db_config import get_db_connection

# CRUD functions for TemplateCategories
def add_template_category(category_name: str, description: str = None) -> int | None:
    """
    Adds a new template category if it doesn't exist by name.
    Returns the category_id of the new or existing category, or None on error.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = ?", (category_name,))
        row = cursor.fetchone()
        if row:
            return row['category_id']
        sql = "INSERT INTO TemplateCategories (category_name, description) VALUES (?, ?)"
        cursor.execute(sql, (category_name, description))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_template_category: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def get_template_category_by_id(category_id: int) -> dict | None:
    """Retrieves a template category by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM TemplateCategories WHERE category_id = ?", (category_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_template_category_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_template_category_by_name(category_name: str) -> dict | None:
    """Retrieves a template category by its name."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM TemplateCategories WHERE category_name = ?", (category_name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_template_category_by_name: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_template_categories() -> list[dict]:
    """Retrieves all template categories."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM TemplateCategories ORDER BY category_name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_template_categories: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_template_category(category_id: int, new_name: str = None, new_description: str = None) -> bool:
    """
    Updates a template category's name and/or description.
    Returns True on success, False otherwise.
    """
    conn = None
    if not new_name and not new_description:
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        set_clauses = []
        params = []
        if new_name:
            set_clauses.append("category_name = ?")
            params.append(new_name)
        if new_description is not None:
            set_clauses.append("description = ?")
            params.append(new_description)
        if not set_clauses:
            return False
        sql = f"UPDATE TemplateCategories SET {', '.join(set_clauses)} WHERE category_id = ?"
        params.append(category_id)
        cursor.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_template_category: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def delete_template_category(category_id: int) -> bool:
    """
    Deletes a template category.
    Templates using this category will have their category_id set to NULL.
    Returns True on success, False otherwise.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM TemplateCategories WHERE category_id = ?", (category_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_template_category: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# CRUD functions for Templates
def add_template(template_data: dict) -> int | None:
    """
    Adds a new template to the database. Returns the template_id if successful.
    Ensures created_at and updated_at are set.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO Templates (
                template_name, template_type, description, base_file_name, language_code,
                is_default_for_type_lang, category_id, content_definition, email_subject_template,
                email_variables_info, cover_page_config_json, document_mapping_config_json,
                raw_template_file_data, version, created_at, updated_at, created_by_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            template_data.get('template_name'), template_data.get('template_type'),
            template_data.get('description'), template_data.get('base_file_name'),
            template_data.get('language_code'), template_data.get('is_default_for_type_lang', False),
            template_data.get('category_id'), template_data.get('content_definition'),
            template_data.get('email_subject_template'), template_data.get('email_variables_info'),
            template_data.get('cover_page_config_json'), template_data.get('document_mapping_config_json'),
            template_data.get('raw_template_file_data'), template_data.get('version'),
            now, now, template_data.get('created_by_user_id')
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_template: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_template_by_id(template_id: int) -> dict | None:
    """Retrieves a template by its ID. Returns a dict or None if not found."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Templates WHERE template_id = ?", (template_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_template_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_templates_by_type(template_type: str, language_code: str = None) -> list[dict]:
    """
    Retrieves templates filtered by template_type.
    If language_code is provided, also filters by language_code.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM Templates WHERE template_type = ?"
        params = [template_type]
        if language_code:
            sql += " AND language_code = ?"
            params.append(language_code)
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_templates_by_type: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_template(template_id: int, template_data: dict) -> bool:
    """
    Updates an existing template. Ensures updated_at is set. Returns True on success.
    """
    conn = None
    if not template_data:
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        template_data['updated_at'] = now
        set_clauses = [f"{key} = ?" for key in template_data if key != 'template_id']
        params = [value for key, value in template_data.items() if key != 'template_id']
        if not set_clauses:
            return False
        sql = f"UPDATE Templates SET {', '.join(set_clauses)} WHERE template_id = ?"
        params.append(template_id)
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_template: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_template(template_id: int) -> bool:
    """Deletes a template from the database. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Templates WHERE template_id = ?", (template_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_template: {e}")
        return False
    finally:
        if conn:
            conn.close()

# ClientDocument functions
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
            if 'project_id' in filters:
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

# Template lookup/utility functions
def get_template_details_for_preview(template_id: int) -> dict | None:
    """
    Fetches base_file_name and language_code for a given template_id for preview purposes.
    Returns a dictionary like {'base_file_name': 'name.xlsx', 'language_code': 'fr'} or None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT base_file_name, language_code FROM Templates WHERE template_id = ?", (template_id,))
        row = cursor.fetchone()
        if row:
            return {'base_file_name': row['base_file_name'], 'language_code': row['language_code']}
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_template_details_for_preview: {e}")
        return None
    finally:
        if conn: conn.close()

def get_template_path_info(template_id: int) -> dict | None:
    """
    Fetches base_file_name (as file_name) and language_code (as language) for a given template_id.
    Returns {'file_name': 'name.xlsx', 'language': 'fr'} or None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT base_file_name, language_code FROM Templates WHERE template_id = ?", (template_id,))
        row = cursor.fetchone()
        if row:
            return {'file_name': row['base_file_name'], 'language': row['language_code']}
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_template_path_info: {e}")
        return None
    finally:
        if conn: conn.close()

def delete_template_and_get_file_info(template_id: int) -> dict | None:
    """
    Deletes the template record by template_id after fetching its file information.
    Returns {'file_name': 'name.xlsx', 'language': 'fr'} if successful, None otherwise.
    """
    conn = None
    try:
        conn = get_db_connection()
        conn.isolation_level = None
        cursor = conn.cursor()
        cursor.execute("BEGIN")
        cursor.execute("SELECT base_file_name, language_code FROM Templates WHERE template_id = ?", (template_id,))
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            print(f"Template with ID {template_id} not found for deletion.")
            return None
        file_info = {'file_name': row['base_file_name'], 'language': row['language_code']}
        cursor.execute("DELETE FROM Templates WHERE template_id = ?", (template_id,))
        if cursor.rowcount > 0:
            conn.commit()
            return file_info
        else:
            conn.rollback()
            print(f"Failed to delete template with ID {template_id} after fetching info.")
            return None
    except sqlite3.Error as e:
        if conn: conn.rollback()
        print(f"Database error in delete_template_and_get_file_info: {e}")
        return None
    finally:
        if conn:
            conn.isolation_level = ''
            conn.close()

def set_default_template_by_id(template_id: int) -> bool:
    """
    Sets a template as the default for its template_type and language_code.
    Unsets other templates of the same type and language.
    Returns True on success, False on error.
    """
    conn = None
    try:
        conn = get_db_connection()
        conn.isolation_level = None
        cursor = conn.cursor()
        cursor.execute("BEGIN")
        cursor.execute("SELECT template_type, language_code FROM Templates WHERE template_id = ?", (template_id,))
        template_info = cursor.fetchone()
        if not template_info:
            print(f"Template with ID {template_id} not found.")
            conn.rollback()
            return False
        current_template_type = template_info['template_type']
        current_language_code = template_info['language_code']
        cursor.execute("UPDATE Templates SET is_default_for_type_lang = 0 WHERE template_type = ? AND language_code = ?", (current_template_type, current_language_code))
        cursor.execute("UPDATE Templates SET is_default_for_type_lang = 1 WHERE template_id = ?", (template_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        if conn: conn.rollback()
        print(f"Database error in set_default_template_by_id: {e}")
        return False
    finally:
        if conn:
            conn.isolation_level = ''
            conn.close()

def add_default_template_if_not_exists(template_data: dict) -> int | None:
    """
    Adds a template if it doesn't exist based on name, type, and language.
    Calls add_template_category (now local to this file).
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        name = template_data.get('template_name')
        ttype = template_data.get('template_type')
        lang = template_data.get('language_code')
        filename = template_data.get('base_file_name')
        category_name_text = template_data.get('category_name', "General")
        if not all([name, ttype, lang, filename]):
            print(f"Error: Missing required fields for default template: {template_data}")
            return None

        # Call to local add_template_category
        category_id = add_template_category(category_name_text, f"{category_name_text} (auto-created)")
        if category_id is None:
            print(f"Error: Could not get or create category_id for '{category_name_text}'.")
            return None

        cursor.execute("SELECT template_id FROM Templates WHERE template_name = ? AND template_type = ? AND language_code = ?", (name, ttype, lang))
        existing_template = cursor.fetchone()
        if existing_template:
            print(f"Default template '{name}' ({ttype}, {lang}) already exists with ID: {existing_template['template_id']}.")
            return existing_template['template_id']
        else:
            now = datetime.utcnow().isoformat() + "Z"
            sql = """
                INSERT INTO Templates (
                    template_name, template_type, language_code, base_file_name,
                    description, category_id, is_default_for_type_lang,
                    email_subject_template, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                name, ttype, lang, filename,
                template_data.get('description', f"Default {name} template"),
                category_id, template_data.get('is_default_for_type_lang', True),
                template_data.get('email_subject_template'), now, now
            )
            cursor.execute(sql, params)
            conn.commit()
            new_id = cursor.lastrowid
            print(f"Added default template '{name}' ({ttype}, {lang}) with Category ID: {category_id}, new Template ID: {new_id}.")
            return new_id
    except sqlite3.Error as e:
        print(f"Database error in add_default_template_if_not_exists for '{template_data.get('template_name')}': {e}")
        if conn: conn.rollback()
        return None
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
        languages = [row['language_code'] for row in rows if row['language_code']]
    except sqlite3.Error as e:
        print(f"Database error in get_distinct_languages_for_template_type for type '{template_type}': {e}")
    finally:
        if conn: conn.close()
    return languages

def get_all_file_based_templates() -> list[dict]:
    """Retrieves all templates that have a base_file_name, suitable for document creation."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
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
        if conn: conn.close()
