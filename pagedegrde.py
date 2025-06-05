# -*- coding: utf-8 -*-
import sys
import os
import sqlite3
import base64
import datetime
import json
import shutil
from typing import Optional, List, Dict, Any, Tuple, Union
from PyQt5.QtWidgets import QAction

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox, 
                             QFileDialog, QMessageBox, QScrollArea, QFrame, 
                             QSizePolicy, QGraphicsDropShadowEffect, QCompleter,
                             QDialog, QDialogButtonBox, QColorDialog, QGridLayout,
                             QRadioButton, QButtonGroup, QSpacerItem, QGraphicsView,
                             QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem,
                             QAbstractItemView, QListView, QCheckBox, QSpinBox,
                             QSlider, QGraphicsProxyWidget, QProgressBar, QSplitter,
                             QListWidget, QListWidgetItem, QStackedWidget, QGraphicsSceneMouseEvent,
                             QGraphicsItem)

from PyQt5.QtCore import (Qt, QSize, QPoint, QRect, QTimer, QPropertyAnimation, 
                          QEasingCurve, QByteArray, QBuffer, QIODevice, pyqtSignal, 
                          QEvent, QRegExp, QSettings, QUrl, QPointF, QRectF, QLineF, pyqtProperty)

from PyQt5.QtGui import (QFont, QPixmap, QPalette, QColor, QIcon, QLinearGradient, 
                         QPainter, QBrush, QPen, QFontDatabase, QMovie, QImage, QPainterPath,
                         QDesktopServices, QFontMetrics, QPolygonF, QTransform, QKeySequence,
                         QRegExpValidator)


from reportlab.pdfgen import canvas as reportlab_canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Line, Drawing
from reportlab.graphics.barcode import code128, qr
from reportlab.graphics import renderPDF
import io # Added for io.BytesIO

# Define APP_ROOT_DIR for font path resolution
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    APP_ROOT_DIR = sys._MEIPASS
else:
    APP_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Global configuration (can be overridden by user preferences or template settings)
APP_CONFIG: Dict[str, Any] = {
    "default_font": "Arial",
    "default_font_size": 12,
    "default_text_color": "#000000",
    "preview_background_color": "#F0F0F0",
    "max_history": 20,
    "autosave_interval": 30000,  # milliseconds (30 seconds)
    "default_language": "Français",
    "db_path": "cover_pages.db"
}

# --- Translator Class ---
class Translator:
    def __init__(self):
        self.translations = {}
        self.current_language = "Français" # Default language
        # Define available languages and their display names
        self.LANGUAGES = {
            "fr": "Français",
            "en": "English",
            "es": "Español",
            "ar": "Arabic",
            "tr": "Turkish",
            "pt": "Portuguese"
        }
        self.init_translations()

    def init_translations(self):
        # Initialize for French (Primary)
        self.translations["Français"] = {
            # Dialog specific
            "Préférences": "Préférences",
            "Auteur par défaut:": "Auteur par défaut:",
            "Institution par défaut:": "Institution par défaut:",
            "Langue:": "Langue:",
            "Police par défaut:": "Police par défaut:",
            "Taille de police par défaut:": "Taille de police par défaut:",
            "Chemin base de données:": "Chemin base de données:",
            "OK": "OK",
            "Annuler": "Annuler",
            "Appliquer": "Appliquer",
            "Les préférences ont été appliquées.": "Les préférences ont été appliquées.",
            # Main Window & Menus
            "Générateur de Page de Garde Moderne": "Générateur de Page de Garde Moderne",
            "&Fichier": "&Fichier",
            "&Édition": "&Édition",
            "&Affichage": "&Affichage",
            "&Aide": "&Aide",
            "&Nouveau": "&Nouveau",
            "&Ouvrir Modèle...": "&Ouvrir Modèle...",
            "&Enregistrer Modèle": "&Enregistrer Modèle",
            "Enregistrer Modèle &Sous...": "Enregistrer Modèle &Sous...",
            "Exporter en &PDF...": "Exporter en &PDF...",
            "&Préférences...": "&Préférences...",
            "&Quitter": "&Quitter",
            "&À propos": "&À propos",
            "Barre d'outils principale": "Barre d'outils principale",
            # Panel Group Titles
            "Modèles": "Modèles",
            "Informations du Document": "Informations du Document",
            "Mise en Page et Style": "Mise en Page et Style",
            "Logo": "Logo",
            # Labels in "Informations du Document"
            "Titre:": "Titre:", "Titre principal du document": "Titre principal du document",
            "Sous-titre:": "Sous-titre:", "Sous-titre (optionnel)": "Sous-titre (optionnel)",
            "Auteur:": "Auteur:", "Nom de l'auteur": "Nom de l'auteur",
            "Institution:": "Institution:", "Université, Organisation, etc.": "Université, Organisation, etc.",
            "Département/Faculté:": "Département/Faculté:", "Département ou faculté (optionnel)": "Département ou faculté (optionnel)",
            "Type de document:": "Type de document:", "Rapport de stage, Thèse, Mémoire...": "Rapport de stage, Thèse, Mémoire...",
            "Date (YYYY-MM-DD):": "Date (YYYY-MM-DD):",
            "Version:": "Version:", "1.0, Version finale...": "1.0, Version finale...",
            # Labels/Text in "Mise en Page et Style"
            "Style de modèle:": "Style de modèle:",
            "Police du Titre:": "Police du Titre:",
            "Couleur du Texte Principal:": "Couleur du Texte Principal:",
            "Choisir Couleur": "Choisir Couleur",
            "Taille Police Titre:": "Taille Police Titre:",
            "Afficher la ligne horizontale": "Afficher la ligne horizontale",
            # Labels/Text in "Logo"
            "Chemin vers l'image du logo": "Chemin vers l'image du logo",
            "Charger Logo": "Charger Logo",
            "Retirer Logo": "Retirer Logo",
            "Aucun logo chargé.": "Aucun logo chargé.",
            # Main Action Buttons
            "Aperçu Rapide": "Aperçu Rapide",
            "Générer PDF": "Générer PDF",
            # Template List Buttons & Labels
            "Charger": "Charger",
            "Supprimer": "Supprimer",
            "Nom du modèle actuel:": "Nom du modèle actuel:",
            "Nouveau Modèle": "Nouveau Modèle", # Placeholder for template name
            # Common Dialog Titles/Messages
            "Nom Requis": "Nom Requis",
            "Veuillez donner un nom à ce modèle.": "Veuillez donner un nom à ce modèle.",
            "Modèle Existant": "Modèle Existant",
            "Un modèle nommé '{}' existe déjà. Voulez-vous le remplacer?": "Un modèle nommé '{}' existe déjà. Voulez-vous le remplacer?",
            "Confirmation de Suppression": "Confirmation de Suppression",
            "Êtes-vous sûr de vouloir supprimer le modèle '{}'?": "Êtes-vous sûr de vouloir supprimer le modèle '{}'?",
            "Modèle Enregistré": "Modèle Enregistré",
            "Modèle '{}' enregistré avec succès.": "Modèle '{}' enregistré avec succès.",
            "Erreur d'Enregistrement": "Erreur d'Enregistrement",
            "Impossible d'enregistrer le modèle.": "Impossible d'enregistrer le modèle.",
            "Charger Modèle": "Charger Modèle", # Dialog title / Button text
            "Veuillez sélectionner un modèle dans la liste.": "Veuillez sélectionner un modèle dans la liste.",
            "Modèle Supprimé": "Modèle Supprimé",
            "Modèle '{}' supprimé.": "Modèle '{}' supprimé.",
            "Formulaire réinitialisé.": "Formulaire réinitialisé.",
            "Erreur Logo": "Erreur Logo",
            "Impossible de charger le logo: {}": "Impossible de charger le logo: {}",
            "Format d'image non reconnu ou fichier corrompu.": "Format d'image non reconnu ou fichier corrompu.",
            "PDF Généré": "PDF Généré",
            "Le fichier PDF a été enregistré sous:\n{}": "Le fichier PDF a été enregistré sous:\n{}",
            "Ouvrir PDF": "Ouvrir PDF",
            "Voulez-vous ouvrir le fichier généré?": "Voulez-vous ouvrir le fichier généré?",
            "Quitter": "&Quitter", # Dialog title / Menu item
            "Êtes-vous sûr de vouloir quitter?": "Êtes-vous sûr de vouloir quitter?",
            "À propos de Générateur de Page de Garde": "À propos de Générateur de Page de Garde",
            "Erreur d'aperçu: {}": "Erreur d'aperçu: {}",
            "Impossible de charger l'aperçu du PDF.": "Impossible de charger l'aperçu du PDF.",
            "Note: Ceci est un aperçu simplifié.": "Note: Ceci est un aperçu simplifié.",
            "Aperçu PDF (Rendu réel requis)": "Aperçu PDF (Rendu réel requis)",
            "Aperçu de '{}'": "Aperçu de '{}'",
            "Aperçu du PDF en mémoire": "Aperçu du PDF en mémoire",
            "Impossible de générer l'aperçu.": "Impossible de générer l'aperçu.",
            "Erreur PDF": "Erreur PDF",
            "Impossible de générer le PDF en mémoire: {}": "Impossible de générer le PDF en mémoire: {}",
            "Aucune donnée PDF à enregistrer.": "Aucune donnée PDF à enregistrer.",
            "Enregistrer le PDF": "Enregistrer le PDF",
            "Changement de Langue": "Changement de Langue",
            "Le changement de langue prendra effet au prochain redémarrage ou nécessite une actualisation de l'interface utilisateur (non implémenté).": "Le changement de langue prendra effet au prochain redémarrage ou nécessite une actualisation de l'interface utilisateur (non implémenté).",
             "Modèle Copié": "Modèle Copié",
             "Logo chargé depuis la base de données: {}": "Logo chargé depuis la base de données: {}",
             "Choisir un Logo": "Choisir un Logo", # For QFileDialog title
             "PageDeGarde": "PageDeGarde", # Default filename part
             "Impossible de trouver les données du modèle sélectionné.": "Impossible de trouver les données du modèle sélectionné.",
             "Supprimer Modèle": "Supprimer Modèle", # Dialog title
             "Veuillez sélectionner un modèle à supprimer.": "Veuillez sélectionner un modèle à supprimer.",
             "Moderne": "Moderne", "Classique": "Classique", "Minimaliste": "Minimaliste", "Personnalisé": "Personnalisé", # ComboBox items
             "<b>Générateur de Page de Garde Moderne</b> v0.1 Alpha\n<p>Une application pour créer facilement des pages de garde personnalisées.\n<p>Développé avec PyQt5 et ReportLab.\n<p>© 2023 Votre Nom/Organisation. Tous droits réservés.\n<p><a href='https://example.com'>Visitez notre site web</a>\n": "<b>Générateur de Page de Garde Moderne</b> v0.1 Alpha\n<p>Une application pour créer facilement des pages de garde personnalisées.\n<p>Développé avec PyQt5 et ReportLab.\n<p>© 2023 Votre Nom/Organisation. Tous droits réservés.\n<p><a href='https://example.com'>Visitez notre site web</a>\n",
        }
        # Initialize for English
        self.translations["English"] = {
            # Dialog specific
            "Préférences": "Preferences",
            "Auteur par défaut:": "Default Author:",
            "Institution par défaut:": "Default Institution:",
            "Langue:": "Language:",
            "Police par défaut:": "Default Font:",
            "Taille de police par défaut:": "Default Font Size:",
            "Chemin base de données:": "Database Path:",
            "OK": "OK",
            "Annuler": "Cancel",
            "Appliquer": "Apply",
            "Les préférences ont été appliquées.": "Preferences have been applied.",
            # Main Window & Menus
            "Générateur de Page de Garde Moderne": "Modern Cover Page Generator",
            "&Fichier": "&File",
            "&Édition": "&Edit",
            "&Affichage": "&View",
            "&Aide": "&Help",
            "&Nouveau": "&New",
            "&Ouvrir Modèle...": "&Open Template...",
            "&Enregistrer Modèle": "&Save Template",
            "Enregistrer Modèle &Sous...": "Save Template &As...",
            "Exporter en &PDF...": "Export to &PDF...",
            "&Préférences...": "&Preferences...",
            "&Quitter": "&Quit",
            "&À propos": "&About",
            "Barre d'outils principale": "Main Toolbar",
            # Panel Group Titles
            "Modèles": "Templates",
            "Informations du Document": "Document Information",
            "Mise en Page et Style": "Layout and Style",
            "Logo": "Logo",
            # Labels in "Informations du Document"
            "Titre:": "Title:", "Titre principal du document": "Main title of the document",
            "Sous-titre:": "Subtitle:", "Sous-titre (optionnel)": "Subtitle (optional)",
            "Auteur:": "Author:", "Nom de l'auteur": "Author's name",
            "Institution:": "Institution:", "Université, Organisation, etc.": "University, Organization, etc.",
            "Département/Faculté:": "Department/Faculty:", "Département ou faculté (optionnel)": "Department or faculty (optional)",
            "Type de document:": "Document Type:", "Rapport de stage, Thèse, Mémoire...": "Internship report, Thesis, Dissertation...",
            "Date (YYYY-MM-DD):": "Date (YYYY-MM-DD):",
            "Version:": "Version:", "1.0, Version finale...": "1.0, Final version...",
            # Labels/Text in "Mise en Page et Style"
            "Style de modèle:": "Template Style:",
            "Police du Titre:": "Title Font:",
            "Couleur du Texte Principal:": "Main Text Color:",
            "Choisir Couleur": "Choose Color",
            "Taille Police Titre:": "Title Font Size:",
            "Afficher la ligne horizontale": "Show Horizontal Line",
            # Labels/Text in "Logo"
            "Chemin vers l'image du logo": "Path to logo image",
            "Charger Logo": "Load Logo",
            "Retirer Logo": "Remove Logo",
            "Aucun logo chargé.": "No logo loaded.",
            # Main Action Buttons
            "Aperçu Rapide": "Quick Preview",
            "Générer PDF": "Generate PDF",
            # Template List Buttons & Labels
            "Charger": "Load",
            "Supprimer": "Delete",
            "Nom du modèle actuel:": "Current template name:",
            "Nouveau Modèle": "New Template",
            # Common Dialog Titles/Messages
            "Nom Requis": "Name Required",
            "Veuillez donner un nom à ce modèle.": "Please provide a name for this template.",
            "Modèle Existant": "Template Exists",
            "Un modèle nommé '{}' existe déjà. Voulez-vous le remplacer?": "A template named '{}' already exists. Do you want to replace it?",
            "Confirmation de Suppression": "Confirm Deletion",
            "Êtes-vous sûr de vouloir supprimer le modèle '{}'?": "Are you sure you want to delete the template '{}'?",
            "Modèle Enregistré": "Template Saved",
            "Modèle '{}' enregistré avec succès.": "Template '{}' saved successfully.",
            "Erreur d'Enregistrement": "Save Error",
            "Impossible d'enregistrer le modèle.": "Could not save the template.",
            "Charger Modèle": "Load Template",
            "Veuillez sélectionner un modèle dans la liste.": "Please select a template from the list.",
            "Modèle Supprimé": "Template Deleted",
            "Modèle '{}' supprimé.": "Template '{}' deleted.",
            "Formulaire réinitialisé.": "Form reset.",
            "Erreur Logo": "Logo Error",
            "Impossible de charger le logo: {}": "Could not load logo: {}",
            "Format d'image non reconnu ou fichier corrompu.": "Image format not recognized or file corrupted.",
            "PDF Généré": "PDF Generated",
            "Le fichier PDF a été enregistré sous:\n{}": "The PDF file has been saved as:\n{}",
            "Ouvrir PDF": "Open PDF",
            "Voulez-vous ouvrir le fichier généré?": "Do you want to open the generated file?",
            "Quitter": "&Quit", # Dialog context
            "Êtes-vous sûr de vouloir quitter?": "Are you sure you want to quit?",
            "À propos de Générateur de Page de Garde": "About Cover Page Generator",
            "Erreur d'aperçu: {}": "Preview Error: {}",
            "Impossible de charger l'aperçu du PDF.": "Could not load PDF preview.",
            "Note: Ceci est un aperçu simplifié.": "Note: This is a simplified preview.",
            "Aperçu PDF (Rendu réel requis)": "PDF Preview (Actual rendering required)",
            "Aperçu de '{}'": "Preview of '{}'",
            "Aperçu du PDF en mémoire": "In-memory PDF Preview",
            "Impossible de générer l'aperçu.": "Could not generate preview.",
            "Erreur PDF": "PDF Error",
            "Impossible de générer le PDF en mémoire: {}": "Could not generate in-memory PDF: {}",
            "Aucune donnée PDF à enregistrer.": "No PDF data to save.",
            "Enregistrer le PDF": "Save PDF",
            "Changement de Langue": "Language Change",
            "Le changement de langue prendra effet au prochain redémarrage ou nécessite une actualisation de l'interface utilisateur (non implémenté).": "Language change will take effect on next restart or requires UI refresh (not implemented).",
            "Modèle Copié": "Copied Template",
            "Logo chargé depuis la base de données: {}": "Logo loaded from database: {}",
            "Choisir un Logo": "Choose a Logo",
            "PageDeGarde": "CoverPage", # Default filename part
            "Impossible de trouver les données du modèle sélectionné.": "Could not find data for selected template.",
            "Supprimer Modèle": "Delete Template",
            "Veuillez sélectionner un modèle à supprimer.": "Please select a template to delete.",
            "Moderne": "Modern", "Classique": "Classic", "Minimaliste": "Minimalist", "Personnalisé": "Custom", # ComboBox items
            "<b>Générateur de Page de Garde Moderne</b> v0.1 Alpha\n<p>Une application pour créer facilement des pages de garde personnalisées.\n<p>Développé avec PyQt5 et ReportLab.\n<p>© 2023 Votre Nom/Organisation. Tous droits réservés.\n<p><a href='https://example.com'>Visitez notre site web</a>\n": "<b>Modern Cover Page Generator</b> v0.1 Alpha\n<p>An application to easily create custom cover pages.\n<p>Developed with PyQt5 and ReportLab.\n<p>© 2023 Your Name/Organization. All rights reserved.\n<p><a href='https://example.com'>Visit our website</a>\n",
        }
        # Initialize for Spanish
        self.translations["Español"] = {
            # Dialog specific
            "Préférences": "Preferencias",
            "Auteur par défaut:": "Autor por Defecto:",
            "Institution par défaut:": "Institución por Defecto:",
            "Langue:": "Idioma:",
            "Police par défaut:": "Fuente por Defecto:",
            "Taille de police par défaut:": "Tamaño de Fuente por Defecto:",
            "Chemin base de données:": "Ruta de Base de Datos:",
            "OK": "Aceptar",
            "Annuler": "Cancelar",
            "Appliquer": "Aplicar",
            "Les préférences ont été appliquées.": "Las preferencias han sido aplicadas.",
            # ... (Add more Spanish translations as needed, mirroring English and French)
            "Générateur de Page de Garde Moderne": "Generador de Portadas Moderno", # Example
            "Générateur de Page de Garde Moderne": "Generador de Portadas Moderno", # Example
            "&Fichier": "&Archivo", # Example
        }
        # Initialize for Arabic, Turkish, Portuguese with a few placeholder translations
        self.translations["Arabic"] = {
            "Préférences": "[AR] Préférences", "Langue:": "[AR] Langue:",
            "OK": "[AR] OK", "Annuler": "[AR] Annuler", "Appliquer": "[AR] Appliquer",
            "Générateur de Page de Garde Moderne": "[AR] Générateur de Page de Garde Moderne",
            "&Fichier": "[AR] &Fichier",
        }
        self.translations["Turkish"] = {
            "Préférences": "[TR] Tercihler", "Langue:": "[TR] Dil:",
            "OK": "[TR] Tamam", "Annuler": "[TR] İptal", "Appliquer": "[TR] Uygula",
            "Générateur de Page de Garde Moderne": "[TR] Modern Kapak Sayfası Oluşturucu",
            "&Fichier": "[TR] &Dosya",
        }
        self.translations["Portuguese"] = {
            "Préférences": "[PT] Preferências", "Langue:": "[PT] Idioma:",
            "OK": "[PT] OK", "Annuler": "[PT] Cancelar", "Appliquer": "[PT] Aplicar",
            "Générateur de Page de Garde Moderne": "[PT] Gerador de Páginas de Capa Moderno",
            "&Fichier": "[PT] &Arquivo",
        }


    def set_language(self, language_display_name: str):
        # Use the display name as the key for self.translations dictionary
        if language_display_name in self.translations:
            self.current_language = language_display_name # Storing the display name
            print(f"Translator: Language set to {language_display_name}")
        else:
            # Fallback logic or warning
            # Attempt to find by code if display name fails (e.g. if system locale was 'en' but display is 'English')
            found_by_code = False
            for code, display_name_iter in self.LANGUAGES.items():
                if code == language_display_name and display_name_iter in self.translations: # language_display_name might be a code here
                    self.current_language = display_name_iter
                    print(f"Translator: Language set to {display_name_iter} (via code '{code}')")
                    found_by_code = True
                    break
            if not found_by_code:
                print(f"Translator: Warning - Language display name '{language_display_name}' not found in translations. Keeping '{self.current_language}'.")


    def tr(self, key_text: str, *args) -> str:
        # Try current language (using display name as key)
        translation = self.translations.get(self.current_language, {}).get(key_text)
        
        # Fallback to French (primary key source) if not found in current language
        # Assuming "Français" is the display name for French
        if translation is None and self.current_language != self.LANGUAGES.get("fr", "Français"):
            translation = self.translations.get(self.LANGUAGES.get("fr", "Français"), {}).get(key_text)
            
        # Fallback to key_text itself if no translation found
        if translation is None:
            # print(f"Translator: Key '{key_text}' not found for language '{self.current_language}'. Using key as fallback.")
            translation = f"[!] {key_text}" # Or just key_text

        if args:
            try:
                return translation.format(*args)
            except (TypeError, IndexError) as e: # Changed from KeyError to TypeError/IndexError for format issues
                print(f"Translator: Error formatting key '{key_text}' with args {args}: {e}")
                return f"[F!] {translation}" # Indicate formatting error
        return translation

