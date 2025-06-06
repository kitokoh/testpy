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
from openpyxl.utils import get_column_letter, column_index_from_string
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.drawing.image import Image as OpenpyxlImage
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
import io
from reportlab.lib.utils import ImageReader

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PageOrientation(Enum): PORTRAIT = 1; LANDSCAPE = 2
DEFAULT_FONT_NAME = "Arial"
MAX_ROWS_PREVIEW, MAX_COLS_PREVIEW = 5000, 100
PDF_DPI, PDF_PAGE_MARGINS = 300, 15 * mm
PDF_HEADER_HEIGHT, PDF_FOOTER_HEIGHT = 15 * mm, 10 * mm
HF_SECTION_PADDING = 2 * mm
DEFAULT_HF_FONT_SIZE = 9
PDF_HEADER_IMAGE_MAX_WIDTH, PDF_FOOTER_IMAGE_MAX_WIDTH = 1.5 * inch, 1.5 * inch
PDF_HEADER_IMAGE_MAX_HEIGHT_FACTOR, PDF_FOOTER_IMAGE_MAX_HEIGHT_FACTOR = 0.85, 0.85

@dataclass
class ExcelCellStyle:
    font_name: str = "Calibri"; font_size: int = 11; bold: bool = False; italic: bool = False
    underline: bool = False; text_color: str = "#000000"; bg_color: str = "#FFFFFF"
    h_align: str = "left"; v_align: str = "center"; wrap_text: bool = False
    number_format: str = "General"; border_left_style: Optional[str] = None
    border_left_color: Optional[str] = None; border_right_style: Optional[str] = None
    border_right_color: Optional[str] = None; border_top_style: Optional[str] = None
    border_top_color: Optional[str] = None; border_bottom_style: Optional[str] = None
    border_bottom_color: Optional[str] = None; fill_pattern_type: Optional[str] = None

@dataclass
class ClientData:
    name: str = ""; company: str = ""; address: str = ""; phone: str = ""; email: str = ""
    project: str = ""; project_id: str = ""; price: float = 0.0; currency: str = "€"
    notes: str = ""; logo_path: str = ""

@dataclass
class PDFExportSettings:
    orientation: PageOrientation = PageOrientation.PORTRAIT; page_size: Tuple[float, float] = A4
    margins: Tuple[float,float,float,float] = (PDF_PAGE_MARGINS,)*4; header: bool = True
    footer: bool = True; grid_lines: bool = True; repeat_headers: bool = True
    watermark: str = ""; quality: int = 100

class ExcelTableModel:
    def __init__(self):
        self.file_path: Optional[str] = None; self.workbook: Optional[Workbook] = None
        self.current_sheet: Optional[Worksheet] = None; self.sheets: List[str] = []
        self.client_data: ClientData = ClientData(); self.is_modified: bool = False
        self.load_error_message: Optional[str] = None
        self.sheet_images: Dict[str, List[bytes]] = {}
        self.sheet_headers_footers: Dict[str, Dict[str, Dict[str, Dict[str, Optional[Union[str, bytes]]]]]] = {}
    
    def load_workbook(self, file_path: str):
        self.load_error_message = None; self.workbook = None
        try:
            logger.info(f"Attempting to load workbook (styles preserved): {file_path}")
            self.workbook = load_workbook(file_path, read_only=False, keep_vba=True, data_only=False, keep_links=True)
            logger.info(f"Successfully loaded {file_path} with styles (read-write).")
        except Exception:
            try:
                logger.info(f"Attempting to load workbook (styles preserved, read-only): {file_path}")
                self.workbook = load_workbook(file_path, read_only=True, keep_vba=True, data_only=False, keep_links=True)
                logger.info(f"Successfully loaded {file_path} with styles (read-only).")
            except Exception as e_ro:
                self.load_error_message = f"Error loading workbook '{file_path}' (read-only attempt): {type(e_ro).__name__} - {str(e_ro)}"
                logger.error(self.load_error_message); self.workbook = None; return False
        if not self.workbook: return False
        self.file_path = file_path; self.sheets = self.workbook.sheetnames; self.current_sheet = self.workbook.active
        self.is_modified = False; self.sheet_images.clear(); self.sheet_headers_footers.clear()
        for sheet in self.workbook.worksheets:
            if sheet._images:
                image_bytes_list = []
                for img_idx, img_obj_excel in enumerate(sheet._images):
                    try: image_bytes_list.append(img_obj_excel._data())
                    except Exception as e_img_data: logger.error(f"Could not extract data for sheet image {img_idx} on sheet '{sheet.title}': {e_img_data}")
                if image_bytes_list: self.sheet_images[sheet.title] = image_bytes_list; logger.info(f"Stored {len(image_bytes_list)} image(s) data for sheet '{sheet.title}'.")
                else: logger.info(f"No image data could be extracted from images on sheet '{sheet.title}'.")
            else: logger.info(f"No image objects found on sheet '{sheet.title}'.")
            hf_data_sheet = {}
            if sheet.HeaderFooter:
                hf_obj_main = sheet.HeaderFooter
                hf_types = {"odd_header": hf_obj_main.oddHeader, "even_header": hf_obj_main.evenHeader, "first_header": hf_obj_main.firstHeader, "odd_footer": hf_obj_main.oddFooter, "even_footer": hf_obj_main.evenFooter, "first_footer": hf_obj_main.firstFooter}
                for hf_type, hf_member_obj in hf_types.items():
                    if hf_member_obj:
                        current_hf_parts = {}
                        for part_key_str, hf_item_obj_ref_func in [("left", lambda: hf_member_obj.left), ("center", lambda: hf_member_obj.center), ("right", lambda: hf_member_obj.right)]:
                            hf_item_obj = hf_item_obj_ref_func()
                            text_val = hf_item_obj.text if hf_item_obj else None
                            img_bytes_val = None
                            if hf_item_obj and hasattr(hf_item_obj, 'img') and isinstance(hf_item_obj.img, OpenpyxlImage):
                                try: img_bytes_val = hf_item_obj.img._data(); logger.info(f"  Extracted direct image data from {hf_type} {part_key_str.upper()} for sheet '{sheet.title}'.")
                                except Exception as e_img: logger.error(f"  Error extracting direct image data from {hf_type} {part_key_str.upper()}: {e_img}")
                            current_hf_parts[part_key_str] = {"text": text_val, "image_data": img_bytes_val}
                        hf_data_sheet[hf_type] = current_hf_parts
                        log_msg = f"Extracted {hf_type} for sheet '{sheet.title}':"
                        for pk_log in ["left", "center", "right"]:
                            txt_log = current_hf_parts[pk_log]["text"]; img_log = current_hf_parts[pk_log]["image_data"]
                            if txt_log or img_log: log_msg += f" {pk_log.upper()}(txt='{txt_log}', img={'yes' if img_log else 'no'})"
                        logger.info(log_msg)
                        for pk_log in ["left", "center", "right"]:
                            txt_log = current_hf_parts[pk_log]["text"]
                            if txt_log and "&G" in txt_log: logger.info(f"  Found text image reference (&G) in {hf_type} {pk_log} for sheet '{sheet.title}'.")
            if hf_data_sheet: self.sheet_headers_footers[sheet.title] = hf_data_sheet
            else: logger.info(f"No header/footer data found for sheet '{sheet.title}'.")
        self.extract_client_data(); return True
    def extract_client_data(self):
        if not self.current_sheet: return
        patterns = {"name": ["client", "customer", "nom", "name"], "company": ["company", "société", "entreprise"], "project": ["project", "projet", "description"], "price": ["price", "prix", "cost", "montant"]}
        for r, row in enumerate(self.current_sheet.iter_rows(max_row=20)):
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    lv = cell.value.lower()
                    for key, p_list in patterns.items():
                        if any(p in lv for p in p_list):
                            try:
                                val_cell = self.current_sheet.cell(row=cell.row, column=cell.column+1)
                                if key == "price" and isinstance(val_cell.value, (int, float)): setattr(self.client_data, key, float(val_cell.value))
                                elif key != "price": setattr(self.client_data, key, str(val_cell.value))
                            except: pass

