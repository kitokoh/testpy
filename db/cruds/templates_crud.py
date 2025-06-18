import sqlite3
import os
from datetime import datetime
import json # For some template fields that might be JSON strings
import logging
from typing import List, Optional, Union # Added Union
import sys # Add sys for path manipulation

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    import config
except ImportError:
    print("CRITICAL: config.py not found at project root by templates_crud.py. Path construction may fail.")
    # Define a minimal fallback config object if needed for APP_ROOT_DIR, or let it fail if config is essential.
    class config_fallback_templates:
        APP_ROOT_DIR = project_root # Best guess fallback
    config = config_fallback_templates

from .generic_crud import _manage_conn, get_db_connection # db_config removed from this import
from .template_categories_crud import add_template_category, get_template_category_by_name

# --- Templates CRUD ---
@_manage_conn
def add_template(data: dict, conn: sqlite3.Connection = None, client_id: str = None) -> int | None: # Added client_id
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"
    cat_id = data.get('category_id')

    # If category_id is not provided, try to find/create by category_name
    if not cat_id and 'category_name' in data and data['category_name']:
        # Use the imported add_template_category, ensuring conn is passed
        # Also pass category_purpose if available in data
        cat_id = add_template_category(
            data['category_name'],
            data.get('category_description'),
            purpose=data.get('category_purpose'), # Pass the purpose
            conn=conn
        )
        if not cat_id: # Failed to add/get category
            logging.error(f"Failed to add/get category: {data['category_name']} for template: {data['template_name']}")
            return None # Stop if category cannot be processed

    raw_blob = data.get('raw_template_file_data')
    if isinstance(raw_blob, str):
        raw_blob = raw_blob.encode('utf-8')

    sql="""INSERT INTO Templates
             (template_name, template_type, description, base_file_name, language_code,
              is_default_for_type_lang, category_id, content_definition, email_subject_template,
              email_variables_info, cover_page_config_json, document_mapping_config_json,
              raw_template_file_data, version, created_at, updated_at, created_by_user_id, client_id)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""" # Added one more ? for client_id
    params=(data.get('template_name'), data.get('template_type'), data.get('description'),
            data.get('base_file_name'), data.get('language_code'),
            data.get('is_default_for_type_lang', False), cat_id, data.get('content_definition'),
            data.get('email_subject_template'), data.get('email_variables_info'),
            data.get('cover_page_config_json'), data.get('document_mapping_config_json'),
            raw_blob, data.get('version'), now, now, data.get('created_by_user_id'),
            data.get('client_id')) # Added client_id to params
    try:
        cursor.execute(sql,params)
        return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error(f"Failed to add template '{data.get('template_name')}': {e}")
        return None

@_manage_conn
def add_default_template_if_not_exists(data: dict, conn: sqlite3.Connection = None, **kwargs) -> int | None:
    cursor=conn.cursor()
    name,ttype,lang = data.get('template_name'),data.get('template_type'),data.get('language_code')

    try:
        cursor.execute("SELECT template_id FROM Templates WHERE template_name=? AND template_type=? AND language_code=?",(name,ttype,lang))
        ex=cursor.fetchone()
        if ex:
            return ex['template_id']

        cat_id = data.get('category_id')
        if not cat_id and 'category_name' in data and data['category_name']:
            # Pass category_purpose if available in data, when creating category for default template
            cat_id = add_template_category(
                data.get('category_name', "General"),
                description=data.get('category_description'), # Add description if available
                purpose=data.get('category_purpose'), # Pass purpose
                conn=conn
            )
            if not cat_id:
                logging.error(f"Failed to ensure category for default template: {name}")
                return None
        data['category_id'] = cat_id

        if 'base_file_name' in data and 'raw_template_file_data' not in data:
            # Use config.APP_ROOT_DIR from the root config.py
            # The new config.py defines APP_ROOT_DIR.
            # The path "email_template_designs" is relative to the project root.
            fpath = os.path.join(config.APP_ROOT_DIR, "email_template_designs", data['base_file_name'])

            if os.path.exists(fpath):
                with open(fpath,'r',encoding='utf-8') as f:
                    data['raw_template_file_data'] = f.read()
            else:
                logging.warning(f"Template file not found at {fpath} for default template {name}")
                data['raw_template_file_data'] = None # Or some default content

        original_template_id = add_template(data, conn=conn) # Pass conn

        # Check if the template is an HTML email and duplicate it for PDF generation
        if data.get('template_type') == 'html_email' and original_template_id is not None:
            pdf_template_data = data.copy() # Create a shallow copy
            pdf_template_data['template_type'] = 'html_email_to_pdf'
            pdf_template_data['is_default_for_type_lang'] = False
            # client_id for the PDF version should be the same as the original
            pdf_template_data['client_id'] = data.get('client_id')

            # Remove template_id if it was somehow set in data, to ensure a new insert
            pdf_template_data.pop('template_id', None)

            # Call add_template for the new PDF version, passing client_id if it exists
            add_template(pdf_template_data, conn=conn, client_id=pdf_template_data.get('client_id'))

        return original_template_id
    except sqlite3.Error as e:
        logging.error(f"Error in add_default_template_if_not_exists for '{name}': {e}")
        return None
    except IOError as e_io:
        logging.error(f"IOError reading template file for '{name}': {e_io}")
        return None

