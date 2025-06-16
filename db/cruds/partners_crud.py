import sqlite3
import uuid
from datetime import datetime
import logging
from .generic_crud import get_db_connection, _manage_conn
from .contacts_crud import (
    add_contact as central_add_contact,
    get_contact_by_id as central_get_contact_by_id,
    update_contact as central_update_contact,
    delete_contact as central_delete_contact # Not used in this subtask as per instructions
)

logger = logging.getLogger(__name__)

# --- PartnerCategories CRUD Functions ---
@_manage_conn
def add_partner_category(category_data_or_name: str | dict, description: str = None, conn: sqlite3.Connection = None, **kwargs) -> int | None:
    """Adds a new partner category. Can accept name directly or a dict."""
    cursor = conn.cursor()
    name = None
    desc_val = description

    if isinstance(category_data_or_name, dict):
        name = category_data_or_name.get('category_name')
        desc_val = category_data_or_name.get('description', description) # Dict's description overrides arg
    else: # Is a string
        name = category_data_or_name

    if not name:
        logger.error("Category name is required for add_partner_category.")
        return None

    # Use category_data_or_name directly if it's a dict for other potential fields (none currently)
    created_at = datetime.utcnow().isoformat()
    updated_at = created_at

    sql = "INSERT INTO PartnerCategories (category_name, description, created_at, updated_at) VALUES (?, ?, ?, ?)"
    try:
        cursor.execute(sql, (name, desc_val, created_at, updated_at))
        logger.info(f"Partner category '{name}' added with ID: {cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logger.warning(f"Partner category '{name}' already exists.")
        existing_category = get_partner_category_by_name(name, conn=conn)
        return existing_category['partner_category_id'] if existing_category else None
    except sqlite3.Error as e:
        logger.error(f"Database error in add_partner_category for '{name}': {e}")
        return None

@_manage_conn
def get_partner_category_by_id(category_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PartnerCategories WHERE partner_category_id = ?", (category_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_partner_category_by_name(name: str, conn: sqlite3.Connection = None, **kwargs) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PartnerCategories WHERE category_name = ?", (name,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_partner_categories(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PartnerCategories ORDER BY category_name")
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_partner_category(category_id: int, category_data_or_name: str | dict, description: str = None, conn: sqlite3.Connection = None) -> bool:
    """Updates a partner category. Can accept name directly or a dict."""
    cursor = conn.cursor()
    name = None
    desc_val = description

    if isinstance(category_data_or_name, dict):
        name = category_data_or_name.get('category_name')
        desc_val = category_data_or_name.get('description', description)
    else: # is string
        name = category_data_or_name

    if name is None and desc_val is None:
        logger.warning(f"Update partner category {category_id}: No data provided.")
        return False

    fields_to_update = []
    params = []

    if name is not None:
        fields_to_update.append("category_name = ?")
        params.append(name)
    if desc_val is not None:
        fields_to_update.append("description = ?")
        params.append(desc_val)

    if not fields_to_update: return False

    params.append(datetime.utcnow().isoformat()) # updated_at
    fields_to_update.append("updated_at = ?")
    params.append(category_id)

    sql = f"UPDATE PartnerCategories SET {', '.join(fields_to_update)} WHERE partner_category_id = ?"
    try:
        cursor.execute(sql, tuple(params))
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        logger.warning(f"Failed to update partner category {category_id} due to name conflict with '{name}'.")
        return False
    except sqlite3.Error as e:
        logger.error(f"Database error in update_partner_category for {category_id}: {e}")
        return False

@_manage_conn
def delete_partner_category(category_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM PartnerCategories WHERE partner_category_id = ?", (category_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error deleting partner category {category_id}: {e}")
        return False

@_manage_conn
def get_or_add_partner_category(category_name: str, description: str = None, conn: sqlite3.Connection = None) -> int | None:
    category = get_partner_category_by_name(category_name, conn=conn)
    if category:
        return category['partner_category_id']
    else:
        return add_partner_category(category_name, description, conn=conn)

# --- Partners CRUD ---
@_manage_conn
def add_partner(partner_data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor = conn.cursor()
    new_partner_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    required_fields = ['partner_name']
    for field in required_fields:
        if not partner_data.get(field):
            logger.error(f"{field} is required to add a partner.")
            return None

    sql = """
        INSERT INTO Partners (partner_id, partner_name, partner_category_id, contact_person_name, email,
                              phone, address, website_url, services_offered, collaboration_start_date,
                              status, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        new_partner_id, partner_data['partner_name'], partner_data.get('partner_category_id'),
        partner_data.get('contact_person_name'), partner_data.get('email'), partner_data.get('phone'),
        partner_data.get('address'), partner_data.get('website_url'), partner_data.get('services_offered'),
        partner_data.get('collaboration_start_date'), partner_data.get('status', 'Active'),
        partner_data.get('notes'), now, now
    )
    try:
        cursor.execute(sql, params)
        return new_partner_id
    except sqlite3.IntegrityError as e:
        logger.warning(f"Failed to add partner, possibly due to duplicate email: {partner_data.get('email')}. Error: {e}")
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error in add_partner: {e}")
        return None

@_manage_conn
def get_partner_by_id(partner_id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Partners WHERE partner_id = ?", (partner_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_partner_by_email(email: str, conn: sqlite3.Connection = None) -> dict | None:
    if not email: return None
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Partners WHERE email = ?", (email,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_partners(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT p.*, pc.category_name as partner_category_name FROM Partners p LEFT JOIN PartnerCategories pc ON p.partner_category_id = pc.partner_category_id"
    query_params = []
    conditions = []

    if filters:
        if filters.get('name'):
            conditions.append("p.partner_name LIKE ?")
            query_params.append(f"%{filters['name']}%")
        if filters.get('partner_category_id'):
            conditions.append("p.partner_category_id = ?")
            query_params.append(filters['partner_category_id'])
        if filters.get('status'):
            conditions.append("p.status = ?")
            query_params.append(filters['status'])
        if filters.get('email'):
            conditions.append("p.email LIKE ?") # Changed to LIKE for partial match
            query_params.append(f"%{filters['email']}%")
        # Add other filters as needed

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY p.partner_name"
    cursor.execute(sql, tuple(query_params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_partner(partner_id: str, partner_data: dict, conn: sqlite3.Connection = None) -> bool:
    if not partner_data: return False
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    valid_columns = ['partner_name', 'partner_category_id', 'contact_person_name', 'email', 'phone',
                     'address', 'website_url', 'services_offered', 'collaboration_start_date',
                     'status', 'notes']

    fields_to_update = {k: v for k, v in partner_data.items() if k in valid_columns}
    if not fields_to_update:
        logger.info(f"No valid fields to update for partner {partner_id}.")
        return False # Or True, if just touching updated_at is fine

    fields_to_update['updated_at'] = now

    set_clauses = [f"{col} = ?" for col in fields_to_update.keys()]
    params = list(fields_to_update.values())
    params.append(partner_id)

    sql = f"UPDATE Partners SET {', '.join(set_clauses)} WHERE partner_id = ?"
    try:
        cursor.execute(sql, tuple(params))
        return cursor.rowcount > 0
    except sqlite3.IntegrityError as e:
        logger.warning(f"Failed to update partner {partner_id} due to integrity constraint. Error: {e}")
        return False
    except sqlite3.Error as e:
        logger.error(f"Database error in update_partner for {partner_id}: {e}")
        return False

@_manage_conn
def delete_partner(partner_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Partners WHERE partner_id = ?", (partner_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error deleting partner {partner_id}: {e}")
        return False

@_manage_conn
def get_partners_by_category_id(category_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    return get_all_partners(filters={'partner_category_id': category_id}, conn=conn)

# --- PartnerContacts CRUD ---
@_manage_conn
def add_partner_contact(partner_id: str, contact_data: dict, conn: sqlite3.Connection = None) -> int | None:
    """
    Adds a contact to the central Contacts table and links it to a partner
    in the PartnerContacts table.
    """
    # Step 1: Extract data for central Contacts table
    # Ensure 'name' or 'displayName' is present for central_add_contact
    if not contact_data.get('name') and not contact_data.get('displayName'):
        logger.error("Contact name or displayName is required.")
        return None

    # displayName is preferred by central_add_contact if 'name' is not also present
    # We can pass all of contact_data, central_add_contact will pick what it needs.
    central_contact_id = central_add_contact(contact_data, conn=conn)

    if central_contact_id is None:
        logger.error(f"Failed to add contact to central Contacts table for partner {partner_id}.")
        return None

    # Step 2: Extract data for PartnerContacts link table
    is_primary = bool(contact_data.get('is_primary', False))
    can_receive_documents = bool(contact_data.get('can_receive_documents', True))
    now = datetime.utcnow().isoformat()

    sql_link = """
        INSERT INTO PartnerContacts (partner_id, contact_id, is_primary, can_receive_documents, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    params_link = (
        partner_id,
        central_contact_id,
        is_primary,
        can_receive_documents,
        now,
        now
    )

    cursor = conn.cursor()
    try:
        cursor.execute(sql_link, params_link)
        logger.info(f"Linked contact {central_contact_id} to partner {partner_id} with PartnerContacts ID: {cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        # This might happen if the (partner_id, contact_id) pair already exists
        logger.warning(f"Failed to link contact {central_contact_id} to partner {partner_id}. Link might already exist. Error: {e}")
        # Check if it exists and return its ID if so? Or just return None. For now, None.
        # To get existing:
        # cursor.execute("SELECT partner_contact_id FROM PartnerContacts WHERE partner_id = ? AND contact_id = ?", (partner_id, central_contact_id))
        # existing_row = cursor.fetchone()
        # if existing_row: return existing_row['partner_contact_id']
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error linking contact to partner {partner_id}: {e}")
        # Potentially roll back the central_add_contact? Complex, for now, we assume it's fine or handled by caller.
        # Consider that central_add_contact might also have its own error handling/logging.
        return None

@_manage_conn
def get_partner_contact_by_id(partner_contact_id: int, conn: sqlite3.Connection = None) -> dict | None:
    """
    Retrieves a specific partner contact by the PartnerContacts link ID,
    joining with the central Contacts table.
    """
    cursor = conn.cursor()
    sql = """
        SELECT c.*, pc.partner_contact_id, pc.partner_id, pc.is_primary, pc.can_receive_documents,
               pc.created_at AS link_created_at, pc.updated_at AS link_updated_at
        FROM Contacts c
        JOIN PartnerContacts pc ON c.contact_id = pc.contact_id
        WHERE pc.partner_contact_id = ?
    """
    cursor.execute(sql, (partner_contact_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_contacts_for_partner(partner_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    """
    Retrieves all contacts linked to a specific partner, fetching full contact details
    from the central Contacts table.
    """
    cursor = conn.cursor()
    sql = """
        SELECT c.*, pc.partner_contact_id, pc.is_primary, pc.can_receive_documents,
               pc.created_at AS link_created_at, pc.updated_at AS link_updated_at
        FROM Contacts c
        JOIN PartnerContacts pc ON c.contact_id = pc.contact_id
        WHERE pc.partner_id = ?
        ORDER BY c.name, c.displayName
    """
    try:
        cursor.execute(sql, (partner_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error in get_contacts_for_partner for partner {partner_id}: {e}")
        return []

@_manage_conn
def update_partner_contact(partner_contact_id: int, contact_data: dict, conn: sqlite3.Connection = None) -> bool:
    """
    Updates a partner contact. This can involve updating the central contact details
    and/or the link-specific details in PartnerContacts.
    """
    if not contact_data:
        logger.info(f"No data provided for updating partner_contact_id {partner_contact_id}.")
        return False

    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    updated_central = False
    updated_link = False

    # Step 1: Get central_contact_id from PartnerContacts
    cursor.execute("SELECT contact_id FROM PartnerContacts WHERE partner_contact_id = ?", (partner_contact_id,))
    link_row = cursor.fetchone()
    if not link_row:
        logger.error(f"PartnerContacts link with ID {partner_contact_id} not found.")
        return False
    central_contact_id = link_row['contact_id']

    # Step 2: Update central Contacts table if relevant fields are present
    # Define fields that belong to the central Contacts table (subset of what contacts_crud.update_contact handles)
    central_contact_fields = [
        'name', 'email', 'phone', 'position', 'company_name', 'notes', 'givenName',
        'familyName', 'displayName', 'phone_type', 'email_type', 'address_formattedValue',
        'address_streetAddress', 'address_city', 'address_region', 'address_postalCode',
        'address_country', 'organization_name', 'organization_title', 'birthday_date'
    ]
    central_data_to_update = {k: v for k, v in contact_data.items() if k in central_contact_fields}

    if central_data_to_update:
        if central_update_contact(central_contact_id, central_data_to_update, conn=conn):
            logger.info(f"Updated central contact details for contact_id {central_contact_id} linked to partner_contact_id {partner_contact_id}.")
            updated_central = True
        else:
            # Log error or warning if central update fails, but proceed to link update if any
            logger.warning(f"Failed to update central contact details for contact_id {central_contact_id}.")
            # Depending on requirements, one might choose to return False here if central update is critical

    # Step 3: Update PartnerContacts link table if relevant fields are present
    link_fields_to_update_sql = []
    link_params_sql = []

    if 'is_primary' in contact_data:
        link_fields_to_update_sql.append("is_primary = ?")
        link_params_sql.append(bool(contact_data['is_primary']))
    if 'can_receive_documents' in contact_data:
        link_fields_to_update_sql.append("can_receive_documents = ?")
        link_params_sql.append(bool(contact_data['can_receive_documents']))

    if link_fields_to_update_sql:
        link_fields_to_update_sql.append("updated_at = ?")
        link_params_sql.append(now)
        link_params_sql.append(partner_contact_id)

        sql_update_link = f"UPDATE PartnerContacts SET {', '.join(link_fields_to_update_sql)} WHERE partner_contact_id = ?"
        try:
            cursor.execute(sql_update_link, tuple(link_params_sql))
            if cursor.rowcount > 0:
                logger.info(f"Updated PartnerContacts link details for partner_contact_id {partner_contact_id}.")
                updated_link = True
        except sqlite3.Error as e:
            logger.error(f"Database error updating PartnerContacts link for {partner_contact_id}: {e}")
            # No specific return here, rely on updated_link or updated_central

    return updated_central or updated_link

@_manage_conn
def delete_partner_contact(partner_contact_id: int, conn: sqlite3.Connection = None) -> bool:
    """
    Deletes the link between a partner and a contact from PartnerContacts.
    Does NOT delete the contact from the central Contacts table.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM PartnerContacts WHERE partner_contact_id = ?", (partner_contact_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error deleting partner contact {contact_id}: {e}")
        return False

@_manage_conn
def delete_contacts_for_partner(partner_id: str, conn: sqlite3.Connection = None) -> bool:
    """
    Deletes all links between a specific partner and their associated contacts
    from the PartnerContacts table. Does NOT delete contacts from the central Contacts table.
    Returns True if deletion was attempted (does not guarantee rows were deleted if none existed).
    Check rowcount from cursor if specific feedback on rows deleted is needed.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM PartnerContacts WHERE partner_id = ?", (partner_id,))
        # cursor.rowcount will indicate how many rows were actually deleted.
        # For this function, returning True on successful execution (no error) is typical.
        logger.info(f"Attempted deletion of all contacts for partner {partner_id}. Rows affected: {cursor.rowcount}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error deleting contacts for partner {partner_id}: {e}")
        return False

# --- PartnerCategoryLink CRUD ---
@_manage_conn
def link_partner_to_category(partner_id: str, category_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    sql = "INSERT OR IGNORE INTO PartnerCategoryLink (partner_id, category_id) VALUES (?, ?)"
    try:
        cursor.execute(sql, (partner_id, category_id))
        # INSERT OR IGNORE won't increment rowcount if it's ignored.
        # We can check if the link exists after to confirm success.
        cursor.execute("SELECT 1 FROM PartnerCategoryLink WHERE partner_id = ? AND category_id = ?", (partner_id, category_id))
        return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"Database error linking partner {partner_id} to category {category_id}: {e}")
        return False

@_manage_conn
def unlink_partner_from_category(partner_id: str, category_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    sql = "DELETE FROM PartnerCategoryLink WHERE partner_id = ? AND category_id = ?"
    try:
        cursor.execute(sql, (partner_id, category_id))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error unlinking partner {partner_id} from category {category_id}: {e}")
        return False

@_manage_conn
def get_categories_for_partner(partner_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = """
        SELECT pc.*
        FROM PartnerCategories pc
        JOIN PartnerCategoryLink pcl ON pc.partner_category_id = pcl.partner_category_id
        WHERE pcl.partner_id = ? ORDER BY pc.category_name
    """
    cursor.execute(sql, (partner_id,))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_partners_in_category(category_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = """
        SELECT p.*
        FROM Partners p
        JOIN PartnerCategoryLink pcl ON p.partner_id = pcl.partner_id
        WHERE pcl.partner_category_id = ? ORDER BY p.partner_name
    """
    cursor.execute(sql, (category_id,))
    return [dict(row) for row in cursor.fetchall()]

# --- PartnerDocuments CRUD ---
@_manage_conn
def add_partner_document(data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor = conn.cursor()
    new_document_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    required_fields = ['partner_id', 'document_name', 'file_path_relative']
    for field in required_fields:
        if not data.get(field):
            logger.error(f"{field} is required for adding a partner document.")
            return None

    sql = """
        INSERT INTO PartnerDocuments (document_id, partner_id, document_name, file_path_relative,
                                      document_type, description, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        new_document_id, data['partner_id'], data['document_name'], data['file_path_relative'],
        data.get('document_type'), data.get('description'), now, now
    )
    try:
        cursor.execute(sql, params)
        return new_document_id
    except sqlite3.IntegrityError as e:
        logger.warning(f"Failed to add document for partner {data.get('partner_id')}. Error: {e}")
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error in add_partner_document: {e}")
        return None

@_manage_conn
def get_documents_for_partner(partner_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT * FROM PartnerDocuments WHERE partner_id = ? ORDER BY created_at DESC"
    cursor.execute(sql, (partner_id,))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_partner_document_by_id(document_id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    sql = "SELECT * FROM PartnerDocuments WHERE document_id = ?"
    cursor.execute(sql, (document_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def update_partner_document(document_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data or not any(k in data for k in ['document_name', 'document_type', 'description']):
        logger.info("No updatable fields provided for update_partner_document.")
        return False

    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    update_fields = {k: v for k, v in data.items() if k in ['document_name', 'document_type', 'description']}
    if not update_fields: return False

    update_fields['updated_at'] = now
    set_clauses = [f"{key} = ?" for key in update_fields.keys()]
    params = list(update_fields.values())
    params.append(document_id)

    sql = f"UPDATE PartnerDocuments SET {', '.join(set_clauses)} WHERE document_id = ?"
    try:
        cursor.execute(sql, tuple(params))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error updating partner document {document_id}: {e}")
        return False

@_manage_conn
def delete_partner_document(document_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    sql = "DELETE FROM PartnerDocuments WHERE document_id = ?"
    try:
        cursor.execute(sql, (document_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error deleting partner document {document_id}: {e}")
        return False

__all__ = [
    # PartnerCategories
    "add_partner_category",
    "get_partner_category_by_id",
    "get_partner_category_by_name",
    "get_all_partner_categories",
    "update_partner_category",
    "delete_partner_category",
    "get_or_add_partner_category",
    # Partners
    "add_partner",
    "get_partner_by_id",
    "get_partner_by_email",
    "get_all_partners",
    "update_partner",
    "delete_partner",
    "get_partners_by_category_id", # Alias for get_all_partners with filter
    # PartnerContacts
    "add_partner_contact",
    "get_partner_contact_by_id",
    "get_contacts_for_partner",
    "update_partner_contact",
    "delete_partner_contact",
    "delete_contacts_for_partner",
    # PartnerCategoryLink
    "link_partner_to_category",
    "unlink_partner_from_category",
    "get_categories_for_partner",
    "get_partners_in_category", # This is the one needed by the import
    # PartnerDocuments
    "add_partner_document",
    "get_documents_for_partner",
    "get_partner_document_by_id",
    "update_partner_document",
    "delete_partner_document",
]
