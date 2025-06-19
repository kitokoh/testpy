import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import os
import sys
import sqlite3 # For TestGetNextInvoiceNumber setUp

# Adjust path to import from the app's root directory
APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(APP_ROOT)

# For get_next_invoice_number
from db.cruds.application_settings_crud import get_next_invoice_number, set_setting, get_setting
from db.init_schema import initialize_database
import db.db_config as db_config

# For get_final_invoice_context_data
from proforma_invoice_utils import get_final_invoice_context_data
# Mocked dependencies from proforma_invoice_utils's perspective
# These are the names as they would be accessed *within* proforma_invoice_utils.py
# Based on its try-except import block, they are defined in its global scope.
# So, we patch 'proforma_invoice_utils.get_company_by_id', etc.

class TestGetNextInvoiceNumber(unittest.TestCase):
    original_db_path = None

    @classmethod
    def setUpClass(cls):
        cls.original_db_path = db_config.DATABASE_PATH
        db_config.DATABASE_PATH = ":memory:"
        initialize_database()

    @classmethod
    def tearDownClass(cls):
        if cls.original_db_path:
            db_config.DATABASE_PATH = cls.original_db_path

    def setUp(self):
        # Clear relevant app settings before each test
        conn = sqlite3.connect(db_config.DATABASE_PATH)
        cursor = conn.cursor()
        current_year = datetime.now().year
        setting_key_current = f"last_invoice_sequence_{current_year}"
        setting_key_last_year = f"last_invoice_sequence_{current_year - 1}"

        cursor.execute("DELETE FROM ApplicationSettings WHERE setting_key = ?", (setting_key_current,))
        cursor.execute("DELETE FROM ApplicationSettings WHERE setting_key = ?", (setting_key_last_year,))
        conn.commit()
        conn.close()

    def test_first_invoice_of_year(self):
        current_year = datetime.now().year
        expected_inv_num = f"INV-{current_year}-00001"
        self.assertEqual(get_next_invoice_number(), expected_inv_num)
        self.assertEqual(get_setting(f"last_invoice_sequence_{current_year}"), "1")

    def test_sequential_invoice_numbers(self):
        current_year = datetime.now().year
        first_inv_num = get_next_invoice_number() # INV-YYYY-00001
        self.assertEqual(first_inv_num, f"INV-{current_year}-00001")

        expected_inv_num_2 = f"INV-{current_year}-00002"
        self.assertEqual(get_next_invoice_number(), expected_inv_num_2)
        self.assertEqual(get_setting(f"last_invoice_sequence_{current_year}"), "2")

    def test_invoice_number_resets_for_new_year(self):
        # Mock current year to be last year
        # We need to patch datetime.now() where it's called in get_next_invoice_number
        # which is directly 'from datetime import datetime'.

        # Setup: clear settings for both years to ensure clean state
        conn = sqlite3.connect(db_config.DATABASE_PATH)
        cursor = conn.cursor()
        current_year_val = datetime.now().year
        last_year_val = current_year_val -1
        cursor.execute("DELETE FROM ApplicationSettings WHERE setting_key = ?", (f"last_invoice_sequence_{current_year_val}",))
        cursor.execute("DELETE FROM ApplicationSettings WHERE setting_key = ?", (f"last_invoice_sequence_{last_year_val}",))
        conn.commit()
        conn.close()

        with patch('db.cruds.application_settings_crud.datetime') as mock_datetime_crud:
            # Configure the mock for the first call (last year)
            mock_now_last_year = MagicMock()
            mock_now_last_year.year = last_year_val
            mock_datetime_crud.now.return_value = mock_now_last_year

            expected_last_year_inv = f"INV-{last_year_val}-00001"
            self.assertEqual(get_next_invoice_number(), expected_last_year_inv)
            self.assertEqual(get_setting(f"last_invoice_sequence_{last_year_val}"), "1")

            # Configure the mock for the second call (current year)
            mock_now_current_year = MagicMock()
            mock_now_current_year.year = current_year_val
            mock_datetime_crud.now.return_value = mock_now_current_year

            expected_this_year_inv = f"INV-{current_year_val}-00001"
            self.assertEqual(get_next_invoice_number(), expected_this_year_inv)
            self.assertEqual(get_setting(f"last_invoice_sequence_{current_year_val}"), "1")

            # Verify last year's setting is untouched
            self.assertEqual(get_setting(f"last_invoice_sequence_{last_year_val}"), "1")


