import sqlite3
from datetime import datetime # datetime is used directly
import uuid # uuid might be used by functions like add_product_to_client_or_project indirectly or for future needs
import json # json might be used by functions indirectly or for future needs

# Assuming db_config.py is in the same directory 'db'
from .db_config import get_db_connection

# CRUD functions for Products
def add_product(product_data: dict) -> int | None:
    """Adds a new product, including weight and dimensions. Returns product_id or None."""
    conn = None
    try:
        product_name = product_data.get('product_name')
        base_unit_price = product_data.get('base_unit_price')
        language_code = product_data.get('language_code', 'fr') # Default to 'fr'

        if not product_name:
            print("Error in add_product: 'product_name' is required.")
            return None
        if base_unit_price is None:
            print("Error in add_product: 'base_unit_price' is required.")
            return None
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO Products (
                product_name, description, category, language_code, base_unit_price,
                unit_of_measure, weight, dimensions, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            product_name, product_data.get('description'),
            product_data.get('category'),
            language_code,
            base_unit_price,
            product_data.get('unit_of_measure'),
            product_data.get('weight'),
            product_data.get('dimensions'),
            product_data.get('is_active', True),
            now, now
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        print(f"IntegrityError in add_product for name '{product_name}' and lang '{language_code}': {e}")
        if conn:
            conn.rollback()
        return None
    except sqlite3.Error as e:
        print(f"Database error in add_product: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn: conn.close()

def get_product_by_id(product_id: int) -> dict | None:
    """Retrieves a product by ID, including weight and dimensions."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at FROM Products WHERE product_id = ?", (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_product_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_product_by_name(product_name: str) -> dict | None:
    """Retrieves a product by its exact name, including weight and dimensions. Returns a dict or None if not found."""
    conn = None
    if not product_name:
        return None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at FROM Products WHERE product_name = ?", (product_name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_product_by_name: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_products(filters: dict = None) -> list[dict]:
    """Retrieves all products, including weight and dimensions. Filters by category (exact) or product_name (partial LIKE)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at FROM Products"
        params = []
        where_clauses = []
        if filters:
            if 'category' in filters:
                where_clauses.append("category = ?")
                params.append(filters['category'])
            if 'product_name' in filters:
                where_clauses.append("product_name LIKE ?")
                params.append(f"%{filters['product_name']}%")

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_products: {e}")
        return []
    finally:
        if conn: conn.close()

def update_product(product_id: int, product_data: dict) -> bool:
    """Updates an existing product, including weight and dimensions. Sets updated_at."""
    conn = None
    if not product_data:
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        product_data['updated_at'] = now

        valid_columns = [
            'product_name', 'description', 'category', 'language_code',
            'base_unit_price', 'unit_of_measure', 'weight', 'dimensions',
            'is_active', 'updated_at'
        ]

        set_clauses = []
        params = []
        for key, value in product_data.items():
            if key in valid_columns:
                set_clauses.append(f"{key} = ?")
                params.append(value)

        if not set_clauses:
            print("Warning: No valid fields to update in update_product.")
            return False

        params.append(product_id)
        sql = f"UPDATE Products SET {', '.join(set_clauses)} WHERE product_id = ?"

        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_product: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_product(product_id: int) -> bool:
    """Deletes a product. Associated ClientProjectProducts are handled by ON DELETE CASCADE."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Products WHERE product_id = ?", (product_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_product: {e}")
        return False
    finally:
        if conn: conn.close()

# ProductEquivalency functions
def add_product_equivalence(product_id_a: int, product_id_b: int) -> int | None:
    """
    Adds a product equivalence pair.
    Ensures product_id_a < product_id_b to maintain uniqueness.
    Returns equivalence_id of the new or existing record.
    """
    if product_id_a == product_id_b:
        print("Error: Cannot create equivalence for a product with itself.")
        return None

    p_a = min(product_id_a, product_id_b)
    p_b = max(product_id_a, product_id_b)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO ProductEquivalencies (product_id_a, product_id_b) VALUES (?, ?)"
        cursor.execute(sql, (p_a, p_b))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        print(f"IntegrityError: Product equivalence pair ({p_a}, {p_b}) likely already exists.")
        try: # Fetch the ID of the existing pair
            cursor.execute("SELECT equivalence_id FROM ProductEquivalencies WHERE product_id_a = ? AND product_id_b = ?", (p_a, p_b))
            row = cursor.fetchone()
            if row:
                return row['equivalence_id']
            else:
                print(f"Warning: IntegrityError for pair ({p_a}, {p_b}) but could not retrieve existing ID.")
                return None
        except sqlite3.Error as e_select:
            print(f"Database error while trying to retrieve existing equivalence_id for ({p_a}, {p_b}): {e_select}")
            return None
    except sqlite3.Error as e:
        print(f"Database error in add_product_equivalence: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn: conn.close()

def get_equivalent_products(product_id: int) -> list[dict]:
    """
    Retrieves all products equivalent to the given product_id.
    Returns a list of product dictionaries (including weight and dimensions).
    """
    conn = None
    equivalent_product_ids = set()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT product_id_b FROM ProductEquivalencies WHERE product_id_a = ?", (product_id,))
        rows_a = cursor.fetchall()
        for row in rows_a:
            equivalent_product_ids.add(row['product_id_b'])

        cursor.execute("SELECT product_id_a FROM ProductEquivalencies WHERE product_id_b = ?", (product_id,))
        rows_b = cursor.fetchall()
        for row in rows_b:
            equivalent_product_ids.add(row['product_id_a'])

        equivalent_products_details = []
        if equivalent_product_ids:
            for eq_id in equivalent_product_ids:
                prod_details = get_product_by_id(eq_id)
                if prod_details:
                    equivalent_products_details.append(prod_details)
        return equivalent_products_details

    except sqlite3.Error as e:
        print(f"Database error in get_equivalent_products: {e}")
        return []
    finally:
        if conn: conn.close()

def get_all_product_equivalencies() -> list[dict]:
    """
    Retrieves all product equivalencies with product details for both products in the pair.
    Returns a list of dictionaries.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT
                pe.equivalence_id,
                pe.product_id_a,
                pA.product_name AS product_name_a,
                pA.language_code AS language_code_a,
                pA.weight AS weight_a,
                pA.dimensions AS dimensions_a,
                pe.product_id_b,
                pB.product_name AS product_name_b,
                pB.language_code AS language_code_b,
                pB.weight AS weight_b,
                pB.dimensions AS dimensions_b
            FROM ProductEquivalencies pe
            JOIN Products pA ON pe.product_id_a = pA.product_id
            JOIN Products pB ON pe.product_id_b = pB.product_id
            ORDER BY pA.product_name, pB.product_name;
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_product_equivalencies: {e}")
        return []
    finally:
        if conn:
            conn.close()

def remove_product_equivalence(equivalence_id: int) -> bool:
    """
    Deletes a product equivalence by its equivalence_id.
    Returns True if deletion was successful, False otherwise.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ProductEquivalencies WHERE equivalence_id = ?", (equivalence_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in remove_product_equivalence: {e}")
        return False
    finally:
        if conn:
            conn.close()

# ClientProjectProduct functions
def add_product_to_client_or_project(link_data: dict) -> int | None:
    """Links a product to a client or project, calculating total price."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        effective_unit_price = None
        product_info = None

        product_id = link_data.get('product_id')
        product_info = get_product_by_id(product_id)
        if not product_info:
            print(f"Product with ID {product_id} not found.")
            return None

        quantity = link_data.get('quantity', 1)
        unit_price_override = link_data.get('unit_price_override')

        if unit_price_override is not None:
            effective_unit_price = unit_price_override
        else:
            effective_unit_price = product_info.get('base_unit_price')

        if effective_unit_price is None:
            print(f"Warning: effective_unit_price was None for product ID {product_id} (Quantity: {quantity}, Override: {unit_price_override}, Base from DB: {product_info.get('base_unit_price') if product_info else 'N/A'}). Defaulting to 0.0.")
            effective_unit_price = 0.0

        total_price_calculated = quantity * effective_unit_price

        sql = """
            INSERT INTO ClientProjectProducts (
                client_id, project_id, product_id, quantity, unit_price_override, total_price_calculated, added_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            link_data.get('client_id'),
            link_data.get('project_id'),
            product_id,
            quantity,
            link_data.get('unit_price_override'),
            total_price_calculated,
            datetime.utcnow().isoformat() + "Z"
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except TypeError as te:
        print(f"TypeError in add_product_to_client_or_project: {te}")
        print(f"  product_id: {link_data.get('product_id')}")
        print(f"  quantity: {link_data.get('quantity', 1)}")
        print(f"  unit_price_override from link_data: {link_data.get('unit_price_override')}")
        if product_info:
            print(f"  base_unit_price from product_info: {product_info.get('base_unit_price')}")
        else:
            print(f"  product_info was None or not fetched prior to error.")
        print(f"  effective_unit_price at point of error: {effective_unit_price if 'effective_unit_price' in locals() else 'Not yet defined or error before definition'}")
        return None
    except sqlite3.Error as e:
        print(f"Database error in add_product_to_client_or_project: {e}")
        return None
    finally:
        if conn: conn.close()

def get_products_for_client_or_project(client_id: str, project_id: str = None) -> list[dict]:
    """Fetches products for a client, optionally filtered by project_id. Joins with Products."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT cpp.*,
                   p.product_id as product_id_original_lang, p.product_name, p.description as product_description,
                   p.category as product_category, p.base_unit_price, p.unit_of_measure,
                   p.weight, p.dimensions, p.language_code
            FROM ClientProjectProducts cpp
            JOIN Products p ON cpp.product_id = p.product_id
            WHERE cpp.client_id = ?
        """
        params = [client_id]

        if project_id:
            sql += " AND cpp.project_id = ?"
            params.append(project_id)
        else:
            sql += " AND cpp.project_id IS NULL"

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_products_for_client_or_project: {e}")
        return []
    finally:
        if conn: conn.close()

def update_client_project_product(link_id: int, update_data: dict) -> bool:
    """Updates a ClientProjectProduct link. Recalculates total_price if needed."""
    conn = None
    if not update_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM ClientProjectProducts WHERE client_project_product_id = ?", (link_id,))
        current_link = cursor.fetchone()
        if not current_link:
            print(f"ClientProjectProduct link with ID {link_id} not found.")
            return False

        current_link_dict = dict(current_link)
        new_quantity = update_data.get('quantity', current_link_dict['quantity'])
        new_unit_price_override = update_data.get('unit_price_override', current_link_dict['unit_price_override'])

        final_unit_price = new_unit_price_override
        if final_unit_price is None:
            product_info = get_product_by_id(current_link_dict['product_id'])
            if not product_info: return False
            final_unit_price = product_info['base_unit_price']

        update_data['total_price_calculated'] = new_quantity * final_unit_price

        set_clauses = [f"{key} = ?" for key in update_data.keys()]
        params_list = list(update_data.values())
        params_list.append(link_id)

        sql = f"UPDATE ClientProjectProducts SET {', '.join(set_clauses)} WHERE client_project_product_id = ?"
        cursor.execute(sql, params_list)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_client_project_product: {e}")
        return False
    finally:
        if conn: conn.close()

def remove_product_from_client_or_project(link_id: int) -> bool:
    """Removes a product link from a client/project."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM ClientProjectProducts WHERE client_project_product_id = ?"
        cursor.execute(sql, (link_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in remove_product_from_client_or_project: {e}")
        return False
    finally:
        if conn: conn.close()

# Product lookup functions
def get_products_by_name_pattern(pattern: str) -> list[dict] | None:
    """
    Retrieves products where the product_name matches the given pattern (LIKE %pattern%).
    Returns a list of up to 10 matching products as dictionaries, or None on error.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        search_pattern = f"%{pattern}%"
        sql = """
            SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at
            FROM Products
            WHERE product_name LIKE ?
            ORDER BY product_name
            LIMIT 10
        """
        cursor.execute(sql, (search_pattern,))
        rows = cursor.fetchall()

        products = [dict(row) for row in rows]
        return products

    except sqlite3.Error as e:
        print(f"Database error in get_products_by_name_pattern: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_products_for_selection(language_code: str = None, name_pattern: str = None) -> list[dict]:
    """
    Retrieves active products for selection, optionally filtered by language_code
    and/or name_pattern (searches product_name and description).
    Orders by product_name.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql_params = []
        sql_where_clauses = ["is_active = TRUE"]

        if language_code:
            sql_where_clauses.append("language_code = ?")
            sql_params.append(language_code)

        if name_pattern:
            sql_where_clauses.append("(product_name LIKE ? OR description LIKE ?)")
            sql_params.append(name_pattern)
            sql_params.append(name_pattern)

        sql = f"""
            SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at
            FROM Products
            WHERE {' AND '.join(sql_where_clauses)}
            ORDER BY product_name
        """

        cursor.execute(sql, tuple(sql_params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_products_for_selection: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_all_products_for_selection_filtered(language_code: str = None, name_pattern: str = None) -> list[dict]:
    """
    Retrieves active products for selection, optionally filtered by language_code
    and/or name_pattern (searches product_name and description).
    Orders by product_name.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql_params = []
        sql_where_clauses = ["is_active = TRUE"]

        if language_code:
            sql_where_clauses.append("language_code = ?")
            sql_params.append(language_code)

        if name_pattern:
            sql_where_clauses.append("(product_name LIKE ? OR description LIKE ?)")
            sql_params.append(name_pattern)
            sql_params.append(name_pattern)

        sql = f"""
            SELECT product_id, product_name, description, base_unit_price, language_code
            FROM Products
            WHERE {' AND '.join(sql_where_clauses)}
            ORDER BY product_name
        """

        cursor.execute(sql, tuple(sql_params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_products_for_selection_filtered: {e}")
        return []
    finally:
        if conn:
            conn.close()
