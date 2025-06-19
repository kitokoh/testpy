# controllers/client_controller.py
import db as db_manager # Assuming db_manager is the existing module for DB interactions

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
                # Add any other fields required by the database schema for a client
            }

            # Validate required client fields before calling db_manager
            if not db_client_data.get('client_name'):
                print("Error: Client name is required.")
                return None

            # Assuming db_manager.add_client returns the newly created client object or its ID
            # Let's assume it returns a dict of the created client for consistency
            new_client = db_manager.add_client(db_client_data)
            if new_client:
                print(f"Client '{new_client.get('client_name')}' created successfully.")
                return new_client
            else:
                print("Error: Failed to create client in database.")
                return None

        except Exception as e:
            print(f"Error in ClientController.create_client: {e}")
            # Consider logging this error properly
            return None

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
