"""
Ultimate Excel Editor - Solution complète pour l'édition et l'export PDF de modèles Excel complexes
"""

import os
import sys
import logging
import tempfile
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

# Excel handling
import openpyxl
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, Fill, Alignment, Border, Side, PatternFill, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.utils.exceptions import InvalidFileException, ReadOnlyWorkbookException
import zipfile
from openpyxl.worksheet.page import PageMargins

# PDF export
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, letter
from reportlab.lib.units import cm, inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import Flowable

# Qt GUI
from PyQt5.QtWidgets import (
    QApplication, QDialog, QTableWidget, QTableWidgetItem, QMessageBox,
    QVBoxLayout, QHBoxLayout, QPushButton, QDialogButtonBox,
    QAbstractItemView, QHeaderView, QFileDialog, QProgressBar,
    QLabel, QFrame, QSplitter, QWidget, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QStyleFactory, QStyle, QSizePolicy, QScrollArea, QToolBar, QAction
)
from PyQt5.QtGui import (
    QFont, QColor, QIcon, QPalette, QBrush, QKeySequence,
    QTextDocument, QTextCursor, QTextCharFormat, QTextTableFormat,
    QTextLength, QSyntaxHighlighter, QTextFormat
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QCoreApplication, QSize,
    QRectF, QEvent, QObject, QFileInfo, QSettings
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
class PageOrientation(Enum):
    PORTRAIT = 1
    LANDSCAPE = 2

DEFAULT_FONT_NAME = "Arial"
MAX_ROWS_PREVIEW = 5000
MAX_COLS_PREVIEW = 100
PDF_DPI = 300
PDF_PAGE_MARGINS = 15 * mm
PDF_HEADER_HEIGHT = 15 * mm
PDF_FOOTER_HEIGHT = 10 * mm

@dataclass
class ExcelCellStyle:
    font_name: str = "Calibri"
    font_size: int = 11
    bold: bool = False
    italic: bool = False
    underline: bool = False
    text_color: str = "#000000"
    bg_color: str = "#FFFFFF"
    h_align: str = "left"
    v_align: str = "center"
    border: str = "none"
    wrap_text: bool = False
    number_format: str = "General"

@dataclass
class ClientData:
    name: str = ""
    company: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    project: str = ""
    project_id: str = ""
    price: float = 0.0
    currency: str = "€"
    notes: str = ""
    logo_path: str = ""

@dataclass
class PDFExportSettings:
    orientation: PageOrientation = PageOrientation.PORTRAIT
    page_size: Tuple[float, float] = A4
    margins: Tuple[float, float, float, float] = (PDF_PAGE_MARGINS, PDF_PAGE_MARGINS, PDF_PAGE_MARGINS, PDF_PAGE_MARGINS)
    header: bool = True
    footer: bool = True
    grid_lines: bool = True
    repeat_headers: bool = True
    watermark: str = ""
    quality: int = 100  # %

class ExcelTableModel:
    """Represents the complete Excel workbook model"""
    
    def __init__(self):
        self.file_path: Optional[str] = None
        self.workbook: Optional[Workbook] = None
        self.current_sheet: Optional[Worksheet] = None
        self.sheets: List[str] = []
        self.client_data: ClientData = ClientData()
        self.is_modified: bool = False
        self.load_error_message: Optional[str] = None
    
    def load_workbook(self, file_path: str):
        """Load workbook from file with maximum compatibility"""
        self.load_error_message = None
        self.workbook = None
        try:
            # Primary attempt: load with data_only=False to preserve styles
            logger.info(f"Attempting to load workbook (styles preserved): {file_path}")
            self.workbook = load_workbook(
                file_path,
                read_only=False,  # Try to open in read-write mode first
                keep_vba=True,
                data_only=False, # Crucial for style preservation
                keep_links=True
            )
            logger.info(f"Successfully loaded {file_path} with styles (read-write).")

        except (InvalidFileException, ReadOnlyWorkbookException, IOError, zipfile.BadZipFile) as e_rw:
            logger.warning(f"Read-write load attempt failed for {file_path} with {type(e_rw).__name__}: {e_rw}. Trying read-only.")
            try:
                # Fallback attempt: load with read_only=True if read-write fails
                logger.info(f"Attempting to load workbook (styles preserved, read-only): {file_path}")
                self.workbook = load_workbook(
                    file_path,
                    read_only=True,   # Fallback to read-only
                    keep_vba=True,
                    data_only=False, # Crucial for style preservation
                    keep_links=True
                )
                logger.info(f"Successfully loaded {file_path} with styles (read-only).")
            except (InvalidFileException, ReadOnlyWorkbookException, IOError, zipfile.BadZipFile) as e_ro:
                error_msg = f"Error loading workbook '{file_path}' (read-only attempt): {type(e_ro).__name__} - {str(e_ro)}"
                logger.error(error_msg)
                self.load_error_message = error_msg
                self.workbook = None
                return False
            except Exception as e_generic_ro: # Catch any other unexpected errors during read-only attempt
                error_msg = f"Unexpected error loading workbook '{file_path}' (read-only attempt): {type(e_generic_ro).__name__} - {str(e_generic_ro)}"
                logger.error(error_msg)
                self.load_error_message = error_msg
                self.workbook = None
                return False
        except Exception as e_generic_rw: # Catch any other unexpected errors during initial read-write attempt
            error_msg = f"Unexpected error loading workbook '{file_path}': {type(e_generic_rw).__name__} - {str(e_generic_rw)}"
            logger.error(error_msg)
            self.load_error_message = error_msg
            self.workbook = None
            return False

        # If workbook is loaded successfully by either method
        if self.workbook:
            self.file_path = file_path
            self.sheets = self.workbook.sheetnames
            self.current_sheet = self.workbook.active
            self.is_modified = False
            
            # Extract potential client data from sheet
            self.extract_client_data()
            
            return True

        # This part should ideally not be reached if logic is correct,
        # but as a safeguard:
        if not self.workbook:
            if not self.load_error_message: # Ensure an error message is set
                 self.load_error_message = f"Failed to load workbook '{file_path}' after multiple attempts."
            logger.error(self.load_error_message)
            return False

        return False # Should not be reached
    
    def extract_client_data(self):
        """Try to extract client data from common cell positions"""
        if not self.current_sheet:
            return
            
        # Common patterns for client data in templates
        patterns = {
            "name": ["client", "customer", "nom", "name"],
            "company": ["company", "société", "entreprise"],
            "project": ["project", "projet", "description"],
            "price": ["price", "prix", "cost", "montant"]
        }
        
        # Scan first row and column for potential matches
        for row in self.current_sheet.iter_rows(max_row=20):
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    lower_val = cell.value.lower()
                    # Check for name
                    if any(p in lower_val for p in patterns["name"]):
                        try:
                            self.client_data.name = str(self.current_sheet.cell(row=cell.row, column=cell.column+1).value)
                        except:
                            pass
                    # Check for company
                    elif any(p in lower_val for p in patterns["company"]):
                        try:
                            self.client_data.company = str(self.current_sheet.cell(row=cell.row, column=cell.column+1).value)
                        except:
                            pass
                    # Check for project
                    elif any(p in lower_val for p in patterns["project"]):
                        try:
                            self.client_data.project = str(self.current_sheet.cell(row=cell.row, column=cell.column+1).value)
                        except:
                            pass
                    # Check for price
                    elif any(p in lower_val for p in patterns["price"]):
                        try:
                            val = self.current_sheet.cell(row=cell.row, column=cell.column+1).value
                            if isinstance(val, (int, float)):
                                self.client_data.price = float(val)
                        except:
                            pass

class StyleConverter:
    """Handles conversion between Excel, Qt and PDF styles"""
    
    @staticmethod
    def excel_to_qt(excel_cell) -> ExcelCellStyle:
        """Convert Excel cell style to Qt compatible style"""
        style = ExcelCellStyle()
        
        if excel_cell.has_style:
            # Font properties
            if excel_cell.font:
                style.font_name = excel_cell.font.name or "Calibri"
                style.font_size = excel_cell.font.sz or 11
                style.bold = excel_cell.font.b
                style.italic = excel_cell.font.i
                style.underline = excel_cell.font.u
                if excel_cell.font.color and excel_cell.font.color.rgb:
                    style.text_color = f"#{str(excel_cell.font.color.rgb)[2:]}"
            
            # Background color
            if excel_cell.fill and excel_cell.fill.fgColor and excel_cell.fill.fgColor.rgb:
                style.bg_color = f"#{str(excel_cell.fill.fgColor.rgb)[2:]}"
            
            # Alignment
            if excel_cell.alignment:
                style.h_align = excel_cell.alignment.horizontal or "left"
                style.v_align = excel_cell.alignment.vertical or "center"
                style.wrap_text = excel_cell.alignment.wrapText
            
            # Number format
            style.number_format = excel_cell.number_format or "General"
        
        return style
    
    @staticmethod
    def qt_to_excel(qt_item, excel_cell):
        """Apply Qt item style to Excel cell"""
        if not qt_item or not excel_cell:
            return
            
        # Font
        font = Font(
            name=str(qt_item.font().family()),
            sz=qt_item.font().pointSize(),
            b=qt_item.font().bold(),
            i=qt_item.font().italic(),
            u=qt_item.font().underline(),
            color=StyleConverter.hex_to_excel_rgb(qt_item.foreground().color().name())
        )
        excel_cell.font = font
        
        # Background
        fill = PatternFill(
            start_color=StyleConverter.hex_to_excel_rgb(qt_item.background().color().name()),
            end_color=StyleConverter.hex_to_excel_rgb(qt_item.background().color().name()),
            fill_type="solid"
        )
        excel_cell.fill = fill
        
        # Alignment
        align = Alignment(
            horizontal=StyleConverter.qt_to_excel_alignment(qt_item.textAlignment()),
            vertical="center",
            wrap_text=True
        )
        excel_cell.alignment = align
    
    @staticmethod
    def hex_to_excel_rgb(hex_color: str) -> str:
        """Convert hex color to Excel RGB format"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c * 2 for c in hex_color])
        return f"00{hex_color[4:6]}{hex_color[2:4]}{hex_color[0:2]}"
    
    @staticmethod
    def qt_to_excel_alignment(qt_alignment: int) -> str:
        """Convert Qt alignment to Excel alignment string"""
        if qt_alignment & Qt.AlignLeft:
            return "left"
        elif qt_alignment & Qt.AlignRight:
            return "right"
        elif qt_alignment & Qt.AlignHCenter:
            return "center"
        elif qt_alignment & Qt.AlignJustify:
            return "justify"
        return "left"

class ExcelTableWidget(QTableWidget):
    """Enhanced QTableWidget with Excel-like features and style preservation"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.merged_cells = []
    
    def setup_ui(self):
        """Initialize table with Excel-like appearance"""
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.setAlternatingRowColors(False)
        self.setStyleSheet("""
            QTableWidget {
                background-color: white;
                gridline-color: #d0d0d0;
            }
            QTableWidget::item {
                padding: 3px;
            }
            QTableWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #d0d0d0;
            }
        """)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.verticalHeader().setDefaultSectionSize(24)
        self.verticalHeader().setVisible(False)
    
    def load_excel_sheet(self, worksheet: Worksheet):
        """Load Excel worksheet into the table while preserving all styles"""
        try:
            self.clear()
            self.setRowCount(min(worksheet.max_row, MAX_ROWS_PREVIEW))
            self.setColumnCount(min(worksheet.max_column, MAX_COLS_PREVIEW))
            
            # Load headers
            headers = []
            for col in range(1, self.columnCount() + 1):
                cell = worksheet.cell(row=1, column=col)
                headers.append(str(cell.value) if cell.value else f"Column {col}")
            self.setHorizontalHeaderLabels(headers)
            
            # Load data and styles
            for row in range(1, self.rowCount() + 1):
                for col in range(1, self.columnCount() + 1):
                    cell = worksheet.cell(row=row, column=col)
                    value = self.format_cell_value(cell.value)
                    
                    item = QTableWidgetItem(value)
                    self.apply_excel_style(cell, item)
                    self.setItem(row - 1, col - 1, item)
            
            # Handle merged cells
            self.merged_cells = []
            for merge_range in worksheet.merged_cells.ranges:
                self.setSpan(
                    merge_range.min_row - 1,
                    merge_range.min_col - 1,
                    merge_range.max_row - merge_range.min_row + 1,
                    merge_range.max_col - merge_range.min_col + 1
                )
                self.merged_cells.append((
                    merge_range.min_row - 1,
                    merge_range.min_col - 1,
                    merge_range.max_row - merge_range.min_row + 1,
                    merge_range.max_col - merge_range.min_col + 1
                ))
            
            self.resizeColumnsToContents()
            return True
            
        except Exception as e:
            logger.error(f"Error loading Excel sheet: {str(e)}")
            return False
    
    def apply_excel_style(self, excel_cell, qt_item):
        """Apply Excel cell style to QTableWidgetItem"""
        style = StyleConverter.excel_to_qt(excel_cell)
        
        # Font
        font = QFont(style.font_name, style.font_size)
        font.setBold(style.bold)
        font.setItalic(style.italic)
        font.setUnderline(style.underline)
        qt_item.setFont(font)
        
        # Colors
        qt_item.setForeground(QColor(style.text_color))
        qt_item.setBackground(QColor(style.bg_color))
        
        # Alignment
        alignment = 0
        if style.h_align == "left":
            alignment |= Qt.AlignLeft
        elif style.h_align == "right":
            alignment |= Qt.AlignRight
        elif style.h_align == "center":
            alignment |= Qt.AlignHCenter
        elif style.h_align == "justify":
            alignment |= Qt.AlignJustify
            
        if style.v_align == "top":
            alignment |= Qt.AlignTop
        elif style.v_align == "center":
            alignment |= Qt.AlignVCenter
        elif style.v_align == "bottom":
            alignment |= Qt.AlignBottom
            
        qt_item.setTextAlignment(alignment)
    
    def format_cell_value(self, value) -> str:
        """Format cell value for display"""
        if value is None:
            return ""
            
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y %H:%M")
        if isinstance(value, (int, float)):
            return f"{value:,}"
            
        return str(value)

class PDFGenerator:
    """Handles high-quality PDF export with modern styling"""
    
    def __init__(self, table: ExcelTableWidget, client_data: ClientData, settings: PDFExportSettings):
        self.table = table
        self.client_data = client_data
        self.settings = settings
        self.styles = getSampleStyleSheet()
        
        # Register fonts
        self.register_fonts()
        
        # Create custom styles
        self.create_styles()
    
    def register_fonts(self):
        """Register fonts for PDF generation"""
        try:
            # Try to register Arial
            pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Italic', 'ariali.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-BoldItalic', 'arialbi.ttf'))
        except:
            # Fallback to default fonts
            pass
    
    def create_styles(self):
        """Create custom PDF styles"""
        # Title style
        self.title_style = ParagraphStyle(
            'Title',
            parent=self.styles['Heading1'],
            fontName='Arial-Bold',
            fontSize=16,
            leading=18,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2c3e50')
        )
        
        # Client info style
        self.client_style = ParagraphStyle(
            'Client',
            parent=self.styles['BodyText'],
            fontName='Arial',
            fontSize=10,
            leading=12,
            spaceAfter=6,
            textColor=colors.HexColor('#34495e')
        )
        
        # Table header style
        self.table_header_style = ParagraphStyle(
            'TableHeader',
            parent=self.styles['BodyText'],
            fontName='Arial-Bold',
            fontSize=9,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.white,
            backColor=colors.HexColor('#3498db')
        )
        
        # Table cell style
        self.table_cell_style = ParagraphStyle(
            'TableCell',
            parent=self.styles['BodyText'],
            fontName='Arial',
            fontSize=8,
            leading=9,
            textColor=colors.black
        )
        
        # Footer style
        self.footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['BodyText'],
            fontName='Arial',
            fontSize=8,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#7f8c8d')
        )
    
    def generate(self, file_path: str) -> Tuple[bool, str]:
        """Generate PDF document"""
        try:
            # Create document
            doc = SimpleDocTemplate(
                file_path,
                pagesize=self.settings.page_size,
                leftMargin=self.settings.margins[0],
                rightMargin=self.settings.margins[1],
                topMargin=self.settings.margins[2],
                bottomMargin=self.settings.margins[3]
            )
            
            elements = []
            
            # Add header
            if self.settings.header:
                elements.extend(self.create_header())
            
            # Add title
            elements.append(Paragraph(
                f"<u>Devis {self.client_data.project_id}</u>" if self.client_data.project_id else "<u>Devis</u>",
                self.title_style
            ))
            elements.append(Spacer(1, 12))
            
            # Add client info
            elements.extend(self.create_client_info())
            elements.append(Spacer(1, 15))
            
            # Add main table
            table_data, col_widths = self.prepare_table_data()
            if table_data:
                main_table = Table(
                    table_data,
                    colWidths=col_widths,
                    repeatRows=1 if self.settings.repeat_headers else 0
                )
                main_table.setStyle(self.create_table_style(len(table_data), len(table_data[0])))
                elements.append(main_table)
            else:
                return False, "No table data to export"
            
            # Add footer
            if self.settings.footer:
                elements.append(Spacer(1, 10))
                elements.extend(self.create_footer())
            
            # Build document
            doc.build(
                elements,
                onFirstPage=self.add_page_decorations,
                onLaterPages=self.add_page_decorations
            )
            
            return True, "PDF generated successfully"
            
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            return False, str(e)
    
    def create_header(self) -> List[Flowable]:
        """Create document header with logo and info"""
        header_elements = []
        
        # Create table for header
        header_table = Table([
            [
                self.create_company_info(),
                self.create_document_info()
            ]
        ], colWidths=['70%', '30%'])
        
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('RIGHTPADDING', (1, 0), (1, 0), 0)
        ]))
        
        header_elements.append(header_table)
        header_elements.append(Spacer(1, 10))
        
        return header_elements
    
    def create_company_info(self) -> Paragraph:
        """Create company info paragraph"""
        company_info = [
            f"<b>{self.client_data.company or 'Société'}</b>",
            self.client_data.address or "Adresse",
            f"Tél: {self.client_data.phone or 'N/A'}",
            f"Email: {self.client_data.email or 'N/A'}"
        ]
        return Paragraph("<br/>".join(company_info), self.client_style)
    
    def create_document_info(self) -> Paragraph:
        """Create document info paragraph"""
        doc_info = [
            f"<b>Devis N° {self.client_data.project_id or 'XXXX'}</b>",
            f"Date: {datetime.now().strftime('%d/%m/%Y')}",
            f"Client: {self.client_data.name or 'N/A'}"
        ]
        return Paragraph("<br/>".join(doc_info), self.client_style)
    
    def create_client_info(self) -> List[Flowable]:
        """Create client info section"""
        client_elements = []
        
        client_table = Table([
            ["Client:", self.client_data.name or "N/A"],
            ["Société:", self.client_data.company or "N/A"],
            ["Projet:", self.client_data.project or "N/A"],
            ["Date:", datetime.now().strftime("%d/%m/%Y")],
            ["Prix Total:", f"{self.client_data.price:,.2f} {self.client_data.currency}"]
        ], colWidths=[3*cm, 10*cm])
        
        client_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f8f9fa")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Arial-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4)
        ]))
        
        client_elements.append(client_table)
        return client_elements
    
    def prepare_table_data(self) -> Tuple[List[List[Union[str, Paragraph]]], List[float]]:
        """Prepare table data for PDF export"""
        rows = min(self.table.rowCount(), MAX_ROWS_PREVIEW)
        cols = min(self.table.columnCount(), MAX_COLS_PREVIEW)
        
        # Prepare data matrix
        data = []
        col_widths = []
        
        # Add headers
        headers = []
        for col in range(cols):
            header = self.table.horizontalHeaderItem(col)
            header_text = header.text() if header else f"Colonne {col+1}"
            headers.append(Paragraph(header_text, self.table_header_style))
            col_widths.append(self.table.columnWidth(col) / 10)  # Convert to mm
        
        data.append(headers)
        
        # Add table data
        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = self.table.item(row, col)
                if item:
                    # Create paragraph with cell style
                    cell_style = self.table_cell_style.clone('TableCell')
                    
                    # Apply text color
                    text_color = item.foreground().color().name()
                    if text_color != "#000000":
                        cell_style.textColor = colors.HexColor(text_color)
                    
                    # Apply alignment
                    align = item.textAlignment()
                    if align & Qt.AlignLeft:
                        cell_style.alignment = TA_LEFT
                    elif align & Qt.AlignRight:
                        cell_style.alignment = TA_RIGHT
                    elif align & Qt.AlignHCenter:
                        cell_style.alignment = TA_CENTER
                    elif align & Qt.AlignJustify:
                        cell_style.alignment = TA_JUSTIFY
                    
                    row_data.append(Paragraph(item.text(), cell_style))
                else:
                    row_data.append("")
            data.append(row_data)
        
        return data, col_widths
    
    def create_table_style(self, rows: int, cols: int) -> TableStyle:
        """Create table style with modern look"""
        style = TableStyle([
            # Basic table styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3498db")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Arial-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            
            # Grid lines
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), 
             [colors.white, colors.HexColor("#f8f9fa")]),
            
            # Cell padding
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ])
        
        # Add cell-specific styles
        for row in range(rows):
            for col in range(cols):
                if row >= self.table.rowCount() or col >= self.table.columnCount():
                    continue
                    
                item = self.table.item(row, col)
                if item:
                    # Background color
                    bg_color = item.background().color().name()
                    if bg_color != "#ffffff":
                        style.add('BACKGROUND', (col, row), (col, row), colors.HexColor(bg_color))
                    
                    # Handle merged cells
                    row_span = self.table.rowSpan(row, col)
                    col_span = self.table.columnSpan(row, col)
                    if row_span > 1 or col_span > 1:
                        style.add('SPAN', (col, row), (col + col_span - 1, row + row_span - 1))
        
        return style
    
    def create_footer(self) -> List[Flowable]:
        """Create document footer"""
        footer_elements = []
        
        # Add notes if available
        if self.client_data.notes:
            notes = Paragraph(
                f"<b>Notes:</b><br/>{self.client_data.notes}",
                ParagraphStyle(
                    'Notes',
                    parent=self.styles['BodyText'],
                    fontName='Arial',
                    fontSize=8,
                    leading=9,
                    textColor=colors.HexColor("#7f8c8d")
                )
            )
            footer_elements.append(notes)
            footer_elements.append(Spacer(1, 10))
        
        # Add footer text
        footer_text = Paragraph(
            f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | {self.client_data.company or 'Société'}",
            self.footer_style
        )
        footer_elements.append(footer_text)
        
        return footer_elements
    
    def add_page_decorations(self, canvas: canvas.Canvas, doc):
        """Add page decorations (watermark, page numbers, etc.)"""
        # Add watermark if specified
        if self.settings.watermark:
            canvas.saveState()
            canvas.setFont('Arial', 60)
            canvas.setFillColor(colors.HexColor("#f0f0f0"))
            canvas.rotate(45)
            canvas.drawString(10 * cm, -2 * cm, self.settings.watermark)
            canvas.restoreState()
        
        # Add page number
        page_num = canvas.getPageNumber()
        canvas.setFont('Arial', 8)
        canvas.setFillColor(colors.HexColor("#7f8c8d"))
        canvas.drawRightString(
            doc.width + doc.leftMargin,
            doc.bottomMargin / 2,
            f"Page {page_num}"
        )