# --- Custom Widgets ---

class AnimatedButton(QPushButton):
    def __init__(self, text="", icon_path=None, style_type="primary", parent=None):
        super().__init__(text, parent)
        self.style_type = style_type
        self.icon_path = icon_path
        self._effect_strength_val = 0.0  # Store the actual property value
        self._animation = QPropertyAnimation(self, b"effect_strength", self)
        self._animation.setDuration(150)
        self._effect = QGraphicsDropShadowEffect(self)
        self._effect.setOffset(0, 0)
        self._effect.setBlurRadius(0)
        self._effect.setColor(QColor(0,0,0,0))
        self.setGraphicsEffect(self._effect)
        self.setMinimumHeight(35)
        self.setCursor(Qt.PointingHandCursor)
        self.apply_style()

        if self.icon_path:
            self.setIcon(QIcon(self.icon_path))
            self.setIconSize(QSize(18,18))

    def apply_style(self):
        # Base style
        font = QFont("Segoe UI", 10, QFont.Bold)
        self.setFont(font)
        
        radius = "8px"
        common_style = f"""
            QPushButton {{
                border: 1px solid transparent;
                border-radius: {radius};
                padding: 8px 12px;
                outline: none;
            }}
            QPushButton:hover {{
                border: 1px solid #888888;
            }}
            QPushButton:pressed {{
                border: 1px solid #555555;
            }}
        """
        if self.style_type == "primary":
            self.setStyleSheet(common_style + f"""
                QPushButton {{
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #007BFF, stop:1 #0056b3);
                    color: white;
                }}
                QPushButton:hover {{ background-color: #0069D9; border-color: #0056b3; }}
                QPushButton:pressed {{ background-color: #0056b3; }}
            """)
        elif self.style_type == "secondary":
            self.setStyleSheet(common_style + f"""
                QPushButton {{
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6c757d, stop:1 #545b62);
                    color: white;
                }}
                QPushButton:hover {{ background-color: #5a6268; border-color: #4e555b;}}
                QPushButton:pressed {{ background-color: #545b62; }}
            """)
        elif self.style_type == "danger":
             self.setStyleSheet(common_style + f"""
                QPushButton {{
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #dc3545, stop:1 #c82333);
                    color: white;
                }}
                QPushButton:hover {{ background-color: #c82333; border-color: #b21f2d;}}
                QPushButton:pressed {{ background-color: #bd2130; }}
            """)
        else: # default/flat
            self.setStyleSheet(common_style + f"""
                QPushButton {{
                    background-color: #f8f9fa;
                    color: #212529;
                    border: 1px solid #ced4da;
                }}
                QPushButton:hover {{ background-color: #e2e6ea; border-color: #dae0e5;}}
                QPushButton:pressed {{ background-color: #dae0e5; }}
            """)

    def _get_effect_strength(self):
        return self._effect_strength_val

    def _set_effect_strength(self, value: float):
        self._effect_strength_val = value
        self._effect.setBlurRadius(self._effect_strength_val) # Use the stored value
        self._effect.setColor(QColor(0,0,0, int(self._effect_strength_val*5))) # Use the stored value

    effect_strength = pyqtProperty(float, _get_effect_strength, _set_effect_strength)

    def enterEvent(self, event: QEvent):
        self._animation.setStartValue(self.effect_strength) # Use property getter
        self._animation.setEndValue(10)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        self._animation.setStartValue(self.effect_strength) # Use property getter
        self._animation.setEndValue(0)
        self._animation.start()
        super().leaveEvent(event)

