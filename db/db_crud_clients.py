import sqlite3
import uuid
from datetime import datetime

from .db_config import get_db_connection

# CRUD functions for Clients
def add_client(client_data: dict) -> str | None:
    """
    Adds a new client to the database.
    Returns the new client_id if successful, otherwise None.
    Ensures created_at and updated_at are set.
    Expects 'category_id' instead of 'category' text.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        new_client_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat() + "Z"

        # Ensure all required fields are present, or provide defaults
        sql = """
            INSERT INTO Clients (
                client_id, client_name, company_name, primary_need_description, project_identifier,
                country_id, city_id, default_base_folder_path, status_id,
                selected_languages, notes, category, created_at, updated_at, created_by_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_client_id,
            client_data.get('client_name'),
            client_data.get('company_name'),
            client_data.get('primary_need_description'),
            client_data.get('project_identifier'), # Added
            client_data.get('country_id'),
            client_data.get('city_id'),
            client_data.get('default_base_folder_path'),
            client_data.get('status_id'),
            client_data.get('selected_languages'),
            client_data.get('notes'),
            client_data.get('category'),
            now,  # created_at
            now,  # updated_at
            client_data.get('created_by_user_id')
        )

        cursor.execute(sql, params)
        conn.commit()
        return new_client_id
    except sqlite3.Error as e:
        print(f"Database error in add_client: {e}")
        # Consider raising a custom exception or logging more formally
        return None
    finally:
        if conn:
            conn.close()

