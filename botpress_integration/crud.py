from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from . import models
from .models import Conversation, Message, UserBotpressSettings, UserPrompt # Explicit imports for clarity
from typing import Optional
from datetime import datetime
import logging

# --- Botpress Settings CRUD ---

def get_botpress_settings(db: Session, user_id: str) -> models.UserBotpressSettings | None:
    """
    Retrieves Botpress settings for a given user_id.
    """
    try:
        return db.query(models.UserBotpressSettings).filter(models.UserBotpressSettings.user_id == user_id).first()
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_botpress_settings for user_id {user_id}: {e}", exc_info=True)
        raise # Re-raise for the caller to handle

def create_or_update_botpress_settings(
    db: Session,
    user_id: str,
    api_key: str,
    bot_id: str,
    preferred_language: str = "en",
    base_url: str | None = None
) -> models.UserBotpressSettings:
    """
    Creates new Botpress settings for a user or updates existing ones.
    """
    try:
        db_settings = db.query(models.UserBotpressSettings).filter(models.UserBotpressSettings.user_id == user_id).first()
        if db_settings:
            logging.info(f"Updating Botpress settings for user_id: {user_id}")
            db_settings.api_key = api_key
            db_settings.bot_id = bot_id
            db_settings.preferred_language = preferred_language
            db_settings.base_url = base_url
            # Update other fields as needed
        else:
            logging.info(f"Creating new Botpress settings for user_id: {user_id}")
            db_settings = models.UserBotpressSettings(
                user_id=user_id,
                api_key=api_key,
                bot_id=bot_id,
                preferred_language=preferred_language,
                base_url=base_url
            )
            db.add(db_settings)
        db.commit()
        db.refresh(db_settings)
        return db_settings
    except SQLAlchemyError as e:
        logging.error(f"Database error in create_or_update_botpress_settings for user_id {user_id}: {e}", exc_info=True)
        db.rollback() # Rollback in case of error
        raise

def delete_botpress_settings(db: Session, user_id: str) -> bool:
    """
    Deletes Botpress settings for a given user_id.
    Returns True if settings were deleted, False otherwise.
    """
    try:
        db_settings = db.query(models.UserBotpressSettings).filter(models.UserBotpressSettings.user_id == user_id).first()
        if db_settings:
            logging.info(f"Deleting Botpress settings and associated prompts for user_id: {user_id}")
            # Also delete associated prompts
            db.query(models.UserPrompt).filter(models.UserPrompt.settings_id == db_settings.id).delete(synchronize_session=False)
            db.delete(db_settings)
            db.commit()
            return True
        logging.info(f"No Botpress settings found to delete for user_id: {user_id}")
        return False
    except SQLAlchemyError as e:
        logging.error(f"Database error in delete_botpress_settings for user_id {user_id}: {e}", exc_info=True)
        db.rollback()
        raise

# --- User Prompts CRUD ---

def get_prompt_by_name(db: Session, settings_id: int, prompt_name: str) -> models.UserPrompt | None:
    """
    Retrieves a specific prompt by its name for a given settings_id.
    """
    try:
        return db.query(models.UserPrompt).filter(
            models.UserPrompt.settings_id == settings_id,
            models.UserPrompt.prompt_name == prompt_name
        ).first()
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_prompt_by_name for settings_id {settings_id}, prompt_name {prompt_name}: {e}", exc_info=True)
        raise

def get_prompts_for_user(db: Session, settings_id: int, skip: int = 0, limit: int = 100) -> list[models.UserPrompt]:
    """
    Retrieves all prompts for a given settings_id (associated with a user).
    """
    try:
        return db.query(models.UserPrompt).filter(models.UserPrompt.settings_id == settings_id).offset(skip).limit(limit).all()
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_prompts_for_user for settings_id {settings_id}: {e}", exc_info=True)
        raise

