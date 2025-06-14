import sqlite3
import uuid
from datetime import datetime
import logging
from .generic_crud import get_db_connection, _manage_conn

logger = logging.getLogger(__name__)

# --- PartnerCategories CRUD Functions ---
@_manage_conn
def add_partner_category(category_data_or_name: str | dict, description: str = None, conn: sqlite3.Connection = None) -> int | None:
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
def get_partner_category_by_name(name: str, conn: sqlite3.Connection = None) -> dict | None:
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
def add_partner_contact(contact_data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    sql = """
        INSERT INTO PartnerContacts (partner_id, name, email, phone, role, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        contact_data.get('partner_id'), contact_data.get('name'), contact_data.get('email'),
        contact_data.get('phone'), contact_data.get('role'), now, now
    )
    try:
        if not contact_data.get('partner_id') or not contact_data.get('name'):
            logger.error("partner_id and name are required for adding a partner contact.")
            return None
        cursor.execute(sql, params)
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        logger.warning(f"Failed to add partner contact for partner {contact_data.get('partner_id')}. Error: {e}")
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error in add_partner_contact: {e}")
        return None

@_manage_conn
def get_partner_contact_by_id(contact_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PartnerContacts WHERE contact_id = ?", (contact_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_contacts_for_partner(partner_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PartnerContacts WHERE partner_id = ? ORDER BY name", (partner_id,))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_partner_contact(contact_id: int, contact_data: dict, conn: sqlite3.Connection = None) -> bool:
    if not contact_data: return False
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    contact_data['updated_at'] = now

    valid_columns = ['name', 'email', 'phone', 'role', 'updated_at']
    fields_to_update = {k:v for k,v in contact_data.items() if k in valid_columns and v is not None}

    if not fields_to_update or ('updated_at' in fields_to_update and len(fields_to_update) == 1) :
         logger.info(f"No data fields to update for partner contact {contact_id} other than timestamp.")
         # Still update timestamp if that's the only change
         if 'updated_at' in fields_to_update and len(fields_to_update) == 1:
            cursor.execute("UPDATE PartnerContacts SET updated_at = ? WHERE contact_id = ?", (now, contact_id))
            return cursor.rowcount > 0
         return False


    set_clauses = [f"{col} = ?" for col in fields_to_update.keys()]
    params = list(fields_to_update.values())
    params.append(contact_id)

    sql = f"UPDATE PartnerContacts SET {', '.join(set_clauses)} WHERE contact_id = ?"
    try:
        cursor.execute(sql, tuple(params))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error updating partner contact {contact_id}: {e}")
        return False

@_manage_conn
def delete_partner_contact(contact_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM PartnerContacts WHERE contact_id = ?", (contact_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error deleting partner contact {contact_id}: {e}")
        return False

@_manage_conn
def delete_contacts_for_partner(partner_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM PartnerContacts WHERE partner_id = ?", (partner_id,))
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
