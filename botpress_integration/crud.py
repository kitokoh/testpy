from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from . import models # Assuming models.py is in the same directory
import logging
import time # For __main__ test for updated_at

# --- Botpress Settings CRUD ---

def get_botpress_settings(db: Session, user_id: str) -> models.UserBotpressSettings | None:
    """
    Retrieves Botpress settings for a given user_id.
    """
    try:
        return db.query(models.UserBotpressSettings).filter(models.UserBotpressSettings.user_id == user_id).first()
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_botpress_settings for user_id {user_id}: {e}", exc_info=True)
        raise

def create_or_update_botpress_settings(
    db: Session,
    user_id: str,
    api_key: str,
    bot_id: str,
    preferred_language: str = "en"
) -> models.UserBotpressSettings:
    """
    Creates new Botpress settings for a user or updates existing ones.
    SECURITY NOTE: API keys are sensitive. In a production system, the api_key
    should be encrypted before being stored in the database or managed via a
    secure secrets vault. This implementation stores it directly for simplicity
    during this development phase.
    """
    try:
        db_settings = db.query(models.UserBotpressSettings).filter(models.UserBotpressSettings.user_id == user_id).first()
        if db_settings:
            logging.info(f"Updating Botpress settings for user_id: {user_id}")
            db_settings.api_key = api_key
            db_settings.bot_id = bot_id
            db_settings.preferred_language = preferred_language
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
        db.rollback()
        raise

def delete_botpress_settings(db: Session, user_id: str) -> bool:
    try:
        db_settings = db.query(models.UserBotpressSettings).filter(models.UserBotpressSettings.user_id == user_id).first()
        if db_settings:
            logging.info(f"Deleting Botpress settings and associated prompts/WA settings for user_id: {user_id}")
            # Cascading delete for prompts and whatsapp_settings handled by relationship settings in models.py
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

def get_prompt_by_id(db: Session, prompt_id: int) -> models.UserPrompt | None:
    """Retrieves a specific prompt by its primary key ID."""
    try:
        return db.query(models.UserPrompt).filter(models.UserPrompt.id == prompt_id).first()
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_prompt_by_id for prompt_id {prompt_id}: {e}", exc_info=True)
        raise

def get_prompt_by_name(db: Session, settings_id: int, prompt_name: str) -> models.UserPrompt | None:
    try:
        return db.query(models.UserPrompt).filter(
            models.UserPrompt.settings_id == settings_id,
            models.UserPrompt.prompt_name == prompt_name
        ).first()
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_prompt_by_name for settings_id {settings_id}, prompt_name {prompt_name}: {e}", exc_info=True)
        raise

def get_prompts_for_user(db: Session, settings_id: int, skip: int = 0, limit: int = 100) -> list[models.UserPrompt]:
    try:
        return db.query(models.UserPrompt).filter(models.UserPrompt.settings_id == settings_id).order_by(models.UserPrompt.updated_at.desc()).offset(skip).limit(limit).all()
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_prompts_for_user for settings_id {settings_id}: {e}", exc_info=True)
        raise

def create_user_prompt(
    db: Session,
    settings_id: int,
    prompt_name: str,
    prompt_text: str,
    category: str | None = None,
    tags: str | None = None
) -> models.UserPrompt:
    try:
        existing_prompt = get_prompt_by_name(db, settings_id, prompt_name)
        if existing_prompt:
            logging.warning(f"Attempt to create duplicate prompt name '{prompt_name}' for settings_id {settings_id}")
            raise ValueError(f"Prompt with name '{prompt_name}' already exists for this user.")

        logging.info(f"Creating new prompt '{prompt_name}' for settings_id {settings_id}, category='{category}', tags='{tags}'")
        db_prompt = models.UserPrompt(
            settings_id=settings_id,
            prompt_name=prompt_name,
            prompt_text=prompt_text,
            category=category.strip() if category and category.strip() else None,
            tags=tags.strip() if tags and tags.strip() else None
        )
        db.add(db_prompt)
        db.commit()
        db.refresh(db_prompt)
        return db_prompt
    except ValueError:
        raise
    except SQLAlchemyError as e:
        logging.error(f"Database error in create_user_prompt for settings_id {settings_id}, prompt_name {prompt_name}: {e}", exc_info=True)
        db.rollback()
        raise

