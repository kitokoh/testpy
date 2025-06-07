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
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QGridLayout,
    QFrame,QSizePolicy # Added for CustomNotificationBanner
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QColor
from PyQt5.QtCore import Qt, QUrl, QTimer, QLocale, QLibraryInfo, QCoreApplication # QStandardPaths removed as get_config_dir is no longer here
from PyQt5.QtWidgets import QDoubleSpinBox

# Imports for sequential dialogs
from gui_components import ContactDialog, ProductDialog, CreateDocumentDialog


# Custom Notification Banner Class (copied from projectManagement.py)
class CustomNotificationBanner(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("customNotificationBanner")
        self.setStyleSheet("""
            #customNotificationBanner {
                background-color: #333333;
                color: white;
                border-radius: 5px;
                padding: 10px;
            }
            #customNotificationBanner QLabel {
                color: white;
                font-size: 10pt;
            }
            #customNotificationBanner QPushButton {
                color: white;
                background-color: #555555;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 5px 8px;
                font-size: 9pt;
            }
            #customNotificationBanner QPushButton:hover {
                background-color: #666666;
            }
        """)
        self.setFixedHeight(50)
        self.setFixedWidth(350)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        self.icon_label = QLabel("ℹ️")
        self.icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.message_label = QLabel("Notification message will appear here.")
        self.message_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.message_label.setWordWrap(True)
        self.close_button = QPushButton("X")
        self.close_button.setToolTip("Close")
        self.close_button.setFixedSize(25, 25)
        self.close_button.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                background-color: transparent;
                border: none;
                color: white;
                font-size: 12pt;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.close_button.clicked.connect(self.hide)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.message_label)
        layout.addStretch()
        layout.addWidget(self.close_button)
        self.hide()

    def set_message(self, title, message):
        full_message = f"<b>{title}</b><br>{message}"
        self.message_label.setText(full_message)
        if "error" in title.lower() or "alert" in title.lower():
            self.icon_label.setText("⚠️")
        elif "success" in title.lower():
            self.icon_label.setText("✅")
        elif "urgent" in title.lower() or "reminder" in title.lower():
            self.icon_label.setText("🔔")
        else:
            self.icon_label.setText("ℹ️")

# Style helper functions (replicating from projectManagement.py for consistency)
def get_primary_button_style():
    return """
        QPushButton {
            background-color: #28a745; color: white; font-weight: bold;
            padding: 10px; border-radius: 5px; border: none;
        }
        QPushButton:hover { background-color: #218838; }
        QPushButton:pressed { background-color: #1e7e34; }
    """

def get_small_button_style():
    return """
        QPushButton {
            background-color: #6c757d; color: white; font-weight: bold;
            border-radius: 4px; padding: 5px; border: none;
        }
        QPushButton:hover { background-color: #5a6268; }
        QPushButton:pressed { background-color: #545b62; }
    """

def get_generic_input_style():
    return """
        QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit, QSpinBox {
            padding: 8px 10px; border: 1px solid #ced4da;
            border-radius: 4px; background-color: white; min-height: 20px;
        }
        QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QSpinBox:focus {
            border-color: #80bdff;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding; subcontrol-position: top right; width: 20px;
            border-left-width: 1px; border-left-color: #ced4da; border-left-style: solid;
            border-top-right-radius: 3px; border-bottom-right-radius: 3px;
        }
        QComboBox::down-arrow {
            image: url(icons/arrow_down.png);
        }
    """ # Assuming icons/arrow_down.png exists or will be added

def get_group_box_style():
    return """
        QGroupBox {
            font-size: 12pt; font-weight: bold; color: #343a40;
            border: 1px solid #dee2e6; border-radius: 6px; margin-top: 15px;
        }
        QGroupBox::title {
            subcontrol-origin: margin; subcontrol-position: top left;
            padding: 5px 10px; background-color: #e9ecef;
            border-top-left-radius: 6px; border-top-right-radius: 6px;
            border-bottom: 1px solid #dee2e6;
        }
    """

