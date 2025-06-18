import asyncio
import json
import logging
import requests # Ensure this is in your project's requirements.txt
from typing import Dict, Any, Optional

from .base_connector import BasePlatformConnector, BaseConnectorConfig, MessageCallback

logger = logging.getLogger(__name__)

# --- WhatsApp Specific Configuration ---

DEFAULT_WHATSAPP_BASE_URL = "https://graph.facebook.com/v18.0/" # Example, version might change

class WhatsAppConnectorConfig(BaseConnectorConfig):
    """
    Configuration specific to the WhatsApp Business API Connector.
    """
    phone_number_id: str
    whatsapp_business_api_token: str
    base_url: Optional[str] # Optional, defaults to a common Facebook Graph API URL


# --- WhatsApp Connector Implementation ---

class WhatsAppConnector(BasePlatformConnector):
    """
    Connector for interacting with the WhatsApp Business API (via Meta/Facebook Graph API).

    This connector handles sending messages. Receiving messages typically requires setting up
    a webhook endpoint that Meta's servers will call, which is outside the direct
    scope of this client's `start_listening` method for active connections like WebSockets.
    """

    def __init__(self, config: WhatsAppConnectorConfig):
        """
        Initializes the WhatsApp Connector.

        Args:
            config (WhatsAppConnectorConfig): Configuration dictionary containing:
                - platform_name (str): Should be "whatsapp".
                - is_enabled (bool): Whether this connector is active.
                - phone_number_id (str): The Phone Number ID from Meta for Developers.
                - whatsapp_business_api_token (str): The access token for the WhatsApp Business API.
                - base_url (str, optional): The base URL for the Graph API. Defaults to a recent version.
        """
        super().__init__(config) # Sets self._config, self._is_connected, self.loop

        self.phone_number_id = config.get("phone_number_id")
        self.api_token = config.get("whatsapp_business_api_token")
        self.base_url = config.get("base_url") or DEFAULT_WHATSAPP_BASE_URL

        if not self.phone_number_id:
            raise ValueError("WhatsApp Connector: 'phone_number_id' is required in config.")
        if not self.api_token:
            raise ValueError("WhatsApp Connector: 'whatsapp_business_api_token' is required in config.")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        })
        logger.info(f"WhatsAppConnector initialized for Phone Number ID: {self.phone_number_id} using base URL: {self.base_url}")

    def _handle_api_error(self, response: requests.Response, context: str) -> None:
        """
        Private helper to consistently log and handle API errors from WhatsApp.
        Args:
            response (requests.Response): The response object from the requests library.
            context (str): A string describing the context of the API call (e.g., "sending message").
        """
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "No error message provided.")
            error_type = error_data.get("error", {}).get("type", "UnknownError")
            error_code = error_data.get("error", {}).get("code", "N/A")
            fb_trace_id = error_data.get("error", {}).get("fbtrace_id", "N/A")
            logger.error(
                f"WhatsApp API error while {context}: {error_message} (Type: {error_type}, Code: {error_code}, Status: {response.status_code}, FBTraceID: {fb_trace_id})"
            )
        except json.JSONDecodeError:
            logger.error(
                f"WhatsApp API error while {context}: Status {response.status_code}, Content: {response.text}"
            )

    async def connect(self) -> bool:
        """
        Establishes and verifies the connection to WhatsApp Business API.
        This typically involves making a simple test API call, e.g., to get app fields.
        """
        if self._is_connected:
            logger.info(f"[{self.platform_name}] Already connected.")
            return True

        # A simple test: try to get information about the phone number ID.
        # Endpoint: GET /{phone-number-ID}?fields=name,display_phone_number
        test_url = f"{self.base_url.rstrip('/')}/{self.phone_number_id}?fields=display_phone_number"
        logger.info(f"[{self.platform_name}] Attempting to connect by verifying Phone Number ID info at {test_url}...")

        try:
            # Run requests call in a separate thread to avoid blocking asyncio loop
            response = await self.loop.run_in_executor(None, lambda: self.session.get(test_url, timeout=10))

            if response.status_code == 200:
                data = response.json()
                logger.info(f"[{self.platform_name}] Connection test successful. Display Phone: {data.get('display_phone_number', 'N/A')}")
                self._is_connected = True
                return True
            else:
                self._handle_api_error(response, "connecting (verifying phone number ID)")
                self._is_connected = False
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"[{self.platform_name}] Network error during connection test: {e}", exc_info=True)
            self._is_connected = False
            return False
        except Exception as e:
            logger.error(f"[{self.platform_name}] Unexpected error during connection test: {e}", exc_info=True)
            self._is_connected = False
            return False

    async def disconnect(self) -> bool:
        """
        "Disconnects" from WhatsApp API by closing the session.
        Actual persistent connections are not standard for this type of HTTP API.
        """
        logger.info(f"[{self.platform_name}] Disconnecting...")
        if hasattr(self, 'session') and self.session:
            await self.loop.run_in_executor(None, self.session.close)
        self._is_connected = False
        logger.info(f"[{self.platform_name}] Disconnected (session closed).")
        return True

    async def send_message(self, recipient_id: str, message_content: Dict[str, Any]) -> bool:
        """
        Sends a message to a WhatsApp user.

        Args:
            recipient_id (str): The recipient's WhatsApp phone number (with country code, no '+').
            message_content (Dict[str, Any]): A dictionary defining the message.
                Example for text: `{'type': 'text', 'text': 'Hello!'}`
                Future types: 'image', 'document', 'template', etc.

        Returns:
            bool: True if the message was accepted by WhatsApp API, False otherwise.
        """
        if not self.is_connected:
            logger.error(f"[{self.platform_name}] Cannot send message, not connected.")
            return False
        if not recipient_id:
            logger.error(f"[{self.platform_name}] Recipient ID is required.")
            return False

        msg_type = message_content.get("type", "text")
        text_body = message_content.get("text")

        if msg_type == "text" and text_body:
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "text",
                "text": {"body": text_body}
            }
        # TODO: Add support for other message types (image, template, etc.)
        # elif msg_type == "template":
        #     payload = { ... }
        else:
            logger.error(f"[{self.platform_name}] Unsupported message type '{msg_type}' or missing content.")
            return False

        messages_url = f"{self.base_url.rstrip('/')}/{self.phone_number_id}/messages"

        logger.debug(f"[{self.platform_name}] Sending message to {recipient_id} via {messages_url}. Payload: {payload}")

        try:
            response = await self.loop.run_in_executor(None, lambda: self.session.post(messages_url, json=payload, timeout=15))

            if response.status_code == 200:
                response_data = response.json()
                message_ids = [msg.get('id') for msg in response_data.get('messages', []) if msg.get('id')]
                logger.info(f"[{self.platform_name}] Message sent successfully to {recipient_id}. Message IDs: {message_ids}")
                return True
            else:
                self._handle_api_error(response, f"sending message to {recipient_id}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"[{self.platform_name}] Network error sending message to {recipient_id}: {e}", exc_info=True)
            return False
        except Exception as e: # Catch-all for other unexpected errors
            logger.error(f"[{self.platform_name}] Unexpected error sending message to {recipient_id}: {e}", exc_info=True)
            return False

    async def start_listening(self, callback: MessageCallback) -> None:
        """
        Prepares for receiving messages. For WhatsApp, this usually means a webhook is configured.
        This method itself doesn't run a persistent listener but can confirm readiness.

        The actual incoming messages would be handled by a separate web server endpoint
        that calls a method on this connector instance (e.g., `handle_incoming_webhook_payload`).
        Such a method would then parse the payload and invoke the `callback`.

        Args:
            callback (MessageCallback): The callback to be invoked by the webhook handler.
        """
        if not self.is_connected:
            logger.warning(f"[{self.platform_name}] Not connected. Cannot 'start listening'. Ensure webhook is configured separately.")
            return

        self.message_callback = callback # Store the callback for the webhook handler to use
        logger.info(f"[{self.platform_name}] Now 'listening'. Webhook endpoint should be configured and active.")
        logger.info(f"[{self.platform_name}] Incoming messages will be processed by the registered callback via a webhook handler.")
        # In a real scenario, you might register the webhook URL with Meta here if not done manually,
        # or verify its status. For now, this is conceptual.

    async def stop_listening(self) -> None:
        """
        Conceptually stops listening. For webhooks, this might mean de-registering
        the webhook or simply logging that the system will no longer process callbacks.
        """
        logger.info(f"[{self.platform_name}] 'Stopped listening'. No further messages will be processed via callbacks from this instance.")
        # If there were any active tasks related to listening (e.g., a health check for webhook), stop them.
        if hasattr(self, 'message_callback'):
            del self.message_callback # Remove callback reference

    # --- Example method that a webhook endpoint would call ---
    async def handle_incoming_webhook_payload(self, payload: Dict[str, Any]):
        """
        Processes an incoming webhook payload from WhatsApp.
        This method should be called by your web server's route handler for WhatsApp webhooks.

        It transforms the platform-specific payload into the standardized message format
        and then calls the registered `message_callback`.

        Args:
            payload (Dict[str, Any]): The raw JSON payload from the WhatsApp webhook.
        """
        logger.info(f"[{self.platform_name}] Received raw webhook payload: {json.dumps(payload, indent=2)}")
        if not hasattr(self, 'message_callback') or not self.message_callback:
            logger.warning(f"[{self.platform_name}] No message callback registered. Ignoring incoming webhook.")
            return

        # WhatsApp webhook payload parsing can be complex due to varied structures.
        # This is a simplified parser for common text messages.
        # Refer to Meta documentation for full payload structure:
        # https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components

        # Typically, messages are in `entry[0].changes[0].value.messages[0]`
        try:
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    metadata = value.get("metadata", {}) # Contains display_phone_number, phone_number_id

                    if "messages" in value:
                        for message_data in value["messages"]:
                            if message_data.get("type") == "text":
                                sender_id = message_data.get("from") # User's phone number
                                recipient_id = metadata.get("phone_number_id") # Bot's phone number ID
                                timestamp_ms = message_data.get("timestamp") # Unix timestamp (string)

                                dt_object = datetime.fromtimestamp(int(timestamp_ms)) if timestamp_ms else datetime.now()
                                iso_timestamp = dt_object.isoformat()

                                standardized_msg = {
                                    'platform': self.platform_name,
                                    'connector_id': self.phone_number_id, # Using phone_number_id as a unique connector ID
                                    'sender_id': sender_id,
                                    'recipient_id': recipient_id,
                                    'conversation_id': sender_id, # For 1-on-1 chats, sender_id is often the conversation key
                                    'message_id': message_data.get("id"),
                                    'timestamp': iso_timestamp,
                                    'type': 'text',
                                    'content': {'text': message_data.get("text", {}).get("body")},
                                    'raw': message_data
                                }
                                logger.debug(f"[{self.platform_name}] Standardized message: {standardized_msg}")
                                await self.message_callback(standardized_msg)
                            # TODO: Handle other message types (image, audio, location, button clicks from templates, etc.)
                            # elif message_data.get("type") == "interactive" and message_data.get("interactive", {}).get("type") == "button_reply":
                            #    ...
                            else:
                                logger.info(f"[{self.platform_name}] Received unhandled message type: {message_data.get('type')}")
                    elif "statuses" in value:
                        # Handle message status updates (sent, delivered, read) if needed
                        for status_data in value["statuses"]:
                            logger.debug(f"[{self.platform_name}] Received status update: {status_data}")
                            # Example: {'id': 'wamid.HB...', 'status': 'delivered', ...}
                            pass # Not processing statuses into callback for now
                    else:
                        logger.debug(f"[{self.platform_name}] Received other change value: {value}")

        except Exception as e:
            logger.error(f"[{self.platform_name}] Error processing webhook payload: {e}", exc_info=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(name)s] %(message)s')

    # --- IMPORTANT: Replace with your actual test credentials and numbers ---
    # Ensure the recipient number is registered with WhatsApp and can receive messages from your business.
    # This test will likely FAIL without valid, configured credentials.
    TEST_PHONE_NUMBER_ID = "YOUR_PHONE_NUMBER_ID"  # e.g., "1001234567890"
    TEST_WABA_TOKEN = "YOUR_WHATSAPP_BUSINESS_API_TOKEN" # Should be a system user token or long-lived user token
    TEST_RECIPIENT_PHONE_NUMBER = "USER_PHONE_NUMBER_FOR_TESTING"  # e.g., "15551234567" (Country code + number, no '+')

    async def test_whatsapp_connector():
        if TEST_PHONE_NUMBER_ID == "YOUR_PHONE_NUMBER_ID" or \
           TEST_WABA_TOKEN == "YOUR_WHATSAPP_BUSINESS_API_TOKEN" or \
           TEST_RECIPIENT_PHONE_NUMBER == "USER_PHONE_NUMBER_FOR_TESTING":
            logger.warning("Update placeholder credentials in __main__ to test WhatsAppConnector.")
            return

        config: WhatsAppConnectorConfig = {
            "platform_name": "whatsapp_test",
            "is_enabled": True,
            "phone_number_id": TEST_PHONE_NUMBER_ID,
            "whatsapp_business_api_token": TEST_WABA_TOKEN,
            # "base_url": "https://graph.facebook.com/v17.0/" # Optional: if you need a different API version
        }
        connector = WhatsAppConnector(config)

        # Test Connection
        logger.info("--- Testing Connection ---")
        connected = await connector.connect()
        logger.info(f"Connection successful: {connected}")
        if not connected:
            logger.error("Failed to connect. Aborting further tests.")
            return

        # Test Sending Message
        logger.info("\n--- Testing Send Message ---")
        message_to_send = {
            "type": "text",
            "text": f"Hello from WhatsAppConnector test! ({datetime.now().strftime('%H:%M:%S')})"
        }
        sent_successfully = await connector.send_message(TEST_RECIPIENT_PHONE_NUMBER, message_to_send)
        logger.info(f"Message sent successfully: {sent_successfully}")

        # Test Listening (Conceptual for webhook)
        logger.info("\n--- Testing Listening (Conceptual) ---")
        async def my_message_handler(message: Dict[str, Any]):
            logger.info(f"MAIN APP (Test Handler): Received message via webhook callback: {json.dumps(message, indent=2)}")

        await connector.start_listening(my_message_handler)
        logger.info("Connector is 'listening'. To test fully, send a message to your WhatsApp number from the TEST_RECIPIENT_PHONE_NUMBER.")
        logger.info("The webhook server (not part of this client) would call `connector.handle_incoming_webhook_payload(payload)`.")

        # Simulate a webhook payload being received after a few seconds
        await asyncio.sleep(5)
        sample_text_payload = { # Example from Meta docs, simplified
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "YOUR_DISPLAY_PHONE_NUMBER",
                            "phone_number_id": TEST_PHONE_NUMBER_ID
                        },
                        "messages": [{
                            "from": TEST_RECIPIENT_PHONE_NUMBER, # User sent this
                            "id": "wamid.TEST_MESSAGE_ID",
                            "timestamp": str(int(datetime.now().timestamp())),
                            "text": {"body": "This is a reply from the user!"},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        logger.info("\n--- Simulating Incoming Webhook Payload ---")
        await connector.handle_incoming_webhook_payload(sample_text_payload)

        await asyncio.sleep(2) # Give time for callback to process

        await connector.stop_listening()

        # Test Disconnection
        logger.info("\n--- Testing Disconnection ---")
        await connector.disconnect()
        logger.info(f"Disconnected. Is connected: {connector.is_connected}")

    if __name__ == "__main__":
        # This ensures that if this script is run directly, the async test function is executed.
        # In a real application, the asyncio event loop would be managed by the main application.
        try:
            asyncio.run(test_whatsapp_connector())
        except KeyboardInterrupt:
            logger.info("Test run interrupted by user.")
        except Exception as main_e:
            logger.error(f"Error in test_whatsapp_connector: {main_e}", exc_info=True)

# Example of how to run from an existing asyncio loop if needed:
# async def main():
#     # ... other async setup ...
#     await test_whatsapp_connector()
# if __name__ == "__main__":
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(main())
