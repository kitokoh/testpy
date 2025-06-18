# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, QFormLayout,
    QTableWidget, QHeaderView, QTabWidget, QProgressBar, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QIcon
# Assuming db_manager is accessible (original imports retained for existing functionality)
from db import get_all_clients, get_active_clients_count, get_total_projects_count, get_active_projects_count, get_total_products_count, get_client_counts_by_country, get_client_segmentation_by_city, get_client_segmentation_by_status, get_client_segmentation_by_category
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


class CollapsibleStatisticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Basic logging setup if not configured by main app, specific to this widget's context
        if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
            logging.debug("CollapsibleStatisticsWidget initialized.")
        else:
            logging.basicConfig(level=logging.INFO)
            logging.info("CollapsibleStatisticsWidget initialized, basic logging configured.")
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
            # Total Clients
            # Using direct function calls as per this file's existing pattern for these counts
            _total_clients_list = get_all_clients()
            current_total_clients = len(_total_clients_list) if _total_clients_list else 0
            self.stats_labels["total_clients"].setText(str(current_total_clients))
            self.update_total_clients_trend(current_total_clients)

            # Active Clients
            current_active_clients = get_active_clients_count()
            self.stats_labels["active_clients"].setText(str(current_active_clients))
            self.update_active_clients_trend(current_active_clients)

            total_projects = get_total_projects_count()
            self.stats_labels["total_projects"].setText(str(total_projects))
            active_projects = get_active_projects_count()
            self.stats_labels["active_projects"].setText(str(active_projects))
            total_products = get_total_products_count()
            self.stats_labels["total_products"].setText(str(total_products))

            # Total Sales (Proforma) - Current Month
            sales_current_month = self.get_total_sales_from_proforma_current_month()
            self.stats_labels["total_sales_proforma"].setText("€ {:,.2f}".format(sales_current_month))
            self.update_total_sales_proforma_trend(sales_current_month)

        except Exception as e:
            logging.error(f"Error updating global stats in CollapsibleStatisticsWidget: {e}", exc_info=True)
            for key in self.stats_labels:
                self.stats_labels[key].setText(self.tr("Erreur"))
            # Clear trend labels specifically
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
            logging.error(f"Error calculating total sales for current month in CollapsibleStatisticsWidget: {e}", exc_info=True)
            return 0.0
        finally:
            if db_session:
                try:
                    db_session.close()
                except Exception as e:
                    logging.error(f"Error closing db_session in get_total_sales_from_proforma_current_month (CollapsibleStatisticsWidget): {e}", exc_info=True)

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
            logging.error(f"Error updating total clients trend in CollapsibleStatisticsWidget: {e}", exc_info=True)
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
            logging.error(f"Error updating active clients trend in CollapsibleStatisticsWidget: {e}", exc_info=True)
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
            logging.error(f"Error updating total sales proforma trend in CollapsibleStatisticsWidget: {e}", exc_info=True)
            self.stats_labels["total_sales_proforma_trend"].setText("")
            self.stats_labels["total_sales_proforma_trend"].setStyleSheet("")
        finally:
            if db_session:
                try:
                    db_session.close()
                except Exception as e:
                    logging.error(f"Error closing db_session in update_total_sales_proforma_trend (CollapsibleStatisticsWidget): {e}", exc_info=True)

    def _calculate_trend_text_and_style(self, current_value, previous_value, is_currency=False):
        trend_text = ""
        style = "color: gray;" # Default style
        if previous_value > 0:
            percentage_change = ((current_value - previous_value) / previous_value) * 100
            arrow = "→"
            if percentage_change > 0.5:
                arrow = "↗"
                style = "color: green;"
            elif percentage_change < -0.5:
                arrow = "↘"
                style = "color: red;"
            trend_text = f"{arrow} {percentage_change:.1f}%"
        elif current_value > 0:
            trend_text = "↗ New"
            style = "color: green;"
        else:
            trend_text = f"→ {current_value:.1f}%" if is_currency else "→ 0.0%"
            if is_currency and current_value == 0 : trend_text = "→ €0.00"
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
            logging.error(f"Error updating client acquisition stats in CollapsibleStatisticsWidget: {e}", exc_info=True)
            self.stats_labels["new_clients_last_month"].setText(self.tr("Erreur"))
            self.stats_labels["new_clients_last_quarter"].setText(self.tr("Erreur"))

    def update_business_health_score(self):
        # Basic example: score based on ratio of active clients to total clients
        try:
            total_clients_list = get_all_clients()
            total_clients_count = len(total_clients_list) if total_clients_list else 0
            active_clients_count = get_active_clients_count()

            if total_clients_count > 0:
                health_score = (active_clients_count / total_clients_count) * 100
            else:
                health_score = 0

            self.health_score_value_label.setText(f"{health_score:.0f} %")
            self.health_score_progress_bar.setValue(int(health_score))
        except Exception as e:
            logging.error(f"Error updating business health score in CollapsibleStatisticsWidget: {e}", exc_info=True)
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
        table.setSortingEnabled(False)
        table.setRowCount(0)
        try:
            data_rows = data_fetch_func()
            if data_rows is None: data_rows = []
            for row_idx, row_data in enumerate(data_rows):
                table.insertRow(row_idx)
                for col_idx, col_key in enumerate(column_keys):
                    item_value = row_data.get(col_key, "")
                    # Corrected: QTableWidget should be QTableWidgetItem
                    from PyQt5.QtWidgets import QTableWidgetItem
                    table.setItem(row_idx, col_idx, QTableWidgetItem(str(item_value)))
        except Exception as e:
            logging.error(f"Error populating table {table_key} in CollapsibleStatisticsWidget: {e}", exc_info=True)
            # Optionally show error in table or a message box
        finally:
            table.setSortingEnabled(True)

    def update_customer_segmentation_views(self):
        self._populate_table("country", get_client_counts_by_country, ["country_name", "client_count"])
        self._populate_table("city", get_client_segmentation_by_city, ["country_name", "city_name", "client_count"])
        self._populate_table("status", get_client_segmentation_by_status, ["status_name", "client_count"])
        self._populate_table("category", get_client_segmentation_by_category, ["category", "client_count"])
        self._populate_table("product_popularity", get_product_usage_counts, ["product_name", "usage_count"]) # Added

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
