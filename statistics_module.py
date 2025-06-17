# -*- coding: utf-8 -*-
import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QSplitter, QHBoxLayout,
    QGroupBox, QFormLayout, QTableWidget, QHeaderView, QTabWidget, QProgressBar,
    QTableWidgetItem, QStackedWidget
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QIcon
from PyQt5.QtWebEngineWidgets import QWebEngineView

import json # Added for robust JS string escaping
import folium
import pandas as pd
from branca.colormap import StepColormap # Import StepColormap

from db import (
    get_total_clients_count,
    get_active_clients_count,
    get_country_by_name, # Added
    get_total_projects_count,
    get_active_projects_count,
    get_total_products_count,
    get_client_segmentation_by_city,
    get_client_segmentation_by_status,
    get_client_segmentation_by_category,
    get_client_counts_by_country,
    get_country_by_id,
    get_city_by_id,
    get_status_setting_by_id
)
# It seems db_manager is not directly imported, but functions are. If needed, import db as db_manager
from db.cruds.clients_crud import clients_crud_instance

from app_setup import APP_ROOT_DIR


class MapInteractionHandler(QObject): # Remains as it's used for the new interactive map
    country_clicked_signal = pyqtSignal(str)
    client_clicked_on_map_signal = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

    @pyqtSlot(str)
    def countryClicked(self, country_name):
        logging.info(f"MapInteractionHandler: countryClicked received: {country_name}")
        self.country_clicked_signal.emit(country_name)

    @pyqtSlot(str, str)
    def clientClickedOnMap(self, client_id, client_name):
        logging.info(f"MapInteractionHandler: clientClickedOnMap received ID: {client_id}, Name: {client_name}")
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
        # Connect client_clicked_on_map_signal to the new panel display method
        self.map_interaction_handler.client_clicked_on_map_signal.connect(self._display_client_details_in_panel)

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

    # This slot is now replaced by _display_client_details_in_panel if request_view_client_details signal is removed.
    # For now, keep it if the signal is still defined, but it won't be connected to map_interaction_handler.
    # If request_view_client_details is to be removed, this slot should also be removed or repurposed.
    # Based on instructions, the signal's connection is changed, not the signal itself removed yet.
    @pyqtSlot(str)
    def _on_map_client_clicked(self, client_id, client_name):
        # This method is kept for now in case request_view_client_details is used elsewhere,
        # but the map click will now go to _display_client_details_in_panel.
        logging.info(f"Legacy _on_map_client_clicked for {client_name} (ID: {client_id}). Emitting request_view_client_details if this signal is still used.")
        self.request_view_client_details.emit(client_id) # This signal might be deprecated for this class's map.

    def refresh_all_dashboard_content(self):
        logging.info("Refreshing all dashboard content...")
        self.refresh_statistics_data()
        self.update_map()
        logging.info("All dashboard content refresh complete.")

    # Placeholder for _setup_stats_display_ui - to be filled in Phase 2
    def _setup_stats_display_ui(self, layout_to_populate):
        self.stats_stack = QStackedWidget()
        layout_to_populate.addWidget(self.stats_stack)

        # --- Global Stats Widget ---
        self.global_stats_widget = QWidget()
        global_stats_page_layout = QVBoxLayout(self.global_stats_widget)
        # global_stats_page_layout.setContentsMargins(0,0,0,0) # Keep consistent margins or remove if parent handles

        title_label = QLabel(self.tr("Statistiques Détaillées"))
        title_label.setObjectName("statisticsTitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        global_stats_page_layout.addWidget(title_label)

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
        global_stats_page_layout.addWidget(global_stats_group)

        health_score_group = QGroupBox(self.tr("Indice de Santé Commerciale"))
        health_score_layout = QVBoxLayout(health_score_group)
        self.health_score_value_label = QLabel("0 %")
        self.health_score_value_label.setAlignment(Qt.AlignCenter)
        self.health_score_value_label.setObjectName("healthScoreValueLabel")
        self.health_score_progress_bar = QProgressBar()
        self.health_score_progress_bar.setRange(0, 100); self.health_score_progress_bar.setValue(0)
        self.health_score_progress_bar.setTextVisible(False)
        health_score_layout.addWidget(self.health_score_value_label)
        health_score_layout.addWidget(self.health_score_progress_bar)
        global_stats_page_layout.addWidget(health_score_group)

        self.segmentation_tabs = QTabWidget()
        self._setup_segmentation_tab_ui_internal()
        global_stats_page_layout.addWidget(self.segmentation_tabs)
        self.global_stats_widget.setLayout(global_stats_page_layout)
        self.stats_stack.addWidget(self.global_stats_widget)

        # --- Client Details Widget ---
        self.client_details_widget = QWidget()
        client_details_page_layout = QVBoxLayout(self.client_details_widget)

        # Title for Client Details
        client_details_title = QLabel(self.tr("Détails du Client")) # Create a title
        client_details_title.setObjectName("clientDetailsTitleLabel") # Apply styling if needed
        client_details_title.setAlignment(Qt.AlignCenter)
        client_details_page_layout.addWidget(client_details_title)

        self.client_details_layout = QFormLayout() # For displaying client info
        # self.client_details_layout.setContentsMargins(5,5,5,5)
        client_details_page_layout.addLayout(self.client_details_layout)

        client_details_page_layout.addStretch(1) # Pushes button to bottom

        self.back_to_global_stats_button = QPushButton(self.tr("Retour aux Statistiques Globales"))
        self.back_to_global_stats_button.setIcon(QIcon.fromTheme("go-previous", QIcon(":/icons/arrow-left-circle.svg")))
        self.back_to_global_stats_button.clicked.connect(self._show_global_stats_view)
        client_details_page_layout.addWidget(self.back_to_global_stats_button)

        self.client_details_widget.setLayout(client_details_page_layout)
        self.stats_stack.addWidget(self.client_details_widget)

        self.stats_stack.setCurrentWidget(self.global_stats_widget) # Show global stats by default

    def _show_global_stats_view(self):
        self.stats_stack.setCurrentWidget(self.global_stats_widget)

    @pyqtSlot(str, str)
    def _display_client_details_in_panel(self, client_id_str, client_name_str):
        logging.info(f"Displaying details for client: {client_name_str} (ID: {client_id_str}) in panel.")

        # Clear previous content from self.client_details_layout
        while self.client_details_layout.rowCount() > 0:
            self.client_details_layout.removeRow(0)

        try:
            client_data = clients_crud_instance.get_client_by_id(client_id_str, include_deleted=True)
            if not client_data:
                self.client_details_layout.addRow(QLabel(self.tr("Erreur:")), QLabel(self.tr("Client non trouvé.")))
                self.stats_stack.setCurrentWidget(self.client_details_widget)
                return

            country_name = self.tr("N/A")
            if client_data.get('country_id'):
                country_obj = get_country_by_id(client_data['country_id'])
                if country_obj: country_name = country_obj.get('country_name', self.tr("N/A"))

            city_name = self.tr("N/A")
            if client_data.get('city_id'):
                city_obj = get_city_by_id(client_data['city_id'])
                if city_obj: city_name = city_obj.get('city_name', self.tr("N/A"))

            status_name = self.tr("N/A")
            if client_data.get('status_id'):
                status_obj = get_status_setting_by_id(client_data['status_id'])
                if status_obj: status_name = status_obj.get('status_name', self.tr("N/A"))

            details_to_display = {
                self.tr("Nom Client:"): client_data.get('client_name', self.tr("N/A")),
                self.tr("Société:"): client_data.get('company_name', self.tr("N/A")) or self.tr("N/A"), # Ensure empty string becomes N/A
                self.tr("Pays:"): country_name,
                self.tr("Ville:"): city_name,
                self.tr("Statut:"): status_name,
                self.tr("Date Création:"): client_data.get('created_at_str', self.tr("N/A")), # Assuming 'created_at_str' exists
                self.tr("Besoin Principal:"): client_data.get('primary_need_description', self.tr("N/A")) or self.tr("N/A")
            }

            for label, value in details_to_display.items():
                value_label = QLabel(str(value))
                value_label.setWordWrap(True) # Allow text wrapping for longer values
                self.client_details_layout.addRow(QLabel(label), value_label)

        except Exception as e:
            logging.error(f"Error fetching/displaying client details for ID {client_id_str}: {e}", exc_info=True)
            self.client_details_layout.addRow(QLabel(self.tr("Erreur:")), QLabel(self.tr("Impossible de charger les détails du client.")))

        self.stats_stack.setCurrentWidget(self.client_details_widget)

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

            m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB positron") # Standardized casing

            if data_for_map["country_name"] and data_for_map["client_count"]:
                df = pd.DataFrame(data_for_map)

                # Define color categories and thresholds
                category_colors = ['#f0f0f0', '#c6dbef', '#6baed6', '#08519c'] # Grey, Light Blue, Medium Blue, Dark Blue
                # Index: Start of each category. [0, 1, 2, 4] means:
                #   color[0] for values in [0, 1) (i.e., 0 clients)
                #   color[1] for values in [1, 2) (i.e., 1 client)
                #   color[2] for values in [2, 4) (i.e., 2, 3 clients)
                #   color[3] for values >= 4 (i.e., 4+ clients)
                color_index = [0, 1, 2, 4]

                max_observed_clients = df["client_count"].max() if not df.empty else 0

                client_colormap = StepColormap(
                    colors=category_colors,
                    index=color_index,
                    vmin=0,
                    vmax=max(4, max_observed_clients), # Ensure colormap covers at least up to 4, or max observed
                    caption=self.tr("Client Count by Country (Categories)")
                )

                folium.Choropleth(
                    geo_data=geojson_path, name="choropleth", data=df,
                    columns=["country_name", "client_count"], key_on="feature.properties.name",
                    fill_color=client_colormap, # Use the StepColormap instance
                    fill_opacity=0.7, # Slightly more opaque for better color visibility
                    line_opacity=0.3,
                    highlight=True,
                    # legend_name removed to use the StepColormap's legend
                ).add_to(m)

                # Add the colormap itself to the map to generate the legend
                client_colormap.add_to(m)

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

                popup_html = f"<b>{country_name}</b><br>"
                popup_html += f"{self.tr('Clients (Total)')}: {country_client_count}<br><hr>"

                # Fetch and list clients by city for this country
                country_obj = get_country_by_name(country_name)
                city_client_map = {}
                if country_obj:
                    country_id = country_obj.get('country_id')
                    clients_in_country = clients_crud_instance.get_all_clients_with_details(
                        filters={'country_id': country_id},
                        include_deleted=False # Only show active clients in this list
                    )
                    if clients_in_country:
                        for client in clients_in_country:
                            city_name = client.get('city', self.tr('Ville Inconnue'))
                            client_detail_name = client.get('client_name', self.tr('Client Inconnu'))
                            client_id = client.get('client_id')

                            city_name = client.get('city', self.tr('Ville Inconnue'))
                            client_detail_name = client.get('client_name', self.tr('Client Inconnu'))
                            client_id = client.get('client_id')

                            if city_name not in city_client_map:
                                city_client_map[city_name] = []

                            if len(city_client_map[city_name]) < 3: # Limit to 3 clients per city for popup
                                city_client_map[city_name].append({
                                    'id': client_id,
                                    'name': client_detail_name
                                })

                if city_client_map:
                    for city_name_iter, clients_in_city_list in city_client_map.items():
                        popup_html += f"<b>{self.tr('Ville')}: {city_name_iter}</b> ({len(clients_in_city_list)} {self.tr('client(s) affiché(s)')})<br>"
                        popup_html += "<ul>"
                        for client_data_item in clients_in_city_list:
                            # Use json.dumps directly on the raw data for JS arguments
                            js_client_id_arg = json.dumps(client_data_item['id'])
                            js_client_name_arg = json.dumps(client_data_item['name'])
                            onclick_js = f"pyMapConnector.clientClickedOnMap({js_client_id_arg}, {js_client_name_arg}); return false;"
                            popup_html += f"<li><a href='#' onclick='{onclick_js}'>{client_data_item['name']}</a></li>"
                        popup_html += "</ul>"
                else:
                    popup_html += f"{self.tr('Aucun client détaillé à afficher pour les villes.')}<br>"

                # "Ajouter Client Ici" button
                js_country_name_arg = json.dumps(country_name)
                button_text = self.tr('Ajouter Client Ici')
                onclick_country_js = f"pyMapConnector.countryClicked({js_country_name_arg}); return false;"
                popup_html += f"<br><button onclick='{onclick_country_js}'>{button_text}</button>"

                feature['properties']['popup_content'] = popup_html

            popup_layer.add_child(folium.features.GeoJsonPopup(fields=['popup_content'], localize=True))
            popup_layer.add_to(m)

            if data_for_map["country_name"]: # Only add LayerControl if there's data
                # Check if popup_layer is defined before adding LayerControl.
                # Only add LayerControl if there's more than just the base map and choropleth.
                # The popup_layer adds interactivity, so it's a good condition.
                if 'popup_layer' in locals() and popup_layer is not None:
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

    def _setup_segmentation_tab_ui_internal(self):
        self.segmentation_tables = {} # Ensure this is initialized before use
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