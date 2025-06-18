import sqlite3
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from ..database_manager import get_db_connection
# GenericCRUD might not be directly used if methods are highly custom,
# but can be a base if some simple operations align.
# For this, operations are quite custom due to multiple tables.
# from .generic_crud import GenericCRUD

# Configure logging
logger = logging.getLogger(__name__)

class ReportConfigurationsCRUD:
    """
    CRUD operations for ReportConfigurations and related tables.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.main_table = "ReportConfigurations"
        self.fields_table = "ReportConfigFields"
        self.filters_table = "ReportConfigFilters"

    def _execute_query(self, query: str, params: tuple = (), conn: Optional[sqlite3.Connection] = None, fetch_one: bool = False, fetch_all: bool = False, commit: bool = False) -> Any:
        """Helper to execute queries, managing connection if not provided."""
        # This helper is more for SELECTs or simple ops. Transactions need careful handling of conn.
        db_conn_internal = None
        if conn is None:
            db_conn_internal = get_db_connection(self.db_path)
            conn_to_use = db_conn_internal
        else:
            conn_to_use = conn

        cursor = conn_to_use.cursor()
        try:
            cursor.execute(query, params)
            if commit:
                if db_conn_internal: # Only commit if this function owns the connection
                    db_conn_internal.commit()
                # If conn was passed, caller handles commit.
                return cursor.lastrowid if cursor.lastrowid else True

            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            return cursor # Should typically not return raw cursor unless for specific iteration

        except sqlite3.Error as e:
            logger.error(f"Database error for query '{query[:100]}...': {e}", exc_info=True)
            # Do not rollback here if conn was passed; caller handles transaction.
            raise
        finally:
            if db_conn_internal: # Close only if this function opened it
                db_conn_internal.close()


    def add_report_configuration(self, config_data: dict, fields_data: List[dict], filters_data: List[dict], conn_ext: Optional[sqlite3.Connection] = None) -> Optional[str]:
        """
        Adds a new report configuration with its fields and filters in a single transaction.
        Returns the report_config_id or None on error.
        """
        report_config_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = conn_ext if conn_ext else get_db_connection(self.db_path)
        cursor = conn.cursor()

        try:
            # Insert into ReportConfigurations
            cfg_sql = f"""
                INSERT INTO {self.main_table}
                (report_config_id, report_name, description, target_entity, output_format,
                 created_by_user_id, created_at, updated_at, is_system_report)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(cfg_sql, (
                report_config_id,
                config_data.get('report_name'),
                config_data.get('description'),
                config_data.get('target_entity'),
                config_data.get('output_format'),
                config_data.get('created_by_user_id'),
                now_iso,
                now_iso,
                config_data.get('is_system_report', False)
            ))

            # Insert into ReportConfigFields
            if fields_data:
                fld_sql = f"""
                    INSERT INTO {self.fields_table}
                    (report_config_id, field_name, display_name, sort_order, sort_direction, group_by_priority)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                for field in fields_data:
                    cursor.execute(fld_sql, (
                        report_config_id,
                        field.get('field_name'),
                        field.get('display_name'),
                        field.get('sort_order', 0),
                        field.get('sort_direction'),
                        field.get('group_by_priority', 0)
                    ))

            # Insert into ReportConfigFilters
            if filters_data:
                flt_sql = f"""
                    INSERT INTO {self.filters_table}
                    (report_config_id, field_name, operator, filter_value_1, filter_value_2, logical_group)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                for flt_filter in filters_data: # Renamed to avoid conflict with built-in filter
                    cursor.execute(flt_sql, (
                        report_config_id,
                        flt_filter.get('field_name'),
                        flt_filter.get('operator'),
                        flt_filter.get('filter_value_1'),
                        flt_filter.get('filter_value_2'),
                        flt_filter.get('logical_group', 'AND')
                    ))

            if not conn_ext: # If we created the connection, we manage the transaction.
                conn.commit()
            logger.info(f"Report configuration '{report_config_id}' added successfully.")
            return report_config_id

        except sqlite3.Error as e:
            logger.error(f"Error adding report configuration '{config_data.get('report_name')}': {e}", exc_info=True)
            if not conn_ext:
                conn.rollback()
            return None
        finally:
            if not conn_ext: # Close only if we opened it.
                conn.close()

    def get_report_configuration_by_id(self, report_config_id: str, conn_ext: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
        """Fetches a full report configuration including fields and filters."""
        conn = conn_ext if conn_ext else get_db_connection(self.db_path)
        conn.row_factory = sqlite3.Row # Ensure dict-like rows
        cursor = conn.cursor()

        result = None
        try:
            # Fetch main configuration
            cursor.execute(f"SELECT * FROM {self.main_table} WHERE report_config_id = ?", (report_config_id,))
            config_row = cursor.fetchone()
            if not config_row:
                return None

            result = dict(config_row)

            # Fetch fields
            cursor.execute(f"SELECT * FROM {self.fields_table} WHERE report_config_id = ? ORDER BY sort_order, report_config_field_id", (report_config_id,))
            result['fields'] = [dict(row) for row in cursor.fetchall()]

            # Fetch filters
            cursor.execute(f"SELECT * FROM {self.filters_table} WHERE report_config_id = ? ORDER BY report_config_filter_id", (report_config_id,))
            result['filters'] = [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Error fetching report configuration by ID '{report_config_id}': {e}", exc_info=True)
            return None # Error occurred
        finally:
            if not conn_ext:
                conn.close()
        return result

    def get_report_configuration_by_name(self, report_name: str, conn_ext: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
        """Fetches a full report configuration by its unique name."""
        conn = conn_ext if conn_ext else get_db_connection(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(f"SELECT report_config_id FROM {self.main_table} WHERE report_name = ?", (report_name,))
            config_id_row = cursor.fetchone()
            if not config_id_row:
                return None
            return self.get_report_configuration_by_id(config_id_row['report_config_id'], conn_ext=conn) # Pass existing conn if any
        except sqlite3.Error as e:
            logger.error(f"Error finding report configuration ID by name '{report_name}': {e}", exc_info=True)
            return None
        finally:
            if not conn_ext: # Close only if we opened it AND it wasn't passed to get_report_configuration_by_id
                conn.close()


    def get_all_report_configurations(self, user_id: Optional[str] = None, include_system_reports: bool = True, conn_ext: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
        """
        Fetches all report configurations (main details only).
        Optionally filter by user_id and inclusion of system reports.
        """
        conn = conn_ext if conn_ext else get_db_connection(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = f"SELECT * FROM {self.main_table}"
        conditions = []
        params = []

        if user_id is not None:
            # Show reports created by the user OR system reports (if include_system_reports is True)
            if include_system_reports:
                conditions.append("(created_by_user_id = ? OR is_system_report = 1)")
                params.append(user_id)
            else: # Only user-specific, non-system reports
                conditions.append("created_by_user_id = ? AND is_system_report = 0")
                params.append(user_id)
        elif not include_system_reports: # No user_id given, but exclude system reports
            conditions.append("is_system_report = 0")
        # If user_id is None and include_system_reports is True, no condition needed based on these flags.

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY report_name ASC"

        try:
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching all report configurations: {e}", exc_info=True)
            return []
        finally:
            if not conn_ext:
                conn.close()

    def update_report_configuration(self, report_config_id: str, config_data: Optional[dict] = None, fields_data: Optional[List[dict]] = None, filters_data: Optional[List[dict]] = None, conn_ext: Optional[sqlite3.Connection] = None) -> bool:
        """
        Updates a report configuration. Fields and filters are replaced entirely if provided.
        Transactional operation.
        """
        conn = conn_ext if conn_ext else get_db_connection(self.db_path)
        cursor = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            # Update ReportConfigurations table if config_data is provided
            if config_data:
                # Ensure updated_at is set
                config_data['updated_at'] = now_iso

                set_clauses = []
                params = []
                for key, value in config_data.items():
                    # Basic whitelist of updatable fields in main config table
                    if key in ['report_name', 'description', 'target_entity', 'output_format', 'is_system_report', 'updated_at']:
                        set_clauses.append(f"{key} = ?")
                        params.append(value)

                if set_clauses:
                    params.append(report_config_id)
                    cfg_sql = f"UPDATE {self.main_table} SET {', '.join(set_clauses)} WHERE report_config_id = ?"
                    cursor.execute(cfg_sql, tuple(params))

            # Replace fields if fields_data is provided (even if empty list)
            if fields_data is not None:
                cursor.execute(f"DELETE FROM {self.fields_table} WHERE report_config_id = ?", (report_config_id,))
                if fields_data: # If not empty list, insert new ones
                    fld_sql = f"""
                        INSERT INTO {self.fields_table}
                        (report_config_id, field_name, display_name, sort_order, sort_direction, group_by_priority)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """
                    for field in fields_data:
                        cursor.execute(fld_sql, (
                            report_config_id, field.get('field_name'), field.get('display_name'),
                            field.get('sort_order', 0), field.get('sort_direction'), field.get('group_by_priority', 0)
                        ))

            # Replace filters if filters_data is provided (even if empty list)
            if filters_data is not None:
                cursor.execute(f"DELETE FROM {self.filters_table} WHERE report_config_id = ?", (report_config_id,))
                if filters_data: # If not empty list, insert new ones
                    flt_sql = f"""
                        INSERT INTO {self.filters_table}
                        (report_config_id, field_name, operator, filter_value_1, filter_value_2, logical_group)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """
                    for flt_filter in filters_data:
                        cursor.execute(flt_sql, (
                            report_config_id, flt_filter.get('field_name'), flt_filter.get('operator'),
                            flt_filter.get('filter_value_1'), flt_filter.get('filter_value_2'), flt_filter.get('logical_group', 'AND')
                        ))

            if not conn_ext:
                conn.commit()
            logger.info(f"Report configuration '{report_config_id}' updated successfully.")
            return True

        except sqlite3.Error as e:
            logger.error(f"Error updating report configuration '{report_config_id}': {e}", exc_info=True)
            if not conn_ext:
                conn.rollback()
            return False
        finally:
            if not conn_ext:
                conn.close()

    def delete_report_configuration(self, report_config_id: str, conn_ext: Optional[sqlite3.Connection] = None) -> bool:
        """
        Deletes a report configuration. Associated fields and filters are deleted by CASCADE.
        """
        conn = conn_ext if conn_ext else get_db_connection(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(f"DELETE FROM {self.main_table} WHERE report_config_id = ?", (report_config_id,))
            if not conn_ext:
                conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Report configuration '{report_config_id}' deleted successfully.")
                return True
            else:
                logger.warning(f"Report configuration '{report_config_id}' not found for deletion.")
                return False # Not found, so not deleted by this call.
        except sqlite3.Error as e:
            logger.error(f"Error deleting report configuration '{report_config_id}': {e}", exc_info=True)
            if not conn_ext:
                conn.rollback()
            return False
        finally:
            if not conn_ext:
                conn.close()

# Instance for easy import
report_configurations_crud = ReportConfigurationsCRUD()

__all__ = [
    "ReportConfigurationsCRUD",
    "report_configurations_crud"
]
