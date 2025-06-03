import os
import sys
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, Fill, Alignment, Border, Side, PatternFill, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.worksheet.merge import MergedCellRange
from PyQt5.QtWidgets import (
    QDialog, QTableWidget, QTableWidgetItem, QMessageBox, 
    QVBoxLayout, QHBoxLayout, QPushButton, QDialogButtonBox,
    QAbstractItemView, QHeaderView, QFileDialog, QProgressBar,
    QLabel, QFrame, QSplitter, QWidget, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QCheckBox, QStyleFactory, QAction
)
from PyQt5.QtGui import QFont, QColor, QIcon, QPalette, QBrush, QKeySequence
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QCoreApplication

# Reportlab imports
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Define APP_ROOT_DIR for font path resolution
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    APP_ROOT_DIR = sys._MEIPASS
else:
    APP_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Enregistrer les polices pour Unicode
# Arial
try:
    arial_path = os.path.join(APP_ROOT_DIR, 'fonts', 'arial.ttf')
    if os.path.exists(arial_path):
        pdfmetrics.registerFont(TTFont('Arial', arial_path))
    else:
        print(f"Warning: Arial font not found at {arial_path}. Using ReportLab default.")
except Exception as e:
    print(f"Error registering Arial font: {e}")

# Arial Bold
try:
    arial_bold_path = os.path.join(APP_ROOT_DIR, 'fonts', 'arialbd.ttf')
    if os.path.exists(arial_bold_path):
        pdfmetrics.registerFont(TTFont('Arial-Bold', arial_bold_path))
    else:
        print(f"Warning: Arial Bold font not found at {arial_bold_path}. Using ReportLab default.")
except Exception as e:
    print(f"Error registering Arial Bold font: {e}")

# Showcard Gothic
try:
    showcard_path = os.path.join(APP_ROOT_DIR, 'fonts', 'ShowcardGothic.ttf') # Common name is Showcard Gothic.ttf or showg.ttf
    # Attempt with ShowcardGothic.ttf first, then showg.ttf if not found
    if not os.path.exists(showcard_path):
        showcard_path_alt = os.path.join(APP_ROOT_DIR, 'fonts', 'showg.ttf')
        if os.path.exists(showcard_path_alt):
            showcard_path = showcard_path_alt # Use alternative path

    if os.path.exists(showcard_path):
        pdfmetrics.registerFont(TTFont('Showcard Gothic', showcard_path))
        print(f"Successfully registered Showcard Gothic from {showcard_path}")
    else:
        # Fallback or warning if Showcard Gothic is not found
        print(f"Warning: Showcard Gothic font not found at {os.path.join(APP_ROOT_DIR, 'fonts', 'ShowcardGothic.ttf')} or showg.ttf. PDF output may differ.")
        # Example fallback: register Arial as Showcard Gothic
        # try:
        #     arial_fallback_path = os.path.join(APP_ROOT_DIR, 'fonts', 'arial.ttf')
        #     if os.path.exists(arial_fallback_path):
        #        pdfmetrics.registerFont(TTFont('Showcard Gothic', arial_fallback_path))
        #        print(f"Registered Arial as fallback for Showcard Gothic.")
        # except Exception as fallback_e:
        #    print(f"Could not register Arial as fallback for Showcard Gothic: {fallback_e}")
except Exception as e:
    print(f"Error registering Showcard Gothic font: {e}")


class ExcelProcessor(QThread):
    """Thread worker pour les opérations Excel lourdes"""
    progress_update = pyqtSignal(int)
    status_update = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    data_loaded = pyqtSignal(list, list, list)
    
    def __init__(self, operation, file_path, data=None, client_data=None):
        super().__init__()
        self.operation = operation
        self.file_path = file_path
        self.data = data
        self.client_data = client_data or {}
        
    def run(self):
        try:
            if self.operation == "load":
                self._load_excel()
            elif self.operation == "save":
                self._save_excel()
            elif self.operation == "export_pdf":
                self._export_pdf()
        except Exception as e:
            self.finished_signal.emit(False, str(e))
            
    def _load_excel(self):
        try:
            self.status_update.emit("Chargement du fichier Excel...")
            
            # Charger le workbook
            workbook = load_workbook(self.file_path)
            sheet_names = workbook.sheetnames
            
            # Préparer les données de toutes les feuilles
            sheets_data = []
            merged_cells_all = []
            
            for sheet_name in sheet_names:
                sheet = workbook[sheet_name]
                
                # Lire les données
                data = []
                for row in sheet.iter_rows():
                    row_data = []
                    for cell in row:
                        row_data.append(cell.value)
                    data.append(row_data)
                
                # Stocker les cellules fusionnées
                merged_cells = []
                for merge_range in sheet.merged_cells.ranges:
                    merged_cells.append((
                        merge_range.min_row, 
                        merge_range.min_col,
                        merge_range.max_row,
                        merge_range.max_col
                    ))
                
                sheets_data.append(data)
                merged_cells_all.append(merged_cells)
            
            self.data_loaded.emit(sheets_data, merged_cells_all, sheet_names)
            self.finished_signal.emit(True, "Chargement terminé")
            
        except Exception as e:
            self.finished_signal.emit(False, str(e))
            
    def _save_excel(self):
        # Implémentation de sauvegarde optimisée
        pass
        
    def _export_pdf(self):
        # Implémentation d'export PDF
        pass


