from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from . import models # Assuming models.py is in the same directory
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
    preferred_language: str = "en"
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
            # Update other fields as needed
        else:
            logging.info(f"Creating new Botpress settings for user_id: {user_id}")
            db_settings = models.UserBotpressSettings(
                user_id=user_id,
                api_key=api_key,
                bot_id=bot_id,
                preferred_language=preferred_language
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
                bot_id="crud_test_bot_id_1"
            )
            logging.info(f"Created/Updated settings: {settings}")

            retrieved_settings = get_botpress_settings(db, USER_ID_TEST)
            logging.info(f"Retrieved settings: {retrieved_settings}")
            assert retrieved_settings is not None
            assert retrieved_settings.api_key == "crud_test_api_key_1"

            logging.info("Updating settings...")
            settings = create_or_update_botpress_settings(
                db,
                user_id=USER_ID_TEST,
                api_key="crud_test_api_key_updated",
                bot_id="crud_test_bot_id_updated",
                preferred_language="fr"
            )
            logging.info(f"Updated settings: {settings}")
            assert settings.api_key == "crud_test_api_key_updated"
            assert settings.preferred_language == "fr"

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
