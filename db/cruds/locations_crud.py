import sqlite3
import logging
from datetime import datetime
from .generic_crud import _manage_conn, get_db_connection

# --- Countries CRUD ---
@_manage_conn
def get_country_by_name(name: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor()
    try:
        cursor.execute("SELECT * FROM Countries WHERE country_name = ?",(name,))
        row=cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Error getting country by name '{name}': {e}")
        return None

@_manage_conn
def get_country_by_id(id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor()
    try:
        cursor.execute("SELECT * FROM Countries WHERE country_id = ?",(id,))
        row=cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Error getting country by id {id}: {e}")
        return None

@_manage_conn
def get_or_add_country(country_name: str, conn: sqlite3.Connection = None) -> dict | None:
    if not country_name:
        logging.warning("get_or_add_country: country_name is required.")
        return None

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Countries WHERE country_name = ?", (country_name,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        else:
            now = datetime.utcnow().isoformat() + "Z"
            sql = "INSERT INTO Countries (country_name, created_at, updated_at) VALUES (?, ?, ?)"
            params = (country_name, now, now)
            cursor.execute(sql, params)
            new_country_id = cursor.lastrowid
            if new_country_id:
                return {'country_id': new_country_id, 'country_name': country_name, 'created_at': now, 'updated_at': now}
            else: # Should not happen if insert was successful
                logging.error(f"Failed to get lastrowid after inserting country: {country_name}")
                return None
    except sqlite3.IntegrityError: # country_name likely has a UNIQUE constraint, race condition?
        logging.warning(f"Integrity error adding country '{country_name}', trying to fetch again.")
        cursor.execute("SELECT * FROM Countries WHERE country_name = ?", (country_name,))
        row_after_error = cursor.fetchone()
        return dict(row_after_error) if row_after_error else None
    except sqlite3.Error as e_general:
        logging.error(f"General SQLite error in get_or_add_country for '{country_name}': {e_general}")
        return None

@_manage_conn
def add_country(data: dict, conn: sqlite3.Connection = None) -> int | None:
    """
    Adds a new country. Expects data['country_name'].
    This is a simplified version. Consider using get_or_add_country for more robust addition.
    STUB FUNCTION - Original was a stub.
    """
    logging.warning(f"Called stub/simplified function add_country with data: {data}. Consider using get_or_add_country.")
    if 'country_name' not in data:
        logging.error("add_country: 'country_name' is required in data.")
        return None

    country_name = data['country_name']
    existing_country = get_country_by_name(country_name, conn=conn) # Use passed connection
    if existing_country:
        return existing_country['country_id']

    now = datetime.utcnow().isoformat() + "Z"
    sql = "INSERT INTO Countries (country_name, created_at, updated_at) VALUES (?, ?, ?)"
    params = (country_name, now, now)
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error(f"Database error in add_country for '{country_name}': {e}")
        return None

@_manage_conn
def get_all_countries(conn: sqlite3.Connection = None) -> list[dict]:
    """
    Retrieves all countries.
    STUB FUNCTION - Original was a stub.
    """
    logging.warning("Called stub function get_all_countries. Providing basic implementation.")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Countries ORDER BY country_name")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Database error in get_all_countries: {e}")
        return []

# --- Cities CRUD ---
@_manage_conn
def get_city_by_name_and_country_id(name: str, country_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor()
    try:
        cursor.execute("SELECT * FROM Cities WHERE city_name = ? AND country_id = ?",(name,country_id))
        row=cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Error getting city by name '{name}' and country_id {country_id}: {e}")
        return None

@_manage_conn
def get_city_by_id(id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor()
    try:
        cursor.execute("SELECT * FROM Cities WHERE city_id = ?",(id,))
        row=cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Error getting city by id {id}: {e}")
        return None

@_manage_conn
def add_city(data: dict, conn: sqlite3.Connection = None) -> int | None:
    """
    Adds a new city to the Cities table.
    STUB FUNCTION - Original was a stub. Consider get_or_add_city.
    Expects data['city_name'] and data['country_id'].
    """
    logging.warning(f"Called stub function add_city with data: {data}. Consider get_or_add_city.")
    if not data.get('city_name') or not data.get('country_id'):
        logging.error("add_city requires 'city_name' and 'country_id'.")
        return None

    # Simplified: direct insert without all fields from original schema example
    now = datetime.utcnow().isoformat() + "Z"
    sql = "INSERT INTO Cities (city_name, country_id, created_at, updated_at) VALUES (?, ?, ?, ?)"
    params = (data['city_name'], data['country_id'], now, now)
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logging.warning(f"City '{data['city_name']}' likely already exists for country_id {data['country_id']}.")
        existing_city = get_city_by_name_and_country_id(data['city_name'], data['country_id'], conn=conn)
        return existing_city['city_id'] if existing_city else None
    except sqlite3.Error as e:
        logging.error(f"Database error in add_city for '{data['city_name']}': {e}")
        return None

@_manage_conn
def get_or_add_city(city_name: str, country_id: int, conn: sqlite3.Connection = None) -> dict | None:
    if not city_name or not country_id:
        logging.warning("get_or_add_city: city_name and country_id are required.")
        return None

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Cities WHERE city_name = ? AND country_id = ?", (city_name, country_id))
        row = cursor.fetchone()
        if row:
            return dict(row)
        else:
            now = datetime.utcnow().isoformat() + "Z"
            sql = "INSERT INTO Cities (city_name, country_id, created_at, updated_at) VALUES (?, ?, ?, ?)"
            params = (city_name, country_id, now, now)
            cursor.execute(sql, params)
            new_city_id = cursor.lastrowid
            if new_city_id:
                return {'city_id': new_city_id, 'city_name': city_name, 'country_id': country_id,
                        'latitude': None, 'longitude': None, 'population': None, # Match potential full dict
                        'created_at': now, 'updated_at': now}
            else:
                logging.error(f"Failed to get lastrowid after inserting city: {city_name}")
                return None
    except sqlite3.IntegrityError as e:
        logging.error(f"Integrity error adding city '{city_name}' for country_id {country_id}: {e}")
        return None
    except sqlite3.Error as e_general:
        logging.error(f"General SQLite error adding city '{city_name}': {e_general}")
        return None

@_manage_conn
def get_all_cities(country_id: int = None, conn: sqlite3.Connection = None) -> list[dict]:
    """
    Retrieves all cities, optionally filtered by country_id.
    """
    cursor = conn.cursor()
    sql = "SELECT * FROM Cities"
    params = []
    if country_id is not None:
        sql += " WHERE country_id = ?"
        params.append(country_id)
    sql += " ORDER BY city_name" # Or country_id, city_name
    try:
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Database error in get_all_cities (country_id={country_id}): {e}")
        return []

__all__ = [
    "get_country_by_name",
    "get_country_by_id",
    "get_or_add_country",
    "add_country", # Keep for compatibility if used elsewhere, though get_or_add is preferred
    "get_all_countries",
    "get_city_by_name_and_country_id",
    "get_city_by_id",
    "add_city", # Keep for compatibility
    "get_or_add_city",
    "get_all_cities",
]
