# -*- coding: utf-8 -*-
import os
import shutil

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QDialogButtonBox, QMessageBox, QLabel, QGroupBox, QHBoxLayout,
    QFileDialog
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt

import db as db_manager # This class uses db_manager directly
import icons_rc # Import for Qt resource file

class ClientProductDimensionDialog(QDialog):
    def __init__(self, client_id, product_id, app_root_dir, parent=None):
        super().__init__(parent)
        self.client_id = client_id # Stored, though not used in current methods
        self.product_id = product_id
        self.app_root_dir = app_root_dir
        self.current_tech_image_path = None

        self.setWindowTitle(self.tr("Gérer Dimensions Produit Client") + f" (Produit ID: {self.product_id})")
        self.setMinimumSize(500, 600)
        self.more_dimension_widgets = [] # For rows G-H and I-J
        self.are_more_dimensions_visible = False # State tracker

        self.setup_ui()
        self.load_dimensions()
        # Set initial state for G-J and button after UI is built
        self._toggle_more_dimensions_visibility(initial_setup=True)


    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        form_group = QGroupBox(self.tr("Dimensions Spécifiques"))
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)
        main_layout.addWidget(form_group)

        self.dimension_inputs = {}
        dim_labels = [chr(65 + i) for i in range(10)] # A, B, C, ..., J

        # Dimensions A-F (3 rows, 2 per row)
        for i in range(0, 6, 2): # Loops for A-B, C-D, E-F
            row_widget = QWidget()
            row_h_layout = QHBoxLayout(row_widget)
            row_h_layout.setContentsMargins(0,0,0,0)

            # First dimension in pair (A, C, E)
            label1_text = dim_labels[i]
            line_edit1 = QLineEdit()
            self.dimension_inputs[f'dim_{label1_text.lower()}'] = line_edit1
            row_h_layout.addWidget(QLabel(self.tr(f"{label1_text}:")))
            row_h_layout.addWidget(line_edit1)

            row_h_layout.addSpacing(20)

            # Second dimension in pair (B, D, F)
            label2_text = dim_labels[i+1]
            line_edit2 = QLineEdit()
            self.dimension_inputs[f'dim_{label2_text.lower()}'] = line_edit2
            row_h_layout.addWidget(QLabel(self.tr(f"{label2_text}:")))
            row_h_layout.addWidget(line_edit2)

            form_layout.addRow(row_widget) # Add the composite widget for the row

        # Toggle Button for G-J
        self.toggle_more_dims_button = QPushButton(self.tr("Show More Dimensions"))
        self.toggle_more_dims_button.clicked.connect(self._toggle_more_dimensions_visibility)
        form_layout.addRow(self.toggle_more_dims_button) # Add button below A-F

        # Dimensions G-J (2 rows, 2 per row, initially hidden)
        for i in range(6, 10, 2): # Loops for G-H, I-J
            row_widget = QWidget() # This is the QWidget for the entire row in QFormLayout
            row_h_layout = QHBoxLayout(row_widget)
            row_h_layout.setContentsMargins(0,0,0,0)

            # First dimension in pair (G, I)
            label1_text = dim_labels[i]
            line_edit1 = QLineEdit()
            self.dimension_inputs[f'dim_{label1_text.lower()}'] = line_edit1
            row_h_layout.addWidget(QLabel(self.tr(f"{label1_text}:")))
            row_h_layout.addWidget(line_edit1)

            row_h_layout.addSpacing(20)

            # Second dimension in pair (H, J)
            label2_text = dim_labels[i+1]
            line_edit2 = QLineEdit()
            self.dimension_inputs[f'dim_{label2_text.lower()}'] = line_edit2
            row_h_layout.addWidget(QLabel(self.tr(f"{label2_text}:")))
            row_h_layout.addWidget(line_edit2)

            # Add the QWidget (row_widget) to form_layout and store it for toggling
            # QFormLayout wraps its rows. We need to get the row widget itself.
            # A common way is to add the widget directly, and it spans both columns.
            # Or, add a label and then the widget.
            # Let's add it directly, and it will span.
            form_layout.addRow(row_widget)
            self.more_dimension_widgets.append(row_widget) # Store the QWidget containing G-H or I-J

        tech_image_group = QGroupBox(self.tr("Image Technique"))
        tech_image_layout = QVBoxLayout(tech_image_group)
        path_button_layout = QHBoxLayout()
        self.tech_image_path_input = QLineEdit()
        self.tech_image_path_input.setReadOnly(True)
        self.tech_image_path_input.setPlaceholderText(self.tr("Aucune image sélectionnée"))
        path_button_layout.addWidget(self.tech_image_path_input)
        self.browse_tech_image_button = QPushButton(self.tr("Parcourir..."))
        self.browse_tech_image_button.setIcon(QIcon.fromTheme("document-open", QIcon(":/icons/folder.svg")))
        self.browse_tech_image_button.clicked.connect(self.handle_browse_tech_image)
        path_button_layout.addWidget(self.browse_tech_image_button)
        tech_image_layout.addLayout(path_button_layout)
        self.tech_image_preview_label = QLabel(self.tr("Aperçu de l'image non disponible."))
        self.tech_image_preview_label.setAlignment(Qt.AlignCenter)
        self.tech_image_preview_label.setMinimumSize(200, 200)
        self.tech_image_preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")
        tech_image_layout.addWidget(self.tech_image_preview_label)
        main_layout.addWidget(tech_image_group)
        main_layout.addStretch()

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Save).setText(self.tr("Enregistrer"))
        self.button_box.button(QDialogButtonBox.Save).setObjectName("primaryButton")
        self.button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def _toggle_more_dimensions_visibility(self, initial_setup=False):
        if not initial_setup: # Regular click
            self.are_more_dimensions_visible = not self.are_more_dimensions_visible
        else: # Initial setup, set to hidden by default
            self.are_more_dimensions_visible = False

        for widget_row in self.more_dimension_widgets:
            # widget_row is the QWidget that was added to the form_layout.
            # We also need to toggle the label associated with this row if QFormLayout created one.
            # However, by adding row_widget directly (form_layout.addRow(row_widget)), it spans both columns.
            # So, toggling row_widget.setVisible() is sufficient.
            widget_row.setVisible(self.are_more_dimensions_visible)

        if self.are_more_dimensions_visible:
            self.toggle_more_dims_button.setText(self.tr("Show Less Dimensions"))
        else:
            self.toggle_more_dims_button.setText(self.tr("Show More Dimensions"))

        # Adjust dialog height if needed, might be automatic
        self.adjustSize()


    def load_dimensions(self):
        try:
            # Using db_manager as per original class structure for this dialog
            dimension_data = db_manager.get_product_dimension(self.product_id)
            if dimension_data:
                for dim_ui_key, input_widget in self.dimension_inputs.items(): # dim_ui_key is "dim_a" etc
                    input_widget.setText(str(dimension_data.get(dim_ui_key, ""))) # Ensure text is string

                technical_image_path_from_db = dimension_data.get('technical_image_path', '')
                self.current_tech_image_path = technical_image_path_from_db

                if technical_image_path_from_db:
                    self.tech_image_path_input.setText(technical_image_path_from_db)
                    if not self.app_root_dir:
                        print("ERROR: app_root_dir not set. Cannot form absolute path for image.")
                        self.tech_image_preview_label.setText(self.tr("Erreur configuration."))
                        return
                    absolute_image_path = os.path.join(self.app_root_dir, technical_image_path_from_db)
                    if os.path.exists(absolute_image_path):
                        pixmap = QPixmap(absolute_image_path)
                        if not pixmap.isNull():
                            self.tech_image_preview_label.setPixmap(
                                pixmap.scaled(self.tech_image_preview_label.width(),
                                              self.tech_image_preview_label.height(),
                                              Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            )
                        else: self.tech_image_preview_label.setText(self.tr("Aperçu non disponible (format invalide)."))
                    else: self.tech_image_preview_label.setText(self.tr("Image non trouvée."))
                else:
                    self.tech_image_path_input.setPlaceholderText(self.tr("Aucune image technique définie."))
                    self.tech_image_preview_label.setText(self.tr("Aucune image technique."))
                    self.current_tech_image_path = None
            else:
                for input_widget in self.dimension_inputs.values(): input_widget.clear()
                self.tech_image_path_input.clear()
                self.tech_image_preview_label.setText(self.tr("Aucune dimension pour ce produit."))
                self.current_tech_image_path = None
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Chargement Dimensions"), self.tr("Impossible de charger les dimensions: {0}").format(str(e)))
            self.current_tech_image_path = None

    def handle_browse_tech_image(self):
        initial_dir = os.path.expanduser("~")
        source_file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Sélectionner une Image Technique"), initial_dir,
            self.tr("Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        )
        if source_file_path:
            base_product_images_dir_name = "product_technical_images"
            if not self.app_root_dir:
                QMessageBox.critical(self, self.tr("Erreur Configuration"), self.tr("Le chemin racine de l'application n'est pas configuré."))
                return
            target_product_dir = os.path.join(self.app_root_dir, base_product_images_dir_name, str(self.product_id))
            try:
                os.makedirs(target_product_dir, exist_ok=True)
                image_filename = os.path.basename(source_file_path)
                absolute_target_file_path = os.path.join(target_product_dir, image_filename)
                shutil.copy2(source_file_path, absolute_target_file_path)
                relative_image_path = os.path.join(base_product_images_dir_name, str(self.product_id), image_filename).replace(os.sep, '/')
                self.tech_image_path_input.setText(relative_image_path)
                self.current_tech_image_path = relative_image_path
                pixmap = QPixmap(absolute_target_file_path)
                if not pixmap.isNull():
                    self.tech_image_preview_label.setPixmap(
                        pixmap.scaled(self.tech_image_preview_label.width(), self.tech_image_preview_label.height(),
                                      Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    self.tech_image_preview_label.setText(self.tr("Aperçu non disponible."))
                    self.current_tech_image_path = None
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur Copie Image"), self.tr("Impossible de copier l'image: {0}").format(str(e)))
                self.current_tech_image_path = None

    def accept(self):
        dimension_data_to_save = {}
        for dim_key, input_widget in self.dimension_inputs.items(): # dim_key is "dim_a"
            dimension_data_to_save[dim_key] = input_widget.text().strip()
        dimension_data_to_save['technical_image_path'] = self.current_tech_image_path
        try:
            # Using db_manager as per original class structure for this dialog
            success = db_manager.add_or_update_product_dimension(self.product_id, dimension_data_to_save)
            if success: # Assuming add_or_update_product_dimension returns boolean or equivalent
                QMessageBox.information(self, self.tr("Succès"), self.tr("Dimensions du produit enregistrées avec succès."))
                super().accept()
            else:
                QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible d'enregistrer les dimensions. Vérifiez les logs."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Enregistrement"), self.tr("Une erreur est survenue: {0}").format(str(e)))
