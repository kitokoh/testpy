"""
CRUD (Create, Read, Update, Delete) operations for managing item storage locations
and the products stored within them.

This module provides functions to interact with the `ItemLocations` and
`ProductStorageLocations` tables in the database. It handles the creation,
retrieval, modification, and deletion of location records, as well as linking
products to these locations with details like quantity and notes.
Helper functions for tasks like resolving full location paths are also included.
"""
import sqlite3
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Assuming _manage_conn is in a shared utility or generic_crud.py
# Adjust the import path as necessary based on your project structure.
# For now, let's assume it's in a module accessible like this:
from .generic_crud import _manage_conn, object_to_dict

# Setup logger for this module
logger = logging.getLogger(__name__)

class ItemLocationsCRUD:
    """
    Provides CRUD operations for both ItemLocations and ProductStorageLocations tables.

    ItemLocations store hierarchical information about physical or logical storage spaces.
    ProductStorageLocations links products (from the Products table) to these ItemLocations,
    specifying quantity and any relevant notes for that specific product-location pairing.
    """

    # --- ItemLocations Table Operations ---

    @_manage_conn
    def add_item_location(self, conn: sqlite3.Connection, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adds a new item location to the database.

        Args:
            conn: The database connection object.
            location_data: A dictionary containing the location's details.
                Required key: 'location_name' (str).
                Optional keys: 'parent_location_id' (str, UUID of parent),
                               'location_type' (str, e.g., "Shelf", "Area"),
                               'description' (str),
                               'visual_coordinates' (str, JSON string for UI representation).

        Returns:
            A dictionary with 'success' (bool) and either 'data' (dict of the new location)
            or 'error' (str) message.
        """
        cursor = conn.cursor()
        location_id = str(uuid.uuid4())  # Generate a new UUID for the location
        current_time = datetime.utcnow().isoformat()

        required_fields = ['location_name']
        if not all(field in location_data for field in required_fields):
            logger.warning(f"add_item_location: Missing required fields. Data: {location_data}")
            return {'success': False, 'error': 'Missing required fields (location_name).'}

        try:
            # Prepare SQL query for insertion
            sql = """
                INSERT INTO ItemLocations (
                    location_id, location_name, parent_location_id, location_type,
                    description, visual_coordinates, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                location_id,
                location_data['location_name'],
                location_data.get('parent_location_id'), # Optional: can be None
                location_data.get('location_type'),      # Optional
                location_data.get('description'),        # Optional
                location_data.get('visual_coordinates'), # Optional
                current_time,
                current_time
            )
            cursor.execute(sql, params)
            conn.commit()

            # Fetch and return the newly created location data
            fetch_result = self.get_item_location_by_id(location_id=location_id, conn_passed=conn)
            if fetch_result['success']:
                logger.info(f"Successfully added item location: {location_id} - {location_data['location_name']}")
                return {'success': True, 'data': fetch_result['data']}
            else:
                # This case implies get_item_location_by_id failed right after a successful insert,
                # which is unlikely but handled. Return raw inserted data as fallback.
                logger.warning(f"Added item location {location_id}, but failed to retrieve it back. Error: {fetch_result.get('error')}")
                return {'success': True, 'data': {'location_id': location_id, **location_data}}
        except sqlite3.IntegrityError as e:
            logger.error(f"Error adding item location due to integrity constraint (e.g., duplicate name if unique, FK issue): {e}. Data: {location_data}")
            return {'success': False, 'error': f"Database integrity error: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error adding item location: {e}. Data: {location_data}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def get_item_location_by_id(self, conn: sqlite3.Connection, location_id: str) -> Dict[str, Any]:
        """
        Fetches a specific item location by its unique ID.

        Args:
            conn: The database connection object.
            location_id: The UUID string of the location to retrieve.

        Returns:
            A dictionary with 'success' (bool) and 'data' (dict of location details if found)
            or 'error' (str) message if not found or an error occurs.
        """
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM ItemLocations WHERE location_id = ?", (location_id,))
            location_row = cursor.fetchone()
            if location_row:
                return {'success': True, 'data': object_to_dict(location_row)}
            else:
                logger.info(f"ItemLocation with ID {location_id} not found.")
                return {'success': False, 'error': 'ItemLocation not found.'}
        except Exception as e:
            logger.error(f"Error getting item location by ID {location_id}: {e}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def get_item_locations_by_parent_id(self, conn: sqlite3.Connection, parent_location_id: Optional[str]) -> Dict[str, Any]:
        """
        Fetches all item locations that are direct children of a given parent location.
        If parent_location_id is None, it fetches all top-level locations (those without a parent).

        Args:
            conn: The database connection object.
            parent_location_id: The UUID string of the parent location, or None for top-level locations.

        Returns:
            A dictionary with 'success' (bool) and 'data' (list of location dicts)
            or 'error' (str) message. The list is empty if no matching locations are found.
        """
        cursor = conn.cursor()
        try:
            if parent_location_id is None:
                # Query for top-level locations
                cursor.execute("SELECT * FROM ItemLocations WHERE parent_location_id IS NULL ORDER BY location_name")
            else:
                # Query for children of the specified parent
                cursor.execute("SELECT * FROM ItemLocations WHERE parent_location_id = ? ORDER BY location_name", (parent_location_id,))
            locations_rows = cursor.fetchall()
            return {'success': True, 'data': [object_to_dict(loc) for loc in locations_rows]}
        except Exception as e:
            logger.error(f"Error getting item locations by parent ID {parent_location_id}: {e}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def get_all_item_locations(self, conn: sqlite3.Connection, location_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches all item locations, optionally filtering by location type.

        Args:
            conn: The database connection object.
            location_type: Optional string to filter locations by their type (e.g., "Shelf").

        Returns:
            A dictionary with 'success' (bool) and 'data' (list of location dicts)
            or 'error' (str) message.
        """
        cursor = conn.cursor()
        try:
            sql = "SELECT * FROM ItemLocations"
            params = []
            if location_type:
                sql += " WHERE location_type = ?"
                params.append(location_type)
            sql += " ORDER BY location_name"

            cursor.execute(sql, tuple(params))
            locations_rows = cursor.fetchall()
            return {'success': True, 'data': [object_to_dict(loc) for loc in locations_rows]}
        except Exception as e:
            logger.error(f"Error getting all item locations (type: {location_type}): {e}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def update_item_location(self, conn: sqlite3.Connection, location_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates an existing item location's details.

        Args:
            conn: The database connection object.
            location_id: The UUID string of the location to update.
            update_data: A dictionary containing the fields to update and their new values.
                         Allowed keys: 'location_name', 'parent_location_id', 'location_type',
                                       'description', 'visual_coordinates'.

        Returns:
            A dictionary with 'success' (bool) and 'data' (dict of the updated location)
            or 'error' (str) message.
        """
        cursor = conn.cursor()
        current_time = datetime.utcnow().isoformat()

        fields_to_update = []
        values = []

        # Whitelist fields that can be updated
        allowed_fields = ['location_name', 'parent_location_id', 'location_type', 'description', 'visual_coordinates']
        for key, value in update_data.items():
            if key in allowed_fields:
                fields_to_update.append(f"{key} = ?")
                values.append(value)

        if not fields_to_update:
            logger.warning(f"update_item_location: No valid fields provided for update. Location ID: {location_id}, Data: {update_data}")
            return {'success': False, 'error': 'No valid fields provided for update.'}

        # Always update the 'updated_at' timestamp
        fields_to_update.append("updated_at = ?")
        values.append(current_time)

        # Add location_id to the end of values for the WHERE clause
        values.append(location_id)

        sql = f"UPDATE ItemLocations SET {', '.join(fields_to_update)} WHERE location_id = ?"

        try:
            cursor.execute(sql, tuple(values))
            conn.commit()
            if cursor.rowcount == 0:
                return {'success': False, 'error': 'ItemLocation not found or no changes made.'}

            updated_location = self.get_item_location_by_id(location_id=location_id, conn_passed=conn)
            return updated_location # This already wraps in success/data or error
        except sqlite3.IntegrityError as e:
            logger.error(f"Error updating item location {location_id}: {e}")
            return {'success': False, 'error': f"Database integrity error: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error updating item location {location_id}: {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def delete_item_location(self, conn: sqlite3.Connection, location_id: str) -> Dict[str, Any]:
        """
        Deletes a location.
        Prevents deletion if child locations exist.
        ProductStorageLocations linked are handled by ON DELETE CASCADE.
        """
        cursor = conn.cursor()
        try:
            # Check for child locations
            children_check = self.get_item_locations_by_parent_id(parent_location_id=location_id, conn_passed=conn)
            if children_check['success'] and children_check['data']:
                return {'success': False, 'error': 'Cannot delete location with child locations. Re-parent or delete children first.'}

            cursor.execute("DELETE FROM ItemLocations WHERE location_id = ?", (location_id,))
            conn.commit()
            if cursor.rowcount > 0:
                return {'success': True, 'data': {'message': 'ItemLocation deleted successfully.'}}
            else:
                return {'success': False, 'error': 'ItemLocation not found.'}
        except sqlite3.IntegrityError as e:
            # This might occur if other direct FK constraints exist that are not ON DELETE CASCADE
            logger.error(f"Integrity error deleting item location {location_id}: {e}")
            return {'success': False, 'error': f"Database integrity error: {e}. Check for related data."}
        except Exception as e:
            logger.error(f"Error deleting item location {location_id}: {e}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    # --- ItemStorageLocations Table Operations (Formerly ProductStorageLocations) ---

    @_manage_conn
    def link_item_to_location(self, conn: sqlite3.Connection, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Links an internal stock item to an item location.

        Args:
            conn: The database connection object.
            data: A dictionary containing the link details.
                Required keys: 'item_id' (str, UUID of InternalStockItem),
                               'location_id' (str, UUID of ItemLocation).
                Optional keys: 'quantity' (int), 'notes' (str).

        Returns:
            A dictionary with 'success' (bool) and 'data' (dict of the new link)
            or 'error' (str) message.
        """
        cursor = conn.cursor()
        isl_id = str(uuid.uuid4()) # Unique ID for the item-storage-location link
        current_time = datetime.utcnow().isoformat()

        required_fields = ['item_id', 'location_id']
        if not all(field in data for field in required_fields):
            logger.warning(f"link_item_to_location: Missing required fields. Data: {data}")
            return {'success': False, 'error': 'Missing required fields (item_id, location_id).'}

        try:
            sql = """
                INSERT INTO ItemStorageLocations (
                    item_storage_location_id, item_id, location_id,
                    quantity, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                isl_id,
                data['item_id'],
                data['location_id'],
                data.get('quantity'),
                data.get('notes'),
                current_time,
                current_time
            )
            cursor.execute(sql, params)
            conn.commit()

            new_link = self.get_item_storage_location_by_id(isl_id=isl_id, conn_passed=conn)
            if new_link['success']:
                logger.info(f"Successfully linked item {data['item_id']} to location {data['location_id']}. Link ID: {isl_id}")
                return {'success': True, 'data': new_link['data']}
            else:
                 logger.warning(f"Linked item {data['item_id']} to location {data['location_id']}, but failed to retrieve it back. Link ID: {isl_id}")
                 return {'success': True, 'data': {'item_storage_location_id': isl_id, **data }}
        except sqlite3.IntegrityError as e:
            logger.error(f"Error linking item to location due to integrity constraint: {e}. Data: {data}", exc_info=True)
            if "UNIQUE constraint failed: ItemStorageLocations.item_id, ItemStorageLocations.location_id" in str(e):
                return {'success': False, 'error': 'This item is already linked to this location.'}
            return {'success': False, 'error': f"Database integrity error: {e}. Check if item and location exist."}
        except Exception as e:
            logger.error(f"Unexpected error linking item to location: {e}. Data: {data}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def get_item_storage_location_by_id(self, conn: sqlite3.Connection, isl_id: str) -> Dict[str, Any]:
        """
        Fetches a specific item-location link by its unique ID.

        Args:
            conn: The database connection object.
            isl_id: The UUID string of the ItemStorageLocation link.

        Returns:
            A dictionary with 'success' (bool) and 'data' (dict of link details if found)
            or 'error' (str) message.
        """
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM ItemStorageLocations WHERE item_storage_location_id = ?", (isl_id,))
            link_row = cursor.fetchone()
            if link_row:
                return {'success': True, 'data': object_to_dict(link_row)}
            else:
                return {'success': False, 'error': 'ItemStorageLocation not found.'}
        except Exception as e:
            logger.error(f"Error fetching item storage location by ID {isl_id}: {e}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def get_locations_for_item(self, conn: sqlite3.Connection, item_id: str) -> Dict[str, Any]:
        """
        Fetches all locations where a specific internal stock item is stored.
        Includes quantity, notes, and joins with ItemLocations for location details.

        Args:
            conn: The database connection object.
            item_id: The UUID string of the InternalStockItem.

        Returns:
            A dictionary with 'success' (bool) and 'data' (list of dicts, each merging
            ItemStorageLocations and ItemLocations details) or 'error' (str).
        """
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    isl.item_storage_location_id, isl.item_id, isl.location_id,
                    isl.quantity, isl.notes, isl.created_at AS isl_created_at, isl.updated_at AS isl_updated_at,
                    il.location_name, il.location_type, il.description AS location_description,
                    il.parent_location_id, il.visual_coordinates
                FROM ItemStorageLocations isl
                JOIN ItemLocations il ON isl.location_id = il.location_id
                WHERE isl.item_id = ?
                ORDER BY il.location_name
            """, (item_id,))
            results = cursor.fetchall()
            return {'success': True, 'data': [object_to_dict(row) for row in results]}
        except Exception as e:
            logger.error(f"Error getting locations for item {item_id}: {e}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def get_items_in_location(self, conn: sqlite3.Connection, location_id: str) -> Dict[str, Any]:
        """
        Fetches all internal stock items stored in a specific location.
        Includes quantity, notes, and joins with InternalStockItems for item details.

        Args:
            conn: The database connection object.
            location_id: The UUID string of the ItemLocation.

        Returns:
            A dictionary with 'success' (bool) and 'data' (list of dicts, each merging
            ItemStorageLocations and InternalStockItems details) or 'error' (str).
        """
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    isl.item_storage_location_id, isl.item_id, isl.location_id,
                    isl.quantity, isl.notes, isl.created_at AS isl_created_at, isl.updated_at AS isl_updated_at,
                    isi.item_name, isi.item_code, isi.description AS item_description, isi.category AS item_category,
                    isi.manufacturer, isi.supplier, isi.unit_of_measure
                FROM ItemStorageLocations isl
                JOIN InternalStockItems isi ON isl.item_id = isi.item_id
                WHERE isl.location_id = ?
                ORDER BY isi.item_name
            """, (location_id,))
            results = cursor.fetchall()
            return {'success': True, 'data': [object_to_dict(row) for row in results]}
        except Exception as e:
            logger.error(f"Error getting items in location {location_id}: {e}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def update_item_in_location(self, conn: sqlite3.Connection, isl_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates details (quantity, notes) of an item in a specific location link.

        Args:
            conn: The database connection object.
            isl_id: The UUID string of the ItemStorageLocation link to update.
            update_data: A dictionary with fields to update.
                         Allowed keys: 'quantity' (int), 'notes' (str).

        Returns:
            A dictionary with 'success' (bool) and 'data' (dict of the updated link)
            or 'error' (str) message.
        """
        cursor = conn.cursor()
        current_time = datetime.utcnow().isoformat()

        fields_to_update = []
        values = []

        if 'quantity' in update_data:
            fields_to_update.append("quantity = ?")
            values.append(update_data['quantity'])
        if 'notes' in update_data:
            fields_to_update.append("notes = ?")
            values.append(update_data['notes'])

        if not fields_to_update:
            return {'success': False, 'error': 'No valid fields (quantity, notes) provided for update.'}

        fields_to_update.append("updated_at = ?")
        values.append(current_time)
        values.append(isl_id)

        sql = f"UPDATE ItemStorageLocations SET {', '.join(fields_to_update)} WHERE item_storage_location_id = ?"

        try:
            cursor.execute(sql, tuple(values))
            conn.commit()
            if cursor.rowcount == 0:
                return {'success': False, 'error': 'ItemStorageLocation not found or no changes made.'}
            logger.info(f"Successfully updated item link {isl_id}.")
            updated_link = self.get_item_storage_location_by_id(isl_id=isl_id, conn_passed=conn)
            return updated_link
        except sqlite3.IntegrityError as e:
            logger.error(f"Error updating item in location link {isl_id}: {e}", exc_info=True)
            return {'success': False, 'error': f"Database integrity error: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error updating item in location link {isl_id}: {e}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def unlink_item_from_location(self, conn: sqlite3.Connection, isl_id: str) -> Dict[str, Any]:
        """
        Removes an item-location link by its ItemStorageLocation ID.

        Args:
            conn: The database connection object.
            isl_id: The UUID string of the ItemStorageLocation link to delete.

        Returns:
            A dictionary with 'success' (bool) and 'data' (message) or 'error' (str).
        """
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM ItemStorageLocations WHERE item_storage_location_id = ?", (isl_id,))
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Successfully unlinked item (ISL ID: {isl_id}).")
                return {'success': True, 'data': {'message': 'Item unlinked from location successfully.'}}
            else:
                return {'success': False, 'error': 'ItemStorageLocation link not found.'}
        except Exception as e:
            logger.error(f"Error unlinking item from location (ISL ID: {isl_id}): {e}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def unlink_item_from_specific_location(self, conn: sqlite3.Connection, item_id: str, location_id: str) -> Dict[str, Any]:
        """
        Removes an item-location link using the item ID and location ID.

        Args:
            conn: The database connection object.
            item_id: The UUID string of the InternalStockItem.
            location_id: The UUID string of the ItemLocation.

        Returns:
            A dictionary with 'success' (bool) and 'data' (message) or 'error' (str).
        """
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM ItemStorageLocations
                WHERE item_id = ? AND location_id = ?
            """, (item_id, location_id))
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Successfully unlinked item {item_id} from location {location_id}.")
                return {'success': True, 'data': {'message': 'Item unlinked from specific location successfully.'}}
            else:
                return {'success': False, 'error': 'Link not found for the given item_id and location_id.'}
        except Exception as e:
            logger.error(f"Error unlinking item {item_id} from location {location_id}: {e}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    # --- Helper functions --- (get_full_location_path_str remains relevant for ItemLocations)

    def _get_location_path_recursive(self, conn: sqlite3.Connection, location_id: str, path_list: List[str]) -> None:
        """
        Internal helper to recursively fetch parent location names to build a path.
        This method expects an active database connection and cursor to be managed by the caller,
        or by the outer function decorated with @_manage_conn.

        Args:
            conn: The *already open* database connection object.
            location_id: The ID of the current location in the recursion.
            path_list: A list to which location names are prepended.
        """
        # This method is called internally by get_full_location_path_str,
        # which is @_manage_conn decorated. So, `conn` is valid.
        cursor = conn.cursor()
        # Fetch current location's name and parent_id
        # Ensure this part does not call a @_manage_conn decorated function to avoid nested connection issues
        # if called from within another @_manage_conn decorated function using the same conn_passed.
        # Direct execution on the passed cursor is fine.
        current_location_query = "SELECT location_name, parent_location_id FROM ItemLocations WHERE location_id = ?"
        cursor.execute(current_location_query, (location_id,))
        current_loc = cursor.fetchone()

        if current_loc:
            path_list.insert(0, current_loc['location_name']) # Prepend current location name
            if current_loc['parent_location_id']:
                self._get_location_path_recursive(conn, current_loc['parent_location_id'], path_list)
        # If location_id is not found, it simply won't add to path_list, effectively stopping recursion for that branch.

    @_manage_conn
    def get_full_location_path_str(self, conn: sqlite3.Connection, location_id: str) -> Dict[str, Any]:
        """
        Builds a human-readable path string for a location (e.g., "Main Area > Storage Unit 1 > Shelf B").
        The path is constructed by traversing up the parent_location_id references.

        Args:
            conn: The database connection object.
            location_id: The UUID string of the location for which to get the full path.

        Returns:
            A dictionary with 'success' (bool) and 'data' (the path string)
            or 'error' (str) if the location_id is invalid or an error occurs.
        """
        path_list = []
        try:
            self._get_location_path_recursive(conn, location_id, path_list)

            # If path_list is empty after recursion, it means the initial location_id was not found
            # or had no name. Try to get its name directly if it exists.
            if not path_list:
                loc_details = self.get_item_location_by_id(location_id=location_id, conn_passed=conn)
                if loc_details['success'] and loc_details['data']:
                    path_list.append(loc_details['data'].get('location_name', 'Unknown Location'))
                else: # location_id is indeed not valid or inaccessible
                    logger.warning(f"get_full_location_path_str: Initial location ID {location_id} not found.")
                    return {'success': False, 'error': f"Location ID {location_id} not found or invalid."}

            return {'success': True, 'data': " > ".join(path_list)}
        except Exception as e:
            logger.error(f"Error generating full location path for {location_id}: {e}", exc_info=True)
            return {'success': False, 'error': f"An unexpected error occurred while generating path: {e}"}

    @_manage_conn
    def get_item_in_specific_location(self, conn: sqlite3.Connection, item_id: str, location_id: str) -> Dict[str, Any]: # Renamed product_id to item_id (TEXT)
        """
        Checks if a specific internal stock item exists at a specific location and retrieves its details.

        Args:
            conn: The database connection object.
            item_id: The UUID string of the InternalStockItem.
            location_id: The UUID string of the ItemLocation.

        Returns:
            A dictionary with 'success' (bool) and 'data' (dict of link details if found, else None)
            or 'error' (str) message.
        """
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM ItemStorageLocations
                WHERE item_id = ? AND location_id = ?
            """, (item_id, location_id)) # Updated table name
            link_row = cursor.fetchone()
            if link_row:
                return {'success': True, 'data': object_to_dict(link_row)}
            else:
                return {'success': True, 'data': None} # Success, but no data found
        except Exception as e:
            logger.error(f"Error checking item {item_id} in location {location_id}: {e}", exc_info=True) # Updated log
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}


# Instantiate the CRUD class for easy import and use
item_locations_crud_instance = ItemLocationsCRUD()

# For easier direct import of functions if preferred by parts of the application
# ItemLocation specific CRUDs
add_item_location = item_locations_crud_instance.add_item_location
get_item_location_by_id = item_locations_crud_instance.get_item_location_by_id
get_item_locations_by_parent_id = item_locations_crud_instance.get_item_locations_by_parent_id
get_all_item_locations = item_locations_crud_instance.get_all_item_locations
update_item_location = item_locations_crud_instance.update_item_location
delete_item_location = item_locations_crud_instance.delete_item_location

# ItemStorageLocation specific CRUDs (formerly ProductStorageLocation)
link_item_to_location = item_locations_crud_instance.link_item_to_location # Renamed
get_item_storage_location_by_id = item_locations_crud_instance.get_item_storage_location_by_id # Renamed
get_locations_for_item = item_locations_crud_instance.get_locations_for_item # Renamed
get_items_in_location = item_locations_crud_instance.get_items_in_location # Renamed
update_item_in_location = item_locations_crud_instance.update_item_in_location # Renamed
unlink_item_from_location = item_locations_crud_instance.unlink_item_from_location # Renamed
unlink_item_from_specific_location = item_locations_crud_instance.unlink_item_from_specific_location # Renamed

# Helper functions
get_full_location_path_str = item_locations_crud_instance.get_full_location_path_str
get_item_in_specific_location = item_locations_crud_instance.get_item_in_specific_location # Renamed

if __name__ == '__main__':
    # This section is for basic testing and example usage.
    # It requires a database to be set up (e.g., via init_schema.py)
    # and generic_crud.py to be in the correct path.
    # You would also need to configure the DB_PATH for _manage_conn.
    # For now, this will likely not run directly without project context.

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.info("ItemLocationsCRUD module direct execution (for testing - requires DB setup).")

    # Example Usage (Illustrative - requires DB_PATH in generic_crud or config)
    # Ensure your generic_crud._get_db_connection() can find the database.
    # from db.database_manager import DB_PATH, set_db_path # Assuming you have this
    # set_db_path("your_db_name.db") # Set your actual DB path here for testing

    # --- Test ItemLocations ---
    # 1. Add a location
    # new_loc_data = {'location_name': 'Main Warehouse Area 1', 'location_type': 'Area'}
    # result = add_item_location(location_data=new_loc_data)
    # logger.info(f"Add Location: {result}")
    #
    # if result['success']:
    #     loc_id = result['data']['location_id']
    #
    #     # 2. Get location by ID
    #     get_result = get_item_location_by_id(location_id=loc_id)
    #     logger.info(f"Get Location by ID: {get_result}")
    #
    #     # 3. Add a child location
    #     child_loc_data = {'location_name': 'Shelf A1', 'parent_location_id': loc_id, 'location_type': 'Shelf'}
    #     child_result = add_item_location(location_data=child_loc_data)
    #     logger.info(f"Add Child Location: {child_result}")
    #
    #     # 4. Get locations by parent ID
    #     children = get_item_locations_by_parent_id(parent_location_id=loc_id)
    #     logger.info(f"Children of {loc_id}: {children}")
    #
    #     # 5. Get top-level locations
    #     top_level = get_item_locations_by_parent_id(parent_location_id=None)
    #     logger.info(f"Top Level Locations: {top_level}")
    #
    #     # 6. Update location
    #     update_res = update_item_location(location_id=loc_id, update_data={'description': 'Primary storage area'})
    #     logger.info(f"Update Location: {update_res}")
    #
    # --- Test ProductStorageLocations (requires existing product_id) ---
    # Assuming product_id = 1 exists from Products table
    # product_id_example = 1
    # if result['success'] and child_result['success']:
    #     shelf_id = child_result['data']['location_id']
    #
    #     # 7. Link product to location
    #     link_data = {'product_id': product_id_example, 'location_id': shelf_id, 'quantity': 100, 'notes': 'Stocked items'}
    #     link_res = link_product_to_location(data=link_data)
    #     logger.info(f"Link Product to Location: {link_res}")
    #
    #     if link_res['success']:
    #         psl_id_example = link_res['data']['product_storage_location_id']
    #
    #         # 8. Get locations for product
    #         prod_locs = get_locations_for_product(product_id=product_id_example)
    #         logger.info(f"Locations for Product {product_id_example}: {prod_locs}")
    #
    #         # 9. Get products in location
    #         loc_prods = get_products_in_location(location_id=shelf_id)
    #         logger.info(f"Products in Shelf {shelf_id}: {loc_prods}")
    #
    #         # 10. Update product in location
    #         update_link_res = update_product_in_location(psl_id=psl_id_example, update_data={'quantity': 95, 'notes': 'Updated stock count'})
    #         logger.info(f"Update Product in Location: {update_link_res}")
    #
    #         # 11. Unlink product from location by PSL ID
    #         # unlink_res = unlink_product_from_location(psl_id=psl_id_example)
    #         # logger.info(f"Unlink Product (by PSL ID): {unlink_res}")
    #
    #         # 12. Or Unlink product from specific location by product_id and location_id
    #         # unlink_specific_res = unlink_product_from_specific_location(product_id=product_id_example, location_id=shelf_id)
    #         # logger.info(f"Unlink Product (specific): {unlink_specific_res}")
    #
    #     # Clean up (optional, careful with real data)
    #     # if child_result['success']:
    #     #     delete_item_location(location_id=child_result['data']['location_id'])
    #     # delete_item_location(location_id=loc_id)

    pass
