import requests
import random
import logging

# Custom Exception for API specific errors
class BotpressAPIError(Exception):
    pass

class BotpressClient:
    def __init__(self, api_key, bot_id):
        self.api_key = api_key
        self.bot_id = bot_id
        self.base_url = f"https://api.botpress.cloud/v1/bots/{self.bot_id}" # Example, not hit in mock
        logging.info(f"BotpressClient initialized for bot_id: {self.bot_id}")

    def send_message(self, message_text):
        """
        Simulates sending a message to Botpress.
        In a real implementation, this would make an HTTP POST request.
        """
        logging.debug(f"Attempting to send message: '{message_text}'")
        try:
            # Simulate random errors
            if random.random() < 0.1: # 10% chance of connection error
                logging.error("Simulated ConnectionError during send_message")
                raise requests.exceptions.ConnectionError("Simulated network problem")
            if random.random() < 0.05: # 5% chance of API error
                logging.error("Simulated BotpressAPIError during send_message")
                raise BotpressAPIError("Simulated Botpress API failure (e.g., invalid token, bot down)")

            # Mock successful implementation:
            logging.info(f"Simulating successful send_message to Botpress: '{message_text}'")
            # In a real scenario, you would use requests.post:
            # headers = {
            #     "Authorization": f"Bearer {self.api_key}",
            #     "Content-Type": "application/json"
            # }
            # payload = {"text": message_text, "type": "text", "conversationId": "default"} # conversationId might be needed
            # response = requests.post(f"{self.base_url}/messages", json=payload, headers=headers)
            # response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            # return response.json()
            return f"Botpress mock response to: {message_text}"

        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error while sending message: {e}", exc_info=True)
            raise  # Re-raise for UI to handle or display
        except requests.exceptions.Timeout as e:
            logging.error(f"Timeout while sending message: {e}", exc_info=True)
            raise
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error while sending message: {e} - Response: {e.response.text if e.response else 'N/A'}", exc_info=True)
            raise BotpressAPIError(f"HTTP Error: {e.response.status_code if e.response else 'Unknown'}")
        except BotpressAPIError as e: # Custom API error
            logging.error(f"Botpress API error while sending message: {e}", exc_info=True)
            raise
        except Exception as e:
            logging.error(f"Unexpected error in send_message: {e}", exc_info=True)
            raise BotpressAPIError(f"An unexpected error occurred: {e}")


    def get_conversations(self):
        """
        Simulates retrieving conversation history from Botpress.
        In a real implementation, this would make an HTTP GET request.
        """
        logging.debug("Attempting to get conversation history.")
        try:
            # Simulate random errors
            if random.random() < 0.1: # 10% chance of connection error
                logging.error("Simulated ConnectionError during get_conversations")
                raise requests.exceptions.ConnectionError("Simulated network problem retrieving history")
            if random.random() < 0.05: # 5% chance of API error
                logging.error("Simulated BotpressAPIError during get_conversations")
                raise BotpressAPIError("Simulated Botpress API failure retrieving history")

            # Mock successful implementation:
            logging.info("Simulating successful get_conversations from Botpress.")
            # In a real scenario, you would use requests.get:
            # headers = {"Authorization": f"Bearer {self.api_key}"}
            # response = requests.get(f"{self.base_url}/conversations/default/messages", headers=headers) # Adjust endpoint as needed
            # response.raise_for_status()
            # return response.json().get("messages", [])
            return [
                {"sender": "Bot", "text": "Hello! This is a mock history message."},
                {"sender": "User", "text": "I previously asked about my account."},
                {"sender": "Bot", "text": "And I mockingly offered to help."}
            ]
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error while getting conversations: {e}", exc_info=True)
            raise
        except requests.exceptions.Timeout as e:
            logging.error(f"Timeout while getting conversations: {e}", exc_info=True)
            raise
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error while getting conversations: {e} - Response: {e.response.text if e.response else 'N/A'}", exc_info=True)
            raise BotpressAPIError(f"HTTP Error: {e.response.status_code if e.response else 'Unknown'}")
        except BotpressAPIError as e: # Custom API error
            logging.error(f"Botpress API error while getting conversations: {e}", exc_info=True)
            raise
        except Exception as e:
            logging.error(f"Unexpected error in get_conversations: {e}", exc_info=True)
            raise BotpressAPIError(f"An unexpected error occurred retrieving conversations: {e}")


if __name__ == '__main__':
    # Example Usage (for testing purposes)
    # Configure basic logging for testing this module directly
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

    mock_api_key = "MOCK_API_KEY"
    mock_bot_id = "MOCK_BOT_ID"

    client = BotpressClient(api_key=mock_api_key, bot_id=mock_bot_id)

    print("\n--- Testing send_message (will run multiple times to check random errors) ---")
    for i in range(5):
        try:
            print(f"Attempt {i+1}:")
            response = client.send_message(f"Test message {i+1}")
            print(f"  send_message response: {response}")
        except (requests.exceptions.ConnectionError, BotpressAPIError, Exception) as e:
            print(f"  send_message caught error: {e.__class__.__name__} - {e}")

    print("\n--- Testing get_conversations (will run multiple times to check random errors) ---")
    for i in range(3):
        try:
            print(f"Attempt {i+1}:")
            conversations = client.get_conversations()
            print("  get_conversations response:")
            for msg in conversations:
                print(f"  - {msg['sender']}: {msg['text']}")
        except (requests.exceptions.ConnectionError, BotpressAPIError, Exception) as e:
            print(f"  get_conversations caught error: {e.__class__.__name__} - {e}")
