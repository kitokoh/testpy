import sqlite3
from .generic_crud import _manage_conn, get_db_connection
import logging

# --- TemplateCategories CRUD ---
@_manage_conn
def add_template_category(category_name: str, description: str = None, purpose: str = None, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor()
    try:
        cursor.execute("INSERT INTO TemplateCategories (category_name, description, purpose) VALUES (?,?,?)", (category_name, description, purpose))
        return cursor.lastrowid
    except sqlite3.IntegrityError: # Category name likely not unique
        try:
            # Attempt to fetch the existing category's ID if it already exists.
            cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = ?", (category_name,))
            row = cursor.fetchone()
            if row:
                logging.warning(f"Template category '{category_name}' already exists with id {row['category_id']}. Returning existing id.")
                return row['category_id']
            else:
                # This case should ideally not be reached if IntegrityError was due to unique constraint
                logging.error(f"IntegrityError for template category '{category_name}', but could not retrieve existing.")
                return None
        except sqlite3.Error as e_fetch:
            logging.error(f"Failed to fetch existing template category '{category_name}' after IntegrityError: {e_fetch}")
            return None
    except sqlite3.Error as e:
        logging.error(f"Failed to add template category '{category_name}': {e}")
        return None

@_manage_conn
def get_template_category_by_id(category_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM TemplateCategories WHERE category_id = ?", (category_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get template category by id {category_id}: {e}")
        return None

@_manage_conn
def get_template_category_by_name(category_name: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM TemplateCategories WHERE category_name = ?", (category_name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get template category by name '{category_name}': {e}")
        return None

@_manage_conn
def get_all_template_categories(conn: sqlite3.Connection = None) -> list[dict]:
    logging.info("Attempting to fetch all template categories.")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM TemplateCategories ORDER BY category_name")
        rows = cursor.fetchall()
        logging.info(f"Found {len(rows)} template categories.")
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logging.error(f"Failed to get all template categories: {e}")
        return []

@_manage_conn
def update_template_category(category_id: int, new_name: str = None, new_description: str = None, new_purpose: str = None, conn: sqlite3.Connection = None) -> bool:
    if not new_name and new_description is None and new_purpose is None:
        logging.info("No new name, description, or purpose provided for update_template_category.")
        return False

    cursor = conn.cursor()
    set_clauses = []
    params = []
    if new_name:
        set_clauses.append("category_name = ?")
        params.append(new_name)
    if new_description is not None: # Allow empty string for description
        set_clauses.append("description = ?")
        params.append(new_description)
    if new_purpose is not None: # Allow empty string for purpose
        set_clauses.append("purpose = ?")
        params.append(new_purpose)

    if not set_clauses:
        logging.info("No valid fields to update in update_template_category.") # Should be unreachable if first check is correct
        return False

    sql = f"UPDATE TemplateCategories SET {', '.join(set_clauses)} WHERE category_id = ?"
    params.append(category_id)

    try:
        cursor.execute(sql, tuple(params))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to update template category {category_id}: {e}")
        return False

@_manage_conn
def delete_template_category(category_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM TemplateCategories WHERE category_id = ?", (category_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to delete template category {category_id}: {e}")
        return False

@_manage_conn
def get_template_category_details(category_id: int, conn: sqlite3.Connection = None) -> dict | None:
    # This function is essentially an alias for get_template_category_by_id
    return get_template_category_by_id(category_id, conn=conn)
