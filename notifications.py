from PyQt5.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
                             QGraphicsOpacityEffect, QApplication, QMainWindow, QSpacerItem, QSizePolicy,
                             QStyle) # Added QStyle here
from PyQt5.QtCore import QObject, QTimer, QPropertyAnimation, Qt, pyqtSignal, QRect
from PyQt5.QtGui import QIcon, QFont, QColor, QPixmap, QScreen
import os # For joining paths if needed for icons


class NotificationWidget(QWidget):
    """
    A widget for displaying a single notification message.
    Features auto-fade, styling based on type, and a close button.
    """
    closed = pyqtSignal(QWidget)
    """Signal emitted just before the notification is about to close and be deleted."""

    # Refined Color Palette
    TYPE_COLORS = {
        'INFO': {
            'bg': QColor("#D6EAF8"), 'border': QColor("#AED6F1"), 'text': QColor("#1A5276"),
            'icon_default': "SP_MessageBoxInformation", 'icon_custom': "icons/bell.svg" # Example custom
        },
        'SUCCESS': {
            'bg': QColor("#D4EFDF"), 'border': QColor("#A9DFBF"), 'text': QColor("#196F3D"),
            'icon_default': "SP_DialogApplyButton", 'icon_custom': "icons/check-square.svg"
        },
        'WARNING': {
            'bg': QColor("#FDEBD0"), 'border': QColor("#FAD7A0"), 'text': QColor("#7E5109"),
            'icon_default': "SP_MessageBoxWarning", 'icon_custom': "icons/help-circle.svg" # Example custom
        },
        'ERROR': {
            'bg': QColor("#FADBD8"), 'border': QColor("#F5B7B1"), 'text': QColor("#78281F"),
            'icon_default': "SP_MessageBoxCritical", 'icon_custom': "icons/help-circle.svg" # Example custom, might need a specific error icon
        }
    }
    DEFAULT_TYPE_STYLE = TYPE_COLORS['INFO'] # Fallback for unknown types

    # Using QStyle for the close button icon
    CLOSE_ICON_STD_NAME = "SP_DialogCloseButton"
    ICON_SIZE = 24 # Desired icon size

    def __init__(self, title, message, type='INFO', duration=5000, parent_window=None, icon_path=None):
        """
        Initialize the notification widget.

        Args:
            title (str): The title of the notification.
            message (str): The main message content of the notification.
            type (str, optional): Type of notification ('INFO', 'SUCCESS', 'WARNING', 'ERROR').
                                  Defaults to 'INFO'. Determines styling and default icon.
            duration (int, optional): Duration in milliseconds before the notification auto-closes.
                                      Defaults to 5000ms. Set to 0 for no auto-close.
            parent_window (QWidget, optional): The main application window, used for context by the
                                               NotificationManager for positioning. Defaults to None.
            icon_path (str, optional): Path to a custom icon. If None, a default icon based
                                       on the 'type' will be used. Defaults to None.
        """
        super().__init__(None)

        self.title_text = title # Renamed to avoid clash if self.title is a QWidget property
        self.message_text = message
        self.type = type.upper()
        self.duration = duration
        self.parent_window_context = parent_window
        self.custom_icon_path = icon_path # Renamed for clarity

        self._init_ui()
        self._apply_styling()
        self._setup_animations()
        self._setup_timer()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.hide()
        self.setFocusPolicy(Qt.NoFocus)

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12) # Slightly increased padding
        self.main_layout.setSpacing(8) # Spacing between elements

        self.top_row_layout = QHBoxLayout()
        self.top_row_layout.setSpacing(8)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.top_row_layout.addWidget(self.icon_label)

        self.title_label = QLabel(self.title_text)
        title_font = QFont("Arial", 10) # Or Segoe UI
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.top_row_layout.addWidget(self.title_label)
        self.top_row_layout.addStretch()

        self.close_button = QPushButton()
        style = self.style()
        close_icon_std_enum = getattr(QStyle, self.CLOSE_ICON_STD_NAME, QStyle.SP_DialogCloseButton)
        close_icon_pixmap = style.standardPixmap(close_icon_std_enum)
        if not close_icon_pixmap.isNull():
            self.close_button.setIcon(QIcon(close_icon_pixmap))
        else:
            self.close_button.setText("X") # Fallback
        self.close_button.setFixedSize(20, 20)
        self.close_button.setStyleSheet("QPushButton { border: none; background-color: transparent; }")
        self.close_button.setToolTip(self.tr("Close notification"))
        self.close_button.clicked.connect(self.fade_out)
        self.top_row_layout.addWidget(self.close_button)

        self.main_layout.addLayout(self.top_row_layout)

        self.message_label = QLabel(self.message_text)
        self.message_label.setFont(QFont("Arial", 9)) # Or Segoe UI
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignTop) # Keep message text aligned to top
        self.main_layout.addWidget(self.message_label)

        self.setLayout(self.main_layout)
        # Initial size, will be adjusted. Min width can be useful.
        self.setMinimumWidth(320)
        self.setMaximumWidth(400) # Max width to prevent overly wide notifications
        self.adjustSize() # Adjust to content initially

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)

    def _apply_styling(self):
        style_data = self.TYPE_COLORS.get(self.type, self.DEFAULT_TYPE_STYLE)
        bg_color = style_data['bg']
        border_color = style_data['border']
        text_color = style_data['text']

        # Main widget stylesheet
        stylesheet = f"""
            NotificationWidget {{
                background-color: {bg_color.name()};
                border: 1px solid {border_color.name()};
                border-radius: 5px;
            }}
        """
        self.setStyleSheet(stylesheet)

        # Text color for title and message
        text_color_str = f"color: {text_color.name()}; background-color: transparent;"
        self.title_label.setStyleSheet(text_color_str)
        self.message_label.setStyleSheet(text_color_str)
        self.close_button.setStyleSheet(f"QPushButton {{ {text_color_str} border: none; }} QPushButton:hover {{ {text_color_str} background-color: {border_color.lighter(120).name()}; }}")


        # Icon selection
        pixmap = None
        icon_source_path = self.custom_icon_path if self.custom_icon_path else style_data.get('icon_custom')

        if icon_source_path:
            # Check if icon_source_path is a QStyle enum name (like "SP_MessageBoxInformation")
            # This check is basic; a more robust way might be needed if mixing paths and SP_ enums frequently.
            if icon_source_path.startswith("SP_"):
                style = self.style()
                std_icon_enum = getattr(QStyle, icon_source_path, None)
                if std_icon_enum is not None:
                    pixmap = style.standardPixmap(std_icon_enum, None, self)
            elif os.path.exists(icon_source_path): # It's a file path
                 icon = QIcon(icon_source_path)
                 if not icon.isNull():
                    pixmap = icon.pixmap(self.ICON_SIZE, self.ICON_SIZE, mode=Qt.KeepAspectRatio, state=Qt.OnState)
            else: # Not an SP_ enum and path doesn't exist, try default SP_ for type
                pass # Will fall through to next block

        if not pixmap: # Fallback to default QStyle icon for the type if custom/path failed
            style = self.style()
            default_sp_name = style_data.get('icon_default', 'SP_MessageBoxInformation')
            std_icon_enum = getattr(QStyle, default_sp_name, QStyle.SP_MessageBoxInformation)
            pixmap = style.standardPixmap(std_icon_enum, None, self)

        if pixmap and not pixmap.isNull():
            # For SVG, ensure color is appropriate or apply one if needed.
            # Here, assuming SVG icons are designed to work with various backgrounds or are neutral.
            # If icon color needs to match text_color, it's more complex for pixmaps directly.
            self.icon_label.setPixmap(pixmap.scaled(self.ICON_SIZE, self.ICON_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            # Text fallback if all icon loading fails
            self.icon_label.setText(self.type[0])
            self.icon_label.setStyleSheet(f"color: {text_color.name()}; font-weight: bold; background-color: transparent;")

    def _setup_animations(self):
        self.animation_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation_in.setDuration(300)
        self.animation_in.setStartValue(0.0)
        self.animation_in.setEndValue(0.97) # Slightly more opaque

        self.animation_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation_out.setDuration(300)
        self.animation_out.setStartValue(0.97)
        self.animation_out.setEndValue(0.0)
        self.animation_out.finished.connect(self._on_fade_out_finished)

    def _setup_timer(self):
        self.life_timer = QTimer(self)
        self.life_timer.setSingleShot(True)
        self.life_timer.setInterval(self.duration)
        self.life_timer.timeout.connect(self.fade_out)

    def show_notification(self):
        """
        Displays the notification widget on screen and starts its life timer.
        The widget will fade in and then, after its duration, fade out and close.
        """
        self.setWindowOpacity(0.0)
        self.show()
        self.adjustSize() # Recalculate size based on content
        # Set fixed size after adjustSize to ensure it fits content but isn't resizable by user
        # and maintains a consistent look.
        self.setFixedSize(self.width(), self.height())
        self.animation_in.start()
        self.life_timer.start()

    def fade_out(self):
        if self.life_timer.isActive():
            self.life_timer.stop()
        if self.opacity_effect.opacity() > 0 and self.animation_out.state() != QPropertyAnimation.Running:
            self.animation_out.start()

    def _on_fade_out_finished(self):
        self.closed.emit(self)
        self.close()

    def enterEvent(self, event):
        if self.life_timer.isActive():
            self.life_timer.stop()
        self.animation_in.stop()
        self.animation_out.stop()
        self.opacity_effect.setOpacity(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.life_timer.isActive() and self.duration > 0:
            if self.opacity_effect.opacity() > 0.9: # Check if not already fading out
                self.life_timer.start()
                self.opacity_effect.setOpacity(0.97)
        super().leaveEvent(event)


class NotificationManager(QObject):
    """
    Manages the display and positioning of multiple NotificationWidget instances.
    Ensures notifications stack neatly on the screen and are removed when closed.
    """
    PADDING = 10
    SPACING = 5

    def __init__(self, parent_window=None):
        """
        Initialize the NotificationManager.

        Args:
            parent_window (QWidget, optional): The main application window. This is used as a
                                               reference for positioning notifications, typically
                                               on the primary screen related to this window.
                                               Defaults to None.
        """
        super().__init__()
        self.parent_window = parent_window
        self.active_notifications = []

    def show(self, title, message, type='INFO', duration=5000, icon_path=None):
        """
        Creates, configures, and displays a new notification.

        Args:
            title (str): The title of the notification.
            message (str): The main message content.
            type (str, optional): Notification type ('INFO', 'SUCCESS', 'WARNING', 'ERROR').
                                  Defaults to 'INFO'.
            duration (int, optional): Duration in milliseconds for auto-close. Defaults to 5000.
                                      Set to 0 or negative for no auto-close by timer.
            icon_path (str, optional): Path to a custom icon. Defaults to None (uses type-based default).
        """
        notification_widget = NotificationWidget(title, message, type, duration,
                                                 parent_window=self.parent_window,
                                                 icon_path=icon_path)
        notification_widget.closed.connect(self._on_notification_closed)
        self.active_notifications.insert(0, notification_widget)
        self._reposition_notifications()
        notification_widget.show_notification()

    def _on_notification_closed(self, notification_widget):
        try:
            self.active_notifications.remove(notification_widget)
        except ValueError:
            pass
        notification_widget.deleteLater()
        self._reposition_notifications()

    def _reposition_notifications(self):
        if not QApplication.instance(): return
        screen = QApplication.primaryScreen()
        if not screen:
            if self.parent_window and self.parent_window.windowHandle():
                screen = self.parent_window.windowHandle().screen()
            elif QApplication.desktop().screenCount() > 0:
                 screen = QApplication.desktop().screen(QApplication.desktop().primaryScreen())
            else:
                screens = QApplication.screens()
                if screens: screen = screens[0]
                else: return

        screen_geometry = screen.availableGeometry()
        current_y = screen_geometry.height() - self.PADDING

        for widget in self.active_notifications:
            widget_height = widget.height()
            current_y -= (widget_height + self.SPACING)
            x = screen_geometry.width() - widget.width() - self.PADDING
            y = current_y
            widget.move(x, y)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)

    main_win = QMainWindow()
    main_win.setWindowTitle("Notification Test Window")
    main_win.setGeometry(300, 300, 700, 500) # Increased size for more buttons

    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    main_win.setCentralWidget(central_widget)

    notification_manager = NotificationManager(parent_window=main_win)

    # Test buttons for each type
    btn_info = QPushButton("Show INFO (icons/bell.svg or SP_MessageBoxInformation)")
    btn_info.clicked.connect(lambda: notification_manager.show(
        "Information",
        "This is an informational message with the new styling. It should use bell.svg if found, or a default info icon.",
        type='INFO'
    ))
    layout.addWidget(btn_info)

    btn_success = QPushButton("Show SUCCESS (icons/check-square.svg or SP_DialogApplyButton)")
    btn_success.clicked.connect(lambda: notification_manager.show(
        "Success!",
        "The operation was completed successfully. This uses check-square.svg or a default success icon.",
        type='SUCCESS',
        duration=7000
    ))
    layout.addWidget(btn_success)

    btn_warning = QPushButton("Show WARNING (icons/help-circle.svg or SP_MessageBoxWarning)")
    btn_warning.clicked.connect(lambda: notification_manager.show(
        "Warning Alert",
        "Something might require your attention. This uses help-circle.svg or a default warning icon.",
        type='WARNING'
    ))
    layout.addWidget(btn_warning)

    btn_error = QPushButton("Show ERROR (icons/help-circle.svg or SP_MessageBoxCritical)")
    btn_error.clicked.connect(lambda: notification_manager.show(
        "Error Occurred",
        "An error has happened during the process. This uses help-circle.svg or a default error icon.",
        type='ERROR',
        duration=10000
    ))
    layout.addWidget(btn_error)

    btn_custom_icon_error = QPushButton("Show ERROR (Custom User-Provided Icon)")
    # NOTE: Replace "icons/user.svg" with an actual path to a DIFFERENT icon for testing this specific case.
    # If "icons/user.svg" doesn't exist, it will fall back to the default ERROR icon.
    # This is to test the icon_path parameter.
    custom_icon_test_path = "icons/user.svg" # Make sure this icon exists for a clear test
    if not os.path.exists(custom_icon_test_path):
         btn_custom_icon_error.setText(f"Show ERROR (Custom Icon Test - {custom_icon_test_path} NOT FOUND)")
         btn_custom_icon_error.setStyleSheet("color: red;")


    btn_custom_icon_error.clicked.connect(lambda: notification_manager.show(
        "Error With Custom Icon",
        f"This error notification attempts to use a user-defined icon: {custom_icon_test_path}.",
        type='ERROR',
        icon_path=custom_icon_test_path
    ))
    layout.addWidget(btn_custom_icon_error)

    spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
    layout.addItem(spacer)

    main_win.show()
    sys.exit(app.exec_())
