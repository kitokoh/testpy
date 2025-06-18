from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./botpress_integration.db"  # Example SQLite URL

Base = declarative_base()

class UserBotpressSettings(Base):
    __tablename__ = "user_botpress_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)  # Assuming user_id is a string
    api_key = Column(String, nullable=False)
    bot_id = Column(String, nullable=False)
    preferred_language = Column(String, default="en")
    base_url = Column(String, nullable=True) # For self-hosted instances
    # Add other relevant settings here
    # example_setting = Column(String)

    prompts = relationship("UserPrompt", back_populates="settings")

    def __repr__(self):
        return f"<UserBotpressSettings(user_id='{self.user_id}', bot_id='{self.bot_id}', base_url='{self.base_url}')>"

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

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    botpress_conversation_id = Column(String, unique=True, index=True, nullable=False)
    channel_type = Column(String, nullable=True)  # e.g., 'whatsapp', 'messenger', 'web'
    user_identifier_on_channel = Column(String, nullable=True)
    last_message_timestamp = Column(DateTime, nullable=True, index=True)
    status = Column(String, default='active', nullable=False)  # e.g., 'active', 'archived', 'closed'

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.id}, botpress_conversation_id='{self.botpress_conversation_id}', status='{self.status}')>"

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    botpress_message_id = Column(String, unique=True, index=True, nullable=True) # Nullable if purely local
    sender_type = Column(String, nullable=False)  # e.g., 'user', 'bot', 'agent'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    suggestions = Column(Text, nullable=True)  # Store JSON string of suggestions
    is_read = Column(Boolean, default=False, nullable=False, index=True)

    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, sender_type='{self.sender_type}', timestamp='{self.timestamp}', is_read={self.is_read})>"

if __name__ == "__main__":
    # This will create the database and tables when models.py is run directly
    create_db_and_tables()
    print("Database and tables created (if they didn't exist).")

    # Example of how to use the models (optional, for testing)
    from sqlalchemy.orm import Session
    db: Session = SessionLocal()

    # Clean up existing test data for a fresh run
    db.query(Message).delete()
    db.query(Conversation).delete()
    db.query(UserPrompt).delete()
    db.query(UserBotpressSettings).delete()
    db.commit()
    print("Cleared existing test data.")

    # Create a new setting
    new_setting = UserBotpressSettings(user_id="user_conv_test", api_key="test_key", bot_id="test_bot", base_url="http://localhost:3000/api/v1")
    db.add(new_setting)
    db.commit()
    db.refresh(new_setting)
    print(f"Created setting: {new_setting}")

    # Create a new conversation
    new_conversation = Conversation(
        botpress_conversation_id="bp_conv_123",
        channel_type="web",
        user_identifier_on_channel="visitor_xyz",
        last_message_timestamp=datetime.utcnow(),
        status="active"
    )
    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)
    print(f"Created conversation: {new_conversation}")

    # Add messages to the conversation
    message1 = Message(
        conversation_id=new_conversation.id,
        botpress_message_id="bp_msg_abc",
        sender_type="user",
        content="Hello, I need help!",
        timestamp=datetime.utcnow(),
        is_read=True # User messages are read by default
    )
    db.add(message1)

    message2 = Message(
        conversation_id=new_conversation.id,
        sender_type="bot",
        content="Hello! How can I assist you today?",
        timestamp=datetime.utcnow(), # Botpress message ID might be null if bot initiated locally
        is_read=False # Bot messages are unread by default
    )
    db.add(message2)
    db.commit()
    db.refresh(message1)
    db.refresh(message2)
    print(f"Added message: {message1}")
    print(f"Added message: {message2}")

    # Query the conversation and its messages
    retrieved_conv = db.query(Conversation).filter(Conversation.botpress_conversation_id == "bp_conv_123").first()
    if retrieved_conv:
        print(f"\nRetrieved conversation: {retrieved_conv}")
        print(f"  Status: {retrieved_conv.status}")
        print(f"  Last message at: {retrieved_conv.last_message_timestamp}")
        print(f"  Messages ({len(retrieved_conv.messages)}):")
        for msg in retrieved_conv.messages:
            print(f"    - [{msg.sender_type} at {msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}]: {msg.content[:50]}...")

    # Example of querying a message by its Botpress ID
    retrieved_msg = db.query(Message).filter(Message.botpress_message_id == "bp_msg_abc").first()
    if retrieved_msg:
        print(f"\nRetrieved message by Botpress ID 'bp_msg_abc': {retrieved_msg.content}")

    db.close()
