#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application complète de gestion d'emails avec PyQt
Fonctionnalités:
- Configuration SMTP
- Gestion des templates d'emails
- Gestion des contacts et listes
- Planification d'envois
- Système de relances
- Interface moderne avec thème sombre
"""

import sys
import sqlite3
import smtplib
import json
import threading
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
import schedule
import time

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QDateTimeEdit, QCheckBox,
    QGroupBox, QFormLayout, QMessageBox, QListWidget, QSplitter,
    QTreeWidget, QTreeWidgetItem, QSpinBox, QProgressBar, QFrame,
    QScrollArea, QGridLayout, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QDateTime, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPixmap
from PyQt5.QtWidgets import QAction
from imports import DB_PATH_mail
class DatabaseManager:
    """Gestionnaire de base de données SQLite"""
    
    def __init__(self, db_path=DB_PATH_mail):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialise la base de données avec toutes les tables nécessaires"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Table configuration SMTP
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS smtp_config (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                smtp_server TEXT NOT NULL,
                smtp_port INTEGER NOT NULL,
                email TEXT NOT NULL,
                password TEXT NOT NULL,
                use_tls BOOLEAN DEFAULT 1,
                is_default BOOLEAN DEFAULT 0
            )
        ''')
        
        # Table templates d'emails
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_templates (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                variables TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table contacts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                company TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table listes de contacts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contact_lists (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table relation contacts-listes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contact_list_members (
                id INTEGER PRIMARY KEY,
                contact_id INTEGER,
                list_id INTEGER,
                FOREIGN KEY (contact_id) REFERENCES contacts (id),
                FOREIGN KEY (list_id) REFERENCES contact_lists (id)
            )
        ''')
        
        # Table envois planifiés
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_emails (
                id INTEGER PRIMARY KEY,
                template_id INTEGER,
                smtp_config_id INTEGER,
                recipient_type TEXT, -- 'contact' ou 'list'
                recipient_id INTEGER,
                scheduled_time TIMESTAMP,
                status TEXT DEFAULT 'pending', -- pending, sent, failed
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES email_templates (id),
                FOREIGN KEY (smtp_config_id) REFERENCES smtp_config (id)
            )
        ''')
        
        # Table relances
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY,
                scheduled_email_id INTEGER,
                reminder_time TIMESTAMP,
                message TEXT,
                is_sent BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (scheduled_email_id) REFERENCES scheduled_emails (id)
            )
        ''')
        
        conn.commit()
        conn.close()

class EmailSender(QThread):
    """Thread pour l'envoi d'emails en arrière-plan"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished_sending = pyqtSignal(bool, str)
    
    def __init__(self, smtp_config, template, recipients):
        super().__init__()
        self.smtp_config = smtp_config
        self.template = template
        self.recipients = recipients
        self.should_stop = False
    
    def stop(self):
        self.should_stop = True
    
    def run(self):
        try:
            # Configuration du serveur SMTP
            server = smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port'])
            if self.smtp_config['use_tls']:
                server.starttls()
            server.login(self.smtp_config['email'], self.smtp_config['password'])
            
            total = len(self.recipients)
            sent = 0
            
            for i, recipient in enumerate(self.recipients):
                if self.should_stop:
                    break
                
                try:
                    # Création du message
                    msg = MIMEMultipart()
                    msg['From'] = self.smtp_config['email']
                    msg['To'] = recipient['email']
                    msg['Subject'] = self.template['subject']
                    
                    # Personnalisation du contenu
                    content = self.template['content']
                    for key, value in recipient.items():
                        content = content.replace(f"{{{key}}}", str(value))
                    
                    msg.attach(MIMEText(content, 'html'))
                    
                    # Envoi
                    server.send_message(msg)
                    sent += 1
                    
                    self.status_updated.emit(f"Envoyé à {recipient['email']}")
                    
                except Exception as e:
                    self.status_updated.emit(f"Erreur pour {recipient['email']}: {str(e)}")
                
                progress = int((i + 1) * 100 / total)
                self.progress_updated.emit(progress)
                
                self.msleep(100)  # Pause pour éviter le spam
            
            server.quit()
            self.finished_sending.emit(True, f"Envoi terminé: {sent}/{total} emails envoyés")
            
        except Exception as e:
            self.finished_sending.emit(False, f"Erreur SMTP: {str(e)}")

