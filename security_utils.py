import os
from cryptography.fernet import Fernet, InvalidToken
import logging

logger = logging.getLogger(__name__)

KEY_FILE = "encryption_key.key" # Consider a more secure, configurable path for production

def generate_key():
    """
    Generates a new Fernet key and saves it to the KEY_FILE.
    """
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(key)
    logger.info(f"New encryption key generated and saved to {KEY_FILE}")
    return key

def load_key():
    """
    Loads the Fernet key from KEY_FILE.
    If KEY_FILE does not exist, it generates a new key.
    """
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as key_file:
            key = key_file.read()
        if not key: # File might be empty
            logger.warning(f"{KEY_FILE} was empty. Generating a new key.")
            key = generate_key()
    else:
        logger.info(f"Encryption key file '{KEY_FILE}' not found. Generating and saving a new key.")
        key = generate_key()
    return key

# Initialize the global encryption key when the module is imported
try:
    ENCRYPTION_KEY = load_key()
    if not ENCRYPTION_KEY: # Should not happen if load_key is correct
        # This part of the code runs at module import time.
        # If load_key fails and returns None, ENCRYPTION_KEY will be None.
        # The original code would then raise ValueError.
        # Logging it as critical here.
        logger.critical("CRITICAL: Failed to load or generate ENCRYPTION_KEY for Fernet instance.")
        # raise ValueError("Failed to load or generate ENCRYPTION_KEY.") # Optional: re-raise
    FERNET_INSTANCE = Fernet(ENCRYPTION_KEY) # This line will fail if ENCRYPTION_KEY is None
except Exception as e:
    logger.critical(f"CRITICAL ERROR: Could not initialize encryption system: {e}", exc_info=True)
    # In a real application, you might want to prevent the app from starting
    # or run in a degraded mode if encryption cannot be set up.
    ENCRYPTION_KEY = None
    FERNET_INSTANCE = None


def encrypt_password(password_str: str) -> str | None:
    """
    Encrypts a plaintext password string.
    Returns the encrypted token as a URL-safe base64 encoded string.
    Returns None if encryption fails (e.g., key not loaded).
    """
    if not FERNET_INSTANCE:
        logger.error("Error: Encryption service not initialized. Cannot encrypt password.")
        return None
    if not password_str: # Handle empty password string if needed
        # Depending on policy, either encrypt empty string or return specific value
        # Fernet can encrypt an empty string.
        pass

    try:
        password_bytes = password_str.encode('utf-8')
        encrypted_token_bytes = FERNET_INSTANCE.encrypt(password_bytes)
        return encrypted_token_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Error during password encryption: {e}", exc_info=True)
        return None


def decrypt_password(encrypted_token_str: str) -> str | None:
    """
    Decrypts an encrypted token string.
    Returns the plaintext password string.
    Returns None if decryption fails (e.g., invalid token, wrong key).
    """
    if not FERNET_INSTANCE:
        logger.error("Error: Decryption service not initialized. Cannot decrypt password.")
        return None
    if not encrypted_token_str: # Handle empty or None token string
        return "" # Or None, depending on how empty passwords should be treated

    try:
        encrypted_token_bytes = encrypted_token_str.encode('utf-8')
        decrypted_bytes = FERNET_INSTANCE.decrypt(encrypted_token_bytes)
        return decrypted_bytes.decode('utf-8')
    except InvalidToken as e:
        logger.warning(f"Failed to decrypt password token due to InvalidToken. This may mean the token was malformed, not a Fernet token, or encrypted with a different key. Error: {e}")
        return None # Or re-raise a custom error
    except Exception as e:
        # This could catch other errors, e.g., if encrypted_token_str is not valid base64
        logger.error(f"An unexpected error occurred during password decryption: {e}", exc_info=True)
        return None

if __name__ == '__main__':
    # Basic logging for standalone script execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Test key generation and loading
    logger.info(f"Current key (first 10 bytes for display): {ENCRYPTION_KEY[:10] if ENCRYPTION_KEY else 'None'}...")

    # Test encryption and decryption
    test_password = "MySecretPassword123!@#"
    logger.info(f"\nOriginal Password: '{test_password}'")

    encrypted = encrypt_password(test_password)
    if encrypted:
        logger.info(f"Encrypted Token: '{encrypted}'")

        decrypted = decrypt_password(encrypted)
        if decrypted is not None:
            logger.info(f"Decrypted Password: '{decrypted}'")
            assert test_password == decrypted, "Decryption test FAILED!"
            logger.info("Encryption/Decryption test PASSED.")
        else:
            logger.error("Decryption FAILED.")
    else:
        logger.error("Encryption FAILED.")

    # Test with an invalid token
    logger.info("\nTesting decryption with invalid token...")
    invalid_token = "this_is_not_a_valid_fernet_token"
    decrypted_invalid = decrypt_password(invalid_token)
    if decrypted_invalid is None:
        logger.info("Decryption of invalid token correctly failed (returned None). Test PASSED.")
    else:
        logger.error(f"Decryption of invalid token returned '{decrypted_invalid}' instead of None. Test FAILED.")

    # Test with empty password
    logger.info("\nTesting encryption/decryption of empty password...")
    encrypted_empty = encrypt_password("")
    if encrypted_empty:
        logger.info(f"Encrypted empty string: {encrypted_empty}")
        decrypted_empty = decrypt_password(encrypted_empty)
        if decrypted_empty == "":
            logger.info("Encryption/Decryption of empty string PASSED.")
        else:
            logger.error(f"Decryption of empty string FAILED. Got: '{decrypted_empty}'")
    else:
        logger.error("Encryption of empty string FAILED.")
