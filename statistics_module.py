# -*- coding: utf-8 -*-
import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QSplitter, QHBoxLayout)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWebEngineWidgets import QWebEngineView

import folium
import pandas as pd # For map data manipulation

from statistics_panel import CollapsibleStatisticsWidget
from db.cruds.clients_crud import clients_crud_instance
from app_setup import APP_ROOT_DIR # For path construction

# This MapInteractionHandler is for the DocumentManager's interactive map.
# It's kept here if other parts of statistics_module might still reference it,
# but StatisticsDashboard will not use it for its display-only map.
class MapInteractionHandler(QObject):
    country_clicked_signal = pyqtSignal(str)
    client_clicked_on_map_signal = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

    @pyqtSlot(str)
    def countryClicked(self, country_name):
        # print(f"[MapInteractionHandler] countryClicked slot called with: {country_name}")
        self.country_clicked_signal.emit(country_name)

    @pyqtSlot(str, str)
    def clientClickedOnMap(self, client_id, client_name):
        # print(f"[MapInteractionHandler] clientClickedOnMap slot called with ID: {client_id}, Name: {client_name}")
        self.client_clicked_on_map_signal.emit(client_id, client_name)

class StatisticsDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Tableau de Bord Statistiques"))

        main_layout = QVBoxLayout(self)

        # Refresh Button
        self.refresh_button = QPushButton(self.tr("Rafraîchir les Données"))
        self.refresh_button.clicked.connect(self.refresh_dashboard_data)

        # Top layout for button
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.refresh_button)
        top_layout.addStretch() # Pushes button to the left
        main_layout.addLayout(top_layout)

        # Splitter for Stats Panel and Map
        splitter = QSplitter(Qt.Vertical, self)

        self.stats_panel = CollapsibleStatisticsWidget(self)
        splitter.addWidget(self.stats_panel)

        self.map_view = QWebEngineView(self)
        splitter.addWidget(self.map_view)

        splitter.setSizes([int(self.height() * 0.4), int(self.height() * 0.6)]) # Initial sizing

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        self.refresh_dashboard_data() # Initial data load
        logging.info("StatisticsDashboard initialized with new UI.")

    def refresh_dashboard_data(self):
        logging.info("Refreshing Statistics Dashboard data...")
        if hasattr(self.stats_panel, 'refresh_all_statistics_displays'):
            self.stats_panel.refresh_all_statistics_displays()
        else:
            logging.warning("stats_panel does not have 'refresh_all_statistics_displays' method.")
        self.update_statistics_map()
        logging.info("Statistics Dashboard data refresh complete.")

    def update_statistics_map(self):
        logging.info("Updating statistics map...")
        try:
            clients_by_country_counts = clients_crud_instance.get_client_counts_by_country(include_deleted=False)

            data_for_map = {"country_name": [], "client_count": []}
            if clients_by_country_counts:
                for entry in clients_by_country_counts:
                    data_for_map["country_name"].append(entry["country_name"])
                    data_for_map["client_count"].append(entry["client_count"])

            geojson_path = os.path.join(APP_ROOT_DIR, "assets", "world_countries.geojson")

            if not os.path.exists(geojson_path):
                logging.error(f"GeoJSON file not found at: {geojson_path}")
                # Display a simple map with an error message or just a blank map
                m = folium.Map(location=[20,0], zoom_start=2)
                folium.Marker([0,0], popup="Error: GeoJSON file for map not found.").add_to(m)
                self.map_view.setHtml(m.get_root().render())
                return

            m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodb positron")

            if data_for_map["country_name"] and data_for_map["client_count"]: # Check if there's data to plot
                df = pd.DataFrame(data_for_map)

                folium.Choropleth(
                    geo_data=geojson_path,
                    name="choropleth",
                    data=df,
                    columns=["country_name", "client_count"],
                    key_on="feature.properties.name", # Make sure this matches your GeoJSON properties
                    fill_color="YlGnBu",
                    fill_opacity=0.7,
                    line_opacity=0.2,
                    legend_name=self.tr("Nombre de Clients par Pays"),
                    highlight=True, # Enable highlighting of features on mouseover
                ).add_to(m)

                # Add tooltips to show country name and client count
                style_function = lambda x: {'fillColor': '#ffffff',
                                            'color':'#000000',
                                            'fillOpacity': 0.1,
                                            'weight': 0.1}
                highlight_function = lambda x: {'fillColor': '#000000',
                                                'color':'#000000',
                                                'fillOpacity': 0.50,
                                                'weight': 0.1}

                tooltip_layer = folium.features.GeoJson(
                    geojson_path,
                    style_function=style_function,
                    control=False,
                    highlight_function=highlight_function,
                    tooltip=folium.features.GeoJsonTooltip(
                        fields=['name'], # Assuming 'name' is the property for country name in GeoJSON
                        aliases=['Pays:'],
                        style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
                    )
                )
                m.add_child(tooltip_layer)
                m.keep_in_front(tooltip_layer)
                folium.LayerControl().add_to(m)

            else:
                logging.info("No client data by country to display on the map or GeoJSON is missing name property.")
                # Add a simple marker or message if no data
                folium.Marker([0,0], popup=self.tr("Aucune donnée client par pays disponible pour la carte.")).add_to(m)

            self.map_view.setHtml(m.get_root().render())
            logging.info("Statistics map updated successfully.")
        except Exception as e:
            logging.error(f"Error updating statistics map: {e}", exc_info=True)
            # Display a simple map with an error message
            error_map = folium.Map(location=[0,0], zoom_start=1)
            folium.Marker([0,0], popup=f"Error generating map: {e}").add_to(error_map)
            self.map_view.setHtml(error_map.get_root().render())