def get_tab_widget_style():
    return """
        QTabWidget::pane {
            border: 1px solid #dee2e6; border-top: none;
            border-radius: 0 0 5px 5px; padding: 15px;
        }
        QTabBar::tab {
            padding: 10px 18px; background: #e9ecef;
            border: 1px solid #dee2e6; border-bottom: none;
            border-top-left-radius: 5px; border-top-right-radius: 5px;
            color: #495057; font-weight: bold; margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #007bff; color: white; border-color: #007bff;
        }
        QTabBar::tab:hover:!selected { background: #d8dde2; }
    """


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
        # Base styling for the main window
        self.setStyleSheet("QWidget { background-color: #f8f9fa; font-family: 'Segoe UI'; font-size: 10pt; }")

        # Notification Banner Setup
        self.notification_banner = CustomNotificationBanner(self)
        self.notification_banner.raise_()

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
        # Apply base font to central widget, it will be inherited by children
        font = QFont("Segoe UI", 10)
        central_widget.setFont(font)

        main_layout = QVBoxLayout(central_widget); main_layout.setContentsMargins(10,10,10,10); main_layout.setSpacing(10)
        self.stats_widget = StatisticsWidget(); main_layout.addWidget(self.stats_widget)
        self.main_area_stack = QStackedWidget()
        main_layout.addWidget(self.main_area_stack)
        self.documents_page_widget = QWidget()
        content_layout = QHBoxLayout(self.documents_page_widget)
        left_panel = QWidget(); left_layout = QVBoxLayout(left_panel); left_layout.setContentsMargins(5,5,5,5)

        # Input and ComboBox styling for filter/search area
        self.status_filter_combo = QComboBox(); self.status_filter_combo.addItem(self.tr("Tous les statuts"))
        self.status_filter_combo.setStyleSheet(get_generic_input_style())
        self.load_statuses_into_filter_combo()
        self.status_filter_combo.currentIndexChanged.connect(self.filter_client_list_display)

        self.search_input_field = QLineEdit(); self.search_input_field.setPlaceholderText(self.tr("Rechercher client..."))
        self.search_input_field.setStyleSheet(get_generic_input_style())
        self.search_input_field.textChanged.connect(self.filter_client_list_display)

        filter_search_layout = QHBoxLayout()
        filter_search_layout.addWidget(QLabel(self.tr("Filtrer par statut:")))
        filter_search_layout.addWidget(self.status_filter_combo)
        filter_search_layout.addWidget(self.search_input_field); left_layout.addLayout(filter_search_layout)

        self.client_list_widget = QListWidget(); self.client_list_widget.setAlternatingRowColors(True)
        self.client_list_widget.setItemDelegate(StatusDelegate(self.client_list_widget))
        self.client_list_widget.itemClicked.connect(self.handle_client_list_click)
        self.client_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.client_list_widget.customContextMenuRequested.connect(self.show_client_context_menu)
        left_layout.addWidget(self.client_list_widget)

        form_group_box = QGroupBox(self.tr("Ajouter un Nouveau Client"))
        form_group_box.setStyleSheet(get_group_box_style())
        form_vbox_layout = QVBoxLayout(form_group_box)

        creation_form_layout = QFormLayout(); creation_form_layout.setLabelAlignment(Qt.AlignRight)
        # Apply generic input style to form fields
        self.client_name_input = QLineEdit(); self.client_name_input.setPlaceholderText(self.tr("Nom du client"))
        self.client_name_input.setStyleSheet(get_generic_input_style())
        creation_form_layout.addRow(self.tr("Nom Client:"), self.client_name_input)

        self.company_name_input = QLineEdit(); self.company_name_input.setPlaceholderText(self.tr("Nom entreprise (optionnel)"))
        self.company_name_input.setStyleSheet(get_generic_input_style())
        creation_form_layout.addRow(self.tr("Nom Entreprise:"), self.company_name_input)

        self.client_need_input = QLineEdit(); self.client_need_input.setPlaceholderText(self.tr("Besoin principal du client"))
        self.client_need_input.setStyleSheet(get_generic_input_style())
        creation_form_layout.addRow(self.tr("Besoin Client:"), self.client_need_input)

        country_hbox_layout = QHBoxLayout(); self.country_select_combo = QComboBox()
        self.country_select_combo.setEditable(True); self.country_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.country_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.country_select_combo.completer().setFilterMode(Qt.MatchContains)
        self.country_select_combo.setStyleSheet(get_generic_input_style())
        self.country_select_combo.currentTextChanged.connect(self.load_cities_for_country)
        country_hbox_layout.addWidget(self.country_select_combo)

        self.add_country_button = QPushButton("+"); self.add_country_button.setFixedSize(30,30)
        self.add_country_button.setStyleSheet(get_small_button_style())
        self.add_country_button.setToolTip(self.tr("Ajouter un nouveau pays"))
        self.add_country_button.clicked.connect(self.add_new_country_dialog)
        country_hbox_layout.addWidget(self.add_country_button); creation_form_layout.addRow(self.tr("Pays Client:"), country_hbox_layout)

        city_hbox_layout = QHBoxLayout(); self.city_select_combo = QComboBox()
        self.city_select_combo.setEditable(True); self.city_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.city_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.city_select_combo.completer().setFilterMode(Qt.MatchContains)
        self.city_select_combo.setStyleSheet(get_generic_input_style())
        city_hbox_layout.addWidget(self.city_select_combo)

        self.add_city_button = QPushButton("+"); self.add_city_button.setFixedSize(30,30)
        self.add_city_button.setStyleSheet(get_small_button_style())
        self.add_city_button.setToolTip(self.tr("Ajouter une nouvelle ville"))
        self.add_city_button.clicked.connect(self.add_new_city_dialog)
        city_hbox_layout.addWidget(self.add_city_button); creation_form_layout.addRow(self.tr("Ville Client:"), city_hbox_layout)

        self.project_id_input_field = QLineEdit(); self.project_id_input_field.setPlaceholderText(self.tr("Référence unique pour le client/commande"))
        self.project_id_input_field.setStyleSheet(get_generic_input_style())
        creation_form_layout.addRow(self.tr("Référence Client/Commande:"), self.project_id_input_field)

        self.final_price_input = QDoubleSpinBox(); self.final_price_input.setPrefix("€ ")
        self.final_price_input.setRange(0, 10000000); self.final_price_input.setValue(0)
        self.final_price_input.setStyleSheet(get_generic_input_style())
        creation_form_layout.addRow(self.tr("Prix Final:"), self.final_price_input)

        self.language_select_combo = QComboBox()
        self.language_select_combo.addItems([self.tr("Français uniquement (fr)"), self.tr("Arabe uniquement (ar)"), self.tr("Turc uniquement (tr)"), self.tr("Toutes les langues (fr, ar, tr)")])
        self.language_select_combo.setStyleSheet(get_generic_input_style())
        creation_form_layout.addRow(self.tr("Langues:"), self.language_select_combo)

        self.create_client_button = QPushButton(self.tr("Créer Client")); self.create_client_button.setIcon(QIcon.fromTheme("list-add"))
        self.create_client_button.setStyleSheet(get_primary_button_style())
        self.create_client_button.clicked.connect(self.execute_create_client)
        creation_form_layout.addRow(self.create_client_button)

        form_vbox_layout.addLayout(creation_form_layout); left_layout.addWidget(form_group_box)
        content_layout.addWidget(left_panel, 1)
        self.client_tabs_widget = QTabWidget(); self.client_tabs_widget.setTabsClosable(True)
        self.client_tabs_widget.tabCloseRequested.connect(self.close_client_tab)
        # Apply TabWidget style
        self.client_tabs_widget.setStyleSheet(get_tab_widget_style())
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
                # Use banner for non-critical DB error if appropriate, or keep QMessageBox for critical ones
                self.show_notification(self.tr("Erreur DB"), self.tr("Impossible de créer le client. L'ID de projet ou le chemin du dossier existe peut-être déjà, ou autre erreur de contrainte DB."), duration=10000)
                return
            os.makedirs(base_folder_full_path, exist_ok=True)
            for lang_code in selected_langs_list:
                os.makedirs(os.path.join(base_folder_full_path, lang_code), exist_ok=True)

            project_status_planning_obj = db_manager.get_status_setting_by_name("Planning", "Project")
            project_status_id_for_pm = project_status_planning_obj['status_id'] if project_status_planning_obj else None
            if not project_status_id_for_pm:
                 self.show_notification(self.tr("Erreur Configuration Projet"), self.tr("Statut de projet par défaut 'Planning' non trouvé. Le projet ne sera pas créé avec un statut initial."), duration=8000)
            project_data_for_db = {
                'client_id': actual_new_client_id, 'project_name': f"Projet: {project_identifier_val} - {client_name_val}",
                'description': f"Projet pour client: {client_name_val}. Besoin initial: {need_val}",
                'start_date': datetime.now().strftime("%Y-%m-%d"), 'deadline_date': (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
                'budget': 0.0, 'status_id': project_status_id_for_pm, 'priority': 1
            }
            new_project_id_central_db = db_manager.add_project(project_data_for_db)
            if new_project_id_central_db:
                self.show_notification(self.tr("Projet Créé (Central DB)"), self.tr("Un projet associé a été créé dans la base de données centrale pour {0}.").format(client_name_val))
                task_status_todo_obj = db_manager.get_status_setting_by_name("To Do", "Task")
                task_status_id_for_todo = task_status_todo_obj['status_id'] if task_status_todo_obj else None
                if not task_status_id_for_todo:
                    self.show_notification(self.tr("Erreur Configuration Tâche"), self.tr("Statut de tâche par défaut 'To Do' non trouvé. Les tâches standard ne seront pas créées avec un statut initial."), duration=8000)
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
                self.show_notification(self.tr("Tâches Créées (Central DB)"), self.tr("Des tâches standard ont été ajoutées au projet pour {0}.").format(client_name_val))
            else:
                self.show_notification(self.tr("Erreur DB Projet"), self.tr("Le client a été créé, mais la création du projet associé dans la base de données centrale a échoué."), duration=10000)

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
            self.show_notification(self.tr("Client Créé"), self.tr("Client {0} créé avec succès (ID Interne: {1}).").format(client_name_val, actual_new_client_id))
            self.open_client_tab_by_id(actual_new_client_id)
            self.stats_widget.update_stats()

            # --- Start of sequential dialog logic ---
            client_widget_instance = None
            for i in range(self.client_tabs_widget.count()):
                widget = self.client_tabs_widget.widget(i)
                if hasattr(widget, 'client_info') and widget.client_info.get("client_id") == actual_new_client_id:
                    client_widget_instance = widget
                    break

            if not client_widget_instance:
                print(f"Error: Could not find ClientWidget for client ID {actual_new_client_id} to refresh data after dialogs.")
                # Not returning here, as the core client creation was successful.
                # Document creation dialog might still be useful.

            # B. Show Contact Dialog
            contact_dialog = ContactDialog(client_id=actual_new_client_id, parent=self)
            if contact_dialog.exec_() == QDialog.Accepted:
                contact_form_data = contact_dialog.get_data()
                existing_contact = db_manager.get_contact_by_email(contact_form_data['email'])
                contact_id_to_link = None

                if existing_contact:
                    contact_id_to_link = existing_contact['contact_id']
                    # Optional: Update existing global contact if details differ significantly
                    # For now, we assume if email matches, we use this contact.
                    # db_manager.update_contact(contact_id_to_link, {
                    # 'name': contact_form_data['name'], 'phone': contact_form_data['phone'],
                    # 'position': contact_form_data['position']
                    # })
                else:
                    new_contact_id_global = db_manager.add_contact({
                        'name': contact_form_data['name'], 'email': contact_form_data['email'],
                        'phone': contact_form_data['phone'], 'position': contact_form_data['position']
                    })
                    if new_contact_id_global:
                        contact_id_to_link = new_contact_id_global
                    else:
                        QMessageBox.critical(self, self.tr("Error DB"), self.tr("Could not create global contact record."))
                        # No return here, proceed to product dialog if user wishes, but contact part failed.

                if contact_id_to_link:
                    # Check if this contact is already linked to this client
                    already_linked = False
                    client_current_contacts = db_manager.get_contacts_for_client(actual_new_client_id)
                    if client_current_contacts:
                        for c_link in client_current_contacts:
                            if c_link['contact_id'] == contact_id_to_link:
                                already_linked = True
                                # Potentially update the existing link's primary status if changed
                                if contact_form_data['is_primary'] != c_link.get('is_primary_for_client'):
                                    if contact_form_data['is_primary']: # Unset other primaries
                                        for cc_item in client_current_contacts:
                                            if cc_item.get('is_primary_for_client') and cc_item['contact_id'] != contact_id_to_link:
                                                db_manager.update_client_contact_link(cc_item['client_contact_id'], {'is_primary_for_client': False})
                                    db_manager.update_client_contact_link(c_link['client_contact_id'], {'is_primary_for_client': contact_form_data['is_primary']})
                                self.show_notification(self.tr("Contact Updated"), self.tr("Contact link updated for this client."))
                                break

                    if not already_linked:
                        if contact_form_data['is_primary']:
                            client_contacts_list = db_manager.get_contacts_for_client(actual_new_client_id) # Re-fetch, could be empty
                            if client_contacts_list: # Ensure it's not None
                                for cc_link_item in client_contacts_list:
                                    if cc_link_item.get('is_primary_for_client'):
                                        db_manager.update_client_contact_link(cc_link_item['client_contact_id'], {'is_primary_for_client': False})

                        link_id = db_manager.link_contact_to_client(
                            actual_new_client_id, contact_id_to_link,
                            is_primary=contact_form_data['is_primary']
                        )
                        if not link_id:
                            QMessageBox.critical(self, self.tr("Error DB"), self.tr("Could not link contact to client."))
                            # No return, proceed to product.

                    if client_widget_instance:
                        client_widget_instance.load_contacts_for_client()
                else: # Failed to get or create a global contact ID
                    QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to obtain contact ID for linking. Contact not added to client."))
                    # No return, proceed.

                # C. Show Product Dialog (if Contact Dialog was accepted - this means we are inside this block)
                product_dialog = ProductDialog(client_id=actual_new_client_id, parent=self)
                if product_dialog.exec_() == QDialog.Accepted:
                    product_form_data = product_dialog.get_data()
                    global_product = db_manager.get_product_by_name(product_form_data['product_name'])
                    global_product_id = None

                    if global_product:
                        global_product_id = global_product['product_id']
                        # Optional: Update global product description if it has changed
                        # if global_product['description'] != product_form_data['product_description']:
                        #     db_manager.update_product(global_product_id, {'description': product_form_data['product_description']})
                    else:
                        new_global_product_id = db_manager.add_product({
                            'product_name': product_form_data['product_name'],
                            'description': product_form_data['product_description'],
                            'base_unit_price': product_form_data['unit_price_for_dialog'] # Store the price given as base if new
                        })
                        if new_global_product_id:
                            global_product_id = new_global_product_id
                            global_product = db_manager.get_product_by_id(global_product_id) # Fetch to get consistent data
                        else:
                            QMessageBox.critical(self, self.tr("Error DB"), self.tr("Could not create global product."))
                            # No return, proceed to doc dialog if user wishes.

                    if global_product_id:
                        # Determine unit_price_override
                        # Base price is from the global product table. If it's a new product, it's what user entered.
                        # If existing product, it's its stored base_unit_price.
                        base_price_to_compare = global_product['base_unit_price'] if global_product else product_form_data['unit_price_for_dialog']
                        price_override = None
                        if product_form_data['unit_price_for_dialog'] != base_price_to_compare:
                            price_override = product_form_data['unit_price_for_dialog']

                        link_data = {
                            'client_id': actual_new_client_id,
                            'project_id': None, # Not linked to a specific project from this workflow
                            'product_id': global_product_id,
                            'quantity': product_form_data['quantity'],
                            'unit_price_override': price_override
                        }
                        cpp_id = db_manager.add_product_to_client_or_project(link_data)
                        if cpp_id:
                            if client_widget_instance:
                                client_widget_instance.load_products_for_client()
                        else:
                            QMessageBox.critical(self, self.tr("Error DB"), self.tr("Could not link product to client."))
                            # No return
                    else: # Should not happen if logic is correct
                        QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to obtain product ID for linking. Product not added."))
                        # No return

                    # D. Show CreateDocumentDialog (if Product Dialog was accepted)
                    # client_info_for_doc_dialog is ui_map_data from earlier in execute_create_client
                    # or self.clients_data_map.get(actual_new_client_id)
                    client_info_for_doc_dialog = self.clients_data_map.get(actual_new_client_id)
                    if not client_info_for_doc_dialog:
                        QMessageBox.warning(self, self.tr("Error"), self.tr("Client data not found for document creation step."))
                        # No return here, this is the end of the sequence if this fails.
                    else:
                        doc_dialog = CreateDocumentDialog(client_info_for_doc_dialog, self.config, self)
                        if doc_dialog.exec_() == QDialog.Accepted:
                            if client_widget_instance:
                                client_widget_instance.populate_doc_table_for_client()
                        # No return, end of sequence regardless of doc_dialog acceptance.

                else: # Product dialog cancelled
                    self.show_notification(self.tr("Product Skipped"), self.tr("Product addition was skipped by the user."))
                    # Proceed to Document Creation even if product is skipped.
                    client_info_for_doc_dialog = self.clients_data_map.get(actual_new_client_id)
                    if not client_info_for_doc_dialog:
                        QMessageBox.warning(self, self.tr("Error"), self.tr("Client data not found for document creation step."))
                    else:
                        doc_dialog = CreateDocumentDialog(client_info_for_doc_dialog, self.config, self)
                        if doc_dialog.exec_() == QDialog.Accepted:
                            if client_widget_instance:
                                client_widget_instance.populate_doc_table_for_client()
                    return # End of workflow if product dialog is cancelled.

            else: # Contact dialog cancelled
                self.show_notification(self.tr("Contact Skipped"), self.tr("Contact addition was skipped by the user."))
                # Ask if user wants to proceed to Product addition anyway
                reply = QMessageBox.question(self, self.tr("Skip Contact"),
                                             self.tr("Contact addition was skipped. Do you want to add a product and create a document for this client?"),
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    product_dialog = ProductDialog(client_id=actual_new_client_id, parent=self)
                    if product_dialog.exec_() == QDialog.Accepted:
                        product_form_data = product_dialog.get_data()
                        # ... (Same product logic as above)
                        global_product = db_manager.get_product_by_name(product_form_data['product_name'])
                        global_product_id = None
                        if global_product:
                            global_product_id = global_product['product_id']
                        else:
                            new_global_product_id = db_manager.add_product({
                                'product_name': product_form_data['product_name'],
                                'description': product_form_data['product_description'],
                                'base_unit_price': product_form_data['unit_price_for_dialog']
                            })
                            if new_global_product_id:
                                global_product_id = new_global_product_id
                                global_product = db_manager.get_product_by_id(global_product_id)
                            else:
                                QMessageBox.critical(self, self.tr("Error DB"), self.tr("Could not create global product."))

                        if global_product_id:
                            base_price_to_compare = global_product['base_unit_price'] if global_product else product_form_data['unit_price_for_dialog']
                            price_override = None
                            if product_form_data['unit_price_for_dialog'] != base_price_to_compare:
                                price_override = product_form_data['unit_price_for_dialog']
                            link_data = {
                                'client_id': actual_new_client_id, 'project_id': None,
                                'product_id': global_product_id, 'quantity': product_form_data['quantity'],
                                'unit_price_override': price_override
                            }
                            cpp_id = db_manager.add_product_to_client_or_project(link_data)
                            if cpp_id and client_widget_instance:
                                client_widget_instance.load_products_for_client()
                            elif not cpp_id:
                                QMessageBox.critical(self, self.tr("Error DB"), self.tr("Could not link product to client."))
                        else:
                             QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to obtain product ID for linking."))

                        # Proceed to Document Creation
                        client_info_for_doc_dialog = self.clients_data_map.get(actual_new_client_id)
                        if not client_info_for_doc_dialog:
                            QMessageBox.warning(self, self.tr("Error"), self.tr("Client data not found for document creation step."))
                        else:
                            doc_dialog = CreateDocumentDialog(client_info_for_doc_dialog, self.config, self)
                            if doc_dialog.exec_() == QDialog.Accepted:
                                if client_widget_instance:
                                    client_widget_instance.populate_doc_table_for_client()
                        return # End of workflow here

                    else: # Product dialog cancelled after contact was skipped
                        self.show_notification(self.tr("Workflow Skipped"), self.tr("Product and document steps skipped by the user."))
                        return # Stop the workflow
                else: # User chose not to proceed after skipping contact
                    self.show_notification(self.tr("Workflow Stopped"), self.tr("Client creation complete. Contact, product, and document steps skipped."))
                    return # Stop the workflow
            # --- End of sequential dialog logic ---

        except OSError as e_os:
            # Keep critical for OS errors that prevent folder creation
            QMessageBox.critical(self, self.tr("Erreur Dossier"), self.tr("Erreur de création du dossier client:
{0}").format(str(e_os)))
            if actual_new_client_id:
                 db_manager.delete_client(actual_new_client_id)
                 self.show_notification(self.tr("Rollback"), self.tr("Le client a été retiré de la base de données suite à l'erreur de création de dossier."), duration=8000)
        except Exception as e_db:
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur s'est produite lors de la création du client, du projet ou des tâches:
{0}").format(str(e_db)))
            if new_project_id_central_db and db_manager.get_project_by_id(new_project_id_central_db):
                db_manager.delete_project(new_project_id_central_db)
            if actual_new_client_id and db_manager.get_client_by_id(actual_new_client_id):
                 db_manager.delete_client(actual_new_client_id)
                 self.show_notification(self.tr("Rollback"), self.tr("Le client et le projet associé (si créé) ont été retirés de la base de données suite à l'erreur."), duration=10000)

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
        # Connect the signal
        client_detail_widget.manage_project_requested.connect(self.handle_manage_project_request)
        tab_idx = self.client_tabs_widget.addTab(client_detail_widget, client_data_to_show["client_name"])
        self.client_tabs_widget.setCurrentIndex(tab_idx)

    def handle_manage_project_request(self, client_id):
        # 1. Find the project_id for this client_id.
        project_for_client = db_manager.get_project_by_client_id(client_id)

        if project_for_client and project_for_client.get('project_id'):
            project_id_to_focus = project_for_client['project_id']

            # 2. Switch to the project management dashboard view
            self.main_area_stack.setCurrentWidget(self.project_management_widget_instance)

            # 3. Call focus_on_project on the dashboard instance
            if hasattr(self.project_management_widget_instance, 'focus_on_project'):
                self.project_management_widget_instance.focus_on_project(project_id_to_focus)
            else:
                # Fallback: just switch to the dashboard if focus method isn't there
                print("Warning: focus_on_project method not found on dashboard instance.")
        else:
            self.show_notification(self.tr("Project Not Found"),
                                   self.tr("No project linked to client ID {0} was found in the project management module.").format(client_id),
                                   duration=10000)

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
                self.show_notification(self.tr("Erreur Configuration"), self.tr("Statut 'Archivé' non trouvé. Veuillez configurer les statuts."), duration=8000)
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
                self.show_notification(self.tr("Client Archivé"), self.tr("Le client '{0}' a été archivé.").format(self.clients_data_map[client_id_val]['client_name']))
            else:
                self.show_notification(self.tr("Erreur DB"), self.tr("Erreur d'archivage du client. Vérifiez les logs."), duration=8000)
        except Exception as e:
            self.show_notification(self.tr("Erreur DB"), self.tr("Erreur d'archivage du client: {0}").format(str(e)), duration=10000)


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
                    self.show_notification(self.tr("Client Supprimé"), self.tr("Client '{0}' supprimé avec succès.").format(client_name_val))
                else:
                    # Keep critical for actual DB delete failure
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur lors de la suppression du client de la base de données. Le dossier n'a pas été supprimé."))
            except OSError as e_os:
                QMessageBox.critical(self, self.tr("Erreur Dossier"), self.tr("Le client a été supprimé de la base de données, mais une erreur est survenue lors de la suppression de son dossier:
{0}").format(str(e_os)))
                if client_id_val in self.clients_data_map: # Ensure it's still there if DB part was done
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
            self.show_notification(self.tr("Paramètres Sauvegardés"), self.tr("Nouveaux paramètres enregistrés."))

    def open_template_manager_dialog(self):
        TemplateDialog(self).exec_()

    def open_status_manager_dialog(self):
        QMessageBox.information(self, self.tr("Gestion des Statuts"), self.tr("Fonctionnalité de gestion des statuts personnalisés à implémenter (e.g., via un nouveau QDialog)."))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'notification_banner') and self.notification_banner.isVisible():
            banner = self.notification_banner
            parent_width = self.width()
            banner_width = banner.width()
            x = parent_width - banner_width - 10
            # Adjust y; consider menubar height if it exists and is visible
            y_offset = self.menuBar().height() + 5 if self.menuBar() and self.menuBar().isVisible() else 10
            banner.move(x, y_offset)

    def show_notification(self, title, message, duration=7000):
        if not hasattr(self, 'notification_banner'):
            return

        self.notification_banner.set_message(title, message)

        parent_width = self.width()
        banner_width = self.notification_banner.width()
        x = parent_width - banner_width - 10
        y_offset = self.menuBar().height() + 5 if self.menuBar() and self.menuBar().isVisible() else 10
        self.notification_banner.move(x, y_offset)

        self.notification_banner.show()
        self.notification_banner.raise_()
        QTimer.singleShot(duration, self.notification_banner.hide)

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
        tabs_widget.setStyleSheet(get_tab_widget_style()) # Apply TabWidget style

        general_tab_widget = QWidget(); general_form_layout = QFormLayout(general_tab_widget)
        self.templates_dir_input = QLineEdit(self.current_config_data["templates_dir"])
        self.templates_dir_input.setStyleSheet(get_generic_input_style())
        templates_browse_btn = QPushButton(self.tr("Parcourir...")); templates_browse_btn.clicked.connect(lambda: self.browse_directory_for_input(self.templates_dir_input, self.tr("Sélectionner dossier modèles")))
        templates_browse_btn.setStyleSheet(get_small_button_style()) # Example of secondary/small button
        templates_dir_layout = QHBoxLayout(); templates_dir_layout.addWidget(self.templates_dir_input); templates_dir_layout.addWidget(templates_browse_btn)
        general_form_layout.addRow(self.tr("Dossier des Modèles:"), templates_dir_layout)

        self.clients_dir_input = QLineEdit(self.current_config_data["clients_dir"])
        self.clients_dir_input.setStyleSheet(get_generic_input_style())
        clients_browse_btn = QPushButton(self.tr("Parcourir...")); clients_browse_btn.clicked.connect(lambda: self.browse_directory_for_input(self.clients_dir_input, self.tr("Sélectionner dossier clients")))
        clients_browse_btn.setStyleSheet(get_small_button_style())
        clients_dir_layout = QHBoxLayout(); clients_dir_layout.addWidget(self.clients_dir_input); clients_dir_layout.addWidget(clients_browse_btn)
        general_form_layout.addRow(self.tr("Dossier des Clients:"), clients_dir_layout)

        self.interface_lang_combo = QComboBox()
        self.interface_lang_combo.setStyleSheet(get_generic_input_style())
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
        self.reminder_days_spinbox.setStyleSheet(get_generic_input_style())
        general_form_layout.addRow(self.tr("Jours avant rappel client ancien:"), self.reminder_days_spinbox)
        tabs_widget.addTab(general_tab_widget, self.tr("Général"))

        email_tab_widget = QWidget(); email_form_layout = QFormLayout(email_tab_widget)
        self.smtp_server_input_field = QLineEdit(self.current_config_data.get("smtp_server", ""))
        self.smtp_server_input_field.setStyleSheet(get_generic_input_style())
        email_form_layout.addRow(self.tr("Serveur SMTP:"), self.smtp_server_input_field)

        self.smtp_port_spinbox = QSpinBox(); self.smtp_port_spinbox.setRange(1, 65535)
        self.smtp_port_spinbox.setValue(self.current_config_data.get("smtp_port", 587))
        self.smtp_port_spinbox.setStyleSheet(get_generic_input_style())
        email_form_layout.addRow(self.tr("Port SMTP:"), self.smtp_port_spinbox)

        self.smtp_user_input_field = QLineEdit(self.current_config_data.get("smtp_user", ""))
        self.smtp_user_input_field.setStyleSheet(get_generic_input_style())
        email_form_layout.addRow(self.tr("Utilisateur SMTP:"), self.smtp_user_input_field)

        self.smtp_pass_input_field = QLineEdit(self.current_config_data.get("smtp_password", ""))
        self.smtp_pass_input_field.setEchoMode(QLineEdit.Password)
        self.smtp_pass_input_field.setStyleSheet(get_generic_input_style())
        email_form_layout.addRow(self.tr("Mot de passe SMTP:"), self.smtp_pass_input_field)
        tabs_widget.addTab(email_tab_widget, self.tr("Email"))

        dialog_button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = dialog_button_box.button(QDialogButtonBox.Ok)
        ok_button.setText(self.tr("OK"))
        ok_button.setStyleSheet(get_primary_button_style()) # Apply primary style to OK

        cancel_button = dialog_button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText(self.tr("Annuler"))
        # Default button style will apply or you can set a secondary style:
        # cancel_button.setStyleSheet(get_secondary_button_style())

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
    # Set default font for the entire application
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)


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

    # HTML Templates Metadata and Registration
    html_templates_metadata = [
        {
            'base_file_name': "proforma_invoice_template.html",
            'template_type': "HTML_PROFORMA",
            'fr_name': "Facture Proforma", # Base name, lang will be added
            'fr_description': "Modèle HTML pour factures proforma.",
            'category_name': "Documents HTML"
        },
        {
            'base_file_name': "packing_list_template.html",
            'template_type': "HTML_PACKING_LIST",
            'fr_name': "Liste de Colisage",
            'fr_description': "Modèle HTML pour listes de colisage.",
            'category_name': "Documents HTML"
        },
        {
            'base_file_name': "sales_contract_template.html",
            'template_type': "HTML_SALES_CONTRACT",
            'fr_name': "Contrat de Vente",
            'fr_description': "Modèle HTML pour contrats de vente.",
            'category_name': "Documents HTML"
        },
        {
            'base_file_name': "warranty_document_template.html",
            'template_type': "HTML_WARRANTY",
            'fr_name': "Document de Garantie",
            'fr_description': "Modèle HTML pour documents de garantie.",
            'category_name': "Documents HTML"
        },
        {
            'base_file_name': "cover_page_template.html",
            'template_type': "HTML_COVER_PAGE",
            'fr_name': "Page de Garde",
            'fr_description': "Modèle HTML pour pages de garde de documents.",
            'category_name': "Documents HTML"
        }
    ]

    html_template_languages = ["fr", "en", "ar", "tr", "pt"]
    templates_root_dir_for_html = CONFIG["templates_dir"] # Assuming this is the same root

    print("\n--- Starting HTML Template Registration ---")
    for template_meta in html_templates_metadata:
        for lang_code in html_template_languages:
            template_full_path = os.path.join(templates_root_dir_for_html, lang_code, template_meta['base_file_name'])

            if os.path.exists(template_full_path):
                # Construct a unique name for DB, including type and language
                # e.g., "Facture Proforma (HTML) (FR)"
                db_template_name = f"{template_meta['fr_name']} (HTML) ({lang_code.upper()})"

                template_data_for_db = {
                    'template_name': db_template_name,
                    'template_type': template_meta['template_type'], # This is the unique type identifier
                    'language_code': lang_code,
                    'base_file_name': template_meta['base_file_name'],
                    'description': template_meta['fr_description'], # Could be translated later if needed
                    'category_name': template_meta['category_name'], # All HTML templates go to this category
                    'is_default_for_type_lang': True if lang_code == 'fr' else False # FR is default for its type
                }

                # Ensure add_default_template_if_not_exists can handle 'category_name'
                # by resolving it to 'category_id' internally or that we pass 'category_id'
                # db_manager.add_default_template_if_not_exists expects 'category_name'
                template_id = db_manager.add_default_template_if_not_exists(template_data_for_db)
                if template_id:
                    print(f"SUCCESS: HTML Template '{db_template_name}' (Type: {template_meta['template_type']}, Lang: {lang_code}) processed. DB ID: {template_id}")
                else:
                    # This message could mean it already exists and was skipped, or an actual error.
                    # The db_manager function should ideally differentiate. For now, assume it handles existing gracefully.
                    print(f"INFO: HTML Template '{db_template_name}' (Type: {template_meta['template_type']}, Lang: {lang_code}) processing complete (may already exist or error occurred).")
            else:
                print(f"SKIP: HTML Template file not found at '{template_full_path}'. Cannot register.")
    print("--- HTML Template Registration Finished ---")

    main_window = DocumentManager()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main_app_entry_point()
