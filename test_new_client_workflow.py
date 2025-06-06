import sys
import os
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import QTimer # Import QTimer

# Add project root to Python path to allow imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main_window import DocumentManager
from gui_components import ContactDialog, ProductDialog, CreateDocumentDialog
import db as db_manager

print("Starting test_new_client_workflow.py")

# --- Mocking and Monkeypatching for Automated Testing ---
original_contact_dialog_exec = ContactDialog.exec_
original_product_dialog_exec = ProductDialog.exec_
original_create_document_dialog_exec = CreateDocumentDialog.exec_

def mock_contact_dialog_exec(self_dialog):
    print("Mock ContactDialog: Opened")
    # Simulate adding a contact
    # In a real test, you might pre-fill data or interact with widgets
    # For now, just accept it to trigger the next step.
    QTimer.singleShot(100, self_dialog.accept) # Accept after a short delay
    return QDialog.Accepted # Simulate user clicking OK

def mock_product_dialog_exec(self_dialog):
    print("Mock ProductDialog: Opened")
    # Simulate adding a product
    QTimer.singleShot(100, self_dialog.accept)
    return QDialog.Accepted

def mock_create_document_dialog_exec(self_dialog):
    print("Mock CreateDocumentDialog: Opened")
    # Simulate creating a document
    # For this dialog, 'accept' might not be the right action if it auto-closes.
    # Let's simulate selecting one template and clicking "Create" then "Accept"
    if self_dialog.templates_list.count() > 0:
        self_dialog.templates_list.setCurrentRow(0) # Select the first template
        # Simulate clicking create_documents_from_selection which leads to self.accept()
        # We can't directly click the button, so we'll call the method if possible,
        # or just accept the dialog for simplicity in this mock.
        print("Mock CreateDocumentDialog: Simulating document creation and accepting.")
    else:
        print("Mock CreateDocumentDialog: No templates to select, just accepting.")
    QTimer.singleShot(100, self_dialog.accept)
    return QDialog.Accepted

ContactDialog.exec_ = mock_contact_dialog_exec
ProductDialog.exec_ = mock_product_dialog_exec
CreateDocumentDialog.exec_ = mock_create_document_dialog_exec
# --- End Mocking ---

try:
    # Initialize the database (using the existing db.py)
    db_manager.initialize_database()
    print("Database initialized for test.")

    # Add a dummy country and city if they don't exist, as they are required for client creation
    country_name = "TestCountry"
    city_name = "TestCity"
    country = db_manager.get_country_by_name(country_name)
    if not country:
        country_obj = db_manager.add_country({'country_name': country_name})
        country_id = country_obj['country_id']
        print(f"Added {country_name} with ID {country_id}")
    else:
        country_id = country['country_id']
        print(f"{country_name} already exists with ID {country_id}")

    if country_id:
        city = db_manager.get_city_by_name_and_country_id(city_name, country_id)
        if not city:
            city_obj = db_manager.add_city({'country_id': country_id, 'city_name': city_name})
            city_id = city_obj['city_id']
            print(f"Added {city_name} with ID {city_id} to {country_name}")
        else:
            city_id = city['city_id']
            print(f"{city_name} in {country_name} already exists with ID {city_id}")
    else:
        print(f"Could not ensure country {country_name} exists. City not added.")
        city_id = None


    app = QApplication.instance() # Check if an instance already exists
    if not app: # Create QApplication if it doesn't exist
        app = QApplication(sys.argv)
    print("QApplication instance obtained/created.")

    main_win = DocumentManager()
    print("DocumentManager instance created.")

    # Set required fields for client creation directly on the input widgets
    main_win.client_name_input.setText("Test Auto Client")
    main_win.company_name_input.setText("Test Auto Company")
    main_win.client_need_input.setText("Automated testing need")
    main_win.project_id_input_field.setText("AUTO_PROJ_001")
    main_win.final_price_input.setValue(1000)

    # Select country and city in combo boxes
    # This requires the country/city to be loaded into the combos first
    main_win.load_countries_into_combo() # Ensure countries are loaded
    country_index = main_win.country_select_combo.findData(country_id)
    if country_index != -1:
        main_win.country_select_combo.setCurrentIndex(country_index)
        print(f"Selected country: {main_win.country_select_combo.currentText()}")
        # Trigger city loading for the selected country
        main_win.load_cities_for_country(main_win.country_select_combo.currentText())
        city_index = main_win.city_select_combo.findData(city_id)
        if city_index != -1:
            main_win.city_select_combo.setCurrentIndex(city_index)
            print(f"Selected city: {main_win.city_select_combo.currentText()}")
        else:
            print(f"City ID {city_id} not found in combo after loading for country {main_win.country_select_combo.currentText()}. Cities in combo: {[main_win.city_select_combo.itemData(i) for i in range(main_win.city_select_combo.count())]}")
    else:
        print(f"Country ID {country_id} not found in combo. Countries in combo: {[main_win.country_select_combo.itemData(i) for i in range(main_win.country_select_combo.count())]}")


    print("Simulating 'Create Client' button click by calling execute_create_client...")
    main_win.execute_create_client() # This should trigger the chain

    # The test relies on the mocked dialogs printing messages and automatically "accepting".
    # We need to allow the Qt event loop to process these QTimer.singleShot events.
    print("Starting QTimer to allow event processing for dialogs and then exit.")
    QTimer.singleShot(2000, app.quit) # Allow 2 seconds for events to process
    app.exec_() # Start the event loop

    print("Test script finished execution.")

except Exception as e:
    print(f"Error during test execution: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1) # Indicate error

finally:
    # Clean up: Remove the test client, project, tasks, country, city if created
    # This is important for test idempotency
    try:
        client = db_manager.get_client_by_project_identifier("AUTO_PROJ_001")
        if client:
            print(f"Cleaning up client ID: {client['client_id']}")
            # Delete associated project first if it exists
            project = db_manager.get_project_by_client_id(client['client_id'])
            if project:
                print(f"Cleaning up project ID: {project['project_id']}")
                db_manager.delete_project_and_tasks(project['project_id']) # Assumes this function exists or implement task deletion separately
            db_manager.delete_client(client['client_id'])
        else:
            print("Test client AUTO_PROJ_001 not found for cleanup.")

        # Clean up country and city
        # Note: This is a simplified cleanup. In a real scenario, you'd ensure these are the *exact*
        # records created by this test run, perhaps by checking IDs more carefully or using specific test markers.
        # Deleting shared test data like "TestCountry" might affect other tests if run concurrently or if not cleaned properly.
        if country_id:
            city_to_delete = db_manager.get_city_by_name_and_country_id(city_name, country_id)
            if city_to_delete:
                 # Before deleting city, ensure it's not linked to other clients if that's a concern.
                 # For this test, we assume if the client AUTO_PROJ_001 was deleted, this city is likely specific to it.
                print(f"Attempting to clean up city ID: {city_to_delete['city_id']}")
                # db_manager.delete_city(city_to_delete['city_id']) # Requires delete_city function in db_manager

            country_to_delete = db_manager.get_country_by_name(country_name)
            if country_to_delete:
                 # Similar caution for country.
                print(f"Attempting to clean up country ID: {country_to_delete['country_id']}")
                # db_manager.delete_country(country_to_delete['country_id']) # Requires delete_country function in db_manager
        print("Cleanup phase finished.")

    except Exception as e_clean:
        print(f"Error during cleanup: {e_clean}")
        import traceback
        traceback.print_exc()

sys.exit(0) # Indicate success
