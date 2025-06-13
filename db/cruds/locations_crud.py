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
def add_country(country_data: dict, conn: sqlite3.Connection = None) -> int | None:
    """
    Adds a new country to the Countries table.
    Expects country_data['country_name']. Optional: country_data['country_code'].
    created_at and updated_at are handled by database defaults.
    Returns the country_id of the newly added or existing country.
    """
    country_name = country_data.get('country_name')
    country_code = country_data.get('country_code') # Optional

    if not country_name:
        logging.error("add_country: 'country_name' is required.")
        return None

    cursor = conn.cursor()
    try:
        # Check if country already exists
        cursor.execute("SELECT country_id FROM Countries WHERE country_name = ?", (country_name,))
        row = cursor.fetchone()
        if row:
            logging.info(f"Country '{country_name}' already exists with ID {row['country_id']}. Returning existing ID.")
            return row['country_id']

        # If not exists, insert new country
        # created_at and updated_at will use DEFAULT CURRENT_TIMESTAMP from schema
        sql = "INSERT INTO Countries (country_name, country_code) VALUES (?, ?)"
        cursor.execute(sql, (country_name, country_code))
        # conn.commit() will be handled by @_manage_conn if it's the outermost call
        new_id = cursor.lastrowid
        logging.info(f"Added country '{country_name}' with ID {new_id}.")
        return new_id
    except sqlite3.IntegrityError: # Should be caught by the initial check, but as a safeguard
        logging.warning(f"IntegrityError for country '{country_name}'. It might have been added concurrently. Fetching again.")
        cursor.execute("SELECT country_id FROM Countries WHERE country_name = ?", (country_name,))
        row = cursor.fetchone()
        return row['country_id'] if row else None
    except sqlite3.Error as e:
        logging.error(f"Database error in add_country for '{country_name}': {e}", exc_info=True)
        return None

@_manage_conn
def get_or_add_country(country_name: str, country_code: str = None, conn: sqlite3.Connection = None) -> dict | None:
    """
    Retrieves a country by name, or adds it if it doesn't exist.
    Returns a dictionary representing the country row, or None on error.
    """
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
            # Country does not exist, add it using the refactored add_country logic
            new_country_id = add_country({'country_name': country_name, 'country_code': country_code}, conn=conn)
            if new_country_id:
                # Fetch the newly added country to return the full dict including defaults
                cursor.execute("SELECT * FROM Countries WHERE country_id = ?", (new_country_id,))
                new_row = cursor.fetchone()
                return dict(new_row) if new_row else None
            return None # Error during add_country
    except sqlite3.Error as e:
        logging.error(f"Database error in get_or_add_country for '{country_name}': {e}", exc_info=True)
        return None


@_manage_conn
def get_all_countries(conn: sqlite3.Connection = None) -> list[dict]:
    """
    Retrieves all countries.
    STUB FUNCTION - Original was a stub.
    """
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
    Expects data['city_name'] and data['country_id'].
    created_at and updated_at are handled by database defaults (if schema supports it).
    Returns the city_id of the newly added or existing city.
    """
    city_name = data.get('city_name')
    country_id = data.get('country_id')

    if not city_name or not country_id:
        logging.error("add_city: 'city_name' and 'country_id' are required.")
        return None

    cursor = conn.cursor()
    try:
        # Check if city already exists for this country
        cursor.execute("SELECT city_id FROM Cities WHERE city_name = ? AND country_id = ?", (city_name, country_id))
        row = cursor.fetchone()
        if row:
            logging.info(f"City '{city_name}' in country_id {country_id} already exists with ID {row['city_id']}.")
            return row['city_id']

        # If not exists, insert new city. Assuming Cities table also has created_at/updated_at defaults.
        sql = "INSERT INTO Cities (city_name, country_id) VALUES (?, ?)"
        cursor.execute(sql, (city_name, country_id))
        new_id = cursor.lastrowid
        logging.info(f"Added city '{city_name}' to country_id {country_id} with new ID {new_id}.")
        return new_id
    except sqlite3.IntegrityError: # Should be caught by the initial check
        logging.warning(f"IntegrityError for city '{city_name}', country_id {country_id}. Fetching again.")
        cursor.execute("SELECT city_id FROM Cities WHERE city_name = ? AND country_id = ?", (city_name, country_id))
        row = cursor.fetchone()
        return row['city_id'] if row else None
    except sqlite3.Error as e:
        logging.error(f"Database error in add_city for '{city_name}', country_id {country_id}: {e}", exc_info=True)
        return None

@_manage_conn
def get_or_add_city(city_name: str, country_id: int, conn: sqlite3.Connection = None) -> dict | None:
    """
    Retrieves a city by name and country_id, or adds it if it doesn't exist.
    Returns a dictionary representing the city row, or None on error.
    """
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
            # City does not exist, add it using the refactored add_city logic
            new_city_id = add_city({'city_name': city_name, 'country_id': country_id}, conn=conn)
            if new_city_id:
                # Fetch the newly added city to return the full dict
                cursor.execute("SELECT * FROM Cities WHERE city_id = ?", (new_city_id,))
                new_row = cursor.fetchone()
                return dict(new_row) if new_row else None
            return None # Error during add_city
    except sqlite3.Error as e:
        logging.error(f"Database error in get_or_add_city for '{city_name}', country_id {country_id}: {e}", exc_info=True)
        return None

@_manage_conn
def get_all_cities(conn: sqlite3.Connection = None) -> list[dict]:
    """
    Retrieves all cities.
    STUB FUNCTION - Original was a stub.
    """
    logging.warning("Called stub function get_all_cities. Providing basic implementation.")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Cities ORDER BY country_id, city_name")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Database error in get_all_cities: {e}")
        return []
