import pywhatkit
import time
import logging # Optional: for logging errors

class WhatsAppService:
    """
    A service class to handle sending WhatsApp messages using pywhatkit.
    """
    def __init__(self):
        """
        Initializes the WhatsAppService.
        """
        pass

    def send_message(self, phone_number: str, message: str, wait_time: int = 20, tab_close: bool = True, close_time: int = 3):
        """
        Sends a WhatsApp message to the given phone number.

        Args:
            phone_number (str): The recipient's phone number with country code.
                                (e.g., "+12345678900")
            message (str): The message to send.
            wait_time (int): Time (in seconds) for pywhatkit to wait after opening WhatsApp Web
                             and finding the chat before attempting to send the message.
                             A value of 20s is a common recommendation.
            tab_close (bool): Whether to close the browser tab after sending.
            close_time (int): Time (in seconds) to wait before closing the tab if tab_close is True.

        Returns:
            tuple[bool, str]: (success, status_message)
        """
        if not phone_number or not message:
            return False, "Phone number and message cannot be empty."

        try:
            # pywhatkit.sendwhatmsg_instantly sends the message "instantly".
            # It requires WhatsApp Web to be open and logged in on the default browser.
            # The user might need to scan a QR code if not already logged in.
            # The wait_time here is the time the function waits for the message to be sent
            # once WhatsApp Web is open and the chat is found.
            pywhatkit.sendwhatmsg_instantly(
                phone_no=phone_number,
                message=message,
                wait_time=wait_time,
                tab_close=tab_close,
                close_time=close_time
            )
            # sendwhatmsg_instantly doesn't have a direct success return value.
            # If no exception is raised, it means the command was accepted by pywhatkit.
            # Actual delivery depends on WhatsApp Web and network conditions.
            return True, "Message sending process initiated. Check WhatsApp Web for status."
        except Exception as e:
            # Catching a generic exception as pywhatkit can raise various errors
            # (e.g., pywhatkit.exceptions.CountryCodeException, selenium WebDriverException, network issues).
            error_message = f"Error sending WhatsApp message: {str(e)}"
            logging.error(error_message) # Log the error
            return False, error_message

if __name__ == '__main__':
    # Example Usage (for testing this module directly)
    # Important: Make sure you are logged into WhatsApp Web on your default browser first.
    # You might need to scan a QR code.
    logging.basicConfig(level=logging.INFO)
    service = WhatsAppService()

    # Replace with a valid test phone number (including country code, e.g., "+12345678900")
    # and a test message. Using a placeholder for safety.
    test_phone = "+19999999999"  # <-- IMPORTANT: REPLACE with a real test phone number
    test_message = "Hello from Python! This is a test message using WhatsAppService via pywhatkit.sendwhatmsg_instantly."

    print(f"Attempting to send a message to {test_phone}...")
    # Increased wait_time for demonstration, default is 20s in the method.
    # tab_close=True and close_time=5 means the tab will attempt to close 5 seconds after message is sent.
    success, status = service.send_message(test_phone, test_message, wait_time=25, tab_close=True, close_time=5)

    if success:
        print(f"Service Status: {status}")
    else:
        print(f"Service Error: {status}")

    # Example 2: Message without closing tab (useful for debugging or multiple messages)
    # print("\nAttempting to send a message and keep tab open...")
    # test_message_2 = "Test 2 - tab should stay open after this message."
    # success, status = service.send_message(test_phone, test_message_2, wait_time=20, tab_close=False)
    # if success:
    #     print(f"Service Status: {status}")
    # else:
    #     print(f"Service Error: {status}")

    print("\nNote: For this test to work, you must be logged into WhatsApp Web")
    print("on your default browser. pywhatkit will open a new tab and send the message.")
    print("Replace the placeholder test_phone with a valid number to test.")
