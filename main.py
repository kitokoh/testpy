# -*- coding: utf-8 -*-
import sys
import os
import json
import sqlite3
import pandas as pd
import shutil
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QListWidget,
    QFileDialog, QMessageBox, QDialog, QFormLayout, QComboBox,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QInputDialog, QSplitter,
    QCompleter, QTabWidget, QAction, QMenu, QToolBar, QGroupBox,
    QCheckBox, QDateEdit, QSpinBox, QStackedWidget, QListWidgetItem,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QGridLayout
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QColor, QBrush, QPixmap
from PyQt5.QtCore import Qt, QUrl, QStandardPaths, QSettings, QDir, QDate, QTimer
from PyPDF2 import PdfWriter, PdfReader, PdfMerger
from reportlab.pdfgen import canvas
import io
from PyQt5.QtWidgets import QDoubleSpinBox
from excel_editor import ExcelEditor
from PyQt5.QtWidgets import QBoxLayout

# --- Configuration & Database ---
CONFIG_DIR_NAME = "ClientDocumentManager"
CONFIG_FILE_NAME = "config.json"
DATABASE_NAME = "" 
TEMPLATES_SUBDIR = "templates"
CLIENTS_SUBDIR = "clients"
SPEC_TECH_TEMPLATE_NAME = "specification_technique_template.xlsx"
PROFORMA_TEMPLATE_NAME = "proforma_template.xlsx"
CONTRAT_VENTE_TEMPLATE_NAME = "contrat_vente_template.xlsx"
PACKING_LISTE_TEMPLATE_NAME = "packing_liste_template.xlsx"

if getattr(sys, 'frozen', False):
    APP_ROOT_DIR = sys._MEIPASS
else:
    APP_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_TEMPLATES_DIR = os.path.join(APP_ROOT_DIR, TEMPLATES_SUBDIR)
DEFAULT_CLIENTS_DIR = os.path.join(APP_ROOT_DIR, CLIENTS_SUBDIR)

def get_config_dir():
    config_dir_path = os.path.join(
        QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation), 
        CONFIG_DIR_NAME
    )
    os.makedirs(config_dir_path, exist_ok=True)
    return config_dir_path

def get_config_file_path():
    return os.path.join(get_config_dir(), CONFIG_FILE_NAME)

def init_database():
    global DATABASE_NAME 
    db_path = os.path.join(get_config_dir(), "client_manassgessr.db") 
    DATABASE_NAME = db_path 
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
        """CREATE TABLE IF NOT EXISTS Clients (
            client_id TEXT PRIMARY KEY,
            client_name TEXT NOT NULL,
            company_name TEXT,
            need TEXT,
            country TEXT,
            city TEXT,
            project_identifier TEXT NOT NULL,
            base_folder_path TEXT NOT NULL UNIQUE,
            status TEXT DEFAULT 'En cours',
            selected_languages TEXT,
            price REAL DEFAULT 0,
            notes TEXT,
            creation_date TEXT,
            last_modified TEXT,
            category TEXT DEFAULT 'Standard',
            primary_contact TEXT
        );"""
        )
        
        cursor.execute(
        """CREATE TABLE IF NOT EXISTS Countries (
            country_id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_name TEXT NOT NULL UNIQUE
        );"""
        )
        
        cursor.execute(
        """CREATE TABLE IF NOT EXISTS Cities (
            city_id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_id INTEGER NOT NULL REFERENCES Countries(country_id),
            city_name TEXT NOT NULL,
            UNIQUE(country_id, city_name)
        );"""
        )
        
        cursor.execute(
        """CREATE TABLE IF NOT EXISTS Contacts (
            contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL REFERENCES Clients(client_id),
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            position TEXT,
            is_primary INTEGER DEFAULT 0
        );"""
        )
        
        cursor.execute(
        """CREATE TABLE IF NOT EXISTS Templates (
            template_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            file_name TEXT NOT NULL,
            language TEXT NOT NULL,
            is_default INTEGER DEFAULT 0,
            category TEXT
        );"""
        )
        
        cursor.execute(
        """CREATE TABLE IF NOT EXISTS StatusSettings (
            status_id INTEGER PRIMARY KEY AUTOINCREMENT,
            status_name TEXT NOT NULL UNIQUE,
            default_days INTEGER NOT NULL,
            color TEXT
        );"""
        )

        cursor.execute(
        """CREATE TABLE IF NOT EXISTS ClientProducts (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL REFERENCES Clients(client_id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT,
            quantity REAL DEFAULT 0,
            unit_price REAL DEFAULT 0,
            total_price REAL DEFAULT 0
        );"""
        )
        
        cursor.execute("SELECT COUNT(*) FROM Countries")
        if cursor.fetchone()[0] == 0:
            initial_countries = [
                "France", "Sénégal", "Turquie", "Maroc", "Algérie", 
                "Allemagne", "Belgique", "Canada", "Suisse", 
                "Royaume-Uni", "États-Unis"
            ]
            for country in initial_countries:
                try:
                    cursor.execute("INSERT INTO Countries (country_name) VALUES (?)", (country,))
                except sqlite3.IntegrityError:
                    pass
        
        cursor.execute("SELECT COUNT(*) FROM StatusSettings")
        if cursor.fetchone()[0] == 0:
            statuses = [
                ("En cours", 30, "#3498db"),
                ("Archivé", 365, "#95a5a6"),
                ("Urgent", 7, "#e74c3c"),
                ("Complété", 0, "#2ecc71"),
                ("En attente", 15, "#f39c12")
            ]
            for status_item in statuses: 
                cursor.execute(
                    "INSERT INTO StatusSettings (status_name, default_days, color) VALUES (?, ?, ?)",
                    status_item
                )
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
        QMessageBox.critical(
            None, 
            "Erreur Base de Données", 
            f"Impossible d'initialiser la base de données: {e}\nL'application pourrait ne pas fonctionner correctement."
        )
    finally:
        if conn:
            conn.close()
    return db_path 

DATABASE_NAME = init_database() 

def load_config():
    config_path = get_config_file_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading config: {e}. Using defaults.")
    
    return {
        "templates_dir": DEFAULT_TEMPLATES_DIR,
        "clients_dir": DEFAULT_CLIENTS_DIR,
        "language": "fr",
        "smtp_server": "",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": "",
        "default_reminder_days": 30
    }

def save_config(config_data):
    try:
        config_path = get_config_file_path()
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        QMessageBox.warning(None, "Erreur de Configuration", f"Impossible d'enregistrer la configuration: {e}")

CONFIG = load_config()

os.makedirs(CONFIG["templates_dir"], exist_ok=True)
os.makedirs(CONFIG["clients_dir"], exist_ok=True)

class ContactDialog(QDialog):
    def __init__(self, client_id=None, contact_data=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.contact_data = contact_data or {}
        self.setWindowTitle("Gestion des Contacts" if not contact_data else "Modifier Contact")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit(self.contact_data.get("name", ""))
        layout.addRow("Nom complet:", self.name_input)
        
        self.email_input = QLineEdit(self.contact_data.get("email", ""))
        layout.addRow("Email:", self.email_input)
        
        self.phone_input = QLineEdit(self.contact_data.get("phone", ""))
        layout.addRow("Téléphone:", self.phone_input)
        
        self.position_input = QLineEdit(self.contact_data.get("position", ""))
        layout.addRow("Poste:", self.position_input)
        
        self.primary_check = QCheckBox("Contact principal")
        self.primary_check.setChecked(bool(self.contact_data.get("is_primary", 0)))
        layout.addRow(self.primary_check)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
        
    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "email": self.email_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "position": self.position_input.text().strip(),
            "is_primary": 1 if self.primary_check.isChecked() else 0
        }

class TemplateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestion des Modèles")
        self.setMinimumSize(600, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.template_list = QListWidget()
        self.template_list.itemDoubleClicked.connect(self.edit_template)
        layout.addWidget(self.template_list)
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter Modèle")
        self.add_btn.setIcon(QIcon.fromTheme("list-add"))
        self.add_btn.clicked.connect(self.add_template)
        btn_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("Modifier")
        self.edit_btn.setIcon(QIcon.fromTheme("document-edit"))
        self.edit_btn.clicked.connect(self.edit_template)
        btn_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Supprimer")
        self.delete_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.delete_btn.clicked.connect(self.delete_template)
        btn_layout.addWidget(self.delete_btn)
        
        self.default_btn = QPushButton("Définir par Défaut")
        self.default_btn.setIcon(QIcon.fromTheme("emblem-default"))
        self.default_btn.clicked.connect(self.set_default_template)
        btn_layout.addWidget(self.default_btn)
        
        layout.addLayout(btn_layout)
        self.load_templates()
        
    def load_templates(self):
        self.template_list.clear()
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT template_id, name, language, is_default FROM Templates ORDER BY name, language")
            for row in cursor.fetchall():
                item = QListWidgetItem(f"{row[1]} ({row[2]}) {'[Défaut]' if row[3] else ''}")
                item.setData(Qt.UserRole, row[0]) 
                self.template_list.addItem(item)
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Erreur DB", f"Erreur de chargement des modèles:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def add_template(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Sélectionner un modèle", CONFIG["templates_dir"], "Fichiers Excel (*.xlsx);;Tous les fichiers (*)")
        if not file_path: return
            
        name, ok = QInputDialog.getText(self, "Nom du Modèle", "Entrez un nom pour ce modèle:")
        if not ok or not name.strip(): return
            
        languages = ["fr", "ar", "tr"]
        lang, ok = QInputDialog.getItem(self, "Langue du Modèle", "Sélectionnez la langue:", languages, 0, False)
        if not ok: return
            
        target_dir = os.path.join(CONFIG["templates_dir"], lang)
        os.makedirs(target_dir, exist_ok=True)
        base_file_name = os.path.basename(file_path) 
        target_path = os.path.join(target_dir, base_file_name) 
        conn = None
        try:
            shutil.copy(file_path, target_path)
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Templates (name, file_name, language, is_default) VALUES (?, ?, ?, 0)",
                (name.strip(), base_file_name, lang) 
            )
            conn.commit()
            self.load_templates()
            QMessageBox.information(self, "Succès", "Modèle ajouté avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'ajout du modèle:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def edit_template(self): 
        item = self.template_list.currentItem()
        if not item: return
        template_id = item.data(Qt.UserRole)
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT file_name, language FROM Templates WHERE template_id = ?", (template_id,))
            result = cursor.fetchone()
            if result:
                file_path = os.path.join(CONFIG["templates_dir"], result[1], result[0]) 
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Erreur DB", f"Erreur d'accès au modèle:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def delete_template(self):
        item = self.template_list.currentItem()
        if not item: return
        template_id = item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self,
            "Confirmer Suppression",
            "Êtes-vous sûr de vouloir supprimer ce modèle ?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            conn = None
            try:
                conn = sqlite3.connect(DATABASE_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT file_name, language FROM Templates WHERE template_id = ?", (template_id,))
                result = cursor.fetchone()
                cursor.execute("DELETE FROM Templates WHERE template_id = ?", (template_id,))
                conn.commit()
                if result:
                    file_path = os.path.join(CONFIG["templates_dir"], result[1], result[0])
                    if os.path.exists(file_path): os.remove(file_path)
                self.load_templates()
                QMessageBox.information(self, "Succès", "Modèle supprimé avec succès.")
            except Exception as e: 
                QMessageBox.critical(self, "Erreur", f"Erreur de suppression du modèle:\n{str(e)}")
            finally:
                if conn: conn.close()
                
    def set_default_template(self):
        item = self.template_list.currentItem()
        if not item: return
        template_id = item.data(Qt.UserRole)
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM Templates WHERE template_id = ?", (template_id,))
            name_result = cursor.fetchone()
            if not name_result: return
            base_name = name_result[0] 
            
            cursor.execute("UPDATE Templates SET is_default = 0 WHERE name = ?", (base_name,))
            cursor.execute("UPDATE Templates SET is_default = 1 WHERE template_id = ?", (template_id,))
            conn.commit()
            self.load_templates()
            QMessageBox.information(self, "Succès", "Modèle défini comme modèle par défaut pour sa catégorie et langue.")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Erreur DB", f"Erreur de mise à jour du modèle:\n{str(e)}")
        finally:
            if conn: conn.close()

class ProductDialog(QDialog):
    def __init__(self, client_id, product_data=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.product_data = product_data or {}
        self.setWindowTitle("Ajouter Produit" if not self.product_data else "Modifier Produit")
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)

        self.name_input = QLineEdit(self.product_data.get("name", ""))
        layout.addRow("Nom du Produit:", self.name_input)

        self.description_input = QTextEdit(self.product_data.get("description", ""))
        self.description_input.setFixedHeight(80)
        layout.addRow("Description:", self.description_input)

        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0, 1000000)
        self.quantity_input.setValue(self.product_data.get("quantity", 0))
        self.quantity_input.valueChanged.connect(self.update_total_price)
        layout.addRow("Quantité:", self.quantity_input)

        self.unit_price_input = QDoubleSpinBox()
        self.unit_price_input.setRange(0, 10000000)
        self.unit_price_input.setPrefix("€ ")
        self.unit_price_input.setValue(self.product_data.get("unit_price", 0))
        self.unit_price_input.valueChanged.connect(self.update_total_price)
        layout.addRow("Prix Unitaire:", self.unit_price_input)
        
        total_price_title_label = QLabel("Prix Total:")
        self.total_price_label = QLabel("€ 0.00")
        self.total_price_label.setStyleSheet("font-weight: bold;")
        layout.addRow(total_price_title_label, self.total_price_label)

        if self.product_data:
            self.update_total_price()

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def update_total_price(self):
        quantity = self.quantity_input.value()
        unit_price = self.unit_price_input.value()
        total = quantity * unit_price
        self.total_price_label.setText(f"€ {total:.2f}")

    def get_data(self):
        return {
            "client_id": self.client_id,
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "quantity": self.quantity_input.value(),
            "unit_price": self.unit_price_input.value(),
            "total_price": self.quantity_input.value() * self.unit_price_input.value()
        }

class CreateDocumentDialog(QDialog):
    def __init__(self, client_info, config, parent=None):
        super().__init__(parent)
        self.client_info = client_info
        self.config = config
        self.setWindowTitle("Créer des Documents")
        self.setMinimumSize(600, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Langue sélection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Langue:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(self.client_info.get("selected_languages", ["fr"]))
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)
        
        # Liste des templates
        self.templates_list = QListWidget()
        self.templates_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(QLabel("Sélectionnez les documents à créer:"))
        layout.addWidget(self.templates_list)
        
        self.load_templates()
        
        # Boutons
        btn_layout = QHBoxLayout()
        create_btn = QPushButton("Créer Documents")
        create_btn.setIcon(QIcon.fromTheme("document-new"))
        create_btn.clicked.connect(self.create_documents)
        btn_layout.addWidget(create_btn)
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setIcon(QIcon.fromTheme("dialog-cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
    def load_templates(self):
        self.templates_list.clear()
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT name, language FROM Templates ORDER BY name")
            for name, lang in cursor.fetchall():
                item = QListWidgetItem(f"{name} ({lang})")
                item.setData(Qt.UserRole, (name, lang))
                self.templates_list.addItem(item)
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Erreur DB", f"Erreur de chargement des modèles:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def create_documents(self):
        selected_items = self.templates_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Aucun document sélectionné", "Veuillez sélectionner au moins un document à créer.")
            return
            
        lang = self.lang_combo.currentText()
        target_dir = os.path.join(self.client_info["base_folder_path"], lang)
        os.makedirs(target_dir, exist_ok=True)
        
        created_files = []
        
        for item in selected_items:
            template_name, template_lang = item.data(Qt.UserRole)
            
            # Trouver le fichier template
            template_file = None
            template_path = os.path.join(self.config["templates_dir"], template_lang, f"{template_name}.xlsx")
            if os.path.exists(template_path):
                template_file = template_path
            else:
                # Chercher dans tous les fichiers de la langue
                lang_dir = os.path.join(self.config["templates_dir"], template_lang)
                for f in os.listdir(lang_dir):
                    if f.endswith(".xlsx"):
                        template_file = os.path.join(lang_dir, f)
                        break
            
            if template_file:
                target_path = os.path.join(target_dir, f"{template_name}.xlsx")
                shutil.copy(template_file, target_path)
                created_files.append(target_path)
        
        if created_files:
            QMessageBox.information(self, "Documents créés", f"{len(created_files)} documents ont été créés avec succès.")
            self.accept()
        else:
            QMessageBox.warning(self, "Erreur", "Aucun document n'a pu être créé.")

class CompilePdfDialog(QDialog):
    def __init__(self, client_info, parent=None):
        super().__init__(parent)
        self.client_info = client_info
        self.setWindowTitle("Compiler des PDF")
        self.setMinimumSize(700, 500)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Liste des PDF disponibles
        layout.addWidget(QLabel("Sélectionnez les PDF à compiler:"))
        self.pdf_list = QTableWidget()
        self.pdf_list.setColumnCount(4)
        self.pdf_list.setHorizontalHeaderLabels(["Sélection", "Nom du fichier", "Chemin", "Pages (ex: 1-3,5)"])
        self.pdf_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.pdf_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.pdf_list)
        
        # Boutons de contrôle
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Ajouter PDF")
        add_btn.setIcon(QIcon.fromTheme("list-add"))
        add_btn.clicked.connect(self.add_pdf)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Supprimer")
        remove_btn.setIcon(QIcon.fromTheme("edit-delete"))
        remove_btn.clicked.connect(self.remove_selected)
        btn_layout.addWidget(remove_btn)
        
        move_up_btn = QPushButton("Monter")
        move_up_btn.setIcon(QIcon.fromTheme("go-up"))
        move_up_btn.clicked.connect(self.move_up)
        btn_layout.addWidget(move_up_btn)
        
        move_down_btn = QPushButton("Descendre")
        move_down_btn.setIcon(QIcon.fromTheme("go-down"))
        move_down_btn.clicked.connect(self.move_down)
        btn_layout.addWidget(move_down_btn)
        
        layout.addLayout(btn_layout)
        
        # Options de compilation
        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel("Nom du fichier compilé:"))
        self.output_name = QLineEdit(f"compilation_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
        options_layout.addWidget(self.output_name)
        layout.addLayout(options_layout)
        
        # Boutons d'action
        action_layout = QHBoxLayout()
        compile_btn = QPushButton("Compiler PDF")
        compile_btn.setIcon(QIcon.fromTheme("document-export"))
        compile_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        compile_btn.clicked.connect(self.compile_pdf)
        action_layout.addWidget(compile_btn)
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setIcon(QIcon.fromTheme("dialog-cancel"))
        cancel_btn.clicked.connect(self.reject)
        action_layout.addWidget(cancel_btn)
        
        layout.addLayout(action_layout)
        
        self.load_existing_pdfs()
        
    def load_existing_pdfs(self):
        client_dir = self.client_info["base_folder_path"]
        pdf_files = []
        
        for root, dirs, files in os.walk(client_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        
        self.pdf_list.setRowCount(len(pdf_files))
        
        for i, file_path in enumerate(pdf_files):
            # Checkbox de sélection
            chk = QCheckBox()
            chk.setChecked(True)
            self.pdf_list.setCellWidget(i, 0, chk)
            
            # Nom du fichier
            self.pdf_list.setItem(i, 1, QTableWidgetItem(os.path.basename(file_path)))
            
            # Chemin complet
            self.pdf_list.setItem(i, 2, QTableWidgetItem(file_path))
            
            # Champ pour les pages
            pages_edit = QLineEdit("all")
            pages_edit.setPlaceholderText("all ou 1-3,5")
            self.pdf_list.setCellWidget(i, 3, pages_edit)
    
    def add_pdf(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Sélectionner des PDF", "", "Fichiers PDF (*.pdf)")
        if not file_paths:
            return
            
        current_row_count = self.pdf_list.rowCount()
        self.pdf_list.setRowCount(current_row_count + len(file_paths))
        
        for i, file_path in enumerate(file_paths):
            row = current_row_count + i
            
            # Checkbox de sélection
            chk = QCheckBox()
            chk.setChecked(True)
            self.pdf_list.setCellWidget(row, 0, chk)
            
            # Nom du fichier
            self.pdf_list.setItem(row, 1, QTableWidgetItem(os.path.basename(file_path)))
            
            # Chemin complet
            self.pdf_list.setItem(row, 2, QTableWidgetItem(file_path))
            
            # Champ pour les pages
            pages_edit = QLineEdit("all")
            pages_edit.setPlaceholderText("all ou 1-3,5")
            self.pdf_list.setCellWidget(row, 3, pages_edit)
    
    def remove_selected(self):
        selected_rows = set(index.row() for index in self.pdf_list.selectedIndexes())
        for row in sorted(selected_rows, reverse=True):
            self.pdf_list.removeRow(row)
    
    def move_up(self):
        current_row = self.pdf_list.currentRow()
        if current_row > 0:
            self.swap_rows(current_row, current_row - 1)
            self.pdf_list.setCurrentCell(current_row - 1, 0)
    
    def move_down(self):
        current_row = self.pdf_list.currentRow()
        if current_row < self.pdf_list.rowCount() - 1:
            self.swap_rows(current_row, current_row + 1)
            self.pdf_list.setCurrentCell(current_row + 1, 0)
    
    def swap_rows(self, row1, row2):
        for col in range(self.pdf_list.columnCount()):
            item1 = self.pdf_list.takeItem(row1, col)
            item2 = self.pdf_list.takeItem(row2, col)
            
            self.pdf_list.setItem(row1, col, item2)
            self.pdf_list.setItem(row2, col, item1)
            
        # Swap des widgets
        widget1 = self.pdf_list.cellWidget(row1, 0)
        widget3 = self.pdf_list.cellWidget(row1, 3)
        widget2 = self.pdf_list.cellWidget(row2, 0)
        widget4 = self.pdf_list.cellWidget(row2, 3)
        
        self.pdf_list.setCellWidget(row1, 0, widget2)
        self.pdf_list.setCellWidget(row1, 3, widget4)
        self.pdf_list.setCellWidget(row2, 0, widget1)
        self.pdf_list.setCellWidget(row2, 3, widget3)
    
    def compile_pdf(self):
        merger = PdfMerger()
        output_name = self.output_name.text().strip()
        if not output_name:
            QMessageBox.warning(self, "Nom manquant", "Veuillez spécifier un nom de fichier pour la compilation.")
            return
            
        if not output_name.lower().endswith('.pdf'):
            output_name += '.pdf'
            
        output_path = os.path.join(self.client_info["base_folder_path"], output_name)
        
        # Créer une page de garde
        cover_path = self.create_cover_page()
        if cover_path:
            merger.append(cover_path)
        
        # Ajouter les PDF sélectionnés
        for row in range(self.pdf_list.rowCount()):
            chk = self.pdf_list.cellWidget(row, 0)
            if chk and chk.isChecked():
                file_path = self.pdf_list.item(row, 2).text()
                pages_spec = self.pdf_list.cellWidget(row, 3).text().strip()
                
                try:
                    if pages_spec.lower() == "all" or not pages_spec:
                        merger.append(file_path)
                    else:
                        # Gestion des plages de pages (ex: "1-3,5")
                        pages = []
                        for part in pages_spec.split(','):
                            if '-' in part:
                                start, end = part.split('-')
                                pages.extend(range(int(start), int(end)+1))
                            else:
                                pages.append(int(part))
                        
                        merger.append(file_path, pages=pages)
                except Exception as e:
                    QMessageBox.warning(self, "Erreur", f"Erreur lors de l'ajout de {os.path.basename(file_path)}:\n{str(e)}")
        
        # Sauvegarder le PDF compilé
        try:
            with open(output_path, 'wb') as f:
                merger.write(f)
            
            # Supprimer la page de garde temporaire
            if cover_path and os.path.exists(cover_path):
                os.remove(cover_path)
                
            QMessageBox.information(self, "Compilation réussie", f"Le PDF compilé a été sauvegardé dans:\n{output_path}")
            
            # Proposer de télécharger ou envoyer par email
            self.offer_download_or_email(output_path)
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la compilation du PDF:\n{str(e)}")
    
    def create_cover_page(self):
        try:
            # Créer une page de garde simple
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(595.27, 841.89))  # A4
            
            # Logo (si disponible)
            logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
            if os.path.exists(logo_path):
                can.drawImage(logo_path, 50, 700, width=100, height=50, preserveAspectRatio=True)
            
            # Titre
            can.setFont("Helvetica-Bold", 24)
            can.drawCentredString(297, 650, "Compilation de Documents")
            
            # Informations client
            can.setFont("Helvetica", 14)
            can.drawString(100, 600, f"Client: {self.client_info['client_name']}")
            can.drawString(100, 570, f"Projet: {self.client_info['project_identifier']}")
            can.drawString(100, 540, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            # Signature
            can.setFont("Helvetica-Oblique", 12)
            can.drawString(400, 100, "Signature:")
            can.line(400, 90, 500, 90)
            
            can.save()
            
            # Sauvegarder dans un fichier temporaire
            temp_path = os.path.join(self.client_info["base_folder_path"], "cover_temp.pdf")
            with open(temp_path, "wb") as f:
                f.write(packet.getbuffer())
                
            return temp_path
        except Exception as e:
            print(f"Erreur création page de garde: {str(e)}")
            return None
    
    def offer_download_or_email(self, pdf_path):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Compilation réussie")
        msg_box.setText(f"Le PDF compilé a été sauvegardé dans:\n{pdf_path}")
        
        download_btn = msg_box.addButton("Télécharger", QMessageBox.ActionRole)
        email_btn = msg_box.addButton("Envoyer par email", QMessageBox.ActionRole)
        close_btn = msg_box.addButton("Fermer", QMessageBox.RejectRole)
        
        msg_box.exec_()
        
        if msg_box.clickedButton() == download_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
        elif msg_box.clickedButton() == email_btn:
            self.send_email(pdf_path)
    
    def send_email(self, pdf_path):
        # Trouver l'email principal du client
        primary_email = None
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT email FROM Contacts WHERE client_id = ? AND is_primary = 1", 
                          (self.client_info["client_id"],))
            result = cursor.fetchone()
            if result:
                primary_email = result[0]
        except sqlite3.Error as e:
            print(f"Erreur DB recherche email: {str(e)}")
        finally:
            if conn: conn.close()
        
        # Demander l'adresse email
        email, ok = QInputDialog.getText(
            self, 
            "Envoyer par email", 
            "Adresse email du destinataire:", 
            text=primary_email or ""
        )
        
        if not ok or not email.strip():
            return
            
        # Config SMTP
        config = load_config()
        if not config.get("smtp_server") or not config.get("smtp_user"):
            QMessageBox.warning(self, "Configuration manquante", "Veuillez configurer les paramètres SMTP dans les paramètres de l'application.")
            return
            
        # Préparer l'email
        msg = MIMEMultipart()
        msg['From'] = config["smtp_user"]
        msg['To'] = email
        msg['Subject'] = f"Documents compilés - {self.client_info['client_name']}"
        
        body = f"Bonjour,\n\nVeuillez trouver ci-joint les documents compilés pour le projet {self.client_info['project_identifier']}.\n\nCordialement,\nVotre équipe"
        msg.attach(MIMEText(body, 'plain'))
        
        with open(pdf_path, 'rb') as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'
        msg.attach(part)
        
        # Envoyer l'email
        try:
            server = smtplib.SMTP(config["smtp_server"], config.get("smtp_port", 587))
            if config.get("smtp_port", 587) == 587:
                server.starttls()
            server.login(config["smtp_user"], config["smtp_password"])
            server.send_message(msg)
            server.quit()
            QMessageBox.information(self, "Email envoyé", "Le document a été envoyé avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur d'envoi", f"Erreur lors de l'envoi de l'email:\n{str(e)}")

class ClientWidget(QWidget):
    def __init__(self, client_info, config, parent=None): 
        super().__init__(parent)
        self.client_info = client_info
        self.config = config 
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # En-tête
        header = QLabel(f"<h2>{self.client_info['client_name']}</h2>")
        header.setStyleSheet("color: #2c3e50;") 
        layout.addWidget(header)
        
        # Barre d'actions
        action_layout = QHBoxLayout()
        
        # Bouton pour créer des documents
        self.create_docs_btn = QPushButton("Créer Documents")
        self.create_docs_btn.setIcon(QIcon.fromTheme("document-new"))
        self.create_docs_btn.setStyleSheet("background-color: #3498db; color: white;")
        self.create_docs_btn.clicked.connect(self.open_create_docs_dialog)
        action_layout.addWidget(self.create_docs_btn)
        
        # Bouton pour compiler PDF
        self.compile_pdf_btn = QPushButton("Compiler PDF")
        self.compile_pdf_btn.setIcon(QIcon.fromTheme("document-export"))
        self.compile_pdf_btn.setStyleSheet("background-color: #27ae60; color: white;")
        self.compile_pdf_btn.clicked.connect(self.open_compile_pdf_dialog)
        action_layout.addWidget(self.compile_pdf_btn)
        
        layout.addLayout(action_layout)
        
        # Statut
        status_layout = QHBoxLayout()
        status_label = QLabel("Statut:")
        status_layout.addWidget(status_label)
        self.status_combo = QComboBox()
        self.load_statuses()
        self.status_combo.setCurrentText(self.client_info.get("status", "En cours"))
        self.status_combo.currentTextChanged.connect(self.update_client_status)
        status_layout.addWidget(self.status_combo)
        layout.addLayout(status_layout)
        
        # Détails client
        details_layout = QFormLayout()
        details_layout.setLabelAlignment(Qt.AlignRight)
        details = [
            ("ID Projet:", self.client_info.get("project_identifier", "N/A")),
            ("Pays:", self.client_info.get("country", "N/A")),
            ("Ville:", self.client_info.get("city", "N/A")),
            ("Besoin Principal:", self.client_info.get("need", "N/A")),
            ("Prix Final:", f"{self.client_info.get('price', 0)} €"),
            ("Date Création:", self.client_info.get("creation_date", "N/A")),
            ("Chemin Dossier:", f"<a href='file:///{self.client_info['base_folder_path']}'>{self.client_info['base_folder_path']}</a>") 
        ]
        for label_text, value_text in details: 
            label_widget = QLabel(label_text)
            value_widget = QLabel(value_text)
            value_widget.setOpenExternalLinks(True)
            value_widget.setTextInteractionFlags(Qt.TextBrowserInteraction)
            details_layout.addRow(label_widget, value_widget)
        layout.addLayout(details_layout)
        
        # Notes
        notes_group = QGroupBox("Notes")
        notes_layout = QVBoxLayout(notes_group)
        self.notes_edit = QTextEdit(self.client_info.get("notes", ""))
        self.notes_edit.setPlaceholderText("Ajoutez des notes sur ce client...")
        self.notes_edit.textChanged.connect(self.save_client_notes) 
        notes_layout.addWidget(self.notes_edit)
        layout.addWidget(notes_group)
        
        # Onglets
        self.tab_widget = QTabWidget()
        
        # Onglet Documents
        docs_tab = QWidget()
        docs_layout = QVBoxLayout(docs_tab)
        
        # Tableau des documents
        self.doc_table = QTableWidget()
        self.doc_table.setColumnCount(5)
        self.doc_table.setHorizontalHeaderLabels(["Nom", "Type", "Langue", "Date", "Actions"])
        self.doc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.doc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.doc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        docs_layout.addWidget(self.doc_table)
        
        # Boutons d'action pour les documents
        doc_btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Actualiser")
        refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        refresh_btn.clicked.connect(self.populate_doc_table)
        doc_btn_layout.addWidget(refresh_btn)
        
        open_btn = QPushButton("Ouvrir")
        open_btn.setIcon(QIcon.fromTheme("document-open"))
        open_btn.clicked.connect(self.open_selected_doc)
        doc_btn_layout.addWidget(open_btn)
        
        delete_btn = QPushButton("Supprimer")
        delete_btn.setIcon(QIcon.fromTheme("edit-delete"))
        delete_btn.clicked.connect(self.delete_selected_doc)
        doc_btn_layout.addWidget(delete_btn)
        
        docs_layout.addLayout(doc_btn_layout)
        self.tab_widget.addTab(docs_tab, "Documents")
        
        # Onglet Contacts
        contacts_tab = QWidget()
        contacts_layout = QVBoxLayout(contacts_tab)
        self.contacts_list = QListWidget()
        self.contacts_list.setAlternatingRowColors(True)
        self.contacts_list.itemDoubleClicked.connect(self.edit_contact)
        contacts_layout.addWidget(self.contacts_list)
        
        contacts_btn_layout = QHBoxLayout()
        self.add_contact_btn = QPushButton("Ajouter Contact")
        self.add_contact_btn.setIcon(QIcon.fromTheme("contact-new"))
        self.add_contact_btn.clicked.connect(self.add_contact)
        contacts_btn_layout.addWidget(self.add_contact_btn)
        
        self.edit_contact_btn = QPushButton("Modifier Contact")
        self.edit_contact_btn.setIcon(QIcon.fromTheme("document-edit"))
        self.edit_contact_btn.clicked.connect(self.edit_contact)
        contacts_btn_layout.addWidget(self.edit_contact_btn)
        
        self.remove_contact_btn = QPushButton("Supprimer Contact")
        self.remove_contact_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.remove_contact_btn.clicked.connect(self.remove_contact)
        contacts_btn_layout.addWidget(self.remove_contact_btn)
        
        contacts_layout.addLayout(contacts_btn_layout)
        self.tab_widget.addTab(contacts_tab, "Contacts")

        # Onglet Produits
        products_tab = QWidget()
        products_layout = QVBoxLayout(products_tab)
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels(["ID", "Nom Produit", "Description", "Qté", "Prix Unitaire", "Prix Total"])
        self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        products_layout.addWidget(self.products_table)
        
        products_btn_layout = QHBoxLayout()
        self.add_product_btn = QPushButton("Ajouter Produit")
        self.add_product_btn.setIcon(QIcon.fromTheme("list-add"))
        self.add_product_btn.clicked.connect(self.add_product)
        products_btn_layout.addWidget(self.add_product_btn)
        
        self.edit_product_btn = QPushButton("Modifier Produit")
        self.edit_product_btn.setIcon(QIcon.fromTheme("document-edit"))
        self.edit_product_btn.clicked.connect(self.edit_product)
        products_btn_layout.addWidget(self.edit_product_btn)
        
        self.remove_product_btn = QPushButton("Supprimer Produit")
        self.remove_product_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.remove_product_btn.clicked.connect(self.remove_product)
        products_btn_layout.addWidget(self.remove_product_btn)
        
        products_layout.addLayout(products_btn_layout)
        self.tab_widget.addTab(products_tab, "Produits")
        
        layout.addWidget(self.tab_widget)
        
        # Initialiser les données
        self.populate_doc_table()
        self.load_contacts()
        self.load_products()

    def load_statuses(self):
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT status_name FROM StatusSettings")
            for status_row in cursor.fetchall(): 
                self.status_combo.addItem(status_row[0])
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Erreur DB", f"Erreur de chargement des statuts:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def update_client_status(self, status_text): 
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE Clients SET status = ? WHERE client_id = ?", (status_text, self.client_info["client_id"]))
            conn.commit()
            self.client_info["status"] = status_text 
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Erreur DB", f"Erreur de mise à jour du statut:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def save_client_notes(self): 
        notes = self.notes_edit.toPlainText()
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE Clients SET notes = ? WHERE client_id = ?", (notes, self.client_info["client_id"]))
            conn.commit()
            self.client_info["notes"] = notes 
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Erreur DB", f"Erreur de sauvegarde des notes:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def populate_doc_table(self):
        self.doc_table.setRowCount(0)
        client_path = self.client_info["base_folder_path"] 
        if not os.path.exists(client_path):
            return
            
        row = 0
        for lang in self.client_info.get("selected_languages", ["fr"]):
            lang_dir = os.path.join(client_path, lang)
            if not os.path.exists(lang_dir):
                continue
                
            for file_name in os.listdir(lang_dir):
                if file_name.endswith(('.xlsx', '.pdf')):
                    file_path = os.path.join(lang_dir, file_name)
                    file_type = "Excel" if file_name.endswith('.xlsx') else "PDF"
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')
                    
                    self.doc_table.insertRow(row)
                    
                    # Nom
                    self.doc_table.setItem(row, 0, QTableWidgetItem(file_name))
                    
                    # Type
                    self.doc_table.setItem(row, 1, QTableWidgetItem(file_type))
                    
                    # Langue
                    self.doc_table.setItem(row, 2, QTableWidgetItem(lang))
                    
                    # Date
                    self.doc_table.setItem(row, 3, QTableWidgetItem(mod_time))
                    
                    # Actions
                    action_widget = QWidget()
                    action_layout = QHBoxLayout(action_widget)
                    action_layout.setContentsMargins(0, 0, 0, 0)
                    
                    open_btn = QPushButton()
                    open_btn.setIcon(QIcon.fromTheme("document-open"))
                    open_btn.setToolTip("Ouvrir")
                    open_btn.setFixedSize(30, 30)
                    open_btn.clicked.connect(lambda _, p=file_path: self.open_document(p))
                    action_layout.addWidget(open_btn)
                    
                    if file_name.endswith('.xlsx'):
                        edit_btn = QPushButton()
                        edit_btn.setIcon(QIcon.fromTheme("document-edit"))
                        edit_btn.setToolTip("Éditer")
                        edit_btn.setFixedSize(30, 30)
                        edit_btn.clicked.connect(lambda _, p=file_path: self.open_document(p))
                        action_layout.addWidget(edit_btn)
                    
                    delete_btn = QPushButton()
                    delete_btn.setIcon(QIcon.fromTheme("edit-delete"))
                    delete_btn.setToolTip("Supprimer")
                    delete_btn.setFixedSize(30, 30)
                    delete_btn.clicked.connect(lambda _, p=file_path: self.delete_document(p))
                    action_layout.addWidget(delete_btn)
                    
                    self.doc_table.setCellWidget(row, 4, action_widget)
                    
                    row += 1

    def open_create_docs_dialog(self):
        dialog = CreateDocumentDialog(self.client_info, self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            self.populate_doc_table()
            
    def open_compile_pdf_dialog(self):
        dialog = CompilePdfDialog(self.client_info, self)
        dialog.exec_()
            
    def open_selected_doc(self):
        selected_row = self.doc_table.currentRow()
        if selected_row >= 0:
            file_path = self.doc_table.item(selected_row, 0).data(Qt.UserRole)
            if file_path and os.path.exists(file_path):
                self.open_document(file_path)
                
    def delete_selected_doc(self):
        selected_row = self.doc_table.currentRow()
        if selected_row >= 0:
            file_path = self.doc_table.item(selected_row, 0).data(Qt.UserRole)
            if file_path and os.path.exists(file_path):
                self.delete_document(file_path)
                
    def open_document(self, file_path):
        if os.path.exists(file_path):
            try:
                if file_path.lower().endswith('.xlsx'):
                    editor_client_data = {
                        "Nom du client": self.client_info.get("client_name", ""),
                        "Besoin": self.client_info.get("need", ""),
                        "price": self.client_info.get("price", 0),
                        "project_identifier": self.client_info.get("project_identifier", "")
                    }
                    editor = ExcelEditor(file_path, client_data=editor_client_data, parent=self)
                    editor.exec_()
                    self.populate_doc_table()
                else:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            except Exception as e:
                QMessageBox.warning(self, "Erreur Ouverture Fichier", f"Impossible d'ouvrir le fichier:\n{str(e)}")
        else:
            QMessageBox.warning(self, "Fichier Introuvable", "Le fichier n'existe plus.")
            self.populate_doc_table()
            
    def delete_document(self, file_path):
        if not os.path.exists(file_path):
            return
            
        reply = QMessageBox.question(
            self, 
            "Confirmer la suppression", 
            f"Êtes-vous sûr de vouloir supprimer le fichier {os.path.basename(file_path)} ?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(file_path)
                self.populate_doc_table()
                QMessageBox.information(self, "Fichier supprimé", "Le fichier a été supprimé avec succès.")
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Impossible de supprimer le fichier:\n{str(e)}")
    
    def load_contacts(self):
        self.contacts_list.clear()
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT contact_id, name, email, phone, position, is_primary FROM Contacts WHERE client_id = ?", 
                (self.client_info["client_id"],)
            )
            for row in cursor.fetchall():
                contact_text = f"{row[1]}" 
                if row[3]: contact_text += f" ({row[3]})" 
                if row[5]: contact_text += " [Principal]" 
                item = QListWidgetItem(contact_text)
                item.setData(Qt.UserRole, row[0]) 
                self.contacts_list.addItem(item)
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Erreur DB", f"Erreur de chargement des contacts:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def add_contact(self):
        dialog = ContactDialog(self.client_info["client_id"], parent=self) 
        if dialog.exec_() == QDialog.Accepted:
            contact_data = dialog.get_data()
            conn = None
            try:
                conn = sqlite3.connect(DATABASE_NAME)
                cursor = conn.cursor()
                if contact_data["is_primary"]:
                    cursor.execute("UPDATE Contacts SET is_primary = 0 WHERE client_id = ?", (self.client_info["client_id"],))
                cursor.execute(
                    "INSERT INTO Contacts (client_id, name, email, phone, position, is_primary) VALUES (?, ?, ?, ?, ?, ?)", 
                    (self.client_info["client_id"], contact_data["name"], contact_data["email"], contact_data["phone"], contact_data["position"], contact_data["is_primary"])
                )
                conn.commit()
                self.load_contacts()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Erreur DB", f"Erreur d'ajout du contact:\n{str(e)}")
            finally:
                if conn: conn.close()
                
    def edit_contact(self):
        item = self.contacts_list.currentItem()
        if not item: return
        contact_id = item.data(Qt.UserRole)
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT name, email, phone, position, is_primary FROM Contacts WHERE contact_id = ?", (contact_id,)) 
            contact_row = cursor.fetchone() 
            if contact_row:
                dialog = ContactDialog(self.client_info["client_id"], {
                    "name": contact_row[0], "email": contact_row[1], "phone": contact_row[2], 
                    "position": contact_row[3], "is_primary": contact_row[4] 
                }, parent=self) 
                if dialog.exec_() == QDialog.Accepted:
                    new_data = dialog.get_data()
                    if new_data["is_primary"]:
                        cursor.execute("UPDATE Contacts SET is_primary = 0 WHERE client_id = ?", (self.client_info["client_id"],))
                    cursor.execute(
                        "UPDATE Contacts SET name = ?, email = ?, phone = ?, position = ?, is_primary = ? WHERE contact_id = ?", 
                        (new_data["name"], new_data["email"], new_data["phone"], new_data["position"], new_data["is_primary"], contact_id)
                    )
                    conn.commit()
                    self.load_contacts()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Erreur DB", f"Erreur de modification du contact:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def remove_contact(self):
        item = self.contacts_list.currentItem()
        if not item: return
        contact_id = item.data(Qt.UserRole)
        reply = QMessageBox.question(self, "Confirmer Suppression", "Êtes-vous sûr de vouloir supprimer ce contact?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = None
            try:
                conn = sqlite3.connect(DATABASE_NAME)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Contacts WHERE contact_id = ?", (contact_id,))
                conn.commit()
                self.load_contacts()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Erreur DB", f"Erreur de suppression du contact:\n{str(e)}")
            finally:
                if conn: conn.close()
                
    def add_product(self):
        dialog = ProductDialog(self.client_info["client_id"], parent=self)
        if dialog.exec_() == QDialog.Accepted:
            product_data = dialog.get_data()
            conn = None
            try:
                conn = sqlite3.connect(DATABASE_NAME)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO ClientProducts (client_id, name, description, quantity, unit_price, total_price) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (product_data["client_id"], product_data["name"], product_data["description"],
                    product_data["quantity"], product_data["unit_price"], product_data["total_price"]))
                conn.commit()
                self.load_products()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Erreur DB", f"Erreur d'ajout du produit:\n{str(e)}")
            finally:
                if conn: conn.close()

    def edit_product(self):
        selected_row = self.products_table.currentRow()
        if selected_row < 0: return
        
        product_id = self.products_table.item(selected_row, 0).data(Qt.UserRole)
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT name, description, quantity, unit_price FROM ClientProducts WHERE product_id = ?", (product_id,))
            product_row = cursor.fetchone()
            if product_row:
                dialog = ProductDialog(
                    self.client_info["client_id"],
                    {
                        "name": product_row[0],
                        "description": product_row[1],
                        "quantity": product_row[2],
                        "unit_price": product_row[3]
                    },
                    parent=self
                )
                if dialog.exec_() == QDialog.Accepted:
                    new_data = dialog.get_data()
                    cursor.execute(
                        "UPDATE ClientProducts SET name = ?, description = ?, quantity = ?, unit_price = ?, total_price = ? "
                        "WHERE product_id = ?",
                        (new_data["name"], new_data["description"], new_data["quantity"],
                        new_data["unit_price"], new_data["total_price"], product_id)
                    )
                    conn.commit()
                    self.load_products()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Erreur DB", f"Erreur de modification du produit:\n{str(e)}")
        finally:
            if conn: conn.close()

    def remove_product(self):
        selected_row = self.products_table.currentRow()
        if selected_row < 0: return
        
        product_id = self.products_table.item(selected_row, 0).data(Qt.UserRole)
        product_name = self.products_table.item(selected_row, 1).text()
        
        reply = QMessageBox.question(
            self, 
            "Confirmer Suppression", 
            f"Êtes-vous sûr de vouloir supprimer le produit '{product_name}'?", 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            conn = None
            try:
                conn = sqlite3.connect(DATABASE_NAME)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ClientProducts WHERE product_id = ?", (product_id,))
                conn.commit()
                self.load_products()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Erreur DB", f"Erreur de suppression du produit:\n{str(e)}")
            finally:
                if conn: conn.close()

    def load_products(self):
        self.products_table.setRowCount(0)
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT product_id, name, description, quantity, unit_price, total_price "
                "FROM ClientProducts WHERE client_id = ?",
                (self.client_info["client_id"],)
            )
            
            for row_idx, row_data in enumerate(cursor.fetchall()):
                self.products_table.insertRow(row_idx)
                
                # ID
                id_item = QTableWidgetItem(str(row_data[0]))
                id_item.setData(Qt.UserRole, row_data[0])
                self.products_table.setItem(row_idx, 0, id_item)
                
                # Nom
                self.products_table.setItem(row_idx, 1, QTableWidgetItem(row_data[1]))
                
                # Description
                self.products_table.setItem(row_idx, 2, QTableWidgetItem(row_data[2]))
                
                # Quantité
                qty_item = QTableWidgetItem(str(row_data[3]))
                qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.products_table.setItem(row_idx, 3, qty_item)
                
                # Prix unitaire
                unit_price = QTableWidgetItem(f"€ {row_data[4]:.2f}")
                unit_price.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.products_table.setItem(row_idx, 4, unit_price)
                
                # Prix total
                total_price = QTableWidgetItem(f"€ {row_data[5]:.2f}")
                total_price.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.products_table.setItem(row_idx, 5, total_price)
                
            self.products_table.resizeColumnsToContents()
            
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Erreur DB", f"Erreur de chargement des produits:\n{str(e)}")
        finally:
            if conn: conn.close()

class StatisticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self); layout.setContentsMargins(10, 5, 10, 5)
        stat_items_data = [ 
            ("Clients Totaux", "total_label", "0", None),
            ("Valeur Totale", "value_label", "0 €", None),
            ("Projets en Cours", "ongoing_label", "0", None),
            ("Projets Urgents", "urgent_label", "0", "color: #e74c3c;")
        ]
        for title, attr_name, default_text, style in stat_items_data: 
            group = QGroupBox(title); group_layout = QVBoxLayout(group) 
            label = QLabel(default_text)
            label.setFont(QFont("Arial", 16, QFont.Bold)); label.setAlignment(Qt.AlignCenter)
            if style: label.setStyleSheet(style)
            setattr(self, attr_name, label) 
            group_layout.addWidget(label); layout.addWidget(group)
        
    def update_stats(self):
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM Clients"); total_clients = cursor.fetchone()[0] 
            self.total_label.setText(str(total_clients))
            
            cursor.execute("SELECT SUM(price) FROM Clients"); total_val = cursor.fetchone()[0] or 0 
            self.value_label.setText(f"{total_val:,.2f} €")
            
            cursor.execute("SELECT COUNT(*) FROM Clients WHERE status = 'En cours'"); ongoing_count = cursor.fetchone()[0] 
            self.ongoing_label.setText(str(ongoing_count))
            
            cursor.execute("SELECT COUNT(*) FROM Clients WHERE status = 'Urgent'"); urgent_count = cursor.fetchone()[0] 
            self.urgent_label.setText(str(urgent_count))
        except sqlite3.Error as e:
            print(f"Erreur de mise à jour des statistiques: {str(e)}")
        finally:
            if conn: conn.close()

class StatusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        status_text = index.data(Qt.UserRole) 
        bg_color_hex = "#95a5a6" 
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT color FROM StatusSettings WHERE status_name = ?", (status_text,))
            color_row = cursor.fetchone() 
            if color_row: bg_color_hex = color_row[0]
        except sqlite3.Error: pass 
        finally:
            if conn: conn.close()
        
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
        self.setWindowTitle("Gestionnaire de Documents Client"); self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon.fromTheme("folder-documents"))
        
        self.config = CONFIG 
        self.clients_data_map = {} 
        
        self.setup_ui_main() 
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
        content_layout = QHBoxLayout(); main_layout.addLayout(content_layout)
        
        left_panel = QWidget(); left_layout = QVBoxLayout(left_panel); left_layout.setContentsMargins(5,5,5,5)
        filter_search_layout = QHBoxLayout() 
        self.status_filter_combo = QComboBox(); self.status_filter_combo.addItem("Tous les statuts") 
        self.load_statuses_into_filter_combo() 
        self.status_filter_combo.currentIndexChanged.connect(self.filter_client_list_display) 
        filter_search_layout.addWidget(QLabel("Filtrer par statut:"))
        filter_search_layout.addWidget(self.status_filter_combo)
        self.search_input_field = QLineEdit(); self.search_input_field.setPlaceholderText("Rechercher client...") 
        self.search_input_field.textChanged.connect(self.filter_client_list_display) 
        filter_search_layout.addWidget(self.search_input_field); left_layout.addLayout(filter_search_layout)
        
        self.client_list_widget = QListWidget(); self.client_list_widget.setAlternatingRowColors(True) 
        self.client_list_widget.setItemDelegate(StatusDelegate(self.client_list_widget))
        self.client_list_widget.itemClicked.connect(self.handle_client_list_click) 
        self.client_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.client_list_widget.customContextMenuRequested.connect(self.show_client_context_menu)
        left_layout.addWidget(self.client_list_widget)
        
        form_group_box = QGroupBox("Ajouter un Nouveau Client"); form_vbox_layout = QVBoxLayout(form_group_box) 
        creation_form_layout = QFormLayout(); creation_form_layout.setLabelAlignment(Qt.AlignRight) 
        
        self.client_name_input = QLineEdit(); self.client_name_input.setPlaceholderText("Nom du client") 
        creation_form_layout.addRow("Nom Client:", self.client_name_input)
        self.company_name_input = QLineEdit(); self.company_name_input.setPlaceholderText("Nom entreprise (optionnel)") 
        creation_form_layout.addRow("Nom Entreprise:", self.company_name_input)
        self.client_need_input = QLineEdit(); self.client_need_input.setPlaceholderText("Besoin principal du client") 
        creation_form_layout.addRow("Besoin Client:", self.client_need_input)
        
        country_hbox_layout = QHBoxLayout(); self.country_select_combo = QComboBox() 
        self.country_select_combo.setEditable(True); self.country_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.country_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.country_select_combo.completer().setFilterMode(Qt.MatchContains)
        self.country_select_combo.currentTextChanged.connect(self.load_cities_for_country) 
        country_hbox_layout.addWidget(self.country_select_combo)
        self.add_country_button = QPushButton("+"); self.add_country_button.setFixedSize(30,30) 
        self.add_country_button.setToolTip("Ajouter un nouveau pays")
        self.add_country_button.clicked.connect(self.add_new_country_dialog) 
        country_hbox_layout.addWidget(self.add_country_button); creation_form_layout.addRow("Pays Client:", country_hbox_layout)
        
        city_hbox_layout = QHBoxLayout(); self.city_select_combo = QComboBox() 
        self.city_select_combo.setEditable(True); self.city_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.city_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.city_select_combo.completer().setFilterMode(Qt.MatchContains)
        city_hbox_layout.addWidget(self.city_select_combo)
        self.add_city_button = QPushButton("+"); self.add_city_button.setFixedSize(30,30) 
        self.add_city_button.setToolTip("Ajouter une nouvelle ville")
        self.add_city_button.clicked.connect(self.add_new_city_dialog) 
        city_hbox_layout.addWidget(self.add_city_button); creation_form_layout.addRow("Ville Client:", city_hbox_layout)
        
        self.project_id_input_field = QLineEdit(); self.project_id_input_field.setPlaceholderText("Identifiant unique du projet") 
        creation_form_layout.addRow("ID Projet:", self.project_id_input_field)
        self.final_price_input = QDoubleSpinBox(); self.final_price_input.setPrefix("€ ") 
        self.final_price_input.setRange(0, 10000000); self.final_price_input.setValue(0)
        creation_form_layout.addRow("Prix Final:", self.final_price_input)
        self.language_select_combo = QComboBox() 
        self.language_select_combo.addItems(["Français uniquement (fr)", "Arabe uniquement (ar)", "Turc uniquement (tr)", "Toutes les langues (fr, ar, tr)"])
        creation_form_layout.addRow("Langues:", self.language_select_combo)
        self.create_client_button = QPushButton("Créer Client"); self.create_client_button.setIcon(QIcon.fromTheme("list-add")) 
        self.create_client_button.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 10px; border-radius: 5px; } QPushButton:hover { background-color: #2ecc71; }")
        self.create_client_button.clicked.connect(self.execute_create_client) 
        creation_form_layout.addRow(self.create_client_button)
        form_vbox_layout.addLayout(creation_form_layout); left_layout.addWidget(form_group_box)
        content_layout.addWidget(left_panel, 1)
        
        self.client_tabs_widget = QTabWidget(); self.client_tabs_widget.setTabsClosable(True) 
        self.client_tabs_widget.tabCloseRequested.connect(self.close_client_tab) 
        content_layout.addWidget(self.client_tabs_widget, 2)
        self.load_countries_into_combo() 
        
    def create_actions_main(self): 
        self.settings_action = QAction("Paramètres", self); self.settings_action.triggered.connect(self.open_settings_dialog) 
        self.template_action = QAction("Gérer les Modèles", self); self.template_action.triggered.connect(self.open_template_manager_dialog) 
        self.status_action = QAction("Gérer les Statuts", self); self.status_action.triggered.connect(self.open_status_manager_dialog) 
        self.exit_action = QAction("Quitter", self); self.exit_action.setShortcut("Ctrl+Q"); self.exit_action.triggered.connect(self.close)
        
    def create_menus_main(self): 
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("Fichier")
        file_menu.addAction(self.settings_action); file_menu.addAction(self.template_action); file_menu.addAction(self.status_action)
        file_menu.addSeparator(); file_menu.addAction(self.exit_action)
        help_menu = menu_bar.addMenu("Aide")
        about_action = QAction("À propos", self); about_action.triggered.connect(self.show_about_dialog) 
        help_menu.addAction(about_action)
        
    def show_about_dialog(self): 
        QMessageBox.about(self, "À propos", "<b>Gestionnaire de Documents Client</b><br><br>Version 4.0<br>Application de gestion de documents clients avec templates Excel.<br><br>Développé par Saadiya Management (Concept)")
        
    def load_countries_into_combo(self): 
        self.country_select_combo.clear()
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT country_name FROM Countries ORDER BY country_name")
            for country_row in cursor.fetchall(): self.country_select_combo.addItem(country_row[0]) 
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Erreur DB", f"Erreur de chargement des pays:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def load_cities_for_country(self, country_name_str): 
        self.city_select_combo.clear()
        if not country_name_str: return
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT city_name FROM Cities WHERE country_id = (SELECT country_id FROM Countries WHERE country_name = ?) ORDER BY city_name",
                (country_name_str,)
            )
            for city_row in cursor.fetchall(): self.city_select_combo.addItem(city_row[0]) 
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Erreur DB", f"Erreur de chargement des villes:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def add_new_country_dialog(self): 
        country_text, ok = QInputDialog.getText(self, "Nouveau Pays", "Entrez le nom du nouveau pays:") 
        if ok and country_text.strip():
            conn = None
            try:
                conn = sqlite3.connect(DATABASE_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Countries (country_name) VALUES (?)", (country_text.strip(),))
                conn.commit()
                self.load_countries_into_combo()
                self.country_select_combo.setCurrentText(country_text.strip())
            except sqlite3.IntegrityError: QMessageBox.warning(self, "Pays Existant", "Ce pays existe déjà.")
            except sqlite3.Error as e: QMessageBox.critical(self, "Erreur DB", f"Erreur d'ajout du pays:\n{str(e)}")
            finally:
                if conn: conn.close()
                
    def add_new_city_dialog(self): 
        current_country = self.country_select_combo.currentText() 
        if not current_country:
            QMessageBox.warning(self, "Pays Requis", "Veuillez d'abord sélectionner un pays."); return
        city_text, ok = QInputDialog.getText(self, "Nouvelle Ville", f"Entrez le nom de la nouvelle ville pour {current_country}:") 
        if ok and city_text.strip():
            conn = None
            try:
                conn = sqlite3.connect(DATABASE_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT country_id FROM Countries WHERE country_name = ?", (current_country,))
                country_id_row = cursor.fetchone() 
                if not country_id_row: QMessageBox.warning(self, "Pays Inconnu", "Pays sélectionné introuvable."); return
                cursor.execute("INSERT INTO Cities (country_id, city_name) VALUES (?, ?)", (country_id_row[0], city_text.strip()))
                conn.commit()
                self.load_cities_for_country(current_country)
                self.city_select_combo.setCurrentText(city_text.strip())
            except sqlite3.IntegrityError: QMessageBox.warning(self, "Ville Existante", "Cette ville existe déjà pour ce pays.")
            except sqlite3.Error as e: QMessageBox.critical(self, "Erreur DB", f"Erreur d'ajout de la ville:\n{str(e)}")
            finally:
                if conn: conn.close()
                
    def generate_new_client_id(self): 
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(CAST(SUBSTR(client_id, 2) AS INTEGER)) FROM Clients WHERE client_id LIKE 'C%'") 
            last_num_row = cursor.fetchone() 
            next_num = (last_num_row[0] or 0) + 1
            return f"C{next_num:04d}"
        except sqlite3.Error: return f"C{int(datetime.now().timestamp()) % 10000:04d}" 
        finally:
            if conn: conn.close()
                
    def execute_create_client(self): 
        client_name_val = self.client_name_input.text().strip() 
        company_name_val = self.company_name_input.text().strip()
        need_val = self.client_need_input.text().strip()
        country_val = self.country_select_combo.currentText().strip()
        city_val = self.city_select_combo.currentText().strip()
        project_id_val = self.project_id_input_field.text().strip()
        price_val = self.final_price_input.value()
        lang_option_text = self.language_select_combo.currentText() 
        
        if not client_name_val or not country_val or not project_id_val:
            QMessageBox.warning(self, "Champs Requis", "Nom client, Pays et ID Projet sont obligatoires."); return
            
        lang_map_dict = {
            "Français uniquement (fr)": ["fr"], 
            "Arabe uniquement (ar)": ["ar"],
            "Turc uniquement (tr)": ["tr"], 
            "Toutes les langues (fr, ar, tr)": ["fr", "ar", "tr"]
        }
        selected_langs_list = lang_map_dict.get(lang_option_text, ["fr"]) 
        
        folder_name_str = f"{client_name_val}_{country_val}_{project_id_val}".replace(" ", "_").replace("/", "-") 
        base_folder_full_path = os.path.join(self.config["clients_dir"], folder_name_str) 
        
        if os.path.exists(base_folder_full_path):
            QMessageBox.warning(self, "Dossier Existant", "Un dossier client avec ces identifiants (nom, pays, projet) existe déjà."); return
            
        new_client_id = self.generate_new_client_id() 
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT client_id FROM Clients WHERE project_identifier = ?", (project_id_val,))
            if cursor.fetchone():
                 QMessageBox.warning(self, "ID Projet Existant", f"L'ID Projet '{project_id_val}' est déjà utilisé."); return

            cursor.execute(
                "INSERT INTO Clients (client_id, client_name, company_name, need, country, city, project_identifier, base_folder_path, selected_languages, price, creation_date, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (new_client_id, client_name_val, company_name_val, need_val, country_val, city_val, project_id_val, base_folder_full_path, 
                 ",".join(selected_langs_list), price_val, datetime.now().strftime("%Y-%m-%d"), "En cours")
            )
            conn.commit()
            os.makedirs(base_folder_full_path, exist_ok=True)
            for lang_code in selected_langs_list: os.makedirs(os.path.join(base_folder_full_path, lang_code), exist_ok=True) 
                
            client_dict_data = { 
                "client_id": new_client_id, "client_name": client_name_val, "company_name": company_name_val,
                "need": need_val, "country": country_val, "city": city_val, "project_identifier": project_id_val,
                "base_folder_path": base_folder_full_path, "selected_languages": selected_langs_list, "price": price_val,
                "creation_date": datetime.now().strftime("%Y-%m-%d"), "status": "En cours", "notes": ""
            }
            self.clients_data_map[new_client_id] = client_dict_data 
            self.add_client_to_list_widget(client_dict_data) 
            
            self.client_name_input.clear(); self.company_name_input.clear(); self.client_need_input.clear()
            self.project_id_input_field.clear(); self.final_price_input.setValue(0)
            
            QMessageBox.information(self, "Client Créé", f"Client {client_name_val} créé (ID: {new_client_id}).")
            self.open_client_tab_by_id(new_client_id) 
            self.stats_widget.update_stats()
        except sqlite3.IntegrityError as ie: 
             QMessageBox.warning(self, "Conflit de Données", f"Un client avec un chemin de dossier similaire existe déjà or autre contrainte DB violée: {ie}")
        except sqlite3.Error as e: QMessageBox.critical(self, "Erreur DB", f"Erreur de sauvegarde du client:\n{str(e)}")
        except OSError as e: QMessageBox.critical(self, "Erreur Dossier", f"Erreur de création du dossier client:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def load_clients_from_db(self):
        self.clients_data_map.clear()
        self.client_list_widget.clear()
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT client_id, client_name, company_name, need, country, city, project_identifier, base_folder_path, selected_languages, price, notes, status, creation_date FROM Clients ORDER BY client_name")
            for row_data in cursor.fetchall(): 
                client_dict = { 
                    "client_id": row_data[0], "client_name": row_data[1], "company_name": row_data[2],
                    "need": row_data[3], "country": row_data[4], "city": row_data[5], 
                    "project_identifier": row_data[6], "base_folder_path": row_data[7],
                    "selected_languages": row_data[8].split(',') if row_data[8] else ['fr'], 
                    "price": row_data[9], "notes": row_data[10], "status": row_data[11], 
                    "creation_date": row_data[12]
                }
                self.clients_data_map[client_dict["client_id"]] = client_dict 
                self.add_client_to_list_widget(client_dict)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Erreur DB", f"Erreur de chargement des clients:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def add_client_to_list_widget(self, client_dict_data): 
        item = QListWidgetItem(client_dict_data["client_name"])
        item.setData(Qt.UserRole, client_dict_data["status"])  
        item.setData(Qt.UserRole + 1, client_dict_data["client_id"]) 
        self.client_list_widget.addItem(item)
            
    def filter_client_list_display(self): 
        search_term = self.search_input_field.text().lower() 
        status_val_filter = self.status_filter_combo.currentText() 
        self.client_list_widget.clear()
        for client_id_key, client_data_val in self.clients_data_map.items(): 
            if status_val_filter != "Tous les statuts" and client_data_val["status"] != status_val_filter:
                continue
            if search_term and not (search_term in client_data_val["client_name"].lower() or \
                                   search_term in client_data_val.get("project_identifier","").lower() or \
                                   search_term in client_data_val.get("company_name","").lower()): 
                continue
            self.add_client_to_list_widget(client_data_val)
            
    def load_statuses_into_filter_combo(self): 
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT status_name FROM StatusSettings ORDER BY status_name") 
            for status_row in cursor.fetchall(): self.status_filter_combo.addItem(status_row[0]) 
        except sqlite3.Error as e: print(f"Erreur chargement statuts pour filtre: {str(e)}")
        finally:
            if conn: conn.close()
            
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
        client_name_val = self.clients_data_map[client_id_val]["client_name"] if client_id_val in self.clients_data_map else "N/A"

        menu = QMenu()
        open_action = menu.addAction("Ouvrir Fiche Client"); open_action.triggered.connect(lambda: self.open_client_tab_by_id(client_id_val))
        open_folder_action = menu.addAction("Ouvrir Dossier Client"); open_folder_action.triggered.connect(lambda: self.open_client_folder_fs(client_id_val)) 
        menu.addSeparator()
        archive_action = menu.addAction("Archiver Client"); archive_action.triggered.connect(lambda: self.set_client_status_archived(client_id_val)) 
        delete_action = menu.addAction("Supprimer Client"); delete_action.triggered.connect(lambda: self.delete_client_permanently(client_id_val)) 
        menu.exec_(self.client_list_widget.mapToGlobal(pos))
        
    def open_client_folder_fs(self, client_id_val): 
        if client_id_val in self.clients_data_map:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.clients_data_map[client_id_val]["base_folder_path"]))
            
    def set_client_status_archived(self, client_id_val): 
        if client_id_val not in self.clients_data_map: return
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE Clients SET status = 'Archivé' WHERE client_id = ?", (client_id_val,))
            conn.commit()
            self.clients_data_map[client_id_val]["status"] = "Archivé"
            self.filter_client_list_display() 
            for i in range(self.client_tabs_widget.count()):
                tab_w = self.client_tabs_widget.widget(i)
                if hasattr(tab_w, 'client_info') and tab_w.client_info["client_id"] == client_id_val:
                    tab_w.status_combo.setCurrentText("Archivé") 
                    break
            self.stats_widget.update_stats()
            QMessageBox.information(self, "Client Archivé", f"Le client '{self.clients_data_map[client_id_val]['client_name']}' a été archivé.")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Erreur DB", f"Erreur d'archivage du client:\n{str(e)}")
        finally:
            if conn: conn.close()
            
    def delete_client_permanently(self, client_id_val): 
        if client_id_val not in self.clients_data_map: return
        client_name_val = self.clients_data_map[client_id_val]['client_name']
        reply = QMessageBox.question(self, "Confirmer Suppression", f"Supprimer '{client_name_val}'?\nCeci supprimera le client, ses contacts, et son dossier (si possible). Action irréversible.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = None
            try:
                conn = sqlite3.connect(DATABASE_NAME)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Clients WHERE client_id = ?", (client_id_val,))
                cursor.execute("DELETE FROM Contacts WHERE client_id = ?", (client_id_val,))
                conn.commit()
                
                client_folder_path = self.clients_data_map[client_id_val]["base_folder_path"] 
                if os.path.exists(client_folder_path): shutil.rmtree(client_folder_path, ignore_errors=True) 
                
                del self.clients_data_map[client_id_val]
                self.filter_client_list_display() 
                for i in range(self.client_tabs_widget.count()): 
                    if hasattr(self.client_tabs_widget.widget(i), 'client_info') and self.client_tabs_widget.widget(i).client_info["client_id"] == client_id_val:
                        self.close_client_tab(i); break
                self.stats_widget.update_stats()
                QMessageBox.information(self, "Client Supprimé", f"Client '{client_name_val}' supprimé.")
            except sqlite3.Error as e: QMessageBox.critical(self, "Erreur DB", f"Erreur DB suppression client:\n{str(e)}")
            except OSError as e: QMessageBox.critical(self, "Erreur Dossier", f"Erreur suppression dossier client:\n{str(e)}") 
            finally:
                if conn: conn.close()
                
    def check_old_clients_routine(self): 
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            reminder_days_val = self.config.get("default_reminder_days", 30) 
            cursor.execute(f"SELECT client_id, client_name, creation_date FROM Clients WHERE status NOT IN ('Archivé', 'Complété') AND date(creation_date) <= date('now', '-{reminder_days_val} days')")
            old_clients_list = cursor.fetchall() 
            if old_clients_list:
                client_names_str = "\n".join([f"- {client_row[1]} (créé le {client_row[2]})" for client_row in old_clients_list]) 
                reply = QMessageBox.question(self, "Clients Anciens Actifs", f"Les clients suivants sont actifs depuis plus de {reminder_days_val} jours:\n{client_names_str}\n\nVoulez-vous les archiver?", QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    for client_row in old_clients_list: self.set_client_status_archived(client_row[0]) 
        except sqlite3.Error as e: print(f"Erreur vérification clients anciens: {str(e)}")
        finally:
            if conn: conn.close()
            
    def open_settings_dialog(self): 
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            new_conf = dialog.get_config() 
            self.config.update(new_conf)
            save_config(self.config) 
            os.makedirs(self.config["templates_dir"], exist_ok=True) 
            os.makedirs(self.config["clients_dir"], exist_ok=True)
            QMessageBox.information(self, "Paramètres Sauvegardés", "Nouveaux paramètres enregistrés.")
            
    def open_template_manager_dialog(self): TemplateDialog(self).exec_() 
        
    def open_status_manager_dialog(self): 
        QMessageBox.information(self, "Gestion des Statuts", "Fonctionnalité de gestion des statuts personnalisés à implémenter (e.g., via un nouveau QDialog).")
            
    def closeEvent(self, event): 
        save_config(self.config) 
        super().closeEvent(event)

class SettingsDialog(QDialog):
    def __init__(self, current_config, parent=None): 
        super().__init__(parent)
        self.setWindowTitle("Paramètres de l'Application"); self.setMinimumSize(500, 400)
        self.current_config_data = current_config 
        self.setup_ui_settings() 
        
    def setup_ui_settings(self): 
        layout = QVBoxLayout(self); tabs_widget = QTabWidget(); layout.addWidget(tabs_widget) 
        
        general_tab_widget = QWidget(); general_form_layout = QFormLayout(general_tab_widget) 
        self.templates_dir_input = QLineEdit(self.current_config_data["templates_dir"]) 
        templates_browse_btn = QPushButton("Parcourir..."); templates_browse_btn.clicked.connect(lambda: self.browse_directory_for_input(self.templates_dir_input)) 
        templates_dir_layout = QHBoxLayout(); templates_dir_layout.addWidget(self.templates_dir_input); templates_dir_layout.addWidget(templates_browse_btn) 
        general_form_layout.addRow("Dossier des Modèles:", templates_dir_layout)
        
        self.clients_dir_input = QLineEdit(self.current_config_data["clients_dir"]) 
        clients_browse_btn = QPushButton("Parcourir..."); clients_browse_btn.clicked.connect(lambda: self.browse_directory_for_input(self.clients_dir_input)) 
        clients_dir_layout = QHBoxLayout(); clients_dir_layout.addWidget(self.clients_dir_input); clients_dir_layout.addWidget(clients_browse_btn) 
        general_form_layout.addRow("Dossier des Clients:", clients_dir_layout)
        
        self.interface_lang_combo = QComboBox(); self.interface_lang_combo.addItems(["Français (fr)", "Arabe (ar)", "Turc (tr)"]) 
        lang_map_display = {"fr": "Français (fr)", "ar": "Arabe (ar)", "tr": "Turc (tr)"} 
        self.interface_lang_combo.setCurrentText(lang_map_display.get(self.current_config_data.get("language", "fr"), "Français (fr)"))
        general_form_layout.addRow("Langue Interface (futur):", self.interface_lang_combo) 
        
        self.reminder_days_spinbox = QSpinBox(); self.reminder_days_spinbox.setRange(1, 365) 
        self.reminder_days_spinbox.setValue(self.current_config_data.get("default_reminder_days", 30))
        general_form_layout.addRow("Jours avant rappel client ancien:", self.reminder_days_spinbox)
        tabs_widget.addTab(general_tab_widget, "Général")
        
        email_tab_widget = QWidget(); email_form_layout = QFormLayout(email_tab_widget) 
        self.smtp_server_input_field = QLineEdit(self.current_config_data.get("smtp_server", "")) 
        email_form_layout.addRow("Serveur SMTP:", self.smtp_server_input_field)
        self.smtp_port_spinbox = QSpinBox(); self.smtp_port_spinbox.setRange(1, 65535) 
        self.smtp_port_spinbox.setValue(self.current_config_data.get("smtp_port", 587))
        email_form_layout.addRow("Port SMTP:", self.smtp_port_spinbox)
        self.smtp_user_input_field = QLineEdit(self.current_config_data.get("smtp_user", "")) 
        email_form_layout.addRow("Utilisateur SMTP:", self.smtp_user_input_field)
        self.smtp_pass_input_field = QLineEdit(self.current_config_data.get("smtp_password", "")) 
        self.smtp_pass_input_field.setEchoMode(QLineEdit.Password)
        email_form_layout.addRow("Mot de passe SMTP:", self.smtp_pass_input_field)
        tabs_widget.addTab(email_tab_widget, "Email")
        
        dialog_button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel) 
        dialog_button_box.accepted.connect(self.accept); dialog_button_box.rejected.connect(self.reject)
        layout.addWidget(dialog_button_box)
        
    def browse_directory_for_input(self, line_edit_target): 
        dir_path = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier", line_edit_target.text())
        if dir_path: line_edit_target.setText(dir_path)
            
    def get_config(self):
        lang_map_save = {"Français (fr)": "fr", "Arabe (ar)": "ar", "Turc (tr)": "tr"} 
        return {
            "templates_dir": self.templates_dir_input.text(), "clients_dir": self.clients_dir_input.text(),
            "language": lang_map_save.get(self.interface_lang_combo.currentText(), "fr"),
            "default_reminder_days": self.reminder_days_spinbox.value(),
            "smtp_server": self.smtp_server_input_field.text(), "smtp_port": self.smtp_port_spinbox.value(),
            "smtp_user": self.smtp_user_input_field.text(), "smtp_password": self.smtp_pass_input_field.text()
        }

def main():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'): QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("ClientDocManager")
    app.setStyle("Fusion") 
    
    templates_root_dir = CONFIG["templates_dir"] 
    default_langs = ["fr", "ar", "tr"]
    
    default_templates_data = {
        SPEC_TECH_TEMPLATE_NAME: pd.DataFrame({'Section': ["Info Client", "Détails Tech"], 'Champ': ["Nom:", "Exigence:"], 'Valeur': ["{NOM_CLIENT}", ""]}),
        PROFORMA_TEMPLATE_NAME: pd.DataFrame({'Article': ["Produit A"], 'Qté': [1], 'PU': [10.0], 'Total': [10.0]}),
        CONTRAT_VENTE_TEMPLATE_NAME: pd.DataFrame({'Clause': ["Objet"], 'Description': ["Vente de ..."]}),
        PACKING_LISTE_TEMPLATE_NAME: pd.DataFrame({'Colis': [1], 'Contenu': ["Marchandise X"], 'Poids': [5.0]})
    }

    for lang_code in default_langs:
        lang_specific_dir = os.path.join(templates_root_dir, lang_code)
        os.makedirs(lang_specific_dir, exist_ok=True)
        for template_file_name, df_content in default_templates_data.items(): 
            template_full_path = os.path.join(lang_specific_dir, template_file_name) 
            if not os.path.exists(template_full_path):
                try:
                    df_content.to_excel(template_full_path, index=False)
                except Exception as e: print(f"Erreur création template {template_file_name} pour {lang_code}: {str(e)}")
    
    main_window = DocumentManager() 
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
