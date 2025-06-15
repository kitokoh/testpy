import sqlite3
from datetime import datetime
import logging
from typing import List, Dict, Optional, Any

from ..db.cruds.generic_crud import _manage_conn, get_db_connection # Corrected relative import


@_manage_conn
def link_media_to_product(product_id: int, media_item_id: str,
                          display_order: int = 0, alt_text: Optional[str] = None,
                          conn: sqlite3.Connection = None) -> Optional[int]:
    """
    Links a media item to a product in the ProductMediaLinks table.
    Returns the link_id if successful, None otherwise.
    """
    now = datetime.utcnow().isoformat() + "Z"
    sql = """
        INSERT INTO ProductMediaLinks (product_id, media_item_id, display_order, alt_text, created_at)
        VALUES (?, ?, ?, ?, ?)
    """
    params = (product_id, media_item_id, display_order, alt_text, now)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        logging.error(f"IntegrityError linking media {media_item_id} to product {product_id}: {e}")
        return None
    except sqlite3.Error as e:
        logging.error(f"SQLite error linking media {media_item_id} to product {product_id}: {e}")
        return None

@_manage_conn
def get_media_links_for_product(product_id: int, conn: sqlite3.Connection = None) -> List[Dict[str, Any]]:
    """
    Retrieves all media links for a given product_id, ordered by display_order.
    Each link includes details from ProductMediaLinks and MediaItems.
    """
    sql = """
        SELECT
            pml.link_id,
            pml.product_id,
            pml.media_item_id,
            pml.display_order,
            pml.alt_text,
            pml.created_at AS link_created_at,
            mi.title AS media_title,
            mi.description AS media_description,
            mi.item_type AS media_item_type,
            mi.filepath AS media_filepath,
            mi.thumbnail_path AS media_thumbnail_path,
            mi.metadata_json AS media_metadata_json
        FROM ProductMediaLinks pml
        JOIN MediaItems mi ON pml.media_item_id = mi.media_item_id
        WHERE pml.product_id = ?
        ORDER BY pml.display_order ASC, pml.created_at ASC
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (product_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logging.error(f"SQLite error retrieving media links for product {product_id}: {e}")
        return []

@_manage_conn
def get_media_link_by_ids(product_id: int, media_item_id: str, conn: sqlite3.Connection = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves a specific media link by product_id and media_item_id.
    """
    sql = "SELECT * FROM ProductMediaLinks WHERE product_id = ? AND media_item_id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (product_id, media_item_id))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"SQLite error retrieving link for product {product_id}, media {media_item_id}: {e}")
        return None

@_manage_conn
def get_media_link_by_link_id(link_id: int, conn: sqlite3.Connection = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves a specific media link by its link_id.
    """
    sql = "SELECT * FROM ProductMediaLinks WHERE link_id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (link_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"SQLite error retrieving link by link_id {link_id}: {e}")
        return None

@_manage_conn
def update_media_link(link_id: int, display_order: Optional[int] = None,
                      alt_text: Optional[str] = None, conn: sqlite3.Connection = None) -> bool:
    """
    Updates the display_order and/or alt_text for a specific media link.
    Returns True if update was successful, False otherwise.
    """
    if display_order is None and alt_text is None:
        logging.warning(f"Update_media_link called without changes for link_id {link_id}.")
        return False

    fields_to_update = {}
    if display_order is not None:
        fields_to_update['display_order'] = display_order
    if alt_text is not None:
        fields_to_update['alt_text'] = alt_text

    if not fields_to_update:
        return False

    set_clauses = [f"{field} = ?" for field in fields_to_update.keys()]
    params = list(fields_to_update.values())
    params.append(link_id)

    sql = f"UPDATE ProductMediaLinks SET {', '.join(set_clauses)} WHERE link_id = ?"

    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.rowcount > 0
    except sqlite3.IntegrityError as e:
        logging.error(f"IntegrityError updating media link {link_id}: {e}")
        return False
    except sqlite3.Error as e:
        logging.error(f"SQLite error updating media link {link_id}: {e}")
        return False

@_manage_conn
def unlink_media_from_product(link_id: int, conn: sqlite3.Connection = None) -> bool:
    """
    Removes a specific media link by its link_id.
    Returns True if deletion was successful, False otherwise.
    """
    sql = "DELETE FROM ProductMediaLinks WHERE link_id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (link_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"SQLite error unlinking media (link_id {link_id}): {e}")
        return False

@_manage_conn
def unlink_media_by_ids(product_id: int, media_item_id: str, conn: sqlite3.Connection = None) -> bool:
    """
    Removes a specific media link by product_id and media_item_id.
    Returns True if deletion was successful, False otherwise.
    """
    sql = "DELETE FROM ProductMediaLinks WHERE product_id = ? AND media_item_id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (product_id, media_item_id))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"SQLite error unlinking media for product {product_id}, media {media_item_id}: {e}")
        return False

@_manage_conn
def unlink_all_media_from_product(product_id: int, conn: sqlite3.Connection = None) -> int:
    """
    Removes all media links for a given product_id.
    Returns the number of links removed.
    """
    sql = "DELETE FROM ProductMediaLinks WHERE product_id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (product_id,))
        return cursor.rowcount
    except sqlite3.Error as e:
        logging.error(f"SQLite error unlinking all media for product {product_id}: {e}")
        return 0

def update_product_media_display_orders(product_id: int, ordered_media_item_ids: List[str]) -> bool:
    """
    Updates the display_order for all media items linked to a product based on a new list of ordered media_item_ids.
    This is a transactional operation.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        for index, media_item_id in enumerate(ordered_media_item_ids):
            sql_update = "UPDATE ProductMediaLinks SET display_order = ? WHERE product_id = ? AND media_item_id = ?"
            cursor.execute(sql_update, (index, product_id, media_item_id))
            if cursor.rowcount == 0:
                conn.rollback()
                logging.error(f"Failed to update display order: Media item {media_item_id} not found for product {product_id}.")
                return False

        conn.commit()
        return True
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logging.error(f"SQLite error updating display orders for product {product_id}: {e}")
        return False
    finally:
        if conn:
            conn.close()
