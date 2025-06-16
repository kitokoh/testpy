# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QMessageBox

class ProductDimensionUIDialog(QDialog):
    def __init__(self, product_id, app_root_dir, parent=None, read_only=False):
        super().__init__(parent)
        self.product_id = product_id
        self.app_root_dir = app_root_dir
        self.read_only = read_only
        self.setWindowTitle("Product Dimensions") # Provide a window title

        # Basic UI - can be expanded later
        layout = QVBoxLayout(self)
        message_label = QLabel("Detailed dimensions view is currently unavailable.")
        layout.addWidget(message_label)
        self.setLayout(layout)

        # Log that the dialog is being used with placeholder functionality
        print(f"ProductDimensionUIDialog initialized for product_id: {self.product_id} (Placeholder Implementation)")

    def exec_(self):
        # For a placeholder, we might just show a message and not block like a real modal.
        # Or, to behave more like a dialog, call super().exec_()
        # For now, let's show an informational message if it's opened.
        QMessageBox.information(self, "Feature Incomplete", "Detailed dimensions view is currently unavailable.")
        # If it should behave like a modal dialog, uncomment the next line and remove/comment out the QMessageBox
        # return super().exec_()
        return QDialog.Accepted # Or Rejected, depending on desired non-blocking behavior
