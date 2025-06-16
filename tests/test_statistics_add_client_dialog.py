import sys
import unittest
from unittest.mock import patch, MagicMock, call

from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import Qt

# Add project root to sys.path if tests are run from a different directory
# This assumes the tests directory is at the same level as 'dialogs' and 'db'
# import os
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# if project_root not in sys.path:
# sys.path.insert(0, project_root)

# Mock db_manager before importing the dialog if db_manager is imported at module level in the dialog
# This is important if db_manager itself tries to connect to a DB upon import.
# However, StatisticsAddClientDialog imports db_manager functions, so patching them during tests is fine.
mock_db_manager = MagicMock()
# We need to mock the specific functions used by the dialog during its import or __init__ if any.
# For StatisticsAddClientDialog, db calls are mostly in methods, so patching at method/class level is okay.

# Patch the actual db_manager where it's looked up by the dialog module
# This ensures that the dialog uses our mocks.
# The dialog file imports `db as db_manager` or `from database import db_manager`
# Assuming the mock structure in the dialog itself (try-except ImportError)
# For tests, we want to ensure our explicit mocks are used.
# So, we patch 'dialogs.statistics_add_client_dialog.db_manager'
# And also potentially 'db.get_all_countries' etc. if they are imported directly using 'from db import ...'

# For QApplication
q_app = None

def setUpModule():
    global q_app
    q_app = QApplication.instance()
    if q_app is None:
        # sys.argv might need to be ['test'] or something simple if not running via a test runner that handles it
        q_app = QApplication(sys.argv if hasattr(sys, 'argv') else [''])

def tearDownModule():
    global q_app
    # QApplication.quit() # May not be necessary, or could cause issues with some test runners
    q_app = None


from dialogs.statistics_add_client_dialog import StatisticsAddClientDialog

