import sqlite3
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Assuming _manage_conn is in a shared utility or generic_crud.py
# Adjust the import path as necessary based on your project structure.
# For now, let's assume it's in a module accessible like this:
from .generic_crud import _manage_conn, object_to_dict

# Setup logger
logger = logging.getLogger(__name__)

class ItemLocationsCRUD:
    """
    CRUD operations for ItemLocations and ProductStorageLocations tables.
    """

    # --- ItemLocations Table Operations ---

    @_manage_conn
    def add_item_location(self, conn: sqlite3.Connection, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adds a new item location.
        Requires: location_name
        Optional: parent_location_id, location_type, description, visual_coordinates
        """
        cursor = conn.cursor()
        location_id = str(uuid.uuid4())
        current_time = datetime.utcnow().isoformat()

        required_fields = ['location_name']
        if not all(field in location_data for field in required_fields):
            return {'success': False, 'error': 'Missing required fields (location_name).'}

        try:
            cursor.execute("""
                INSERT INTO ItemLocations (
                    location_id, location_name, parent_location_id, location_type,
                    description, visual_coordinates, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                location_id,
                location_data['location_name'],
                location_data.get('parent_location_id'),
                location_data.get('location_type'),
                location_data.get('description'),
                location_data.get('visual_coordinates'),
                current_time,
                current_time
            ))
            conn.commit()
            new_location = self.get_item_location_by_id(location_id=location_id, conn_passed=conn)
            if new_location['success']:
                return {'success': True, 'data': new_location['data']}
            else:
                # This case should ideally not happen if insert was successful
                return {'success': True, 'data': {'location_id': location_id, **location_data}}
        except sqlite3.IntegrityError as e:
            logger.error(f"Error adding item location: {e}")
            return {'success': False, 'error': f"Database integrity error: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error adding item location: {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def get_item_location_by_id(self, conn: sqlite3.Connection, location_id: str) -> Dict[str, Any]:
        """Fetches a location by its ID."""
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM ItemLocations WHERE location_id = ?", (location_id,))
            location = cursor.fetchone()
            if location:
                return {'success': True, 'data': object_to_dict(location)}
            else:
                return {'success': False, 'error': 'ItemLocation not found.'}
        except Exception as e:
            logger.error(f"Error getting item location by ID {location_id}: {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def get_item_locations_by_parent_id(self, conn: sqlite3.Connection, parent_location_id: Optional[str]) -> Dict[str, Any]:
        """Fetches all locations under a given parent. If parent_location_id is None, fetches top-level locations."""
        cursor = conn.cursor()
        try:
            if parent_location_id is None:
                cursor.execute("SELECT * FROM ItemLocations WHERE parent_location_id IS NULL ORDER BY location_name")
            else:
                cursor.execute("SELECT * FROM ItemLocations WHERE parent_location_id = ? ORDER BY location_name", (parent_location_id,))
            locations = cursor.fetchall()
            return {'success': True, 'data': [object_to_dict(loc) for loc in locations]}
        except Exception as e:
            logger.error(f"Error getting item locations by parent ID {parent_location_id}: {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def get_all_item_locations(self, conn: sqlite3.Connection, location_type: Optional[str] = None) -> Dict[str, Any]:
        """Fetches all locations, optionally filtered by location_type."""
        cursor = conn.cursor()
        try:
            if location_type:
                cursor.execute("SELECT * FROM ItemLocations WHERE location_type = ? ORDER BY location_name", (location_type,))
            else:
                cursor.execute("SELECT * FROM ItemLocations ORDER BY location_name")
            locations = cursor.fetchall()
            return {'success': True, 'data': [object_to_dict(loc) for loc in locations]}
        except Exception as e:
            logger.error(f"Error getting all item locations (type: {location_type}): {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def update_item_location(self, conn: sqlite3.Connection, location_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates a location's details."""
        cursor = conn.cursor()
        current_time = datetime.utcnow().isoformat()

        fields_to_update = []
        values = []

        for key, value in update_data.items():
            if key in ['location_name', 'parent_location_id', 'location_type', 'description', 'visual_coordinates']:
                fields_to_update.append(f"{key} = ?")
                values.append(value)

        if not fields_to_update:
            return {'success': False, 'error': 'No valid fields provided for update.'}

        fields_to_update.append("updated_at = ?")
        values.append(current_time)
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
            logger.error(f"Error deleting item location {location_id}: {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    # --- ProductStorageLocations Table Operations ---

    @_manage_conn
    def link_product_to_location(self, conn: sqlite3.Connection, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Links a product to an item location.
        Requires: product_id, location_id
        Optional: quantity, notes
        """
        cursor = conn.cursor()
        psl_id = str(uuid.uuid4())
        current_time = datetime.utcnow().isoformat()

        required_fields = ['product_id', 'location_id']
        if not all(field in data for field in required_fields):
            return {'success': False, 'error': 'Missing required fields (product_id, location_id).'}

        try:
            cursor.execute("""
                INSERT INTO ProductStorageLocations (
                    product_storage_location_id, product_id, location_id,
                    quantity, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                psl_id,
                data['product_id'],
                data['location_id'],
                data.get('quantity'),
                data.get('notes'),
                current_time,
                current_time
            ))
            conn.commit()
            # Fetch the newly created link to return its full data
            new_link = self.get_product_storage_location_by_id(psl_id=psl_id, conn_passed=conn)
            if new_link['success']:
                return {'success': True, 'data': new_link['data']}
            else:
                 return {'success': True, 'data': {'product_storage_location_id': psl_id, **data }}
        except sqlite3.IntegrityError as e:
            logger.error(f"Error linking product to location: {e}")
            if "UNIQUE constraint failed: ProductStorageLocations.product_id, ProductStorageLocations.location_id" in str(e):
                return {'success': False, 'error': 'This product is already linked to this location.'}
            return {'success': False, 'error': f"Database integrity error: {e}. Check if product and location exist."}
        except Exception as e:
            logger.error(f"Unexpected error linking product to location: {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def get_product_storage_location_by_id(self, conn: sqlite3.Connection, psl_id: str) -> Dict[str, Any]:
        """Fetches a specific product-location link by its ID."""
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM ProductStorageLocations WHERE product_storage_location_id = ?", (psl_id,))
            link = cursor.fetchone()
            if link:
                return {'success': True, 'data': object_to_dict(link)}
            else:
                return {'success': False, 'error': 'ProductStorageLocation not found.'}
        except Exception as e:
            logger.error(f"Error fetching product storage location by ID {psl_id}: {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def get_locations_for_product(self, conn: sqlite3.Connection, product_id: int) -> Dict[str, Any]:
        """
        Fetches all locations where a specific product is stored, including quantity and notes.
        Joins with ItemLocations to provide location details.
        """
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    psl.product_storage_location_id, psl.product_id, psl.location_id,
                    psl.quantity, psl.notes, psl.created_at AS psl_created_at, psl.updated_at AS psl_updated_at,
                    il.location_name, il.location_type, il.description AS location_description,
                    il.parent_location_id, il.visual_coordinates
                FROM ProductStorageLocations psl
                JOIN ItemLocations il ON psl.location_id = il.location_id
                WHERE psl.product_id = ?
                ORDER BY il.location_name
            """, (product_id,))
            results = cursor.fetchall()
            return {'success': True, 'data': [object_to_dict(row) for row in results]}
        except Exception as e:
            logger.error(f"Error getting locations for product {product_id}: {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def get_products_in_location(self, conn: sqlite3.Connection, location_id: str) -> Dict[str, Any]:
        """
        Fetches all products stored in a specific location, including quantity and notes.
        Joins with Products to provide product details.
        """
        cursor = conn.cursor()
        try:
            # Ensure Products table has product_name and product_code, adjust if necessary
            cursor.execute("""
                SELECT
                    psl.product_storage_location_id, psl.product_id, psl.location_id,
                    psl.quantity, psl.notes, psl.created_at AS psl_created_at, psl.updated_at AS psl_updated_at,
                    p.product_name, p.product_code, p.description AS product_description, p.category AS product_category
                FROM ProductStorageLocations psl
                JOIN Products p ON psl.product_id = p.product_id
                WHERE psl.location_id = ?
                ORDER BY p.product_name
            """, (location_id,))
            results = cursor.fetchall()
            return {'success': True, 'data': [object_to_dict(row) for row in results]}
        except Exception as e:
            logger.error(f"Error getting products in location {location_id}: {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def update_product_in_location(self, conn: sqlite3.Connection, psl_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates details of a product in a location (e.g., quantity, notes)."""
        cursor = conn.cursor()
        current_time = datetime.utcnow().isoformat()

        fields_to_update = []
        values = []

        # Only quantity and notes are typically updatable for a link.
        # product_id and location_id changes would mean deleting this link and creating a new one.
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
        values.append(psl_id)

        sql = f"UPDATE ProductStorageLocations SET {', '.join(fields_to_update)} WHERE product_storage_location_id = ?"

        try:
            cursor.execute(sql, tuple(values))
            conn.commit()
            if cursor.rowcount == 0:
                return {'success': False, 'error': 'ProductStorageLocation not found or no changes made.'}

            updated_link = self.get_product_storage_location_by_id(psl_id=psl_id, conn_passed=conn)
            return updated_link
        except sqlite3.IntegrityError as e: # Should not happen for quantity/notes update
            logger.error(f"Error updating product in location link {psl_id}: {e}")
            return {'success': False, 'error': f"Database integrity error: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error updating product in location link {psl_id}: {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def unlink_product_from_location(self, conn: sqlite3.Connection, psl_id: str) -> Dict[str, Any]:
        """Removes a product from a location by the ProductStorageLocation ID."""
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM ProductStorageLocations WHERE product_storage_location_id = ?", (psl_id,))
            conn.commit()
            if cursor.rowcount > 0:
                return {'success': True, 'data': {'message': 'Product unlinked from location successfully.'}}
            else:
                return {'success': False, 'error': 'ProductStorageLocation link not found.'}
        except Exception as e:
            logger.error(f"Error unlinking product from location (ID: {psl_id}): {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    @_manage_conn
    def unlink_product_from_specific_location(self, conn: sqlite3.Connection, product_id: int, location_id: str) -> Dict[str, Any]:
        """Removes a product from a specific location using their respective IDs."""
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM ProductStorageLocations
                WHERE product_id = ? AND location_id = ?
            """, (product_id, location_id))
            conn.commit()
            if cursor.rowcount > 0:
                return {'success': True, 'data': {'message': 'Product unlinked from specific location successfully.'}}
            else:
                return {'success': False, 'error': 'Link not found for the given product_id and location_id.'}
        except Exception as e:
            logger.error(f"Error unlinking product {product_id} from location {location_id}: {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}

    # --- Helper functions ---

    def _get_location_path_recursive(self, conn: sqlite3.Connection, location_id: str, path_list: List[str]) -> None:
        """ Helper to recursively fetch parent location names. """
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
        """
        path_list = []
        try:
            self._get_location_path_recursive(conn, location_id, path_list)
            if not path_list:
                 # This could happen if the initial location_id is invalid or has no name
                loc_details = self.get_item_location_by_id(location_id=location_id, conn_passed=conn)
                if loc_details['success'] and loc_details['data']:
                    path_list.append(loc_details['data'].get('location_name', 'Unknown Location'))
                else: # location_id is not valid
                    return {'success': False, 'error': f"Location ID {location_id} not found or invalid."}

            return {'success': True, 'data': " > ".join(path_list)}
        except Exception as e:
            logger.error(f"Error generating full location path for {location_id}: {e}")
            return {'success': False, 'error': f"An unexpected error occurred while generating path: {e}"}

    @_manage_conn
    def get_product_in_specific_location(self, conn: sqlite3.Connection, product_id: int, location_id: str) -> Dict[str, Any]:
        """
        Checks if a product already exists at a location and get its details.
        """
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM ProductStorageLocations
                WHERE product_id = ? AND location_id = ?
            """, (product_id, location_id))
            link_data = cursor.fetchone()
            if link_data:
                return {'success': True, 'data': object_to_dict(link_data)}
            else:
                return {'success': True, 'data': None} # Success, but no data found
        except Exception as e:
            logger.error(f"Error checking product {product_id} in location {location_id}: {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {e}"}


# Instantiate the CRUD class for easy import and use
item_locations_crud_instance = ItemLocationsCRUD()

# For easier direct import of functions if preferred by parts of the application
add_item_location = item_locations_crud_instance.add_item_location
get_item_location_by_id = item_locations_crud_instance.get_item_location_by_id
get_item_locations_by_parent_id = item_locations_crud_instance.get_item_locations_by_parent_id
get_all_item_locations = item_locations_crud_instance.get_all_item_locations
update_item_location = item_locations_crud_instance.update_item_location
delete_item_location = item_locations_crud_instance.delete_item_location

link_product_to_location = item_locations_crud_instance.link_product_to_location
get_product_storage_location_by_id = item_locations_crud_instance.get_product_storage_location_by_id
get_locations_for_product = item_locations_crud_instance.get_locations_for_product
get_products_in_location = item_locations_crud_instance.get_products_in_location
update_product_in_location = item_locations_crud_instance.update_product_in_location
unlink_product_from_location = item_locations_crud_instance.unlink_product_from_location
unlink_product_from_specific_location = item_locations_crud_instance.unlink_product_from_specific_location

# New helper functions exposed
get_full_location_path_str = item_locations_crud_instance.get_full_location_path_str
get_product_in_specific_location = item_locations_crud_instance.get_product_in_specific_location

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
