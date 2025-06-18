import sqlite3
import uuid
import logging
from datetime import datetime, timezone

from ..database_manager import get_db_connection
from .generic_crud import GenericCRUD # Assuming GenericCRUD has _manage_conn

# Configure logging
logger = logging.getLogger(__name__)

class CompanyAssetsCRUD(GenericCRUD):
    """
    CRUD operations for CompanyAssets table.
    """

    def __init__(self, db_path=None):
        super().__init__(table_name="CompanyAssets", primary_key="asset_id", db_path=db_path)

    def add_asset(self, asset_data: dict, conn: sqlite3.Connection = None) -> str | None:
        """
        Adds a new asset to the CompanyAssets table.

        Args:
            asset_data (dict): A dictionary containing asset information.
                               Required keys: 'asset_name', 'asset_type', 'current_status'.
                               Optional keys: 'serial_number', 'description', 'purchase_date',
                                            'purchase_value', 'notes'.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            str | None: The asset_id of the newly added asset, or None if an error occurs.
        """
        required_fields = ['asset_name', 'asset_type', 'current_status']
        if not all(field in asset_data for field in required_fields):
            logger.error(f"Missing one or more required fields: {required_fields}")
            return None

        asset_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        asset = {
            'asset_id': asset_id,
            'asset_name': asset_data['asset_name'],
            'asset_type': asset_data['asset_type'],
            'serial_number': asset_data.get('serial_number'),
            'description': asset_data.get('description'),
            'purchase_date': asset_data.get('purchase_date'),
            'purchase_value': asset_data.get('purchase_value'),
            'current_status': asset_data['current_status'],
            'notes': asset_data.get('notes'),
            'created_at': now,
            'updated_at': now,
            'is_deleted': 0,
            'deleted_at': None
        }

        try:
            if self.create(asset, conn=conn):
                logger.info(f"Asset '{asset_id}' added successfully.")
                return asset_id
            else:
                # create method in GenericCRUD should log its own errors if it returns False
                logger.error(f"Failed to add asset '{asset_id}' due to GenericCRUD.create failure.")
                return None
        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error adding asset: {e}. Serial number might be duplicate.")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while adding asset: {e}")
            return None


    def get_asset_by_id(self, asset_id: str, include_deleted: bool = False, conn: sqlite3.Connection = None) -> dict | None:
        """
        Fetches an asset by its ID.

        Args:
            asset_id (str): The ID of the asset to fetch.
            include_deleted (bool, optional): Whether to include soft-deleted assets. Defaults to False.
            conn (sqlite3.Connection, optional): Database connection.


        Returns:
            dict | None: The asset data as a dictionary, or None if not found or error.
        """
        query = f"SELECT * FROM {self.table_name} WHERE {self.primary_key} = ?"
        params = [asset_id]

        if not include_deleted:
            query += " AND is_deleted = 0"

        try:
            if conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                row = cursor.fetchone()
            else:
                with get_db_connection(self.db_path) as local_conn:
                    cursor = local_conn.cursor()
                    cursor.execute(query, tuple(params))
                    row = cursor.fetchone()

            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Error fetching asset by ID '{asset_id}': {e}")
            return None

    def get_assets(self, filters: dict = None, limit: int = None, offset: int = 0, include_deleted: bool = False, conn: sqlite3.Connection = None) -> list[dict]:
        """
        Fetches assets with optional filtering, pagination, and soft delete handling.

        Args:
            filters (dict, optional): A dictionary of filters to apply.
                                      Keys are column names, values are the values to filter by.
                                      Example: {'asset_type': 'Laptop', 'current_status': 'In Use'}
            limit (int, optional): Maximum number of assets to return.
            offset (int, optional): Number of assets to skip.
            include_deleted (bool, optional): Whether to include soft-deleted assets. Defaults to False.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            list[dict]: A list of assets, or an empty list if none found or error.
        """
        query = f"SELECT * FROM {self.table_name}"
        conditions = []
        params = []

        if filters:
            for key, value in filters.items():
                # Basic protection against SQL injection for keys, assumes keys are valid column names
                if key in self._get_column_names(conn): # Ensure key is a valid column
                    conditions.append(f"{key} = ?")
                    params.append(value)
                else:
                    logger.warning(f"Filter key '{key}' is not a valid column name. Ignoring.")


        if not include_deleted:
            conditions.append("is_deleted = 0")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC" # Default ordering

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        if offset is not None and offset > 0 : # OFFSET is only useful with LIMIT
            query += " OFFSET ?"
            params.append(offset)

        results = []
        try:
            if conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                results = [dict(row) for row in cursor.fetchall()]
            else:
                with get_db_connection(self.db_path) as local_conn:
                    cursor = local_conn.cursor()
                    cursor.execute(query, tuple(params))
                    results = [dict(row) for row in cursor.fetchall()]
            return results
        except Exception as e:
            logger.error(f"Error fetching assets with filters '{filters}': {e}")
            return []

    def _get_column_names(self, conn: sqlite3.Connection = None) -> list[str]:
        """Helper to get column names for filter validation."""
        query = f"PRAGMA table_info({self.table_name});"
        try:
            if conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return [row['name'] for row in cursor.fetchall()]
            else:
                with get_db_connection(self.db_path) as local_conn:
                    cursor = local_conn.cursor()
                    cursor.execute(query)
                    return [row['name'] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching column names for {self.table_name}: {e}")
            return []


    def update_asset(self, asset_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
        """
        Updates an existing asset.

        Args:
            asset_id (str): The ID of the asset to update.
            data (dict): A dictionary containing the asset data to update.
                         'updated_at' will be set automatically.
                         To soft delete, include 'is_deleted': 1 and 'deleted_at': (timestamp).
                         To restore, include 'is_deleted': 0 and 'deleted_at': None.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        if not data:
            logger.warning("No data provided for asset update.")
            return False

        data['updated_at'] = datetime.now(timezone.utc).isoformat()

        # Specific handling for soft delete/restore
        if 'is_deleted' in data:
            if data['is_deleted'] == 1 and 'deleted_at' not in data:
                data['deleted_at'] = data['updated_at'] # Set deleted_at if not provided
            elif data['is_deleted'] == 0:
                data['deleted_at'] = None # Ensure deleted_at is nullified on restore

        try:
            if self.update(asset_id, data, conn=conn):
                logger.info(f"Asset '{asset_id}' updated successfully.")
                return True
            else:
                # GenericCRUD.update should log its own detailed errors
                logger.error(f"Failed to update asset '{asset_id}' via GenericCRUD.update.")
                return False
        except Exception as e:
            logger.error(f"An unexpected error occurred while updating asset '{asset_id}': {e}")
            return False

    def delete_asset(self, asset_id: str, conn: sqlite3.Connection = None) -> bool:
        """
        Soft deletes an asset.
        Sets is_deleted = 1, deleted_at to current timestamp.
        Optionally, current_status could be updated here or by a trigger/application logic.

        Args:
            asset_id (str): The ID of the asset to soft delete.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            bool: True if soft deletion was successful, False otherwise.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        data_to_update = {
            'is_deleted': 1,
            'deleted_at': now_iso,
            'updated_at': now_iso
            # Consider adding 'current_status': 'Disposed' or similar if appropriate
            # For now, status update is left to higher-level logic or direct update_asset call
        }

        try:
            if self.update(asset_id, data_to_update, conn=conn):
                logger.info(f"Asset '{asset_id}' soft deleted successfully.")
                return True
            else:
                logger.error(f"Soft delete failed for asset '{asset_id}' via GenericCRUD.update.")
                return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during soft delete of asset '{asset_id}': {e}")
            return False

# Instance for easy import
company_assets_crud = CompanyAssetsCRUD()

__all__ = [
    "CompanyAssetsCRUD",
    "company_assets_crud"
]

# Example Usage (for testing purposes, can be removed or commented out)
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # Ensure your generic_crud.py and database_manager.py are accessible
    # and a dummy database is initialized for testing.
    # For example, you might need to run db/init_schema.py first.

    # Fallback for DB_PATH if config is not set up for direct script run
    import os
    # Assuming this script is in db/cruds/
    # Project root is two levels up from cruds, then to app_data.db
    project_root_for_db = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    test_db_path = os.path.join(project_root_for_db, "app_data.db") # Adjust if your DB is elsewhere

    # Ensure the database and CompanyAssets table exist by running init_schema.py first.
    # This basic test assumes init_schema.py has been run.
    if not os.path.exists(test_db_path):
         logger.error(f"Database file not found at {test_db_path}. Please run init_schema.py first.")
    else:
        logger.info(f"Using database at {test_db_path} for testing.")

        # Override the db_path for the test instance
        test_crud = CompanyAssetsCRUD(db_path=test_db_path)

        # Test: Add Asset
        new_asset_data = {
            'asset_name': 'Test Laptop Pro',
            'asset_type': 'Laptop',
            'serial_number': f'TESTSN{uuid.uuid4().hex[:8]}', # Unique serial
            'description': 'A powerful laptop for testing',
            'purchase_date': '2023-01-15',
            'purchase_value': 1200.50,
            'current_status': 'In Stock',
            'notes': 'Initial stock'
        }
        added_asset_id = test_crud.add_asset(new_asset_data)
        if added_asset_id:
            logger.info(f"Test: Added asset with ID: {added_asset_id}")

            # Test: Get Asset by ID
            fetched_asset = test_crud.get_asset_by_id(added_asset_id)
            if fetched_asset:
                logger.info(f"Test: Fetched asset: {fetched_asset['asset_name']}")
            else:
                logger.error(f"Test: Failed to fetch asset {added_asset_id}")

            # Test: Update Asset
            update_data = {'current_status': 'Assigned', 'notes': 'Assigned to John Doe'}
            if test_crud.update_asset(added_asset_id, update_data):
                logger.info(f"Test: Updated asset {added_asset_id}")
                updated_fetched_asset = test_crud.get_asset_by_id(added_asset_id)
                if updated_fetched_asset:
                    logger.info(f"Test: Verified update - Status: {updated_fetched_asset['current_status']}, Notes: {updated_fetched_asset['notes']}")
            else:
                logger.error(f"Test: Failed to update asset {added_asset_id}")

            # Test: Get Assets (filtered)
            all_laptops = test_crud.get_assets(filters={'asset_type': 'Laptop'})
            logger.info(f"Test: Found {len(all_laptops)} laptops.")
            for laptop in all_laptops:
                logger.debug(f"  - Laptop: {laptop['asset_name']}, SN: {laptop['serial_number']}, Status: {laptop['current_status']}")


            # Test: Soft Delete Asset
            if test_crud.delete_asset(added_asset_id):
                logger.info(f"Test: Soft deleted asset {added_asset_id}")

                # Verify soft delete (should not be found by default)
                deleted_asset_check = test_crud.get_asset_by_id(added_asset_id)
                if not deleted_asset_check:
                    logger.info(f"Test: Asset {added_asset_id} correctly not found after soft delete (default get).")
                else:
                    logger.error(f"Test: Asset {added_asset_id} found after soft delete, which is unexpected for default get.")

                # Verify soft delete (should be found when including deleted)
                deleted_asset_included = test_crud.get_asset_by_id(added_asset_id, include_deleted=True)
                if deleted_asset_included and deleted_asset_included['is_deleted'] == 1:
                    logger.info(f"Test: Asset {added_asset_id} found with include_deleted=True and is_deleted flag is set.")
                    logger.info(f"  Deleted at: {deleted_asset_included['deleted_at']}")
                else:
                    logger.error(f"Test: Asset {added_asset_id} not found with include_deleted=True or is_deleted flag not set.")
            else:
                logger.error(f"Test: Failed to soft delete asset {added_asset_id}")
        else:
            logger.error("Test: Failed to add initial asset for testing.")

        logger.info("CompanyAssetsCRUD testing finished.")
    # Example of how to get column names (might be useful for validation layers)
    # cols = company_assets_crud._get_column_names()
    # logger.debug(f"CompanyAssets columns: {cols}")

    # Example of fetching all assets (including deleted)
    # all_assets_ever = company_assets_crud.get_assets(include_deleted=True, limit=5)
    # logger.debug(f"All assets (including deleted, limit 5): {len(all_assets_ever)}")
    # for asset in all_assets_ever:
    #    logger.debug(f"  - {asset['asset_name']}, Deleted: {asset['is_deleted']}")

    # Example of fetching specific status
    # in_stock_assets = company_assets_crud.get_assets(filters={'current_status': 'In Stock'})
    # logger.debug(f"In Stock assets: {len(in_stock_assets)}")

    # Attempt to add asset with duplicate serial number (should fail if serial is unique)
    # duplicate_sn_asset = {
    #     'asset_name': 'Duplicate SN Laptop',
    #     'asset_type': 'Laptop',
    #     'serial_number': 'TESTSN001', # Assuming TESTSN001 was used above or exists
    #     'current_status': 'In Stock'
    # }
    # test_crud.add_asset(duplicate_sn_asset) # Expect error log for integrity

    # Attempt to add asset with missing required fields
    # missing_fields_asset = {'asset_name': 'Laptop Missing Type'}
    # test_crud.add_asset(missing_fields_asset) # Expect error log for missing fields

    # Attempt to update a non-existent asset
    # non_existent_id = str(uuid.uuid4())
    # test_crud.update_asset(non_existent_id, {'notes': 'Trying to update non-existent'}) # Expect error/False

    # Attempt to delete a non-existent asset
    # test_crud.delete_asset(non_existent_id) # Expect error/False

    # Test get_assets with pagination
    # for i in range(5): # Add a few more assets
    #    test_crud.add_asset({
    #        'asset_name': f'Asset Page Test {i+1}', 'asset_type': 'Monitor',
    #        'current_status': 'Available', 'serial_number': f'SNPAGE{i+1}'
    #    })
    # page1 = test_crud.get_assets(filters={'asset_type':'Monitor'}, limit=2, offset=0)
    # logger.debug(f"Monitors Page 1 (limit 2, offset 0): {len(page1)}")
    # for p_asset in page1: logger.debug(f"  - {p_asset['asset_name']}")
    # page2 = test_crud.get_assets(filters={'asset_type':'Monitor'}, limit=2, offset=2)
    # logger.debug(f"Monitors Page 2 (limit 2, offset 2): {len(page2)}")
    # for p_asset in page2: logger.debug(f"  - {p_asset['asset_name']}")

    # Clean up - soft delete any test assets if necessary (or hard delete if GenericCRUD supports it and it's desired)
    # This part depends on how GenericCRUD handles hard deletes or if you want to leave them soft-deleted.
    # For example, to clean up 'Test Laptop Pro' if it was added:
    # if added_asset_id:
    #    test_crud.delete_asset(added_asset_id) # Ensure it's soft-deleted
    #    logger.info(f"Cleaned up asset {added_asset_id} by soft deleting.")
    # For assets added in pagination test:
    # for i in range(5):
    #    monitor_asset = test_crud.get_assets(filters={'serial_number': f'SNPAGE{i+1}'}, include_deleted=True)
    #    if monitor_asset:
    #        test_crud.delete_asset(monitor_asset[0]['asset_id'])
    #        logger.info(f"Cleaned up asset SNPAGE{i+1} by soft deleting.")

    # If GenericCRUD had a hard delete, it might look like:
    # generic_crud_instance = GenericCRUD(table_name="CompanyAssets", primary_key="asset_id", db_path=test_db_path)
    # if added_asset_id:
    #     if generic_crud_instance.delete(added_asset_id): # Assuming GenericCRUD.delete is hard delete
    #         logger.info(f"Test: Hard deleted asset {added_asset_id} for cleanup.")
    #     else:
    #         logger.error(f"Test: Failed to hard delete asset {added_asset_id} for cleanup.")

    # NOTE: The GenericCRUD class as used by other CRUDs (e.g. users_crud.py)
    # does not seem to have a _manage_conn decorator.
    # Its methods (create, read, update, delete) typically accept a `conn` parameter.
    # If `conn` is None, they establish a new connection.
    # The provided structure for CompanyAssetsCRUD aligns with that pattern by
    # also accepting `conn` and passing it down or establishing its own connection.
    # The _get_column_names helper also follows this pattern.
    # The `@_manage_conn` decorator is not part of the provided GenericCRUD structure in other files.
    # Thus, it's omitted here to maintain consistency with the presumed existing GenericCRUD.
    # If GenericCRUD *does* have _manage_conn and it's intended for use,
    # the methods in CompanyAssetsCRUD would need to be decorated with it,
    # and they might not need to handle the `conn` parameter explicitly in their signature
    # or establish connections using `get_db_connection` directly.
    # For now, I'm following the pattern seen in users_crud.py, etc.
    pass
