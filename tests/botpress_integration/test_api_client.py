import unittest
from unittest.mock import patch, MagicMock
import requests # For requests.exceptions

# Assuming your project structure allows this import:
# Adjust if your project root is not directly discoverable by Python path
# e.g. by setting PYTHONPATH environment variable or using sys.path.append
from botpress_integration.api_client import BotpressClient, BotpressAPIError

class TestBotpressClient(unittest.TestCase):

    def test_init_default_base_url(self):
        client = BotpressClient(api_key="test_key", bot_id="test_bot")
        self.assertEqual(client.api_key, "test_key")
        self.assertEqual(client.bot_id, "test_bot")
        self.assertEqual(client.base_url, "https://api.botpress.cloud/v1/")
        self.assertEqual(client.bot_specific_url, "https://api.botpress.cloud/v1/bots/test_bot")

    def test_init_custom_base_url(self):
        client = BotpressClient(api_key="test_key", bot_id="test_bot", base_url="http://localhost:3000/api/v1")
        self.assertEqual(client.base_url, "http://localhost:3000/api/v1/") # Ensure trailing slash
        self.assertEqual(client.bot_specific_url, "http://localhost:3000/api/v1/bots/test_bot")

    def test_init_custom_base_url_without_trailing_slash(self):
        client = BotpressClient(api_key="test_key", bot_id="test_bot", base_url="http://custom.domain/api/v1")
        self.assertEqual(client.base_url, "http://custom.domain/api/v1/") # Ensure trailing slash is added
        self.assertEqual(client.bot_specific_url, "http://custom.domain/api/v1/bots/test_bot")

    @patch('botpress_integration.api_client.requests.post')
    def test_send_message_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "message_id": "msg123"}
        mock_response.raise_for_status = MagicMock() # Does not raise for success
        mock_post.return_value = mock_response

        client = BotpressClient(api_key="test_key", bot_id="test_bot")
        response = client.send_message("Hello Botpress", conversation_id="conv456")

        expected_url = "https://api.botpress.cloud/v1/bots/test_bot/messages"
        expected_payload = {
            "text": "Hello Botpress",
            "type": "text",
            "conversationId": "conv456"
        }
        expected_headers = {
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json"
        }
        mock_post.assert_called_once_with(
            expected_url,
            json=expected_payload,
            headers=expected_headers,
            timeout=10
        )
        self.assertEqual(response, {"status": "success", "message_id": "msg123"})

    @patch('botpress_integration.api_client.requests.post')
    def test_send_message_no_conversation_id(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success_no_conv_id"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = BotpressClient(api_key="test_key", bot_id="test_bot")
        response = client.send_message("Hello direct to bot")

        expected_payload = {
            "text": "Hello direct to bot",
            "type": "text"
            # No conversationId
        }
        mock_post.assert_called_once_with(
            unittest.mock.ANY, # URL
            json=expected_payload,
            headers=unittest.mock.ANY,
            timeout=unittest.mock.ANY
        )
        self.assertEqual(response, {"status": "success_no_conv_id"})


    @patch('botpress_integration.api_client.requests.post')
    def test_send_message_http_error(self, mock_post):
        mock_response = MagicMock()
        # Simulate an HTTPError (e.g., 401 Unauthorized)
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Client Error: Unauthorized for url",
            response=MagicMock(status_code=401, text="Auth error details")
        )
        mock_post.return_value = mock_response

        client = BotpressClient(api_key="invalid_key", bot_id="test_bot")
        with self.assertRaises(BotpressAPIError) as context:
            client.send_message("test message")

        self.assertTrue("401" in str(context.exception))
        self.assertTrue("Auth error details" in str(context.exception))

    @patch('botpress_integration.api_client.requests.post')
    def test_send_message_connection_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("Failed to connect")

        client = BotpressClient(api_key="test_key", bot_id="test_bot")
        with self.assertRaises(BotpressAPIError) as context:
            client.send_message("test message")
        self.assertTrue("Connection error" in str(context.exception))
        self.assertTrue("Failed to connect" in str(context.exception))

    @patch('botpress_integration.api_client.requests.post')
    def test_send_message_timeout_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        client = BotpressClient(api_key="test_key", bot_id="test_bot")
        with self.assertRaises(BotpressAPIError) as context:
            client.send_message("test message")
        self.assertTrue("Timeout sending message" in str(context.exception))
        self.assertTrue("Request timed out" in str(context.exception))


    @patch('botpress_integration.api_client.requests.get')
    def test_get_conversations_success_no_conv_id(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "m1", "text": "hi"}]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = BotpressClient(api_key="test_key", bot_id="test_bot")
        response = client.get_conversations()

        expected_url = "https://api.botpress.cloud/v1/bots/test_bot/messages"
        mock_get.assert_called_once_with(
            expected_url,
            headers={"Authorization": "Bearer test_key"},
            timeout=10
        )
        self.assertEqual(response, [{"id": "m1", "text": "hi"}])

    @patch('botpress_integration.api_client.requests.get')
    def test_get_conversations_success_with_conv_id(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "m2", "text": "hello"}]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = BotpressClient(api_key="test_key", bot_id="test_bot")
        response = client.get_conversations(conversation_id="conv123")

        expected_url = "https://api.botpress.cloud/v1/bots/test_bot/conversations/conv123/messages"
        mock_get.assert_called_once_with(
            expected_url,
            headers={"Authorization": "Bearer test_key"},
            timeout=10
        )
        self.assertEqual(response, [{"id": "m2", "text": "hello"}])

    @patch('botpress_integration.api_client.requests.get')
    def test_get_conversations_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error: Not Found for url",
            response=MagicMock(status_code=404, text="Not found details")
        )
        mock_get.return_value = mock_response

        client = BotpressClient(api_key="test_key", bot_id="test_bot")
        with self.assertRaises(BotpressAPIError) as context:
            client.get_conversations(conversation_id="non_existent_conv")
        self.assertTrue("404" in str(context.exception))
        self.assertTrue("Not found details" in str(context.exception))


    @patch('botpress_integration.api_client.requests.get')
    def test_get_bot_info_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"name": "Test Bot", "version": "1.0"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        client = BotpressClient(api_key="test_key", bot_id="test_bot_info")
        response = client.get_bot_info()

        expected_url = "https://api.botpress.cloud/v1/bots/test_bot_info"
        mock_get.assert_called_once_with(
            expected_url,
            headers={"Authorization": "Bearer test_key"},
            timeout=10
        )
        self.assertEqual(response, {"name": "Test Bot", "version": "1.0"})

    @patch('botpress_integration.api_client.requests.get')
    def test_get_bot_info_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error", response=MagicMock(status_code=500, text="Server panic")
        )
        mock_get.return_value = mock_response

        client = BotpressClient(api_key="test_key", bot_id="test_bot_info")
        with self.assertRaises(BotpressAPIError) as context:
            client.get_bot_info()
        self.assertTrue("500" in str(context.exception))
        self.assertTrue("Server panic" in str(context.exception))


if __name__ == '__main__':
    unittest.main()