def update_user_prompt(
    db: Session,
    prompt_id: int,
    prompt_name: str | None = None,
    prompt_text: str | None = None,
    category: str | None = None,
    tags: str | None = None
) -> models.UserPrompt | None:
    try:
        db_prompt = db.query(models.UserPrompt).filter(models.UserPrompt.id == prompt_id).first()
        if db_prompt:
            updated_fields = {}
            if prompt_name is not None:
                if db_prompt.prompt_name != prompt_name:
                    existing_prompt_with_new_name = get_prompt_by_name(db, db_prompt.settings_id, prompt_name)
                    if existing_prompt_with_new_name and existing_prompt_with_new_name.id != prompt_id:
                        logging.warning(f"Attempt to update prompt ID {prompt_id} to a duplicate name '{prompt_name}' for settings_id {db_prompt.settings_id}")
                        raise ValueError(f"Another prompt with name '{prompt_name}' already exists for this user.")
                    db_prompt.prompt_name = prompt_name
                    updated_fields['prompt_name'] = prompt_name

            if prompt_text is not None and db_prompt.prompt_text != prompt_text:
                db_prompt.prompt_text = prompt_text
                updated_fields['prompt_text'] = True # Mark as changed

            if category is not None: # If category is explicitly passed
                new_category = category.strip() if category and category.strip() else None
                if db_prompt.category != new_category:
                    db_prompt.category = new_category
                    updated_fields['category'] = new_category

            if tags is not None: # If tags are explicitly passed
                new_tags = tags.strip() if tags and tags.strip() else None
                if db_prompt.tags != new_tags:
                    db_prompt.tags = new_tags
                    updated_fields['tags'] = new_tags

            if updated_fields:
                 logging.info(f"Updating prompt ID {prompt_id}. Changed fields: {list(updated_fields.keys())}")
                 db.commit()
                 db.refresh(db_prompt)
            else:
                logging.info(f"No fields to update for prompt ID {prompt_id}.")
        return db_prompt
    except ValueError:
        raise
    except SQLAlchemyError as e:
        logging.error(f"Database error in update_user_prompt for prompt_id {prompt_id}: {e}", exc_info=True)
        db.rollback()
        raise

def delete_user_prompt(db: Session, prompt_id: int) -> bool:
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

# --- WhatsApp Connector Settings CRUD ---

def get_whatsapp_settings(db: Session, user_botpress_settings_id: int) -> models.WhatsAppConnectorSettings | None:
    try:
        return db.query(models.WhatsAppConnectorSettings).filter(
            models.WhatsAppConnectorSettings.user_botpress_settings_id == user_botpress_settings_id
        ).first()
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_whatsapp_settings for ubs_id {user_botpress_settings_id}: {e}", exc_info=True)
        raise

def create_or_update_whatsapp_settings(
    db: Session,
    user_botpress_settings_id: int,
    is_enabled: bool,
    phone_number_id: str | None = None,
    api_token: str | None = None
) -> models.WhatsAppConnectorSettings:
    """
    SECURITY NOTE: The api_token is sensitive. Store encrypted or in vault.
    If api_token is None, existing token is NOT changed. Pass "" to clear.
    """
    try:
        settings = get_whatsapp_settings(db, user_botpress_settings_id)
        if settings:
            logging.info(f"Updating WhatsApp settings for ubs_id: {user_botpress_settings_id}")
            settings.is_enabled = is_enabled
            settings.phone_number_id = phone_number_id
            if api_token is not None:
                settings.whatsapp_business_api_token = api_token
        else:
            logging.info(f"Creating new WhatsApp settings for ubs_id: {user_botpress_settings_id}")
            settings = models.WhatsAppConnectorSettings(
                user_botpress_settings_id=user_botpress_settings_id,
                is_enabled=is_enabled,
                phone_number_id=phone_number_id,
                whatsapp_business_api_token=api_token
            )
            db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings
    except SQLAlchemyError as e:
        logging.error(f"Database error in create_or_update_whatsapp_settings for ubs_id {user_botpress_settings_id}: {e}", exc_info=True)
        db.rollback()
        raise

