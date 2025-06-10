import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QSpacerItem, QSizePolicy, QFrame, QWidget
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
import db # Import the db.py from the root directory
from .registration_window import RegistrationWindow
import uuid

class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Login")
        self.setMinimumWidth(760) # Increased width for two columns
        self.session_token = None
        self.current_user = None
        self.init_ui()

    def init_ui(self):
        # Main horizontal layout
        main_h_layout = QHBoxLayout(self) # Set this as the dialog's layout
        main_h_layout.setContentsMargins(0, 0, 0, 0) # No margins for the main layout, handled by frames
        main_h_layout.setSpacing(0)

        # --- Left Side (Form Area) ---
        left_widget = QWidget() # Use QWidget as container
        left_widget.setObjectName("loginFormArea") # For potential specific styling
        # left_widget.setStyleSheet("background-color: #f8f9fa;") # Light gray for form area, or keep transparent

        form_layout = QVBoxLayout(left_widget)
        form_layout.setContentsMargins(30, 40, 30, 40) # Generous margins
        form_layout.setSpacing(20)

        # Logo
        logo_label = QLabel()
        pixmap = QPixmap(":/icons/logo.svg")
        if pixmap.isNull():
            logo_label.setText("Company Logo")
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("font-size: 14px; color: #888;")
        else:
            logo_label.setPixmap(pixmap.scaledToWidth(120, Qt.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(logo_label)

        # Title Label
        title_label = QLabel("Welcome Back!")
        title_label.setObjectName("dialogHeaderLabel")
        title_label.setAlignment(Qt.AlignCenter)
        # Consider increasing font size directly if QSS isn't overriding enough
        # title_font = QFont()
        # title_font.setPointSize(18) # Example size
        # title_font.setBold(True)
        # title_label.setFont(title_font)
        form_layout.addWidget(title_label)

        # Subtitle or instruction
        instruction_label = QLabel("Please enter your credentials to log in.")
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setStyleSheet("font-size: 10pt; color: #6c757d;") # Softer color
        form_layout.addWidget(instruction_label)

        form_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))


        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        # Password
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)

        form_layout.addWidget(QLabel("Username:")) # Adding labels for fields
        form_layout.addWidget(self.username_input)
        form_layout.addWidget(QLabel("Password:"))
        form_layout.addWidget(self.password_input)

        # Login Button
        login_button = QPushButton("Login")
        login_button.setObjectName("primaryButton")
        login_button.setMinimumHeight(35) # Make button a bit taller
        login_button.clicked.connect(self.handle_login)
        form_layout.addWidget(login_button)

        form_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Register Button (as a link)
        register_button = QPushButton("Don't have an account? Create one")
        register_button.setObjectName("linkButton")
        register_button.setCursor(Qt.PointingHandCursor)
        register_button.clicked.connect(self.open_registration_window)
        form_layout.addWidget(register_button, 0, Qt.AlignCenter)

        form_layout.addStretch(1) # Add stretch at the bottom of the form

        # --- Right Side (Promo Area) ---
        promo_frame = QFrame()
        promo_frame.setObjectName("promoAreaFrame")
        # promo_frame.setStyleSheet("#promoAreaFrame { background-color: #007bff; border-left: 1px solid #ddd; }") # Style from QSS
        promo_frame.setMinimumWidth(300)

        promo_layout = QVBoxLayout(promo_frame)
        promo_layout.setContentsMargins(30, 40, 30, 40) # Consistent margins
        promo_layout.setSpacing(20)
        promo_layout.setAlignment(Qt.AlignCenter)

        promo_header = QLabel("ClientDocManager")
        promo_header.setObjectName("promoHeaderLabel")
        promo_header.setAlignment(Qt.AlignCenter)
        promo_header.setWordWrap(True) # Ensure header wraps if needed
        promo_layout.addWidget(promo_header)

        promo_text_content = "Streamline your client documentation and project management effortlessly. Secure, efficient, and professional."
        promo_text = QLabel(promo_text_content)
        promo_text.setObjectName("promoTextLabel")
        promo_text.setAlignment(Qt.AlignCenter) # Center align text
        promo_text.setWordWrap(True)
        promo_layout.addWidget(promo_text)

        promo_layout.addStretch(1)

        # Add left and right widgets to main horizontal layout
        main_h_layout.addWidget(left_widget, 1) # Give form area a stretch factor of 1
        main_h_layout.addWidget(promo_frame, 1) # Give promo area a stretch factor of 1

        # No need to call self.setLayout() as main_h_layout was passed `self`

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        user = db.verify_user_password(username, password)

        if user:
            self.current_user = user
            self.session_token = uuid.uuid4().hex
            print(f"Login successful for user: {username}, Token: {self.session_token}")
            self.accept()  # Close the dialog on successful login
        else:
            self.current_user = None # Ensure current_user is None on failed login
            self.session_token = None
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")

    def get_session_token(self) -> str | None:
        return self.session_token

    def get_current_user(self) -> dict | None:
        return self.current_user

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