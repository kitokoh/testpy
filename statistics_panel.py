# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, QFormLayout,
    QTableWidget, QHeaderView, QTabWidget, QProgressBar, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QIcon
import db as db_manager # Assuming db_manager is accessible

class CollapsibleStatisticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("collapsibleStatisticsWidget")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0) # No margins for the main layout

        self.toggle_button = QPushButton(self.tr("Afficher les Statistiques Détaillées"))
        self.toggle_button.setIcon(QIcon.fromTheme("view-reveal", QIcon(":/icons/chevron-down.svg"))) # Default icon
        self.toggle_button.setCheckable(True)
        self.toggle_button.toggled.connect(self.toggle_content_visibility)
        main_layout.addWidget(self.toggle_button)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("statisticsContentWidget")
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(5,5,5,5) # Margins for the content area

        # Placeholder for statistics elements - to be filled from StatisticsDashboard
        self._setup_statistics_ui(content_layout) # Call to setup detailed UI

        self.content_widget.setVisible(False) # Initially hidden
        self.toggle_button.setChecked(False)
        self.toggle_button.setText(self.tr("Afficher les Statistiques Détaillées"))
        self.toggle_button.setIcon(QIcon.fromTheme("view-reveal", QIcon(":/icons/chevron-down.svg")))


        main_layout.addWidget(self.content_widget)
        self.setLayout(main_layout)

        # Initial data load can be triggered here or upon first expansion
        # self.refresh_all_statistics_displays()


    def _setup_statistics_ui(self, layout_to_populate):
        # This method will recreate the UI from StatisticsDashboard's right_panel_widget

        refresh_button_layout = QHBoxLayout()
        self.refresh_stats_button = QPushButton(self.tr("Actualiser les Statistiques"))
        self.refresh_stats_button.setIcon(QIcon.fromTheme("view-refresh", QIcon(":/icons/refresh-cw.svg")))
        self.refresh_stats_button.clicked.connect(self.refresh_all_statistics_displays)
        refresh_button_layout.addStretch()
        refresh_button_layout.addWidget(self.refresh_stats_button)
        layout_to_populate.addLayout(refresh_button_layout)

        title_label = QLabel(self.tr("Statistiques Détaillées"))
        title_label.setObjectName("statisticsTitleLabel") # For styling
        title_label.setAlignment(Qt.AlignCenter)
        layout_to_populate.addWidget(title_label)

        # Global Stats GroupBox
        global_stats_group = QGroupBox(self.tr("Statistiques Globales"))
        global_stats_layout = QFormLayout(global_stats_group)
        self.stats_labels = {
            "total_clients": QLabel("0"), "active_clients": QLabel("0"),
            "total_projects": QLabel("0"), "active_projects": QLabel("0"),
            "total_products": QLabel("0")
        }
        global_stats_layout.addRow(self.tr("Nombre total de clients:"), self.stats_labels["total_clients"])
        global_stats_layout.addRow(self.tr("Nombre de clients actifs:"), self.stats_labels["active_clients"])
        global_stats_layout.addRow(self.tr("Nombre total de projets:"), self.stats_labels["total_projects"])
        global_stats_layout.addRow(self.tr("Nombre de projets actifs:"), self.stats_labels["active_projects"])
        global_stats_layout.addRow(self.tr("Nombre total de produits (BDD):"), self.stats_labels["total_products"])
        layout_to_populate.addWidget(global_stats_group)

        # Business Health Score GroupBox
        health_score_group = QGroupBox(self.tr("Indice de Santé Commerciale"))
        health_score_layout = QVBoxLayout(health_score_group)
        self.health_score_value_label = QLabel("0 %")
        self.health_score_value_label.setAlignment(Qt.AlignCenter)
        self.health_score_value_label.setObjectName("healthScoreValueLabel")
        self.health_score_progress_bar = QProgressBar()
        self.health_score_progress_bar.setRange(0, 100)
        self.health_score_progress_bar.setValue(0)
        self.health_score_progress_bar.setTextVisible(False)
        health_score_layout.addWidget(self.health_score_value_label)
        health_score_layout.addWidget(self.health_score_progress_bar)
        layout_to_populate.addWidget(health_score_group)

        # Segmentation Tabs
        self.segmentation_tabs = QTabWidget()
        self._setup_segmentation_tab_ui() # Call the helper to create tabs
        layout_to_populate.addWidget(self.segmentation_tabs)

        # Set size policy to expand vertically
        self.content_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)


    @pyqtSlot(bool)
    def toggle_content_visibility(self, checked):
        self.content_widget.setVisible(checked)
        if checked:
            self.toggle_button.setText(self.tr("Masquer les Statistiques Détaillées"))
            self.toggle_button.setIcon(QIcon.fromTheme("view-conceal", QIcon(":/icons/chevron-up.svg")))
            self.refresh_all_statistics_displays() # Refresh when shown
        else:
            self.toggle_button.setText(self.tr("Afficher les Statistiques Détaillées"))
            self.toggle_button.setIcon(QIcon.fromTheme("view-reveal", QIcon(":/icons/chevron-down.svg")))

    def collapse_panel(self):
        """Collapses the statistics panel."""
        self.content_widget.setVisible(False)
        self.toggle_button.setChecked(False) # This will also update text/icon via toggle_content_visibility
        # Ensure text/icon are explicitly set if toggle_button's signal is blocked or behavior is complex
        # self.toggle_button.setText(self.tr("Afficher les Statistiques Détaillées"))
        # self.toggle_button.setIcon(QIcon.fromTheme("view-reveal", QIcon(":/icons/chevron-down.svg")))

    def show_and_expand(self):
        """Ensures the panel is visible and expanded."""
        self.toggle_button.setChecked(True) # This will trigger toggle_content_visibility
        self.content_widget.setVisible(True) # Ensure it's visible

    def refresh_all_statistics_displays(self):
        self.update_global_stats()
        self.update_business_health_score()
        self.update_customer_segmentation_views()
        print("CollapsibleStatisticsWidget: All statistics refreshed.")

    def update_global_stats(self):
        try:
            total_clients = db_manager.get_all_clients()
            self.stats_labels["total_clients"].setText(str(len(total_clients) if total_clients else 0))

            active_clients = db_manager.get_active_clients_count()
            self.stats_labels["active_clients"].setText(str(active_clients))

            total_projects = db_manager.get_total_projects_count()
            self.stats_labels["total_projects"].setText(str(total_projects))

            active_projects = db_manager.get_active_projects_count()
            self.stats_labels["active_projects"].setText(str(active_projects))

            total_products = db_manager.get_total_products_count() # Assuming this function exists
            self.stats_labels["total_products"].setText(str(total_products))
        except Exception as e:
            print(f"Error updating global stats: {e}")
            for label in self.stats_labels.values():
                label.setText(self.tr("Erreur"))

    def update_business_health_score(self):
        # Basic example: score based on ratio of active clients to total clients
        try:
            total_clients_list = db_manager.get_all_clients()
            total_clients_count = len(total_clients_list) if total_clients_list else 0
            active_clients_count = db_manager.get_active_clients_count()

            if total_clients_count > 0:
                health_score = (active_clients_count / total_clients_count) * 100
            else:
                health_score = 0

            self.health_score_value_label.setText(f"{health_score:.0f} %")
            self.health_score_progress_bar.setValue(int(health_score))
        except Exception as e:
            print(f"Error updating business health score: {e}")
            self.health_score_value_label.setText(self.tr("Erreur"))
            self.health_score_progress_bar.setValue(0)

    def _setup_segmentation_tab_ui(self):
        self.segmentation_tables = {}
        tab_configs = [
            ("country", self.tr("Par Pays"), ["Pays", "Nombre de Clients"]),
            ("city", self.tr("Par Ville"), ["Pays", "Ville", "Nombre de Clients"]),
            ("status", self.tr("Par Statut"), ["Statut", "Nombre de Clients"]),
            ("category", self.tr("Par Catégorie"), ["Catégorie", "Nombre de Clients"]),
        ]

        for key, title, headers in tab_configs:
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            table_widget = QTableWidget()
            table_widget.setColumnCount(len(headers))
            table_widget.setHorizontalHeaderLabels(headers)
            table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
            table_widget.setSelectionBehavior(QTableWidget.SelectRows)
            table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table_widget.setSortingEnabled(True)
            tab_layout.addWidget(table_widget)
            self.segmentation_tabs.addTab(tab_widget, title)
            self.segmentation_tables[key] = table_widget

    def _populate_table(self, table_key, data_fetch_func, column_keys):
        table = self.segmentation_tables.get(table_key)
        if not table: return
        table.setSortingEnabled(False)
        table.setRowCount(0)
        try:
            data_rows = data_fetch_func()
            if data_rows is None: data_rows = []
            for row_idx, row_data in enumerate(data_rows):
                table.insertRow(row_idx)
                for col_idx, col_key in enumerate(column_keys):
                    item_value = row_data.get(col_key, "")
                    table.setItem(row_idx, col_idx, QTableWidget(str(item_value)))
        except Exception as e:
            print(f"Error populating table {table_key}: {e}")
            # Optionally show error in table or a message box
        finally:
            table.setSortingEnabled(True)

    def update_customer_segmentation_views(self):
        self._populate_table("country", db_manager.get_client_counts_by_country, ["country_name", "client_count"])
        self._populate_table("city", db_manager.get_client_segmentation_by_city, ["country_name", "city_name", "client_count"])
        self._populate_table("status", db_manager.get_client_segmentation_by_status, ["status_name", "client_count"])
        self._populate_table("category", db_manager.get_client_segmentation_by_category, ["category", "client_count"])

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    # Example usage:
    main_window_dummy = QWidget() # Dummy parent for testing
    collapsible_widget = CollapsibleStatisticsWidget(main_window_dummy)
    collapsible_widget.show()
    collapsible_widget.resize(400, 500) # Give it some size to see content

    # Test toggling and showing
    # collapsible_widget.toggle_button.setChecked(True) # Show content
    # collapsible_widget.show_and_expand()

    sys.exit(app.exec_())
