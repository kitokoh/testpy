import smtplib
import os
import re # For placeholder replacement
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
# from email.mime.application import MIMEApplication # MIMEBase is more general
from email.encoders import encode_base64

from PyQt5.QtCore import QObject # QObject for potential signals if service itself was threaded, not strictly needed now

# Assuming db.py and app_config.py are accessible
import db
from app_config import CONFIG # Though CONFIG not directly used here, db.py might use it

class EmailSenderService(QObject): # Inherit from QObject if it were to emit signals directly
    def __init__(self, smtp_config_id=None, parent=None):
        super().__init__(parent) # Call QObject's init if it's a QObject
        self.smtp_config = None
        if smtp_config_id:
            self.smtp_config = db.get_smtp_config_by_id(smtp_config_id)
        else:
            self.smtp_config = db.get_default_smtp_config()

        if not self.smtp_config:
            # This state should be checked by the caller before trying to send.
            print("Error: EmailSenderService initialized without a valid SMTP configuration.")
            # Consider raising an exception or having a method to check service readiness.

    def _get_value_from_context(self, path: str, context: dict, default_value="[Not Found]"):
        """
        Retrieves a value from a nested dictionary using a dot-separated path.
        Example path: "client.contact_person_name"
        """
        keys = path.split('.')
        current_level = context
        try:
            for key in keys:
                if isinstance(current_level, dict):
                    current_level = current_level[key]
                else: # Path is deeper than available context
                    return default_value
            # Ensure the final value is a string or can be converted
            return str(current_level) if current_level is not None else default_value
        except (KeyError, TypeError):
            return default_value

    def _replace_placeholders_in_text(self, text: str, context: dict) -> str:
        """
        Replaces placeholders like {{client.name}} or {{doc.current_date}} in text
        using values from the provided context dictionary.
        """
        if not text: # Handle None or empty text
            return ""

        def replacer(match):
            placeholder_path = match.group(1).strip() # Get the path inside {{}}
            return self._get_value_from_context(placeholder_path, context)

        # Regex to find {{ path.to.variable }}
        # It allows for spaces around the path.
        return re.sub(r"{{\s*([\w.]+)\s*}}", replacer, text)

    def send_email(self, client_id: str, recipients: list[str], subject_template: str,
                   body_html_template: str, attachments: list[str],
                   template_language_code: str, project_id: str = None) -> tuple[bool, str]:

        if not self.smtp_config:
            return False, "SMTP configuration not found or invalid."

        if not self.smtp_config.get('smtp_server') or not self.smtp_config.get('sender_email_address'):
             return False, "SMTP configuration is incomplete (missing server or sender email)."

        # 1. Fetch Personalization Context
        default_company = db.get_default_company()
        if not default_company:
            return False, "Default company information not found. Cannot send email."
        company_id = default_company['company_id']

        try:
            # Assuming get_document_context_data is robust enough
            context_data = db.get_document_context_data(
                client_id=client_id,
                company_id=company_id,
                target_language_code=template_language_code,
                project_id=project_id,
                # additional_context could be passed here if needed
            )
        except Exception as e:
            print(f"Error fetching document context data: {e}")
            return False, f"Failed to fetch personalization context: {e}"

        # 2. Personalize Subject and Body
        personalized_subject = self._replace_placeholders_in_text(subject_template, context_data)
        personalized_body_html = self._replace_placeholders_in_text(body_html_template, context_data)

        # 3. Create MIMEMultipart message
        msg = MIMEMultipart('related') # 'related' for embedding images if any, 'alternative' if plain text version also sent

        sender_display_name = self.smtp_config.get('sender_display_name', '')
        sender_email = self.smtp_config['sender_email_address']

        if sender_display_name:
            msg['From'] = f"{sender_display_name} <{sender_email}>"
        else:
            msg['From'] = sender_email

        msg['To'] = ", ".join(recipients)
        msg['Subject'] = personalized_subject

        # Attach HTML body
        # Ensure UTF-8 encoding for special characters
        msg.attach(MIMEText(personalized_body_html, 'html', 'utf-8'))

        # 4. Attach Files
        for file_path in attachments:
            if not os.path.exists(file_path):
                print(f"Attachment file not found: {file_path}. Skipping.")
                # Optionally, return an error or collect messages about skipped files
                continue

            ctype, encoding = mimetypes.guess_type(file_path)
            if ctype is None or encoding is not None: # Encoding suggests text, but we want binary for MIMEBase
                ctype = 'application/octet-stream' # Default for unknown or encoded types

            maintype, subtype = ctype.split('/', 1)

            try:
                with open(file_path, 'rb') as fp:
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(fp.read())

                encode_base64(part)
                part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file_path))
                msg.attach(part)
            except Exception as e:
                print(f"Error attaching file {file_path}: {e}")
                return False, f"Error attaching file {os.path.basename(file_path)}: {e}"

        # 5. SMTP Sending
        try:
            server = smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config.get('smtp_port', 587)) # Default port if not found
            if self.smtp_config.get('use_tls'):
                server.starttls()

            # Password is password_encrypted but used directly as per previous subtask's decision
            # This is insecure and should be addressed by encrypting/decrypting properly.
            password_to_use = self.smtp_config.get('password_encrypted', '')
            if self.smtp_config.get('username'): # Only login if username is present
                 server.login(self.smtp_config['username'], password_to_use)

            server.sendmail(sender_email, recipients, msg.as_string())
            server.quit()
            return True, "Email sent successfully."

        except smtplib.SMTPException as e:
            error_message = f"SMTP Error: {str(e)}"
            print(error_message)
            # More specific error handling if needed (e.g. auth failure, connection error)
            return False, error_message
        except Exception as e: # Catch other potential errors (e.g., network issues before SMTP stage)
            error_message = f"An unexpected error occurred during sending: {str(e)}"
            print(error_message)
            return False, error_message

