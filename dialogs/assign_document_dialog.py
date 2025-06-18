import os
import shutil
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal

# These will be passed in, so no direct import needed if they are proper instances/functions
# from db.cruds.clients_crud import clients_crud_instance # Example
# from db.cruds.client_documents_crud import add_client_document # Example

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AssignDocumentToClientDialog(QDialog):
    """
    A dialog to assign a newly detected document (file_path) to a client.
    It moves the file to the client's directory and records it in the database.
    """
    document_assigned = pyqtSignal(str, str)  # client_id, new_document_id

    def __init__(self, file_path, current_user_id, clients_crud, client_docs_crud_add_func, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.current_user_id = current_user_id
        self.clients_crud = clients_crud
        self.client_docs_crud_add_func = client_docs_crud_add_func

        self.original_file_name = os.path.basename(file_path)
        self.final_file_name_on_disk = self.original_file_name # May change due to conflict resolution

        self.setWindowTitle(self.tr("Assign Document to Client"))
        self.setMinimumSize(500, 400)

        # --- Layout ---
        main_layout = QVBoxLayout(self)

        self.info_label = QLabel(self.tr("New document detected: <b>{0}</b>").format(self.original_file_name))
        main_layout.addWidget(self.info_label)

        assign_to_label = QLabel(self.tr("Assign to which client?"))
        main_layout.addWidget(assign_to_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Search client by name..."))
        self.search_input.textChanged.connect(self.filter_clients)
        main_layout.addWidget(self.search_input)

        self.client_list_widget = QListWidget()
        self.client_list_widget.setSelectionMode(QListWidget.SingleSelection)
        main_layout.addWidget(self.client_list_widget)

        # --- Button Box ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText(self.tr("Assign"))
        self.button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        self.button_box.accepted.connect(self.accept_assignment)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

        # --- Initial Population ---
        self.populate_client_list()

    def populate_client_list(self, filter_text=""):
        self.client_list_widget.clear()
        try:
            # Assuming get_all_clients_with_details can take a filter dictionary
            # The exact filter format depends on the CRUD method's implementation
            client_filters = {}
            if filter_text:
                # This is a common way to filter, but might need adjustment
                # based on how clients_crud.get_all_clients_with_details handles filters.
                # It might expect {'name_like': filter_text} or similar.
                # For now, assuming a simple direct match or 'contains' if supported by the backend.
                client_filters['client_name_search_term'] = filter_text # Example filter key

            # Call the passed CRUD method instance
            all_clients = self.clients_crud.get_all_clients_with_details(
                filters=client_filters if filter_text else None,
                include_deleted=False
            )

            if all_clients:
                for client in all_clients:
                    item_text = client.get('client_name', self.tr('Unnamed Client'))
                    if client.get('project_identifier'):
                        item_text += f" ({client.get('project_identifier')})"

                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, client) # Store full client dict
                    self.client_list_widget.addItem(item)
            else:
                logger.info(f"No clients found for filter: '{filter_text}'")

        except Exception as e:
            logger.error(f"Error populating client list: {e}", exc_info=True)
            QMessageBox.critical(self, self.tr("Error"), self.tr("Could not load client list: {0}").format(str(e)))

    def filter_clients(self):
        self.populate_client_list(self.search_input.text().strip())

    def _find_unique_destination_path(self, base_folder, original_filename):
        """Finds a unique file path by appending numbers if necessary."""
        name, ext = os.path.splitext(original_filename)
        counter = 1
        current_filename = original_filename
        destination_path = os.path.join(base_folder, current_filename)

        while os.path.exists(destination_path):
            current_filename = f"{name}_{counter}{ext}"
            destination_path = os.path.join(base_folder, current_filename)
            counter += 1
        return destination_path, current_filename

    def accept_assignment(self):
        selected_item = self.client_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, self.tr("No Selection"), self.tr("Please select a client to assign the document to."))
            return

        selected_client_data = selected_item.data(Qt.UserRole)
        client_id = selected_client_data.get('client_id')
        # Ensure 'default_base_folder_path' is the correct key from your client data
        client_base_folder = selected_client_data.get('default_base_folder_path')

        if not client_id:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Selected client data is missing 'client_id'."))
            return

        if not client_base_folder:
            QMessageBox.critical(self, self.tr("Configuration Error"),
                                 self.tr("The selected client does not have a default base folder configured. Cannot assign document."))
            return

        try:
            os.makedirs(client_base_folder, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(self, self.tr("Directory Error"),
                                 self.tr("Could not create client directory '{0}': {1}").format(client_base_folder, str(e)))
            return

        destination_path, self.final_file_name_on_disk = self._find_unique_destination_path(client_base_folder, self.original_file_name)

        # --- Move the file ---
        try:
            logger.info(f"Attempting to move {self.file_path} to {destination_path}")
            shutil.move(self.file_path, destination_path)
            logger.info(f"File moved successfully to {destination_path}")
        except (IOError, OSError) as e:
            logger.error(f"Error moving file {self.file_path} to {destination_path}: {e}", exc_info=True)
            QMessageBox.critical(self, self.tr("File Error"),
                                 self.tr("Could not move the document to the client's folder: {0}").format(str(e)))
            return # Critical error, cannot proceed

        # --- Add document record to DB ---
        try:
            # file_path_relative should be relative to a known root, or just store the full path if that's the system's design.
            # If client_base_folder is an absolute path, then file_path_relative makes sense to be relative to it.
            file_path_relative = os.path.relpath(destination_path, start=client_base_folder)

            # Prepare document data for DB insertion
            doc_data = {
                'client_id': client_id,
                'document_name': self.final_file_name_on_disk, # User-facing name, can be edited later
                'file_name_on_disk': self.final_file_name_on_disk, # Actual name on disk
                'file_path_relative': file_path_relative, # Path relative to client's base folder
                'document_type_generated': "Document Téléchargé", # Or a more generic "Uploaded Document"
                'user_id': self.current_user_id,
                'source_template_id': None, # No template for downloaded files
                'language_code': selected_client_data.get('default_language_code', 'en'), # Or try to detect, or default
                'description': self.tr("Document automatically assigned from download monitoring."),
                # Add other fields as required by your add_client_document schema
            }
            logger.debug(f"Attempting to add document to DB with data: {doc_data}")

            # Call the passed CRUD function instance
            new_doc_id = self.client_docs_crud_add_func(doc_data)

            if new_doc_id is None:
                logger.error(f"Failed to add document record to DB for {self.final_file_name_on_disk}. CRUD function returned None.")
                QMessageBox.critical(self, self.tr("Database Error"),
                                     self.tr("The document was moved, but failed to record it in the database. Please check logs."))
                # At this point, the file is moved but not tracked. Manual intervention might be needed.
                return

            logger.info(f"Document record added to DB with ID: {new_doc_id} for client {client_id}")
            QMessageBox.information(self, self.tr("Success"),
                                    self.tr("Document '{0}' assigned to client '{1}' and moved to their folder.")
                                    .format(self.final_file_name_on_disk, selected_client_data.get('client_name')))
            self.document_assigned.emit(str(client_id), str(new_doc_id))
            self.accept() # QDialog's accept method

        except Exception as e: # Catch any other unexpected errors during DB interaction
            logger.error(f"Unexpected error adding document record to DB for {self.final_file_name_on_disk}: {e}", exc_info=True)
            QMessageBox.critical(self, self.tr("Database Error"),
                                 self.tr("An unexpected error occurred while recording the document in the database: {0}").format(str(e)))
            # File is moved. Consider implications.
            return


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    # --- Mocking for standalone testing ---
    class MockClientsCRUD:
        def get_all_clients_with_details(self, filters=None, include_deleted=False):
            logger.info(f"MockClientsCRUD.get_all_clients_with_details called with filters: {filters}")
            clients = [
                {"client_id": "client1", "client_name": "Alpha Corp", "project_identifier": "P001", "default_base_folder_path": os.path.abspath("./test_clients/Alpha_Corp"), "default_language_code": "en"},
                {"client_id": "client2", "client_name": "Beta LLC", "project_identifier": "P002", "default_base_folder_path": os.path.abspath("./test_clients/Beta_LLC"), "default_language_code": "fr"},
                {"client_id": "client3", "client_name": "Gamma Inc", "project_identifier": "P003", "default_base_folder_path": os.path.abspath("./test_clients/Gamma_Inc_No_Folder"), "default_language_code": "es"}, # Test case for no folder
                {"client_id": "client4", "client_name": "Delta Services", "project_identifier": "P004", "default_base_folder_path": None, "default_language_code": "en"}, # Test case for missing folder path
            ]
            if filters and 'client_name_search_term' in filters:
                term = filters['client_name_search_term'].lower()
                return [c for c in clients if term in c['client_name'].lower()]
            return clients

    def mock_add_client_document(doc_data):
        logger.info(f"mock_add_client_document called with: {doc_data}")
        if not doc_data.get('client_id'): # Basic validation
            return None
        return "doc_mock_id_" + str(os.urandom(4).hex()) # Return a mock document ID

    # --- Test Setup ---
    app = QApplication(sys.argv)

    # Create a dummy file to be "downloaded"
    dummy_downloads_dir = "dummy_downloads_for_dialog_test"
    os.makedirs(dummy_downloads_dir, exist_ok=True)
    test_file_name = "sample_document.pdf"
    test_file_path = os.path.join(dummy_downloads_dir, test_file_name)
    with open(test_file_path, "w") as f:
        f.write("This is a test PDF content.")

    # Create some dummy client folders for testing move operation
    os.makedirs("./test_clients/Alpha_Corp", exist_ok=True)
    os.makedirs("./test_clients/Beta_LLC", exist_ok=True)
    # Not creating Gamma_Inc_No_Folder to test that case if selected

    mock_clients_crud_instance = MockClientsCRUD()

    dialog = AssignDocumentToClientDialog(
        file_path=test_file_path,
        current_user_id="test_user_dialog",
        clients_crud=mock_clients_crud_instance,
        client_docs_crud_add_func=mock_add_client_document
    )

    def handle_assigned(client_id, new_doc_id):
        print(f"SIGNAL RECEIVED: Document assigned to client {client_id}, new doc ID: {new_doc_id}")

    dialog.document_assigned.connect(handle_assigned)

    if dialog.exec_() == QDialog.Accepted:
        print("Dialog accepted.")
        # Check if the file was moved (original should be gone)
        if not os.path.exists(test_file_path):
            print(f"Original file {test_file_path} correctly moved/deleted.")
        else:
            print(f"WARNING: Original file {test_file_path} still exists.")
        # Further checks could involve verifying its new location based on client selection.
    else:
        print("Dialog cancelled.")
        if os.path.exists(test_file_path):
            print(f"Original file {test_file_path} still exists (as expected after cancel).")
        else:
            print(f"WARNING: Original file {test_file_path} is GONE despite cancel.")


    # --- Cleanup ---
    if os.path.exists(test_file_path): # If not moved by test
        os.remove(test_file_path)
    if os.path.exists(dummy_downloads_dir):
        # Check if any files were "moved" into client folders during successful test
        # and remove them before rmdir. This is a simplified cleanup.
        for root, dirs, files in os.walk("./test_clients", topdown=False):
            for name in files:
                if name.startswith("sample_document"): # Be specific to avoid deleting other things
                    os.remove(os.path.join(root, name))
            # for name in dirs: # Not removing client dirs themselves in this test
            #     pass
        shutil.rmtree(dummy_downloads_dir)
        # shutil.rmtree("./test_clients") # Uncomment if you want to clean up client folders too

    sys.exit(app.exec_())
