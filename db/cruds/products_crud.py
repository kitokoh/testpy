import sqlite3
from datetime import datetime
from .generic_crud import GenericCRUD, _manage_conn, get_db_connection # Updated import
import logging
from typing import Dict, Any, Optional, List # Added List for type hinting

# product_media_links_crud is likely needed, ensure it's available.
# If it's in the same directory, the import should be fine.
# Otherwise, adjust the import path as necessary.
from . import product_media_links_crud
import os

class ProductsCRUD(GenericCRUD):
    """
    Manages CRUD operations for products, including their dimensions, equivalencies,
    and media links. Handles soft deletion for products.
    Inherits from GenericCRUD for basic product operations.
    """
    def __init__(self):
        """
        Initializes the ProductsCRUD class.
        Sets table_name and id_column for GenericCRUD, and initializes
        a reference to the product_media_links_crud module.
        """
        self.table_name = "Products"
        self.id_column = "product_id"
        # Assuming product_media_links_crud is a module with functions.
        # If it were a class, instantiation might be `product_media_links_crud.ProductMediaLinksCRUD()`.
        self.media_links_crud = product_media_links_crud

    @_manage_conn
    def add_product(self, product_data: dict, conn: sqlite3.Connection = None) -> dict:
        """
        Adds a new product to the database.

        Validates required fields ('product_name', 'product_code', 'base_unit_price') and 'base_unit_price' type.
        Sets 'is_deleted' to 0 and 'is_active' to True by default for new products.

        Args:
            product_data (dict): Data for the new product. Expected keys include:
                                 'product_name', 'product_code', 'base_unit_price',
                                 'description' (optional), 'category' (optional),
                                 'language_code' (optional, default 'fr'),
                                 'unit_of_measure' (optional), 'weight' (optional),
                                 'dimensions' (optional), 'is_active' (optional, default True).
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'id': new_product_id} on success,
                  {'success': False, 'error': 'message'} on failure.
        """
        logging.info(f"products_crud.add_product: Attempting to add product with data: {product_data}")
        required_fields = ['product_name', 'product_code', 'base_unit_price']
        for field in required_fields:
            if not product_data.get(field): # Also checks for empty string for product_code implicitly here
                logging.error(f"Missing required field: {field} in add_product")
                return {'success': False, 'error': f"Missing required field: {field}"}

        if not isinstance(product_data['base_unit_price'], (int, float)):
            logging.error("Invalid data type for base_unit_price in add_product")
            return {'success': False, 'error': "Invalid data type for base_unit_price. Must be a number."}

        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"

        # Add is_deleted and deleted_at with default values
        product_data['is_deleted'] = product_data.get('is_deleted', 0) # Default to not deleted
        product_data['deleted_at'] = product_data.get('deleted_at', None)


        sql = """INSERT INTO Products
                 (product_name, product_code, description, category, language_code, base_unit_price,
                  unit_of_measure, weight, dimensions, is_active, created_at, updated_at,
                  is_deleted, deleted_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (product_data.get('product_name'), product_data.get('product_code'),
                  product_data.get('description'), product_data.get('category'),
                  product_data.get('language_code', 'fr'), product_data.get('base_unit_price'),
                  product_data.get('unit_of_measure'), product_data.get('weight'),
                  product_data.get('dimensions'), product_data.get('is_active', True),
                  now, now, product_data.get('is_deleted', 0), product_data.get('deleted_at', None))
        try:
            cursor.execute(sql, params)
            new_id = cursor.lastrowid
            return {'success': True, 'id': new_id}
        except sqlite3.IntegrityError as e: # Specific integrity error
            logging.error(f"products_crud.add_product: Failed to add product with data {product_data}. Error: {type(e).__name__} - {e}", exc_info=True)
            # More specific error message for unique constraint violation can be useful
            if "UNIQUE constraint failed" in str(e):
                 return {'success': False, 'error': f"Product name, code, or other unique field already exists: {str(e)}"}
            return {'success': False, 'error': f"Database integrity error: {str(e)}"}
        except sqlite3.Error as e_gen: # Generic SQLite error
            logging.error(f"products_crud.add_product: Failed to add product with data {product_data}. Error: {type(e_gen).__name__} - {e_gen}", exc_info=True)
            return {'success': False, 'error': str(e_gen)}

    @_manage_conn
    def get_product_by_id(self, product_id: int, conn: sqlite3.Connection = None, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetches a single product by its ID, along with its media links.
        Uses the generic get_by_id and then enhances with product-specific details.

        Args:
            product_id (int): The ID of the product to fetch.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted products.
                                              Defaults to False.

        Returns:
            Optional[Dict[str, Any]]: Product data as a dictionary if found and not excluded
                                      by soft delete policy, otherwise None. Includes a 'media_links' key.
        """
        # Use super().get_by_id for the basic fetch
        product_dict = super().get_by_id(table_name=self.table_name, id_column=self.id_column, item_id=product_id, conn=conn)

        if not product_dict:
            return None

        # Handle soft delete check
        if not include_deleted and (product_dict.get('is_deleted') == 1 or product_dict.get('is_deleted') is True):
            return None # Product is soft-deleted and we are not including them

        # Fetch associated media links
        if self.media_links_crud:
             media_links = self.media_links_crud.get_media_links_for_product(product_id=product_id, conn=conn)
             product_dict['media_links'] = media_links
        else:
            product_dict['media_links'] = []

        return product_dict

    @_manage_conn
    def get_product_by_name(self, product_name: str, conn: sqlite3.Connection = None, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetches a single product by its name, along with its media links.

        Args:
            product_name (str): The name of the product to fetch.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted products.
                                              Defaults to False.

        Returns:
            Optional[Dict[str, Any]]: Product data as a dictionary if found and not excluded,
                                      otherwise None. Includes 'media_links'.
        """
        logging.info(f"products_crud.get_product_by_name: Searching for product_name='{product_name}'")
        cursor = conn.cursor()
        sql = f"SELECT * FROM {self.table_name} WHERE product_name = ?"
        params = [product_name]

        # Base query already selects all columns including is_deleted

        try:
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
            if not row:
                return None

            product_dict = dict(row)

            if not include_deleted and (product_dict.get('is_deleted') == 1 or product_dict.get('is_deleted') is True):
                return None # Product is soft-deleted

            product_id = product_dict.get(self.id_column)
            if product_id is not None and self.media_links_crud:
                media_links = self.media_links_crud.get_media_links_for_product(product_id=product_id, conn=conn)
                product_dict['media_links'] = media_links
            else:
                product_dict['media_links'] = []
            logging.info(f"products_crud.get_product_by_name: Found product: {product_dict if product_dict else None}")
            return product_dict
        except sqlite3.Error as e:
            logging.error(f"products_crud.get_product_by_name: DB error for product_name='{product_name}'. Error: {type(e).__name__} - {e}", exc_info=True)
            return None

    @_manage_conn
    def get_all_products(self, filters: dict = None, conn: sqlite3.Connection = None, limit: int = None, offset: int = 0, include_deleted: bool = False, active_only: bool = None) -> list[dict]:
        """
        Retrieves all products, with optional filtering, pagination, and inclusion
        of soft-deleted records. Also supports filtering by active status directly.

        Args:
            filters (dict, optional): Filters to apply (e.g., {'category': 'Electronics'}).
                                      Valid keys: 'category', 'product_name', 'is_active', 'language_code'.
            conn (sqlite3.Connection, optional): Database connection.
            limit (int, optional): Max number of records for pagination.
            offset (int, optional): Offset for pagination. Defaults to 0.
            include_deleted (bool, optional): If True, includes soft-deleted products.
                                              Defaults to False.
            active_only (bool, optional): If True, only active products are returned.
                                          If False, only inactive products.
                                          If None, 'is_active' in filters is used or no active filter.

        Returns:
            list[dict]: A list of product records.
        """
        if active_only is not None:
            if filters is None:
                filters = {}
            filters['is_active'] = bool(active_only)

        cursor = conn.cursor()
        sql = f"SELECT * FROM {self.table_name} p" # Alias table as p for clarity in conditions
        q_params = []

        conditions = []
        if not include_deleted:
            conditions.append("(p.is_deleted IS NULL OR p.is_deleted = 0)")

        if filters:
            valid_filters = ['category', 'product_name', 'is_active', 'language_code', 'product_code_like'] # Added product_code_like
            for k, v in filters.items():
                if k in valid_filters:
                    if k == 'product_name':
                        conditions.append("p.product_name LIKE ?")
                        q_params.append(f"%{v}%")
                    elif k == 'product_code_like': # Added handler for product_code_like
                        conditions.append("p.product_code LIKE ?")
                        q_params.append(f"%{v}%")
                    elif k == 'is_active':
                        # This will now correctly use the value set by active_only if it was provided
                        conditions.append("p.is_active = ?")
                        q_params.append(1 if bool(v) else 0) # Ensure v is treated as boolean
                    else:
                        conditions.append(f"p.{k} = ?")
                        q_params.append(v)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY p.product_name"

        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            q_params.extend([limit, offset])

        try:
            cursor.execute(sql, q_params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting all products with filters '{filters}': {e}")
            return []

    @_manage_conn
    def update_product(self, product_id: int, data: dict, conn: sqlite3.Connection = None) -> dict:
        """
        Updates an existing product's information.

        Validates `product_id` and input data. Handles 'base_unit_price' data type.
        Allows updating soft delete fields `is_deleted` and `deleted_at`.

        Args:
            product_id (int): The ID of the product to update.
            data (dict): Data to update. Keys should correspond to column names.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'updated_count': count} or {'success': False, 'error': 'message'}.
        """
        if not product_id:
             return {'success': False, 'error': "Product ID is required for update."}
        if not data:
             return {'success': False, 'error': "No data provided for update."}

        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        data['updated_at'] = now

        valid_cols = ['product_name', 'product_code', 'description', 'category', 'language_code',
                      'base_unit_price', 'unit_of_measure', 'weight', 'dimensions',
                      'is_active', 'updated_at', 'is_deleted', 'deleted_at']

        to_set = {}
        for k,v in data.items():
            if k in valid_cols:
                if k == 'base_unit_price' and not isinstance(v, (int, float)) and v is not None:
                    logging.error(f"Invalid data type for base_unit_price in update_product for product {product_id}")
                    return {'success': False, 'error': "Invalid data type for base_unit_price."}
                to_set[k] = v

        if not to_set:
            return {'success': False, 'error': "No valid fields to update."}

        set_c = [f"{key}=?" for key in to_set.keys()]
        params = list(to_set.values())
        params.append(product_id)
        sql = f"UPDATE {self.table_name} SET {', '.join(set_c)} WHERE {self.id_column} = ?"

        try:
            cursor.execute(sql, params)
            return {'success': cursor.rowcount > 0, 'updated_count': cursor.rowcount}
        except sqlite3.Error as e:
            logging.error(f"Error updating product {product_id}: {e}")
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def delete_product(self, product_id: int, conn: sqlite3.Connection = None) -> dict:
        """
        Soft deletes a product by setting `is_deleted = 1`, `deleted_at` to current UTC time,
        and `is_active = 0`.

        Args:
            product_id (int): The ID of the product to soft delete.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'message': 'Product soft deleted.'} on success,
                  {'success': False, 'error': 'Product not found or no change made.'} if no update,
                  {'success': False, 'error': 'DB error message'} on database error.
        """
        if not product_id:
            return {'success': False, 'error': "Product ID is required for deletion."}

        now = datetime.utcnow().isoformat() + "Z"
        # Also set is_active to False for soft-deleted products.
        # This is a business rule decision; active products are generally not deleted.
        update_data = {'is_deleted': 1, 'deleted_at': now, 'is_active': 0}

        cursor = conn.cursor()
        sql = f"UPDATE {self.table_name} SET is_deleted = ?, deleted_at = ?, is_active = ? WHERE {self.id_column} = ?"
        params = (1, now, 0, product_id)

        try:
            cursor.execute(sql, params)
            if cursor.rowcount > 0:
                return {'success': True, 'message': f"Product {product_id} soft deleted."}
            else:
                return {'success': False, 'error': f"Product {product_id} not found or no change made."}
        except sqlite3.Error as e:
            logging.error(f"Failed to soft delete product {product_id}: {e}")
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_products(self, language_code: str = None, conn: sqlite3.Connection = None, include_deleted: bool = False) -> list[dict]:
        """
        Retrieves active products, optionally filtered by language code.

        Args:
            language_code (str, optional): Language code to filter products by.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted products.
                                              Defaults to False (only active, non-deleted products).

        Returns:
            list[dict]: A list of product records.
        """
        cursor = conn.cursor()
        sql = f"SELECT * FROM {self.table_name} p"
        params = []
        conditions = ["p.is_active = TRUE"] # Default to active products

        if not include_deleted:
            conditions.append("(p.is_deleted IS NULL OR p.is_deleted = 0)")

        if language_code:
            conditions.append("p.language_code = ?")
            params.append(language_code)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY p.product_name"
        try:
            cursor.execute(sql, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting products (lang: {language_code}): {e}")
            return []

    @_manage_conn
    def update_product_price(self, product_id: int, new_price: float, conn: sqlite3.Connection = None) -> dict:
        """
        Updates the base_unit_price of a specific product.
        Ensures the product exists and is not soft-deleted before updating.

        Args:
            product_id (int): The ID of the product to update.
            new_price (float): The new price.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True} on successful price update,
                  {'success': False, 'error': 'message'} on failure or if product not found/deleted.
        """
        if not isinstance(new_price, (int, float)):
             return {'success': False, 'error': "New price must be a number."}
        # Check if product exists and is not deleted before updating price
        product = self.get_product_by_id(product_id, conn=conn, include_deleted=False) # Ensures we don't update deleted product price
        if not product:
            return {'success': False, 'error': f"Product {product_id} not found or is deleted."}

        now = datetime.utcnow().isoformat() + "Z"
        sql = f"UPDATE {self.table_name} SET base_unit_price = ?, updated_at = ? WHERE {self.id_column} = ?"

        try:
            cursor = conn.cursor()
            cursor.execute(sql, (new_price, now, product_id))
            if cursor.rowcount > 0:
                return {'success': True}
            else:
                return {'success': False, 'error': "Price update failed, product not found or price is the same."} # Should be caught by get_product_by_id
        except sqlite3.Error as e:
            logging.error(f"Error updating price for product {product_id}: {e}")
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_products_by_name_pattern(self, pattern: str, conn: sqlite3.Connection = None, include_deleted: bool = False) -> list[dict] | None:
        """
        Searches for products where the name matches a given pattern (case-insensitive LIKE).
        Limits results to 10.

        Args:
            pattern (str): The pattern to search for in product names.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted products.
                                              Defaults to False.

        Returns:
            list[dict] | None: A list of matching product records, or None on error.
                               Returns empty list if no matches.
        """
        cursor = conn.cursor()
        search_pattern = f"%{pattern}%"
        sql = f"SELECT * FROM {self.table_name} p WHERE p.product_name LIKE ?"
        params = [search_pattern]

        if not include_deleted:
            sql += " AND (p.is_deleted IS NULL OR p.is_deleted = 0)"

        sql += " ORDER BY p.product_name LIMIT 10"
        try:
            cursor.execute(sql, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting products by name pattern '{pattern}': {e}")
            return None # Or an empty list: []

    @_manage_conn
    def get_all_products_for_selection_filtered(self, language_code: str = None, name_pattern: str = None, conn: sqlite3.Connection = None, include_deleted: bool = False) -> list[dict]:
        """
        Retrieves products suitable for selection lists (e.g., in UI dropdowns),
        filtered by language and/or name pattern. Only returns a subset of fields.

        Args:
            language_code (str, optional): Language code to filter by.
            name_pattern (str, optional): Pattern for product name or description.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted products.
                                              Defaults to False.

        Returns:
            list[dict]: List of products with 'product_id', 'product_name', 'description',
                        'base_unit_price', 'language_code'.
        """
        cursor = conn.cursor()
        params = []
        conditions = ["p.is_active = TRUE"] # Start with active products

        if not include_deleted:
            conditions.append("(p.is_deleted IS NULL OR p.is_deleted = 0)")

        if language_code:
            conditions.append("p.language_code = ?")
            params.append(language_code)
        if name_pattern:
            conditions.append("(p.product_name LIKE ? OR p.description LIKE ?)")
            params.extend([f"%{name_pattern}%", f"%{name_pattern}%"])

        sql = f"SELECT p.product_id, p.product_name, p.description, p.base_unit_price, p.language_code FROM {self.table_name} p WHERE {' AND '.join(conditions)} ORDER BY p.product_name"
        try:
            cursor.execute(sql, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error in get_all_products_for_selection_filtered (lang: {language_code}, pattern: {name_pattern}): {e}")
            return []

    @_manage_conn
    def get_total_products_count(self, conn: sqlite3.Connection = None, include_deleted: bool = False) -> int:
        """
        Counts the total number of products.

        Args:
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, count includes soft-deleted products.
                                              Defaults to False.

        Returns:
            int: The total count of products based on the criteria.
        """
        cursor = conn.cursor()
        sql = f"SELECT COUNT({self.id_column}) as total_count FROM {self.table_name} p"
        params = []
        conditions = []

        if not include_deleted:
            conditions.append("(p.is_deleted IS NULL OR p.is_deleted = 0)")

        if conditions: # Though for count, this might always be true if we add more conditions later
            sql += " WHERE " + " AND ".join(conditions)

        try:
            cursor.execute(sql, tuple(params)) # params would be used if conditions had placeholders
            row = cursor.fetchone()
            return row['total_count'] if row else 0
        except sqlite3.Error as e:
            logging.error(f"Error getting total products count: {e}")
            return 0

    # --- ProductDimensions CRUD ---
    @_manage_conn
    def add_or_update_product_dimension(self, product_id: int, dimension_data: dict, conn: sqlite3.Connection = None) -> dict:
        """
        Adds or updates dimensions for a given product.
        The product must exist and not be soft-deleted.

        Args:
            product_id (int): The ID of the product.
            dimension_data (dict): Dictionary of dimension fields (dim_A, dim_B, etc.)
                                   and 'technical_image_path'.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'operation': 'inserted'/'updated', 'product_id': id} on success,
                  {'success': False, 'error': 'message'} on failure.
        """
        # First, check if the product exists and is not deleted
        product = self.get_product_by_id(product_id, conn=conn, include_deleted=False)
        if not product:
            return {'success': False, 'error': f"Product {product_id} not found or is deleted. Cannot add/update dimensions."}

        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        try:
            cursor.execute("SELECT product_id FROM ProductDimensions WHERE product_id = ?", (product_id,))
            exists = cursor.fetchone()
            dim_cols = ['dim_A','dim_B','dim_C','dim_D','dim_E','dim_F','dim_G','dim_H','dim_I','dim_J','technical_image_path']

            if exists:
                data_to_set = {k:v for k,v in dimension_data.items() if k in dim_cols}
                if not data_to_set:
                    cursor.execute("UPDATE ProductDimensions SET updated_at = ? WHERE product_id = ?", (now, product_id))
                    return {'success': True, 'operation': 'timestamp_updated'}
                data_to_set['updated_at'] = now
                set_c = [f"{k}=?" for k in data_to_set.keys()]
                params_list = list(data_to_set.values())
                params_list.append(product_id)
                sql_update = f"UPDATE ProductDimensions SET {', '.join(set_c)} WHERE product_id = ?"
                cursor.execute(sql_update, params_list)
                op = 'updated'
            else:
                cols = ['product_id','created_at','updated_at'] + [col for col in dim_cols if col in dimension_data]
                vals = [product_id, now, now] + [dimension_data.get(c) for c in dim_cols if c in dimension_data]
                placeholders = ','.join(['?']*len(cols))
                sql_insert = f"INSERT INTO ProductDimensions ({','.join(cols)}) VALUES ({placeholders})"
                cursor.execute(sql_insert, tuple(vals))
                op = 'inserted'

            success = cursor.rowcount > 0 or (not exists and cursor.lastrowid is not None)
            return {'success': success, 'operation': op, 'product_id': product_id}
        except sqlite3.Error as e:
            logging.error(f"Error in add_or_update_product_dimension for product {product_id}: {e}")
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_product_dimension(self, product_id: int, conn: sqlite3.Connection = None, include_deleted_product: bool = False) -> dict | None:
        """
        Retrieves dimensions for a specific product.

        Args:
            product_id (int): The ID of the product.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted_product (bool, optional): If True, allows fetching dimensions
                                                      for a product that is soft-deleted.
                                                      Defaults to False.

        Returns:
            dict | None: Dimension data as a dictionary if found, otherwise None.
                         Returns None if the parent product is soft-deleted and
                         `include_deleted_product` is False.
        """
        # Check product soft delete status first, unless explicitly asked to include
        if not include_deleted_product:
            product = self.get_product_by_id(product_id, conn=conn, include_deleted=False)
            if not product: # Product is soft-deleted or does not exist
                 logging.warning(f"Product {product_id} not found or is soft-deleted. Cannot fetch dimensions by default.")
                 return None
        # If include_deleted_product is True, or product was found (not soft-deleted), proceed.
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM ProductDimensions WHERE product_id = ?", (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logging.error(f"Error getting product dimension for product {product_id}: {e}")
            return None

    @_manage_conn
    def delete_product_dimension(self, product_id: int, conn: sqlite3.Connection = None) -> dict:
        """
        Deletes dimensions for a given product_id.
        This is a hard delete of the dimension data. It does not check the soft-delete
        status of the parent product, allowing dimensions to be removed even if the
        product is soft-deleted (e.g., for data cleanup).

        Args:
            product_id (int): The ID of the product whose dimensions are to be deleted.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'message': 'Dimensions deleted.'} on success,
                  {'success': False, 'error': 'Dimensions not found.'} if no dimensions existed,
                  {'success': False, 'error': 'DB error message'} on database error.
        """
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM ProductDimensions WHERE product_id = ?", (product_id,))
            if cursor.rowcount > 0:
                return {'success': True, 'message': f"Dimensions for product {product_id} deleted."}
            else:
                return {'success': False, 'error': f"Dimensions for product {product_id} not found."}
        except sqlite3.Error as e:
            logging.error(f"Error deleting product dimension for product {product_id}: {e}")
            return {'success': False, 'error': str(e)}

    # --- ProductEquivalencies CRUD ---
    @_manage_conn
    def add_product_equivalence(self, product_id_a: int, product_id_b: int, conn: sqlite3.Connection = None) -> dict:
        """
        Adds an equivalence link between two products.
        Both products must exist and not be soft-deleted.
        The order of product_id_a and product_id_b is normalized (min, max) to prevent duplicates.

        Args:
            product_id_a (int): ID of the first product.
            product_id_b (int): ID of the second product.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'id': equivalence_id, 'message' (optional)} on success,
                  {'success': False, 'error': 'message'} on failure.
        """
        if product_id_a == product_id_b:
            logging.warning("Cannot create equivalence for a product with itself.")
            return {'success': False, 'error': "Cannot create equivalence for a product with itself."}

        # Check if both products exist and are not soft-deleted
        prod_a = self.get_product_by_id(product_id_a, conn=conn, include_deleted=False)
        prod_b = self.get_product_by_id(product_id_b, conn=conn, include_deleted=False)

        if not prod_a:
            return {'success': False, 'error': f"Product {product_id_a} not found or is deleted."}
        if not prod_b:
            return {'success': False, 'error': f"Product {product_id_b} not found or is deleted."}

        p_a, p_b = min(product_id_a, product_id_b), max(product_id_a, product_id_b) # Normalize order
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO ProductEquivalencies (product_id_a, product_id_b) VALUES (?,?)", (p_a,p_b))
            return {'success': True, 'id': cursor.lastrowid}
        except sqlite3.IntegrityError:
            try:
                cursor.execute("SELECT equivalence_id FROM ProductEquivalencies WHERE product_id_a = ? AND product_id_b = ?", (p_a,p_b))
                row=cursor.fetchone()
                logging.warning(f"Equivalence between {p_a} and {p_b} already exists.")
                return {'success': True, 'id': row['equivalence_id'] if row else None, 'message': "Equivalence already exists."}
            except sqlite3.Error as e_fetch:
                logging.error(f"Error fetching existing equivalence for {p_a}-{p_b}: {e_fetch}")
                return {'success': False, 'error': f"Error fetching existing equivalence: {str(e_fetch)}"}
        except sqlite3.Error as e:
            logging.error(f"Error adding product equivalence for {p_a}-{p_b}: {e}")
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_equivalent_products(self, product_id: int, conn: sqlite3.Connection = None, include_deleted: bool = False) -> list[dict]:
        """
        Retrieves all products equivalent to a given product.
        The main product's existence and soft-delete status are checked first.
        Equivalent products that are soft-deleted are filtered out by default.

        Args:
            product_id (int): The ID of the product to find equivalents for.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted equivalent products.
                                              Defaults to False.

        Returns:
            list[dict]: A list of product records for equivalent products.
        """
        # First check if the main product exists and is not deleted (unless `include_deleted` is True for the main product itself)
        main_product = self.get_product_by_id(product_id, conn=conn, include_deleted=include_deleted)
        if not main_product:
            logging.warning(f"Main product {product_id} not found or is (soft-)deleted as per include_deleted flag. Cannot fetch equivalents.")
            return []

        cursor = conn.cursor(); ids = set()
        try:
            cursor.execute("SELECT product_id_b FROM ProductEquivalencies WHERE product_id_a = ?", (product_id,))
            for row in cursor.fetchall(): ids.add(row['product_id_b'])
            cursor.execute("SELECT product_id_a FROM ProductEquivalencies WHERE product_id_b = ?", (product_id,))
            for row in cursor.fetchall(): ids.add(row['product_id_a'])
            ids.discard(product_id)

            if not ids: return []

            placeholders = ','.join('?'*len(ids))
            # Fetch products and then filter by soft delete status
            sql = f"SELECT * FROM {self.table_name} p WHERE p.{self.id_column} IN ({placeholders})"

            # This sub-query approach for filtering by is_deleted is not straightforward with IN.
            # Fetch all, then filter in Python:
            cursor.execute(sql, tuple(ids))
            all_equivalent_products = [dict(row) for row in cursor.fetchall()]

            if include_deleted:
                return all_equivalent_products
            else:
                return [p for p in all_equivalent_products if not (p.get('is_deleted') == 1 or p.get('is_deleted') is True)]

        except sqlite3.Error as e:
            logging.error(f"Error getting equivalent products for product {product_id}: {e}")
            return []

    @_manage_conn
    def get_all_product_equivalencies(self, conn: sqlite3.Connection = None, include_deleted_products: bool = False) -> list[dict]:
        """
        Retrieves all product equivalency links, along with details of the linked products.
        Allows filtering out links where one or both products are soft-deleted.

        Args:
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted_products (bool, optional): If True, includes equivalencies even if
                                                       one or both linked products are soft-deleted.
                                                       Defaults to False.

        Returns:
            list[dict]: A list of equivalency records with product details.
        """
        cursor = conn.cursor()
        sql = """SELECT pe.*,
                 pA.product_name AS product_name_a, pA.language_code AS language_code_a,
                 pA.weight AS weight_a, pA.dimensions AS dimensions_a, pA.is_deleted AS pA_is_deleted,
                 pB.product_name AS product_name_b, pB.language_code AS language_code_b,
                 pB.weight AS weight_b, pB.dimensions AS dimensions_b, pB.is_deleted AS pB_is_deleted
                 FROM ProductEquivalencies pe
                 JOIN Products pA ON pe.product_id_a = pA.product_id
                 JOIN Products pB ON pe.product_id_b = pB.product_id
              """

        conditions = []
        if not include_deleted_products: # If we are NOT including deleted products, then both must be active
            conditions.append("(pA.is_deleted IS NULL OR pA.is_deleted = 0)")
            conditions.append("(pB.is_deleted IS NULL OR pB.is_deleted = 0)")

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY pA.product_name, pB.product_name"

        try:
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting all product equivalencies: {e}")
            return []

    @_manage_conn
    def remove_product_equivalence(self, equivalence_id: int, conn: sqlite3.Connection = None) -> dict:
        """
        Removes a product equivalency link by its ID. This is a hard delete of the link.

        Args:
            equivalence_id (int): The ID of the equivalency link to remove.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'message': 'Equivalence removed.'} on success,
                  {'success': False, 'error': 'Equivalence not found.'} if no link matched,
                  {'success': False, 'error': 'DB error message'} on database error.
        """
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM ProductEquivalencies WHERE equivalence_id = ?", (equivalence_id,))
            if cursor.rowcount > 0:
                return {'success': True, 'message': f"Equivalence {equivalence_id} removed."}
            else:
                 return {'success': False, 'error': f"Equivalence {equivalence_id} not found."}
        except sqlite3.Error as e:
            logging.error(f"Error removing product equivalence {equivalence_id}: {e}")
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_product_by_code(self, product_code: str, conn: sqlite3.Connection = None, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetches a single product by its product_code, along with its media links.

        Args:
            product_code (str): The product_code of the product to fetch.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted products.
                                              Defaults to False.

        Returns:
            Optional[Dict[str, Any]]: Product data as a dictionary if found and not excluded,
                                      otherwise None. Includes 'media_links'.
        """
        cursor = conn.cursor()
        sql = f"SELECT * FROM {self.table_name} WHERE product_code = ?"
        params = [product_code]

        try:
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
            if not row:
                return None

            product_dict = dict(row)

            if not include_deleted and (product_dict.get('is_deleted') == 1 or product_dict.get('is_deleted') is True):
                return None # Product is soft-deleted

            product_id = product_dict.get(self.id_column)
            if product_id is not None and self.media_links_crud:
                media_links = self.media_links_crud.get_media_links_for_product(product_id=product_id, conn=conn)
                product_dict['media_links'] = media_links
            else:
                product_dict['media_links'] = []

            return product_dict
        except sqlite3.Error as e:
            logging.error(f"Error getting product by code '{product_code}': {e}")
            return None