class ModernWidget(QWidget):
    """Widget de base avec style moderne"""
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: #0d7377;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #14a085;
            }
            QPushButton:pressed {
                background-color: #0a5d61;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #3c3c3c;
                border: 2px solid #555555;
                border-radius: 5px;
                padding: 8px;
                selection-background-color: #0d7377;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #0d7377;
            }
            QTableWidget {
                background-color: #3c3c3c;
                alternate-background-color: #2b2b2b;
                gridline-color: #555555;
                selection-background-color: #0d7377;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #404040;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                padding: 10px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0d7377;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin: 10px 0px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

class SMTPConfigWidget(ModernWidget):
    """Widget de configuration SMTP"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_configurations()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Titre
        title = QLabel("Configuration SMTP")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Configuration actuelle
        config_group = QGroupBox("Nouvelle Configuration")
        config_layout = QFormLayout(config_group)
        
        self.name_edit = QLineEdit()
        self.server_edit = QLineEdit()
        self.port_edit = QSpinBox()
        self.port_edit.setRange(1, 65535)
        self.port_edit.setValue(587)
        self.email_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.tls_check = QCheckBox("Utiliser TLS")
        self.tls_check.setChecked(True)
        self.default_check = QCheckBox("Configuration par défaut")
        
        config_layout.addRow("Nom:", self.name_edit)
        config_layout.addRow("Serveur SMTP:", self.server_edit)
        config_layout.addRow("Port:", self.port_edit)
        config_layout.addRow("Email:", self.email_edit)
        config_layout.addRow("Mot de passe:", self.password_edit)
        config_layout.addRow("", self.tls_check)
        config_layout.addRow("", self.default_check)
        
        buttons_layout = QHBoxLayout()
        self.save_btn = QPushButton("Sauvegarder")
        self.test_btn = QPushButton("Tester")
        self.save_btn.clicked.connect(self.save_configuration)
        self.test_btn.clicked.connect(self.test_configuration)
        
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.test_btn)
        buttons_layout.addStretch()
        
        config_layout.addRow("", buttons_layout)
        layout.addWidget(config_group)
        
        # Liste des configurations existantes
        list_group = QGroupBox("Configurations Existantes")
        list_layout = QVBoxLayout(list_group)
        
        self.config_table = QTableWidget()
        self.config_table.setColumnCount(4)
        self.config_table.setHorizontalHeaderLabels(["Nom", "Serveur", "Email", "Actions"])
        self.config_table.horizontalHeader().setStretchLastSection(True)
        
        list_layout.addWidget(self.config_table)
        layout.addWidget(list_group)
        
        layout.addStretch()
    
    def save_configuration(self):
        """Sauvegarde une nouvelle configuration SMTP"""
        name = self.name_edit.text().strip()
        server = self.server_edit.text().strip()
        port = self.port_edit.value()
        email = self.email_edit.text().strip()
        password = self.password_edit.text()
        use_tls = self.tls_check.isChecked()
        is_default = self.default_check.isChecked()
        
        if not all([name, server, email, password]):
            QMessageBox.warning(self, "Erreur", "Tous les champs sont requis!")
            return
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Si c'est la configuration par défaut, désactiver les autres
            if is_default:
                cursor.execute("UPDATE smtp_config SET is_default = 0")
            
            cursor.execute('''
                INSERT INTO smtp_config (name, smtp_server, smtp_port, email, password, use_tls, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, server, port, email, password, use_tls, is_default))
            
            conn.commit()
            QMessageBox.information(self, "Succès", "Configuration sauvegardée!")
            self.clear_form()
            self.load_configurations()
            
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Erreur", "Cette configuration existe déjà!")
        finally:
            conn.close()
    
    def test_configuration(self):
        """Test la configuration SMTP"""
        server = self.server_edit.text().strip()
        port = self.port_edit.value()
        email = self.email_edit.text().strip()
        password = self.password_edit.text()
        use_tls = self.tls_check.isChecked()
        
        if not all([server, email, password]):
            QMessageBox.warning(self, "Erreur", "Veuillez remplir tous les champs!")
            return
        
        try:
            smtp_server = smtplib.SMTP(server, port)
            if use_tls:
                smtp_server.starttls()
            smtp_server.login(email, password)
            smtp_server.quit()
            
            QMessageBox.information(self, "Succès", "Configuration SMTP valide!")
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec du test SMTP:\n{str(e)}")
    
    def load_configurations(self):
        """Charge les configurations existantes"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, smtp_server, email, is_default FROM smtp_config")
        configs = cursor.fetchall()
        
        self.config_table.setRowCount(len(configs))
        
        for row, config in enumerate(configs):
            self.config_table.setItem(row, 0, QTableWidgetItem(config[1]))
            self.config_table.setItem(row, 1, QTableWidgetItem(config[2]))
            self.config_table.setItem(row, 2, QTableWidgetItem(config[3]))
            
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 5, 5, 5)
            
            if config[4]:  # is_default
                default_label = QLabel("Par défaut")
                default_label.setStyleSheet("color: #0d7377; font-weight: bold;")
                actions_layout.addWidget(default_label)
            
            delete_btn = QPushButton("Supprimer")
            delete_btn.setStyleSheet("background-color: #d32f2f;")
            delete_btn.clicked.connect(lambda checked, config_id=config[0]: self.delete_configuration(config_id))
            actions_layout.addWidget(delete_btn)
            
            self.config_table.setCellWidget(row, 3, actions_widget)
        
        conn.close()
    
    def delete_configuration(self, config_id):
        """Supprime une configuration"""
        reply = QMessageBox.question(self, "Confirmation", 
                                   "Êtes-vous sûr de vouloir supprimer cette configuration?")
        
        if reply == QMessageBox.Yes:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM smtp_config WHERE id = ?", (config_id,))
            conn.commit()
            conn.close()
            
            self.load_configurations()
            QMessageBox.information(self, "Succès", "Configuration supprimée!")
    
    def clear_form(self):
        """Vide le formulaire"""
        self.name_edit.clear()
        self.server_edit.clear()
        self.port_edit.setValue(587)
        self.email_edit.clear()
        self.password_edit.clear()
        self.tls_check.setChecked(True)
        self.default_check.setChecked(False)

