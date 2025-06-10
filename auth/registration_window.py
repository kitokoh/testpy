import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QPixmap # For logo, though not strictly required by instructions for this window
from PyQt5.QtCore import Qt
import db # For database operations

class RegistrationWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Account")
        self.setMinimumWidth(400) # Slightly wider for more fields
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)

        # Title Label
        title_label = QLabel("Create Account")
        title_label.setObjectName("dialogHeaderLabel") # For QSS styling
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Spacer
        main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)) # Smaller spacer

        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        # Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")

        # Password
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)

        # Confirm Password
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirm Password")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)

        # Register Button
        register_button = QPushButton("Register")
        register_button.setObjectName("primaryButton") # Or "registerButton"
        register_button.clicked.connect(self.handle_registration)

        # Back to Login Button
        back_to_login_button = QPushButton("Back to Login")
        back_to_login_button.setObjectName("linkButton") # Or "secondaryButton"
        back_to_login_button.setCursor(Qt.PointingHandCursor)
        back_to_login_button.clicked.connect(self.go_to_login)

        # Button Layout for Register
        register_button_layout = QHBoxLayout()
        register_button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        register_button_layout.addWidget(register_button)
        register_button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Add widgets to main layout
        main_layout.addWidget(self.username_input)
        main_layout.addWidget(self.email_input)
        main_layout.addWidget(self.password_input)
        main_layout.addWidget(self.confirm_password_input)
        main_layout.addLayout(register_button_layout) # Add register button layout
        main_layout.addWidget(back_to_login_button, 0, Qt.AlignCenter) # Center the back to login link

        # Spacer at the bottom
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.setLayout(main_layout)

    def handle_registration(self):
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()

        # Validation
        if not all([username, email, password, confirm_password]):
            QMessageBox.warning(self, "Input Error", "All fields are required.")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "Input Error", "Passwords do not match.")
            return

        if db.get_user_by_username(username):
            QMessageBox.warning(self, "Input Error", "Username already exists.")
            return

        if db.get_user_by_email(email):
            QMessageBox.warning(self, "Input Error", "Email already registered.")
            return

        # If all validations pass
        user_data = {
            'username': username,
            'email': email,
            'password': password, # The db.add_user function is expected to hash this
            'role': 'member',  # Default role
            'full_name': username # Or prompt for full name separately
        }

        user_id = db.add_user(user_data)

        if user_id:
            QMessageBox.information(self, "Success", "Registration successful! You can now log in.")
            self.accept()  # Close the registration dialog
        else:
            QMessageBox.critical(self, "Error", "Registration failed. Please try again or contact support if the problem persists.")

    def go_to_login(self):
        self.accept() # Close the dialog, LoginWindow will re-show itself.

if __name__ == '__main__':
    # This is for testing the RegistrationWindow independently
    # Similar to LoginWindow, direct execution might need PYTHONPATH adjustments
    # or running as a module from the project root.
    try:
        import db
        db.initialize_database() # Ensure DB and tables are created for the test
        print("db.py found and imported for test. Database initialized.")
    except ImportError:
        print("Failed to import db.py directly. Ensure PYTHONPATH is set or run as a module from root.")
        # Fallback to mocks for UI testing if db is not found or initialization fails
        class MockDB:
            def get_user_by_username(self, username): return None
            def get_user_by_email(self, email): return None
            def add_user(self, user_data): return "mock_user_id_123"
        db = MockDB()
        print("Using MockDB for RegistrationWindow test.")
    except Exception as e_init:
        print(f"Error initializing database for test: {e_init}")
        # Fallback to mocks as well
        class MockDB:
            def get_user_by_username(self, username): return None
            def get_user_by_email(self, email): return None
            def add_user(self, user_data): return "mock_user_id_123"
        db = MockDB()
        print("Using MockDB due to DB initialization error for RegistrationWindow test.")


    app = QApplication(sys.argv)
    registration_window = RegistrationWindow()
    registration_window.show()
    sys.exit(app.exec_())
