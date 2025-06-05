# -*- coding: utf-8 -*-
import sys
import os
import json
import db as db_manager
from db import DATABASE_NAME as CENTRAL_DATABASE_NAME
import pandas as pd
import shutil # For DocumentManager.delete_client_permanently and main_app_entry_point template copying

from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget,
    QFileDialog, QMessageBox, QDialog, QFormLayout, QComboBox,
    QDialogButtonBox, QInputDialog, QSplitter,
    QCompleter, QTabWidget, QAction, QMenu, QGroupBox,
    QCheckBox, QDateEdit, QSpinBox, QStackedWidget, QListWidgetItem,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QGridLayout
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QColor
from PyQt5.QtCore import Qt, QUrl, QTimer, QLocale, QLibraryInfo, QCoreApplication # QStandardPaths removed as get_config_dir is no longer here
from PyQt5.QtWidgets import QDoubleSpinBox

from projectManagement import MainDashboard as ProjectManagementDashboard
from gui_components import ClientWidget, TemplateDialog
from app_config import (
    CONFIG, APP_ROOT_DIR, save_config, # load_config no longer needed here
    SPEC_TECH_TEMPLATE_NAME, PROFORMA_TEMPLATE_NAME,
    CONTRAT_VENTE_TEMPLATE_NAME, PACKING_LISTE_TEMPLATE_NAME
)

# --- Database Initialization ---
# DATABASE_NAME is imported from db.py as CENTRAL_DATABASE_NAME and used by db_manager
# CENTRAL_DATABASE_NAME is used directly by db_manager.initialize_database() if needed, or db.py handles its own name.
db_manager.initialize_database()

#Removed CONFIG_DIR_NAME, CONFIG_FILE_NAME, TEMPLATES_SUBDIR, CLIENTS_SUBDIR
#Removed SPEC_TECH_TEMPLATE_NAME, PROFORMA_TEMPLATE_NAME, CONTRAT_VENTE_TEMPLATE_NAME, PACKING_LISTE_TEMPLATE_NAME (imported)
#Removed APP_ROOT_DIR, DEFAULT_TEMPLATES_DIR, DEFAULT_CLIENTS_DIR (imported or handled by app_config)
#Removed get_config_dir(), get_config_file_path(), load_config(), save_config() (imported or handled by app_config)
#Removed CONFIG = load_config() (imported)
#Removed os.makedirs calls (handled by app_config)

class StatisticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self); layout.setContentsMargins(10, 5, 10, 5)
        stat_items_data = [
            (self.tr("Clients Totaux"), "total_label", "0", None),
            (self.tr("Valeur Totale"), "value_label", "0 €", None),
            (self.tr("Projets en Cours"), "ongoing_label", "0", None),
            (self.tr("Projets Urgents"), "urgent_label", "0", "color: #e74c3c;")
        ]
        for title, attr_name, default_text, style in stat_items_data:
            group = QGroupBox(title); group_layout = QVBoxLayout(group)
            label = QLabel(default_text)
            label.setFont(QFont("Arial", 16, QFont.Bold)); label.setAlignment(Qt.AlignCenter)
            if style: label.setStyleSheet(style)
            setattr(self, attr_name, label)
            group_layout.addWidget(label); layout.addWidget(group)

    def update_stats(self):
        try:
            all_clients = db_manager.get_all_clients()
            if all_clients is None: all_clients = []
            total_clients = len(all_clients)
            self.total_label.setText(str(total_clients))
            total_val = sum(c.get('price', 0) for c in all_clients if c.get('price') is not None)
            self.value_label.setText(f"{total_val:,.2f} €")
            status_en_cours_obj = db_manager.get_status_setting_by_name('En cours', 'Client')
            status_en_cours_id = status_en_cours_obj['status_id'] if status_en_cours_obj else None
            status_urgent_obj = db_manager.get_status_setting_by_name('Urgent', 'Client')
            status_urgent_id = status_urgent_obj['status_id'] if status_urgent_obj else None
            ongoing_count = 0
            if status_en_cours_id is not None:
                ongoing_count = sum(1 for c in all_clients if c.get('status_id') == status_en_cours_id)
            self.ongoing_label.setText(str(ongoing_count))
            urgent_count = 0
            if status_urgent_id is not None:
                urgent_count = sum(1 for c in all_clients if c.get('status_id') == status_urgent_id)
            self.urgent_label.setText(str(urgent_count))
        except Exception as e:
            print(f"Erreur de mise à jour des statistiques: {str(e)}")

class StatusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        status_name_for_delegate = index.data(Qt.UserRole)
        bg_color_hex = "#95a5a6"
        if status_name_for_delegate:
            try:
                status_setting = db_manager.get_status_setting_by_name(status_name_for_delegate, 'Client')
                if status_setting and status_setting.get('color_hex'):
                    bg_color_hex = status_setting['color_hex']
            except Exception as e:
                print(f"Error fetching status color for delegate: {e}")
        painter.save()
        painter.fillRect(option.rect, QColor(bg_color_hex))
        bg_qcolor = QColor(bg_color_hex)
        text_qcolor = QColor(Qt.black)
        if bg_qcolor.lightnessF() < 0.5:
            text_qcolor = QColor(Qt.white)
        painter.setPen(text_qcolor)
        text_rect = option.rect.adjusted(5, 0, -5, 0)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, index.data(Qt.DisplayRole))
        painter.restore()

class DocumentManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Gestionnaire de Documents Client")); self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon.fromTheme("folder-documents"))
        self.config = CONFIG
        self.clients_data_map = {}
        self.setup_ui_main()
        self.project_management_widget_instance = ProjectManagementDashboard(parent=self, current_user=None)
        self.main_area_stack.addWidget(self.project_management_widget_instance)
        self.main_area_stack.setCurrentWidget(self.documents_page_widget)
        self.create_actions_main()
        self.create_menus_main()
        self.load_clients_from_db()
        self.stats_widget.update_stats()
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_old_clients_routine)
        self.check_timer.start(3600000)

    def setup_ui_main(self):
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget); main_layout.setContentsMargins(10,10,10,10); main_layout.setSpacing(10)
        self.stats_widget = StatisticsWidget(); main_layout.addWidget(self.stats_widget)
        self.main_area_stack = QStackedWidget()
        main_layout.addWidget(self.main_area_stack)
        self.documents_page_widget = QWidget()
        content_layout = QHBoxLayout(self.documents_page_widget)
        left_panel = QWidget(); left_layout = QVBoxLayout(left_panel); left_layout.setContentsMargins(5,5,5,5)
        filter_search_layout = QHBoxLayout()
        self.status_filter_combo = QComboBox(); self.status_filter_combo.addItem(self.tr("Tous les statuts"))
        self.load_statuses_into_filter_combo()
        self.status_filter_combo.currentIndexChanged.connect(self.filter_client_list_display)
        filter_search_layout.addWidget(QLabel(self.tr("Filtrer par statut:")))
        filter_search_layout.addWidget(self.status_filter_combo)
        self.search_input_field = QLineEdit(); self.search_input_field.setPlaceholderText(self.tr("Rechercher client..."))
        self.search_input_field.textChanged.connect(self.filter_client_list_display)
        filter_search_layout.addWidget(self.search_input_field); left_layout.addLayout(filter_search_layout)
        self.client_list_widget = QListWidget(); self.client_list_widget.setAlternatingRowColors(True)
        self.client_list_widget.setItemDelegate(StatusDelegate(self.client_list_widget))
        self.client_list_widget.itemClicked.connect(self.handle_client_list_click)
        self.client_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.client_list_widget.customContextMenuRequested.connect(self.show_client_context_menu)
        left_layout.addWidget(self.client_list_widget)
        form_group_box = QGroupBox(self.tr("Ajouter un Nouveau Client")); form_vbox_layout = QVBoxLayout(form_group_box)
        creation_form_layout = QFormLayout(); creation_form_layout.setLabelAlignment(Qt.AlignRight)
        self.client_name_input = QLineEdit(); self.client_name_input.setPlaceholderText(self.tr("Nom du client"))
        creation_form_layout.addRow(self.tr("Nom Client:"), self.client_name_input)
        self.company_name_input = QLineEdit(); self.company_name_input.setPlaceholderText(self.tr("Nom entreprise (optionnel)"))
        creation_form_layout.addRow(self.tr("Nom Entreprise:"), self.company_name_input)
        self.client_need_input = QLineEdit(); self.client_need_input.setPlaceholderText(self.tr("Besoin principal du client"))
        creation_form_layout.addRow(self.tr("Besoin Client:"), self.client_need_input)
        country_hbox_layout = QHBoxLayout(); self.country_select_combo = QComboBox()
        self.country_select_combo.setEditable(True); self.country_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.country_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.country_select_combo.completer().setFilterMode(Qt.MatchContains)
        self.country_select_combo.currentTextChanged.connect(self.load_cities_for_country)
        country_hbox_layout.addWidget(self.country_select_combo)
        self.add_country_button = QPushButton("+"); self.add_country_button.setFixedSize(30,30)
        self.add_country_button.setToolTip(self.tr("Ajouter un nouveau pays"))
        self.add_country_button.clicked.connect(self.add_new_country_dialog)
        country_hbox_layout.addWidget(self.add_country_button); creation_form_layout.addRow(self.tr("Pays Client:"), country_hbox_layout)
        city_hbox_layout = QHBoxLayout(); self.city_select_combo = QComboBox()
        self.city_select_combo.setEditable(True); self.city_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.city_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.city_select_combo.completer().setFilterMode(Qt.MatchContains)
        city_hbox_layout.addWidget(self.city_select_combo)
        self.add_city_button = QPushButton("+"); self.add_city_button.setFixedSize(30,30)
        self.add_city_button.setToolTip(self.tr("Ajouter une nouvelle ville"))
        self.add_city_button.clicked.connect(self.add_new_city_dialog)
        city_hbox_layout.addWidget(self.add_city_button); creation_form_layout.addRow(self.tr("Ville Client:"), city_hbox_layout)
        self.project_id_input_field = QLineEdit(); self.project_id_input_field.setPlaceholderText(self.tr("Identifiant unique du projet"))
        creation_form_layout.addRow(self.tr("ID Projet:"), self.project_id_input_field)
        self.final_price_input = QDoubleSpinBox(); self.final_price_input.setPrefix("€ ")
        self.final_price_input.setRange(0, 10000000); self.final_price_input.setValue(0)
        creation_form_layout.addRow(self.tr("Prix Final:"), self.final_price_input)
        self.language_select_combo = QComboBox()
        self.language_select_combo.addItems([self.tr("Français uniquement (fr)"), self.tr("Arabe uniquement (ar)"), self.tr("Turc uniquement (tr)"), self.tr("Toutes les langues (fr, ar, tr)")])
        creation_form_layout.addRow(self.tr("Langues:"), self.language_select_combo)
        self.create_client_button = QPushButton(self.tr("Créer Client")); self.create_client_button.setIcon(QIcon.fromTheme("list-add"))
        self.create_client_button.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 10px; border-radius: 5px; } QPushButton:hover { background-color: #2ecc71; }")
        self.create_client_button.clicked.connect(self.execute_create_client)
        creation_form_layout.addRow(self.create_client_button)
        form_vbox_layout.addLayout(creation_form_layout); left_layout.addWidget(form_group_box)
        content_layout.addWidget(left_panel, 1)
        self.client_tabs_widget = QTabWidget(); self.client_tabs_widget.setTabsClosable(True)
        self.client_tabs_widget.tabCloseRequested.connect(self.close_client_tab)
        content_layout.addWidget(self.client_tabs_widget, 2)
        self.main_area_stack.addWidget(self.documents_page_widget)
        self.load_countries_into_combo()

    def create_actions_main(self):
        self.settings_action = QAction(self.tr("Paramètres"), self); self.settings_action.triggered.connect(self.open_settings_dialog)
        self.template_action = QAction(self.tr("Gérer les Modèles"), self); self.template_action.triggered.connect(self.open_template_manager_dialog)
        self.status_action = QAction(self.tr("Gérer les Statuts"), self); self.status_action.triggered.connect(self.open_status_manager_dialog)
        self.exit_action = QAction(self.tr("Quitter"), self); self.exit_action.setShortcut("Ctrl+Q"); self.exit_action.triggered.connect(self.close)
        self.project_management_action = QAction(QIcon.fromTheme("preferences-system"), self.tr("Gestion de Projet"), self)
        self.project_management_action.triggered.connect(self.show_project_management_view)
        self.documents_view_action = QAction(QIcon.fromTheme("folder-documents"), self.tr("Gestion Documents"), self)
        self.documents_view_action.triggered.connect(self.show_documents_view)

    def create_menus_main(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu(self.tr("Fichier"))
        file_menu.addAction(self.settings_action); file_menu.addAction(self.template_action); file_menu.addAction(self.status_action)
        file_menu.addSeparator(); file_menu.addAction(self.exit_action)
        modules_menu = menu_bar.addMenu(self.tr("Modules"))
        modules_menu.addAction(self.documents_view_action)
        modules_menu.addAction(self.project_management_action)
        help_menu = menu_bar.addMenu(self.tr("Aide"))
        about_action = QAction(self.tr("À propos"), self); about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_project_management_view(self):
        self.main_area_stack.setCurrentWidget(self.project_management_widget_instance)

    def show_documents_view(self):
        self.main_area_stack.setCurrentWidget(self.documents_page_widget)

    def show_about_dialog(self):
        QMessageBox.about(self, self.tr("À propos"), self.tr("<b>Gestionnaire de Documents Client</b><br><br>Version 4.0<br>Application de gestion de documents clients avec templates Excel.<br><br>Développé par Saadiya Management (Concept)"))

    def load_countries_into_combo(self):
        self.country_select_combo.clear()
        try:
            countries = db_manager.get_all_countries()
            if countries is None: countries = []
            for country_dict in countries:
                self.country_select_combo.addItem(country_dict['country_name'], country_dict.get('country_id'))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des pays:
{0}").format(str(e)))

    def load_cities_for_country(self, country_name_str):
        self.city_select_combo.clear()
        if not country_name_str: return
        selected_country_id = self.country_select_combo.currentData()
        if selected_country_id is None:
            country_obj = db_manager.get_country_by_name(country_name_str)
            if country_obj: selected_country_id = country_obj['country_id']
            else: return
        try:
            cities = db_manager.get_all_cities(country_id=selected_country_id)
            if cities is None: cities = []
            for city_dict in cities:
                self.city_select_combo.addItem(city_dict['city_name'], city_dict.get('city_id'))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des villes:
{0}").format(str(e)))

    def add_new_country_dialog(self):
        country_text, ok = QInputDialog.getText(self, self.tr("Nouveau Pays"), self.tr("Entrez le nom du nouveau pays:"))
        if ok and country_text.strip():
            try:
                new_country_obj = db_manager.add_country({'country_name': country_text.strip()})
                if new_country_obj and new_country_obj.get('country_id'):
                    self.load_countries_into_combo()
                    index = self.country_select_combo.findText(country_text.strip())
                    if index >= 0: self.country_select_combo.setCurrentIndex(index)
                elif db_manager.get_country_by_name(country_text.strip()):
                     QMessageBox.warning(self, self.tr("Pays Existant"), self.tr("Ce pays existe déjà."))
                     index = self.country_select_combo.findText(country_text.strip())
                     if index >=0: self.country_select_combo.setCurrentIndex(index)
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du pays. Vérifiez les logs."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du pays:
{0}").format(str(e)))

    def add_new_city_dialog(self):
        current_country_name = self.country_select_combo.currentText()
        current_country_id = self.country_select_combo.currentData()
        if not current_country_id:
            QMessageBox.warning(self, self.tr("Pays Requis"), self.tr("Veuillez d'abord sélectionner un pays valide.")); return
        city_text, ok = QInputDialog.getText(self, self.tr("Nouvelle Ville"), self.tr("Entrez le nom de la nouvelle ville pour {0}:").format(current_country_name))
        if ok and city_text.strip():
            try:
                city_data = {'country_id': current_country_id, 'city_name': city_text.strip()}
                new_city_obj = db_manager.add_city(city_data)
                if new_city_obj and new_city_obj.get('city_id'):
                    self.load_cities_for_country(current_country_name)
                    index = self.city_select_combo.findText(city_text.strip())
                    if index >= 0: self.city_select_combo.setCurrentIndex(index)
                elif db_manager.get_city_by_name_and_country_id(city_text.strip(), current_country_id):
                     QMessageBox.warning(self, self.tr("Ville Existante"), self.tr("Cette ville existe déjà pour ce pays."))
                     index = self.city_select_combo.findText(city_text.strip())
                     if index >=0: self.city_select_combo.setCurrentIndex(index)
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout de la ville. Vérifiez les logs."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout de la ville:
{0}").format(str(e)))

    def execute_create_client(self):

        client_name_val = self.client_name_input.text().strip()
        company_name_val = self.company_name_input.text().strip()
        need_val = self.client_need_input.text().strip()
        country_id_val = self.country_select_combo.currentData()
        country_name_for_folder = self.country_select_combo.currentText().strip()
        city_id_val = self.city_select_combo.currentData()
        project_identifier_val = self.project_id_input_field.text().strip()
        price_val = self.final_price_input.value()
        lang_option_text = self.language_select_combo.currentText()

        if not client_name_val or not country_id_val or not project_identifier_val:
            QMessageBox.warning(self, self.tr("Champs Requis"), self.tr("Nom client, Pays et ID Projet sont obligatoires.")); return

        lang_map_from_display = {
            self.tr("Français uniquement (fr)"): ["fr"], self.tr("Arabe uniquement (ar)"): ["ar"],
            self.tr("Turc uniquement (tr)"): ["tr"], self.tr("Toutes les langues (fr, ar, tr)"): ["fr", "ar", "tr"]
        }
        selected_langs_list = lang_map_from_display.get(lang_option_text, ["fr"])
        folder_name_str = f"{client_name_val}_{country_name_for_folder}_{project_identifier_val}".replace(" ", "_").replace("/", "-")
        base_folder_full_path = os.path.join(self.config["clients_dir"], folder_name_str)

        if os.path.exists(base_folder_full_path):
            QMessageBox.warning(self, self.tr("Dossier Existant"), self.tr("Un dossier client avec un chemin similaire existe déjà. Veuillez vérifier les détails ou choisir un ID Projet différent."))
            return

        default_status_name = "En cours"
        status_setting_obj = db_manager.get_status_setting_by_name(default_status_name, 'Client')
        if not status_setting_obj or not status_setting_obj.get('status_id'):
            QMessageBox.critical(self, self.tr("Erreur Configuration"), self.tr("Statut par défaut '{0}' non trouvé pour les clients. Veuillez configurer les statuts.").format(default_status_name))
            return
        default_status_id = status_setting_obj['status_id']

        client_data_for_db = {
            'client_name': client_name_val, 'company_name': company_name_val if company_name_val else None,
            'primary_need_description': need_val, 'project_identifier': project_identifier_val,
            'country_id': country_id_val, 'city_id': city_id_val if city_id_val else None,
            'default_base_folder_path': base_folder_full_path, 'selected_languages': ",".join(selected_langs_list),
            'price': price_val, 'status_id': default_status_id, 'category': 'Standard', 'notes': '',
        }
        actual_new_client_id = None
        new_project_id_central_db = None
        try:
            actual_new_client_id = db_manager.add_client(client_data_for_db)
            if not actual_new_client_id:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de créer le client. L'ID de projet ou le chemin du dossier existe peut-être déjà, ou autre erreur de contrainte DB."))
                return
            os.makedirs(base_folder_full_path, exist_ok=True)
            for lang_code in selected_langs_list:
                os.makedirs(os.path.join(base_folder_full_path, lang_code), exist_ok=True)

            project_status_planning_obj = db_manager.get_status_setting_by_name("Planning", "Project")
            project_status_id_for_pm = project_status_planning_obj['status_id'] if project_status_planning_obj else None
            if not project_status_id_for_pm:
                 QMessageBox.warning(self, self.tr("Erreur Configuration Projet"), self.tr("Statut de projet par défaut 'Planning' non trouvé. Le projet ne sera pas créé avec un statut initial."))
            project_data_for_db = {
                'client_id': actual_new_client_id, 'project_name': f"Projet pour {client_name_val}",
                'description': f"Projet pour client: {client_name_val}. Besoin initial: {need_val}",
                'start_date': datetime.now().strftime("%Y-%m-%d"), 'deadline_date': (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
                'budget': 0.0, 'status_id': project_status_id_for_pm, 'priority': 1
            }
            new_project_id_central_db = db_manager.add_project(project_data_for_db)
            if new_project_id_central_db:
                QMessageBox.information(self, self.tr("Projet Créé (Central DB)"), self.tr("Un projet associé a été créé dans la base de données centrale pour {0}.").format(client_name_val))
                task_status_todo_obj = db_manager.get_status_setting_by_name("To Do", "Task")
                task_status_id_for_todo = task_status_todo_obj['status_id'] if task_status_todo_obj else None
                if not task_status_id_for_todo:
                    QMessageBox.warning(self, self.tr("Erreur Configuration Tâche"), self.tr("Statut de tâche par défaut 'To Do' non trouvé. Les tâches standard ne seront pas créées avec un statut initial."))
                standard_tasks = [
                    {"name": "Initial Client Consultation & Needs Assessment", "description": "Understand client requirements, objectives, target markets, and budget.", "priority_val": 2, "deadline_days": 3},
                    {"name": "Market Research & Analysis", "description": "Research target international markets, including competition, regulations, and cultural nuances.", "priority_val": 1, "deadline_days": 7},
                    {"name": "Post-Sales Follow-up & Support", "description": "Follow up with the client after delivery.", "priority_val": 1, "deadline_days": 60}
                ]
                for task_item in standard_tasks:
                    task_deadline = (datetime.now() + timedelta(days=task_item["deadline_days"])).strftime("%Y-%m-%d")
                    db_manager.add_task({
                        'project_id': new_project_id_central_db, 'task_name': task_item["name"],
                        'description': task_item["description"], 'status_id': task_status_id_for_todo,
                        'priority': task_item["priority_val"], 'due_date': task_deadline
                    })
                QMessageBox.information(self, self.tr("Tâches Créées (Central DB)"), self.tr("Des tâches standard ont été ajoutées au projet pour {0}.").format(client_name_val))
            else:
                QMessageBox.warning(self, self.tr("Erreur DB Projet"), self.tr("Le client a été créé, mais la création du projet associé dans la base de données centrale a échoué."))

            client_dict_from_db = db_manager.get_client_by_id(actual_new_client_id)
            if client_dict_from_db:
                country_obj = db_manager.get_country_by_id(client_dict_from_db.get('country_id')) if client_dict_from_db.get('country_id') else None
                city_obj = db_manager.get_city_by_id(client_dict_from_db.get('city_id')) if client_dict_from_db.get('city_id') else None
                status_obj = db_manager.get_status_setting_by_id(client_dict_from_db.get('status_id')) if client_dict_from_db.get('status_id') else None
                ui_map_data = {
                    "client_id": client_dict_from_db.get('client_id'), "client_name": client_dict_from_db.get('client_name'),
                    "company_name": client_dict_from_db.get('company_name'), "need": client_dict_from_db.get('primary_need_description'),
                    "country": country_obj['country_name'] if country_obj else "N/A", "country_id": client_dict_from_db.get('country_id'),
                    "city": city_obj['city_name'] if city_obj else "N/A", "city_id": client_dict_from_db.get('city_id'),
                    "project_identifier": client_dict_from_db.get('project_identifier'),
                    "base_folder_path": client_dict_from_db.get('default_base_folder_path'),
                    "selected_languages": client_dict_from_db.get('selected_languages','').split(',') if client_dict_from_db.get('selected_languages') else [],
                    "price": client_dict_from_db.get('price'), "notes": client_dict_from_db.get('notes'),
                    "status": status_obj['status_name'] if status_obj else "N/A", "status_id": client_dict_from_db.get('status_id'),
                    "creation_date": client_dict_from_db.get('created_at','').split("T")[0] if client_dict_from_db.get('created_at') else "N/A",
                    "category": client_dict_from_db.get('category')
                }
                self.clients_data_map[actual_new_client_id] = ui_map_data
                self.add_client_to_list_widget(ui_map_data)
            self.client_name_input.clear(); self.company_name_input.clear(); self.client_need_input.clear()
            self.project_id_input_field.clear(); self.final_price_input.setValue(0)
            QMessageBox.information(self, self.tr("Client Créé"), self.tr("Client {0} créé avec succès (ID Interne: {1}).").format(client_name_val, actual_new_client_id))
            self.open_client_tab_by_id(actual_new_client_id)
            self.stats_widget.update_stats()
        except OSError as e_os:
            QMessageBox.critical(self, self.tr("Erreur Dossier"), self.tr("Erreur de création du dossier client:
{0}").format(str(e_os)))
            if actual_new_client_id:
                 db_manager.delete_client(actual_new_client_id)
                 QMessageBox.information(self, self.tr("Rollback"), self.tr("Le client a été retiré de la base de données suite à l'erreur de création de dossier."))
        except Exception as e_db:
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur s'est produite lors de la création du client, du projet ou des tâches:
{0}").format(str(e_db)))
            if new_project_id_central_db and db_manager.get_project_by_id(new_project_id_central_db):
                db_manager.delete_project(new_project_id_central_db)
            if actual_new_client_id and db_manager.get_client_by_id(actual_new_client_id):
                 db_manager.delete_client(actual_new_client_id)
                 QMessageBox.information(self, self.tr("Rollback"), self.tr("Le client et le projet associé (si créé) ont été retirés de la base de données suite à l'erreur."))

    def load_clients_from_db(self):
        self.clients_data_map.clear()
        self.client_list_widget.clear()
        try:
            all_clients_dicts = db_manager.get_all_clients()
            if all_clients_dicts is None: all_clients_dicts = []
            all_clients_dicts.sort(key=lambda c: c.get('client_name', ''))
            for client_data in all_clients_dicts:
                country_name = "N/A"
                if client_data.get('country_id'):
                    country_obj = db_manager.get_country_by_id(client_data['country_id'])
                    if country_obj: country_name = country_obj['country_name']
                city_name = "N/A"
                if client_data.get('city_id'):
                    city_obj = db_manager.get_city_by_id(client_data['city_id'])
                    if city_obj: city_name = city_obj['city_name']
                status_name = "N/A"
                status_id_val = client_data.get('status_id')
                if status_id_val:
                    status_obj = db_manager.get_status_setting_by_id(status_id_val)
                    if status_obj: status_name = status_obj['status_name']
                adapted_client_dict = {
                    "client_id": client_data.get('client_id'), "client_name": client_data.get('client_name'),
                    "company_name": client_data.get('company_name'), "need": client_data.get('primary_need_description'),
                    "country": country_name, "country_id": client_data.get('country_id'),
                    "city": city_name, "city_id": client_data.get('city_id'),
                    "project_identifier": client_data.get('project_identifier'),
                    "base_folder_path": client_data.get('default_base_folder_path'),
                    "selected_languages": client_data.get('selected_languages', '').split(',') if client_data.get('selected_languages') else ['fr'],
                    "price": client_data.get('price', 0), "notes": client_data.get('notes'),
                    "status": status_name, "status_id": status_id_val,
                    "creation_date": client_data.get('created_at', '').split('T')[0] if client_data.get('created_at') else "N/A",
                    "category": client_data.get('category', 'Standard')
                }
                self.clients_data_map[adapted_client_dict["client_id"]] = adapted_client_dict
                self.add_client_to_list_widget(adapted_client_dict)
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des clients:
{0}").format(str(e)))

    def add_client_to_list_widget(self, client_dict_data):
        item = QListWidgetItem(client_dict_data["client_name"])
        item.setData(Qt.UserRole, client_dict_data.get("status", "N/A"))
        item.setData(Qt.UserRole + 1, client_dict_data["client_id"])
        self.client_list_widget.addItem(item)

    def filter_client_list_display(self):
        search_term = self.search_input_field.text().lower()
        selected_status_id = self.status_filter_combo.currentData()
        self.client_list_widget.clear()
        for client_id_key, client_data_val in self.clients_data_map.items():
            if selected_status_id is not None:
                if client_data_val.get("status_id") != selected_status_id: continue
            if search_term and not (search_term in client_data_val.get("client_name","").lower() or \
                                   search_term in client_data_val.get("project_identifier","").lower() or \
                                   search_term in client_data_val.get("company_name","").lower()):
                continue
            self.add_client_to_list_widget(client_data_val)

    def load_statuses_into_filter_combo(self):
        current_selection_data = self.status_filter_combo.currentData()
        self.status_filter_combo.clear()
        self.status_filter_combo.addItem(self.tr("Tous les statuts"), None)
        try:
            client_statuses = db_manager.get_all_status_settings(status_type='Client')
            if client_statuses is None: client_statuses = []
            for status_dict in client_statuses:
                self.status_filter_combo.addItem(status_dict['status_name'], status_dict.get('status_id'))
            index = self.status_filter_combo.findData(current_selection_data)
            if index != -1: self.status_filter_combo.setCurrentIndex(index)
        except Exception as e:
            print(self.tr("Erreur chargement statuts pour filtre: {0}").format(str(e)))

    def handle_client_list_click(self, item):
        client_id_val = item.data(Qt.UserRole + 1)
        if client_id_val: self.open_client_tab_by_id(client_id_val)

    def open_client_tab_by_id(self, client_id_to_open):
        client_data_to_show = self.clients_data_map.get(client_id_to_open)
        if not client_data_to_show: return
        for i in range(self.client_tabs_widget.count()):
            tab_widget_ref = self.client_tabs_widget.widget(i)
            if hasattr(tab_widget_ref, 'client_info') and tab_widget_ref.client_info["client_id"] == client_id_to_open:
                self.client_tabs_widget.setCurrentIndex(i); return
        client_detail_widget = ClientWidget(client_data_to_show, self.config, self)
        tab_idx = self.client_tabs_widget.addTab(client_detail_widget, client_data_to_show["client_name"])
        self.client_tabs_widget.setCurrentIndex(tab_idx)

    def close_client_tab(self, index):
        widget_to_close = self.client_tabs_widget.widget(index)
        if widget_to_close: widget_to_close.deleteLater()
        self.client_tabs_widget.removeTab(index)

    def show_client_context_menu(self, pos):
        list_item = self.client_list_widget.itemAt(pos)
        if not list_item: return
        client_id_val = list_item.data(Qt.UserRole + 1)
        menu = QMenu()
        open_action = menu.addAction(self.tr("Ouvrir Fiche Client")); open_action.triggered.connect(lambda: self.open_client_tab_by_id(client_id_val))
        open_folder_action = menu.addAction(self.tr("Ouvrir Dossier Client")); open_folder_action.triggered.connect(lambda: self.open_client_folder_fs(client_id_val))
        menu.addSeparator()
        archive_action = menu.addAction(self.tr("Archiver Client")); archive_action.triggered.connect(lambda: self.set_client_status_archived(client_id_val))
        delete_action = menu.addAction(self.tr("Supprimer Client")); delete_action.triggered.connect(lambda: self.delete_client_permanently(client_id_val))
        menu.exec_(self.client_list_widget.mapToGlobal(pos))

    def open_client_folder_fs(self, client_id_val):
        if client_id_val in self.clients_data_map:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.clients_data_map[client_id_val]["base_folder_path"]))

    def set_client_status_archived(self, client_id_val):
        if client_id_val not in self.clients_data_map: return
        try:
            status_archived_obj = db_manager.get_status_setting_by_name('Archivé', 'Client')
            if not status_archived_obj:
                QMessageBox.critical(self, self.tr("Erreur Configuration"), self.tr("Statut 'Archivé' non trouvé. Veuillez configurer les statuts."))
                return
            archived_status_id = status_archived_obj['status_id']
            updated = db_manager.update_client(client_id_val, {'status_id': archived_status_id})
            if updated:
                self.clients_data_map[client_id_val]["status"] = "Archivé"
                self.clients_data_map[client_id_val]["status_id"] = archived_status_id
                self.filter_client_list_display()
                for i in range(self.client_tabs_widget.count()):
                    tab_w = self.client_tabs_widget.widget(i)
                    if hasattr(tab_w, 'client_info') and tab_w.client_info["client_id"] == client_id_val:
                        if hasattr(tab_w, 'status_combo'):
                           tab_w.status_combo.setCurrentText("Archivé")
                        break
                self.stats_widget.update_stats()
                QMessageBox.information(self, self.tr("Client Archivé"), self.tr("Le client '{0}' a été archivé.").format(self.clients_data_map[client_id_val]['client_name']))
            else:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'archivage du client. Vérifiez les logs."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'archivage du client:
{0}").format(str(e)))

    def delete_client_permanently(self, client_id_val):
        if client_id_val not in self.clients_data_map: return
        client_name_val = self.clients_data_map[client_id_val]['client_name']
        client_folder_path = self.clients_data_map[client_id_val]["base_folder_path"]
        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"), self.tr("Supprimer '{0}'?
Ceci supprimera le client de la base de données (les contacts liés seront détachés mais pas supprimés globalement) et son dossier de fichiers (si possible).
Cette action est irréversible.").format(client_name_val), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                deleted_from_db = db_manager.delete_client(client_id_val)
                if deleted_from_db:
                    if os.path.exists(client_folder_path):
                        shutil.rmtree(client_folder_path, ignore_errors=True)
                    del self.clients_data_map[client_id_val]
                    self.filter_client_list_display()
                    for i in range(self.client_tabs_widget.count()):
                        if hasattr(self.client_tabs_widget.widget(i), 'client_info') and \
                           self.client_tabs_widget.widget(i).client_info["client_id"] == client_id_val:
                            self.close_client_tab(i); break
                    self.stats_widget.update_stats()
                    QMessageBox.information(self, self.tr("Client Supprimé"), self.tr("Client '{0}' supprimé avec succès.").format(client_name_val))
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur lors de la suppression du client de la base de données. Le dossier n'a pas été supprimé."))
            except OSError as e_os:
                QMessageBox.critical(self, self.tr("Erreur Dossier"), self.tr("Le client a été supprimé de la base de données, mais une erreur est survenue lors de la suppression de son dossier:
{0}").format(str(e_os)))
                if client_id_val in self.clients_data_map:
                    del self.clients_data_map[client_id_val]
                    self.filter_client_list_display()
                    for i in range(self.client_tabs_widget.count()):
                        if hasattr(self.client_tabs_widget.widget(i), 'client_info') and \
                        self.client_tabs_widget.widget(i).client_info["client_id"] == client_id_val:
                            self.close_client_tab(i); break
                    self.stats_widget.update_stats()
            except Exception as e_db:
                 QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur lors de la suppression du client:
{0}").format(str(e_db)))

    def check_old_clients_routine(self):
        try:
            reminder_days_val = self.config.get("default_reminder_days", 30)
            s_archived_obj = db_manager.get_status_setting_by_name('Archivé', 'Client')
            s_archived_id = s_archived_obj['status_id'] if s_archived_obj else -1
            s_complete_obj = db_manager.get_status_setting_by_name('Complété', 'Client')
            s_complete_id = s_complete_obj['status_id'] if s_complete_obj else -2
            all_clients = db_manager.get_all_clients()
            if all_clients is None: all_clients = []
            old_clients_to_notify = []
            cutoff_date = datetime.now() - timedelta(days=reminder_days_val)
            for client in all_clients:
                if client.get('status_id') not in [s_archived_id, s_complete_id]:
                    creation_date_str = client.get('created_at')
                    if creation_date_str:
                        try:
                            if 'T' in creation_date_str and '.' in creation_date_str:
                                client_creation_date = datetime.fromisoformat(creation_date_str.split('.')[0])
                            elif 'T' in creation_date_str:
                                 client_creation_date = datetime.fromisoformat(creation_date_str.replace('Z', ''))
                            else:
                                client_creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d")
                            if client_creation_date <= cutoff_date:
                                old_clients_to_notify.append({
                                    'client_id': client.get('client_id'), 'client_name': client.get('client_name'),
                                    'creation_date_str': client_creation_date.strftime("%Y-%m-%d")
                                })
                        except ValueError as ve:
                            print(f"Could not parse creation_date '{creation_date_str}' for client {client.get('client_id')}: {ve}")
                            continue
            if old_clients_to_notify:
                client_names_str = "
".join([f"- {c['client_name']} (créé le {c['creation_date_str']})" for c in old_clients_to_notify])
                reply = QMessageBox.question(self, self.tr("Clients Anciens Actifs"), self.tr("Les clients suivants sont actifs depuis plus de {0} jours:
{1}

Voulez-vous les archiver?").format(reminder_days_val, client_names_str), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    for c_info in old_clients_to_notify:
                        self.set_client_status_archived(c_info['client_id'])
        except Exception as e:
            print(f"Erreur vérification clients anciens: {str(e)}")

    def open_settings_dialog(self):
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            new_conf = dialog.get_config()
            self.config.update(new_conf)
            save_config(self.config)
            os.makedirs(self.config["templates_dir"], exist_ok=True)
            os.makedirs(self.config["clients_dir"], exist_ok=True)
            QMessageBox.information(self, self.tr("Paramètres Sauvegardés"), self.tr("Nouveaux paramètres enregistrés."))

    def open_template_manager_dialog(self):
        TemplateDialog(self).exec_()

    def open_status_manager_dialog(self):
        QMessageBox.information(self, self.tr("Gestion des Statuts"), self.tr("Fonctionnalité de gestion des statuts personnalisés à implémenter (e.g., via un nouveau QDialog)."))

    def closeEvent(self, event):
        save_config(self.config)
        super().closeEvent(event)

class SettingsDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Paramètres de l'Application")); self.setMinimumSize(500, 400)
        self.current_config_data = current_config
        self.setup_ui_settings()

    def setup_ui_settings(self):
        layout = QVBoxLayout(self); tabs_widget = QTabWidget(); layout.addWidget(tabs_widget)
        general_tab_widget = QWidget(); general_form_layout = QFormLayout(general_tab_widget)
        self.templates_dir_input = QLineEdit(self.current_config_data["templates_dir"])
        templates_browse_btn = QPushButton(self.tr("Parcourir...")); templates_browse_btn.clicked.connect(lambda: self.browse_directory_for_input(self.templates_dir_input, self.tr("Sélectionner dossier modèles")))
        templates_dir_layout = QHBoxLayout(); templates_dir_layout.addWidget(self.templates_dir_input); templates_dir_layout.addWidget(templates_browse_btn)
        general_form_layout.addRow(self.tr("Dossier des Modèles:"), templates_dir_layout)
        self.clients_dir_input = QLineEdit(self.current_config_data["clients_dir"])
        clients_browse_btn = QPushButton(self.tr("Parcourir...")); clients_browse_btn.clicked.connect(lambda: self.browse_directory_for_input(self.clients_dir_input, self.tr("Sélectionner dossier clients")))
        clients_dir_layout = QHBoxLayout(); clients_dir_layout.addWidget(self.clients_dir_input); clients_dir_layout.addWidget(clients_browse_btn)
        general_form_layout.addRow(self.tr("Dossier des Clients:"), clients_dir_layout)
        self.interface_lang_combo = QComboBox()
        self.lang_display_to_code = {
            self.tr("Français (fr)"): "fr", self.tr("English (en)"): "en",
            self.tr("العربية (ar)"): "ar", self.tr("Türkçe (tr)"): "tr",
            self.tr("Português (pt)"): "pt"
        }
        self.interface_lang_combo.addItems(list(self.lang_display_to_code.keys()))
        current_lang_code = self.current_config_data.get("language", "fr")
        code_to_display_text = {code: display for display, code in self.lang_display_to_code.items()}
        current_display_text = code_to_display_text.get(current_lang_code)
        if current_display_text: self.interface_lang_combo.setCurrentText(current_display_text)
        else:
            french_display_text = code_to_display_text.get("fr", list(self.lang_display_to_code.keys())[0])
            self.interface_lang_combo.setCurrentText(french_display_text)
        general_form_layout.addRow(self.tr("Langue Interface (redémarrage requis):"), self.interface_lang_combo)
        self.reminder_days_spinbox = QSpinBox(); self.reminder_days_spinbox.setRange(1, 365)
        self.reminder_days_spinbox.setValue(self.current_config_data.get("default_reminder_days", 30))
        general_form_layout.addRow(self.tr("Jours avant rappel client ancien:"), self.reminder_days_spinbox)
        tabs_widget.addTab(general_tab_widget, self.tr("Général"))

        email_tab_widget = QWidget(); email_form_layout = QFormLayout(email_tab_widget)
        self.smtp_server_input_field = QLineEdit(self.current_config_data.get("smtp_server", ""))
        email_form_layout.addRow(self.tr("Serveur SMTP:"), self.smtp_server_input_field)
        self.smtp_port_spinbox = QSpinBox(); self.smtp_port_spinbox.setRange(1, 65535)
        self.smtp_port_spinbox.setValue(self.current_config_data.get("smtp_port", 587))
        email_form_layout.addRow(self.tr("Port SMTP:"), self.smtp_port_spinbox)
        self.smtp_user_input_field = QLineEdit(self.current_config_data.get("smtp_user", ""))
        email_form_layout.addRow(self.tr("Utilisateur SMTP:"), self.smtp_user_input_field)
        self.smtp_pass_input_field = QLineEdit(self.current_config_data.get("smtp_password", ""))
        self.smtp_pass_input_field.setEchoMode(QLineEdit.Password)
        email_form_layout.addRow(self.tr("Mot de passe SMTP:"), self.smtp_pass_input_field)
        tabs_widget.addTab(email_tab_widget, self.tr("Email"))

        dialog_button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dialog_button_box.button(QDialogButtonBox.Ok).setText(self.tr("OK"))
        dialog_button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        dialog_button_box.accepted.connect(self.accept); dialog_button_box.rejected.connect(self.reject)
        layout.addWidget(dialog_button_box)

    def browse_directory_for_input(self, line_edit_target, dialog_title):
        dir_path = QFileDialog.getExistingDirectory(self, dialog_title, line_edit_target.text())
        if dir_path: line_edit_target.setText(dir_path)

    def get_config(self):
        selected_lang_display_text = self.interface_lang_combo.currentText()
        language_code = self.lang_display_to_code.get(selected_lang_display_text, "fr")
        return {
            "templates_dir": self.templates_dir_input.text(), "clients_dir": self.clients_dir_input.text(),
            "language": language_code, "default_reminder_days": self.reminder_days_spinbox.value(),
            "smtp_server": self.smtp_server_input_field.text(), "smtp_port": self.smtp_port_spinbox.value(),
            "smtp_user": self.smtp_user_input_field.text(), "smtp_password": self.smtp_pass_input_field.text()
        }

def main_app_entry_point():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'): QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    language_code = CONFIG.get("language", QLocale.system().name().split('_')[0])

    app = QApplication(sys.argv)
    app.setApplicationName("ClientDocManager")
    app.setStyle("Fusion")

    translator = QTranslator()
    translation_file_name = f"app_{language_code}.qm"
    translation_path_full = os.path.join(APP_ROOT_DIR, "translations", translation_file_name)

    if translator.load(translation_path_full):
        app.installTranslator(translator)
        print(f"Loaded custom translation: {translation_path_full}")
    else:
        print(f"Failed to load custom translation for {language_code} from {translation_path_full}")
        if translator.load(QLocale(language_code), translation_file_name, "_", QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
            app.installTranslator(translator)
            print(f"Loaded custom translation from Qt standard path for {language_code}")
        else:
            print(f"Also failed to load custom translation from Qt standard path for {language_code}")

    qt_translator = QTranslator()
    qt_translation_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    if qt_translator.load(QLocale(language_code), "qtbase", "_", qt_translation_path):
        app.installTranslator(qt_translator)
        print(f"Loaded Qt base translations for {language_code} from {qt_translation_path}")
    else:
        print(f"Failed to load Qt base translations for {language_code} from {qt_translation_path}")

    TARGET_LANGS_TO_POPULATE = ["en", "pt"]
    SOURCE_LANG_DIR_CODE = "fr"
    base_templates_dir = CONFIG["templates_dir"]
    source_lang_full_path = os.path.join(base_templates_dir, SOURCE_LANG_DIR_CODE)
    if os.path.exists(source_lang_full_path):
        for target_lang_code in TARGET_LANGS_TO_POPULATE:
            target_lang_dir_path = os.path.join(base_templates_dir, target_lang_code)
            os.makedirs(target_lang_dir_path, exist_ok=True)
            for filename in os.listdir(source_lang_full_path):
                source_file = os.path.join(source_lang_full_path, filename)
                destination_file = os.path.join(target_lang_dir_path, filename)
                if os.path.isfile(source_file):
                    if not os.path.exists(destination_file):
                        try:
                            shutil.copy2(source_file, destination_file)
                            print(f"Copied '{filename}' to '{target_lang_code}' directory.")
                        except Exception as e: print(f"Error copying '{filename}' to '{target_lang_code}': {e}")
    else: print(f"Source French template directory '{source_lang_full_path}' does not exist. Cannot copy templates.")

    templates_root_dir = CONFIG["templates_dir"]
    default_langs_for_creation = ["fr", "en", "ar", "tr", "pt"]

    default_templates_data = {
        SPEC_TECH_TEMPLATE_NAME: pd.DataFrame({'Section': ["Info Client", "Détails Tech"], 'Champ': ["Nom:", "Exigence:"], 'Valeur': ["{NOM_CLIENT}", ""]}),
        PROFORMA_TEMPLATE_NAME: pd.DataFrame({'Article': ["Produit A"], 'Qté': [1], 'PU': [10.0], 'Total': [10.0]}),
        CONTRAT_VENTE_TEMPLATE_NAME: pd.DataFrame({'Clause': ["Objet"], 'Description': ["Vente de ..."]}),
        PACKING_LISTE_TEMPLATE_NAME: pd.DataFrame({'Colis': [1], 'Contenu': ["Marchandise X"], 'Poids': [5.0]})
    }
    for lang_code in default_langs_for_creation:
        lang_specific_dir = os.path.join(templates_root_dir, lang_code)
        os.makedirs(lang_specific_dir, exist_ok=True)
        for template_file_name, df_content in default_templates_data.items():
            template_full_path = os.path.join(lang_specific_dir, template_file_name)
            if not os.path.exists(template_full_path):
                try: df_content.to_excel(template_full_path, index=False)
                except Exception as e: print(f"Erreur création template {template_file_name} pour {lang_code}: {str(e)}")

    # At this point, gui_components module is not yet created, so imports from it would fail.
    # The classes DocumentManager uses from gui_components (ClientWidget, TemplateDialog)
    # are referenced via placeholder local imports within DocumentManager's methods for now.
    # These will be converted to top-level imports in a later step.

    main_window = DocumentManager()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main_app_entry_point()
