import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession # Use alias to avoid confusion
import logging

# Adjust import path as necessary
from botpress_integration.models import Base, UserBotpressSettings, UserPrompt, Conversation, Message, create_db_and_tables as main_create_db_and_tables
from botpress_integration import crud
# from botpress_integration.crud import has_unread_bot_messages # No longer needed to explicitly import if using crud.has_unread_bot_messages
from datetime import datetime

# Configure logging for tests (optional, but can be helpful)
# logging.basicConfig(level=logging.DEBUG)

class TestCrudOperations(unittest.TestCase):

    engine = None
    SessionLocalTest = None

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        # We need to pass the engine to the models.Base.metadata.create_all
        # If create_db_and_tables from models.py uses a global engine, we need to adapt.
        # For now, let's assume create_db_and_tables can accept an engine or we call Base.metadata.create_all directly.
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocalTest = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        logging.info("In-memory SQLite DB initialized for testing CRUD operations.")

    def setUp(self):
        # Create a new session for each test
        self.db: SQLAlchemySession = self.SessionLocalTest()
        # Clear data from tables before each test to ensure isolation
        self._clear_all_tables()

    def _clear_all_tables(self):
        # Delete data in reverse order of creation due to foreign key constraints
        self.db.query(Message).delete()
        self.db.query(Conversation).delete()
        self.db.query(UserPrompt).delete()
        self.db.query(UserBotpressSettings).delete()
        self.db.commit()

    def tearDown(self):
        self.db.close()

    # --- UserBotpressSettings Tests ---
    def test_create_and_get_botpress_settings(self):
        created_settings = crud.create_or_update_botpress_settings(
            self.db, "user1", "key1", "bot1", "en", "http://localhost:3000"
        )
        self.assertIsNotNone(created_settings.id)
        self.assertEqual(created_settings.user_id, "user1")
        self.assertEqual(created_settings.api_key, "key1")
        self.assertEqual(created_settings.bot_id, "bot1")
        self.assertEqual(created_settings.preferred_language, "en")
        self.assertEqual(created_settings.base_url, "http://localhost:3000")

        retrieved_settings = crud.get_botpress_settings(self.db, "user1")
        self.assertIsNotNone(retrieved_settings)
        self.assertEqual(retrieved_settings.id, created_settings.id)
        self.assertEqual(retrieved_settings.base_url, "http://localhost:3000")

    def test_get_botpress_settings_not_found(self):
        retrieved_settings = crud.get_botpress_settings(self.db, "non_existent_user")
        self.assertIsNone(retrieved_settings)

    def test_update_botpress_settings(self):
        crud.create_or_update_botpress_settings(
            self.db, "user2", "key2_orig", "bot2_orig", "en", None
        )
        updated_settings = crud.create_or_update_botpress_settings(
            self.db, "user2", "key2_new", "bot2_new", "fr", "https://new.url"
        )
        self.assertEqual(updated_settings.api_key, "key2_new")
        self.assertEqual(updated_settings.bot_id, "bot2_new")
        self.assertEqual(updated_settings.preferred_language, "fr")
        self.assertEqual(updated_settings.base_url, "https://new.url")

        # Test updating to remove base_url
        updated_settings_no_base = crud.create_or_update_botpress_settings(
            self.db, "user2", "key2_final", "bot2_final", "de", None
        )
        self.assertEqual(updated_settings_no_base.base_url, None)


    def test_delete_botpress_settings(self):
        settings = crud.create_or_update_botpress_settings(
            self.db, "user_to_delete", "key_del", "bot_del"
        )
        # Add a prompt to ensure cascade delete is handled (or verify it's deleted)
        crud.create_user_prompt(self.db, settings.id, "test_prompt", "text")

        delete_result = crud.delete_botpress_settings(self.db, "user_to_delete")
        self.assertTrue(delete_result)
        self.assertIsNone(crud.get_botpress_settings(self.db, "user_to_delete"))
        # Verify prompts are also deleted
        prompts = crud.get_prompts_for_user(self.db, settings.id)
        self.assertEqual(len(prompts), 0)


    def test_delete_botpress_settings_not_found(self):
        delete_result = crud.delete_botpress_settings(self.db, "non_existent_user_for_delete")
        self.assertFalse(delete_result)

    # --- UserPrompt Tests ---
    def test_create_and_get_user_prompt(self):
        settings = crud.create_or_update_botpress_settings(self.db, "user_prompt_test", "k", "b")

        prompt = crud.create_user_prompt(self.db, settings.id, "Greeting", "Hello there!")
        self.assertIsNotNone(prompt.id)
        self.assertEqual(prompt.prompt_name, "Greeting")
        self.assertEqual(prompt.prompt_text, "Hello there!")
        self.assertEqual(prompt.settings_id, settings.id)

        retrieved_prompt = crud.get_prompt_by_name(self.db, settings.id, "Greeting")
        self.assertIsNotNone(retrieved_prompt)
        self.assertEqual(retrieved_prompt.id, prompt.id)

    def test_create_duplicate_user_prompt_name(self):
        settings = crud.create_or_update_botpress_settings(self.db, "user_dup_prompt", "k", "b")
        crud.create_user_prompt(self.db, settings.id, "UniquePrompt", "Text1")
        with self.assertRaises(ValueError):
            crud.create_user_prompt(self.db, settings.id, "UniquePrompt", "Text2")

    def test_get_prompts_for_user(self):
        settings = crud.create_or_update_botpress_settings(self.db, "user_multi_prompt", "k", "b")
        crud.create_user_prompt(self.db, settings.id, "Prompt1", "1")
        crud.create_user_prompt(self.db, settings.id, "Prompt2", "2")

        prompts = crud.get_prompts_for_user(self.db, settings.id)
        self.assertEqual(len(prompts), 2)

    def test_update_user_prompt(self):
        settings = crud.create_or_update_botpress_settings(self.db, "user_update_prompt", "k", "b")
        prompt = crud.create_user_prompt(self.db, settings.id, "OldName", "OldText")

        updated_prompt = crud.update_user_prompt(self.db, prompt.id, "NewName", "NewText")
        self.assertEqual(updated_prompt.prompt_name, "NewName")
        self.assertEqual(updated_prompt.prompt_text, "NewText")

        # Test updating only one field
        updated_prompt_text_only = crud.update_user_prompt(self.db, prompt.id, prompt_text="OnlyTextUpdated")
        self.assertEqual(updated_prompt_text_only.prompt_name, "NewName") # Should retain previous name
        self.assertEqual(updated_prompt_text_only.prompt_text, "OnlyTextUpdated")

    def test_update_user_prompt_name_conflict(self):
        settings = crud.create_or_update_botpress_settings(self.db, "user_prompt_name_conflict", "k","b")
        prompt1 = crud.create_user_prompt(self.db, settings.id, "Name1", "Text1")
        prompt2 = crud.create_user_prompt(self.db, settings.id, "Name2", "Text2")
        with self.assertRaises(ValueError):
            crud.update_user_prompt(self.db, prompt2.id, prompt_name="Name1") # Trying to rename prompt2 to Name1

    def test_delete_user_prompt(self):
        settings = crud.create_or_update_botpress_settings(self.db, "user_del_prompt", "k", "b")
        prompt = crud.create_user_prompt(self.db, settings.id, "ToDelete", "...")

        result = crud.delete_user_prompt(self.db, prompt.id)
        self.assertTrue(result)
        self.assertIsNone(crud.get_prompt_by_name(self.db, settings.id, "ToDelete"))

    # --- Conversation and Message Tests to be added here ---
    def test_create_get_or_create_conversation(self):
        bp_conv_id = "bp_test_conv_001"
        conv1 = crud.create_conversation(self.db, bp_conv_id, "web", "user_xyz", "active")
        self.assertEqual(conv1.botpress_conversation_id, bp_conv_id)
        self.assertEqual(conv1.channel_type, "web")

        conv2 = crud.get_conversation_by_botpress_id(self.db, bp_conv_id)
        self.assertEqual(conv1.id, conv2.id)

        conv3 = crud.get_or_create_conversation(self.db, bp_conv_id, "sms", "user_abc") # Should get existing
        self.assertEqual(conv1.id, conv3.id)
        # Current get_or_create doesn't update existing, so channel_type remains 'web'
        self.assertEqual(conv3.channel_type, "web")


        bp_conv_id_new = "bp_test_conv_002"
        conv4 = crud.get_or_create_conversation(self.db, bp_conv_id_new, "messenger") # Should create new
        self.assertEqual(conv4.botpress_conversation_id, bp_conv_id_new)
        self.assertEqual(conv4.channel_type, "messenger")

    def test_update_conversation_status_and_timestamp(self):
        conv = crud.create_conversation(self.db, "bp_conv_status_ts", "web")
        original_ts = conv.last_message_timestamp

        updated_conv_status = crud.update_conversation_status(self.db, conv.id, "archived")
        self.assertEqual(updated_conv_status.status, "archived")

        new_ts = datetime.utcnow()
        updated_conv_ts = crud.update_conversation_timestamp(self.db, conv.id, new_ts)
        self.assertEqual(updated_conv_ts.last_message_timestamp, new_ts)
        self.assertNotEqual(original_ts, new_ts)

    def test_get_recent_conversations(self):
        crud.create_conversation(self.db, "conv_old", "web", last_message_timestamp=datetime(2023, 1, 1, 10, 0, 0))
        conv_new = crud.create_conversation(self.db, "conv_new", "web", last_message_timestamp=datetime(2023, 1, 1, 12, 0, 0))

        recent = crud.get_recent_conversations(self.db, limit=1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].id, conv_new.id)

    def test_add_and_get_messages(self):
        conv = crud.create_conversation(self.db, "conv_for_msgs", "chat")
        ts_before_msg = conv.last_message_timestamp

        msg_content1 = "Hello from user"
        msg_ts1 = datetime.utcnow()
        msg1 = crud.add_message(self.db, conv.id, "user", msg_content1, msg_ts1, "bp_msg_1")
        self.assertEqual(msg1.content, msg_content1)
        self.assertEqual(msg1.sender_type, "user")
        self.assertEqual(msg1.botpress_message_id, "bp_msg_1")
        self.assertTrue(msg1.is_read, "User message should be read by default")

        # Check conversation's last_message_timestamp was updated
        conv_reloaded = crud.get_conversation_by_botpress_id(self.db, "conv_for_msgs")
        self.assertEqual(conv_reloaded.last_message_timestamp, msg_ts1)

        msg_content2 = "Reply from bot"
        msg_ts2 = datetime.utcnow()
        suggestions_json = '[{"title": "Option 1", "payload": "opt1"}]'
        msg2 = crud.add_message(self.db, conv.id, "bot", msg_content2, msg_ts2, "bp_msg_2", suggestions_json)
        self.assertEqual(msg2.suggestions, suggestions_json)
        self.assertFalse(msg2.is_read, "Bot message should be unread by default")

        conv_reloaded_again = crud.get_conversation_by_botpress_id(self.db, "conv_for_msgs")
        self.assertEqual(conv_reloaded_again.last_message_timestamp, msg_ts2)

        # Test explicit is_read
        msg_user_unread = crud.add_message(self.db, conv.id, "user", "Test unread user", datetime.utcnow(), is_read=False)
        self.assertFalse(msg_user_unread.is_read, "User message explicitly set to unread")

        msg_bot_read = crud.add_message(self.db, conv.id, "bot", "Test read bot", datetime.utcnow(), is_read=True)
        self.assertTrue(msg_bot_read.is_read, "Bot message explicitly set to read")

        messages_for_conv = crud.get_messages_for_conversation(self.db, conv.id, limit=10)
        self.assertEqual(len(messages_for_conv), 4) # 2 default + 2 explicit
        self.assertEqual(messages_for_conv[0].id, msg1.id)
        self.assertEqual(messages_for_conv[1].id, msg2.id)

        retrieved_msg_by_bp_id = crud.get_message_by_botpress_id(self.db, "bp_msg_1")
        self.assertEqual(retrieved_msg_by_bp_id.id, msg1.id)

    def test_mark_messages_as_read(self):
        conv = crud.create_conversation(self.db, "conv_mark_read", "test")
        # Add messages
        crud.add_message(self.db, conv.id, "user", "User msg 1", datetime.utcnow(), is_read=True) # Already read
        crud.add_message(self.db, conv.id, "bot", "Bot msg 1 (unread)", datetime.utcnow(), is_read=False)
        crud.add_message(self.db, conv.id, "agent", "Agent msg (unread)", datetime.utcnow(), is_read=False)
        crud.add_message(self.db, conv.id, "bot", "Bot msg 2 (read)", datetime.utcnow(), is_read=True)

        # Mark messages as read
        updated_count = crud.mark_messages_as_read(self.db, conv.id)
        self.assertEqual(updated_count, 2, "Should have updated 2 messages (bot msg 1, agent msg)")

        # Verify all messages are now read
        messages = crud.get_messages_for_conversation(self.db, conv.id)
        for msg in messages:
            self.assertTrue(msg.is_read, f"Message {msg.id} should be read")

        # Test with a conversation with no unread messages
        updated_count_none = crud.mark_messages_as_read(self.db, conv.id)
        self.assertEqual(updated_count_none, 0)

        # Test with a non-existent conversation ID
        updated_count_non_existent = crud.mark_messages_as_read(self.db, 99999)
        self.assertEqual(updated_count_non_existent, 0)

    def test_count_unread_bot_messages(self):
        # Scenario 1: No unread messages
        self.assertEqual(crud.count_unread_bot_messages(self.db), 0)

        # Scenario 2: Add conversations and messages
        conv1 = crud.create_conversation(self.db, "c1_unread_test")
        crud.add_message(self.db, conv1.id, "user", "u1", datetime.utcnow()) # Read
        crud.add_message(self.db, conv1.id, "bot", "b1 unread", datetime.utcnow()) # Unread
        crud.add_message(self.db, conv1.id, "agent", "a1 unread", datetime.utcnow()) # Unread

        conv2 = crud.create_conversation(self.db, "c2_unread_test")
        crud.add_message(self.db, conv2.id, "bot", "b2 unread", datetime.utcnow()) # Unread
        crud.add_message(self.db, conv2.id, "system", "s2 read", datetime.utcnow(), is_read=True) # Read

        # Assert count is 3 (b1, a1, b2)
        self.assertEqual(crud.count_unread_bot_messages(self.db), 3)

        # Mark some as read
        crud.mark_messages_as_read(self.db, conv1.id) # Marks b1, a1 as read
        self.assertEqual(crud.count_unread_bot_messages(self.db), 1) # Only b2 left

        crud.mark_messages_as_read(self.db, conv2.id) # Marks b2 as read
        self.assertEqual(crud.count_unread_bot_messages(self.db), 0)

    def test_has_unread_bot_messages(self):
        conv_test = crud.create_conversation(self.db, "conv_has_unread")

        # Test with no messages
        self.assertFalse(crud.has_unread_bot_messages(self.db, conv_test.id))

        # Test with only read bot messages
        crud.add_message(self.db, conv_test.id, "bot", "read bot", datetime.utcnow(), is_read=True)
        self.assertFalse(crud.has_unread_bot_messages(self.db, conv_test.id))

        # Test with only unread user messages
        crud.add_message(self.db, conv_test.id, "user", "unread user", datetime.utcnow(), is_read=False) # User messages are read by default if is_read=None
        # Re-add user message explicitly as unread to test the filter for "sender_type != 'user'"
        user_msg = self.db.query(Message).filter(Message.conversation_id == conv_test.id, Message.sender_type == 'user').first()
        if user_msg: # If it was created by add_message (which auto-sets user to read)
            user_msg.is_read = False
            self.db.commit()
        else: # If not, then add one as unread
             crud.add_message(self.db, conv_test.id, "user", "explicit unread user", datetime.utcnow(), is_read=False)

        self.assertFalse(crud.has_unread_bot_messages(self.db, conv_test.id), "Should be false as only user message is unread")

        # Test with unread bot messages
        crud.add_message(self.db, conv_test.id, "bot", "unread bot 2", datetime.utcnow(), is_read=False)
        self.assertTrue(crud.has_unread_bot_messages(self.db, conv_test.id))

        # Test after marking messages as read
        crud.mark_messages_as_read(self.db, conv_test.id)
        self.assertFalse(crud.has_unread_bot_messages(self.db, conv_test.id))


if __name__ == '__main__':
    unittest.main()
