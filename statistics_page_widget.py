# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, QFormLayout,
    QTableWidget, QHeaderView, QTabWidget, QProgressBar, QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import db as db_manager # Assuming db_manager is accessible
import logging # Added for logging

# Imports for proforma sales
from db.connection import get_db_session
from db.cruds.proforma_invoices_crud import list_proforma_invoices

# Imports for client acquisition stats
from datetime import datetime
from dateutil.relativedelta import relativedelta
from db.cruds.clients_crud import clients_crud_instance

# Import for product popularity
from db.cruds.client_project_products_crud import get_product_usage_counts

# Imports for trends and new sales logic
from PyQt5.QtWidgets import QHBoxLayout # Ensure QHBoxLayout is imported
from db import get_db_session # Assuming this is the correct SQLAlchemy session provider
from db.cruds.proforma_invoices_crud import get_total_sales_amount_for_period


class StatisticsPageWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        if logging.getLogger().getEffectiveLevel() == logging.DEBUG: # Basic check if logging is configured
             logging.debug("StatisticsPageWidget initialized.")
        else: # Fallback if no root logger config
            logging.basicConfig(level=logging.INFO) # Ensure some basic logging
            logging.info("StatisticsPageWidget initialized, basic logging configured.")
        self.setObjectName("StatisticsPageWidget")

        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout) # Set the layout for the widget itself

        # Call _setup_statistics_ui to populate the main layout directly
        self._setup_statistics_ui(main_layout)

        # Initial data load can be triggered here or connected to a showEvent
        self.refresh_all_statistics_displays()

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
            "total_clients": QLabel("0"),
            "active_clients": QLabel("0"),
            "total_projects": QLabel("0"),
            "active_projects": QLabel("0"),
            "total_products": QLabel("0"),
            "total_sales_proforma": QLabel("0"),
            "new_clients_last_month": QLabel("0"),
            "new_clients_last_quarter": QLabel("0"),
            "total_clients_trend": QLabel(""),
            "active_clients_trend": QLabel(""),
            "total_sales_proforma_trend": QLabel("")
        }

        # Total Clients with Trend
        total_clients_main_layout = QHBoxLayout()
        total_clients_main_layout.addWidget(self.stats_labels["total_clients"])
        total_clients_main_layout.addSpacing(10)
        self.stats_labels["total_clients_trend"].setObjectName("trendLabel")
        total_clients_main_layout.addWidget(self.stats_labels["total_clients_trend"])
        total_clients_main_layout.addStretch()
        global_stats_layout.addRow(self.tr("Nombre total de clients:"), total_clients_main_layout)

        # Active Clients with Trend
        active_clients_main_layout = QHBoxLayout()
        active_clients_main_layout.addWidget(self.stats_labels["active_clients"])
        active_clients_main_layout.addSpacing(10)
        self.stats_labels["active_clients_trend"].setObjectName("trendLabel")
        active_clients_main_layout.addWidget(self.stats_labels["active_clients_trend"])
        active_clients_main_layout.addStretch()
        global_stats_layout.addRow(self.tr("Nombre de clients actifs:"), active_clients_main_layout)

        global_stats_layout.addRow(self.tr("Nombre total de projets:"), self.stats_labels["total_projects"])
        global_stats_layout.addRow(self.tr("Nombre de projets actifs:"), self.stats_labels["active_projects"])
        global_stats_layout.addRow(self.tr("Nombre total de produits (BDD):"), self.stats_labels["total_products"])

        # Total Sales (Proforma) with Trend
        total_sales_proforma_main_layout = QHBoxLayout()
        total_sales_proforma_main_layout.addWidget(self.stats_labels["total_sales_proforma"])
        total_sales_proforma_main_layout.addSpacing(10)
        self.stats_labels["total_sales_proforma_trend"].setObjectName("trendLabel")
        total_sales_proforma_main_layout.addWidget(self.stats_labels["total_sales_proforma_trend"])
        total_sales_proforma_main_layout.addStretch()
        global_stats_layout.addRow(self.tr("Total Ventes (Proforma):"), total_sales_proforma_main_layout)

        global_stats_layout.addRow(self.tr("Nouveaux Clients (Mois Dernier):"), self.stats_labels["new_clients_last_month"])
        global_stats_layout.addRow(self.tr("Nouveaux Clients (Trimestre Dernier):"), self.stats_labels["new_clients_last_quarter"])
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

        # Set size policy to expand vertically - Applied to the widget itself if it's the main content
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    def refresh_all_statistics_displays(self):
        self.update_global_stats()
        self.update_business_health_score()
        self.update_customer_segmentation_views()
        print("StatisticsPageWidget: All statistics refreshed.")

    def update_global_stats(self):
        try:
            # Total Clients
            # Assuming db_manager.get_all_clients() returns a list and its length is the total.
            # For consistency with `statistics_module.py`, we should use `get_total_clients_count` if it exists in db_manager
            # or directly from `clients_crud_instance` if `db_manager` is just an alias or less direct.
            # Let's assume `db_manager.get_total_clients_count()` is preferred if available and matches the intent.
            # If `db_manager` is an older pattern, using `clients_crud_instance.get_total_clients_count(include_deleted=False)` might be more direct.
            # For now, sticking to existing pattern for this widget for this specific line:
            _total_clients_list = db_manager.get_all_clients() # This might fetch all data, inefficient
            current_total_clients = len(_total_clients_list) if _total_clients_list else 0
            self.stats_labels["total_clients"].setText(str(current_total_clients))
            self.update_total_clients_trend(current_total_clients)

            # Active Clients
            current_active_clients = db_manager.get_active_clients_count()
            self.stats_labels["active_clients"].setText(str(current_active_clients))
            self.update_active_clients_trend(current_active_clients)

            # Other stats remain as they were
            total_projects = db_manager.get_total_projects_count()
            self.stats_labels["total_projects"].setText(str(total_projects))
            active_projects = db_manager.get_active_projects_count()
            self.stats_labels["active_projects"].setText(str(active_projects))
            total_products = db_manager.get_total_products_count()
            self.stats_labels["total_products"].setText(str(total_products))

            # Total Sales (Proforma) - Current Month
            sales_current_month = self.get_total_sales_from_proforma_current_month()
            self.stats_labels["total_sales_proforma"].setText("€ {:,.2f}".format(sales_current_month))
            self.update_total_sales_proforma_trend(sales_current_month)

        except Exception as e:
            logging.error(f"Error updating global stats in StatisticsPageWidget: {e}", exc_info=True)
            for key in self.stats_labels:
                self.stats_labels[key].setText(self.tr("Erreur"))
            # Clear trend labels specifically if not covered by loop or if keys changed
            self.stats_labels["total_clients_trend"].setText("")
            self.stats_labels["active_clients_trend"].setText("")
            self.stats_labels["total_sales_proforma_trend"].setText("")

        self.update_client_acquisition_stats()


    def get_total_sales_from_proforma_current_month(self) -> float:
        """Fetches total sales from proforma invoices for the current calendar month."""
        db_session = None
        try:
            today = datetime.utcnow().date()
            start_of_current_month = today.replace(day=1)
            end_of_current_month = (today.replace(day=1) + relativedelta(months=1)) - relativedelta(days=1)
            start_iso = start_of_current_month.strftime('%Y-%m-%dT00:00:00.000000Z')
            end_iso = end_of_current_month.strftime('%Y-%m-%dT23:59:59.999999Z')

            db_session = get_db_session() # Using the imported session provider
            current_month_sales = get_total_sales_amount_for_period(db_session, start_iso, end_iso)
            return current_month_sales
        except Exception as e:
            logging.error(f"Error calculating total sales for current month in StatisticsPageWidget: {e}", exc_info=True)
            return 0.0
        finally:
            if db_session:
                try:
                    db_session.close()
                except Exception as e:
                    logging.error(f"Error closing db_session in get_total_sales_from_proforma_current_month (StatisticsPageWidget): {e}", exc_info=True)

    def update_total_clients_trend(self, current_total_clients: int):
        try:
            today = datetime.utcnow().date()
            end_of_last_month_date = today.replace(day=1) - relativedelta(days=1)
            end_of_last_month_iso = end_of_last_month_date.strftime('%Y-%m-%dT23:59:59.999999Z')
            previous_total_clients = clients_crud_instance.get_total_clients_count_up_to_date(end_of_last_month_iso)
            trend_text, style = self._calculate_trend_text_and_style(current_total_clients, previous_total_clients)
            self.stats_labels["total_clients_trend"].setText(trend_text)
            self.stats_labels["total_clients_trend"].setStyleSheet(style)
        except Exception as e:
            logging.error(f"Error updating total clients trend in StatisticsPageWidget: {e}", exc_info=True)
            self.stats_labels["total_clients_trend"].setText("")
            self.stats_labels["total_clients_trend"].setStyleSheet("")

    def update_active_clients_trend(self, current_active_clients: int):
        try:
            today = datetime.utcnow().date()
            end_of_last_month_date = today.replace(day=1) - relativedelta(days=1)
            end_of_last_month_iso = end_of_last_month_date.strftime('%Y-%m-%dT23:59:59.999999Z')
            previous_active_clients = clients_crud_instance.get_active_clients_count_up_to_date(end_of_last_month_iso)
            trend_text, style = self._calculate_trend_text_and_style(current_active_clients, previous_active_clients)
            self.stats_labels["active_clients_trend"].setText(trend_text)
            self.stats_labels["active_clients_trend"].setStyleSheet(style)
        except Exception as e:
            logging.error(f"Error updating active clients trend in StatisticsPageWidget: {e}", exc_info=True)
            self.stats_labels["active_clients_trend"].setText("")
            self.stats_labels["active_clients_trend"].setStyleSheet("")

    def update_total_sales_proforma_trend(self, current_month_sales: float):
        db_session = None
        try:
            today = datetime.utcnow().date()
            end_of_last_month_date = today.replace(day=1) - relativedelta(days=1)
            start_of_last_month_date = end_of_last_month_date.replace(day=1)
            start_prev_month_iso = start_of_last_month_date.strftime('%Y-%m-%dT00:00:00.000000Z')
            end_prev_month_iso = end_of_last_month_date.strftime('%Y-%m-%dT23:59:59.999999Z')

            db_session = get_db_session()
            previous_month_total_sales = get_total_sales_amount_for_period(db_session, start_prev_month_iso, end_prev_month_iso)
            trend_text, style = self._calculate_trend_text_and_style(current_month_sales, previous_month_total_sales, is_currency=True)
            self.stats_labels["total_sales_proforma_trend"].setText(trend_text)
            self.stats_labels["total_sales_proforma_trend"].setStyleSheet(style)
        except Exception as e:
            logging.error(f"Error updating total sales proforma trend in StatisticsPageWidget: {e}", exc_info=True)
            self.stats_labels["total_sales_proforma_trend"].setText("")
            self.stats_labels["total_sales_proforma_trend"].setStyleSheet("")
        finally:
            if db_session:
                try:
                    db_session.close()
                except Exception as e:
                    logging.error(f"Error closing db_session in update_total_sales_proforma_trend (StatisticsPageWidget): {e}", exc_info=True)

    def _calculate_trend_text_and_style(self, current_value, previous_value, is_currency=False):
        trend_text = ""
        style = "color: gray;" # Default style
        if previous_value > 0: # Avoid division by zero
            percentage_change = ((current_value - previous_value) / previous_value) * 100
            arrow = "→"
            if percentage_change > 0.5:
                arrow = "↗"
                style = "color: green;"
            elif percentage_change < -0.5:
                arrow = "↘"
                style = "color: red;"
            trend_text = f"{arrow} {percentage_change:.1f}%"
        elif current_value > 0: # Current is > 0 but previous was 0 or N/A
            trend_text = "↗ New"
            style = "color: green;"
        else: # Both current and previous are 0 (or current is 0 and previous was 0)
            trend_text = f"→ {current_value:.1f}%" if is_currency else "→ 0.0%"
            # For currency, if current is 0, showing 0.0% might be fine or show absolute 0.
            # For non-currency, 0.0% is fine.
            if is_currency and current_value == 0 : trend_text = "→ €0.00" # Or some other indicator for zero currency
            elif current_value == 0 : trend_text = "→ 0"


        return trend_text, style

    def update_client_acquisition_stats(self):
        """Updates labels for new clients acquired in the last month and last quarter."""
        try:
            today = datetime.utcnow().date()

            # Last Month Calculation
            end_of_last_month_date = today.replace(day=1) - relativedelta(days=1)
            start_of_last_month_date = end_of_last_month_date.replace(day=1)

            start_of_last_month_iso = start_of_last_month_date.strftime('%Y-%m-%dT00:00:00.000000Z')
            end_of_last_month_iso = end_of_last_month_date.strftime('%Y-%m-%dT23:59:59.999999Z')

            count_last_month = clients_crud_instance.get_clients_count_created_between(
                start_date_iso=start_of_last_month_iso,
                end_date_iso=end_of_last_month_iso
            )
            self.stats_labels["new_clients_last_month"].setText(str(count_last_month))

            # Last Quarter Calculation
            current_quarter = (today.month - 1) // 3 + 1

            if current_quarter == 1:
                start_of_last_quarter_date = datetime(today.year - 1, 10, 1).date()
                end_of_last_quarter_date = datetime(today.year - 1, 12, 31).date()
            else:
                start_month_of_last_quarter = 3 * (current_quarter - 2) + 1
                end_month_of_last_quarter = 3 * (current_quarter - 1)

                start_of_last_quarter_date = datetime(today.year, start_month_of_last_quarter, 1).date()

                if end_month_of_last_quarter < 12:
                    last_day_of_end_month = (datetime(today.year, end_month_of_last_quarter + 1, 1).date() - relativedelta(days=1)).day
                else:
                    last_day_of_end_month = 31
                end_of_last_quarter_date = datetime(today.year, end_month_of_last_quarter, last_day_of_end_month).date()

            start_of_last_quarter_iso = start_of_last_quarter_date.strftime('%Y-%m-%dT00:00:00.000000Z')
            end_of_last_quarter_iso = end_of_last_quarter_date.strftime('%Y-%m-%dT23:59:59.999999Z')

            count_last_quarter = clients_crud_instance.get_clients_count_created_between(
                start_date_iso=start_of_last_quarter_iso,
                end_date_iso=end_of_last_quarter_iso
            )
            self.stats_labels["new_clients_last_quarter"].setText(str(count_last_quarter))

        except Exception as e:
            logging.error(f"Error updating client acquisition stats in StatisticsPageWidget: {e}", exc_info=True)
            self.stats_labels["new_clients_last_month"].setText(self.tr("Erreur"))
            self.stats_labels["new_clients_last_quarter"].setText(self.tr("Erreur"))

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
            logging.error(f"Error updating business health score in StatisticsPageWidget: {e}", exc_info=True)
            self.health_score_value_label.setText(self.tr("Erreur"))
            self.health_score_progress_bar.setValue(0)

    def _setup_segmentation_tab_ui(self):
        self.segmentation_tables = {}
        tab_configs = [
            ("country", self.tr("Par Pays"), ["Pays", "Nombre de Clients"]),
            ("city", self.tr("Par Ville"), ["Pays", "Ville", "Nombre de Clients"]),
            ("status", self.tr("Par Statut"), ["Statut", "Nombre de Clients"]),
            ("category", self.tr("Par Catégorie"), ["Catégorie", "Nombre de Clients"]),
            ("product_popularity", self.tr("Par Popularité Produit"), [self.tr("Nom Produit"), self.tr("Nombre d'Utilisations")]) # Added
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
        table.setSortingEnabled(False) # Disable sorting during population
        table.setRowCount(0) # Clear existing rows
        try:
            data_rows = data_fetch_func()
            if data_rows is None: data_rows = [] # Ensure data_rows is iterable

            for row_idx, row_data in enumerate(data_rows):
                table.insertRow(row_idx)
                for col_idx, col_key in enumerate(column_keys):
                    # Ensure row_data is a dictionary and col_key exists
                    if isinstance(row_data, dict):
                        item_value = row_data.get(col_key, "")
                    else:
                        # Fallback or error handling if row_data is not a dict
                        # This might happen if data_fetch_func returns a list of tuples/lists
                        # For now, assume it's an index-based access or skip
                        try:
                            item_value = row_data[col_idx] # Simplistic fallback
                        except (IndexError, TypeError):
                            item_value = "" # Or handle error appropriately

                    # Create QTableWidgetItem with the string representation of item_value
                    # Corrected: QTableWidget should be QTableWidgetItem
                    from PyQt5.QtWidgets import QTableWidgetItem
                    table.setItem(row_idx, col_idx, QTableWidgetItem(str(item_value)))
        except Exception as e:
            logging.error(f"Error populating table {table_key} in StatisticsPageWidget: {e}", exc_info=True)
            # Optionally, display an error message in the table or a dialog
        finally:
            table.setSortingEnabled(True) # Re-enable sorting

    def update_customer_segmentation_views(self):
        # Assuming db_manager functions are updated to return list of dicts
        # or _populate_table is robust enough to handle different data structures.
        # Corrected: self_populate_table to self._populate_table
        self._populate_table("country", db_manager.get_client_counts_by_country, ["country_name", "client_count"])
        self._populate_table("city", db_manager.get_client_segmentation_by_city, ["country_name", "city_name", "client_count"])
        self._populate_table("status", db_manager.get_client_segmentation_by_status, ["status_name", "client_count"])
        self._populate_table("category", db_manager.get_client_segmentation_by_category, ["category", "client_count"])
        self._populate_table("product_popularity", get_product_usage_counts, ["product_name", "usage_count"]) # Added

if __name__ == '__main__':
    import sys
    # Ensure QApplication instance exists
    app = QApplication.instance() # Check if an instance already exists
    if not app: # Create one if it doesn't
        app = QApplication(sys.argv)

    # Example usage:
    statistics_page = StatisticsPageWidget()
    statistics_page.setWindowTitle("Standalone Statistics Page Test")
    statistics_page.show()
    statistics_page.resize(600, 700) # Adjust size as needed

    # To make the script executable and keep the window open
    if not QApplication.instance(): # Should not happen if correctly initialized above
        sys.exit(app.exec_())
    else:
        # If running in an environment that already has an event loop (e.g. Jupyter, Spyder)
        # you might not need app.exec_() here.
        # For standalone script, ensure event loop is running.
        # If app was newly created, we need to start the event loop.
        if len(sys.argv) > 1 and sys.argv[0] == __file__: # A basic check if script is run directly
             sys.exit(app.exec_())
        pass # If imported or run in an existing Qt loop, do nothing more.
