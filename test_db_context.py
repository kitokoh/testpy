import unittest
from unittest.mock import MagicMock, PropertyMock
import datetime # Import datetime
from db import get_document_context_data, _parse_json_field, _parse_key_value_string, _format_address_parts

# --- Mocks for SQLAlchemy models ---
# These need to be classes to allow attribute assignment in tests.

class MockCompany:
    def __init__(self, name=None, email=None, phone=None, website=None, address=None, payment_info=None, other_info=None):
        self.id = 1  # Default ID
        self.name = name
        self.email = email
        self.phone = phone
        self.website = website
        self.address = address
        self.payment_info = payment_info # Store as string or dict based on test
        self.other_info = other_info   # Store as string or dict based on test

class MockClient:
    def __init__(self, id=1, company_name=None, email=None, phone=None, notes=None, distributor_specific_info=None,
                 address_line1=None, city_name=None, postal_code=None, country_name=None, address=None, company=None):
        self.id = id
        self.company_name = company_name
        self.email = email
        self.phone = phone
        self.notes = notes
        self.distributor_specific_info = distributor_specific_info
        self.address_line1 = address_line1
        self.city_name = city_name
        self.postal_code = postal_code
        self.country_name = country_name
        self.address = address # General address field
        self.company = company # Associated company (e.g. for client.company relationship)

class MockContact:
    def __init__(self, id=1, first_name=None, last_name=None, email=None, phone=None,
                 address_streetAddress=None, address_city=None, address_postalCode=None, address_country=None):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.address_streetAddress = address_streetAddress
        self.address_city = address_city
        self.address_postalCode = address_postalCode
        self.address_country = address_country

class MockClientContact:
    def __init__(self, client_id=None, contact_id=None, is_primary=False, contact=None):
        self.client_id = client_id
        self.contact_id = contact_id
        self.is_primary = is_primary
        self.contact = contact # Nested MockContact

class MockPlaceholder:
    def __init__(self, name=None):
        self.name = name

class MockDocumentPlaceholder:
    def __init__(self, placeholder=None, value=None, name=None): # Added name for fallback
        self.placeholder = placeholder
        self.value = value
        self.name = name # Fallback if placeholder object isn't there

class MockDocumentVersion:
    def __init__(self, id=1, version_number=1, created_at=None, placeholders=None):
        self.id = id
        self.version_number = version_number
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc)
        self.placeholders = placeholders if placeholders is not None else []

class MockDocument:
    def __init__(self, id=1, title=None, document_type=None, status=None, created_at=None, updated_at=None,
                 currency=None, total_amount=None, due_date=None, company=None, client=None, versions=None):
        self.id = id
        self.title = title
        self.document_type = document_type
        self.status = status
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc)
        self.updated_at = updated_at or datetime.datetime.now(datetime.timezone.utc)
        self.currency = currency
        self.total_amount = total_amount
        self.due_date = due_date
        self.company = company # MockCompany (Seller)
        self.client = client   # MockClient
        self.versions = versions if versions is not None else [MockDocumentVersion()]


