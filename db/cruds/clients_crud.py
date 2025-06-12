import sqlite3
import uuid
from datetime import datetime
import logging # Added for logging
from .generic_crud import _manage_conn, get_db_connection
# from .status_settings_crud import get_status_setting_by_id # Not directly used by name in these functions
# from .locations_crud import get_country_by_id, get_city_by_id # Not directly used by name in these functions

# --- Clients CRUD ---
@_manage_conn
def add_client(data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor(); new_id=str(uuid.uuid4()); now=datetime.utcnow().isoformat()+"Z"
    sql="""INSERT INTO Clients
             (client_id, client_name, company_name, primary_need_description, project_identifier,
              country_id, city_id, default_base_folder_path, status_id, selected_languages,
              price, notes, category, created_at, updated_at, created_by_user_id)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    params=(new_id,data.get('client_name'),data.get('company_name'),data.get('primary_need_description'),
            data.get('project_identifier','N/A'),data.get('country_id'),data.get('city_id'),
            data.get('default_base_folder_path'),data.get('status_id'),
            data.get('selected_languages'),data.get('price',0),data.get('notes'),
            data.get('category'),now,now,data.get('created_by_user_id'))
    try:
        cursor.execute(sql,params)
        return new_id
    except sqlite3.Error as e:
        logging.error(f"Failed to add client '{data.get('client_name')}': {e}")
        return None

@_manage_conn
def get_client_by_id(id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor()
    try:
        cursor.execute("SELECT * FROM Clients WHERE client_id = ?",(id,))
        row=cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get client by ID '{id}': {e}")
        return None

@_manage_conn
def get_all_clients(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM Clients"; q_params=[]
    if filters:
        cls=[]; valid_filters=['client_name','company_name','country_id','city_id','status_id','category','created_by_user_id']
        for k,v in filters.items():
            if k in valid_filters:
                # Handle potential SQL injection by ensuring k is a valid column name (already done by valid_filters)
                # and value is parameterized.
                if isinstance(v, str) and k in ['client_name', 'company_name', 'category']:
                    cls.append(f"{k} LIKE ?") # Use LIKE for string matching
                    q_params.append(f"%{v}%")
                else:
                    cls.append(f"{k} = ?")
                    q_params.append(v)
        if cls: sql+=" WHERE "+" AND ".join(cls)
    sql += " ORDER BY client_name" # Added default ordering
    try:
        cursor.execute(sql,q_params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get all clients with filters '{filters}': {e}")
        return []

@_manage_conn
def update_client(client_id: str, client_data: dict, conn: sqlite3.Connection = None) -> bool:
    if not client_data: return False
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"; client_data['updated_at'] = now
    valid_cols = ['client_name', 'company_name', 'primary_need_description', 'project_identifier',
                  'country_id', 'city_id', 'default_base_folder_path', 'status_id',
                  'selected_languages', 'price', 'notes', 'category', 'updated_at',
                  'created_by_user_id']
    data_to_set = {k:v for k,v in client_data.items() if k in valid_cols}
    if not data_to_set : return False

    set_clauses = [f"{key} = ?" for key in data_to_set.keys()]
    params = list(data_to_set.values()); params.append(client_id)
    sql = f"UPDATE Clients SET {', '.join(set_clauses)} WHERE client_id = ?"
    try:
        cursor.execute(sql, params)
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to update client {client_id}: {e}")
        return False

@_manage_conn
def delete_client(client_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Clients WHERE client_id = ?", (client_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to delete client {client_id}: {e}")
        return False

@_manage_conn
def get_all_clients_with_details(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    query = """
    SELECT c.client_id, c.client_name, c.company_name, c.primary_need_description,
           c.project_identifier, c.default_base_folder_path, c.selected_languages,
           c.price, c.notes, c.created_at, c.category, c.status_id, c.country_id, c.city_id,
           co.country_name AS country, ci.city_name AS city,
           s.status_name AS status, s.color_hex AS status_color, s.icon_name AS status_icon_name
    FROM Clients c
    LEFT JOIN Countries co ON c.country_id = co.country_id
    LEFT JOIN Cities ci ON c.city_id = ci.city_id
    LEFT JOIN StatusSettings s ON c.status_id = s.status_id AND s.status_type = 'Client'
    ORDER BY c.client_name;
    """
    try:
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get all clients with details: {e}")
        return []

@_manage_conn
def get_active_clients_count(conn: sqlite3.Connection = None) -> int:
    cursor = conn.cursor()
    # Assumes StatusSettings table has is_archival_status (boolean or 0/1)
    sql = """SELECT COUNT(c.client_id) as active_count
             FROM Clients c
             LEFT JOIN StatusSettings ss ON c.status_id = ss.status_id
             WHERE (ss.is_archival_status IS NOT TRUE AND ss.is_archival_status != 1) OR c.status_id IS NULL"""
    try:
        cursor.execute(sql)
        row = cursor.fetchone()
        return row['active_count'] if row else 0
    except sqlite3.Error as e:
        logging.error(f"Failed to get active clients count: {e}")
        return 0

@_manage_conn
def get_client_counts_by_country(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = """SELECT co.country_name, COUNT(cl.client_id) as client_count
             FROM Clients cl
             JOIN Countries co ON cl.country_id = co.country_id
             GROUP BY co.country_name
             HAVING COUNT(cl.client_id) > 0
             ORDER BY client_count DESC"""
    try:
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get client counts by country: {e}")
        return []

@_manage_conn
def get_client_segmentation_by_city(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = """SELECT co.country_name, ci.city_name, COUNT(cl.client_id) as client_count
             FROM Clients cl
             JOIN Cities ci ON cl.city_id = ci.city_id
             JOIN Countries co ON ci.country_id = co.country_id
             GROUP BY co.country_name, ci.city_name
             HAVING COUNT(cl.client_id) > 0
             ORDER BY co.country_name, client_count DESC, ci.city_name"""
    try:
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get client segmentation by city: {e}")
        return []

@_manage_conn
def get_client_segmentation_by_status(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = """SELECT ss.status_name, COUNT(cl.client_id) as client_count
             FROM Clients cl
             JOIN StatusSettings ss ON cl.status_id = ss.status_id
             WHERE ss.status_type = 'Client' -- Ensure only client statuses
             GROUP BY ss.status_name
             HAVING COUNT(cl.client_id) > 0
             ORDER BY client_count DESC, ss.status_name"""
    try:
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get client segmentation by status: {e}")
        return []

@_manage_conn
def get_client_segmentation_by_category(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = """SELECT cl.category, COUNT(cl.client_id) as client_count
             FROM Clients cl
             WHERE cl.category IS NOT NULL AND cl.category != ''
             GROUP BY cl.category
             HAVING COUNT(cl.client_id) > 0
             ORDER BY client_count DESC, cl.category"""
    try:
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get client segmentation by category: {e}")
        return []

@_manage_conn
def get_clients_by_archival_status(is_archived: bool, include_null_status_for_active: bool = True, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); params = []
    try:
        cursor.execute("SELECT status_id FROM StatusSettings WHERE status_type = 'Client' AND (is_archival_status = TRUE OR is_archival_status = 1)")
        archival_ids_tuples = cursor.fetchall()
        archival_ids = [row['status_id'] for row in archival_ids_tuples]

        base_query = """SELECT c.*, co.country_name AS country, ci.city_name AS city,
                        s.status_name AS status, s.color_hex AS status_color, s.icon_name AS status_icon_name
                        FROM Clients c
                        LEFT JOIN Countries co ON c.country_id = co.country_id
                        LEFT JOIN Cities ci ON c.city_id = ci.city_id
                        LEFT JOIN StatusSettings s ON c.status_id = s.status_id AND s.status_type = 'Client'"""
        conditions = []

        if not archival_ids:
            if is_archived: return []
            # else no specific status condition if no archival statuses are defined
        else:
            placeholders = ','.join('?' for _ in archival_ids)
            if is_archived:
                conditions.append(f"c.status_id IN ({placeholders})")
                params.extend(archival_ids)
            else:
                not_in_cond = f"c.status_id NOT IN ({placeholders})"
                if include_null_status_for_active:
                    conditions.append(f"({not_in_cond} OR c.status_id IS NULL)")
                else:
                    conditions.append(not_in_cond)
                params.extend(archival_ids)

        sql = f"{base_query} {'WHERE ' + ' AND '.join(conditions) if conditions else ''} ORDER BY c.client_name;"
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get clients by archival status (is_archived={is_archived}): {e}")
        return []

@_manage_conn
def get_active_clients_per_country(conn: sqlite3.Connection = None) -> dict:
    cursor = conn.cursor()
    clients_by_country_map = {}
    try:
        cursor.execute("SELECT status_id FROM StatusSettings WHERE (is_archival_status = TRUE OR is_archival_status = 1) AND status_type = 'Client'")
        archival_status_ids_tuples = cursor.fetchall()
        archival_status_ids = [row['status_id'] for row in archival_status_ids_tuples]

        query_parts = [
            "SELECT",
            "    co.country_name,",
            "    cl.client_id,",
            "    cl.client_name",
            "FROM Clients cl",
            "JOIN Countries co ON cl.country_id = co.country_id"
        ]
        params_for_query = []

        if archival_status_ids:
            placeholders = ','.join('?' for _ in archival_status_ids)
            query_parts.append(f"WHERE (cl.status_id IS NULL OR cl.status_id NOT IN ({placeholders}))")
            params_for_query.extend(archival_status_ids)
        # If no archival_status_ids, all clients are considered active (no WHERE clause needed for status)

        query_parts.append("ORDER BY co.country_name, cl.client_name;")
        query = "\n".join(query_parts)

        cursor.execute(query, params_for_query)

        for row in cursor.fetchall():
            country = row['country_name']
            client_detail = {'client_id': row['client_id'], 'client_name': row['client_name']}
            if country not in clients_by_country_map:
                clients_by_country_map[country] = []
            clients_by_country_map[country].append(client_detail)
    except sqlite3.Error as e:
        logging.error(f"Failed to get active clients per country: {e}")
    return clients_by_country_map

# --- ClientNotes CRUD ---
@_manage_conn
def add_client_note(client_id: str, note_text: str, user_id: str = None, conn: sqlite3.Connection = None) -> int | None:
    cursor = conn.cursor()
    sql = "INSERT INTO ClientNotes (client_id, note_text, user_id, timestamp) VALUES (?, ?, ?, ?)" # Added timestamp
    now = datetime.utcnow().isoformat() + "Z"
    try:
        cursor.execute(sql, (client_id, note_text, user_id, now))
        return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error(f"Failed to add client note for client {client_id}: {e}")
        return None

@_manage_conn
def get_client_notes(client_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT note_id, client_id, timestamp, note_text, user_id FROM ClientNotes WHERE client_id = ? ORDER BY timestamp DESC" # Order by DESC
    try:
        cursor.execute(sql, (client_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get client notes for client {client_id}: {e}")
        return []
