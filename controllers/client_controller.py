# controllers/client_controller.py
import db as db_manager # Assuming db_manager is the existing module for DB interactions
from db.cruds import clients_crud, products_crud, client_project_products_crud
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ClientController:
    def __init__(self):
        # In the future, we might pass a specific DB connection or configuration
        pass

    def get_all_countries(self):
        """Fetches all countries from the database."""
        try:
            # Assuming db_manager.get_all_countries() returns a list of dicts
            # e.g., [{'country_id': 1, 'country_name': 'USA'}, ...]
            return db_manager.get_all_countries()
        except Exception as e:
            print(f"Error in ClientController.get_all_countries: {e}") # Basic error handling
            # Consider logging this error properly
            return [] # Return empty list on error

    def get_cities_for_country(self, country_id):
        """Fetches all cities for a given country_id."""
        try:
            # Assuming db_manager.get_all_cities(country_id=country_id) returns a list of dicts
            # e.g., [{'city_id': 1, 'city_name': 'New York', 'country_id': 1}, ...]
            return db_manager.get_all_cities(country_id=country_id)
        except Exception as e:
            print(f"Error in ClientController.get_cities_for_country: {e}")
            return []

    def add_country(self, country_name):
        """Adds a new country to the database.
        Returns the new country's data (e.g., dict with id and name) or None on failure.
        """
        if not country_name or not country_name.strip():
            # Basic validation
            return None
        try:
            # Assuming db_manager.add_country({'country_name': country_name.strip()})
            # returns the ID of the newly added country or the country dict.
            # Let's assume it returns a dict {'country_id': id, 'country_name': name} for consistency
            # or db_manager.get_or_add_country which might be more robust.
            # Based on AddNewClientDialog, it seems `add_country` returns an ID,
            # and `get_or_add_country` returns a dict.
            # Let's aim for get_or_add_country behavior if available, or adapt.

            # Using get_or_add_country as it's generally safer and used in dialogs
            country_data = db_manager.get_or_add_country(country_name.strip())
            return country_data # Expects {'country_id': id, 'country_name': name} or similar
        except Exception as e:
            print(f"Error in ClientController.add_country: {e}")
            return None

    def add_city(self, city_name, country_id):
        """Adds a new city to the database for the given country_id.
        Returns the new city's data (e.g., dict with id and name) or None on failure.
        """
        if not city_name or not city_name.strip() or country_id is None:
            # Basic validation
            return None
        try:
            # Assuming db_manager.get_or_add_city(city_name.strip(), country_id)
            # returns a dict {'city_id': id, 'city_name': name, 'country_id': country_id}
            city_data = db_manager.get_or_add_city(city_name.strip(), country_id)
            return city_data
        except Exception as e:
            print(f"Error in ClientController.add_city: {e}")
            return None

    def create_client(self, client_data: dict):
        """
        Creates a new client.
        client_data is a dictionary expected to contain keys like:
        'client_name', 'company_name', 'primary_need_description',
        'country_name', 'city_name', 'project_identifier', 'selected_languages'

        This method will handle resolving country and city names to IDs,
        adding them to the database if they don't exist.
        Returns the created client data (with IDs) or None on failure.
        """
        try:
            country_name = client_data.get('country_name', '').strip()
            city_name = client_data.get('city_name', '').strip()

            if not country_name:
                print("Error: Country name is required to create a client.")
                return None # Or raise ValueError

            # Get or add country
            country_obj = self.add_country(country_name) # add_country handles get_or_add
            if not country_obj or 'country_id' not in country_obj:
                print(f"Error: Could not get or add country '{country_name}'.")
                return None

            final_country_id = country_obj['country_id']

            final_city_id = None
            if city_name:
                city_obj = self.add_city(city_name, final_country_id)
                if not city_obj or 'city_id' not in city_obj:
                    print(f"Warning: Could not get or add city '{city_name}'. Proceeding without city.")
                    # Depending on requirements, this could be an error or a warning.
                    # For now, allow client creation without a city if city processing fails.
                else:
                    final_city_id = city_obj['city_id']

            # Prepare data for db_manager.add_client (or equivalent)
            # The actual fields for add_client need to be checked against db_manager.py
            # Assuming db_manager.add_client takes a dictionary similar to this:
            db_client_data = {
                'client_name': client_data.get('client_name'),
                'company_name': client_data.get('company_name'),
                'primary_need_description': client_data.get('primary_need_description'),
                'country_id': final_country_id,
                'city_id': final_city_id, # Can be None
                'project_identifier': client_data.get('project_identifier'),
                'client_status_id': client_data.get('client_status_id', 1), # Default status if applicable
                'languages': client_data.get('selected_languages') # Assuming this is how languages are stored
                # 'default_template_id': client_data.get('default_template_id') # Removed

                # Add any other fields required by the database schema for a client
            }

            # Validate required client fields before calling db_manager
            if not db_client_data.get('client_name'):
                print("Error: Client name is required.")
                return None

            # Assuming db_manager.add_client returns the newly created client object or its ID
            # Let's assume it returns a dict of the created client for consistency
            # new_client = db_manager.add_client(db_client_data) # Original incorrect call
            # Corrected call:
            # The add_client function in clients_crud.py expects the data dict directly.
            # It also requires 'created_by_user_id'. This needs to be added to db_client_data
            # or passed explicitly if the controller has access to it.
            # For now, let's assume it's part of client_data or a default is used.
            if 'created_by_user_id' not in db_client_data:
                # Add a placeholder or fetch actual user ID if available in controller context
                db_client_data['created_by_user_id'] = 'SYSTEM_USER' # Placeholder

            result = clients_crud.add_client(db_client_data) # Call the CRUD function

            if result and result.get('success'):
                # If successful, fetch the full client details to return a consistent object
                new_client_id = result.get('client_id')
                # It's better to return the full client dict as expected by some calling UI components
                # The CRUD's get_client_by_id or get_all_clients_with_details can be used.
                # For simplicity, if the UI primarily needs the ID and basic info,
                # we can augment the input data with the new ID.
                # However, a full fetch is cleaner.
            # For this refactor, let's assume returning the result from add_client is sufficient for now.
                # The add_client CRUD returns {'success': True, 'client_id': new_id}.
                if new_client_id:
                    created_client_details = clients_crud.clients_crud_instance.get_client_by_id(new_client_id)
                if not created_client_details:
                    logging.warning(f"Client created with ID {new_client_id}, but failed to fetch details. Returning minimal info.")
                    created_client_details = {'client_id': new_client_id, 'client_name': db_client_data.get('client_name'), 'success': True, 'warning': 'Details fetch failed'}
                else:
                    logging.info(f"Client '{created_client_details.get('client_name')}' created successfully with ID {new_client_id}.")

                # --- Add Product if data is provided ---
                if client_data.get('product_product_name', '').strip():
                    logging.info(f"Attempting to add product for client ID {new_client_id}.")
                    product_base_price_str = client_data.get('product_base_unit_price', '0').strip()
                    try:
                        product_base_price = float(product_base_price_str) if product_base_price_str else 0.0
                    except ValueError:
                        logging.error(f"Invalid base_unit_price format: '{product_base_price_str}'. Defaulting to 0.0.")
                        product_base_price = 0.0

                    new_product_data = {
                        'product_name': client_data.get('product_product_name').strip(),
                        'product_code': client_data.get('product_product_code', '').strip(),
                        'description': client_data.get('product_product_description', '').strip(),
                        'category_name': client_data.get('product_product_category', '').strip(), # Assuming products_crud handles category by name
                        'language_code': client_data.get('product_product_language_code', 'en').strip(), # Default 'en'
                        'base_unit_price': product_base_price,
                        'unit_of_measure': client_data.get('product_unit_of_measure', '').strip(),
                        'is_active': True,
                        'created_by_user_id': db_client_data['created_by_user_id']
                        # 'supplier_id': None, # Assuming not provided here
                        # 'currency_code': 'USD', # Assuming default or needs to be passed
                    }

                    product_result = products_crud.add_product(new_product_data)

                    if product_result and product_result.get('success'):
                        new_product_id = product_result.get('product_id')
                        logging.info(f"Product '{new_product_data['product_name']}' added successfully with ID {new_product_id}.")
                        created_client_details['product_creation_status'] = {'success': True, 'product_id': new_product_id, 'product_name': new_product_data['product_name']}

                        # Link product to client/project
                        # Determine project_id:
                        # The current 'create_client' method stores 'project_identifier' in 'clients' table.
                        # It does not explicitly create a project or return a project_id here.
                        # For now, we'll assume project_id is None for this link,
                        # unless client_data contains an explicit 'project_id' (e.g. resolved earlier).
                        # This part might need refinement based on how projects are managed.
                        resolved_project_id = client_data.get('resolved_project_id') # Ideal, if resolved before this controller method

                        link_data = {
                            'client_id': new_client_id,
                            'product_id': new_product_id,
                            'project_id': resolved_project_id, # This needs to be sourced correctly.
                            'quantity': 1, # Default quantity
                            'added_by_user_id': db_client_data['created_by_user_id']
                        }
                        link_result = client_project_products_crud.add_product_to_client_or_project(link_data)
                        if link_result and link_result.get('success'):
                            logging.info(f"Successfully linked product ID {new_product_id} to client ID {new_client_id}.")
                            created_client_details['product_linking_status'] = {'success': True, 'link_id': link_result.get('link_id')}
                        else:
                            error_msg = link_result.get('error', 'Failed to link product to client/project.')
                            logging.error(f"Failed to link product ID {new_product_id} to client ID {new_client_id}: {error_msg}")
                            created_client_details['product_linking_status'] = {'success': False, 'error': error_msg}
                    else:
                        error_msg = product_result.get('error', 'Failed to add product.')
                        logging.error(f"Failed to add product for client ID {new_client_id}: {error_msg}")
                        created_client_details['product_creation_status'] = {'success': False, 'error': error_msg}
                else:
                    logging.info(f"No product information provided for client ID {new_client_id}.")

                return created_client_details # Return the (potentially augmented) client details
            else: # Should not happen if success is True and client_id is missing from clients_crud.add_client result
                logging.error("Client creation reported success by CRUD but no client_id was returned.")
                return {'success': False, 'error': 'Client ID missing after reported successful creation.'}
            # else:
            #     error_message = result.get('error', 'Failed to create client in database.')
            #     print(f"Error: {error_message}")
            #     return {'success': False, 'error': error_message} # Return the error dict

        except Exception as e:
            logging.exception(f"Unhandled exception in ClientController.create_client: {e}")
            return {'success': False, 'error': f"An unexpected error occurred: {str(e)}"}

