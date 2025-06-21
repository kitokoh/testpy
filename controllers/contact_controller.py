# controllers/contact_controller.py
from db.cruds import contacts_crud # Assuming this is where the CRUD functions are
import logging

class ContactController:
    def __init__(self):
        # In the future, we might pass a specific DB connection or configuration
        # For now, contacts_crud functions are expected to handle their own DB connections
        pass

    def get_contact_by_id(self, contact_id):
        """Fetches a contact by its ID."""
        try:
            return contacts_crud.get_contact_by_id(contact_id)
        except Exception as e:
            logging.error(f"Error in ContactController.get_contact_by_id: {e}")
            return None

    def get_contact_by_email(self, email):
        """Fetches a contact by its email."""
        try:
            return contacts_crud.get_contact_by_email(email)
        except Exception as e:
            logging.error(f"Error in ContactController.get_contact_by_email: {e}")
            return None

    def get_contacts_for_client(self, client_id, primary_only=False):
        """Fetches contacts linked to a specific client.
        Can optionally fetch only the primary contact.
        """
        try:
            # Assuming contacts_crud.get_contacts_for_client does not take primary_only
            # If primary_only filtering is needed, it should be implemented in contacts_crud
            # or filtered here after fetching all contacts.
            # For now, remove primary_only from the call to contacts_crud.
            if primary_only:
                # Placeholder: If primary_only is True, this controller method needs
                # to fetch all and then filter, or contacts_crud.get_contacts_for_client
                # needs to support it. For the error reported, the CRUD layer doesn't support it.
                # This path is not taken by the problematic call from the logs.
                all_contacts = contacts_crud.get_contacts_for_client(client_id)
                return [c for c in all_contacts if c.get('is_primary_for_client')]
            else:
                return contacts_crud.get_contacts_for_client(client_id)
        except Exception as e:
            logging.error(f"Error in ContactController.get_contacts_for_client: {e}")
            return []

    def add_contact(self, contact_data: dict):
        """
        Adds a new contact to the central contacts table.
        contact_data is a dictionary, e.g., {'name': 'John Doe', 'email': 'john.doe@example.com', ...}
        Returns the ID of the newly added contact or None on failure.
        """ # Corrected: Added closing triple quote for docstring
        if not contact_data or not contact_data.get('email'): # Basic validation
            logging.warning("ContactController.add_contact: Attempted to add contact with missing email.")
            return None
        try:
            # contacts_crud.add_contact is expected to return the new contact's ID
            new_contact_id = contacts_crud.add_contact(contact_data)
            return new_contact_id
        except Exception as e:
            logging.error(f"Error in ContactController.add_contact: {e}")
            return None

    def update_contact(self, contact_id, contact_data: dict):
        """
        Updates an existing contact in the central contacts table.
        contact_data contains fields to update.
        Returns True on success, False on failure.
        """
        if not contact_id or not contact_data:
            logging.warning("ContactController.update_contact: Missing contact_id or data.")
            return False
        try:
            # contacts_crud.update_contact is expected to return a boolean or affected row count
            success = contacts_crud.update_contact(contact_id, contact_data)
            return bool(success) # Ensure boolean
        except Exception as e:
            logging.error(f"Error in ContactController.update_contact for ID {contact_id}: {e}")
            return False

    def link_contact_to_client(self, client_id, contact_id, is_primary=False, can_receive_documents=True, role=None):
        """
        Links a contact (from central table) to a client.
        Returns the ID of the link record or None on failure.
        """
        if not client_id or not contact_id:
            logging.warning("ContactController.link_contact_to_client: Missing client_id or contact_id.")
            return None
        try:
            # contacts_crud.link_contact_to_client is expected to return link ID
            # Role is accepted in signature for future use but not passed to CRUD yet.
            link_id = contacts_crud.link_contact_to_client(client_id, contact_id, is_primary, can_receive_documents)
            return link_id
        except Exception as e:
            logging.error(f"Error linking contact {contact_id} to client {client_id}: {e}")
            return None

    def update_client_contact_link(self, client_contact_id, link_data: dict):
        """
        Updates an existing link between a client and a contact.
        link_data contains fields to update (e.g., is_primary, role).
        Returns True on success, False on failure.
        """
        if not client_contact_id or not link_data:
            logging.warning("ContactController.update_client_contact_link: Missing client_contact_id or data.")
            return False
        try:
            success = contacts_crud.update_client_contact_link(client_contact_id, link_data)
            return bool(success)
        except Exception as e:
            logging.error(f"Error updating client_contact_link ID {client_contact_id}: {e}")
            return False


    def get_or_create_contact_and_link(self, client_id: str, contact_form_data: dict):
        """
        High-level method to get or create a contact, then link to a client.
        Handles unlinking other primary contacts if 'is_primary_for_client' is True.

        Args:
            client_id (str): The ID of the client.
            contact_form_data (dict): Data from ContactDialog, includes:
                'name', 'email', 'phone', 'position', 'is_primary_for_client', 'role_in_project' (optional)

        Returns:
            tuple: (contact_id_linked_or_found, link_id_if_created)
                   Returns (None, None) on critical failure.
        """
        logging.info(f"get_or_create_contact_and_link called with client_id: {client_id}") # New log
        if not client_id: # Changed condition
            logging.error("get_or_create_contact_and_link: client_id is None or empty. Cannot link contact.")
            return None, None

        if not contact_form_data or not contact_form_data.get('email'): # Original check for contact_form_data
            logging.error("get_or_create_contact_and_link: Missing contact_form_data or contact email.")
            return None, None

        email = contact_form_data['email'].strip()
        contact_id_to_link = None

        try:
            existing_contact = self.get_contact_by_email(email)

            contact_details_for_db = {
                'name': contact_form_data.get('name', '').strip(),
                'email': email, # Already stripped
                'phone': contact_form_data.get('phone', '').strip(),
                'position': contact_form_data.get('position', '').strip()
                # Add any other fields expected by contacts_crud.add_contact or .update_contact
            }

            if existing_contact:
                contact_id_to_link = existing_contact['contact_id']
                # Check if any details need updating for the global contact
                update_payload = {
                    k: contact_details_for_db[k]
                    for k, v in contact_details_for_db.items()
                    if k in existing_contact and v != existing_contact.get(k) and v # Only update if different and not empty
                }
                if update_payload:
                    logging.info(f"Updating existing global contact {contact_id_to_link} with data: {update_payload}")
                    self.update_contact(contact_id_to_link, update_payload)
            else:
                logging.info(f"No existing global contact found for email {email}. Creating new one.")
                logging.info(f"Attempting to add new global contact for email {email} with details: {contact_details_for_db}") # New log
                new_contact_id = self.add_contact(contact_details_for_db)
                if new_contact_id:
                    contact_id_to_link = new_contact_id
                else:
                    logging.error(f"Failed to create new global contact for email {email}.")
                    # Potentially show message to user via main window signal or direct QMessageBox if context allows
                    return None, None # Critical failure if contact cannot be added

            if not contact_id_to_link:
                logging.error("Could not determine contact_id_to_link.")
                return None, None

            # Handle primary contact logic: if this contact is primary, unmark others.
            is_primary_for_client = contact_form_data.get('is_primary_for_client', False)
            if is_primary_for_client:
                client_contacts = self.get_contacts_for_client(client_id)
                if client_contacts:
                    for cc in client_contacts:
                        # Ensure 'is_primary_for_client' and 'client_contact_id' exist
                        if cc.get('is_primary_for_client') and cc.get('client_contact_id') and cc.get('contact_id') != contact_id_to_link:
                            logging.info(f"Unmarking existing primary contact link {cc['client_contact_id']} for client {client_id}.")
                            self.update_client_contact_link(cc['client_contact_id'], {'is_primary_for_client': False})

            # Link the contact to the client
            # Check if link already exists to prevent duplicates, or let DB handle it (contacts_crud.link_contact_to_client might check)
            # For simplicity, let's assume link_contact_to_client handles existing links gracefully or an error is acceptable if it doesn't.
            # A more robust check would be:
            # existing_links = self.get_contacts_for_client(client_id)
            # if any(link['contact_id'] == contact_id_to_link for link in existing_links):
            #    logging.info(f"Contact {contact_id_to_link} already linked to client {client_id}. Updating role/primary status if needed.")
            #    # Find the specific client_contact_id and call update_client_contact_link
            # else:
            #    # Create new link

            # Corrected call:
            is_primary = contact_form_data.get('is_primary_for_client', False)
            can_receive = contact_form_data.get('can_receive_documents', True) # Get from form data
            role_from_form = contact_form_data.get('role_in_project')

            if role_from_form:
                logging.info(f"Contact role '{role_from_form}' was provided for contact {contact_id_to_link} and client {client_id}, but is not currently saved to the ClientContacts link.")

            logging.info(f"Attempting to link contact_id {contact_id_to_link} to client_id {client_id} with is_primary={is_primary}, can_receive_docs={can_receive}") # New log
            link_id = self.link_contact_to_client(
                client_id,
                contact_id_to_link,
                is_primary=is_primary,
                can_receive_documents=can_receive,
                role=role_from_form # This 'role' is now handled by the method's signature but not passed to CRUD
            )

            if not link_id:
                # This could happen if the link already exists and link_contact_to_client doesn't update/return ID for existing.
                # Or if there was an actual error.
                logging.warning(f"Failed to create new link or get existing link ID for contact {contact_id_to_link} to client {client_id}. Link might already exist.")
                # Try to find existing link to return its ID if that's the case.
                # This part depends on how contacts_crud.link_contact_to_client behaves with existing links.
                # For now, we just return what we have.

            return contact_id_to_link, link_id

        except Exception as e:
            logging.error(f"Exception in get_or_create_contact_and_link for client {client_id}, email {email}: {e}", exc_info=True)
            return None, None

