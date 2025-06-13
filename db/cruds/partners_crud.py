import sqlite3
import uuid
from datetime import datetime
import logging
from .generic_crud import get_db_connection, _manage_conn

# Setup logger
logger = logging.getLogger(__name__)

# --- PartnerCategories CRUD Functions ---

@_manage_conn
def add_partner_category(category_data: dict, conn: sqlite3.Connection = None) -> int | None:
    """Adds a new partner category to the database."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO PartnerCategories (category_name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (
            category_data['category_name'],
            category_data.get('description'),
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))
        # conn.commit() will be handled by _manage_conn
        logger.info(f"Partner category '{category_data['category_name']}' added with ID: {cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        logger.error(f"Error adding partner category '{category_data['category_name']}': {e} (Likely already exists).")
        return None
    except Exception as e:
        logger.error(f"Unexpected error adding partner category '{category_data['category_name']}': {e}", exc_info=True)
        return None

@_manage_conn
def get_partner_category_by_id(category_id: int, conn: sqlite3.Connection = None) -> dict | None:
    """Retrieves a partner category by its ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PartnerCategories WHERE partner_category_id = ?", (category_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_partner_category_by_name(category_name: str, conn: sqlite3.Connection = None) -> dict | None:
    """Retrieves a partner category by its name."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PartnerCategories WHERE category_name = ?", (category_name,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_partner_categories(conn: sqlite3.Connection = None) -> list[dict]:
    """Retrieves all partner categories."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PartnerCategories ORDER BY category_name")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@_manage_conn
def update_partner_category(category_id: int, category_data: dict, conn: sqlite3.Connection = None) -> bool:
    """Updates an existing partner category."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE PartnerCategories
            SET category_name = ?, description = ?, updated_at = ?
            WHERE partner_category_id = ?
        """, (
            category_data['category_name'],
            category_data.get('description'),
            datetime.utcnow().isoformat(),
            category_id
        ))
        # conn.commit() will be handled by _manage_conn
        updated = cursor.rowcount > 0
        if updated:
            logger.info(f"Partner category ID {category_id} updated.")
        else:
            logger.warning(f"Partner category ID {category_id} not found for update.")
        return updated
    except sqlite3.IntegrityError as e:
        logger.error(f"Error updating partner category ID {category_id}: {e} (Name might conflict).")
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating partner category ID {category_id}: {e}", exc_info=True)
        return False

@_manage_conn
def delete_partner_category(category_id: int, conn: sqlite3.Connection = None) -> bool:
    """Deletes a partner category.
       Note: This will fail if partners are linked to this category due to FK constraints,
       unless ON DELETE SET NULL/CASCADE is handled appropriately in schema or by pre-updating partners.
       The current schema for Partners has ON DELETE SET NULL for partner_category_id.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM PartnerCategories WHERE partner_category_id = ?", (category_id,))
        # conn.commit() will be handled by _manage_conn
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Partner category ID {category_id} deleted.")
        else:
            logger.warning(f"Partner category ID {category_id} not found for deletion.")
        return deleted
    except Exception as e:
        logger.error(f"Error deleting partner category ID {category_id}: {e}", exc_info=True)
        return False

# --- Partners CRUD Functions ---

@_manage_conn
def add_partner(partner_data: dict, conn: sqlite3.Connection = None) -> str | None:
    """Adds a new partner to the database."""
    cursor = conn.cursor()
    partner_id = str(uuid.uuid4())
    try:
        cursor.execute("""
            INSERT INTO Partners (
                partner_id, partner_name, partner_category_id, contact_person_name, email,
                phone, address, website_url, services_offered, collaboration_start_date,
                status, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            partner_id,
            partner_data['partner_name'],
            partner_data.get('partner_category_id'),
            partner_data.get('contact_person_name'),
            partner_data.get('email'),
            partner_data.get('phone'),
            partner_data.get('address'),
            partner_data.get('website_url'),
            partner_data.get('services_offered'),
            partner_data.get('collaboration_start_date'),
            partner_data.get('status', 'Active'),
            partner_data.get('notes'),
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))
        # conn.commit() handled by _manage_conn
        logger.info(f"Partner '{partner_data['partner_name']}' added with ID: {partner_id}")
        return partner_id
    except sqlite3.IntegrityError as e: # e.g. email unique constraint
        logger.error(f"Error adding partner '{partner_data['partner_name']}': {e} (Likely unique constraint violation).")
        return None
    except Exception as e:
        logger.error(f"Unexpected error adding partner '{partner_data['partner_name']}': {e}", exc_info=True)
        return None

