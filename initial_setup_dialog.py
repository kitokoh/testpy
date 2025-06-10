# -*- coding: utf-8 -*-
import os
import shutil
import uuid

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QFileDialog, QStackedWidget, QDialogButtonBox, QMessageBox,
    QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QCoreApplication
from PyQt5.QtGui import QPixmap

# Assuming db_manager.py is in the same directory or Python path
import db as db_manager
# Assuming app_setup.py defines these, adjust if they are in utils or config
from app_setup import APP_ROOT_DIR, LOGO_SUBDIR


class CompanyInfoStepDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(QCoreApplication.translate("CompanyInfoStepDialog", "Company Information"))
        self.setModal(True) # Act as a modal dialog within the setup flow

        self.existing_company_id = None # Added for editing
        self.current_logo_path_on_disk = None # Store existing logo path when editing
        self.logo_path_selected_for_upload = None # Store path of newly selected logo by user

        self.company_id = None # This will store the ID after add/update for the main dialog to use

        layout = QVBoxLayout(self)

        # Company Name
        self.name_label = QLabel(QCoreApplication.translate("CompanyInfoStepDialog", "Company Name:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_edit)

        # Address
        self.address_label = QLabel(QCoreApplication.translate("CompanyInfoStepDialog", "Address:"))
        self.address_edit = QTextEdit()
        self.address_edit.setFixedHeight(80)
        layout.addWidget(self.address_label)
        layout.addWidget(self.address_edit)

        # Payment Info (Optional - keeping for now, can be removed later if too complex for initial)
        self.payment_info_label = QLabel(QCoreApplication.translate("CompanyInfoStepDialog", "Payment Information (e.g., Bank Details):"))
        self.payment_info_edit = QTextEdit()
        self.payment_info_edit.setFixedHeight(80)
        layout.addWidget(self.payment_info_label)
        layout.addWidget(self.payment_info_edit)

        # Other Info (Optional - keeping for now)
        self.other_info_label = QLabel(QCoreApplication.translate("CompanyInfoStepDialog", "Other Information:"))
        self.other_info_edit = QTextEdit()
        self.other_info_edit.setFixedHeight(80)
        layout.addWidget(self.other_info_label)
        layout.addWidget(self.other_info_edit)

        # Logo
        logo_layout = QHBoxLayout()
        self.logo_label_display = QLabel(QCoreApplication.translate("CompanyInfoStepDialog", "Logo:"))
        logo_layout.addWidget(self.logo_label_display)
        self.logo_preview_label = QLabel()
        self.logo_preview_label.setFixedSize(150, 150)
        self.logo_preview_label.setStyleSheet("border: 1px solid #ccc;")
        self.logo_preview_label.setAlignment(Qt.AlignCenter)
        self.logo_preview_label.setText(QCoreApplication.translate("CompanyInfoStepDialog", "Logo Preview"))
        logo_layout.addWidget(self.logo_preview_label)
        self.upload_logo_button = QPushButton(QCoreApplication.translate("CompanyInfoStepDialog", "Upload Logo"))
        self.upload_logo_button.clicked.connect(self.handle_upload_logo)
        logo_layout.addWidget(self.upload_logo_button)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)

        # Note: Buttons like "Next", "Cancel" for this step will be managed by the parent InitialSetupDialog
        # This dialog's accept() method will be called programmatically.

    def handle_upload_logo(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            QCoreApplication.translate("CompanyInfoStepDialog", "Select Logo Image"),
            "",
            QCoreApplication.translate("CompanyInfoStepDialog", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"),
            options=options
        )
        if file_path:
            self.logo_path_selected_for_upload = file_path # User selected a new logo
            pixmap = QPixmap(file_path)
            self.logo_preview_label.setPixmap(pixmap.scaled(
                self.logo_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

    def save_company_data(self):
        company_name = self.name_edit.text().strip()
        address = self.address_edit.toPlainText().strip()
        payment_info = self.payment_info_edit.toPlainText().strip()
        other_info = self.other_info_edit.toPlainText().strip()

        if not company_name:
            QMessageBox.warning(self, QCoreApplication.translate("CompanyInfoStepDialog", "Input Error"), QCoreApplication.translate("CompanyInfoStepDialog", "Company Name is required."))
            return None

        company_data_for_db = {
            "company_name": company_name,
            "address": address,
            "payment_info": payment_info,
            "other_info": other_info,
            # logo_path will be handled next
        }

        processed_logo_db_path = None # This will be the relative path for DB (e.g., logo_xyz.png)
        new_logo_abs_path_for_cleanup = None # Store absolute path for potential cleanup on DB error

        if self.logo_path_selected_for_upload: # User selected a new logo
            logo_dir_abs = os.path.join(APP_ROOT_DIR, LOGO_SUBDIR)
            os.makedirs(logo_dir_abs, exist_ok=True)
            _, ext = os.path.splitext(self.logo_path_selected_for_upload)
            processed_logo_db_path = f"logo_{uuid.uuid4().hex}{ext}"
            new_logo_abs_path_for_cleanup = os.path.join(logo_dir_abs, processed_logo_db_path)
            try:
                shutil.copy(self.logo_path_selected_for_upload, new_logo_abs_path_for_cleanup)
            except Exception as e:
                QMessageBox.critical(self, QCoreApplication.translate("CompanyInfoStepDialog", "Logo Error"), QCoreApplication.translate("CompanyInfoStepDialog", f"Could not save new logo: {e}"))
                return None
        elif self.existing_company_id and self.current_logo_path_on_disk:
            # Editing, no new logo selected, so keep the existing one
            processed_logo_db_path = self.current_logo_path_on_disk

        company_data_for_db['logo_path'] = processed_logo_db_path

        try:
            if self.existing_company_id:
                # Update existing company - Ensure 'is_default' is handled correctly.
                # For initial setup, the first company (even if edited here) should be default.
                company_data_for_db['is_default'] = True # Or fetch current and preserve if logic changes
                success = db_manager.update_company(self.existing_company_id, company_data_for_db)
                if success:
                    QMessageBox.information(self, QCoreApplication.translate("CompanyInfoStepDialog", "Success"), QCoreApplication.translate("CompanyInfoStepDialog", "Company information updated successfully."))
                    return self.existing_company_id
                else:
                    QMessageBox.warning(self, QCoreApplication.translate("CompanyInfoStepDialog", "DB Error"), QCoreApplication.translate("CompanyInfoStepDialog", "Failed to update company information in the database."))
                    # If update failed but a new logo was copied, it should ideally be cleaned up.
                    # However, this might be complex if the original logo was overwritten by name.
                    # For now, new logo copy remains if DB update fails.
                    return None
            else:
                # Add new company
                company_data_for_db['is_default'] = True
                new_company_id = db_manager.add_company(company_data_for_db)
                if new_company_id:
                    self.company_id = new_company_id # Store the new ID
                    QMessageBox.information(self, QCoreApplication.translate("CompanyInfoStepDialog", "Success"), QCoreApplication.translate("CompanyInfoStepDialog", "Company information saved successfully."))
                    return new_company_id
                else:
                    QMessageBox.warning(self, QCoreApplication.translate("CompanyInfoStepDialog", "DB Error"), QCoreApplication.translate("CompanyInfoStepDialog", "Failed to save new company information to the database."))
                    if new_logo_abs_path_for_cleanup and os.path.exists(new_logo_abs_path_for_cleanup):
                        try: os.remove(new_logo_abs_path_for_cleanup)
                        except OSError as e_rem: print(f"Error cleaning up new logo after add_company failed: {e_rem}")
                    return None
        except Exception as e:
            QMessageBox.critical(self, QCoreApplication.translate("CompanyInfoStepDialog", "DB Error"), QCoreApplication.translate("CompanyInfoStepDialog", f"An error occurred: {e}"))
            if new_logo_abs_path_for_cleanup and os.path.exists(new_logo_abs_path_for_cleanup) and not self.existing_company_id : # only cleanup if adding new
                 try: os.remove(new_logo_abs_path_for_cleanup)
                 except OSError as e_rem: print(f"Error cleaning up new logo after exception: {e_rem}")
            return None

    def load_company_for_editing(self, company_data: dict):
        self.existing_company_id = company_data.get('company_id')
        self.name_edit.setText(company_data.get('company_name', ''))
        self.address_edit.setPlainText(company_data.get('address', ''))
        self.payment_info_edit.setPlainText(company_data.get('payment_info', ''))
        self.other_info_edit.setPlainText(company_data.get('other_info', ''))

        self.current_logo_path_on_disk = company_data.get('logo_path') # This is relative path from DB
        self.logo_path_selected_for_upload = None # Reset any prior user selection

        if self.current_logo_path_on_disk:
            # Construct absolute path to display existing logo
            logo_full_path = os.path.join(APP_ROOT_DIR, LOGO_SUBDIR, self.current_logo_path_on_disk)
            if os.path.exists(logo_full_path):
                pixmap = QPixmap(logo_full_path)
                self.logo_preview_label.setPixmap(pixmap.scaled(
                    self.logo_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            else:
                self.logo_preview_label.setText(QCoreApplication.translate("CompanyInfoStepDialog", "Logo not found"))
                print(f"Warning: Existing logo not found at {logo_full_path}")
        else:
            self.logo_preview_label.setText(QCoreApplication.translate("CompanyInfoStepDialog", "No Logo"))


class PromptCompanyInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(QCoreApplication.translate("PromptCompanyInfoDialog", "Initial Company Information"))
        self.setModal(True)
        self.use_default_company = False # Flag to indicate user's choice

        layout = QVBoxLayout(self)

        instruction_label = QLabel(
            QCoreApplication.translate(
                "PromptCompanyInfoDialog",
                "No company is configured. Please enter your company details or use a default configuration to proceed."
            )
        )
        instruction_label.setWordWrap(True)
        layout.addWidget(instruction_label)

        form_layout = QFormLayout()
        self.company_name_edit = QLineEdit()
        form_layout.addRow(QCoreApplication.translate("PromptCompanyInfoDialog", "Company Name:"), self.company_name_edit)

        self.address_edit = QTextEdit()
        self.address_edit.setFixedHeight(60) # Smaller than the full setup dialog
        form_layout.addRow(QCoreApplication.translate("PromptCompanyInfoDialog", "Address (Optional):"), self.address_edit)
        layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox()
        # Save and Continue (AcceptRole)
        self.save_button = self.button_box.addButton(QCoreApplication.translate("PromptCompanyInfoDialog", "Save and Continue"), QDialogButtonBox.AcceptRole)
        # Use Default (ActionRole)
        self.use_default_button = self.button_box.addButton(QCoreApplication.translate("PromptCompanyInfoDialog", "Use Default and Continue"), QDialogButtonBox.ActionRole)
        # Cancel Setup (RejectRole)
        self.cancel_button = self.button_box.addButton(QDialogButtonBox.Cancel) # Standard Cancel role

        self.save_button.clicked.connect(self.accept_dialog)
        self.use_default_button.clicked.connect(self.use_default_and_accept)
        self.cancel_button.clicked.connect(self.reject)

        layout.addWidget(self.button_box)

    def accept_dialog(self):
        if not self.company_name_edit.text().strip():
            QMessageBox.warning(self,
                                QCoreApplication.translate("PromptCompanyInfoDialog", "Input Error"),
                                QCoreApplication.translate("PromptCompanyInfoDialog", "Company Name is required to save."))
            return
        self.use_default_company = False # Explicitly set when saving
        super().accept()

    def use_default_and_accept(self):
        self.use_default_company = True
        super().accept() # Accept the dialog

    def get_company_data(self):
        if self.use_default_company:
            return None # Indicate that default should be used
        return {
            "company_name": self.company_name_edit.text().strip(),
            "address": self.address_edit.toPlainText().strip()
        }


# --- Personnel Entry Widgets ---
class PersonnelInputRowWidget(QWidget):
    remove_signal = pyqtSignal(QWidget) # Signal to emit for removal, passing self

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0) # Compact layout

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(QCoreApplication.translate("PersonnelInputRowWidget", "Name (Required)"))
        layout.addWidget(self.name_edit)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText(QCoreApplication.translate("PersonnelInputRowWidget", "Phone"))
        layout.addWidget(self.phone_edit)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText(QCoreApplication.translate("PersonnelInputRowWidget", "Email"))
        layout.addWidget(self.email_edit)

        self.remove_button = QPushButton(QCoreApplication.translate("PersonnelInputRowWidget", "Remove"))
        self.remove_button.clicked.connect(lambda: self.remove_signal.emit(self))
        layout.addWidget(self.remove_button)

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "phone": self.phone_edit.text().strip(),
            "email": self.email_edit.text().strip(),
        }

    def clear_data(self):
        self.name_edit.clear()
        self.phone_edit.clear()
        self.email_edit.clear()

class PersonnelStepWidget(QWidget):
    def __init__(self, title_text, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)

        self.title_label = QLabel(title_text)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14pt;") # Make title prominent
        self.main_layout.addWidget(self.title_label)

        # Layout for the rows of personnel
        self.personnel_rows_container_widget = QWidget() # A container for rows to potentially put in scroll area
        self.personnel_rows_layout = QVBoxLayout(self.personnel_rows_container_widget)
        self.personnel_rows_layout.setContentsMargins(0,0,0,0)

        # TODO: Implement QScrollArea if many personnel are expected
        # For now, adding rows_container_widget directly.
        # self.scroll_area = QScrollArea()
        # self.scroll_area.setWidgetResizable(True)
        # self.scroll_area.setWidget(self.personnel_rows_container_widget)
        # self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addWidget(self.personnel_rows_container_widget)


        self.add_person_button = QPushButton(QCoreApplication.translate("PersonnelStepWidget", "Add Person"))
        self.add_person_button.clicked.connect(self.add_person_row)
        self.main_layout.addWidget(self.add_person_button, 0, Qt.AlignLeft) # Align button left

        self.personnel_widgets = []
        self.company_id = None # To be set by the main dialog

        self.main_layout.addStretch(1) # Add stretch at the end

    def set_company_id(self, company_id):
        self.company_id = company_id

    def add_person_row(self, name="", phone="", email=""): # Allow pre-filling data
        row_widget = PersonnelInputRowWidget()
        row_widget.name_edit.setText(name)
        row_widget.phone_edit.setText(phone)
        row_widget.email_edit.setText(email)
        row_widget.remove_signal.connect(self.handle_remove_person_row)

        self.personnel_rows_layout.addWidget(row_widget)
        self.personnel_widgets.append(row_widget)

    def handle_remove_person_row(self, row_widget_to_remove):
        if row_widget_to_remove in self.personnel_widgets:
            self.personnel_widgets.remove(row_widget_to_remove)
            self.personnel_rows_layout.removeWidget(row_widget_to_remove)
            row_widget_to_remove.deleteLater()

    def get_personnel_data(self):
        all_data = []
        for widget in self.personnel_widgets:
            data = widget.get_data()
            if data['name']: # Only include if name is present
                all_data.append(data)
        return all_data

    def save_personnel(self, company_id_param, role_name):
        if not company_id_param: # Check if company_id from param is valid
             QMessageBox.critical(self, QCoreApplication.translate("PersonnelStepWidget", "Error"), QCoreApplication.translate("PersonnelStepWidget", "Company ID is not set. Cannot save personnel."))
             return False

        self.set_company_id(company_id_param) # Ensure internal company_id is also set

        personnel_to_save = self.get_personnel_data()
        if not personnel_to_save:
            # It's okay to have no personnel, so this might not be an error.
            # Or, if at least one is required, show a warning.
            # For initial setup, let's assume it's okay to skip adding personnel.
            QMessageBox.information(self, QCoreApplication.translate("PersonnelStepWidget", "No Personnel"), QCoreApplication.translate("PersonnelStepWidget", "No personnel information was entered. Proceeding without adding new personnel."))
            return True # Indicate success (no data to save, but no error)

        saved_count = 0
        error_count = 0
        for person_data in personnel_to_save:
            if not person_data['name']: # Should be caught by get_personnel_data, but double check
                error_count +=1
                continue

            db_data = {
                'company_id': self.company_id,
                'name': person_data['name'],
                'role': role_name,
                'phone': person_data['phone'],
                'email': person_data['email']
            }
            personnel_id = db_manager.add_company_personnel(db_data)
            if personnel_id:
                saved_count += 1
            else:
                error_count += 1
                QMessageBox.warning(self, QCoreApplication.translate("PersonnelStepWidget", "Save Error"),
                                    QCoreApplication.translate("PersonnelStepWidget", f"Failed to save personnel: {person_data['name']}."))

        if error_count == 0:
            QMessageBox.information(self, QCoreApplication.translate("PersonnelStepWidget", "Success"),
                                    QCoreApplication.translate("PersonnelStepWidget", f"Successfully saved {saved_count} personnel."))
            return True
        else:
            QMessageBox.warning(self, QCoreApplication.translate("PersonnelStepWidget", "Partial Success"),
                                QCoreApplication.translate("PersonnelStepWidget", f"Successfully saved {saved_count} personnel. Failed to save {error_count} personnel."))
            return False # Indicate that some saves failed

class WelcomeStepWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        welcome_label = QLabel(
            f"<h1>{QCoreApplication.translate('WelcomeStepWidget', 'Setup Complete!')}</h1>"
            f"<p>{QCoreApplication.translate('WelcomeStepWidget', 'Welcome to ClientDocManager.')}</p>"
            f"<p>{QCoreApplication.translate('WelcomeStepWidget', 'You can now proceed to use the application. Your initial company and personnel configurations have been saved.')}</p>"
        )
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setWordWrap(True)
        layout.addWidget(welcome_label)

        # Placeholder for a fireworks image or styled text
        # For now, we'll use styled text. If an image 'icons/fireworks.png' was available:
        # self.fireworks_label = QLabel()
        # fireworks_pixmap = QPixmap(os.path.join(APP_ROOT_DIR, "icons", "fireworks.png")) # Assuming APP_ROOT_DIR is accessible
        # if not fireworks_pixmap.isNull():
        #     self.fireworks_label.setPixmap(fireworks_pixmap.scaledToHeight(150, Qt.SmoothTransformation))
        #     self.fireworks_label.setAlignment(Qt.AlignCenter)
        #     layout.addWidget(self.fireworks_label)
        # else:
        #     print("Warning: Fireworks image not found or could not be loaded.")
        #     no_image_label = QLabel(QCoreApplication.translate("WelcomeStepWidget", "🎉 Congratulations! 🎉"))
        #     no_image_label.setStyleSheet("font-size: 24pt; text-align: center;")
        #     no_image_label.setAlignment(Qt.AlignCenter)
        #     layout.addWidget(no_image_label)

        congrats_label = QLabel(QCoreApplication.translate("WelcomeStepWidget", "🎉 Congratulations! 🎉"))
        congrats_label.setStyleSheet("font-size: 24pt; text-align: center;")
        congrats_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(congrats_label)


class InitialSetupDialog(QDialog):
    setup_completed_signal = pyqtSignal() # Emitted when setup is successfully finished

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(QCoreApplication.translate("InitialSetupDialog", "Initial Application Setup"))
        self.setMinimumSize(600, 400) # Make it a bit larger
        self.setModal(True)

        self.company_id = None # To store the ID of the company created/updated in the first step
        self.default_company_to_edit_data = None


        layout = QVBoxLayout(self)
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

        # Step 1: Company Information
        self.company_info_step = CompanyInfoStepDialog(self) # Pass self as parent
        self.stacked_widget.addWidget(self.company_info_step)

        # Load default company for editing if it exists
        try:
            self.default_company_to_edit_data = db_manager.get_default_company()
            if self.default_company_to_edit_data:
                self.company_info_step.load_company_for_editing(self.default_company_to_edit_data)
                self.company_id = self.default_company_to_edit_data.get('company_id') # Pre-set company_id for other steps
        except Exception as e:
            print(f"Error loading default company for editing: {e}")
            # Proceed without pre-filling if error occurs

        # Step 2: Sellers
        self.sellers_step = PersonnelStepWidget(QCoreApplication.translate("InitialSetupDialog", "Add Sellers (Optional)"))
        self.stacked_widget.addWidget(self.sellers_step)

        # Step 3: Technicians (Placeholder, to be replaced with another PersonnelStepWidget instance)
        self.technicians_step = PersonnelStepWidget(QCoreApplication.translate("InitialSetupDialog", "Add Technicians (Optional)"))
        # For now, let's use a simple placeholder for technicians to keep this change focused
        # self.technicians_step_placeholder = QWidget()
        # tech_layout = QVBoxLayout(self.technicians_step_placeholder)
        # tech_layout.addWidget(QLabel(QCoreApplication.translate("InitialSetupDialog", "Step 3: Configure Technicians (Placeholder)")))
        # self.stacked_widget.addWidget(self.technicians_step_placeholder)
        self.stacked_widget.addWidget(self.technicians_step) # Add the actual widget

        # Step 4: Welcome
        self.welcome_step = WelcomeStepWidget()
        self.stacked_widget.addWidget(self.welcome_step)

        # Navigation Buttons
        self.button_box = QDialogButtonBox()
        self.prev_button = self.button_box.addButton(QCoreApplication.translate("InitialSetupDialog", "Previous"), QDialogButtonBox.ActionRole)
        self.next_button = self.button_box.addButton(QCoreApplication.translate("InitialSetupDialog", "Next"), QDialogButtonBox.ActionRole)
        self.finish_button = self.button_box.addButton(QDialogButtonBox.Finish)
        self.cancel_button = self.button_box.addButton(QDialogButtonBox.Cancel)

        self.prev_button.clicked.connect(self.go_previous)
        self.next_button.clicked.connect(self.go_next)
        self.finish_button.clicked.connect(self.finish_setup)
        self.cancel_button.clicked.connect(self.reject) # QDialog's reject

        layout.addWidget(self.button_box)
        self.update_button_states()

    def update_button_states(self):
        current_index = self.stacked_widget.currentIndex()
        is_last_page = (current_index == self.stacked_widget.count() - 1)
        is_welcome_page = (self.stacked_widget.widget(current_index) == self.welcome_step)

        self.prev_button.setEnabled(current_index > 0 and not is_welcome_page)
        self.next_button.setEnabled(not is_last_page and not is_welcome_page)

        # Finish button is always enabled on the welcome page,
        # or on the last "data entry" page (e.g. Technicians before Welcome)
        self.finish_button.setEnabled(is_welcome_page or current_index == self.stacked_widget.indexOf(self.technicians_step))

        if is_welcome_page:
            self.finish_button.setDefault(True) # Make Finish the default button on welcome page
        else:
            self.next_button.setDefault(True)


    def go_next(self):
        current_index = self.stacked_widget.currentIndex()

        if current_index == 0: # Company Info Step
            # The CompanyInfoStepDialog is a QDialog, but we are using it as a page.
            # We need to call its save method.
            company_id = self.company_info_step.save_company_data()
            if company_id:
                self.company_id = company_id
                self.sellers_step.set_company_id(self.company_id) # Pass company_id to sellers step
                self.technicians_step.set_company_id(self.company_id) # And to technicians step
                self.stacked_widget.setCurrentIndex(current_index + 1)
            else:
                # Error message already shown by save_company_data
                return
        elif current_index == 1: # Currently on Sellers step
            if self.sellers_step.save_personnel(self.company_id, "seller"):
                self.stacked_widget.setCurrentIndex(current_index + 1)
            else:
                # Error message shown by save_personnel
                return
        elif current_index == 2: # Currently on Technicians step (if it were also PersonnelStepWidget)
            # This will be activated when technicians step is fully implemented
            # For now, it just moves to next if PersonnelStepWidget is used for it
            if self.technicians_step.save_personnel(self.company_id, "technician"):
                 # This was the Technicians step, successful save, so go to Welcome step
                 self.stacked_widget.setCurrentIndex(self.stacked_widget.indexOf(self.welcome_step))
            else:
                return # Error message shown by save_personnel, stay on Technicians page
        elif current_index < self.stacked_widget.count() - 1: # Generic next for other non-final steps
            self.stacked_widget.setCurrentIndex(current_index + 1)

        self.update_button_states()

    def go_previous(self):
        current_index = self.stacked_widget.currentIndex()
        if current_index > 0:
            self.stacked_widget.setCurrentIndex(current_index - 1)
        self.update_button_states()

    def finish_setup(self):
        # This is called when the "Finish" button is clicked.
        current_index = self.stacked_widget.currentIndex()
        current_widget = self.stacked_widget.widget(current_index)

        if current_widget == self.technicians_step:
            if not self.technicians_step.save_personnel(self.company_id, "technician"):
                return # Don't finish if save fails
        elif current_widget == self.sellers_step: # Should not happen if Technicians is after Sellers and Welcome is last
             # This case might be hit if Technicians step is skipped or Welcome step is before Technicians
             # For robusteness, if Finish is clicked on Sellers step, save sellers.
            if not self.sellers_step.save_personnel(self.company_id, "seller"):
                return
        # No specific save action needed if on CompanyInfoStep (Next would have saved) or WelcomeStep

        QMessageBox.information(self, QCoreApplication.translate("InitialSetupDialog", "Setup Complete"), QCoreApplication.translate("InitialSetupDialog", "Initial setup is complete. Welcome to the application!"))
        self.setup_completed_signal.emit()
        self.accept() # QDialog's accept

    def reject(self):
        # Handle cancellation
        reply = QMessageBox.question(self,
                                     QCoreApplication.translate("InitialSetupDialog", "Confirm Cancel"),
                                     QCoreApplication.translate("InitialSetupDialog", "Are you sure you want to cancel the initial setup? The application might not function correctly."),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            super().reject() # Call QDialog's reject method
        # else: do nothing, stay on dialog

if __name__ == '__main__':
    # This is for testing the dialogs independently
    from PyQt5.QtWidgets import QApplication
    import sys

    # Dummy app_setup variables for standalone testing
    APP_ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
    LOGO_SUBDIR = "company_logos"
    os.makedirs(os.path.join(APP_ROOT_DIR, LOGO_SUBDIR), exist_ok=True)

    # Dummy db_manager for standalone testing
    class DummyDBManager:
        def add_company(self, name, address, logo_filename, payment_info, other_info, is_default):
            print(f"DummyDB: Adding company: {name}, Logo: {logo_filename}, Default: {is_default}")
            return 1 # Simulate successful add with company_id = 1
        def initialize_database(self): # Ensure this method exists
             print("DummyDB: Database initialized.")

    db_manager.initialize_database() # Call initialize_database on the actual or dummy db_manager
    # Replace actual db_manager with dummy for test if needed, or ensure test DB is setup
    # For this example, we'll assume the actual db_manager can be used or a test DB is configured.
    # If using the actual db_manager, ensure the database file (e.g., client_docs.db) is writable in the test context.


    app = QApplication(sys.argv)

    # Test CompanyInfoStepDialog
    # company_dialog = CompanyInfoStepDialog()
    # if company_dialog.exec_() == QDialog.Accepted:
    #     print(f"Company Info Accepted. Company ID: {company_dialog.company_id}")
    # else:
    #     print("Company Info Cancelled.")

    # Test InitialSetupDialog
    initial_dialog = InitialSetupDialog()
    if initial_dialog.exec_() == QDialog.Accepted:
        print("Initial Setup Dialog Accepted (Finished).")
    else:
        print("Initial Setup Dialog Cancelled.")

    sys.exit(app.exec_())
