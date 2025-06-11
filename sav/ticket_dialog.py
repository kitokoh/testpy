# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTextEdit,
    QPushButton, QMessageBox, QFormLayout
)
from PyQt5.QtCore import Qt
from datetime import datetime
import db as db_manager
from email_service import EmailSenderService

class SAVTicketDialog(QDialog):
    def __init__(self, client_id, purchased_products, ticket_data=None, email_service_instance=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.purchased_products = purchased_products # List of dicts: {'name': str, 'client_project_product_id': int}
        self.ticket_data = ticket_data # Dict if editing, None if new
        self.email_service = email_service_instance if email_service_instance else EmailSenderService()
        # self.email_service = None # Placeholder for now

        self.setWindowTitle(self.tr("Gestion Ticket SAV"))
        self.setMinimumWidth(500)

        self.setup_ui()

        if self.ticket_data:
            self.populate_edit_data()
        else: # New ticket mode
            self.resolution_edit.setVisible(False)
            self.form_layout.labelForField(self.resolution_edit).setVisible(False)
            self.status_combo.setVisible(False)
            self.form_layout.labelForField(self.status_combo).setVisible(False)
            self.technician_combo.setVisible(False)
            self.form_layout.labelForField(self.technician_combo).setVisible(False)


    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        self.product_combo = QComboBox()
        self.product_combo.addItem(self.tr("Aucun / Problème Général"), None)
        for prod in self.purchased_products:
            self.product_combo.addItem(f"{prod['name']} (ID: {prod['client_project_product_id']})", prod['client_project_product_id'])

        self.issue_desc_edit = QTextEdit()
        self.issue_desc_edit.setPlaceholderText(self.tr("Décrivez en détail le problème rencontré..."))

        self.status_combo = QComboBox() # Populated in edit mode
        self.technician_combo = QComboBox() # Populated in edit mode
        self.resolution_edit = QTextEdit()
        self.resolution_edit.setPlaceholderText(self.tr("Détails de la résolution ou des étapes entreprises..."))

        self.form_layout.addRow(self.tr("Produit Concerné (si applicable):"), self.product_combo)
        self.form_layout.addRow(self.tr("Description du Problème:"), self.issue_desc_edit)
        self.form_layout.addRow(self.tr("Statut:"), self.status_combo)
        self.form_layout.addRow(self.tr("Technicien Assigné:"), self.technician_combo)
        self.form_layout.addRow(self.tr("Détails de Résolution:"), self.resolution_edit)

        main_layout.addLayout(self.form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton(self.tr("OK"))
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton(self.tr("Annuler"))
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

    def populate_edit_data(self):
        if not self.ticket_data:
            return

        # Product selection
        cpp_id = self.ticket_data.get('client_project_product_id')
        if cpp_id:
            index = self.product_combo.findData(cpp_id)
            if index >= 0:
                self.product_combo.setCurrentIndex(index)
            else:
                # Product might not be in the list (e.g. if it was unlinked or data inconsistency)
                # Add it as a disabled/special item or handle as error
                self.product_combo.addItem(self.tr(f"Produit ID {cpp_id} (Archivé/Manquant)"), cpp_id)
                self.product_combo.setCurrentIndex(self.product_combo.count() -1)
                # self.product_combo.setEnabled(False) # Optionally disable if product context is critical and missing
        else:
            self.product_combo.setCurrentIndex(0) # "Aucun / Problème Général"

        self.issue_desc_edit.setText(self.ticket_data.get('issue_description', ''))
        self.resolution_edit.setText(self.ticket_data.get('resolution_details', ''))

        # Load and set Status
        sav_statuses = db_manager.get_all_status_settings(status_type='SAVTicket')
        self.status_combo.clear()
        current_status_id = self.ticket_data.get('status_id')
        current_status_index = 0
        for i, status in enumerate(sav_statuses):
            self.status_combo.addItem(status['status_name'], status['status_id'])
            if status['status_id'] == current_status_id:
                current_status_index = i
        self.status_combo.setCurrentIndex(current_status_index)

        # Load and set Technician
        technicians = db_manager.get_all_team_members(filters={'is_active': True})
        self.technician_combo.clear()
        self.technician_combo.addItem(self.tr("Non assigné"), None)
        current_technician_id = self.ticket_data.get('assigned_technician_id')
        current_tech_index = 0
        for i, tech in enumerate(technicians):
            self.technician_combo.addItem(tech['full_name'], tech['team_member_id'])
            if tech['team_member_id'] == current_technician_id:
                current_tech_index = i + 1 # +1 due to "Non assigné"
        self.technician_combo.setCurrentIndex(current_tech_index)

        # Make read-only fields visible and populated if needed (e.g. Ticket ID, Opened At)
        # For simplicity, these are not added as separate labels in this iteration
        # but could be added to the form_layout.
        self.setWindowTitle(self.tr("Modifier Ticket SAV - ID: ") + self.ticket_data.get('ticket_id'))


    def accept(self):
        # Data collection
        selected_cpp_id = self.product_combo.currentData()
        issue_description = self.issue_desc_edit.toPlainText().strip()

        if not issue_description:
            QMessageBox.warning(self, self.tr("Validation"), self.tr("La description du problème est obligatoire."))
            return

        if self.ticket_data: # Edit Mode
            status_id = self.status_combo.currentData()
            assigned_technician_id = self.technician_combo.currentData()
            resolution_details = self.resolution_edit.toPlainText().strip()

            update_payload = {
                'client_project_product_id': selected_cpp_id, # Allow product change
                'issue_description': issue_description, # Allow issue desc change
                'status_id': status_id,
                'assigned_technician_id': assigned_technician_id,
                'resolution_details': resolution_details
            }

            old_status_id = self.ticket_data.get('status_id')
            success = db_manager.update_sav_ticket(self.ticket_data['ticket_id'], update_payload)

            if success:
                new_status_id = update_payload['status_id']
                new_status_obj = db_manager.get_status_setting_by_id(new_status_id)

                if new_status_obj and new_status_obj.get('status_name') == 'Résolu' and \
                   (old_status_id != new_status_id or not self.ticket_data.get('closed_at')): # Check if status changed to Résolu or was already Résolu but not closed
                    db_manager.update_sav_ticket(self.ticket_data['ticket_id'], {'closed_at': datetime.utcnow().isoformat() + "Z"})

                    client_data_res = db_manager.get_client_by_id(self.client_id)
                    lang_code_res = 'fr'
                    if client_data_res and client_data_res.get('selected_languages'):
                        primary_lang_res = client_data_res.get('selected_languages').split(',')[0].strip()
                        if primary_lang_res: lang_code_res = primary_lang_res

                    template_obj_res = db_manager.get_template_by_type_lang_default('email_sav_ticket_resolved', lang_code_res)
                    contact_email_res = self._get_primary_client_email(self.client_id)

                    if template_obj_res and contact_email_res and self.email_service:
                        google_maps_url = db_manager.get_setting('google_maps_review_url')
                        resolved_ticket_details = db_manager.get_sav_ticket_by_id(self.ticket_data['ticket_id'])
                        product_name_res = "N/A"
                        if resolved_ticket_details and resolved_ticket_details.get('client_project_product_id'): # Check resolved_ticket_details not None
                            cpp_data_res = db_manager.get_client_project_product_by_id(resolved_ticket_details['client_project_product_id'])
                            if cpp_data_res: product_name_res = cpp_data_res.get('product_name', "N/A")

                        email_context_res = {
                            'ticket': resolved_ticket_details,
                            'client': client_data_res,
                            'product': {'name': product_name_res},
                            'project': db_manager.get_project_by_id(client_data_res['project_identifier']) if client_data_res and client_data_res.get('project_identifier') else {},
                            'seller': db_manager.get_default_company(),
                            'app': {'google_maps_review_url': google_maps_url if google_maps_url else ""}
                        }
                        body_content_res = template_obj_res.get('raw_template_file_data')
                        if isinstance(body_content_res, bytes):
                            body_content_res = body_content_res.decode('utf-8')

                        if body_content_res:
                            self.email_service.send_email(
                                recipient_email=contact_email_res,
                                subject_template=template_obj_res['email_subject_template'],
                                body_html_content_or_filename=body_content_res,
                                context_data=email_context_res,
                                template_obj=template_obj_res
                            )
                            print(f"INFO: 'Ticket Résolu' email sent for ticket {self.ticket_data['ticket_id']} to {contact_email_res}")
                        else:
                            print(f"Warning: Email body content for 'email_sav_ticket_resolved' ({lang_code_res}) is empty.")
                    else:
                        print(f"Warning: Could not send 'Ticket Résolu' email for {self.ticket_data['ticket_id']}. Template: {bool(template_obj_res)}, Email: {contact_email_res}, Service: {bool(self.email_service)}")

                    print(f"INFO: Ticket {self.ticket_data['ticket_id']} marked as Résolu and closed.")

                QMessageBox.information(self, self.tr("Succès"), self.tr("Ticket SAV mis à jour avec succès."))
                super().accept()
            else:
                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Impossible de mettre à jour le ticket SAV."))

        else: # New Ticket Mode
            initial_status_ouver_info = db_manager.get_status_setting_by_name('Ouvert', 'SAVTicket')
            if not initial_status_ouver_info:
                QMessageBox.critical(self, self.tr("Erreur Configuration"), self.tr("Le statut initial 'Ouvert' pour les tickets SAV n'est pas configuré."))
                return
            initial_status_id = initial_status_ouver_info['status_id']

            ticket_payload = {
                'client_id': self.client_id,
                'client_project_product_id': selected_cpp_id,
                'issue_description': issue_description,
                'status_id': initial_status_id,
                # 'created_by_user_id': get_current_user_id() # Placeholder for actual user ID
            }
            new_ticket_id = db_manager.add_sav_ticket(ticket_payload)
            if new_ticket_id:
                client_data = db_manager.get_client_by_id(self.client_id)
                lang_code = 'fr' # Default
                if client_data and client_data.get('selected_languages'):
                    primary_lang = client_data.get('selected_languages').split(',')[0].strip()
                    if primary_lang: lang_code = primary_lang

                template_obj = db_manager.get_template_by_type_lang_default('email_sav_ticket_opened', lang_code)
                contact_email = self._get_primary_client_email(self.client_id)

                if template_obj and contact_email and self.email_service:
                    ticket_details_for_email = db_manager.get_sav_ticket_by_id(new_ticket_id)
                    product_name_for_email = "N/A"
                    if ticket_details_for_email.get('client_project_product_id'):
                        cpp_data = db_manager.get_client_project_product_by_id(ticket_details_for_email['client_project_product_id'])
                        if cpp_data: product_name_for_email = cpp_data.get('product_name', "N/A")

                    email_context = {
                        'ticket': ticket_details_for_email,
                        'client': client_data,
                        'product': {'name': product_name_for_email},
                        'project': db_manager.get_project_by_id(client_data['project_identifier']) if client_data.get('project_identifier') else {}, # Basic project info if available
                        'seller': db_manager.get_default_company() # Assuming default company is seller
                    }

                    # Ensure raw_template_file_data is used
                    body_content = template_obj.get('raw_template_file_data')
                    if isinstance(body_content, bytes):
                        body_content = body_content.decode('utf-8')

                    if body_content:
                        self.email_service.send_email(
                            recipient_email=contact_email,
                            subject_template=template_obj['email_subject_template'],
                            body_html_content_or_filename=body_content, # Pass raw HTML content
                            context_data=email_context,
                            template_obj=template_obj # Pass the whole object for flexibility
                        )
                        print(f"INFO: 'Ticket Ouvert' email sent for ticket {new_ticket_id} to {contact_email}")
                    else:
                        print(f"Warning: Email body content for 'email_sav_ticket_opened' ({lang_code}) is empty or missing.")
                else:
                    print(f"Warning: Could not send 'Ticket Ouvert' email for {new_ticket_id}. Template found: {bool(template_obj)}, Contact email: {contact_email}")

                QMessageBox.information(self, self.tr("Succès"), self.tr("Nouveau ticket SAV ouvert avec succès (ID: {0}).").format(new_ticket_id))
                super().accept()
            else:
                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Impossible d'ouvrir le nouveau ticket SAV."))

    def _get_primary_client_email(self, client_id_for_email):
        contacts = db_manager.get_contacts_for_client(client_id_for_email)
        if not contacts:
            return None

        primary_contact = next((c for c in contacts if c.get('is_primary_for_client') and c.get('email')), None)
        if primary_contact:
            return primary_contact['email']

        # Fallback to first contact with an email
        first_contact_with_email = next((c for c in contacts if c.get('email')), None)
        if first_contact_with_email:
            return first_contact_with_email['email']

        return None

if __name__ == '__main__':
    # This part is for testing the dialog independently
    # You would need to mock db_manager and EmailSenderService or have a test DB setup
    from PyQt5.QtWidgets import QApplication
    import sys

    # Mocking purchased_products for testing
    mock_purchased_products = [
        {'name': 'Product Alpha (XYZ-123)', 'client_project_product_id': 101},
        {'name': 'Service Beta', 'client_project_product_id': 102},
    ]

    # Mocking ticket_data for testing edit mode
    mock_ticket_data_edit = {
        'ticket_id': 'TICKET-007',
        'client_project_product_id': 101,
        'issue_description': 'The alpha product makes weird noises.',
        'status_id': 1, # Assuming 1 is 'Ouvert' or some existing status_id for SAVTicket
        'assigned_technician_id': None,
        'resolution_details': ''
    }

    app = QApplication(sys.argv)

    # Test new ticket dialog
    # dialog_new = SAVTicketDialog(client_id='CLIENT-001', purchased_products=mock_purchased_products)
    # if dialog_new.exec_() == QDialog.Accepted:
    #     print("New ticket dialog accepted.")
    # else:
    #     print("New ticket dialog cancelled.")

    # Test edit ticket dialog
    # Ensure your db has a status with ID 1 for SAVTicket type, and some team members.
    # Or, mock db_manager calls within the dialog for standalone testing.
    dialog_edit = SAVTicketDialog(client_id='CLIENT-001', purchased_products=mock_purchased_products, ticket_data=mock_ticket_data_edit)
    if dialog_edit.exec_() == QDialog.Accepted:
        print("Edit ticket dialog accepted.")
    else:
        print("Edit ticket dialog cancelled.")

    # sys.exit(app.exec_()) # Comment out to prevent premature exit if run as part of larger script
