"""
CRUD (Create, Read, Update, Delete) operations for the InternalStockItems table.

This module provides functions to manage internal stock items, including adding,
retrieving, updating, and soft-deleting items.
"""
import sqlite3
import uuid
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from .generic_crud import _manage_conn, object_to_dict

logger = logging.getLogger(__name__)

class InternalStockItemsCRUD:
    """
    Manages CRUD operations for the InternalStockItems table.
    """

    @_manage_conn
    def add_item(self, conn: sqlite3.Connection, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adds a new internal stock item to the database.

        Args:
            conn: The database connection object.
            item_data: A dictionary containing the item's details.
                Required key: 'item_name' (str).
                Optional keys: 'item_code' (str), 'description' (str), 'category' (str),
                               'manufacturer' (str), 'supplier' (str), 'unit_of_measure' (str),
                               'current_stock_level' (int), 'custom_fields' (dict or JSON str).

        Returns:
            A dictionary with 'success' (bool) and either 'id' (str, the new item_id)
            or 'error' (str) message.
        """
        cursor = conn.cursor()
        item_id = str(uuid.uuid4())
        current_time = datetime.utcnow().isoformat()

        if not item_data.get('item_name'):
            return {'success': False, 'error': 'Item name is required.'}

        custom_fields_str = None
        if 'custom_fields' in item_data:
            if isinstance(item_data['custom_fields'], dict):
                custom_fields_str = json.dumps(item_data['custom_fields'])
            elif isinstance(item_data['custom_fields'], str):
                # Assume it's a valid JSON string, or let DB handle error if not
                custom_fields_str = item_data['custom_fields']
            else:
                return {'success': False, 'error': 'custom_fields must be a dictionary or a JSON string.'}

        sql = """
            INSERT INTO InternalStockItems (
                item_id, item_name, item_code, description, category, manufacturer,
                supplier, unit_of_measure, current_stock_level, custom_fields,
                is_deleted, deleted_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            item_id,
            item_data['item_name'],
            item_data.get('item_code'),
            item_data.get('description'),
            item_data.get('category'),
            item_data.get('manufacturer'),
            item_data.get('supplier'),
            item_data.get('unit_of_measure'),
            item_data.get('current_stock_level', 0),
            custom_fields_str,
            0, # is_deleted
            None, # deleted_at
            current_time,
            current_time
        )
        try:
            cursor.execute(sql, params)
            conn.commit()
            logger.info(f"Internal stock item added successfully: {item_id} - {item_data['item_name']}")
            return {'success': True, 'id': item_id}
        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error adding internal stock item: {e}. Data: {item_data}", exc_info=True)
            if "UNIQUE constraint failed: InternalStockItems.item_code" in str(e):
                return {'success': False, 'error': f"Item code '{item_data.get('item_code')}' already exists."}
            return {'success': False, 'error': f"Database integrity error: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error adding internal stock item: {e}. Data: {item_data}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def get_item_by_id(self, conn: sqlite3.Connection, item_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetches an internal stock item by its item_id.

        Args:
            conn: The database connection object.
            item_id: The UUID string of the item.
            include_deleted: If True, includes items even if they are soft-deleted.

        Returns:
            A dictionary representing the item if found, otherwise None.
            Returns None on error as well, with error logged.
        """
        cursor = conn.cursor()
        sql = "SELECT * FROM InternalStockItems WHERE item_id = ?"
        params = [item_id]
        if not include_deleted:
            sql += " AND is_deleted = 0"

        try:
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
            if row:
                item = object_to_dict(row)
                if item.get('custom_fields'): # Attempt to parse JSON
                    try:
                        item['custom_fields'] = json.loads(item['custom_fields'])
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse custom_fields JSON for item {item_id}: {item['custom_fields']}")
                        # Keep as string if parsing fails
                return item
            return None
        except Exception as e:
            logger.error(f"Error getting internal stock item by ID {item_id}: {e}", exc_info=True)
            return None

    @_manage_conn
    def get_item_by_code(self, conn: sqlite3.Connection, item_code: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetches an internal stock item by its unique item_code.

        Args:
            conn: The database connection object.
            item_code: The item code.
            include_deleted: If True, includes items even if they are soft-deleted.

        Returns:
            A dictionary representing the item if found, otherwise None.
        """
        cursor = conn.cursor()
        sql = "SELECT * FROM InternalStockItems WHERE item_code = ?"
        params = [item_code]
        if not include_deleted:
            sql += " AND is_deleted = 0"

        try:
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
            if row:
                item = object_to_dict(row)
                if item.get('custom_fields'):
                    try:
                        item['custom_fields'] = json.loads(item['custom_fields'])
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse custom_fields JSON for item code {item_code}: {item['custom_fields']}")
                return item
            return None
        except Exception as e:
            logger.error(f"Error getting internal stock item by code {item_code}: {e}", exc_info=True)
            return None

    @_manage_conn
    def get_items(self, conn: sqlite3.Connection, filters: Optional[Dict[str, Any]] = None,
                  limit: Optional[int] = None, offset: int = 0, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        Retrieves multiple internal stock items with optional filtering and pagination.

        Args:
            conn: The database connection object.
            filters: A dictionary of filters to apply.
                     Valid keys: 'category', 'item_name' (for LIKE '%value%'), 'manufacturer', 'supplier'.
            limit: Maximum number of items to return.
            offset: Number of items to skip for pagination.
            include_deleted: If True, includes soft-deleted items.

        Returns:
            A list of dictionaries, where each dictionary represents an item.
            Returns an empty list if no items match or an error occurs.
        """
        cursor = conn.cursor()
        sql = "SELECT * FROM InternalStockItems"
        where_clauses = []
        params = []

        if not include_deleted:
            where_clauses.append("is_deleted = 0")

        if filters:
            if 'category' in filters:
                where_clauses.append("category = ?")
                params.append(filters['category'])
            if 'item_name' in filters: # Partial match for item_name
                where_clauses.append("item_name LIKE ?")
                params.append(f"%{filters['item_name']}%")
            if 'manufacturer' in filters:
                where_clauses.append("manufacturer = ?")
                params.append(filters['manufacturer'])
            if 'supplier' in filters:
                where_clauses.append("supplier = ?")
                params.append(filters['supplier'])

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY item_name ASC" # Default ordering
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        if offset > 0: # LIMIT must be present for OFFSET to work in SQLite if not using -1 for limit
            if limit is None:
                sql += " LIMIT -1" # SQLite specific: -1 means no limit, but allows OFFSET
            sql += " OFFSET ?"
            params.append(offset)

        try:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            items = []
            for row in rows:
                item = object_to_dict(row)
                if item.get('custom_fields'):
                    try:
                        item['custom_fields'] = json.loads(item['custom_fields'])
                    except json.JSONDecodeError:
                         logger.warning(f"Could not parse custom_fields for item {item.get('item_id')}")
                items.append(item)
            return items
        except Exception as e:
            logger.error(f"Error getting internal stock items: {e}. Filters: {filters}", exc_info=True)
            return []

    @_manage_conn
    def update_item(self, conn: sqlite3.Connection, item_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates an existing internal stock item.

        Args:
            conn: The database connection object.
            item_id: The UUID string of the item to update.
            update_data: A dictionary containing fields to update.
                         Allowed fields: 'item_name', 'item_code', 'description', 'category',
                                         'manufacturer', 'supplier', 'unit_of_measure',
                                         'current_stock_level', 'custom_fields',
                                         'is_deleted', 'deleted_at'.

        Returns:
            A dictionary with 'success' (bool) and 'error' (str, if any).
        """
        cursor = conn.cursor()
        current_time = datetime.utcnow().isoformat()

        fields_to_update = []
        values = []

        allowed_fields = [
            'item_name', 'item_code', 'description', 'category', 'manufacturer',
            'supplier', 'unit_of_measure', 'current_stock_level', 'custom_fields',
            'is_deleted', 'deleted_at'
        ]

        for key, value in update_data.items():
            if key in allowed_fields:
                if key == 'custom_fields':
                    if isinstance(value, dict):
                        fields_to_update.append("custom_fields = ?")
                        values.append(json.dumps(value))
                    elif isinstance(value, str) or value is None: # Allow setting to null or pre-formatted JSON
                        fields_to_update.append("custom_fields = ?")
                        values.append(value)
                    else:
                        return {'success': False, 'error': 'custom_fields must be a dictionary, JSON string, or None.'}
                else:
                    fields_to_update.append(f"{key} = ?")
                    values.append(value)

        if not fields_to_update:
            return {'success': False, 'error': 'No valid fields provided for update.'}

        fields_to_update.append("updated_at = ?")
        values.append(current_time)
        values.append(item_id)

        sql = f"UPDATE InternalStockItems SET {', '.join(fields_to_update)} WHERE item_id = ?"

        try:
            cursor.execute(sql, tuple(values))
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning(f"No internal stock item found with ID {item_id} to update, or data was the same.")
                return {'success': False, 'error': 'Item not found or no changes made.'}
            logger.info(f"Internal stock item updated successfully: {item_id}")
            return {'success': True}
        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error updating item {item_id}: {e}. Data: {update_data}", exc_info=True)
            if "UNIQUE constraint failed: InternalStockItems.item_code" in str(e):
                return {'success': False, 'error': f"Item code '{update_data.get('item_code')}' already exists for another item."}
            return {'success': False, 'error': f"Database integrity error: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error updating item {item_id}: {e}. Data: {update_data}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def delete_item(self, conn: sqlite3.Connection, item_id: str) -> Dict[str, Any]:
        """
        Soft deletes an internal stock item by setting is_deleted = 1 and recording deleted_at.

        Args:
            conn: The database connection object.
            item_id: The UUID string of the item to soft delete.

        Returns:
            A dictionary with 'success' (bool) and 'error' (str, if any).
        """
        update_data = {
            "is_deleted": 1,
            "deleted_at": datetime.utcnow().isoformat()
        }
        # Use the existing update_item method to perform the soft delete
        # This ensures 'updated_at' is also handled correctly.
        result = self.update_item(item_id=item_id, update_data=update_data, conn_passed=conn)
        if result['success']:
            logger.info(f"Internal stock item soft-deleted: {item_id}")
        else:
            # update_item already logs, but we can add context
            logger.warning(f"Soft delete failed for item {item_id}, underlying update error: {result.get('error')}")
        return result

    @_manage_conn
    def get_total_items_count(self, conn: sqlite3.Connection, include_deleted: bool = False) -> int:
        """
        Counts the total number of internal stock items.

        Args:
            conn: The database connection object.
            include_deleted: If True, counts all items including soft-deleted ones.

        Returns:
            The total count of items, or 0 if an error occurs.
        """
        cursor = conn.cursor()
        sql = "SELECT COUNT(*) FROM InternalStockItems"
        if not include_deleted:
            sql += " WHERE is_deleted = 0"

        try:
            cursor.execute(sql)
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            logger.error(f"Error getting total items count: {e}", exc_info=True)
            return 0

# Instantiate the CRUD class for easy import and use
internal_stock_items_crud_instance = InternalStockItemsCRUD()

# Expose functions for direct import if preferred
add_item = internal_stock_items_crud_instance.add_item
get_item_by_id = internal_stock_items_crud_instance.get_item_by_id
get_item_by_code = internal_stock_items_crud_instance.get_item_by_code
get_items = internal_stock_items_crud_instance.get_items
update_item = internal_stock_items_crud_instance.update_item
delete_item = internal_stock_items_crud_instance.delete_item
get_total_items_count = internal_stock_items_crud_instance.get_total_items_count
