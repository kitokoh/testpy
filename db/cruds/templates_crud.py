import sqlite3
import os
from datetime import datetime
import json # For some template fields that might be JSON strings
import logging
from .generic_crud import _manage_conn, get_db_connection # Removed db_config
# Import APP_ROOT_DIR_CONTEXT from the root config.py
# This requires that the execution path is set up correctly for db_seed.py to find 'config'
# or for the application to run from the root where 'config' is discoverable.
from config import APP_ROOT_DIR_CONTEXT
from .template_categories_crud import add_template_category

# --- Templates CRUD ---
@_manage_conn
def add_template(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"
    cat_id = data.get('category_id')

    # If category_id is not provided, try to find/create by category_name
    if not cat_id and 'category_name' in data and data['category_name']:
        # Use the imported add_template_category, ensuring conn is passed
        cat_id = add_template_category(data['category_name'], data.get('category_description'), conn=conn)
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
              raw_template_file_data, version, created_at, updated_at, created_by_user_id)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    params=(data.get('template_name'), data.get('template_type'), data.get('description'),
            data.get('base_file_name'), data.get('language_code'),
            data.get('is_default_for_type_lang', False), cat_id, data.get('content_definition'),
            data.get('email_subject_template'), data.get('email_variables_info'),
            data.get('cover_page_config_json'), data.get('document_mapping_config_json'),
            raw_blob, data.get('version'), now, now, data.get('created_by_user_id'))
    try:
        cursor.execute(sql,params)
        return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error(f"Failed to add template '{data.get('template_name')}': {e}")
        return None

@_manage_conn
def add_default_template_if_not_exists(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor()
    name,ttype,lang = data.get('template_name'),data.get('template_type'),data.get('language_code')

    try:
        cursor.execute("SELECT template_id FROM Templates WHERE template_name=? AND template_type=? AND language_code=?",(name,ttype,lang))
        ex=cursor.fetchone()
        if ex:
            return ex['template_id']

        cat_id = data.get('category_id')
        if not cat_id and 'category_name' in data and data['category_name']:
            cat_id = add_template_category(data.get('category_name',"General"), conn=conn) # Pass conn
            if not cat_id:
                logging.error(f"Failed to ensure category for default template: {name}")
                return None
        data['category_id'] = cat_id

        if 'base_file_name' in data and 'raw_template_file_data' not in data:
            # Use the directly imported APP_ROOT_DIR_CONTEXT
            fpath = os.path.join(APP_ROOT_DIR_CONTEXT, "email_template_designs", data['base_file_name'])

            if os.path.exists(fpath):
                with open(fpath,'r',encoding='utf-8') as f:
                    data['raw_template_file_data'] = f.read()
            else:
                logging.warning(f"Template file not found at {fpath} for default template {name}")
                data['raw_template_file_data'] = None # Or some default content

        return add_template(data, conn=conn) # Pass conn
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
def get_templates_by_type(template_type: str, language_code: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT * FROM Templates WHERE template_type = ?"
    params = [template_type]
    if language_code:
        sql += " AND language_code = ?"
        params.append(language_code)
    try:
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get templates by type '{template_type}' and lang '{language_code}': {e}")
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
                  'raw_template_file_data', 'version', 'updated_at', 'created_by_user_id']
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
def get_filtered_templates(category_id: int = None, language_code: str = None, template_type: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM Templates"; where_clauses = []; params = []
    if category_id is not None: where_clauses.append("category_id = ?"); params.append(category_id)
    if language_code is not None: where_clauses.append("language_code = ?"); params.append(language_code)
    if template_type is not None: where_clauses.append("template_type = ?"); params.append(template_type)

    if where_clauses: sql += " WHERE " + " AND ".join(where_clauses)
    sql += " ORDER BY category_id, template_name"

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
        # These two execute calls should be part of the same transaction,
        # which _manage_conn handles by committing after the function if func name implies write.
        cursor.execute("UPDATE Templates SET is_default_for_type_lang = 0 WHERE template_type = ? AND language_code = ?",
                       (template_info['template_type'], template_info['language_code']))
        cursor.execute("UPDATE Templates SET is_default_for_type_lang = 1 WHERE template_id = ?", (template_id,))
        return True
    except sqlite3.Error as e:
        logging.error(f"Failed to set default template for ID {template_id}: {e}")
        return False

@_manage_conn
def get_template_by_type_lang_default(template_type: str, language_code: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Templates WHERE template_type = ? AND language_code = ? AND is_default_for_type_lang = TRUE LIMIT 1",
                       (template_type, language_code))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get default template by type '{template_type}' and lang '{language_code}': {e}")
        return None

@_manage_conn
def get_all_templates(template_type_filter: str = None, language_code_filter: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM Templates"; params = []; clauses = []
    if template_type_filter: clauses.append("template_type = ?"); params.append(template_type_filter)
    if language_code_filter: clauses.append("language_code = ?"); params.append(language_code_filter)
    if clauses: sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY template_name, language_code"
    try:
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get all templates with filters type='{template_type_filter}', lang='{language_code_filter}': {e}")
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
