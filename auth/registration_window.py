import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QSpacerItem, QSizePolicy, QFrame, QWidget
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import db # For database operations
import random # For promo text, though might share LoginWindow's list
from .login_window import LoginWindow # To access PROMOTIONAL_TEXTS

class RegistrationWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RegistrationWindow") # Set object name for the dialog
        self.setWindowTitle(self.tr("Create New Account"))
        self.setMinimumWidth(800) # Keep overall dialog width for two columns
        self.init_ui()

    def init_ui(self):
        # Main horizontal layout
        main_h_layout = QHBoxLayout(self)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # --- Left Side (Form Area) ---
        left_widget = QWidget()
        left_widget.setObjectName("registrationFormArea")
        left_widget.setFixedWidth(380) # Set fixed width for the form area

        form_layout = QVBoxLayout(left_widget)
        form_layout.setContentsMargins(30, 40, 30, 40)
        form_layout.setSpacing(15)

        # Title Label
        title_label = QLabel("Create Your Account")
        title_label.setObjectName("dialogHeaderLabel")
        title_label.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(title_label)

        # Subtitle or instruction
        instruction_label = QLabel("Fill in the details below to register.")
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setStyleSheet("font-size: 10pt; color: #6c757d;")
        form_layout.addWidget(instruction_label)

        form_layout.addSpacerItem(QSpacerItem(20, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

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

        form_layout.addWidget(QLabel("Username:"))
        form_layout.addWidget(self.username_input)
        form_layout.addWidget(QLabel("Email:"))
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(QLabel("Password:"))
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(QLabel("Confirm Password:"))
        form_layout.addWidget(self.confirm_password_input)

        form_layout.addSpacerItem(QSpacerItem(20, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Register Button
        register_button = QPushButton("Register")
        register_button.setObjectName("primaryButton")
        register_button.setMinimumHeight(35)
        register_button.clicked.connect(self.handle_registration)
        form_layout.addWidget(register_button)

        form_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Back to Login Button
        back_to_login_button = QPushButton("Already have an account? Login")
        back_to_login_button.setObjectName("linkButton")
        back_to_login_button.setCursor(Qt.PointingHandCursor)
        back_to_login_button.clicked.connect(self.go_to_login)
        form_layout.addWidget(back_to_login_button, 0, Qt.AlignCenter)

        form_layout.addStretch(1)

        # --- Right Side (Promo Area) ---
        promo_frame = QFrame()
        promo_frame.setObjectName("promoAreaFrame") # Consistent object name
        # promo_frame.setStyleSheet("#promoAreaFrame { background-color: #28a745; border-left: 1px solid #ddd; }") # Style from QSS
        promo_frame.setMinimumWidth(320)

        promo_layout = QVBoxLayout(promo_frame)
        promo_layout.setContentsMargins(30, 40, 30, 40) # Consistent margins
        promo_layout.setSpacing(20)
        promo_layout.setAlignment(Qt.AlignCenter)

        self.promoHeaderLabel = QLabel(self.tr("Create Your Account"))
        self.promoHeaderLabel.setObjectName("promoHeaderLabel")
        self.promoHeaderLabel.setAlignment(Qt.AlignCenter) # Ensure alignment
        self.promoHeaderLabel.setWordWrap(True)

        # Promotional Text Label
        self.promoTextLabel = QLabel()
        self.promoTextLabel.setObjectName("promoTextLabel")
        self.promoTextLabel.setAlignment(Qt.AlignCenter) # Ensure alignment
        self.promoTextLabel.setWordWrap(True)

        # New Order: Stretch, Header, Spacing, Text, Stretch
        promo_layout.addStretch(1)
        promo_layout.addWidget(self.promoHeaderLabel)
        promo_layout.addSpacing(10)
        promo_layout.addWidget(self.promoTextLabel)
        promo_layout.addStretch(1)

        self.update_promo_text()

        # Add left and right widgets to main horizontal layout
        main_h_layout.addWidget(left_widget, 1)
        main_h_layout.addWidget(promo_frame, 1)

    def update_promo_text(self):
        # Using a specific text for registration page, or could randomize from a specific list
        registration_promo_text = "Join us to manage your documents and projects with ease. Sign up in seconds!"
        if hasattr(self, 'promoTextLabel'):
             self.promoTextLabel.setText(self.tr(registration_promo_text))


    def showEvent(self, event):
        super().showEvent(event)
        self.update_promo_text()

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
