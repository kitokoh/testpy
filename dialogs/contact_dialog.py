# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QDialogButtonBox, QMessageBox, QLabel, QCheckBox,
    QScrollArea, QWidget, QGroupBox, QFrame
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
import db as db_manager
# from main import get_notification_manager # This will be a local import

class ContactDialog(QDialog):
    def __init__(self, client_id=None, contact_data=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id; self.contact_data = contact_data or {}
        self.setWindowTitle(self.tr("Modifier Contact") if self.contact_data else self.tr("Ajouter Contact"))
        self.setMinimumSize(450,300); # Adjusted initial min height, will grow with optional fields
        self.setup_ui()

    def _create_icon_label_widget(self,icon_name,label_text):
        widget=QWidget();layout=QHBoxLayout(widget);layout.setContentsMargins(0,0,0,0);layout.setSpacing(5)
        icon_label=QLabel();icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(16,16));layout.addWidget(icon_label);layout.addWidget(QLabel(label_text));return widget

    def setup_ui(self):
        main_layout=QVBoxLayout(self);main_layout.setSpacing(10) # Reduced main spacing a bit
        header_label=QLabel(self.tr("Ajouter Nouveau Contact") if not self.contact_data else self.tr("Modifier Détails Contact")); header_label.setObjectName("dialogHeaderLabel"); main_layout.addWidget(header_label)

        # Scroll Area for many fields
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget) # Main layout for scrollable content

        # --- Mandatory Fields ---
        mandatory_group = QGroupBox(self.tr("Informations Principales"))
        form_layout=QFormLayout(mandatory_group);form_layout.setSpacing(8)

        self.name_input=QLineEdit(self.contact_data.get("name", self.contact_data.get("displayName", ""))) # Use displayName as fallback
        form_layout.addRow(self._create_icon_label_widget("user",self.tr("Nom Affichage (ou Nom Complet)*:")),self.name_input)

        self.email_input=QLineEdit(self.contact_data.get("email",""))
        form_layout.addRow(self._create_icon_label_widget("mail-message-new",self.tr("Email:")),self.email_input)

        self.phone_input=QLineEdit(self.contact_data.get("phone",""))
        form_layout.addRow(self._create_icon_label_widget("phone",self.tr("Téléphone:")),self.phone_input)

        self.position_input=QLineEdit(self.contact_data.get("position",""))
        form_layout.addRow(self._create_icon_label_widget("preferences-desktop-user",self.tr("Poste/Fonction:")),self.position_input)

        self.primary_check=QCheckBox(self.tr("Contact principal pour le client"))
        self.primary_check.setChecked(bool(self.contact_data.get("is_primary_for_client", self.contact_data.get("is_primary",0))))
        self.primary_check.stateChanged.connect(self.update_primary_contact_visuals)
        form_layout.addRow(self._create_icon_label_widget("emblem-important",self.tr("Principal:")),self.primary_check)

        self.can_receive_docs_checkbox = QCheckBox(self.tr("Peut recevoir des documents"))
        self.can_receive_docs_checkbox.setChecked(self.contact_data.get("can_receive_documents", True)) # Default true
        form_layout.addRow(self._create_icon_label_widget("document-send", self.tr("Autorisations Docs:")), self.can_receive_docs_checkbox)

        scroll_layout.addWidget(mandatory_group)

        # --- "Show Optional Fields" Checkbox ---
        self.show_optional_fields_checkbox = QCheckBox(self.tr("Afficher les champs optionnels"))
        self.show_optional_fields_checkbox.setChecked(False) # Default to hidden
        self.show_optional_fields_checkbox.toggled.connect(self.toggle_optional_fields_visibility)
        scroll_layout.addWidget(self.show_optional_fields_checkbox)

        # --- Optional Fields GroupBox ---
        self.optional_fields_container = QWidget() # Container for all optional groups
        optional_fields_main_layout = QVBoxLayout(self.optional_fields_container)
        optional_fields_main_layout.setContentsMargins(0,0,0,0)

        # Optional: Detailed Name parts
        name_details_group = QGroupBox(self.tr("Noms Détaillés"))
        name_details_form_layout = QFormLayout(name_details_group)
        self.givenName_input = QLineEdit(self.contact_data.get("givenName", ""))
        name_details_form_layout.addRow(self.tr("Prénom:"), self.givenName_input)
        self.familyName_input = QLineEdit(self.contact_data.get("familyName", ""))
        name_details_form_layout.addRow(self.tr("Nom de famille:"), self.familyName_input)
        self.displayName_input = QLineEdit(self.contact_data.get("displayName", "")) # If different from 'name'
        name_details_form_layout.addRow(self.tr("Nom Affiché (alternatif):"), self.displayName_input)
        optional_fields_main_layout.addWidget(name_details_group)

        # Optional: Contact Types
        contact_types_group = QGroupBox(self.tr("Types Contact"))
        contact_types_form_layout = QFormLayout(contact_types_group)
        self.phone_type_input = QLineEdit(self.contact_data.get("phone_type", ""))
        contact_types_form_layout.addRow(self.tr("Type téléphone:"), self.phone_type_input)
        self.email_type_input = QLineEdit(self.contact_data.get("email_type", ""))
        contact_types_form_layout.addRow(self.tr("Type email:"), self.email_type_input)
        optional_fields_main_layout.addWidget(contact_types_group)

        # Optional: Address
        address_group = QGroupBox(self.tr("Adresse"))
        address_form_layout = QFormLayout(address_group)
        self.address_streetAddress_input = QLineEdit(self.contact_data.get("address_streetAddress", ""))
        address_form_layout.addRow(self.tr("Rue:"), self.address_streetAddress_input)
        self.address_city_input = QLineEdit(self.contact_data.get("address_city", ""))
        address_form_layout.addRow(self.tr("Ville:"), self.address_city_input)
        self.address_region_input = QLineEdit(self.contact_data.get("address_region", ""))
        address_form_layout.addRow(self.tr("Région/État:"), self.address_region_input)
        self.address_postalCode_input = QLineEdit(self.contact_data.get("address_postalCode", ""))
        address_form_layout.addRow(self.tr("Code Postal:"), self.address_postalCode_input)
        self.address_country_input = QLineEdit(self.contact_data.get("address_country", ""))
        address_form_layout.addRow(self.tr("Pays:"), self.address_country_input)
        self.address_formattedValue_input = QLineEdit(self.contact_data.get("address_formattedValue", ""))
        address_form_layout.addRow(self.tr("Adresse complète (si unique champ):"), self.address_formattedValue_input)
        optional_fields_main_layout.addWidget(address_group)

        # Optional: Organization
        org_group = QGroupBox(self.tr("Organisation (Contact)"))
        org_form_layout = QFormLayout(org_group)
        self.contact_company_name_input = QLineEdit(self.contact_data.get("company_name", "")) # Contact's specific company
        org_form_layout.addRow(self.tr("Société (Contact):"), self.contact_company_name_input)
        self.organization_name_input = QLineEdit(self.contact_data.get("organization_name", ""))
        org_form_layout.addRow(self.tr("Nom Organisation (détaillé):"), self.organization_name_input)
        self.organization_title_input = QLineEdit(self.contact_data.get("organization_title", ""))
        org_form_layout.addRow(self.tr("Titre dans l'organisation:"), self.organization_title_input)
        optional_fields_main_layout.addWidget(org_group)

        # Optional: Other Details
        other_details_group = QGroupBox(self.tr("Autres Détails"))
        other_details_form_layout = QFormLayout(other_details_group)
        self.birthday_date_input = QLineEdit(self.contact_data.get("birthday_date", ""))
        self.birthday_date_input.setPlaceholderText(self.tr("AAAA-MM-JJ"))
        other_details_form_layout.addRow(self.tr("Date de naissance:"), self.birthday_date_input)
        self.notes_input = QTextEdit(self.contact_data.get("notes", ""))
        self.notes_input.setFixedHeight(80)
        other_details_form_layout.addRow(self.tr("Notes (Contact):"), self.notes_input)
        optional_fields_main_layout.addWidget(other_details_group)

        scroll_layout.addWidget(self.optional_fields_container)
        self.optional_fields_container.setVisible(False) # Initially hidden

        scroll_area.setWidget(scroll_widget) # Set the widget containing the form layout into the scroll area
        main_layout.addWidget(scroll_area) # Add scroll area to main layout

        # Auto-check "Show Optional Fields" if any optional data exists
        self.check_and_show_optional_fields()
        self.update_primary_contact_visuals(self.primary_check.checkState()) # Initial visual state for primary contact

        main_layout.addStretch(1) # Add stretch after scroll area
        button_frame=QFrame(self);button_frame.setObjectName("buttonFrame")
        button_frame_layout=QHBoxLayout(button_frame);button_frame_layout.setContentsMargins(0,0,0,0)
        button_box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        ok_button=button_box.button(QDialogButtonBox.Ok);ok_button.setText(self.tr("OK"));ok_button.setIcon(QIcon(":/icons/dialog-ok-apply.svg"));ok_button.setObjectName("primaryButton")
        cancel_button=button_box.button(QDialogButtonBox.Cancel);cancel_button.setText(self.tr("Annuler"));cancel_button.setIcon(QIcon(":/icons/dialog-cancel.svg"))
        button_box.accepted.connect(self.accept);button_box.rejected.connect(self.reject);button_frame_layout.addWidget(button_box);main_layout.addWidget(button_frame)
        self.update_primary_contact_visuals(self.primary_check.checkState())

    def toggle_optional_fields_visibility(self, checked):
        self.optional_fields_container.setVisible(checked)

    def check_and_show_optional_fields(self):
        optional_field_keys = [
            "givenName", "familyName", "displayName",
            "phone_type", "email_type", "company_name",
            "address_formattedValue", "address_streetAddress", "address_city",
            "address_region", "address_postalCode", "address_country",
            "organization_name", "organization_title", "birthday_date", "notes"
        ]
        show = False
        for key in optional_field_keys:
            if self.contact_data.get(key, "").strip():
                show = True
                break
        if show:
            self.show_optional_fields_checkbox.setChecked(True)

    def populate_form(self): # Added to populate all fields
        self.name_input.setText(self.contact_data.get("name", self.contact_data.get("displayName", "")))
        self.email_input.setText(self.contact_data.get("email",""))
        self.phone_input.setText(self.contact_data.get("phone",""))
        self.position_input.setText(self.contact_data.get("position",""))
        self.primary_check.setChecked(bool(self.contact_data.get("is_primary_for_client", self.contact_data.get("is_primary",0))))
        self.can_receive_docs_checkbox.setChecked(self.contact_data.get("can_receive_documents", True))

        self.givenName_input.setText(self.contact_data.get("givenName", ""))
        self.familyName_input.setText(self.contact_data.get("familyName", ""))
        self.displayName_input.setText(self.contact_data.get("displayName", ""))
        self.phone_type_input.setText(self.contact_data.get("phone_type", ""))
        self.email_type_input.setText(self.contact_data.get("email_type", ""))
        self.contact_company_name_input.setText(self.contact_data.get("company_name", ""))

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
        if state==Qt.Checked:
            self.name_input.setStyleSheet("background-color: #E8F5E9;")
        else:
            self.name_input.setStyleSheet("")

    def get_data(self):
        data = {
            "name": self.name_input.text().strip(),
            "email": self.email_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "position": self.position_input.text().strip(),
            "is_primary_for_client": 1 if self.primary_check.isChecked() else 0,
            "can_receive_documents": self.can_receive_docs_checkbox.isChecked(),
        }
        data.update({
            "givenName": self.givenName_input.text().strip(),
            "familyName": self.familyName_input.text().strip(),
            "displayName": self.displayName_input.text().strip(),
            "phone_type": self.phone_type_input.text().strip(),
            "email_type": self.email_type_input.text().strip(),
            "company_name": self.contact_company_name_input.text().strip(),
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

        final_name_for_db = self.name_input.text().strip()
        optional_display_name = self.displayName_input.text().strip()
        if not final_name_for_db and optional_display_name:
            data["name"] = optional_display_name
        return data

    def accept(self):
        contact_details_to_save = self.get_data()
        if not contact_details_to_save.get("name"):
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Le Nom Affichage (ou Nom Complet) du contact est requis."))
            self.name_input.setFocus()
            return

        is_primary_from_form = bool(contact_details_to_save.get("is_primary_for_client", False))
        can_receive_docs_from_form = bool(contact_details_to_save.get("can_receive_documents", True))

        from main import get_notification_manager # Local import

        if self.contact_data and self.contact_data.get('contact_id'): # Editing existing contact
            central_contact_id = self.contact_data['contact_id']
            success_central_update = db_manager.update_contact(central_contact_id, contact_details_to_save)

            if success_central_update:
                if self.client_id:
                    link_details = db_manager.get_specific_client_contact_link_details(self.client_id, central_contact_id)
                    if link_details:
                        client_contact_link_id = link_details['client_contact_id']
                        update_link_payload = {
                            'is_primary_for_client': is_primary_from_form,
                            'can_receive_documents': can_receive_docs_from_form
                        }
                        db_manager.update_client_contact_link(client_contact_link_id, update_link_payload)
                get_notification_manager().show(title=self.tr("Contact Mis à Jour"), message=self.tr("Les détails du contact ont été mis à jour."), type='SUCCESS')
                super().accept()
            else:
                get_notification_manager().show(title=self.tr("Erreur Contact"), message=self.tr("Impossible de mettre à jour le contact."), type='ERROR')
                return
        else: # Adding new contact
            central_contact_payload = {k: v for k, v in contact_details_to_save.items() if k not in ['is_primary_for_client', 'can_receive_documents']}
            new_central_contact_id = db_manager.add_contact(central_contact_payload)

            if new_central_contact_id and self.client_id:
                link_id = db_manager.link_contact_to_client(
                    self.client_id, new_central_contact_id,
                    is_primary=is_primary_from_form, can_receive_documents=can_receive_docs_from_form
                )
                if link_id:
                    contact_count = db_manager.get_contacts_for_client_count(self.client_id)
                    if contact_count == 1:
                        db_manager.update_client_contact_link(link_id, {'is_primary_for_client': True, 'can_receive_documents': True})
                    get_notification_manager().show(title=self.tr("Contact Ajouté"), message=self.tr("Contact ajouté et lié au client avec succès."), type='SUCCESS')
                    super().accept()
                else:
                     get_notification_manager().show(title=self.tr("Erreur Liaison Contact"), message=self.tr("Contact ajouté mais échec de la liaison avec le client."), type='WARNING')
                     return
            elif new_central_contact_id:
                get_notification_manager().show(title=self.tr("Contact Ajouté"), message=self.tr("Contact ajouté avec succès (non lié à un client)."), type='SUCCESS')
                super().accept()
            else:
                get_notification_manager().show(title=self.tr("Erreur Contact"), message=self.tr("Impossible d'ajouter le contact."), type='ERROR')
                return