class TestStatisticsAddClientDialog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure QApplication instance exists for all tests in this class
        # This is redundant if setUpModule is used effectively by the test runner
        # but good as a fallback.
        global q_app
        if QApplication.instance() is None:
            q_app = QApplication(sys.argv if hasattr(sys, 'argv') else [''])

        # Mock countries and cities data that would be returned by db_manager
        cls.mock_countries = [
            {'country_id': 1, 'country_name': 'CountryA'},
            {'country_id': 2, 'country_name': 'CountryB'}
        ]
        cls.mock_cities_country_a = [
            {'city_id': 10, 'city_name': 'CityA1'},
            {'city_id': 11, 'city_name': 'CityA2'}
        ]
        cls.mock_cities_country_b = [
            {'city_id': 20, 'city_name': 'CityB1'}
        ]

    def setUp(self):
        # Create a new dialog instance for each test
        # We will patch db_manager for each test method to ensure clean mocks.

        # Default mock for db_manager functions
        self.db_manager_patcher = patch('dialogs.statistics_add_client_dialog.db_manager')
        self.mock_db_manager = self.db_manager_patcher.start()

        self.mock_db_manager.get_all_countries.return_value = self.mock_countries
        self.mock_db_manager.get_all_cities.side_effect = self.get_mock_cities
        self.mock_db_manager.get_country_by_name.side_effect = self.get_mock_country_by_name
        self.mock_db_manager.get_or_add_country.side_effect = self.get_or_add_mock_country
        self.mock_db_manager.get_or_add_city.side_effect = self.get_or_add_mock_city

        self.dialog = StatisticsAddClientDialog()

    def tearDown(self):
        self.db_manager_patcher.stop()
        self.dialog.deleteLater() # Ensure the dialog is cleaned up
        self.dialog = None

    # Helper mock implementations
    def get_mock_cities(self, country_id):
        if country_id == 1: return self.mock_cities_country_a
        if country_id == 2: return self.mock_cities_country_b
        return []

    def get_mock_country_by_name(self, name):
        for country in self.mock_countries:
            if country['country_name'] == name:
                return country
        return None

    def get_or_add_mock_country(self, country_name):
        existing = self.get_mock_country_by_name(country_name)
        if existing: return existing
        new_country = {'country_id': hash(country_name) % 1000, 'country_name': country_name}
        # self.mock_countries.append(new_country) # Simulate adding to DB for subsequent calls if needed by a test
        return new_country

    def get_or_add_mock_city(self, city_name, country_id):
        # Check existing (simplified for test)
        mock_city_list = self.get_mock_cities(country_id)
        for city in mock_city_list:
            if city['city_name'] == city_name:
                return city
        new_city = {'city_id': hash(city_name) % 1000, 'city_name': city_name, 'country_id': country_id}
        # mock_city_list.append(new_city) # Simulate adding
        return new_city


    def test_01_initialization_and_default_state(self):
        self.assertIsInstance(self.dialog, QDialog)
        self.assertEqual(self.dialog.windowTitle(), "Add New Client Wizard")
        self.assertEqual(self.dialog._current_step, 0)
        self.assertEqual(self.dialog.stacked_widget.currentIndex(), 0)
        self.assertTrue(self.dialog.next_button.isEnabled())
        self.assertFalse(self.dialog.prev_button.isEnabled())
        self.assertFalse(self.dialog.finish_button.isVisible())
        self.mock_db_manager.get_all_countries.assert_called_once() # Called in __init__ via _load_countries_into_combo

    def test_02_initial_country_provided(self):
        # Stop the default patcher for this test to set up a specific scenario first
        self.db_manager_patcher.stop()

        db_m_patcher = patch('dialogs.statistics_add_client_dialog.db_manager')
        mock_db_m = db_m_patcher.start()
        mock_db_m.get_all_countries.return_value = self.mock_countries
        mock_db_m.get_all_cities.side_effect = self.get_mock_cities
        mock_db_m.get_country_by_name.side_effect = self.get_mock_country_by_name

        initial_country = 'CountryA'
        dialog_with_initial = StatisticsAddClientDialog(initial_country_name=initial_country)

        # Check if CountryA is selected in country_select_combo (Step 2)
        # _load_countries_into_combo and _handle_initial_country are called in __init__
        self.assertEqual(dialog_with_initial.country_select_combo.currentText(), initial_country)
        # Check if cities for CountryA were loaded
        # _on_country_selected -> _load_cities_for_country is called when currentText changes
        # For this to be asserted, get_all_cities must have been called with CountryA's ID (1)
        mock_db_m.get_all_cities.assert_called_with(country_id=1)
        self.assertTrue(dialog_with_initial.city_select_combo.count() > 0)
        self.assertEqual(dialog_with_initial.city_select_combo.itemText(0), 'CityA1')

        db_m_patcher.stop()
        dialog_with_initial.deleteLater()
        # Restart the main patcher if other tests need it (setUp will do this)

    def test_03_step_navigation_forward_and_backward(self):
        # Step 0 -> 1 (Client Info -> Location)
        self.dialog.client_name_input.setText("Test Client") # Required for validation
        self.dialog._go_to_next_step()
        self.assertEqual(self.dialog._current_step, 1)
        self.assertEqual(self.dialog.stacked_widget.currentIndex(), 1)
        self.assertTrue(self.dialog.prev_button.isEnabled())

        # Step 1 -> 2 (Location -> Language)
        self.dialog.country_select_combo.setCurrentText("CountryA") # Required for validation
        self.dialog._go_to_next_step()
        self.assertEqual(self.dialog._current_step, 2)
        self.assertEqual(self.dialog.stacked_widget.currentIndex(), 2)

        # Step 2 -> 3 (Language -> Summary)
        self.dialog._go_to_next_step()
        self.assertEqual(self.dialog._current_step, 3)
        self.assertEqual(self.dialog.stacked_widget.currentIndex(), 3)
        self.assertFalse(self.dialog.next_button.isVisible())
        self.assertTrue(self.dialog.finish_button.isVisible())
        self.assertTrue(self.dialog.finish_button.isEnabled()) # Assuming validation passes up to here

        # Step 3 -> 2 (Summary -> Language)
        self.dialog._go_to_previous_step()
        self.assertEqual(self.dialog._current_step, 2)
        self.assertEqual(self.dialog.stacked_widget.currentIndex(), 2)
        self.assertTrue(self.dialog.next_button.isVisible())
        self.assertFalse(self.dialog.finish_button.isVisible())

    @patch('PyQt5.QtWidgets.QMessageBox.warning')
    def test_04_validation_step1_client_name_required(self, mock_message_box):
        self.dialog.client_name_input.setText("") # Empty client name
        self.dialog._go_to_next_step()

        self.assertEqual(self.dialog._current_step, 0) # Should not advance
        mock_message_box.assert_called_once()
        # Check args of warning if needed: mock_message_box.assert_called_with(ANY, "Validation Error", ANY)

    @patch('PyQt5.QtWidgets.QMessageBox.warning')
    def test_05_validation_step2_country_required(self, mock_message_box):
        self.dialog.client_name_input.setText("Test Client")
        self.dialog._go_to_next_step() # Go to step 1 (Location)

        self.dialog.country_select_combo.setCurrentText("") # Empty country
        self.dialog._go_to_next_step()

        self.assertEqual(self.dialog._current_step, 1) # Should not advance from step 1
        mock_message_box.assert_called_once()

    @patch('PyQt5.QtWidgets.QInputDialog.getText')
    def test_06_add_new_country_dialog(self, mock_input_dialog):
        # Navigate to step 2 (Location Info page)
        self.dialog.client_name_input.setText("Test Client")
        self.dialog._go_to_next_step() # Now on step 1 (Location)

        new_country_name = "NewTestCountry"
        mock_input_dialog.return_value = (new_country_name, True)

        # Simulate adding this new country to the list of countries for the reload
        self.mock_db_manager.get_or_add_country.return_value = {'country_id': 3, 'country_name': new_country_name}
        # Ensure get_all_countries returns the new country after adding
        updated_countries = self.mock_countries + [{'country_id': 3, 'country_name': new_country_name}]
        self.mock_db_manager.get_all_countries.return_value = updated_countries

        self.dialog.add_country_button.click() # Click "+" for country

        self.mock_db_manager.get_or_add_country.assert_called_with(new_country_name)
        self.mock_db_manager.get_all_countries.assert_called() # To reload combo
        self.assertEqual(self.dialog.country_select_combo.currentText(), new_country_name)

    @patch('PyQt5.QtWidgets.QInputDialog.getText')
    def test_07_add_new_city_dialog(self, mock_input_dialog):
        self.dialog.client_name_input.setText("Test Client")
        self.dialog._go_to_next_step() # To Location page

        self.dialog.country_select_combo.setCurrentText("CountryA") # Select a country first
        # This should trigger _on_country_selected -> _load_cities_for_country for CountryA (ID 1)
        self.mock_db_manager.get_all_cities.assert_called_with(country_id=1)

        new_city_name = "NewTestCityA"
        mock_input_dialog.return_value = (new_city_name, True)

        self.mock_db_manager.get_or_add_city.return_value = {'city_id': 12, 'city_name': new_city_name, 'country_id': 1}
        # Simulate adding new city for the reload
        updated_cities_a = self.mock_cities_country_a + [{'city_id': 12, 'city_name': new_city_name}]

        # Redefine side effect for get_all_cities for this test after adding a city
        def side_effect_get_cities_after_add(country_id):
            if country_id == 1: return updated_cities_a
            return self.get_mock_cities(country_id) # Original behavior for other countries
        self.mock_db_manager.get_all_cities.side_effect = side_effect_get_cities_after_add

        self.dialog.add_city_button.click()

        self.mock_db_manager.get_or_add_city.assert_called_with(city_name=new_city_name, country_id=1)
        self.mock_db_manager.get_all_cities.assert_called_with(country_id=1) # To reload cities
        self.assertEqual(self.dialog.city_select_combo.currentText(), new_city_name)


    @patch('PyQt5.QtWidgets.QMessageBox.warning')
    def test_08_accept_success(self, mock_qmessagebox_warning):
        # Fill Step 1
        self.dialog.client_name_input.setText("Final Client")
        self.dialog.company_name_input.setText("Final Corp")
        self.dialog.client_need_input.setText("Urgent Need")
        self.dialog.project_identifier_input.setText("PID123")

        # Fill Step 2
        self.dialog.country_select_combo.setCurrentText("CountryB") # Existing country
        self.dialog.city_select_combo.setCurrentText("CityB1")   # Existing city for CountryB

        # Fill Step 3
        self.dialog.language_select_combo.setCurrentText("French only (fr)")

        # Call accept (which is connected to Finish button)
        # The dialog's accept() method performs the final db calls for typed entries
        # Here, we used existing, so get_or_add should not be called for them in accept unless text doesn't match data
        self.dialog.accept()

        self.assertEqual(self.dialog.result(), QDialog.Accepted)
        mock_qmessagebox_warning.assert_not_called() # No validation warnings should occur

        # Verify that get_or_add_country/city were NOT called again in accept if items were selected from combo
        # Note: _on_country_selected calls get_country_by_name, which might be called.
        # But in accept() itself, if country_id and city_id are already set from combo.currentData(),
        # get_or_add should not be called.
        # Check calls after the initial setup calls.
        # This needs more specific call count checks if we want to be precise.
        # For now, we trust that if data is valid, accept works.

    @patch('PyQt5.QtWidgets.QMessageBox.warning')
    def test_09_accept_failure_client_name_missing(self, mock_qmessagebox_warning):
        # Try to accept without filling client name
        self.dialog.accept()
        self.assertEqual(self.dialog.result(), QDialog.Rejected) # Default result unless explicitly accepted
        mock_qmessagebox_warning.assert_called_once()
        # We can check the current stack index to see if it navigated to the problematic step
        self.assertEqual(self.dialog.stacked_widget.currentIndex(), 0)


    def test_10_get_data_after_successful_accept(self):
        # Simulate a fully filled dialog
        self.dialog.client_name_input.setText("Data Client")
        self.dialog.company_name_input.setText("Data Corp")
        self.dialog.client_need_input.setText("Data Need")
        self.dialog.project_identifier_input.setText("PIDXYZ")

        # For location, simulate typing a new country and new city
        typed_new_country = "New Country For Data"
        typed_new_city = "New City For Data"

        # Mock return values for these new typed entries when accept() processes them
        mock_new_country_id = 99
        mock_new_city_id = 999
        self.mock_db_manager.get_or_add_country.return_value = {'country_id': mock_new_country_id, 'country_name': typed_new_country}
        self.mock_db_manager.get_or_add_city.return_value = {'city_id': mock_new_city_id, 'city_name': typed_new_city, 'country_id': mock_new_country_id}

        self.dialog.country_select_combo.lineEdit().setText(typed_new_country) # Simulate typing
        self.dialog.city_select_combo.lineEdit().setText(typed_new_city)    # Simulate typing

        self.dialog.language_select_combo.setCurrentIndex(0) # "English only (en)"

        # Call accept to process and store IDs
        self.dialog.accept()
        self.assertEqual(self.dialog.result(), QDialog.Accepted)

        # Now call get_data
        data = self.dialog.get_data()

        self.assertEqual(data['client_name'], "Data Client")
        self.assertEqual(data['company_name'], "Data Corp")
        self.assertEqual(data['primary_need_description'], "Data Need")
        self.assertEqual(data['project_identifier'], "PIDXYZ")
        self.assertEqual(data['country_name'], typed_new_country)
        self.assertEqual(data['country_id'], mock_new_country_id)
        self.assertEqual(data['city_name'], typed_new_city)
        self.assertEqual(data['city_id'], mock_new_city_id)
        self.assertEqual(data['selected_languages'], "en") # From "English only (en)"


if __name__ == '__main__':
    unittest.main()
