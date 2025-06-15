import sqlite3 # Keep for type hinting if conn is directly manipulated, though _manage_conn handles it.
import logging
import uuid # For generating document_id
from .generic_crud import _manage_conn, get_db_connection # get_db_connection might not be needed if _manage_conn is sufficient

# Configure logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- ClientDocuments ---
@_manage_conn
def add_client_document(data: dict, conn: sqlite3.Connection = None) -> str | None:
    """
    Adds a new client document entry to the ClientDocuments table.

    Args:
        data (dict): A dictionary containing the document metadata. Expected keys:
            'client_id': (str) ID of the client.
            'document_name': (str) Name of the document.
            'file_name_on_disk': (str) The actual name of the file stored on disk.
            'file_path_relative': (str) The path to the file, relative to a base client directory.
            'document_type_generated': (str) Type of document (e.g., 'invoice_pdf', 'report_pdf').
            'source_template_id': (int) ID of the template used to generate this document.
            'user_id': (str) ID of the user creating this document (maps to created_by_user_id).
            Optional keys:
            'project_id': (str, optional) ID of the associated project.
            'order_identifier': (str, optional) Specific order ID related to this document.
            'version_tag': (str, optional) A version tag or number for the document.
            'notes': (str, optional) Any notes related to the document.
        conn (sqlite3.Connection, optional): SQLite connection object. Provided by _manage_conn.

    Returns:
        str | None: The newly generated document_id if successful, otherwise None.
    """
    new_document_id = str(uuid.uuid4())
    cursor = conn.cursor()

    sql = """
        INSERT INTO ClientDocuments (
            document_id, client_id, project_id, order_identifier,
            document_name, file_name_on_disk, file_path_relative,
            document_type_generated, source_template_id,
            version_tag, notes, created_by_user_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        new_document_id,
        data.get('client_id'),
        data.get('project_id'), # Optional
        data.get('order_identifier'), # Optional
        data.get('document_name'),
        data.get('file_name_on_disk'),
        data.get('file_path_relative'),
        data.get('document_type_generated'),
        data.get('source_template_id'),
        data.get('version_tag'), # Optional
        data.get('notes'), # Optional
        data.get('user_id') # This is from doc_metadata and maps to created_by_user_id
    )

    try:
        cursor.execute(sql, params)
        # conn.commit() # Handled by _manage_conn decorator if it's configured to do so
        logging.info(f"Successfully added client document with ID: {new_document_id} for client: {data.get('client_id')}")
        return new_document_id
    except sqlite3.Error as e:
        logging.error(f"Error adding client document for client {data.get('client_id')}: {e} - SQL: {sql} - Params: {params}")
        # conn.rollback() # Handled by _manage_conn decorator if it's configured to do so
        return None

@_manage_conn
def delete_client_document(document_id: str, conn: sqlite3.Connection = None) -> bool:
    """
    Deletes a client document by its document_id.
    STUB FUNCTION - Full implementation pending.
    """
    # Changed document_id type hint to str to match new_document_id type
    logging.warning(f"Called stub function delete_client_document for document_id: {document_id}. Full implementation is missing.")
    # Example:
    # cursor = conn.cursor()
    # try:
    #     cursor.execute("DELETE FROM ClientDocuments WHERE document_id = ?", (document_id,))
    #     return cursor.rowcount > 0 # Returns True if a row was deleted
    # except sqlite3.Error as e:
    #     logging.error(f"Stub delete_client_document error for {document_id}: {e}")
    #     return False
    return False

@_manage_conn
def get_document_by_id(document_id: str, conn: sqlite3.Connection = None) -> dict | None:
    """
    Retrieves a client document by its document_id.
    STUB FUNCTION - Full implementation pending.
    """
    # Changed document_id type hint to str
    logging.warning(f"Called stub function get_document_by_id for ID: {document_id}. Full implementation is missing.")
    # Example:
    # cursor = conn.cursor()
    # cursor.execute("SELECT * FROM ClientDocuments WHERE document_id = ?", (document_id,))
    # row = cursor.fetchone()
    # if row:
    #     # Convert row to dict if conn.row_factory is not set to sqlite3.Row
    #     # Assuming it is for now, or that dict conversion is handled
    #     return dict(row)
    # return None
    return {'document_id': document_id, 'client_id': 'dummy_client_id', 'file_path_relative': 'dummy/path.pdf', 'file_name_on_disk': 'dummy.pdf'} # Placeholder for API to work

@_manage_conn
def get_documents_for_client(client_id: str, filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    """
    Retrieves all documents for a specific client, with optional filtering.

    Args:
        client_id (str): The ID of the client whose documents are to be retrieved.
        filters (dict, optional): A dictionary for filtering results.
            Supported filters:
            - 'order_identifier':
                - 'NONE': Retrieves documents where order_identifier IS NULL.
                - 'ALL': Retrieves all documents regardless of order_identifier (or if key is missing).
                - Any other string: Retrieves documents matching that specific order_identifier.
        conn (sqlite3.Connection, optional): SQLite connection object. Provided by _manage_conn.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents a document.
                    Returns an empty list if no documents are found or in case of an error.
    """
    if not client_id:
        logging.error("get_documents_for_client: client_id cannot be empty.")
        return []

    try:
        # Assuming conn.row_factory = sqlite3.Row is set by _manage_conn or globally
        # If not, dict conversion would be more manual:
        # e.g., columns = [col[0] for col in cursor.description]
        # then for row in rows: result.append(dict(zip(columns, row)))

        sql = "SELECT * FROM ClientDocuments WHERE client_id = ?"
        params = [client_id]

        if filters:
            order_identifier_filter = filters.get('order_identifier')
            if order_identifier_filter == 'NONE':
                sql += " AND order_identifier IS NULL"
            elif order_identifier_filter and order_identifier_filter != 'ALL':
                sql += " AND order_identifier = ?"
                params.append(order_identifier_filter)
            # If 'ALL' or not provided, no additional order_identifier filter is applied

        sql += " ORDER BY created_at DESC"

        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        # Convert rows to dicts (assuming conn.row_factory = sqlite3.Row)
        return [dict(row) for row in rows]

    except sqlite3.Error as e:
        logging.error(f"Error retrieving documents for client {client_id} with filters {filters}: {e} - SQL: {sql} - Params: {params}")
        return []
    except Exception as e: # Catch any other unexpected errors
        logging.error(f"Unexpected error in get_documents_for_client for client {client_id}: {e}")
        return []

@_manage_conn
def get_documents_for_project(project_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    """
    Retrieves all documents for a specific project.
    STUB FUNCTION - Full implementation pending.
    """
    logging.warning(f"Called stub function get_documents_for_project for project_id: {project_id}. Full implementation is missing.")
    return []

@_manage_conn
def update_client_document(document_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    """
    Updates a client document.
    STUB FUNCTION - Full implementation pending.
    """
    # Changed document_id type hint to str
    logging.warning(f"Called stub function update_client_document for document_id: {document_id} with data: {data}. Full implementation is missing.")
    return False

# --- ClientDocumentNotes CRUD ---
# (Keep existing ClientDocumentNotes functions as they are, assuming they are not part of this subtask)
@_manage_conn
def get_client_document_notes(client_id: str, document_type: str = None, language_code: str = None, is_active: bool = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor(); sql="SELECT * FROM ClientDocumentNotes WHERE client_id = ?"; params=[client_id]
    if document_type: sql+=" AND document_type = ?"; params.append(document_type)
    if language_code: sql+=" AND language_code = ?"; params.append(language_code)
    if is_active is not None: sql+=" AND is_active = ?"; params.append(1 if is_active else 0)
    sql+=" ORDER BY created_at DESC";
    try:
        cursor.execute(sql,params)
        # Assuming conn.row_factory = sqlite3.Row is set globally for the connection
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error getting client document notes for client {client_id}: {e}")
        return []

@_manage_conn
def add_client_document_note(data: dict, conn: sqlite3.Connection = None) -> int | None:
    logging.warning(f"Called stub function add_client_document_note with data {data}. Full implementation is missing.")
    return None

@_manage_conn
def update_client_document_note(note_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    logging.warning(f"Called stub function update_client_document_note for note_id {note_id} with data {data}. Full implementation is missing.")
    return False

@_manage_conn
def delete_client_document_note(note_id: int, conn: sqlite3.Connection = None) -> bool:
    logging.warning(f"Called stub function delete_client_document_note for note_id {note_id}. Full implementation is missing.")
    return False

@_manage_conn
def get_client_document_note_by_id(note_id: int, conn: sqlite3.Connection = None) -> dict | None:
    logging.warning(f"Called stub function get_client_document_note_by_id for note_id {note_id}. Full implementation is missing.")
    return None