class ModernLineEdit(QLineEdit):
    def __init__(self, placeholder_text="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        self.setFont(QFont("Segoe UI", 10))
        self.setMinimumHeight(30)
        self.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 6px;
                padding: 5px 8px;
                background-color: #ffffff;
                selection-background-color: #007BFF;
                selection-color: white;
            }
            QLineEdit:focus {
                border-color: #80bdff;
                outline: 0;
                /* box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25); */ /* Removed as it's not directly supported and QGraphicsDropShadowEffect is used */
            }
            QLineEdit:disabled {
                background-color: #e9ecef;
                opacity: 0.7;
            }
        """)
        self._effect = QGraphicsDropShadowEffect(self)
        self._effect.setOffset(2, 2)
        self._effect.setBlurRadius(5)
        self._effect.setColor(QColor(0,0,0,80))
        self._effect.setEnabled(False)
        self.setGraphicsEffect(self._effect)

    def focusInEvent(self, event: QEvent):
        self._effect.setEnabled(True)
        super().focusInEvent(event)

    def focusOutEvent(self, event: QEvent):
        self._effect.setEnabled(False)
        super().focusOutEvent(event)

class ModernComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 10))
        self.setMinimumHeight(30)
        self.setStyleSheet("""
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 6px;
                padding: 5px 8px;
                background-color: white;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: #ced4da;
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox::down-arrow {
                image: url(icons/arrow-down.png); /* Add a down arrow icon */
                width: 10px;
                height: 10px;
            }
            QComboBox:focus {
                border-color: #80bdff;
            }
            QComboBox QAbstractItemView { /* Style for the dropdown list */
                border: 1px solid #ced4da;
                background-color: white;
                selection-background-color: #007BFF;
                color: #333;
            }
        """)
        # To load custom fonts like Segoe UI, ensure they are installed or load them via QFontDatabase.addApplicationFont
        # For simplicity, assuming Segoe UI is available.

class GlassmorphismFrame(QFrame):
    def __init__(self, parent=None, blur_radius=15, background_opacity=0.3, border_color=QColor(255,255,255,90)):
        super().__init__(parent)
        self.blur_radius = blur_radius
        self.background_opacity = background_opacity # 0.0 (transparent) to 1.0 (opaque)
        self.border_color = border_color
        self.setAttribute(Qt.WA_StyledBackground, True) # Important for stylesheet
        self.setStyleSheet(f"""
            GlassmorphismFrame {{
                background-color: rgba(225, 225, 225, {int(self.background_opacity * 255)}); /* Light background with opacity */
                border-radius: 10px;
                border: 1px solid rgba({border_color.red()},{border_color.green()},{border_color.blue()},{border_color.alpha()});
            }}
        """)
        # In a more complex scenario with background blur, you might need to grab widget behind and apply blur,
        # or use platform specific APIs. For Qt, true glassmorphism is tricky.
        # This provides a styled translucent frame.

class PreviewWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QBrush(QColor(APP_CONFIG.get("preview_background_color", "#F0F0F0"))))
        self.page_item = None # QGraphicsPixmapItem for the PDF page
        self.page_width_mm = 210 # A4
        self.page_height_mm = 297 # A4
        self.dpi = 72 # Standard DPI for screen rendering
        self.scale_factor = 1.0

    def load_pdf_preview(self, pdf_path):
        try:
            # This is a simplified way to get a preview. For high fidelity,
            # you might need a library like Poppler-Qt or MuPDF.
            # For now, we'll render page 1 to a QImage then display.
            
            # If reportlab generated an image directly:
            # image = QImage(pdf_path) 
            
            # If it's a PDF, we need to render it. This part is tricky without external libs.
            # For demonstration, let's assume we have an image representation of the PDF page.
            # In a real app, you'd call a PDF rendering utility here.
            # For now, we'll create a dummy preview.
            
            # Placeholder: Create a QImage from the first page of the PDF
            # This is where you'd integrate a PDF to image conversion
            image = self.render_pdf_page_to_image(pdf_path, 0)

            if image.isNull():
                self.scene.clear()
                self.display_error_message("Impossible de charger l'aperçu du PDF.")
                return

            pixmap = QPixmap.fromImage(image)
            if self.page_item:
                self.scene.removeItem(self.page_item)
            
            self.page_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.page_item)
            
            # Calculate scene rect based on A4 size in pixels
            self.page_width_px = (self.page_width_mm / 25.4) * self.dpi
            self.page_height_px = (self.page_height_mm / 25.4) * self.dpi
            
            self.scene.setSceneRect(0, 0, self.page_width_px, self.page_height_px)
            self.page_item.setPos(0,0) # Ensure pixmap is at the origin of its coordinate system
            
            self.fit_to_view()

        except Exception as e:
            self.scene.clear()
            self.display_error_message(f"Erreur d'aperçu: {e}")
            print(f"Error loading PDF preview: {e}", file=sys.stderr)

    def render_pdf_page_to_image(self, pdf_data_or_path, page_number):
        # This is a placeholder. In a real application, you would use a library
        # like python-poppler-qt5, PyMuPDF (fitz), or Ghostscript to render a PDF page to an image.
        # For this example, let's create a dummy QImage.
        
        # If pdf_data_or_path is actual PDF bytes (from ReportLab buffer):
        # This requires a robust PDF rendering solution.
        
        # Fallback: create a dummy image with text
        image_width_px = int((self.page_width_mm / 25.4) * self.dpi)
        image_height_px = int((self.page_height_mm / 25.4) * self.dpi)
        image = QImage(image_width_px, image_height_px, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.white)
        painter = QPainter(image)
        painter.setPen(Qt.black)
        painter.setFont(QFont("Arial", 20))
        
        text_to_draw = "Aperçu PDF (Rendu réel requis)"
        if isinstance(pdf_data_or_path, str) and os.path.exists(pdf_data_or_path):
            text_to_draw = f"Aperçu de '{os.path.basename(pdf_data_or_path)}'"
        elif isinstance(pdf_data_or_path, bytes):
             text_to_draw = "Aperçu du PDF en mémoire"

        fm = QFontMetrics(painter.font())
        text_rect = fm.boundingRect(text_to_draw)
        painter.drawText((image_width_px - text_rect.width()) / 2, (image_height_px / 2) - text_rect.height(), text_to_draw)
        
        painter.setFont(QFont("Arial", 10))
        painter.drawText(10, image_height_px - 10, "Note: Ceci est un aperçu simplifié.")
        painter.end()
        return image

    def display_error_message(self, message):
        self.scene.clear() # Clear previous content
        text_item = self.scene.addText(message, QFont("Arial", 12))
        text_item.setDefaultTextColor(Qt.red)
        # Center the text item (approximate)
        # view_rect = self.viewport().rect()
        # text_item.setPos(view_rect.width()/2 - text_item.boundingRect().width()/2, 
        #                  view_rect.height()/2 - text_item.boundingRect().height()/2)


    def fit_to_view(self):
        if not self.page_item:
            return
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.scale_factor = self.transform().m11() # Get current scale

    def zoom_in(self, factor=1.1):
        self.scale(factor, factor)
        self.scale_factor *= factor
        
    def zoom_out(self, factor=1.1):
        self.scale(1.0/factor, 1.0/factor)
        self.scale_factor /= factor

    def reset_zoom(self):
        self.fit_to_view() # This already resets zoom to fit the page

    def resizeEvent(self, event: QEvent):
        super().resizeEvent(event)
        self.fit_to_view()


# --- Database Manager ---
class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or APP_CONFIG["db_path"]
        self.init_database()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row # Access columns by name
        return conn

    def init_database(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Templates Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    title TEXT,
                    subtitle TEXT,
                    author TEXT,
                    institution TEXT,
                    department TEXT,
                    doc_type TEXT,
                    template_style TEXT, -- e.g., 'modern', 'classic', 'minimalist'
                    description TEXT,
                    keywords TEXT, -- Comma-separated
                    logo_data BLOB,
                    logo_name TEXT, -- Original filename of the logo
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    config_json TEXT -- Store all other specific settings as JSON
                )
            """)
            # Generation History Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS generation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    author TEXT,
                    file_path TEXT, -- Path to the generated PDF
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    template_id INTEGER,
                    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE SET NULL
                )
            """)
            # User Preferences Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}", file=sys.stderr)
        finally:
            conn.close()

    def save_preference(self, key: str, value: Any):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Convert value to string for storage, simple approach
            # For complex types, consider JSON serialization
            value_str = str(value) if not isinstance(value, (dict, list)) else json.dumps(value)
            cursor.execute("INSERT OR REPLACE INTO user_preferences (key, value) VALUES (?, ?)", (key, value_str))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error saving preference '{key}': {e}", file=sys.stderr)
        finally:
            conn.close()

    def load_preference(self, key: str, default_value: Optional[Any] = None) -> Optional[Any]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                # Attempt to deserialize if it looks like JSON
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0] # Return as string if not JSON
            return default_value
        except sqlite3.Error as e:
            print(f"Error loading preference '{key}': {e}", file=sys.stderr)
            return default_value
        finally:
            conn.close()
    
    # Add methods for templates and history
    def save_template(self, template_data: Dict[str, Any]) -> Optional[int]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Separate logo data if present
            logo_data = template_data.pop('logo_data', None)
            logo_name = template_data.pop('logo_name', None)
            
            # All other fields that are not direct columns go into config_json
            direct_columns = ['name', 'title', 'subtitle', 'author', 'institution', 
                              'department', 'doc_type', 'template_style', 'description', 'keywords']
            
            config_data = {k: v for k, v in template_data.items() if k not in direct_columns}
            config_json = json.dumps(config_data)

            sql = """INSERT INTO templates 
                     (name, title, subtitle, author, institution, department, doc_type, template_style, description, keywords, logo_data, logo_name, config_json) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            params = [
                template_data.get('name'), template_data.get('title'), template_data.get('subtitle'),
                template_data.get('author'), template_data.get('institution'), template_data.get('department'),
                template_data.get('doc_type'), template_data.get('template_style'),
                template_data.get('description'), template_data.get('keywords'),
                logo_data, logo_name, config_json
            ]
            cursor.execute(sql, params)
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error saving template: {e}", file=sys.stderr)
            return None
        finally:
            conn.close()

    def load_templates(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        templates = []
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM templates ORDER BY name ASC")
            for row in cursor.fetchall():
                template = dict(row)
                if template.get('config_json'):
                    try:
                        config_data = json.loads(template['config_json'])
                        template.update(config_data) # Merge JSON data into the main dict
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse config_json for template {template['name']}", file=sys.stderr)
                # config_json is not needed in the final dict after parsing
                # template.pop('config_json', None) # Keep it if needed for editing raw JSON
                templates.append(template)
            return templates
        except sqlite3.Error as e:
            print(f"Error loading templates: {e}", file=sys.stderr)
            return []
        finally:
            conn.close()
            
    def get_template_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM templates WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                template = dict(row)
                if template.get('config_json'):
                    try:
                        config_data = json.loads(template['config_json'])
                        template.update(config_data)
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse config_json for template {template['name']}", file=sys.stderr)
                return template
            return None
        except sqlite3.Error as e:
            print(f"Error getting template by name '{name}': {e}", file=sys.stderr)
            return None
        finally:
            conn.close()

    def delete_template(self, template_id: int):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error deleting template id {template_id}: {e}", file=sys.stderr)
        finally:
            conn.close()

    def log_generation(self, title: str, author: str, file_path: str, template_id: Optional[int] = None):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO generation_history (title, author, file_path, template_id) 
                VALUES (?, ?, ?, ?)
            """, (title, author, file_path, template_id))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error logging generation: {e}", file=sys.stderr)
        finally:
            conn.close()

    def get_generation_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        history = []
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT gh.id, gh.title, gh.author, gh.file_path, gh.generated_at, t.name as template_name
                FROM generation_history gh
                LEFT JOIN templates t ON gh.template_id = t.id
                ORDER BY gh.generated_at DESC
                LIMIT ?
            """, (limit,))
            for row in cursor.fetchall():
                history.append(dict(row))
            return history
        except sqlite3.Error as e:
            print(f"Error getting generation history: {e}", file=sys.stderr)
            return []
        finally:
            conn.close()

