import sqlite3
import json
import os

# Consistent with sendmail.py's use of DB_PATH_mail from imports.py
# However, for this script, we'll define it directly as per requirements.
DB_PATH = "mail_db.sqlite"
TEMPLATES_DIR = "email_template_designs"

# Placeholder list for variables, can be refined per template if needed
DEFAULT_VARIABLES = json.dumps([
    "user_name", "company_name", "email_subject", "email_body_title",
    "email_body_content", "call_to_action_button_text", "call_to_action_button_link",
    "logo_url", "current_year", "email_footer_contact_info", "email_footer_terms_link",
    "email_footer_privacy_policy_link", "email_footer_unsubscribe_link", "reset_link",
    "confirmation_link"
])

TEMPLATES_DATA = [
    # Welcome Emails
    {
        "name": "Welcome Email (EN)",
        "subject": "Welcome to {{company_name}}!",
        "content_file": "welcome_email_en.html",
        "variables": DEFAULT_VARIABLES
    },
    {
        "name": "Welcome Email (FR)",
        "subject": "Bienvenue chez {{company_name}} !",
        "content_file": "welcome_email_fr.html",
        "variables": DEFAULT_VARIABLES
    },
    {
        "name": "Welcome Email (AR)",
        "subject": "مرحباً بك في {{company_name}}!",
        "content_file": "welcome_email_ar.html",
        "variables": DEFAULT_VARIABLES
    },
    # Password Reset Emails
    {
        "name": "Password Reset (EN)",
        "subject": "Reset Your Password for {{company_name}}",
        "content_file": "password_reset_email_en.html",
        "variables": DEFAULT_VARIABLES # reset_link is included in DEFAULT_VARIABLES
    },
    {
        "name": "Password Reset (FR)",
        "subject": "Réinitialisez votre mot de passe pour {{company_name}}",
        "content_file": "password_reset_email_fr.html",
        "variables": DEFAULT_VARIABLES
    },
    {
        "name": "Password Reset (AR)",
        "subject": "إعادة تعيين كلمة المرور الخاصة بك لـ {{company_name}}",
        "content_file": "password_reset_email_ar.html",
        "variables": DEFAULT_VARIABLES
    },
    # Newsletter Subscription Emails
    {
        "name": "Newsletter Subscription (EN)",
        "subject": "Confirm Your Subscription to {{company_name}} Newsletter",
        "content_file": "newsletter_subscription_email_en.html",
        "variables": DEFAULT_VARIABLES # confirmation_link is included
    },
    {
        "name": "Newsletter Subscription (FR)",
        "subject": "Confirmez votre abonnement à la newsletter de {{company_name}}",
        "content_file": "newsletter_subscription_email_fr.html",
        "variables": DEFAULT_VARIABLES
    },
    {
        "name": "Newsletter Subscription (AR)",
        "subject": "أكّد اشتراكك في النشرة الإخبارية لـ {{company_name}}",
        "content_file": "newsletter_subscription_email_ar.html",
        "variables": DEFAULT_VARIABLES
    }
]

def create_tables_if_not_exist(conn):
    cursor = conn.cursor()

    # Table configuration SMTP
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS smtp_config (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            smtp_server TEXT NOT NULL,
            smtp_port INTEGER NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            use_tls BOOLEAN DEFAULT 1,
            is_default BOOLEAN DEFAULT 0
        )
    ''')

    # Table templates d'emails
    # Added UNIQUE constraint to 'name' as requested for idempotency
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            subject TEXT NOT NULL,
            content TEXT NOT NULL,
            variables TEXT, -- JSON string
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table contacts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            company TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table listes de contacts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_lists (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table relation contacts-listes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_list_members (
            id INTEGER PRIMARY KEY,
            contact_id INTEGER,
            list_id INTEGER,
            FOREIGN KEY (contact_id) REFERENCES contacts (id) ON DELETE CASCADE, -- Added ON DELETE CASCADE
            FOREIGN KEY (list_id) REFERENCES contact_lists (id) ON DELETE CASCADE -- Added ON DELETE CASCADE
        )
    ''')

    # Table envois planifiés
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_emails (
            id INTEGER PRIMARY KEY,
            template_id INTEGER,
            smtp_config_id INTEGER,
            recipient_type TEXT, -- 'contact' ou 'list'
            recipient_id INTEGER,
            scheduled_time TIMESTAMP,
            status TEXT DEFAULT 'pending', -- pending, sent, failed
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP,
            FOREIGN KEY (template_id) REFERENCES email_templates (id) ON DELETE SET NULL, -- Added ON DELETE SET NULL
            FOREIGN KEY (smtp_config_id) REFERENCES smtp_config (id) ON DELETE SET NULL -- Added ON DELETE SET NULL
        )
    ''')

    # Table relances
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY,
            scheduled_email_id INTEGER,
            reminder_time TIMESTAMP,
            message TEXT,
            is_sent BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scheduled_email_id) REFERENCES scheduled_emails (id) ON DELETE CASCADE -- Added ON DELETE CASCADE
        )
    ''')

    conn.commit()
    print("Database tables checked/created successfully.")

def main():
    conn = None  # Initialize conn to None
    try:
        conn = sqlite3.connect(DB_PATH)
        print(f"Connected to database: {DB_PATH}")
        create_tables_if_not_exist(conn)
        cursor = conn.cursor()

        for template_data in TEMPLATES_DATA:
            try:
                # Check if template already exists by name
                cursor.execute("SELECT id FROM email_templates WHERE name = ?", (template_data["name"],))
                if cursor.fetchone():
                    print(f"Template '{template_data['name']}' already exists. Skipping.")
                    continue

                file_path = os.path.join(TEMPLATES_DIR, template_data["content_file"])

                if not os.path.exists(file_path):
                    print(f"Error: File not found for template '{template_data['name']}' at path '{file_path}'. Skipping.")
                    continue

                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                cursor.execute(
                    "INSERT INTO email_templates (name, subject, content, variables) VALUES (?, ?, ?, ?)",
                    (template_data["name"], template_data["subject"], content, template_data["variables"])
                )
                conn.commit()
                print(f"Successfully inserted template: {template_data['name']}")

            except FileNotFoundError: # Should be caught by os.path.exists now, but good to keep
                print(f"Error: File not found for template '{template_data['name']}' at path '{file_path}'")
            except sqlite3.IntegrityError: # Handles UNIQUE constraint violation if somehow the check above fails
                print(f"Error: Template '{template_data['name']}' already exists (IntegrityError). Skipping.")
            except sqlite3.Error as e:
                print(f"Database error inserting template '{template_data['name']}': {e}")
            except Exception as e:
                print(f"An unexpected error occurred with template '{template_data['name']}': {e}")

    except sqlite3.Error as e:
        print(f"Failed to connect to or initialize database: {e}")
    finally:
        if conn:
            conn.close()
            print(f"Database connection closed.")

if __name__ == "__main__":
    main()
