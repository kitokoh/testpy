# partners/partner_category_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QListWidget, QPushButton,
                             QHBoxLayout, QMessageBox, QDialogButtonBox,
                             QInputDialog, QListWidgetItem)
from PyQt5.QtCore import Qt
import db as db_manager

from db import ( get_all_partner_categories,get_partner_category_by_name,add_partner_category,  delete_partner_category, 
    get_all_partner_categories, update_partner_category, get_partner_category_by_id
)
class PartnerCategoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Partner Categories")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        self.category_list_widget = QListWidget()
        layout.addWidget(self.category_list_widget)

        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.edit_button = QPushButton("Edit Selected")
        self.delete_button = QPushButton("Delete Selected")

        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.delete_button)
        layout.addLayout(buttons_layout)

        self.done_button_box = QDialogButtonBox(QDialogButtonBox.Ok) # Changed name for clarity
        layout.addWidget(self.done_button_box)

        # Connect signals
        self.add_button.clicked.connect(self.add_category)
        self.edit_button.clicked.connect(self.edit_selected_category) # Renamed handler for clarity
        self.delete_button.clicked.connect(self.delete_category)
        self.category_list_widget.itemDoubleClicked.connect(self.edit_category_item)
        self.done_button_box.accepted.connect(self.accept)

        self.load_categories()

    def load_categories(self):
        self.category_list_widget.clear()
        try:
            categories = get_all_partner_categories()
            if categories:
                for category in categories:
                    item = QListWidgetItem(category['name'])
                    item.setData(Qt.UserRole, category['category_id'])
                    self.category_list_widget.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Categories", f"Could not load categories: {e}")

    def add_category(self):
        text, ok = QInputDialog.getText(self, "Add Category", "Enter category name:")
        if ok and text.strip():
            category_name = text.strip()
            # Check if category already exists (case insensitive for example)
            existing = get_partner_category_by_name(category_name)
            if existing:
                QMessageBox.warning(self, "Add Category", f"Category '{category_name}' already exists.")
                return

            category_id = add_partner_category(name=category_name)
            if category_id is not None:
                self.load_categories()
            else:
                QMessageBox.warning(self, "Add Category", "Failed to add category.")
        elif ok and not text.strip():
            QMessageBox.warning(self, "Add Category", "Category name cannot be empty.")

    def edit_selected_category(self):
        current_item = self.category_list_widget.currentItem()
        if not current_item:
            QMessageBox.information(self, "Edit Category", "Please select a category to edit.")
            return
        self.edit_category_item(current_item)

    def edit_category_item(self, item):
        if not item: return

        category_id = item.data(Qt.UserRole)
        current_name = item.text()

        text, ok = QInputDialog.getText(self, "Edit Category", "Enter new category name:", text=current_name)
        if ok and text.strip():
            new_name = text.strip()
            if new_name == current_name:
                return # No change

            # Check if new name conflicts with another existing category
            existing_other = get_partner_category_by_name(new_name)
            if existing_other and existing_other['category_id'] != category_id:
                 QMessageBox.warning(self, "Edit Category", f"Another category with name '{new_name}' already exists.")
                 return

            if update_partner_category(category_id, name=new_name):
                self.load_categories()
            else:
                QMessageBox.warning(self, "Edit Category", f"Failed to update category '{current_name}'.")
        elif ok and not text.strip():
             QMessageBox.warning(self, "Edit Category", "Category name cannot be empty.")

    def delete_category(self):
        current_item = self.category_list_widget.currentItem()
        if not current_item:
            QMessageBox.information(self, "Delete Category", "Please select a category to delete.")
            return

        category_id = current_item.data(Qt.UserRole)
        category_name = current_item.text()

        reply = QMessageBox.question(self, "Delete Category",
                                     f"Are you sure you want to delete category '{category_name}'?\n"
                                     "This will also unlink it from all partners.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if delete_partner_category(category_id):
                self.load_categories()
            else:
                QMessageBox.warning(self, "Delete Category", f"Failed to delete category '{category_name}'.")

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    dialog = PartnerCategoryDialog()
    dialog.show()
    sys.exit(app.exec_())