# --- Preferences Dialog ---
class PreferencesDialog(QDialog):
    def __init__(self, parent: QWidget, db_manager: DatabaseManager, translator: Translator):
        super().__init__(parent)
        self.translator = translator
        self.setWindowTitle(self.translator.tr("Préférences"))
        self.setMinimumWidth(450)
        self.db = db_manager
        self.current_settings = {} # To store loaded settings for comparison

        main_layout = QVBoxLayout(self)

        # General Settings
        general_group = QFrame()
        general_group.setFrameShape(QFrame.StyledPanel)
        general_layout = QGridLayout(general_group)
        main_layout.addWidget(general_group)
        
        general_layout.addWidget(QLabel(self.translator.tr("Langue:")), 0, 0)
        self.language_combo = ModernComboBox()
        # Populate with display names from the Translator's LANGUAGES dict
        for lang_code in self.translator.LANGUAGES:
            self.language_combo.addItem(self.translator.LANGUAGES[lang_code])
        general_layout.addWidget(self.language_combo, 0, 1)

        general_layout.addWidget(QLabel(self.translator.tr("Auteur par défaut:")), 1, 0)
        self.author_edit = ModernLineEdit()
        general_layout.addWidget(self.author_edit, 1, 1)

        general_layout.addWidget(QLabel(self.translator.tr("Institution par défaut:")), 2, 0)
        self.institution_edit = ModernLineEdit()
        general_layout.addWidget(self.institution_edit, 2, 1)
        
        general_layout.addWidget(QLabel(self.translator.tr("Police par défaut:")), 3, 0) # Assuming "Police par défaut:" is added to translator
        self.font_combo = QComboBox() # Using standard for now, could be ModernComboBox
        self.font_combo.addItems(QFontDatabase().families()) # Populate with system fonts
        general_layout.addWidget(self.font_combo, 3, 1)

        general_layout.addWidget(QLabel("Taille de police par défaut:"), 4, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 72)
        general_layout.addWidget(self.font_size_spin, 4, 1)

        # Database Path
        db_group = QFrame()
        db_group.setFrameShape(QFrame.StyledPanel)
        db_layout = QHBoxLayout(db_group)
        main_layout.addWidget(db_group)

        db_layout.addWidget(QLabel("Chemin base de données:"))
        self.db_path_edit = ModernLineEdit()
        self.db_path_edit.setReadOnly(True) # Usually not changed by user directly here
        db_layout.addWidget(self.db_path_edit)
        # db_browse_btn = AnimatedButton("Parcourir", style_type="secondary")
        # db_browse_btn.clicked.connect(self.browse_db_path)
        # db_layout.addWidget(db_browse_btn) # Might be complex to implement live DB change

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        button_box.button(QDialogButtonBox.Ok).setText(self.translator.tr("OK"))
        button_box.button(QDialogButtonBox.Cancel).setText(self.translator.tr("Annuler"))
        button_box.button(QDialogButtonBox.Apply).setText(self.translator.tr("Appliquer"))

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_changes)
        main_layout.addWidget(button_box)

        self.load_preferences()

    def load_preferences(self):
        # Load language preference (it's stored as display name, e.g., "Français", "English")
        default_lang_display_name = self.translator.LANGUAGES.get(
            APP_CONFIG.get('default_language', 'fr'), # Default to 'fr' code if APP_CONFIG is not set
            "Français" # Fallback display name
        )
        current_lang_display_name = self.db.load_preference('language', default_lang_display_name)
        self.language_combo.setCurrentText(current_lang_display_name)
        self.current_settings['language'] = current_lang_display_name
        
        self.current_settings['default_author'] = self.db.load_preference('default_author', '')
        self.author_edit.setText(self.current_settings['default_author'])

        self.current_settings['default_institution'] = self.db.load_preference('default_institution', '')
        self.institution_edit.setText(self.current_settings['default_institution'])
        
        self.current_settings['default_font'] = self.db.load_preference('default_font', APP_CONFIG['default_font'])
        self.font_combo.setCurrentText(self.current_settings['default_font'])

        self.current_settings['default_font_size'] = self.db.load_preference('default_font_size', APP_CONFIG['default_font_size'])
        self.font_size_spin.setValue(int(self.current_settings['default_font_size']))

        self.db_path_edit.setText(self.db.db_path)


    def apply_changes(self):
        self.db.save_preference('language', self.language_combo.currentText())
        self.db.save_preference('default_author', self.author_edit.text())
        self.db.save_preference('default_institution', self.institution_edit.text())
        self.db.save_preference('default_font', self.font_combo.currentText())
        self.db.save_preference('default_font_size', self.font_size_spin.value())
        
        # Update current_settings after saving
        self.current_settings['language'] = self.language_combo.currentText()
        self.current_settings['default_author'] = self.author_edit.text()
        self.current_settings['default_institution'] = self.institution_edit.text()
        self.current_settings['default_font'] = self.font_combo.currentText()
        self.current_settings['default_font_size'] = self.font_size_spin.value()
        
        QMessageBox.information(self, "Préférences", "Les préférences ont été appliquées.")
        if self.parent(): # Notify parent (main window) to apply changes
            self.parent().apply_application_preferences()


    def accept(self):
        self.apply_changes()
        super().accept()

    # def browse_db_path(self):
    #     # This is complex because it might involve restarting or re-initializing parts of the app
    #     new_path, _ = QFileDialog.getSaveFileName(self, "Choisir base de données", self.db.db_path, "SQLite DB (*.db)")
    #     if new_path and new_path != self.db.db_path:
    #         # self.db_path_edit.setText(new_path)
    #         # Potentially save this path and prompt for restart
    #         QMessageBox.warning(self, "Chemin Base de Données", "Le changement de base de données nécessite un redémarrage de l'application.")
    #         pass


