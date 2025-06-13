# db/cruds/scheduled_emails_crud.py
import logging

def add_scheduled_email(*args, **kwargs):
    logging.warning("Placeholder function add_scheduled_email called")
    return None

def get_scheduled_email_by_id(*args, **kwargs):
    logging.warning("Placeholder function get_scheduled_email_by_id called")
    return None

def get_pending_scheduled_emails(*args, **kwargs):
    logging.warning("Placeholder function get_pending_scheduled_emails called")
    return []

def update_scheduled_email_status(*args, **kwargs):
    logging.warning("Placeholder function update_scheduled_email_status called")
    return None

def delete_scheduled_email(*args, **kwargs):
    logging.warning("Placeholder function delete_scheduled_email called")
    return None

def add_email_reminder(*args, **kwargs):
    logging.warning("Placeholder function add_email_reminder called")
    return None

def get_pending_reminders(*args, **kwargs):
    logging.warning("Placeholder function get_pending_reminders called")
    return []

def update_reminder_status(*args, **kwargs):
    logging.warning("Placeholder function update_reminder_status called")
    return None

def delete_email_reminder(*args, **kwargs):
    logging.warning("Placeholder function delete_email_reminder called")
    return None

__all__ = [
    "add_scheduled_email",
    "get_scheduled_email_by_id",
    "get_pending_scheduled_emails",
    "update_scheduled_email_status",
    "delete_scheduled_email",
    "add_email_reminder",
    "get_pending_reminders",
    "update_reminder_status",
    "delete_email_reminder",
]
