import sqlite3
import uuid
import json # For custom_style_config_json
from datetime import datetime
from .generic_crud import _manage_conn, get_db_connection
import logging

# --- CoverPages CRUD ---
@_manage_conn
def add_cover_page(data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor(); new_id=str(uuid.uuid4()); now=datetime.utcnow().isoformat()+"Z"
    custom_style=data.get('custom_style_config_json')
    if isinstance(custom_style, dict):
        custom_style_str=json.dumps(custom_style)
    else:
        custom_style_str = custom_style # Assume it's already a JSON string or None

    sql="""INSERT INTO CoverPages
             (cover_page_id, cover_page_name, client_id, project_id, template_id, title, subtitle,
              author_text, institution_text, department_text, document_type_text, document_version,
              creation_date, logo_name, logo_data, custom_style_config_json,
              created_at, updated_at, created_by_user_id)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    params=(new_id, data.get('cover_page_name'), data.get('client_id'), data.get('project_id'),
            data.get('template_id'), data.get('title'), data.get('subtitle'), data.get('author_text'),
            data.get('institution_text'), data.get('department_text'), data.get('document_type_text'),
            data.get('document_version'), data.get('creation_date'), data.get('logo_name'),
            data.get('logo_data'), custom_style_str, now, now, data.get('created_by_user_id'))
    try:
        cursor.execute(sql,params)
        return new_id
    except sqlite3.Error as e:
        logging.error(f"Failed to add cover page '{data.get('cover_page_name')}': {e}")
        return None

@_manage_conn
def get_cover_page_by_id(id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor()
    try:
        cursor.execute("SELECT * FROM CoverPages WHERE cover_page_id = ?",(id,))
        row=cursor.fetchone()
        if row:
            data = dict(row)
            if data.get('custom_style_config_json'):
                try:
                    data['custom_style_config_json'] = json.loads(data['custom_style_config_json'])
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse custom_style_config_json for cover page ID '{id}'")
                    # Keep as string if parsing fails, or handle as error
            return data
        return None
    except sqlite3.Error as e:
        logging.error(f"Failed to get cover page by ID '{id}': {e}")
        return None

@_manage_conn
def get_cover_pages_for_client(client_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor()
    covers=[]
    try:
        cursor.execute("SELECT * FROM CoverPages WHERE client_id = ? ORDER BY created_at DESC",(client_id,))
        for row in cursor.fetchall():
            data=dict(row)
            if data.get('custom_style_config_json'):
                try:
                    data['custom_style_config_json'] = json.loads(data['custom_style_config_json'])
                except json.JSONDecodeError:
                     logging.error(f"Failed to parse custom_style_config_json for cover page ID '{data['cover_page_id']}'")
            covers.append(data)
    except sqlite3.Error as e:
        logging.error(f"Failed to get cover pages for client '{client_id}': {e}")
    return covers

@_manage_conn
def get_cover_pages_for_project(project_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor()
    covers=[]
    try:
        cursor.execute("SELECT * FROM CoverPages WHERE project_id = ? ORDER BY created_at DESC",(project_id,))
        for row in cursor.fetchall():
            data=dict(row)
            if data.get('custom_style_config_json'):
                try:
                    data['custom_style_config_json'] = json.loads(data['custom_style_config_json'])
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse custom_style_config_json for cover page ID '{data['cover_page_id']}'")
            covers.append(data)
    except sqlite3.Error as e:
        logging.error(f"Failed to get cover pages for project '{project_id}': {e}")
    return covers

@_manage_conn
def update_cover_page(id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False
    cursor=conn.cursor(); data['updated_at']=datetime.utcnow().isoformat()+"Z"

    if 'custom_style_config_json' in data and isinstance(data['custom_style_config_json'],dict):
        data['custom_style_config_json'] = json.dumps(data['custom_style_config_json'])

    valid_cols = ['cover_page_name','client_id','project_id','template_id','title','subtitle',
                  'author_text','institution_text','department_text','document_type_text',
                  'document_version','creation_date','logo_name','logo_data',
                  'custom_style_config_json','updated_at','created_by_user_id']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False

    set_c=[f"{k}=?" for k in to_set.keys()]; params_list=list(to_set.values()); params_list.append(id)
    sql=f"UPDATE CoverPages SET {', '.join(set_c)} WHERE cover_page_id = ?"
    try:
        cursor.execute(sql,params_list)
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to update cover page {id}: {e}")
        return False

@_manage_conn
def delete_cover_page(id: str, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor()
    try:
        cursor.execute("DELETE FROM CoverPages WHERE cover_page_id = ?",(id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to delete cover page {id}: {e}")
        return False

@_manage_conn
def get_cover_pages_for_user(user_id: str, limit: int = 50, offset: int = 0, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor()
    sql="SELECT * FROM CoverPages WHERE created_by_user_id = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?"
    params=(user_id,limit,offset)
    covers=[]
    try:
        cursor.execute(sql,params)
        for row in cursor.fetchall():
            data=dict(row)
            if data.get('custom_style_config_json'):
                try:
                    data['custom_style_config_json'] = json.loads(data['custom_style_config_json'])
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse custom_style_config_json for cover page ID '{data['cover_page_id']}'")
            covers.append(data)
    except sqlite3.Error as e:
        logging.error(f"Failed to get cover pages for user '{user_id}': {e}")
    return covers