@_manage_conn
def get_partner_by_id(partner_id: str, conn: sqlite3.Connection = None) -> dict | None:
    """Retrieves a partner by its ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Partners WHERE partner_id = ?", (partner_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_all_partners(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    """Retrieves all partners, optionally filtered."""
    cursor = conn.cursor()
    query = "SELECT p.*, pc.category_name as partner_category_name FROM Partners p LEFT JOIN PartnerCategories pc ON p.partner_category_id = pc.partner_category_id"
    params = []

    if filters:
        conditions = []
        for key, value in filters.items():
            if value is not None:
                if key == "partner_category_id": # Example filter
                    conditions.append(f"p.partner_category_id = ?")
                    params.append(value)
                elif key == "status":
                    conditions.append(f"p.status = ?")
                    params.append(value)
                # Add more filters as needed
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY p.partner_name"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@_manage_conn
def get_partners_by_category_id(category_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    """Retrieves all partners belonging to a specific category."""
    return get_all_partners(filters={'partner_category_id': category_id}, conn=conn)


@_manage_conn
def update_partner(partner_id: str, partner_data: dict, conn: sqlite3.Connection = None) -> bool:
    """Updates an existing partner."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Partners SET
                partner_name = ?, partner_category_id = ?, contact_person_name = ?, email = ?,
                phone = ?, address = ?, website_url = ?, services_offered = ?,
                collaboration_start_date = ?, status = ?, notes = ?, updated_at = ?
            WHERE partner_id = ?
        """, (
            partner_data['partner_name'],
            partner_data.get('partner_category_id'),
            partner_data.get('contact_person_name'),
            partner_data.get('email'),
            partner_data.get('phone'),
            partner_data.get('address'),
            partner_data.get('website_url'),
            partner_data.get('services_offered'),
            partner_data.get('collaboration_start_date'),
            partner_data.get('status', 'Active'),
            partner_data.get('notes'),
            datetime.utcnow().isoformat(),
            partner_id
        ))
        # conn.commit() handled by _manage_conn
        updated = cursor.rowcount > 0
        if updated:
            logger.info(f"Partner ID {partner_id} updated.")
        else:
            logger.warning(f"Partner ID {partner_id} not found for update.")
        return updated
    except sqlite3.IntegrityError as e:
        logger.error(f"Error updating partner ID {partner_id}: {e} (Constraint violation).")
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating partner ID {partner_id}: {e}", exc_info=True)
        return False

@_manage_conn
def delete_partner(partner_id: str, conn: sqlite3.Connection = None) -> bool:
    """Deletes a partner.
       This will also delete related PartnerContacts, PartnerCategoryLink, PartnerDocuments
       due to ON DELETE CASCADE in their schema definitions.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Partners WHERE partner_id = ?", (partner_id,))
        # conn.commit() handled by _manage_conn
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Partner ID {partner_id} deleted.")
        else:
            logger.warning(f"Partner ID {partner_id} not found for deletion.")
        return deleted
    except Exception as e:
        logger.error(f"Error deleting partner ID {partner_id}: {e}", exc_info=True)
        return False

# Helper for seeding if needed - get or add category
@_manage_conn
def get_or_add_partner_category(category_name: str, description: str = None, conn: sqlite3.Connection = None) -> int | None:
    """Gets a partner category by name, adds it if it doesn't exist. Returns category_id."""
    category = get_partner_category_by_name(category_name, conn=conn) # Pass conn
    if category:
        return category['partner_category_id']
    else:
        return add_partner_category({'category_name': category_name, 'description': description}, conn=conn) # Pass conn