class TestDocumentContext(unittest.TestCase):

    def setUp(self):
        self.mock_db_session = MagicMock()

        # Mock for document query
        self.mock_doc_query = MagicMock()
        self.mock_db_session.query.return_value.options.return_value.filter.return_value.first = self.mock_doc_query

        # Mock for client contact query
        self.mock_client_contact_query = MagicMock()
        # Configure the session mock to return the client contact query mock
        # This is a bit tricky as it's a chained call. We'll assume a structure.
        # If ClientContact is queried directly:
        # self.mock_db_session.query(ClientContact).join(Contact)... = self.mock_client_contact_query
        # For now, let's make the return_value of query itself configurable for different model queries

        # A more flexible way to mock chained queries:
        self.mock_db_session.query.return_value.join.return_value.filter.return_value.options.return_value.first = self.mock_client_contact_query


    def test_helper_parse_json_field(self):
        self.assertEqual(_parse_json_field('{"key": "value"}'), {"key": "value"})
        self.assertEqual(_parse_json_field('{"num": 1, "bool": true}'), {"num": 1, "bool": True})
        self.assertEqual(_parse_json_field('invalid json', default_value={"error": True}), {"error": True})
        self.assertEqual(_parse_json_field(None, default_value={}), {})
        self.assertEqual(_parse_json_field({"already": "parsed"}), {"already": "parsed"})

    def test_helper_parse_key_value_string(self):
        self.assertEqual(_parse_key_value_string("VAT: 123; REG: 456"), {"vat": "123", "reg": "456"})
        self.assertEqual(_parse_key_value_string("Vat ID: XYZ; Reg Number: ABC"), {"vat_id": "XYZ", "reg_number": "ABC"})
        self.assertEqual(_parse_key_value_string("INVALID"), {})
        self.assertEqual(_parse_key_value_string(None), {})
        self.assertEqual(_parse_key_value_string("KEY_WITHOUT_VALUE;", default_value={"failed":1}), {"failed":1})


    def test_helper_format_address_parts(self):
        self.assertEqual(_format_address_parts("1 St", "City", "123", "Country"), "1 St, City, 123, Country")
        self.assertEqual(_format_address_parts(None, "City", "123", "Country"), "City, 123, Country")
        self.assertEqual(_format_address_parts("1 St", None, None, "Country"), "1 St, Country")
        self.assertEqual(_format_address_parts(None, None, None, None), "")

    def test_seller_bank_details_from_json(self):
        mock_seller_company = MockCompany(
            payment_info='{"bank_name": "JSON Bank", "account_number": "JSON123", "swift_bic": "JSONBIC", "bank_address": "JSON Address", "account_holder_name": "JSON Holder"}'
        )
        mock_document = MockDocument(company=mock_seller_company, client=MockClient())
        self.mock_doc_query.return_value = mock_document

        context = get_document_context_data(self.mock_db_session, 1)
        self.assertEqual(context["seller"]["bank_name"], "JSON Bank")
        self.assertEqual(context["seller"]["bank_account_number"], "JSON123")
        self.assertEqual(context["seller"]["bank_swift_bic"], "JSONBIC")
        self.assertEqual(context["seller"]["bank_address"], "JSON Address")
        self.assertEqual(context["seller"]["bank_account_holder_name"], "JSON Holder")

    def test_seller_bank_details_from_additional_context(self):
        mock_seller_company = MockCompany(payment_info="invalid json") # or None
        mock_document = MockDocument(company=mock_seller_company, client=MockClient())
        self.mock_doc_query.return_value = mock_document

        additional = {
            "seller_bank_name": "Context Bank", "seller_bank_account_number": "Context123",
            "seller_bank_swift_bic": "ContextBIC", "seller_bank_address": "Context Address"
        }
        context = get_document_context_data(self.mock_db_session, 1, additional_context=additional)
        self.assertEqual(context["seller"]["bank_name"], "Context Bank")
        self.assertEqual(context["seller"]["bank_account_number"], "Context123")
        self.assertEqual(context["seller"]["bank_swift_bic"], "ContextBIC")
        self.assertEqual(context["seller"]["bank_address"], "Context Address")

    def test_seller_vat_reg_from_json(self):
        mock_seller_company = MockCompany(other_info='{"vat_id": "JSONVAT", "registration_number": "JSONREG"}')
        mock_document = MockDocument(company=mock_seller_company, client=MockClient())
        self.mock_doc_query.return_value = mock_document

        context = get_document_context_data(self.mock_db_session, 1)
        self.assertEqual(context["seller"]["vat_id"], "JSONVAT")
        self.assertEqual(context["seller"]["registration_number"], "JSONREG")

    def test_seller_vat_reg_from_kv_string(self):
        mock_seller_company = MockCompany(other_info="VAT: KVVAT; REG: KVREG")
        mock_document = MockDocument(company=mock_seller_company, client=MockClient())
        self.mock_doc_query.return_value = mock_document

        context = get_document_context_data(self.mock_db_session, 1)
        self.assertEqual(context["seller"]["vat_id"], "KVVAT")
        self.assertEqual(context["seller"]["registration_number"], "KVREG")

    def test_seller_vat_reg_from_additional_context(self):
        mock_seller_company = MockCompany(other_info="invalid")
        mock_document = MockDocument(company=mock_seller_company, client=MockClient())
        self.mock_doc_query.return_value = mock_document
        additional = {"seller_vat_id": "ContextVAT", "seller_registration_number": "ContextREG"}

        context = get_document_context_data(self.mock_db_session, 1, additional_context=additional)
        self.assertEqual(context["seller"]["vat_id"], "ContextVAT")
        self.assertEqual(context["seller"]["registration_number"], "ContextREG")

    def test_seller_structured_address(self):
        mock_seller_company = MockCompany(address="1 Main St")
        mock_document = MockDocument(company=mock_seller_company, client=MockClient())
        self.mock_doc_query.return_value = mock_document
        additional = {"seller_city": "Sellerville", "seller_postal_code": "S1234", "seller_country": "Sellerland"}

        context = get_document_context_data(self.mock_db_session, 1, additional_context=additional)
        self.assertEqual(context["seller"]["address_line1"], "1 Main St")
        self.assertEqual(context["seller"]["city"], "Sellerville")
        self.assertEqual(context["seller"]["postal_code"], "S1234")
        self.assertEqual(context["seller"]["country"], "Sellerland")
        self.assertEqual(context["seller"]["city_zip_country"], "Sellerville, S1234, Sellerland")
        self.assertEqual(context["seller"]["address"], "1 Main St, Sellerville, S1234, Sellerland")

    def test_seller_address_fallback_to_raw(self):
        mock_seller_company = MockCompany(address="Complex Seller Address, Unit 10, Business Park")
        mock_document = MockDocument(company=mock_seller_company, client=MockClient())
        self.mock_doc_query.return_value = mock_document
        # No city/zip/country in additional_context
        context = get_document_context_data(self.mock_db_session, 1, additional_context={})
        self.assertEqual(context["seller"]["address_line1"], "Complex Seller Address, Unit 10, Business Park")
        self.assertEqual(context["seller"]["city"], "") # empty as not provided
        self.assertEqual(context["seller"]["address"], "Complex Seller Address, Unit 10, Business Park")


    def test_client_vat_reg_from_notes_json(self):
        mock_client = MockClient(notes='{"vat_id": "ClientVATJson", "registration_number": "ClientREGJson"}')
        mock_document = MockDocument(client=mock_client, company=MockCompany())
        self.mock_doc_query.return_value = mock_document

        context = get_document_context_data(self.mock_db_session, 1)
        self.assertEqual(context["client"]["vat_id"], "ClientVATJson")
        self.assertEqual(context["client"]["registration_number"], "ClientREGJson")

    def test_client_vat_reg_from_distributor_info_kv(self):
        mock_client = MockClient(notes="bad json", distributor_specific_info="VAT: ClientVATKV; REG: ClientREGKV")
        mock_document = MockDocument(client=mock_client, company=MockCompany())
        self.mock_doc_query.return_value = mock_document

        context = get_document_context_data(self.mock_db_session, 1)
        self.assertEqual(context["client"]["vat_id"], "ClientVATKV")
        self.assertEqual(context["client"]["registration_number"], "ClientREGKV")

    def test_client_vat_reg_from_additional_context(self):
        mock_client = MockClient(notes="bad", distributor_specific_info="bad")
        mock_document = MockDocument(client=mock_client, company=MockCompany())
        self.mock_doc_query.return_value = mock_document
        additional = {"client_vat_id": "ContextClientVAT", "client_registration_number": "ContextClientREG"}

        context = get_document_context_data(self.mock_db_session, 1, additional_context=additional)
        self.assertEqual(context["client"]["vat_id"], "ContextClientVAT")
        self.assertEqual(context["client"]["registration_number"], "ContextClientREG")

    def test_client_structured_address_from_primary_contact(self):
        mock_primary_contact = MockContact(
            first_name="Primary", last_name="Contact", email="pc@example.com", phone="111222",
            address_streetAddress="1 Contact St", address_city="Contactville",
            address_postalCode="C1234", address_country="Contactland"
        )
        mock_client_contact_assoc = MockClientContact(contact=mock_primary_contact, is_primary=True)
        # self.mock_db_session.query(ClientContact).join().filter().options().first.return_value = mock_client_contact_assoc
        self.mock_client_contact_query.return_value = mock_client_contact_assoc


        mock_client = MockClient(id=5) # Ensure client_id matches for query if that's how it's filtered
        mock_document = MockDocument(client=mock_client, company=MockCompany())
        self.mock_doc_query.return_value = mock_document

        context = get_document_context_data(self.mock_db_session, 1)

        self.assertEqual(context["contact_person"]["full_name"], "Primary Contact")
        self.assertEqual(context["client"]["address_line1"], "1 Contact St")
        self.assertEqual(context["client"]["city"], "Contactville")
        self.assertEqual(context["client"]["postal_code"], "C1234")
        self.assertEqual(context["client"]["country"], "Contactland")
        self.assertEqual(context["client"]["city_zip_country"], "Contactville, C1234, Contactland")
        self.assertEqual(context["client"]["address"], "1 Contact St, Contactville, C1234, Contactland")

    def test_client_structured_address_fallback_to_client_data(self):
        self.mock_client_contact_query.return_value = None # No primary contact found

        mock_client = MockClient(
            address_line1="123 Client Rd", city_name="Client City",
            postal_code="CL567", country_name="Client Nation",
            company_name="Client Corp"
        )
        mock_document = MockDocument(client=mock_client, company=MockCompany())
        self.mock_doc_query.return_value = mock_document

        context = get_document_context_data(self.mock_db_session, 1)
        self.assertEqual(context["client"]["address_line1"], "123 Client Rd")
        self.assertEqual(context["client"]["city"], "Client City")
        self.assertEqual(context["client"]["postal_code"], "CL567")
        self.assertEqual(context["client"]["country"], "Client Nation")
        self.assertEqual(context["client"]["address"], "123 Client Rd, Client City, CL567, Client Nation")

    def test_client_structured_address_fallback_to_additional_context(self):
        self.mock_client_contact_query.return_value = None # No primary contact
        mock_client = MockClient(company_name="Client Corp") # Client has no direct address fields
        mock_document = MockDocument(client=mock_client, company=MockCompany())
        self.mock_doc_query.return_value = mock_document

        additional = {
            "client_address_line1": "AddrContext Line1", "client_city": "AddrContext City",
            "client_postal_code": "AddrContext PC", "client_country": "AddrContext Country"
        }
        context = get_document_context_data(self.mock_db_session, 1, additional_context=additional)
        self.assertEqual(context["client"]["address_line1"], "AddrContext Line1")
        self.assertEqual(context["client"]["city"], "AddrContext City")
        # ... and so on for postal_code, country, full address

    def test_placeholder_mapping(self):
        mock_seller = MockCompany(name="MegaCorp Seller", address="1 Mega Way", vat_id="SELLERVAT1")
        mock_client = MockClient(company_name="MicroClient Buyer", address="1 Micro Ln", vat_id="CLIENTVAT1")
        mock_doc = MockDocument(title="TestDoc", company=mock_seller, client=mock_client)
        self.mock_doc_query.return_value = mock_doc

        context = get_document_context_data(self.mock_db_session, 1)
        placeholders = context["placeholders"]

        self.assertEqual(placeholders["SELLER_COMPANY_NAME"], "MegaCorp Seller")
        self.assertEqual(placeholders["SELLER_ADDRESS"], "1 Mega Way") # Assuming simple address for this test
        self.assertEqual(placeholders["SELLER_VAT_ID"], "N/A") # Because vat_id is not in other_info or additional_context

        self.assertEqual(placeholders["BUYER_COMPANY_NAME"], "MicroClient Buyer")
        self.assertEqual(placeholders["BUYER_ADDRESS"], "1 Micro Ln")
        self.assertEqual(placeholders["CLIENT_VAT_ID"], "N/A") # Because vat_id is not in notes or additional_context

    def test_custom_placeholders_from_document_version(self):
        mock_ph1 = MockPlaceholder(name="CustomInfo1")
        mock_doc_ph1 = MockDocumentPlaceholder(placeholder=mock_ph1, value="ValueForCustom1")
        mock_ph2_direct = MockDocumentPlaceholder(name="CustomInfo2", value="ValueForCustom2") # Test fallback name

        mock_version = MockDocumentVersion(placeholders=[mock_doc_ph1, mock_ph2_direct])
        mock_document = MockDocument(company=MockCompany(), client=MockClient(), versions=[mock_version])
        self.mock_doc_query.return_value = mock_document

        context = get_document_context_data(self.mock_db_session, 1)
        placeholders = context["placeholders"]

        self.assertEqual(placeholders["CUSTOMINFO1"], "ValueForCustom1") # Name from Placeholder obj
        self.assertEqual(placeholders["CUSTOMINFO2"], "ValueForCustom2") # Name directly from DocumentPlaceholder


if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