# --- Main Application Window ---
class CoverPageGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.translator = Translator() # Initialize Translator
        self.db = DatabaseManager() # Initialize DatabaseManager first
        self.current_template_id = None # For tracking loaded template for saving
        self.current_logo_data = None # Store loaded logo data (bytes)
        self.current_pdf_data = None # Store last generated PDF bytes for preview
        self.current_language = self.translator.current_language # Initialize from translator

        self.init_ui()
        self.load_and_apply_initial_preferences() # Load and apply startup prefs
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave_current_form)
        self.autosave_timer.start(APP_CONFIG['autosave_interval'])
        
        self.load_templates_into_list()
        # Load last state or default
        # self.load_state() # Implement if needed

    def init_ui(self):
        self.setWindowTitle(self.translator.tr("Générateur de Page de Garde Moderne"))
        self.setGeometry(100, 100, 1200, 800)
        QFontDatabase.addApplicationFont(":/fonts/some_font.ttf") # Example if fonts are in resources
        self.group_title_labels = {} # To store group title QLabels for retranslation
        self.ui_labels = {} # To store other labels that need retranslation

        # --- Central Widget & Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget) # Main layout: form | preview
        
        # --- Form Panel (Left) ---
        form_scroll_area = QScrollArea()
        form_scroll_area.setWidgetResizable(True)
        form_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        form_panel = QWidget()
        self.form_layout = QVBoxLayout(form_panel) # Will add groups here
        form_scroll_area.setWidget(form_panel)
        
        # --- Preview Panel (Right) ---
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        self.preview_widget = PreviewWidget(self)
        
        preview_controls = QHBoxLayout()
        zoom_in_btn = AnimatedButton("", icon_path=":/icons/zoom-in.png", style_type="secondary")
        zoom_out_btn = AnimatedButton("", icon_path=":/icons/zoom-out.png", style_type="secondary")
        reset_zoom_btn = AnimatedButton("", icon_path=":/icons/zoom-reset.png", style_type="secondary")
        zoom_in_btn.clicked.connect(self.preview_widget.zoom_in)
        zoom_out_btn.clicked.connect(self.preview_widget.zoom_out)
        reset_zoom_btn.clicked.connect(self.preview_widget.reset_zoom)
        preview_controls.addStretch()
        preview_controls.addWidget(zoom_in_btn)
        preview_controls.addWidget(zoom_out_btn)
        preview_controls.addWidget(reset_zoom_btn)
        preview_controls.addStretch()

        preview_layout.addLayout(preview_controls)
        preview_layout.addWidget(self.preview_widget)

        # --- Splitter for Form and Preview ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(form_scroll_area)
        splitter.addWidget(preview_panel)
        splitter.setStretchFactor(0, 1) # Form panel smaller
        splitter.setStretchFactor(1, 2) # Preview panel larger
        main_layout.addWidget(splitter)

        # --- Create Form Sections ---
        self.create_template_management_panel()
        self.create_document_info_panel()
        self.create_layout_style_panel()
        self.create_logo_panel()
        self.create_actions_panel()
        
        self.form_layout.addStretch() # Push everything up

        self.create_menus_and_toolbar()
        self.apply_stylesheet() # Apply global styles

    def create_menus_and_toolbar(self):
        # Menubar
        menubar = self.menuBar()
        
        # File Menu
        self.file_menu = menubar.addMenu(self.translator.tr("&Fichier"))
        self.new_action = QAction(QIcon(":/icons/new.png"), self.translator.tr("&Nouveau"), self)
        self.new_action.setShortcut(QKeySequence.New)
        self.new_action.triggered.connect(self.clear_form)
        self.file_menu.addAction(self.new_action)

        self.open_template_action = QAction(QIcon(":/icons/open.png"), self.translator.tr("&Ouvrir Modèle..."), self)
        self.open_template_action.setShortcut(QKeySequence.Open)
        # self.open_template_action.triggered.connect(self.TODO_load_template_dialog) # TODO
        self.file_menu.addAction(self.open_template_action)
        
        self.save_template_action = QAction(QIcon(":/icons/save.png"), self.translator.tr("&Enregistrer Modèle"), self)
        self.save_template_action.setShortcut(QKeySequence.Save)
        self.save_template_action.triggered.connect(self.save_current_as_template)
        self.file_menu.addAction(self.save_template_action)

        self.save_template_as_action = QAction(QIcon(":/icons/save-as.png"), self.translator.tr("Enregistrer Modèle &Sous..."), self)
        self.save_template_as_action.setShortcut(QKeySequence.SaveAs)
        self.save_template_as_action.triggered.connect(lambda: self.save_current_as_template(save_as=True))
        self.file_menu.addAction(self.save_template_as_action)
        
        self.file_menu.addSeparator()
        
        self.export_pdf_action = QAction(QIcon(":/icons/export-pdf.png"), self.translator.tr("Exporter en &PDF..."), self)
        self.export_pdf_action.triggered.connect(self.generate_pdf_final)
        self.file_menu.addAction(self.export_pdf_action)
        
        self.file_menu.addSeparator()
        self.preferences_action = QAction(QIcon(":/icons/settings.png"), self.translator.tr("&Préférences..."), self)
        self.preferences_action.setShortcut(QKeySequence.Preferences)
        self.preferences_action.triggered.connect(self.show_preferences_dialog)
        self.file_menu.addAction(self.preferences_action)
        
        self.file_menu.addSeparator()
        self.exit_action = QAction(QIcon(":/icons/exit.png"), self.translator.tr("&Quitter"), self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)

        # Edit Menu (placeholder)
        self.edit_menu = menubar.addMenu(self.translator.tr("&Édition"))
        # ... undo, redo, copy, paste ...

        # View Menu (placeholder)
        self.view_menu = menubar.addMenu(self.translator.tr("&Affichage"))
        # ... zoom, fullscreen ...

        # Help Menu
        self.help_menu = menubar.addMenu(self.translator.tr("&Aide"))
        self.about_action = QAction(self.translator.tr("&À propos"), self)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.help_menu.addAction(self.about_action)

        # Toolbar (example)
        self.main_toolbar = self.addToolBar(self.translator.tr("Barre d'outils principale"))
        self.main_toolbar.setIconSize(QSize(24,24))
        self.main_toolbar.addAction(self.new_action)
        self.main_toolbar.addAction(self.save_template_action)
        self.main_toolbar.addAction(self.export_pdf_action)
        self.main_toolbar.addSeparator()
        self.main_toolbar.addAction(self.preferences_action)


    def create_panel_group(self, title: str) -> Tuple[QFrame, QVBoxLayout]:
        group_frame = GlassmorphismFrame(self) # Using custom frame
        group_frame.setObjectName(f"group{title.replace(' ','')}")
        
        outer_layout = QVBoxLayout(group_frame) # Layout for the frame itself
        
        # Store title QLabel for retranslation, using the original French title as key
        title_key = title # Assuming 'title' passed is the French key
        title_label = QLabel(self.translator.tr(title_key))
        title_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title_label.setStyleSheet("color: #333; margin-bottom: 5px; padding-top: 5px; background: transparent;")
        self.group_title_labels[title_key] = title_label
        outer_layout.addWidget(title_label)
        
        content_layout = QVBoxLayout() # Layout for the content of the group
        content_layout.setContentsMargins(10,5,10,10) # Margins for content
        outer_layout.addLayout(content_layout) # Add content layout to frame's layout

        self.form_layout.addWidget(group_frame)
        return group_frame, content_layout


    def create_template_management_panel(self):
        _, layout = self.create_panel_group("Modèles") # Key "Modèles"
        
        self.template_list_widget = QListWidget()
        self.template_list_widget.itemDoubleClicked.connect(self.load_selected_template_from_list)
        layout.addWidget(self.template_list_widget)
        
        btn_layout = QHBoxLayout()
        self.load_template_btn_list = AnimatedButton(self.translator.tr("Charger"), icon_path=":/icons/open.png")
        self.load_template_btn_list.clicked.connect(self.load_selected_template_from_list)
        self.delete_template_btn_list = AnimatedButton(self.translator.tr("Supprimer"), icon_path=":/icons/delete.png", style_type="danger")
        self.delete_template_btn_list.clicked.connect(self.delete_selected_template)
        btn_layout.addWidget(self.load_template_btn_list)
        btn_layout.addWidget(self.delete_template_btn_list)
        layout.addLayout(btn_layout)
        
        self.current_template_name_label_list = QLabel(self.translator.tr("Nom du modèle actuel:"))
        layout.addWidget(self.current_template_name_label_list)
        self.current_template_name_edit = ModernLineEdit(placeholder_text=self.translator.tr("Nouveau Modèle"))
        layout.addWidget(self.current_template_name_edit)


    def create_document_info_panel(self):
        _, layout = self.create_panel_group("Informations du Document") # Key "Informations du Document"
        
        grid = QGridLayout()
        grid.setSpacing(10)
        
        self.ui_labels["Titre:"] = QLabel(self.translator.tr("Titre:"))
        grid.addWidget(self.ui_labels["Titre:"], 0, 0)
        self.title_edit = ModernLineEdit(placeholder_text=self.translator.tr("Titre principal du document"))
        self.title_edit.textChanged.connect(self.on_form_field_changed)
        grid.addWidget(self.title_edit, 0, 1)

        self.ui_labels["Sous-titre:"] = QLabel(self.translator.tr("Sous-titre:"))
        grid.addWidget(self.ui_labels["Sous-titre:"], 1, 0)
        self.subtitle_edit = ModernLineEdit(placeholder_text=self.translator.tr("Sous-titre (optionnel)"))
        self.subtitle_edit.textChanged.connect(self.on_form_field_changed)
        grid.addWidget(self.subtitle_edit, 1, 1)

        self.ui_labels["Auteur:"] = QLabel(self.translator.tr("Auteur:"))
        grid.addWidget(self.ui_labels["Auteur:"], 2, 0)
        self.author_edit = ModernLineEdit(placeholder_text=self.translator.tr("Nom de l'auteur"))
        self.author_edit.textChanged.connect(self.on_form_field_changed)
        grid.addWidget(self.author_edit, 2, 1)
        
        self.ui_labels["Institution:"] = QLabel(self.translator.tr("Institution:"))
        grid.addWidget(self.ui_labels["Institution:"], 3, 0)
        self.institution_edit = ModernLineEdit(placeholder_text=self.translator.tr("Université, Organisation, etc."))
        self.institution_edit.textChanged.connect(self.on_form_field_changed)
        grid.addWidget(self.institution_edit, 3, 1)

        self.ui_labels["Département/Faculté:"] = QLabel(self.translator.tr("Département/Faculté:"))
        grid.addWidget(self.ui_labels["Département/Faculté:"], 4, 0)
        self.department_edit = ModernLineEdit(placeholder_text=self.translator.tr("Département ou faculté (optionnel)"))
        self.department_edit.textChanged.connect(self.on_form_field_changed)
        grid.addWidget(self.department_edit, 4, 1)

        self.ui_labels["Type de document:"] = QLabel(self.translator.tr("Type de document:"))
        grid.addWidget(self.ui_labels["Type de document:"], 5, 0)
        self.doc_type_edit = ModernLineEdit(placeholder_text=self.translator.tr("Rapport de stage, Thèse, Mémoire..."))
        self.doc_type_edit.textChanged.connect(self.on_form_field_changed)
        grid.addWidget(self.doc_type_edit, 5, 1)
        
        self.ui_labels["Date (YYYY-MM-DD):"] = QLabel(self.translator.tr("Date (YYYY-MM-DD):"))
        grid.addWidget(self.ui_labels["Date (YYYY-MM-DD):"], 6, 0)
        self.date_edit = ModernLineEdit(placeholder_text=datetime.date.today().strftime("%Y-%m-%d"))
        self.date_edit.setValidator(QRegExpValidator(QRegExp(r"\d{4}-\d{2}-\d{2}")))
        self.date_edit.textChanged.connect(self.on_form_field_changed)
        grid.addWidget(self.date_edit, 6, 1)
        
        self.ui_labels["Version:"] = QLabel(self.translator.tr("Version:"))
        grid.addWidget(self.ui_labels["Version:"], 7, 0)
        self.version_edit = ModernLineEdit(placeholder_text=self.translator.tr("1.0, Version finale..."))
        self.version_edit.textChanged.connect(self.on_form_field_changed)
        grid.addWidget(self.version_edit, 7, 1)

        layout.addLayout(grid)


    def create_layout_style_panel(self):
        _, layout = self.create_panel_group("Mise en Page et Style") # Key "Mise en Page et Style"
        grid = QGridLayout()
        
        self.ui_labels["Style de modèle:"] = QLabel(self.translator.tr("Style de modèle:"))
        grid.addWidget(self.ui_labels["Style de modèle:"], 0, 0)
        self.template_style_combo = ModernComboBox()
        self.template_style_combo.addItems([self.translator.tr("Moderne"), self.translator.tr("Classique"), self.translator.tr("Minimaliste"), self.translator.tr("Personnalisé")])
        self.template_style_combo.currentTextChanged.connect(self.on_form_field_changed)
        grid.addWidget(self.template_style_combo, 0, 1)

        self.ui_labels["Police du Titre:"] = QLabel(self.translator.tr("Police du Titre:"))
        grid.addWidget(self.ui_labels["Police du Titre:"], 1, 0)
        self.title_font_combo = ModernComboBox()
        self.title_font_combo.addItems(QFontDatabase().families())
        self.title_font_combo.currentTextChanged.connect(self.on_form_field_changed)
        grid.addWidget(self.title_font_combo, 1, 1)
        
        self.ui_labels["Couleur du Texte Principal:"] = QLabel(self.translator.tr("Couleur du Texte Principal:"))
        grid.addWidget(self.ui_labels["Couleur du Texte Principal:"], 2, 0)
        self.text_color_button = QPushButton(self.translator.tr("Choisir Couleur"))
        self.text_color_button.clicked.connect(lambda: self.choose_color('main_text_color', self.text_color_preview))
        self.text_color_preview = QFrame()
        self.text_color_preview.setFrameShape(QFrame.Box)
        self.text_color_preview.setFixedSize(20,20)
        color_layout = QHBoxLayout()
        color_layout.addWidget(self.text_color_button)
        color_layout.addWidget(self.text_color_preview)
        color_layout.addStretch()
        grid.addLayout(color_layout, 2, 1)

        self.ui_labels["Taille Police Titre:"] = QLabel(self.translator.tr("Taille Police Titre:"))
        grid.addWidget(self.ui_labels["Taille Police Titre:"], 3, 0)
        self.title_font_size_spin = QSpinBox()
        self.title_font_size_spin.setRange(10, 72)
        self.title_font_size_spin.setValue(24) # Default
        self.title_font_size_spin.valueChanged.connect(self.on_form_field_changed)
        grid.addWidget(self.title_font_size_spin, 3, 1)

        self.show_horizontal_line_checkbox = QCheckBox(self.translator.tr("Afficher la ligne horizontale"))
        self.show_horizontal_line_checkbox.setChecked(True)
        self.show_horizontal_line_checkbox.stateChanged.connect(self.on_form_field_changed)
        grid.addWidget(self.show_horizontal_line_checkbox, 4, 0, 1, 2)
        
        layout.addLayout(grid)

    def create_logo_panel(self):
        _, layout = self.create_panel_group("Logo") # Key "Logo"
        
        self.logo_path_edit = ModernLineEdit(placeholder_text=self.translator.tr("Chemin vers l'image du logo"))
        self.logo_path_edit.setReadOnly(True)
        layout.addWidget(self.logo_path_edit)
        
        btn_layout = QHBoxLayout()
        self.browse_logo_btn = AnimatedButton(self.translator.tr("Charger Logo"), icon_path=":/icons/image.png")
        self.browse_logo_btn.clicked.connect(self.browse_logo)
        self.clear_logo_btn = AnimatedButton(self.translator.tr("Retirer Logo"), style_type="secondary")
        self.clear_logo_btn.clicked.connect(self.clear_logo)
        btn_layout.addWidget(self.browse_logo_btn)
        btn_layout.addWidget(self.clear_logo_btn)
        layout.addLayout(btn_layout)

        self.logo_preview_label = QLabel(self.translator.tr("Aucun logo chargé."))
        self.logo_preview_label.setAlignment(Qt.AlignCenter)
        self.logo_preview_label.setMinimumHeight(100)
        self.logo_preview_label.setStyleSheet("border: 1px dashed #ccc; border-radius: 6px; background-color: #f8f9fa;")
        layout.addWidget(self.logo_preview_label)


    def create_actions_panel(self):
        self.actions_frame = GlassmorphismFrame(self)
        actions_layout = QHBoxLayout(self.actions_frame)
        actions_layout.setSpacing(15)
        actions_layout.setContentsMargins(20,10,20,10)

        self.preview_btn = AnimatedButton(self.translator.tr("Aperçu Rapide"), icon_path=":/icons/preview.png", style_type="secondary")
        self.preview_btn.clicked.connect(self.update_preview)
        actions_layout.addWidget(self.preview_btn)

        self.generate_btn = AnimatedButton(self.translator.tr("Générer PDF"), icon_path=":/icons/export-pdf.png", style_type="primary")
        self.generate_btn.clicked.connect(self.generate_pdf_final)
        actions_layout.addWidget(self.generate_btn)
        
        # Adding Preferences button here as requested by a subtask, if it's not in menu/toolbar
        # self.preferences_btn = AnimatedButton("⚙️ Préférences", style_type="secondary")
        # self.preferences_btn.setToolTip("Ouvrir les préférences de l'application")
        # self.preferences_btn.clicked.connect(self.show_preferences_dialog)
        # actions_layout.addWidget(self.preferences_btn) # Or place in toolbar/menu

        self.form_layout.addWidget(self.actions_frame)


    def apply_stylesheet(self):
        # Example of applying a more global stylesheet for the app
        # For more complex styling, consider loading from a .qss file
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa; /* Light gray background */
            }
            QLabel {
                font-size: 10pt;
                color: #333;
                background: transparent; /* Ensure labels in groups are transparent */
            }
            QFrame#groupInfoDoc, QFrame#groupMisePage, QFrame#groupLogo { /* Example for named groups */
                /* Styles for specific groups if needed */
            }
            QScrollArea {
                border: none;
            }
        """)
        # For icons, ensure they are in a Qt Resource file (e.g., icons.qrc)
        # and compiled with pyrcc5 icons.qrc -o icons_rc.py, then import icons_rc.


    def on_form_field_changed(self, *args):
        # This can be connected to textChanged, currentTextChanged, stateChanged, valueChanged signals
        # For now, just trigger an autosave or a preview update implicitly
        # print("Form field changed, potential autosave/preview update.")
        self.autosave_current_form() # Or a more delayed version
        self.update_preview(is_live=True) # Update preview more frequently on changes

    # --- Preferences Logic ---
    def load_and_apply_initial_preferences(self):
        # Load author and institution
        default_author = self.db.load_preference('default_author', '')
        if default_author and hasattr(self, 'author_edit'):
            self.author_edit.setText(default_author)
        
        default_institution = self.db.load_preference('default_institution', '')
        if default_institution and hasattr(self, 'institution_edit'):
            self.institution_edit.setText(default_institution)

        # Load language (application of language will be more complex, involving i18n)
        # The preference is stored as the display name (e.g., "Français", "English")
        default_lang_display_name = self.translator.LANGUAGES.get(
            APP_CONFIG.get('default_language', 'fr'), # Default to 'fr' code if not set
            "Français" # Fallback display name if code not in LANGUAGES
        )
        preferred_language_display_name = self.db.load_preference('language', default_lang_display_name)

        print(f"Preferred language loaded from DB: {preferred_language_display_name}")
        self.translator.set_language(preferred_language_display_name) # Pass display name
        self.current_language = self.translator.current_language # Update based on what was actually set

        # Load default font and size (apply to relevant widgets if needed, or use as default for new elements)
        APP_CONFIG['default_font'] = self.db.load_preference('default_font', APP_CONFIG['default_font'])
        APP_CONFIG['default_font_size'] = int(self.db.load_preference('default_font_size', APP_CONFIG['default_font_size']))
        
        # Apply default author and institution if the fields exist and preferences are set
        if hasattr(self, 'author_edit') and default_author: # Check if default_author has a value
            self.author_edit.setText(default_author)
        if hasattr(self, 'institution_edit') and default_institution: # Check if default_institution has a value
            self.institution_edit.setText(default_institution)

        # Other preferences can be loaded and applied here.
        # self.apply_application_preferences() # This was called too early. It's for when dialog closes.
        self.update_preview(is_live=False) # Update preview once after initial prefs are set.


    def show_preferences_dialog(self):
        dialog = PreferencesDialog(self, self.db, self.translator) # Pass translator
        dialog.exec_()

    def retranslate_ui(self):
        self.setWindowTitle(self.translator.tr("Générateur de Page de Garde Moderne"))

        # Menus & Actions
        self.file_menu.setTitle(self.translator.tr("&Fichier"))
        self.new_action.setText(self.translator.tr("&Nouveau"))
        self.open_template_action.setText(self.translator.tr("&Ouvrir Modèle..."))
        self.save_template_action.setText(self.translator.tr("&Enregistrer Modèle"))
        self.save_template_as_action.setText(self.translator.tr("Enregistrer Modèle &Sous..."))
        self.export_pdf_action.setText(self.translator.tr("Exporter en &PDF..."))
        self.preferences_action.setText(self.translator.tr("&Préférences..."))
        self.exit_action.setText(self.translator.tr("&Quitter"))
        
        self.edit_menu.setTitle(self.translator.tr("&Édition"))
        self.view_menu.setTitle(self.translator.tr("&Affichage"))
        self.help_menu.setTitle(self.translator.tr("&Aide"))
        self.about_action.setText(self.translator.tr("&À propos"))
        
        self.main_toolbar.setWindowTitle(self.translator.tr("Barre d'outils principale"))

        # Panel Group Titles
        for key, label_widget in self.group_title_labels.items():
            label_widget.setText(self.translator.tr(key))

        # Document Info Panel Labels & Placeholders
        for key, label_widget in self.ui_labels.items(): # Assuming self.ui_labels stores these
            label_widget.setText(self.translator.tr(key))
        
        self.title_edit.setPlaceholderText(self.translator.tr("Titre principal du document"))
        self.subtitle_edit.setPlaceholderText(self.translator.tr("Sous-titre (optionnel)"))
        self.author_edit.setPlaceholderText(self.translator.tr("Nom de l'auteur"))
        self.institution_edit.setPlaceholderText(self.translator.tr("Université, Organisation, etc."))
        self.department_edit.setPlaceholderText(self.translator.tr("Département ou faculté (optionnel)"))
        self.doc_type_edit.setPlaceholderText(self.translator.tr("Rapport de stage, Thèse, Mémoire..."))
        self.version_edit.setPlaceholderText(self.translator.tr("1.0, Version finale..."))

        # Layout Style Panel Labels & Controls
        # self.ui_labels["Style de modèle:"].setText(self.translator.tr("Style de modèle:"))
        self.template_style_combo.setItemText(0, self.translator.tr("Moderne"))
        self.template_style_combo.setItemText(1, self.translator.tr("Classique"))
        self.template_style_combo.setItemText(2, self.translator.tr("Minimaliste"))
        self.template_style_combo.setItemText(3, self.translator.tr("Personnalisé"))

        self.text_color_button.setText(self.translator.tr("Choisir Couleur"))
        self.show_horizontal_line_checkbox.setText(self.translator.tr("Afficher la ligne horizontale"))

        # Logo Panel
        self.logo_path_edit.setPlaceholderText(self.translator.tr("Chemin vers l'image du logo"))
        self.browse_logo_btn.setText(self.translator.tr("Charger Logo"))
        self.clear_logo_btn.setText(self.translator.tr("Retirer Logo"))
        if self.logo_preview_label.pixmap() is None or self.logo_preview_label.pixmap().isNull():
             self.logo_preview_label.setText(self.translator.tr("Aucun logo chargé."))

        # Actions Panel
        self.preview_btn.setText(self.translator.tr("Aperçu Rapide"))
        self.generate_btn.setText(self.translator.tr("Générer PDF"))
        
        # Template Management Panel
        self.load_template_btn_list.setText(self.translator.tr("Charger"))
        self.delete_template_btn_list.setText(self.translator.tr("Supprimer"))
        self.current_template_name_label_list.setText(self.translator.tr("Nom du modèle actuel:"))
        self.current_template_name_edit.setPlaceholderText(self.translator.tr("Nouveau Modèle"))

        print(f"UI Retranslation executed for language: {self.current_language}")


    def apply_application_preferences(self):
        """Called by PreferencesDialog to apply changes to the main app if needed."""
        print("Applying application-wide preferences...")
        # Reload language preference
        # new_lang is the display name, e.g., "English"
        new_lang_display_name = self.db.load_preference('language', self.translator.LANGUAGES.get(APP_CONFIG['default_language'], "Français"))
        
        self.translator.set_language(new_lang_display_name)
        self.current_language = self.translator.current_language # This should be the display name
        
        self.retranslate_ui() # Always call to ensure UI is in correct state
        
        # Re-populate fields with (potentially new) defaults from preferences.
        default_author_after_pref = self.db.load_preference('default_author', '')
        if hasattr(self, 'author_edit'): # Check if the attribute exists before setting
             self.author_edit.setText(default_author_after_pref)
        
        default_institution_after_pref = self.db.load_preference('default_institution', '')
        if hasattr(self, 'institution_edit'): # Check if the attribute exists
             self.institution_edit.setText(default_institution_after_pref)

        # Update global config if needed for PDF generation defaults
        APP_CONFIG['default_font'] = self.db.load_preference('default_font', APP_CONFIG['default_font'])
        APP_CONFIG['default_font_size'] = int(self.db.load_preference('default_font_size', APP_CONFIG['default_font_size']))
        
        # self.current_language = new_lang # This is already set above via self.translator

        self.update_preview(is_live=False) # Refresh preview as some defaults might affect it

    # --- Template Management ---
    def get_current_form_data(self) -> Dict[str, Any]:
        data = {
            "name": self.current_template_name_edit.text() or self.translator.tr("Nouveau Modèle"), # Use placeholder if empty
            "title": self.title_edit.text(),
            "subtitle": self.subtitle_edit.text(),
            "author": self.author_edit.text(),
            "institution": self.institution_edit.text(),
            "department": self.department_edit.text(),
            "doc_type": self.doc_type_edit.text(),
            "date": self.date_edit.text() or datetime.date.today().strftime("%Y-%m-%d"),
            "version": self.version_edit.text(),
            "template_style": self.template_style_combo.currentText(),
            "title_font_name": self.title_font_combo.currentText(),
            # "main_text_color": self.main_text_color_value,
            "title_font_size": self.title_font_size_spin.value(),
            "show_horizontal_line": self.show_horizontal_line_checkbox.isChecked(),
            "logo_path_on_disk": self.logo_path_edit.text(), # Store path for reference, not saved to DB directly
            "logo_name": os.path.basename(self.logo_path_edit.text()) if self.logo_path_edit.text() else None,
            "logo_data": self.current_logo_data, # Actual image data
            # Store other fields from layout_style_panel, etc.
        }
        # Add any other specific config items
        data['config_json_extras'] = { 
            # 'custom_ margins': ...
        }
        return data

    def populate_form_from_data(self, data: Dict[str, Any]):
        self.current_template_name_edit.setText(data.get("name", self.translator.tr("Nouveau Modèle"))) # Changed from "Modèle Copié"
        self.title_edit.setText(data.get("title", ""))
        self.subtitle_edit.setText(data.get("subtitle", ""))
        self.author_edit.setText(data.get("author", ""))
        self.institution_edit.setText(data.get("institution", ""))
        self.department_edit.setText(data.get("department", ""))
        self.doc_type_edit.setText(data.get("doc_type", ""))
        self.date_edit.setText(data.get("date", datetime.date.today().strftime("%Y-%m-%d")))
        self.version_edit.setText(data.get("version", ""))
        
        self.template_style_combo.setCurrentText(data.get("template_style", "Moderne"))
        self.title_font_combo.setCurrentText(data.get("title_font_name", APP_CONFIG['default_font']))
        # self.main_text_color_value = data.get("main_text_color", APP_CONFIG['default_text_color'])
        # self.text_color_preview.setStyleSheet(f"background-color: {self.main_text_color_value};")
        self.title_font_size_spin.setValue(data.get("title_font_size", 24))
        self.show_horizontal_line_checkbox.setChecked(data.get("show_horizontal_line", True))

        self.current_logo_data = data.get("logo_data")
        logo_name_for_display = data.get("logo_name", "")
        if self.current_logo_data and logo_name_for_display:
            self.logo_path_edit.setText(f"Logo chargé depuis la base de données: {logo_name_for_display}")
            pixmap = QPixmap()
            pixmap.loadFromData(self.current_logo_data)
            self.logo_preview_label.setPixmap(pixmap.scaled(self.logo_preview_label.size() * 0.8, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.clear_logo(update_preview=False) # Don't trigger preview yet
            self.logo_path_edit.setText(data.get("logo_path_on_disk", "")) # If loaded from disk state
            if self.logo_path_edit.text(): # try to load from path if no db data
                 self.load_logo_from_path(self.logo_path_edit.text(), update_preview=False)


        self.current_template_id = data.get("id") # Store db id of loaded template
        self.update_preview()


    def save_current_as_template(self, save_as=False):
        template_data = self.get_current_form_data()
        template_name = template_data.get("name")

        if not template_name:
            QMessageBox.warning(self, self.translator.tr("Nom Requis"), self.translator.tr("Veuillez donner un nom à ce modèle."))
            self.current_template_name_edit.setFocus()
            return

        existing_template = self.db.get_template_by_name(template_name)
        if existing_template and (save_as or existing_template.get('id') != self.current_template_id):
             reply = QMessageBox.question(self, self.translator.tr("Modèle Existant"), 
                                         self.translator.tr("Un modèle nommé '{}' existe déjà. Voulez-vous le remplacer?", template_name),
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
             if reply == QMessageBox.No:
                 return
             else: # Yes, delete old one before saving new
                 self.db.delete_template(existing_template['id'])
        elif existing_template and existing_template.get('id') == self.current_template_id and not save_as:
            # This is an update to the currently loaded template
             self.db.delete_template(self.current_template_id)


        new_id = self.db.save_template(template_data)
        if new_id:
            self.current_template_id = new_id
            QMessageBox.information(self, self.translator.tr("Modèle Enregistré"), self.translator.tr("Modèle '{}' enregistré avec succès.", template_name))
            self.load_templates_into_list()
            items = self.template_list_widget.findItems(template_name, Qt.MatchExactly)
            if items:
                self.template_list_widget.setCurrentItem(items[0])
        else:
            QMessageBox.critical(self, self.translator.tr("Erreur d'Enregistrement"), self.translator.tr("Impossible d'enregistrer le modèle."))


    def load_templates_into_list(self):
        self.template_list_widget.clear()
        templates = self.db.load_templates()
        for template in templates:
            item = QListWidgetItem(template['name'])
            item.setData(Qt.UserRole, template['id']) # Store id with the item
            self.template_list_widget.addItem(item)

    def load_selected_template_from_list(self):
        selected_item = self.template_list_widget.currentItem()
        if not selected_item:
            QMessageBox.information(self, self.translator.tr("Charger Modèle"), self.translator.tr("Veuillez sélectionner un modèle dans la liste."))
            return
        
        template_id = selected_item.data(Qt.UserRole)
        templates = self.db.load_templates() 
        template_data = next((t for t in templates if t['id'] == template_id), None)

        if template_data:
            self.populate_form_from_data(template_data)
        else:
            QMessageBox.warning(self, self.translator.tr("Charger Modèle"), self.translator.tr("Impossible de trouver les données du modèle sélectionné."))


    def delete_selected_template(self):
        selected_item = self.template_list_widget.currentItem()
        if not selected_item:
            QMessageBox.information(self, self.translator.tr("Supprimer Modèle"), self.translator.tr("Veuillez sélectionner un modèle à supprimer."))
            return

        template_id = selected_item.data(Qt.UserRole)
        template_name = selected_item.text()
        
        reply = QMessageBox.warning(self, self.translator.tr("Confirmation de Suppression"),
                                   self.translator.tr("Êtes-vous sûr de vouloir supprimer le modèle '{}'?", template_name),
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.delete_template(template_id)
            self.load_templates_into_list()
            if self.current_template_id == template_id:
                self.clear_form()
            QMessageBox.information(self, self.translator.tr("Modèle Supprimé"), self.translator.tr("Modèle '{}' supprimé.", template_name))


    def clear_form(self):
        self.current_template_name_edit.setText(self.translator.tr("Nouveau Modèle"))
        self.title_edit.clear()
        self.subtitle_edit.clear()
        # self.author_edit.clear() # Keep default author from prefs
        # self.institution_edit.clear() # Keep default institution
        self.department_edit.clear()
        self.doc_type_edit.clear()
        self.date_edit.setText(datetime.date.today().strftime("%Y-%m-%d"))
        self.version_edit.clear()
        
        self.template_style_combo.setCurrentIndex(0) # Back to "Moderne" or first item
        self.title_font_combo.setCurrentText(APP_CONFIG['default_font'])
        # self.main_text_color_value = APP_CONFIG['default_text_color']
        # self.text_color_preview.setStyleSheet(f"background-color: {self.main_text_color_value};")
        self.title_font_size_spin.setValue(24) # Default
        self.show_horizontal_line_checkbox.setChecked(True)
        
        self.clear_logo(update_preview=False) # Don't trigger preview update immediately from here
        self.current_template_id = None
        self.template_list_widget.clearSelection()

        # Re-apply default author/institution from preferences
        self.author_edit.setText(self.db.load_preference('default_author', ''))
        self.institution_edit.setText(self.db.load_preference('default_institution', ''))

        self.update_preview()
        QMessageBox.information(self, self.translator.tr("&Nouveau"), self.translator.tr("Formulaire réinitialisé."))


    # --- Logo Handling ---
    def browse_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.translator.tr("Choisir un Logo"), "", 
                                                   "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            self.load_logo_from_path(file_path)

    def load_logo_from_path(self, file_path, update_preview=True):
        try:
            with open(file_path, 'rb') as f:
                self.current_logo_data = f.read()
            
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                self.current_logo_data = None
                raise ValueError(self.translator.tr("Format d'image non reconnu ou fichier corrompu."))

            self.logo_path_edit.setText(file_path)
            self.logo_preview_label.setPixmap(pixmap.scaled(self.logo_preview_label.size() * 0.9, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            if update_preview: self.update_preview()

        except Exception as e:
            QMessageBox.warning(self, self.translator.tr("Erreur Logo"), self.translator.tr("Impossible de charger le logo: {}", str(e)))
            self.clear_logo(update_preview=update_preview)


    def clear_logo(self, update_preview=True):
        self.logo_path_edit.clear()
        self.logo_preview_label.setText(self.translator.tr("Aucun logo chargé."))
        self.logo_preview_label.setPixmap(QPixmap())
        self.current_logo_data = None
        if update_preview: self.update_preview()

    # --- Color Picker ---
    def choose_color(self, config_key_name: str, preview_widget: QFrame):
        # current_color = getattr(self, config_key_name, APP_CONFIG['default_text_color'])
        # color = QColorDialog.getColor(QColor(current_color), self, "Choisir une couleur")
        # if color.isValid():
        #     setattr(self, config_key_name, color.name())
        #     preview_widget.setStyleSheet(f"background-color: {color.name()};")
        #     self.on_form_field_changed() # Trigger update
        pass # Simplified for now

    # --- PDF Generation & Preview ---
    def _collect_config_for_pdf(self) -> Dict[str, Any]:
        # This should gather all relevant settings from the form
        # and from APP_CONFIG or loaded template for PDF generation.
        form_data = self.get_current_form_data()
        
        pdf_config = {
            "page_width": APP_CONFIG.get("page_width", 210), # A4 width in mm
            "page_height": APP_CONFIG.get("page_height", 297), # A4 height in mm
            "margin_left": 20, "margin_right": 20, "margin_top": 25, "margin_bottom": 25, # Defaults in mm
            
            "font_name": form_data.get("title_font_name", APP_CONFIG['default_font']), # Example
            "font_size_title": form_data.get("title_font_size", 24),
            "font_size_subtitle": 18, # Example, make configurable
            "font_size_author": 12,   # Example
            "text_color": (0,0,0), # Black, make configurable
            
            "title": form_data.get("title"),
            "subtitle": form_data.get("subtitle"),
            "author": form_data.get("author"),
            "institution": form_data.get("institution"),
            "department": form_data.get("department"),
            "doc_type": form_data.get("doc_type"),
            "date": form_data.get("date"),
            "version": form_data.get("version"),

            "logo_data": self.current_logo_data, # Use the actual bytes
            "logo_width": 50, "logo_height": 50, # mm, make configurable
            "logo_x_position": "center", # make configurable
            "logo_y_position": "top",    # make configurable

            "horizontal_line": form_data.get("show_horizontal_line", True),
            "line_color": (0,0,0),
            "line_thickness": 0.5,
            "line_y_position": 150, # mm from top, make configurable

            "footer_text": f"Document généré par CoverPageGenerator © {datetime.date.today().year}", # Example
            "font_size_footer": 8,
            # ... add all other relevant fields from form_data and APP_CONFIG ...
        }
        return pdf_config

    def generate_pdf_to_buffer(self) -> Optional[bytes]:
        pdf_config = self._collect_config_for_pdf()
        buffer = QBuffer() # Use QBuffer for easier integration with QByteArray
        buffer.open(QIODevice.ReadWrite)

        # --- Register Fonts ---
        effective_arial_font = 'Helvetica'
        effective_arial_bold_font = 'Helvetica-Bold'
        effective_showcard_font = 'Helvetica' # Default fallback for Showcard Gothic

        # Arial
        try:
            arial_path = os.path.join(APP_ROOT_DIR, 'fonts', 'arial.ttf')
            if os.path.exists(arial_path):
                pdfmetrics.registerFont(TTFont('Arial', arial_path))
                effective_arial_font = 'Arial'
                print(f"Successfully registered Arial from {arial_path}")
            else:
                print(f"Warning: Custom Arial font not found at {arial_path}. Using Helvetica.")
        except Exception as e:
            print(f"Error registering custom Arial font from {arial_path}: {e}. Using Helvetica.")

        # Arial Bold
        arial_bold_path = os.path.join(APP_ROOT_DIR, 'fonts', 'arialbd.ttf')
        if os.path.exists(arial_bold_path):
            try:
                pdfmetrics.registerFont(TTFont('Arial-Bold', arial_bold_path))
                effective_arial_bold_font = 'Arial-Bold'
                print(f"Successfully registered Arial-Bold from {arial_bold_path}")
            except Exception as e:
                print(f"Error registering custom Arial Bold font from {arial_bold_path}: {e}. Using Helvetica-Bold.")
        else:
            print(f"Warning: Custom Arial Bold font file 'arialbd.ttf' not found in 'fonts/' directory. Using Helvetica-Bold.")

        # Showcard Gothic
        showcard_font_name_to_register = 'Showcard Gothic'
        showcard_paths_to_try = [
            os.path.join(APP_ROOT_DIR, 'fonts', 'ShowcardGothic.ttf'),
            os.path.join(APP_ROOT_DIR, 'fonts', 'showg.ttf')
        ]
        showcard_registered = False
        for showcard_path in showcard_paths_to_try:
            if os.path.exists(showcard_path):
                try:
                    pdfmetrics.registerFont(TTFont(showcard_font_name_to_register, showcard_path))
                    effective_showcard_font = showcard_font_name_to_register
                    showcard_registered = True
                    print(f"Successfully registered {showcard_font_name_to_register} from {showcard_path}")
                    break
                except Exception as e:
                    print(f"Error registering {showcard_font_name_to_register} font from {showcard_path}: {e}")

        if not showcard_registered:
            print(f"Warning: Failed to load custom '{showcard_font_name_to_register}' font from expected paths. "
                  f"Please ensure 'fonts/ShowcardGothic.ttf' or 'fonts/showg.ttf' is a valid TTF file. "
                  f"Falling back to {effective_showcard_font}. Appearance will differ.")
        # --- End Font Registration ---
        
        # Use the CLI PDF generator class, but instantiated, not as a class method
        # This assumes PDFCoverPageGenerator_CLI is the class name for the CLI version.
        # For now, let's assume the CLI class is named `PDFGeneratorLogic` or similar
        # to avoid confusion with the GUI class `CoverPageGenerator`.
        # If the CLI class is indeed `PDFCoverPageGenerator` from previous steps,
        # we might need to rename it or ensure it can be used this way.
        
        # For this step, I will assume the CLI class from previous steps is named `PDFGenerator_Logic`.
        # If `PDFCoverPageGenerator` is the CLI script, it needs to be callable as an instance.
        
        # Simplified call to a hypothetical PDF generation logic class:
        try:
            # pdf_logic = PDFGenerator_Logic( # Instantiate the logic class
            #     title=pdf_config.get("title"),
            #     subtitle=pdf_config.get("subtitle"),
            #     # ... pass all other relevant items from pdf_config ...
            #     custom_config=pdf_config # Pass the whole dict
            # )
            # # The logic class's generate method should accept a file-like object
            # pdf_logic.generate(output_filename_or_buffer=buffer) # This needs adjustment in CLI class
            
            # Direct ReportLab usage for simplicity here, mirroring the CLI class's logic
            # This part should be identical to the PDF generation logic from the CLI script
            # For demonstration, a very simplified version:
            c = reportlab_canvas.Canvas(buffer, pagesize=A4)

            # Determine font to use based on pdf_config and registration success
            requested_font_name = pdf_config.get("font_name", "Arial")
            font_to_use = effective_arial_font # Default to Arial (or its fallback)

            if requested_font_name == 'Arial-Bold':
                font_to_use = effective_arial_bold_font
            elif requested_font_name == 'Showcard Gothic':
                font_to_use = effective_showcard_font
            elif requested_font_name != 'Arial': # If a different font than Arial was requested and not Showcard or Arial-Bold
                # This case implies a font name was provided that we don't have specific handling for here.
                # We'll try to use it directly, hoping it's a standard one or already registered by some other means.
                # If not, ReportLab will attempt its own fallback (often to Helvetica).
                font_to_use = requested_font_name
                # A warning could be added here if font_to_use is not in our list of effectives
                # print(f"Warning: Font '{font_to_use}' requested directly. Ensure it is a standard or pre-registered font.")


            c.setFont(font_to_use, pdf_config.get("font_size_title", 24))
            
            title_y = A4[1] - pdf_config.get("margin_top",25)*mm - 30*mm
            if pdf_config.get("title"):
                 c.drawCentredString(A4[0]/2, title_y, pdf_config.get("title"))
            
            # For subtitle, typically use the same font or a variation
            # Assuming subtitle uses the same base font as title for this example
            c.setFont(font_to_use, pdf_config.get("font_size_subtitle", 18))
            if pdf_config.get("subtitle"):
                # c.setFont(font_to_use, pdf_config.get("font_size_subtitle", 18)) # setFont was here, moved up
                title_y -= 15*mm
                c.drawCentredString(A4[0]/2, title_y, pdf_config.get("subtitle"))

            # For author, typically use the same font or a variation
            # Assuming author uses the same base font as title for this example
            c.setFont(font_to_use, pdf_config.get("font_size_author", 12))
            if pdf_config.get("author"):
                # c.setFont(font_to_use, pdf_config.get("font_size_author", 12)) # setFont was here, moved up
                author_y = A4[1]/2 # Example position
                c.drawCentredString(A4[0]/2, author_y, pdf_config.get("author"))

            if pdf_config.get("logo_data"):
                try:
                    logo_image = ImageReader(QBuffer(QByteArray(pdf_config.get("logo_data")))) # Wrap bytes in QBuffer for ImageReader
                    # Example positioning, make this configurable
                    c.drawImage(logo_image, A4[0]/2 - 25*mm, A4[1] - 60*mm, width=50*mm, height=50*mm, preserveAspectRatio=True)
                except Exception as logo_e:
                    print(f"Error drawing logo in PDF: {logo_e}", file=sys.stderr)

            c.save()
            buffer.seek(0)
            pdf_bytes = buffer.data().data() # Get bytes from QByteArray
            buffer.close()
            return pdf_bytes

        except Exception as e:
            print(f"Error generating PDF to buffer: {e}", file=sys.stderr)
            QMessageBox.critical(self, "Erreur PDF", f"Impossible de générer le PDF en mémoire: {e}")
            return None


    def update_preview(self, is_live=False):
        if is_live and not hasattr(self, '_live_preview_timer'):
            self._live_preview_timer = QTimer(self)
            self._live_preview_timer.setSingleShot(True)
            self._live_preview_timer.timeout.connect(self._perform_preview_update)
            self._live_preview_timer.start(500) # 500ms delay for live preview
        elif not is_live:
             self._perform_preview_update()


    def _perform_preview_update(self):
        print("Updating preview...")
        pdf_bytes = self.generate_pdf_to_buffer()
        if pdf_bytes:
            self.current_pdf_data = pdf_bytes
            # To display in QGraphicsView, we need to render PDF page to QImage.
            # This is where a proper PDF rendering library is essential.
            # For now, using the placeholder in PreviewWidget.
            temp_pdf_path = os.path.join(os.getcwd(), "_temp_preview.pdf") 
            try:
                with open(temp_pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                self.preview_widget.load_pdf_preview(temp_pdf_path) # This method will handle its own error display
            except Exception as e: # Catch error writing temp file
                self.preview_widget.display_error_message(self.translator.tr("Erreur d'aperçu: {}", str(e)))
            finally:
                if os.path.exists(temp_pdf_path):
                    try:
                        os.remove(temp_pdf_path)
                    except Exception as e:
                        print(f"Could not remove temp preview file: {e}", file=sys.stderr)
        else:
            self.preview_widget.display_error_message(self.translator.tr("Impossible de générer l'aperçu."))


    def generate_pdf_final(self):
        pdf_bytes = self.current_pdf_data 
        if not pdf_bytes:
            pdf_bytes = self.generate_pdf_to_buffer()

        if not pdf_bytes:
            QMessageBox.critical(self, self.translator.tr("Erreur PDF"), self.translator.tr("Aucune donnée PDF à enregistrer."))
            return

        default_filename = (self.title_edit.text() or self.translator.tr("PageDeGarde", "Default PDF Name Context")) + ".pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, self.translator.tr("Enregistrer le PDF"), default_filename,
                                                   "PDF Files (*.pdf)")
        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(pdf_bytes)
                
                form_data = self.get_current_form_data()
                self.db.log_generation(title=form_data.get('title'), 
                                       author=form_data.get('author'),
                                       file_path=file_path,
                                       template_id=self.current_template_id)
                
                QMessageBox.information(self, self.translator.tr("PDF Généré"), 
                                        self.translator.tr("Le fichier PDF a été enregistré sous:\n{}", file_path))
                reply = QMessageBox.question(self, self.translator.tr("Ouvrir PDF"), 
                                             self.translator.tr("Voulez-vous ouvrir le fichier généré?"),
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

            except Exception as e:
                QMessageBox.critical(self, self.translator.tr("Erreur d'Enregistrement"), 
                                     self.translator.tr("Impossible d'enregistrer le PDF: {}", str(e)))


    # --- Autosave & State Management (Simplified) ---
    def autosave_current_form(self):
        # This would save current form data to a temporary location or special preference
        # For now, let's just print a message.
        # print(f"Autosave triggered at {datetime.datetime.now()}")
        # self.db.save_preference("autosave_form_data", self.get_current_form_data())
        pass


    def load_state(self): # Called at startup
        # form_data = self.db.load_preference("autosave_form_data")
        # if form_data and isinstance(form_data, dict):
        #     print("Restoring autosaved form data.")
        #     self.populate_form_from_data(form_data)
        # else: # Load default template or clear form
        #     default_template_name = self.db.load_preference("default_template")
        #     if default_template_name:
        #         # logic to load this template
        #         pass
        #     else:
        #         self.clear_form()
        pass

    def save_state(self): # Called on exit
        # self.db.save_preference("autosave_form_data", self.get_current_form_data())
        # self.db.save_preference("last_used_template_id", self.current_template_id)
        pass

    def closeEvent(self, event: QEvent):
        # self.save_state()
        reply = QMessageBox.question(self, self.translator.tr("&Quitter"),
                                     self.translator.tr("Êtes-vous sûr de vouloir quitter?"),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
            
    def show_about_dialog(self):
        QMessageBox.about(self, self.translator.tr("À propos de Générateur de Page de Garde"),
                          self.translator.tr(
                          """
                          <b>Générateur de Page de Garde Moderne</b> v0.1 Alpha
                          <p>Une application pour créer facilement des pages de garde personnalisées.
                          <p>Développé avec PyQt5 et ReportLab.
                          <p>© 2023 Votre Nom/Organisation. Tous droits réservés.
                          <p><a href='https://example.com'>Visitez notre site web</a>
                          """)
                          )

# --- Standalone PDF Generation Logic ---
def generate_cover_page_logic(config: Dict[str, Any]) -> bytes:
    """
    Generates a cover page PDF based on the provided configuration dictionary.

    Args:
        config (Dict[str, Any]): A dictionary containing parameters for PDF generation.
            Expected keys include:
            - 'title' (str): Main title of the document.
            - 'subtitle' (str, optional): Subtitle of the document.
            - 'author' (str, optional): Author's name.
            - 'institution' (str, optional): Institution name.
            - 'department' (str, optional): Department name.
            - 'doc_type' (str, optional): Type of document (e.g., "Report").
            - 'date' (str, optional): Date string.
            - 'version' (str, optional): Version string.
            - 'font_name' (str, optional): Default font name (e.g., 'Arial', 'Helvetica'). Defaults to 'Helvetica'.
            - 'font_size_title' (int, optional): Font size for the title. Defaults to 24.
            - 'font_size_subtitle' (int, optional): Font size for the subtitle. Defaults to 18.
            - 'font_size_author' (int, optional): Font size for author/institution. Defaults to 12.
            - 'font_size_footer' (int, optional): Font size for footer text. Defaults to 8 or 10.
            - 'text_color' (str, optional): Main text color (e.g., '#000000'). Not fully implemented for all elements yet.
            - 'logo_data' (bytes, optional): Byte data of the logo image.
            - 'logo_width_mm' (int, optional): Width of the logo in mm. Defaults to 50.
            - 'logo_height_mm' (int, optional): Max height of the logo in mm. Defaults to 50.
            - 'logo_x_mm' (int, optional): X position of the logo in mm.
            - 'logo_y_mm' (int, optional): Y position of the logo in mm.
            - 'show_horizontal_line' (bool, optional): Whether to show a horizontal line. Defaults to True.
            - 'line_y_position_mm' (int, optional): Y position of the horizontal line in mm.
            - 'line_color_hex' (str, optional): Color of the line in hex (e.g., '#000000').
            - 'line_thickness_pt' (float, optional): Thickness of the line in points.
            - 'margin_top' (int, optional): Top margin in mm. Defaults to 25.
            - 'margin_bottom' (int, optional): Bottom margin in mm. Defaults to 25.
            - 'margin_left' (int, optional): Left margin in mm. Defaults to 20.
            - 'margin_right' (int, optional): Right margin in mm. Defaults to 20.
            - 'footer_text' (str, optional): Text for the footer.
            - 'template_style' (str, optional): Style hint (e.g., 'Modern'). Currently not heavily used by this basic logic.


    Returns:
        bytes: The generated PDF as a byte string.

    Raises:
        Exception: If any error occurs during PDF generation.
    """
    buffer = io.BytesIO()

    # --- Register Fonts (copied from original generate_pdf_to_buffer) ---
    # This section should ideally be managed globally or passed if fonts are pre-registered.
    # For now, keeping it here to ensure the logic is self-contained.
    # --- Register Fonts ---
    effective_arial_font = 'Helvetica'
    effective_arial_bold_font = 'Helvetica-Bold'
    effective_showcard_font = 'Helvetica' # Default fallback for Showcard Gothic

    # Arial
    try:
        arial_path = os.path.join(APP_ROOT_DIR, 'fonts', 'arial.ttf')
        if os.path.exists(arial_path):
            pdfmetrics.registerFont(TTFont('Arial', arial_path))
            effective_arial_font = 'Arial'
            print(f"Successfully registered Arial from {arial_path} in generate_cover_page_logic")
        else:
            print(f"Warning (generate_cover_page_logic): Custom Arial font not found at {arial_path}. Using Helvetica.")
    except Exception as e:
        print(f"Error (generate_cover_page_logic): Registering custom Arial font from {arial_path}: {e}. Using Helvetica.")

    # Arial Bold
    arial_bold_path = os.path.join(APP_ROOT_DIR, 'fonts', 'arialbd.ttf')
    if os.path.exists(arial_bold_path):
        try:
            pdfmetrics.registerFont(TTFont('Arial-Bold', arial_bold_path))
            effective_arial_bold_font = 'Arial-Bold'
            print(f"Successfully registered Arial-Bold from {arial_bold_path} in generate_cover_page_logic")
        except Exception as e:
            print(f"Error (generate_cover_page_logic): Registering custom Arial Bold from {arial_bold_path}: {e}. Using Helvetica-Bold.")
    else:
        print(f"Warning (generate_cover_page_logic): Custom Arial Bold font 'arialbd.ttf' not found in 'fonts/'. Using Helvetica-Bold.")

    # Showcard Gothic
    showcard_font_name_to_register = 'Showcard Gothic'
    showcard_paths_to_try = [
        os.path.join(APP_ROOT_DIR, 'fonts', 'ShowcardGothic.ttf'),
        os.path.join(APP_ROOT_DIR, 'fonts', 'showg.ttf')
    ]
    showcard_registered = False
    for showcard_path in showcard_paths_to_try:
        if os.path.exists(showcard_path):
            try:
                pdfmetrics.registerFont(TTFont(showcard_font_name_to_register, showcard_path))
                effective_showcard_font = showcard_font_name_to_register
                showcard_registered = True
                print(f"Successfully registered {showcard_font_name_to_register} from {showcard_path} in generate_cover_page_logic")
                break
            except Exception as e:
                print(f"Error (generate_cover_page_logic): Registering {showcard_font_name_to_register} from {showcard_path}: {e}")

    if not showcard_registered:
        print(f"Warning (generate_cover_page_logic): Failed to load custom '{showcard_font_name_to_register}' font. "
              f"Ensure 'fonts/ShowcardGothic.ttf' or 'fonts/showg.ttf' is valid. "
              f"Falling back to {effective_showcard_font}. Appearance will differ.")
    # --- End Font Registration ---

    c = reportlab_canvas.Canvas(buffer, pagesize=A4)

    # Determine base font to use based on pdf_config and registration success
    requested_base_font_name = config.get("font_name", "Arial") # Default to "Arial" if not specified in config
    base_font_to_use = effective_arial_font # Default to Arial (or its fallback)

    if requested_base_font_name == 'Arial-Bold':
        base_font_to_use = effective_arial_bold_font
    elif requested_base_font_name == 'Showcard Gothic':
        base_font_to_use = effective_showcard_font
    elif requested_base_font_name != 'Arial': # If a different font than Arial was requested
        base_font_to_use = requested_base_font_name # Use it directly, hoping it's standard or pre-registered
        # print(f"Warning (generate_cover_page_logic): Font '{base_font_to_use}' requested directly. Ensure it's standard or pre-registered.")


    # Title
    c.setFont(base_font_to_use, config.get("font_size_title", 24))
    title_y = A4[1] - config.get("margin_top", 25) * mm - 30 * mm # Example y position
    if config.get("title"):
        c.drawCentredString(A4[0] / 2, title_y, config.get("title"))

    # Subtitle
    # Assuming subtitle uses the same base font as title
    c.setFont(base_font_to_use, config.get("font_size_subtitle", 18))
    if config.get("subtitle"):
        title_y -= 15 * mm # Adjust Y position
        c.drawCentredString(A4[0] / 2, title_y, config.get("subtitle"))

    # Author
    # Assuming author uses the same base font
    c.setFont(base_font_to_use, config.get("font_size_author", 12))
    if config.get("author"):
        author_y = A4[1] / 2  # Example position, make configurable via config
        c.drawCentredString(A4[0] / 2, author_y, config.get("author"))

    # Institution (similar to author)
    if config.get("institution"):
        # Assuming same font as author for now
        institution_y = author_y - 10 * mm # Adjust as needed
        c.drawCentredString(A4[0] / 2, institution_y, config.get("institution"))

    # Department (similar to institution)
    if config.get("department"):
        department_y = institution_y - 7*mm
        c.drawCentredString(A4[0]/2, department_y, config.get("department"))

    # Document Type
    if config.get("doc_type"):
        # Assuming same font
        doc_type_y = department_y - 15*mm # Adjust
        c.drawCentredString(A4[0]/2, doc_type_y, config.get("doc_type"))

    # Date & Version (typically at bottom or specific locations)
    # Assuming these also use the base_font_to_use or a generic one like effective_arial_font
    c.setFont(base_font_to_use, config.get("font_size_footer", 10)) # Example, use a specific size

    date_text = config.get("date", "")
    version_text = config.get("version", "")

    if date_text:
        c.drawString(config.get("margin_left", 20)*mm, config.get("margin_bottom", 25)*mm + 10*mm, f"Date: {date_text}")
    if version_text:
        c.drawRightString(A4[0] - config.get("margin_right", 20)*mm, config.get("margin_bottom", 25)*mm + 10*mm, f"Version: {version_text}")


    # Logo
    if config.get("logo_data"):
        try:
            logo_buffer = io.BytesIO(config.get("logo_data")) # ReportLab ImageReader needs a file-like object
            logo_image = ImageReader(logo_buffer)

            # Positioning and sizing from config, with defaults
            logo_width_mm = config.get("logo_width_mm", 50)
            logo_height_mm = config.get("logo_height_mm", 50) # Not used directly if preserveAspectRatio=True for drawImage

            # Default to top center if not specified
            default_logo_x_mm = (A4[0]/mm - logo_width_mm) / 2
            default_logo_y_mm = A4[1]/mm - config.get("margin_top", 25) - logo_width_mm - 10 # above title typically

            logo_x_mm = config.get("logo_x_mm", default_logo_x_mm)
            logo_y_mm = config.get("logo_y_mm", default_logo_y_mm)

            c.drawImage(logo_image, logo_x_mm * mm, logo_y_mm * mm,
                        width=logo_width_mm * mm, height=logo_height_mm*mm, # height is max_height with preserveAspectRatio
                        preserveAspectRatio=True, anchor='c', mask='auto')
        except Exception as logo_e:
            print(f"Error drawing logo in PDF (logic function): {logo_e}", file=sys.stderr)
            # Optionally draw a placeholder or skip

    # Horizontal Line
    if config.get("show_horizontal_line", True):
        line_y_mm = config.get("line_y_position_mm", A4[1]/mm / 2 + 20*mm) # Example position
        line_color_hex = config.get("line_color_hex", "#000000")
        line_thickness_pt = config.get("line_thickness_pt", 0.5)

        c.setStrokeColor(HexColor(line_color_hex))
        c.setLineWidth(line_thickness_pt)
        c.line(config.get("margin_left", 20)*mm, line_y_mm*mm, A4[0] - config.get("margin_right", 20)*mm, line_y_mm*mm)

    # Footer text (example)
    if config.get("footer_text"):
        c.setFont(date_version_font_name, config.get("font_size_footer", 8))
        c.drawCentredString(A4[0]/2, config.get("margin_bottom", 25)*mm / 2, config.get("footer_text"))

    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# --- Main Execution ---
def main():
    # Ensure resource file is imported if you use qrc paths (e.g. :/icons/)
    # import resources_rc # Assuming your .qrc is compiled to resources_rc.py

    # For high DPI scaling (optional but recommended)
    # These should be set BEFORE the QApplication is instantiated.
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("CoverPageGenerator")
    app.setOrganizationName("MyCompany") # Optional
    
    # Apply a style (optional, but Fusion looks good on many platforms)
    # app.setStyle("Fusion")

    # --- Setup Language from Preferences before UI is created ---
    # This is a preliminary setup. The main window will also apply prefs.
    temp_db = DatabaseManager() # Temporary DB manager to load language pref

    # Determine default language display name from APP_CONFIG or hardcoded fallback
    # This ensures that if 'fr' is not in LANGUAGES, "Français" is used as fallback.
    # And if APP_CONFIG['default_language'] is 'en', it correctly fetches "English".
    initial_default_lang_code = APP_CONFIG.get('default_language', 'fr')
    initial_default_lang_display_name = Translator().LANGUAGES.get(initial_default_lang_code, "Français")

    # Load preferred language (display name) from DB, or use the determined default
    preferred_lang_display_name = temp_db.load_preference('language', initial_default_lang_display_name)

    # For now, we don't have a global translator instance yet.
    # The main_window will create its own translator and set its language.
    # This is just to potentially inform Qt's own translations if possible early.
    # QLocale.setDefault(QLocale(preferred_lang_code)) # This would need lang code e.g. 'en_US'

    del temp_db # Clean up temporary DB manager

    main_window = CoverPageGenerator()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()