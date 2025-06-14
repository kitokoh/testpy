import sqlite3
import uuid
from datetime import datetime
import logging
from .generic_crud import GenericCRUD, _manage_conn, get_db_connection # Updated import

# --- Clients CRUD ---
class ClientsCRUD(GenericCRUD):
    """
    Manages CRUD operations for clients, including handling soft deletes,
    client notes, and various client segmentation/reporting queries.
    Inherits from GenericCRUD for basic operations.
    """
    def __init__(self):
        """
        Initializes the ClientsCRUD class, setting the table name and ID column
        for use with GenericCRUD methods.
        """
        self.table_name = "Clients"
        self.id_column = "client_id"

    @_manage_conn
    def add_client(self, data: dict, conn: sqlite3.Connection = None) -> dict:
        """
        Adds a new client to the database.

        Performs input validation for required fields ('client_name', 'created_by_user_id')
        and data types (e.g., 'price'). Sets 'is_deleted' to 0 by default.

        Args:
            data (dict): A dictionary containing client data. Expected keys include:
                         'client_name', 'created_by_user_id', 'company_name' (optional),
                         'primary_need_description' (optional), 'project_identifier' (optional, default 'N/A'),
                         'country_id' (optional), 'city_id' (optional), 'default_base_folder_path' (optional),
                         'status_id' (optional), 'selected_languages' (optional),
                         'price' (optional, default 0), 'notes' (optional), 'category' (optional).
            conn (sqlite3.Connection, optional): Database connection. Managed by decorator if None.

        Returns:
            dict: A dictionary with {'success': True, 'client_id': new_id} on success,
                  or {'success': False, 'error': 'error message'} on failure.
        """
        # Input Validation
        required_fields = ['client_name', 'created_by_user_id']
        for field in required_fields:
            if not data.get(field):
                logging.error(f"Missing required field: {field} in add_client")
                return {'success': False, 'error': f"Missing required field: {field}"}

        if 'price' in data and not isinstance(data['price'], (int, float)):
            logging.error("Invalid data type for price in add_client")
            return {'success': False, 'error': "Invalid data type for price. Must be a number."}

        cursor = conn.cursor()
        new_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"

        # Add is_deleted and deleted_at with default values
        data['is_deleted'] = data.get('is_deleted', 0) # Default to not deleted
        data['deleted_at'] = data.get('deleted_at', None)

        sql = """INSERT INTO Clients
                 (client_id, client_name, company_name, primary_need_description, project_identifier,
                  country_id, city_id, default_base_folder_path, status_id, selected_languages,
                  price, notes, category, created_at, updated_at, created_by_user_id, is_deleted, deleted_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        params = (new_id, data.get('client_name'), data.get('company_name'), data.get('primary_need_description'),
                  data.get('project_identifier', 'N/A'), data.get('country_id'), data.get('city_id'),
                  data.get('default_base_folder_path'), data.get('status_id'),
                  data.get('selected_languages'), data.get('price', 0), data.get('notes'),
                  data.get('category'), now, now, data.get('created_by_user_id'),
                  data['is_deleted'], data['deleted_at'])
        try:
            cursor.execute(sql, params)
            # conn.commit() # Handled by _manage_conn
            return {'success': True, 'client_id': new_id}
        except sqlite3.Error as e:
            logging.error(f"Failed to add client '{data.get('client_name')}': {e}")
            # conn.rollback() # Handled by _manage_conn
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_client_by_id(self, client_id: str, conn: sqlite3.Connection = None, include_deleted: bool = False) -> dict | None:
        """
        Fetches a single client by their client_id.

        Args:
            client_id (str): The UUID of the client to fetch.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted clients.
                                              Defaults to False.

        Returns:
            dict | None: A dictionary representing the client if found and not excluded by
                         soft delete policy, otherwise None.
        """
        query = f"SELECT * FROM {self.table_name} WHERE {self.id_column} = ?"
        params = [client_id]
        if not include_deleted:
            query += " AND (is_deleted IS NULL OR is_deleted = 0)"

        cursor = conn.execute(query, tuple(params))
        row = cursor.fetchone()
        return dict(row) if row else None

    @_manage_conn
    def get_all_clients(self, filters: dict = None, conn: sqlite3.Connection = None, limit: int = None, offset: int = 0, include_deleted: bool = False) -> list[dict]:
        """
        Retrieves all clients, with optional filtering, pagination, and inclusion of
        soft-deleted records.

        Args:
            filters (dict, optional): A dictionary of filters to apply (e.g., {'category': 'Tech'}).
                                      Valid filter keys: 'client_name', 'company_name', 'country_id',
                                      'city_id', 'status_id', 'category', 'created_by_user_id'.
            conn (sqlite3.Connection, optional): Database connection.
            limit (int, optional): Maximum number of records to return for pagination.
            offset (int, optional): Number of records to skip for pagination. Defaults to 0.
            include_deleted (bool, optional): If True, includes soft-deleted clients.
                                              Defaults to False.

        Returns:
            list[dict]: A list of dictionaries, where each dictionary is a client record.
        """
        cursor = conn.cursor()
        sql = f"SELECT * FROM {self.table_name}"
        q_params = []

        conditions = []
        if not include_deleted:
            conditions.append("(is_deleted IS NULL OR is_deleted = 0)")

        if filters:
            valid_filters = ['client_name', 'company_name', 'country_id', 'city_id', 'status_id', 'category', 'created_by_user_id']
            for k, v in filters.items():
                if k in valid_filters:
                    if isinstance(v, str) and k in ['client_name', 'company_name', 'category']:
                        conditions.append(f"{k} LIKE ?")
                        q_params.append(f"%{v}%")
                    else:
                        conditions.append(f"{k} = ?")
                        q_params.append(v)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY client_name" # Default ordering

        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            q_params.extend([limit, offset])

        try:
            cursor.execute(sql, q_params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Failed to get all clients with filters '{filters}': {e}")
            return []

    @_manage_conn
    def update_client(self, client_id: str, client_data: dict, conn: sqlite3.Connection = None) -> dict:
        """
        Updates an existing client's information.

        Validates that `client_id` is provided and that `client_data` is not empty.
        Performs data type validation for fields like 'price'.
        Allows updating of soft delete fields `is_deleted` and `deleted_at`.

        Args:
            client_id (str): The UUID of the client to update.
            client_data (dict): A dictionary containing the client data to update.
                                Keys should correspond to valid column names.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'updated_count': count} if rows were updated,
                  {'success': False, 'error': 'message'} or
                  {'success': True, 'updated_count': 0} if no rows matched or no valid data.
        """
        if not client_id:
            return {'success': False, 'error': "Client ID is required for update."}
        if not client_data:
            return {'success': False, 'error': "No data provided for update."}

        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        client_data['updated_at'] = now

        valid_cols = ['client_name', 'company_name', 'primary_need_description', 'project_identifier',
                      'country_id', 'city_id', 'default_base_folder_path', 'status_id',
                      'selected_languages', 'price', 'notes', 'category', 'updated_at',
                      'created_by_user_id', 'is_deleted', 'deleted_at'] # Added soft delete fields

        data_to_set = {}
        for k, v in client_data.items():
            if k in valid_cols:
                # Basic type validation (example for price)
                if k == 'price' and not isinstance(v, (int, float)) and v is not None:
                    logging.error(f"Invalid data type for price in update_client for client {client_id}")
                    return {'success': False, 'error': "Invalid data type for price. Must be a number."}
                data_to_set[k] = v

        if not data_to_set:
            return {'success': False, 'error': "No valid fields to update."}

        set_clauses = [f"{key} = ?" for key in data_to_set.keys()]
        params = list(data_to_set.values())
        params.append(client_id)
        sql = f"UPDATE {self.table_name} SET {', '.join(set_clauses)} WHERE {self.id_column} = ?"

        try:
            cursor.execute(sql, params)
            # conn.commit() # Handled by _manage_conn
            return {'success': cursor.rowcount > 0, 'updated_count': cursor.rowcount}
        except sqlite3.Error as e:
            logging.error(f"Failed to update client {client_id}: {e}")
            # conn.rollback() # Handled by _manage_conn
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def delete_client(self, client_id: str, conn: sqlite3.Connection = None) -> dict:
        """
        Soft deletes a client by setting `is_deleted = 1` and `deleted_at` to the current UTC timestamp.

        Args:
            client_id (str): The UUID of the client to soft delete.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'message': 'Client soft deleted.'} on success,
                  {'success': False, 'error': 'Client not found or already deleted.'} if no record was updated,
                  {'success': False, 'error': 'DB error message'} on database error.
        """
        if not client_id:
            return {'success': False, 'error': "Client ID is required for deletion."}

        now = datetime.utcnow().isoformat() + "Z"
        # Direct SQL for soft delete operation.
        # Note: This operation marks the client as deleted.
        # Associated entities (like notes) are not automatically soft-deleted by this method.
        cursor = conn.cursor()
        sql = f"UPDATE {self.table_name} SET is_deleted = ?, deleted_at = ? WHERE {self.id_column} = ?"
        params = (1, now, client_id)

        try:
            cursor.execute(sql, params)
            if cursor.rowcount > 0:
                return {'success': True, 'message': f"Client {client_id} soft deleted."}
            else:
                return {'success': False, 'error': f"Client {client_id} not found or already deleted."}
        except sqlite3.Error as e:
            logging.error(f"Failed to soft delete client {client_id}: {e}")
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_all_clients_with_details(self, conn: sqlite3.Connection = None, limit: int = None, offset: int = 0, include_deleted: bool = False) -> list[dict]:
        """
        Retrieves all clients along with details from joined tables (Countries, Cities, StatusSettings).
        Supports pagination and filtering of soft-deleted records.

        Args:
            conn (sqlite3.Connection, optional): Database connection.
            limit (int, optional): Maximum number of records for pagination.
            offset (int, optional): Offset for pagination.
            include_deleted (bool, optional): If True, includes soft-deleted clients. Defaults to False.

        Returns:
            list[dict]: A list of client records with joined details.
        """
        cursor = conn.cursor()
        q_params = []
        query = """
        SELECT c.client_id, c.client_name, c.company_name, c.primary_need_description,
               c.project_identifier, c.default_base_folder_path, c.selected_languages,
               c.price, c.notes, c.created_at, c.category, c.status_id, c.country_id, c.city_id,
               c.is_deleted, c.deleted_at,
               co.country_name AS country, ci.city_name AS city,
               s.status_name AS status, s.color_hex AS status_color, s.icon_name AS status_icon_name
        FROM Clients c
        LEFT JOIN Countries co ON c.country_id = co.country_id
        LEFT JOIN Cities ci ON c.city_id = ci.city_id
        LEFT JOIN StatusSettings s ON c.status_id = s.status_id AND s.status_type = 'Client'
        """

        conditions = []
        if not include_deleted:
            conditions.append("(c.is_deleted IS NULL OR c.is_deleted = 0)")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY c.client_name"

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            q_params.extend([limit, offset])

        try:
            cursor.execute(query, q_params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Failed to get all clients with details: {e}")
            return []

    @_manage_conn
    def get_active_clients_count(self, conn: sqlite3.Connection = None, include_deleted: bool = False) -> int:
        """
        Counts active clients. Active status is determined by `StatusSettings.is_archival_status`.
        Clients with no status are also considered active.

        Args:
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, count includes clients that are soft-deleted
                                              but would otherwise be active. Defaults to False.

        Returns:
            int: The count of active clients.
        """
        cursor = conn.cursor()
        sql = """SELECT COUNT(c.client_id) as active_count
                 FROM Clients c
                 LEFT JOIN StatusSettings ss ON c.status_id = ss.status_id
                 WHERE ((ss.is_archival_status IS NOT TRUE AND ss.is_archival_status != 1) OR c.status_id IS NULL)"""

        if not include_deleted: # If we are not including deleted, add this condition
             sql += " AND (c.is_deleted IS NULL OR c.is_deleted = 0)"

        try:
            cursor.execute(sql)
            row = cursor.fetchone()
            return row['active_count'] if row else 0
        except sqlite3.Error as e:
            logging.error(f"Failed to get active clients count: {e}")
            return 0

    @_manage_conn
    def get_client_counts_by_country(self, conn: sqlite3.Connection = None, include_deleted: bool = False) -> list[dict]:
        """
        Gets client counts grouped by country.

        Args:
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, calculation includes soft-deleted clients.
                                              Defaults to False.

        Returns:
            list[dict]: A list of {'country_name': name, 'client_count': count}.
        """
        cursor = conn.cursor()
        sql = """SELECT co.country_name, COUNT(cl.client_id) as client_count
                 FROM Clients cl
                 JOIN Countries co ON cl.country_id = co.country_id
              """
        conditions = []
        if not include_deleted:
            conditions.append("(cl.is_deleted IS NULL OR cl.is_deleted = 0)")

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += """
                 GROUP BY co.country_name
                 HAVING COUNT(cl.client_id) > 0
                 ORDER BY client_count DESC"""
        try:
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Failed to get client counts by country: {e}")
            return []

    @_manage_conn
    def get_client_segmentation_by_city(self, conn: sqlite3.Connection = None, include_deleted: bool = False) -> list[dict]:
        """
        Gets client counts grouped by country and city.

        Args:
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, calculation includes soft-deleted clients.
                                              Defaults to False.

        Returns:
            list[dict]: A list of {'country_name': c_name, 'city_name': ci_name, 'client_count': count}.
        """
        cursor = conn.cursor()
        sql = """SELECT co.country_name, ci.city_name, COUNT(cl.client_id) as client_count
                 FROM Clients cl
                 JOIN Cities ci ON cl.city_id = ci.city_id
                 JOIN Countries co ON ci.country_id = co.country_id
              """
        conditions = []
        if not include_deleted:
            conditions.append("(cl.is_deleted IS NULL OR cl.is_deleted = 0)")

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += """
                 GROUP BY co.country_name, ci.city_name
                 HAVING COUNT(cl.client_id) > 0
                 ORDER BY co.country_name, client_count DESC, ci.city_name"""
        try:
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Failed to get client segmentation by city: {e}")
            return []

    @_manage_conn
    def get_client_segmentation_by_status(self, conn: sqlite3.Connection = None, include_deleted: bool = False) -> list[dict]:
        """
        Gets client counts grouped by status name.

        Args:
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, calculation includes soft-deleted clients.
                                              Defaults to False.

        Returns:
            list[dict]: A list of {'status_name': name, 'client_count': count}.
        """
        cursor = conn.cursor()

        conditions = ["(ss.status_type = 'Client')"] # Initial condition for status type
        if not include_deleted:
            conditions.append("(cl.is_deleted IS NULL OR cl.is_deleted = 0)")

        sql = f"""SELECT ss.status_name, COUNT(cl.client_id) as client_count
                  FROM Clients cl
                  JOIN StatusSettings ss ON cl.status_id = ss.status_id
                  WHERE {' AND '.join(conditions)}
                  GROUP BY ss.status_name
                  HAVING COUNT(cl.client_id) > 0
                  ORDER BY client_count DESC, ss.status_name"""
        try:
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Failed to get client segmentation by status: {e}")
            return []

    @_manage_conn
    def get_client_segmentation_by_category(self, conn: sqlite3.Connection = None, include_deleted: bool = False) -> list[dict]:
        """
        Gets client counts grouped by category.

        Args:
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, calculation includes soft-deleted clients.
                                              Defaults to False.

        Returns:
            list[dict]: A list of {'category': name, 'client_count': count}.
        """
        cursor = conn.cursor()

        conditions = ["(cl.category IS NOT NULL AND cl.category != '')"] # Initial category filter
        if not include_deleted:
            conditions.append("(cl.is_deleted IS NULL OR cl.is_deleted = 0)")

        sql = f"""SELECT cl.category, COUNT(cl.client_id) as client_count
                  FROM Clients cl
                  WHERE {' AND '.join(conditions)}
                  GROUP BY cl.category
                  HAVING COUNT(cl.client_id) > 0
                  ORDER BY client_count DESC, cl.category"""
        try:
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Failed to get client segmentation by category: {e}")
            return []

    @_manage_conn
    def get_clients_by_archival_status(self, is_archived: bool, include_null_status_for_active: bool = True, conn: sqlite3.Connection = None, include_deleted: bool = False) -> list[dict]:
        """
        Retrieves clients based on their archival status (derived from StatusSettings).

        Args:
            is_archived (bool): If True, fetches archived clients. If False, fetches active clients.
            include_null_status_for_active (bool, optional): If True and fetching active clients,
                                                             includes clients with no status_id. Defaults to True.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted clients that match
                                              the archival status criteria. Defaults to False.

        Returns:
            list[dict]: A list of client records.
        """
        cursor = conn.cursor(); params = []
        try:
            cursor.execute("SELECT status_id FROM StatusSettings WHERE status_type = 'Client' AND (is_archival_status = TRUE OR is_archival_status = 1)")
            archival_ids_tuples = cursor.fetchall()
            archival_ids = [row['status_id'] for row in archival_ids_tuples]

            base_query = """SELECT c.*, co.country_name AS country, ci.city_name AS city,
                            s.status_name AS status, s.color_hex AS status_color, s.icon_name AS status_icon_name
                            FROM Clients c
                            LEFT JOIN Countries co ON c.country_id = co.country_id
                            LEFT JOIN Cities ci ON c.city_id = ci.city_id
                            LEFT JOIN StatusSettings s ON c.status_id = s.status_id AND s.status_type = 'Client'"""
            conditions = []

            if not include_deleted:
                conditions.append("(c.is_deleted IS NULL OR c.is_deleted = 0)")

            if not archival_ids:
                if is_archived: return []
                # else no specific status condition if no archival statuses are defined
            else:
                placeholders = ','.join('?' for _ in archival_ids)
                if is_archived:
                    conditions.append(f"c.status_id IN ({placeholders})")
                    params.extend(archival_ids)
                else:
                    not_in_cond = f"c.status_id NOT IN ({placeholders})"
                    if include_null_status_for_active:
                        conditions.append(f"({not_in_cond} OR c.status_id IS NULL)")
                    else:
                        conditions.append(not_in_cond)
                    params.extend(archival_ids)

            sql = f"{base_query} {'WHERE ' + ' AND '.join(conditions) if conditions else ''} ORDER BY c.client_name;"
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Failed to get clients by archival status (is_archived={is_archived}): {e}")
            return []

    @_manage_conn
    def get_active_clients_per_country(self, conn: sqlite3.Connection = None, include_deleted: bool = False) -> dict:
        """
        Retrieves active clients, mapping them by country.

        Args:
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted clients in the map.
                                              Defaults to False.

        Returns:
            dict: A dictionary where keys are country names and values are lists of
                  client details ({'client_id', 'client_name'}).
        """
        cursor = conn.cursor()
        clients_by_country_map = {}
        try:
            cursor.execute("SELECT status_id FROM StatusSettings WHERE (is_archival_status = TRUE OR is_archival_status = 1) AND status_type = 'Client'")
            archival_status_ids_tuples = cursor.fetchall()
            archival_status_ids = [row['status_id'] for row in archival_status_ids_tuples]

            query_parts = [
                "SELECT",
                "    co.country_name,",
                "    cl.client_id,",
                "    cl.client_name",
                "FROM Clients cl",
                "JOIN Countries co ON cl.country_id = co.country_id"
            ]
            params_for_query = []

            conditions = []
            if not include_deleted:
                conditions.append("(cl.is_deleted IS NULL OR cl.is_deleted = 0)")

            if archival_status_ids:
                placeholders = ','.join('?' for _ in archival_status_ids)
                conditions.append(f"(cl.status_id IS NULL OR cl.status_id NOT IN ({placeholders}))")
                params_for_query.extend(archival_status_ids)

            if conditions:
                query_parts.append(f"WHERE {' AND '.join(conditions)}")


            query_parts.append("ORDER BY co.country_name, cl.client_name;")
            query = "\n".join(query_parts)

            cursor.execute(query, params_for_query)

            for row in cursor.fetchall():
                country = row['country_name']
                client_detail = {'client_id': row['client_id'], 'client_name': row['client_name']}
                if country not in clients_by_country_map:
                    clients_by_country_map[country] = []
                clients_by_country_map[country].append(client_detail)
        except sqlite3.Error as e:
            logging.error(f"Failed to get active clients per country: {e}")
        return clients_by_country_map

    # --- ClientNotes CRUD ---
    @_manage_conn
    def add_client_note(self, client_id: str, note_text: str, user_id: str = None, conn: sqlite3.Connection = None) -> dict:
        """
        Adds a note for a specific client.

        Args:
            client_id (str): The UUID of the client.
            note_text (str): The content of the note.
            user_id (str, optional): The UUID of the user adding the note.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'note_id': new_id} on success,
                  {'success': False, 'error': 'message'} on failure.
        """
        if not client_id or not note_text:
             return {'success': False, 'error': "Client ID and note text are required."}
        cursor = conn.cursor()
        sql = "INSERT INTO ClientNotes (client_id, note_text, user_id, timestamp) VALUES (?, ?, ?, ?)"
        now = datetime.utcnow().isoformat() + "Z"
        try:
            cursor.execute(sql, (client_id, note_text, user_id, now))
            return {'success': True, 'note_id': cursor.lastrowid}
        except sqlite3.Error as e:
            logging.error(f"Failed to add client note for client {client_id}: {e}")
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_client_notes(self, client_id: str, conn: sqlite3.Connection = None) -> list[dict]:
        """
        Retrieves all notes for a specific client, ordered by timestamp descending.
        Client notes are not subject to the client's soft delete status directly;
        they are always retrieved if the client_id exists.

        Args:
            client_id (str): The UUID of the client.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            list[dict]: A list of note records.
        """
        cursor = conn.cursor()
        sql = "SELECT note_id, client_id, timestamp, note_text, user_id FROM ClientNotes WHERE client_id = ? ORDER BY timestamp DESC"
        try:
            cursor.execute(sql, (client_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Failed to get client notes for client {client_id}: {e}")
            return []

# Instantiate the CRUD class for easy import and use elsewhere
clients_crud_instance = ClientsCRUD()

# Expose specific CRUD methods for direct import
get_all_clients = clients_crud_instance.get_all_clients
get_client_by_id = clients_crud_instance.get_client_by_id
add_client = clients_crud_instance.add_client
update_client = clients_crud_instance.update_client
delete_client = clients_crud_instance.delete_client
get_all_clients_with_details = clients_crud_instance.get_all_clients_with_details
get_active_clients_count = clients_crud_instance.get_active_clients_count
get_client_counts_by_country = clients_crud_instance.get_client_counts_by_country
get_client_segmentation_by_city = clients_crud_instance.get_client_segmentation_by_city
get_client_segmentation_by_status = clients_crud_instance.get_client_segmentation_by_status
get_client_segmentation_by_category = clients_crud_instance.get_client_segmentation_by_category
get_clients_by_archival_status = clients_crud_instance.get_clients_by_archival_status
get_active_clients_per_country = clients_crud_instance.get_active_clients_per_country
add_client_note = clients_crud_instance.add_client_note
get_client_notes = clients_crud_instance.get_client_notes

__all__ = [
    "add_client",
    "get_client_by_id",
    "get_all_clients",
    "update_client",
    "delete_client", # Soft delete
    "get_all_clients_with_details",
    "get_active_clients_count",
    "get_client_counts_by_country",
    "get_client_segmentation_by_city",
    "get_client_segmentation_by_status",
    "get_client_segmentation_by_category",
    "get_clients_by_archival_status",
    "get_active_clients_per_country",
    "add_client_note",
    "get_client_notes",
    "ClientsCRUD", # Exporting the class itself for type hinting or direct instantiation
    "clients_crud_instance" # Exporting the instance if needed elsewhere
]