class ClientInfoWidget(QGroupBox):
    """Widget dédié aux informations client"""
    
    def __init__(self, client_data: Dict[str, Any] = None):
        super().__init__(self.tr("Informations Client"))
        self.client_data = client_data or {}
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        layout = QFormLayout()
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        self.nom_client = QLineEdit()
        self.nom_client.setPlaceholderText(self.tr("Nom du client"))
        layout.addRow(self.tr("Nom du client:"), self.nom_client)
        
        self.besoin_client = QTextEdit()
        self.besoin_client.setMaximumHeight(80)
        self.besoin_client.setPlaceholderText(self.tr("Description du besoin"))
        layout.addRow(self.tr("Besoin:"), self.besoin_client)
        
        self.project_id = QLineEdit()
        self.project_id.setPlaceholderText(self.tr("Identifiant du projet"))
        layout.addRow(self.tr("ID Projet:"), self.project_id)
        
        self.price = QSpinBox()
        self.price.setRange(0, 99999999)
        self.price.setSuffix(" €") # Currency symbol might need locale-specific handling
        layout.addRow(self.tr("Prix:"), self.price)
        
        self.setLayout(layout)
        
    def _load_data(self):
        """Charge les données client dans les widgets"""
        self.nom_client.setText(self.client_data.get("Nom du client", ""))
        self.besoin_client.setPlainText(self.client_data.get("Besoin", ""))
        self.project_id.setText(self.client_data.get("project_identifier", ""))
        self.price.setValue(int(self.client_data.get("price", 0)))
        
    def get_client_data(self) -> Dict[str, Any]:
        """Retourne les données client actuelles"""
        return {
            "Nom du client": self.nom_client.text(),
            "Besoin": self.besoin_client.toPlainText(),
            "project_identifier": self.project_id.text(),
            "price": self.price.value()
        }


