import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any

from db.connection import get_db_connection

# --- Company Facture CRUD Operations ---

def add_company_facture(
    original_file_name: str,
    stored_file_path: str,
    file_mime_type: Optional[str] = None,
    extraction_status: str = 'pending_review',
    extracted_data_json: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> Optional[int]:
    """Adds a new company facture record to the database."""
    close_conn_locally = False
    if conn is None:
        conn = get_db_connection()
        close_conn_locally = True

    try:
        cursor = conn.cursor()
        current_time = datetime.now()
        cursor.execute("""
            INSERT INTO company_factures (
                original_file_name, stored_file_path, file_mime_type,
                extraction_status, extracted_data_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            original_file_name, stored_file_path, file_mime_type,
            extraction_status, extracted_data_json, current_time, current_time
        ))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_company_facture: {e}")
        return None
    finally:
        if close_conn_locally and conn:
            conn.close()

def get_company_facture_by_id(facture_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a company facture by its ID."""
    close_conn_locally = False
    if conn is None:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        close_conn_locally = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM company_factures WHERE facture_id = ? AND is_deleted = 0", (facture_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_company_facture_by_id: {e}")
        return None
    finally:
        if close_conn_locally and conn:
            conn.close()

def update_company_facture(
    facture_id: int,
    original_file_name: Optional[str] = None,
    stored_file_path: Optional[str] = None,
    file_mime_type: Optional[str] = None,
    extraction_status: Optional[str] = None,
    extracted_data_json: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> bool:
    """Updates an existing company facture."""
    close_conn_locally = False
    if conn is None:
        conn = get_db_connection()
        close_conn_locally = True

    fields_to_update = []
    params = []

    if original_file_name is not None:
        fields_to_update.append("original_file_name = ?")
        params.append(original_file_name)
    if stored_file_path is not None:
        fields_to_update.append("stored_file_path = ?")
        params.append(stored_file_path)
    if file_mime_type is not None:
        fields_to_update.append("file_mime_type = ?")
        params.append(file_mime_type)
    if extraction_status is not None:
        fields_to_update.append("extraction_status = ?")
        params.append(extraction_status)
    if extracted_data_json is not None:
        fields_to_update.append("extracted_data_json = ?")
        params.append(extracted_data_json)

    if not fields_to_update:
        return False # Nothing to update

    fields_to_update.append("updated_at = ?")
    params.append(datetime.now())
    params.append(facture_id)

    sql = f"UPDATE company_factures SET {', '.join(fields_to_update)} WHERE facture_id = ? AND is_deleted = 0"

    try:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_company_facture: {e}")
        return False
    finally:
        if close_conn_locally and conn:
            conn.close()

def soft_delete_company_facture(facture_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Soft deletes a company facture by setting is_deleted to 1 and updating deleted_at."""
    close_conn_locally = False
    if conn is None:
        conn = get_db_connection()
        close_conn_locally = True

    try:
        cursor = conn.cursor()
        current_time = datetime.now()
        cursor.execute("""
            UPDATE company_factures
            SET is_deleted = 1, deleted_at = ?, updated_at = ?
            WHERE facture_id = ? AND is_deleted = 0
        """, (current_time, current_time, facture_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in soft_delete_company_facture: {e}")
        return False
    finally:
        if close_conn_locally and conn:
            conn.close()

# --- Company Expense CRUD Operations ---

def add_company_expense(
    expense_date: str, # YYYY-MM-DD
    amount: float,
    currency: str,
    recipient_name: str,
    description: Optional[str] = None,
    facture_id: Optional[int] = None,
    created_by_user_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> Optional[int]:
    """Adds a new company expense to the database."""
    close_conn_locally = False
    if conn is None:
        conn = get_db_connection()
        close_conn_locally = True

    try:
        cursor = conn.cursor()
        current_time = datetime.now()
        # Ensure expense_date is in the correct format for SQLite DATE type (YYYY-MM-DD)
        # The input is expected to be a string already.

        cursor.execute("""
            INSERT INTO company_expenses (
                expense_date, amount, currency, recipient_name, description,
                facture_id, created_by_user_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            expense_date, amount, currency, recipient_name, description,
            facture_id, created_by_user_id, current_time, current_time
        ))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_company_expense: {e}")
        # Consider logging the error more formally if this were a production system
        return None
    finally:
        if close_conn_locally and conn:
            conn.close()

def get_company_expense_by_id(expense_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a company expense by its ID."""
    close_conn_locally = False
    if conn is None:
        conn = get_db_connection()
        # Set row_factory for the connection if we are creating it here
        conn.row_factory = sqlite3.Row
        close_conn_locally = True

    try:
        # If conn was passed, assume row_factory is already set or handled by caller
        # For consistency, ensure cursor operations can handle dict access
        # This requires sqlite3.Row to be set on the connection.
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM company_expenses WHERE expense_id = ? AND is_deleted = 0", (expense_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_company_expense_by_id: {e}")
        return None
    finally:
        if close_conn_locally and conn:
            conn.close()

def get_all_company_expenses(
    limit: int = 100,
    offset: int = 0,
    recipient_name: Optional[str] = None,
    date_from: Optional[str] = None, # YYYY-MM-DD
    date_to: Optional[str] = None,   # YYYY-MM-DD
    description_keywords: Optional[str] = None,
    facture_id: Optional[int] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    currency: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """Retrieves all non-deleted company expenses with pagination and filtering."""
    close_conn_locally = False
    if conn is None:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        close_conn_locally = True

    expenses_list = []
    params = []

    sql = "SELECT * FROM company_expenses WHERE is_deleted = 0"

    if recipient_name:
        sql += " AND recipient_name LIKE ?"
        params.append(f"%{recipient_name}%")
    if date_from:
        sql += " AND expense_date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND expense_date <= ?"
        params.append(date_to)
    if description_keywords:
        # Simple keyword search, could be more advanced (e.g., FTS5)
        sql += " AND description LIKE ?"
        params.append(f"%{description_keywords}%")
    if facture_id is not None:
        sql += " AND facture_id = ?"
        params.append(facture_id)
    if min_amount is not None:
        sql += " AND amount >= ?"
        params.append(min_amount)
    if max_amount is not None:
        sql += " AND amount <= ?"
        params.append(max_amount)
    if currency:
        sql += " AND currency = ?"
        params.append(currency.upper())

    sql += " ORDER BY expense_date DESC, created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    try:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        for row in rows:
            expenses_list.append(dict(row))
        return expenses_list
    except sqlite3.Error as e:
        print(f"Database error in get_all_company_expenses: {e}")
        return []
    finally:
        if close_conn_locally and conn:
            conn.close()

def get_all_company_factures(
    limit: int = 100,
    offset: int = 0,
    original_file_name_like: Optional[str] = None,
    extraction_status: Optional[str] = None,
    upload_date_from: Optional[str] = None, # YYYY-MM-DD
    upload_date_to: Optional[str] = None,   # YYYY-MM-DD
    conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """Retrieves all non-deleted company factures with pagination and filtering."""
    close_conn_locally = False
    if conn is None:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        close_conn_locally = True

    factures_list = []
    params = []
    sql = "SELECT * FROM company_factures WHERE is_deleted = 0"

    if original_file_name_like:
        sql += " AND original_file_name LIKE ?"
        params.append(f"%{original_file_name_like}%")
    if extraction_status:
        sql += " AND extraction_status = ?"
        params.append(extraction_status)
    if upload_date_from:
        sql += " AND DATE(upload_date) >= ?" # Compare DATE part of timestamp
        params.append(upload_date_from)
    if upload_date_to:
        sql += " AND DATE(upload_date) <= ?" # Compare DATE part of timestamp
        params.append(upload_date_to)

    sql += " ORDER BY upload_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    try:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        for row in rows:
            factures_list.append(dict(row))
        return factures_list
    except sqlite3.Error as e:
        print(f"Database error in get_all_company_factures: {e}")
        return []
    finally:
        if close_conn_locally and conn:
            conn.close()


def update_company_expense(
    expense_id: int,
    expense_date: Optional[str] = None,
    amount: Optional[float] = None,
    currency: Optional[str] = None,
    recipient_name: Optional[str] = None,
    description: Optional[str] = None,
    facture_id: Optional[int] = None, # Use None to keep existing, or an int to change/set, or 0 to clear (handle 0 as NULL)
    conn: Optional[sqlite3.Connection] = None
) -> bool:
    """Updates an existing company expense."""
    close_conn_locally = False
    if conn is None:
        conn = get_db_connection()
        close_conn_locally = True

    fields_to_update = []
    params = []

    if expense_date is not None:
        fields_to_update.append("expense_date = ?")
        params.append(expense_date)
    if amount is not None:
        fields_to_update.append("amount = ?")
        params.append(amount)
    if currency is not None:
        fields_to_update.append("currency = ?")
        params.append(currency)
    if recipient_name is not None:
        fields_to_update.append("recipient_name = ?")
        params.append(recipient_name)
    if description is not None: # Allow setting description to empty string
        fields_to_update.append("description = ?")
        params.append(description)

    # Special handling for facture_id to allow unsetting it
    # If facture_id is explicitly passed (even if None or 0 for unsetting)
    if facture_id is not None: # facture_id = 0 or None means to clear it (set to NULL)
        fields_to_update.append("facture_id = ?")
        params.append(facture_id if facture_id > 0 else None) # Store NULL if 0 or None
    elif 'facture_id' in locals() and facture_id is None: # Explicitly passed as None
        fields_to_update.append("facture_id = ?")
        params.append(None)


    if not fields_to_update:
        return False # Nothing to update

    fields_to_update.append("updated_at = ?")
    params.append(datetime.now())
    params.append(expense_id)

    sql = f"UPDATE company_expenses SET {', '.join(fields_to_update)} WHERE expense_id = ? AND is_deleted = 0"

    try:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_company_expense: {e}")
        return False
    finally:
        if close_conn_locally and conn:
            conn.close()

def soft_delete_company_expense(expense_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Soft deletes a company expense by setting is_deleted to 1 and updating deleted_at."""
    close_conn_locally = False
    if conn is None:
        conn = get_db_connection()
        close_conn_locally = True

    try:
        cursor = conn.cursor()
        current_time = datetime.now()
        cursor.execute("""
            UPDATE company_expenses
            SET is_deleted = 1, deleted_at = ?, updated_at = ?
            WHERE expense_id = ? AND is_deleted = 0
        """, (current_time, current_time, expense_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in soft_delete_company_expense: {e}")
        return False
    finally:
        if close_conn_locally and conn:
            conn.close()

def link_facture_to_expense(expense_id: int, facture_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Links a facture to an expense."""
    return update_company_expense(expense_id=expense_id, facture_id=facture_id, conn=conn)

def unlink_facture_from_expense(expense_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Unlinks a facture from an expense by setting facture_id to NULL."""
    return update_company_expense(expense_id=expense_id, facture_id=None, conn=conn) # Pass None for facture_id to clear

if __name__ == '__main__':
    # Basic Test/Example Usage (assumes db is initialized and connection works)
    print("Running basic tests for company_expenses_crud...")

    # Test DB connection (implicitly tested by get_db_connection)
    # Ensure your config.DATABASE_PATH is correct for this test to run standalone
    # And that init_schema.py has been run at least once.

    # Add a test facture (required if linking)
    test_facture_id = add_company_facture("test_facture.pdf", "/path/to/test_facture.pdf", "application/pdf")
    if test_facture_id:
        print(f"Added test facture with ID: {test_facture_id}")

        # Add an expense
        expense_id = add_company_expense(
            expense_date="2023-10-27",
            amount=100.50,
            currency="USD",
            recipient_name="Test Vendor Inc.",
            description="Office Supplies",
            facture_id=test_facture_id,
            created_by_user_id="test_user_uuid_123" # Example UUID
        )
        if expense_id:
            print(f"Added expense with ID: {expense_id}")

            # Get the expense
            expense_details = get_company_expense_by_id(expense_id)
            print(f"Retrieved expense: {expense_details}")

            # Update the expense
            updated = update_company_expense(
                expense_id=expense_id,
                amount=105.75,
                description="Updated Office Supplies Description"
            )
            print(f"Expense update status: {updated}")
            if updated:
                expense_details_updated = get_company_expense_by_id(expense_id)
                print(f"Retrieved updated expense: {expense_details_updated}")

            # List expenses
            all_expenses = get_all_company_expenses(limit=5)
            print(f"All expenses (limit 5): {all_expenses}")

            # Unlink facture
            unlinked = unlink_facture_from_expense(expense_id)
            print(f"Facture unlinking status: {unlinked}")
            expense_details_unlinked = get_company_expense_by_id(expense_id)
            print(f"Expense after unlinking facture: {expense_details_unlinked}")

            # Soft delete the expense
            # deleted = soft_delete_company_expense(expense_id)
            # print(f"Expense soft delete status: {deleted}")
            # expense_details_deleted = get_company_expense_by_id(expense_id)
            # print(f"Attempt to retrieve soft-deleted expense: {expense_details_deleted}") # Should be None

        # Soft delete the facture
        # deleted_facture = soft_delete_company_facture(test_facture_id)
        # print(f"Test facture soft delete status: {deleted_facture}")
        # facture_details_deleted = get_company_facture_by_id(test_facture_id)
        # print(f"Attempt to retrieve soft-deleted facture: {facture_details_deleted}") # Should be None

    else:
        print("Failed to add test facture, skipping expense tests that depend on it.")

    print("Basic tests completed.")

# To make these CRUDs available for import:
# Ensure db.cruds has an __init__.py that might expose them, or import directly.
# e.g. from db.cruds.company_expenses_crud import add_company_expense