def create_user_prompt(
    db: Session,
    settings_id: int,
    prompt_name: str,
    prompt_text: str
) -> models.UserPrompt:
    """
    Creates a new prompt for a user.
    Ensures prompt_name is unique for the given user settings.
    """
    try:
        existing_prompt = get_prompt_by_name(db, settings_id, prompt_name) # This now also handles SQLAlchemyError
        if existing_prompt:
            logging.warning(f"Attempt to create duplicate prompt name '{prompt_name}' for settings_id {settings_id}")
            raise ValueError(f"Prompt with name '{prompt_name}' already exists for this user.")

        logging.info(f"Creating new prompt '{prompt_name}' for settings_id {settings_id}")
        db_prompt = models.UserPrompt(
            settings_id=settings_id,
            prompt_name=prompt_name,
            prompt_text=prompt_text
        )
        db.add(db_prompt)
        db.commit()
        db.refresh(db_prompt)
        return db_prompt
    except ValueError: # Re-raise ValueError to be handled by UI
        raise
    except SQLAlchemyError as e:
        logging.error(f"Database error in create_user_prompt for settings_id {settings_id}, prompt_name {prompt_name}: {e}", exc_info=True)
        db.rollback()
        raise

def update_user_prompt(
    db: Session,
    prompt_id: int,
    prompt_name: str | None = None,
    prompt_text: str | None = None
) -> models.UserPrompt | None:
    """
    Updates an existing prompt.
    """
    try:
        db_prompt = db.query(models.UserPrompt).filter(models.UserPrompt.id == prompt_id).first()
        if db_prompt:
            if prompt_name is not None:
                # Check if new prompt_name would conflict
                existing_prompt_with_new_name = get_prompt_by_name(db, db_prompt.settings_id, prompt_name)
                if existing_prompt_with_new_name and existing_prompt_with_new_name.id != prompt_id:
                    logging.warning(f"Attempt to update prompt ID {prompt_id} to a duplicate name '{prompt_name}' for settings_id {db_prompt.settings_id}")
                    raise ValueError(f"Another prompt with name '{prompt_name}' already exists for this user.")
                db_prompt.prompt_name = prompt_name
            if prompt_text is not None: # Allow empty string for prompt text
                db_prompt.prompt_text = prompt_text

            logging.info(f"Updating prompt ID {prompt_id} with name '{db_prompt.prompt_name}'")
            db.commit()
            db.refresh(db_prompt)
        return db_prompt
    except ValueError: # Re-raise ValueError
        raise
    except SQLAlchemyError as e:
        logging.error(f"Database error in update_user_prompt for prompt_id {prompt_id}: {e}", exc_info=True)
        db.rollback()
        raise

def delete_user_prompt(db: Session, prompt_id: int) -> bool:
    """
    Deletes a prompt by its ID.
    Returns True if prompt was deleted, False otherwise.
    """
    try:
        db_prompt = db.query(models.UserPrompt).filter(models.UserPrompt.id == prompt_id).first()
        if db_prompt:
            logging.info(f"Deleting prompt ID {prompt_id}, name '{db_prompt.prompt_name}'")
            db.delete(db_prompt)
            db.commit()
            return True
        logging.info(f"No prompt found to delete with ID {prompt_id}")
        return False
    except SQLAlchemyError as e:
        logging.error(f"Database error in delete_user_prompt for prompt_id {prompt_id}: {e}", exc_info=True)
        db.rollback()
        raise

