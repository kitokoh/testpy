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

from db.cruds.products_crud import products_crud_instance

class ProductDimensionUIDialog(QDialog):
    def __init__(self, product_id, app_root_dir, parent=None, read_only=False): # Added app_root_dir and read_only
        super().__init__(parent)
        self.product_id = product_id
        self.app_root_dir = app_root_dir # Crucial for image path construction
        self.read_only = read_only
        self.setWindowTitle(self.tr("Gérer Dimensions Détaillées du Produit") + f" (ID: {self.product_id})")
        self.setMinimumSize(500, 600)
        self.current_tech_image_path = None # Relative path for DB
        self.setup_ui()
        self.load_dimensions()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        form_group = QGroupBox(self.tr("Dimensions Spécifiques"))
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)

        self.dimension_inputs = {}
        for dim_label_key_part in [f"{chr(65 + i)}" for i in range(10)]: # A to J
            dim_label_ui = f"dim_{dim_label_key_part}" # For UI consistency if needed, though DB uses lower e.g. dim_a
            line_edit = QLineEdit()
            self.dimension_inputs[dim_label_ui.lower()] = line_edit # Store with DB key "dim_a"
            form_layout.addRow(self.tr(f"Dimension {dim_label_key_part}:"), line_edit)
        main_layout.addWidget(form_group)

        tech_image_group = QGroupBox(self.tr("Image Technique"))
        tech_image_layout = QVBoxLayout(tech_image_group)
        path_button_layout = QHBoxLayout()
        self.tech_image_path_input = QLineEdit()
        self.tech_image_path_input.setReadOnly(True)
        self.tech_image_path_input.setPlaceholderText(self.tr("Aucune image sélectionnée"))
        path_button_layout.addWidget(self.tech_image_path_input)
        self.browse_tech_image_button = QPushButton(self.tr("Parcourir..."))
        self.browse_tech_image_button.setIcon(QIcon.fromTheme("document-open"))
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

        if self.read_only:
            for dim_input_widget in self.dimension_inputs.values():
                dim_input_widget.setReadOnly(True)
            self.browse_tech_image_button.setEnabled(False)
            save_button = self.button_box.button(QDialogButtonBox.Save)
            if save_button: save_button.setEnabled(False)
            cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
            if cancel_button: cancel_button.setText(self.tr("Fermer")) # More appropriate for read_only
        self.setLayout(main_layout)

    def load_dimensions(self):
        try:
            dimension_data = products_crud_instance.get_product_dimension(self.product_id, include_deleted_product=True)
            if dimension_data:
                for dim_db_key, input_widget in self.dimension_inputs.items(): # dim_db_key is "dim_a", etc.
                    input_widget.setText(dimension_data.get(dim_db_key, ""))

                technical_image_path_from_db = dimension_data.get('technical_image_path', '')
                self.current_tech_image_path = technical_image_path_from_db
                if technical_image_path_from_db:
                    self.tech_image_path_input.setText(technical_image_path_from_db)
                    if not self.app_root_dir:
                        print("ERROR: app_root_dir not set. Cannot form absolute path for image preview.")
                        self.tech_image_preview_label.setText(self.tr("Erreur configuration (chemin racine)."))
                        return
                    absolute_image_path = os.path.join(self.app_root_dir, technical_image_path_from_db)
                    if os.path.exists(absolute_image_path):
                        pixmap = QPixmap(absolute_image_path)
                        if not pixmap.isNull():
                            self.tech_image_preview_label.setPixmap(
                                pixmap.scaled(self.tech_image_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            )
                        else: self.tech_image_preview_label.setText(self.tr("Aperçu non disponible (format invalide)."))
                    else: self.tech_image_preview_label.setText(self.tr("Image non trouvée au chemin stocké."))
                else:
                    self.tech_image_path_input.setPlaceholderText(self.tr("Aucune image technique définie."))
                    self.tech_image_preview_label.setText(self.tr("Aucune image technique."))
                    self.current_tech_image_path = None
            else:
                for input_widget in self.dimension_inputs.values(): input_widget.clear()
                self.tech_image_path_input.clear()
                self.tech_image_path_input.setPlaceholderText(self.tr("Aucune dimension détaillée trouvée."))
                self.tech_image_preview_label.setText(self.tr("Aperçu de l'image non disponible."))
                self.current_tech_image_path = None
        except Exception as e:
            print(f"ERROR: Failed to load product dimensions for product_id {self.product_id}: {e}") # Or use logging
            QMessageBox.critical(self, self.tr("Erreur de Chargement"), self.tr("Impossible de charger les dimensions du produit:\n{0}").format(str(e)))

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
                    self.tech_image_preview_label.setPixmap(pixmap.scaled(self.tech_image_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    self.tech_image_preview_label.setText(self.tr("Aperçu non disponible (format invalide après copie)."))
                    self.current_tech_image_path = None
            except shutil.Error as e_shutil:
                QMessageBox.critical(self, self.tr("Erreur de Copie"), self.tr("Impossible de copier l'image sélectionnée : {0}").format(str(e_shutil)))
            except Exception as e_general:
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur est survenue lors du traitement de l'image : {0}").format(str(e_general)))

    def accept(self):
        if self.read_only: # If read-only, just accept to close.
            super().accept()
            return

        dimension_data_to_save = {}
        for dim_key, input_widget in self.dimension_inputs.items(): # dim_key is "dim_a", "dim_b" etc.
            dimension_data_to_save[dim_key] = input_widget.text().strip()
        dimension_data_to_save['technical_image_path'] = self.current_tech_image_path

        try:
            result = products_crud_instance.add_or_update_product_dimension(self.product_id, dimension_data_to_save)
            if result['success']:
                QMessageBox.information(self, self.tr("Succès"), self.tr("Dimensions du produit enregistrées avec succès."))
                super().accept()
            else:
                QMessageBox.warning(self, self.tr("Échec"), result.get('error', self.tr("Impossible d'enregistrer les dimensions.")))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur"), self.tr("Une erreur est survenue lors de l'enregistrement des dimensions:\n{0}").format(str(e)))
