import sqlite3
import uuid
import json # For style_config_json
from datetime import datetime
from .generic_crud import _manage_conn, get_db_connection
import logging

# --- CoverPageTemplates CRUD ---
@_manage_conn
def add_cover_page_template(data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor(); new_id=str(uuid.uuid4()); now=datetime.utcnow().isoformat()+"Z"
    style_str = data.get('style_config_json')
    if isinstance(style_str, dict): # Ensure it's a JSON string
        style_str = json.dumps(style_str)

    sql="""INSERT INTO CoverPageTemplates
             (template_id, template_name, description, default_title, default_subtitle,
              default_author, style_config_json, is_default_template, created_at,
              updated_at, created_by_user_id)
             VALUES (?,?,?,?,?,?,?,?,?,?,?)"""
    params=(new_id,data['template_name'],data.get('description'),data.get('default_title'),
            data.get('default_subtitle'),data.get('default_author'),style_str,
            data.get('is_default_template',0),now,now,data.get('created_by_user_id'))
    try:
        cursor.execute(sql,params)
        return new_id
    except sqlite3.Error as e:
        logging.error(f"Failed to add cover page template '{data.get('template_name')}': {e}")
        return None

@_manage_conn
def get_cover_page_template_by_name(name: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor()
    try:
        cursor.execute("SELECT * FROM CoverPageTemplates WHERE template_name = ?",(name,))
        row=cursor.fetchone()
        if row:
            data = dict(row)
            if data.get('style_config_json'):
                try:
                    data['style_config_json'] = json.loads(data['style_config_json'])
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse style_config_json for cover page template '{name}'")
                    # Depending on strictness, could return None or the raw string.
                    # For now, leave it as a string if parsing fails.
            return data
        return None
    except sqlite3.Error as e:
        logging.error(f"Failed to get cover page template by name '{name}': {e}")
        return None

@_manage_conn
def get_cover_page_template_by_id(template_id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM CoverPageTemplates WHERE template_id = ?", (template_id,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            if data.get('style_config_json'):
                try:
                    data['style_config_json'] = json.loads(data['style_config_json'])
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse style_config_json for cover page template ID '{template_id}'")
            return data
        return None
    except sqlite3.Error as e:
        logging.error(f"Failed to get cover page template by ID '{template_id}': {e}")
        return None

@_manage_conn
def get_all_cover_page_templates(is_default: bool = None, limit: int = 100, offset: int = 0, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM CoverPageTemplates"; params = []
    if is_default is not None:
        sql += " WHERE is_default_template = ?"
        params.append(1 if is_default else 0)
    sql += " ORDER BY template_name LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    templates = []
    try:
        cursor.execute(sql, params)
        for row in cursor.fetchall():
            data = dict(row)
            if data.get('style_config_json'):
                try:
                    data['style_config_json'] = json.loads(data['style_config_json'])
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse style_config_json for cover page template ID '{data['template_id']}' in get_all_cover_page_templates")
            templates.append(data)
    except sqlite3.Error as e:
        logging.error(f"Failed to get all cover page templates: {e}")
    return templates

@_manage_conn
def update_cover_page_template(template_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False
    cursor = conn.cursor()
    data['updated_at'] = datetime.utcnow().isoformat() + "Z"

    if 'style_config_json' in data and isinstance(data['style_config_json'], dict):
        data['style_config_json'] = json.dumps(data['style_config_json'])
    if 'is_default_template' in data:
        data['is_default_template'] = 1 if data['is_default_template'] else 0

    valid_cols = ['template_name', 'description', 'default_title', 'default_subtitle',
                  'default_author', 'style_config_json', 'is_default_template', 'updated_at',
                  'created_by_user_id'] # Added created_by_user_id as it was in add
    to_set={k:v for k,v in data.items() if k in valid_cols}

    if not to_set: return False

    set_c=[f"{k}=?" for k in to_set.keys()]
    sql_params=list(to_set.values())
    sql_params.append(template_id)

    sql=f"UPDATE CoverPageTemplates SET {', '.join(set_c)} WHERE template_id = ?"
    try:
        cursor.execute(sql,sql_params)
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to update cover page template {template_id}: {e}")
        return False

@_manage_conn
def delete_cover_page_template(template_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM CoverPageTemplates WHERE template_id = ?", (template_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to delete cover page template {template_id}: {e}")
        return False

__all__ = [
    "add_cover_page_template",
    "get_cover_page_template_by_name",
    "get_cover_page_template_by_id",
    "get_all_cover_page_templates",
    "update_cover_page_template",
    "delete_cover_page_template",
]