if __name__ == "__main__":
    # This is for example usage and basic testing.
    # Configure basic logging for testing this module directly
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

    # If running this file directly, you might need to adjust imports.
    # For direct execution, ensure models.py ran `create_db_and_tables()`
    # and that `botpress_integration.db` is in the expected location.
    try:
        from models import SessionLocal, UserBotpressSettings, UserPrompt, create_db_and_tables
    except ImportError: # Handle case where models.py is not directly runnable in this context
        logging.warning("Could not import models directly for __main__ test in crud.py. Assuming DB is set up.")
        # In a real test environment, you'd ensure the DB is available and schema is created.
        # For this simple test, we'll proceed, but operations will fail if DB isn't there.
        SessionLocal = None # Prevent further execution if models aren't available
        pass


    if SessionLocal: # Only run tests if SessionLocal was imported
        # Create tables if they don't exist (e.g., first time running)
        try:
            create_db_and_tables()
            logging.info("Database tables ensured/created for CRUD __main__ test.")
        except Exception as e:
            logging.error(f"Failed to create/ensure tables in CRUD __main__: {e}", exc_info=True)
            # Depending on the error, you might want to exit or skip tests.
            # For now, we'll let it try to proceed, and individual CRUDs will fail.

        db: Session = SessionLocal()
    else:
        logging.error("SessionLocal is None. Cannot run CRUD __main__ tests.")
        db = None # Ensure db is None so tests are skipped.

    # --- Test Botpress Settings (only if db is available) ---
    if db:
        USER_ID_TEST = "crud_test_user_123"

        # Clean up previous test data
        try:
            logging.info(f"Attempting to clean up old settings for {USER_ID_TEST}")
            delete_botpress_settings(db, USER_ID_TEST)
        except Exception as e:
            logging.warning(f"Could not clean up old settings for {USER_ID_TEST}, might not exist: {e}")

        logging.info(f"Creating settings for user: {USER_ID_TEST}")
        try:
            settings = create_or_update_botpress_settings(
                db,
                user_id=USER_ID_TEST,
                api_key="crud_test_api_key_1",
                bot_id="crud_test_bot_id_1",
                base_url="http://localhost:3000/api/v1"
            )
            logging.info(f"Created/Updated settings: {settings}")

            retrieved_settings = get_botpress_settings(db, USER_ID_TEST)
            logging.info(f"Retrieved settings: {retrieved_settings}")
            assert retrieved_settings is not None
            assert retrieved_settings.api_key == "crud_test_api_key_1"
            assert retrieved_settings.base_url == "http://localhost:3000/api/v1"

            logging.info("Updating settings (clearing base_url)...")
            settings = create_or_update_botpress_settings(
                db,
                user_id=USER_ID_TEST,
                api_key="crud_test_api_key_updated",
                bot_id="crud_test_bot_id_updated",
                preferred_language="fr",
                base_url=None # Test clearing it
            )
            logging.info(f"Updated settings: {settings}")
            assert settings.api_key == "crud_test_api_key_updated"
            assert settings.preferred_language == "fr"
            assert settings.base_url is None

            # --- Test User Prompts ---
            if retrieved_settings: # Should be true if above passed
                SETTINGS_ID_TEST = retrieved_settings.id

                # Clean up previous prompt test data
                logging.info(f"Cleaning up old prompts for settings_id {SETTINGS_ID_TEST}")
                existing_prompts = get_prompts_for_user(db, SETTINGS_ID_TEST)
                for p in existing_prompts:
                    delete_user_prompt(db, p.id)

                logging.info("\nCreating prompt 'WelcomeCRUD'")
                prompt1 = create_user_prompt(db, SETTINGS_ID_TEST, "WelcomeCRUD", "Hello there! Welcome from CRUD test.")
                logging.info(f"Created prompt: {prompt1}")
                assert prompt1.prompt_name == "WelcomeCRUD"

                logging.info("Creating prompt 'HelpCRUD'")
                prompt2 = create_user_prompt(db, SETTINGS_ID_TEST, "HelpCRUD", "How can I assist you today from CRUD test?")
                logging.info(f"Created prompt: {prompt2}")

                try:
                    logging.info("Attempting to create a duplicate prompt name 'WelcomeCRUD' (should fail)")
                    create_user_prompt(db, SETTINGS_ID_TEST, "WelcomeCRUD", "This is a duplicate.")
                except ValueError as e:
                    logging.info(f"Caught expected error for duplicate prompt: {e}")

                user_prompts = get_prompts_for_user(db, SETTINGS_ID_TEST)
                logging.info(f"\nRetrieved prompts for user (settings_id {SETTINGS_ID_TEST}):")
                for p in user_prompts:
                    logging.info(f"- ID: {p.id}, Name: {p.prompt_name}, Text: {p.prompt_text[:30]}...")
                assert len(user_prompts) == 2

                logging.info(f"\nUpdating prompt '{prompt1.prompt_name}' (ID: {prompt1.id})")
                updated_prompt1 = update_user_prompt(db, prompt1.id, prompt_text="A new welcome message from CRUD test!")
                logging.info(f"Updated prompt: {updated_prompt1}")
                assert updated_prompt1 is not None and updated_prompt1.prompt_text == "A new welcome message from CRUD test!"

                retrieved_prompt1 = get_prompt_by_name(db, SETTINGS_ID_TEST, "WelcomeCRUD")
                assert retrieved_prompt1 is not None and retrieved_prompt1.prompt_text == "A new welcome message from CRUD test!"

                logging.info(f"\nDeleting prompt '{prompt2.prompt_name}' (ID: {prompt2.id})")
                deleted = delete_user_prompt(db, prompt2.id)
                logging.info(f"Deletion status: {deleted}")
                assert deleted

                user_prompts_after_delete = get_prompts_for_user(db, SETTINGS_ID_TEST)
                assert len(user_prompts_after_delete) == 1
                assert user_prompts_after_delete[0].id == prompt1.id

                logging.info("\nAll CRUD __main__ tests (basic) completed successfully.")

            else:
                logging.warning("Skipping prompt tests as settings were not retrieved/created.")

        except SQLAlchemyError as e:
            logging.error(f"A SQLAlchemyError occurred during __main__ tests in crud.py: {e}", exc_info=True)
        except AssertionError as e:
            logging.error(f"An assertion failed during __main__ tests in crud.py: {e}", exc_info=True)
        except Exception as e:
            logging.error(f"An unexpected error occurred during __main__ tests in crud.py: {e}", exc_info=True)
        finally:
            # Clean up test user settings at the end
            try:
                logging.info(f"Attempting to clean up settings for {USER_ID_TEST} after tests.")
                delete_botpress_settings(db, USER_ID_TEST) # This will also delete its prompts
                logging.info(f"Cleaned up settings for user: {USER_ID_TEST}")
            except Exception as e:
                logging.error(f"Failed to clean up settings for {USER_ID_TEST} post-test: {e}", exc_info=True)

            if db:
                db.close()
                logging.info("CRUD __main__ test: Database session closed.")
    else:
        logging.info("Skipping CRUD __main__ tests as database session is not available.")