class StyleConverter:
    @staticmethod
    def excel_to_qt(excel_cell) -> ExcelCellStyle:
        style = ExcelCellStyle(font_name="Arial", bg_color="#FFFFFF", text_color="#000000")

        def get_safe_hex_color(color_obj_rgb, default_color_hex_no_hash="000000"):
            if color_obj_rgb and isinstance(color_obj_rgb, str):
                # Basic check for hex characters, can be improved
                is_hex_candidate = all(c in '0123456789abcdefABCDEF' for c in color_obj_rgb)
                if is_hex_candidate:
                    if len(color_obj_rgb) == 8: # AARRGGBB
                        return f"#{color_obj_rgb[2:]}"
                    elif len(color_obj_rgb) == 6: # RRGGBB
                        return f"#{color_obj_rgb}"
                    # Potentially handle other valid lengths if necessary, e.g. 3-char hex
                    # else: logger.warning(f"Unexpected hex string length: {color_obj_rgb}")
            # logger.warning(f"Invalid or non-string color RGB value '{color_obj_rgb}', defaulting.")
            return f"#{default_color_hex_no_hash}"

        if excel_cell.has_style:
            if excel_cell.font:
                style.font_name = excel_cell.font.name or "Arial"
                style.font_size = excel_cell.font.sz or 11; style.bold = excel_cell.font.b; style.italic = excel_cell.font.i; style.underline = excel_cell.font.u
                if excel_cell.font.color: # Check if color object exists
                    style.text_color = get_safe_hex_color(excel_cell.font.color.rgb, "000000")
            if excel_cell.fill and excel_cell.fill.fgColor: # Check if fgColor object exists
                style.bg_color = get_safe_hex_color(excel_cell.fill.fgColor.rgb, "FFFFFF")
                style.fill_pattern_type = excel_cell.fill.patternType
            if excel_cell.alignment: style.h_align = excel_cell.alignment.horizontal or "left"; style.v_align = excel_cell.alignment.vertical or "center"; style.wrap_text = excel_cell.alignment.wrapText
            style.number_format = excel_cell.number_format or "General"
            sides = {"left": excel_cell.border.left, "right": excel_cell.border.right, "top": excel_cell.border.top, "bottom": excel_cell.border.bottom}
            for side_name, border_side in sides.items():
                if border_side:
                    setattr(style, f"border_{side_name}_style", border_side.style)
                    if border_side.color: # Check if color object exists
                        border_color_val = get_safe_hex_color(border_side.color.rgb, "000000")
                        setattr(style, f"border_{side_name}_color", border_color_val)
        return style
    @staticmethod
    def qt_to_excel(qt_item, excel_cell):
        if not qt_item or not excel_cell: return
        font = Font(name=str(qt_item.font().family()),sz=qt_item.font().pointSize(),b=qt_item.font().bold(),i=qt_item.font().italic(),u=qt_item.font().underline(),color=StyleConverter.hex_to_excel_rgb(qt_item.foreground().color().name()))
        excel_cell.font = font; fill = PatternFill(start_color=StyleConverter.hex_to_excel_rgb(qt_item.background().color().name()),end_color=StyleConverter.hex_to_excel_rgb(qt_item.background().color().name()),fill_type="solid")
        excel_cell.fill = fill; align = Alignment(horizontal=StyleConverter.qt_to_excel_alignment(qt_item.textAlignment()),vertical="center",wrap_text=True)
        excel_cell.alignment = align
    @staticmethod
    def hex_to_excel_rgb(hex_color: str) -> str:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3: hex_color = ''.join([c * 2 for c in hex_color])
        return f"FF{hex_color.upper()}"
    @staticmethod
    def qt_to_excel_alignment(qt_alignment: int) -> str:
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
    def __init__(self): super().__init__(); self.setup_ui(); self.merged_cells = []
    def setup_ui(self): self.setEditTriggers(QAbstractItemView.AllEditTriggers); self.setSelectionBehavior(QAbstractItemView.SelectItems); self.setSelectionMode(QAbstractItemView.ContiguousSelection); self.setAlternatingRowColors(False); self.setStyleSheet("QTableWidget { background-color: white; gridline-color: #d0d0d0; } QTableWidget::item { padding: 3px; } QTableWidget::item:selected { background-color: #0078d7; color: white; } QHeaderView::section { background-color: #f0f0f0; padding: 5px; border: 1px solid #d0d0d0; }"); self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter); self.verticalHeader().setDefaultSectionSize(24); self.verticalHeader().setVisible(False)
    def load_excel_sheet(self, worksheet: Worksheet):
        try:
            self.clear(); self.setRowCount(min(worksheet.max_row, MAX_ROWS_PREVIEW)); self.setColumnCount(min(worksheet.max_column, MAX_COLS_PREVIEW))
            headers = [str(worksheet.cell(row=1, column=c+1).value) if worksheet.cell(row=1, column=c+1).value else f"Column {c+1}" for c in range(self.columnCount())]; self.setHorizontalHeaderLabels(headers)
            for r_tbl in range(self.rowCount()):
                for c_tbl in range(self.columnCount()):
                    cell = worksheet.cell(row=r_tbl+1, column=c_tbl+1); value_str = self.format_cell_value(cell.value, cell.number_format)
                    item = QTableWidgetItem(value_str); self.apply_excel_style(cell, item); self.setItem(r_tbl, c_tbl, item)
            self.merged_cells = []
            for mr in worksheet.merged_cells.ranges: self.setSpan(mr.min_row-1, mr.min_col-1, mr.max_row-mr.min_row+1, mr.max_col-mr.min_col+1); self.merged_cells.append((mr.min_row-1, mr.min_col-1, mr.max_row-mr.min_row+1, mr.max_col-mr.min_col+1))
            self.resizeColumnsToContents(); return True
        except Exception as e: logger.error(f"Error loading Excel sheet into table: {str(e)}"); return False
    def apply_excel_style(self, excel_cell, qt_item):
        style = StyleConverter.excel_to_qt(excel_cell); font = QFont(style.font_name, style.font_size); font.setBold(style.bold); font.setItalic(style.italic); font.setUnderline(style.underline)
        qt_item.setFont(font); qt_item.setForeground(QColor(style.text_color)); qt_item.setBackground(QColor(style.bg_color))
        alignment = 0
        if style.h_align == "left": alignment |= Qt.AlignLeft
        elif style.h_align == "right": alignment |= Qt.AlignRight
        elif style.h_align == "center": alignment |= Qt.AlignHCenter
        elif style.h_align == "justify": alignment |= Qt.AlignJustify
        if style.v_align == "top": alignment |= Qt.AlignTop
        elif style.v_align == "center": alignment |= Qt.AlignVCenter
        elif style.v_align == "bottom": alignment |= Qt.AlignBottom
        else: alignment |= Qt.AlignVCenter
        qt_item.setTextAlignment(alignment)
        if style.fill_pattern_type: logger.debug(f"Cell ({excel_cell.row},{excel_cell.column}) Fill: {style.fill_pattern_type}")
        b_info = [f"{s[0].upper()}: {getattr(style,f'border_{s}_style')}({getattr(style,f'border_{s}_color')})" for s in ["left","right","top","bottom"] if getattr(style,f"border_{s}_style")];
        if b_info: logger.debug(f"Cell ({excel_cell.row},{excel_cell.column}) Border: {', '.join(b_info)}")
    def format_cell_value(self, value, number_format_str="General") -> str:
        if value is None: return ""
        if isinstance(value, datetime): return value.strftime("%d/%m/%Y %H:%M")
        if isinstance(value, (int, float)):
            if number_format_str and '%' in number_format_str:
                try:
                    if '.' in number_format_str: decimals = len(number_format_str.split('.')[1].split('%')[0]); return f"{value * 100:.{decimals}f}%"
                    return f"{value * 100:.0f}%"
                except: return f"{value * 100}%"
            return f"{value:,}"
        return str(value)
    def add_row(self): rc=self.rowCount();self.insertRow(rc);_=(self.insertColumn(0),self.setHorizontalHeaderItem(0,QTableWidgetItem("Column 1")))if self.columnCount()==0 else None
    def add_column(self): cc=self.columnCount();self.insertColumn(cc);self.setHorizontalHeaderItem(cc,QTableWidgetItem(f"Column {cc+1}"));_=(self.insertRow(0))if self.rowCount()==0 else None
    def delete_selected_rows(self): sr=sorted(list(set(i.row()for i in self.selectedIndexes())),reverse=True);[self.removeRow(r)for r in sr]
    def delete_selected_columns(self): sc=sorted(list(set(i.column()for i in self.selectedIndexes())),reverse=True);[self.removeColumn(c)for c in sc]

