# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem,
    QDialogButtonBox, QLabel, QAbstractItemView
)
from PyQt5.QtCore import Qt
import db as db_manager

class SelectContactsDialog(QDialog):
    def __init__(self, client_id, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.selected_emails = []

        self.setWindowTitle(self.tr("Sélectionner des Contacts"))
        self.setMinimumSize(400, 300)
        self.setup_ui()
        self.load_contacts()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.contacts_list_widget = QListWidget()
        self.contacts_list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        layout.addWidget(QLabel(self.tr("Contacts disponibles :")))
        layout.addWidget(self.contacts_list_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setText(self.tr("OK"))
        ok_button.setObjectName("primaryButton")
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText(self.tr("Annuler"))

        button_box.accepted.connect(self.accept_selection)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_contacts(self):
        contacts = db_manager.get_contacts_for_client(self.client_id)
        if contacts:
            for contact in contacts:
                name = contact.get("name", self.tr("N/A"))
                email = contact.get("email", self.tr("N/A"))
                if email == self.tr("N/A") or not email.strip():
                    continue
                item_text = f"{name} <{email}>"
                list_item = QListWidgetItem(item_text)
                list_item.setFlags(list_item.flags() | Qt.ItemIsUserCheckable)
                list_item.setCheckState(Qt.Unchecked)
                list_item.setData(Qt.UserRole, email)
                self.contacts_list_widget.addItem(list_item)

    def accept_selection(self):
        self.selected_emails = []
        for i in range(self.contacts_list_widget.count()):
            item = self.contacts_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                email = item.data(Qt.UserRole)
                if email:
                    self.selected_emails.append(email)
        self.accept()

    def get_selected_emails(self):
        return self.selected_emails
