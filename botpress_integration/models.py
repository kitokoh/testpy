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

    def __repr__(self):
        return f"<UserBotpressSettings(user_id='{self.user_id}', bot_id='{self.bot_id}')>"

class UserPrompt(Base):
    __tablename__ = "user_prompts"

    id = Column(Integer, primary_key=True, index=True)
    prompt_name = Column(String, index=True, nullable=False)
    prompt_text = Column(Text, nullable=False)

    settings_id = Column(Integer, ForeignKey("user_botpress_settings.id"))
    settings = relationship("UserBotpressSettings", back_populates="prompts")

    def __repr__(self):
        return f"<UserPrompt(prompt_name='{self.prompt_name}')>"

# Engine and session setup (can be moved to a central db management file later)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}) # check_same_thread for SQLite
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    # This will create the database and tables when models.py is run directly
    create_db_and_tables()
    print("Database and tables created (if they didn't exist).")

    # Example of how to use the models (optional, for testing)
    # from sqlalchemy.orm import Session
    # db: Session = SessionLocal()
    #
    # # Create a new setting
    # new_setting = UserBotpressSettings(user_id="user123", api_key="fake_api_key", bot_id="fake_bot_id")
    # db.add(new_setting)
    # db.commit()
    # db.refresh(new_setting)
    # print(f"Created setting: {new_setting}")

    # # Create a new prompt associated with the setting
    # new_prompt = UserPrompt(prompt_name="Greeting", prompt_text="Hello, how can I help you?", settings_id=new_setting.id)
    # db.add(new_prompt)
    # db.commit()
    # db.refresh(new_prompt)
    # print(f"Created prompt: {new_prompt}")

    # # Query data
    # retrieved_setting = db.query(UserBotpressSettings).filter(UserBotpressSettings.user_id == "user123").first()
    # if retrieved_setting:
    #     print(f"Retrieved setting for user123: {retrieved_setting}")
    #     for prompt in retrieved_setting.prompts:
    #         print(f"  - Prompt: {prompt.prompt_name} - {prompt.prompt_text}")
    # db.close()