class PDFGenerator:
    def __init__(self, table: ExcelTableWidget, client_data: ClientData, settings: PDFExportSettings,
                 current_sheet_title: str, sheet_images_data: Dict[str, List[bytes]],
                 sheet_headers_footers_data: Dict[str, Dict[str, Dict[str, Dict[str, Optional[Union[str, bytes]]]]]],
                 current_excel_sheet: Optional[Worksheet] = None):
        self.table = table; self.client_data = client_data; self.settings = settings
        self.current_sheet_title = current_sheet_title; self.sheet_images_data = sheet_images_data
        self.sheet_hf_data = sheet_headers_footers_data
        self.current_excel_sheet = current_excel_sheet
        self.styles = getSampleStyleSheet()
        self.register_fonts(); self.create_styles()

    def register_fonts(self):
        try: pdfmetrics.registerFont(TTFont('Arial','arial.ttf')); pdfmetrics.registerFont(TTFont('Arial-Bold','arialbd.ttf')); pdfmetrics.registerFont(TTFont('Arial-Italic','ariali.ttf')); pdfmetrics.registerFont(TTFont('Arial-BoldItalic','arialbi.ttf'))
        except: pass
    def create_styles(self):
        s=self.styles;h=colors.HexColor;f,fs,l='Helvetica',DEFAULT_HF_FONT_SIZE,9;fb,fsb,lb='Helvetica-Bold',DEFAULT_HF_FONT_SIZE,10
        self.title_style=ParagraphStyle('Title',parent=s['Heading1'],fontName=fb,fontSize=16,leading=18,spaceAfter=12,alignment=TA_CENTER,textColor=h('#2c3e50'))
        self.client_style=ParagraphStyle('Client',parent=s['BodyText'],fontName=f,fontSize=10,leading=12,spaceAfter=6,textColor=h('#34495e'))
        self.table_header_style=ParagraphStyle('TableHeader',parent=s['BodyText'],fontName=fb,fontSize=fsb,leading=lb,alignment=TA_CENTER,textColor=colors.white,backColor=h('#3498db'))
        self.table_cell_style=ParagraphStyle('TableCell',parent=s['BodyText'],fontName=f,fontSize=fs,leading=l,textColor=colors.black)
        self.footer_style=ParagraphStyle('Footer',parent=s['BodyText'],fontName=f,fontSize=fs,leading=l,alignment=TA_CENTER,textColor=h('#7f8c8d'))

    def _get_pdf_font_name(self, excel_font_name: Optional[str], is_bold: bool, is_italic: bool) -> str:
        name_lower = (excel_font_name or "").lower()
        if is_bold and is_italic:
            if name_lower == "arial": return "Arial-BoldItalic"
            return "Helvetica-BoldOblique"
        if is_bold:
            if name_lower == "arial": return "Arial-Bold"
            return "Helvetica-Bold"
        if is_italic:
            if name_lower == "arial": return "Arial-Italic"
            return "Helvetica-Oblique"
        if name_lower == "arial": return "Arial"
        return "Helvetica"

    def _format_cell_value_for_pdf(self, value, number_format_str: str) -> str:
        if value is None: return ""
        if isinstance(value, datetime): return value.strftime("%d/%m/%Y %H:%M")
        if isinstance(value, (int, float)):
            if number_format_str and '%' in number_format_str:
                try:
                    num_decimals = 0
                    if '.' in number_format_str:
                        num_decimals = len(number_format_str.split('.')[1].split('%')[0])
                    return f"{value * 100:.{num_decimals}f}%"
                except: return f"{value * 100}%"
            return f"{value:,}"
        return str(value)

    def generate(self, file_path: str) -> Tuple[bool, str]:
        try:
            doc=SimpleDocTemplate(file_path,pagesize=self.settings.page_size,leftMargin=self.settings.margins[0],rightMargin=self.settings.margins[1],topMargin=self.settings.margins[2],bottomMargin=self.settings.margins[3])
            elements=[];has_excel_header,has_excel_footer=False,False
            if self.current_sheet_title and self.current_sheet_title in self.sheet_hf_data:
                sheet_hf=self.sheet_hf_data[self.current_sheet_title]
                if any(k in sheet_hf for k in['odd_header','even_header','first_header']):has_excel_header=True
                if any(k in sheet_hf for k in['odd_footer','even_footer','first_footer']):has_excel_footer=True
            if self.settings.header and not has_excel_header:elements.extend(self.create_header())
            elements.append(Paragraph(f"<u>Devis {self.client_data.project_id}</u>"if self.client_data.project_id else"<u>Devis</u>",self.title_style));elements.append(Spacer(1,12))
            elements.extend(self.create_client_info());elements.append(Spacer(1,15))
            if self.current_sheet_title and self.current_sheet_title in self.sheet_images_data:
                images_bytes_on_sheet=self.sheet_images_data[self.current_sheet_title]
                if images_bytes_on_sheet:
                    hs=self.styles['Heading3']if'Heading3'in self.styles else self.styles['h3']
                    elements.append(Paragraph("<u>Sheet Images:</u>",hs));elements.append(Spacer(1,0.1*inch))
                    for i,img_data_bytes in enumerate(images_bytes_on_sheet):
                        try:
                            img_flowable=Image(io.BytesIO(img_data_bytes))
                            img_flowable.drawWidth=2*inch;img_flowable.drawHeight=(img_flowable.imageHeight/img_flowable.imageWidth)*(2*inch)if img_flowable.imageWidth else 1*inch
                            img_flowable.preserveAspectRatio=True;elements.append(img_flowable);elements.append(Spacer(1,0.1*inch))
                            logger.info(f"Added sheet body image {i+1} to PDF.")
                        except Exception as e:logger.error(f"Could not process sheet body image bytes: {e}")
                    elements.append(Spacer(1,0.2*inch))
            table_data,col_widths=self.prepare_table_data()
            if table_data:main_table=Table(table_data,colWidths=col_widths,repeatRows=1 if self.settings.repeat_headers else 0);main_table.setStyle(self.create_table_style(len(table_data),len(table_data[0])));elements.append(main_table)
            else:logger.warning(f"No table data for sheet '{self.current_sheet_title}'.");_=(False,f"No content for sheet '{self.current_sheet_title}'")if not elements else None
            if self.settings.footer and not has_excel_footer:elements.append(Spacer(1,10));elements.extend(self.create_footer())
            doc.build(elements,onFirstPage=self.add_page_decorations,onLaterPages=self.add_page_decorations)
            return True,"PDF generated successfully"
        except Exception as e:logger.error(f"PDF generation failed: {str(e)}",exc_info=True);return False,str(e)

    def create_header(self) -> List[Flowable]:
        hE=[];hT=Table([[self.create_company_info(),self.create_document_info()]],colWidths=['70%','30%']);hT.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),10),('LEFTPADDING',(0,0),(0,0),0),('RIGHTPADDING',(1,0),(1,0),0)]));hE.append(hT);hE.append(Spacer(1,10));return hE
    def create_company_info(self) -> Paragraph:return Paragraph("<br/>".join([f"<b>{self.client_data.company or 'Société'}</b>",self.client_data.address or"Adresse",f"Tél: {self.client_data.phone or 'N/A'}",f"Email: {self.client_data.email or 'N/A'}"]),self.client_style)
    def create_document_info(self) -> Paragraph:return Paragraph("<br/>".join([f"<b>Devis N° {self.client_data.project_id or 'XXXX'}</b>",f"Date: {datetime.now().strftime('%d/%m/%Y')}",f"Client: {self.client_data.name or 'N/A'}"]),self.client_style)
    def create_client_info(self) -> List[Flowable]:
        cE=[];cT=Table([["Client:",self.client_data.name or"N/A"],["Société:",self.client_data.company or"N/A"],["Projet:",self.client_data.project or"N/A"],["Date:",datetime.now().strftime("%d/%m/%Y")],["Prix Total:",f"{self.client_data.price:,.2f} {self.client_data.currency}"]],colWidths=[3*cm,10*cm]);cT.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor("#f8f9fa")),('TEXTCOLOR',(0,0),(-1,-1),colors.black),('ALIGN',(0,0),(0,-1),'RIGHT'),('ALIGN',(1,0),(1,-1),'LEFT'),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),('GRID',(0,0),(-1,-1),0.5,colors.HexColor("#e0e0e0")),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4)]));cE.append(cT);return cE

    def prepare_table_data(self) -> Tuple[List[List[Union[str,Paragraph]]],List[float]]:
        if not self.current_excel_sheet: return [],[]
        sheet_to_process = self.current_excel_sheet
        max_r = min(sheet_to_process.max_row, MAX_ROWS_PREVIEW)
        max_c = min(sheet_to_process.max_column, MAX_COLS_PREVIEW)
        if max_r == 0 or max_c == 0: return [],[]
        data_matrix, col_widths_list = [],[]
        for c_idx in range(1, max_c + 1):
            dim = sheet_to_process.column_dimensions.get(get_column_letter(c_idx))
            width = dim.width if dim and dim.width else 12
            col_widths_list.append(width * 6)
        for r_idx in range(1, max_r + 1):
            row_data_list=[]
            for c_idx in range(1, max_c + 1):
                excel_cell = sheet_to_process.cell(row=r_idx, column=c_idx)
                excel_style = StyleConverter.excel_to_qt(excel_cell)
                formatted_value = self._format_cell_value_for_pdf(excel_cell.value, excel_style.number_format)
                text_content = formatted_value
                if excel_style.bold: text_content = f"<b>{text_content}</b>"
                if excel_style.italic: text_content = f"<i>{text_content}</i>"
                if excel_style.underline : text_content = f"<u>{text_content}</u>"
                p_style = self.table_cell_style.clone(f'cell_{r_idx}_{c_idx}')
                p_style.fontName = self._get_pdf_font_name(excel_style.font_name, excel_style.bold, excel_style.italic)
                p_style.fontSize = excel_style.font_size
                if excel_style.text_color: p_style.textColor = colors.HexColor(excel_style.text_color)
                logger.info(f"PDF Cell ({excel_cell.row},{excel_cell.column}): Text='{text_content[:30]}...', Font='{p_style.fontName}', Size={p_style.fontSize}, Color='{excel_style.text_color}', Bold={'<b>' in text_content}, Italic={'<i>' in text_content}, Underline={'<u>' in text_content}")
                if excel_style.h_align == "left": p_style.alignment = TA_LEFT
                elif excel_style.h_align == "center": p_style.alignment = TA_CENTER
                elif excel_style.h_align == "right": p_style.alignment = TA_RIGHT
                elif excel_style.h_align == "justify": p_style.alignment = TA_JUSTIFY
                row_data_list.append(Paragraph(text_content, p_style))
            data_matrix.append(row_data_list)
        return data_matrix, col_widths_list

    def create_table_style(self,nr:int,nc:int)->TableStyle:
        if nr==0 or nc==0 or not self.current_excel_sheet: return TableStyle([])
        cmds = [('BACKGROUND',(0,0),(-1,0),colors.HexColor("#3498db")),('TEXTCOLOR',(0,0),(-1,0),colors.white),('ALIGN',(0,0),(-1,0),'CENTER'),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,0),DEFAULT_HF_FONT_SIZE + 1),('BOTTOMPADDING',(0,0),(-1,0),6),('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f0f0f0")])]
        for r_pdf in range(nr):
            for c_pdf in range(nc):
                excel_r, excel_c = r_pdf + 1, c_pdf + 1
                if excel_r > self.current_excel_sheet.max_row or excel_c > self.current_excel_sheet.max_column: continue
                excel_cell = self.current_excel_sheet.cell(row=excel_r, column=excel_c)
                excel_style = StyleConverter.excel_to_qt(excel_cell)
                if excel_style.bg_color and excel_style.bg_color.upper() != '#FFFFFF':
                    cmds.append(('BACKGROUND', (c_pdf, r_pdf), (c_pdf, r_pdf), colors.HexColor(excel_style.bg_color)))
                    logger.info(f"PDF Cell ({excel_r},{excel_c}): BGCOLOR='{excel_style.bg_color}'")
                if excel_style.v_align == "top": cmds.append(('VALIGN', (c_pdf, r_pdf), (c_pdf, r_pdf), 'TOP'))
                elif excel_style.v_align == "center": cmds.append(('VALIGN', (c_pdf, r_pdf), (c_pdf, r_pdf), 'MIDDLE'))
                elif excel_style.v_align == "bottom": cmds.append(('VALIGN', (c_pdf, r_pdf), (c_pdf, r_pdf), 'BOTTOM'))
                border_map = {'left': excel_style.border_left_style, 'right': excel_style.border_right_style, 'top': excel_style.border_top_style, 'bottom': excel_style.border_bottom_style}
                color_map = {'left': excel_style.border_left_color, 'right': excel_style.border_right_color, 'top': excel_style.border_top_color, 'bottom': excel_style.border_bottom_color}
                line_cmds = {'left': 'LINEBEFORE', 'right': 'LINEAFTER', 'top': 'LINETOP', 'bottom': 'LINEBELOW'}
                for side, style_val in border_map.items():
                    if style_val and style_val != 'none':
                        thickness = 0.5;
                        if style_val == 'medium': thickness = 1.0
                        elif style_val == 'thick': thickness = 1.5
                        border_color_hex = color_map.get(side); border_color = colors.HexColor(border_color_hex) if border_color_hex else colors.black
                        cmds.append((line_cmds[side], (c_pdf, r_pdf), (c_pdf, r_pdf), thickness, border_color))
                        logger.info(f"PDF Cell ({excel_r},{excel_c}): BORDER_{line_cmds[side]}='{border_color_hex} {thickness}pt'")
        for mc_range in self.current_excel_sheet.merged_cells.ranges:
            min_r,min_c,max_r,max_c=mc_range.min_row,mc_range.min_col,mc_range.max_row,mc_range.max_col
            if min_r<=MAX_ROWS_PREVIEW and min_c<=MAX_COLS_PREVIEW:
                pdf_min_r,pdf_min_c=min_r-1,min_c-1;pdf_max_r=min(max_r-1,MAX_ROWS_PREVIEW-1);pdf_max_c=min(max_c-1,MAX_COLS_PREVIEW-1)
                if pdf_min_r<=pdf_max_r and pdf_min_c<=pdf_max_c: cmds.append(('SPAN',(pdf_min_c,pdf_min_r),(pdf_max_c,pdf_max_r)))
        return TableStyle(cmds)

    def create_footer(self) -> List[Flowable]:
        fE=[]
        if self.client_data.notes:n=Paragraph(f"<b>Notes:</b><br/>{self.client_data.notes}",ParagraphStyle('Notes',parent=self.styles['BodyText'],fontName='Helvetica',fontSize=8,leading=9,textColor=colors.HexColor("7f8c8d")));fE.append(n);fE.append(Spacer(1,10))
        fT=Paragraph(f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | {self.client_data.company or 'Société'}",self.footer_style);fE.append(fT);return fE

    def _draw_hf_section(self, canvas: canvas.Canvas, doc, section_content_map: Dict, is_header: bool, default_hf_height: float, font_name: str, font_size: int, available_sheet_images_bytes: List[bytes]): # Unchanged
        canvas.setFont(font_name, font_size)
        text_y_position = 0; font_ascent_approx = font_size * 0.8
        if is_header: text_y_position = doc.height + doc.topMargin - default_hf_height + font_ascent_approx * 0.5
        else: text_y_position = doc.bottomMargin + font_ascent_approx * 0.5
        positions = {"left_text_x": doc.leftMargin + HF_SECTION_PADDING, "center_text_x": doc.leftMargin + doc.width / 2, "right_text_x": doc.width + doc.leftMargin - HF_SECTION_PADDING}
        for part_key in ["left", "center", "right"]:
            part_data = section_content_map.get(part_key)
            if not part_data: continue
            text_to_draw = part_data.get("text")
            image_bytes = part_data.get("image_data")
            drew_image_for_part = False
            if not image_bytes and text_to_draw and "&G" in text_to_draw:
                if available_sheet_images_bytes:
                    image_bytes = available_sheet_images_bytes.pop(0)
                    logger.info(f"Rendering sheet image (from bytes) for &G in {part_key} of {'header' if is_header else 'footer'}.")
                    text_to_draw = text_to_draw.replace("&G", "").strip()
                else: logger.warning(f"&G tag in {part_key} of {'header' if is_header else 'footer'} but no available sheet images bytes."); text_to_draw = text_to_draw.replace("&G", "").strip()
            if image_bytes:
                try:
                    img_reader = ImageReader(io.BytesIO(image_bytes)); img_orig_width, img_orig_height = img_reader.getSize()
                    max_h = default_hf_height * (PDF_HEADER_IMAGE_MAX_HEIGHT_FACTOR if is_header else PDF_FOOTER_IMAGE_MAX_HEIGHT_FACTOR)
                    max_w = (PDF_HEADER_IMAGE_MAX_WIDTH if is_header else PDF_FOOTER_IMAGE_MAX_WIDTH)
                    aspect = img_orig_height / float(img_orig_width) if img_orig_width != 0 else 1
                    img_display_width = min(max_w, img_orig_width); img_display_height = img_display_width * aspect
                    if img_display_height > max_h: img_display_height = max_h; img_display_width = img_display_height / aspect if aspect != 0 else 0
                    img_y_center = (doc.height + doc.topMargin - default_hf_height / 2) if is_header else (doc.bottomMargin + default_hf_height / 2)
                    img_y_pos = img_y_center - img_display_height / 2
                    img_x_pos = 0
                    if part_key == "left": img_x_pos = doc.leftMargin + HF_SECTION_PADDING
                    elif part_key == "center": img_x_pos = doc.leftMargin + doc.width / 2 - img_display_width / 2
                    elif part_key == "right": img_x_pos = doc.width + doc.leftMargin - HF_SECTION_PADDING - img_display_width
                    logger.info(f"PDF H/F Image: Drawing image for {'header' if is_header else 'footer'} {part_key}. Using {'direct image_data' if part_data.get('image_data') else 'resolved &G image'}.")
                    canvas.drawImage(img_reader, img_x_pos, img_y_pos, width=img_display_width, height=img_display_height, preserveAspectRatio=True)
                    logger.info(f"Drew image in {part_key} of {'header' if is_header else 'footer'}."); drew_image_for_part = True
                except Exception as e: logger.error(f"Failed to draw image in {part_key} of {'header' if is_header else 'footer'}: {e}")
            if text_to_draw and (not drew_image_for_part or text_to_draw.strip()):
                page_num_str=str(canvas.getPageNumber());total_pages_str=str(getattr(doc,'_pageNumber',page_num_str))
                processed_text=text_to_draw.replace("&[Page]",page_num_str).replace("&P",page_num_str).replace("&[Pages]",total_pages_str).replace("&N",total_pages_str).replace("&[Date]",datetime.now().strftime("%Y-%m-%d")).replace("&D",datetime.now().strftime("%Y-%m-%d")).replace("&[Time]",datetime.now().strftime("%H:%M:%S")).replace("&T",datetime.now().strftime("%H:%M:%S")).replace("&[File]",Path(doc.filename).name if doc.filename else"Document").replace("&F",Path(doc.filename).name if doc.filename else"Document").replace("&[Tab]",self.current_sheet_title or"Sheet").replace("&A",self.current_sheet_title or"Sheet").replace("&B","").replace("&I","")
                logger.info(f"PDF H/F Text: Drawing text for {'header' if is_header else 'footer'} {part_key}: '{processed_text[:30]}...'")
                canvas.setFillColor(colors.black)
                if part_key=="left":canvas.drawString(positions["left_text_x"],text_y_position,processed_text)
                elif part_key=="center":canvas.drawCentredString(positions["center_text_x"],text_y_position,processed_text)
                elif part_key=="right":canvas.drawRightString(positions["right_text_x"],text_y_position,processed_text)

    def add_page_decorations(self, canvas: canvas.Canvas, doc): # Unchanged
        canvas.saveState()
        if self.settings.watermark: canvas.setFont('Helvetica',60);canvas.setFillColor(colors.HexColor("#f0f0f0"));canvas.rotate(45);page_width,page_height=doc.pagesize;canvas.drawString(page_width*0.25,page_height*0.25,self.settings.watermark);canvas.rotate(-45)
        default_page_num_text=f"Page {canvas.getPageNumber()}";excel_hf_applied_for_page=False
        hf_font_name="Helvetica";hf_font_size=DEFAULT_HF_FONT_SIZE
        available_sheet_images_bytes_for_page=[]
        if self.current_sheet_title in self.sheet_images_data:
            for img_data_bytes_from_model in self.sheet_images_data[self.current_sheet_title]: available_sheet_images_bytes_for_page.append(img_data_bytes_from_model)
        if self.current_sheet_title and self.current_sheet_title in self.sheet_hf_data:
            sheet_hf_content=self.sheet_hf_data[self.current_sheet_title];page_num=canvas.getPageNumber();header_type_to_use,footer_type_to_use=None,None
            if page_num==1 and sheet_hf_content.get("first_header"):header_type_to_use="first_header"
            elif page_num%2==0 and sheet_hf_content.get("even_header"):header_type_to_use="even_header"
            elif sheet_hf_content.get("odd_header"):header_type_to_use="odd_header"
            if page_num==1 and sheet_hf_content.get("first_footer"):footer_type_to_use="first_footer"
            elif page_num%2==0 and sheet_hf_content.get("even_footer"):footer_type_to_use="even_footer"
            elif sheet_hf_content.get("odd_footer"):footer_type_to_use="odd_footer"
            if header_type_to_use and header_type_to_use in sheet_hf_content:
                header_data=sheet_hf_content[header_type_to_use];self._draw_hf_section(canvas,doc,header_data,True,PDF_HEADER_HEIGHT,hf_font_name,hf_font_size,available_sheet_images_bytes_for_page)
                if any(header_data.get(part,{}).get('text')or header_data.get(part,{}).get('image_data')for part in["left","center","right"]):excel_hf_applied_for_page=True
            if footer_type_to_use and footer_type_to_use in sheet_hf_content:
                footer_data=sheet_hf_content[footer_type_to_use];self._draw_hf_section(canvas,doc,footer_data,False,PDF_FOOTER_HEIGHT,hf_font_name,hf_font_size,available_sheet_images_bytes_for_page)
                if any(footer_data.get(part,{}).get('text')or footer_data.get(part,{}).get('image_data')for part in["left","center","right"]):excel_hf_applied_for_page=True
        if self.settings.footer and not excel_hf_applied_for_page:
            canvas.setFont(hf_font_name,hf_font_size);canvas.setFillColor(colors.HexColor("#7f8c8d"))
            page_num_y_pos=doc.bottomMargin+(PDF_FOOTER_HEIGHT-hf_font_size*0.8)/2
            canvas.drawRightString(doc.width+doc.leftMargin-HF_SECTION_PADDING,page_num_y_pos,default_page_num_text)
        canvas.restoreState()

class ExcelEditor(QDialog): # Unchanged
    def __init__(self, file_path: str = "", parent=None):
        super().__init__(parent)
        self.file_path: Optional[str] = file_path if file_path else None
        self.excel_model = ExcelTableModel()
        self.pdf_settings = PDFExportSettings()
        self.setup_ui()
        self.setup_connections()
        if self.file_path: # Corrected conditional load
            self.load_file(self.file_path)
    def setup_ui(self): self.setWindowTitle("Ultimate Excel Editor");self.setMinimumSize(1280,800);self.resize(1366,768);self.setStyle(QStyleFactory.create("Fusion"));p=self.palette();p.setColor(QPalette.Window,QColor(53,53,53));p.setColor(QPalette.WindowText,Qt.white);p.setColor(QPalette.Base,QColor(25,25,25));p.setColor(QPalette.AlternateBase,QColor(53,53,53));p.setColor(QPalette.ToolTipBase,Qt.white);p.setColor(QPalette.ToolTipText,Qt.white);p.setColor(QPalette.Text,Qt.white);p.setColor(QPalette.Button,QColor(53,53,53));p.setColor(QPalette.ButtonText,Qt.white);p.setColor(QPalette.BrightText,Qt.red);p.setColor(QPalette.Link,QColor(42,130,218));p.setColor(QPalette.Highlight,QColor(42,130,218));p.setColor(QPalette.HighlightedText,Qt.black);self.setPalette(p);ml=QVBoxLayout(self);ml.setContentsMargins(5,5,5,5);ml.setSpacing(5);self.tp=self.create_table_panel();self.cp=self.create_client_panel();self.create_toolbar(ml);cs=QSplitter(Qt.Horizontal);cs.addWidget(self.cp);cs.addWidget(self.tp);cs.setStretchFactor(0,1);cs.setStretchFactor(1,3);ml.addWidget(cs);self.create_status_bar(ml);self.pb=QProgressBar();self.pb.setFixedHeight(20);self.pb.setVisible(False);ml.addWidget(self.pb)
    def create_toolbar(self,pl):tb=QToolBar();tb.setIconSize(QSize(24,24));tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon);tb.setMovable(False);acs=[("document-open","Open",QKeySequence.Open,self.open_file_dialog),("document-save","Save",QKeySequence.Save,self.save_file),("separator",),("document-export","Export PDF","Ctrl+E",self.export_pdf),("configure","Settings","",self.show_settings),("separator",),("list-add","Add Row","",self.table.add_row),("list-add","Add Column","",self.table.add_column),("list-remove","Delete Row","",self.table.delete_selected_rows),("list-remove","Delete Column","",self.table.delete_selected_columns)];[(tb.addSeparator()if i[0]=="separator"else(ac:=QAction(QIcon.fromTheme(i[0]),i[1],self),ac.setShortcut(i[2])if i[2]else None,ac.triggered.connect(i[3]),tb.addAction(ac)))for i in acs];pl.addWidget(tb)
    def create_status_bar(self,pl):sb=QFrame();sb.setFrameShape(QFrame.StyledPanel);sb.setStyleSheet("background-color:#3a3a3a;border-top:1px solid #505050;");sb.setFixedHeight(30);ly=QHBoxLayout(sb);ly.setContentsMargins(10,0,10,0);self.sl=QLabel("Ready");self.sl.setStyleSheet("color:#aaaaaa;");ly.addWidget(self.sl);ly.addStretch();self.fl=QLabel("No file loaded");self.fl.setStyleSheet("color:#7f8c8d;font-style:italic;");ly.addWidget(self.fl);pl.addWidget(sb)
    def create_client_panel(self)->QWidget:
        p=QGroupBox("Client Information");p.setMaximumWidth(350);ly=QFormLayout(p);ly.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.cn=QLineEdit();self.cn.setPlaceholderText("Client name");ly.addRow("Name:",self.cn);self.cc=QLineEdit();self.cc.setPlaceholderText("Company name");ly.addRow("Company:",self.cc)
        self.ca=QTextEdit();self.ca.setMaximumHeight(60);self.ca.setPlaceholderText("Address");ly.addRow("Address:",self.ca)
        cl=QHBoxLayout();self.cpn=QLineEdit();self.cpn.setPlaceholderText("Phone");cl.addWidget(self.cpn);self.ce=QLineEdit();self.ce.setPlaceholderText("Email");cl.addWidget(self.ce);ly.addRow("Contact:",cl)
        self.pn=QLineEdit();self.pn.setPlaceholderText("Project name");ly.addRow("Project:",self.pn);self.pid=QLineEdit();self.pid.setPlaceholderText("Project ID");ly.addRow("Project ID:",self.pid)
        prl=QHBoxLayout();self.pp=QDoubleSpinBox();self.pp.setRange(0,99999999);self.pp.setPrefix("€ ");prl.addWidget(self.pp);self.curc=QComboBox();self.curc.addItems(["€","$","£","¥","₺"]);prl.addWidget(self.curc);ly.addRow("Price:",prl)
        self.nts=QTextEdit();self.nts.setMaximumHeight(80);self.nts.setPlaceholderText("Additional notes");ly.addRow("Notes:",self.nts)
        self.lb=QPushButton("Select Logo...");self.lb.clicked.connect(self.select_logo);ly.addRow("Logo:",self.lb);return p
    def create_table_panel(self)->QWidget:p=QWidget();ly=QVBoxLayout(p);ly.setContentsMargins(0,0,0,0);ly.setSpacing(0);self.sc=QComboBox();self.sc.setMinimumWidth(200);ly.addWidget(self.sc);self.table=ExcelTableWidget();ly.addWidget(self.table);return p
    def setup_connections(self):self.cn.textChanged.connect(self.update_client_data);self.cc.textChanged.connect(self.update_client_data);self.ca.textChanged.connect(self.update_client_data);self.cpn.textChanged.connect(self.update_client_data);self.ce.textChanged.connect(self.update_client_data);self.pn.textChanged.connect(self.update_client_data);self.pid.textChanged.connect(self.update_client_data);self.pp.valueChanged.connect(self.update_client_data);self.curc.currentTextChanged.connect(self.update_client_data);self.nts.textChanged.connect(self.update_client_data);self.sc.currentTextChanged.connect(self.change_sheet);self.table.itemChanged.connect(self.mark_as_modified)
    def load_file(self,fp:str):
        self.set_progress(True,f"Loading file: {QFileInfo(fp).fileName()}...")
        if self.excel_model.load_workbook(fp):(self.file_path,self.fl.setText(QFileInfo(fp).fileName()),self.sc.clear(),self.sc.addItems(self.excel_model.sheets),self.load_client_data(),(_:=self.table.load_excel_sheet(self.excel_model.current_sheet))if self.excel_model.current_sheet else(self.table.clearContents(),self.table.setRowCount(0),self.table.setColumnCount(0)),self.set_progress(False),self.update_status("File loaded successfully"),logger.info(f"Successfully loaded: {fp}"),True)
        else:em=self.excel_model.load_error_message or f"Unknown error: {fp}";QMessageBox.critical(self,"Error",em);self.file_path,self.fl.setText("No file"),self.sc.clear(),self.table.clearContents(),self.table.setRowCount(0),self.table.setColumnCount(0);[x.clear()for x in[self.cn,self.cc,self.ca,self.cpn,self.ce,self.pn,self.pid,self.nts]];self.pp.setValue(0);self.set_progress(False),self.update_status("Failed to load","red"),logger.error(f"Failed to load: {fp}");return False
    def load_client_data(self):c=self.excel_model.client_data;self.cn.setText(c.name);self.cc.setText(c.company);self.ca.setPlainText(c.address);self.cpn.setText(c.phone);self.ce.setText(c.email);self.pn.setText(c.project);self.pid.setText(c.project_id);self.pp.setValue(c.price);self.curc.setCurrentText(c.currency);self.nts.setPlainText(c.notes)
    def update_client_data(self):d=self.excel_model.client_data;d.name,d.company,d.address,d.phone,d.email,d.project,d.project_id,d.price,d.currency,d.notes=self.cn.text(),self.cc.text(),self.ca.toPlainText(),self.cpn.text(),self.ce.text(),self.pn.text(),self.pid.text(),self.pp.value(),self.curc.currentText(),self.nts.toPlainText();self.mark_as_modified()
    def mark_as_modified(self):self.excel_model.is_modified=True;self.update_status("Modified","orange")
    def update_status(self,msg:str,color:str="green"):self.sl.setText(msg);self.sl.setStyleSheet(f"color:{color};")
    def set_progress(self,v:bool,msg:str=""):self.pb.setVisible(v);self.pb.setRange(0,0 if v else 1);self.update_status(msg,"blue")if v else None
    def open_file_dialog(self):
        if self.excel_model.is_modified:
            r=QMessageBox.question(self,"Unsaved","Save changes?",QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel)
            if r==QMessageBox.Save and not self.save_file():return
            if r==QMessageBox.Cancel:return
        fp,_=QFileDialog.getOpenFileName(self,"Open Excel","","Excel (*.xlsx *.xls *.xlsm);;All (*)");_=(self.load_file(fp))if fp else None
    def save_file(self)->bool:
        try:
            if not self.file_path:return self.save_file_as()
            self.set_progress(True,"Saving...");self.update_client_data();self.excel_model.workbook.save(self.file_path);self.excel_model.is_modified=False;self.set_progress(False);self.update_status("Saved");return True
        except Exception as e:logger.error(f"Error saving file: {str(e)}");QMessageBox.critical(self,"Error",f"Error saving file:\n{str(e)}");self.set_progress(False);return False
    def save_file_as(self)->bool: # Corrected from one-liner
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Excel File", "", "Excel Files (*.xlsx);;All Files (*)")
        if file_path:
            self.file_path = file_path
            self.file_label.setText(QFileInfo(file_path).fileName())
            return self.save_file()
        return False
    def change_sheet(self,sn:str):
        if not sn or not self.excel_model.workbook or(self.excel_model.current_sheet and sn==self.excel_model.current_sheet.title):return
        if self.excel_model.is_modified:
            r=QMessageBox.question(self,"Unsaved","Save changes?",QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel)
            if r==QMessageBox.Save and not self.save_file():return
            if r==QMessageBox.Cancel:self.sc.setCurrentText(self.excel_model.current_sheet.title);return
        try:self.set_progress(True,f"Loading {sn}...");self.excel_model.current_sheet=self.excel_model.workbook[sn];self.table.load_excel_sheet(self.excel_model.current_sheet);self.set_progress(False);self.update_status(f"Sheet '{sn}' loaded")
        except Exception as e:logger.error(f"Error changing sheet:{e}");QMessageBox.critical(self,"Error",f"Error loading sheet:\n{e}");self.set_progress(False)
    def export_pdf(self):
        if not self.file_path:QMessageBox.warning(self,"Warning","No file loaded");return
        self.update_client_data();dn=f"{Path(self.file_path).stem}.pdf";sp,_=QFileDialog.getSaveFileName(self,"Export PDF",dn,"PDF (*.pdf)");_=(None)if not sp else None
        try:
            self.set_progress(True,"Exporting PDF...");cs_title=self.excel_model.current_sheet.title if self.excel_model.current_sheet else""
            pdf_gen=PDFGenerator(self.table,self.excel_model.client_data,self.pdf_settings,cs_title,self.excel_model.sheet_images,self.excel_model.sheet_headers_footers,self.excel_model.current_sheet)
            s,m=pdf_gen.generate(sp);self.set_progress(False)
            if s:self.update_status("PDF Exported");_=(self.open_file(sp))if QMessageBox.question(self,"Complete",f"PDF created:\n{sp}\n\nOpen?",QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes else None
            else:QMessageBox.critical(self,"Export Error",f"Error exporting PDF:\n{m}")
        except Exception as e:logger.error(f"PDF export error:{e}",exc_info=True);QMessageBox.critical(self,"Error",f"PDF export error:\n{e}");self.set_progress(False)
    def select_logo(self):
        fp,_=QFileDialog.getOpenFileName(self,"Select Logo","","Images (*.png *.jpg *.jpeg)")
        if fp:
            self.excel_model.client_data.logo_path = fp
            self.mark_as_modified()
    def show_settings(self):QMessageBox.information(self,"Settings","Settings available next version.")
    def open_file(self,fp:str):[(os.startfile(fp)if sys.platform=="win32"else os.system(f'open "{fp}"')if sys.platform=="darwin"else os.system(f'xdg-open "{fp}"'))]or[logger.error(f"Cannot open file:{e}"),QMessageBox.warning(self,"Warning",f"Cannot open file:\n{e}")]

def main():app=QApplication(sys.argv);app.setStyle(QStyleFactory.create("Fusion"));app.setApplicationName("Ultimate Excel Editor");app.setApplicationVersion("1.0");app.setWindowIcon(QIcon.fromTheme("x-office-spreadsheet"));editor=ExcelEditor();_=(editor.load_file(sys.argv[1]))if len(sys.argv)>1 else None;editor.show();sys.exit(app.exec_())
if __name__=="__main__":main()
