import unittest
from unittest.mock import patch, MagicMock, ANY
import sys

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt

# Ensure a QApplication instance exists for widget testing
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

# Adjust import paths as necessary
from botpress_integration import crud # To mock its functions
from botpress_integration.ui_components import BotpressIntegrationUI, CONVO_ID_ROLE, BP_CONVO_ID_ROLE, IS_UNREAD_ROLE
from botpress_integration.api_client import BotpressClient
from botpress_integration.models import UserBotpressSettings, Conversation, Message
from PyQt5.QtWidgets import QListWidgetItem, QSystemTrayIcon
from PyQt5.QtGui import QFont


class TestBotpressIntegrationUI(unittest.TestCase):

    @patch('botpress_integration.ui_components.SessionLocal')
    @patch('botpress_integration.ui_components.create_db_and_tables')
    @patch('PyQt5.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable', return_value=True) # Assume tray is available
    def setUp(self, mock_tray_available, mock_create_db, mock_session_local):
        self.mock_db_session = MagicMock()
        mock_session_local.return_value = self.mock_db_session

        self.parent_widget = QWidget()
        # Patch the tray icon directly in the UI's __init__ if it's created there
        # For simplicity, we might let it be created and then mock its methods if needed,
        # or patch QSystemTrayIcon globally if that's easier.
        # Let's assume self.ui.tray_icon will be a MagicMock for some tests.
        self.ui = BotpressIntegrationUI(parent=self.parent_widget, current_user_id="test_user")
        # Mock the tray_icon's methods if it was created by the UI, to avoid actual notifications
        if hasattr(self.ui, 'tray_icon'):
            self.ui.tray_icon = MagicMock(spec=QSystemTrayIcon)
            self.ui.tray_icon.isVisible.return_value = True # Assume it's visible for tests that need it


    def tearDown(self):
        if self.parent_widget:
            self.parent_widget.deleteLater() # Ensure proper Qt cleanup
        del self.ui

    @patch('botpress_integration.ui_components.crud.get_botpress_settings')
    @patch('botpress_integration.ui_components.crud.get_or_create_conversation')
    @patch('botpress_integration.ui_components.BotpressClient')
    @patch.object(BotpressIntegrationUI, 'load_and_display_recent_conversations') # Mock this to prevent its full execution
    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_load_settings_existing_settings(self, mock_qmessagebox, mock_load_recent_convos_ui, mock_botpress_client, mock_get_or_create_conv, mock_get_settings):
        mock_settings = UserBotpressSettings(id=1, user_id="test_user", api_key="key", bot_id="bot", base_url="url")
        mock_get_settings.return_value = mock_settings
        mock_conv = Conversation(id=1, botpress_conversation_id="bot_main_chat")
        mock_get_or_create_conv.return_value = mock_conv
        mock_api_client_instance = MagicMock(spec=BotpressClient)
        mock_botpress_client.return_value = mock_api_client_instance

        with patch.object(self.ui.notification_timer, 'start') as mock_timer_start, \
             patch.object(self.ui, 'check_for_new_messages') as mock_check_new_msg:
            self.ui.load_settings()

        mock_get_settings.assert_called_once_with(self.mock_db_session, user_id="test_user")
        self.assertEqual(self.ui.api_key_input.text(), "key")
        self.assertEqual(self.ui.bot_id_input.text(), "bot")
        self.assertEqual(self.ui.base_url_input.text(), "url")
        mock_botpress_client.assert_called_once_with(api_key="key", bot_id="bot", base_url="url")
        mock_get_or_create_conv.assert_called_once()
        self.assertEqual(self.ui.current_db_conversation_id, 1)
        mock_load_recent_convos_ui.assert_called_once()
        mock_timer_start.assert_called_once_with(15000)
        mock_check_new_msg.assert_called_once()


    @patch('botpress_integration.ui_components.crud.get_botpress_settings')
    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_load_settings_no_existing_settings(self, mock_qmessagebox, mock_get_settings):
        mock_get_settings.return_value = None
        with patch.object(self.ui.notification_timer, 'stop') as mock_timer_stop:
            self.ui.load_settings()

        mock_get_settings.assert_called_once_with(self.mock_db_session, user_id="test_user")
        self.assertEqual(self.ui.api_key_input.text(), "")
        self.assertEqual(self.ui.base_url_input.text(), "https://api.botpress.cloud/v1/")
        self.assertIsNone(self.ui.botpress_client)
        mock_timer_stop.assert_called_once()


    @patch('botpress_integration.ui_components.crud.create_or_update_botpress_settings')
    @patch('botpress_integration.ui_components.BotpressClient')
    @patch.object(BotpressIntegrationUI, 'load_and_display_recent_conversations')
    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_save_settings_new_settings(self, mock_qmessagebox, mock_load_recent_convos, mock_botpress_client, mock_create_update_settings):
        self.ui.api_key_input.setText("new_key")
        self.ui.bot_id_input.setText("new_bot")
        self.ui.base_url_input.setText("http://new.url/")
        mock_saved_settings = UserBotpressSettings(id=2, user_id="test_user", api_key="new_key", bot_id="new_bot", base_url="http://new.url/")
        mock_create_update_settings.return_value = mock_saved_settings
        mock_api_client_instance = MagicMock(spec=BotpressClient)
        mock_botpress_client.return_value = mock_api_client_instance

        with patch.object(self.ui.notification_timer, 'start') as mock_timer_start, \
             patch.object(self.ui, 'check_for_new_messages') as mock_check_new_msg:
            self.ui.save_settings()

        mock_create_update_settings.assert_called_once_with(
            self.mock_db_session, user_id="test_user", api_key="new_key", bot_id="new_bot", base_url="http://new.url/"
        )
        mock_botpress_client.assert_called_once_with(api_key="new_key", bot_id="new_bot", base_url="http://new.url/")
        mock_load_recent_convos.assert_called_once()
        mock_timer_start.assert_called_once_with(15000)
        mock_check_new_msg.assert_called_once()


    @patch('botpress_integration.ui_components.crud.create_or_update_botpress_settings')
    @patch('botpress_integration.ui_components.BotpressClient')
    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_save_settings_empty_base_url_saves_none(self, mock_qmessagebox, mock_botpress_client, mock_create_update_settings):
        self.ui.api_key_input.setText("key_no_base")
        self.ui.bot_id_input.setText("bot_no_base")
        self.ui.base_url_input.setText("") # Empty base URL

        mock_saved_settings = UserBotpressSettings(id=3, user_id="test_user", api_key="key_no_base", bot_id="bot_no_base", base_url=None)
        mock_create_update_settings.return_value = mock_saved_settings

        self.ui.save_settings()

        mock_create_update_settings.assert_called_once_with(
            self.mock_db_session,
            user_id="test_user",
            api_key="key_no_base",
            bot_id="bot_no_base",
            base_url=None # Should save None
        )
        mock_botpress_client.assert_called_once_with(api_key="key_no_base", bot_id="bot_no_base", base_url="https://api.botpress.cloud/v1/") # Client uses default


    @patch('botpress_integration.ui_components.crud.add_message')
    @patch.object(BotpressIntegrationUI, 'add_message_to_display') # Mocking the instance method
    @patch.object(BotpressIntegrationUI, 'load_and_display_recent_conversations')
    @patch.object(BotpressIntegrationUI, 'restore_conversation_list_selection')
    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_handle_send_message_success(self, mock_qmessagebox, mock_restore_selection, mock_load_recent_convos, mock_add_msg_display, mock_crud_add_msg):
        # Arrange
        self.ui.botpress_client = MagicMock(spec=BotpressClient)
        # Simulate a successful API response with suggestions
        mock_api_response = {
            "message": { # Assuming this structure based on previous work
                "id": "bp_msg_123",
                "conversationId": "bp_conv_abc",
                "text": "Hello from bot!",
                "suggestions": [{"title": "OK", "payload": "ok_payload"}]
            }
        }
        self.ui.botpress_client.send_message.return_value = mock_api_response

        self.ui.current_db_conversation_id = 1 # Assume a conversation is active
        self.ui.current_botpress_conversation_id = "bp_conv_abc" # Initial Botpress conv ID
        self.ui.message_input.setText("Hello there")

        # Act
        self.ui.handle_send_message()

        # Assert
        # 1. User message displayed and saved
        mock_add_msg_display.assert_any_call(sender_type='user', text="Hello there", timestamp=ANY)
        mock_crud_add_msg.assert_any_call(self.mock_db_session, conversation_id=1, sender_type='user', content="Hello there", timestamp=ANY)

        # 2. API client called
        self.ui.botpress_client.send_message.assert_called_once_with("Hello there", conversation_id="bp_conv_abc")

        # 3. Bot message displayed and saved (with suggestions)
        mock_add_msg_display.assert_any_call(sender_type='bot', text="Hello from bot!", timestamp=ANY, suggestions=[{"title": "OK", "payload": "ok_payload"}])
        mock_crud_add_msg.assert_any_call(
            self.mock_db_session,
            conversation_id=1,
            sender_type='bot',
            content="Hello from bot!",
            timestamp=ANY,
            botpress_message_id="bp_msg_123",
            suggestions='[{"title": "OK", "payload": "ok_payload"}]' # JSON string
        )

        self.assertEqual(self.ui.message_input.text(), "") # Input cleared
        mock_load_recent_convos.assert_called_once()
        mock_restore_selection.assert_called_once_with(1)


    @patch.object(BotpressIntegrationUI, 'handle_send_message') # Mock the method that would be called
    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_handle_suggestion_clicked(self, mock_qmessagebox, mock_handle_send):
        test_payload = "suggestion_payload_text"
        mock_message_widget_container = QWidget()
        self.ui.handle_suggestion_clicked(test_payload, mock_message_widget_container)
        self.assertEqual(self.ui.message_input.text(), test_payload)
        mock_handle_send.assert_called_once()

    # --- Notification and Unread Indicator Tests ---

    @patch('botpress_integration.ui_components.crud.count_unread_bot_messages')
    @patch.object(BotpressIntegrationUI, 'trigger_notifications')
    @patch.object(BotpressIntegrationUI, 'load_and_display_recent_conversations')
    def test_check_for_new_messages_polling(self, mock_load_convos, mock_trigger_notif, mock_count_unread):
        self.ui.botpress_client = MagicMock() # Ensure client is considered "ready"

        # Scenario 1: No unread messages
        mock_count_unread.return_value = 0
        self.ui.has_unread_bot_messages = False # Initial state
        self.ui.check_for_new_messages()
        mock_trigger_notif.assert_not_called()
        self.assertFalse(self.ui.has_unread_bot_messages)
        # load_and_display_recent_conversations might be called if state changed, ensure it is if needed
        # For now, let's assume it's called if has_unread_bot_messages changes from True to False.

        # Scenario 2: New unread messages appear
        mock_count_unread.return_value = 3
        self.ui.has_unread_bot_messages = False # State before finding new messages
        self.ui.check_for_new_messages()
        mock_trigger_notif.assert_called_once_with(3)
        self.assertTrue(self.ui.has_unread_bot_messages)
        mock_load_convos.assert_called_once() # Should refresh list to show bolding

        mock_trigger_notif.reset_mock()
        mock_load_convos.reset_mock()

        # Scenario 3: Unread messages persist, no new notification
        self.ui.has_unread_bot_messages = True # State remains true
        self.ui.check_for_new_messages() # count still 3
        mock_trigger_notif.assert_not_called() # Should not notify again for the same state
        self.assertTrue(self.ui.has_unread_bot_messages)
        # Depending on design, load_and_display_recent_conversations might or might not be called here.
        # If it's only for state *change*, it shouldn't. If it's for any unread count > 0, it should.
        # Current logic in check_for_new_messages implies it's called if unread_count > 0.
        mock_load_convos.assert_called_once()

        mock_load_convos.reset_mock()
        # Scenario 4: Messages become read
        mock_count_unread.return_value = 0
        self.ui.has_unread_bot_messages = True # State was true
        self.ui.check_for_new_messages()
        self.assertFalse(self.ui.has_unread_bot_messages)
        mock_load_convos.assert_called_once() # Should refresh to remove bolding

    def test_trigger_notifications(self):
        # self.ui.tray_icon is already a MagicMock from setUp
        self.ui.trigger_notifications(3)
        self.ui.tray_icon.showMessage.assert_called_with(
            "3 New Botpress Messages",
            "You have 3 unread message(s) in the Botpress integration.",
            QSystemTrayIcon.Information,
            5000
        )
        self.ui.trigger_notifications(1)
        self.ui.tray_icon.showMessage.assert_called_with(
            "New Botpress Message",
            "You have 1 unread message(s) in the Botpress integration.",
            QSystemTrayIcon.Information,
            5000
        )

    def test_update_conversation_item_style(self):
        mock_item = MagicMock(spec=QListWidgetItem)
        mock_font = MagicMock(spec=QFont)
        mock_item.font.return_value = mock_font

        # Test setting as unread
        self.ui.update_conversation_item_style(mock_item, True, base_text="Test Convo")
        mock_font.setBold.assert_called_with(True)
        mock_item.setText.assert_called_with("[UNREAD] Test Convo")
        mock_item.setData.assert_called_with(IS_UNREAD_ROLE, True)

        # Test setting as read (when it was unread)
        mock_item.text.return_value = "[UNREAD] Test Convo" # Simulate current text
        self.ui.update_conversation_item_style(mock_item, False, base_text="Test Convo") # Pass base_text for proper stripping
        mock_font.setBold.assert_called_with(False)
        mock_item.setText.assert_called_with("Test Convo")
        mock_item.setData.assert_called_with(IS_UNREAD_ROLE, False)

        # Test setting as read (when it was already read, no marker)
        mock_item.text.return_value = "Test Convo"
        self.ui.update_conversation_item_style(mock_item, False, base_text="Test Convo")
        mock_font.setBold.assert_called_with(False)
        mock_item.setText.assert_called_with("Test Convo") # Should remain the same
        mock_item.setData.assert_called_with(IS_UNREAD_ROLE, False)


    @patch('botpress_integration.ui_components.crud.get_recent_conversations')
    @patch('botpress_integration.ui_components.crud.has_unread_bot_messages')
    @patch.object(BotpressIntegrationUI, 'update_conversation_item_style')
    def test_load_and_display_recent_conversations_unread_styling(self, mock_update_style, mock_has_unread, mock_get_recent):
        mock_convo1 = Conversation(id=1, botpress_conversation_id="bp1", last_message_timestamp=datetime.now())
        mock_convo2 = Conversation(id=2, botpress_conversation_id="bp2", last_message_timestamp=datetime.now())
        mock_get_recent.return_value = [mock_convo1, mock_convo2]

        # Simulate one convo unread, one read
        mock_has_unread.side_effect = lambda db, convo_id: True if convo_id == mock_convo1.id else False

        self.ui.load_and_display_recent_conversations()

        self.assertEqual(mock_update_style.call_count, 2)
        # Check calls to update_conversation_item_style
        # First call for mock_convo1 (should be unread=True)
        args_convo1, _ = mock_update_style.call_args_list[0]
        self.assertIsInstance(args_convo1[0], QListWidgetItem) # item
        self.assertTrue(args_convo1[1]) # is_unread = True
        self.assertTrue("bp1" in args_convo1[2]) # base_text contains convo id

        # Second call for mock_convo2 (should be unread=False)
        args_convo2, _ = mock_update_style.call_args_list[1]
        self.assertIsInstance(args_convo2[0], QListWidgetItem) # item
        self.assertFalse(args_convo2[1]) # is_unread = False
        self.assertTrue("bp2" in args_convo2[2]) # base_text

    @patch('botpress_integration.ui_components.crud.mark_messages_as_read')
    @patch.object(BotpressIntegrationUI, 'update_conversation_item_style')
    @patch.object(BotpressIntegrationUI, 'check_for_new_messages')
    @patch.object(BotpressIntegrationUI, 'load_conversation_history') # Mock this to simplify test
    def test_handle_conversation_selected_marks_read_and_updates_style(self, mock_load_history, mock_check_new, mock_update_style, mock_mark_read):
        mock_mark_read.return_value = 1 # Simulate 1 message was marked as read

        mock_item = QListWidgetItem()
        mock_item.setData(CONVO_ID_ROLE, 123)
        mock_item.setData(BP_CONVO_ID_ROLE, "bp_conv_selected")
        mock_item.setData(IS_UNREAD_ROLE, True) # Initially unread

        self.ui.handle_conversation_selected(mock_item, None)

        mock_mark_read.assert_called_once_with(self.mock_db_session, conversation_id=123)
        mock_update_style.assert_called_once_with(mock_item, False)
        mock_check_new.assert_called_once()
        mock_load_history.assert_called_once() # Ensure history is loaded for selected item

    @patch.object(QWidget, 'showNormal') # Mocking QWidget's method
    @patch.object(QWidget, 'raise_')
    @patch.object(QWidget, 'activateWindow')
    def test_handle_tray_icon_activated(self, mock_activate, mock_raise, mock_show_normal):
        # To properly test this, self.ui.window() needs to return a mockable window.
        # If self.ui is the top-level window, self.ui.window() is self.ui.
        # We can patch self.ui directly for these methods.

        with patch.object(self.ui, 'window', return_value=self.ui) as mock_get_window: # mock self.window() call
            with patch.object(self.ui, 'isMinimized', return_value=True): # Simulate minimized
                 with patch.object(self.ui, 'showNormal') as self_show_normal, \
                      patch.object(self.ui, 'raise_') as self_raise, \
                      patch.object(self.ui, 'activateWindow') as self_activate:

                    self.ui.handle_tray_icon_activated(QSystemTrayIcon.Trigger)

                    mock_get_window.assert_called()
                    self_show_normal.assert_called_once()
                    self_raise.assert_called_once()
                    self_activate.assert_called_once()


if __name__ == '__main__':
    unittest.main()