# Example usage (for testing purposes, would be removed or in a test file)
if __name__ == '__main__':
    # This requires contacts_crud to be available and configured for DB access.
    # Mocking would be needed for standalone unit testing.
    logging.basicConfig(level=logging.INFO)
    controller = ContactController()

    # --- Test Add Contact ---
    # test_contact_data = {'name': 'Jane Test', 'email': 'jane.test@example.com', 'phone': '1234567890', 'position': 'Tester'}
    # new_id = controller.add_contact(test_contact_data)
    # if new_id:
    #     logging.info(f"Added contact with ID: {new_id}")
    #     # --- Test Get Contact ---
    #     retrieved_contact = controller.get_contact_by_id(new_id)
    #     logging.info(f"Retrieved contact: {retrieved_contact}")

    #     # --- Test Update Contact ---
    #     update_success = controller.update_contact(new_id, {'phone': '0987654321', 'position': 'Lead Tester'})
    #     logging.info(f"Update success: {update_success}")
    #     retrieved_updated_contact = controller.get_contact_by_id(new_id)
    #     logging.info(f"Retrieved updated contact: {retrieved_updated_contact}")

    #     # --- Test Link Contact to Client (assuming client_id 'client_dummy_1' exists) ---
    #     client_id_example = 'client_dummy_1' # Replace with a valid client ID for testing
    #     link_id_created = controller.link_contact_to_client(client_id_example, new_id, is_primary=True, role="Primary Test Contact")
    #     if link_id_created:
    #         logging.info(f"Linked contact {new_id} to client {client_id_example} with link ID: {link_id_created}")
    #         # --- Test Get Contacts for Client ---
    #         client_contacts_list = controller.get_contacts_for_client(client_id_example)
    #         logging.info(f"Contacts for client {client_id_example}: {client_contacts_list}")

    #         # --- Test Update Client Contact Link ---
    #         # Find the client_contact_id from client_contacts_list (it's the primary key of the link table)
    #         # This assumes the link_id_created is the client_contact_id, which might or might not be true
    #         # depending on contacts_crud.link_contact_to_client implementation.
    #         # Let's assume it is for this example if the list contains one item.
    #         if client_contacts_list and client_contacts_list[0].get('client_contact_id'):
    #             client_contact_id_to_update = client_contacts_list[0]['client_contact_id']
    #             update_link_success = controller.update_client_contact_link(client_contact_id_to_update, {'role': 'Lead Test Contact Updated'})
    #             logging.info(f"Updated client_contact_link {client_contact_id_to_update} success: {update_link_success}")
    #             updated_links = controller.get_contacts_for_client(client_id_example)
    #             logging.info(f"Updated contacts for client {client_id_example}: {updated_links}")

    # else:
    #     logging.error("Failed to add initial test contact.")

    # --- Test get_or_create_contact_and_link ---
    # client_id_for_goc = 'client_goc_test_1' # Ensure this client exists or mock client creation
    # contact_dialog_data = {
    #     'name': 'Mike GOC Test',
    #     'email': 'mike.goc.test@example.com',
    #     'phone': '555111222',
    #     'position': 'GOC Manager',
    #     'is_primary_for_client': True,
    #     'role_in_project': 'Key Decision Maker'
    # }
    # goc_contact_id, goc_link_id = controller.get_or_create_contact_and_link(client_id_for_goc, contact_dialog_data)
    # if goc_contact_id:
    #     logging.info(f"get_or_create_contact_and_link successful: Contact ID {goc_contact_id}, Link ID {goc_link_id}")
    #     contacts_for_goc_client = controller.get_contacts_for_client(client_id_for_goc)
    #     logging.info(f"Contacts for GOC client {client_id_for_goc}: {contacts_for_goc_client}")
    # else:
    #     logging.error(f"get_or_create_contact_and_link failed for client {client_id_for_goc}")

    # Test with an existing email to see if it updates and links
    # contact_dialog_data_existing_email = {
    #     'name': 'Mike GOC Test Updated Name', # Name changed
    #     'email': 'mike.goc.test@example.com', # Same email
    #     'phone': '555111333', # Phone changed
    #     'position': 'Senior GOC Manager',
    #     'is_primary_for_client': True,
    #     'role_in_project': 'Main Point of Contact'
    # }
    # goc_contact_id_existing, goc_link_id_existing = controller.get_or_create_contact_and_link(client_id_for_goc, contact_dialog_data_existing_email)
    # if goc_contact_id_existing:
    #     logging.info(f"get_or_create_contact_and_link (existing email) successful: Contact ID {goc_contact_id_existing}, Link ID {goc_link_id_existing}")
    #     retrieved_goc_contact = controller.get_contact_by_id(goc_contact_id_existing)
    #     logging.info(f"Retrieved GOC contact after update: {retrieved_goc_contact}")
    #     contacts_for_goc_client_after_update = controller.get_contacts_for_client(client_id_for_goc)
    #     logging.info(f"Contacts for GOC client {client_id_for_goc} after update: {contacts_for_goc_client_after_update}")

    # else:
    #     logging.error(f"get_or_create_contact_and_link (existing email) failed for client {client_id_for_goc}")

    pass # End of example usage