@_manage_conn
def get_template_by_id(template_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Templates WHERE template_id = ?", (template_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get template by id {template_id}: {e}")
        return None

@_manage_conn
def get_templates_by_type(template_type: str, language_code: str = None, client_id: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    params = [template_type]
    sql = "SELECT * FROM Templates WHERE template_type = ?"

    if language_code:
        sql += " AND language_code = ?"
        params.append(language_code)

    if client_id:
        sql += " AND (client_id = ? OR client_id IS NULL)"
        params.append(client_id)
    else:
        # If no client_id is specified, typically we might only want global templates or all.
        # For now, let's assume it means all templates of that type (client-specific or global)
        # This part of the logic might need refinement based on exact requirements for calls without client_id.
        # The current behavior without specific client_id handling means it would fetch ALL templates of that type.
        # To be more explicit or restrictive, one might add "AND client_id IS NULL" if client_id is None
        # but the requirement is "client templates + global templates", so this is implicitly handled.
        pass


    try:
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get templates by type '{template_type}', lang '{language_code}', client '{client_id}': {e}")
        return []

@_manage_conn
def update_template(template_id: int, template_data: dict, conn: sqlite3.Connection = None) -> bool:
    if not template_data: return False
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"; template_data['updated_at'] = now

    if 'category_name' in template_data and 'category_id' not in template_data and template_data['category_name']:
        category_id = add_template_category(template_data.pop('category_name'), template_data.pop('category_description', None), conn=conn)
        if category_id:
            template_data['category_id'] = category_id
        else:
            logging.warning(f"Could not resolve category for template update (ID: {template_id}). Category related fields may not be updated.")

    if 'raw_template_file_data' in template_data and isinstance(template_data['raw_template_file_data'], str):
        template_data['raw_template_file_data'] = template_data['raw_template_file_data'].encode('utf-8')

    valid_cols = ['template_name', 'template_type', 'description', 'base_file_name',
                  'language_code', 'is_default_for_type_lang', 'category_id',
                  'content_definition', 'email_subject_template', 'email_variables_info',
                  'cover_page_config_json', 'document_mapping_config_json',
                  'raw_template_file_data', 'version', 'updated_at', 'created_by_user_id', 'client_id'] # Added client_id
    data_to_set = {k:v for k,v in template_data.items() if k in valid_cols}

    if not data_to_set : return False # Nothing valid to update (besides possibly category_name already handled)

    set_clauses = [f"{key} = ?" for key in data_to_set.keys()]
    params_list = list(data_to_set.values()); params_list.append(template_id)
    sql = f"UPDATE Templates SET {', '.join(set_clauses)} WHERE template_id = ?"

    try:
        cursor.execute(sql, params_list)
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to update template {template_id}: {e}")
        return False

@_manage_conn
def delete_template(template_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Templates WHERE template_id = ?", (template_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to delete template {template_id}: {e}")
        return False

@_manage_conn
def get_distinct_template_languages(conn: sqlite3.Connection = None) -> list[tuple[str]]:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT language_code FROM Templates WHERE language_code IS NOT NULL AND language_code != '' ORDER BY language_code")
        return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Failed to get distinct template languages: {e}")
        return []

@_manage_conn
def get_distinct_template_types(conn: sqlite3.Connection = None) -> list[tuple[str]]:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT template_type FROM Templates WHERE template_type IS NOT NULL AND template_type != '' ORDER BY template_type")
        return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Failed to get distinct template types: {e}")
        return []

@_manage_conn
def get_filtered_templates(
    category_id: int = None,
    language_code: str = None,
    template_type: str = None,
    client_id_filter: str = None,
    fetch_global_only: bool = False,
    conn: sqlite3.Connection = None
) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM Templates"; where_clauses = []; params = []

    if category_id is not None:
        where_clauses.append("category_id = ?")
        params.append(category_id)
    if language_code is not None:
        where_clauses.append("language_code = ?")
        params.append(language_code)
    if template_type is not None:
        where_clauses.append("template_type = ?")
        params.append(template_type)

    if fetch_global_only:
        where_clauses.append("client_id IS NULL")
    elif client_id_filter is not None:
        where_clauses.append("(client_id = ? OR client_id IS NULL)")
        params.append(client_id_filter)
    # If neither fetch_global_only is True nor client_id_filter is set, all templates (client-specific and global) are fetched.

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    sql += " ORDER BY client_id, category_id, template_name"

    try:
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get filtered templates: {e}")
        return []

@_manage_conn
def get_template_details_for_preview(template_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT base_file_name, language_code FROM Templates WHERE template_id = ?", (template_id,))
        row = cursor.fetchone()
        return {'base_file_name': row['base_file_name'], 'language_code': row['language_code']} if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get template details for preview (ID: {template_id}): {e}")
        return None

@_manage_conn
def get_template_path_info(template_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT base_file_name, language_code FROM Templates WHERE template_id = ?", (template_id,))
        row = cursor.fetchone()
        return {'file_name': row['base_file_name'], 'language': row['language_code']} if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get template path info (ID: {template_id}): {e}")
        return None

@_manage_conn
def delete_template_and_get_file_info(template_id: int, conn: sqlite3.Connection = None) -> dict | None:
    # This function performs multiple operations; _manage_conn handles commit/rollback at the end.
    file_info = get_template_path_info(template_id, conn=conn) # Pass conn
    if not file_info:
        logging.warning(f"No file info found for template ID {template_id}, cannot delete.")
        return None
    deleted = delete_template(template_id, conn=conn) # Pass conn
    return file_info if deleted else None

@_manage_conn
def set_default_template_by_id(template_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    template_info = get_template_by_id(template_id, conn=conn) # Pass conn
    if not template_info:
        logging.warning(f"Template ID {template_id} not found for setting as default.")
        return False
    try:
        # These two execute calls should be part of the same transaction
        # Unset other defaults for this type, language, and client (or global if client_id is NULL)
        if template_info.get('client_id'):
            cursor.execute("UPDATE Templates SET is_default_for_type_lang = 0 WHERE template_type = ? AND language_code = ? AND client_id = ?",
                           (template_info['template_type'], template_info['language_code'], template_info['client_id']))
        else:
            cursor.execute("UPDATE Templates SET is_default_for_type_lang = 0 WHERE template_type = ? AND language_code = ? AND client_id IS NULL",
                           (template_info['template_type'], template_info['language_code']))

        cursor.execute("UPDATE Templates SET is_default_for_type_lang = 1 WHERE template_id = ?", (template_id,))
        return True
    except sqlite3.Error as e:
        logging.error(f"Failed to set default template for ID {template_id}, client {template_info.get('client_id')}: {e}")
        return False

@_manage_conn
def get_template_by_type_lang_default(template_type: str, language_code: str, client_id: str = None, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    # Prioritize client-specific default, then global default.
    # If client_id is provided, look for that client's default OR a global default, prioritizing client.
    # If client_id is None, look for a global default only.
    sql = """
        SELECT * FROM Templates
        WHERE template_type = ? AND language_code = ? AND is_default_for_type_lang = TRUE
    """
    params = [template_type, language_code]

    if client_id:
        sql += "AND (client_id = ? OR client_id IS NULL) ORDER BY CASE WHEN client_id IS NULL THEN 1 ELSE 0 END, template_id LIMIT 1"
        params.append(client_id)
    else:
        sql += "AND client_id IS NULL LIMIT 1"

    try:
        cursor.execute(sql, tuple(params))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get default template by type '{template_type}', lang '{language_code}', client '{client_id}': {e}")
        return None

@_manage_conn
def get_all_templates(
    template_type_filter: str = None,
    language_code_filter: str = None,
    client_id_filter: str = None,
    category_id_filter: Optional[Union[int, List[int]]] = None, # Modified type hint
    template_type_filter_list: list[str] = None,  # New parameter for list of types
    conn: sqlite3.Connection = None
) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT * FROM Templates"
    params = []
    clauses = []

    if template_type_filter_list and isinstance(template_type_filter_list, list) and len(template_type_filter_list) > 0:
        placeholders = ','.join('?' for _ in template_type_filter_list)
        clauses.append(f"template_type IN ({placeholders})")
        params.extend(template_type_filter_list)
    elif template_type_filter: # Keep single type filter if list is not provided
        clauses.append("template_type = ?")
        params.append(template_type_filter)

    if language_code_filter:
        clauses.append("language_code = ?")
        params.append(language_code_filter)

    if category_id_filter is not None:
        if isinstance(category_id_filter, list):
            if category_id_filter: # Ensure list is not empty
                placeholders = ','.join('?' for _ in category_id_filter)
                clauses.append(f"category_id IN ({placeholders})")
                params.extend(category_id_filter)
            # If list is empty, it effectively means no filter on category_id, or you might want to handle it differently
        else: # Single integer
            clauses.append("category_id = ?")
            params.append(category_id_filter)

    if client_id_filter is not None: # Explicitly check for None, as empty string could be a valid (though unlikely) client_id
        clauses.append("(client_id = ? OR client_id IS NULL)")
        params.append(client_id_filter)
    # If client_id_filter is None, all templates (global and all client-specific) are implicitly included by not adding a client_id clause.

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)

    sql += " ORDER BY client_id, category_id, template_name, language_code" # Added category_id to order for consistency

    try:
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(
            f"Failed to get all templates with filters type='{template_type_filter if not template_type_filter_list else template_type_filter_list}', "
            f"lang='{language_code_filter}', client='{client_id_filter}', "
            f"category_id='{category_id_filter}': {e}"
        )
        return []

@_manage_conn
def get_distinct_languages_for_template_type(template_type: str, conn: sqlite3.Connection = None) -> list[str]:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT language_code FROM Templates WHERE template_type = ? ORDER BY language_code ASC", (template_type,))
        return [row['language_code'] for row in cursor.fetchall() if row['language_code']]
    except sqlite3.Error as e:
        logging.error(f"Failed to get distinct languages for template type '{template_type}': {e}")
        return []

@_manage_conn
def get_all_file_based_templates(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT template_id, template_name, language_code, base_file_name, description, category_id FROM Templates WHERE base_file_name IS NOT NULL AND base_file_name != '' ORDER BY template_name, language_code"
    try:
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get all file-based templates: {e}")
        return []

@_manage_conn
def get_templates_by_category_id(category_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Templates WHERE category_id = ? ORDER BY template_name, language_code", (category_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get templates by category id {category_id}: {e}")
        return []

__all__ = [
    "add_template",
    "add_default_template_if_not_exists",
    "get_template_by_id",
    "get_templates_by_type",
    "update_template",
    "delete_template",
    "get_distinct_template_languages",
    "get_distinct_template_types",
    "get_filtered_templates",
    "get_template_details_for_preview",
    "get_template_path_info",
    "delete_template_and_get_file_info",
    "set_default_template_by_id",
    "get_template_by_type_lang_default",
    "get_all_templates",
    "get_distinct_languages_for_template_type",
    "get_all_file_based_templates",
    "get_templates_by_category_id",
    "add_utility_document_template",
    "get_utility_documents",
]

UTILITY_DOCUMENT_CATEGORY_NAME = "Document Utilitaires"

@_manage_conn
def add_utility_document_template(name: str, language_code: str, base_file_name: str, description: str, created_by_user_id: str = None, conn: sqlite3.Connection = None) -> int | None:
    """
    Adds a new utility document template to the database.
    These templates are global and not tied to a specific client.
    """
    # Determine template_type based on file extension
    ext = os.path.splitext(base_file_name)[1].lower()
    if ext == '.pdf':
        template_type = 'document_pdf'
    elif ext == '.html':
        template_type = 'document_html'
    elif ext == '.docx':
        template_type = 'document_word'
    elif ext == '.xlsx':
        template_type = 'document_excel'
    else:
        template_type = 'document_other'

    # Get or create category ID for "Document Utilitaires"
    category_id = add_template_category(
        UTILITY_DOCUMENT_CATEGORY_NAME,
        "Modèles de documents utilitaires globaux",
        purpose='utility', # Explicitly set purpose for utility documents category
        conn=conn
    )
    if not category_id:
        logging.error(f"Failed to get or create category '{UTILITY_DOCUMENT_CATEGORY_NAME}' for utility template: {name}")
        return None

    template_data = {
        'template_name': name,
        'template_type': template_type,
        'language_code': language_code,
        'base_file_name': base_file_name,
        'description': description,
        'category_id': category_id,
        'created_by_user_id': created_by_user_id,
        'client_id': None,  # Utility documents are global
        'is_default_for_type_lang': False # Utility documents are not typically defaults
    }

    return add_template(template_data, conn=conn)

@_manage_conn
def get_utility_documents(language_code: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    """
    Retrieves all utility document templates, optionally filtered by language.
    Utility documents are global and belong to the 'Document Utilitaires' category.
    """
    category = get_template_category_by_name(UTILITY_DOCUMENT_CATEGORY_NAME, conn=conn)
    if not category:
        logging.warning(f"Utility document category '{UTILITY_DOCUMENT_CATEGORY_NAME}' not found.")
        return []

    utility_category_id = category['category_id']

    return get_filtered_templates(
        category_id=utility_category_id,
        language_code=language_code,
        client_id_filter=None,  # Explicitly not filtering by client
        fetch_global_only=True, # Ensures only global templates are fetched
        conn=conn
    )
