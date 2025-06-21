import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QSpacerItem, QSizePolicy, QFrame, QWidget, QCheckBox
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QSettings
from db import verify_user_password # Import the db.py from the root directory - No longer needed for user auth
# from db.cruds.users_crud import users_crud_instance # Import the UsersCRUD instance
import uuid
import logging # Added for logging
import random # Added for promotional text

class LoginWindow(QDialog):
    PROMOTIONAL_TEXTS = [
        "Streamline your client documentation and project management effortlessly.",
        "Secure, efficient, and professional document handling.",
        "Welcome! Let's get your documents organized.",
        "Unlock productivity with ClientDocManager.",
        "Your success, documented.",
        "Focus on your clients, we'll handle the paperwork."
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoginWindow") # Set object name for the dialog

        self.setWindowTitle(self.tr("User Login"))
        self.setMinimumWidth(760)
        self.session_token = None
        self.current_user = None
        self.init_ui()

        # Load Remember Me state
        settings = QSettings()
        remember_me_active = settings.value("auth/remember_me_active", False, type=bool)
        self.remember_me_checkbox.setChecked(remember_me_active)
        # If active, could potentially auto-fill username, but token logic is for auto-login later
        if remember_me_active:
            saved_username = settings.value("auth/username", "")
            if saved_username:
                self.username_input.setText(saved_username)


    def init_ui(self):
        # Main horizontal layout
        main_h_layout = QHBoxLayout(self)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # --- Left Side (Form Area) ---
        left_widget = QWidget()
        left_widget.setObjectName("loginFormArea")
        left_widget.setFixedWidth(360) # Set fixed width for the form area

        self.form_layout = QVBoxLayout(left_widget)
        self.form_layout.setContentsMargins(30, 40, 30, 40)
        self.form_layout.setSpacing(15)



        # Logo
        logo_label = QLabel()
        pixmap = QPixmap(":/icons/logo.svg")
        if pixmap.isNull():
            logo_label.setText(self.tr("Company Logo"))
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("font-size: 14px; color: #888;")
        else:
            logo_label.setPixmap(pixmap.scaledToWidth(120, Qt.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignCenter)
        self.form_layout.addWidget(logo_label)

        # Title Label
        title_label = QLabel(self.tr("Welcome Back!"))
        title_label.setObjectName("dialogHeaderLabel")
        title_label.setAlignment(Qt.AlignCenter)
        self.form_layout.addWidget(title_label)

        # Subtitle or instruction
        instruction_label = QLabel(self.tr("Please enter your credentials to log in."))
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setStyleSheet("font-size: 10pt; color: #6c757d;")
        self.form_layout.addWidget(instruction_label)

        self.form_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(self.tr("Username"))

        # Password
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(self.tr("Password"))
        self.password_input.setEchoMode(QLineEdit.Password)

        self.form_layout.addWidget(QLabel(self.tr("Username:")))
        self.form_layout.addWidget(self.username_input)
        self.form_layout.addWidget(QLabel(self.tr("Password:")))
        self.form_layout.addWidget(self.password_input)

        # Remember Me Checkbox
        self.remember_me_checkbox = QCheckBox(self.tr("Remember Me"))
        self.form_layout.addWidget(self.remember_me_checkbox) # Added here

        # Login Button
        login_button = QPushButton(self.tr("Login"))
        login_button.setObjectName("primaryButton")
        login_button.setMinimumHeight(35)
        login_button.clicked.connect(self.handle_login)
        self.form_layout.addWidget(login_button)

        self.form_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Register Button (as a link)
        register_button = QPushButton(self.tr("Don't have an account? Create one"))
        register_button.setObjectName("linkButton")
        register_button.setCursor(Qt.PointingHandCursor)
        register_button.clicked.connect(self.open_registration_window)
        self.form_layout.addWidget(register_button, 0, Qt.AlignCenter)

        self.form_layout.addStretch(1)

        # --- Right Side (Promo Area) ---
        promo_frame = QFrame()
        promo_frame.setObjectName("promoAreaFrame")
        # promo_frame.setStyleSheet("#promoAreaFrame { background-color: #007bff; border-left: 1px solid #ddd; }") # Style from QSS
        promo_frame.setMinimumWidth(300)

        promo_layout = QVBoxLayout(promo_frame)
        promo_layout.setContentsMargins(30, 40, 30, 40) # Consistent margins
        promo_layout.setSpacing(20)
        promo_layout.setAlignment(Qt.AlignCenter)

        self.promoHeaderLabel = QLabel(self.tr("ClientDocManager"))
        self.promoHeaderLabel.setObjectName("promoHeaderLabel")
        self.promoHeaderLabel.setAlignment(Qt.AlignCenter) # Set alignment in Python
        self.promoHeaderLabel.setWordWrap(True)

        self.promoTextLabel = QLabel()
        self.promoTextLabel.setObjectName("promoTextLabel")
        self.promoTextLabel.setAlignment(Qt.AlignCenter) # Set alignment in Python
        self.promoTextLabel.setWordWrap(True)

        # New Order: Stretch, Header, Spacing, Text, Stretch
        promo_layout.addStretch(1)
        promo_layout.addWidget(self.promoHeaderLabel)
        promo_layout.addSpacing(10)
        promo_layout.addWidget(self.promoTextLabel)
        promo_layout.addStretch(1)

        self.update_promo_text() # Set initial random text

        # Add left and right widgets to main horizontal layout
        main_h_layout.addWidget(left_widget, 1)

        main_h_layout.addWidget(promo_frame, 1) # Give promo area a stretch factor of 1

        # No need to call self.setLayout() as main_h_layout was passed `self`

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        # Use the new users_crud_instance for verification
        user_verification_result = verify_user_password(username=username, password=password)

        if user_verification_result:
            self.current_user = user_verification_result # verify_user_password returns the user dict
            self.session_token = uuid.uuid4().hex
            logging.info(f"Login successful for user: {username}, Token: {self.session_token}")

            settings = QSettings()
            if self.remember_me_checkbox.isChecked():
                settings.setValue("auth/remember_me_active", True)
                settings.setValue("auth/session_token", self.session_token)
                settings.setValue("auth/user_id", self.current_user.get('user_id'))
                settings.setValue("auth/username", self.current_user.get('username'))
                settings.setValue("auth/user_role", self.current_user.get('role'))
                logging.info("Remember Me enabled. Token and user info stored.")
            else:
                settings.setValue("auth/remember_me_active", False)
                settings.remove("auth/session_token")
                settings.remove("auth/user_id")
                settings.remove("auth/username")
                settings.remove("auth/user_role")
                logging.info("Remember Me disabled. Stored token and user info cleared.")

            self.accept()
        else:
            self.current_user = None
            self.session_token = None
            QMessageBox.warning(self, self.tr("Login Failed"), self.tr("Invalid username or password."))

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
        from .registration_window import  RegistrationWindow
        reg_window = RegistrationWindow(parent=self)
        reg_window.exec_()
        self.show()

    def update_promo_text(self):
        selected_promo_text = random.choice(LoginWindow.PROMOTIONAL_TEXTS)
        if hasattr(self, 'promoTextLabel'): # Ensure label exists
            self.promoTextLabel.setText(self.tr(selected_promo_text))

    def showEvent(self, event):
        super().showEvent(event)
        self.update_promo_text() # Update promo text when dialog is shown

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
    # try:
    #     import db # db.py is no longer directly used for user auth here
    #     print("db.py found and imported for test.")
    # except ImportError:
    #     print("Failed to import db.py directly. Ensure PYTHONPATH is set or run as a module from root.")
        # Fallback to a mock for direct execution if db is not found
        # class PlaceholderDB: # No longer needed as we import users_crud_instance
        #     def verify_user_password(self, username, password):
        #         print(f"Placeholder verify_user_password called with {username}, {password}")
        #         if username == "test" and password == "password": return {"username": "test"}
        #         return None
        # db = PlaceholderDB()


    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec_())

