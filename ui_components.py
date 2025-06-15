# -*- coding: utf-8 -*-
import os
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QGroupBox,
    QStyledItemDelegate, QStyleOptionViewItem, QStyle # QListWidgetItem was not used directly here
)
from PyQt5.QtGui import QFont, QColor, QIcon
from PyQt5.QtCore import Qt, QRect
import db as db_manager # Used by both classes

# --- UI Components ---

class MyScoreWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("myScoreWidget") # For styling if needed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5) # Compact margins

        self.title_label = QLabel(self.tr("My Score"))
        title_font = QFont("Arial", 12, QFont.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        self.score_label = QLabel("0")
        score_font = QFont("Arial", 20, QFont.Bold) # Larger font for the score
        self.score_label.setFont(score_font)
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setObjectName("myScoreValueLabel") # For specific styling
        layout.addWidget(self.score_label)

        # To make it behave more like the QGroupBoxes in StatisticsWidget,
        # we can wrap this widget's content in a QGroupBox look-alike or ensure
        # it has a border through stylesheets if desired, or just add it as is.
        # For simplicity, adding as is. Can be wrapped in QGroupBox in StatisticsWidget if needed.

    def update_score(self):
        try:
            active_clients_count = db_manager.get_active_clients_count()
            self.score_label.setText(str(active_clients_count))
        except Exception as e:
            print(f"Error updating My Score: {e}")
            self.score_label.setText(self.tr("Error"))


class StatisticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self); layout.setContentsMargins(10, 5, 10, 5)
        # Titles are UI text, values are data
        stat_items_data = [
            (self.tr("Clients Totaux"), "total_label", "0", None),
            (self.tr("Valeur Totale"), "value_label", "0 €", None), # Currency format
            (self.tr("Projets en Cours"), "ongoing_label", "0", None),
            (self.tr("Projets Urgents"), "urgent_label", "0", "color: #e74c3c;")
        ]
        for title, attr_name, default_text, style_info in stat_items_data: # style renamed to style_info
            group = QGroupBox(title); group.setObjectName("statisticsGroup")
            group_layout = QVBoxLayout(group)
            label = QLabel(default_text) # Default text is data-like here (a number)
            label.setFont(QFont("Arial", 16, QFont.Bold)); label.setAlignment(Qt.AlignCenter)

            if attr_name == "urgent_label":
                label.setObjectName("urgentStatisticLabel")
            else:
                label.setObjectName("statisticValueLabel")

            setattr(self, attr_name, label)
            group_layout.addWidget(label); layout.addWidget(group)

        # Add MyScoreWidget
        # Option 1: MyScoreWidget is self-contained and added directly
        # self.my_score_widget = MyScoreWidget()
        # layout.addWidget(self.my_score_widget)

        # Option 2: Wrap MyScoreWidget in a QGroupBox to match other stats
        self.my_score_group = QGroupBox(self.tr("My Score")) # Title for the group box
        self.my_score_group.setObjectName("statisticsGroup") # Use same object name for styling
        my_score_group_layout = QVBoxLayout(self.my_score_group)
        self.my_score_widget_internal = MyScoreWidget()
        # Remove title from MyScoreWidget if GroupBox provides it, or adjust MyScoreWidget
        # For now, MyScoreWidget has its own title; we can hide group title or MyScoreWidget's title
        self.my_score_group.setTitle("") # Hide group box title, let MyScoreWidget display its own
        my_score_group_layout.addWidget(self.my_score_widget_internal)
        layout.addWidget(self.my_score_group)


    def update_stats(self):
        try:
            all_clients = db_manager.get_all_clients()
            if all_clients is None: all_clients = []

            total_clients = len(all_clients)
            self.total_label.setText(str(total_clients))

            total_val = sum(c.get('price', 0) for c in all_clients if c.get('price') is not None)
            self.value_label.setText(f"{total_val:,.2f} €")

            status_en_cours_obj = db_manager.get_status_setting_by_name('En cours', 'Client')
            status_en_cours_id = status_en_cours_obj['status_id'] if status_en_cours_obj else None

            status_urgent_obj = db_manager.get_status_setting_by_name('Urgent', 'Client')
            status_urgent_id = status_urgent_obj['status_id'] if status_urgent_obj else None

            ongoing_count = 0
            if status_en_cours_id is not None:
                ongoing_count = sum(1 for c in all_clients if c.get('status_id') == status_en_cours_id)
            self.ongoing_label.setText(str(ongoing_count))

            urgent_count = 0
            if status_urgent_id is not None:
                urgent_count = sum(1 for c in all_clients if c.get('status_id') == status_urgent_id)
            self.urgent_label.setText(str(urgent_count))

            # Update MyScoreWidget
            if hasattr(self, 'my_score_widget_internal'): # Check if it's initialized
                self.my_score_widget_internal.update_score()
            elif hasattr(self, 'my_score_widget'): # If using Option 1
                 self.my_score_widget.update_score()

        except Exception as e:
            print(f"Erreur de mise à jour des statistiques: {str(e)}")


class StatusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        client_data_for_delegate = index.data(Qt.UserRole)
        status_name_for_delegate = None
        if isinstance(client_data_for_delegate, dict):
            status_name_for_delegate = client_data_for_delegate.get('status') # 'status' is the key holding the status name string

        bg_color_hex = "#95a5a6" # Default color
        icon_name = None

        if status_name_for_delegate: # This condition now correctly uses the string
            try:
                # Ensure 'Client' is the correct status_type context here
                status_setting = db_manager.get_status_setting_by_name(status_name_for_delegate, 'Client')
                if status_setting:
                    if status_setting.get('color_hex'):
                        bg_color_hex = status_setting['color_hex']
                    if status_setting.get('icon_name'):
                        icon_name = status_setting['icon_name']
            except Exception as e:
                print(f"Error fetching status color/icon for delegate: {e}")

        painter.save()

        bg_qcolor = QColor(bg_color_hex)
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight().color())
        else:
            painter.fillRect(option.rect, bg_qcolor)

        text_qcolor = QColor(Qt.black)
        effective_bg_for_text = option.palette.highlight().color() if (option.state & QStyle.State_Selected) else bg_qcolor
        if effective_bg_for_text.lightnessF() < 0.5:
            text_qcolor = QColor(Qt.white)
        painter.setPen(text_qcolor)
        painter.setFont(option.font)

        icon_size = 16
        left_padding = 5
        icon_text_spacing = 5
        text_rect = option.rect.adjusted(left_padding, 0, -5, 0)

        if icon_name:
            # Attempt to load icon from resources or theme.
            # For this example, assuming icons are available via QIcon.fromTheme() or resource path.
            # If using resource paths (e.g., ":/icons/status_icon.png"), ensure resources are compiled.
            icon_path = f":/icons/{icon_name}.svg" # Example if icons are in resources under 'icons' prefix
            if not QIcon.hasThemeIcon(icon_name) and os.path.exists(icon_path.replace(":/", "")): # Basic check if not theme icon
                 icon = QIcon(icon_path)
            else: # Fallback to theme or default
                 icon = QIcon.fromTheme(icon_name) # Default behavior

            if not icon.isNull():
                icon_y_offset = (option.rect.height() - icon_size) // 2
                icon_rect = QRect(option.rect.left() + left_padding,
                                  option.rect.top() + icon_y_offset,
                                  icon_size, icon_size)
                icon.paint(painter, icon_rect, Qt.AlignCenter,
                           QIcon.Normal if (option.state & QStyle.State_Enabled) else QIcon.Disabled,
                           QIcon.On if (option.state & QStyle.State_Selected) else QIcon.Off)

                text_rect = option.rect.adjusted(left_padding + icon_size + icon_text_spacing, 0, -5, 0)

        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, index.data(Qt.DisplayRole))
        painter.restore()
