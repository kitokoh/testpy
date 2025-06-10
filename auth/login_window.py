import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import db # Import the db.py from the root directory
from .registration_window import RegistrationWindow

class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Login")
        self.setMinimumWidth(380)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)

        # Logo
        logo_label = QLabel()
        pixmap = QPixmap(":/icons/logo.svg") # Assuming icons.qrc is compiled and available
        if pixmap.isNull():
            print("Warning: Could not load logo.svg. Check path and icons_rc.py.")
            # Fallback text or leave empty
            logo_label.setText("Company Logo")
            logo_label.setAlignment(Qt.AlignCenter)
        else:
            logo_label.setPixmap(pixmap.scaledToWidth(150, Qt.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(logo_label)

        # Title Label
        title_label = QLabel("Login")
        title_label.setObjectName("dialogHeaderLabel") # For QSS styling
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Spacer
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        # Password
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)

        # Login Button
        login_button = QPushButton("Login")
        login_button.setObjectName("primaryButton") # For QSS styling
        login_button.clicked.connect(self.handle_login)

        # Register Button
        register_button = QPushButton("Create an account")
        register_button.setObjectName("linkButton") # For QSS styling (or secondaryButton)
        register_button.setCursor(Qt.PointingHandCursor)
        register_button.clicked.connect(self.open_registration_window)

        # Button Layout
        button_h_layout = QHBoxLayout()
        button_h_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        button_h_layout.addWidget(login_button)
        button_h_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Main Layout
        main_layout.addWidget(self.username_input)
        main_layout.addWidget(self.password_input)
        main_layout.addLayout(button_h_layout) # Add button layout
        main_layout.addWidget(register_button, 0, Qt.AlignCenter) # Center the register link

        # Spacer at the bottom
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.setLayout(main_layout)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        user = db.verify_user_password(username, password)

        if user:
            print(f"Login successful for user: {username}")
            self.accept()  # Close the dialog on successful login
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")

    def open_registration_window(self):
        self.hide()
        # Pass self.parent() if LoginWindow itself has a parent (e.g. the main app window, though not typical for initial login)
        # Or pass None if RegistrationWindow should not have a specific Qt parent from LoginWindow's context.
        # If LoginWindow is the top-level window before main app shows, self.parent() might be None.
        # For simplicity, creating RegistrationWindow potentially without a direct Qt parent from here,
        # or with self if it makes sense in the application structure.
        # Let's assume self (LoginWindow instance) can be a logical parent.
        reg_window = RegistrationWindow(parent=self) # Or self.parent() if that's more appropriate
        reg_window.exec_()  # Show as a modal dialog
        self.show() # Re-show login window when registration window is closed

    # The __main__ block might have issues running directly from here
    # if db.py relies on other parts of the application being initialized,
    # or if sys.path isn't set up to find 'db' when run as a script from the 'auth' directory.
    # However, when LoginWindow is imported and used by main.py (or equivalent),
    # the 'import db' should work as expected.
if __name__ == '__main__':
    # This is for testing the LoginWindow independently
    # For this test to work directly, you might need to adjust PYTHONPATH
    # to include the root directory, e.g., PYTHONPATH=. python auth/login_window.py
    # or run as a module: python -m auth.login_window

    # A simple way to test if db can be imported if this script is run directly:
    try:
        import db
        print("db.py found and imported for test.")
    except ImportError:
        print("Failed to import db.py directly. Ensure PYTHONPATH is set or run as a module from root.")
        # Fallback to a mock for direct execution if db is not found
        class PlaceholderDB:
            def verify_user_password(self, username, password):
                print(f"Placeholder verify_user_password called with {username}, {password}")
                if username == "test" and password == "password": return {"username": "test"}
                return None
        db = PlaceholderDB()


    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec_())
