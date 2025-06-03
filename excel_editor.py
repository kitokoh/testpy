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
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

# Reportlab imports
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Enregistrer les polices pour Unicode
try:
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
except:
    # Fallback si les polices ne sont pas disponibles
    pass


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
        super().__init__("Informations Client")
        self.client_data = client_data or {}
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        layout = QFormLayout()
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        self.nom_client = QLineEdit()
        self.nom_client.setPlaceholderText("Nom du client")
        layout.addRow("Nom du client:", self.nom_client)
        
        self.besoin_client = QTextEdit()
        self.besoin_client.setMaximumHeight(80)
        self.besoin_client.setPlaceholderText("Description du besoin")
        layout.addRow("Besoin:", self.besoin_client)
        
        self.project_id = QLineEdit()
        self.project_id.setPlaceholderText("Identifiant du projet")
        layout.addRow("ID Projet:", self.project_id)
        
        self.price = QSpinBox()
        self.price.setRange(0, 99999999)
        self.price.setSuffix(" €")
        layout.addRow("Prix:", self.price)
        
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
        self.setHorizontalHeaderItem(current_cols, QTableWidgetItem(f"Colonne {current_cols + 1}"))
        
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
                fontName='Arial-Bold',
                fontSize=14,
                spaceAfter=12,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#2c3e50")
            )
            
            # Titre
            title_text = f"<u>Formulaire d'Offre</u>"
            elements.append(Paragraph(title_text, title_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Informations client dans un tableau
            client_info = [
                ['Client:', self.client_data.get('Nom du client', 'N/A')],
                ['Projet:', self.client_data.get('Besoin', 'N/A')],
                ['ID Projet:', self.client_data.get('project_identifier', 'N/A')],
                ['Prix Total:', f"{self.client_data.get('price', 0):,} €"],
                ['Date d\'émission:', datetime.now().strftime('%d/%m/%Y %H:%M')]
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
                fontName='Arial',
                fontSize=10,
                leading=14,
                spaceAfter=6
            )
            
            contact_text = (
                "<b>Personnel responsable:</b> Ramazan Demirci    "
                "<b>Tél:</b> +90 533 548 27 29    "
                "<b>Email:</b> bilgi@hidrogucpres.com"
            )
            elements.append(Paragraph(contact_text, contact_style))
            
            # Conditions d'achat
            elements.append(Spacer(1, 0.5*cm))
            elements.append(Paragraph("<b>Conditions d'achat:</b>", contact_style))
            
            conditions = [
                "1. Les offres seront présentées en livres turques (prioritairement) ou en devises étrangères, TVA comprise.",
                "2. Le délai de livraison de la presse est de dix jours calendaires à compter de la signature du contrat.",
                "3. Lieu de livraison du matériel : Hidroguç Konya Türkiye",
                "4. Le paiement sera effectué conformément au plan de paiement de Hidroguç, après la production du matériel.",
                "5. L’offre est valable pendant 30 jours calendaires.",
                "6. Ce produit est exonéré de TVA."
            ]
            
            for condition in conditions:
                elements.append(Paragraph(condition, contact_style))
            
            # Construction du PDF
            doc.build(elements)
            return True, "Export PDF réussi"
            
        except Exception as e:
            return False, f"Erreur lors de l'export PDF: {str(e)}"
    
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


# class ExcelEditor(QDialog):
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
        self.table_widget = None  # Initialisation de table_widget

        # Configuration du logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self._setup_ui()  # Assurez-vous que cette méthode est appelée en premier
        self._connect_signals()
        self._load_data()

    def _setup_ui(self):
        """Configuration de l'interface utilisateur"""
        self.setWindowTitle(f"Éditeur Excel - {os.path.basename(self.file_path)}")
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

        sheet_label = QLabel("Feuille:")
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
    def _load_data(self):
        """Charge les données à partir du fichier Excel."""
        try:
            self._update_status("Chargement des données...", "#3498db")
            self._show_progress(True)

            if not os.path.exists(self.file_path):
                self.logger.warning(f"Fichier inexistant: {self.file_path}")
                QMessageBox.warning(
                    self,
                    "Fichier Inexistant",
                    f"Le fichier {self.file_path} n'existe pas.\nUn nouveau fichier sera créé."
                )
                self._create_empty_table()
                self.workbook = Workbook()
                self.active_sheet = self.workbook.active
                self.sheet_combo.addItem(self.active_sheet.title)
                self._update_status("Nouveau fichier créé", "#27ae60")
                self._show_progress(False)
                return

            # Chargement du workbook
            self.workbook = load_workbook(self.file_path)

            if not self.workbook.sheetnames:
                self.logger.warning("Workbook sans feuilles")
                self._create_empty_table()
                self.active_sheet = self.workbook.create_sheet("Sheet1")
                self.sheet_combo.addItem(self.active_sheet.title)
                self._update_status("Fichier vide - nouvelle feuille créée", "#f39c12")
                self._show_progress(False)
                return

            # Remplir le combo des feuilles
            self.sheet_combo.clear()
            self.sheet_combo.addItems(self.workbook.sheetnames)

            # Charger la feuille active
            self.active_sheet = self.workbook.active
            self.sheet_combo.setCurrentText(self.active_sheet.title)
            self.load_sheet(self.active_sheet)

        except Exception as e:
            self.logger.error(f"Erreur lors du chargement: {e}")
            QMessageBox.critical(
                self,
                "Erreur de Chargement",
                f"Impossible de charger le fichier Excel:\n{str(e)}\n\nUn tableau vide sera créé."
            )
            self._create_empty_table()
            self.workbook = Workbook()
            self.active_sheet = self.workbook.active
            self.sheet_combo.addItem(self.active_sheet.title)
            self._update_status("Erreur - nouveau fichier créé", "#e74c3c")

        finally:
            self._show_progress(False)


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