# Instantiate the CRUD class for easy import and use elsewhere
products_crud_instance = ProductsCRUD()

# Expose methods as module-level functions
get_product_by_id = products_crud_instance.get_product_by_id
add_product = products_crud_instance.add_product
get_product_by_name = products_crud_instance.get_product_by_name
get_product_by_code = products_crud_instance.get_product_by_code
get_all_products = products_crud_instance.get_all_products
update_product = products_crud_instance.update_product
delete_product = products_crud_instance.delete_product
get_products = products_crud_instance.get_products
update_product_price = products_crud_instance.update_product_price
get_products_by_name_pattern = products_crud_instance.get_products_by_name_pattern
get_all_products_for_selection_filtered = products_crud_instance.get_all_products_for_selection_filtered
get_total_products_count = products_crud_instance.get_total_products_count
add_or_update_product_dimension = products_crud_instance.add_or_update_product_dimension
get_product_dimension = products_crud_instance.get_product_dimension
delete_product_dimension = products_crud_instance.delete_product_dimension
add_product_equivalence = products_crud_instance.add_product_equivalence
get_equivalent_products = products_crud_instance.get_equivalent_products
get_all_product_equivalencies = products_crud_instance.get_all_product_equivalencies
remove_product_equivalence = products_crud_instance.remove_product_equivalence

__all__ = [
    "get_product_by_id",
    "add_product",
    "get_product_by_name",
    "get_all_products",
    "update_product",
    "delete_product", # Soft delete
    "get_products", # Active products, optionally by lang
    "update_product_price",
    "get_products_by_name_pattern",
    "get_all_products_for_selection_filtered",
    "get_total_products_count",
    "add_or_update_product_dimension",
    "get_product_dimension",
    "delete_product_dimension",
    "add_product_equivalence",
    "get_equivalent_products",
    "get_all_product_equivalencies",
    "remove_product_equivalence",
    "get_product_by_code", # Added new function
    "ProductsCRUD", # Exporting the class itself for type hinting or direct instantiation
    "products_crud_instance" # Exporting the instance if needed elsewhere
]
