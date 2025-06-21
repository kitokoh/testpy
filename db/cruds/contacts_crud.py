import sqlite3
import uuid # Not directly used in current selection but good for consistency
from datetime import datetime # For add_contact
import logging # For stub add_contact_list and others
from .generic_crud import _manage_conn, get_db_connection

# --- Contacts CRUD ---
@_manage_conn
def get_contacts_for_client(client_id: str, limit: int = None, offset: int = 0, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor()
    sql = """SELECT c.*, cc.is_primary_for_client, cc.can_receive_documents
             FROM Contacts c JOIN ClientContacts cc ON c.contact_id = cc.contact_id WHERE cc.client_id = ?"""
    params = [client_id]
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    try:
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error getting contacts for client {client_id} with limit {limit} and offset {offset}: {e}")
        return []

@_manage_conn
def add_contact(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"
    name=data.get('displayName', data.get('name')) # Use displayName if name is not present
    sql="""INSERT INTO Contacts
             (name, email, phone, position, company_name, notes,
              givenName, familyName, displayName, phone_type, email_type,
              address_formattedValue, address_streetAddress, address_city,
              address_region, address_postalCode, address_country,
              organization_name, organization_title, birthday_date,
              created_at, updated_at)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    params=(name, data.get('email'), data.get('phone'), data.get('position'),
            data.get('company_name'), data.get('notes'), data.get('givenName'),
            data.get('familyName'), data.get('displayName'), data.get('phone_type'),
            data.get('email_type'), data.get('address_formattedValue'),
            data.get('address_streetAddress'), data.get('address_city'),
            data.get('address_region'), data.get('address_postalCode'),
            data.get('address_country'), data.get('organization_name'),
            data.get('organization_title'), data.get('birthday_date'),
            now, now)
    try:
        cursor.execute(sql,params)
        return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error(f"Error adding contact with data {params}: {type(e).__name__} - {e}", exc_info=True)
        return None

@_manage_conn
def get_contact_by_id(id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor()
    try:
        cursor.execute("SELECT * FROM Contacts WHERE contact_id = ?",(id,))
        row=cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Error getting contact by ID {id}: {e}")
        return None

@_manage_conn
def get_contact_by_email(email: str, conn: sqlite3.Connection = None) -> dict | None:
    if not email: return None
    cursor=conn.cursor()
    try:
        cursor.execute("SELECT * FROM Contacts WHERE email = ?",(email,))
        row=cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Error getting contact by email '{email}': {e}")
        return None

@_manage_conn
def get_all_contacts(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM Contacts"; params=[]; clauses=[]
    if filters:
        if 'company_name' in filters:
            clauses.append("company_name LIKE ?") # Use LIKE for partial match
            params.append(f"%{filters['company_name']}%")
        if 'name' in filters:
            clauses.append("(name LIKE ? OR displayName LIKE ?)")
            params.extend([f"%{filters['name']}%", f"%{filters['name']}%"])
        if 'email' in filters: # Added email filter
            clauses.append("email LIKE ?")
            params.append(f"%{filters['email']}%")
        if clauses: sql+=" WHERE "+" AND ".join(clauses)
    sql += " ORDER BY name, displayName" # Default order
    try:
        cursor.execute(sql,params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error getting all contacts with filters '{filters}': {e}")
        return []

@_manage_conn
def update_contact(id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False
    cursor=conn.cursor(); now=datetime.utcnow().isoformat()+"Z"; data['updated_at']=now
    if 'displayName' in data and 'name' not in data: data['name'] = data['displayName']

    valid_cols=['name','email','phone','position','company_name','notes','givenName',
                  'familyName','displayName','phone_type','email_type','address_formattedValue',
                  'address_streetAddress','address_city','address_region','address_postalCode',
                  'address_country','organization_name','organization_title','birthday_date','updated_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False

    set_c=[f"{k}=?" for k in to_set.keys()]; params_list=list(to_set.values()); params_list.append(id)
    sql=f"UPDATE Contacts SET {', '.join(set_c)} WHERE contact_id = ?"
    try:
        cursor.execute(sql,params_list)
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Error updating contact {id}: {e}")
        return False

@_manage_conn
def delete_contact(id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor()
    try:
        cursor.execute("DELETE FROM Contacts WHERE contact_id = ?",(id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Error deleting contact {id}: {e}")
        return False

# --- ContactLists Stubs ---
@_manage_conn
def add_contact_list(data: dict, conn: sqlite3.Connection = None) -> int | None:
    logging.warning(f"Called stub function add_contact_list with data: {data}. Full implementation is missing.")
    # Example: return cursor.lastrowid
    return None

@_manage_conn
def add_contact_to_list(data: dict, conn: sqlite3.Connection = None) -> object | None: # Changed to object as per original
    logging.warning(f"Called stub function add_contact_to_list with data: {data}. Full implementation is missing.")
    return None

@_manage_conn
def delete_contact_list(data: dict, conn: sqlite3.Connection = None) -> object | None: # Changed to object
    logging.warning(f"Called stub function delete_contact_list with data: {data}. Full implementation is missing.")
    return None

@_manage_conn
def get_all_contact_lists(data: dict = None, conn: sqlite3.Connection = None) -> object | None: # Changed to object
    logging.warning(f"Called stub function get_all_contact_lists with data: {data}. Full implementation is missing.")
    return None

@_manage_conn
def get_contact_list_by_id(data: dict, conn: sqlite3.Connection = None) -> object | None: # Changed to object
    logging.warning(f"Called stub function get_contact_list_by_id with data: {data}. Full implementation is missing.")
    return None

@_manage_conn
def get_contacts_in_list(data: dict, conn: sqlite3.Connection = None) -> object | None: # Changed to object
    logging.warning(f"Called stub function get_contacts_in_list with data: {data}. Full implementation is missing.")
    return None

@_manage_conn
def remove_contact_from_list(data: dict, conn: sqlite3.Connection = None) -> object | None: # Changed to object
    logging.warning(f"Called stub function remove_contact_from_list with data: {data}. Full implementation is missing.")
    return None

# --- ClientContacts CRUD ---
@_manage_conn
def link_contact_to_client(client_id: str, contact_id: int, is_primary: bool = False, can_receive_documents: bool = True, conn: sqlite3.Connection = None) -> int | None:
    logging.info(f"link_contact_to_client called with client_id: {client_id}, contact_id: {contact_id}") # New log
    cursor=conn.cursor()
    sql="INSERT INTO ClientContacts (client_id, contact_id, is_primary_for_client, can_receive_documents) VALUES (?,?,?,?)"
    try:
        cursor.execute(sql,(client_id,contact_id,is_primary,can_receive_documents))
        return cursor.lastrowid
    except sqlite3.Error as e: # Handles UNIQUE constraint
        logging.error(f"Error linking contact {contact_id} to client {client_id}. Error type: {type(e)}, Message: {e}") # Enhanced log
        return None

@_manage_conn
def unlink_contact_from_client(client_id: str, contact_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor()
    sql="DELETE FROM ClientContacts WHERE client_id = ? AND contact_id = ?"
    try:
        cursor.execute(sql,(client_id,contact_id))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Error unlinking contact {contact_id} from client {client_id}: {e}")
        return False

@_manage_conn
def get_contacts_for_client_count(client_id: str, conn: sqlite3.Connection = None) -> int:
    cursor=conn.cursor()
    try:
        cursor.execute("SELECT COUNT(contact_id) FROM ClientContacts WHERE client_id = ?",(client_id,))
        row=cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.Error as e:
        logging.error(f"Error getting contact count for client {client_id}: {e}")
        return 0

@_manage_conn
def get_clients_for_contact(contact_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor()
    sql="""SELECT cl.*, cc.is_primary_for_client, cc.can_receive_documents, cc.client_contact_id
             FROM Clients cl
             JOIN ClientContacts cc ON cl.client_id = cc.client_id
             WHERE cc.contact_id = ?"""
    try:
        cursor.execute(sql,(contact_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error getting clients for contact {contact_id}: {e}")
        return []

@_manage_conn
def get_specific_client_contact_link_details(client_id: str, contact_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor()
    sql="SELECT client_contact_id, is_primary_for_client, can_receive_documents FROM ClientContacts WHERE client_id = ? AND contact_id = ?"
    try:
        cursor.execute(sql,(client_id,contact_id))
        row=cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Error getting specific client-contact link for client {client_id}, contact {contact_id}: {e}")
        return None

@_manage_conn
def update_client_contact_link(client_contact_id: int, details: dict, conn: sqlite3.Connection = None) -> bool:
    if not details or not any(k in details for k in ['is_primary_for_client','can_receive_documents']):
        logging.warning("No valid details provided for update_client_contact_link.")
        return False
    cursor=conn.cursor(); set_c=[]; params=[]
    if 'is_primary_for_client' in details:
        set_c.append("is_primary_for_client=?")
        params.append(1 if details['is_primary_for_client'] else 0) # Ensure boolean is 0/1
    if 'can_receive_documents' in details:
        set_c.append("can_receive_documents=?")
        params.append(1 if details['can_receive_documents'] else 0) # Ensure boolean is 0/1

    if not set_c: return False # Should not happen based on initial check

    params.append(client_contact_id)
    sql=f"UPDATE ClientContacts SET {', '.join(set_c)} WHERE client_contact_id = ?"
    try:
        cursor.execute(sql,params)
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Error updating client_contact_link {client_contact_id}: {e}")
        return False