if __name__ == '__main__':
    # This block is for basic testing of EmailSenderService if run directly.
    # Requires db.py to be functional and app_data.db to be initialized with:
    # - A default company
    # - An SMTP configuration (or one specified by ID)
    # - A client
    # - (Optional) A project

    print("Testing EmailSenderService...")
    db.initialize_database() # Ensure DB is ready

    # Attempt to get/create necessary data
    default_company = db.get_default_company()
    if not default_company:
        comp_id = db.add_company({'company_name': "Test Default Corp Inc.", 'address': "123 Test St"})
        if comp_id: db.set_default_company(comp_id)
        default_company = db.get_default_company()

    if not default_company:
        print("CRITICAL: Could not set up a default company. Aborting test.")
        sys.exit(1)

    smtp_config = db.get_default_smtp_config()
    if not smtp_config:
        print("No default SMTP config found. Add one manually or update this test.")
        # Example: Add a dummy SMTP config for testing structure (won't actually send without real server)
        # db.add_smtp_config({
        #     'config_name': 'TestSMTP', 'smtp_server': 'localhost', 'smtp_port': 1025, # Use a local debug server
        #     'username': 'testuser', 'password_encrypted': 'testpass',
        #     'sender_email_address': 'test@example.com', 'is_default': True
        # })
        # smtp_config = db.get_default_smtp_config()

    if not smtp_config:
        print("CRITICAL: No SMTP configuration available. Aborting test.")
        sys.exit(1)

    clients = db.get_all_clients()
    if not clients:
        client_id = db.add_client({'client_name': 'Email Test Client', 'company_name': 'Client Corp'})
        if not client_id:
            print("CRITICAL: Could not create a client. Aborting test.")
            sys.exit(1)
        clients = db.get_all_clients()

    test_client_id = clients[0]['client_id']

    # Create a dummy attachment file for testing
    dummy_attachment_path = "dummy_attachment.txt"
    with open(dummy_attachment_path, "w") as f:
        f.write("This is a test attachment.")

    email_service = EmailSenderService() # Uses default SMTP

    if not email_service.smtp_config:
        print("Failed to initialize EmailSenderService with SMTP config. Check DB setup.")
    else:
        print(f"Using SMTP config: {email_service.smtp_config.get('config_name')}")
        subject_template = "Test Email for {{client.company_name}} - {{doc.current_date}}"
        body_template = """
        <html>
            <body>
                <h1>Hello {{client.contact_person_name}} at {{client.company_name}}!</h1>
                <p>This is a test email regarding project: {{project.name | default: 'N/A'}}.</p>
                <p>Seller contact: {{seller.personnel.representative_name}}</p>
                <p>Current date: {{doc.current_date}}</p>
            </body>
        </html>
        """
        recipients_list = ["recipient1@example.com", "recipient2@example.com"] # Replace with actual testable emails if using a real SMTP server

        success, message = email_service.send_email(
            client_id=test_client_id,
            recipients=recipients_list,
            subject_template=subject_template,
            body_html_template=body_template,
            attachments=[dummy_attachment_path],
            template_language_code='en', # Assuming 'en'
            project_id=None # Or provide a test project ID
        )

        print(f"Send Email Attempt Result: Success={success}, Message='{message}'")

    # Clean up dummy attachment
    if os.path.exists(dummy_attachment_path):
        os.remove(dummy_attachment_path)

    print("EmailSenderService test finished.")
