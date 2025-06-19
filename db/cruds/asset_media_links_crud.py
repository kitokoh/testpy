import sqlite3
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from ..database_manager import get_db_connection
from .generic_crud import GenericCRUD # Assuming GenericCRUD is sufficient

# Configure logging
logger = logging.getLogger(__name__)

class AssetMediaLinksCRUD(GenericCRUD):
    """
    CRUD operations for AssetMediaLinks table.
    Manages links between CompanyAssets and MediaItems.
    """

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(table_name="AssetMediaLinks", primary_key="link_id", db_path=db_path)
        # Additional table names used in joins
        self.media_items_table = "MediaItems"
        self.assets_table = "CompanyAssets"


    def _execute_query(self, query: str, params: tuple = (), conn: Optional[sqlite3.Connection] = None, fetch_one: bool = False, commit: bool = False) -> Any:
        """Helper to execute queries, managing connection if not provided."""
        db_conn = conn if conn else get_db_connection(self.db_path)
        cursor = db_conn.cursor()
        try:
            cursor.execute(query, params)
            if commit:
                db_conn.commit()
                if not conn: # Only close if we opened it
                    db_conn.close()
                return cursor.lastrowid if cursor.lastrowid else True # For INSERT/UPDATE/DELETE

            if fetch_one:
                result = cursor.fetchone()
            else:
                result = cursor.fetchall()

            if not conn: # Only close if we opened it
                db_conn.close()
            return result
        except sqlite3.Error as e:
            logger.error(f"Database error for query '{query[:100]}...': {e}")
            if not conn and db_conn: # Close connection if opened here and error occurred
                try:
                    db_conn.close()
                except Exception as close_err: # pragma: no cover
                    logger.error(f"Failed to close connection after error: {close_err}")
            raise # Re-raise the exception for the caller to handle or log further
        except Exception as e: # pragma: no cover (general unexpected errors)
            logger.error(f"Unexpected error for query '{query[:100]}...': {e}")
            if not conn and db_conn:
                try:
                    db_conn.close()
                except Exception as close_err:
                    logger.error(f"Failed to close connection after unexpected error: {close_err}")
            raise


    def link_media_to_asset(self, asset_id: str, media_item_id: str, display_order: int = 0, alt_text: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> Optional[int]:
        """
        Links a media item to an asset.

        Args:
            asset_id (str): The ID of the asset.
            media_item_id (str): The ID of the media item.
            display_order (int, optional): The display order of the media item for this asset. Defaults to 0.
            alt_text (Optional[str], optional): Alternative text for the media link. Defaults to None.
            conn (Optional[sqlite3.Connection], optional): Database connection.

        Returns:
            Optional[int]: The link_id of the new link, or None if an error occurs.
        """
        query = f"""
            INSERT INTO {self.table_name} (asset_id, media_item_id, display_order, alt_text, created_at)
            VALUES (?, ?, ?, ?, ?)
        """
        now = datetime.now(timezone.utc).isoformat()
        params = (asset_id, media_item_id, display_order, alt_text, now)
        try:
            link_id = self._execute_query(query, params, conn=conn, commit=True)
            logger.info(f"Media item '{media_item_id}' linked to asset '{asset_id}' with link_id {link_id}.")
            return link_id
        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error linking media '{media_item_id}' to asset '{asset_id}': {e}. Likely duplicate link or invalid IDs.")
            return None
        except Exception as e:
            logger.error(f"Error linking media '{media_item_id}' to asset '{asset_id}': {e}")
            return None

    def get_media_links_for_asset(self, asset_id: str, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
        """
        Retrieves all media links for a given asset, ordered by display_order.
        Joins with MediaItems table to include media details.

        Args:
            asset_id (str): The ID of the asset.
            conn (Optional[sqlite3.Connection], optional): Database connection.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a linked media item with its details.
        """
        query = f"""
            SELECT
                aml.link_id, aml.asset_id, aml.media_item_id, aml.display_order, aml.alt_text, aml.created_at AS link_created_at,
                mi.title AS media_title, mi.description AS media_description, mi.item_type AS media_item_type,
                mi.filepath AS media_filepath, mi.url AS media_url, mi.thumbnail_path AS media_thumbnail_path,
                mi.metadata_json AS media_metadata_json, mi.created_at AS media_created_at
            FROM {self.table_name} aml
            JOIN {self.media_items_table} mi ON aml.media_item_id = mi.media_item_id
            WHERE aml.asset_id = ?
            ORDER BY aml.display_order ASC, aml.link_id ASC
        """
        params = (asset_id,)
        try:
            rows = self._execute_query(query, params, conn=conn, fetch_one=False)
            return [dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Error fetching media links for asset '{asset_id}': {e}")
            return []

    def get_media_link_by_ids(self, asset_id: str, media_item_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific link by asset_id and media_item_id.

        Args:
            asset_id (str): The ID of the asset.
            media_item_id (str): The ID of the media item.
            conn (Optional[sqlite3.Connection], optional): Database connection.

        Returns:
            Optional[Dict[str, Any]]: The link data, or None if not found.
        """
        query = f"SELECT * FROM {self.table_name} WHERE asset_id = ? AND media_item_id = ?"
        params = (asset_id, media_item_id)
        try:
            row = self._execute_query(query, params, conn=conn, fetch_one=True)
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching media link by asset_id '{asset_id}' and media_item_id '{media_item_id}': {e}")
            return None

    def get_media_link_by_link_id(self, link_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific link by its link_id.

        Args:
            link_id (int): The primary key ID of the link.
            conn (Optional[sqlite3.Connection], optional): Database connection.

        Returns:
            Optional[Dict[str, Any]]: The link data, or None if not found.
        """
        try:
            # GenericCRUD's read method can be used here if it returns a dict.
            # Assuming it does based on typical CRUD patterns.
            return self.read(link_id, conn=conn)
        except Exception as e:
            logger.error(f"Error fetching media link by link_id '{link_id}': {e}")
            return None


    def update_media_link(self, link_id: int, display_order: Optional[int] = None, alt_text: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> bool:
        """
        Updates display_order or alt_text for a link.

        Args:
            link_id (int): The ID of the link to update.
            display_order (Optional[int], optional): New display order.
            alt_text (Optional[str], optional): New alt text. Can be empty string. Use with care if you want to "unset" vs set to empty.
            conn (Optional[sqlite3.Connection], optional): Database connection.

        Returns:
            bool: True if update was successful, False otherwise.
        """
        if display_order is None and alt_text is None:
            logger.warning(f"Update called for link_id {link_id} without any data to update.")
            return False

        fields_to_update = {}
        if display_order is not None:
            fields_to_update['display_order'] = display_order
        if alt_text is not None: # Allows setting alt_text to ""
            fields_to_update['alt_text'] = alt_text

        # Add updated_at if your table has it (AssetMediaLinks schema does not explicitly list updated_at, but good practice)
        # fields_to_update['updated_at'] = datetime.now(timezone.utc).isoformat()

        try:
            # GenericCRUD's update method used here.
            return self.update(link_id, fields_to_update, conn=conn)
        except Exception as e:
            logger.error(f"Error updating media link '{link_id}': {e}")
            return False

    def unlink_media_from_asset(self, link_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
        """
        Removes a link by its link_id (hard delete).

        Args:
            link_id (int): The ID of the link to remove.
            conn (Optional[sqlite3.Connection], optional): Database connection.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        try:
            # GenericCRUD's delete method used here.
            success = self.delete(link_id, conn=conn)
            if success:
                logger.info(f"Media link '{link_id}' unlinked successfully.")
            else:
                logger.warning(f"Failed to unlink media link '{link_id}'. It might not exist or another error occurred.")
            return success
        except Exception as e:
            logger.error(f"Error unlinking media link '{link_id}': {e}")
            return False

    def unlink_media_by_ids(self, asset_id: str, media_item_id: str, conn: Optional[sqlite3.Connection] = None) -> bool:
        """
        Removes a link by asset_id and media_item_id.

        Args:
            asset_id (str): The ID of the asset.
            media_item_id (str): The ID of the media item.
            conn (Optional[sqlite3.Connection], optional): Database connection.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        query = f"DELETE FROM {self.table_name} WHERE asset_id = ? AND media_item_id = ?"
        params = (asset_id, media_item_id)
        try:
            # Using _execute_query as this is a specific delete not by primary key.
            # A bit of a workaround if GenericCRUD only supports delete by PK.
            # We need to check affected rows if possible.
            # For simplicity, we'll assume success if no error. A more robust check would be cursor.rowcount.

            # Re-evaluating: GenericCRUD delete is by PK. This needs custom execution.
            db_conn = conn if conn else get_db_connection(self.db_path)
            cursor = db_conn.cursor()
            cursor.execute(query, params)
            db_conn.commit()
            deleted_rows = cursor.rowcount
            if not conn: # Only close if we opened it
                db_conn.close()

            if deleted_rows > 0:
                logger.info(f"Media item '{media_item_id}' unlinked from asset '{asset_id}' successfully.")
                return True
            else:
                logger.warning(f"No link found for media item '{media_item_id}' and asset '{asset_id}' to unlink.")
                return False
        except Exception as e:
            logger.error(f"Error unlinking media by IDs (asset: {asset_id}, media: {media_item_id}): {e}")
            return False

    def unlink_all_media_from_asset(self, asset_id: str, conn: Optional[sqlite3.Connection] = None) -> bool:
        """
        Removes all media links for a given asset.

        Args:
            asset_id (str): The ID of the asset.
            conn (Optional[sqlite3.Connection], optional): Database connection.

        Returns:
            bool: True if deletion was successful or no links existed, False on error.
        """
        query = f"DELETE FROM {self.table_name} WHERE asset_id = ?"
        params = (asset_id,)
        try:
            db_conn = conn if conn else get_db_connection(self.db_path)
            cursor = db_conn.cursor()
            cursor.execute(query, params)
            db_conn.commit()
            # deleted_count = cursor.rowcount # Good for logging
            if not conn:
                db_conn.close()
            logger.info(f"All media links for asset '{asset_id}' unlinked successfully (affected rows: {cursor.rowcount}).")
            return True
        except Exception as e:
            logger.error(f"Error unlinking all media from asset '{asset_id}': {e}")
            return False

    def update_asset_media_display_orders(self, asset_id: str, ordered_media_item_ids: List[str], conn: Optional[sqlite3.Connection] = None) -> bool:
        """
        Updates display order for all media items linked to an asset.
        Items not in the list might be unlinked or handled differently based on stricter requirements.
        This implementation only updates existing links.

        Args:
            asset_id (str): The ID of the asset.
            ordered_media_item_ids (List[str]): A list of media_item_ids in the desired display order.
            conn (Optional[sqlite3.Connection], optional): Database connection.

        Returns:
            bool: True if all updates were successful, False otherwise.
        """
        # This operation should be atomic (all or nothing).
        db_conn = conn if conn else get_db_connection(self.db_path)
        cursor = db_conn.cursor()

        try:
            for i, media_item_id in enumerate(ordered_media_item_ids):
                # We assume 'updated_at' is not on AssetMediaLinks as per schema in prompt. If it were, it should be updated too.
                update_query = f"UPDATE {self.table_name} SET display_order = ? WHERE asset_id = ? AND media_item_id = ?"
                cursor.execute(update_query, (i, asset_id, media_item_id))

            if not conn: # Commit only if we own the connection
                db_conn.commit()
            logger.info(f"Display orders updated for asset '{asset_id}'.")
            return True
        except Exception as e:
            logger.error(f"Error updating display orders for asset '{asset_id}': {e}")
            if not conn: # Rollback if we own the connection and an error occurred
                db_conn.rollback()
            return False
        finally:
            if not conn: # Close if we opened it
                db_conn.close()


# Instance for easy import
asset_media_links_crud = AssetMediaLinksCRUD()

__all__ = [
    "AssetMediaLinksCRUD",
    "asset_media_links_crud"
]

# Example Usage (for testing purposes)
if __name__ == '__main__': # pragma: no cover
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    import os
    # Adjust path to root if necessary, assuming this script is in db/cruds/
    project_root_for_db = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    test_db_path = os.path.join(project_root_for_db, "app_data.db")

    if not os.path.exists(test_db_path):
        logger.error(f"Database file not found at {test_db_path}. Please run db/init_schema.py first.")
        logger.error("Also ensure CompanyAssets and MediaItems tables are populated with sample data for tests.")
    else:
        logger.info(f"Using database at {test_db_path} for AssetMediaLinksCRUD testing.")

        test_crud = AssetMediaLinksCRUD(db_path=test_db_path)

        # These tests require existing asset_id and media_item_id values.
        # For robust testing, create dummy CompanyAsset and MediaItem entries first.
        # For this example, we'll use placeholder UUIDs.
        # These tests WILL LIKELY FAIL due to FK constraints if these IDs don't exist.

        sample_asset_id = str(uuid.uuid4()) # Placeholder
        sample_media_item_id_1 = str(uuid.uuid4()) # Placeholder
        sample_media_item_id_2 = str(uuid.uuid4()) # Placeholder

        logger.warning(f"Using placeholder asset_id: {sample_asset_id} and media_ids: {sample_media_item_id_1}, {sample_media_item_id_2}")
        logger.warning("These tests will likely fail due to FK constraints if these IDs do not exist in their respective tables.")
        logger.warning("Populate CompanyAssets and MediaItems tables for meaningful tests.")

        # Test: Link media to asset
        link_id_1 = None
        try:
            link_id_1 = test_crud.link_media_to_asset(sample_asset_id, sample_media_item_id_1, display_order=0, alt_text="Test Image 1")
            if link_id_1:
                logger.info(f"Test: Linked media {sample_media_item_id_1} to asset {sample_asset_id}, link_id: {link_id_1}")
            else:
                logger.error("Test: Failed to link media 1 (check FK constraints or logs).")
        except Exception as e:
             logger.error(f"Test: Error during link_media_to_asset for media 1: {e}")


        link_id_2 = None
        try:
            link_id_2 = test_crud.link_media_to_asset(sample_asset_id, sample_media_item_id_2, display_order=1, alt_text="Test Image 2")
            if link_id_2:
                logger.info(f"Test: Linked media {sample_media_item_id_2} to asset {sample_asset_id}, link_id: {link_id_2}")
            else:
                logger.error("Test: Failed to link media 2 (check FK constraints or logs).")
        except Exception as e:
            logger.error(f"Test: Error during link_media_to_asset for media 2: {e}")

        if link_id_1:
            # Test: Get media links for asset
            try:
                links = test_crud.get_media_links_for_asset(sample_asset_id)
                logger.info(f"Test: Found {len(links)} media links for asset {sample_asset_id}.")
                for link in links:
                    logger.info(f"  - Link ID: {link['link_id']}, Media Title: {link.get('media_title', 'N/A')}, Order: {link['display_order']}")
            except Exception as e:
                logger.error(f"Test: Error in get_media_links_for_asset: {e}")

            # Test: Get media link by IDs
            try:
                specific_link = test_crud.get_media_link_by_ids(sample_asset_id, sample_media_item_id_1)
                if specific_link:
                    logger.info(f"Test: Fetched specific link by IDs: {specific_link['link_id']}")
                else:
                    logger.error("Test: Failed to fetch specific link by IDs.")
            except Exception as e:
                logger.error(f"Test: Error in get_media_link_by_ids: {e}")


            # Test: Get media link by link_id
            try:
                link_by_pk = test_crud.get_media_link_by_link_id(link_id_1)
                if link_by_pk:
                    logger.info(f"Test: Fetched specific link by link_id {link_id_1}: Order {link_by_pk['display_order']}")
                else:
                    logger.error(f"Test: Failed to fetch link by link_id {link_id_1}")
            except Exception as e:
                logger.error(f"Test: Error in get_media_link_by_link_id for {link_id_1}: {e}")


            # Test: Update media link
            try:
                if test_crud.update_media_link(link_id_1, display_order=5, alt_text="Updated Alt Text 1"):
                    logger.info(f"Test: Updated media link {link_id_1}.")
                    updated_link = test_crud.get_media_link_by_link_id(link_id_1)
                    if updated_link:
                        logger.info(f"  - Verified update: Order: {updated_link['display_order']}, Alt: {updated_link['alt_text']}")
                else:
                    logger.error(f"Test: Failed to update media link {link_id_1}.")
            except Exception as e:
                 logger.error(f"Test: Error in update_media_link for {link_id_1}: {e}")


        if link_id_1 and link_id_2:
             # Test: Update asset media display orders
            try:
                if test_crud.update_asset_media_display_orders(sample_asset_id, [sample_media_item_id_2, sample_media_item_id_1]):
                    logger.info(f"Test: Updated display orders for asset {sample_asset_id}.")
                    # Verify new order
                    updated_links = test_crud.get_media_links_for_asset(sample_asset_id)
                    for ul_idx, ul in enumerate(updated_links):
                        logger.info(f"  - New Order: {ul_idx}, Link ID: {ul['link_id']}, Media ID: {ul['media_item_id']}, Actual DB Order: {ul['display_order']}")
                else:
                    logger.error(f"Test: Failed to update display orders for asset {sample_asset_id}.")
            except Exception as e:
                logger.error(f"Test: Error in update_asset_media_display_orders for {sample_asset_id}: {e}")


        # Test: Unlink media by IDs
        if link_id_1: # Only try if linking was potentially successful
            try:
                if test_crud.unlink_media_by_ids(sample_asset_id, sample_media_item_id_1):
                    logger.info(f"Test: Unlinked media {sample_media_item_id_1} from asset {sample_asset_id} by IDs.")
                else:
                    logger.error(f"Test: Failed to unlink media {sample_media_item_id_1} by IDs.")
            except Exception as e:
                logger.error(f"Test: Error in unlink_media_by_ids for media 1: {e}")

        # Test: Unlink media from asset (by link_id)
        if link_id_2: # Only try if linking was potentially successful
            try:
                if test_crud.unlink_media_from_asset(link_id_2):
                    logger.info(f"Test: Unlinked media link {link_id_2} successfully.")
                else:
                    logger.error(f"Test: Failed to unlink media link {link_id_2}.")
            except Exception as e:
                logger.error(f"Test: Error in unlink_media_from_asset for link_id_2: {e}")

        # Re-link some items for unlink_all_media_from_asset test
        # This section also likely to fail if initial links failed due to FK.
        temp_link_ids_for_cleanup_test = []
        try:
            l_id_a = test_crud.link_media_to_asset(sample_asset_id, sample_media_item_id_1, 0)
            if l_id_a: temp_link_ids_for_cleanup_test.append(l_id_a)
            l_id_b = test_crud.link_media_to_asset(sample_asset_id, sample_media_item_id_2, 1)
            if l_id_b: temp_link_ids_for_cleanup_test.append(l_id_b)
        except Exception: # Catch FK errors
            pass # Already logged during linking attempt

        if temp_link_ids_for_cleanup_test: # Only run if any re-linking worked
            # Test: Unlink all media from asset
            try:
                if test_crud.unlink_all_media_from_asset(sample_asset_id):
                    logger.info(f"Test: Unlinked all media from asset {sample_asset_id}.")
                    remaining_links = test_crud.get_media_links_for_asset(sample_asset_id)
                    if not remaining_links:
                        logger.info("  - Verified: No media links remaining for the asset.")
                    else:
                        logger.error(f"  - Error: {len(remaining_links)} links still found for asset {sample_asset_id}.")
                else:
                    logger.error(f"Test: Failed to unlink all media from asset {sample_asset_id}.")
            except Exception as e:
                logger.error(f"Test: Error in unlink_all_media_from_asset for {sample_asset_id}: {e}")
        else:
            logger.info("Skipping unlink_all_media_from_asset test as re-linking failed (likely due to FK issues).")


        logger.info("AssetMediaLinksCRUD testing finished. Check logs for errors, especially FK constraint violations if sample IDs were not valid.")
    pass