class TestGetFinalInvoiceContextData(unittest.TestCase):

    # Patching the names as they are defined/imported in proforma_invoice_utils.py
    @patch('proforma_invoice_utils.get_next_invoice_number')
    @patch('proforma_invoice_utils.get_company_by_id')
    @patch('proforma_invoice_utils.get_client_by_id')
    @patch('proforma_invoice_utils.get_project_by_id')
    @patch('proforma_invoice_utils._get_batch_products_and_equivalents')
    @patch('proforma_invoice_utils.get_contacts_for_client') # Used for client representative
    @patch('proforma_invoice_utils.get_personnel_for_company') # Used for seller representative
    @patch('proforma_invoice_utils.get_country_by_id') # Used for client address
    @patch('proforma_invoice_utils.get_city_by_id') # Used for client address
    @patch('proforma_invoice_utils.get_db_session') # Mock session creation
    def test_basic_context_generation(self, mock_get_session, mock_get_city, mock_get_country, mock_get_personnel, mock_get_contacts, mock_batch_prod, mock_get_proj, mock_get_client, mock_get_comp, mock_get_next_inv_num):

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_get_next_inv_num.return_value = "INV-2024-00777"

        mock_company_data = {
            'id': 'comp1', 'name': 'Test Seller Inc.', 'email': 'seller@test.com',
            'phone': '123-SELL', 'website': 'seller.com', 'address': '1 Seller St, Sellville',
            'payment_info': json.dumps({'bank_name': 'World Bank', 'iban': 'SELLERIBAN', 'swift_bic': 'SELLSWIFT', 'account_holder_name': 'Test Seller Inc.'}),
            'other_info': json.dumps({'vat_id': 'SELLER_VAT_ID', 'city': 'Sellville', 'postal_code': 'S1234', 'country': 'Sellerland'}),
            'logo_filename': 'seller_logo.png'
        }
        mock_get_comp.return_value = MagicMock(**mock_company_data)

        mock_client_data = {
            'id': 'client1', 'client_name': 'Client Rep Name', 'company_name': 'Test Client LLC',
            'email': 'client_contact@test.com', 'phone': '456-CLIENT',
            'address_line1': '2 Client Ave', # Assuming this field might exist on client directly
            'country_id': 1, 'city_id': 1, 'notes': '{}',
            'distributor_specific_info': json.dumps({'vat_id': 'CLIENT_VAT_ID'})
        }
        mock_get_client.return_value = MagicMock(**mock_client_data)

        mock_get_country.return_value = {'name': 'ClientCountry'}
        mock_get_city.return_value = {'name': 'ClientCity'}

        # Mock primary contact for client
        mock_primary_contact_data = {
            'first_name': 'ContactFirst', 'last_name': 'ContactLast', 'email': 'primary@client.com',
            'phone': '789-CONTACT', 'address_streetAddress': '2 Client Ave',
            'address_city': 'ClientCity', 'address_postalCode': 'C5678', 'address_country': 'ClientCountry'
        }
        mock_get_contacts.return_value = [MagicMock(**mock_primary_contact_data)]
        mock_get_personnel.return_value = [] # No seller personnel for this basic test

        mock_get_proj.return_value = MagicMock(id='proj1', name='Test Project X', project_identifier='PRJX001')

        mock_batch_prod.return_value = {
            101: {"id": 101, "original_name": "Super Widget", "original_description": "High quality widget.", "base_unit_price": 100.0, "unit_of_measure": "pcs", "original_language_code": "en"},
            102: {"id": 102, "original_name": "Mega Gadget", "original_description": "Useful gadget.", "base_unit_price": 50.0, "unit_of_measure": "pcs", "original_language_code": "en"}
        }

        line_items_input = [
            {'product_id': 101, 'quantity': 2, 'unit_price': 100.0},
            {'product_id': 102, 'quantity': 1, 'unit_price': 45.0}
        ]
        additional_context = {
            'line_items': line_items_input,
            'tax_rate_percentage': 10.0,
            'tax_label': 'GST',
            'final_payment_terms': 'Net 15',
            'currency_symbol': '$', # For formatting
            'seller_city': 'Sellville', # Passed to ensure seller address is complete
            'seller_postal_code': 'S1234',
            'seller_country': 'Sellerland'
        }

        context = get_final_invoice_context_data(
            client_id='client1', company_id='comp1', target_language_code='en',
            project_id = 'proj1',
            additional_context=additional_context
        )

        self.assertIsNotNone(context)
        doc = context['doc']
        self.assertEqual(doc['invoice_number'], "INV-2024-00777")
        self.assertEqual(doc['invoice_title'], "INVOICE")
        self.assertEqual(context['client']['company_name'], 'Test Client LLC')
        self.assertEqual(context['client']['representative_name'], 'ContactFirst ContactLast')
        self.assertEqual(context['seller']['company_name'], 'Test Seller Inc.')
        self.assertEqual(context['project']['name'], 'Test Project X')

        # Calculations:
        # Item 1: 2 * 100.0 = 200.0
        # Item 2: 1 * 45.0 = 45.0
        # Subtotal = 245.0
        # Discount = 0 (default)
        # Amount after discount = 245.0
        # Tax (10% of 245.0) = 24.5
        # Grand Total = 245.0 + 24.5 = 269.5
        self.assertAlmostEqual(doc['subtotal_amount_raw'], 245.0)
        self.assertAlmostEqual(doc['discount_amount_raw'], 0.0) # Default discount is 0
        self.assertAlmostEqual(doc['tax_amount_raw'], 24.5)
        self.assertAlmostEqual(doc['grand_total_amount_raw'], 269.5)

        self.assertEqual(doc['tax_label'], 'GST')
        self.assertEqual(doc['tax_rate_percentage'], 10.0)
        self.assertEqual(doc['payment_terms'], 'Net 15')
        self.assertEqual(doc['currency_symbol'], '$')

        self.assertEqual(len(context['products']), 2)
        self.assertEqual(context['products'][0]['name'], "Super Widget")
        self.assertEqual(context['products'][1]['total_price_raw'], 45.0)

        # Check placeholders
        self.assertEqual(context['placeholders']['doc.invoice_number'], "INV-2024-00777")
        self.assertEqual(context['placeholders']['seller.vat_id'], "SELLER_VAT_ID")
        self.assertEqual(context['placeholders']['client.vat_id'], "CLIENT_VAT_ID")
        self.assertEqual(context['placeholders']['seller.bank_iban'], "SELLERIBAN")


if __name__ == '__main__':
    unittest.main()

```
