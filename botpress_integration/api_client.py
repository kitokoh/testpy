import requests
import random
import logging

# Custom Exception for API specific errors
class BotpressAPIError(Exception):
    pass

class BotpressClient:
    def __init__(self, api_key, bot_id, base_url="https://api.botpress.cloud/v1/"):
        self.api_key = api_key
        self.bot_id = bot_id
        # Ensure base_url ends with a slash
        if not base_url.endswith('/'):
            base_url += '/'
        self.base_url = base_url
        self.bot_specific_url = f"{self.base_url}bots/{self.bot_id}"
        logging.info(f"BotpressClient initialized for bot_id: {self.bot_id} using base_url: {self.base_url}")

    def send_message(self, message_text, conversation_id=None):
        """
        Sends a message to the Botpress bot.
        Optionally, a conversation_id can be provided to send the message to a specific conversation.
        """
        logging.debug(f"Attempting to send message: '{message_text}' to bot {self.bot_id}, conversation_id: {conversation_id}")
        endpoint_url = f"{self.bot_specific_url}/messages"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": message_text,
            "type": "text"
        }
        if conversation_id:
            payload["conversationId"] = conversation_id

        try:
            response = requests.post(endpoint_url, json=payload, headers=headers, timeout=10) # 10s timeout
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            logging.info(f"Message sent successfully to {endpoint_url}. Response: {response.json()}")
            return response.json()
        except requests.exceptions.Timeout as e:
            logging.error(f"Timeout occurred while sending message to {endpoint_url}: {e}", exc_info=True)
            raise BotpressAPIError(f"Timeout sending message to Botpress: {e}")
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error occurred while sending message to {endpoint_url}: {e}", exc_info=True)
            raise BotpressAPIError(f"Connection error sending message to Botpress: {e}")
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error for {endpoint_url}: {e.response.status_code} - {e.response.text}", exc_info=True)
            raise BotpressAPIError(f"Botpress API HTTP error: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e: # Catch any other requests-related errors
            logging.error(f"Error sending message to {endpoint_url}: {e}", exc_info=True)
            raise BotpressAPIError(f"Failed to send message to Botpress: {e}")
        except Exception as e: # Catch any other unexpected errors
            logging.error(f"Unexpected error in send_message to {endpoint_url}: {e}", exc_info=True)
            raise BotpressAPIError(f"An unexpected error occurred while sending message: {e}")

    def get_conversations(self, conversation_id=None):
        """
        Retrieves messages.
        If conversation_id is provided, fetches messages for that specific conversation.
        Otherwise, fetches generic messages for the bot (actual behavior depends on Botpress API).
        """
        if conversation_id:
            endpoint_url = f"{self.bot_specific_url}/conversations/{conversation_id}/messages"
            logging.debug(f"Attempting to get messages for bot {self.bot_id}, conversation_id: {conversation_id}")
        else:
            endpoint_url = f"{self.bot_specific_url}/messages"
            logging.debug(f"Attempting to get messages for bot {self.bot_id} (no specific conversation_id)")

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            response = requests.get(endpoint_url, headers=headers, timeout=10) # 10s timeout
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            # Assuming the response JSON has a "messages" key containing a list of messages.
            # This might need adjustment based on the actual Botpress API response structure.
            messages = response.json().get("messages", [])
            logging.info(f"Successfully retrieved {len(messages)} messages from {endpoint_url}.")
            return messages
        except requests.exceptions.Timeout as e:
            logging.error(f"Timeout occurred while getting messages from {endpoint_url}: {e}", exc_info=True)
            raise BotpressAPIError(f"Timeout getting messages from Botpress: {e}")
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error occurred while getting messages from {endpoint_url}: {e}", exc_info=True)
            raise BotpressAPIError(f"Connection error getting messages from Botpress: {e}")
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error for {endpoint_url}: {e.response.status_code} - {e.response.text}", exc_info=True)
            raise BotpressAPIError(f"Botpress API HTTP error: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e: # Catch any other requests-related errors
            logging.error(f"Error getting messages from {endpoint_url}: {e}", exc_info=True)
            raise BotpressAPIError(f"Failed to get messages from Botpress: {e}")
        except Exception as e: # Catch any other unexpected errors
            logging.error(f"Unexpected error in get_conversations from {endpoint_url}: {e}", exc_info=True)
            raise BotpressAPIError(f"An unexpected error occurred while retrieving messages: {e}")

    def get_bot_info(self):
        """
        Retrieves information about the bot.
        This can be used to validate the bot_id and API key.
        """
        # The endpoint for bot information is typically the bot-specific URL itself.
        endpoint_url = self.bot_specific_url
        logging.debug(f"Attempting to get bot info from {endpoint_url}")

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            response = requests.get(endpoint_url, headers=headers, timeout=10)
            response.raise_for_status()
            bot_info = response.json()
            logging.info(f"Successfully retrieved bot info from {endpoint_url}: {bot_info}")
            return bot_info
        except requests.exceptions.Timeout as e:
            logging.error(f"Timeout occurred while getting bot info from {endpoint_url}: {e}", exc_info=True)
            raise BotpressAPIError(f"Timeout getting bot info: {e}")
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error occurred while getting bot info from {endpoint_url}: {e}", exc_info=True)
            raise BotpressAPIError(f"Connection error getting bot info: {e}")
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error for {endpoint_url}: {e.response.status_code} - {e.response.text}", exc_info=True)
            raise BotpressAPIError(f"Botpress API HTTP error getting bot info: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error getting bot info from {endpoint_url}: {e}", exc_info=True)
            raise BotpressAPIError(f"Failed to get bot info: {e}")
        except Exception as e:
            logging.error(f"Unexpected error in get_bot_info from {endpoint_url}: {e}", exc_info=True)
            raise BotpressAPIError(f"An unexpected error occurred while retrieving bot info: {e}")

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    # Configure basic logging for testing this module directly
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

    # IMPORTANT: Replace with your actual API key and Bot ID for real testing.
    # Using mock values will likely result in authentication errors (e.g., 401 Unauthorized).
    actual_api_key = "MOCK_API_KEY_REPLACE_ME_FOR_REAL_TESTS"
    actual_bot_id = "MOCK_BOT_ID_REPLACE_ME_FOR_REAL_TESTS"
    # Example: Test with a specific conversation ID
    mock_conversation_id = "mock_conv_12345"

    # To use a custom Botpress instance (e.g. self-hosted):
    # custom_base_url = "http://localhost:3000/api/v1/"
    # client = BotpressClient(api_key=actual_api_key, bot_id=actual_bot_id, base_url=custom_base_url)

    client = BotpressClient(api_key=actual_api_key, bot_id=actual_bot_id)

    print("--- Example API Client Usage ---")
    print(f"Using Bot ID: {client.bot_id}")
    print(f"Using Base URL: {client.base_url}")
    print(f"Bot-specific URL: {client.bot_specific_url}")
    print("\nNOTE: The following API calls will use MOCK credentials by default.")
    print("Replace MOCK_API_KEY and MOCK_BOT_ID with real credentials to interact with Botpress.")
    print("Expect errors (like 401 Unauthorized) if using mock credentials against a real API endpoint.")

    print("\n--- Testing get_bot_info ---")
    try:
        bot_info = client.get_bot_info()
        print(f"  get_bot_info response: {bot_info}")
    except BotpressAPIError as e:
        print(f"  get_bot_info caught error: {e}")
    except Exception as e:
        print(f"  get_bot_info caught unexpected error: {e}")

    print("\n--- Testing send_message (without conversation_id) ---")
    try:
        test_message = "Hello from the API client example (no conv_id)!"
        response = client.send_message(test_message)
        print(f"  send_message response to '{test_message}': {response}")
    except BotpressAPIError as e:
        print(f"  send_message caught error: {e}")
    except Exception as e:
        print(f"  send_message caught unexpected error: {e}")

    print("\n--- Testing send_message (with conversation_id) ---")
    try:
        test_message_with_conv = "Hello from the API client example (with conv_id)!"
        response_with_conv = client.send_message(test_message_with_conv, conversation_id=mock_conversation_id)
        print(f"  send_message response to '{test_message_with_conv}' (conv_id: {mock_conversation_id}): {response_with_conv}")
    except BotpressAPIError as e:
        print(f"  send_message (with conv_id) caught error: {e}")
    except Exception as e:
        print(f"  send_message (with conv_id) caught unexpected error: {e}")

    print("\n--- Testing get_conversations (fetching messages without conversation_id) ---")
    try:
        messages = client.get_conversations()
        print(f"  get_conversations response (no conv_id) (messages received: {len(messages)}):")
        if messages:
            for i, msg in enumerate(messages[:3]): # Print first 3 messages
                print(f"    Message {i+1}: {msg}")
        elif not messages and actual_api_key != "MOCK_API_KEY_REPLACE_ME_FOR_REAL_TESTS":
             print("  No messages found (no conv_id), or the endpoint/bot configuration needs review.")
        else:
            print("  No messages retrieved (no conv_id) (as expected with mock credentials or if bot has no messages).")
    except BotpressAPIError as e:
        print(f"  get_conversations (no conv_id) caught error: {e}")
    except Exception as e:
        print(f"  get_conversations (no conv_id) caught unexpected error: {e}")

    print("\n--- Testing get_conversations (fetching messages with conversation_id) ---")
    try:
        messages_with_conv = client.get_conversations(conversation_id=mock_conversation_id)
        print(f"  get_conversations response (conv_id: {mock_conversation_id}) (messages received: {len(messages_with_conv)}):")
        if messages_with_conv:
            for i, msg in enumerate(messages_with_conv[:3]): # Print first 3 messages
                print(f"    Message {i+1}: {msg}")
        elif not messages_with_conv and actual_api_key != "MOCK_API_KEY_REPLACE_ME_FOR_REAL_TESTS":
            print(f"  No messages found for conv_id {mock_conversation_id}, or the endpoint/bot configuration needs review.")
        else:
            print(f"  No messages retrieved for conv_id {mock_conversation_id} (as expected with mock credentials or if bot has no messages for this specific conversation).")
    except BotpressAPIError as e:
        print(f"  get_conversations (with conv_id) caught error: {e}")
    except Exception as e:
        print(f"  get_conversations (with conv_id) caught unexpected error: {e}")
