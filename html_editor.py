import os
import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QToolBar, QAction, QMessageBox,
    QFileDialog, QFontComboBox, QComboBox, QColorDialog, QDialogButtonBox,
    QSizePolicy, QActionGroup
)
from PyQt5.QtGui import QIcon, QTextCharFormat, QColor, QFont, QKeySequence, QTextImageFormat, QDesktopServices
from PyQt5.QtCore import Qt, QFileInfo, QUrl, pyqtSignal

class HtmlEditor(QDialog):
    # Signal to indicate the file was saved, potentially with new path
    file_saved = pyqtSignal(str)

    def __init__(self, file_path=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        # self.new_file_path_on_save = None # Not strictly needed if self.file_path is updated directly

        self.setWindowIcon(QIcon.fromTheme("text-html", QIcon(":/icons/html.png"))) # Fallback icon
        if self.file_path and os.path.exists(self.file_path):
            self.setWindowTitle(f"HTML Editor - {os.path.basename(self.file_path)}")
        else:
            self.setWindowTitle("HTML Editor - New Document")

        self.setMinimumSize(800, 600)

        self.setup_ui() # Call this before trying to load HTML

        if self.file_path and os.path.exists(self.file_path):
            self.load_html()
        else:
            self.text_edit.setHtml("<!DOCTYPE html><html><head><title>New Document</title></head><body><p>Start editing here...</p></body></html>")
            if self.file_path: # Path provided but file doesn't exist
                 QMessageBox.information(self, "New File", f"Creating new file at: {self.file_path}")
            self.text_edit.document().setModified(False) # New doc is not modified


    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        self.setup_toolbar() # Initialize self.toolbar
        main_layout.addWidget(self.toolbar)

        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(True)
        self.text_edit.currentCharFormatChanged.connect(self.update_toolbar_states)
        self.text_edit.cursorPositionChanged.connect(self.update_toolbar_states)
        main_layout.addWidget(self.text_edit)

        button_box = QDialogButtonBox()
        self.save_button = button_box.addButton("Save", QDialogButtonBox.AcceptRole)
        self.cancel_button = button_box.addButton("Cancel", QDialogButtonBox.RejectRole)

        self.save_button.clicked.connect(self.accept_changes) # Connect to custom slot
        self.cancel_button.clicked.connect(self.reject)

        main_layout.addWidget(button_box)
        self.setLayout(main_layout)

    def setup_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(Qt.QSize(16,16))

        # Font Family
        self.font_combo = QFontComboBox(self.toolbar)
        self.font_combo.currentFontChanged.connect(self.handle_font_family)
        self.toolbar.addWidget(self.font_combo)

        # Font Size
        self.size_combo = QComboBox(self.toolbar)
        self.size_combo.setEditable(True)
        font_sizes = ['8', '9', '10', '11', '12', '14', '16', '18', '20', '22', '24', '28', '32', '36', '48', '72']
        self.size_combo.addItems(font_sizes)
        self.size_combo.setCurrentText("12")
        self.size_combo.activated[str].connect(self.handle_font_size)
        self.toolbar.addWidget(self.size_combo)

        self.toolbar.addSeparator()

        self.bold_action = QAction(QIcon.fromTheme("format-text-bold"), "Bold", self)
        self.bold_action.setCheckable(True)
        self.bold_action.setShortcut(QKeySequence.Bold)
        self.bold_action.triggered.connect(self.handle_bold)
        self.toolbar.addAction(self.bold_action)

        self.italic_action = QAction(QIcon.fromTheme("format-text-italic"), "Italic", self)
        self.italic_action.setCheckable(True)
        self.italic_action.setShortcut(QKeySequence.Italic)
        self.italic_action.triggered.connect(self.handle_italic)
        self.toolbar.addAction(self.italic_action)

        self.underline_action = QAction(QIcon.fromTheme("format-text-underline"), "Underline", self)
        self.underline_action.setCheckable(True)
        self.underline_action.setShortcut(QKeySequence.Underline)
        self.underline_action.triggered.connect(self.handle_underline)
        self.toolbar.addAction(self.underline_action)

        self.toolbar.addSeparator()

        self.color_action = QAction(QIcon.fromTheme("format-text-color"), "Text Color", self)
        self.color_action.triggered.connect(self.handle_text_color)
        self.toolbar.addAction(self.color_action)

        self.toolbar.addSeparator()

        self.alignment_group_actions = QActionGroup(self)
        self.alignment_group_actions.setExclusive(True)

        self.align_left_action = QAction(QIcon.fromTheme("format-justify-left"), "Align Left", self)
        self.align_left_action.setCheckable(True)
        self.align_left_action.triggered.connect(lambda: self.text_edit.setAlignment(Qt.AlignLeft))
        self.alignment_group_actions.addAction(self.align_left_action)
        self.toolbar.addAction(self.align_left_action)

        self.align_center_action = QAction(QIcon.fromTheme("format-justify-center"), "Align Center", self)
        self.align_center_action.setCheckable(True)
        self.align_center_action.triggered.connect(lambda: self.text_edit.setAlignment(Qt.AlignHCenter))
        self.alignment_group_actions.addAction(self.align_center_action)
        self.toolbar.addAction(self.align_center_action)

        self.align_right_action = QAction(QIcon.fromTheme("format-justify-right"), "Align Right", self)
        self.align_right_action.setCheckable(True)
        self.align_right_action.triggered.connect(lambda: self.text_edit.setAlignment(Qt.AlignRight))
        self.alignment_group_actions.addAction(self.align_right_action)
        self.toolbar.addAction(self.align_right_action)

        self.align_justify_action = QAction(QIcon.fromTheme("format-justify-fill"), "Align Justify", self)
        self.align_justify_action.setCheckable(True)
        self.align_justify_action.triggered.connect(lambda: self.text_edit.setAlignment(Qt.AlignJustify))
        self.alignment_group_actions.addAction(self.align_justify_action)
        self.toolbar.addAction(self.align_justify_action)

    def handle_font_family(self, font):
        self.text_edit.setCurrentFont(font)

    def handle_font_size(self, point_size_str):
        try:
            point_size = float(point_size_str)
            if point_size > 0:
                self.text_edit.setFontPointSize(point_size)
        except ValueError:
            pass

    def handle_bold(self, checked):
        self.text_edit.setFontWeight(QFont.Bold if checked else QFont.Normal)

    def handle_italic(self, checked):
        self.text_edit.setFontItalic(checked)

    def handle_underline(self, checked):
        self.text_edit.setFontUnderline(checked)

    def handle_text_color(self):
        color = QColorDialog.getColor(self.text_edit.textColor(), self)
        if color.isValid():
            self.text_edit.setTextColor(color)

    def update_toolbar_states(self):
        fmt = self.text_edit.currentCharFormat()
        self.font_combo.setCurrentFont(fmt.font())

        point_size_str = str(int(fmt.fontPointSize())) # Use int for cleaner display
        idx = self.size_combo.findText(point_size_str)
        if idx != -1:
            self.size_combo.setCurrentIndex(idx)
        else:
            self.size_combo.setCurrentText(point_size_str)

        self.bold_action.setChecked(fmt.fontWeight() == QFont.Bold)
        self.italic_action.setChecked(fmt.fontItalic())
        self.underline_action.setChecked(fmt.fontUnderline())

        alignment = self.text_edit.alignment()
        if alignment == Qt.AlignLeft: self.align_left_action.setChecked(True)
        elif alignment == Qt.AlignHCenter: self.align_center_action.setChecked(True)
        elif alignment == Qt.AlignRight: self.align_right_action.setChecked(True)
        elif alignment == Qt.AlignJustify: self.align_justify_action.setChecked(True)


    def load_html(self):
        if self.file_path and os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                self.text_edit.setHtml(html_content)
                self.text_edit.document().setModified(False)
            except Exception as e:
                QMessageBox.critical(self, "Error Loading File", f"Could not load HTML file: {str(e)}")
        elif self.file_path:
             QMessageBox.information(self, "File Not Found", f"The file {self.file_path} was not found. A new document will be created.")
             self.text_edit.setHtml("<!DOCTYPE html><html><head><title>New Document</title></head><body><p></p></body></html>")
             self.text_edit.document().setModified(False)

    def save_html(self):
        current_file_path_to_save = self.file_path

        if not current_file_path_to_save:
            new_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save HTML File",
                os.getcwd(),
                "HTML Files (*.html *.htm);;All Files (*)"
            )
            if not new_path:
                return False
            current_file_path_to_save = new_path
            # self.file_path = new_path # Update file_path only after successful save

        html_content = self.text_edit.toHtml()
        try:
            with open(current_file_path_to_save, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.file_path = current_file_path_to_save # Update instance's file_path
            self.setWindowTitle(f"HTML Editor - {os.path.basename(self.file_path)}")
            self.text_edit.document().setModified(False)
            self.file_saved.emit(self.file_path)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error Saving File", f"Could not save HTML file to {current_file_path_to_save}: {str(e)}")
            return False

    def accept_changes(self):
        if self.save_html():
            self.accept()

    def maybe_save(self):
        if not self.text_edit.document().isModified():
            return True

        reply = QMessageBox.question(self, "Unsaved Changes",
                                     "You have unsaved changes. Do you want to save them?",
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                     QMessageBox.Save)

        if reply == QMessageBox.Save:
            return self.save_html()
        elif reply == QMessageBox.Cancel:
            return False
        return True # Discard

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

if __name__ == '__main__':
    if QApplication.instance() is None:
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()

    # Test with a dummy file for development
    # Ensure 'example.html' exists or the editor will start with a new document message.
    # with open("example.html", "w", encoding="utf-8") as f:
    #    f.write("<h1>Hello World</h1><p>This is a test <b>bold</b> and <i>italic</i>.</p>")
    # editor = HtmlEditor("example.html")

    editor = HtmlEditor() # Test new file scenario

    if editor.exec_() == QDialog.Accepted:
        print(f"Editor accepted, file path: {editor.file_path}")
    else:
        print("Editor cancelled.")

    # sys.exit(app.exec_()) # Avoid if imported
