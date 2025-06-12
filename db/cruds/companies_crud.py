import sqlite3
import uuid
from datetime import datetime
from .generic_crud import _manage_conn, get_db_connection

# --- Companies CRUD ---
@_manage_conn
def add_company(company_data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor(); new_id=str(uuid.uuid4()); now=datetime.utcnow().isoformat()+"Z"
    sql="INSERT INTO Companies (company_id, company_name, address, payment_info, logo_path, other_info, is_default, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)"
    params=(new_id, company_data['company_name'], company_data.get('address'), company_data.get('payment_info'), company_data.get('logo_path'), company_data.get('other_info'), company_data.get('is_default',False), now, now)
    try:
        cursor.execute(sql,params)
        return new_id
    except sqlite3.Error: # More specific error handling
        # logging.error(f"Failed to add company: {e}") # Consider logging
        return None

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
    sql=f"UPDATE Companies SET {', '.join(set_c)} WHERE company_id = ?";
    try:
        cursor.execute(sql,params)
        return cursor.rowcount > 0
    except sqlite3.Error:
        # logging.error(f"Failed to update company {company_id}: {e}") # Consider logging
        return False

@_manage_conn
def delete_company(company_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor()
    try:
        cursor.execute("DELETE FROM Companies WHERE company_id = ?", (company_id,))
        return cursor.rowcount > 0
    except sqlite3.Error:
        # logging.error(f"Failed to delete company {company_id}: {e}") # Consider logging
        return False

@_manage_conn
def set_default_company(company_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor()
    try:
        # Transaction: Ensure this is atomic if _manage_conn doesn't already guarantee it
        # For this decorator, commit is called at the end if it's a write operation.
        # Since there are two UPDATE statements, they should ideally be in one transaction.
        # The _manage_conn will commit after the whole function if func name implies write.
        cursor.execute("UPDATE Companies SET is_default = FALSE WHERE is_default = TRUE AND company_id != ?", (company_id,))
        cursor.execute("UPDATE Companies SET is_default = TRUE WHERE company_id = ?", (company_id,))
        return True # Assume success if no exceptions
    except sqlite3.Error:
        # logging.error(f"Failed to set default company {company_id}: {e}") # Consider logging
        return False

@_manage_conn
def get_default_company(conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor();
    try:
        cursor.execute("SELECT * FROM Companies WHERE is_default = TRUE");
        row=cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error:
        # logging.error(f"Failed to get default company: {e}") # Consider logging
        return None