class TemplateManager(ModernWidget):
    """Gestionnaire de templates d'emails"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.current_template_id = None
        self.init_ui()
        self.load_templates()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        # Liste des templates (gauche)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(300)
        
        templates_label = QLabel("Templates")
        templates_label.setFont(QFont("Arial", 14, QFont.Bold))
        left_layout.addWidget(templates_label)
        
        self.templates_list = QListWidget()
        self.templates_list.itemClicked.connect(self.load_template_details)
        left_layout.addWidget(self.templates_list)
        
        new_template_btn = QPushButton("Nouveau Template")
        new_template_btn.clicked.connect(self.new_template)
        left_layout.addWidget(new_template_btn)
        
        # Éditeur de template (droite)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        editor_label = QLabel("Éditeur de Template")
        editor_label.setFont(QFont("Arial", 14, QFont.Bold))
        right_layout.addWidget(editor_label)
        
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        
        self.name_edit = QLineEdit()
        self.subject_edit = QLineEdit()
        self.content_edit = QTextEdit()
        self.content_edit.setMinimumHeight(300)
        
        # Variables disponibles
        variables_info = QLabel("Variables disponibles: {name}, {email}, {company}")
        variables_info.setStyleSheet("color: #888888; font-style: italic;")
        
        form_layout.addRow("Nom:", self.name_edit)
        form_layout.addRow("Sujet:", self.subject_edit)
        form_layout.addRow("Contenu:", self.content_edit)
        form_layout.addRow("", variables_info)
        
        right_layout.addWidget(form_widget)
        
        # Boutons d'action
        buttons_layout = QHBoxLayout()
        self.save_btn = QPushButton("Sauvegarder")
        self.preview_btn = QPushButton("Aperçu")
        self.delete_btn = QPushButton("Supprimer")
        self.delete_btn.setStyleSheet("background-color: #d32f2f;")
        
        self.save_btn.clicked.connect(self.save_template)
        self.preview_btn.clicked.connect(self.preview_template)
        self.delete_btn.clicked.connect(self.delete_template)
        
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.preview_btn)
        buttons_layout.addWidget(self.delete_btn)
        buttons_layout.addStretch()
        
        right_layout.addLayout(buttons_layout)
        
        # Assemblage
        layout.addWidget(left_panel)
        layout.addWidget(right_panel, 1)
    
    def load_templates(self):
        """Charge la liste des templates"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name FROM email_templates ORDER BY name")
        templates = cursor.fetchall()
        
        self.templates_list.clear()
        for template_id, name in templates:
            item = QTreeWidgetItem([name])
            item.setData(0, Qt.UserRole, template_id)
            self.templates_list.addItem(f"{name} (ID: {template_id})")
        
        conn.close()
    
    def load_template_details(self, item):
        """Charge les détails d'un template sélectionné"""
        template_text = item.text()
        template_id = int(template_text.split("ID: ")[1].replace(")", ""))
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, subject, content FROM email_templates WHERE id = ?", (template_id,))
        template = cursor.fetchone()
        
        if template:
            self.current_template_id = template_id
            self.name_edit.setText(template[0])
            self.subject_edit.setText(template[1])
            self.content_edit.setPlainText(template[2])
        
        conn.close()
    
    def new_template(self):
        """Crée un nouveau template"""
        self.current_template_id = None
        self.name_edit.clear()
        self.subject_edit.clear()
        self.content_edit.clear()
    
    def save_template(self):
        """Sauvegarde le template"""
        name = self.name_edit.text().strip()
        subject = self.subject_edit.text().strip()
        content = self.content_edit.toPlainText()
        
        if not all([name, subject, content]):
            QMessageBox.warning(self, "Erreur", "Tous les champs sont requis!")
            return
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.current_template_id:
                # Mise à jour
                cursor.execute('''
                    UPDATE email_templates 
                    SET name = ?, subject = ?, content = ?
                    WHERE id = ?
                ''', (name, subject, content, self.current_template_id))
            else:
                # Création
                cursor.execute('''
                    INSERT INTO email_templates (name, subject, content)
                    VALUES (?, ?, ?)
                ''', (name, subject, content))
                self.current_template_id = cursor.lastrowid
            
            conn.commit()
            QMessageBox.information(self, "Succès", "Template sauvegardé!")
            self.load_templates()
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la sauvegarde:\n{str(e)}")
        finally:
            conn.close()
    
    def preview_template(self):
        """Affiche un aperçu du template"""
        subject = self.subject_edit.text()
        content = self.content_edit.toPlainText()
        
        # Template de test avec des données fictives
        test_data = {
            'name': 'Jean Dupont',
            'email': 'jean.dupont@example.com',
            'company': 'Ma Société'
        }
        
        preview_subject = subject
        preview_content = content
        
        for key, value in test_data.items():
            preview_subject = preview_subject.replace(f"{{{key}}}", value)
            preview_content = preview_content.replace(f"{{{key}}}", value)
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Aperçu du Template")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        subject_label = QLabel(f"Sujet: {preview_subject}")
        subject_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(subject_label)
        
        content_display = QTextEdit()
        content_display.setPlainText(preview_content)
        content_display.setReadOnly(True)
        layout.addWidget(content_display)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        
        dialog.exec_()
    
    def delete_template(self):
        """Supprime le template actuel"""
        if not self.current_template_id:
            QMessageBox.warning(self, "Erreur", "Aucun template sélectionné!")
            return
        
        reply = QMessageBox.question(self, "Confirmation", 
                                   "Êtes-vous sûr de vouloir supprimer ce template?")
        
        if reply == QMessageBox.Yes:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM email_templates WHERE id = ?", (self.current_template_id,))
            conn.commit()
            conn.close()
            
            self.new_template()
            self.load_templates()
            QMessageBox.information(self, "Succès", "Template supprimé!")

