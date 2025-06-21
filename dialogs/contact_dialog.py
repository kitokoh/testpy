# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QDialogButtonBox, QMessageBox, QLabel, QCheckBox,
    QScrollArea, QWidget, QGroupBox, QFrame
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
# import db as db_manager # Removed
from controllers.contact_controller import ContactController # Added
import icons_rc # Import for Qt resource file

class ContactDialog(QDialog):
    def __init__(self, client_id=None, contact_data=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.contact_data = contact_data or {}
        self.contact_controller = ContactController() # Added
        self.setWindowTitle(self.tr("Modifier Contact") if self.contact_data and self.contact_data.get('contact_id') else self.tr("Ajouter Contact"))
        self.setMinimumSize(450,300)
        self.setup_ui()
        if self.contact_data: # Ensure form is populated if contact_data is provided
            self.populate_form()


    def _create_icon_label_widget(self,icon_name,label_text):
        widget=QWidget();layout=QHBoxLayout(widget);layout.setContentsMargins(0,0,0,0);layout.setSpacing(5)
        icon_label=QLabel();icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(16,16));layout.addWidget(icon_label);layout.addWidget(QLabel(label_text));return widget

    def setup_ui(self):
        main_layout=QVBoxLayout(self);main_layout.setSpacing(10)
        header_label_text = self.tr("Modifier Détails Contact") if self.contact_data and self.contact_data.get('contact_id') else self.tr("Ajouter Nouveau Contact")
        header_label=QLabel(header_label_text); header_label.setObjectName("dialogHeaderLabel"); main_layout.addWidget(header_label)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        mandatory_group = QGroupBox(self.tr("Informations Principales"))
        form_layout=QFormLayout(mandatory_group);form_layout.setSpacing(8)

        self.name_input=QLineEdit() # Populated by populate_form or direct set
        form_layout.addRow(self._create_icon_label_widget("user",self.tr("Nom Affichage (ou Nom Complet)*:")),self.name_input)

        self.email_input=QLineEdit()
        form_layout.addRow(self._create_icon_label_widget("mail-message-new",self.tr("Email:")),self.email_input)

        self.phone_input=QLineEdit()
        form_layout.addRow(self._create_icon_label_widget("phone",self.tr("Téléphone:")),self.phone_input)

        self.position_input=QLineEdit()
        form_layout.addRow(self._create_icon_label_widget("preferences-desktop-user",self.tr("Poste/Fonction:")),self.position_input)

        # Role in project (specific to client linking context)
        self.role_in_project_input = QLineEdit()
        # This field might only be relevant if self.client_id is present
        # We can hide/show it based on self.client_id if needed, or just leave it always visible
        form_layout.addRow(self._create_icon_label_widget("view-process-tree", self.tr("Rôle dans le projet (si applicable):")), self.role_in_project_input)


        self.primary_check=QCheckBox(self.tr("Contact principal pour le client"))
        self.primary_check.stateChanged.connect(self.update_primary_contact_visuals)
        form_layout.addRow(self._create_icon_label_widget("emblem-important",self.tr("Principal:")),self.primary_check)
        if not self.client_id: # Hide if no client context
            self.primary_check.setVisible(False)
            form_layout.labelForField(self.primary_check).setVisible(False)


        self.can_receive_docs_checkbox = QCheckBox(self.tr("Peut recevoir des documents"))
        form_layout.addRow(self._create_icon_label_widget("document-send", self.tr("Autorisations Docs:")), self.can_receive_docs_checkbox)
        if not self.client_id: # Hide if no client context
            self.can_receive_docs_checkbox.setVisible(False)
            form_layout.labelForField(self.can_receive_docs_checkbox).setVisible(False)


        scroll_layout.addWidget(mandatory_group)

        self.show_optional_fields_checkbox = QCheckBox(self.tr("Afficher les champs optionnels"))
        self.show_optional_fields_checkbox.setChecked(False)
        self.show_optional_fields_checkbox.toggled.connect(self.toggle_optional_fields_visibility)
        scroll_layout.addWidget(self.show_optional_fields_checkbox)

        self.optional_fields_container = QWidget()
        optional_fields_main_layout = QVBoxLayout(self.optional_fields_container)
        optional_fields_main_layout.setContentsMargins(0,0,0,0)

        name_details_group = QGroupBox(self.tr("Noms Détaillés"))
        name_details_form_layout = QFormLayout(name_details_group)
        self.givenName_input = QLineEdit()
        name_details_form_layout.addRow(self.tr("Prénom:"), self.givenName_input)
        self.familyName_input = QLineEdit()
        name_details_form_layout.addRow(self.tr("Nom de famille:"), self.familyName_input)
        self.displayName_input = QLineEdit()
        name_details_form_layout.addRow(self.tr("Nom Affiché (alternatif):"), self.displayName_input)
        optional_fields_main_layout.addWidget(name_details_group)

        contact_types_group = QGroupBox(self.tr("Types Contact"))
        contact_types_form_layout = QFormLayout(contact_types_group)
        self.phone_type_input = QLineEdit()
        contact_types_form_layout.addRow(self.tr("Type téléphone:"), self.phone_type_input)
        self.email_type_input = QLineEdit()
        contact_types_form_layout.addRow(self.tr("Type email:"), self.email_type_input)
        optional_fields_main_layout.addWidget(contact_types_group)

        address_group = QGroupBox(self.tr("Adresse"))
        address_form_layout = QFormLayout(address_group)
        self.address_streetAddress_input = QLineEdit()
        address_form_layout.addRow(self.tr("Rue:"), self.address_streetAddress_input)
        self.address_city_input = QLineEdit()
        address_form_layout.addRow(self.tr("Ville:"), self.address_city_input)
        self.address_region_input = QLineEdit()
        address_form_layout.addRow(self.tr("Région/État:"), self.address_region_input)
        self.address_postalCode_input = QLineEdit()
        address_form_layout.addRow(self.tr("Code Postal:"), self.address_postalCode_input)
        self.address_country_input = QLineEdit()
        address_form_layout.addRow(self.tr("Pays:"), self.address_country_input)
        self.address_formattedValue_input = QLineEdit()
        address_form_layout.addRow(self.tr("Adresse complète (si unique champ):"), self.address_formattedValue_input)
        optional_fields_main_layout.addWidget(address_group)

        org_group = QGroupBox(self.tr("Organisation (Contact)"))
        org_form_layout = QFormLayout(org_group)
        self.contact_company_name_input = QLineEdit()
        org_form_layout.addRow(self.tr("Société (Contact):"), self.contact_company_name_input)
        self.organization_name_input = QLineEdit()
        org_form_layout.addRow(self.tr("Nom Organisation (détaillé):"), self.organization_name_input)
        self.organization_title_input = QLineEdit()
        org_form_layout.addRow(self.tr("Titre dans l'organisation:"), self.organization_title_input)
        optional_fields_main_layout.addWidget(org_group)

        other_details_group = QGroupBox(self.tr("Autres Détails"))
        other_details_form_layout = QFormLayout(other_details_group)
        self.birthday_date_input = QLineEdit()
        self.birthday_date_input.setPlaceholderText(self.tr("AAAA-MM-JJ"))
        other_details_form_layout.addRow(self.tr("Date de naissance:"), self.birthday_date_input)
        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(80)
        other_details_form_layout.addRow(self.tr("Notes (Contact):"), self.notes_input)
        optional_fields_main_layout.addWidget(other_details_group)

        scroll_layout.addWidget(self.optional_fields_container)
        self.optional_fields_container.setVisible(False)

        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        main_layout.addStretch(1)
        button_frame=QFrame(self);button_frame.setObjectName("buttonFrame")
        button_frame_layout=QHBoxLayout(button_frame);button_frame_layout.setContentsMargins(0,0,0,0)
        button_box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        ok_button=button_box.button(QDialogButtonBox.Ok);ok_button.setText(self.tr("OK"));ok_button.setIcon(QIcon(":/icons/dialog-ok-apply.svg"));ok_button.setObjectName("primaryButton")
        cancel_button=button_box.button(QDialogButtonBox.Cancel);cancel_button.setText(self.tr("Annuler"));cancel_button.setIcon(QIcon(":/icons/dialog-cancel.svg"))
        button_box.accepted.connect(self.accept);button_box.rejected.connect(self.reject);button_frame_layout.addWidget(button_box);main_layout.addWidget(button_frame)

        # Populate form after UI is fully set up
        if self.contact_data:
            self.populate_form()
        else: # Default for new contact
            self.can_receive_docs_checkbox.setChecked(True)
            self.primary_check.setChecked(False) # Default to not primary

        self.update_primary_contact_visuals(self.primary_check.checkState())


    def toggle_optional_fields_visibility(self, checked):
        self.optional_fields_container.setVisible(checked)

    def check_and_show_optional_fields(self):
        optional_field_keys = [
            "givenName", "familyName", "displayName",
            "phone_type", "email_type", "company_name", # company_name is contact's own company
            "address_formattedValue", "address_streetAddress", "address_city",
            "address_region", "address_postalCode", "address_country",
            "organization_name", "organization_title", "birthday_date", "notes",
            "role_in_project"
        ]
        show = False
        for key in optional_field_keys:
            if self.contact_data.get(key, "").strip():
                show = True
                break
        if show:
            self.show_optional_fields_checkbox.setChecked(True)


    def populate_form(self):
        self.name_input.setText(self.contact_data.get("name", self.contact_data.get("displayName", "")))
        self.email_input.setText(self.contact_data.get("email",""))
        self.phone_input.setText(self.contact_data.get("phone",""))
        self.position_input.setText(self.contact_data.get("position",""))
        self.role_in_project_input.setText(self.contact_data.get("role_in_project", self.contact_data.get("role", "")))


        if self.client_id: # Only set these if there's a client context
            self.primary_check.setChecked(bool(self.contact_data.get("is_primary_for_client", self.contact_data.get("is_primary",0))))
            self.can_receive_docs_checkbox.setChecked(self.contact_data.get("can_receive_documents", True))
        else: # For global contacts, these might not be directly applicable or default differently
            self.primary_check.setChecked(False) # Default not primary if no client
            self.can_receive_docs_checkbox.setChecked(True) # Default to true for new global contact

        self.givenName_input.setText(self.contact_data.get("givenName", ""))
        self.familyName_input.setText(self.contact_data.get("familyName", ""))
        # If 'name' is empty but givenName and familyName exist, construct 'name'
        if not self.name_input.text() and (self.givenName_input.text() or self.familyName_input.text()):
            self.name_input.setText(f"{self.givenName_input.text()} {self.familyName_input.text()}".strip())

        self.displayName_input.setText(self.contact_data.get("displayName", ""))
        self.phone_type_input.setText(self.contact_data.get("phone_type", ""))
        self.email_type_input.setText(self.contact_data.get("email_type", ""))
        self.contact_company_name_input.setText(self.contact_data.get("company_name", "")) # Contact's own company

        self.address_formattedValue_input.setText(self.contact_data.get("address_formattedValue", ""))
        self.address_streetAddress_input.setText(self.contact_data.get("address_streetAddress", ""))
        self.address_city_input.setText(self.contact_data.get("address_city", ""))
        self.address_region_input.setText(self.contact_data.get("address_region", ""))
        self.address_postalCode_input.setText(self.contact_data.get("address_postalCode", ""))
        self.address_country_input.setText(self.contact_data.get("address_country", ""))

        self.organization_name_input.setText(self.contact_data.get("organization_name", ""))
        self.organization_title_input.setText(self.contact_data.get("organization_title", ""))
        self.birthday_date_input.setText(self.contact_data.get("birthday_date", ""))
        self.notes_input.setPlainText(self.contact_data.get("notes", ""))

        self.check_and_show_optional_fields()
        self.update_primary_contact_visuals(self.primary_check.checkState())


    def update_primary_contact_visuals(self,state):
        if state==Qt.Checked and self.client_id: # Only apply visual if client context
            self.name_input.setStyleSheet("background-color: #E8F5E9;")
        else:
            self.name_input.setStyleSheet("")

    def get_data(self):
        # Core data, always collected
        data = {
            "name": self.name_input.text().strip(),
            "email": self.email_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "position": self.position_input.text().strip(),
            "role_in_project": self.role_in_project_input.text().strip(), # Added
        }
        # Fields specific to client linking context
        if self.client_id:
            data["is_primary_for_client"] = self.primary_check.isChecked() # Boolean
            data["can_receive_documents"] = self.can_receive_docs_checkbox.isChecked() # Boolean

        # Optional fields
        data.update({
            "givenName": self.givenName_input.text().strip(),
            "familyName": self.familyName_input.text().strip(),
            "displayName": self.displayName_input.text().strip(), # Alternative display name
            "phone_type": self.phone_type_input.text().strip(),
            "email_type": self.email_type_input.text().strip(),
            "company_name": self.contact_company_name_input.text().strip(), # Contact's own company
            "address_formattedValue": self.address_formattedValue_input.text().strip(),
            "address_streetAddress": self.address_streetAddress_input.text().strip(),
            "address_city": self.address_city_input.text().strip(),
            "address_region": self.address_region_input.text().strip(),
            "address_postalCode": self.address_postalCode_input.text().strip(),
            "address_country": self.address_country_input.text().strip(),
            "organization_name": self.organization_name_input.text().strip(),
            "organization_title": self.organization_title_input.text().strip(),
            "birthday_date": self.birthday_date_input.text().strip(),
            "notes": self.notes_input.toPlainText().strip(),
        })

        # Ensure 'name' is populated if givenName and familyName are provided but 'name' (main input) is empty
        if not data["name"] and (data["givenName"] or data["familyName"]):
            data["name"] = f"{data['givenName']} {data['familyName']}".strip()
        # If 'displayName' is provided and 'name' is empty, use 'displayName' for 'name'
        elif not data["name"] and data["displayName"]:
             data["name"] = data["displayName"]

        # If contact_id is available (editing existing), include it
        if self.contact_data and self.contact_data.get('contact_id'):
            data['contact_id'] = self.contact_data.get('contact_id')

        return data

    def accept(self):
        contact_form_data = self.get_data() # This now includes contact_id if editing

        if not contact_form_data.get("name"): # Main name (Nom Affichage) is critical
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Le Nom Affichage (ou Nom Complet) du contact est requis."))
            self.name_input.setFocus()
            return

        if not contact_form_data.get("email") and not contact_form_data.get("phone"):
             QMessageBox.warning(self, self.tr("Validation"), self.tr("Au moins un Email ou un Numéro de téléphone est requis."))
             self.email_input.setFocus()
             return


        from main import get_notification_manager # Local import for notifications
        success = False
        action_message = "" # For notification manager

        try:
            if self.client_id: # Dialog is for a specific client context (add/edit contact and link)
                # contact_form_data includes all fields from the dialog
                # The controller's get_or_create_contact_and_link will handle parsing this
                contact_id_linked, link_id = self.contact_controller.get_or_create_contact_and_link(
                    self.client_id,
                    contact_form_data
                )
                if contact_id_linked:
                    success = True
                    action_message = self.tr("Contact traité et lié au client avec succès.")
                    # Store the linked contact_id if needed for further operations by the caller
                    self.contact_data['contact_id'] = contact_id_linked
                    if link_id : self.contact_data['client_contact_link_id'] = link_id
                else:
                    action_message = self.tr("Échec du traitement ou de la liaison du contact avec le client. Veuillez consulter les logs pour plus de détails ou contacter l'administrateur.")

            # Case: Managing a global contact (no client_id context)
            elif contact_form_data.get('contact_id'): # Editing an existing global contact
                contact_id = contact_form_data['contact_id']
                # Prepare data for update (controller will pick relevant fields)
                if self.contact_controller.update_contact(contact_id, contact_form_data):
                    success = True
                    action_message = self.tr("Les détails du contact global ont été mis à jour.")
                else:
                    action_message = self.tr("Impossible de mettre à jour le contact global.")

            else: # Adding a new global contact
                new_contact_id = self.contact_controller.add_contact(contact_form_data)
                if new_contact_id:
                    success = True
                    self.contact_data['contact_id'] = new_contact_id # Store new ID
                    action_message = self.tr("Contact global ajouté avec succès.")
                else:
                    action_message = self.tr("Impossible d'ajouter le contact global.")

        except Exception as e:
            success = False
            action_message = self.tr("Une erreur inattendue est survenue: {0}").format(str(e))
            logging.error(f"Une erreur inattendue est survenue dans ContactDialog.accept(): {type(e).__name__} - {str(e)}", exc_info=True)

        if success:
            get_notification_manager().show(title=self.tr("Opération Contact Réussie"), message=action_message, type='SUCCESS')
            super().accept()
        else:
            get_notification_manager().show(title=self.tr("Erreur Contact"), message=action_message, type='ERROR')
            # Dialog remains open for correction or cancellation
