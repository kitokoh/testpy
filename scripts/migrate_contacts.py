import sqlite3
import os
import sys
import logging
from datetime import datetime # Though not directly used, good for potential future use

# --- Script Setup ---
# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

# Adjust sys.path to allow imports from the project's root
# Assumes this script is in a 'scripts' directory one level below project root.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# --- Database and CRUD Imports ---
# These imports are placed after sys.path manipulation to ensure they are found.
try:
    from db.connection import get_db_connection, DB_PATH
    # The central_add_contact and central_get_contact_by_email are used internally by the
    # add_partner_contact and add_personnel_contact CRUDs.
    # We only need to import the linking functions from partners_crud and company_personnel_crud.
    from db.cruds.partners_crud import add_partner_contact as link_partner_to_contact
    from db.cruds.company_personnel_crud import add_personnel_contact as link_personnel_to_contact
except ImportError as e:
    logging.error(f"Failed to import necessary modules. Ensure PYTHONPATH is correct and CRUDs exist: {e}")
    sys.exit(1)

# --- Migration Functions ---

def migrate_partner_contacts(conn: sqlite3.Connection):
    """
    Migrates contact data from the old PartnerContacts table structure to the
    central Contacts table and creates links in the new PartnerContacts table.

    IMPORTANT ASSUMPTION: This function assumes the PartnerContacts table
    still has its OLD structure (name, email, phone, role directly in it).
    If the schema has already been updated to the new link-table-only structure,
    this migration will likely fail or do nothing. Run this script *before*
    fully applying the new PartnerContacts schema that removes these columns,
    or ensure this part is skipped if the old schema is not present.
    """
    logging.info("Starting migration of old PartnerContacts...")
    cursor = conn.cursor()

    try:
        # Attempt to select from the old PartnerContacts structure
        cursor.execute("SELECT partner_id, name, email, phone, role FROM PartnerContacts")
        old_partner_contacts = cursor.fetchall()
        logging.info(f"Found {len(old_partner_contacts)} records in old PartnerContacts table structure.")
    except sqlite3.OperationalError as e:
        logging.error(f"Could not query old PartnerContacts table structure (partner_id, name, email, phone, role): {e}")
        logging.warning("This might be because the PartnerContacts table has already been migrated to the new schema, or it's empty/missing.")
        logging.info("Skipping migration from old PartnerContacts table structure.")
        return

    migrated_count = 0
    failed_count = 0
    for row in old_partner_contacts:
        try:
            partner_id = row['partner_id']
            name = row['name']
            email = row['email']
            phone = row['phone']
            role = row['role'] # This was the 'position' like field in old PartnerContacts

            if not name and not email: # Basic check for minimally viable contact
                logging.warning(f"Skipping record for partner_id {partner_id} due to missing name and email in old PartnerContacts.")
                failed_count += 1
                continue

            contact_payload = {
                'name': name, # Will be used for displayName if displayName not provided
                'displayName': name, # Explicitly set displayName
                'email': email,
                'phone': phone,
                'position': role, # Mapping 'role' from old table to 'position'
                'notes': f"Migrated from old PartnerContacts table. Original role: {role if role else 'N/A'}"
                # is_primary and can_receive_documents will default in link_partner_to_contact
                # or can be added to payload if there's a logic for them from old data
            }

            # The updated link_partner_to_contact (aliased from add_partner_contact)
            # now handles the creation of the central contact and then the link.
            # It requires partner_id as a separate first argument.
            link_id = link_partner_to_contact(partner_id=partner_id, contact_data=contact_payload, conn=conn)

            if link_id:
                logging.info(f"Successfully migrated and linked contact '{name}' (Email: {email}) for partner_id {partner_id}. New link ID: {link_id}")
                migrated_count += 1
            else:
                logging.warning(f"Failed to migrate or link contact '{name}' (Email: {email}) for partner_id {partner_id}.")
                failed_count += 1
        except Exception as e_row:
            logging.error(f"Error processing row {dict(row) if row else 'N/A'} from old PartnerContacts: {e_row}", exc_info=True)
            failed_count += 1

    logging.info(f"Migration from old PartnerContacts table structure complete. Migrated: {migrated_count}, Failed: {failed_count}.")


