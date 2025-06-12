# PyQt5 dialog for managing Google Account linking settings for contact synchronization.

import sys
import webbrowser
from PyQt5.QtWidgets import (QDialog, QPushButton, QLabel, QVBoxLayout, QMessageBox, QApplication, QHBoxLayout)
from PyQt5.QtCore import Qt

# --- Application specific imports ---
try:
    # Assuming contact_manager is a package and google_auth is a module within it
    from . import google_auth
    from ..db import crud as db_manager
except (ImportError, ValueError) as e:
    # Fallback for running script standalone or if path issues occur
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_root_dir = os.path.dirname(current_dir) # up to /app
    if app_root_dir not in sys.path:
        sys.path.append(app_root_dir)
    try:
        import google_auth # from contact_manager.google_auth
        from db import crud as db_manager
    except ImportError as final_e:
        google_auth = None
        db_manager = None
        print(f"Critical Import Error in GoogleSettingsDialog: {final_e}. Dialog may not function correctly.")


class GoogleSettingsDialog(QDialog):
    def __init__(self, user_id: str, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        if not self.user_id:
            raise ValueError("user_id is required for GoogleSettingsDialog")

        self.setWindowTitle("Google Sync Settings")
        self.setMinimumWidth(400)

        # --- UI Setup ---
        layout = QVBoxLayout(self)

        self.status_label = QLabel("Status: Loading...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        buttons_layout = QHBoxLayout()
        self.link_button = QPushButton("Link Google Account")
        self.link_button.clicked.connect(self.initiate_linking)
        buttons_layout.addWidget(self.link_button)

        self.unlink_button = QPushButton("Unlink Google Account")
        self.unlink_button.clicked.connect(self.unlink_account)
        buttons_layout.addWidget(self.unlink_button)

        layout.addLayout(buttons_layout)

        # --- Close Button ---
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept) # QDialog.accept() closes the dialog
        layout.addWidget(self.close_button, alignment=Qt.AlignCenter)


        # --- Load initial status ---
        if db_manager and google_auth:
            self.load_status()
        else:
            self.status_label.setText("Status: Error - Core modules missing.")
            self.link_button.setEnabled(False)
            self.unlink_button.setEnabled(False)


    def load_status(self):
        """Loads the current linking status and updates the UI."""
        if not db_manager:
            self.status_label.setText("Status: Error - DB Manager not available.")
            self.link_button.setEnabled(False)
            self.unlink_button.setEnabled(False)
            return

        account = db_manager.get_user_google_account_by_user_id(self.user_id)
        if account and account.get('email'):
            self.status_label.setText(f"Status: Linked as {account['email']}")
            self.link_button.setVisible(False)
            self.unlink_button.setVisible(True)
            self.unlink_button.setEnabled(True)
        else:
            self.status_label.setText("Status: Not Linked")
            self.link_button.setVisible(True)
            self.link_button.setEnabled(True)
            self.unlink_button.setVisible(False)

    def initiate_linking(self):
        """Initiates the Google OAuth 2.0 flow by opening the authorization URL."""
        if not google_auth:
            QMessageBox.critical(self, "Error", "Google Auth module is not available.")
            return

        try:
            auth_url = google_auth.get_authorization_url()
            if not auth_url or "YOUR_CLIENT_ID_HERE" in auth_url:
                 QMessageBox.warning(self, "Configuration Error",
                                    "Google API client is not configured correctly. Please check CLIENT_ID.")
                 self.status_label.setText("Status: Configuration Error.")
                 return

            webbrowser.open(auth_url)
            self.status_label.setText("Status: Linking in progress... Authorize in browser.")

            # IMPORTANT COMMENT FOR DEVELOPER:
            # The OAuth flow requires handling a redirect from Google.
            # Typically, this involves:
            # 1. `google_auth.py` (or a web framework part of this app) starting a temporary local HTTP server
            #    to listen on the REDIRECT_URI (e.g., http://localhost:8080/oauth2callback).
            # 2. After the user authorizes in the browser, Google redirects to this REDIRECT_URI with an
            #    `authorization_code` (or an error).
            # 3. The local server captures this code.
            # 4. The server then calls a function like `handle_oauth_callback(auth_code)` in this dialog
            #    (or directly calls `google_auth.exchange_code_for_tokens` and `store_google_account_creds`).
            # 5. This dialog needs to be updated once the process completes (success or failure). This can be
            #    done via signals/slots if the server runs in a separate thread, or by making the dialog wait
            #    (though not ideal for GUI responsiveness).
            #
            # For this subtask, we stop at opening the browser. The user is informed to manually
            # trigger the next step if such a mechanism existed (e.g., "Paste code here" - not implemented).

            QMessageBox.information(self, "Action Required",
                                    "Please complete the authorization in your web browser.\n\n"
                                    "Note: This application currently does not automatically detect authorization completion. "
                                    "Further steps (like providing an auth code back to this app) would be needed in a full implementation.")
            # self.link_button.setEnabled(False) # Optionally disable until flow is "resolved"
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not initiate Google linking: {e}")
            self.load_status() # Reset status

    def handle_oauth_callback(self, auth_code: str):
        """
        Placeholder for handling the OAuth callback with the authorization code.
        This would be called by the mechanism that captures the redirect from Google.
        """
        if not google_auth or not db_manager:
            QMessageBox.critical(self, "Error", "Core modules missing, cannot handle OAuth callback.")
            self.load_status()
            return

        print(f"Received auth_code: {auth_code[:20]}...") # Log a snippet for privacy
        tokens = google_auth.exchange_code_for_tokens(auth_code)

        if tokens and tokens.get("access_token"):
            # In a real scenario, you would use the access_token to fetch user's profile
            # from Google to get their Google Account ID and email.
            # Example: google_user_info = google_people_api.get_user_profile(access_token)
            # For now, using dummy values.
            dummy_google_id = "google_id_" + auth_code[:5] # Simulate unique ID from code
            dummy_email = "user_" + auth_code[:5] + "@example.com" # Simulate email

            # The 'tokens' dict from exchange_code_for_tokens should contain:
            # access_token, refresh_token (if access_type=offline), expires_in, scope, id_token (if openid scope)
            user_google_account_id = google_auth.store_google_account_creds(
                user_id=self.user_id,
                google_account_id=dummy_google_id,
                email=dummy_email, # This should come from Google user info API call
                tokens=tokens
            )
            if user_google_account_id:
                QMessageBox.information(self, "Success", f"Google Account linked successfully as {dummy_email}!")
            else:
                 QMessageBox.warning(self, "Storage Error", "Failed to store Google account credentials after token exchange.")
        else:
            QMessageBox.warning(self, "Token Exchange Error", "Failed to exchange authorization code for tokens with Google.")

        self.load_status() # Refresh UI

    def unlink_account(self):
        """Unlinks the Google account by revoking tokens and deleting local record."""
        if not db_manager or not google_auth:
            QMessageBox.critical(self, "Error", "Core modules missing, cannot unlink account.")
            return

        confirm = QMessageBox.question(self, "Confirm Unlink",
                                       "Are you sure you want to unlink this Google Account?\n"
                                       "This will revoke access and stop contact synchronization.",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.No:
            return

        account = db_manager.get_user_google_account_by_user_id(self.user_id)
        if not account or not account.get('user_google_account_id'):
            QMessageBox.information(self, "Not Linked", "No Google account is currently linked for this user.")
            self.load_status()
            return

        user_google_account_id_to_delete = account['user_google_account_id']

        # Attempt to revoke tokens with Google first
        # The `revoke_google_tokens` function in google_auth.py is a placeholder.
        # It should ideally make an HTTP request to Google's revocation endpoint.
        # For this subtask, its placeholder returns True/False.
        revoked_on_google = google_auth.revoke_google_tokens(user_google_account_id_to_delete)

        if revoked_on_google:
            print(f"Tokens successfully revoked on Google's side for {user_google_account_id_to_delete}.")
        else:
            # Even if revocation fails, ask user if they want to remove local link
            proceed_local_delete = QMessageBox.warning(self, "Revocation Issue",
                                                       "Could not confirm token revocation with Google (this might be a placeholder or API issue).\n"
                                                       "Do you still want to remove the local link and data?",
                                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if proceed_local_delete == QMessageBox.No:
                self.load_status() # Refresh status, but don't change it if they cancel
                return

        # Delete local record
        deleted_locally = db_manager.delete_user_google_account(user_google_account_id_to_delete)
        if deleted_locally:
            QMessageBox.information(self, "Success", "Google Account has been unlinked and local data removed.")
        else:
            # This is problematic, means local DB deletion failed.
            QMessageBox.critical(self, "Database Error", "Failed to remove the Google account link from the local database.")
            # Status might be inconsistent here.

        self.load_status()


# --- Main (for testing) ---
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Mock user_id for testing
    # In a real app, this would come from the logged-in user session.
    MOCK_USER_ID = "test_user_001"

    if db_manager is None or google_auth is None:
        QMessageBox.critical(None, "Startup Error", "DB Manager or Google Auth module not loaded. Cannot run dialog.")
        sys.exit(1)

    # --- Mocking for standalone test ---
    # To test load_status and unlink, we might need a dummy entry.
    # To test initiate_linking, google_auth.get_authorization_url needs to work.
    # To test handle_oauth_callback, exchange_code_for_tokens and store_google_account_creds need to work.

    # Example of how to simulate a linked account for testing load_status and unlink:
    # if MOCK_USER_ID == "test_user_001" and not db_manager.get_user_google_account_by_user_id(MOCK_USER_ID):
    #     print("Creating dummy UserGoogleAccount for testing...")
    #     db_manager.add_user_google_account({
    #         'user_id': MOCK_USER_ID,
    #         'google_account_id': 'dummy_google_id_for_test',
    #         'email': 'test_dialog@example.com',
    #         'refresh_token': 'dummy_refresh_token_test_dialog'
    #     })
    # End example mock data setup

    dialog = GoogleSettingsDialog(user_id=MOCK_USER_ID)

    # Example of how handle_oauth_callback might be manually triggered for testing:
    # test_auth_code = "4/0Adummycodefortesting"
    # if len(sys.argv) > 1 and sys.argv[1] == "test_callback":
    #     dialog.handle_oauth_callback(test_auth_code) # Call it after dialog is shown or setup

    dialog.show()
    sys.exit(app.exec_())