# --- Conversation CRUD ---

def get_conversation_by_botpress_id(db: Session, botpress_conversation_id: str) -> models.Conversation | None:
    """Retrieves a conversation by its Botpress ID."""
    try:
        return db.query(models.Conversation).filter(models.Conversation.botpress_conversation_id == botpress_conversation_id).first()
    except SQLAlchemyError as e:
        logging.error(f"DB error in get_conversation_by_botpress_id for bp_conv_id {botpress_conversation_id}: {e}", exc_info=True)
        raise

def create_conversation(db: Session, botpress_conversation_id: str, channel_type: Optional[str] = None, user_identifier_on_channel: Optional[str] = None, status: str = 'active') -> models.Conversation:
    """Creates a new conversation."""
    try:
        logging.info(f"Creating new conversation with Botpress ID: {botpress_conversation_id}")
        db_conversation = models.Conversation(
            botpress_conversation_id=botpress_conversation_id,
            channel_type=channel_type,
            user_identifier_on_channel=user_identifier_on_channel,
            status=status,
            last_message_timestamp=datetime.utcnow() # Initialize with current time
        )
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        return db_conversation
    except SQLAlchemyError as e:
        logging.error(f"DB error in create_conversation for bp_conv_id {botpress_conversation_id}: {e}", exc_info=True)
        db.rollback()
        raise

def get_or_create_conversation(db: Session, botpress_conversation_id: str, channel_type: Optional[str] = None, user_identifier_on_channel: Optional[str] = None) -> models.Conversation:
    """Tries to get by botpress_conversation_id, if not found, creates one."""
    try:
        conversation = get_conversation_by_botpress_id(db, botpress_conversation_id)
        if conversation:
            # Optionally update channel_type or user_identifier if provided and different
            # For now, just return the existing one.
            # conversation.last_message_timestamp = datetime.utcnow() # Potentially update this here or in add_message
            # db.commit()
            # db.refresh(conversation)
            return conversation
        return create_conversation(db, botpress_conversation_id, channel_type, user_identifier_on_channel)
    except SQLAlchemyError as e: # Should be caught by called functions, but as a safeguard
        logging.error(f"DB error in get_or_create_conversation for bp_conv_id {botpress_conversation_id}: {e}", exc_info=True)
        raise


