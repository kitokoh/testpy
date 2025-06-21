import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QLineEdit, QComboBox, QSpinBox,
    QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout, QMessageBox
)
from PyQt5.QtCore import Qt

class AddEditStatusDialog(QDialog):
    def __init__(self, parent=None, status_data=None):
        super().__init__(parent)
        self.status_data = status_data  # For pre-filling in edit mode

        if self.status_data:
            self.setWindowTitle("Edit Status")
        else:
            self.setWindowTitle("Add New Status")

        self.init_ui()
        if self.status_data:
            self.prefill_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        # For now, predefined list. Can be made editable or fetched from DB later.
        self.type_combo.addItems(["Client", "Project", "Task", "Ticket"]) # Added Ticket as an example
        self.type_combo.setEditable(True) # Allow free text input

        self.color_edit = QLineEdit()
        self.color_edit.setPlaceholderText("#RRGGBB (e.g., #FF0000)")
        self.sort_order_spinbox = QSpinBox()
        self.sort_order_spinbox.setRange(0, 999) # Max sort order

        form_layout.addRow(QLabel("Name:"), self.name_edit)
        form_layout.addRow(QLabel("Type:"), self.type_combo)
        form_layout.addRow(QLabel("Color (Hex):"), self.color_edit)
        form_layout.addRow(QLabel("Sort Order:"), self.sort_order_spinbox)

        main_layout.addLayout(form_layout)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)

        main_layout.addLayout(buttons_layout)

        # Connect signals
        self.ok_button.clicked.connect(self.accept_dialog)
        self.cancel_button.clicked.connect(self.reject)

    def prefill_data(self):
        """Prefills the dialog fields if status_data is provided (for editing)."""
        if self.status_data:
            self.name_edit.setText(self.status_data.get("status_name", ""))

            type_value = self.status_data.get("status_type", "")
            type_index = self.type_combo.findText(type_value, Qt.MatchFixedString)
            if type_index >= 0:
                self.type_combo.setCurrentIndex(type_index)
            else:
                self.type_combo.setCurrentText(type_value) # For free text if not in predefined list

            self.color_edit.setText(self.status_data.get("color_hex", ""))
            self.sort_order_spinbox.setValue(self.status_data.get("sort_order", 0))

    def get_data(self):
        """Returns the entered data as a dictionary."""
        return {
            "status_name": self.name_edit.text().strip(),
            "status_type": self.type_combo.currentText().strip(),
            "color_hex": self.color_edit.text().strip() if self.color_edit.text().strip() else None, # Store None if empty
            "sort_order": self.sort_order_spinbox.value()
        }

    def accept_dialog(self):
        """Validates input before accepting."""
        data = self.get_data()
        if not data["status_name"]:
            QMessageBox.warning(self, "Input Error", "Status Name cannot be empty.")
            return
        if not data["status_type"]:
            QMessageBox.warning(self, "Input Error", "Status Type cannot be empty.")
            return

        # Optional: Validate color_hex format if needed (e.g., regex for #RRGGBB)
        color = data["color_hex"]
        if color and not (color.startswith("#") and len(color) == 7):
            try:
                # Check if it's a valid hex by attempting to convert the R, G, B parts
                int(color[1:3], 16)
                int(color[3:5], 16)
                int(color[5:7], 16)
            except (ValueError, IndexError):
                QMessageBox.warning(self, "Input Error", "Color Hex code should be in #RRGGBB format (e.g., #FF0000) or empty.")
                return

        self.accept()


if __name__ == '__main__':
    # This part is for testing the dialog independently
    app = QApplication(sys.argv)

    # Test Add mode
    add_dialog = AddEditStatusDialog()
    if add_dialog.exec_() == QDialog.Accepted:
        print("Add Dialog Accepted. Data:", add_dialog.get_data())
    else:
        print("Add Dialog Canceled.")

    # Test Edit mode (example data)
    sample_edit_data = {
        "status_id": 1,
        "status_name": "In Progress",
        "status_type": "Project",
        "color_hex": "#FFA500",
        "sort_order": 10
    }
    edit_dialog = AddEditStatusDialog(status_data=sample_edit_data)
    if edit_dialog.exec_() == QDialog.Accepted:
        print("Edit Dialog Accepted. Data:", edit_dialog.get_data())
    else:
        print("Edit Dialog Canceled.")

    sys.exit(app.exec_())
