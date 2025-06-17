# -*- coding: utf-8 -*-
import re
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QDialogButtonBox, QMessageBox, QLabel
)
from auth.roles import ALL_ROLES # To populate roles combobox

class UserDialog(QDialog):
    def __init__(self, user_data=None, parent=None, is_editing=False):
        super().__init__(parent)
        self.user_data = user_data # Store existing user data if provided (for editing)
        self.is_editing = is_editing # Flag to differentiate add vs edit mode

        self.setWindowTitle(self.tr("Edit User") if self.is_editing else self.tr("Add New User"))
        self.setMinimumWidth(400)
        self.email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$" # Basic email validation

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Username
        if self.is_editing and self.user_data:
            self.username_label = QLabel(self.user_data.get('username', 'N/A'))
            form_layout.addRow(self.tr("Username:"), self.username_label)
            self.username_input = None # No input field for username in edit mode
        else:
            self.username_input = QLineEdit()
            form_layout.addRow(self.tr("Username*:"), self.username_input)
            self.username_label = None

        # Full Name
        self.full_name_input = QLineEdit()
        form_layout.addRow(self.tr("Full Name:"), self.full_name_input)

        # Email
        self.email_input = QLineEdit()
        form_layout.addRow(self.tr("Email*:"), self.email_input)

        # Password
        password_label_text = self.tr("Password*:") if not self.is_editing else self.tr("New Password (leave blank to keep current):")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow(password_label_text, self.password_input)

        # Confirm Password
        confirm_password_label_text = self.tr("Confirm Password*:") if not self.is_editing else self.tr("Confirm New Password:")
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow(confirm_password_label_text, self.confirm_password_input)

        # Role
        self.role_combo = QComboBox()
        self.role_combo.addItems(sorted(list(ALL_ROLES)))
        form_layout.addRow(self.tr("Role*:"), self.role_combo)

        # Is Active
        self.is_active_checkbox = QCheckBox(self.tr("User is active"))
        self.is_active_checkbox.setChecked(True) # Default to active for new users
        form_layout.addRow(self.is_active_checkbox)

        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText(self.tr("Save User") if not self.is_editing else self.tr("Update User"))
        self.button_box.button(QDialogButtonBox.Ok).setObjectName("primaryButton")
        self.button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Cancel"))

        self.button_box.accepted.connect(self.accept_dialog) # Changed from self.accept
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

        if self.is_editing and self.user_data:
            self._load_user_data()

    def _load_user_data(self):
        # Username is already set as a label if editing
        self.full_name_input.setText(self.user_data.get('full_name', ''))
        self.email_input.setText(self.user_data.get('email', ''))

        current_role = self.user_data.get('role', '')
        if current_role in ALL_ROLES:
            self.role_combo.setCurrentText(current_role)

        self.is_active_checkbox.setChecked(self.user_data.get('is_active', True))
        # Password fields are intentionally left blank for editing

    def accept_dialog(self): # Renamed from accept to avoid QDialog.accept() override issues if not intended
        # Validation
        username = ""
        if self.username_input: # Adding new user
            username = self.username_input.text().strip()
            if not username:
                QMessageBox.warning(self, self.tr("Input Error"), self.tr("Username is required."))
                self.username_input.setFocus()
                return
        elif self.is_editing and self.user_data: # Editing existing user
             username = self.user_data.get('username') # Get from stored data


        email = self.email_input.text().strip()
        if not email:
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Email is required."))
            self.email_input.setFocus()
            return
        if not re.match(self.email_regex, email):
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Invalid email format."))
            self.email_input.setFocus()
            return

        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()

        if not self.is_editing: # Password is required for new users
            if not password:
                QMessageBox.warning(self, self.tr("Input Error"), self.tr("Password is required for new users."))
                self.password_input.setFocus()
                return
            if len(password) < 8: # Basic complexity check
                QMessageBox.warning(self, self.tr("Input Error"), self.tr("Password must be at least 8 characters long."))
                self.password_input.setFocus()
                return
        elif password: # If editing and password field is not blank, then validate length
             if len(password) < 8:
                QMessageBox.warning(self, self.tr("Input Error"), self.tr("New password must be at least 8 characters long."))
                self.password_input.setFocus()
                return


        if password != confirm_password:
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Passwords do not match."))
            self.confirm_password_input.setFocus()
            return

        if not self.role_combo.currentText():
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Role is required."))
            self.role_combo.setFocus()
            return

        # If all validations pass
        super().accept() # Actually accept the dialog

    def get_data(self):
        data = {
            'full_name': self.full_name_input.text().strip(),
            'email': self.email_input.text().strip(),
            'role': self.role_combo.currentText(),
            'is_active': self.is_active_checkbox.isChecked()
        }
        if self.username_input: # Only for new users
            data['username'] = self.username_input.text().strip()

        password = self.password_input.text()
        if password: # Only include password if it's entered (for new user or password change)
            data['password'] = password

        return data

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    # Mock roles for testing if auth.roles is not available in this scope directly
    # This is only for the __main__ block. The class itself relies on the import.
    try:
        from auth.roles import ALL_ROLES
    except ImportError:
        print("Warning: auth.roles.ALL_ROLES not found. Using mock roles for __main__ testing.")
        ALL_ROLES = {"admin", "user", "editor", "viewer"}


    app = QApplication(sys.argv)

    # Test Add User Dialog
    print("Testing Add User Dialog:")
    add_dialog = UserDialog(is_editing=False)
    if add_dialog.exec_() == QDialog.Accepted:
        print("Add User Dialog Accepted. Data:", add_dialog.get_data())
    else:
        print("Add User Dialog Cancelled.")

    print("\nTesting Edit User Dialog:")
    # Test Edit User Dialog
    # Ensure a role from the actual or mocked ALL_ROLES is used here
    mock_user_role = "admin" if "admin" in ALL_ROLES else list(ALL_ROLES)[0] if ALL_ROLES else "user"

    mock_user_to_edit = {
        'username': 'testuser',
        'full_name': 'Test User Name',
        'email': 'test@example.com',
        'role': mock_user_role,
        'is_active': False
    }

    edit_dialog = UserDialog(user_data=mock_user_to_edit, is_editing=True)
    if edit_dialog.exec_() == QDialog.Accepted:
        print("Edit User Dialog Accepted. Data:", edit_dialog.get_data())
    else:
        print("Edit User Dialog Cancelled.")

    sys.exit()
