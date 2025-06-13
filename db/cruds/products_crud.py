import sqlite3
from datetime import datetime
from .generic_crud import _manage_conn, get_db_connection
import logging
from typing import Dict, Any, Optional
from . import product_media_links_crud
import os

# --- Products CRUD ---
@_manage_conn
def get_product_by_id(id: int, conn: sqlite3.Connection = None) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Products WHERE product_id = ?", (id,))
        row = cursor.fetchone()
        if not row:
            return None

        product_dict = dict(row)

        # Fetch associated media links
        # The get_media_links_for_product function already returns detailed media info
        media_links = product_media_links_crud.get_media_links_for_product(product_id=id, conn=conn)

        # Process media_links to potentially create full URLs if needed, or pass them as is.
        # For now, we'll pass them as returned by get_media_links_for_product.
        # The structure includes 'media_filepath' and 'media_thumbnail_path'.
        # Consumers (like an API) can then decide how to form full URLs based on a base path.
        product_dict['media_links'] = media_links

        return product_dict
    except sqlite3.Error as e:
        logging.error(f"Error getting product by ID {id}: {e}")
        return None

@_manage_conn
def add_product(product_data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"
    if not product_data.get('product_name') or product_data.get('base_unit_price') is None:
        logging.error("Error: product_name and base_unit_price are required for add_product.")
        return None
    sql = """INSERT INTO Products
             (product_name, description, category, language_code, base_unit_price,
              unit_of_measure, weight, dimensions, is_active, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    params = (product_data.get('product_name'), product_data.get('description'),
              product_data.get('category'), product_data.get('language_code', 'fr'),
              product_data.get('base_unit_price'), product_data.get('unit_of_measure'),
              product_data.get('weight'), product_data.get('dimensions'),
              product_data.get('is_active', True), now, now)
    try:
        cursor.execute(sql, params)
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        logging.error(f"IntegrityError in add_product for '{product_data.get('product_name')}': {e}")
        return None
    except sqlite3.Error as e_gen:
        logging.error(f"SQLite error in add_product for '{product_data.get('product_name')}': {e_gen}")
        return None

@_manage_conn
def get_product_by_name(product_name: str, conn: sqlite3.Connection = None) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Products WHERE product_name = ?", (product_name,))
        row = cursor.fetchone()
        if not row:
            return None

        product_dict = dict(row)
        product_id = product_dict.get('product_id')

        if product_id is not None:
            media_links = product_media_links_crud.get_media_links_for_product(product_id=product_id, conn=conn)
            product_dict['media_links'] = media_links
        else:
            product_dict['media_links'] = [] # Should not happen if product_id is PK

        return product_dict
    except sqlite3.Error as e:
        logging.error(f"Error getting product by name '{product_name}': {e}")
        return None

@_manage_conn
def get_all_products(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM Products"; q_params = []
    if filters:
        clauses = []
        valid_filters = ['category', 'product_name', 'is_active', 'language_code'] # Added more filters
        for k,v in filters.items():
            if k in valid_filters:
                if k == 'product_name': # Use LIKE for name search
                    clauses.append("product_name LIKE ?")
                    q_params.append(f"%{v}%")
                elif k == 'is_active': # Handle boolean
                    clauses.append("is_active = ?")
                    q_params.append(1 if v else 0)
                else:
                    clauses.append(f"{k} = ?")
                    q_params.append(v)
        if clauses: sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY product_name"
    try:
        cursor.execute(sql, q_params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error getting all products with filters '{filters}': {e}")
        return []

@_manage_conn
def update_product(product_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"; data['updated_at'] = now
    valid_cols = ['product_name', 'description', 'category', 'language_code',
                  'base_unit_price', 'unit_of_measure', 'weight', 'dimensions',
                  'is_active', 'updated_at']
    to_set = {k:v for k,v in data.items() if k in valid_cols}
    if not to_set: return False

    set_c = [f"{k}=?" for k in to_set.keys()]; params = list(to_set.values()); params.append(product_id)
    sql = f"UPDATE Products SET {', '.join(set_c)} WHERE product_id = ?"
    try:
        cursor.execute(sql, params)
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Error updating product {product_id}: {e}")
        return False

@_manage_conn
def delete_product(product_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Products WHERE product_id = ?", (product_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Error deleting product {product_id}: {e}")
        return False

@_manage_conn
def get_products(language_code: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); sql = "SELECT * FROM Products"; params = []; conditions = ["is_active = TRUE"]
    if language_code:
        conditions.append("language_code = ?")
        params.append(language_code)
    sql += " WHERE " + " AND ".join(conditions) + " ORDER BY product_name"
    try:
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error getting products (lang: {language_code}): {e}")
        return []

@_manage_conn
def update_product_price(product_id: int, new_price: float, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"
    sql = "UPDATE Products SET base_unit_price = ?, updated_at = ? WHERE product_id = ?"
    try:
        cursor.execute(sql, (new_price, now, product_id))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Error updating price for product {product_id}: {e}")
        return False

@_manage_conn
def get_products_by_name_pattern(pattern: str, conn: sqlite3.Connection = None) -> list[dict] | None:
    cursor = conn.cursor(); search_pattern = f"%{pattern}%"
    sql = "SELECT * FROM Products WHERE product_name LIKE ? ORDER BY product_name LIMIT 10"
    try:
        cursor.execute(sql, (search_pattern,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error getting products by name pattern '{pattern}': {e}")
        return None

@_manage_conn
def get_all_products_for_selection_filtered(language_code: str = None, name_pattern: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); params = []; conditions = ["is_active = TRUE"]
    if language_code:
        conditions.append("language_code = ?"); params.append(language_code)
    if name_pattern:
        conditions.append("(product_name LIKE ? OR description LIKE ?)")
        params.extend([f"%{name_pattern}%", f"%{name_pattern}%"])

    sql = f"SELECT product_id, product_name, description, base_unit_price, language_code FROM Products WHERE {' AND '.join(conditions)} ORDER BY product_name"
    try:
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error in get_all_products_for_selection_filtered (lang: {language_code}, pattern: {name_pattern}): {e}")
        return []

@_manage_conn
def get_total_products_count(conn: sqlite3.Connection = None) -> int:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(product_id) as total_count FROM Products")
        row = cursor.fetchone()
        return row['total_count'] if row else 0
    except sqlite3.Error as e:
        logging.error(f"Error getting total products count: {e}")
        return 0

# --- ProductDimensions CRUD ---
@_manage_conn
def add_or_update_product_dimension(product_id: int, dimension_data: dict, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); now = datetime.utcnow().isoformat() + "Z"
    try:
        cursor.execute("SELECT product_id FROM ProductDimensions WHERE product_id = ?", (product_id,))
        exists = cursor.fetchone()
        dim_cols = ['dim_A','dim_B','dim_C','dim_D','dim_E','dim_F','dim_G','dim_H','dim_I','dim_J','technical_image_path']

        if exists:
            data_to_set = {k:v for k,v in dimension_data.items() if k in dim_cols}
            if not data_to_set: # Only update timestamp if no other fields
                cursor.execute("UPDATE ProductDimensions SET updated_at = ? WHERE product_id = ?", (now, product_id))
                return True # Assuming success if only timestamp is updated
            data_to_set['updated_at'] = now
            set_c = [f"{k}=?" for k in data_to_set.keys()]; params_list = list(data_to_set.values()); params_list.append(product_id)
            sql = f"UPDATE ProductDimensions SET {', '.join(set_c)} WHERE product_id = ?"
            cursor.execute(sql, params_list)
        else:
            cols = ['product_id','created_at','updated_at'] + [col for col in dim_cols if col in dimension_data] # Only include provided dim_cols
            vals = [product_id, now, now] + [dimension_data.get(c) for c in dim_cols if c in dimension_data]
            placeholders = ','.join(['?']*len(cols))
            sql = f"INSERT INTO ProductDimensions ({','.join(cols)}) VALUES ({placeholders})"
            cursor.execute(sql, tuple(vals))
        return cursor.rowcount > 0 or (not exists and cursor.lastrowid is not None) # lastrowid for INSERT
    except sqlite3.Error as e:
        logging.error(f"Error in add_or_update_product_dimension for product {product_id}: {e}")
        return False

@_manage_conn
def get_product_dimension(product_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM ProductDimensions WHERE product_id = ?", (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Error getting product dimension for product {product_id}: {e}")
        return None

@_manage_conn
def delete_product_dimension(product_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM ProductDimensions WHERE product_id = ?", (product_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Error deleting product dimension for product {product_id}: {e}")
        return False

# --- ProductEquivalencies CRUD ---
@_manage_conn
def add_product_equivalence(product_id_a: int, product_id_b: int, conn: sqlite3.Connection = None) -> int | None:
    if product_id_a == product_id_b:
        logging.warning("Cannot create equivalence for a product with itself.")
        return None
    p_a, p_b = min(product_id_a, product_id_b), max(product_id_a, product_id_b)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO ProductEquivalencies (product_id_a, product_id_b) VALUES (?,?)", (p_a,p_b))
        return cursor.lastrowid
    except sqlite3.IntegrityError: # Already exists
        try:
            cursor.execute("SELECT equivalence_id FROM ProductEquivalencies WHERE product_id_a = ? AND product_id_b = ?", (p_a,p_b))
            row=cursor.fetchone()
            logging.warning(f"Equivalence between {p_a} and {p_b} already exists.")
            return row['equivalence_id'] if row else None
        except sqlite3.Error as e_fetch:
            logging.error(f"Error fetching existing equivalence for {p_a}-{p_b}: {e_fetch}")
            return None
    except sqlite3.Error as e:
        logging.error(f"Error adding product equivalence for {p_a}-{p_b}: {e}")
        return None

@_manage_conn
def get_equivalent_products(product_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor(); ids = set()
    try:
        cursor.execute("SELECT product_id_b FROM ProductEquivalencies WHERE product_id_a = ?", (product_id,))
        for row in cursor.fetchall(): ids.add(row['product_id_b'])
        cursor.execute("SELECT product_id_a FROM ProductEquivalencies WHERE product_id_b = ?", (product_id,))
        for row in cursor.fetchall(): ids.add(row['product_id_a'])
        ids.discard(product_id) # Remove the product itself if present

        if not ids: return []

        placeholders = ','.join('?'*len(ids))
        cursor.execute(f"SELECT * FROM Products WHERE product_id IN ({placeholders})", tuple(ids))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error getting equivalent products for product {product_id}: {e}")
        return []

@_manage_conn
def get_all_product_equivalencies(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = """SELECT pe.*,
             pA.product_name AS product_name_a, pA.language_code AS language_code_a,
             pA.weight AS weight_a, pA.dimensions AS dimensions_a,
             pB.product_name AS product_name_b, pB.language_code AS language_code_b,
             pB.weight AS weight_b, pB.dimensions AS dimensions_b
             FROM ProductEquivalencies pe
             JOIN Products pA ON pe.product_id_a = pA.product_id
             JOIN Products pB ON pe.product_id_b = pB.product_id
             ORDER BY pA.product_name, pB.product_name"""
    try:
        cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error getting all product equivalencies: {e}")
        return []

@_manage_conn
def remove_product_equivalence(equivalence_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM ProductEquivalencies WHERE equivalence_id = ?", (equivalence_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Error removing product equivalence {equivalence_id}: {e}")
        return False