class ExcelEditor(QDialog):
    """Main Excel editor application with modern UI"""
    
    def __init__(self, file_path: str = "", parent=None):
        super().__init__(parent)
        self.file_path: Optional[str] = file_path if file_path else None # Store initial file path
        self.excel_model = ExcelTableModel() # Instantiate without file_path
        self.pdf_settings = PDFExportSettings()
        
        self.setup_ui() # Creates self.table, self.sheet_combo, self.file_label etc.
        self.setup_connections()
        
        if self.file_path: # If a file_path was provided to constructor
            self.load_file(self.file_path)
    
    def setup_ui(self):
        """Initialize the main UI"""
        self.setWindowTitle("Ultimate Excel Editor")
        self.setMinimumSize(1280, 800)
        self.resize(1366, 768)
        
        # Apply modern style
        self.setStyle(QStyleFactory.create("Fusion"))
        
        # Dark palette for modern look
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Create toolbar
        self.create_toolbar(main_layout)
        
        # Create status bar
        self.create_status_bar(main_layout)
        
        # Main content area
        content_splitter = QSplitter(Qt.Horizontal)
        
        # Client info panel
        self.client_panel = self.create_client_panel()
        content_splitter.addWidget(self.client_panel)
        
        # Excel table panel
        self.table_panel = self.create_table_panel()
        content_splitter.addWidget(self.table_panel)
        
        # PDF preview panel (optional)
        # self.preview_panel = self.create_preview_panel()
        # content_splitter.addWidget(self.preview_panel)
        
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 3)
        # content_splitter.setStretchFactor(2, 1)
        
        main_layout.addWidget(content_splitter)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
    
    def create_toolbar(self, parent_layout):
        """Create main application toolbar"""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.setMovable(False)
        
        # File actions
        open_action = QAction(QIcon.fromTheme("document-open"), "Open", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file_dialog)
        toolbar.addAction(open_action)
        
        save_action = QAction(QIcon.fromTheme("document-save"), "Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # PDF export
        pdf_action = QAction(QIcon.fromTheme("document-export"), "Export PDF", self)
        pdf_action.setShortcut("Ctrl+E")
        pdf_action.triggered.connect(self.export_pdf)
        toolbar.addAction(pdf_action)
        
        # Settings
        settings_action = QAction(QIcon.fromTheme("configure"), "Settings", self)
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)
        
        toolbar.addSeparator()
        
        # Table actions
        add_row_action = QAction(QIcon.fromTheme("list-add"), "Add Row", self)
        add_row_action.triggered.connect(self.table.add_row)
        toolbar.addAction(add_row_action)
        
        add_col_action = QAction(QIcon.fromTheme("list-add"), "Add Column", self)
        add_col_action.triggered.connect(self.table.add_column)
        toolbar.addAction(add_col_action)
        
        del_row_action = QAction(QIcon.fromTheme("list-remove"), "Delete Row", self)
        del_row_action.triggered.connect(self.table.delete_selected_rows)
        toolbar.addAction(del_row_action)
        
        del_col_action = QAction(QIcon.fromTheme("list-remove"), "Delete Column", self)
        del_col_action.triggered.connect(self.table.delete_selected_columns)
        toolbar.addAction(del_col_action)
        
        parent_layout.addWidget(toolbar)
    
    def create_status_bar(self, parent_layout):
        """Create status bar at bottom of window"""
        status_bar = QFrame()
        status_bar.setFrameShape(QFrame.StyledPanel)
        status_bar.setStyleSheet("background-color: #3a3a3a; border-top: 1px solid #505050;")
        status_bar.setFixedHeight(30)
        
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(10, 0, 10, 0)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #aaaaaa;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        self.file_label = QLabel("No file loaded")
        self.file_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        layout.addWidget(self.file_label)
        
        parent_layout.addWidget(status_bar)
    
    def create_client_panel(self) -> QWidget:
        """Create panel for client information"""
        panel = QGroupBox("Client Information")
        panel.setMaximumWidth(350)
        
        layout = QFormLayout(panel)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        # Client name
        self.client_name = QLineEdit()
        self.client_name.setPlaceholderText("Client name")
        layout.addRow("Name:", self.client_name)
        
        # Company
        self.client_company = QLineEdit()
        self.client_company.setPlaceholderText("Company name")
        layout.addRow("Company:", self.client_company)
        
        # Address
        self.client_address = QTextEdit()
        self.client_address.setMaximumHeight(60)
        self.client_address.setPlaceholderText("Address")
        layout.addRow("Address:", self.client_address)
        
        # Contact info
        contact_layout = QHBoxLayout()
        self.client_phone = QLineEdit()
        self.client_phone.setPlaceholderText("Phone")
        contact_layout.addWidget(self.client_phone)
        
        self.client_email = QLineEdit()
        self.client_email.setPlaceholderText("Email")
        contact_layout.addWidget(self.client_email)
        
        layout.addRow("Contact:", contact_layout)
        
        # Project info
        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("Project name")
        layout.addRow("Project:", self.project_name)
        
        self.project_id = QLineEdit()
        self.project_id.setPlaceholderText("Project ID")
        layout.addRow("Project ID:", self.project_id)
        
        # Price
        price_layout = QHBoxLayout()
        self.project_price = QDoubleSpinBox()
        self.project_price.setRange(0, 99999999)
        self.project_price.setPrefix("€ ")
        price_layout.addWidget(self.project_price)
        
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["€", "$", "£", "¥", "₺"])
        price_layout.addWidget(self.currency_combo)
        
        layout.addRow("Price:", price_layout)
        
        # Notes
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(80)
        self.notes.setPlaceholderText("Additional notes")
        layout.addRow("Notes:", self.notes)
        
        # Logo
        self.logo_button = QPushButton("Select Logo...")
        self.logo_button.clicked.connect(self.select_logo)
        layout.addRow("Logo:", self.logo_button)
        
        return panel
    
    def create_table_panel(self) -> QWidget:
        """Create panel for Excel table editing"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Sheet selector
        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumWidth(200)
        layout.addWidget(self.sheet_combo)
        
        # Table widget
        self.table = ExcelTableWidget()
        layout.addWidget(self.table)
        
        return panel
    
    def setup_connections(self):
        """Setup signal connections between UI elements"""
        # Client data changes
        self.client_name.textChanged.connect(self.update_client_data)
        self.client_company.textChanged.connect(self.update_client_data)
        self.client_address.textChanged.connect(self.update_client_data)
        self.client_phone.textChanged.connect(self.update_client_data)
        self.client_email.textChanged.connect(self.update_client_data)
        self.project_name.textChanged.connect(self.update_client_data)
        self.project_id.textChanged.connect(self.update_client_data)
        self.project_price.valueChanged.connect(self.update_client_data)
        self.currency_combo.currentTextChanged.connect(self.update_client_data)
        self.notes.textChanged.connect(self.update_client_data)
        
        # Sheet selection
        self.sheet_combo.currentTextChanged.connect(self.change_sheet)
        
        # Table changes
        self.table.itemChanged.connect(self.mark_as_modified)
    
    def load_file(self, file_path: str):
        """Load Excel file into editor, updating model and UI."""
        self.set_progress(True, f"Loading file: {QFileInfo(file_path).fileName()}...")

        if self.excel_model.load_workbook(file_path):
            # Success case
            self.file_path = file_path # Update editor's current file_path
            self.file_label.setText(QFileInfo(file_path).fileName())
            
            self.sheet_combo.clear()
            self.sheet_combo.addItems(self.excel_model.sheets)
            
            self.load_client_data() # Populates UI from self.excel_model.client_data
            
            if self.excel_model.current_sheet:
                self.table.load_excel_sheet(self.excel_model.current_sheet)
            else:
                self.table.clearContents() # Clear table if no sheet is active
                self.table.setRowCount(0)
                self.table.setColumnCount(0)

            self.set_progress(False)
            self.update_status("File loaded successfully")
            logger.info(f"Successfully loaded and UI updated for: {file_path}")
            return True
        else:
            # Failure case
            error_msg = self.excel_model.load_error_message or f"Unknown error loading file: {file_path}"
            QMessageBox.critical(self, "Error Loading File", error_msg)
            
            self.file_path = None # Clear current file path
            self.file_label.setText("No file loaded")
            self.sheet_combo.clear()
            self.table.clearContents()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            # Clear client data fields in UI as well
            self.client_name.clear()
            self.client_company.clear()
            self.client_address.clear()
            self.client_phone.clear()
            self.client_email.clear()
            self.project_name.clear()
            self.project_id.clear()
            self.project_price.setValue(0)
            self.notes.clear()

            self.set_progress(False)
            self.update_status("Failed to load file", "red")
            logger.error(f"Failed to load and update UI for: {file_path}")
            return False
    
    def load_client_data(self):
        """Load client data into UI"""
        client = self.excel_model.client_data
        self.client_name.setText(client.name)
        self.client_company.setText(client.company)
        self.client_address.setPlainText(client.address)
        self.client_phone.setText(client.phone)
        self.client_email.setText(client.email)
        self.project_name.setText(client.project)
        self.project_id.setText(client.project_id)
        self.project_price.setValue(client.price)
        self.currency_combo.setCurrentText(client.currency)
        self.notes.setPlainText(client.notes)
    
    def update_client_data(self):
        """Update client data model from UI"""
        self.excel_model.client_data = ClientData(
            name=self.client_name.text(),
            company=self.client_company.text(),
            address=self.client_address.toPlainText(),
            phone=self.client_phone.text(),
            email=self.client_email.text(),
            project=self.project_name.text(),
            project_id=self.project_id.text(),
            price=self.project_price.value(),
            currency=self.currency_combo.currentText(),
            notes=self.notes.toPlainText(),
            logo_path=self.excel_model.client_data.logo_path
        )
        self.mark_as_modified()
    
    def mark_as_modified(self):
        """Mark document as modified"""
        self.excel_model.is_modified = True
        self.update_status("Modified", "orange")
    
    def update_status(self, message: str, color: str = "green"):
        """Update status bar message"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color};")
    
    def set_progress(self, visible: bool, message: str = ""):
        """Show/hide progress bar"""
        self.progress_bar.setVisible(visible)
        if visible:
            self.progress_bar.setRange(0, 0)
            self.update_status(message, "blue")
        else:
            self.progress_bar.setRange(0, 1)
    
    def open_file_dialog(self):
        """Open file dialog to select Excel file"""
        if self.excel_model.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Save before opening new file?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                if not self.save_file():
                    return
            elif reply == QMessageBox.Cancel:
                return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Excel File",
            "",
            "Excel Files (*.xlsx *.xls *.xlsm);;All Files (*)"
        )
        
        if file_path:
            self.load_file(file_path)
    
    def save_file(self) -> bool:
        """Save current file"""
        try:
            if not self.file_path:
                return self.save_file_as()
            
            self.set_progress(True, "Saving file...")
            
            # Update client data
            self.update_client_data()
            
            # Save workbook
            self.excel_model.workbook.save(self.file_path)
            self.excel_model.is_modified = False
            
            self.set_progress(False)
            self.update_status("File saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error saving file:\n{str(e)}")
            self.set_progress(False)
            return False
    
    def save_file_as(self) -> bool:
        """Save file with new name"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Excel File",
            "",
            "Excel Files (*.xlsx);;All Files (*)"
        )
        
        if file_path:
            self.file_path = file_path
            self.file_label.setText(QFileInfo(file_path).fileName())
            return self.save_file()
        return False
    
    def change_sheet(self, sheet_name: str):
        """Change current worksheet"""
        if not sheet_name or not self.excel_model.workbook:
            return
            
        if self.excel_model.current_sheet and sheet_name == self.excel_model.current_sheet.title:
            return
            
        # Check for unsaved changes
        if self.excel_model.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Save before switching sheets?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                if not self.save_file():
                    return
            elif reply == QMessageBox.Cancel:
                self.sheet_combo.setCurrentText(self.excel_model.current_sheet.title)
                return
        
        # Load new sheet
        try:
            self.set_progress(True, f"Loading sheet: {sheet_name}")
            
            self.excel_model.current_sheet = self.excel_model.workbook[sheet_name]
            self.table.load_excel_sheet(self.excel_model.current_sheet)
            
            self.set_progress(False)
            self.update_status(f"Sheet '{sheet_name}' loaded")
            
        except Exception as e:
            logger.error(f"Error changing sheet: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error loading sheet:\n{str(e)}")
            self.set_progress(False)
    
    def export_pdf(self):
        """Export current sheet to PDF"""
        if not self.file_path:
            QMessageBox.warning(self, "Warning", "No file loaded to export")
            return
            
        # Update client data
        self.update_client_data()
        
        # Get save path
        default_name = f"{Path(self.file_path).stem}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export PDF",
            default_name,
            "PDF Files (*.pdf);;All Files (*)"
        )
        
        if not save_path:
            return
            
        try:
            self.set_progress(True, "Exporting to PDF...")
            
            # Create PDF generator
            pdf_gen = PDFGenerator(self.table, self.excel_model.client_data, self.pdf_settings)
            
            # Generate PDF
            success, message = pdf_gen.generate(save_path)
            
            if success:
                self.set_progress(False)
                self.update_status("PDF exported successfully")
                
                # Ask to open PDF
                reply = QMessageBox.question(
                    self,
                    "Export Complete",
                    f"PDF created successfully:\n{save_path}\n\nOpen now?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.open_file(save_path)
            else:
                self.set_progress(False)
                QMessageBox.critical(self, "Export Error", f"Error exporting PDF:\n{message}")
            
        except Exception as e:
            logger.error(f"Error exporting PDF: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error exporting PDF:\n{str(e)}")
            self.set_progress(False)
    
    def select_logo(self):
        """Select logo image for PDF header"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Logo Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        
        if file_path:
            self.excel_model.client_data.logo_path = file_path
            self.mark_as_modified()
    
    def show_settings(self):
        """Show PDF export settings dialog"""
        # Implementation would go here
        QMessageBox.information(self, "Settings", "PDF export settings will be available in the next version")
    
    def open_file(self, file_path: str):
        """Open file with default application"""
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                os.system(f'open "{file_path}"')
            else:
                os.system(f'xdg-open "{file_path}"')
        except Exception as e:
            logger.error(f"Could not open file: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Could not open file:\n{str(e)}")

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application style and properties
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setApplicationName("Ultimate Excel Editor")
    app.setApplicationVersion("1.0")
    app.setWindowIcon(QIcon.fromTheme("x-office-spreadsheet"))
    
    # Create and show main window
    editor = ExcelEditor()
    editor.show()
    
    # Open file if specified as argument
    if len(sys.argv) > 1:
        editor.load_file(sys.argv[1])
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
