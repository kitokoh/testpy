# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QApplication,
                             QGridLayout, QGroupBox, QProgressBar,
                             QHBoxLayout, QScrollArea, QTabWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QPushButton) # Added QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView  # ✅ BON MODULE
from PyQt5.QtGui import QIcon # Added QIcon
from PyQt5.QtCore import Qt, QUrl
import db as db_manager
import folium
import io
import os
import json
import requests
import pandas as pd

class StatisticsDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Tableau de Bord Statistiques"))

        self.main_h_layout = QHBoxLayout(self)
        self.main_h_layout.setContentsMargins(10, 10, 10, 10)
        self.main_h_layout.setSpacing(10)

        self.map_view = QWebEngineView()
        self.map_view.setMinimumHeight(400)
        self.map_view.setObjectName("presenceMapView")
        map_group_box = QGroupBox(self.tr("Carte de Présence"))
        map_group_box.setObjectName("mapGroupBox")
        map_group_layout = QVBoxLayout(map_group_box)
        map_group_layout.addWidget(self.map_view)
        map_group_layout.setContentsMargins(5,5,5,5)
        self.main_h_layout.addWidget(map_group_box, 2)

        self.right_scroll_area = QScrollArea()
        self.right_scroll_area.setWidgetResizable(True)
        self.right_scroll_area.setObjectName("statsScrollArea")
        self.right_panel_widget = QWidget()
        self.right_panel_widget.setObjectName("statsRightPanelWidget")
        self.right_panel_layout = QVBoxLayout(self.right_panel_widget)
        self.right_panel_layout.setAlignment(Qt.AlignTop)
        self.right_panel_layout.setSpacing(15)

        # --- Refresh Button ---
        refresh_section_layout = QHBoxLayout()
        self.refresh_button = QPushButton(self.tr("Actualiser"))
        self.refresh_button.setObjectName("refreshStatsButton")
        refresh_icon = QIcon(":/icons/refresh-cw.svg")
        if not refresh_icon.isNull():
            self.refresh_button.setIcon(refresh_icon)
        else:
            print("Warning: Refresh icon ':/icons/refresh-cw.svg' not found.")
        self.refresh_button.setToolTip(self.tr("Actualiser toutes les données statistiques"))
        self.refresh_button.clicked.connect(self.refresh_all_statistics) # Connect signal
        refresh_section_layout.addStretch()
        refresh_section_layout.addWidget(self.refresh_button)
        self.right_panel_layout.addLayout(refresh_section_layout)

        title_label = QLabel(self.tr("Statistiques Détaillées"))
        title_label.setObjectName("statisticsTitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        self.right_panel_layout.addWidget(title_label)

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
        self.right_panel_layout.addWidget(global_stats_group)

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
        self.right_panel_layout.addWidget(health_score_group)

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
        self.right_panel_layout.addWidget(segmentation_group)

        self.right_scroll_area.setWidget(self.right_panel_widget)
        self.main_h_layout.addWidget(self.right_scroll_area, 1)

        self.refresh_all_statistics() # Initial data load

    def refresh_all_statistics(self):
        print("Refreshing all statistics...")
        self.update_global_stats()
        self.update_presence_map()
        self.update_business_health_score()
        self.update_customer_segmentation_views()
        print("All statistics refreshed.")

    def _setup_segmentation_tab_ui(self):
        layout_country = QVBoxLayout(self.country_segment_tab)
        self.table_segment_country = QTableWidget()
        self.table_segment_country.setColumnCount(2)
        self.table_segment_country.setHorizontalHeaderLabels([self.tr("Pays"), self.tr("Nombre de Clients")])
        self.table_segment_country.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_segment_country.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_segment_country.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_segment_country.setAlternatingRowColors(True)
        layout_country.addWidget(self.table_segment_country)

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

        layout_status = QVBoxLayout(self.status_segment_tab)
        self.table_segment_status = QTableWidget()
        self.table_segment_status.setColumnCount(2)
        self.table_segment_status.setHorizontalHeaderLabels([self.tr("Statut"), self.tr("Nombre de Clients")])
        self.table_segment_status.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_segment_status.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_segment_status.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_segment_status.setAlternatingRowColors(True)
        layout_status.addWidget(self.table_segment_status)

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
        table_widget.setSortingEnabled(False)
        for row_idx, data_item in enumerate(data_list):
            table_widget.insertRow(row_idx)
            for col_idx, (key, _) in enumerate(column_keys_info):
                item_value = data_item.get(key)
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
            for table in [self.table_segment_country, self.table_segment_city, self.table_segment_status, self.table_segment_category]:
                table.setRowCount(1)
                table.setColumnCount(1)
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
            tile_style = "cartodbpositron"
            world_map = folium.Map(location=[20, 0], zoom_start=2, tiles=tile_style)

            if not client_counts_by_country:
                map_html_data = io.BytesIO()
                world_map.save(map_html_data, close_file=False)
                html_content = map_html_data.getvalue().decode("utf-8")
                self.map_view.setHtml(html_content, QUrl("about:blank"))
                return

            local_geojson_file = "assets/world_countries.geojson"
            geojson_data = None

            if os.path.exists(local_geojson_file) and os.path.getsize(local_geojson_file) > 0:
                try:
                    with open(local_geojson_file, 'r', encoding='utf-8') as f:
                        geojson_data = json.load(f)
                    print("Loaded GeoJSON data from local file: assets/world_countries.geojson")
                except Exception as e:
                    print(f"Error loading local GeoJSON file: {e}. Will attempt to fetch from URL.")
                    geojson_data = None

            if not geojson_data:
                country_geo_url = "https://raw.githubusercontent.com/python-visualization/folium/main/examples/data/world-countries.json"
                print(f"Attempting to fetch GeoJSON from URL: {country_geo_url}")
                try:
                    response = requests.get(country_geo_url, timeout=10)
                    response.raise_for_status()
                    geojson_data = response.json()
                    print("Successfully fetched GeoJSON from URL.")
                    try:
                        os.makedirs(os.path.dirname(local_geojson_file), exist_ok=True)
                        with open(local_geojson_file, 'w', encoding='utf-8') as f_save:
                            json.dump(geojson_data, f_save)
                        print(f"Saved fetched GeoJSON to {local_geojson_file} for future use.")
                    except Exception as e_save:
                        print(f"Could not save fetched GeoJSON locally: {e_save}")
                except requests.exceptions.RequestException as e:
                    print(f"Could not download GeoJSON data from URL: {e}.")

            if not geojson_data:
                self.map_view.setHtml(self.tr("Erreur: Données GeoJSON non disponibles. Impossible d'afficher la carte."))
                print("Critical error: GeoJSON data is not available. Map cannot be displayed.")
                return

            df_counts = pd.DataFrame(client_counts_by_country)
            tooltip_data = {row['country_name']: row['client_count'] for _, row in df_counts.iterrows()}

            choropleth_layer = folium.Choropleth(
                geo_data=geojson_data,
                name="choropleth", data=df_counts,
                columns=["country_name", "client_count"], key_on="feature.properties.name",
                fill_color="YlGnBu", fill_opacity=0.7, line_opacity=0.2,
                legend_name=self.tr("Nombre de Clients par Pays"), nan_fill_color='lightgray',
                highlight=True,
            ).add_to(world_map)

            for feature in geojson_data['features']:
                country_name_prop = feature['properties'].get('name')
                client_count_prop = tooltip_data.get(country_name_prop, 0)
                feature['properties']['client_count'] = client_count_prop

            folium.GeoJsonTooltip(
                fields=['name', 'client_count'],
                aliases=['Pays:', self.tr('Nb. Clients:')],
                localize=True, sticky=False, labels=True,
                style="background-color: #F0EFEF; border: 2px solid black; border-radius: 3px; box-shadow: 3px;"
            ).add_to(choropleth_layer.geojson)

            folium.LayerControl().add_to(world_map)

            map_html_data = io.BytesIO()
            world_map.save(map_html_data, close_file=False)
            html_content = map_html_data.getvalue().decode("utf-8")
            self.map_view.setHtml(html_content, QUrl("about:blank"))

        except ImportError:
            self.map_view.setHtml(self.tr("Erreur: Librairies 'folium', 'pandas', ou 'requests' manquantes."))
            print("ImportError: Folium, Pandas, or Requests might be missing for map display.")
        except Exception as e:
            error_html = f"<h1>{self.tr('Erreur de chargement de la carte')}</h1><p>{str(e)}</p>"
            self.map_view.setHtml(error_html)
            print(f"Error updating presence map: {e}")

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
        print("StatisticsDashboard closeEvent triggered.")
        super().closeEvent(event)

    def showEvent(self, event):
        """
        Called when the widget is shown.
        Overrides QWidget.showEvent().
        """
        print("StatisticsDashboard is now visible, refreshing all statistics...") # For debugging
        self.refresh_all_statistics()
        super().showEvent(event) # Call the base class implementation

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    db_manager.initialize_database()

    try:
        print("Populating dummy data for testing if necessary...")
    except Exception as e:
        print(f"Error during __main__ dummy data setup: {e}")

    app.setStyleSheet("""
        #statisticsTitleLabel { font-size: 20px; font-weight: bold; margin-bottom: 15px; }
        #healthScoreValueLabel { font-size: 20px; font-weight: bold; color: #17a2b8; margin-top: 5px; margin-bottom: 5px;}
        #refreshStatsButton {
            font-weight: bold;
            padding: 5px 10px; /* Reduced padding */
            margin-bottom: 5px; /* Reduced margin */
            min-width: 90px;
        }
        QProgressBar {
            border: 1px solid #cccccc;
            border-radius: 5px;
            text-align: center;
            height: 22px;
            margin-top: 5px;
        }
        QProgressBar::chunk {
            background-color: #28a745;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #cccccc;
            border-radius: 5px;
            margin-top: 12px;
            padding: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 3px 8px;
            left: 10px;
            background-color: #f0f0f0;
            border-radius: 3px;
        }
        QLabel { font-size: 13px; padding: 4px; }
        QLabel[objectName^="statValue_"] {
            font-weight: bold;
            color: #007bff;
            font-size: 14px;
            padding: 4px;
        }
        QTableWidget {
            border: 1px solid #dcdcdc;
            alternate-background-color: #f9f9f9;
        }
        QTableWidget::item { padding: 5px; }
        QHeaderView::section {
            background-color: #e9ecef;
            padding: 5px;
            border: 1px solid #d0d0d0;
            font-weight: bold;
            font-size: 13px;
        }
        QTabWidget::pane {
            border: 1px solid #dcdcdc;
            border-top: none;
            padding: 10px;
        }
        QTabBar::tab {
            padding: 8px 15px;
            border: 1px solid #dcdcdc;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            background-color: #f0f0f0;
            margin-right: 2px;
            font-size: 13px;
        }
        QTabBar::tab:selected {
            background-color: #ffffff;
            border-bottom: 1px solid #ffffff;
        }
        QTabBar::tab:hover:!selected { background-color: #e2e6ea; }
        #statsScrollArea { border: none; }
        #statsRightPanelWidget { background-color: transparent; }
        QGroupBox#mapGroupBox {
             padding: 5px;
        }
        #presenceMapView {
            border: 1px solid #cccccc;
            border-radius: 4px;
        }
    """)

    main_widget = StatisticsDashboard()
    main_widget.resize(1200, 700)
    main_widget.show()
    sys.exit(app.exec_())