def update_conversation_status(db: Session, conversation_id: int, status: str) -> models.Conversation | None:
    """Updates the status of a conversation."""
    try:
        db_conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
        if db_conversation:
            logging.info(f"Updating status to '{status}' for conversation ID {conversation_id}")
            db_conversation.status = status
            db.commit()
            db.refresh(db_conversation)
        return db_conversation
    except SQLAlchemyError as e:
        logging.error(f"DB error in update_conversation_status for conv_id {conversation_id}: {e}", exc_info=True)
        db.rollback()
        raise

def update_conversation_timestamp(db: Session, conversation_id: int, last_message_timestamp: datetime) -> models.Conversation | None:
    """Updates the last_message_timestamp of a conversation."""
    try:
        db_conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
        if db_conversation:
            logging.info(f"Updating last_message_timestamp for conversation ID {conversation_id}")
            db_conversation.last_message_timestamp = last_message_timestamp
            db.commit()
            db.refresh(db_conversation)
        return db_conversation
    except SQLAlchemyError as e:
        logging.error(f"DB error in update_conversation_timestamp for conv_id {conversation_id}: {e}", exc_info=True)
        db.rollback()
        raise

def get_recent_conversations(db: Session, limit: int = 20) -> list[models.Conversation]:
    """Fetches recent conversations, ordered by last_message_timestamp descending."""
    try:
        return db.query(models.Conversation).order_by(models.Conversation.last_message_timestamp.desc()).limit(limit).all()
    except SQLAlchemyError as e:
        logging.error(f"DB error in get_recent_conversations: {e}", exc_info=True)
        raise

# --- Message CRUD ---

def add_message(db: Session, conversation_id: int, sender_type: str, content: str, timestamp: datetime, botpress_message_id: Optional[str] = None, suggestions: Optional[str] = None) -> models.Message:
    """Adds a message to a conversation. Also updates the parent conversation's last_message_timestamp."""
    try:
        logging.info(f"Adding message to conversation ID {conversation_id} from '{sender_type}'")
        db_message = models.Message(
            conversation_id=conversation_id,
            botpress_message_id=botpress_message_id,
            sender_type=sender_type,
            content=content,
            timestamp=timestamp,
            suggestions=suggestions
        )
        db.add(db_message)

        # Update conversation's last_message_timestamp
        conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
        if conversation:
            conversation.last_message_timestamp = timestamp

        db.commit()
        db.refresh(db_message)
        if conversation: # Refresh conversation if it was updated
             db.refresh(conversation)
        return db_message
    except SQLAlchemyError as e:
        logging.error(f"DB error in add_message for conv_id {conversation_id}: {e}", exc_info=True)
        db.rollback()
        raise

def get_messages_for_conversation(db: Session, conversation_id: int, limit: int = 50, offset: int = 0) -> list[models.Message]:
    """Fetches messages for a conversation, ordered by timestamp ascending."""
    try:
        return db.query(models.Message).filter(models.Message.conversation_id == conversation_id).order_by(models.Message.timestamp.asc()).offset(offset).limit(limit).all()
    except SQLAlchemyError as e:
        logging.error(f"DB error in get_messages_for_conversation for conv_id {conversation_id}: {e}", exc_info=True)
        raise

