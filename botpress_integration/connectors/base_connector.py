import asyncio
from abc import ABC, abstractmethod
from typing import TypedDict, Dict, Any, Callable, Awaitable

# --- Configuration Model ---

class BaseConnectorConfig(TypedDict):
    """
    Base configuration model for all platform connectors.
    Specific connectors should extend this with their required fields.
    """
    platform_name: str # Read-only identifier for the platform
    is_enabled: bool # Whether this connector instance is active


# --- Standardized Message Format (Informational) ---
# Each connector, when receiving a message from its platform, should aim to
# convert it into a standardized dictionary format before passing it to the
# callback function provided to `start_listening`.
#
# Example Standardized Message Dictionary:
# {
#     'platform': str,          # e.g., 'whatsapp', 'facebook_messenger', 'slack'
#     'connector_id': str,      # A unique ID for this connector instance (if multiple of same platform)
#     'sender_id': str,         # Unique ID of the message sender on the platform
#     'recipient_id': str,      # Unique ID of the message recipient (often the bot/page ID) on the platform
#     'conversation_id': str,   # Unique ID for the conversation thread, if available
#     'message_id': str,        # Unique ID for the message itself, if available
#     'timestamp': str,         # ISO 8601 timestamp of when the message was sent or received
#     'type': str,              # e.g., 'text', 'image', 'audio', 'video', 'file', 'location', 'sticker', 'button_click'
#     'content': Dict[str, Any],# Message content, structure depends on 'type'
#                               # Examples:
#                               # For 'text': {'text': 'Hello world!'}
#                               # For 'image': {'url': 'http://...', 'caption': 'Optional caption'}
#                               # For 'button_click': {'payload': 'button_payload_string', 'text': 'Button display text'}
#     'raw': Any                # Optional: The original raw message from the platform for debugging or specific needs
# }
#
# The `callback` function passed to `start_listening` will receive a message in this format.
# `MessageCallback = Callable[[Dict[str, Any]], Awaitable[None]]` or `Callable[[Dict[str, Any]], None]`

MessageCallback = Callable[[Dict[str, Any]], Awaitable[None]] # Type hint for the async callback

# --- Base Connector Abstract Class ---

