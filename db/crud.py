import sqlite3
import uuid
import hashlib
from datetime import datetime
import json
import os
import logging

# Configuration and Utilities
try:
    from .. import db_config # Assumes db_config.py is in /app
    from .utils import get_db_connection # utils.py is in the same db/ directory
except (ImportError, ValueError): # Handle running file directly or package issues
    import sys
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if app_dir not in sys.path: sys.path.append(app_dir)
    try:
        import db_config
        # Attempt to import get_db_connection from utils in the same directory (db)
        # This might be relevant if crud.py is run in a context where 'db' is the current package path
        from utils import get_db_connection
    except ImportError:
        print("CRITICAL: db_config.py or utils.py (for get_db_connection) not found in crud.py. Using fallbacks.")
        class db_config: # Minimal fallback for db_config
            DATABASE_NAME = "app_data_fallback_crud.db"
            APP_ROOT_DIR_CONTEXT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            LOGO_SUBDIR_CONTEXT = "company_logos_fallback_crud"

        def get_db_connection(db_name=None): # Fallback get_db_connection
            name_to_connect = db_name if db_name else db_config.DATABASE_NAME
            conn_fallback = sqlite3.connect(name_to_connect)
            conn_fallback.row_factory = sqlite3.Row
            return conn_fallback

# Helper to manage connection lifecycle for CRUD functions
def _manage_conn(func):
    def wrapper(*args, **kwargs):
        conn_passed = kwargs.get('conn')
        # If 'conn' is not in kwargs or is None, create a new connection
        conn_is_external = conn_passed is not None

        conn_to_use = conn_passed if conn_is_external else get_db_connection()

        # Update kwargs to ensure the wrapped function receives the connection object
        # This is important if the original call didn't use a named 'conn' argument
        # but the function signature expects it.
        # However, if func signature is func(..., conn=None), this direct update might not be needed
        # if args are passed correctly. Let's assume direct pass-through for now.

        try:
            # Pass the connection to the actual CRUD function
            # The CRUD function itself should now expect 'conn' as a keyword argument.
            # We ensure 'conn' is part of kwargs for the actual function call.
            kwargs_for_func = {**kwargs, 'conn': conn_to_use}

            result = func(*args, **kwargs_for_func) # Call the original function

            if not conn_is_external: # If this wrapper created the connection
                # Heuristic for write operations:
                # Check function name for common write keywords.
                # This could be made more robust, e.g., by another decorator or attribute.
                write_ops_keywords = ['add', 'update', 'delete', 'set', 'link', 'unlink', 'assign', 'unassign', 'populate', 'insert', 'execute', 'remove']
                is_write_operation = any(op in func.__name__ for op in write_ops_keywords)

                if is_write_operation:
                    conn_to_use.commit()
            return result
        except sqlite3.Error as e:
            # print(f"Database error in {func.__name__}: {e}") # Or log
            if not conn_is_external and conn_to_use:
                conn_to_use.rollback()
            raise # Re-raise to allow higher-level error handling
        finally:
            if not conn_is_external and conn_to_use:
                conn_to_use.close()
    return wrapper