class ContactManager(ModernWidget):
    """Gestionnaire de contacts et listes"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_contacts()
        self.load_lists()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        # Panneau gauche - Contacts
        left_panel = QGroupBox("Contacts")
        left_layout = QVBoxLayout(left_panel)
        
        # Formulaire d'ajout de contact
        contact_form = QWidget()
        form_layout = QFormLayout(contact_form)
        
        self.contact_name_edit = QLineEdit()
        self.contact_email_edit = QLineEdit()
        self.contact_phone_edit = QLineEdit()
        self.contact_company_edit = QLineEdit()
        self.contact_notes_edit = QTextEdit()
        self.contact_notes_edit.setMaximumHeight(80)
        
        form_layout.addRow("Nom:", self.contact_name_edit)
        form_layout.addRow("Email:", self.contact_email_edit)
        form_layout.addRow("Téléphone:", self.contact_phone_edit)
        form_layout.addRow("Société:", self.contact_company_edit)
        form_layout.addRow("Notes:", self.contact_notes_edit)
        
        contact_buttons = QHBoxLayout()
        add_contact_btn = QPushButton("Ajouter Contact")
        update_contact_btn = QPushButton("Modifier")
        add_contact_btn.clicked.connect(self.add_contact)
        update_contact_btn.clicked.connect(self.update_contact)
        
        contact_buttons.addWidget(add_contact_btn)
        contact_buttons.addWidget(update_contact_btn)
        
        left_layout.addWidget(contact_form)
        left_layout.addLayout(contact_buttons)
        
        # Table des contacts
        self.contacts_table = QTableWidget()
        self.contacts_table.setColumnCount(5)
        self.contacts_table.setHorizontalHeaderLabels(["Nom", "Email", "Société", "Téléphone", "Actions"])
        self.contacts_table.horizontalHeader().setStretchLastSection(True)
        self.contacts_table.itemClicked.connect(self.select_contact)
        
        left_layout.addWidget(self.contacts_table)
        
        # Panneau droit - Listes
        right_panel = QGroupBox("Listes de Contacts")
        right_layout = QVBoxLayout(right_panel)
        
        # Formulaire de création de liste
        list_form = QWidget()
        list_form_layout = QFormLayout(list_form)
        
        self.list_name_edit = QLineEdit()
        self.list_description_edit = QTextEdit()
        self.list_description_edit.setMaximumHeight(60)
        
        list_form_layout.addRow("Nom de la liste:", self.list_name_edit)
        list_form_layout.addRow("Description:", self.list_description_edit)
        
        create_list_btn = QPushButton("Créer Liste")
        create_list_btn.clicked.connect(self.create_list)
        
        right_layout.addWidget(list_form)
        right_layout.addWidget(create_list_btn)
        
        # Gestion des listes
        self.lists_combo = QComboBox()
        self.lists_combo.currentTextChanged.connect(self.load_list_members)
        
        add_to_list_btn = QPushButton("Ajouter Contact à la Liste")
        add_to_list_btn.clicked.connect(self.add_contact_to_list)
        
        right_layout.addWidget(QLabel("Sélectionner une liste:"))
        right_layout.addWidget(self.lists_combo)
        right_layout.addWidget(add_to_list_btn)
        
        # Membres de la liste
        self.list_members_table = QTableWidget()
        self.list_members_table.setColumnCount(3)
        self.list_members_table.setHorizontalHeaderLabels(["Nom", "Email", "Actions"])
        self.list_members_table.horizontalHeader().setStretchLastSection(True)
        
        right_layout.addWidget(QLabel("Membres de la liste:"))
        right_layout.addWidget(self.list_members_table)
        
        # Assemblage final
        layout.addWidget(left_panel, 2)
        layout.addWidget(right_panel, 1)
        
        self.current_contact_id = None
    
    def add_contact(self):
        """Ajoute un nouveau contact"""
        name = self.contact_name_edit.text().strip()
        email = self.contact_email_edit.text().strip()
        phone = self.contact_phone_edit.text().strip()
        company = self.contact_company_edit.text().strip()
        notes = self.contact_notes_edit.toPlainText().strip()
        
        if not name or not email:
            QMessageBox.warning(self, "Erreur", "Le nom et l'email sont requis!")
            return
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO contacts (name, email, phone, company, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, email, phone, company, notes))
            
            conn.commit()
            QMessageBox.information(self, "Succès", "Contact ajouté!")
            self.clear_contact_form()
            self.load_contacts()
            
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Erreur", "Cet email existe déjà!")
        finally:
            conn.close()
    
    def update_contact(self):
        """Met à jour le contact sélectionné"""
        if not self.current_contact_id:
            QMessageBox.warning(self, "Erreur", "Aucun contact sélectionné!")
            return
        
        name = self.contact_name_edit.text().strip()
        email = self.contact_email_edit.text().strip()
        phone = self.contact_phone_edit.text().strip()
        company = self.contact_company_edit.text().strip()
        notes = self.contact_notes_edit.toPlainText().strip()
        
        if not name or not email:
            QMessageBox.warning(self, "Erreur", "Le nom et l'email sont requis!")
            return
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE contacts 
                SET name = ?, email = ?, phone = ?, company = ?, notes = ?
                WHERE id = ?
            ''', (name, email, phone, company, notes, self.current_contact_id))
            
            conn.commit()
            QMessageBox.information(self, "Succès", "Contact mis à jour!")
            self.load_contacts()
            
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Erreur", "Cet email existe déjà!")
        finally:
            conn.close()
    
    def select_contact(self, item):
        """Sélectionne un contact pour modification"""
        row = item.row()
        contact_id = self.contacts_table.item(row, 0).data(Qt.UserRole)
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
        contact = cursor.fetchone()
        
        if contact:
            self.current_contact_id = contact[0]
            self.contact_name_edit.setText(contact[1])
            self.contact_email_edit.setText(contact[2])
            self.contact_phone_edit.setText(contact[3] or "")
            self.contact_company_edit.setText(contact[4] or "")
            self.contact_notes_edit.setPlainText(contact[5] or "")
        
        conn.close()
    
    def load_contacts(self):
        """Charge tous les contacts"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, email, company, phone FROM contacts ORDER BY name")
        contacts = cursor.fetchall()
        
        self.contacts_table.setRowCount(len(contacts))
        
        for row, contact in enumerate(contacts):
            name_item = QTableWidgetItem(contact[1])
            name_item.setData(Qt.UserRole, contact[0])
            
            self.contacts_table.setItem(row, 0, name_item)
            self.contacts_table.setItem(row, 1, QTableWidgetItem(contact[2]))
            self.contacts_table.setItem(row, 2, QTableWidgetItem(contact[3] or ""))
            self.contacts_table.setItem(row, 3, QTableWidgetItem(contact[4] or ""))
            
            # Bouton de suppression
            delete_btn = QPushButton("Supprimer")
            delete_btn.setStyleSheet("background-color: #d32f2f; padding: 5px;")
            delete_btn.clicked.connect(lambda checked, cid=contact[0]: self.delete_contact(cid))
            self.contacts_table.setCellWidget(row, 4, delete_btn)
        
        conn.close()
    
    def delete_contact(self, contact_id):
        """Supprime un contact"""
        reply = QMessageBox.question(self, "Confirmation", 
                                   "Êtes-vous sûr de vouloir supprimer ce contact?")
        
        if reply == QMessageBox.Yes:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Supprimer aussi des listes
            cursor.execute("DELETE FROM contact_list_members WHERE contact_id = ?", (contact_id,))
            cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
            
            conn.commit()
            conn.close()
            
            self.load_contacts()
            self.load_list_members()
            QMessageBox.information(self, "Succès", "Contact supprimé!")
    
    def create_list(self):
        """Crée une nouvelle liste de contacts"""
        name = self.list_name_edit.text().strip()
        description = self.list_description_edit.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Erreur", "Le nom de la liste est requis!")
            return
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO contact_lists (name, description)
                VALUES (?, ?)
            ''', (name, description))
            
            conn.commit()
            QMessageBox.information(self, "Succès", "Liste créée!")
            self.list_name_edit.clear()
            self.list_description_edit.clear()
            self.load_lists()
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la création:\n{str(e)}")
        finally:
            conn.close()
    
    def load_lists(self):
        """Charge toutes les listes"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name FROM contact_lists ORDER BY name")
        lists = cursor.fetchall()
        
        self.lists_combo.clear()
        self.lists_combo.addItem("Sélectionner une liste...", None)
        
        for list_id, name in lists:
            self.lists_combo.addItem(name, list_id)
        
        conn.close()
    
    def add_contact_to_list(self):
        """Ajoute le contact sélectionné à la liste sélectionnée"""
        if not self.current_contact_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un contact!")
            return
        
        list_id = self.lists_combo.currentData()
        if not list_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner une liste!")
            return
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO contact_list_members (contact_id, list_id)
                VALUES (?, ?)
            ''', (self.current_contact_id, list_id))
            
            conn.commit()
            QMessageBox.information(self, "Succès", "Contact ajouté à la liste!")
            self.load_list_members()
            
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Information", "Ce contact est déjà dans cette liste!")
        finally:
            conn.close()
    
    def load_list_members(self):
        """Charge les membres de la liste sélectionnée"""
        list_id = self.lists_combo.currentData()
        if not list_id:
            self.list_members_table.setRowCount(0)
            return
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, c.name, c.email
            FROM contacts c
            JOIN contact_list_members clm ON c.id = clm.contact_id
            WHERE clm.list_id = ?
            ORDER BY c.name
        ''', (list_id,))
        
        members = cursor.fetchall()
        self.list_members_table.setRowCount(len(members))
        
        for row, member in enumerate(members):
            self.list_members_table.setItem(row, 0, QTableWidgetItem(member[1]))
            self.list_members_table.setItem(row, 1, QTableWidgetItem(member[2]))
            
            # Bouton de retrait
            remove_btn = QPushButton("Retirer")
            remove_btn.setStyleSheet("background-color: #ff9800; padding: 5px;")
            remove_btn.clicked.connect(lambda checked, cid=member[0]: self.remove_from_list(cid, list_id))
            self.list_members_table.setCellWidget(row, 2, remove_btn)
        
        conn.close()
    
    def remove_from_list(self, contact_id, list_id):
        """Retire un contact de la liste"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM contact_list_members 
            WHERE contact_id = ? AND list_id = ?
        ''', (contact_id, list_id))
        
        conn.commit()
        conn.close()
        
        self.load_list_members()
        QMessageBox.information(self, "Succès", "Contact retiré de la liste!")
    
    def clear_contact_form(self):
        """Vide le formulaire de contact"""
        self.current_contact_id = None
        self.contact_name_edit.clear()
        self.contact_email_edit.clear()
        self.contact_phone_edit.clear()
        self.contact_company_edit.clear()
        self.contact_notes_edit.clear()