class BasePlatformConnector(ABC):
    """
    Abstract Base Class for platform-specific connectors.

    This class defines the common interface that all connectors must implement
    to integrate with the Botpress integration module. It handles aspects like
    connecting to a platform, sending messages, and listening for incoming messages.
    """

    def __init__(self, config: BaseConnectorConfig):
        """
        Initializes the connector with its configuration.

        Args:
            config (BaseConnectorConfig): Configuration specific to this connector instance.
                                          Should include 'platform_name' and 'is_enabled'.
        """
        self._config = config
        self._is_connected = False
        self.loop = asyncio.get_event_loop() # Get or create an event loop for async operations

    @property
    def platform_name(self) -> str:
        """
        Returns the name of the platform this connector interfaces with.
        This should be a unique identifier string (e.g., "whatsapp", "slack").
        """
        return self._config.get("platform_name", "unknown_platform")

    @property
    def is_enabled(self) -> bool:
        """Returns True if this connector instance is configured to be enabled."""
        return self._config.get("is_enabled", False)

    @property
    def is_connected(self) -> bool:
        """
        Returns True if the connector is currently considered connected to the platform, False otherwise.
        """
        return self._is_connected

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establishes a connection to the messaging platform.

        This method should handle authentication, WebSocket connections, API client setup, etc.
        It should set the `_is_connected` property to True upon successful connection.

        Returns:
            bool: True if the connection was successful, False otherwise.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnects from the messaging platform.

        This method should handle graceful shutdown of connections, cleanup of resources, etc.
        It should set the `_is_connected` property to False.

        Returns:
            bool: True if disconnection was successful or already disconnected, False on error.
        """
        pass

    @abstractmethod
    async def send_message(self, recipient_id: str, message_content: Dict[str, Any]) -> bool:
        """
        Sends a message to a specified recipient on the platform.

        Args:
            recipient_id (str): The unique identifier of the message recipient on the platform.
            message_content (Dict[str, Any]): A dictionary representing the message to be sent.
                The structure of this dictionary should be standardized if possible,
                or specific to the platform. For example:
                `{'type': 'text', 'text': 'Hello!'}`
                `{'type': 'image', 'url': 'http://...', 'caption': 'Optional'}`

        Returns:
            bool: True if the message was sent successfully (or queued for sending),
                  False otherwise.
        """
        pass

    @abstractmethod
    async def start_listening(self, callback: MessageCallback) -> None:
        """
        Starts listening for incoming messages from the platform.

        This method should initiate any necessary mechanisms to receive messages,
        such as starting a webhook server, connecting to a message queue, or
        polling an API (though polling is generally less preferred for real-time).

        When a new message is received from the platform, the connector is responsible
        for transforming it into the standardized message format (see class docstring)
        and then invoking the provided `callback` function with this standardized message.

        Args:
            callback (MessageCallback): An asynchronous callable (e.g., `async def my_callback(message_dict): ...`)
                                        that will be invoked with a standardized message dictionary
                                        when a new message is received.
        """
        pass

    @abstractmethod
    async def stop_listening(self) -> None:
        """
        Stops listening for incoming messages and cleans up related resources.
        This might involve stopping a webhook server, closing WebSocket connections, etc.
        """
        pass

    # --- Optional Helper Methods (Implement if needed by specific connectors) ---

    async def get_user_profile(self, user_id: str) -> Dict[str, Any] | None:
        """
        Optional: Fetches user profile information from the platform.

        Args:
            user_id (str): The platform-specific ID of the user.

        Returns:
            Dict[str, Any] | None: A dictionary containing user profile information
                                   (e.g., name, profile picture) or None if not found/supported.
        """
        # Default implementation: Not supported
        logging.warning(f"get_user_profile not implemented for {self.platform_name} connector.")
        return None

    async def is_service_healthy(self) -> bool:
        """
        Optional: Checks the health or status of the connection to the platform's API.
        Useful for diagnostics.

        Returns:
            bool: True if the service seems healthy, False otherwise.
        """
        # Default implementation: Assumes healthy if connected.
        # Specific connectors might ping an API endpoint.
        return self.is_connected

if __name__ == '__main__':
    # This section is for demonstration and basic understanding.
    # You cannot instantiate BasePlatformConnector directly as it's an ABC.

    logging.basicConfig(level=logging.INFO)

    class MyTestConnectorConfig(BaseConnectorConfig):
        api_token: str # Example additional field

    class MyTestConnector(BasePlatformConnector):
        def __init__(self, config: MyTestConnectorConfig):
            super().__init__(config)
            self.api_token = config.get("api_token")
            # self.platform_name is automatically set via super().__init__ if in config

        async def connect(self) -> bool:
            if not self.api_token:
                logging.error(f"[{self.platform_name}] API token not provided. Connection failed.")
                return False
            logging.info(f"[{self.platform_name}] Connecting with token: {self.api_token[:4]}...")
            # Simulate connection
            await asyncio.sleep(0.1)
            self._is_connected = True
            logging.info(f"[{self.platform_name}] Connected successfully.")
            return True

        async def disconnect(self) -> bool:
            logging.info(f"[{self.platform_name}] Disconnecting...")
            await asyncio.sleep(0.1)
            self._is_connected = False
            logging.info(f"[{self.platform_name}] Disconnected.")
            return True

        async def send_message(self, recipient_id: str, message_content: Dict[str, Any]) -> bool:
            if not self.is_connected:
                logging.error(f"[{self.platform_name}] Cannot send message, not connected.")
                return False
            msg_type = message_content.get('type', 'unknown')
            logging.info(f"[{self.platform_name}] Sending {msg_type} message to {recipient_id}: {message_content}")
            # Simulate sending
            await asyncio.sleep(0.05)
            return True

        async def _on_message_received(self, platform_specific_message: Any, callback: MessageCallback):
            # Simulate receiving a platform message and converting it
            logging.info(f"[{self.platform_name}] Raw message received: {platform_specific_message}")
            standardized_msg = {
                'platform': self.platform_name,
                'connector_id': 'test_connector_instance_01', # Example
                'sender_id': platform_specific_message.get('user', 'unknown_user'),
                'recipient_id': 'our_bot_id',
                'conversation_id': platform_specific_message.get('channel', 'default_channel'),
                'message_id': platform_specific_message.get('id', 'msg_' + str(hash(platform_specific_message.get('text')))),
                'timestamp': datetime.now().isoformat(),
                'type': 'text',
                'content': {'text': platform_specific_message.get('text', '')},
                'raw': platform_specific_message
            }
            await callback(standardized_msg)


        async def start_listening(self, callback: MessageCallback) -> None:
            if not self.is_connected:
                logging.warning(f"[{self.platform_name}] Cannot start listening, not connected.")
                return

            logging.info(f"[{self.platform_name}] Starting to listen for messages...")
            # Simulate a message listener loop (e.g., a WebSocket client would run its loop here)
            # For this example, we'll just simulate a few incoming messages.
            async def mock_message_source():
                count = 0
                while count < 3 and self.is_connected: # Listen for a few then stop for demo
                    await asyncio.sleep(2) # New message every 2 seconds
                    if not self.is_connected: break # Stop if disconnected

                    mock_raw_msg = {
                        'user': f'user_{count + 1}',
                        'channel': 'channel_A',
                        'id': f'platform_msg_id_{count + 100}',
                        'text': f'Hello from {self.platform_name} user {count+1}!'
                    }
                    # In a real connector, this `_on_message_received` would be triggered by an event
                    # from the platform SDK or webhook server.
                    await self._on_message_received(mock_raw_msg, callback)
                    count += 1
                logging.info(f"[{self.platform_name}] Mock message source finished.")

            # Store the task so it can be cancelled in stop_listening if needed
            self.listening_task = asyncio.create_task(mock_message_source())


        async def stop_listening(self) -> None:
            logging.info(f"[{self.platform_name}] Stopping listener...")
            if hasattr(self, 'listening_task') and self.listening_task:
                if not self.listening_task.done():
                    self.listening_task.cancel()
                    try:
                        await self.listening_task
                    except asyncio.CancelledError:
                        logging.info(f"[{self.platform_name}] Listening task cancelled.")
                else:
                    logging.info(f"[{self.platform_name}] Listening task was already done.")
            # Add any other cleanup for stopping listeners (e.g., close WebSocket)
            logging.info(f"[{self.platform_name}] Listener stopped.")


    async def main_test_routine():
        # Example usage of the test connector
        test_config: MyTestConnectorConfig = {
            "platform_name": "TestPlatform",
            "is_enabled": True,
            "api_token": "dummy_token_123"
        }
        connector = MyTestConnector(config=test_config)

        async def handle_incoming_message(message: Dict[str, Any]):
            logging.info(f"MAIN APP: Received standardized message: {message}")
            # Here, the main application would process this message,
            # potentially sending it to Botpress NLU, etc.

        if await connector.connect():
            logging.info(f"Is '{connector.platform_name}' connected? {connector.is_connected}")

            await connector.send_message("user_A", {"type": "text", "text": "Test outgoing message"})

            await connector.start_listening(handle_incoming_message)

            # Let it listen for a bit (mock_message_source will send a few messages)
            # In a real app, start_listening would likely run indefinitely until stop_listening is called.
            # Wait for the listening task to complete for this demo
            if hasattr(connector, 'listening_task'):
                 await connector.listening_task

            await connector.stop_listening()
            await connector.disconnect()
        else:
            logging.error(f"Failed to connect to {connector.platform_name}")

    # To run the async main_test_routine:
    # asyncio.run(main_test_routine()) # This would run the test
    # For a file that's primarily a library, direct execution like this is for demo/testing.
    # In a real application, the event loop would be managed by the main app.
    # Add logging import for the __main__ block
    import logging
    from datetime import datetime # for standardized message timestamp
    # Example of how one might run it if this file was executed directly:
    # if __name__ == "__main__":
    #     asyncio.run(main_test_routine())
    pass # End of __main__ example block
