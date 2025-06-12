import os
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, text, func, desc, or_, and_
from sqlalchemy.orm import sessionmaker, aliased, contains_eager, joinedload
from contextlib import contextmanager
from models import (
    Base, User, Company, Client, Contact, ClientContact, Document, DocumentVersion,
    Template, Placeholder, DocumentPlaceholder, Role, UserRole, UserCompany, UserClient,
    ApiKey, LoginHistory, EmailVerificationToken, PasswordResetToken, Notification,
    DocumentShare, DocumentSigningRequest, DocumentSigningResponse, AuditLog, Setting,
    Subscription, SubscriptionFeature, Feature, Payment, Invoice, SupportTicket,
    SupportTicketMessage, Comment, Tag, DocumentTag, Team, TeamMember, Project,
    ProjectDocument, ProjectMember, Workflow, WorkflowStep, WorkflowExecution,
    WorkflowStepExecution, CustomField, CustomFieldValue, Integration, Webhook,
    WebhookEvent, File, Folder, FileVersion, ShareLink, UserActivity, Report,
    TwoFactorAuthentication, OAuth2Token, OAuth2Client, UserPreferences, UserGroup,
    GroupPermission, Permission, DocumentTemplate, DocumentEvent, DocumentComment,
    DocumentTask, DocumentReminder, DocumentMetadata, DocumentAnalytics,
    UserDocumentRole, DocumentAccessRequest, DocumentLock, DocumentReview,
    DocumentVersionReview, DocumentNote, DocumentHistory, DocumentComparison,
    DocumentTemplateCategory, DocumentTemplateTag, UserFeedback, SystemNotification,
    UserLoginAttempt, UserPasswordHistory, UserSecurityQuestion, UserAccountRecovery,
    UserPrivacySetting, UserTermsOfServiceAgreement, UserDataExportRequest,
    UserDeletionRequest, AdminActionLog, SystemHealth, ApiUsageStat,
    RateLimit, GeoLocationData, CurrencyExchangeRate, Language, Translation,
    UiCustomization, ReportSchedule, ReportRecipient, ExternalServiceLog,
    UserConsent, DataProcessingPurpose, DataRetentionPolicy, SecurityAuditLog,
    UserSession, FeatureFlag, ABTest, UserSegment, UserSegmentMembership,
    NotificationPreference, UserNotificationChannel, UserNotificationLog,
    UserSearchHistory, UserFavoriteDocument, UserFavoriteTemplate, UserTag,
    UserDocumentTag, UserClientTag, UserCompanyTag, UserContactTag,
    UserProjectTag, UserWorkflowTag, UserFileTag, UserFolderTag, UserCommentTag
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper function to safely parse JSON strings
def _parse_json_field(json_string, default_value=None):
    if default_value is None:
        default_value = {}
    if isinstance(json_string, (dict, list)): # Already parsed
        return json_string
    if isinstance(json_string, str):
        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            return default_value
    return default_value

# Helper function to parse key-value strings (e.g., "VAT: XXX; REG: YYY")
def _parse_key_value_string(kv_string, default_value=None):
    if default_value is None:
        default_value = {}
    if not isinstance(kv_string, str):
        return default_value
    
    parsed_data = {}
    try:
        pairs = kv_string.split(';')
        for pair in pairs:
            if ':' in pair:
                key, value = pair.split(':', 1)
                parsed_data[key.strip().lower().replace(" ", "_")] = value.strip()
    except Exception:
        return default_value
    return parsed_data

# Helper function to format address parts
def _format_address_parts(address_line1, city, postal_code, country):
    parts = [address_line1, city, postal_code, country]
    return ", ".join(filter(None, parts))


def get_document_context_data(db_session, document_id: int, additional_context: dict = None) -> dict:
    if additional_context is None:
        additional_context = {}

    context = {
        "document": {},
        "seller": {},
        "client": {},
        "contact_person": {}, # Primary contact for the client
        "meta": {},
        "additional": additional_context
    }

    # Fetch the document and its relationships
    doc = db_session.query(Document).options(
        joinedload(Document.client).joinedload(Client.company), # client.company for client's associated company if any
        joinedload(Document.company), # seller company
        joinedload(Document.versions).options(
            joinedload(DocumentVersion.placeholders).joinedload(DocumentPlaceholder.placeholder)
        )
    ).filter(Document.id == document_id).first()

    if not doc:
        raise ValueError(f"Document with id {document_id} not found.")

    # --- Document Info ---
    context["document"]["id"] = doc.id
    context["document"]["title"] = doc.title
    context["document"]["type"] = doc.document_type
    context["document"]["status"] = doc.status
    context["document"]["created_at"] = doc.created_at.strftime('%Y-%m-%d %H:%M:%S') if doc.created_at else "N/A"
    context["document"]["updated_at"] = doc.updated_at.strftime('%Y-%m-%d %H:%M:%S') if doc.updated_at else "N/A"
    context["document"]["currency"] = doc.currency or additional_context.get("currency", "USD")
    context["document"]["total_amount"] = str(doc.total_amount) if doc.total_amount is not None else "N/A"
    context["document"]["due_date"] = doc.due_date.strftime('%Y-%m-%d') if doc.due_date else "N/A"
    context["document"]["issue_date"] = additional_context.get("issue_date", datetime.now(timezone.utc).strftime('%Y-%m-%d'))

    # Latest version (assuming versions are ordered by creation or version number)
    latest_version = doc.versions[-1] if doc.versions else None
    if latest_version:
        context["document"]["version_id"] = latest_version.id
        context["document"]["version_number"] = latest_version.version_number
        context["document"]["version_created_at"] = latest_version.created_at.strftime('%Y-%m-%d %H:%M:%S')

    # --- Seller Company Info ---
    seller_company_data = doc.company
    if seller_company_data:
        context["seller"]["company_name"] = seller_company_data.name or "N/A"
        context["seller"]["email"] = seller_company_data.email or "N/A"
        context["seller"]["phone"] = seller_company_data.phone or "N/A"
        context["seller"]["website"] = seller_company_data.website or "N/A"

        # Seller Bank Details
        payment_info_raw = seller_company_data.payment_info # Assuming this is a field in Company model
        payment_info = _parse_json_field(payment_info_raw)

        context["seller"]["bank_name"] = payment_info.get("bank_name", additional_context.get("seller_bank_name", "N/A"))
        context["seller"]["bank_account_number"] = payment_info.get("account_number", additional_context.get("seller_bank_account_number", "N/A"))
        context["seller"]["bank_swift_bic"] = payment_info.get("swift_bic", additional_context.get("seller_bank_swift_bic", "N/A"))
        context["seller"]["bank_address"] = payment_info.get("bank_address", additional_context.get("seller_bank_address", "N/A"))
        context["seller"]["bank_account_holder_name"] = payment_info.get("account_holder_name", context["seller"]["company_name"])


        # Seller VAT ID & Registration Number
        other_info_raw = seller_company_data.other_info # Assuming this is a field in Company model
        other_info_json = _parse_json_field(other_info_raw)
        other_info_kv = _parse_key_value_string(other_info_raw) # Fallback or alternative parsing

        context["seller"]["vat_id"] = other_info_json.get("vat_id",
                                       other_info_kv.get("vat",
                                       other_info_kv.get("vat_id",
                                       additional_context.get("seller_vat_id", "N/A"))))
        context["seller"]["registration_number"] = other_info_json.get("registration_number",
                                                  other_info_kv.get("reg",
                                                  other_info_kv.get("registration_number",
                                                  additional_context.get("seller_registration_number", "N/A"))))

        # Seller Structured Address
        raw_seller_address = seller_company_data.address or ""
        context["seller"]["address_line1"] = raw_seller_address # Can be improved with parsing if complex
        context["seller"]["city"] = additional_context.get("seller_city", "") # Assume simple address for now
        context["seller"]["postal_code"] = additional_context.get("seller_postal_code", "")
        context["seller"]["country"] = additional_context.get("seller_country", "")

        context["seller"]["city_zip_country"] = _format_address_parts(
            None, context["seller"]["city"], context["seller"]["postal_code"], context["seller"]["country"]
        ).strip(", ") or "N/A"

        context["seller"]["address"] = _format_address_parts(
            context["seller"]["address_line1"],
            context["seller"]["city"],
            context["seller"]["postal_code"],
            context["seller"]["country"]
        ) or "N/A"
        if context["seller"]["address"] == "N/A" and raw_seller_address: # Fallback if parts are missing
             context["seller"]["address"] = raw_seller_address

    else: # Fallback if seller_company_data is missing
        context["seller"]["company_name"] = additional_context.get("seller_company_name", "N/A")
        context["seller"]["email"] = additional_context.get("seller_email", "N/A")
        context["seller"]["phone"] = additional_context.get("seller_phone", "N/A")
        context["seller"]["website"] = additional_context.get("seller_website", "N/A")
        context["seller"]["bank_name"] = additional_context.get("seller_bank_name", "N/A")
        context["seller"]["bank_account_number"] = additional_context.get("seller_bank_account_number", "N/A")
        context["seller"]["bank_swift_bic"] = additional_context.get("seller_bank_swift_bic", "N/A")
        context["seller"]["bank_address"] = additional_context.get("seller_bank_address", "N/A")
        context["seller"]["bank_account_holder_name"] = additional_context.get("seller_company_name", "N/A")
        context["seller"]["vat_id"] = additional_context.get("seller_vat_id", "N/A")
        context["seller"]["registration_number"] = additional_context.get("seller_registration_number", "N/A")
        context["seller"]["address_line1"] = additional_context.get("seller_address_line1", "N/A")
        context["seller"]["city"] = additional_context.get("seller_city", "N/A")
        context["seller"]["postal_code"] = additional_context.get("seller_postal_code", "N/A")
        context["seller"]["country"] = additional_context.get("seller_country", "N/A")
        context["seller"]["city_zip_country"] = _format_address_parts(None, context["seller"]["city"], context["seller"]["postal_code"], context["seller"]["country"]).strip(", ") or "N/A"
        context["seller"]["address"] = additional_context.get("seller_address", "N/A")


    # --- Client Info ---
    client_data = doc.client
    primary_client_contact_data = None

    if client_data:
        context["client"]["company_name"] = client_data.company_name or "N/A" # Assuming Client has company_name
        context["client"]["email"] = client_data.email or "N/A"
        context["client"]["phone"] = client_data.phone or "N/A"

        # Client VAT ID & Registration Number
        # Try parsing from client_data.notes then client_data.distributor_specific_info
        client_notes_raw = client_data.notes
        client_dist_info_raw = client_data.distributor_specific_info

        client_notes_json = _parse_json_field(client_notes_raw)
        client_notes_kv = _parse_key_value_string(client_notes_raw)

        client_dist_info_json = _parse_json_field(client_dist_info_raw)
        client_dist_info_kv = _parse_key_value_string(client_dist_info_raw)

        context["client"]["vat_id"] = client_notes_json.get("vat_id",
                                       client_notes_kv.get("vat",
                                       client_notes_kv.get("vat_id",
                                       client_dist_info_json.get("vat_id",
                                       client_dist_info_kv.get("vat",
                                       client_dist_info_kv.get("vat_id",
                                       additional_context.get("client_vat_id", "N/A")))))))

        context["client"]["registration_number"] = client_notes_json.get("registration_number",
                                                  client_notes_kv.get("reg",
                                                  client_notes_kv.get("registration_number",
                                                  client_dist_info_json.get("registration_number",
                                                  client_dist_info_kv.get("reg",
                                                  client_dist_info_kv.get("registration_number",
                                                  additional_context.get("client_registration_number", "N/A")))))))

        # Client Structured Address
        # Try to get primary contact for address details
        primary_client_contact_assoc = db_session.query(ClientContact)\
            .join(Contact)\
            .filter(ClientContact.client_id == client_data.id, ClientContact.is_primary == True)\
            .options(joinedload(ClientContact.contact))\
            .first()

        if primary_client_contact_assoc and primary_client_contact_assoc.contact:
            primary_client_contact_data = primary_client_contact_assoc.contact
            context["contact_person"]["first_name"] = primary_client_contact_data.first_name or "N/A"
            context["contact_person"]["last_name"] = primary_client_contact_data.last_name or "N/A"
            context["contact_person"]["email"] = primary_client_contact_data.email or "N/A"
            context["contact_person"]["phone"] = primary_client_contact_data.phone or "N/A"
            context["contact_person"]["full_name"] = f"{primary_client_contact_data.first_name or ''} {primary_client_contact_data.last_name or ''}".strip() or "N/A"

            context["client"]["address_line1"] = primary_client_contact_data.address_streetAddress or client_data.address_line1 or "N/A" # client_data.address_line1 is a guess
            context["client"]["city"] = primary_client_contact_data.address_city or client_data.city_name or additional_context.get("client_city", "N/A")
            context["client"]["postal_code"] = primary_client_contact_data.address_postalCode or client_data.postal_code or additional_context.get("client_postal_code", "N/A") # client_data.postal_code is a guess
            context["client"]["country"] = primary_client_contact_data.address_country or client_data.country_name or additional_context.get("client_country", "N/A")
        else: # Fallback if no primary contact or contact has no address
            context["contact_person"]["full_name"] = additional_context.get("client_contact_person_name", "N/A")
            context["contact_person"]["email"] = additional_context.get("client_contact_person_email", "N/A")
            context["contact_person"]["phone"] = additional_context.get("client_contact_person_phone", "N/A")

            # Fallback to client table fields or additional_context for address
            # Assuming client_data might have 'address_line1', 'city_name', 'postal_code', 'country_name'
            context["client"]["address_line1"] = client_data.address_line1 if hasattr(client_data, 'address_line1') else additional_context.get("client_address_line1", "N/A")
            context["client"]["city"] = client_data.city_name if hasattr(client_data, 'city_name') else additional_context.get("client_city", "N/A")
            context["client"]["postal_code"] = client_data.postal_code if hasattr(client_data, 'postal_code') else additional_context.get("client_postal_code", "N/A")
            context["client"]["country"] = client_data.country_name if hasattr(client_data, 'country_name') else additional_context.get("client_country", "N/A")

        context["client"]["city_zip_country"] = _format_address_parts(
            None, context["client"]["city"], context["client"]["postal_code"], context["client"]["country"]
        ).strip(", ") or "N/A"

        context["client"]["address"] = _format_address_parts(
            context["client"]["address_line1"],
            context["client"]["city"],
            context["client"]["postal_code"],
            context["client"]["country"]
        ) or "N/A"
        # If address parts were N/A but client_data has a general address field:
        if context["client"]["address"] == "N/A" and hasattr(client_data, 'address') and client_data.address:
            context["client"]["address"] = client_data.address


    else: # Fallback if client_data is missing
        context["client"]["company_name"] = additional_context.get("client_company_name", "N/A")
        context["client"]["email"] = additional_context.get("client_email", "N/A")
        context["client"]["phone"] = additional_context.get("client_phone", "N/A")
        context["client"]["vat_id"] = additional_context.get("client_vat_id", "N/A")
        context["client"]["registration_number"] = additional_context.get("client_registration_number", "N/A")
        context["client"]["address_line1"] = additional_context.get("client_address_line1", "N/A")
        context["client"]["city"] = additional_context.get("client_city", "N/A")
        context["client"]["postal_code"] = additional_context.get("client_postal_code", "N/A")
        context["client"]["country"] = additional_context.get("client_country", "N/A")
        context["client"]["city_zip_country"] = _format_address_parts(None, context["client"]["city"], context["client"]["postal_code"], context["client"]["country"]).strip(", ") or "N/A"
        context["client"]["address"] = additional_context.get("client_address", "N/A")
        context["contact_person"]["full_name"] = additional_context.get("client_contact_person_name", "N/A")
        # ... other contact person fallbacks from additional_context if needed


    # --- Meta & Placeholders ---
    context["meta"]["current_date"] = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    context["meta"]["current_time"] = datetime.now(timezone.utc).strftime('%H:%M:%S')
    context["meta"]["document_name"] = context["document"]["title"] # For convenience

    # Map to common placeholder names that might be used in templates
    # These are general mappings; specific templates might use more direct context paths
    final_placeholders = {
        "DOCUMENT_ID": context["document"]["id"],
        "DOCUMENT_TITLE": context["document"]["title"],
        "DOCUMENT_TYPE": context["document"]["type"],
        "DOCUMENT_CURRENCY": context["document"]["currency"],
        "DOCUMENT_TOTAL_AMOUNT": context["document"]["total_amount"],
        "DOCUMENT_DUE_DATE": context["document"]["due_date"],
        "DOCUMENT_ISSUE_DATE": context["document"]["issue_date"],

        "SELLER_COMPANY_NAME": context["seller"].get("company_name", "N/A"),
        "SELLER_ADDRESS": context["seller"].get("address", "N/A"),
        "SELLER_EMAIL": context["seller"].get("email", "N/A"),
        "SELLER_PHONE": context["seller"].get("phone", "N/A"),
        "SELLER_WEBSITE": context["seller"].get("website", "N/A"),
        "SELLER_VAT_ID": context["seller"].get("vat_id", "N/A"),
        "SELLER_REGISTRATION_NUMBER": context["seller"].get("registration_number", "N/A"),
        "SELLER_BANK_NAME": context["seller"].get("bank_name", "N/A"),
        "SELLER_BANK_ACCOUNT_NUMBER": context["seller"].get("bank_account_number", "N/A"),
        "SELLER_BANK_SWIFT_BIC": context["seller"].get("bank_swift_bic", "N/A"),
        "SELLER_BANK_ADDRESS": context["seller"].get("bank_address", "N/A"),
        "SELLER_ACCOUNT_HOLDER_NAME": context["seller"].get("bank_account_holder_name", "N/A"),
        "SELLER_CITY_ZIP_COUNTRY": context["seller"].get("city_zip_country", "N/A"),


        "BUYER_COMPANY_NAME": context["client"].get("company_name", "N/A"), # Using BUYER_ prefix for client for commonality
        "BUYER_ADDRESS": context["client"].get("address", "N/A"),
        "BUYER_EMAIL": context["client"].get("email", "N/A"),
        "BUYER_PHONE": context["client"].get("phone", "N/A"),
        "BUYER_VAT_ID": context["client"].get("vat_id", "N/A"), # CLIENT_VAT_ID is also fine, depends on template
        "CLIENT_VAT_ID": context["client"].get("vat_id", "N/A"),
        "BUYER_REGISTRATION_NUMBER": context["client"].get("registration_number", "N/A"),
        "CLIENT_REGISTRATION_NUMBER": context["client"].get("registration_number", "N/A"),
        "BUYER_CITY_ZIP_COUNTRY": context["client"].get("city_zip_country", "N/A"),


        "CONTACT_PERSON_NAME": context["contact_person"].get("full_name", "N/A"),
        "CONTACT_PERSON_EMAIL": context["contact_person"].get("email", "N/A"),
        "CONTACT_PERSON_PHONE": context["contact_person"].get("phone", "N/A"),

        "CURRENT_DATE": context["meta"]["current_date"],
    }

    # Add custom fields from the latest version's placeholders
    if latest_version:
        for vp in latest_version.placeholders:
            if vp.placeholder: # Ensure placeholder object exists
                # Use placeholder.name as key, vp.value as value
                # Sanitize placeholder name to be a valid key if necessary, though usually they are simple strings
                placeholder_key = vp.placeholder.name.upper().replace(" ", "_")
                final_placeholders[placeholder_key] = vp.value or "N/A"
            elif vp.name: # Fallback if placeholder object is not loaded but name/value are directly on DocumentPlaceholder
                placeholder_key = vp.name.upper().replace(" ", "_")
                final_placeholders[placeholder_key] = vp.value or "N/A"


    # Merge additional_context into final_placeholders, giving precedence to already processed data
    for key, value in additional_context.items():
        final_placeholders.setdefault(key.upper(), value) # Use setdefault to avoid overwriting
        final_placeholders.setdefault(key, value) # Also add with original key for flexibility

    context["placeholders"] = final_placeholders # This is the flat dict for template rendering

    return context

# Example Usage (requires setting up mock objects or a test database):
if __name__ == "__main__":
    # This is a placeholder for testing.
    # To run this, you would need to initialize the DB and populate it with test data.
    # init_db()
    
    # print("Database initialized.")
    
    # with get_db() as session:
        # Create dummy data for Company, Client, Document, Contact, ClientContact etc.
        # company = Company(name="Test Seller Inc.", email="seller@example.com", phone="123456789", website="seller.example.com",
        #                   address="123 Seller St, Sellerville, SC 12345",
        #                   payment_info='{"bank_name": "Seller Bank", "account_number": "1122334455", "swift_bic": "SELBUS33", "bank_address": "1 Bank Plaza, Sellerville"}',
        #                   other_info='VAT ID: SE1234567890; Registration Number: 556677-8899')
        # client_company = Company(name="Test Buyer Co.", email="buyer@example.com") # If client is also a company
        # client = Client(company_name="Real Buyer Ltd.", email="mainbuyer@example.com", phone="987654321",
        #                 notes='{"vat_id": "CLIVAT001"}', distributor_specific_info="Reg: CLIREG999",
        #                 address_line1="456 Buyer Ave", city_name="Buytown", postal_code="BT 54321", country_name="Clientland"
        #                 )
        # contact = Contact(first_name="John", last_name="Doe", email="john.doe@buyer.com", phone="987650000",
        #                   address_streetAddress="1 Contact Rd", address_city="Buytown", address_postalCode="BT 54321", address_country="Clientland")

        # session.add_all([company, client_company, client, contact])
        # session.commit()

        # client_contact = ClientContact(client_id=client.id, contact_id=contact.id, is_primary=True)
        # session.add(client_contact)

        # document = Document(title="Test Invoice", document_type="invoice", status="draft",
        #                     company_id=company.id, client_id=client.id, currency="EUR", total_amount=1500.75,
        #                     due_date=datetime.utcnow() + timedelta(days=30))
        # session.add(document)
        # session.commit()

        # # Create a version and some placeholders if needed for full testing
        # doc_version = DocumentVersion(document_id=document.id, version_number=1, content="Template content with {{SELLER_COMPANY_NAME}}")
        # session.add(doc_version)
        # session.commit()

        # # Example of adding a DocumentPlaceholder if your structure requires it
        # placeholder_obj = Placeholder(name="CUSTOM_FIELD_1", description="A custom field")
        # session.add(placeholder_obj)
        # session.commit()
        # doc_placeholder = DocumentPlaceholder(document_version_id=doc_version.id, placeholder_id=placeholder_obj.id, value="Custom Value 123")
        # session.add(doc_placeholder)
        # session.commit()


        # print(f"Fetching context for document ID: {document.id}")
        # try:
        #     context_data = get_document_context_data(session, document.id, additional_context={
        #         "issue_date": "2023-10-01",
        #         "seller_city": "New Sellerville", # Test additional_context override/supplement
        #         "seller_postal_code": "SC 67890",
        #         "seller_country": "Sellerland"
        #     })
        #     import pprint
        #     pprint.pprint(context_data)

        #     # Test specific fields
        #     print("\n--- Specific Checks ---")
        #     print(f"Seller Bank Name: {context_data['seller']['bank_name']}")
        #     print(f"Seller VAT ID: {context_data['seller']['vat_id']}")
        #     print(f"Seller Address: {context_data['seller']['address']}")
        #     print(f"Client VAT ID: {context_data['client']['vat_id']}")
        #     print(f"Client Address: {context_data['client']['address']}")
        #     print(f"Contact Person: {context_data['contact_person']['full_name']}")
        #     print(f"Placeholder for SELLER_COMPANY_NAME: {context_data['placeholders']['SELLER_COMPANY_NAME']}")
        #     print(f"Placeholder for CUSTOM_FIELD_1: {context_data['placeholders'].get('CUSTOM_FIELD_1')}")


        # except ValueError as e:
        #     print(f"Error: {e}")
        # except Exception as e:
        #     print(f"An unexpected error occurred: {e}")
        #     import traceback
        #     traceback.print_exc()
    pass
