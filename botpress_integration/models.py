from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = "sqlite:///./botpress_integration.db"  # Example SQLite URL

Base = declarative_base()

class UserBotpressSettings(Base):
    __tablename__ = "user_botpress_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)  # Assuming user_id is a string
    api_key = Column(String, nullable=False)
    bot_id = Column(String, nullable=False)
    preferred_language = Column(String, default="en")
    # Add other relevant settings here
    # example_setting = Column(String)

    prompts = relationship("UserPrompt", back_populates="settings")
    whatsapp_settings = relationship("WhatsAppConnectorSettings", back_populates="user_botpress_setting", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserBotpressSettings(user_id='{self.user_id}', bot_id='{self.bot_id}')>"

class WhatsAppConnectorSettings(Base):
    __tablename__ = "whatsapp_connector_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_botpress_settings_id = Column(Integer, ForeignKey("user_botpress_settings.id"), unique=True, nullable=False)

    phone_number_id = Column(String, nullable=True)
    # SECURITY NOTE: This token is highly sensitive. In production, it should be
    # encrypted at rest or stored in a secure vault, not as plain text in the DB.
    whatsapp_business_api_token = Column(String, nullable=True)
    is_enabled = Column(Boolean, default=False, nullable=False)

    user_botpress_setting = relationship("UserBotpressSettings", back_populates="whatsapp_settings")

    def __repr__(self):
        return f"<WhatsAppConnectorSettings(user_botpress_settings_id='{self.user_botpress_settings_id}', is_enabled='{self.is_enabled}')>"

class UserPrompt(Base):
    __tablename__ = "user_prompts"

    id = Column(Integer, primary_key=True, index=True)
    prompt_name = Column(String, index=True, nullable=False)
    prompt_text = Column(Text, nullable=False)
    category = Column(String, nullable=True, index=True)
    tags = Column(String, nullable=True) # Could be comma-separated, or JSON string

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    settings_id = Column(Integer, ForeignKey("user_botpress_settings.id"), nullable=False)
    settings = relationship("UserBotpressSettings", back_populates="prompts")

    def __repr__(self):
        return f"<UserPrompt(name='{self.prompt_name}', category='{self.category}')>"

# Engine and session setup (can be moved to a central db management file later)
# Note: For timezone=True with SQLite, specific dialect handling might be needed if not using a recent SQLAlchemy version.
# For simplicity, we assume it works or a polyfill/setting is active.
from sqlalchemy import DateTime
from sqlalchemy.sql import func # for server_default=func.now()

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}) # check_same_thread for SQLite
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    # This will create the database and tables when models.py is run directly
    # This is useful for initial setup or simple development environments.
    # For production or more complex scenarios, Alembic for migrations is recommended.
    create_db_and_tables()
    print("Database and tables created/updated (if they didn't exist).")

    # Example of how to use the models (optional, for testing)
    def run_model_examples():
        from sqlalchemy.orm import Session
        db: Session = SessionLocal()

        # Find or create a UserBotpressSettings record
        test_user_id = "model_test_user"
        user_settings = db.query(UserBotpressSettings).filter_by(user_id=test_user_id).first()
        if not user_settings:
            print(f"Creating UserBotpressSettings for {test_user_id}")
            user_settings = UserBotpressSettings(user_id=test_user_id, api_key="test_key", bot_id="test_bot")
            db.add(user_settings)
            db.commit()
            db.refresh(user_settings)

        print(f"Using UserBotpressSettings ID: {user_settings.id} for user {test_user_id}")

        # Create a new prompt associated with the setting
        print("\nCreating new prompt...")
        new_prompt = UserPrompt(
            prompt_name="Welcome_Email_Subject",
            prompt_text="Welcome to Our Service, {customer_name}!",
            category="Email Subjects",
            tags="welcome, email, customer_service",
            settings_id=user_settings.id
        )
        db.add(new_prompt)
        db.commit()
        db.refresh(new_prompt)
        print(f"Created prompt: ID={new_prompt.id}, Name='{new_prompt.prompt_name}', Category='{new_prompt.category}', Created='{new_prompt.created_at}'")

        # Update the prompt
        print("\nUpdating prompt...")
        prompt_to_update = db.query(UserPrompt).filter_by(id=new_prompt.id).first()
        if prompt_to_update:
            prompt_to_update.tags = "welcome, email, customer_service, updated_tag"
            prompt_to_update.prompt_text = "A warm welcome to you, {customer_name}!"
            db.commit()
            db.refresh(prompt_to_update)
            print(f"Updated prompt: ID={prompt_to_update.id}, Tags='{prompt_to_update.tags}', Updated='{prompt_to_update.updated_at}'")

        # Query data
        print("\nQuerying prompts for user...")
        retrieved_settings = db.query(UserBotpressSettings).filter(UserBotpressSettings.user_id == test_user_id).first()
        if retrieved_settings:
            print(f"Retrieved settings for {test_user_id}: {retrieved_settings}")
            for prompt in retrieved_settings.prompts:
                print(f"  - Prompt: Name='{prompt.prompt_name}', Category='{prompt.category}', Tags='{prompt.tags}', Text='{prompt.prompt_text[:30]}...'")

        # Clean up (optional)
        # print("\nCleaning up test prompt...")
        # db.delete(new_prompt)
        # db.commit()
        # print("Test prompt deleted.")

        db.close()

    # To run the examples if this script is executed:
    # run_model_examples()
