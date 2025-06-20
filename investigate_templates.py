import sqlite3
import json
import os
import sys

# Add /app to sys.path to help resolve local modules like app_setup
sys.path.insert(0, '/app')

def get_db_path():
    """Tries to determine the database path."""
    db_path_to_check = None

    # 1. Try app_config.DATABASE_PATH
    try:
        import app_config
        if hasattr(app_config, 'DATABASE_PATH') and isinstance(app_config.DATABASE_PATH, str):
            print(f"Found DATABASE_PATH in app_config: {app_config.DATABASE_PATH}")
            db_path_to_check = app_config.DATABASE_PATH
            if os.path.exists(db_path_to_check):
                print(f"Using DATABASE_PATH from app_config: {db_path_to_check}")
                return db_path_to_check
            else:
                print(f"Path from app_config.DATABASE_PATH does not exist: {db_path_to_check}")
        else:
            print("app_config.DATABASE_PATH not found or not a string.")
    except ImportError:
        print("app_config module not found or import error.")
    except Exception as e:
        print(f"Error accessing app_config.DATABASE_PATH: {e}")

    # 2. Try config.DATABASE_PATH
    try:
        import config # General config file
        if hasattr(config, 'DATABASE_PATH') and isinstance(config.DATABASE_PATH, str):
            print(f"Found DATABASE_PATH in config: {config.DATABASE_PATH}")
            db_path_to_check = config.DATABASE_PATH
            if os.path.exists(db_path_to_check):
                print(f"Using DATABASE_PATH from config: {db_path_to_check}")
                return db_path_to_check
            else:
                print(f"Path from config.DATABASE_PATH does not exist: {db_path_to_check}")
        else:
            print("config.DATABASE_PATH not found or not a string.")
    except ImportError:
        print("config module not found or import error.")
    except Exception as e:
        print(f"Error accessing config.DATABASE_PATH: {e}")

    # 3. Try db.connection.DATABASE_NAME (if db.connection can be imported)
    try:
        from db import connection as db_connection
        if hasattr(db_connection, 'DATABASE_NAME') and isinstance(db_connection.DATABASE_NAME, str):
            print(f"Found DATABASE_NAME in db.connection: {db_connection.DATABASE_NAME}")
            # This path is often relative to the db module, so might need adjustment
            # For now, assume it's an absolute path or relative to /app
            db_path_to_check = db_connection.DATABASE_NAME
            if os.path.exists(db_path_to_check):
                print(f"Using DATABASE_NAME from db.connection: {db_path_to_check}")
                return db_path_to_check
            else:
                # Try prepending "db/" if it's a common pattern for it to be inside db dir
                print(f"Path from db.connection.DATABASE_NAME does not exist: {db_path_to_check}")
                potential_path_in_db_dir = os.path.join("db", db_path_to_check)
                if os.path.exists(potential_path_in_db_dir):
                    print(f"Using DATABASE_NAME from db.connection (adjusted): {potential_path_in_db_dir}")
                    return potential_path_in_db_dir


    except ImportError:
        print("db.connection module not found or import error (might be due to app_setup missing).")
    except Exception as e:
        print(f"Error accessing db.connection.DATABASE_NAME: {e}")


    # 4. Fallback to default relative path "db/database.db"
    default_path = "db/database.db"
    print(f"Trying default path: {default_path}")
    if os.path.exists(default_path):
        return default_path

    # 5. Fallback to "database.db" in root
    root_db_path = "database.db"
    print(f"Trying root path: {root_db_path}")
    if os.path.exists(root_db_path):
        return root_db_path

    print("Database path could not be determined.")
    return None

DB_PATH = get_db_path()

def query_db(query, params=()):
    """Generic function to query the database."""
    if not DB_PATH:
        print("DB_PATH is not set, cannot query.")
        return []

    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database file does not exist at the determined path: {os.path.abspath(DB_PATH)}")
        return []

    conn = None
    try:
        print(f"Attempting to connect to SQLite database at: {os.path.abspath(DB_PATH)}")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error: {e}, Query: {query}, Params: {params}")
        return []
    finally:
        if conn:
            conn.close()

def main():
    if not DB_PATH or not os.path.exists(DB_PATH):
        print("Database not found. Aborting script.")
        print(f"Final DB_PATH tried: {DB_PATH}")
        print(f"Current working directory: {os.getcwd()}")
        print("Relevant environment variables:")
        for var in ["PYTHONPATH", "DB_ABSOLUTE_PATH"]:
            print(f"  {var}: {os.getenv(var)}")
        print(f"Contents of /app: {os.listdir('/app') if os.path.exists('/app') else 'Not found'}")
        print(f"Contents of /app/db: {os.listdir('/app/db') if os.path.exists('/app/db') else 'Not found'}")
        return

    print(f"Successfully resolved DB path to: {os.path.abspath(DB_PATH)}")
    results = {}

    # 1. Query ApplicationSettings table
    app_settings = query_db("SELECT key, value FROM ApplicationSettings WHERE key LIKE 'template_visibility_%'")
    results['application_settings_visibility'] = app_settings
    print("\n--- ApplicationSettings (template_visibility_%) ---")
    if app_settings:
        for row in app_settings:
            print(dict(row))
    else:
        print("No template_visibility settings found or error in query.")

    # 2. Query Templates table
    sample_templates_query = """
        SELECT template_id, template_name, template_type, language_code, base_file_name, category_id, client_id
        FROM Templates
        WHERE template_type IN ('document_html', 'document_word', 'utility', 'document_global', 'client_document')
        ORDER BY template_type, template_id DESC
        LIMIT 15
    """
    sample_templates = query_db(sample_templates_query)

    results['sample_templates'] = sample_templates
    print("\n--- Sample Templates (document_html, document_word, utility, document_global, client_document) ---")
    category_ids_from_templates = set()
    if sample_templates:
        for row in sample_templates:
            print(dict(row))
            if row.get('category_id'):
                category_ids_from_templates.add(row['category_id'])
    else:
        print("No sample templates found for the specified types or error in query.")

    # 3. Query TemplateCategories table
    if category_ids_from_templates:
        placeholders = ','.join('?' for _ in category_ids_from_templates)
        categories_query = f"""
            SELECT category_id, category_name, purpose
            FROM TemplateCategories
            WHERE category_id IN ({placeholders})
        """
        categories = query_db(categories_query, tuple(category_ids_from_templates))
        results['template_categories'] = categories
        print("\n--- TemplateCategories (for categories found in sample templates) ---")
        if categories:
            for row in categories:
                print(dict(row))
        else:
            print(f"No categories found for IDs: {list(category_ids_from_templates)} or error in query.")
    else:
        results['template_categories'] = []
        print("\n--- TemplateCategories ---")
        print("No category IDs gathered from sample templates to query.")
        general_categories = query_db("SELECT category_id, category_name, purpose FROM TemplateCategories LIMIT 5")
        if general_categories:
            print("\n--- General Sample TemplateCategories (since none from templates) ---")
            for row in general_categories:
                print(dict(row))
        else:
            print("No general categories found or error in query.")

if __name__ == "__main__":
    main()
