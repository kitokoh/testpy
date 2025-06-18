import requests
import logging
import json # For parsing response text if it's not automatically parsed by requests

# Standard Botpress Cloud URL. This might need to be configurable for self-hosted instances.
DEFAULT_BOTPRESS_URL = "https://api.botpress.cloud"

# Custom Exception for API specific errors
class BotpressAPIError(Exception):
    """Custom exception for Botpress API related errors."""
    def __init__(self, message, status_code=None, response_text=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        self.message = message

    def __str__(self):
        return f"{self.message} (Status Code: {self.status_code})"

class BotpressClient:
    def __init__(self, api_key: str, bot_id: str, botpress_url: str = None):
        """
        Initializes the Botpress Client.
        Args:
            api_key (str): The API key for Botpress.
            bot_id (str): The ID of the bot to interact with.
            botpress_url (str, optional): The base URL of the Botpress instance.
                                         Defaults to Botpress Cloud URL.
        """
        if not api_key:
            raise ValueError("API key is required.")
        if not bot_id:
            raise ValueError("Bot ID is required.")

        self.api_key = api_key
        self.bot_id = bot_id
        self.botpress_url = botpress_url or DEFAULT_BOTPRESS_URL

        # Construct the base API URL for the specific bot
        self.base_api_url = f"{self.botpress_url}/api/v1/bots/{self.bot_id}"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logging.info(f"BotpressClient initialized for bot_id: {self.bot_id} at {self.base_api_url}")

    def send_message(self, user_id: str, message_text: str) -> list[dict]:
        """
        Sends a message to Botpress and retrieves the bot's response(s).
        Args:
            user_id (str): A unique identifier for the user interacting with the bot.
                           This is used by Botpress to maintain conversation state.
            message_text (str): The text message from the user.
        Returns:
            list[dict]: A list of message objects from the bot. Each message object
                        is a dictionary, and we primarily look for 'text' in 'payload'.
                        Focuses on extracting text responses.
        Raises:
            BotpressAPIError: If the API request fails or returns an error status.
            requests.exceptions.RequestException: For network issues.
        """
        if not user_id:
            raise ValueError("user_id is required to send a message.")
        if not message_text:
            raise ValueError("message_text cannot be empty.")

        # API endpoint for sending a message to a specific user's conversation
        # The `user_id` is often part of the path or managed by Botpress through `x-bp-user-id` or similar.
        # For Botpress v12 style, it's often /converse/USER_ID
        # For Botpress Cloud, it might be /conversations/USER_ID/messages
        # Assuming Botpress Cloud structure for this example.
        # It's crucial to verify this endpoint with the specific Botpress version/setup.
        # A common pattern is POST /conversations/{conversationId}/messages where conversationId might be == user_id or derived.
        # Another pattern is POST /converse/{userId}

        # Let's use the /conversations/{userId}/messages endpoint as it's common in newer Botpress versions.
        # If user_id directly maps to conversationId.
        # If not, one might need to first create/get a conversationId for the user_id.
        # For simplicity, we'll assume user_id can be used as conversationId here.
        # This is a MAJOR assumption. Production systems might need a more robust conversation management.

        # Endpoint: POST /api/v1/bots/{botId}/conversations/{conversationId}/messages
        # OR for creating a new message in a new or existing conversation (Botpress Cloud often uses this)
        # POST /api/v1/bots/{botId}/messages (and user_id/conversationId is part of payload or handled by Botpress)
        # Let's assume the /converse/{userId} endpoint for simplicity as it's often a starting point.
        # If this is not correct, it will need adjustment.
        # The Botpress documentation for "Create Message" API is the source of truth.
        # Example: POST https://api.botpress.cloud/v1/bots/YOUR_BOT_ID/converse/SOME_USER_ID

        # This is a common endpoint pattern; replace 'default' with user_id if that's the convention.
        # For Botpress Cloud, the /converse endpoint is often used to send a message and get an immediate reply.
        # The `user_id` here is the "conversation ID" for the /converse endpoint.
        converse_url = f"{self.base_api_url}/converse/{user_id}"

        payload = {
            "type": "text",
            "text": message_text
            # Additional fields like `metadata` or `tags` could be added if needed.
        }

        logging.debug(f"Sending message to {converse_url}. Payload: {json.dumps(payload)}")

        try:
            response = requests.post(converse_url, headers=self.headers, json=payload, timeout=10) # 10-second timeout
            response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses

            response_data = response.json()
            logging.debug(f"Received response from Botpress: {response_data}")

            # Botpress responses often come in an array called 'responses' or 'messages'.
            # Each item in the array is a directive for the client (e.g., display text, show an image).
            # We are interested in text responses.
            # The structure can vary, e.g., response_data.get('responses', []) or response_data.get('messages', [])
            # A common structure for /converse is a list of "directives"
            bot_messages = []
            if 'responses' in response_data and isinstance(response_data['responses'], list):
                for resp_item in response_data['responses']:
                    if resp_item.get('type') == 'text': # Check if it's a text message
                        # Text content might be in 'text', 'message', 'content.text', 'payload.text' etc.
                        # For Botpress Cloud /converse, it's often in `content.text` or `text` directly.
                        # Example: {"type":"text","content":{"text":"Hello there"}}
                        # Or: {"type":"text","text":"Hello there"}
                        text_content = None
                        if 'text' in resp_item:
                            text_content = resp_item['text']
                        elif 'content' in resp_item and isinstance(resp_item['content'], dict) and 'text' in resp_item['content']:
                            text_content = resp_item['content']['text']

                        if text_content:
                            bot_messages.append({"type": "text", "text": text_content})
            elif 'choices' in response_data: # Handle quick replies / choices if needed
                # For now, we just acknowledge them if they appear at top level
                logging.info(f"Bot offered choices: {response_data['choices']}")
                # You might want to format these choices into a text message or handle them differently.

            if not bot_messages and response_data: # If no specific text messages found, but got a response
                logging.warning(f"No standard text responses extracted, but received data: {response_data}")
                # You might want to return a generic message or the raw data in some cases.

            return bot_messages # Return a list of extracted text messages (dicts)

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            response_text = e.response.text
            logging.error(f"HTTP error {status_code} while sending message: {response_text}", exc_info=True)
            if status_code == 401:
                raise BotpressAPIError("Unauthorized. Check API key.", status_code, response_text)
            elif status_code == 403:
                raise BotpressAPIError("Forbidden. You may not have permissions for this bot or action.", status_code, response_text)
            elif status_code == 404: # Could be bot_id not found, or user_id/conversation_id format issue
                raise BotpressAPIError(f"Bot or conversation endpoint not found (404): {converse_url}", status_code, response_text)
            else:
                raise BotpressAPIError(f"Botpress API request failed with status {status_code}.", status_code, response_text)
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error while sending message: {e}", exc_info=True)
            raise BotpressAPIError(f"Connection error: {e}") # Wrap in BotpressAPIError for consistent handling by UI
        except requests.exceptions.Timeout as e:
            logging.error(f"Timeout while sending message: {e}", exc_info=True)
            raise BotpressAPIError(f"Request timed out: {e}")
        except requests.exceptions.RequestException as e: # Catch any other requests-related error
            logging.error(f"Request exception while sending message: {e}", exc_info=True)
            raise BotpressAPIError(f"An unexpected network error occurred: {e}")
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON response from Botpress: {e}. Response text: {response.text if 'response' in locals() else 'N/A'}", exc_info=True)
            raise BotpressAPIError("Failed to parse Botpress response (Invalid JSON).")
        except Exception as e:
            logging.error(f"Unexpected error in send_message: {e}", exc_info=True)
            raise BotpressAPIError(f"An unexpected error occurred: {e}")


    def get_conversations(self, user_id: str, limit: int = 50) -> list[dict]:
        """
        Retrieves conversation history for a specific user from Botpress.
        Note: This is a common desired feature, but the specific API endpoint and its
        availability can vary significantly between Botpress versions (v12, Cloud, etc.).
        This implementation assumes a common REST pattern; actual endpoint might differ.
        Args:
            user_id (str): The user ID for whom to fetch conversation history.
                           This often maps to a conversationId.
            limit (int): Number of messages to retrieve.
        Returns:
            list[dict]: A list of message objects, or an empty list if not found/supported.
        Raises:
            BotpressAPIError: If the API request fails.
            requests.exceptions.RequestException: For network issues.
        """
        if not user_id:
            raise ValueError("user_id is required to get conversations.")

        # Endpoint: GET /api/v1/bots/{botId}/conversations/{conversationId}/messages
        # This is a common pattern. `user_id` is assumed to be the `conversationId`.
        history_url = f"{self.base_api_url}/conversations/{user_id}/messages"
        params = {"limit": limit, "sortOrder": "desc"} # Get latest messages first

        logging.debug(f"Attempting to get conversation history from {history_url} with params: {params}")

        try:
            response = requests.get(history_url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status() # Raises HTTPError for 4xx/5xx

            response_data = response.json()
            logging.debug(f"Received conversation history response: {response_data}")

            # The response structure for messages usually is a list under a key like "messages" or "items".
            # Example: {"messages": [...], "meta": {...}}
            messages = response_data.get("messages", [])
            if not messages and isinstance(response_data, list): # Sometimes the root is the list
                messages = response_data

            # We might want to reverse the order if they come in desc by default from API
            return list(reversed(messages)) if messages else []

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            response_text = e.response.text
            logging.error(f"HTTP error {status_code} while getting conversations: {response_text}", exc_info=True)
            if status_code == 401:
                raise BotpressAPIError("Unauthorized. Check API key.", status_code, response_text)
            elif status_code == 403:
                 raise BotpressAPIError("Forbidden. You may not have permissions for this bot or action.", status_code, response_text)
            elif status_code == 404: # Conversation history might not exist or endpoint is wrong
                logging.warning(f"Conversation history not found (404) for user {user_id} at {history_url}. This might mean no history or incorrect endpoint.")
                # For 404, it might be valid that no history exists, so return empty list.
                # However, it could also mean the endpoint itself is wrong.
                # Depending on Botpress version, a 404 for conversation history might be "normal" if no messages.
                # For now, let's treat 404 as "no history" rather than a hard error,
                # unless we have specific knowledge this endpoint *must* exist.
                return []
            else:
                raise BotpressAPIError(f"Botpress API request failed with status {status_code}.", status_code, response_text)
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error while getting conversations: {e}", exc_info=True)
            raise BotpressAPIError(f"Connection error: {e}")
        except requests.exceptions.Timeout as e:
            logging.error(f"Timeout while getting conversations: {e}", exc_info=True)
            raise BotpressAPIError(f"Request timed out: {e}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request exception while getting conversations: {e}", exc_info=True)
            raise BotpressAPIError(f"An unexpected network error occurred: {e}")
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON response for history: {e}. Response text: {response.text if 'response' in locals() else 'N/A'}", exc_info=True)
            raise BotpressAPIError("Failed to parse Botpress history response (Invalid JSON).")
        except Exception as e:
            logging.error(f"Unexpected error in get_conversations: {e}", exc_info=True)
            # For get_conversations, it might be better to return empty list on unexpected error
            # than to break the UI completely if history is non-critical.
            # However, for now, re-raising to make it visible.
            raise BotpressAPIError(f"An unexpected error occurred retrieving conversations: {e}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

    # --- IMPORTANT ---
    # To test this locally, you NEED to replace these with your ACTUAL Botpress credentials and IDs.
    # Ensure the Botpress instance is running and accessible.
    # You might also need to adjust DEFAULT_BOTPRESS_URL if self-hosting.

    # Example credentials (REPLACE THESE or set environment variables)
    # import os
    # test_api_key = os.environ.get("BOTPRESS_API_KEY")
    # test_bot_id = os.environ.get("BOTPRESS_BOT_ID")
    # test_user_id = "test_user_for_api_client_py" # A unique ID for your test user
    # test_botpress_url = os.environ.get("BOTPRESS_URL", DEFAULT_BOTPRESS_URL)

    # Hardcoded for example - REPLACE IF YOU UNCOMMENT AND RUN
    test_api_key = "YOUR_ACTUAL_API_KEY"
    test_bot_id = "YOUR_ACTUAL_BOT_ID"
    test_user_id = "local_test_user_12345"
    test_botpress_url = DEFAULT_BOTPRESS_URL # Or your self-hosted URL

    if test_api_key == "YOUR_ACTUAL_API_KEY" or test_bot_id == "YOUR_ACTUAL_BOT_ID":
        logging.warning("Using placeholder API key/Bot ID. Real API calls will fail. Update __main__ block with real credentials to test.")
    else:
        logging.info(f"Using Bot ID: {test_bot_id} and User ID: {test_user_id} for testing.")

        try:
            client = BotpressClient(api_key=test_api_key, bot_id=test_bot_id, botpress_url=test_botpress_url)

            # 1. Test sending a message
            logging.info("\n--- Testing send_message ---")
            try:
                message_to_send = "Hello from api_client.py test!"
                responses = client.send_message(user_id=test_user_id, message_text=message_to_send)
                if responses:
                    logging.info(f"send_message successful. Bot responses for '{message_to_send}':")
                    for i, resp in enumerate(responses):
                        logging.info(f"  Response {i+1}: Type: {resp.get('type')}, Text: {resp.get('text', 'N/A')}")
                else:
                    logging.warning(f"send_message returned no text responses for '{message_to_send}'. Full response might be logged above.")
            except BotpressAPIError as e:
                logging.error(f"send_message failed: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"An unexpected error occurred during send_message test: {e}", exc_info=True)

            # 2. Test getting conversation history
            logging.info("\n--- Testing get_conversations ---")
            try:
                history = client.get_conversations(user_id=test_user_id, limit=10)
                if history:
                    logging.info(f"get_conversations successful. Retrieved {len(history)} messages for user {test_user_id}:")
                    for i, msg in enumerate(history):
                        # Log the whole message object to see its structure
                        logging.info(f"  Msg {i+1}: {msg}")
                else:
                    logging.info(f"No conversation history found or returned for user {test_user_id}.")
            except BotpressAPIError as e:
                logging.error(f"get_conversations failed: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"An unexpected error occurred during get_conversations test: {e}", exc_info=True)

        except ValueError as ve:
            logging.error(f"Initialization error: {ve}")
        except Exception as e:
            logging.error(f"A critical error occurred during client setup or testing: {e}", exc_info=True)