def get_client_by_id(client_id: str) -> dict | None:
    """Retrieves a client by their ID. Returns a dict or None if not found."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Clients WHERE client_id = ?", (client_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_client_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_clients(filters: dict = None) -> list[dict]:
    """
    Retrieves all clients, optionally applying filters.
    Filters can be e.g. {'status_id': 1, 'category': 'VIP'}.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = "SELECT * FROM Clients"
        params = []

        if filters:
            where_clauses = []
            for key, value in filters.items():
                # Basic protection against non-column names; ideally, validate keys against known columns
                if key in ['client_name', 'company_name', 'country_id', 'city_id', 'status_id', 'category', 'created_by_user_id']: # Add other filterable columns
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_clients: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_client(client_id: str, client_data: dict) -> bool:
    """
    Updates an existing client's information.
    Ensures updated_at is set to the current timestamp.
    Returns True if update was successful, False otherwise.
    """
    conn = None
    if not client_data:
        return False # Nothing to update

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat() + "Z"
        client_data['updated_at'] = now

        set_clauses = []
        params = []

        for key, value in client_data.items():
            # Validate keys against actual column names to prevent SQL injection if keys are from unsafe source
            # For now, assuming keys are controlled or map to valid columns
            if key != 'client_id': # client_id should not be updated here
                 set_clauses.append(f"{key} = ?")
                 params.append(value)

        if not set_clauses:
            return False # No valid fields to update

        sql = f"UPDATE Clients SET {', '.join(set_clauses)} WHERE client_id = ?"
        params.append(client_id)

        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_client: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_client(client_id: str) -> bool:
    """
    Deletes a client from the database.
    Returns True if deletion was successful, False otherwise.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Clients WHERE client_id = ?", (client_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_client: {e}")
        return False
    finally:
        if conn:
            conn.close()

# ClientNote functions
def add_client_note(client_id: str, note_text: str, user_id: str = None) -> int | None:
    """
    Adds a new note for a client.
    Returns the note_id if successful, otherwise None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO ClientNotes (client_id, note_text, user_id)
            VALUES (?, ?, ?)
        """
        params = (client_id, note_text, user_id)
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_client_note: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def get_client_notes(client_id: str) -> list[dict]:
    """
    Retrieves all notes for a given client_id, ordered by timestamp (oldest first).
    Returns a list of dictionaries, where each dictionary represents a note.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT note_id, client_id, timestamp, note_text, user_id
            FROM ClientNotes
            WHERE client_id = ?
            ORDER BY timestamp ASC
        """
        cursor.execute(sql, (client_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_client_notes: {e}")
        return []
    finally:
        if conn:
            conn.close()

# CRUD functions for Contacts
def add_contact(contact_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        name_to_insert = contact_data.get('displayName', contact_data.get('name'))
        sql = """
            INSERT INTO Contacts (
                name, email, phone, position, company_name, notes,
                givenName, familyName, displayName, phone_type, email_type,
                address_formattedValue, address_streetAddress, address_city,
                address_region, address_postalCode, address_country,
                organization_name, organization_title, birthday_date,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            name_to_insert, contact_data.get('email'), contact_data.get('phone'),
            contact_data.get('position'), contact_data.get('company_name'),
            contact_data.get('notes'), contact_data.get('givenName'),
            contact_data.get('familyName'), contact_data.get('displayName'),
            contact_data.get('phone_type'), contact_data.get('email_type'),
            contact_data.get('address_formattedValue'), contact_data.get('address_streetAddress'),
            contact_data.get('address_city'), contact_data.get('address_region'),
            contact_data.get('address_postalCode'), contact_data.get('address_country'),
            contact_data.get('organization_name'), contact_data.get('organization_title'),
            contact_data.get('birthday_date'), now, now
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_contact: {e}")
        return None
    finally:
        if conn: conn.close()

def get_contact_by_id(contact_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Contacts WHERE contact_id = ?", (contact_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_contact_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_contact_by_email(email: str) -> dict | None:
    conn = None
    if not email: return None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Contacts WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_contact_by_email: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_contacts(filters: dict = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM Contacts"
        params = []
        where_clauses = []
        if filters:
            if 'company_name' in filters:
                where_clauses.append("company_name = ?")
                params.append(filters['company_name'])
            if 'name' in filters:
                where_clauses.append("(name LIKE ? OR displayName LIKE ?)")
                params.append(f"%{filters['name']}%")
                params.append(f"%{filters['name']}%")
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_contacts: {e}")
        return []
    finally:
        if conn: conn.close()

def update_contact(contact_id: int, contact_data: dict) -> bool:
    conn = None
    if not contact_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        contact_data['updated_at'] = now
        if 'displayName' in contact_data and 'name' not in contact_data:
            contact_data['name'] = contact_data['displayName']
        valid_columns = [
            'name', 'email', 'phone', 'position', 'company_name', 'notes',
            'givenName', 'familyName', 'displayName', 'phone_type', 'email_type',
            'address_formattedValue', 'address_streetAddress', 'address_city',
            'address_region', 'address_postalCode', 'address_country',
            'organization_name', 'organization_title', 'birthday_date', 'updated_at'
        ]
        set_clauses = []
        params = []
        for key, value in contact_data.items():
            if key in valid_columns:
                set_clauses.append(f"{key} = ?")
                params.append(value)
            elif key == 'contact_id':
                continue
        if not set_clauses:
            print("Warning: No valid fields to update in update_contact.")
            return False
        params.append(contact_id)
        sql = f"UPDATE Contacts SET {', '.join(set_clauses)} WHERE contact_id = ?"
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_contact: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_contact(contact_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Contacts WHERE contact_id = ?", (contact_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_contact: {e}")
        return False
    finally:
        if conn: conn.close()

# Functions for ClientContacts association
def link_contact_to_client(client_id: str, contact_id: int, is_primary: bool = False, can_receive_documents: bool = True) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO ClientContacts (client_id, contact_id, is_primary_for_client, can_receive_documents)
            VALUES (?, ?, ?, ?)
        """
        params = (client_id, contact_id, is_primary, can_receive_documents)
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in link_contact_to_client: {e}")
        return None
    finally:
        if conn: conn.close()

def unlink_contact_from_client(client_id: str, contact_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM ClientContacts WHERE client_id = ? AND contact_id = ?"
        cursor.execute(sql, (client_id, contact_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in unlink_contact_from_client: {e}")
        return False
    finally:
        if conn: conn.close()

def get_contacts_for_client(client_id: str) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT c.*, cc.is_primary_for_client, cc.can_receive_documents, cc.client_contact_id
            FROM Contacts c
            JOIN ClientContacts cc ON c.contact_id = cc.contact_id
            WHERE cc.client_id = ?
        """
        cursor.execute(sql, (client_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_contacts_for_client: {e}")
        return []
    finally:
        if conn: conn.close()

def get_clients_for_contact(contact_id: int) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT cl.*, cc.is_primary_for_client, cc.can_receive_documents, cc.client_contact_id
            FROM Clients cl
            JOIN ClientContacts cc ON cl.client_id = cc.client_id
            WHERE cc.contact_id = ?
        """
        cursor.execute(sql, (contact_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_clients_for_contact: {e}")
        return []
    finally:
        if conn: conn.close()

def get_specific_client_contact_link_details(client_id: str, contact_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT client_contact_id, is_primary_for_client, can_receive_documents
            FROM ClientContacts
            WHERE client_id = ? AND contact_id = ?
        """
        cursor.execute(sql, (client_id, contact_id))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_specific_client_contact_link_details: {e}")
        return None
    finally:
        if conn: conn.close()

def update_client_contact_link(client_contact_id: int, details: dict) -> bool:
    conn = None
    if not details or not any(key in details for key in ['is_primary_for_client', 'can_receive_documents']):
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        set_clauses = []
        params = []
        if 'is_primary_for_client' in details:
            set_clauses.append("is_primary_for_client = ?")
            params.append(details['is_primary_for_client'])
        if 'can_receive_documents' in details:
            set_clauses.append("can_receive_documents = ?")
            params.append(details['can_receive_documents'])
        if not set_clauses: return False
        params.append(client_contact_id)
        sql = f"UPDATE ClientContacts SET {', '.join(set_clauses)} WHERE client_contact_id = ?"
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_client_contact_link: {e}")
        return False
    finally:
        if conn: conn.close()

# --- Lookup Table GET Functions (Countries & Cities) ---
def get_all_countries() -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Countries ORDER BY country_name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_all_countries: {e}")
        return []
    finally:
        if conn: conn.close()

def get_country_by_id(country_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Countries WHERE country_id = ?", (country_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_country_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_country_by_name(country_name: str) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Countries WHERE country_name = ?", (country_name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_country_by_name: {e}")
        return None
    finally:
        if conn: conn.close()

def add_country(country_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        country_name = country_data.get('country_name')
        if not country_name:
            print("Error: 'country_name' is required to add a country.")
            return None
        try:
            cursor.execute("INSERT INTO Countries (country_name) VALUES (?)", (country_name,))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"Country '{country_name}' already exists. Fetching its ID.")
            cursor.execute("SELECT country_id FROM Countries WHERE country_name = ?", (country_name,))
            row = cursor.fetchone()
            return row['country_id'] if row else None
    except sqlite3.Error as e:
        print(f"Database error in add_country: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_cities(country_id: int = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM Cities"
        params = []
        if country_id is not None:
            sql += " WHERE country_id = ?"
            params.append(country_id)
        sql += " ORDER BY city_name"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_all_cities: {e}")
        return []
    finally:
        if conn: conn.close()

def add_city(city_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        country_id = city_data.get('country_id')
        city_name = city_data.get('city_name')
        if not country_id or not city_name:
            print("Error: 'country_id' and 'city_name' are required to add a city.")
            return None
        try:
            cursor.execute("INSERT INTO Cities (country_id, city_name) VALUES (?, ?)", (country_id, city_name))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"IntegrityError likely means city '{city_name}' under country_id '{country_id}' already exists or other constraint failed.")
            return None
    except sqlite3.Error as e:
        print(f"Database error in add_city: {e}")
        return None
    finally:
        if conn: conn.close()

def get_city_by_name_and_country_id(city_name: str, country_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Cities WHERE city_name = ? AND country_id = ?", (city_name, country_id))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_city_by_name_and_country_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_city_by_id(city_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Cities WHERE city_id = ?", (city_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_city_by_id: {e}")
        return None
    finally:
        if conn: conn.close()