class ExcelTableWidget(QTableWidget):
    """TableWidget personnalisé avec fonctionnalités étendues"""
    
    def __init__(self):
        super().__init__()
        self._setup_table()
        
    def _setup_table(self):
        """Configuration initiale de la table"""
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.verticalHeader().setVisible(False)
        
        # Style personnalisé
        self.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f5f5f5;
                border: 1px solid #c0c0c0;
            }
            QTableWidget::item:selected {
                background-color: #316AC5;
                color: white;
            }
            QHeaderView::section {
                background-color: #E5E5E5;
                padding: 5px;
                border: 1px solid #C0C0C0;
                font-weight: bold;
            }
        """)
        
    def add_row(self):
        current_rows = self.rowCount()
        self.insertRow(current_rows)
        
    def add_column(self):
        current_cols = self.columnCount()
        self.insertColumn(current_cols)
        self.setHorizontalHeaderItem(current_cols, QTableWidgetItem(self.tr("Colonne {0}").format(current_cols + 1)))
        
    def delete_selected_rows(self):
        selected_rows = set()
        for item in self.selectedItems():
            selected_rows.add(item.row())
            
        for row in sorted(selected_rows, reverse=True):
            self.removeRow(row)
            
    def delete_selected_columns(self):
        selected_cols = set()
        for item in self.selectedItems():
            selected_cols.add(item.column())
            
        for col in sorted(selected_cols, reverse=True):
            self.removeColumn(col)
            
    def set_span(self, row, col, row_span, col_span):
        self.setSpan(row, col, row_span, col_span)
        
    def get_merged_cells(self):
        """Retourne les cellules fusionnées sous forme de liste de tuples (row, col, row_span, col_span)"""
        merged = []
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                row_span = self.rowSpan(row, col)
                col_span = self.columnSpan(row, col)
                if row_span > 1 or col_span > 1:
                    merged.append((row, col, row_span, col_span))
        return merged


class StyleManager:
    """Gestionnaire de styles pour les cellules"""
    
    @staticmethod
    def qcolor_to_hex(qcolor: QColor) -> Optional[str]:
        if not qcolor.isValid():
            return None
        return f"#{qcolor.red():02x}{qcolor.green():02x}{qcolor.blue():02x}"
    
    @staticmethod
    def hex_to_qcolor(hex_color: str) -> QColor:
        try:
            return QColor(hex_color)
        except:
            return QColor()
    
    @staticmethod
    def apply_openpyxl_style_to_item(cell, item: QTableWidgetItem):
        if not cell.has_style:
            return
            
        # Font
        if cell.font:
            font = QFont()
            if cell.font.name:
                font.setFamily(cell.font.name)
            if cell.font.sz:
                font.setPointSize(int(cell.font.sz))
            if cell.font.b:
                font.setBold(True)
            if cell.font.i:
                font.setItalic(True)
            if cell.font.u:
                font.setUnderline(True)
            
            # Couleur du texte
            if cell.font.color and cell.font.color.rgb:
                hex_color = str(cell.font.color.rgb)
                if len(hex_color) == 8:
                    hex_color = hex_color[2:]  # Retirer ARGB prefix
                elif len(hex_color) == 6:
                    pass  # RGB format
                else:
                    hex_color = "000000"  # Default black
                    
                try:
                    item.setForeground(QColor(f"#{hex_color}"))
                except:
                    pass
                    
            item.setFont(font)
        
        # Background color
        if cell.fill and cell.fill.fgColor and cell.fill.fgColor.rgb:
            hex_color = str(cell.fill.fgColor.rgb)
            if len(hex_color) == 8:
                hex_color = hex_color[2:]
            elif len(hex_color) == 6:
                pass
            else:
                hex_color = "FFFFFF"  # Default white
                
            try:
                item.setBackground(QColor(f"#{hex_color}"))
            except:
                pass
        
        # Alignment
        if cell.alignment:
            alignment = 0
            h_align = cell.alignment.horizontal
            v_align = cell.alignment.vertical
            
            if h_align == 'left':
                alignment |= Qt.AlignLeft
            elif h_align == 'center':
                alignment |= Qt.AlignHCenter
            elif h_align == 'right':
                alignment |= Qt.AlignRight
            elif h_align == 'justify':
                alignment |= Qt.AlignJustify
                
            if v_align == 'top':
                alignment |= Qt.AlignTop
            elif v_align == 'center':
                alignment |= Qt.AlignVCenter
            elif v_align == 'bottom':
                alignment |= Qt.AlignBottom
                
            if alignment:
                item.setTextAlignment(alignment)


class PDFExporter:
    """Classe dédiée à l'export PDF avec haute fidélité"""
    
    def __init__(self, table_widget: QTableWidget, client_data: Dict[str, Any], file_name: str):
        self.table_widget = table_widget
        self.client_data = client_data
        self.file_name = file_name
        
    def export_to_pdf(self, save_path: str) -> Tuple[bool, str]:
        try:
            # Configuration du document
            doc = SimpleDocTemplate(
                save_path, 
                pagesize=A4,
                rightMargin=1*cm, 
                leftMargin=1*cm,
                topMargin=1*cm, 
                bottomMargin=1*cm
            )
            
            elements = []
            styles = getSampleStyleSheet()
            
            # Style personnalisé pour le titre
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName='Arial-Bold', # Font names are not typically translated
                fontSize=14,
                spaceAfter=12,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#2c3e50")
            )
            
            # Titre
            title_text = f"<u>{QCoreApplication.translate('PDFExporter', 'Formulaire d''Offre')}</u>"
            elements.append(Paragraph(title_text, title_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Informations client dans un tableau
            client_info = [
                [QCoreApplication.translate('PDFExporter', 'Client:'), self.client_data.get('Nom du client', QCoreApplication.translate('PDFExporter', 'N/A'))],
                [QCoreApplication.translate('PDFExporter', 'Projet:'), self.client_data.get('Besoin', QCoreApplication.translate('PDFExporter', 'N/A'))],
                [QCoreApplication.translate('PDFExporter', 'ID Projet:'), self.client_data.get('project_identifier', QCoreApplication.translate('PDFExporter', 'N/A'))],
                [QCoreApplication.translate('PDFExporter', 'Prix Total:'), f"{self.client_data.get('price', 0):,} €"], # Currency format
                [QCoreApplication.translate('PDFExporter', 'Date d\'émission:'), datetime.now().strftime('%d/%m/%Y %H:%M')] # Date format
            ]
            
            client_table = Table(client_info, colWidths=[3*cm, 10*cm])
            client_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#e8f4f8")),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Arial-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#c0c0c0")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(client_table)
            elements.append(Spacer(1, 0.8*cm))
            
            # Données du tableau principal
            data, col_widths = self._extract_table_data()
            if not data:
                return False, "Le tableau est vide"
                
            # Création du tableau principal
            main_table = Table(data, colWidths=col_widths)
            table_style = self._create_table_style(len(data), len(data[0]) if data else 0)
            main_table.setStyle(table_style)
            
            elements.append(main_table)
            elements.append(Spacer(1, 1.2*cm))
            
            # Informations de contact
            contact_style = ParagraphStyle(
                'ContactStyle',
                parent=styles['BodyText'],
                fontName='Arial', # Font names are not typically translated
                fontSize=10,
                leading=14,
                spaceAfter=6
            )
            
            contact_text = QCoreApplication.translate('PDFExporter',
                "<b>Personnel responsable:</b> Ramazan Demirci    "
                "<b>Tél:</b> +90 533 548 27 29    "
                "<b>Email:</b> bilgi@hidrogucpres.com"
            )
            elements.append(Paragraph(contact_text, contact_style))
            
            # Conditions d'achat
            elements.append(Spacer(1, 0.5*cm))
            elements.append(Paragraph(QCoreApplication.translate('PDFExporter', "<b>Conditions d'achat:</b>"), contact_style))
            
            conditions = [
                QCoreApplication.translate('PDFExporter', "1. Les offres seront présentées en livres turques (prioritairement) ou en devises étrangères, TVA comprise."),
                QCoreApplication.translate('PDFExporter', "2. Le délai de livraison de la presse est de dix jours calendaires à compter de la signature du contrat."),
                QCoreApplication.translate('PDFExporter', "3. Lieu de livraison du matériel : Hidroguç Konya Türkiye"),
                QCoreApplication.translate('PDFExporter', "4. Le paiement sera effectué conformément au plan de paiement de Hidroguç, après la production du matériel."),
                QCoreApplication.translate('PDFExporter', "5. L’offre est valable pendant 30 jours calendaires."),
                QCoreApplication.translate('PDFExporter', "6. Ce produit est exonéré de TVA.")
            ]
            
            for condition in conditions:
                elements.append(Paragraph(condition, contact_style))
            
            # Construction du PDF
            doc.build(elements)
            return True, QCoreApplication.translate('PDFExporter', "Export PDF réussi")
            
        except Exception as e:
            return False, QCoreApplication.translate('PDFExporter', "Erreur lors de l'export PDF: {0}").format(str(e))
    
    def _extract_table_data(self) -> Tuple[List[List[str]], List[float]]:
        rows = self.table_widget.rowCount()
        cols = self.table_widget.columnCount()
        
        # Créer une grille vide
        data = [['' for _ in range(cols)] for _ in range(rows)]
        col_widths = [self.table_widget.columnWidth(c) / 10 for c in range(cols)]  # Convertir en mm
        
        # Remplir les données
        for r in range(rows):
            for c in range(cols):
                item = self.table_widget.item(r, c)
                if item is not None:
                    data[r][c] = item.text()
                    
        return data, col_widths
    
    def _create_table_style(self, rows: int, cols: int) -> TableStyle:
        style_commands = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#c0c0c0")),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3498db")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Arial-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('FONTNAME', (0, 1), (-1, -1), 'Arial'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        # Ajouter les styles spécifiques aux cellules
        for r in range(rows):
            for c in range(cols):
                item = self.table_widget.item(r, c)
                if item:
                    # Couleur de fond
                    bg_color = item.background().color()
                    if bg_color.isValid() and bg_color != Qt.white:
                        hex_color = StyleManager.qcolor_to_hex(bg_color)
                        if hex_color:
                            style_commands.append(('BACKGROUND', (c, r), (c, r), colors.HexColor(hex_color)))
                    
                    # Couleur de texte
                    fg_color = item.foreground().color()
                    if fg_color.isValid() and fg_color != Qt.black:
                        hex_color = StyleManager.qcolor_to_hex(fg_color)
                        if hex_color:
                            style_commands.append(('TEXTCOLOR', (c, r), (c, r), colors.HexColor(hex_color)))
                    
                    # Alignement
                    alignment = item.textAlignment()
                    if alignment & Qt.AlignLeft:
                        style_commands.append(('ALIGN', (c, r), (c, r), 'LEFT'))
                    elif alignment & Qt.AlignRight:
                        style_commands.append(('ALIGN', (c, r), (c, r), 'RIGHT'))
                    elif alignment & Qt.AlignHCenter:
                        style_commands.append(('ALIGN', (c, r), (c, r), 'CENTER'))
        
        # Gestion des fusions
        for r in range(rows):
            for c in range(cols):
                row_span = self.table_widget.rowSpan(r, c)
                col_span = self.table_widget.columnSpan(r, c)
                
                if row_span > 1 or col_span > 1:
                    style_commands.append(('SPAN', (c, r), (c + col_span - 1, r + row_span - 1)))
        
        return TableStyle(style_commands)


class ExcelEditor(QDialog):
    """Éditeur Excel amélioré avec gestion multi-feuilles"""
    
    def __init__(self, file_path: str, client_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.client_data = client_data or {}
        self.workbook = None
        self.active_sheet = None
        self.sheet_data = {}
        self.is_modified = False
        self.merged_cells = []
        self.current_sheet_index = 0
        
        # Configuration du logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self._setup_ui()
        self._connect_signals()
        self._load_data()
        
    def _setup_ui(self):
        """Configuration de l'interface utilisateur"""
        self.setWindowTitle(self.tr("Éditeur Excel - {0}").format(os.path.basename(self.file_path)))
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Appliquer un style moderne
        self.setStyle(QStyleFactory.create("Fusion"))
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Barre de statut en haut
        self._create_status_bar()
        main_layout.addWidget(self.status_frame)
        
        # Barre d'outils des feuilles
        self.sheet_toolbar = QFrame()
        self.sheet_toolbar.setStyleSheet("background-color: #f8f9fa; border-bottom: 1px solid #dee2e6;")
        self.sheet_toolbar.setFixedHeight(40)
        
        sheet_layout = QHBoxLayout(self.sheet_toolbar)
        sheet_layout.setContentsMargins(10, 0, 10, 0)
        
        sheet_label = QLabel(self.tr("Feuille:"))
        sheet_label.setStyleSheet("font-weight: bold;")
        sheet_layout.addWidget(sheet_label)
        
        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumWidth(200)
        sheet_layout.addWidget(self.sheet_combo)
        
        sheet_layout.addStretch()
        
        main_layout.addWidget(self.sheet_toolbar)
        
        # Splitter principal
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel gauche - Informations client
        self.client_info_widget = ClientInfoWidget(self.client_data)
        self.client_info_widget.setMaximumWidth(350)
        splitter.addWidget(self.client_info_widget)
        
        # Panel droit - Table Excel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)
        
        # Barre d'outils de la table
        self.table_toolbar = self._create_table_toolbar()
        right_layout.addWidget(self.table_toolbar)
        
        # Création de la table
        self.table_widget = ExcelTableWidget()
        right_layout.addWidget(self.table_widget)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 1000])
        
        main_layout.addWidget(splitter)
        
        # Barre de boutons principale
        self._create_main_buttons()
        main_layout.addLayout(self.button_layout)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(20)
        main_layout.addWidget(self.progress_bar)

    def _create_status_bar(self):
        self.status_frame = QFrame()
        self.status_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.status_frame.setStyleSheet("background-color: #f0f0f0; border: 1px solid #c0c0c0;")
        self.status_frame.setFixedHeight(30)
        
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(10, 0, 10, 0)
        
        self.status_label = QLabel("Prêt")
        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.file_info_label = QLabel(f"Fichier: {os.path.basename(self.file_path)}")
        self.file_info_label.setStyleSheet("color: #7f8c8d;")
        status_layout.addWidget(self.file_info_label)
        
    def _create_table_toolbar(self):
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #f8f9fa; border-bottom: 1px solid #dee2e6;")
        toolbar.setFixedHeight(40)
        
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 0, 10, 0)
        toolbar_layout.setSpacing(10)
        
        # Boutons d'édition de table
        add_row_btn = QPushButton(self.tr("Ajouter ligne"))
        add_row_btn.setIcon(QIcon.fromTheme("list-add"))
        add_row_btn.setStyleSheet("padding: 5px;")
        add_row_btn.clicked.connect(self.table_widget.add_row)
        toolbar_layout.addWidget(add_row_btn)
        
        add_col_btn = QPushButton(self.tr("Ajouter colonne"))
        add_col_btn.setIcon(QIcon.fromTheme("list-add"))
        add_col_btn.setStyleSheet("padding: 5px;")
        add_col_btn.clicked.connect(self.table_widget.add_column)
        toolbar_layout.addWidget(add_col_btn)
        
        toolbar_layout.addWidget(QFrame())  # Separator
        
        del_row_btn = QPushButton(self.tr("Supprimer lignes"))
        del_row_btn.setIcon(QIcon.fromTheme("edit-delete"))
        del_row_btn.setStyleSheet("padding: 5px;")
        del_row_btn.clicked.connect(self.table_widget.delete_selected_rows)
        toolbar_layout.addWidget(del_row_btn)
        
        del_col_btn = QPushButton(self.tr("Supprimer colonnes"))
        del_col_btn.setIcon(QIcon.fromTheme("edit-delete"))
        del_col_btn.setStyleSheet("padding: 5px;")
        del_col_btn.clicked.connect(self.table_widget.delete_selected_columns)
        toolbar_layout.addWidget(del_col_btn)
        
        toolbar_layout.addStretch()
        
        return toolbar
        
    def _create_main_buttons(self):
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(15)
        
        # Bouton Sauvegarder
        self.save_button = QPushButton(self.tr("💾 Sauvegarder"))
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #219653;
            }
        """)
        self.button_layout.addWidget(self.save_button)
        
        # Bouton Export PDF
        self.export_pdf_button = QPushButton(self.tr("📄 Exporter PDF"))
        self.export_pdf_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1d6fa5;
            }
        """)
        self.button_layout.addWidget(self.export_pdf_button)
        
        self.button_layout.addStretch()
        
        # Bouton Annuler
        self.cancel_button = QPushButton(self.tr("❌ Fermer"))
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        self.button_layout.addWidget(self.cancel_button)
        
    def _connect_signals(self):
        self.save_button.clicked.connect(self.save_data)
        self.export_pdf_button.clicked.connect(self.export_to_pdf)
        self.cancel_button.clicked.connect(self.reject)
        self.sheet_combo.currentIndexChanged.connect(self.change_sheet)
        self.table_widget.itemChanged.connect(self._on_item_changed)
        
    def _on_item_changed(self):
        self.is_modified = True
        self.status_label.setText(self.tr("Modifié"))
        self.status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
        
    def _update_status(self, message: str, color: str = "blue"): # message is dynamic
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
    def _show_progress(self, visible: bool = True):
        self.progress_bar.setVisible(visible)
        if visible:
            self.progress_bar.setRange(0, 0)  # Mode indéterminé
        
    def _replace_placeholders(self, text: str) -> str:
        current_client_data = self.client_info_widget.get_client_data()
        replacements = {
            "{NOM_CLIENT}": current_client_data.get("Nom du client", ""),
            "{BESOIN_CLIENT}": current_client_data.get("Besoin", ""),
            "{DATE_CREATION}": datetime.now().strftime("%d/%m/%Y"),
            "{PRIX_FINAL}": str(current_client_data.get("price", "")),
            "{PROJECT_ID}": current_client_data.get("project_identifier", "")
        }
        
        for placeholder, value in replacements.items():
            text = text.replace(placeholder, str(value))
        return text
        
    def _create_empty_table(self):
        self.table_widget.setRowCount(10)
        self.table_widget.setColumnCount(5)
        headers = [f"Colonne {i+1}" for i in range(5)]
        self.table_widget.setHorizontalHeaderLabels(headers)
        
    def _load_data(self):
        try:
            self._update_status("Chargement des données...", "#3498db")
            self._show_progress(True)
            
            if not os.path.exists(self.file_path):
                self.logger.warning(f"Fichier inexistant: {self.file_path}")
                QMessageBox.warning(
                    self, 
                    self.tr("Fichier Inexistant"),
                    self.tr("Le fichier {0} n'existe pas.\nUn nouveau fichier sera créé.").format(self.file_path)
                )
                self._create_empty_table()
                self.workbook = Workbook()
                self.active_sheet = self.workbook.active
                self.sheet_combo.addItems([self.active_sheet.title]) # Sheet title is data-like
                self._update_status(self.tr("Nouveau fichier créé"), "#27ae60")
                self._show_progress(False)
                return

            # Chargement du workbook
            self.workbook = load_workbook(self.file_path)
            
            if not self.workbook.sheetnames:
                self.logger.warning("Workbook sans feuilles")
                self._create_empty_table()
                self.active_sheet = self.workbook.create_sheet(self.tr("Feuille1")) # Default sheet name
                self.sheet_combo.addItems([self.active_sheet.title])
                self._update_status(self.tr("Fichier vide - nouvelle feuille créée"), "#f39c12")
                self._show_progress(False)
                return
                
            # Remplir le combo des feuilles
            self.sheet_combo.addItems(self.workbook.sheetnames)
            
            # Charger la feuille active
            self.active_sheet = self.workbook.active
            self.sheet_combo.setCurrentText(self.active_sheet.title)
            self.load_sheet(self.active_sheet)
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement: {e}")
            QMessageBox.critical(
                self, 
                    self.tr("Erreur de Chargement"),
                    self.tr("Impossible de charger le fichier Excel:\n{0}\n\nUn tableau vide sera créé.").format(str(e))
            )
            self._create_empty_table()
            self.workbook = Workbook()
            self.active_sheet = self.workbook.active
                self.sheet_combo.addItems([self.active_sheet.title]) # Sheet title is data-like
                self._update_status(self.tr("Erreur - nouveau fichier créé"), "#e74c3c")
            
        finally:
            self._show_progress(False)
    
    def load_sheet(self, sheet: Worksheet):
        """Charge une feuille spécifique dans l'interface"""
        try:
            self._update_status(self.tr("Chargement de la feuille: {0}").format(sheet.title), "#3498db")
            self.table_widget.clear()
            
            # Charger les cellules fusionnées
            self.merged_cells = []
            for merge_range in sheet.merged_cells.ranges:
                self.merged_cells.append((
                    merge_range.min_row, 
                    merge_range.min_col,
                    merge_range.max_row,
                    merge_range.max_col
                ))
            
            # Déterminer la taille de la feuille
            max_row = sheet.max_row
            max_col = sheet.max_column
            
            # Configuration de la table
            self.table_widget.setRowCount(max_row)
            self.table_widget.setColumnCount(max_col)
            
            # Charger les headers
            headers = []
            if max_row >= 1:
                for col in range(1, max_col + 1):
                    cell = sheet.cell(row=1, column=col)
                    header_value = str(cell.value) if cell.value is not None else ""
                    headers.append(self._replace_placeholders(header_value))
            
            if headers:
                self.table_widget.setHorizontalHeaderLabels(headers)
            
            # Charger les données
            for row_idx in range(1, max_row + 1):
                for col_idx in range(1, max_col + 1):
                    cell = sheet.cell(row=row_idx, column=col_idx)
                    
                    cell_value = cell.value
                    if cell_value is None:
                        cell_value = ""
                    elif isinstance(cell_value, float):
                        cell_value = f"{cell_value:,.2f}"
                    else:
                        cell_value = str(cell_value)
                        
                    processed_value = self._replace_placeholders(cell_value)
                    
                    item = QTableWidgetItem(processed_value)
                    
                    # Application des styles
                    StyleManager.apply_openpyxl_style_to_item(cell, item)
                    
                    self.table_widget.setItem(row_idx - 1, col_idx - 1, item)
            
            # Appliquer les cellules fusionnées
            for min_row, min_col, max_row, max_col in self.merged_cells:
                start_row = min_row - 1
                start_col = min_col - 1
                row_span = max_row - min_row + 1
                col_span = max_col - min_col + 1
                
                if (start_row < self.table_widget.rowCount() and 
                    start_col < self.table_widget.columnCount()):
                    self.table_widget.setSpan(start_row, start_col, row_span, col_span)
            
            self.table_widget.resizeColumnsToContents()
            self._update_status(f"Feuille '{sheet.title}' chargée", "#27ae60")
                
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de la feuille: {e}")
            self._update_status(self.tr("Erreur de chargement de la feuille"), "#e74c3c")
            QMessageBox.critical(
                self, 
                self.tr("Erreur de Chargement"),
                self.tr("Impossible de charger la feuille '{0}':\n{1}").format(sheet.title, str(e))
            )
    
    def change_sheet(self, index):
        """Change la feuille active"""
        if index < 0 or index >= len(self.workbook.sheetnames):
            return
            
        sheet_name = self.workbook.sheetnames[index]
        if sheet_name == self.active_sheet.title:
            return
            
        # Sauvegarder les modifications de la feuille courante
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                self.tr("Modifications Non Sauvegardées"),
                self.tr("Vous avez des modifications non sauvegardées dans '{0}'.\nVoulez-vous sauvegarder avant de changer de feuille ?").format(self.active_sheet.title),
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                self.save_current_sheet()
            elif reply == QMessageBox.Cancel:
                # Revenir à la feuille précédente dans le combo
                self.sheet_combo.setCurrentText(self.active_sheet.title)
                return
                
        # Charger la nouvelle feuille
        self.active_sheet = self.workbook[sheet_name]
        self.load_sheet(self.active_sheet)
        self.is_modified = False
    
    def save_current_sheet(self):
        """Sauvegarde la feuille active dans le workbook"""
        try:
            # Mise à jour des données client
            current_client_data = self.client_info_widget.get_client_data()
            self.client_data.update(current_client_data)

            # Sauvegarde des headers
            for c_idx in range(self.table_widget.columnCount()):
                header_item = self.table_widget.horizontalHeaderItem(c_idx)
                header_text = header_item.text() if header_item else f"Colonne {c_idx+1}"
                self.active_sheet.cell(row=1, column=c_idx+1).value = header_text

            # Sauvegarde des données
            max_row_in_table = self.table_widget.rowCount()
            max_col_in_table = self.table_widget.columnCount()
            
            for r_idx in range(max_row_in_table):
                for c_idx in range(max_col_in_table):
                    item = self.table_widget.item(r_idx, c_idx)
                    cell_value = item.text() if item and item.text() else ""
                    
                    # Conversion de types intelligente
                    processed_value = self._convert_cell_value(cell_value)
                    
                    target_cell = self.active_sheet.cell(row=r_idx+1, column=c_idx+1)
                    target_cell.value = processed_value

            # Réappliquer les cellules fusionnées
            self.active_sheet.merged_cells.ranges = []
            for min_row, min_col, max_row, max_col in self.merged_cells:
                self.active_sheet.merge_cells(
                    start_row=min_row, 
                    start_column=min_col,
                    end_row=max_row,
                    end_column=max_col
                )
            
            self.is_modified = False
            self._update_status("Modifications sauvegardées", "#27ae60")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de la feuille: {e}")
            QMessageBox.critical(
                self, 
                self.tr("Erreur de Sauvegarde"),
                self.tr("Impossible de sauvegarder la feuille:\n{0}").format(str(e))
            )
    
    def save_data(self):
        """Sauvegarde toutes les données dans le fichier Excel"""
        if not self.is_modified:
            reply = QMessageBox.question(
                self,
                self.tr("Sauvegarder"),
                self.tr("Aucune modification détectée. Voulez-vous sauvegarder quand même ?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
                
        try:
            self._update_status(self.tr("Sauvegarde en cours..."), "#3498db")
            self._show_progress(True)
            
            # Sauvegarder la feuille courante
            self.save_current_sheet()
            
            # Sauvegarde du fichier
            self.workbook.save(self.file_path)
            
            self._update_status(self.tr("Sauvegarde réussie"), "#27ae60")
            self.logger.info(f"Fichier sauvegardé: {self.file_path}")
            
            QMessageBox.information(
                self, 
                self.tr("Sauvegarde Réussie"),
                self.tr("Le fichier a été sauvegardé avec succès:\n{0}").format(self.file_path)
            )
            
            # Timer pour revenir au statut "Prêt"
            QTimer.singleShot(3000, lambda: self._update_status(self.tr("Prêt"), "#27ae60"))
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde: {e}")
            QMessageBox.critical(
                self, 
                self.tr("Erreur de Sauvegarde"),
                self.tr("Impossible de sauvegarder le fichier:\n{0}").format(str(e))
            )
            self._update_status(self.tr("Erreur de sauvegarde"), "#e74c3c")
            
        finally:
            self._show_progress(False)

    def _convert_cell_value(self, cell_value: str):
        """Convertit intelligemment la valeur d'une cellule"""
        if not cell_value or cell_value.strip() == "":
            return None
            
        cell_value = cell_value.strip()
        
        # Gestion des nombres
        if re.match(r'^[+-]?\d*\.?\d+$', cell_value):
            try:
                if '.' in cell_value:
                    return float(cell_value)
                else:
                    return int(cell_value)
            except ValueError:
                pass
        
        # Gestion des dates
        date_formats = [
            '%d/%m/%Y',   # 31/12/2023
            '%Y-%m-%d',    # 2023-12-31
            '%d-%m-%Y',    # 31-12-2023
            '%m/%d/%Y',    # 12/31/2023 (US)
            '%d %b %Y',    # 31 Dec 2023
            '%d %B %Y',    # 31 December 2023
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(cell_value, fmt).date()
            except ValueError:
                continue
                
        # Gestion des devises
        currency_match = re.match(r'^([€$£])\s*([\d,\.]+)$', cell_value)
        if currency_match:
            try:
                amount = float(currency_match.group(2).replace(',', ''))
                return amount
            except ValueError:
                pass
                
        # Retourner comme string si aucune conversion possible
        return cell_value

    def export_to_pdf(self):
        """Lance l'export PDF avec haute qualité"""
        try:
            # Sélection du fichier de destination
            options = QFileDialog.Options()
            default_name = os.path.splitext(os.path.basename(self.file_path))[0] + ".pdf"
            
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("Exporter en PDF"),
                default_name,
                self.tr("Fichiers PDF (*.pdf);;Tous les fichiers (*)"),
                options=options
            )
            
            if not save_path:
                return
                
            # Vérification que la table n'est pas vide
            if self.table_widget.rowCount() == 0 or self.table_widget.columnCount() == 0:
                QMessageBox.warning(
                    self,
                    self.tr("Export PDF"),
                    self.tr("Le tableau est vide. Impossible d'exporter en PDF.")
                )
                return
                
            self._update_status(self.tr("Export PDF en cours..."), "#3498db")
            self._show_progress(True)
            
            # Utilisation de la classe PDFExporter
            current_client_data = self.client_info_widget.get_client_data()
            exporter = PDFExporter(self.table_widget, current_client_data, self.file_path)
            
            success, message = exporter.export_to_pdf(save_path)
            
            if success:
                self._update_status(self.tr("Export PDF réussi"), "#27ae60")
                self.logger.info(f"PDF exporté: {save_path}")
                
                reply = QMessageBox.question(
                    self,
                    self.tr("Export PDF Réussi"),
                    self.tr("Le fichier PDF a été créé avec succès:\n{0}\n\nVoulez-vous l'ouvrir ?").format(save_path),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    try:
                        if sys.platform == "win32":
                            os.startfile(save_path)
                        elif sys.platform == "darwin":
                            os.system(f'open "{save_path}"')
                        else:
                            os.system(f'xdg-open "{save_path}"')
                    except Exception as e:
                        self.logger.error(self.tr("Erreur d'ouverture du PDF: {0}").format(e))
                            
                # Timer pour revenir au statut "Prêt"
                QTimer.singleShot(3000, lambda: self._update_status(self.tr("Prêt"), "#27ae60"))
                
            else:
                self._update_status(self.tr("Erreur d'export PDF"), "#e74c3c")
                QMessageBox.critical(
                    self,
                    self.tr("Erreur d'Export PDF"),
                    self.tr("Impossible d'exporter le fichier en PDF:\n{0}").format(message)
                )
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'export PDF: {e}")
            self._update_status(self.tr("Erreur d'export PDF"), "#e74c3c")
            QMessageBox.critical(
                self,
                self.tr("Erreur d'Export PDF"),
                self.tr("Une erreur inattendue s'est produite:\n{0}").format(str(e))
            )
            
        finally:
            self._show_progress(False)

    def closeEvent(self, event):
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                self.tr("Modifications Non Sauvegardées"),
                self.tr("Vous avez des modifications non sauvegardées.\nVoulez-vous sauvegarder avant de fermer ?"),
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                self.save_data()
                if self.is_modified:  # Si la sauvegarde a échoué
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
                
        event.accept()

    def reject(self):
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                self.tr("Modifications Non Sauvegardées"),
                self.tr("Vous avez des modifications non sauvegardées.\nÊtes-vous sûr de vouloir annuler ?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
                
        super().reject()


def main():
    """Fonction principale pour tester l'éditeur"""
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Données de test
    test_client_data = {
        "Nom du client": "Entreprise Test",
        "Besoin": "Analyse de données financières",
        "project_identifier": "PRJ-2024-001",
        "price": 2500
    }
    
    # Créer et afficher l'éditeur
    editor = ExcelEditor("test_document.xlsx", test_client_data)
    editor.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