def delete_whatsapp_settings(db: Session, user_botpress_settings_id: int) -> bool:
    try:
        settings = get_whatsapp_settings(db, user_botpress_settings_id)
        if settings:
            logging.info(f"Deleting WhatsApp settings for ubs_id: {user_botpress_settings_id}")
            db.delete(settings)
            db.commit()
            return True
        logging.info(f"No WhatsApp settings found to delete for ubs_id: {user_botpress_settings_id}")
        return False
    except SQLAlchemyError as e:
        logging.error(f"Database error in delete_whatsapp_settings for ubs_id {user_botpress_settings_id}: {e}", exc_info=True)
        db.rollback()
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

    try:
        from models import SessionLocal, UserBotpressSettings, UserPrompt, create_db_and_tables, WhatsAppConnectorSettings
    except ImportError:
        logging.warning("Could not import models directly for __main__ test in crud.py.")
        SessionLocal = None
        pass

    if SessionLocal:
        try:
            create_db_and_tables()
            logging.info("Database tables ensured/created for CRUD __main__ test.")
        except Exception as e:
            logging.error(f"Failed to create/ensure tables in CRUD __main__: {e}", exc_info=True)
        db: Session = SessionLocal()
    else:
        logging.error("SessionLocal is None. Cannot run CRUD __main__ tests.")
        db = None

    if db:
        BP_USER_ID_FOR_TESTS = "crud_main_test_user"
        bp_settings = None
        try:
            delete_botpress_settings(db, BP_USER_ID_FOR_TESTS) # Clean slate
            bp_settings = create_or_update_botpress_settings(
                db, user_id=BP_USER_ID_FOR_TESTS, api_key="main_test_key", bot_id="main_test_bot"
            )
            UBS_ID = bp_settings.id
            logging.info(f"Created parent Botpress settings for tests: ID {UBS_ID}")

            # --- Test User Prompts (with new fields) ---
            logging.info(f"\n--- Testing User Prompts CRUD for UBS_ID: {UBS_ID} ---")

            prompt1 = create_user_prompt(
                db, UBS_ID,
                "Test Prompt 1", "This is the first test prompt.",
                category="General", tags="test, general"
            )
            logging.info(f"Created Prompt 1: ID={prompt1.id}, Cat='{prompt1.category}', Tags='{prompt1.tags}', Created='{prompt1.created_at}'")
            assert prompt1.category == "General"
            assert prompt1.tags == "test, general"

            time.sleep(0.01) # Ensure updated_at will be different

            prompt1_updated = update_user_prompt(
                db, prompt1.id,
                prompt_name="Test Prompt 1 Updated",
                category="General Updated",
                tags="test, general, updated"
            )
            logging.info(f"Updated Prompt 1: Name='{prompt1_updated.prompt_name}', Cat='{prompt1_updated.category}', Tags='{prompt1_updated.tags}', Updated='{prompt1_updated.updated_at}'")
            assert prompt1_updated.prompt_name == "Test Prompt 1 Updated"
            assert prompt1_updated.category == "General Updated"
            assert prompt1_updated.created_at < prompt1_updated.updated_at

            update_user_prompt(db, prompt1.id, category="", tags="") # Clear category and tags
            prompt1_cleared = get_prompt_by_id(db, prompt1.id)
            logging.info(f"Prompt 1 after clearing Cat/Tags: Cat='{prompt1_cleared.category}', Tags='{prompt1_cleared.tags}'")
            assert prompt1_cleared.category is None
            assert prompt1_cleared.tags is None

            prompts_list = get_prompts_for_user(db, UBS_ID)
            assert len(prompts_list) == 1
            logging.info(f"Retrieved {len(prompts_list)} prompts for user.")

            # Test WhatsApp settings CRUD (minimal, as it was tested before)
            wa_settings = create_or_update_whatsapp_settings(db, UBS_ID, True, "wa_phone_1", "wa_token_1")
            assert wa_settings is not None
            logging.info(f"Created WA settings for UBS_ID {UBS_ID}")

            logging.info("\nCRUD __main__ tests completed successfully.")

        except Exception as e:
            logging.error(f"An error occurred during __main__ tests in crud.py: {e}", exc_info=True)
        finally:
            if bp_settings: # Clean up the main Botpress setting (should cascade delete prompts and WA settings)
                logging.info(f"Cleaning up Botpress settings for {BP_USER_ID_FOR_TESTS}.")
                delete_botpress_settings(db, BP_USER_ID_FOR_TESTS)
            if db:
                db.close()
                logging.info("CRUD __main__ test: Database session closed.")
    else:
        logging.info("Skipping CRUD __main__ tests as database session is not available.")