# # Example usage (for testing purposes, would be removed or in a test file)
# if __name__ == '__main__':
#             else:
#                 print("Error: Failed to create client in database.")
#                 return None

#         except Exception as e:
#             print(f"Error in ClientController.create_client: {e}")
#             # Consider logging this error properly
#             return None

# Example usage (for testing purposes, would be removed or in a test file)
if __name__ == '__main__':
    controller = ClientController()

    # Test fetching countries
    # print("Countries:", controller.get_all_countries())

    # Test adding a country (assuming 'Testland' doesn't exist or get_or_add works)
    # test_country = controller.add_country("Testland")
    # print("Added/Fetched Country:", test_country)

    # if test_country and test_country.get('country_id'):
    #     # Test fetching cities for the new/existing country
    #     print(f"Cities in Testland:", controller.get_cities_for_country(test_country['country_id']))

    #     # Test adding a city
    #     test_city = controller.add_city("Testville", test_country['country_id'])
    #     print("Added/Fetched City:", test_city)

    #     # Test creating a client
    #     client_info = {
    #         'client_name': 'Test Client Inc.',
    #         'company_name': 'Test Client Solutions',
    #         'primary_need_description': 'Testing services',
    #         'country_name': 'Testland',
    #         'city_name': 'Testville',
    #         'project_identifier': 'PROJ_TEST_001',
    #         'selected_languages': 'en,fr'
    #     }
    #     created_client = controller.create_client(client_info)
    #     print("Created Client:", created_client)
