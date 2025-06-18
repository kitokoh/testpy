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
from botpress_integration.ui_components import BotpressIntegrationUI
from botpress_integration.api_client import BotpressClient # Needed for type checks / mock return values
from botpress_integration.models import UserBotpressSettings, Conversation # For mock return values from CRUD

class TestBotpressIntegrationUI(unittest.TestCase):

    @patch('botpress_integration.ui_components.SessionLocal') # Mock DB session
    @patch('botpress_integration.ui_components.create_db_and_tables') # Mock DB creation
    def setUp(self, mock_create_db, mock_session_local):
        # Mock the database session for all tests in this class
        self.mock_db_session = MagicMock()
        mock_session_local.return_value = self.mock_db_session

        # Create a dummy parent widget if needed, or None
        self.parent_widget = QWidget()
        self.ui = BotpressIntegrationUI(parent=self.parent_widget, current_user_id="test_user")

    def tearDown(self):
        # Close the dummy parent widget if it was created
        if self.parent_widget:
            self.parent_widget.deleteLater() # Ensure proper Qt cleanup
        # self.ui.close() # If the UI component itself needs explicit closing/cleanup
        del self.ui # Explicitly delete to help with resource management

    @patch('botpress_integration.ui_components.crud.get_botpress_settings')
    @patch('botpress_integration.ui_components.crud.get_or_create_conversation')
    @patch('botpress_integration.ui_components.BotpressClient') # Mock the API client instantiation
    @patch('PyQt5.QtWidgets.QMessageBox') # Suppress QMessageBox popups
    def test_load_settings_existing_settings(self, mock_qmessagebox, mock_botpress_client, mock_get_or_create_conv, mock_get_settings):
        # Arrange
        mock_settings = UserBotpressSettings(
            id=1,
            user_id="test_user",
            api_key="fake_api_key",
            bot_id="fake_bot_id",
            base_url="http://custom.botpress.com"
        )
        mock_get_settings.return_value = mock_settings

        mock_conversation = Conversation(id=1, botpress_conversation_id="fake_bot_id_main_chat")
        mock_get_or_create_conv.return_value = mock_conversation

        mock_api_client_instance = MagicMock(spec=BotpressClient)
        mock_botpress_client.return_value = mock_api_client_instance

        # Act
        self.ui.load_settings()

        # Assert
        mock_get_settings.assert_called_once_with(self.mock_db_session, user_id="test_user")
        self.assertEqual(self.ui.api_key_input.text(), "fake_api_key")
        self.assertEqual(self.ui.bot_id_input.text(), "fake_bot_id")
        self.assertEqual(self.ui.base_url_input.text(), "http://custom.botpress.com")
        self.assertIsNotNone(self.ui.botpress_client)
        mock_botpress_client.assert_called_once_with(api_key="fake_api_key", bot_id="fake_bot_id", base_url="http://custom.botpress.com")
        mock_get_or_create_conv.assert_called_once()
        self.assertEqual(self.ui.current_db_conversation_id, 1)
        self.assertEqual(self.ui.current_botpress_conversation_id, "fake_bot_id_main_chat")
        # Check if load_and_display_recent_conversations was called (indirectly, by checking if it tried to get recent convos)
        # This might require further mocking of get_recent_conversations if we want to be very specific.
        # For now, checking side effects like client init and conversation ID set is a good start.


    @patch('botpress_integration.ui_components.crud.get_botpress_settings')
    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_load_settings_no_existing_settings(self, mock_qmessagebox, mock_get_settings):
        # Arrange
        mock_get_settings.return_value = None

        # Act
        self.ui.load_settings()

        # Assert
        mock_get_settings.assert_called_once_with(self.mock_db_session, user_id="test_user")
        self.assertEqual(self.ui.api_key_input.text(), "")
        self.assertEqual(self.ui.bot_id_input.text(), "")
        self.assertEqual(self.ui.base_url_input.text(), "https://api.botpress.cloud/v1/")
        self.assertIsNone(self.ui.botpress_client)
        self.assertIsNone(self.ui.current_db_conversation_id) # Should not have created one
        # mock_qmessagebox.information.assert_called_once() # Check if "No Settings" dialog shown


    @patch('botpress_integration.ui_components.crud.create_or_update_botpress_settings')
    @patch('botpress_integration.ui_components.BotpressClient')
    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_save_settings_new_settings(self, mock_qmessagebox, mock_botpress_client, mock_create_update_settings):
        # Arrange
        self.ui.api_key_input.setText("new_key")
        self.ui.bot_id_input.setText("new_bot")
        self.ui.base_url_input.setText("http://new.url/")

        mock_saved_settings = UserBotpressSettings(id=2, user_id="test_user", api_key="new_key", bot_id="new_bot", base_url="http://new.url/")
        mock_create_update_settings.return_value = mock_saved_settings

        mock_api_client_instance = MagicMock(spec=BotpressClient)
        mock_botpress_client.return_value = mock_api_client_instance

        # Act
        self.ui.save_settings()

        # Assert
        mock_create_update_settings.assert_called_once_with(
            self.mock_db_session,
            user_id="test_user",
            api_key="new_key",
            bot_id="new_bot",
            base_url="http://new.url/" # Assuming it saves the non-empty URL
        )
        self.assertIsNotNone(self.ui.botpress_client)
        mock_botpress_client.assert_called_once_with(api_key="new_key", bot_id="new_bot", base_url="http://new.url/")
        # mock_qmessagebox.information.assert_called_with(ANY, "Settings Saved", ANY)


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
        # Arrange
        test_payload = "suggestion_payload_text"
        # Simulate a message widget container that would have the suggestion buttons
        # For this test, we only need to ensure the right methods are called.
        # The actual removal of buttons is complex to assert here without more direct access.
        mock_message_widget_container = QWidget()

        # Act
        self.ui.handle_suggestion_clicked(test_payload, mock_message_widget_container)

        # Assert
        self.assertEqual(self.ui.message_input.text(), test_payload)
        mock_handle_send.assert_called_once()


if __name__ == '__main__':
    unittest.main()
