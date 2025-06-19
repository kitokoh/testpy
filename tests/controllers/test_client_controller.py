# tests/controllers/test_client_controller.py
import unittest
from unittest.mock import patch, MagicMock

# Assuming controllers are in the project's PYTHONPATH
from controllers.client_controller import ClientController

class TestClientController(unittest.TestCase):

    def setUp(self):
        self.controller = ClientController()

    @patch('controllers.client_controller.db_manager')
    def test_get_all_countries_success(self, mock_db_manager):
        # Configure the mock
        expected_countries = [{'country_id': 1, 'country_name': 'Testland'}]
        mock_db_manager.get_all_countries.return_value = expected_countries

        # Call the method
        countries = self.controller.get_all_countries()

        # Assert
        mock_db_manager.get_all_countries.assert_called_once()
        self.assertEqual(countries, expected_countries)

    @patch('controllers.client_controller.db_manager')
    def test_get_all_countries_failure(self, mock_db_manager):
        mock_db_manager.get_all_countries.side_effect = Exception("DB error")

        countries = self.controller.get_all_countries()

        mock_db_manager.get_all_countries.assert_called_once()
        self.assertEqual(countries, []) # Expect empty list on error

    @patch('controllers.client_controller.db_manager')
    def test_get_cities_for_country_success(self, mock_db_manager):
        expected_cities = [{'city_id': 1, 'city_name': 'Testville', 'country_id': 1}]
        mock_db_manager.get_all_cities.return_value = expected_cities

        country_id = 1
        cities = self.controller.get_cities_for_country(country_id)

        mock_db_manager.get_all_cities.assert_called_once_with(country_id=country_id)
        self.assertEqual(cities, expected_cities)

    @patch('controllers.client_controller.db_manager')
    def test_get_cities_for_country_failure(self, mock_db_manager):
        mock_db_manager.get_all_cities.side_effect = Exception("DB error")

        cities = self.controller.get_cities_for_country(1)

        mock_db_manager.get_all_cities.assert_called_once_with(country_id=1)
        self.assertEqual(cities, [])

    @patch('controllers.client_controller.db_manager')
    def test_add_country_new(self, mock_db_manager):
        country_name = "Newland"
        expected_country_data = {'country_id': 2, 'country_name': country_name}
        mock_db_manager.get_or_add_country.return_value = expected_country_data

        country_data = self.controller.add_country(country_name)

        mock_db_manager.get_or_add_country.assert_called_once_with(country_name.strip())
        self.assertEqual(country_data, expected_country_data)

    @patch('controllers.client_controller.db_manager')
    def test_add_country_empty_name(self, mock_db_manager):
        country_data = self.controller.add_country("   ") # Empty or whitespace
        self.assertIsNone(country_data)
        mock_db_manager.get_or_add_country.assert_not_called()

    @patch('controllers.client_controller.db_manager')
    def test_add_city_new(self, mock_db_manager):
        city_name = "Newville"
        country_id = 1
        expected_city_data = {'city_id': 3, 'city_name': city_name, 'country_id': country_id}
        mock_db_manager.get_or_add_city.return_value = expected_city_data

        city_data = self.controller.add_city(city_name, country_id)

        mock_db_manager.get_or_add_city.assert_called_once_with(city_name.strip(), country_id)
        self.assertEqual(city_data, expected_city_data)

    @patch('controllers.client_controller.db_manager')
    def test_add_city_empty_name(self, mock_db_manager):
        city_data = self.controller.add_city("  ", 1)
        self.assertIsNone(city_data)
        mock_db_manager.get_or_add_city.assert_not_called()

    @patch('controllers.client_controller.db_manager')
    def test_add_city_none_country_id(self, mock_db_manager):
        city_data = self.controller.add_city("SomeCity", None)
        self.assertIsNone(city_data)
        mock_db_manager.get_or_add_city.assert_not_called()

    @patch('controllers.client_controller.db_manager')
    def test_create_client_success_new_country_city(self, mock_db_manager):
        client_input_data = {
            'client_name': 'Test Client A',
            'company_name': 'Test Co A',
            'primary_need_description': 'Services A',
            'country_name': 'Wonderland', # New country
            'city_name': 'Wondercity',     # New city
            'project_identifier': 'PROJ001',
            'selected_languages': 'en,fr',
            'created_by_user_id': 'user123'
        }

        # Mock return values for get_or_add_country, get_or_add_city, add_client
        mock_country = {'country_id': 10, 'country_name': 'Wonderland'}
        mock_city = {'city_id': 20, 'city_name': 'Wondercity', 'country_id': 10}
        # ClientController's add_client calls db_manager.add_client
        # The ClientController.create_client constructs a dict for db_manager.add_client
        # Let's assume db_manager.add_client returns the client dict including new ID
        expected_client_db_input = {
            'client_name': 'Test Client A',
            'company_name': 'Test Co A',
            'primary_need_description': 'Services A',
            'country_id': 10,
            'city_id': 20,
            'project_identifier': 'PROJ001',
            'client_status_id': 1, # Default from controller's create_client
            'languages': 'en,fr',
            # created_by_user_id is not explicitly passed to db_manager.add_client in controller
            # but it's part of the input dict to controller.create_client
            # Let's verify if the controller's `db_client_data` for `db_manager.add_client` is correct
        }
        mock_created_client_from_db = {**expected_client_db_input, 'client_id': 100, 'created_at': 'sometime'}


        mock_db_manager.get_or_add_country.return_value = mock_country
        mock_db_manager.get_or_add_city.return_value = mock_city
        mock_db_manager.add_client.return_value = mock_created_client_from_db

        created_client = self.controller.create_client(client_input_data)

        mock_db_manager.get_or_add_country.assert_called_once_with('Wonderland')
        mock_db_manager.get_or_add_city.assert_called_once_with('Wondercity', 10)
        # Assert that db_manager.add_client was called with the correctly assembled dictionary
        mock_db_manager.add_client.assert_called_once_with(expected_client_db_input)

        self.assertIsNotNone(created_client)
        self.assertEqual(created_client['client_id'], 100)
        self.assertEqual(created_client['country_id'], 10)
        self.assertEqual(created_client['city_id'], 20)
        self.assertEqual(created_client['client_name'], 'Test Client A')

    @patch('controllers.client_controller.db_manager')
    def test_create_client_success_existing_country_no_city(self, mock_db_manager):
        client_input_data = {
            'client_name': 'Test Client B',
            'country_name': 'Existingland',
            'city_name': '', # No city
            'project_identifier': 'PROJ002',
            'selected_languages': 'es'
        }
        mock_country = {'country_id': 11, 'country_name': 'Existingland'}
        # db_manager.add_client will be called with city_id=None
        expected_client_db_input = {
            'client_name': 'Test Client B',
            'company_name': None,
            'primary_need_description': None,
            'country_id': 11,
            'city_id': None,
            'project_identifier': 'PROJ002',
            'client_status_id': 1,
            'languages': 'es'
        }
        mock_created_client_from_db = {**expected_client_db_input, 'client_id': 101}

        mock_db_manager.get_or_add_country.return_value = mock_country
        mock_db_manager.add_client.return_value = mock_created_client_from_db

        created_client = self.controller.create_client(client_input_data)

        mock_db_manager.get_or_add_country.assert_called_once_with('Existingland')
        mock_db_manager.get_or_add_city.assert_not_called() # No city name provided
        mock_db_manager.add_client.assert_called_once_with(expected_client_db_input)

        self.assertIsNotNone(created_client)
        self.assertEqual(created_client['client_id'], 101)
        self.assertIsNone(created_client['city_id'])

    @patch('controllers.client_controller.db_manager')
    def test_create_client_fail_no_country_name(self, mock_db_manager):
        client_input_data = {'client_name': 'Test Client C', 'country_name': ''}
        created_client = self.controller.create_client(client_input_data)
        self.assertIsNone(created_client)
        mock_db_manager.get_or_add_country.assert_not_called()
        mock_db_manager.add_client.assert_not_called()

    @patch('controllers.client_controller.db_manager')
    def test_create_client_fail_no_client_name(self, mock_db_manager):
        client_input_data = {'client_name': '', 'country_name': 'SomeCountry'}
        # Controller's create_client should catch this before calling db_manager.add_client
        # if db_manager.get_or_add_country is mocked to return a valid country.
        mock_db_manager.get_or_add_country.return_value = {'country_id': 1, 'country_name': 'SomeCountry'}

        created_client = self.controller.create_client(client_input_data)

        self.assertIsNone(created_client)
        mock_db_manager.get_or_add_country.assert_called_once_with('SomeCountry') # Country processing happens first
        mock_db_manager.add_client.assert_not_called() # Should not be called if client_name is missing

    @patch('controllers.client_controller.db_manager')
    def test_create_client_fail_country_add_fails(self, mock_db_manager):
        client_input_data = {'client_name': 'Test Client D', 'country_name': 'FailCountry'}
        mock_db_manager.get_or_add_country.return_value = None # Simulate failure

        created_client = self.controller.create_client(client_input_data)

        self.assertIsNone(created_client)
        mock_db_manager.get_or_add_country.assert_called_once_with('FailCountry')
        mock_db_manager.add_client.assert_not_called()

    @patch('controllers.client_controller.db_manager')
    def test_create_client_warning_city_add_fails(self, mock_db_manager):
        # Test if client is still created if city addition fails (as per controller logic)
        client_input_data = {
            'client_name': 'Test Client E',
            'country_name': 'GoodCountry',
            'city_name': 'FailCity',
            'project_identifier': 'PROJ005'
        }
        mock_country = {'country_id': 12, 'country_name': 'GoodCountry'}
        mock_db_manager.get_or_add_country.return_value = mock_country
        mock_db_manager.get_or_add_city.return_value = None # Simulate city failure

        expected_client_db_input = {
            'client_name': 'Test Client E',
            'company_name': None,
            'primary_need_description': None,
            'country_id': 12,
            'city_id': None, # City ID should be None due to failure
            'project_identifier': 'PROJ005',
            'client_status_id': 1,
            'languages': None # Assuming default if not provided
        }
        mock_created_client_from_db = {**expected_client_db_input, 'client_id': 102}
        mock_db_manager.add_client.return_value = mock_created_client_from_db

        created_client = self.controller.create_client(client_input_data)

        mock_db_manager.get_or_add_country.assert_called_once_with('GoodCountry')
        mock_db_manager.get_or_add_city.assert_called_once_with('FailCity', 12)
        mock_db_manager.add_client.assert_called_once_with(expected_client_db_input)

        self.assertIsNotNone(created_client)
        self.assertEqual(created_client['client_id'], 102)
        self.assertIsNone(created_client['city_id']) # Ensure city_id is None

    @patch('controllers.client_controller.db_manager')
    def test_create_client_db_add_client_fails(self, mock_db_manager):
        client_input_data = {
            'client_name': 'Test Client F',
            'country_name': 'AnotherCountry',
            'project_identifier': 'PROJ006'
        }
        mock_country = {'country_id': 13, 'country_name': 'AnotherCountry'}
        mock_db_manager.get_or_add_country.return_value = mock_country
        mock_db_manager.add_client.return_value = None # Simulate db_manager.add_client failure

        created_client = self.controller.create_client(client_input_data)

        self.assertIsNone(created_client)
        mock_db_manager.get_or_add_country.assert_called_once_with('AnotherCountry')
        mock_db_manager.add_client.assert_called_once() # It should be called

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