def migrate_company_personnel_contacts(conn: sqlite3.Connection):
    """
    Migrates contact data from the CompanyPersonnel table to the central
    Contacts table and creates links in CompanyPersonnelContacts.
    """
    logging.info("Starting migration of CompanyPersonnel contacts...")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT personnel_id, name, email, phone, role FROM CompanyPersonnel")
        personnel_list = cursor.fetchall()
    except sqlite3.OperationalError as e:
        logging.error(f"Could not query CompanyPersonnel table: {e}")
        logging.info("Skipping migration from CompanyPersonnel table.")
        return

    migrated_count = 0
    failed_count = 0
    for personnel_row in personnel_list:
        try:
            personnel_id = personnel_row['personnel_id']
            name = personnel_row['name']
            email = personnel_row['email']
            phone = personnel_row['phone']
            role = personnel_row['role'] # Role of the personnel in their company

            if not name and not email: # Basic check for minimally viable contact
                logging.warning(f"Skipping personnel_id {personnel_id} due to missing name and email.")
                failed_count += 1
                continue

            contact_payload = {
                'name': name, # Will be used for displayName
                'displayName': name,
                'email': email,
                'phone': phone,
                'position': role, # Mapping personnel's 'role' to 'position' in Contacts
                'notes': f"Migrated from CompanyPersonnel table. Original role at company: {role if role else 'N/A'}"
                # is_primary and can_receive_documents will default in link_personnel_to_contact
            }

            # The updated link_personnel_to_contact (aliased from add_personnel_contact)
            # handles creation of central contact and then the link.
            # It requires personnel_id as a separate first argument.
            link_id = link_personnel_to_contact(personnel_id=personnel_id, contact_data=contact_payload, conn=conn)

            if link_id:
                logging.info(f"Successfully migrated and linked contact '{name}' (Email: {email}) for personnel_id {personnel_id}. New link ID: {link_id}")
                migrated_count += 1
            else:
                logging.warning(f"Failed to migrate or link contact '{name}' (Email: {email}) for personnel_id {personnel_id}.")
                failed_count += 1
        except Exception as e_row:
            logging.error(f"Error processing row {dict(personnel_row) if personnel_row else 'N/A'} from CompanyPersonnel: {e_row}", exc_info=True)
            failed_count += 1

    logging.info(f"Migration from CompanyPersonnel table complete. Migrated: {migrated_count}, Failed: {failed_count}.")


# --- Main Execution ---

def main():
    db_conn = None
    try:
        logging.info(f"Connecting to database: {DB_PATH}")
        db_conn = get_db_connection()
        db_conn.row_factory = sqlite3.Row # Ensure dict-like row access for fetched data

        logging.info("Starting contact migration process...")

        # --- Run Migrations ---
        # It's crucial that the CRUD functions (link_partner_to_contact, link_personnel_to_contact)
        # passed the `db_conn` manage their own execution within the transaction.
        # The @_manage_conn decorator in CRUDs usually handles commit/rollback IF conn is None.
        # Since we are passing `conn`, these CRUDs will use the provided `conn` and cursor.
        # The final commit/rollback for the entire process will be handled here in `main`.

        migrate_partner_contacts(db_conn)
        migrate_company_personnel_contacts(db_conn)

        db_conn.commit()
        logging.info("Contact migration process completed successfully and changes committed.")

    except sqlite3.Error as e:
        logging.error(f"Database error during migration: {e}", exc_info=True)
        if db_conn:
            db_conn.rollback()
            logging.info("Changes rolled back due to database error.")
    except Exception as e:
        logging.error(f"An unexpected error occurred during migration: {e}", exc_info=True)
        if db_conn:
            db_conn.rollback()
            logging.info("Changes rolled back due to unexpected error.")
    finally:
        if db_conn:
            db_conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    main()