def get_message_by_botpress_id(db: Session, botpress_message_id: str) -> models.Message | None:
    """Retrieves a message by its Botpress ID."""
    try:
        return db.query(models.Message).filter(models.Message.botpress_message_id == botpress_message_id).first()
    except SQLAlchemyError as e:
        logging.error(f"DB error in get_message_by_botpress_id for bp_msg_id {botpress_message_id}: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    # This is for example usage and basic testing.
    # Configure basic logging for testing this module directly
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

    # If running this file directly, you might need to adjust imports.
    # For direct execution, ensure models.py ran `create_db_and_tables()`
    # and that `botpress_integration.db` is in the expected location.
    try:
        # Ensure models are available for the test
        from models import SessionLocal, UserBotpressSettings, UserPrompt, Conversation, Message, create_db_and_tables
    except ImportError:
        logging.warning("Could not import models directly for __main__ test in crud.py. Assuming DB is set up.")
        SessionLocal = None
        pass


    if SessionLocal:
        try:
            create_db_and_tables()
            logging.info("Database tables ensured/created for CRUD __main__ test.")
        except Exception as e:
            logging.error(f"Failed to create/ensure tables in CRUD __main__: {e}", exc_info=True)
            SessionLocal = None # Do not proceed if table creation fails

        db: Session = SessionLocal() if SessionLocal else None
    else:
        logging.error("SessionLocal is None. Cannot run CRUD __main__ tests.")
        db = None

    # --- Test Botpress Settings (only if db is available) ---
    if db:
        USER_ID_TEST = "crud_test_user_123"
        BP_CONV_ID_TEST = "bp_conv_crud_test_001"
        BP_MSG_ID_TEST_1 = "bp_msg_crud_test_001a"
        BP_MSG_ID_TEST_2 = "bp_msg_crud_test_001b"

        # Clean up previous test data
        try:
            logging.info(f"--- Initial Cleanup ---")
            # Delete messages first due to FK constraints
            existing_conv_for_cleanup = get_conversation_by_botpress_id(db, BP_CONV_ID_TEST)
            if existing_conv_for_cleanup:
                messages_to_delete = get_messages_for_conversation(db, existing_conv_for_cleanup.id)
                for msg in messages_to_delete:
                    db.delete(msg)
                db.commit()
                db.delete(existing_conv_for_cleanup)
                db.commit()
                logging.info(f"Cleaned up old conversation and messages for {BP_CONV_ID_TEST}")

            delete_botpress_settings(db, USER_ID_TEST) # This also cleans its prompts
            logging.info(f"Cleaned up old settings for {USER_ID_TEST}")

        except Exception as e:
            logging.warning(f"Could not clean up old data, might not exist: {e}", exc_info=True)
            db.rollback() # Ensure session is clean if cleanup had issues

        logging.info(f"--- Testing UserBotpressSettings CRUD ---")
        try:
            settings = create_or_update_botpress_settings(
                db, user_id=USER_ID_TEST, api_key="key", bot_id="bot"
            )
            logging.info(f"Created settings: {settings}")
            retrieved_settings = get_botpress_settings(db, USER_ID_TEST)
            assert retrieved_settings is not None and retrieved_settings.user_id == USER_ID_TEST

            logging.info(f"--- Testing Conversation and Message CRUD ---")
            # Create conversation
            logging.info(f"Creating conversation with BP ID: {BP_CONV_ID_TEST}")
            conv = get_or_create_conversation(db, BP_CONV_ID_TEST, channel_type="test_channel", user_identifier_on_channel="test_user_on_channel")
            assert conv is not None
            assert conv.botpress_conversation_id == BP_CONV_ID_TEST
            assert conv.channel_type == "test_channel"
            logging.info(f"Created/Retrieved conversation: {conv}")

            # Add messages
            ts1 = datetime.utcnow()
            msg1 = add_message(db, conv.id, "user", "Hello Bot!", ts1, BP_MSG_ID_TEST_1)
            assert msg1 is not None and msg1.botpress_message_id == BP_MSG_ID_TEST_1
            logging.info(f"Added message 1: {msg1}")

            # Verify conversation timestamp was updated
            conv_after_msg1 = get_conversation_by_botpress_id(db, BP_CONV_ID_TEST)
            assert conv_after_msg1 is not None
            # Timestamps might have microsecond differences from Python's datetime.utcnow() vs DB storage.
            # Compare by ensuring it's very close or check date and hour/minute.
            assert conv_after_msg1.last_message_timestamp is not None
            assert abs((conv_after_msg1.last_message_timestamp - ts1).total_seconds()) < 1 # Check if within 1 second

            ts2 = datetime.utcnow()
            msg2 = add_message(db, conv.id, "bot", "Hello User!", ts2, BP_MSG_ID_TEST_2)
            assert msg2 is not None and msg2.content == "Hello User!"
            logging.info(f"Added message 2: {msg2}")

            conv_after_msg2 = get_conversation_by_botpress_id(db, BP_CONV_ID_TEST)
            assert conv_after_msg2 is not None
            assert abs((conv_after_msg2.last_message_timestamp - ts2).total_seconds()) < 1


            # Get messages for conversation
            messages = get_messages_for_conversation(db, conv.id)
            assert len(messages) == 2
            assert messages[0].content == "Hello Bot!"
            assert messages[1].content == "Hello User!"
            logging.info(f"Retrieved {len(messages)} messages for conversation {conv.id}")

            # Get message by Botpress ID
            retrieved_msg1 = get_message_by_botpress_id(db, BP_MSG_ID_TEST_1)
            assert retrieved_msg1 is not None and retrieved_msg1.id == msg1.id
            logging.info(f"Retrieved message by BP ID '{BP_MSG_ID_TEST_1}': {retrieved_msg1}")

            # Update conversation status
            updated_conv = update_conversation_status(db, conv.id, "archived")
            assert updated_conv is not None and updated_conv.status == "archived"
            logging.info(f"Updated conversation status to '{updated_conv.status}'")

            # Update conversation timestamp explicitly
            new_timestamp = datetime.utcnow()
            updated_conv_ts = update_conversation_timestamp(db, conv.id, new_timestamp)
            assert updated_conv_ts is not None
            assert abs((updated_conv_ts.last_message_timestamp - new_timestamp).total_seconds()) < 1
            logging.info(f"Updated conversation timestamp to: {updated_conv_ts.last_message_timestamp}")

            # Get recent conversations
            recent_convs = get_recent_conversations(db, limit=5)
            assert len(recent_convs) > 0
            assert recent_convs[0].id == conv.id # Assuming this is the most recent
            logging.info(f"Retrieved {len(recent_convs)} recent conversations. Most recent: {recent_convs[0]}")

            logging.info("\n--- Conversation and Message CRUD tests completed successfully. ---")

        except SQLAlchemyError as e:
            logging.error(f"A SQLAlchemyError occurred during __main__ tests in crud.py: {e}", exc_info=True)
            db.rollback()
        except AssertionError as e:
            logging.error(f"An assertion failed during __main__ tests in crud.py: {e}", exc_info=True)
            db.rollback()
        except Exception as e:
            logging.error(f"An unexpected error occurred during __main__ tests in crud.py: {e}", exc_info=True)
            db.rollback()
        finally:
            # Final cleanup
            try:
                logging.info(f"--- Final Cleanup of Test Data ---")
                if 'conv' in locals() and conv and conv.id is not None : # Check if conv was defined and has an id
                    messages_to_delete = get_messages_for_conversation(db, conv.id, limit=1000) # high limit
                    for msg in messages_to_delete:
                        db.delete(msg)
                    db.commit()
                    # Re-fetch conversation to delete, as session might have been rolled back
                    conv_to_delete = db.query(models.Conversation).filter(models.Conversation.id == conv.id).first()
                    if conv_to_delete:
                        db.delete(conv_to_delete)
                        db.commit()
                        logging.info(f"Cleaned up conversation and messages for BP ID {BP_CONV_ID_TEST}")

                delete_botpress_settings(db, USER_ID_TEST)
                logging.info(f"Cleaned up settings for user: {USER_ID_TEST}")
            except Exception as e:
                logging.error(f"Failed to clean up all data post-test: {e}", exc_info=True)
                db.rollback()

            if db:
                db.close()
                logging.info("CRUD __main__ test: Database session closed.")
    else:
        logging.info("Skipping CRUD __main__ tests as database session is not available.")
