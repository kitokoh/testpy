import unittest
from unittest.mock import patch, MagicMock, ANY
import sys
import os

# Adjust path to import ClientController from the parent directory's controllers folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from controllers.client_controller import ClientController

# This is the existing test class. We will add/modify methods in it.
class TestClientController(unittest.TestCase):

    def setUp(self):
        self.controller = ClientController()

    # --- Tests for country/city utility methods (can remain as they use db_manager) ---
    @patch('controllers.client_controller.db_manager')
    def test_get_all_countries_success(self, mock_db_manager):
        expected_countries = [{'country_id': 1, 'country_name': 'Testland'}]
        mock_db_manager.get_all_countries.return_value = expected_countries
        countries = self.controller.get_all_countries()
        mock_db_manager.get_all_countries.assert_called_once()
        self.assertEqual(countries, expected_countries)

    @patch('controllers.client_controller.db_manager')
    def test_get_all_countries_failure(self, mock_db_manager):
        mock_db_manager.get_all_countries.side_effect = Exception("DB error")
        countries = self.controller.get_all_countries()
        mock_db_manager.get_all_countries.assert_called_once()
        self.assertEqual(countries, [])

    @patch('controllers.client_controller.db_manager')
    def test_get_cities_for_country_success(self, mock_db_manager):
        expected_cities = [{'city_id': 1, 'city_name': 'Testville', 'country_id': 1}]
        mock_db_manager.get_all_cities.return_value = expected_cities
        cities = self.controller.get_cities_for_country(1)
        mock_db_manager.get_all_cities.assert_called_once_with(country_id=1)
        self.assertEqual(cities, expected_cities)

    @patch('controllers.client_controller.db_manager')
    def test_add_country_new(self, mock_db_manager):
        country_name = "Newland"
        expected_country_data = {'country_id': 2, 'country_name': country_name}
        # ClientController.add_country uses db_manager.get_or_add_country
        mock_db_manager.get_or_add_country.return_value = expected_country_data
        country_data = self.controller.add_country(country_name)
        mock_db_manager.get_or_add_country.assert_called_once_with(country_name.strip())
        self.assertEqual(country_data, expected_country_data)

    @patch('controllers.client_controller.db_manager')
    def test_add_city_new(self, mock_db_manager):
        city_name = "Newville"
        country_id = 1
        expected_city_data = {'city_id': 3, 'city_name': city_name, 'country_id': country_id}
        # ClientController.add_city uses db_manager.get_or_add_city
        mock_db_manager.get_or_add_city.return_value = expected_city_data
        city_data = self.controller.add_city(city_name, country_id)
        mock_db_manager.get_or_add_city.assert_called_once_with(city_name.strip(), country_id)
        self.assertEqual(city_data, expected_city_data)

    # --- Tests for create_client (modified/new) ---

    @patch('controllers.client_controller.clients_crud')
    @patch('controllers.client_controller.products_crud')
    @patch('controllers.client_controller.client_project_products_crud')
    @patch.object(ClientController, 'add_country') # Patch instance method directly
    @patch.object(ClientController, 'add_city')    # Patch instance method directly
    @patch('controllers.client_controller.logging')
    def test_create_client_with_new_product(self, mock_logging, mock_add_city_method, mock_add_country_method,
                                            mock_cpp_crud, mock_products_crud, mock_clients_crud):
        # Setup Mocks for add_country/add_city called by create_client
        mock_add_country_method.return_value = {'country_id': 1, 'country_name': 'Testland'}
        mock_add_city_method.return_value = {'city_id': 1, 'city_name': 'Testville'}

        # Mock clients_crud
        mock_clients_crud.add_client.return_value = {'success': True, 'client_id': 'test_client_id_123'}
        # Mock the clients_crud_instance separately for get_client_by_id
        # If clients_crud is a module and clients_crud_instance is an attribute of it:
        mock_clients_crud.clients_crud_instance = MagicMock()
        mock_clients_crud.clients_crud_instance.get_client_by_id.return_value = {
            'client_id': 'test_client_id_123', 'client_name': 'Test Client Inc.',
            'company_name': 'Test Solutions Ltd.', 'country_id': 1, 'city_id': 1,
            'success': True
        }

        # Mock products_crud
        mock_products_crud.add_product.return_value = {'success': True, 'product_id': 'test_product_id_456'}

        # Mock client_project_products_crud
        mock_cpp_crud.add_product_to_client_or_project.return_value = {'success': True, 'link_id': 'link_789'}

        client_data = {
            'client_name': 'Test Client Inc.', 'company_name': 'Test Solutions Ltd.',
            'primary_need_description': 'Needs widgets.', 'country_name': 'Testland',
            'city_name': 'Testville', 'project_identifier': 'PROJ001',
            'selected_languages': 'en,fr', 'created_by_user_id': 'user_test_admin',
            'product_product_name': 'Super Widget', 'product_product_code': 'SW001',
            'product_product_description': 'A very super widget.', 'product_product_category': 'Widgets Deluxe',
            'product_product_language_code': 'en', 'product_base_unit_price': '199.99',
            'product_unit_of_measure': 'unit'
        }

        result = self.controller.create_client(client_data)

        mock_add_country_method.assert_called_once_with('Testland')
        mock_add_city_method.assert_called_once_with('Testville', 1)

        expected_db_client_data = {
            'client_name': 'Test Client Inc.', 'company_name': 'Test Solutions Ltd.',
            'primary_need_description': 'Needs widgets.', 'country_id': 1, 'city_id': 1,
            'project_identifier': 'PROJ001', 'client_status_id': 1, 'languages': 'en,fr',
            'created_by_user_id': 'user_test_admin'
        }
        mock_clients_crud.add_client.assert_called_once_with(expected_db_client_data)
        mock_clients_crud.clients_crud_instance.get_client_by_id.assert_called_once_with('test_client_id_123')

        expected_product_data = {
            'product_name': 'Super Widget', 'product_code': 'SW001',
            'description': 'A very super widget.', 'category_name': 'Widgets Deluxe',
            'language_code': 'en', 'base_unit_price': 199.99,
            'unit_of_measure': 'unit', 'is_active': True,
            'created_by_user_id': 'user_test_admin'
        }
        mock_products_crud.add_product.assert_called_once_with(expected_product_data)

        expected_link_data = {
            'client_id': 'test_client_id_123', 'product_id': 'test_product_id_456',
            'project_id': None, 'quantity': 1, 'added_by_user_id': 'user_test_admin'
        }
        mock_cpp_crud.add_product_to_client_or_project.assert_called_once_with(expected_link_data)

        self.assertTrue(result.get('success'))
        self.assertEqual(result.get('client_id'), 'test_client_id_123')
        self.assertTrue(result['product_creation_status'].get('success'))
        self.assertTrue(result['product_linking_status'].get('success'))

    @patch('controllers.client_controller.clients_crud')
    @patch('controllers.client_controller.products_crud')
    @patch('controllers.client_controller.client_project_products_crud')
    @patch.object(ClientController, 'add_country')
    @patch.object(ClientController, 'add_city')
    @patch('controllers.client_controller.logging')
    def test_create_client_without_product(self, mock_logging, mock_add_city_method, mock_add_country_method,
                                           mock_cpp_crud, mock_products_crud, mock_clients_crud):
        mock_add_country_method.return_value = {'country_id': 1, 'country_name': 'Testland'}
        mock_add_city_method.return_value = {'city_id': 1, 'city_name': 'Testville'}

        mock_clients_crud.add_client.return_value = {'success': True, 'client_id': 'test_client_id_789'}
        mock_clients_crud.clients_crud_instance = MagicMock() # Ensure instance is mocked
        mock_clients_crud.clients_crud_instance.get_client_by_id.return_value = {
            'client_id': 'test_client_id_789', 'client_name': 'No Product Client', 'success': True
        }

        client_data_no_product = {
            'client_name': 'No Product Client', 'country_name': 'Testland',
            'city_name': 'Testville', 'created_by_user_id': 'user_test_admin',
            'primary_need_description': 'General services', 'project_identifier': 'PROJNP002',
            'selected_languages': 'fr'
            # No product_product_name or other product_* fields
        }

        result = self.controller.create_client(client_data_no_product)

        mock_add_country_method.assert_called_once_with('Testland')
        mock_add_city_method.assert_called_once_with('Testville', 1)

        expected_db_client_data = {
            'client_name': 'No Product Client', 'company_name': None, # Defaults if not provided
            'primary_need_description': 'General services', 'country_id': 1, 'city_id': 1,
            'project_identifier': 'PROJNP002', 'client_status_id': 1, 'languages': 'fr',
            'created_by_user_id': 'user_test_admin'
        }
        mock_clients_crud.add_client.assert_called_once_with(expected_db_client_data)
        mock_clients_crud.clients_crud_instance.get_client_by_id.assert_called_once_with('test_client_id_789')

        mock_products_crud.add_product.assert_not_called()
        mock_cpp_crud.add_product_to_client_or_project.assert_not_called()

        self.assertTrue(result.get('success'))
        self.assertEqual(result.get('client_id'), 'test_client_id_789')
        self.assertNotIn('product_creation_status', result)
        self.assertNotIn('product_linking_status', result)

    # Add other existing tests for create_client (failure scenarios) if they need to be adapted
    # For example, test_create_client_fail_no_country_name:
    @patch.object(ClientController, 'add_country') # No need to mock db_manager for this one
    @patch('controllers.client_controller.logging')
    def test_create_client_fail_no_country_name(self, mock_logging, mock_add_country_method):
        # This test checks validation before add_country is even meaningfully processed if country_name is empty
        client_input_data = {'client_name': 'Test Client C', 'country_name': ''}
        # We don't expect add_country to be called with an empty name if validation catches it first.
        # The controller's logic is: if not country_name: print error; return None.
        # So, add_country won't be called.

        result = self.controller.create_client(client_input_data)

        self.assertIsNone(result) # The controller returns None directly
        mock_add_country_method.assert_not_called() # add_country should not be called if name is empty

    @patch.object(ClientController, 'add_country')
    @patch('controllers.client_controller.clients_crud') # Mock clients_crud as it might be called
    @patch('controllers.client_controller.logging')
    def test_create_client_fail_no_client_name(self, mock_logging, mock_clients_crud, mock_add_country_method):
        client_input_data = {'client_name': '', 'country_name': 'SomeCountry'}
        mock_add_country_method.return_value = {'country_id': 1, 'country_name': 'SomeCountry'}

        result = self.controller.create_client(client_input_data)

        # The controller should call add_country, but then fail validation for client_name before calling clients_crud.add_client
        mock_add_country_method.assert_called_once_with('SomeCountry')
        mock_clients_crud.add_client.assert_not_called()
        self.assertIn('error', result) # Expecting a dict with error message
        self.assertFalse(result.get('success'))


if __name__ == '__main__':
    unittest.main()
