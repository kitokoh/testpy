# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit,
    QPushButton, QDialogButtonBox, QMessageBox, QLabel,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QGroupBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from db.cruds.products_crud import products_crud_instance

class ProductEquivalencyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Gérer les Équivalences de Produits"))
        self.setMinimumSize(900, 700)

        self.current_selected_product_a_id = None
        self.current_selected_product_a_info = {}
        self.current_selected_product_b_id = None
        self.current_selected_product_b_info = {}

        self.setup_ui()
        self.load_equivalencies()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        display_group = QGroupBox(self.tr("Équivalences Existantes"))
        display_layout = QVBoxLayout(display_group)

        self.equivalencies_table = QTableWidget()
        self.equivalencies_table.setColumnCount(7)
        self.equivalencies_table.setHorizontalHeaderLabels([
            "Equiv. ID", "ID Prod. A", self.tr("Produit A"), self.tr("Langue A"),
            "ID Prod. B", self.tr("Produit B"), self.tr("Langue B")
        ])
        self.equivalencies_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.equivalencies_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.equivalencies_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.equivalencies_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.equivalencies_table.hideColumn(0)
        self.equivalencies_table.hideColumn(1)
        self.equivalencies_table.hideColumn(4)
        self.equivalencies_table.itemSelectionChanged.connect(self._update_button_states)
        display_layout.addWidget(self.equivalencies_table)

        refresh_remove_layout = QHBoxLayout()
        self.refresh_button = QPushButton(self.tr("Actualiser la Liste"))
        self.refresh_button.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_button.clicked.connect(self.load_equivalencies)
        refresh_remove_layout.addWidget(self.refresh_button)

        self.remove_button = QPushButton(self.tr("Supprimer l'Équivalence Sélectionnée"))
        self.remove_button.setIcon(QIcon.fromTheme("list-remove"))
        self.remove_button.setObjectName("dangerButton")
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self.remove_selected_equivalency)
        refresh_remove_layout.addWidget(self.remove_button)
        display_layout.addLayout(refresh_remove_layout)
        main_layout.addWidget(display_group)

        add_group = QGroupBox(self.tr("Ajouter Nouvelle Équivalence"))
        add_layout = QGridLayout(add_group)

        add_layout.addWidget(QLabel(self.tr("Produit A:")), 0, 0)
        self.search_product_a_input = QLineEdit()
        self.search_product_a_input.setPlaceholderText(self.tr("Rechercher Produit A..."))
        self.search_product_a_input.textChanged.connect(self.search_product_a)
        add_layout.addWidget(self.search_product_a_input, 1, 0)
        self.results_product_a_list = QListWidget()
        self.results_product_a_list.itemClicked.connect(self.select_product_a)
        add_layout.addWidget(self.results_product_a_list, 2, 0)
        self.selected_product_a_label = QLabel(self.tr("Aucun produit A sélectionné"))
        add_layout.addWidget(self.selected_product_a_label, 3, 0)

        add_layout.addWidget(QLabel(self.tr("Produit B:")), 0, 1)
        self.search_product_b_input = QLineEdit()
        self.search_product_b_input.setPlaceholderText(self.tr("Rechercher Produit B..."))
        self.search_product_b_input.textChanged.connect(self.search_product_b)
        add_layout.addWidget(self.search_product_b_input, 1, 1)
        self.results_product_b_list = QListWidget()
        self.results_product_b_list.itemClicked.connect(self.select_product_b)
        add_layout.addWidget(self.results_product_b_list, 2, 1)
        self.selected_product_b_label = QLabel(self.tr("Aucun produit B sélectionné"))
        add_layout.addWidget(self.selected_product_b_label, 3, 1)

        self.add_equivalency_button = QPushButton(self.tr("Ajouter Équivalence"))
        self.add_equivalency_button.setIcon(QIcon.fromTheme("list-add"))
        self.add_equivalency_button.setObjectName("primaryButton")
        self.add_equivalency_button.setEnabled(False)
        self.add_equivalency_button.clicked.connect(self.add_new_equivalency)
        add_layout.addWidget(self.add_equivalency_button, 4, 0, 1, 2)
        main_layout.addWidget(add_group)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.button(QDialogButtonBox.Close).setText(self.tr("Fermer"))
        self.button_box.rejected.connect(self.reject) # reject is appropriate for Close on a non-modal or info dialog
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

    def _update_button_states(self):
        self.remove_button.setEnabled(bool(self.equivalencies_table.selectedItems()))
        self.add_equivalency_button.setEnabled(
            self.current_selected_product_a_id is not None and \
            self.current_selected_product_b_id is not None
        )

    def load_equivalencies(self):
        self.equivalencies_table.setRowCount(0)
        try:
            equivalencies = products_crud_instance.get_all_product_equivalencies(include_deleted_products=False)
            for eq_data in equivalencies:
                row_pos = self.equivalencies_table.rowCount()
                self.equivalencies_table.insertRow(row_pos)

                name_a_item = QTableWidgetItem(eq_data.get('product_name_a', 'N/A'))
                # Store equivalence_id in UserRole of the first visible item for easy access on selection
                name_a_item.setData(Qt.UserRole, eq_data.get('equivalence_id'))

                self.equivalencies_table.setItem(row_pos, 0, QTableWidgetItem(str(eq_data.get('equivalence_id',''))))
                self.equivalencies_table.setItem(row_pos, 1, QTableWidgetItem(str(eq_data.get('product_id_a',''))))
                self.equivalencies_table.setItem(row_pos, 2, name_a_item)
                self.equivalencies_table.setItem(row_pos, 3, QTableWidgetItem(eq_data.get('language_code_a', 'N/A')))
                self.equivalencies_table.setItem(row_pos, 4, QTableWidgetItem(str(eq_data.get('product_id_b',''))))
                self.equivalencies_table.setItem(row_pos, 5, QTableWidgetItem(eq_data.get('product_name_b', 'N/A')))
                self.equivalencies_table.setItem(row_pos, 6, QTableWidgetItem(eq_data.get('language_code_b', 'N/A')))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Chargement"), self.tr("Impossible de charger les équivalences: {0}").format(str(e)))
        self._update_button_states()

    def remove_selected_equivalency(self):
        selected_items = self.equivalencies_table.selectedItems()
        if not selected_items: return

        # Get equivalence_id from the UserRole data of the first item in the selected row (e.g., name_a_item)
        # Assuming column 2 (Product A Name) holds the item with UserRole for equivalence_id
        selected_row = self.equivalencies_table.currentRow()
        item_for_id = self.equivalencies_table.item(selected_row, 2) # Product A Name item
        if not item_for_id:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de récupérer l'ID d'équivalence."))
            return
        equivalence_id = item_for_id.data(Qt.UserRole)
        if equivalence_id is None:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("ID d'équivalence non trouvé pour la ligne sélectionnée."))
            return


        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"),
                                     self.tr("Êtes-vous sûr de vouloir supprimer cette équivalence (ID: {0})?").format(equivalence_id),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                remove_result = products_crud_instance.remove_product_equivalence(equivalence_id)
                if remove_result['success']:
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Équivalence supprimée avec succès."))
                else:
                    QMessageBox.warning(self, self.tr("Erreur DB"), remove_result.get('error', self.tr("Échec de la suppression de l'équivalence.")))
            except Exception as e:
                 QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de la suppression: {0}").format(str(e)))
            finally:
                self.load_equivalencies()

    def _search_products(self, search_text, list_widget):
        list_widget.clear()
        if not search_text or len(search_text) < 2: return
        try:
            products = products_crud_instance.get_all_products_for_selection_filtered(name_pattern=f"%{search_text}%", include_deleted=False)
            for prod in products:
                item_text = f"{prod.get('product_name')} ({prod.get('language_code')}) - ID: {prod.get('product_id')}"
                list_item = QListWidgetItem(item_text) # QListWidgetItem needed here
                list_item.setData(Qt.UserRole, prod)
                list_widget.addItem(list_item)
        except Exception as e:
            print(f"Error searching products: {e}")

    def search_product_a(self):
        self._search_products(self.search_product_a_input.text(), self.results_product_a_list)

    def search_product_b(self):
        self._search_products(self.search_product_b_input.text(), self.results_product_b_list)

    def _select_product(self, item, label_widget, target_id_attr, target_info_attr):
        if not item: return
        product_data = item.data(Qt.UserRole)
        if product_data:
            setattr(self, target_id_attr, product_data.get('product_id'))
            info_dict = {'name': product_data.get('product_name'), 'lang': product_data.get('language_code')}
            setattr(self, target_info_attr, info_dict)
            label_widget.setText(self.tr("Sélectionné: {0} ({1})").format(info_dict['name'], info_dict['lang']))
        self._update_button_states()

    def select_product_a(self, item):
        self._select_product(item, self.selected_product_a_label,
                             'current_selected_product_a_id', 'current_selected_product_a_info')

    def select_product_b(self, item):
        self._select_product(item, self.selected_product_b_label,
                             'current_selected_product_b_id', 'current_selected_product_b_info')

    def add_new_equivalency(self):
        if self.current_selected_product_a_id is None or self.current_selected_product_b_id is None:
            QMessageBox.warning(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner les deux produits pour créer une équivalence."))
            return
        if self.current_selected_product_a_id == self.current_selected_product_b_id:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Un produit ne peut pas être équivalent à lui-même."))
            return
        try:
            add_eq_result = products_crud_instance.add_product_equivalence(
                self.current_selected_product_a_id, self.current_selected_product_b_id
            )
            if add_eq_result['success']:
                QMessageBox.information(self, self.tr("Succès"), self.tr("Équivalence ajoutée avec succès (ID: {0}).").format(add_eq_result.get('id', 'N/A')))
                self.load_equivalencies()
                self.current_selected_product_a_id = None; self.current_selected_product_a_info = {}
                self.selected_product_a_label.setText(self.tr("Aucun produit A sélectionné"))
                self.search_product_a_input.clear(); self.results_product_a_list.clear()
                self.current_selected_product_b_id = None; self.current_selected_product_b_info = {}
                self.selected_product_b_label.setText(self.tr("Aucun produit B sélectionné"))
                self.search_product_b_input.clear(); self.results_product_b_list.clear()
            else:
                QMessageBox.warning(self, self.tr("Échec"), add_eq_result.get('error', self.tr("Impossible d'ajouter l'équivalence. Elle existe peut-être déjà ou une erreur s'est produite.")))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de l'ajout de l'équivalence: {0}").format(str(e)))
        finally:
            self._update_button_states()