class EmailScheduler(ModernWidget):
    """Planificateur d'envois d'emails"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_data()
        self.load_scheduled_emails()
        
        # Timer pour vérifier les emails à envoyer
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_scheduled_emails)
        self.check_timer.start(60000)  # Vérifier chaque minute
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Titre
        title = QLabel("Planification d'Envois")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Formulaire de planification
        form_group = QGroupBox("Nouvel Envoi Planifié")
        form_layout = QFormLayout(form_group)
        
        self.smtp_combo = QComboBox()
        self.template_combo = QComboBox()
        self.recipient_type_combo = QComboBox()
        self.recipient_type_combo.addItems(["Contact individuel", "Liste de contacts"])
        self.recipient_type_combo.currentTextChanged.connect(self.on_recipient_type_changed)
        
        self.recipient_combo = QComboBox()
        self.scheduled_datetime = QDateTimeEdit()
        self.scheduled_datetime.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # +1 heure
        self.scheduled_datetime.setDisplayFormat("dd/MM/yyyy hh:mm")
        
        # Options de relance
        self.reminder_check = QCheckBox("Programmer une relance")
        self.reminder_days = QSpinBox()
        self.reminder_days.setRange(1, 30)
        self.reminder_days.setValue(7)
        self.reminder_days.setSuffix(" jours après")
        
        form_layout.addRow("Configuration SMTP:", self.smtp_combo)
        form_layout.addRow("Template:", self.template_combo)
        form_layout.addRow("Type de destinataire:", self.recipient_type_combo)
        form_layout.addRow("Destinataire:", self.recipient_combo)
        form_layout.addRow("Date/Heure d'envoi:", self.scheduled_datetime)
        form_layout.addRow("", self.reminder_check)
        form_layout.addRow("Relance dans:", self.reminder_days)
        
        schedule_btn = QPushButton("Planifier l'Envoi")
        schedule_btn.clicked.connect(self.schedule_email)
        form_layout.addRow("", schedule_btn)
        
        layout.addWidget(form_group)
        
        # Liste des envois planifiés
        scheduled_group = QGroupBox("Envois Planifiés")
        scheduled_layout = QVBoxLayout(scheduled_group)
        
        self.scheduled_table = QTableWidget()
        self.scheduled_table.setColumnCount(7)
        self.scheduled_table.setHorizontalHeaderLabels([
            "Template", "Destinataire", "Type", "Programmé pour", "Statut", "Relance", "Actions"
        ])
        self.scheduled_table.horizontalHeader().setStretchLastSection(True)
        
        scheduled_layout.addWidget(self.scheduled_table)
        layout.addWidget(scheduled_group)
        
        # Boutons d'action globaux
        actions_layout = QHBoxLayout()
        send_now_btn = QPushButton("Envoyer Maintenant")
        send_now_btn.clicked.connect(self.send_selected_now)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_label = QLabel("")
        
        actions_layout.addWidget(send_now_btn)
        actions_layout.addStretch()
        actions_layout.addWidget(self.status_label)
        
        layout.addLayout(actions_layout)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
    
    def load_data(self):
        """Charge les données nécessaires (SMTP, templates, contacts, listes)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Configurations SMTP
        cursor.execute("SELECT id, name FROM smtp_config ORDER BY is_default DESC, name")
        smtp_configs = cursor.fetchall()
        
        self.smtp_combo.clear()
        for config_id, name in smtp_configs:
            self.smtp_combo.addItem(name, config_id)
        
        # Templates
        cursor.execute("SELECT id, name FROM email_templates ORDER BY name")
        templates = cursor.fetchall()
        
        self.template_combo.clear()
        for template_id, name in templates:
            self.template_combo.addItem(name, template_id)
        
        conn.close()
        self.on_recipient_type_changed()
    
    def on_recipient_type_changed(self):
        """Met à jour la liste des destinataires selon le type sélectionné"""
        self.recipient_combo.clear()
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        if self.recipient_type_combo.currentText() == "Contact individuel":
            cursor.execute("SELECT id, name, email FROM contacts ORDER BY name")
            recipients = cursor.fetchall()
            
            for recipient_id, name, email in recipients:
                self.recipient_combo.addItem(f"{name} ({email})", recipient_id)
        else:
            cursor.execute("SELECT id, name FROM contact_lists ORDER BY name")
            lists = cursor.fetchall()
            
            for list_id, name in lists:
                cursor.execute('''
                    SELECT COUNT(*) FROM contact_list_members WHERE list_id = ?
                ''', (list_id,))
                count = cursor.fetchone()[0]
                self.recipient_combo.addItem(f"{name} ({count} contacts)", list_id)
        
        conn.close()
    
    def schedule_email(self):
        """Planifie un nouvel envoi d'email"""
        smtp_id = self.smtp_combo.currentData()
        template_id = self.template_combo.currentData()
        recipient_id = self.recipient_combo.currentData()
        scheduled_time = self.scheduled_datetime.dateTime().toPyDateTime()
        
        if not all([smtp_id, template_id, recipient_id]):
            QMessageBox.warning(self, "Erreur", "Veuillez remplir tous les champs!")
            return
        
        if scheduled_time <= datetime.now():
            QMessageBox.warning(self, "Erreur", "La date doit être dans le futur!")
            return
        
        recipient_type = "contact" if self.recipient_type_combo.currentText() == "Contact individuel" else "list"
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Créer l'envoi planifié
            cursor.execute('''
                INSERT INTO scheduled_emails 
                (template_id, smtp_config_id, recipient_type, recipient_id, scheduled_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (template_id, smtp_id, recipient_type, recipient_id, scheduled_time))
            
            scheduled_id = cursor.lastrowid
            
            # Ajouter une relance si demandée
            if self.reminder_check.isChecked():
                reminder_time = scheduled_time + timedelta(days=self.reminder_days.value())
                cursor.execute('''
                    INSERT INTO reminders (scheduled_email_id, reminder_time, message)
                    VALUES (?, ?, ?)
                ''', (scheduled_id, reminder_time, "Relance automatique"))
            
            conn.commit()
            QMessageBox.information(self, "Succès", "Envoi planifié avec succès!")
            self.load_scheduled_emails()
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la planification:\n{str(e)}")
        finally:
            conn.close()
    
    def load_scheduled_emails(self):
        """Charge la liste des envois planifiés"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT se.id, et.name as template_name, se.recipient_type, se.recipient_id,
                   se.scheduled_time, se.status, se.sent_at,
                   (SELECT COUNT(*) FROM reminders WHERE scheduled_email_id = se.id) as has_reminder
            FROM scheduled_emails se
            JOIN email_templates et ON se.template_id = et.id
            ORDER BY se.scheduled_time DESC
        ''')
        
        scheduled_emails = cursor.fetchall()
        self.scheduled_table.setRowCount(len(scheduled_emails))
        
        for row, email in enumerate(scheduled_emails):
            email_id, template_name, recipient_type, recipient_id, scheduled_time, status, sent_at, has_reminder = email
            
            # Nom du destinataire
            if recipient_type == "contact":
                cursor.execute("SELECT name, email FROM contacts WHERE id = ?", (recipient_id,))
                recipient_info = cursor.fetchone()
                recipient_name = f"{recipient_info[0]} ({recipient_info[1]})" if recipient_info else "Contact supprimé"
            else:
                cursor.execute("SELECT name FROM contact_lists WHERE id = ?", (recipient_id,))
                list_info = cursor.fetchone()
                recipient_name = list_info[0] if list_info else "Liste supprimée"
            
            self.scheduled_table.setItem(row, 0, QTableWidgetItem(template_name))
            self.scheduled_table.setItem(row, 1, QTableWidgetItem(recipient_name))
            self.scheduled_table.setItem(row, 2, QTableWidgetItem("Contact" if recipient_type == "contact" else "Liste"))
            self.scheduled_table.setItem(row, 3, QTableWidgetItem(scheduled_time))
            
            # Statut avec couleur
            status_item = QTableWidgetItem(status.upper())
            if status == "sent":
                status_item.setBackground(QColor("#4caf50"))
            elif status == "failed":
                status_item.setBackground(QColor("#f44336"))
            else:
                status_item.setBackground(QColor("#ff9800"))
            
            self.scheduled_table.setItem(row, 4, status_item)
            self.scheduled_table.setItem(row, 5, QTableWidgetItem("Oui" if has_reminder else "Non"))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 5, 5, 5)
            
            if status == "pending":
                edit_btn = QPushButton("Modifier")
                edit_btn.clicked.connect(lambda checked, eid=email_id: self.edit_scheduled_email(eid))
                actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Supprimer")
            delete_btn.setStyleSheet("background-color: #d32f2f; padding: 5px;")
            delete_btn.clicked.connect(lambda checked, eid=email_id: self.delete_scheduled_email(eid))
            actions_layout.addWidget(delete_btn)
            
            self.scheduled_table.setCellWidget(row, 6, actions_widget)
        
        conn.close()
    
    def check_scheduled_emails(self):
        """Vérifie et envoie les emails planifiés"""
        current_time = datetime.now()
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT se.id, se.template_id, se.smtp_config_id, se.recipient_type, se.recipient_id
            FROM scheduled_emails se
            WHERE se.status = 'pending' AND se.scheduled_time <= ?
        ''', (current_time,))
        
        emails_to_send = cursor.fetchall()
        
        for email_info in emails_to_send:
            self.send_scheduled_email(email_info)
        
        if emails_to_send:
            self.load_scheduled_emails()
        
        conn.close()
    
    def send_scheduled_email(self, email_info):
        """Envoie un email planifié"""
        email_id, template_id, smtp_id, recipient_type, recipient_id = email_info
        
        try:
            # Récupérer les données nécessaires
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Configuration SMTP
            cursor.execute("SELECT * FROM smtp_config WHERE id = ?", (smtp_id,))
            smtp_config = cursor.fetchone()
            
            if not smtp_config:
                raise Exception("Configuration SMTP introuvable")
            
            smtp_dict = {
                'smtp_server': smtp_config[2],
                'smtp_port': smtp_config[3],
                'email': smtp_config[4],
                'password': smtp_config[5],
                'use_tls': smtp_config[6]
            }
            
            # Template
            cursor.execute("SELECT * FROM email_templates WHERE id = ?", (template_id,))
            template = cursor.fetchone()
            
            if not template:
                raise Exception("Template introuvable")
            
            template_dict = {
                'subject': template[2],
                'content': template[3]
            }
            
            # Destinataires
            recipients = []
            if recipient_type == "contact":
                cursor.execute("SELECT name, email, company FROM contacts WHERE id = ?", (recipient_id,))
                contact = cursor.fetchone()
                if contact:
                    recipients.append({
                        'name': contact[0],
                        'email': contact[1],
                        'company': contact[2] or ''
                    })
            else:
                cursor.execute('''
                    SELECT c.name, c.email, c.company
                    FROM contacts c
                    JOIN contact_list_members clm ON c.id = clm.contact_id
                    WHERE clm.list_id = ?
                ''', (recipient_id,))
                
                for contact in cursor.fetchall():
                    recipients.append({
                        'name': contact[0],
                        'email': contact[1],
                        'company': contact[2] or ''
                    })
            
            if not recipients:
                raise Exception("Aucun destinataire trouvé")
            
            # Envoi via thread
            self.email_sender = EmailSender(smtp_dict, template_dict, recipients)
            self.email_sender.finished_sending.connect(
                lambda success, message, eid=email_id: self.on_email_sent(eid, success, message)
            )
            self.email_sender.start()
            
            conn.close()
            
        except Exception as e:
            # Marquer comme échoué
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE scheduled_emails 
                SET status = 'failed', sent_at = ?
                WHERE id = ?
            ''', (datetime.now(), email_id))
            conn.commit()
            conn.close()
            
            print(f"Erreur envoi email ID {email_id}: {str(e)}")
    
    def on_email_sent(self, email_id, success, message):
        """Callback après envoi d'email"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        status = "sent" if success else "failed"
        cursor.execute('''
            UPDATE scheduled_emails 
            SET status = ?, sent_at = ?
            WHERE id = ?
        ''', (status, datetime.now(), email_id))
        
        conn.commit()
        conn.close()
        
        self.status_label.setText(message)
    
    def send_selected_now(self):
        """Envoie immédiatement l'email sélectionné"""
        current_row = self.scheduled_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un email à envoyer!")
            return
        
        # Récupérer l'ID de l'email depuis la base
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT se.id, se.template_id, se.smtp_config_id, se.recipient_type, se.recipient_id
            FROM scheduled_emails se
            JOIN email_templates et ON se.template_id = et.id
            ORDER BY se.scheduled_time DESC
            LIMIT 1 OFFSET ?
        ''', (current_row,))
        
        email_info = cursor.fetchone()
        conn.close()
        
        if email_info:
            self.send_scheduled_email(email_info)
            QMessageBox.information(self, "Info", "Envoi en cours...")
    
    def edit_scheduled_email(self, email_id):
        """Édite un email planifié"""
        # Implementation simplifiée - peut être étendue
        QMessageBox.information(self, "Info", f"Édition de l'email ID: {email_id}\n(Fonctionnalité à implémenter)")
    
    def delete_scheduled_email(self, email_id):
        """Supprime un email planifié"""
        reply = QMessageBox.question(self, "Confirmation", 
                                   "Êtes-vous sûr de vouloir supprimer cet envoi planifié?")
        
        if reply == QMessageBox.Yes:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM reminders WHERE scheduled_email_id = ?", (email_id,))
            cursor.execute("DELETE FROM scheduled_emails WHERE id = ?", (email_id,))
            
            conn.commit()
            conn.close()
            
            self.load_scheduled_emails()
            QMessageBox.information(self, "Succès", "Envoi planifié supprimé!")

class MainWindowMail(QMainWindow):
    """Fenêtre principale de l'application"""
    
    def __init__(self,parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.init_ui()
        self.setWindowTitle("Gestionnaire d'Emails Professionnel")
        self.setGeometry(100, 100, 1400, 900)
        
        # Appliquer le thème sombre
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QMenuBar {
                background-color: #2d2d2d;
                color: #ffffff;
                border-bottom: 1px solid #555555;
            }
            QMenuBar::item {
                padding: 8px 16px;
            }
            QMenuBar::item:selected {
                background-color: #0d7377;
            }
        QStatusBar {
                background-color: #2d2d2d;
                color: #ffffff;
                border-top: 1px solid #555555;
            }
            QToolBar {
                background-color: #2d2d2d;
                border: none;
                padding: 5px;
            }
        """)
    
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        # Barre d'outils
        toolbar = self.addToolBar("Outils")
        toolbar.setIconSize(QSize(32, 32))
        
        # Actions principales
        send_action = QAction(QIcon.fromTheme("mail-send"), "Envoyer un email", self)
        contacts_action = QAction(QIcon.fromTheme("address-book"), "Contacts", self)
        templates_action = QAction(QIcon.fromTheme("document-new"), "Templates", self)
        schedule_action = QAction(QIcon.fromTheme("view-calendar"), "Planification", self)
        
        toolbar.addAction(send_action)
        toolbar.addAction(contacts_action)
        toolbar.addAction(templates_action)
        toolbar.addAction(schedule_action)
        
        # Zone centrale avec onglets
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(True)
        
        # Onglets
        self.smtp_tab = SMTPConfigWidget(self.db_manager)
        self.templates_tab = TemplateManager(self.db_manager)
        self.contacts_tab = ContactManager(self.db_manager)
        self.scheduler_tab = EmailScheduler(self.db_manager)
        
        self.tab_widget.addTab(self.smtp_tab, QIcon.fromTheme("network-server"), "SMTP")
        self.tab_widget.addTab(self.templates_tab, QIcon.fromTheme("text-x-generic"), "Templates")
        self.tab_widget.addTab(self.contacts_tab, QIcon.fromTheme("x-office-contact"), "Contacts")
        self.tab_widget.addTab(self.scheduler_tab, QIcon.fromTheme("x-office-calendar"), "Planification")
        
        self.setCentralWidget(self.tab_widget)
        
        # Barre de statut
        self.statusBar().showMessage("Prêt")
        
        # Connecter les actions
        send_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(3))
        contacts_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(2))
        templates_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))
        schedule_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(3))
    
    def closeEvent(self, event):
        """Gère la fermeture de l'application"""
        reply = QMessageBox.question(
            self, 'Confirmation',
            'Êtes-vous sûr de vouloir quitter?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

def main():
    """Point d'entrée de l'application"""
    app = QApplication(sys.argv)
    
    # Appliquer une palette de couleurs sombre
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)
    
    # Style Fusion pour un look moderne
    app.setStyle("Fusion")
    
    window = MainWindowMail()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
