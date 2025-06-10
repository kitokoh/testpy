# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QApplication, QGridLayout,
                             QGroupBox, QProgressBar, QTabWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl
import db as db_manager
import folium
import io
import os
import tempfile
import pandas as pd

class StatisticsDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Tableau de Bord Statistiques"))
        self.map_temp_file_path = None

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)

        title_label = QLabel(self.tr("Module Statistiques")) # Main title for the whole dashboard
        title_label.setObjectName("statisticsTitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # --- Global Stats Section ---
        global_stats_group = QGroupBox(self.tr("Aperçu Global"))
        global_stats_layout = QGridLayout(global_stats_group)
        self.stats_labels = {}
        stats_to_show = [
            (0, 0, self.tr("Nombre total de clients:"), "get_total_clients_count"),
            (0, 1, self.tr("Nombre de clients actifs:"), "get_active_clients_count"),
            (1, 0, self.tr("Nombre total de projets:"), "get_total_projects_count"),
            (1, 1, self.tr("Nombre de projets actifs:"), "get_active_projects_count"),
            (2, 0, self.tr("Nombre total de produits:"), "get_total_products_count"),
        ]
        for r, c, label_text, func_name in stats_to_show:
            text_label = QLabel(label_text)
            value_label = QLabel(self.tr("Chargement..."))
            value_label.setObjectName(f"statValue_{func_name}")
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            global_stats_layout.addWidget(text_label, r, c * 2)
            global_stats_layout.addWidget(value_label, r, c * 2 + 1)
            self.stats_labels[func_name] = value_label
        global_stats_layout.setColumnStretch(1, 1)
        global_stats_layout.setColumnStretch(3, 1)
        main_layout.addWidget(global_stats_group)

        # --- Presence Map Section ---
        presence_map_group = QGroupBox(self.tr("Carte de Présence Client"))
        presence_map_layout = QVBoxLayout(presence_map_group)
        self.map_view = QWebEngineView()
        self.map_view.setMinimumHeight(300)
        presence_map_layout.addWidget(self.map_view)
        main_layout.addWidget(presence_map_group)

        # --- Business Health Score Section ---
        health_score_group = QGroupBox(self.tr("Score de Santé de l'Entreprise"))
        health_score_layout = QVBoxLayout(health_score_group)
        self.health_score_value_label = QLabel(self.tr("Calcul..."))
        self.health_score_value_label.setObjectName("healthScoreValueLabel")
        self.health_score_value_label.setAlignment(Qt.AlignCenter)
        health_score_layout.addWidget(self.health_score_value_label)
        self.health_score_progress_bar = QProgressBar()
        self.health_score_progress_bar.setRange(0, 100)
        self.health_score_progress_bar.setTextVisible(False)
        self.health_score_progress_bar.setFixedHeight(20)
        health_score_layout.addWidget(self.health_score_progress_bar)
        main_layout.addWidget(health_score_group)

        # --- Customer Segmentation Section ---
        segmentation_group = QGroupBox(self.tr("Segmentation des Clients"))
        segmentation_main_layout = QVBoxLayout(segmentation_group)
        self.segmentation_tabs = QTabWidget()
        segmentation_main_layout.addWidget(self.segmentation_tabs)

        self.country_segment_tab = QWidget()
        self.city_segment_tab = QWidget()
        self.status_segment_tab = QWidget()
        self.category_segment_tab = QWidget()

        self.segmentation_tabs.addTab(self.country_segment_tab, self.tr("Par Pays"))
        self.segmentation_tabs.addTab(self.city_segment_tab, self.tr("Par Ville"))
        self.segmentation_tabs.addTab(self.status_segment_tab, self.tr("Par Statut"))
        self.segmentation_tabs.addTab(self.category_segment_tab, self.tr("Par Catégorie"))

        self._setup_segmentation_tab_ui()
        main_layout.addWidget(segmentation_group)

        self.setLayout(main_layout)

        self.update_global_stats()
        self.update_presence_map()
        self.update_business_health_score()
        self.update_customer_segmentation_views()

    def _setup_segmentation_tab_ui(self):
        # Country Segmentation Tab
        layout_country = QVBoxLayout(self.country_segment_tab)
        self.table_segment_country = QTableWidget()
        self.table_segment_country.setColumnCount(2)
        self.table_segment_country.setHorizontalHeaderLabels([self.tr("Pays"), self.tr("Nombre de Clients")])
        self.table_segment_country.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_segment_country.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_segment_country.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_segment_country.setAlternatingRowColors(True)
        layout_country.addWidget(self.table_segment_country)

        # City Segmentation Tab
        layout_city = QVBoxLayout(self.city_segment_tab)
        self.table_segment_city = QTableWidget()
        self.table_segment_city.setColumnCount(3)
        self.table_segment_city.setHorizontalHeaderLabels([self.tr("Pays"), self.tr("Ville"), self.tr("Nombre de Clients")])
        self.table_segment_city.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_segment_city.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_segment_city.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_segment_city.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_segment_city.setAlternatingRowColors(True)
        layout_city.addWidget(self.table_segment_city)

        # Status Segmentation Tab
        layout_status = QVBoxLayout(self.status_segment_tab)
        self.table_segment_status = QTableWidget()
        self.table_segment_status.setColumnCount(2)
        self.table_segment_status.setHorizontalHeaderLabels([self.tr("Statut"), self.tr("Nombre de Clients")])
        self.table_segment_status.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_segment_status.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_segment_status.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_segment_status.setAlternatingRowColors(True)
        layout_status.addWidget(self.table_segment_status)

        # Category Segmentation Tab
        layout_category = QVBoxLayout(self.category_segment_tab)
        self.table_segment_category = QTableWidget()
        self.table_segment_category.setColumnCount(2)
        self.table_segment_category.setHorizontalHeaderLabels([self.tr("Catégorie"), self.tr("Nombre de Clients")])
        self.table_segment_category.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_segment_category.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_segment_category.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_segment_category.setAlternatingRowColors(True)
        layout_category.addWidget(self.table_segment_category)

    def _populate_table(self, table_widget, data_list, column_keys_info):
        table_widget.setRowCount(0)
        table_widget.setSortingEnabled(False) # Turn off sorting during population for performance
        for row_idx, data_item in enumerate(data_list):
            table_widget.insertRow(row_idx)
            for col_idx, (key, _) in enumerate(column_keys_info): # Use _ for label as it's for header
                item_value = data_item.get(key) # Get value using key
                if item_value is None: item_value = self.tr("N/A")

                table_item = QTableWidgetItem(str(item_value))
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                if isinstance(item_value, (int, float)):
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    table_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table_widget.setItem(row_idx, col_idx, table_item)
        table_widget.setSortingEnabled(True)

    def update_customer_segmentation_views(self):
        try:
            country_data = db_manager.get_client_counts_by_country()
            self._populate_table(self.table_segment_country, country_data, [('country_name', self.tr("Pays")), ('client_count', self.tr("Nombre de Clients"))])

            city_data = db_manager.get_client_segmentation_by_city()
            self._populate_table(self.table_segment_city, city_data, [('country_name', self.tr("Pays")), ('city_name', self.tr("Ville")), ('client_count', self.tr("Nombre de Clients"))])

            status_data = db_manager.get_client_segmentation_by_status()
            self._populate_table(self.table_segment_status, status_data, [('status_name', self.tr("Statut")), ('client_count', self.tr("Nombre de Clients"))])

            category_data = db_manager.get_client_segmentation_by_category()
            self._populate_table(self.table_segment_category, category_data, [('category', self.tr("Catégorie")), ('client_count', self.tr("Nombre de Clients"))])
        except Exception as e:
            print(f"Error updating customer segmentation views: {e}")
            # Display error in each tab's table as a single row
            for table in [self.table_segment_country, self.table_segment_city, self.table_segment_status, self.table_segment_category]:
                table.setRowCount(1)
                table.setColumnCount(1) # Merge columns for error
                error_item = QTableWidgetItem(self.tr("Erreur de chargement des données."))
                error_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(0,0, error_item)
                table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)


    def update_global_stats(self):
        for func_name, label_widget in self.stats_labels.items():
            if hasattr(db_manager, func_name):
                try:
                    db_function = getattr(db_manager, func_name)
                    value = db_function()
                    label_widget.setText(str(value))
                except Exception as e:
                    print(f"Error calling {func_name}: {e}")
                    label_widget.setText(self.tr("Erreur"))
            else:
                label_widget.setText(self.tr("N/A"))

    def update_presence_map(self):
        try:
            client_counts_by_country = db_manager.get_client_counts_by_country()
            world_map = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")
            if not client_counts_by_country:
                map_html_data = io.BytesIO()
                world_map.save(map_html_data, close_file=False)
                self.map_view.setHtml(map_html_data.getvalue().decode())
                return
            country_geo_url = ("https://raw.githubusercontent.com/python-visualization/folium/main/examples/data/world-countries.json")
            df_counts = pd.DataFrame(client_counts_by_country)
            folium.Choropleth(
                geo_data=country_geo_url, name="choropleth", data=df_counts,
                columns=["country_name", "client_count"], key_on="feature.properties.name",
                fill_color="YlGnBu", fill_opacity=0.7, line_opacity=0.2,
                legend_name=self.tr("Nombre de Clients par Pays"), nan_fill_color='lightgray'
            ).add_to(world_map)
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as tmp_file:
                world_map.save(tmp_file.name)
                if self.map_temp_file_path and os.path.exists(self.map_temp_file_path):
                    try: os.unlink(self.map_temp_file_path)
                    except OSError: print(f"Could not delete old temp map file: {self.map_temp_file_path}")
                self.map_temp_file_path = tmp_file.name
            self.map_view.setUrl(QUrl.fromLocalFile(self.map_temp_file_path))
        except ImportError:
            self.map_view.setHtml(self.tr("Erreur: Librairies 'folium' ou 'pandas' manquantes."))
        except Exception as e:
            self.map_view.setHtml(f"<h1>{self.tr('Erreur de chargement de la carte')}</h1><p>{str(e)}</p>")

    def update_business_health_score(self):
        try:
            total_clients = db_manager.get_total_clients_count()
            active_clients = db_manager.get_active_clients_count()
            total_projects = db_manager.get_total_projects_count()
            active_projects = db_manager.get_active_projects_count()
            client_activity_score = (active_clients / total_clients) * 100 if total_clients > 0 else 0
            project_success_score = (active_projects / total_projects) * 100 if total_projects > 0 else 0
            client_base_target = 50
            client_base_score = min((total_clients / client_base_target) * 100, 100) if total_clients > 0 else 0
            overall_health_score = round((client_activity_score * 0.33) + (project_success_score * 0.33) + (client_base_score * 0.34))
            self.health_score_value_label.setText(f"{self.tr('Score Global:')} {overall_health_score}/100")
            self.health_score_progress_bar.setValue(int(overall_health_score))
            if overall_health_score < 40: self.health_score_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #dc3545; }")
            elif overall_health_score < 70: self.health_score_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #ffc107; }")
            else: self.health_score_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #28a745; }")
        except Exception as e:
            self.health_score_value_label.setText(self.tr("Erreur de calcul du score"))
            if hasattr(self, 'health_score_progress_bar'):
                self.health_score_progress_bar.setValue(0)
                self.health_score_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: gray; }")
            print(f"Error calculating business health score: {e}")

    def closeEvent(self, event):
        if self.map_temp_file_path and os.path.exists(self.map_temp_file_path):
            try:
                os.unlink(self.map_temp_file_path)
            except Exception as e:
                print(f"Error deleting temporary map file: {e}")
        super().closeEvent(event)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    db_manager.initialize_database()

    # --- Dummy Data Population for Testing ---
    try:
        conn_check = db_manager.get_db_connection()
        cursor_check = conn_check.cursor()
        try:
            cursor_check.execute("SELECT 1 FROM Countries LIMIT 1") # Check if Countries table can be queried
            countries_table_exists = cursor_check.fetchone()
        except db_manager.sqlite3.Error:
            countries_table_exists = None

        if countries_table_exists:
            # Add Countries if they don't exist
            country_ids = {}
            country_names = {"France_StatsTest": "France", "Germany_StatsTest": "Germany", "USA_StatsTest": "United States of America"}
            for k_name, actual_name in country_names.items():
                c_id = db_manager.add_country({'country_name': actual_name}) # add_country handles existing
                if c_id: country_ids[k_name] = c_id

            # Add Cities, linking to countries
            city_ids = {}
            if country_ids.get("France_StatsTest"):
                city_ids["Paris_StatsTest"] = db_manager.add_city({'country_id': country_ids["France_StatsTest"], 'city_name': 'Paris'})
            if country_ids.get("Germany_StatsTest"):
                city_ids["Berlin_StatsTest"] = db_manager.add_city({'country_id': country_ids["Germany_StatsTest"], 'city_name': 'Berlin'})
            if country_ids.get("USA_StatsTest"):
                 city_ids["NewYork_StatsTest"] = db_manager.add_city({'country_id': country_ids["USA_StatsTest"], 'city_name': 'New York'})


            # Add Statuses if they don't exist
            status_ids = {}
            status_names = {"Active_StatsTest": "Actif", "Prospect_StatsTest": "Prospect", "Inactive_StatsTest": "Inactif"}
            for k_name, actual_name in status_names.items():
                # Assuming get_status_setting_by_name and add_status_setting exist
                # For now, using known default IDs or adding them if a full status manager were here.
                # Simplified: Fetch default ones or use IDs from initialize_database's defaults
                status_obj = db_manager.get_status_setting_by_name(actual_name, 'Client')
                if status_obj: status_ids[k_name] = status_obj['status_id']
                # Else, would need an add_status_setting function here. For testing, rely on init.

            # Add Clients with city, status, category
            if country_ids.get("France_StatsTest") and city_ids.get("Paris_StatsTest") and status_ids.get("Active_StatsTest"):
                db_manager.add_client({'client_name': 'FR Client Paris Active', 'country_id': country_ids["France_StatsTest"], 'city_id': city_ids["Paris_StatsTest"], 'status_id': status_ids["Active_StatsTest"], 'category': 'VIP', 'project_identifier': 'fr_vip_01', 'company_name': 'FR VIP Inc.'})
            if country_ids.get("Germany_StatsTest") and city_ids.get("Berlin_StatsTest") and status_ids.get("Prospect_StatsTest"):
                db_manager.add_client({'client_name': 'DE Client Berlin Prospect', 'country_id': country_ids["Germany_StatsTest"], 'city_id': city_ids["Berlin_StatsTest"], 'status_id': status_ids["Prospect_StatsTest"], 'category': 'Standard', 'project_identifier': 'de_std_01', 'company_name': 'DE Standard GmbH'})
            if country_ids.get("USA_StatsTest") and city_ids.get("NewYork_StatsTest") and status_ids.get("Active_StatsTest"):
                 db_manager.add_client({'client_name': 'US Client NY Active', 'country_id': country_ids["USA_StatsTest"], 'city_id': city_ids["NewYork_StatsTest"], 'status_id': status_ids["Active_StatsTest"], 'category': 'VIP', 'project_identifier': 'us_vip_01', 'company_name': 'US VIP LLC'})
                 db_manager.add_client({'client_name': 'US Client Other Active', 'country_id': country_ids["USA_StatsTest"], 'city_id': None, 'status_id': status_ids["Active_StatsTest"], 'category': 'Standard', 'project_identifier': 'us_std_02', 'company_name': 'US Standard Corp'}) # No city
            if status_ids.get("Inactive_StatsTest"): # Client with Inactive status
                 db_manager.add_client({'client_name': 'Generic Client Inactive', 'country_id': None, 'city_id': None, 'status_id': status_ids["Inactive_StatsTest"], 'category': 'Standard', 'project_identifier': 'gen_inac_01', 'company_name': 'Old Times Ltd'})


            # Add Projects for score testing (simplified)
            clients = db_manager.get_all_clients()
            project_statuses = db_manager.get_all_status_settings(status_type='Project')
            if clients and project_statuses:
                active_proj_status = next((s['status_id'] for s in project_statuses if not s['is_archival_status'] and not s['is_completion_status']), None)
                completed_proj_status = next((s['status_id'] for s in project_statuses if s['is_completion_status']), None)
                if active_proj_status:
                    db_manager.add_project({'client_id': clients[0]['client_id'], 'project_name': 'Dummy Project Active 1', 'status_id': active_proj_status})
                if completed_proj_status and len(clients) > 1:
                     db_manager.add_project({'client_id': clients[1]['client_id'], 'project_name': 'Dummy Project Completed', 'status_id': completed_proj_status})
            print("Dummy data for segmentation and score testing added/verified.")
        else:
            print("DB tables (e.g., Countries) not found or not ready. Skipping detailed dummy data population.")
        conn_check.close()
    except Exception as e:
        print(f"Error during __main__ dummy data setup: {e}")

    app.setStyleSheet("""
    #statisticsTitleLabel { font-size: 20px; font-weight: bold; margin-bottom: 15px; }
    #healthScoreValueLabel { font-size: 22px; font-weight: bold; color: #17a2b8; margin-top: 5px; margin-bottom: 5px;}
    QGroupBox { font-weight: bold; border: 1px solid #cccccc; border-radius: 4px; margin-top: 10px; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px 0 3px; left: 10px; }
    QLabel { font-size: 13px; padding: 4px; }
    QLabel[objectName^="statValue_"] { font-weight: bold; color: #007bff; }
    QProgressBar { border: 1px solid grey; border-radius: 5px; text-align: center; height: 20px; }
    QProgressBar::chunk { background-color: #28a745; }
    QTabWidget::pane { border-top: 1px solid #cccccc; }
    QTableWidget { border: 1px solid #cccccc; selection-behavior: selectRows; }
    QHeaderView::section { background-color: #f0f0f0; padding: 4px; border: 1px solid #cccccc; font-size: 13px; font-weight: bold;}
    """)

    main_widget = StatisticsDashboard()
    main_widget.resize(800, 800) # Adjusted height for new tabs
    main_widget.show()
    sys.exit(app.exec_())
