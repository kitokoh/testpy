# -*- coding: utf-8 -*-
import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QSplitter, QHBoxLayout,
    QGroupBox, QFormLayout, QTableWidget, QHeaderView, QTabWidget, QProgressBar,
    QTableWidgetItem
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QIcon
from PyQt5.QtWebEngineWidgets import QWebEngineView

import folium
import pandas as pd

from db import (
    get_total_clients_count,
    get_active_clients_count,
    get_total_projects_count,
    get_active_projects_count,
    get_total_products_count,
    get_client_segmentation_by_city,
    get_client_segmentation_by_status,
    get_client_segmentation_by_category,
    get_client_counts_by_country
)

from app_setup import APP_ROOT_DIR


class MapInteractionHandler(QObject): # Remains as it's used for the new interactive map

    country_clicked_signal = pyqtSignal(str)
    client_clicked_on_map_signal = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

    @pyqtSlot(str)
    def countryClicked(self, country_name):

        self.country_clicked_signal.emit(country_name)

    @pyqtSlot(str, str)
    def clientClickedOnMap(self, client_id, client_name):
        self.client_clicked_on_map_signal.emit(client_id, client_name)

class StatisticsDashboard(QWidget):
    request_add_client_for_country = pyqtSignal(str)
    request_view_client_details = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Tableau de Bord Statistiques Interactif"))

        main_layout = QVBoxLayout(self)

        # Global Refresh Button
        self.global_refresh_button = QPushButton(self.tr("Rafraîchir Tout le Tableau de Bord"))
        self.global_refresh_button.setIcon(QIcon.fromTheme("view-refresh", QIcon(":/icons/refresh-cw.svg")))
        self.global_refresh_button.clicked.connect(self.refresh_all_dashboard_content)
        main_layout.addWidget(self.global_refresh_button)

        # Main horizontal splitter
        main_splitter = QSplitter(Qt.Horizontal, self)

        # Left widget for Map
        self.left_widget_for_map = QWidget()
        left_map_layout = QVBoxLayout(self.left_widget_for_map)
        left_map_layout.setContentsMargins(0,0,0,0)
        self.map_view = QWebEngineView(self)
        left_map_layout.addWidget(self.map_view)
        self.left_widget_for_map.setLayout(left_map_layout)
        main_splitter.addWidget(self.left_widget_for_map)

        # Right widget for Stats
        self.right_widget_for_stats = QWidget()
        right_stats_layout = QVBoxLayout(self.right_widget_for_stats)
        right_stats_layout.setContentsMargins(5,5,5,5)
        # self._setup_stats_display_ui(right_stats_layout) # This will be called later
        self.right_widget_for_stats.setLayout(right_stats_layout)
        main_splitter.addWidget(self.right_widget_for_stats)

        main_splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)]) # Initial sizing
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

        # Setup for interactive map
        self.map_interaction_handler = MapInteractionHandler(self)
        self.map_interaction_handler.country_clicked_signal.connect(self._on_map_country_clicked)
        self.map_interaction_handler.client_clicked_on_map_signal.connect(self._on_map_client_clicked)

        web_channel = QWebChannel(self.map_view.page())
        self.map_view.page().setWebChannel(web_channel)
        web_channel.registerObject("pyMapConnector", self.map_interaction_handler)

        # Placeholder for ported stats UI setup and initial data load
        self._setup_stats_display_ui(right_stats_layout) # Now call it
        self.refresh_all_dashboard_content()

        logging.info("StatisticsDashboard initialized with new interactive structure.")

    @pyqtSlot(str)
    def _on_map_country_clicked(self, country_name):
        logging.info(f"Map country clicked: {country_name}. Emitting request_add_client_for_country.")
        self.request_add_client_for_country.emit(country_name)

    @pyqtSlot(str) # client_name is not strictly needed by the signal but good for logging
    def _on_map_client_clicked(self, client_id, client_name):
        logging.info(f"Map client clicked: {client_name} (ID: {client_id}). Emitting request_view_client_details.")
        self.request_view_client_details.emit(client_id)

    def refresh_all_dashboard_content(self):
        logging.info("Refreshing all dashboard content...")
        self.refresh_statistics_data()
        self.update_map()
        logging.info("All dashboard content refresh complete.")

    # Placeholder for _setup_stats_display_ui - to be filled in Phase 2
    def _setup_stats_display_ui(self, layout_to_populate):
        # This will be populated with UI elements from CollapsibleStatisticsWidget
        # For now, a simple label
        # temp_label = QLabel("Stats UI will be here.")
        # layout_to_populate.addWidget(temp_label)

        # --- Ported from CollapsibleStatisticsWidget._setup_statistics_ui ---
        # No separate refresh button for stats, global refresh is used.
        # refresh_button_layout = QHBoxLayout()
        # self.refresh_stats_button = QPushButton(self.tr("Actualiser les Statistiques"))
        # self.refresh_stats_button.setIcon(QIcon.fromTheme("view-refresh", QIcon(":/icons/refresh-cw.svg")))
        # self.refresh_stats_button.clicked.connect(self.refresh_statistics_data) # Changed to internal method
        # refresh_button_layout.addStretch()
        # refresh_button_layout.addWidget(self.refresh_stats_button)
        # layout_to_populate.addLayout(refresh_button_layout)

        title_label = QLabel(self.tr("Statistiques Détaillées"))
        title_label.setObjectName("statisticsTitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        layout_to_populate.addWidget(title_label)

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

        self.segmentation_tabs = QTabWidget()
        self._setup_segmentation_tab_ui_internal() # Renamed to avoid conflict if method is also ported directly
        layout_to_populate.addWidget(self.segmentation_tabs)
        # --- End of Ported UI ---


    # Placeholder for refresh_statistics_data - to be filled in Phase 2
    def refresh_statistics_data(self):
        logging.info("Refreshing statistics data panel...")
        self.update_global_stats()
        self.update_business_health_score()
        self.update_customer_segmentation_views()
        logging.info("Statistics data panel refresh complete.")

    # Placeholder for update_map - to be filled in Phase 3
    def update_map(self):
        logging.info("Updating interactive map...")
        try:
            # Fetch data for choropleth
            clients_by_country_counts = get_client_counts_by_country()


            data_for_map = {"country_name": [], "client_count": []}
            if clients_by_country_counts:
                for entry in clients_by_country_counts:
                    data_for_map["country_name"].append(entry["country_name"])
                    data_for_map["client_count"].append(entry["client_count"])

            geojson_path = os.path.join(APP_ROOT_DIR, "assets", "world_countries.geojson")

            if not os.path.exists(geojson_path):
                logging.error(f"GeoJSON file not found at: {geojson_path}")
                m = folium.Map(location=[20,0], zoom_start=2)
                folium.Marker([0,0], popup="Error: GeoJSON file for map not found.").add_to(m)
                self.map_view.setHtml(m.get_root().render())
                return

            m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodb positron")

            if data_for_map["country_name"] and data_for_map["client_count"]:
                df = pd.DataFrame(data_for_map)
                folium.Choropleth(
                    geo_data=geojson_path, name="choropleth", data=df,
                    columns=["country_name", "client_count"], key_on="feature.properties.name",
                    fill_color="YlGnBu", fill_opacity=0.7, line_opacity=0.2,
                    legend_name=self.tr("Nombre de Clients par Pays"), highlight=True,
                ).add_to(m)

            # Fetch active client data for interactive markers/popups
            # This is a simplified version; in DocumentManager it's get_active_clients_per_country
            # For StatisticsDashboard, we might just use the same get_client_counts_by_country data
            # or fetch more detailed client data if we want to plot individual clients (can be slow).
            # For now, the popups will focus on country interaction.

            # Interactive popups for countries
            popup_layer = folium.GeoJson(
                geojson_path,
                name=self.tr("Informations Pays"),
                style_function=lambda x: {'fillColor':'transparent', 'color':'transparent', 'weight':0},
                tooltip=None # Disable default tooltip for this layer if choropleth provides enough
            )

            js_script_content = ""
            for feature in popup_layer.data.get('features', []):
                country_name = feature.get('properties', {}).get('name', 'N/A')
                if country_name == 'N/A': continue

                country_client_count = next((item['client_count'] for item in clients_by_country_counts if item['country_name'] == country_name), 0)

                # HTML for the popup
                popup_html = f"<b>{country_name}</b><br>"
                popup_html += f"{self.tr('Clients (Total)')}: {country_client_count}<br>"

                # Add client button (JS call to pyMapConnector)
                js_safe_country_name = country_name.replace("'", "\\'")
                button_text = self.tr('Ajouter Client Ici')
                popup_html += f"<button onclick='pyMapConnector.countryClicked(\"{js_safe_country_name}\")'>{button_text}</button><br>"

                # If you want to list some clients (example, adapt as needed)
                # active_clients_in_country = clients_crud_instance.get_clients_by_filters({'country_name': country_name, 'is_deleted': False}, limit=5) # Example
                # if active_clients_in_country:
                #     popup_html += f"<br><b>{self.tr('Quelques Clients Actifs')}:</b><ul>"
                #     for client in active_clients_in_country:
                #         js_safe_client_name = client['client_name'].replace("'", "\\'").replace('"', '\\"')
                #         popup_html += f"<li><a href='#' onclick='pyMapConnector.clientClickedOnMap(\"{client['client_id']}\", \"{js_safe_client_name}\")'>{client['client_name']}</a></li>"
                #     popup_html += "</ul>"

                feature['properties']['popup_content'] = popup_html

            popup_layer.add_child(folium.features.GeoJsonPopup(fields=['popup_content']))
            popup_layer.add_to(m)

            if data_for_map["country_name"]: # Only add LayerControl if there's data
                folium.LayerControl().add_to(m)

            # The JavaScript for pyMapConnector to exist.
            # Note: folium's get_root().render() wraps the map in an IFrame.
            # Direct JS injection like this might be tricky if the context is wrong.
            # QWebChannel works by injecting objects into the page's main window.
            # The onclick handlers in popups should correctly call `window.pyMapConnector.method()`.

            # No explicit JS script needed here as pyMapConnector is registered with QWebChannel.
            # The onclick attributes in the HTML popups will use this.

            self.map_view.setHtml(m.get_root().render())
            logging.info("Interactive map updated successfully.")
        except Exception as e:
            logging.error(f"Error updating interactive map: {e}", exc_info=True)
            error_map = folium.Map(location=[0,0], zoom_start=1)
            folium.Marker([0,0], popup=f"Error generating map: {e}").add_to(error_map)
            self.map_view.setHtml(error_map.get_root().render())

    # --- Methods to be ported from CollapsibleStatisticsWidget ---
    def update_global_stats(self):
        try:
            total_clients = get_total_clients_count()
            self.stats_labels["total_clients"].setText(str(total_clients))

            active_clients = get_active_clients_count()
            self.stats_labels["active_clients"].setText(str(active_clients))

            total_projects = get_total_projects_count()
            self.stats_labels["total_projects"].setText(str(total_projects))

            active_projects = get_active_projects_count()
            self.stats_labels["active_projects"].setText(str(active_projects))

            total_products = get_total_products_count()

            self.stats_labels["total_products"].setText(str(total_products))
        except Exception as e:
            logging.error(f"Error updating global stats: {e}", exc_info=True)
            for label in self.stats_labels.values():
                label.setText(self.tr("Erreur"))

    def update_business_health_score(self):
        try:
            total_clients_count = get_total_clients_count()
            active_clients_count = get_active_clients_count()


            if total_clients_count > 0:
                health_score = (active_clients_count / total_clients_count) * 100
            else:
                health_score = 0

            self.health_score_value_label.setText(f"{health_score:.0f} %")
            self.health_score_progress_bar.setValue(int(health_score))
        except Exception as e:
            logging.error(f"Error updating business health score: {e}", exc_info=True)
            self.health_score_value_label.setText(self.tr("Erreur"))
            self.health_score_progress_bar.setValue(0)

    def _setup_segmentation_tab_ui_internal(self): # Renamed
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
                    # Ensure QTableWidgetItem is used
                    table.setItem(row_idx, col_idx, QTableWidgetItem(str(item_value)))
        except Exception as e:
            logging.error(f"Error populating table {table_key}: {e}", exc_info=True)
        finally:
            table.setSortingEnabled(True)

    def update_customer_segmentation_views(self):
        self._populate_table("country", get_client_counts_by_country, ["country_name", "client_count"])
        self._populate_table("city", get_client_segmentation_by_city, ["country_name", "city_name", "client_count"])
        self._populate_table("status", get_client_segmentation_by_status, ["status_name", "client_count"])
        self._populate_table("category", get_client_segmentation_by_category, ["category", "client_count"])

    # --- End of Ported Methods ---
        # The old update_statistics_map method (which was the display-only map) is now removed.
        # self.update_map() is the current method for the interactive map.