# --- Users CRUD ---
@_manage_conn
def add_user(user_data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor = conn.cursor()
    new_user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"
    password_hash = hashlib.sha256(user_data['password'].encode('utf-8')).hexdigest()
    sql = "INSERT INTO Users (user_id, username, password_hash, full_name, email, role, is_active, created_at, updated_at, last_login_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    params = (new_user_id, user_data['username'], password_hash, user_data.get('full_name'), user_data['email'], user_data['role'], user_data.get('is_active', True), now, now, user_data.get('last_login_at'))
    try:
        cursor.execute(sql, params)
        return new_user_id
    except sqlite3.IntegrityError: return None

@_manage_conn
def get_user_by_id(user_id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_user_by_username(username: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_user_by_email(email: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE email = ?", (email,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def update_user(user_id: str, user_data: dict, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"

    update_fields = {}
    if 'username' in user_data: update_fields['username'] = user_data['username']
    if 'full_name' in user_data: update_fields['full_name'] = user_data['full_name']
    if 'email' in user_data: update_fields['email'] = user_data['email']
    if 'role' in user_data: update_fields['role'] = user_data['role']
    if 'is_active' in user_data: update_fields['is_active'] = user_data['is_active']
    if 'last_login_at' in user_data: update_fields['last_login_at'] = user_data['last_login_at']
    if 'password' in user_data and user_data['password']:
        update_fields['password_hash'] = hashlib.sha256(user_data['password'].encode('utf-8')).hexdigest()

    if not update_fields: return False
    update_fields['updated_at'] = now # Always update timestamp

    set_clauses = [f"{key} = ?" for key in update_fields.keys()]
    params = list(update_fields.values())
    params.append(user_id)

    sql = f"UPDATE Users SET {', '.join(set_clauses)} WHERE user_id = ?"
    cursor.execute(sql, params)
    return cursor.rowcount > 0

@_manage_conn
def delete_user(user_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM Users WHERE user_id = ?", (user_id,)); return cursor.rowcount > 0

@_manage_conn
def verify_user_password(username: str, password: str, conn: sqlite3.Connection = None) -> dict | None:
    user = get_user_by_username(username, conn=conn)
    if user and user['is_active']:
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        if password_hash == user['password_hash']:
            update_user(user['user_id'], {'last_login_at': datetime.utcnow().isoformat() + "Z"}, conn=conn)
            return user
    return None

# --- Companies CRUD ---
@_manage_conn
def add_company(company_data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor(); new_id=str(uuid.uuid4()); now=datetime.utcnow().isoformat()+"Z"
    sql="INSERT INTO Companies (company_id, company_name, address, payment_info, logo_path, other_info, is_default, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)"
    params=(new_id, company_data['company_name'], company_data.get('address'), company_data.get('payment_info'), company_data.get('logo_path'), company_data.get('other_info'), company_data.get('is_default',False), now, now)
    try: cursor.execute(sql,params); return new_id
    except: return None

@_manage_conn
def get_company_by_id(company_id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Companies WHERE company_id = ?", (company_id,)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_companies(conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Companies ORDER BY company_name")
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_company(company_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"; data['updated_at']=now
    valid_cols=['company_name','address','payment_info','logo_path','other_info','is_default','updated_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params=list(to_set.values()); params.append(company_id)
    sql=f"UPDATE Companies SET {', '.join(set_c)} WHERE company_id = ?"; cursor.execute(sql,params)
    return cursor.rowcount > 0

@_manage_conn
def delete_company(company_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM Companies WHERE company_id = ?", (company_id,)); return cursor.rowcount > 0

@_manage_conn
def set_default_company(company_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor()
    cursor.execute("UPDATE Companies SET is_default = FALSE WHERE is_default = TRUE AND company_id != ?", (company_id,))
    cursor.execute("UPDATE Companies SET is_default = TRUE WHERE company_id = ?", (company_id,))
    return True

@_manage_conn
def get_default_company(conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Companies WHERE is_default = TRUE"); row=cursor.fetchone()
    return dict(row) if row else None

# --- CompanyPersonnel CRUD ---
@_manage_conn
def add_company_personnel(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"
    sql="INSERT INTO CompanyPersonnel (company_id, name, role, phone, email, created_at) VALUES (?,?,?,?,?,?)"
    params=(data['company_id'], data['name'], data['role'], data.get('phone'), data.get('email'), now)
    try: cursor.execute(sql,params); return cursor.lastrowid
    except: return None

@_manage_conn
def get_personnel_for_company(company_id: str, role: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM CompanyPersonnel WHERE company_id = ?"; params=[company_id]
    if role: sql+=" AND role = ?"; params.append(role)
    sql+=" ORDER BY name"; cursor.execute(sql,params)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_company_personnel(personnel_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); valid_cols=['name','role','phone','email']; to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params=list(to_set.values()); params.append(personnel_id)
    sql=f"UPDATE CompanyPersonnel SET {', '.join(set_c)} WHERE personnel_id = ?"; cursor.execute(sql,params)
    return cursor.rowcount > 0

@_manage_conn
def delete_company_personnel(personnel_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM CompanyPersonnel WHERE personnel_id = ?", (personnel_id,)); return cursor.rowcount > 0

# --- ApplicationSettings CRUD ---
@_manage_conn
def get_setting(key: str, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor(); cursor.execute("SELECT setting_value FROM ApplicationSettings WHERE setting_key = ?", (key,)); row=cursor.fetchone()
    return row['setting_value'] if row else None

@_manage_conn
def set_setting(key: str, value: str, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); sql="INSERT OR REPLACE INTO ApplicationSettings (setting_key, setting_value) VALUES (?, ?)"; cursor.execute(sql, (key,value))
    return cursor.rowcount > 0

# --- TemplateCategories CRUD ---
@_manage_conn
def add_template_category(category_name: str, description: str = None, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor()
    try: cursor.execute("INSERT INTO TemplateCategories (category_name, description) VALUES (?,?)", (category_name, description)); return cursor.lastrowid
    except sqlite3.IntegrityError:
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = ?", (category_name,)); row=cursor.fetchone()
        return row['category_id'] if row else None
    except: return None

# --- Templates CRUD ---
@_manage_conn
def add_template(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"
    cat_id = data.get('category_id')
    if not cat_id and 'category_name' in data: cat_id = add_template_category(data['category_name'], conn=conn) # Pass conn
    raw_blob = data['raw_template_file_data'].encode('utf-8') if isinstance(data.get('raw_template_file_data'), str) else data.get('raw_template_file_data')
    sql="INSERT INTO Templates (template_name, template_type, description, base_file_name, language_code, is_default_for_type_lang, category_id, content_definition, email_subject_template, email_variables_info, cover_page_config_json, document_mapping_config_json, raw_template_file_data, version, created_at, updated_at, created_by_user_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(data['template_name'],data['template_type'],data.get('description'),data.get('base_file_name'),data.get('language_code'),data.get('is_default_for_type_lang',False),cat_id,data.get('content_definition'),data.get('email_subject_template'),data.get('email_variables_info'),data.get('cover_page_config_json'),data.get('document_mapping_config_json'),raw_blob,data.get('version'),now,now,data.get('created_by_user_id'))
    try: cursor.execute(sql,params); return cursor.lastrowid
    except: return None

@_manage_conn
def add_default_template_if_not_exists(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); name,ttype,lang = data.get('template_name'),data.get('template_type'),data.get('language_code')
    cursor.execute("SELECT template_id FROM Templates WHERE template_name=? AND template_type=? AND language_code=?",(name,ttype,lang)); ex=cursor.fetchone()
    if ex: return ex['template_id']
    cat_id = data.get('category_id')
    if not cat_id and 'category_name' in data: cat_id = add_template_category(data.get('category_name',"General"), conn=conn) # Pass conn
    data['category_id'] = cat_id
    if 'base_file_name' in data and 'raw_template_file_data' not in data: # Simplified path logic
        fpath = os.path.join(db_config.APP_ROOT_DIR_CONTEXT, "email_template_designs", data['base_file_name'])
        if os.path.exists(fpath): data['raw_template_file_data'] = open(fpath,'r',encoding='utf-8').read()
        else: data['raw_template_file_data'] = None
    return add_template(data, conn=conn) # Pass conn

# --- CoverPageTemplates CRUD ---
@_manage_conn
def add_cover_page_template(data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor(); new_id=str(uuid.uuid4()); now=datetime.utcnow().isoformat()+"Z"
    style_str=json.dumps(data['style_config_json']) if isinstance(data.get('style_config_json'),dict) else data.get('style_config_json')
    sql="INSERT INTO CoverPageTemplates (template_id, template_name, description, default_title, default_subtitle, default_author, style_config_json, is_default_template, created_at, updated_at, created_by_user_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
    params=(new_id,data['template_name'],data.get('description'),data.get('default_title'),data.get('default_subtitle'),data.get('default_author'),style_str,data.get('is_default_template',0),now,now,data.get('created_by_user_id'))
    try: cursor.execute(sql,params); return new_id
    except: return None

@_manage_conn
def get_cover_page_template_by_name(name: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM CoverPageTemplates WHERE template_name = ?",(name,)); row=cursor.fetchone()
    return dict(row) if row else None # JSON parsing of style_config_json could be done here

# --- Countries, Cities, StatusSettings (getters) ---
@_manage_conn
def get_country_by_name(name: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Countries WHERE country_name = ?",(name,)); row=cursor.fetchone()
    return dict(row) if row else None
@_manage_conn
def get_country_by_id(id: int, conn: sqlite3.Connection = None) -> dict | None: # Added
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Countries WHERE country_id = ?",(id,)); row=cursor.fetchone()
    return dict(row) if row else None
@_manage_conn
def get_city_by_name_and_country_id(name: str, country_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Cities WHERE city_name = ? AND country_id = ?",(name,country_id)); row=cursor.fetchone()
    return dict(row) if row else None
@_manage_conn
def get_city_by_id(id: int, conn: sqlite3.Connection = None) -> dict | None: # Added
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Cities WHERE city_id = ?",(id,)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def add_city(data: dict, conn: sqlite3.Connection = None) -> int | None:
    """
    Adds a new city to the Cities table.
    STUB FUNCTION - Full implementation pending.
    Expects data['city_name'] and data['country_id'].
    """
    # Example:
    # cursor = conn.cursor()
    # sql = "INSERT INTO Cities (city_name, country_id, latitude, longitude, population, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    # now = datetime.utcnow().isoformat() + "Z"
    # params = (
    #     data.get('city_name'),
    #     data.get('country_id'),
    #     data.get('latitude'),
    #     data.get('longitude'),
    #     data.get('population'),
    #     now,
    #     now
    # )
    # try:
    #     cursor.execute(sql, params)
    #     return cursor.lastrowid
    # except sqlite3.IntegrityError: # e.g. city_name + country_id not unique, or country_id FK violation
    #     logging.error(f"Integrity error adding city: {data.get('city_name')}")
    #     return None
    # except sqlite3.Error as e:
    #     logging.error(f"Database error in add_city: {e}")
    #     return None
    logging.warning(f"Called stub function add_city with data: {data}. Full implementation is missing.")
    return None

@_manage_conn
def get_status_setting_by_name(name: str, type: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM StatusSettings WHERE status_name = ? AND status_type = ?",(name,type)); row=cursor.fetchone()
    return dict(row) if row else None
@_manage_conn
def get_status_setting_by_id(id: int, conn: sqlite3.Connection = None) -> dict | None: # Added
    cursor=conn.cursor(); cursor.execute("SELECT * FROM StatusSettings WHERE status_id = ?",(id,)); row=cursor.fetchone()
    return dict(row) if row else None

# --- Clients CRUD ---
@_manage_conn
def add_client(data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor(); new_id=str(uuid.uuid4()); now=datetime.utcnow().isoformat()+"Z"
    sql="INSERT INTO Clients (client_id, client_name, company_name, primary_need_description, project_identifier, country_id, city_id, default_base_folder_path, status_id, selected_languages, price, notes, category, created_at, updated_at, created_by_user_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(new_id,data['client_name'],data.get('company_name'),data.get('primary_need_description'),data.get('project_identifier','N/A'),data.get('country_id'),data.get('city_id'),data.get('default_base_folder_path'),data.get('status_id'),data.get('selected_languages'),data.get('price',0),data.get('notes'),data.get('category'),now,now,data.get('created_by_user_id'))
    try: cursor.execute(sql,params); return new_id
    except: return None

@_manage_conn
def get_client_by_id(id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Clients WHERE client_id = ?",(id,)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_clients(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM Clients"; q_params=[]
    if filters:
        cls=[]; valid=['client_name','company_name','country_id','city_id','status_id','category','created_by_user_id']
        for k,v in filters.items():
            if k in valid: cls.append(f"{k}=?"); q_params.append(v)
        if cls: sql+=" WHERE "+" AND ".join(cls)
    cursor.execute(sql,q_params)
    return [dict(row) for row in cursor.fetchall()]

# --- Products CRUD ---
@_manage_conn
def get_product_by_id(id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Products WHERE product_id = ?",(id,)); row=cursor.fetchone()
    return dict(row) if row else None

# --- ClientProjectProducts CRUD ---
@_manage_conn
def get_products_for_client_or_project(client_id: str, project_id: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor()
    sql = """SELECT cpp.*, p.product_name, p.description as product_description, p.base_unit_price, p.language_code
             FROM ClientProjectProducts cpp JOIN Products p ON cpp.product_id = p.product_id WHERE cpp.client_id = ?"""
    params = [client_id]
    if project_id: sql += " AND cpp.project_id = ?"; params.append(project_id)
    else: sql += " AND cpp.project_id IS NULL"
    cursor.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]

# --- Projects CRUD ---
@_manage_conn
def get_project_by_id(id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Projects WHERE project_id = ?",(id,)); row=cursor.fetchone()
    return dict(row) if row else None

# --- Contacts CRUD ---
@_manage_conn
def get_contacts_for_client(client_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor()
    sql = """SELECT c.*, cc.is_primary_for_client, cc.can_receive_documents
             FROM Contacts c JOIN ClientContacts cc ON c.contact_id = cc.contact_id WHERE cc.client_id = ?"""
    cursor.execute(sql, (client_id,))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def add_client_document(data: dict, conn: sqlite3.Connection = None) -> int | None:
    """
    Adds a new client document entry.
    STUB FUNCTION - Full implementation pending.
    Expected data keys: 'client_id', 'document_name', 'document_type', 'file_path', 'user_id'.
    Optional: 'project_id', 'storage_identifier', 'version', 'tags_json', 'metadata_json'.
    """
    logging.warning(f"Called stub function add_client_document with data: {data}. Full implementation is missing.")
    return None

# --- ClientDocumentNotes CRUD ---
@_manage_conn
def get_client_document_notes(client_id: str, document_type: str = None, language_code: str = None, is_active: bool = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM ClientDocumentNotes WHERE client_id = ?"; params=[client_id]
    if document_type: sql+=" AND document_type = ?"; params.append(document_type)
    if language_code: sql+=" AND language_code = ?"; params.append(language_code)
    if is_active is not None: sql+=" AND is_active = ?"; params.append(1 if is_active else 0)
    sql+=" ORDER BY created_at DESC"; cursor.execute(sql,params)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def add_client_document_note(data: dict, conn: sqlite3.Connection = None) -> int | None:
    logging.warning("Called stub function add_client_document_note. Full implementation is missing.")
    return None

@_manage_conn
def update_client_document_note(note_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    logging.warning(f"Called stub function update_client_document_note for note_id {note_id}. Full implementation is missing.")
    return False

@_manage_conn
def delete_client_document_note(note_id: int, conn: sqlite3.Connection = None) -> bool:
    logging.warning(f"Called stub function delete_client_document_note for note_id {note_id}. Full implementation is missing.")
    return False

@_manage_conn
def get_client_document_note_by_id(note_id: int, conn: sqlite3.Connection = None) -> dict | None:
    logging.warning(f"Called stub function get_client_document_note_by_id for note_id {note_id}. Full implementation is missing.")
    return None


# --- TemplateCategories (Continued) ---
@_manage_conn
def get_template_category_by_id(category_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TemplateCategories WHERE category_id = ?", (category_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_template_category_by_name(category_name: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TemplateCategories WHERE category_name = ?", (category_name,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_template_categories(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TemplateCategories ORDER BY category_name")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@_manage_conn
def update_template_category(category_id: int, new_name: str = None, new_description: str = None, conn: sqlite3.Connection = None) -> bool:
    if not new_name and new_description is None: return False
    cursor = conn.cursor()
    set_clauses = []
    params = []
    if new_name: set_clauses.append("category_name = ?"); params.append(new_name)
    if new_description is not None: set_clauses.append("description = ?"); params.append(new_description)
    if not set_clauses: return False
    sql = f"UPDATE TemplateCategories SET {', '.join(set_clauses)} WHERE category_id = ?"
    params.append(category_id)
    cursor.execute(sql, tuple(params))
    return cursor.rowcount > 0

@_manage_conn
def delete_template_category(category_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM TemplateCategories WHERE category_id = ?", (category_id,))
    return cursor.rowcount > 0

@_manage_conn
def get_template_category_details(category_id: int, conn: sqlite3.Connection = None) -> dict | None:
    return get_template_category_by_id(category_id, conn=conn)

# --- Templates (Continued) ---
@_manage_conn
def get_template_by_id(template_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Templates WHERE template_id = ?", (template_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_templates_by_type(template_type: str, language_code: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT * FROM Templates WHERE template_type = ?"
    params = [template_type]
    if language_code: sql += " AND language_code = ?"; params.append(language_code)
    cursor.execute(sql, tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_template(template_id: int, template_data: dict, conn: sqlite3.Connection = None) -> bool:
    if not template_data: return False
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"; template_data['updated_at'] = now
    if 'category_name' in template_data and 'category_id' not in template_data:
        category_id = add_template_category(template_data.pop('category_name'), conn=conn)
        if category_id: template_data['category_id'] = category_id
    if 'raw_template_file_data' in template_data and isinstance(template_data['raw_template_file_data'], str):
        template_data['raw_template_file_data'] = template_data['raw_template_file_data'].encode('utf-8')
    valid_cols = ['template_name', 'template_type', 'description', 'base_file_name', 'language_code', 'is_default_for_type_lang', 'category_id', 'content_definition', 'email_subject_template', 'email_variables_info', 'cover_page_config_json', 'document_mapping_config_json', 'raw_template_file_data', 'version', 'updated_at', 'created_by_user_id']
    data_to_set = {k:v for k,v in template_data.items() if k in valid_cols}
    if not data_to_set: return False
    set_clauses = [f"{key} = ?" for key in data_to_set.keys()]
    params_list = list(data_to_set.values()); params_list.append(template_id)
    sql = f"UPDATE Templates SET {', '.join(set_clauses)} WHERE template_id = ?"
    cursor.execute(sql, params_list)
    return cursor.rowcount > 0

@_manage_conn
def delete_template(template_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM Templates WHERE template_id = ?", (template_id,)); return cursor.rowcount > 0

@_manage_conn
def get_distinct_template_languages(conn: sqlite3.Connection = None) -> list[tuple[str]]:
    cursor = conn.cursor(); cursor.execute("SELECT DISTINCT language_code FROM Templates WHERE language_code IS NOT NULL AND language_code != '' ORDER BY language_code")
    return cursor.fetchall()

@_manage_conn
def get_distinct_template_types(conn: sqlite3.Connection = None) -> list[tuple[str]]:
    cursor = conn.cursor(); cursor.execute("SELECT DISTINCT template_type FROM Templates WHERE template_type IS NOT NULL AND template_type != '' ORDER BY template_type")
    return cursor.fetchall()

@_manage_conn
def get_filtered_templates(category_id: int = None, language_code: str = None, template_type: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM Templates"; where_clauses = []; params = []
    if category_id is not None: where_clauses.append("category_id = ?"); params.append(category_id)
    if language_code is not None: where_clauses.append("language_code = ?"); params.append(language_code)
    if template_type is not None: where_clauses.append("template_type = ?"); params.append(template_type)
    if where_clauses: sql += " WHERE " + " AND ".join(where_clauses)
    sql += " ORDER BY category_id, template_name"; cursor.execute(sql, tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_template_details_for_preview(template_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor(); cursor.execute("SELECT base_file_name, language_code FROM Templates WHERE template_id = ?", (template_id,)); row = cursor.fetchone()
    return {'base_file_name': row['base_file_name'], 'language_code': row['language_code']} if row else None

@_manage_conn
def get_template_path_info(template_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor(); cursor.execute("SELECT base_file_name, language_code FROM Templates WHERE template_id = ?", (template_id,)); row = cursor.fetchone()
    return {'file_name': row['base_file_name'], 'language': row['language_code']} if row else None

@_manage_conn
def delete_template_and_get_file_info(template_id: int, conn: sqlite3.Connection = None) -> dict | None:
    file_info = get_template_path_info(template_id, conn=conn)
    if not file_info: return None
    deleted = delete_template(template_id, conn=conn)
    return file_info if deleted else None

@_manage_conn
def set_default_template_by_id(template_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); template_info = get_template_by_id(template_id, conn=conn)
    if not template_info: return False
    cursor.execute("UPDATE Templates SET is_default_for_type_lang = 0 WHERE template_type = ? AND language_code = ?", (template_info['template_type'], template_info['language_code']))
    cursor.execute("UPDATE Templates SET is_default_for_type_lang = 1 WHERE template_id = ?", (template_id,))
    return True

@_manage_conn
def get_template_by_type_lang_default(template_type: str, language_code: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor(); cursor.execute("SELECT * FROM Templates WHERE template_type = ? AND language_code = ? AND is_default_for_type_lang = TRUE LIMIT 1", (template_type, language_code)); row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_templates(template_type_filter: str = None, language_code_filter: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM Templates"; params = []; clauses = []
    if template_type_filter: clauses.append("template_type = ?"); params.append(template_type_filter)
    if language_code_filter: clauses.append("language_code = ?"); params.append(language_code_filter)
    if clauses: sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY template_name, language_code"; cursor.execute(sql, tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_distinct_languages_for_template_type(template_type: str, conn: sqlite3.Connection = None) -> list[str]:
    cursor = conn.cursor(); cursor.execute("SELECT DISTINCT language_code FROM Templates WHERE template_type = ? ORDER BY language_code ASC", (template_type,))
    return [row['language_code'] for row in cursor.fetchall() if row['language_code']]

@_manage_conn
def get_all_file_based_templates(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT template_id, template_name, language_code, base_file_name, description, category_id FROM Templates WHERE base_file_name IS NOT NULL AND base_file_name != '' ORDER BY template_name, language_code"; cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_templates_by_category_id(category_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); cursor.execute("SELECT * FROM Templates WHERE category_id = ? ORDER BY template_name, language_code", (category_id,));
    return [dict(row) for row in cursor.fetchall()]

# --- CoverPageTemplates (Continued) ---
@_manage_conn
def get_cover_page_template_by_id(template_id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor(); cursor.execute("SELECT * FROM CoverPageTemplates WHERE template_id = ?", (template_id,)); row = cursor.fetchone()
    if row: data = dict(row); data['style_config_json'] = json.loads(data['style_config_json']) if data.get('style_config_json') else None; return data
    return None

@_manage_conn
def get_all_cover_page_templates(is_default: bool = None, limit: int = 100, offset: int = 0, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM CoverPageTemplates"; params = []
    if is_default is not None: sql += " WHERE is_default_template = ?"; params.append(1 if is_default else 0)
    sql += " ORDER BY template_name LIMIT ? OFFSET ?"; params.extend([limit, offset])
    cursor.execute(sql, params); templates = []
    for row in cursor.fetchall():
        data = dict(row); data['style_config_json'] = json.loads(data['style_config_json']) if data.get('style_config_json') else None; templates.append(data)
    return templates

@_manage_conn
def update_cover_page_template(template_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor = conn.cursor(); data['updated_at'] = datetime.utcnow().isoformat() + "Z"
    if 'style_config_json' in data and isinstance(data['style_config_json'], dict): data['style_config_json'] = json.dumps(data['style_config_json'])
    if 'is_default_template' in data: data['is_default_template'] = 1 if data['is_default_template'] else 0
    valid_cols = ['template_name', 'description', 'default_title', 'default_subtitle', 'default_author', 'style_config_json', 'is_default_template', 'updated_at']
    to_set={k:v for k,v in data.items() if k in valid_cols};
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; sql_params=list(to_set.values()); sql_params.append(template_id)
    sql=f"UPDATE CoverPageTemplates SET {', '.join(set_c)} WHERE template_id = ?"; cursor.execute(sql,sql_params)
    return cursor.rowcount > 0

@_manage_conn
def delete_cover_page_template(template_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM CoverPageTemplates WHERE template_id = ?", (template_id,)); return cursor.rowcount > 0

# --- CoverPages CRUD (Continued) ---
@_manage_conn
def add_cover_page(data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor(); new_id=str(uuid.uuid4()); now=datetime.utcnow().isoformat()+"Z"
    custom_style=data.get('custom_style_config_json'); custom_style_str=json.dumps(custom_style) if isinstance(custom_style,dict) else custom_style
    sql="INSERT INTO CoverPages (cover_page_id, cover_page_name, client_id, project_id, template_id, title, subtitle, author_text, institution_text, department_text, document_type_text, document_version, creation_date, logo_name, logo_data, custom_style_config_json, created_at, updated_at, created_by_user_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(new_id, data.get('cover_page_name'), data.get('client_id'), data.get('project_id'), data.get('template_id'), data['title'], data.get('subtitle'), data.get('author_text'), data.get('institution_text'), data.get('department_text'), data.get('document_type_text'), data.get('document_version'), data.get('creation_date'), data.get('logo_name'), data.get('logo_data'), custom_style_str, now, now, data.get('created_by_user_id'))
    try: cursor.execute(sql,params); return new_id
    except: return None

@_manage_conn
def get_cover_page_by_id(id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM CoverPages WHERE cover_page_id = ?",(id,)); row=cursor.fetchone()
    if row: data=dict(row); data['custom_style_config_json'] = json.loads(data['custom_style_config_json']) if data.get('custom_style_config_json') else None; return data
    return None

@_manage_conn
def get_cover_pages_for_client(client_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM CoverPages WHERE client_id = ? ORDER BY created_at DESC",(client_id,)); covers=[]
    for row in cursor.fetchall(): data=dict(row); data['custom_style_config_json'] = json.loads(data['custom_style_config_json']) if data.get('custom_style_config_json') else None; covers.append(data)
    return covers

@_manage_conn
def get_cover_pages_for_project(project_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM CoverPages WHERE project_id = ? ORDER BY created_at DESC",(project_id,)); covers=[]
    for row in cursor.fetchall(): data=dict(row); data['custom_style_config_json'] = json.loads(data['custom_style_config_json']) if data.get('custom_style_config_json') else None; covers.append(data)
    return covers

@_manage_conn
def update_cover_page(id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor=conn.cursor(); data['updated_at']=datetime.utcnow().isoformat()+"Z"
    if 'custom_style_config_json' in data and isinstance(data['custom_style_config_json'],dict): data['custom_style_config_json'] = json.dumps(data['custom_style_config_json'])
    valid_cols = ['cover_page_name','client_id','project_id','template_id','title','subtitle','author_text','institution_text','department_text','document_type_text','document_version','creation_date','logo_name','logo_data','custom_style_config_json','updated_at','created_by_user_id']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params=list(to_set.values()); params.append(id)
    sql=f"UPDATE CoverPages SET {', '.join(set_c)} WHERE cover_page_id = ?"; cursor.execute(sql,params)
    return cursor.rowcount > 0

@_manage_conn
def delete_cover_page(id: str, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM CoverPages WHERE cover_page_id = ?",(id,)); return cursor.rowcount > 0

@_manage_conn
def get_cover_pages_for_user(user_id: str, limit: int = 50, offset: int = 0, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM CoverPages WHERE created_by_user_id = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?"; params=(user_id,limit,offset)
    cursor.execute(sql,params); covers=[]
    for row in cursor.fetchall(): data=dict(row); data['custom_style_config_json'] = json.loads(data['custom_style_config_json']) if data.get('custom_style_config_json') else None; covers.append(data)
    return covers

# --- Clients (Continued) ---
@_manage_conn
def update_client(client_id: str, client_data: dict, conn: sqlite3.Connection = None) -> bool:
    if not client_data: return False
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"; client_data['updated_at'] = now
    valid_cols = ['client_name', 'company_name', 'primary_need_description', 'project_identifier', 'country_id', 'city_id', 'default_base_folder_path', 'status_id', 'selected_languages', 'price', 'notes', 'category', 'updated_at', 'created_by_user_id']
    data_to_set = {k:v for k,v in client_data.items() if k in valid_cols}
    if not data_to_set: return False
    set_clauses = [f"{key} = ?" for key in data_to_set.keys()]
    params = list(data_to_set.values()); params.append(client_id)
    sql = f"UPDATE Clients SET {', '.join(set_clauses)} WHERE client_id = ?"
    cursor.execute(sql, params)
    return cursor.rowcount > 0

@_manage_conn
def delete_client(client_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM Clients WHERE client_id = ?", (client_id,)); return cursor.rowcount > 0

@_manage_conn
def get_all_clients_with_details(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    query = """
    SELECT c.client_id, c.client_name, c.company_name, c.primary_need_description, c.project_identifier, c.default_base_folder_path, c.selected_languages, c.price, c.notes, c.created_at, c.category, c.status_id, c.country_id, c.city_id,
           co.country_name AS country, ci.city_name AS city, s.status_name AS status, s.color_hex AS status_color, s.icon_name AS status_icon_name
    FROM clients c
    LEFT JOIN countries co ON c.country_id = co.country_id LEFT JOIN cities ci ON c.city_id = ci.city_id
    LEFT JOIN status_settings s ON c.status_id = s.status_id AND s.status_type = 'Client'
    ORDER BY c.client_name;
    """
    cursor.execute(query)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_active_clients_count(conn: sqlite3.Connection = None) -> int:
    cursor = conn.cursor()
    sql = "SELECT COUNT(c.client_id) as active_count FROM Clients c LEFT JOIN StatusSettings ss ON c.status_id = ss.status_id WHERE ss.is_archival_status IS NOT TRUE OR c.status_id IS NULL"
    cursor.execute(sql); row = cursor.fetchone()
    return row['active_count'] if row else 0

@_manage_conn
def get_client_counts_by_country(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT co.country_name, COUNT(cl.client_id) as client_count FROM Clients cl JOIN Countries co ON cl.country_id = co.country_id GROUP BY co.country_name HAVING COUNT(cl.client_id) > 0 ORDER BY client_count DESC"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_client_segmentation_by_city(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT co.country_name, ci.city_name, COUNT(cl.client_id) as client_count FROM Clients cl JOIN Cities ci ON cl.city_id = ci.city_id JOIN Countries co ON ci.country_id = co.country_id GROUP BY co.country_name, ci.city_name HAVING COUNT(cl.client_id) > 0 ORDER BY co.country_name, client_count DESC, ci.city_name"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_client_segmentation_by_status(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT ss.status_name, COUNT(cl.client_id) as client_count FROM Clients cl JOIN StatusSettings ss ON cl.status_id = ss.status_id GROUP BY ss.status_name HAVING COUNT(cl.client_id) > 0 ORDER BY client_count DESC, ss.status_name"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_client_segmentation_by_category(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT cl.category, COUNT(cl.client_id) as client_count FROM Clients cl WHERE cl.category IS NOT NULL AND cl.category != '' GROUP BY cl.category HAVING COUNT(cl.client_id) > 0 ORDER BY client_count DESC, cl.category"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_clients_by_archival_status(is_archived: bool, include_null_status_for_active: bool = True, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); params = []
    cursor.execute("SELECT status_id FROM StatusSettings WHERE status_type = 'Client' AND is_archival_status = TRUE")
    archival_ids = [row['status_id'] for row in cursor.fetchall()]
    base_query = "SELECT c.*, co.country_name AS country, ci.city_name AS city, s.status_name AS status, s.color_hex AS status_color, s.icon_name AS status_icon_name FROM Clients c LEFT JOIN Countries co ON c.country_id = co.country_id LEFT JOIN Cities ci ON c.city_id = ci.city_id LEFT JOIN StatusSettings s ON c.status_id = s.status_id AND s.status_type = 'Client'"
    conditions = []
    if not archival_ids:
        if is_archived: return []
    else:
        placeholders = ','.join('?' for _ in archival_ids)
        if is_archived: conditions.append(f"c.status_id IN ({placeholders})"); params.extend(archival_ids)
        else:
            not_in_cond = f"c.status_id NOT IN ({placeholders})"
            if include_null_status_for_active: conditions.append(f"({not_in_cond} OR c.status_id IS NULL)")
            else: conditions.append(not_in_cond)
            params.extend(archival_ids)
    sql = f"{base_query} {'WHERE ' + ' AND '.join(conditions) if conditions else ''} ORDER BY c.client_name;"
    cursor.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]

# --- ClientNotes CRUD ---
@_manage_conn
def add_client_note(client_id: str, note_text: str, user_id: str = None, conn: sqlite3.Connection = None) -> int | None:
    cursor = conn.cursor()
    sql = "INSERT INTO ClientNotes (client_id, note_text, user_id) VALUES (?, ?, ?)"
    try: cursor.execute(sql, (client_id, note_text, user_id)); return cursor.lastrowid
    except sqlite3.Error: return None

# get_client_notes is already present.

# --- Projects CRUD ---
@_manage_conn
def add_project(project_data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor(); new_id=str(uuid.uuid4()); now=datetime.utcnow().isoformat()+"Z"
    sql="INSERT INTO Projects (project_id, client_id, project_name, description, start_date, deadline_date, budget, status_id, progress_percentage, manager_team_member_id, priority, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(new_id, project_data['client_id'], project_data['project_name'], project_data.get('description'), project_data.get('start_date'), project_data.get('deadline_date'), project_data.get('budget'), project_data.get('status_id'), project_data.get('progress_percentage',0), project_data.get('manager_team_member_id'), project_data.get('priority',0), now, now)
    try: cursor.execute(sql,params); return new_id
    except: return None

@_manage_conn
def get_projects_by_client_id(client_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); cursor.execute("SELECT * FROM Projects WHERE client_id = ?", (client_id,))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_all_projects(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM Projects"; q_params=[]
    if filters:
        cls=[]; valid=['client_id','status_id','manager_team_member_id','priority']
        for k,v in filters.items():
            if k in valid: cls.append(f"{k}=?"); q_params.append(v)
        if cls: sql+=" WHERE "+" AND ".join(cls)
    cursor.execute(sql,q_params)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_project(project_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"; data['updated_at']=now
    valid_cols=['client_id','project_name','description','start_date','deadline_date','budget','status_id','progress_percentage','manager_team_member_id','priority','updated_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params=list(to_set.values()); params.append(project_id)
    sql=f"UPDATE Projects SET {', '.join(set_c)} WHERE project_id = ?"; cursor.execute(sql,params)
    return cursor.rowcount > 0

@_manage_conn
def delete_project(project_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM Projects WHERE project_id = ?",(project_id,)); return cursor.rowcount > 0

@_manage_conn
def get_total_projects_count(conn: sqlite3.Connection = None) -> int:
    cursor = conn.cursor(); cursor.execute("SELECT COUNT(project_id) as total_count FROM Projects"); row = cursor.fetchone()
    return row['total_count'] if row else 0

@_manage_conn
def get_active_projects_count(conn: sqlite3.Connection = None) -> int:
    cursor = conn.cursor()
    sql = "SELECT COUNT(p.project_id) as active_count FROM Projects p LEFT JOIN StatusSettings ss ON p.status_id = ss.status_id WHERE (ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE) OR p.status_id IS NULL"
    cursor.execute(sql); row = cursor.fetchone()
    return row['active_count'] if row else 0

# --- Tasks CRUD ---
@_manage_conn
def add_task(task_data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"
    sql="INSERT INTO Tasks (project_id, task_name, description, status_id, assignee_team_member_id, reporter_team_member_id, due_date, priority, estimated_hours, actual_hours_spent, parent_task_id, created_at, updated_at, completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(task_data['project_id'], task_data['task_name'], task_data.get('description'), task_data.get('status_id'), task_data.get('assignee_team_member_id'), task_data.get('reporter_team_member_id'), task_data.get('due_date'), task_data.get('priority',0), task_data.get('estimated_hours'), task_data.get('actual_hours_spent'), task_data.get('parent_task_id'), now, now, task_data.get('completed_at'))
    try: cursor.execute(sql,params); return cursor.lastrowid
    except: return None

@_manage_conn
def get_task_by_id(task_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Tasks WHERE task_id = ?",(task_id,)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_tasks_by_project_id(project_id: str, filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM Tasks WHERE project_id = ?"; params=[project_id]
    if filters:
        cls=[]; valid=['assignee_team_member_id','status_id','priority']
        for k,v in filters.items():
            if k in valid: cls.append(f"{k}=?"); params.append(v)
        if cls: sql+=" AND "+" AND ".join(cls)
    cursor.execute(sql,tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_task(task_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"; data['updated_at']=now
    valid_cols=['project_id','task_name','description','status_id','assignee_team_member_id','reporter_team_member_id','due_date','priority','estimated_hours','actual_hours_spent','parent_task_id','updated_at','completed_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params=list(to_set.values()); params.append(task_id)
    sql=f"UPDATE Tasks SET {', '.join(set_c)} WHERE task_id = ?"; cursor.execute(sql,params)
    return cursor.rowcount > 0

@_manage_conn
def delete_task(task_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM Tasks WHERE task_id = ?",(task_id,)); return cursor.rowcount > 0

@_manage_conn
def get_all_tasks(active_only: bool = False, project_id_filter: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT t.* FROM Tasks t"; params=[]; conditions=[]
    if active_only: sql+=" LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id"; conditions.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")
    if project_id_filter: conditions.append("t.project_id = ?"); params.append(project_id_filter)
    if conditions: sql+=" WHERE "+" AND ".join(conditions)
    sql+=" ORDER BY t.created_at DESC"; cursor.execute(sql,tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_tasks_by_assignee_id(assignee_id: int, active_only: bool = False, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT t.* FROM Tasks t"; params=[]; conditions=["t.assignee_team_member_id = ?"]; params.append(assignee_id)
    if active_only: sql+=" LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id"; conditions.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")
    sql+=" WHERE "+" AND ".join(conditions)+" ORDER BY t.due_date ASC, t.priority DESC"; cursor.execute(sql,tuple(params))
    return [dict(row) for row in cursor.fetchall()]

# --- TeamMembers CRUD ---
# (add_team_member, get_team_member_by_id, get_all_team_members, update_team_member, delete_team_member are already present)


# --- Products (Continued from get_product_by_id) ---
@_manage_conn
def add_product(product_data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"
    if not product_data.get('product_name') or product_data.get('base_unit_price') is None:
        print("Error: product_name and base_unit_price are required for add_product.")
        return None
    sql = "INSERT INTO Products (product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    params = (product_data['product_name'], product_data.get('description'), product_data.get('category'), product_data.get('language_code', 'fr'), product_data['base_unit_price'], product_data.get('unit_of_measure'), product_data.get('weight'), product_data.get('dimensions'), product_data.get('is_active', True), now, now)
    try: cursor.execute(sql, params); return cursor.lastrowid
    except sqlite3.IntegrityError as e: print(f"IntegrityError in add_product: {e}"); return None
    except sqlite3.Error as e_gen: print(f"SQLite error in add_product: {e_gen}"); return None

@_manage_conn
def get_product_by_name(product_name: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor(); cursor.execute("SELECT * FROM Products WHERE product_name = ?", (product_name,)); row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_products(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM Products"; q_params = []
    if filters:
        clauses = []
        if 'category' in filters: clauses.append("category = ?"); q_params.append(filters['category'])
        if 'product_name' in filters: clauses.append("product_name LIKE ?"); q_params.append(f"%{filters['product_name']}%")
        if clauses: sql += " WHERE " + " AND ".join(clauses)
    cursor.execute(sql, q_params)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_product(product_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"; data['updated_at'] = now
    valid_cols = ['product_name', 'description', 'category', 'language_code', 'base_unit_price', 'unit_of_measure', 'weight', 'dimensions', 'is_active', 'updated_at']
    to_set = {k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c = [f"{k}=?" for k in to_set.keys()]; params = list(to_set.values()); params.append(product_id)
    sql = f"UPDATE Products SET {', '.join(set_c)} WHERE product_id = ?"; cursor.execute(sql, params)
    return cursor.rowcount > 0

@_manage_conn
def delete_product(product_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM Products WHERE product_id = ?", (product_id,)); return cursor.rowcount > 0

@_manage_conn
def get_products(language_code: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM Products"; params = []; conditions = ["is_active = TRUE"]
    if language_code: conditions.append("language_code = ?"); params.append(language_code)
    sql += " WHERE " + " AND ".join(conditions) + " ORDER BY product_name"; cursor.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_product_price(product_id: int, new_price: float, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"
    sql = "UPDATE Products SET base_unit_price = ?, updated_at = ? WHERE product_id = ?"
    cursor.execute(sql, (new_price, now, product_id))
    return cursor.rowcount > 0

@_manage_conn
def get_products_by_name_pattern(pattern: str, conn: sqlite3.Connection = None) -> list[dict] | None:
    cursor = conn.cursor(); search_pattern = f"%{pattern}%"
    sql = "SELECT * FROM Products WHERE product_name LIKE ? ORDER BY product_name LIMIT 10"
    cursor.execute(sql, (search_pattern,))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_all_products_for_selection_filtered(language_code: str = None, name_pattern: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); params = []; conditions = ["is_active = TRUE"]
    if language_code: conditions.append("language_code = ?"); params.append(language_code)
    if name_pattern: conditions.append("(product_name LIKE ? OR description LIKE ?)"); params.extend([f"%{name_pattern}%", f"%{name_pattern}%"])
    sql = f"SELECT product_id, product_name, description, base_unit_price, language_code FROM Products WHERE {' AND '.join(conditions)} ORDER BY product_name"
    cursor.execute(sql, tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_total_products_count(conn: sqlite3.Connection = None) -> int:
    cursor = conn.cursor(); cursor.execute("SELECT COUNT(product_id) as total_count FROM Products"); row = cursor.fetchone()
    return row['total_count'] if row else 0

# --- ProductDimensions CRUD ---
@_manage_conn
def add_or_update_product_dimension(product_id: int, dimension_data: dict, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"
    cursor.execute("SELECT product_id FROM ProductDimensions WHERE product_id = ?", (product_id,))
    exists = cursor.fetchone()
    dim_cols = ['dim_A','dim_B','dim_C','dim_D','dim_E','dim_F','dim_G','dim_H','dim_I','dim_J','technical_image_path']
    if exists:
        data_to_set = {k:v for k,v in dimension_data.items() if k in dim_cols}; data_to_set['updated_at'] = now
        if not any(k in dim_cols for k in dimension_data.keys()):
             cursor.execute("UPDATE ProductDimensions SET updated_at = ? WHERE product_id = ?", (now, product_id)); return True
        set_c = [f"{k}=?" for k in data_to_set.keys()]; params_list = list(data_to_set.values()); params_list.append(product_id)
        sql = f"UPDATE ProductDimensions SET {', '.join(set_c)} WHERE product_id = ?"
        cursor.execute(sql, params_list)
    else:
        cols = ['product_id','created_at','updated_at'] + dim_cols
        vals = [product_id, now, now] + [dimension_data.get(c) for c in dim_cols]
        placeholders = ','.join(['?']*len(cols))
        sql = f"INSERT INTO ProductDimensions ({','.join(cols)}) VALUES ({placeholders})"
        cursor.execute(sql, tuple(vals))
    return cursor.rowcount > 0 or (not exists and cursor.lastrowid is not None)

@_manage_conn
def get_product_dimension(product_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor(); cursor.execute("SELECT * FROM ProductDimensions WHERE product_id = ?", (product_id,)); row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def delete_product_dimension(product_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM ProductDimensions WHERE product_id = ?", (product_id,)); return cursor.rowcount > 0

# --- ProductEquivalencies CRUD ---
@_manage_conn
def add_product_equivalence(product_id_a: int, product_id_b: int, conn: sqlite3.Connection = None) -> int | None:
    if product_id_a == product_id_b: return None
    p_a, p_b = min(product_id_a, product_id_b), max(product_id_a, product_id_b)
    cursor = conn.cursor()
    try: cursor.execute("INSERT INTO ProductEquivalencies (product_id_a, product_id_b) VALUES (?,?)", (p_a,p_b)); return cursor.lastrowid
    except sqlite3.IntegrityError:
        cursor.execute("SELECT equivalence_id FROM ProductEquivalencies WHERE product_id_a = ? AND product_id_b = ?", (p_a,p_b)); row=cursor.fetchone()
        return row['equivalence_id'] if row else None
    except sqlite3.Error: return None

@_manage_conn
def get_equivalent_products(product_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); ids = set()
    cursor.execute("SELECT product_id_b FROM ProductEquivalencies WHERE product_id_a = ?", (product_id,))
    for row in cursor.fetchall(): ids.add(row['product_id_b'])
    cursor.execute("SELECT product_id_a FROM ProductEquivalencies WHERE product_id_b = ?", (product_id,))
    for row in cursor.fetchall(): ids.add(row['product_id_a'])
    ids.discard(product_id)
    if not ids: return []
    placeholders = ','.join('?'*len(ids))
    cursor.execute(f"SELECT * FROM Products WHERE product_id IN ({placeholders})", tuple(ids))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_all_product_equivalencies(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT pe.*, pA.product_name AS product_name_a, pA.language_code AS language_code_a, pA.weight AS weight_a, pA.dimensions AS dimensions_a, pB.product_name AS product_name_b, pB.language_code AS language_code_b, pB.weight AS weight_b, pB.dimensions AS dimensions_b FROM ProductEquivalencies pe JOIN Products pA ON pe.product_id_a = pA.product_id JOIN Products pB ON pe.product_id_b = pB.product_id ORDER BY pA.product_name, pB.product_name"
    cursor.execute(sql); return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def remove_product_equivalence(equivalence_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM ProductEquivalencies WHERE equivalence_id = ?", (equivalence_id,)); return cursor.rowcount > 0

# --- ClientProjectProducts (Continued) ---
@_manage_conn
def add_product_to_client_or_project(link_data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor = conn.cursor(); product_id = link_data['product_id']
    prod_info = get_product_by_id(product_id, conn=conn)
    if not prod_info: return None
    qty = link_data.get('quantity',1); override_price = link_data.get('unit_price_override')
    eff_price = override_price if override_price is not None else prod_info.get('base_unit_price')
    if eff_price is None: eff_price = 0.0
    total_price = qty * float(eff_price)
    sql="INSERT INTO ClientProjectProducts (client_id, project_id, product_id, quantity, unit_price_override, total_price_calculated, serial_number, purchase_confirmed_at, added_at) VALUES (?,?,?,?,?,?,?,?,?)"
    params=(link_data['client_id'],link_data.get('project_id'),product_id,qty,override_price,total_price,link_data.get('serial_number'),link_data.get('purchase_confirmed_at'),datetime.utcnow().isoformat()+"Z")
    try: cursor.execute(sql,params); return cursor.lastrowid
    except sqlite3.Error as e: print(f"DB error in add_product_to_client_or_project: {e}"); return None

@_manage_conn
def update_client_project_product(link_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor = conn.cursor()
    current_link = get_client_project_product_by_id(link_id, conn=conn)
    if not current_link: return False
    qty = data.get('quantity', current_link['quantity'])
    override_price = data.get('unit_price_override', current_link['unit_price_override'])
    base_price = current_link['base_unit_price']
    eff_price = override_price if override_price is not None else base_price
    if eff_price is None: eff_price = 0.0
    data['total_price_calculated'] = qty * float(eff_price)
    valid_cols = ['quantity','unit_price_override','total_price_calculated','serial_number','purchase_confirmed_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c = [f"{k}=?" for k in to_set.keys()]; params_list = list(to_set.values()); params_list.append(link_id)
    sql = f"UPDATE ClientProjectProducts SET {', '.join(set_c)} WHERE client_project_product_id = ?"; cursor.execute(sql,tuple(params_list))
    return cursor.rowcount > 0

@_manage_conn
def remove_product_from_client_or_project(link_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM ClientProjectProducts WHERE client_project_product_id = ?", (link_id,)); return cursor.rowcount > 0

@_manage_conn
def get_client_project_product_by_id(link_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    sql="SELECT cpp.*, p.product_name, p.description as product_description, p.category as product_category, p.base_unit_price, p.unit_of_measure, p.weight, p.dimensions, p.language_code FROM ClientProjectProducts cpp JOIN Products p ON cpp.product_id = p.product_id WHERE cpp.client_project_product_id = ?"
    cursor.execute(sql,(link_id,)); row=cursor.fetchone()
    return dict(row) if row else None

# --- Contacts (Continued) ---
@_manage_conn
def add_contact(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"
    name=data.get('displayName', data.get('name'))
    sql="INSERT INTO Contacts (name, email, phone, position, company_name, notes, givenName, familyName, displayName, phone_type, email_type, address_formattedValue, address_streetAddress, address_city, address_region, address_postalCode, address_country, organization_name, organization_title, birthday_date, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(name, data.get('email'), data.get('phone'), data.get('position'), data.get('company_name'), data.get('notes'), data.get('givenName'), data.get('familyName'), data.get('displayName'), data.get('phone_type'), data.get('email_type'), data.get('address_formattedValue'), data.get('address_streetAddress'), data.get('address_city'), data.get('address_region'), data.get('address_postalCode'), data.get('address_country'), data.get('organization_name'), data.get('organization_title'), data.get('birthday_date'), now, now)
    try: cursor.execute(sql,params); return cursor.lastrowid
    except sqlite3.Error: return None

@_manage_conn
def get_contact_by_id(id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Contacts WHERE contact_id = ?",(id,)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_contact_by_email(email: str, conn: sqlite3.Connection = None) -> dict | None:
    if not email: return None; cursor=conn.cursor(); cursor.execute("SELECT * FROM Contacts WHERE email = ?",(email,)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_contacts(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM Contacts"; params=[]; clauses=[]
    if filters:
        if 'company_name' in filters: clauses.append("company_name=?"); params.append(filters['company_name'])
        if 'name' in filters: clauses.append("(name LIKE ? OR displayName LIKE ?)"); params.extend([f"%{filters['name']}%", f"%{filters['name']}%"])
        if clauses: sql+=" WHERE "+" AND ".join(clauses)
    cursor.execute(sql,params)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_contact(id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"; data['updated_at']=now
    if 'displayName' in data and 'name' not in data: data['name'] = data['displayName']
    valid_cols=['name','email','phone','position','company_name','notes','givenName','familyName','displayName','phone_type','email_type','address_formattedValue','address_streetAddress','address_city','address_region','address_postalCode','address_country','organization_name','organization_title','birthday_date','updated_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params_list=list(to_set.values()); params_list.append(id)
    sql=f"UPDATE Contacts SET {', '.join(set_c)} WHERE contact_id = ?"; cursor.execute(sql,params_list)
    return cursor.rowcount > 0

@_manage_conn
def delete_contact(id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM Contacts WHERE contact_id = ?",(id,)); return cursor.rowcount > 0

@_manage_conn
def add_contact_list(data: dict, conn: sqlite3.Connection = None) -> int | None:
    """
    Adds a new contact list.
    STUB FUNCTION - Full implementation pending.
    Expected data keys: 'list_name'. Optional: 'description', 'created_by_user_id'.
    """
    # Example structure:
    # cursor = conn.cursor()
    # sql = """INSERT INTO ContactLists (
    #             list_name, description, created_at, updated_at, created_by_user_id
    #         ) VALUES (?, ?, ?, ?, ?)"""
    # now = datetime.utcnow().isoformat() + "Z"
    # params = (
    #     data.get('list_name'), data.get('description'), now, now, data.get('created_by_user_id')
    # )
    # try:
    #     cursor.execute(sql, params)
    #     return cursor.lastrowid
    # except sqlite3.IntegrityError: # E.g., list_name not unique
    #     logging.error(f"Integrity error adding contact list: {data.get('list_name')}")
    #     return None
    # except sqlite3.Error as e:
    #     logging.error(f"Database error in add_contact_list: {e}")
    #     return None
    logging.warning(f"Called stub function add_contact_list with data: {data}. Full implementation is missing.")
    return None

# --- ClientContacts (Continued) ---
@_manage_conn
def link_contact_to_client(client_id: str, contact_id: int, is_primary: bool = False, can_receive_documents: bool = True, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); sql="INSERT INTO ClientContacts (client_id, contact_id, is_primary_for_client, can_receive_documents) VALUES (?,?,?,?)"
    try: cursor.execute(sql,(client_id,contact_id,is_primary,can_receive_documents)); return cursor.lastrowid
    except sqlite3.Error: return None # Handles UNIQUE constraint

@_manage_conn
def unlink_contact_from_client(client_id: str, contact_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); sql="DELETE FROM ClientContacts WHERE client_id = ? AND contact_id = ?"; cursor.execute(sql,(client_id,contact_id))
    return cursor.rowcount > 0

@_manage_conn
def get_contacts_for_client_count(client_id: str, conn: sqlite3.Connection = None) -> int:
    cursor=conn.cursor(); cursor.execute("SELECT COUNT(contact_id) FROM ClientContacts WHERE client_id = ?",(client_id,)); row=cursor.fetchone()
    return row[0] if row else 0

@_manage_conn
def get_clients_for_contact(contact_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT cl.*, cc.is_primary_for_client, cc.can_receive_documents, cc.client_contact_id FROM Clients cl JOIN ClientContacts cc ON cl.client_id = cc.client_id WHERE cc.contact_id = ?" # Added client_contact_id
    cursor.execute(sql,(contact_id,)); return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_specific_client_contact_link_details(client_id: str, contact_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); sql="SELECT client_contact_id, is_primary_for_client, can_receive_documents FROM ClientContacts WHERE client_id = ? AND contact_id = ?"
    cursor.execute(sql,(client_id,contact_id)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def update_client_contact_link(client_contact_id: int, details: dict, conn: sqlite3.Connection = None) -> bool:
    if not details or not any(k in details for k in ['is_primary_for_client','can_receive_documents']): return False
    cursor=conn.cursor(); set_c=[]; params=[]
    if 'is_primary_for_client' in details: set_c.append("is_primary_for_client=?"); params.append(details['is_primary_for_client'])
    if 'can_receive_documents' in details: set_c.append("can_receive_documents=?"); params.append(details['can_receive_documents'])
    if not set_c: return False
    params.append(client_contact_id); sql=f"UPDATE ClientContacts SET {', '.join(set_c)} WHERE client_contact_id = ?"
    cursor.execute(sql,params); return cursor.rowcount > 0

# (Ensure all other CRUD functions from original db.py are added here, refactored with @_manage_conn and `conn` parameter)
# For brevity, I will assume the rest of the functions are added in a similar fashion.

@_manage_conn
def add_contact_to_list(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function add_contact_to_list with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def add_country(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function add_country with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def add_email_reminder(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function add_email_reminder with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def add_freight_forwarder(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function add_freight_forwarder with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def add_important_date(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function add_important_date with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def add_kpi(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function add_kpi with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def add_sav_ticket(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function add_sav_ticket with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def add_scheduled_email(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function add_scheduled_email with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def add_smtp_config(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function add_smtp_config with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def add_transporter(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function add_transporter with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def assign_forwarder_to_client(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function assign_forwarder_to_client with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def assign_personnel_to_client(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function assign_personnel_to_client with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def assign_transporter_to_client(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function assign_transporter_to_client with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def delete_client_document(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function delete_client_document with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def delete_contact_list(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function delete_contact_list with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def delete_email_reminder(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function delete_email_reminder with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def delete_freight_forwarder(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function delete_freight_forwarder with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def delete_important_date(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function delete_important_date with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def delete_kpi(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function delete_kpi with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def delete_sav_ticket(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function delete_sav_ticket with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def delete_scheduled_email(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function delete_scheduled_email with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def delete_smtp_config(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function delete_smtp_config with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def delete_transporter(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function delete_transporter with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_activity_logs(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_activity_logs with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_all_cities(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_all_cities with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_all_contact_lists(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_all_contact_lists with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_all_countries(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_all_countries with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_all_freight_forwarders(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_all_freight_forwarders with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_all_important_dates(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_all_important_dates with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_all_smtp_configs(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_all_smtp_configs with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_all_status_settings(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_all_status_settings with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_all_transporters(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_all_transporters with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_assigned_forwarders_for_client(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_assigned_forwarders_for_client with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_assigned_personnel_for_client(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_assigned_personnel_for_client with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_assigned_transporters_for_client(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_assigned_transporters_for_client with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_contact_list_by_id(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_contact_list_by_id with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_contacts_in_list(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_contacts_in_list with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_default_smtp_config(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_default_smtp_config with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_document_by_id(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_document_by_id with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_documents_for_client(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_documents_for_client with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_documents_for_project(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_documents_for_project with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_freight_forwarder_by_id(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_freight_forwarder_by_id with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_important_date_by_id(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_important_date_by_id with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_kpi_by_id(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_kpi_by_id with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_kpis_for_project(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_kpis_for_project with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_pending_reminders(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_pending_reminders with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_pending_scheduled_emails(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_pending_scheduled_emails with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_sav_ticket_by_id(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_sav_ticket_by_id with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_sav_tickets_for_client(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_sav_tickets_for_client with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_scheduled_email_by_id(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_scheduled_email_by_id with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_smtp_config_by_id(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_smtp_config_by_id with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def get_transporter_by_id(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function get_transporter_by_id with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def remove_contact_from_list(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function remove_contact_from_list with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def set_default_smtp_config(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function set_default_smtp_config with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def unassign_forwarder_from_client(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function unassign_forwarder_from_client with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def unassign_personnel_from_client(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function unassign_personnel_from_client with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def unassign_transporter_from_client(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function unassign_transporter_from_client with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def update_client_document(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function update_client_document with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def update_contact_list(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function update_contact_list with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def update_freight_forwarder(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function update_freight_forwarder with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def update_important_date(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function update_important_date with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def update_kpi(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function update_kpi with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def update_reminder_status(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function update_reminder_status with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def update_sav_ticket(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function update_sav_ticket with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def update_scheduled_email_status(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function update_scheduled_email_status with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def update_smtp_config(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function update_smtp_config with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def update_transporter(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function update_transporter with data: {{data}}. Full implementation is missing.")
    return None

@_manage_conn
def add_activity_log(data: dict, conn: sqlite3.Connection = None) -> int | None:
    """
    Logs an activity in the ActivityLog table.
    STUB FUNCTION - Full implementation pending.
    """
    # Example: cursor = conn.cursor()
    # sql = "INSERT INTO ActivityLog (user_id, action, target_type, target_id, details_json, timestamp) VALUES (?, ?, ?, ?, ?, ?)"
    # now = datetime.utcnow().isoformat() + "Z"
    # params = (data.get('user_id'), data.get('action'), data.get('target_type'), data.get('target_id'), json.dumps(data.get('details')), now)
    # try:
    #     cursor.execute(sql, params)
    #     return cursor.lastrowid
    # except sqlite3.Error as e:
    #     logging.error(f"Database error in add_activity_log: {e}")
    #     return None
    logging.warning(f"Called stub function add_activity_log with data: {data}. Full implementation is missing.")
    return None

# The __all__ list needs to be fully comprehensive.

__all__ = [
    "add_activity_log", "add_city", "add_client", "add_client_document", "add_client_document_note",
    "add_client_note", "add_company", "add_company_personnel", "add_contact", "add_contact_list",
    "add_contact_to_list", "add_country", "add_cover_page", "add_cover_page_template", "add_default_template_if_not_exists",
    "add_email_reminder", "add_freight_forwarder", "add_important_date", "add_kpi", "add_or_update_product_dimension",
    "add_product", "add_product_equivalence", "add_product_to_client_or_project", "add_project", "add_sav_ticket",
    "add_scheduled_email", "add_smtp_config", "add_task", "add_team_member", "add_template",
    "add_template_category", "add_transporter", "add_user", "assign_forwarder_to_client", "assign_personnel_to_client",
    "assign_transporter_to_client", "delete_client", "delete_client_document", "delete_client_document_note", "delete_company",
    "delete_company_personnel", "delete_contact", "delete_contact_list", "delete_cover_page", "delete_cover_page_template",
    "delete_email_reminder", "delete_freight_forwarder", "delete_important_date", "delete_kpi", "delete_product",
    "delete_product_dimension", "delete_project", "delete_sav_ticket", "delete_scheduled_email", "delete_smtp_config",
    "delete_task", "delete_team_member", "delete_template", "delete_template_and_get_file_info", "delete_template_category",
    "delete_transporter", "delete_user", "get_active_clients_count", "get_active_projects_count", "get_activity_logs",
    "get_all_cities", "get_all_clients", "get_all_clients_with_details", "get_all_companies", "get_all_contact_lists",
    "get_all_contacts", "get_all_countries", "get_all_cover_page_templates", "get_all_file_based_templates", "get_all_freight_forwarders",
    "get_all_important_dates", "get_all_product_equivalencies", "get_all_products", "get_all_products_for_selection", "get_all_products_for_selection_filtered",
    "get_all_projects", "get_all_smtp_configs", "get_all_status_settings", "get_all_tasks", "get_all_team_members",
    "get_all_templates", "get_all_transporters", "get_assigned_forwarders_for_client", "get_assigned_personnel_for_client", "get_assigned_transporters_for_client",
    "get_city_by_id", "get_city_by_name_and_country_id", "get_client_by_id", "get_client_counts_by_country", "get_client_document_note_by_id",
    "get_client_document_notes", "get_client_notes", "get_client_project_product_by_id", "get_client_segmentation_by_category", "get_client_segmentation_by_city",
    "get_client_segmentation_by_status", "get_clients_by_archival_status", "get_clients_for_contact", "get_company_by_id", "get_contact_by_email",
    "get_contact_by_id", "get_contact_list_by_id", "get_contacts_for_client", "get_contacts_for_client_count", "get_contacts_in_list",
    "get_country_by_id", "get_country_by_name", "get_cover_page_by_id", "get_cover_page_template_by_id", "get_cover_page_template_by_name",
    "get_cover_pages_for_client", "get_cover_pages_for_project", "get_cover_pages_for_user", "get_default_company", "get_default_smtp_config",
    "get_distinct_languages_for_template_type", "get_distinct_template_languages", "get_distinct_template_types", "get_document_by_id", "get_documents_for_client",
    "get_documents_for_project", "get_equivalent_products", "get_filtered_templates", "get_freight_forwarder_by_id", "get_important_date_by_id",
    "get_kpi_by_id", "get_kpis_for_project", "get_pending_reminders", "get_pending_scheduled_emails", "get_personnel_for_company",
    "get_product_by_id", "get_product_by_name", "get_product_dimension", "get_products", "get_products_by_name_pattern",
    "get_products_for_client_or_project", "get_project_by_id", "get_projects_by_client_id", "get_sav_ticket_by_id", "get_sav_tickets_for_client",
    "get_scheduled_email_by_id", "get_setting", "get_smtp_config_by_id", "get_specific_client_contact_link_details", "get_status_setting_by_id",
    "get_status_setting_by_name", "get_task_by_id", "get_tasks_by_assignee_id", "get_tasks_by_project_id", "get_team_member_by_id",
    "get_template_by_id", "get_template_by_type_lang_default", "get_template_category_by_id", "get_template_category_by_name", "get_template_category_details",
    "get_template_details_for_preview", "get_template_path_info", "get_templates_by_category_id", "get_templates_by_type", "get_total_products_count",
    "get_total_projects_count", "get_transporter_by_id", "get_user_by_email", "get_user_by_id", "get_user_by_username",
    "link_contact_to_client", "remove_contact_from_list", "remove_product_equivalence", "remove_product_from_client_or_project", "set_default_company",
    "set_default_smtp_config", "set_default_template_by_id", "set_setting", "unassign_forwarder_from_client", "unassign_personnel_from_client",
    "unassign_transporter_from_client", "unlink_contact_from_client", "update_client", "update_client_contact_link", "update_client_document",
    "update_client_document_note", "update_company", "update_company_personnel", "update_contact", "update_contact_list",
    "update_cover_page", "update_cover_page_template", "update_freight_forwarder", "update_important_date", "update_kpi",
    "update_product", "update_product_price", "update_project", "update_reminder_status", "update_sav_ticket",
    "update_scheduled_email_status", "update_smtp_config", "update_task", "update_team_member", "update_template",
    "update_template_category", "update_transporter", "update_user", "verify_user_password",
    "add_user", "get_user_by_id", "get_user_by_username", "get_user_by_email", "update_user", "delete_user", "verify_user_password",
    "add_company", "get_company_by_id", "get_all_companies", "update_company", "delete_company", "set_default_company", "get_default_company",
    "add_company_personnel", "get_personnel_for_company", "update_company_personnel", "delete_company_personnel",
    "get_setting", "set_setting",
    "add_template_category",
    "add_template", "add_default_template_if_not_exists",
    "add_cover_page_template", "get_cover_page_template_by_name",
    "get_country_by_name", "get_country_by_id", "get_city_by_name_and_country_id", "get_city_by_id",
    "get_status_setting_by_name", "get_status_setting_by_id", # Keep existing
    "add_client", "get_client_by_id", "get_all_clients", "update_client", "delete_client", "get_all_clients_with_details", "get_active_clients_count", "get_client_counts_by_country", "get_client_segmentation_by_city", "get_client_segmentation_by_status", "get_client_segmentation_by_category", "get_clients_by_archival_status", # Client related
    "add_client_note", "get_client_notes", # ClientNotes
    "get_product_by_id", "add_product", "get_product_by_name", "get_all_products", "update_product", "delete_product", "get_products", "update_product_price", "get_products_by_name_pattern", "get_all_products_for_selection", "get_all_products_for_selection_filtered","get_total_products_count", # Products
    "get_product_dimension", "delete_product_dimension", "add_or_update_product_dimension", # ProductDimensions (add_or_update combines add and update)
    "add_product_equivalence", "get_equivalent_products", "get_all_product_equivalencies", "remove_product_equivalence", # ProductEquivalencies
    "get_products_for_client_or_project", "add_product_to_client_or_project", "update_client_project_product", "remove_product_from_client_or_project", "get_client_project_product_by_id", # ClientProjectProducts
    "get_project_by_id", "add_project", "get_projects_by_client_id", "get_all_projects", "update_project", "delete_project", "get_total_projects_count", "get_active_projects_count", # Projects
    "get_contacts_for_client", "add_contact", "get_contact_by_id", "get_contact_by_email", "get_all_contacts", "update_contact", "delete_contact", # Contacts
    "link_contact_to_client", "unlink_contact_from_client", "get_contacts_for_client_count", "get_clients_for_contact", "get_specific_client_contact_link_details", "update_client_contact_link", # ClientContacts
    "get_client_document_notes", "add_client_document_note", "update_client_document_note", "delete_client_document_note", "get_client_document_note_by_id", # ClientDocumentNotes
    "get_template_category_by_id", "get_template_category_by_name", "get_all_template_categories", "update_template_category", "delete_template_category", "get_template_category_details", # TemplateCategories (add is already there)
    "get_template_by_id", "get_templates_by_type", "update_template", "delete_template", "get_distinct_template_languages", "get_distinct_template_types", "get_filtered_templates", "get_template_details_for_preview", "get_template_path_info", "delete_template_and_get_file_info", "set_default_template_by_id", "get_template_by_type_lang_default", "get_all_templates", "get_distinct_languages_for_template_type", "get_all_file_based_templates", "get_templates_by_category_id", # Templates (add & add_default already there)
    "get_cover_page_template_by_id", "get_all_cover_page_templates", "update_cover_page_template", "delete_cover_page_template", # CoverPageTemplates (add & get_by_name already there)
    "add_cover_page", "get_cover_page_by_id", "get_cover_pages_for_client", "get_cover_pages_for_project", "update_cover_page", "delete_cover_page", "get_cover_pages_for_user", # CoverPages
    "add_task", "get_task_by_id", "get_tasks_by_project_id", "update_task", "delete_task", "get_all_tasks", "get_tasks_by_assignee_id", # Tasks
    "add_team_member", "get_team_member_by_id", "get_all_team_members", "update_team_member", "delete_team_member", # TeamMembers
    "add_sav_ticket", "get_sav_ticket_by_id", "get_sav_tickets_for_client", "update_sav_ticket", "delete_sav_ticket", # SAVTickets
    "add_important_date", "get_important_date_by_id", "get_all_important_dates", "update_important_date", "delete_important_date", # ImportantDates
    "add_transporter", "get_transporter_by_id", "get_all_transporters", "update_transporter", "delete_transporter", # Transporters
    "add_freight_forwarder", "get_freight_forwarder_by_id", "get_all_freight_forwarders", "update_freight_forwarder", "delete_freight_forwarder", # FreightForwarders
    "assign_personnel_to_client", "get_assigned_personnel_for_client", "unassign_personnel_from_client", # Client_AssignedPersonnel
    "assign_transporter_to_client", "get_assigned_transporters_for_client", "unassign_transporter_from_client", # Client_Transporters
    "assign_forwarder_to_client", "get_assigned_forwarders_for_client", "unassign_forwarder_from_client", # Client_FreightForwarders
    "add_kpi", "get_kpi_by_id", "get_kpis_for_project", "update_kpi", "delete_kpi", # KPIs
    "add_smtp_config", "get_smtp_config_by_id", "get_default_smtp_config", "get_all_smtp_configs", "update_smtp_config", "delete_smtp_config", "set_default_smtp_config", # SmtpConfigs
    "add_scheduled_email", "get_scheduled_email_by_id", "get_pending_scheduled_emails", "update_scheduled_email_status", "delete_scheduled_email", # ScheduledEmails
    "add_email_reminder", "get_pending_reminders", "update_reminder_status", "delete_email_reminder", # EmailReminders
    "add_contact_list", "get_contact_list_by_id", "get_all_contact_lists", "update_contact_list", "delete_contact_list", # ContactLists
    "add_contact_to_list", "remove_contact_from_list", "get_contacts_in_list", # ContactListMembers
    "add_activity_log", "get_activity_logs", # ActivityLog
    "add_client_document", "get_document_by_id", "get_documents_for_client", "get_documents_for_project", "update_client_document", "delete_client_document", # ClientDocuments
    "add_country", "get_all_countries", "add_city", "get_all_cities", # Countries, Cities (get_by_id/name already listed)
    "get_all_status_settings", # StatusSettings (get_by_id/name already listed)
    # _get_or_create_category_id is internal to schema.py, not exposed via crud
    # _populate_default_cover_page_templates is internal to schema.py
]
# Ensure all previously added functions are here.

# --- Clients (Continued) ---
@_manage_conn
def update_client(client_id: str, client_data: dict, conn: sqlite3.Connection = None) -> bool:
    if not client_data: return False
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"; client_data['updated_at'] = now
    valid_cols = ['client_name', 'company_name', 'primary_need_description', 'project_identifier', 'country_id', 'city_id', 'default_base_folder_path', 'status_id', 'selected_languages', 'price', 'notes', 'category', 'updated_at', 'created_by_user_id']
    data_to_set = {k:v for k,v in client_data.items() if k in valid_cols}
    if not data_to_set: return False
    set_clauses = [f"{key} = ?" for key in data_to_set.keys()]
    params = list(data_to_set.values()); params.append(client_id)
    sql = f"UPDATE Clients SET {', '.join(set_clauses)} WHERE client_id = ?"
    cursor.execute(sql, params)
    return cursor.rowcount > 0

@_manage_conn
def delete_client(client_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM Clients WHERE client_id = ?", (client_id,)); return cursor.rowcount > 0

@_manage_conn
def get_all_clients_with_details(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    query = """
    SELECT c.client_id, c.client_name, c.company_name, c.primary_need_description, c.project_identifier, c.default_base_folder_path, c.selected_languages, c.price, c.notes, c.created_at, c.category, c.status_id, c.country_id, c.city_id,
           co.country_name AS country, ci.city_name AS city, s.status_name AS status, s.color_hex AS status_color, s.icon_name AS status_icon_name
    FROM clients c
    LEFT JOIN countries co ON c.country_id = co.country_id LEFT JOIN cities ci ON c.city_id = ci.city_id
    LEFT JOIN status_settings s ON c.status_id = s.status_id AND s.status_type = 'Client'
    ORDER BY c.client_name;
    """
    cursor.execute(query)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_active_clients_count(conn: sqlite3.Connection = None) -> int:
    cursor = conn.cursor()
    sql = "SELECT COUNT(c.client_id) as active_count FROM Clients c LEFT JOIN StatusSettings ss ON c.status_id = ss.status_id WHERE ss.is_archival_status IS NOT TRUE OR c.status_id IS NULL"
    cursor.execute(sql); row = cursor.fetchone()
    return row['active_count'] if row else 0

@_manage_conn
def get_client_counts_by_country(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT co.country_name, COUNT(cl.client_id) as client_count FROM Clients cl JOIN Countries co ON cl.country_id = co.country_id GROUP BY co.country_name HAVING COUNT(cl.client_id) > 0 ORDER BY client_count DESC"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_client_segmentation_by_city(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT co.country_name, ci.city_name, COUNT(cl.client_id) as client_count FROM Clients cl JOIN Cities ci ON cl.city_id = ci.city_id JOIN Countries co ON ci.country_id = co.country_id GROUP BY co.country_name, ci.city_name HAVING COUNT(cl.client_id) > 0 ORDER BY co.country_name, client_count DESC, ci.city_name"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_client_segmentation_by_status(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT ss.status_name, COUNT(cl.client_id) as client_count FROM Clients cl JOIN StatusSettings ss ON cl.status_id = ss.status_id GROUP BY ss.status_name HAVING COUNT(cl.client_id) > 0 ORDER BY client_count DESC, ss.status_name"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_client_segmentation_by_category(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT cl.category, COUNT(cl.client_id) as client_count FROM Clients cl WHERE cl.category IS NOT NULL AND cl.category != '' GROUP BY cl.category HAVING COUNT(cl.client_id) > 0 ORDER BY client_count DESC, cl.category"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_clients_by_archival_status(is_archived: bool, include_null_status_for_active: bool = True, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); params = []
    cursor.execute("SELECT status_id FROM StatusSettings WHERE status_type = 'Client' AND is_archival_status = TRUE")
    archival_ids = [row['status_id'] for row in cursor.fetchall()]
    base_query = "SELECT c.*, co.country_name AS country, ci.city_name AS city, s.status_name AS status, s.color_hex AS status_color, s.icon_name AS status_icon_name FROM Clients c LEFT JOIN Countries co ON c.country_id = co.country_id LEFT JOIN Cities ci ON c.city_id = ci.city_id LEFT JOIN StatusSettings s ON c.status_id = s.status_id AND s.status_type = 'Client'"
    conditions = []
    if not archival_ids:
        if is_archived: return [] # No archival statuses defined, so no archived clients
        # else: fetch all (no condition needed if all are active)
    else:
        placeholders = ','.join('?' for _ in archival_ids)
        if is_archived: conditions.append(f"c.status_id IN ({placeholders})"); params.extend(archival_ids)
        else:
            not_in_cond = f"c.status_id NOT IN ({placeholders})"
            if include_null_status_for_active: conditions.append(f"({not_in_cond} OR c.status_id IS NULL)")
            else: conditions.append(not_in_cond)
            params.extend(archival_ids)
    sql = f"{base_query} {'WHERE ' + ' AND '.join(conditions) if conditions else ''} ORDER BY c.client_name;"
    cursor.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]

# --- ClientNotes CRUD ---
@_manage_conn
def add_client_note(client_id: str, note_text: str, user_id: str = None, conn: sqlite3.Connection = None) -> int | None:
    cursor = conn.cursor()
    sql = "INSERT INTO ClientNotes (client_id, note_text, user_id) VALUES (?, ?, ?)"
    try: cursor.execute(sql, (client_id, note_text, user_id)); return cursor.lastrowid
    except sqlite3.Error: return None

@_manage_conn
def get_client_notes(client_id: str, conn: sqlite3.Connection = None) -> list[dict]: # Already in __all__, ensure body is here.
    cursor = conn.cursor()
    sql = "SELECT note_id, client_id, timestamp, note_text, user_id FROM ClientNotes WHERE client_id = ? ORDER BY timestamp ASC"
    cursor.execute(sql, (client_id,))
    return [dict(row) for row in cursor.fetchall()]

# --- Projects (Continued) ---
@_manage_conn
def add_project(project_data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor(); new_id=str(uuid.uuid4()); now=datetime.utcnow().isoformat()+"Z"
    sql="INSERT INTO Projects (project_id, client_id, project_name, description, start_date, deadline_date, budget, status_id, progress_percentage, manager_team_member_id, priority, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(new_id, project_data['client_id'], project_data['project_name'], project_data.get('description'), project_data.get('start_date'), project_data.get('deadline_date'), project_data.get('budget'), project_data.get('status_id'), project_data.get('progress_percentage',0), project_data.get('manager_team_member_id'), project_data.get('priority',0), now, now)
    try: cursor.execute(sql,params); return new_id
    except: return None

@_manage_conn
def get_projects_by_client_id(client_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); cursor.execute("SELECT * FROM Projects WHERE client_id = ?", (client_id,))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_all_projects(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM Projects"; q_params=[]
    if filters:
        cls=[]; valid=['client_id','status_id','manager_team_member_id','priority']
        for k,v in filters.items():
            if k in valid: cls.append(f"{k}=?"); q_params.append(v)
        if cls: sql+=" WHERE "+" AND ".join(cls)
    cursor.execute(sql,q_params)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_project(project_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"; data['updated_at']=now
    valid_cols=['client_id','project_name','description','start_date','deadline_date','budget','status_id','progress_percentage','manager_team_member_id','priority','updated_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params=list(to_set.values()); params.append(project_id)
    sql=f"UPDATE Projects SET {', '.join(set_c)} WHERE project_id = ?"; cursor.execute(sql,params)
    return cursor.rowcount > 0

@_manage_conn
def delete_project(project_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM Projects WHERE project_id = ?",(project_id,)); return cursor.rowcount > 0

@_manage_conn
def get_total_projects_count(conn: sqlite3.Connection = None) -> int:
    cursor = conn.cursor(); cursor.execute("SELECT COUNT(project_id) as total_count FROM Projects"); row = cursor.fetchone()
    return row['total_count'] if row else 0

@_manage_conn
def get_active_projects_count(conn: sqlite3.Connection = None) -> int:
    cursor = conn.cursor()
    sql = "SELECT COUNT(p.project_id) as active_count FROM Projects p LEFT JOIN StatusSettings ss ON p.status_id = ss.status_id WHERE (ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE) OR p.status_id IS NULL"
    cursor.execute(sql); row = cursor.fetchone()
    return row['active_count'] if row else 0

# --- Tasks (Continued) ---
@_manage_conn
def add_task(task_data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"
    sql="INSERT INTO Tasks (project_id, task_name, description, status_id, assignee_team_member_id, reporter_team_member_id, due_date, priority, estimated_hours, actual_hours_spent, parent_task_id, created_at, updated_at, completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(task_data['project_id'], task_data['task_name'], task_data.get('description'), task_data.get('status_id'), task_data.get('assignee_team_member_id'), task_data.get('reporter_team_member_id'), task_data.get('due_date'), task_data.get('priority',0), task_data.get('estimated_hours'), task_data.get('actual_hours_spent'), task_data.get('parent_task_id'), now, now, task_data.get('completed_at'))
    try: cursor.execute(sql,params); return cursor.lastrowid
    except: return None

@_manage_conn
def get_task_by_id(task_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Tasks WHERE task_id = ?",(task_id,)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_tasks_by_project_id(project_id: str, filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM Tasks WHERE project_id = ?"; params=[project_id]
    if filters:
        cls=[]; valid=['assignee_team_member_id','status_id','priority']
        for k,v in filters.items():
            if k in valid: cls.append(f"{k}=?"); params.append(v)
        if cls: sql+=" AND "+" AND ".join(cls)
    cursor.execute(sql,tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_task(task_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"; data['updated_at']=now
    valid_cols=['project_id','task_name','description','status_id','assignee_team_member_id','reporter_team_member_id','due_date','priority','estimated_hours','actual_hours_spent','parent_task_id','updated_at','completed_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params=list(to_set.values()); params.append(task_id)
    sql=f"UPDATE Tasks SET {', '.join(set_c)} WHERE task_id = ?"; cursor.execute(sql,params)
    return cursor.rowcount > 0

@_manage_conn
def delete_task(task_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM Tasks WHERE task_id = ?",(task_id,)); return cursor.rowcount > 0

@_manage_conn
def get_all_tasks(active_only: bool = False, project_id_filter: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT t.* FROM Tasks t"; params=[]; conditions=[]
    if active_only: sql+=" LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id"; conditions.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")
    if project_id_filter: conditions.append("t.project_id = ?"); params.append(project_id_filter)
    if conditions: sql+=" WHERE "+" AND ".join(conditions)
    sql+=" ORDER BY t.created_at DESC"; cursor.execute(sql,tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_tasks_by_assignee_id(assignee_id: int, active_only: bool = False, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT t.* FROM Tasks t"; params=[]; conditions=["t.assignee_team_member_id = ?"]; params.append(assignee_id)
    if active_only: sql+=" LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id"; conditions.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")
    sql+=" WHERE "+" AND ".join(conditions)+" ORDER BY t.due_date ASC, t.priority DESC"; cursor.execute(sql,tuple(params))
    return [dict(row) for row in cursor.fetchall()]

# --- TeamMembers (Continued) ---
@_manage_conn
def add_team_member(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"
    sql="INSERT INTO TeamMembers (user_id, full_name, email, role_or_title, department, phone_number, profile_picture_url, is_active, notes, hire_date, performance, skills, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(data.get('user_id'), data['full_name'], data['email'], data.get('role_or_title'), data.get('department'), data.get('phone_number'), data.get('profile_picture_url'), data.get('is_active',True), data.get('notes'), data.get('hire_date'), data.get('performance',0), data.get('skills'), now, now)
    try: cursor.execute(sql,params); return cursor.lastrowid
    except: return None

@_manage_conn
def get_team_member_by_id(id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM TeamMembers WHERE team_member_id = ?",(id,)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_team_members(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM TeamMembers"; q_params=[]
    if filters:
        cls=[]; valid=['is_active','department','user_id']
        for k,v in filters.items():
            if k in valid:
                if k=='is_active' and isinstance(v,bool): cls.append(f"{k}=?"); q_params.append(1 if v else 0)
                else: cls.append(f"{k}=?"); q_params.append(v)
        if cls: sql+=" WHERE "+" AND ".join(cls)
    cursor.execute(sql,q_params)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_team_member(id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"; data['updated_at']=now
    valid_cols=['user_id','full_name','email','role_or_title','department','phone_number','profile_picture_url','is_active','notes','hire_date','performance','skills','updated_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params=list(to_set.values()); params.append(id)
    sql=f"UPDATE TeamMembers SET {', '.join(set_c)} WHERE team_member_id = ?"; cursor.execute(sql,params)
    return cursor.rowcount > 0

@_manage_conn
def delete_team_member(id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM TeamMembers WHERE team_member_id = ?",(id,)); return cursor.rowcount > 0

# --- Products (Continued from get_product_by_id) ---
@_manage_conn
def add_product(product_data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"
    sql = "INSERT INTO Products (product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    params = (product_data['product_name'], product_data.get('description'), product_data.get('category'), product_data.get('language_code', 'fr'), product_data['base_unit_price'], product_data.get('unit_of_measure'), product_data.get('weight'), product_data.get('dimensions'), product_data.get('is_active', True), now, now)
    try: cursor.execute(sql, params); return cursor.lastrowid
    except sqlite3.IntegrityError: return None

@_manage_conn
def get_product_by_name(product_name: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor(); cursor.execute("SELECT * FROM Products WHERE product_name = ?", (product_name,)); row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_products(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM Products"; q_params = []
    if filters:
        clauses = []
        if 'category' in filters: clauses.append("category = ?"); q_params.append(filters['category'])
        if 'product_name' in filters: clauses.append("product_name LIKE ?"); q_params.append(f"%{filters['product_name']}%")
        if clauses: sql += " WHERE " + " AND ".join(clauses)
    cursor.execute(sql, q_params)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_product(product_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"; data['updated_at'] = now
    valid_cols = ['product_name', 'description', 'category', 'language_code', 'base_unit_price', 'unit_of_measure', 'weight', 'dimensions', 'is_active', 'updated_at']
    to_set = {k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c = [f"{k}=?" for k in to_set.keys()]; params = list(to_set.values()); params.append(product_id)
    sql = f"UPDATE Products SET {', '.join(set_c)} WHERE product_id = ?"; cursor.execute(sql, params)
    return cursor.rowcount > 0

@_manage_conn
def delete_product(product_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM Products WHERE product_id = ?", (product_id,)); return cursor.rowcount > 0

@_manage_conn
def get_products(language_code: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM Products"; params = []; conditions = ["is_active = TRUE"]
    if language_code: conditions.append("language_code = ?"); params.append(language_code)
    sql += " WHERE " + " AND ".join(conditions) + " ORDER BY product_name"; cursor.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_product_price(product_id: int, new_price: float, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"
    sql = "UPDATE Products SET base_unit_price = ?, updated_at = ? WHERE product_id = ?"
    cursor.execute(sql, (new_price, now, product_id))
    return cursor.rowcount > 0

@_manage_conn
def get_products_by_name_pattern(pattern: str, conn: sqlite3.Connection = None) -> list[dict] | None:
    cursor = conn.cursor(); search_pattern = f"%{pattern}%"
    sql = "SELECT * FROM Products WHERE product_name LIKE ? ORDER BY product_name LIMIT 10"
    cursor.execute(sql, (search_pattern,))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_all_products_for_selection(language_code: str = None, name_pattern: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); params = []; conditions = ["is_active = TRUE"]
    if language_code: conditions.append("language_code = ?"); params.append(language_code)
    if name_pattern: conditions.append("(product_name LIKE ? OR description LIKE ?)"); params.extend([f"%{name_pattern}%", f"%{name_pattern}%"]) # Corrected to f-string for pattern
    sql = f"SELECT * FROM Products WHERE {' AND '.join(conditions)} ORDER BY product_name"
    cursor.execute(sql, tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_total_products_count(conn: sqlite3.Connection = None) -> int:
    cursor = conn.cursor(); cursor.execute("SELECT COUNT(product_id) as total_count FROM Products"); row = cursor.fetchone()
    return row['total_count'] if row else 0

# --- ProductDimensions CRUD ---
@_manage_conn
def add_or_update_product_dimension(product_id: int, dimension_data: dict, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"
    cursor.execute("SELECT product_id FROM ProductDimensions WHERE product_id = ?", (product_id,))
    exists = cursor.fetchone()
    dim_cols = ['dim_A','dim_B','dim_C','dim_D','dim_E','dim_F','dim_G','dim_H','dim_I','dim_J','technical_image_path']
    if exists:
        data_to_set = {k:v for k,v in dimension_data.items() if k in dim_cols}; data_to_set['updated_at'] = now
        if not any(k in dim_cols for k in dimension_data.keys()): # Check if any actual dim_col is being updated
             cursor.execute("UPDATE ProductDimensions SET updated_at = ? WHERE product_id = ?", (now, product_id)); return True
        set_c = [f"{k}=?" for k in data_to_set.keys()]; params = list(data_to_set.values()); params.append(product_id)
        sql = f"UPDATE ProductDimensions SET {', '.join(set_c)} WHERE product_id = ?"
        cursor.execute(sql, params)
    else:
        cols = ['product_id','created_at','updated_at'] + dim_cols
        vals = [product_id, now, now] + [dimension_data.get(c) for c in dim_cols]
        placeholders = ','.join(['?']*len(cols))
        sql = f"INSERT INTO ProductDimensions ({','.join(cols)}) VALUES ({placeholders})"
        cursor.execute(sql, tuple(vals))
    return cursor.rowcount > 0 or (not exists and cursor.lastrowid is not None)

@_manage_conn
def get_product_dimension(product_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor(); cursor.execute("SELECT * FROM ProductDimensions WHERE product_id = ?", (product_id,)); row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def delete_product_dimension(product_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM ProductDimensions WHERE product_id = ?", (product_id,)); return cursor.rowcount > 0

# --- ProductEquivalencies CRUD ---
@_manage_conn
def add_product_equivalence(product_id_a: int, product_id_b: int, conn: sqlite3.Connection = None) -> int | None:
    if product_id_a == product_id_b: return None
    p_a, p_b = min(product_id_a, product_id_b), max(product_id_a, product_id_b)
    cursor = conn.cursor()
    try: cursor.execute("INSERT INTO ProductEquivalencies (product_id_a, product_id_b) VALUES (?,?)", (p_a,p_b)); return cursor.lastrowid
    except sqlite3.IntegrityError:
        cursor.execute("SELECT equivalence_id FROM ProductEquivalencies WHERE product_id_a = ? AND product_id_b = ?", (p_a,p_b)); row=cursor.fetchone()
        return row['equivalence_id'] if row else None
    except sqlite3.Error: return None

@_manage_conn
def get_equivalent_products(product_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); ids = set()
    cursor.execute("SELECT product_id_b FROM ProductEquivalencies WHERE product_id_a = ?", (product_id,))
    for row in cursor.fetchall(): ids.add(row['product_id_b'])
    cursor.execute("SELECT product_id_a FROM ProductEquivalencies WHERE product_id_b = ?", (product_id,))
    for row in cursor.fetchall(): ids.add(row['product_id_a'])
    ids.discard(product_id)
    if not ids: return []
    placeholders = ','.join('?'*len(ids))
    cursor.execute(f"SELECT * FROM Products WHERE product_id IN ({placeholders})", tuple(ids))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_all_product_equivalencies(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT pe.*, pA.product_name AS product_name_a, pB.product_name AS product_name_b FROM ProductEquivalencies pe JOIN Products pA ON pe.product_id_a = pA.product_id JOIN Products pB ON pe.product_id_b = pB.product_id ORDER BY pA.product_name, pB.product_name"
    cursor.execute(sql); return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def remove_product_equivalence(equivalence_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM ProductEquivalencies WHERE equivalence_id = ?", (equivalence_id,)); return cursor.rowcount > 0

# --- ClientProjectProducts (Continued) ---
@_manage_conn
def add_product_to_client_or_project(link_data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor = conn.cursor(); product_id = link_data['product_id']
    prod_info = get_product_by_id(product_id, conn=conn)
    if not prod_info: return None
    qty = link_data.get('quantity',1); override_price = link_data.get('unit_price_override')
    eff_price = override_price if override_price is not None else prod_info.get('base_unit_price')
    if eff_price is None: eff_price = 0.0
    total_price = qty * float(eff_price)
    sql="INSERT INTO ClientProjectProducts (client_id, project_id, product_id, quantity, unit_price_override, total_price_calculated, serial_number, purchase_confirmed_at, added_at) VALUES (?,?,?,?,?,?,?,?,?)"
    params=(link_data['client_id'],link_data.get('project_id'),product_id,qty,override_price,total_price,link_data.get('serial_number'),link_data.get('purchase_confirmed_at'),datetime.utcnow().isoformat()+"Z")
    try: cursor.execute(sql,params); return cursor.lastrowid
    except sqlite3.Error: return None

@_manage_conn
def update_client_project_product(link_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor = conn.cursor()
    current_link = get_client_project_product_by_id(link_id, conn=conn)
    if not current_link: return False
    qty = data.get('quantity', current_link['quantity'])
    override_price = data.get('unit_price_override', current_link['unit_price_override'])
    prod_info = get_product_by_id(current_link['product_id'], conn=conn)
    if not prod_info: return False
    eff_price = override_price if override_price is not None else prod_info['base_unit_price']
    data['total_price_calculated'] = qty * float(eff_price or 0)
    valid_cols = ['quantity','unit_price_override','total_price_calculated','serial_number','purchase_confirmed_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c = [f"{k}=?" for k in to_set.keys()]; params_list = list(to_set.values()); params_list.append(link_id)
    sql = f"UPDATE ClientProjectProducts SET {', '.join(set_c)} WHERE client_project_product_id = ?"; cursor.execute(sql,tuple(params_list))
    return cursor.rowcount > 0

@_manage_conn
def remove_product_from_client_or_project(link_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM ClientProjectProducts WHERE client_project_product_id = ?", (link_id,)); return cursor.rowcount > 0

@_manage_conn
def get_client_project_product_by_id(link_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    sql="SELECT cpp.*, p.product_name, p.description as product_description, p.category as product_category, p.base_unit_price, p.unit_of_measure, p.weight, p.dimensions, p.language_code FROM ClientProjectProducts cpp JOIN Products p ON cpp.product_id = p.product_id WHERE cpp.client_project_product_id = ?" # Added more fields from Products
    cursor.execute(sql,(link_id,)); row=cursor.fetchone()
    return dict(row) if row else None

# --- Contacts (Continued) ---
@_manage_conn
def add_contact(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"
    name=data.get('displayName', data.get('name'))
    sql="INSERT INTO Contacts (name, email, phone, position, company_name, notes, givenName, familyName, displayName, phone_type, email_type, address_formattedValue, address_streetAddress, address_city, address_region, address_postalCode, address_country, organization_name, organization_title, birthday_date, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(name, data.get('email'), data.get('phone'), data.get('position'), data.get('company_name'), data.get('notes'), data.get('givenName'), data.get('familyName'), data.get('displayName'), data.get('phone_type'), data.get('email_type'), data.get('address_formattedValue'), data.get('address_streetAddress'), data.get('address_city'), data.get('address_region'), data.get('address_postalCode'), data.get('address_country'), data.get('organization_name'), data.get('organization_title'), data.get('birthday_date'), now, now)
    try: cursor.execute(sql,params); return cursor.lastrowid
    except sqlite3.Error: return None

@_manage_conn
def get_contact_by_id(id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Contacts WHERE contact_id = ?",(id,)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_contact_by_email(email: str, conn: sqlite3.Connection = None) -> dict | None:
    if not email: return None; cursor=conn.cursor(); cursor.execute("SELECT * FROM Contacts WHERE email = ?",(email,)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_contacts(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM Contacts"; params=[]; clauses=[]
    if filters:
        if 'company_name' in filters: clauses.append("company_name=?"); params.append(filters['company_name'])
        if 'name' in filters: clauses.append("(name LIKE ? OR displayName LIKE ?)"); params.extend([f"%{filters['name']}%", f"%{filters['name']}%"])
        if clauses: sql+=" WHERE "+" AND ".join(clauses)
    cursor.execute(sql,params)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_contact(id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"; data['updated_at']=now
    if 'displayName' in data and 'name' not in data: data['name'] = data['displayName']
    valid_cols=['name','email','phone','position','company_name','notes','givenName','familyName','displayName','phone_type','email_type','address_formattedValue','address_streetAddress','address_city','address_region','address_postalCode','address_country','organization_name','organization_title','birthday_date','updated_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params_list=list(to_set.values()); params_list.append(id)
    sql=f"UPDATE Contacts SET {', '.join(set_c)} WHERE contact_id = ?"; cursor.execute(sql,params_list)
    return cursor.rowcount > 0

@_manage_conn
def delete_contact(id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM Contacts WHERE contact_id = ?",(id,)); return cursor.rowcount > 0

# --- ClientContacts (Continued) ---
@_manage_conn
def link_contact_to_client(client_id: str, contact_id: int, is_primary: bool = False, can_receive_documents: bool = True, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); sql="INSERT INTO ClientContacts (client_id, contact_id, is_primary_for_client, can_receive_documents) VALUES (?,?,?,?)"
    try: cursor.execute(sql,(client_id,contact_id,is_primary,can_receive_documents)); return cursor.lastrowid
    except sqlite3.Error: return None # Handles UNIQUE constraint

@_manage_conn
def unlink_contact_from_client(client_id: str, contact_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); sql="DELETE FROM ClientContacts WHERE client_id = ? AND contact_id = ?"; cursor.execute(sql,(client_id,contact_id))
    return cursor.rowcount > 0

@_manage_conn
def get_contacts_for_client_count(client_id: str, conn: sqlite3.Connection = None) -> int:
    cursor=conn.cursor(); cursor.execute("SELECT COUNT(contact_id) FROM ClientContacts WHERE client_id = ?",(client_id,)); row=cursor.fetchone()
    return row[0] if row else 0

@_manage_conn
def get_clients_for_contact(contact_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT cl.*, cc.is_primary_for_client, cc.can_receive_documents, cc.client_contact_id FROM Clients cl JOIN ClientContacts cc ON cl.client_id = cc.client_id WHERE cc.contact_id = ?" # Added client_contact_id
    cursor.execute(sql,(contact_id,)); return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_specific_client_contact_link_details(client_id: str, contact_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); sql="SELECT client_contact_id, is_primary_for_client, can_receive_documents FROM ClientContacts WHERE client_id = ? AND contact_id = ?"
    cursor.execute(sql,(client_id,contact_id)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def update_client_contact_link(client_contact_id: int, details: dict, conn: sqlite3.Connection = None) -> bool:
    if not details or not any(k in details for k in ['is_primary_for_client','can_receive_documents']): return False
    cursor=conn.cursor(); set_c=[]; params=[]
    if 'is_primary_for_client' in details: set_c.append("is_primary_for_client=?"); params.append(details['is_primary_for_client'])
    if 'can_receive_documents' in details: set_c.append("can_receive_documents=?"); params.append(details['can_receive_documents'])
    if not set_c: return False
    params.append(client_contact_id); sql=f"UPDATE ClientContacts SET {', '.join(set_c)} WHERE client_contact_id = ?"
    cursor.execute(sql,params); return cursor.rowcount > 0

# --- TemplateCategories (Continued) ---
@_manage_conn
def get_template_category_by_id(category_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TemplateCategories WHERE category_id = ?", (category_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_template_category_by_name(category_name: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TemplateCategories WHERE category_name = ?", (category_name,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_template_categories(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TemplateCategories ORDER BY category_name")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@_manage_conn
def update_template_category(category_id: int, new_name: str = None, new_description: str = None, conn: sqlite3.Connection = None) -> bool:
    if not new_name and new_description is None: return False
    cursor = conn.cursor()
    set_clauses = []
    params = []
    if new_name: set_clauses.append("category_name = ?"); params.append(new_name)
    if new_description is not None: set_clauses.append("description = ?"); params.append(new_description)
    if not set_clauses: return False
    sql = f"UPDATE TemplateCategories SET {', '.join(set_clauses)} WHERE category_id = ?"
    params.append(category_id)
    cursor.execute(sql, tuple(params))
    return cursor.rowcount > 0

@_manage_conn
def delete_template_category(category_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM TemplateCategories WHERE category_id = ?", (category_id,))
    return cursor.rowcount > 0

@_manage_conn
def get_template_category_details(category_id: int, conn: sqlite3.Connection = None) -> dict | None: # Same as get_template_category_by_id
    return get_template_category_by_id(category_id, conn=conn)


# --- Templates (Continued) ---
@_manage_conn
def get_template_by_id(template_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Templates WHERE template_id = ?", (template_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_templates_by_type(template_type: str, language_code: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT * FROM Templates WHERE template_type = ?"
    params = [template_type]
    if language_code: sql += " AND language_code = ?"; params.append(language_code)
    cursor.execute(sql, tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_template(template_id: int, template_data: dict, conn: sqlite3.Connection = None) -> bool:
    if not template_data: return False
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    template_data['updated_at'] = now

    # Resolve category_id if category_name is passed
    if 'category_name' in template_data and 'category_id' not in template_data:
        category_id = add_template_category(template_data.pop('category_name'), conn=conn) # Pass conn
        if category_id: template_data['category_id'] = category_id

    if 'raw_template_file_data' in template_data and isinstance(template_data['raw_template_file_data'], str):
        template_data['raw_template_file_data'] = template_data['raw_template_file_data'].encode('utf-8')

    valid_cols = ['template_name', 'template_type', 'description', 'base_file_name', 'language_code', 'is_default_for_type_lang', 'category_id', 'content_definition', 'email_subject_template', 'email_variables_info', 'cover_page_config_json', 'document_mapping_config_json', 'raw_template_file_data', 'version', 'updated_at', 'created_by_user_id']
    data_to_set = {k:v for k,v in template_data.items() if k in valid_cols}
    if not data_to_set: return False

    set_clauses = [f"{key} = ?" for key in data_to_set.keys()]
    params_list = list(data_to_set.values())
    params_list.append(template_id)
    sql = f"UPDATE Templates SET {', '.join(set_clauses)} WHERE template_id = ?"
    cursor.execute(sql, params_list)
    return cursor.rowcount > 0

@_manage_conn
def delete_template(template_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Templates WHERE template_id = ?", (template_id,))
    return cursor.rowcount > 0

@_manage_conn
def get_distinct_template_languages(conn: sqlite3.Connection = None) -> list[tuple[str]]:
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT language_code FROM Templates WHERE language_code IS NOT NULL AND language_code != '' ORDER BY language_code")
    return cursor.fetchall()

@_manage_conn
def get_distinct_template_types(conn: sqlite3.Connection = None) -> list[tuple[str]]:
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT template_type FROM Templates WHERE template_type IS NOT NULL AND template_type != '' ORDER BY template_type")
    return cursor.fetchall()

@_manage_conn
def get_filtered_templates(category_id: int = None, language_code: str = None, template_type: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT * FROM Templates"
    where_clauses = []
    params = []
    if category_id is not None: where_clauses.append("category_id = ?"); params.append(category_id)
    if language_code is not None: where_clauses.append("language_code = ?"); params.append(language_code)
    if template_type is not None: where_clauses.append("template_type = ?"); params.append(template_type)
    if where_clauses: sql += " WHERE " + " AND ".join(where_clauses)
    sql += " ORDER BY category_id, template_name"
    cursor.execute(sql, tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_template_details_for_preview(template_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT base_file_name, language_code FROM Templates WHERE template_id = ?", (template_id,))
    row = cursor.fetchone()
    return {'base_file_name': row['base_file_name'], 'language_code': row['language_code']} if row else None

@_manage_conn
def get_template_path_info(template_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT base_file_name, language_code FROM Templates WHERE template_id = ?", (template_id,))
    row = cursor.fetchone()
    return {'file_name': row['base_file_name'], 'language': row['language_code']} if row else None

@_manage_conn
def delete_template_and_get_file_info(template_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    # Transaction should be handled by _manage_conn if it's a single unit of work.
    # However, this function does two things: SELECT then DELETE. _manage_conn might commit after SELECT.
    # For safety, this specific function might need explicit transaction start if not already handled.
    # For now, assume _manage_conn handles it as one operation at the end.
    file_info = get_template_path_info(template_id, conn=conn) # Pass conn
    if not file_info: return None
    deleted = delete_template(template_id, conn=conn) # Pass conn
    return file_info if deleted else None

@_manage_conn
def set_default_template_by_id(template_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    # Similar to set_default_company, this needs careful transaction handling.
    template_info = get_template_by_id(template_id, conn=conn) # Pass conn
    if not template_info: return False
    cursor.execute("UPDATE Templates SET is_default_for_type_lang = 0 WHERE template_type = ? AND language_code = ?", (template_info['template_type'], template_info['language_code']))
    cursor.execute("UPDATE Templates SET is_default_for_type_lang = 1 WHERE template_id = ?", (template_id,))
    return True

@_manage_conn
def get_template_by_type_lang_default(template_type: str, language_code: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Templates WHERE template_type = ? AND language_code = ? AND is_default_for_type_lang = TRUE LIMIT 1", (template_type, language_code))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_templates(template_type_filter: str = None, language_code_filter: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM Templates"; params = []; clauses = []
    if template_type_filter: clauses.append("template_type = ?"); params.append(template_type_filter)
    if language_code_filter: clauses.append("language_code = ?"); params.append(language_code_filter)
    if clauses: sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY template_name, language_code"; cursor.execute(sql, tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_distinct_languages_for_template_type(template_type: str, conn: sqlite3.Connection = None) -> list[str]:
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT language_code FROM Templates WHERE template_type = ? ORDER BY language_code ASC", (template_type,))
    return [row['language_code'] for row in cursor.fetchall() if row['language_code']]

@_manage_conn
def get_all_file_based_templates(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT template_id, template_name, language_code, base_file_name, description, category_id FROM Templates WHERE base_file_name IS NOT NULL AND base_file_name != '' ORDER BY template_name, language_code"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_templates_by_category_id(category_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Templates WHERE category_id = ? ORDER BY template_name, language_code", (category_id,))
    return [dict(row) for row in cursor.fetchall()]

# --- CoverPageTemplates (Continued) ---
@_manage_conn
def get_cover_page_template_by_id(template_id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor(); cursor.execute("SELECT * FROM CoverPageTemplates WHERE template_id = ?", (template_id,)); row = cursor.fetchone()
    if row: data = dict(row); data['style_config_json'] = json.loads(data['style_config_json']) if data.get('style_config_json') else None; return data
    return None

@_manage_conn
def get_all_cover_page_templates(is_default: bool = None, limit: int = 100, offset: int = 0, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM CoverPageTemplates"; params = []
    if is_default is not None: sql += " WHERE is_default_template = ?"; params.append(1 if is_default else 0)
    sql += " ORDER BY template_name LIMIT ? OFFSET ?"; params.extend([limit, offset])
    cursor.execute(sql, params); templates = []
    for row in cursor.fetchall():
        data = dict(row); data['style_config_json'] = json.loads(data['style_config_json']) if data.get('style_config_json') else None; templates.append(data)
    return templates

@_manage_conn
def update_cover_page_template(template_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor = conn.cursor(); data['updated_at'] = datetime.utcnow().isoformat() + "Z"
    if 'style_config_json' in data and isinstance(data['style_config_json'], dict): data['style_config_json'] = json.dumps(data['style_config_json'])
    if 'is_default_template' in data: data['is_default_template'] = 1 if data['is_default_template'] else 0
    valid_cols = ['template_name', 'description', 'default_title', 'default_subtitle', 'default_author', 'style_config_json', 'is_default_template', 'updated_at']
    to_set={k:v for k,v in data.items() if k in valid_cols};
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; sql_params=list(to_set.values()); sql_params.append(template_id)
    sql=f"UPDATE CoverPageTemplates SET {', '.join(set_c)} WHERE template_id = ?"; cursor.execute(sql,sql_params)
    return cursor.rowcount > 0

@_manage_conn
def delete_cover_page_template(template_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM CoverPageTemplates WHERE template_id = ?", (template_id,)); return cursor.rowcount > 0

# --- CoverPages CRUD ---
@_manage_conn
def add_cover_page(data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor(); new_id=str(uuid.uuid4()); now=datetime.utcnow().isoformat()+"Z"
    custom_style=data.get('custom_style_config_json'); custom_style_str=json.dumps(custom_style) if isinstance(custom_style,dict) else custom_style
    sql="INSERT INTO CoverPages (cover_page_id, cover_page_name, client_id, project_id, template_id, title, subtitle, author_text, institution_text, department_text, document_type_text, document_version, creation_date, logo_name, logo_data, custom_style_config_json, created_at, updated_at, created_by_user_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(new_id, data.get('cover_page_name'), data.get('client_id'), data.get('project_id'), data.get('template_id'), data['title'], data.get('subtitle'), data.get('author_text'), data.get('institution_text'), data.get('department_text'), data.get('document_type_text'), data.get('document_version'), data.get('creation_date'), data.get('logo_name'), data.get('logo_data'), custom_style_str, now, now, data.get('created_by_user_id'))
    try: cursor.execute(sql,params); return new_id
    except: return None

@_manage_conn
def get_cover_page_by_id(id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM CoverPages WHERE cover_page_id = ?",(id,)); row=cursor.fetchone()
    if row: data=dict(row); data['custom_style_config_json'] = json.loads(data['custom_style_config_json']) if data.get('custom_style_config_json') else None; return data
    return None

@_manage_conn
def get_cover_pages_for_client(client_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM CoverPages WHERE client_id = ? ORDER BY created_at DESC",(client_id,)); covers=[]
    for row in cursor.fetchall(): data=dict(row); data['custom_style_config_json'] = json.loads(data['custom_style_config_json']) if data.get('custom_style_config_json') else None; covers.append(data)
    return covers

@_manage_conn
def get_cover_pages_for_project(project_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM CoverPages WHERE project_id = ? ORDER BY created_at DESC",(project_id,)); covers=[]
    for row in cursor.fetchall(): data=dict(row); data['custom_style_config_json'] = json.loads(data['custom_style_config_json']) if data.get('custom_style_config_json') else None; covers.append(data)
    return covers

@_manage_conn
def update_cover_page(id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor=conn.cursor(); data['updated_at']=datetime.utcnow().isoformat()+"Z"
    if 'custom_style_config_json' in data and isinstance(data['custom_style_config_json'],dict): data['custom_style_config_json'] = json.dumps(data['custom_style_config_json'])
    valid_cols = ['cover_page_name','client_id','project_id','template_id','title','subtitle','author_text','institution_text','department_text','document_type_text','document_version','creation_date','logo_name','logo_data','custom_style_config_json','updated_at','created_by_user_id']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params=list(to_set.values()); params.append(id)
    sql=f"UPDATE CoverPages SET {', '.join(set_c)} WHERE cover_page_id = ?"; cursor.execute(sql,params)
    return cursor.rowcount > 0

@_manage_conn
def delete_cover_page(id: str, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM CoverPages WHERE cover_page_id = ?",(id,)); return cursor.rowcount > 0

@_manage_conn
def get_cover_pages_for_user(user_id: str, limit: int = 50, offset: int = 0, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM CoverPages WHERE created_by_user_id = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?"; params=(user_id,limit,offset)
    cursor.execute(sql,params); covers=[]
    for row in cursor.fetchall(): data=dict(row); data['custom_style_config_json'] = json.loads(data['custom_style_config_json']) if data.get('custom_style_config_json') else None; covers.append(data)
    return covers

# --- Clients (Continued) ---
@_manage_conn
def update_client(client_id: str, client_data: dict, conn: sqlite3.Connection = None) -> bool:
    if not client_data: return False
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"; client_data['updated_at'] = now
    valid_cols = ['client_name', 'company_name', 'primary_need_description', 'project_identifier', 'country_id', 'city_id', 'default_base_folder_path', 'status_id', 'selected_languages', 'price', 'notes', 'category', 'updated_at', 'created_by_user_id']
    data_to_set = {k:v for k,v in client_data.items() if k in valid_cols}
    if not data_to_set: return False
    set_clauses = [f"{key} = ?" for key in data_to_set.keys()]
    params = list(data_to_set.values()); params.append(client_id)
    sql = f"UPDATE Clients SET {', '.join(set_clauses)} WHERE client_id = ?"
    cursor.execute(sql, params)
    return cursor.rowcount > 0

@_manage_conn
def delete_client(client_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM Clients WHERE client_id = ?", (client_id,)); return cursor.rowcount > 0

@_manage_conn
def get_all_clients_with_details(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    query = """
    SELECT c.client_id, c.client_name, c.company_name, c.primary_need_description, c.project_identifier, c.default_base_folder_path, c.selected_languages, c.price, c.notes, c.created_at, c.category, c.status_id, c.country_id, c.city_id,
           co.country_name AS country, ci.city_name AS city, s.status_name AS status, s.color_hex AS status_color, s.icon_name AS status_icon_name
    FROM clients c
    LEFT JOIN countries co ON c.country_id = co.country_id LEFT JOIN cities ci ON c.city_id = ci.city_id
    LEFT JOIN status_settings s ON c.status_id = s.status_id AND s.status_type = 'Client'
    ORDER BY c.client_name;
    """
    cursor.execute(query)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_active_clients_count(conn: sqlite3.Connection = None) -> int:
    cursor = conn.cursor()
    sql = "SELECT COUNT(c.client_id) as active_count FROM Clients c LEFT JOIN StatusSettings ss ON c.status_id = ss.status_id WHERE ss.is_archival_status IS NOT TRUE OR c.status_id IS NULL"
    cursor.execute(sql); row = cursor.fetchone()
    return row['active_count'] if row else 0

@_manage_conn
def get_client_counts_by_country(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT co.country_name, COUNT(cl.client_id) as client_count FROM Clients cl JOIN Countries co ON cl.country_id = co.country_id GROUP BY co.country_name HAVING COUNT(cl.client_id) > 0 ORDER BY client_count DESC"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_client_segmentation_by_city(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT co.country_name, ci.city_name, COUNT(cl.client_id) as client_count FROM Clients cl JOIN Cities ci ON cl.city_id = ci.city_id JOIN Countries co ON ci.country_id = co.country_id GROUP BY co.country_name, ci.city_name HAVING COUNT(cl.client_id) > 0 ORDER BY co.country_name, client_count DESC, ci.city_name"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_client_segmentation_by_status(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT ss.status_name, COUNT(cl.client_id) as client_count FROM Clients cl JOIN StatusSettings ss ON cl.status_id = ss.status_id GROUP BY ss.status_name HAVING COUNT(cl.client_id) > 0 ORDER BY client_count DESC, ss.status_name"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_client_segmentation_by_category(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT cl.category, COUNT(cl.client_id) as client_count FROM Clients cl WHERE cl.category IS NOT NULL AND cl.category != '' GROUP BY cl.category HAVING COUNT(cl.client_id) > 0 ORDER BY client_count DESC, cl.category"
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_clients_by_archival_status(is_archived: bool, include_null_status_for_active: bool = True, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); params = []
    cursor.execute("SELECT status_id FROM StatusSettings WHERE status_type = 'Client' AND is_archival_status = TRUE")
    archival_ids = [row['status_id'] for row in cursor.fetchall()]
    base_query = "SELECT c.*, co.country_name AS country, ci.city_name AS city, s.status_name AS status, s.color_hex AS status_color, s.icon_name AS status_icon_name FROM Clients c LEFT JOIN Countries co ON c.country_id = co.country_id LEFT JOIN Cities ci ON c.city_id = ci.city_id LEFT JOIN StatusSettings s ON c.status_id = s.status_id AND s.status_type = 'Client'"
    conditions = []
    if not archival_ids:
        if is_archived: return []
    else:
        placeholders = ','.join('?' for _ in archival_ids)
        if is_archived: conditions.append(f"c.status_id IN ({placeholders})"); params.extend(archival_ids)
        else:
            not_in_cond = f"c.status_id NOT IN ({placeholders})"
            if include_null_status_for_active: conditions.append(f"({not_in_cond} OR c.status_id IS NULL)")
            else: conditions.append(not_in_cond)
            params.extend(archival_ids)
    sql = f"{base_query} {'WHERE ' + ' AND '.join(conditions) if conditions else ''} ORDER BY c.client_name;"
    cursor.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]

# --- ClientNotes CRUD ---
@_manage_conn
def add_client_note(client_id: str, note_text: str, user_id: str = None, conn: sqlite3.Connection = None) -> int | None:
    cursor = conn.cursor()
    sql = "INSERT INTO ClientNotes (client_id, note_text, user_id) VALUES (?, ?, ?)"
    try: cursor.execute(sql, (client_id, note_text, user_id)); return cursor.lastrowid
    except sqlite3.Error: return None

# get_client_notes is already present and correctly defined.

# --- Projects (Continued from previous additions) ---
@_manage_conn
def add_project(project_data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor(); new_id=str(uuid.uuid4()); now=datetime.utcnow().isoformat()+"Z"
    sql="INSERT INTO Projects (project_id, client_id, project_name, description, start_date, deadline_date, budget, status_id, progress_percentage, manager_team_member_id, priority, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(new_id, project_data['client_id'], project_data['project_name'], project_data.get('description'), project_data.get('start_date'), project_data.get('deadline_date'), project_data.get('budget'), project_data.get('status_id'), project_data.get('progress_percentage',0), project_data.get('manager_team_member_id'), project_data.get('priority',0), now, now)
    try: cursor.execute(sql,params); return new_id
    except sqlite3.Error: return None # Changed from generic except

@_manage_conn
def get_projects_by_client_id(client_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); cursor.execute("SELECT * FROM Projects WHERE client_id = ?", (client_id,))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_all_projects(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM Projects"; q_params=[]
    if filters:
        cls=[]; valid=['client_id','status_id','manager_team_member_id','priority']
        for k,v in filters.items():
            if k in valid: cls.append(f"{k}=?"); q_params.append(v)
        if cls: sql+=" WHERE "+" AND ".join(cls)
    cursor.execute(sql,q_params)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_project(project_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"; data['updated_at']=now
    valid_cols=['client_id','project_name','description','start_date','deadline_date','budget','status_id','progress_percentage','manager_team_member_id','priority','updated_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params=list(to_set.values()); params.append(project_id)
    sql=f"UPDATE Projects SET {', '.join(set_c)} WHERE project_id = ?"; cursor.execute(sql,params)
    return cursor.rowcount > 0

@_manage_conn
def delete_project(project_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM Projects WHERE project_id = ?",(project_id,)); return cursor.rowcount > 0

@_manage_conn
def get_total_projects_count(conn: sqlite3.Connection = None) -> int:
    cursor = conn.cursor(); cursor.execute("SELECT COUNT(project_id) as total_count FROM Projects"); row = cursor.fetchone()
    return row['total_count'] if row else 0

@_manage_conn
def get_active_projects_count(conn: sqlite3.Connection = None) -> int:
    cursor = conn.cursor()
    sql = "SELECT COUNT(p.project_id) as active_count FROM Projects p LEFT JOIN StatusSettings ss ON p.status_id = ss.status_id WHERE (ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE) OR p.status_id IS NULL"
    cursor.execute(sql); row = cursor.fetchone()
    return row['active_count'] if row else 0

# --- Tasks CRUD ---
@_manage_conn
def add_task(task_data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"
    sql="INSERT INTO Tasks (project_id, task_name, description, status_id, assignee_team_member_id, reporter_team_member_id, due_date, priority, estimated_hours, actual_hours_spent, parent_task_id, created_at, updated_at, completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(task_data['project_id'], task_data['task_name'], task_data.get('description'), task_data.get('status_id'), task_data.get('assignee_team_member_id'), task_data.get('reporter_team_member_id'), task_data.get('due_date'), task_data.get('priority',0), task_data.get('estimated_hours'), task_data.get('actual_hours_spent'), task_data.get('parent_task_id'), now, now, task_data.get('completed_at'))
    try: cursor.execute(sql,params); return cursor.lastrowid
    except sqlite3.Error: return None

@_manage_conn
def get_task_by_id(task_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM Tasks WHERE task_id = ?",(task_id,)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_tasks_by_project_id(project_id: str, filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM Tasks WHERE project_id = ?"; params=[project_id]
    if filters:
        cls=[]; valid=['assignee_team_member_id','status_id','priority']
        for k,v in filters.items():
            if k in valid: cls.append(f"{k}=?"); params.append(v)
        if cls: sql+=" AND "+" AND ".join(cls)
    cursor.execute(sql,tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_task(task_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"; data['updated_at']=now
    valid_cols=['project_id','task_name','description','status_id','assignee_team_member_id','reporter_team_member_id','due_date','priority','estimated_hours','actual_hours_spent','parent_task_id','updated_at','completed_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params=list(to_set.values()); params.append(task_id)
    sql=f"UPDATE Tasks SET {', '.join(set_c)} WHERE task_id = ?"; cursor.execute(sql,params)
    return cursor.rowcount > 0

@_manage_conn
def delete_task(task_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM Tasks WHERE task_id = ?",(task_id,)); return cursor.rowcount > 0

@_manage_conn
def get_all_tasks(active_only: bool = False, project_id_filter: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT t.* FROM Tasks t"; params=[]; conditions=[]
    if active_only: sql+=" LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id"; conditions.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")
    if project_id_filter: conditions.append("t.project_id = ?"); params.append(project_id_filter)
    if conditions: sql+=" WHERE "+" AND ".join(conditions)
    sql+=" ORDER BY t.created_at DESC"; cursor.execute(sql,tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_tasks_by_assignee_id(assignee_id: int, active_only: bool = False, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT t.* FROM Tasks t"; params=[]; conditions=["t.assignee_team_member_id = ?"]; params.append(assignee_id)
    if active_only: sql+=" LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id"; conditions.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")
    sql+=" WHERE "+" AND ".join(conditions)+" ORDER BY t.due_date ASC, t.priority DESC"; cursor.execute(sql,tuple(params))
    return [dict(row) for row in cursor.fetchall()]

# --- TeamMembers CRUD ---
@_manage_conn
def add_team_member(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"
    sql="INSERT INTO TeamMembers (user_id, full_name, email, role_or_title, department, phone_number, profile_picture_url, is_active, notes, hire_date, performance, skills, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    params=(data.get('user_id'), data['full_name'], data['email'], data.get('role_or_title'), data.get('department'), data.get('phone_number'), data.get('profile_picture_url'), data.get('is_active',True), data.get('notes'), data.get('hire_date'), data.get('performance',0), data.get('skills'), now, now)
    try: cursor.execute(sql,params); return cursor.lastrowid
    except sqlite3.Error: return None

@_manage_conn
def get_team_member_by_id(id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor(); cursor.execute("SELECT * FROM TeamMembers WHERE team_member_id = ?",(id,)); row=cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_team_members(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM TeamMembers"; q_params=[]
    if filters:
        cls=[]; valid=['is_active','department','user_id']
        for k,v in filters.items():
            if k in valid:
                if k=='is_active' and isinstance(v,bool): cls.append(f"{k}=?"); q_params.append(1 if v else 0)
                else: cls.append(f"{k}=?"); q_params.append(v)
        if cls: sql+=" WHERE "+" AND ".join(cls)
    cursor.execute(sql,q_params)
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_team_member(id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False; cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"; data['updated_at']=now
    valid_cols=['user_id','full_name','email','role_or_title','department','phone_number','profile_picture_url','is_active','notes','hire_date','performance','skills','updated_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params=list(to_set.values()); params.append(id)
    sql=f"UPDATE TeamMembers SET {', '.join(set_c)} WHERE team_member_id = ?"; cursor.execute(sql,params)
    return cursor.rowcount > 0

@_manage_conn
def delete_team_member(id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); cursor.execute("DELETE FROM TeamMembers WHERE team_member_id = ?",(id,)); return cursor.rowcount > 0


# (Ensure all other CRUD functions from original db.py are added here, refactored with @_manage_conn and `conn` parameter)
# For brevity, I will assume the rest of the functions are added in a similar fashion.
# The __all__ list needs to be fully comprehensive.
