import sqlite3
from datetime import datetime
import logging
from .generic_crud import _manage_conn, get_db_connection # get_db_connection might not be needed if only using _manage_conn
from .contacts_crud import (
    add_contact as central_add_contact,
    get_contact_by_id as central_get_contact_by_id,
    update_contact as central_update_contact
    # delete_contact is not directly used for unlinking
)

logger = logging.getLogger(__name__)

# --- CompanyPersonnel CRUD (Existing - Do Not Modify unless directly related to contacts) ---
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
    # New functions for CompanyPersonnelContacts
    "add_personnel_contact",
    "get_contacts_for_personnel",
    "update_personnel_contact_link",
    "get_personnel_contact_link_details",
    "unlink_contact_from_personnel",
    "delete_all_contact_links_for_personnel",
]

# --- CompanyPersonnelContacts Link Table CRUD ---

@_manage_conn
def add_personnel_contact(personnel_id: int, contact_data: dict, conn: sqlite3.Connection = None) -> int | None:
    """
    Adds a contact to the central Contacts table and links it to a company personnel
    in the CompanyPersonnelContacts table.
    contact_data should contain all fields for the main Contacts table (name, email, etc.)
    AND optionally 'is_primary' and 'can_receive_documents' for the link.
    """
    if not contact_data.get('name') and not contact_data.get('displayName'):
        logger.error("Contact name or displayName is required for add_personnel_contact.")
        return None

    central_contact_id = central_add_contact(contact_data, conn=conn)
    if central_contact_id is None:
        logger.error(f"Failed to add contact to central Contacts table for personnel_id {personnel_id}.")
        return None

    is_primary = bool(contact_data.get('is_primary', False))
    can_receive_documents = bool(contact_data.get('can_receive_documents', True))
    now = datetime.utcnow().isoformat()

    sql_link = """
        INSERT INTO CompanyPersonnelContacts (personnel_id, contact_id, is_primary, can_receive_documents, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    params_link = (personnel_id, central_contact_id, is_primary, can_receive_documents, now, now)

    cursor = conn.cursor()
    try:
        cursor.execute(sql_link, params_link)
        new_link_id = cursor.lastrowid
        logger.info(f"Linked central_contact_id {central_contact_id} to personnel_id {personnel_id} with company_personnel_contact_id: {new_link_id}.")
        return new_link_id
    except sqlite3.IntegrityError as e:
        logger.warning(f"Failed to link contact {central_contact_id} to personnel {personnel_id}. Link might already exist. Error: {e}")
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error linking contact to personnel {personnel_id}: {e}")
        return None

@_manage_conn
def get_contacts_for_personnel(personnel_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    """
    Retrieves all contacts linked to a specific company personnel, fetching full
    contact details from the central Contacts table.
    """
    cursor = conn.cursor()
    sql = """
        SELECT c.*, cpc.company_personnel_contact_id, cpc.is_primary, cpc.can_receive_documents,
               cpc.created_at AS link_created_at, cpc.updated_at AS link_updated_at
        FROM Contacts c
        JOIN CompanyPersonnelContacts cpc ON c.contact_id = cpc.contact_id
        WHERE cpc.personnel_id = ?
        ORDER BY c.name, c.displayName
    """
    try:
        cursor.execute(sql, (personnel_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error in get_contacts_for_personnel for personnel_id {personnel_id}: {e}")
        return []

@_manage_conn
def update_personnel_contact_link(company_personnel_contact_id: int, link_data: dict = None, contact_details_data: dict = None, conn: sqlite3.Connection = None) -> bool:
    """
    Updates a personnel-contact link. This can involve updating the central contact details
    and/or the link-specific details in CompanyPersonnelContacts.
    `link_data` is for 'is_primary', 'can_receive_documents'.
    `contact_details_data` is for fields in the main Contacts table.
    """
    if not link_data and not contact_details_data:
        logger.info(f"No data provided for updating company_personnel_contact_id {company_personnel_contact_id}.")
        return False

    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    updated_central = False
    updated_link = False

    # Step 1: Get central_contact_id from CompanyPersonnelContacts
    cursor.execute("SELECT contact_id FROM CompanyPersonnelContacts WHERE company_personnel_contact_id = ?", (company_personnel_contact_id,))
    row = cursor.fetchone()
    if not row:
        logger.error(f"CompanyPersonnelContacts link with ID {company_personnel_contact_id} not found.")
        return False
    central_contact_id = row['contact_id']

    # Step 2: Update central Contacts table if contact_details_data is provided
    if contact_details_data:
        # Ensure 'name' or 'displayName' is handled if that's a constraint of central_update_contact
        # (contacts_crud.update_contact already handles this by checking 'displayName' if 'name' not present)
        if central_update_contact(central_contact_id, contact_details_data, conn=conn):
            logger.info(f"Updated central contact details for contact_id {central_contact_id} linked to company_personnel_contact_id {company_personnel_contact_id}.")
            updated_central = True
        else:
            logger.warning(f"Failed to update central contact details for contact_id {central_contact_id}.")
            # Depending on requirements, one might choose to return False here

    # Step 3: Update CompanyPersonnelContacts link table if link_data is provided
    if link_data:
        link_fields_to_update_sql = []
        link_params_sql = []

        if 'is_primary' in link_data:
            link_fields_to_update_sql.append("is_primary = ?")
            link_params_sql.append(bool(link_data['is_primary']))
        if 'can_receive_documents' in link_data:
            link_fields_to_update_sql.append("can_receive_documents = ?")
            link_params_sql.append(bool(link_data['can_receive_documents']))

        if link_fields_to_update_sql: # If there's something to update
            link_fields_to_update_sql.append("updated_at = ?")
            link_params_sql.append(now)
            link_params_sql.append(company_personnel_contact_id)

            sql_update_link = f"UPDATE CompanyPersonnelContacts SET {', '.join(link_fields_to_update_sql)} WHERE company_personnel_contact_id = ?"
            try:
                cursor.execute(sql_update_link, tuple(link_params_sql))
                if cursor.rowcount > 0:
                    logger.info(f"Updated CompanyPersonnelContacts link details for company_personnel_contact_id {company_personnel_contact_id}.")
                    updated_link = True
            except sqlite3.Error as e:
                logger.error(f"Database error updating CompanyPersonnelContacts link for {company_personnel_contact_id}: {e}")

    return updated_central or updated_link

@_manage_conn
def get_personnel_contact_link_details(company_personnel_contact_id: int, conn: sqlite3.Connection = None) -> dict | None:
    """
    Retrieves a specific personnel-contact link by its ID (company_personnel_contact_id),
    joining with the central Contacts table to get full contact details.
    """
    cursor = conn.cursor()
    sql = """
        SELECT c.*, cpc.company_personnel_contact_id, cpc.personnel_id,
               cpc.is_primary, cpc.can_receive_documents,
               cpc.created_at AS link_created_at, cpc.updated_at AS link_updated_at
        FROM Contacts c
        JOIN CompanyPersonnelContacts cpc ON c.contact_id = cpc.contact_id
        WHERE cpc.company_personnel_contact_id = ?
    """
    try:
        cursor.execute(sql, (company_personnel_contact_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Database error in get_personnel_contact_link_details for ID {company_personnel_contact_id}: {e}")
        return None

@_manage_conn
def unlink_contact_from_personnel(company_personnel_contact_id: int, conn: sqlite3.Connection = None) -> bool:
    """
    Deletes the link between a company personnel and a contact from CompanyPersonnelContacts.
    Does NOT delete the contact from the central Contacts table.
    """
    cursor = conn.cursor()
    sql = "DELETE FROM CompanyPersonnelContacts WHERE company_personnel_contact_id = ?"
    try:
        cursor.execute(sql, (company_personnel_contact_id,))
        if cursor.rowcount > 0:
            logger.info(f"Unlinked contact for company_personnel_contact_id {company_personnel_contact_id}.")
            return True
        else:
            logger.warning(f"No link found to delete for company_personnel_contact_id {company_personnel_contact_id}.")
            return False
    except sqlite3.Error as e:
        logger.error(f"Database error unlinking contact for company_personnel_contact_id {company_personnel_contact_id}: {e}")
        return False

@_manage_conn
def delete_all_contact_links_for_personnel(personnel_id: int, conn: sqlite3.Connection = None) -> bool:
    """
    Deletes all contact links for a specific company personnel from CompanyPersonnelContacts.
    Does NOT delete contacts from the central Contacts table.
    Returns True if the operation was successful (even if no rows were deleted).
    """
    cursor = conn.cursor()
    sql = "DELETE FROM CompanyPersonnelContacts WHERE personnel_id = ?"
    try:
        cursor.execute(sql, (personnel_id,))
        logger.info(f"Attempted deletion of all contact links for personnel_id {personnel_id}. Rows affected: {cursor.rowcount}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error deleting all contact links for personnel_id {personnel_id}: {e}")
        return False
