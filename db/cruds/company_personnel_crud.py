import sqlite3
from datetime import datetime
from .generic_crud import _manage_conn, get_db_connection

# --- CompanyPersonnel CRUD ---
@_manage_conn
def add_company_personnel(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"
    sql="INSERT INTO CompanyPersonnel (company_id, name, role, phone, email, created_at) VALUES (?,?,?,?,?,?)"
    params=(data['company_id'], data['name'], data['role'], data.get('phone'), data.get('email'), now)
    try:
        cursor.execute(sql,params)
        return cursor.lastrowid
    except sqlite3.Error:
        # logging.error(f"Failed to add company personnel: {e}") # Consider logging
        return None

@_manage_conn
def get_personnel_for_company(company_id: str, role: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM CompanyPersonnel WHERE company_id = ?"; params=[company_id]
    if role: sql+=" AND role = ?"; params.append(role)
    sql+=" ORDER BY name";
    try:
        cursor.execute(sql,params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error:
        # logging.error(f"Failed to get personnel for company {company_id}: {e}") # Consider logging
        return []

@_manage_conn
def update_company_personnel(personnel_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor(); valid_cols=['name','role','phone','email']; to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False
    set_c=[f"{k}=?" for k in to_set.keys()]; params=list(to_set.values()); params.append(personnel_id)
    sql=f"UPDATE CompanyPersonnel SET {', '.join(set_c)} WHERE personnel_id = ?";
    try:
        cursor.execute(sql,params)
        return cursor.rowcount > 0
    except sqlite3.Error:
        # logging.error(f"Failed to update company personnel {personnel_id}: {e}") # Consider logging
        return False

@_manage_conn
def delete_company_personnel(personnel_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor()
    try:
        cursor.execute("DELETE FROM CompanyPersonnel WHERE personnel_id = ?", (personnel_id,))
        return cursor.rowcount > 0
    except sqlite3.Error:
        # logging.error(f"Failed to delete company personnel {personnel_id}: {e}") # Consider logging
        return False

__all__ = [
    "add_company_personnel",
    "get_personnel_for_company",
    "update_company_personnel",
    "delete_company_personnel",
]
