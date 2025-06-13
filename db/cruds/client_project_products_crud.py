import sqlite3
import logging
from datetime import datetime

from .generic_crud import _manage_conn
# products_crud is needed for get_product_by_id, used by add and update operations
from .products_crud import get_product_by_id

logger = logging.getLogger(__name__)

@_manage_conn
def get_distinct_purchase_confirmed_at_for_client(client_id: str, conn: sqlite3.Connection = None) -> list[str] | None:
    """
    Retrieves a list of distinct, non-null purchase_confirmed_at timestamps
    for a given client_id from the ClientProjectProducts table.
    Returns a list of ISO formatted timestamp strings, or None on error.
    """
    cursor = conn.cursor()
    try:
        sql = """
            SELECT DISTINCT purchase_confirmed_at
            FROM ClientProjectProducts
            WHERE client_id = ? AND purchase_confirmed_at IS NOT NULL
            ORDER BY purchase_confirmed_at DESC;
        """
        cursor.execute(sql, (client_id,))
        rows = cursor.fetchall()
        return [row[0] for row in rows if row[0] is not None]
    except sqlite3.Error as e:
        logger.error(f"Database error in get_distinct_purchase_confirmed_at_for_client for client {client_id}: {e}", exc_info=True)
        return None
    except Exception as ex:
        logger.error(f"Unexpected error in get_distinct_purchase_confirmed_at_for_client for client {client_id}: {ex}", exc_info=True)
        return None

@_manage_conn
def add_product_to_client_or_project(link_data: dict, conn: sqlite3.Connection = None) -> int | None:
    """Adds a product link to a client or project."""
    cursor = conn.cursor()
    product_id = link_data.get('product_id')
    if not product_id:
        logger.error("product_id is required to link a product.")
        return None

    # Fetch product base_unit_price for calculating total_price_calculated
    # This uses get_product_by_id from products_crud
    prod_info = get_product_by_id(product_id, conn=conn) # Pass the connection
    if not prod_info:
        logger.error(f"Product with id {product_id} not found. Cannot link.")
        return None

    qty = link_data.get('quantity', 1)
    override_price = link_data.get('unit_price_override')

    effective_price = override_price if override_price is not None else prod_info.get('base_unit_price')
    if effective_price is None: # Ensure effective_price is not None before calculation
        logger.warning(f"Effective price for product {product_id} is None. Defaulting to 0.0 for total calculation.")
        effective_price = 0.0

    total_price = qty * float(effective_price)
    now = datetime.utcnow().isoformat() + "Z"

    sql = """
        INSERT INTO ClientProjectProducts (
            client_id, project_id, product_id, quantity,
            unit_price_override, total_price_calculated,
            serial_number, purchase_confirmed_at, added_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        link_data.get('client_id'),
        link_data.get('project_id'),
        product_id,
        qty,
        override_price,
        total_price,
        link_data.get('serial_number'),
        link_data.get('purchase_confirmed_at'),
        now
    )
    try:
        cursor.execute(sql, params)
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"DB error in add_product_to_client_or_project: {e}", exc_info=True)
        return None

@_manage_conn
def get_products_for_client_or_project(client_id: str = None, project_id: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    """
    Retrieves products linked to a specific client or project.
    Fetches comprehensive details by joining with the Products table.
    """
    if not client_id and not project_id:
        logger.error("Either client_id or project_id must be provided.")
        return []

    cursor = conn.cursor()
    sql = """
        SELECT cpp.*, p.product_name, p.description as product_description,
               p.category as product_category, p.base_unit_price,
               p.unit_of_measure, p.weight, p.dimensions, p.language_code
        FROM ClientProjectProducts cpp
        JOIN Products p ON cpp.product_id = p.product_id
    """
    conditions = []
    params = []

    if client_id:
        conditions.append("cpp.client_id = ?")
        params.append(client_id)
    if project_id:
        conditions.append("cpp.project_id = ?")
        params.append(project_id)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY cpp.added_at DESC"

    try:
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error in get_products_for_client_or_project: {e}", exc_info=True)
        return []

@_manage_conn
def update_client_project_product(link_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    """Updates a client/project product link."""
    if not data:
        return False

    cursor = conn.cursor()
    current_link = get_client_project_product_by_id(link_id, conn=conn) # Pass conn
    if not current_link:
        logger.error(f"ClientProjectProduct link with id {link_id} not found.")
        return False

    # Recalculate total_price_calculated if quantity or unit_price_override changes
    qty = data.get('quantity', current_link['quantity'])
    override_price = data.get('unit_price_override', current_link['unit_price_override'])

    # Need product's base_unit_price if override_price is being removed or was not set
    if 'unit_price_override' in data or 'quantity' in data:
        product_id = current_link['product_id']
        prod_info = get_product_by_id(product_id, conn=conn) # Pass conn
        if not prod_info:
            logger.error(f"Product with id {product_id} not found. Cannot update link {link_id}.")
            return False

        base_price = prod_info['base_unit_price']
        effective_price = override_price if override_price is not None else base_price
        if effective_price is None: effective_price = 0.0 # Fallback
        data['total_price_calculated'] = qty * float(effective_price)

    valid_cols = ['quantity', 'unit_price_override', 'total_price_calculated', 'serial_number', 'purchase_confirmed_at']
    fields_to_update = {k: v for k, v in data.items() if k in valid_cols}

    if not fields_to_update:
        logger.info(f"No valid fields to update for link_id {link_id}")
        return False # Or True, if no change means success

    set_clauses = [f"{key} = ?" for key in fields_to_update.keys()]
    params_list = list(fields_to_update.values())
    params_list.append(link_id)

    sql = f"UPDATE ClientProjectProducts SET {', '.join(set_clauses)} WHERE client_project_product_id = ?"

    try:
        cursor.execute(sql, tuple(params_list))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error updating link_id {link_id}: {e}", exc_info=True)
        return False

@_manage_conn
def remove_product_from_client_or_project(link_id: int, conn: sqlite3.Connection = None) -> bool:
    """Removes a product link by its ID."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM ClientProjectProducts WHERE client_project_product_id = ?", (link_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error removing link_id {link_id}: {e}", exc_info=True)
        return False

@_manage_conn
def get_client_project_product_by_id(link_id: int, conn: sqlite3.Connection = None) -> dict | None:
    """Retrieves a specific client/project product link by its ID, joined with product details."""
    cursor = conn.cursor()
    sql = """
        SELECT cpp.*, p.product_name, p.description as product_description,
               p.category as product_category, p.base_unit_price,
               p.unit_of_measure, p.weight, p.dimensions, p.language_code
        FROM ClientProjectProducts cpp
        JOIN Products p ON cpp.product_id = p.product_id
        WHERE cpp.client_project_product_id = ?
    """
    try:
        cursor.execute(sql, (link_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Database error fetching link_id {link_id}: {e}", exc_info=True)
        return None

__all__ = [
    "get_distinct_purchase_confirmed_at_for_client",
    "add_product_to_client_or_project",
    "get_products_for_client_or_project",
    "update_client_project_product",
    "remove_product_from_client_or_project",
    "get_client_project_product_by_id"
]
