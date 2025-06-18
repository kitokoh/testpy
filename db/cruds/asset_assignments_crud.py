import sqlite3
import uuid
import logging
from datetime import datetime, timezone

from ..database_manager import get_db_connection
from .generic_crud import GenericCRUD

# Configure logging
logger = logging.getLogger(__name__)

class AssetAssignmentsCRUD(GenericCRUD):
    """
    CRUD operations for AssetAssignments table.
    """

    def __init__(self, db_path=None):
        super().__init__(table_name="AssetAssignments", primary_key="assignment_id", db_path=db_path)

    def add_assignment(self, assignment_data: dict, conn: sqlite3.Connection = None) -> str | None:
        """
        Creates a new asset assignment.

        Args:
            assignment_data (dict): A dictionary containing assignment information.
                                    Required: 'asset_id', 'personnel_id', 'assignment_date', 'assignment_status'.
                                    Optional: 'expected_return_date', 'actual_return_date', 'notes'.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            str | None: The assignment_id of the newly added assignment, or None if an error occurs.
        """
        required_fields = ['asset_id', 'personnel_id', 'assignment_date', 'assignment_status']
        if not all(field in assignment_data for field in required_fields):
            logger.error(f"Missing one or more required fields for assignment: {required_fields}")
            return None

        assignment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Ensure assignment_date is in ISO format if it's a datetime object
        assignment_date = assignment_data['assignment_date']
        if isinstance(assignment_date, datetime):
            assignment_date = assignment_date.isoformat()

        expected_return_date = assignment_data.get('expected_return_date')
        if isinstance(expected_return_date, datetime):
            expected_return_date = expected_return_date.isoformat()

        actual_return_date = assignment_data.get('actual_return_date')
        if isinstance(actual_return_date, datetime):
            actual_return_date = actual_return_date.isoformat()

        assignment = {
            'assignment_id': assignment_id,
            'asset_id': assignment_data['asset_id'],
            'personnel_id': assignment_data['personnel_id'],
            'assignment_date': assignment_date,
            'expected_return_date': expected_return_date,
            'actual_return_date': actual_return_date,
            'assignment_status': assignment_data['assignment_status'],
            'notes': assignment_data.get('notes'),
            'created_at': now,
            'updated_at': now
        }

        try:
            if self.create(assignment, conn=conn):
                logger.info(f"Assignment '{assignment_id}' for asset '{assignment_data['asset_id']}' to personnel '{assignment_data['personnel_id']}' added successfully.")
                return assignment_id
            else:
                logger.error(f"Failed to add assignment due to GenericCRUD.create failure.")
                return None
        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error adding assignment (likely invalid asset_id or personnel_id): {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while adding assignment: {e}")
            return None

    def get_assignment_by_id(self, assignment_id: str, conn: sqlite3.Connection = None) -> dict | None:
        """
        Fetches an assignment by its ID.

        Args:
            assignment_id (str): The ID of the assignment to fetch.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict | None: The assignment data as a dictionary, or None if not found or error.
        """
        try:
            return self.read(assignment_id, conn=conn)
        except Exception as e:
            logger.error(f"Error fetching assignment by ID '{assignment_id}': {e}")
            return None

    def _get_assignments_by_field(self, field_name: str, value, filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
        """Helper to get assignments by a specific field, with additional filters."""
        query = f"SELECT * FROM {self.table_name} WHERE {field_name} = ?"
        params = [value]

        if filters:
            # Ensure column names are valid before adding to query
            valid_column_names = self._get_column_names(conn)
            for key, val in filters.items():
                if key in valid_column_names:
                    query += f" AND {key} = ?"
                    params.append(val)
                else:
                    logger.warning(f"Filter key '{key}' is not a valid column name for AssetAssignments. Ignoring.")

        query += " ORDER BY assignment_date DESC"

        results = []
        try:
            db_conn = conn if conn else get_db_connection(self.db_path)
            cursor = db_conn.cursor()
            cursor.execute(query, tuple(params))
            results = [dict(row) for row in cursor.fetchall()]
            if not conn: # If we opened a connection, close it
                db_conn.close()
            return results
        except Exception as e:
            logger.error(f"Error fetching assignments by {field_name} = '{value}' with filters '{filters}': {e}")
            if not conn and db_conn: # Ensure connection is closed if opened here and error occurred
                 db_conn.close()
            return []

    def get_assignments_for_asset(self, asset_id: str, filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
        """
        Fetches all assignments for a specific asset, with optional filters (e.g., assignment_status).

        Args:
            asset_id (str): The ID of the asset.
            filters (dict, optional): Additional filters to apply.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            list[dict]: A list of assignments for the asset.
        """
        return self._get_assignments_by_field('asset_id', asset_id, filters, conn)

    def get_assignments_for_personnel(self, personnel_id: int, filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
        """
        Fetches all assignments for a specific personnel, with optional filters.

        Args:
            personnel_id (int): The ID of the personnel.
            filters (dict, optional): Additional filters to apply.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            list[dict]: A list of assignments for the personnel.
        """
        return self._get_assignments_by_field('personnel_id', personnel_id, filters, conn)

    def get_all_assignments(self, filters: dict = None, limit: int = None, offset: int = 0, conn: sqlite3.Connection = None) -> list[dict]:
        """
        Fetches all assignments with optional filtering and pagination.

        Args:
            filters (dict, optional): Filters to apply.
            limit (int, optional): Maximum number of assignments to return.
            offset (int, optional): Number of assignments to skip.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            list[dict]: A list of assignments.
        """
        query = f"SELECT * FROM {self.table_name}"
        conditions = []
        params = []

        if filters:
            valid_column_names = self._get_column_names(conn)
            for key, value in filters.items():
                if key in valid_column_names:
                    conditions.append(f"{key} = ?")
                    params.append(value)
                else:
                    logger.warning(f"Filter key '{key}' is not a valid column name for AssetAssignments. Ignoring.")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        if offset is not None and offset > 0:
            query += " OFFSET ?"
            params.append(offset)

        results = []
        try:
            db_conn = conn if conn else get_db_connection(self.db_path)
            cursor = db_conn.cursor()
            cursor.execute(query, tuple(params))
            results = [dict(row) for row in cursor.fetchall()]
            if not conn:
                db_conn.close()
            return results
        except Exception as e:
            logger.error(f"Error fetching all assignments with filters '{filters}': {e}")
            if not conn and db_conn:
                 db_conn.close()
            return []

    def _get_column_names(self, conn: sqlite3.Connection = None) -> list[str]:
        """Helper to get column names for filter validation."""
        query = f"PRAGMA table_info({self.table_name});"
        names = []
        try:
            db_conn = conn if conn else get_db_connection(self.db_path)
            cursor = db_conn.cursor()
            cursor.execute(query)
            names = [row['name'] for row in cursor.fetchall()]
            if not conn:
                db_conn.close()
            return names
        except Exception as e:
            logger.error(f"Error fetching column names for {self.table_name}: {e}")
            if not conn and db_conn:
                 db_conn.close()
            return []


    def update_assignment(self, assignment_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
        """
        Updates an existing assignment.

        Args:
            assignment_id (str): The ID of the assignment to update.
            data (dict): Data to update (e.g., 'actual_return_date', 'assignment_status', 'notes').
                         'updated_at' will be set automatically.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            bool: True if update was successful, False otherwise.
        """
        if not data:
            logger.warning("No data provided for assignment update.")
            return False

        data['updated_at'] = datetime.now(timezone.utc).isoformat()

        # Ensure date fields are ISO formatted if they are datetime objects
        for date_field in ['assignment_date', 'expected_return_date', 'actual_return_date']:
            if date_field in data and isinstance(data[date_field], datetime):
                data[date_field] = data[date_field].isoformat()

        try:
            if self.update(assignment_id, data, conn=conn):
                logger.info(f"Assignment '{assignment_id}' updated successfully.")
                return True
            else:
                logger.error(f"Failed to update assignment '{assignment_id}' via GenericCRUD.update.")
                return False
        except Exception as e:
            logger.error(f"An unexpected error occurred while updating assignment '{assignment_id}': {e}")
            return False

    def delete_assignment(self, assignment_id: str, conn: sqlite3.Connection = None) -> bool:
        """
        Deletes an assignment (hard delete).
        Note: For operational "cancellation" or marking an error, consider updating
        the assignment_status to a specific value (e.g., 'Cancelled', 'Error in Record')
        using the update_assignment method instead of a hard delete, to preserve history.

        Args:
            assignment_id (str): The ID of the assignment to delete.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        try:
            if self.delete(assignment_id, conn=conn): # Assumes GenericCRUD.delete is a hard delete
                logger.info(f"Assignment '{assignment_id}' deleted successfully (hard delete).")
                return True
            else:
                logger.error(f"Hard delete failed for assignment '{assignment_id}' via GenericCRUD.delete.")
                return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during hard delete of assignment '{assignment_id}': {e}")
            return False

# Instance for easy import
asset_assignments_crud = AssetAssignmentsCRUD()

__all__ = [
    "AssetAssignmentsCRUD",
    "asset_assignments_crud"
]

# Example Usage (for testing purposes)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    import os
    project_root_for_db = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    test_db_path = os.path.join(project_root_for_db, "app_data.db")

    if not os.path.exists(test_db_path):
        logger.error(f"Database file not found at {test_db_path}. Please run db/init_schema.py first.")
    else:
        logger.info(f"Using database at {test_db_path} for AssetAssignmentsCRUD testing.")

        # Create a test instance with the specific DB path
        test_crud = AssetAssignmentsCRUD(db_path=test_db_path)

        # For these tests to run, we need a valid asset_id and personnel_id from CompanyAssets and CompanyPersonnel tables.
        # Let's assume these exist or are created by other tests/setup.
        # For isolated testing, you might pre-populate or mock these.
        # Here, we'll use placeholder IDs and expect failures if they don't exist,
        # or success if they happen to exist in your test DB.

        # A more robust test would involve first creating a dummy asset and personnel using their respective CRUDs.
        # from .company_assets_crud import company_assets_crud as assets_crud_for_test # If CompanyAssetsCRUD is in same dir
        # from .company_personnel_crud import company_personnel_crud # Assuming this exists

        # For simplicity, using fixed UUIDs/IDs for testing. Replace with actual IDs from your DB.
        # These IDs should exist in your CompanyAssets and CompanyPersonnel tables for FK constraints to pass.
        sample_asset_id = str(uuid.uuid4()) # Placeholder, ideally create one.
        sample_personnel_id = 1 # Placeholder, ideally create one.

        logger.info(f"Using sample_asset_id: {sample_asset_id}, sample_personnel_id: {sample_personnel_id} for tests.")
        logger.info("Note: These tests may fail if these IDs do not exist in the target database due to FK constraints.")
        logger.info("Consider pre-populating CompanyAssets and CompanyPersonnel for robust testing.")

        # Test: Add Assignment
        # To make this test more likely to pass, let's first add a dummy asset and personnel
        # This requires access to their CRUDs.
        # For now, we'll proceed with placeholder IDs and note the dependency.

        # It's better to use CompanyAssetsCRUD to add a temporary asset for this test
        # and CompanyPersonnelCRUD for a temporary personnel record.
        # This makes the test self-contained.
        # For now, this example assumes you might run this against a populated DB or mock.

        assignment_data = {
            'asset_id': sample_asset_id, # Replace with a real asset_id from your DB for testing
            'personnel_id': sample_personnel_id, # Replace with a real personnel_id
            'assignment_date': datetime.now(timezone.utc).isoformat(),
            'assignment_status': 'Assigned',
            'expected_return_date': (datetime.now(timezone.utc) + timezone.timedelta(days=30)).isoformat(),
            'notes': 'Test assignment for John Doe'
        }

        # Manually create a dummy asset and personnel for testing if their CRUDs are available
        # This part would ideally be in a setup_method or fixture in a test framework
        # For this script, we'll simulate it.
        # Need to ensure `db.cruds.company_assets_crud` and a hypothetical `db.cruds.company_personnel_crud` are importable.
        # And that `init_schema` has been run.

        # Simplified: Assume CompanyAssets and CompanyPersonnel tables exist.
        # To ensure FK passes, we'd normally do:
        # temp_asset_id = assets_crud_for_test.add_asset({'asset_name':'Test Asset for Assign', 'asset_type':'Tool', 'current_status':'Available'})
        # temp_personnel_id = some_personnel_crud.add_personnel({'name':'Test Assignee', ...})
        # assignment_data['asset_id'] = temp_asset_id
        # assignment_data['personnel_id'] = temp_personnel_id

        added_assignment_id = test_crud.add_assignment(assignment_data)

        if added_assignment_id:
            logger.info(f"Test: Added assignment with ID: {added_assignment_id}")

            # Test: Get Assignment by ID
            fetched_assignment = test_crud.get_assignment_by_id(added_assignment_id)
            if fetched_assignment:
                logger.info(f"Test: Fetched assignment for asset: {fetched_assignment['asset_id']}")
            else:
                logger.error(f"Test: Failed to fetch assignment {added_assignment_id}")

            # Test: Update Assignment
            update_data = {'assignment_status': 'Returned', 'actual_return_date': datetime.now(timezone.utc).isoformat()}
            if test_crud.update_assignment(added_assignment_id, update_data):
                logger.info(f"Test: Updated assignment {added_assignment_id}")
                updated_fetched_assignment = test_crud.get_assignment_by_id(added_assignment_id)
                if updated_fetched_assignment:
                     logger.info(f"Test: Verified update - Status: {updated_fetched_assignment['assignment_status']}")
            else:
                logger.error(f"Test: Failed to update assignment {added_assignment_id}")

            # Test: Get Assignments for Asset
            asset_assignments = test_crud.get_assignments_for_asset(assignment_data['asset_id'])
            logger.info(f"Test: Found {len(asset_assignments)} assignments for asset {assignment_data['asset_id']}.")

            # Test: Get Assignments for Personnel
            personnel_assignments = test_crud.get_assignments_for_personnel(assignment_data['personnel_id'])
            logger.info(f"Test: Found {len(personnel_assignments)} assignments for personnel {assignment_data['personnel_id']}.")

            # Test: Get All Assignments (with a limit for brevity)
            all_assignments = test_crud.get_all_assignments(limit=5)
            logger.info(f"Test: Fetched {len(all_assignments)} assignments (limit 5).")


            # Test: Delete Assignment (Hard Delete)
            if test_crud.delete_assignment(added_assignment_id):
                logger.info(f"Test: Hard deleted assignment {added_assignment_id}")
                # Verify delete
                deleted_assignment_check = test_crud.get_assignment_by_id(added_assignment_id)
                if not deleted_assignment_check:
                    logger.info(f"Test: Assignment {added_assignment_id} correctly not found after hard delete.")
                else:
                    logger.error(f"Test: Assignment {added_assignment_id} still found after hard delete.")
            else:
                logger.error(f"Test: Failed to hard delete assignment {added_assignment_id}")

        else:
            logger.error("Test: Failed to add initial assignment. This might be due to FK constraints if sample_asset_id or sample_personnel_id do not exist.")
            logger.error("Please ensure CompanyAssets and CompanyPersonnel tables have corresponding entries, or adjust sample IDs.")

        # Cleanup (if temp asset/personnel were created)
        # if temp_asset_id: assets_crud_for_test.delete_asset(temp_asset_id) # soft delete is fine
        # if temp_personnel_id: some_personnel_crud.delete_personnel(temp_personnel_id)

        logger.info("AssetAssignmentsCRUD testing finished.")
    pass
