import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import logging
from datetime import datetime

# Adjust sys.path to ensure the 'invoice_generation_logic' module can be found.
# This assumes 'invoice_generation_logic.py' is in the project root directory
# and the 'tests' directory is a subdirectory of the project root.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from invoice_generation_logic import generate_final_invoice_pdf
from html_to_pdf_util import WeasyPrintError # Assuming this is defined in html_to_pdf_util

# Disable logging for tests to keep output clean, unless debugging
logging.disable(logging.CRITICAL)

class TestGenerateFinalInvoicePdf(unittest.TestCase):

    @patch('invoice_generation_logic.convert_html_to_pdf')
    @patch('invoice_generation_logic.render_html_template')
    @patch('invoice_generation_logic.get_final_invoice_context_data')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    @patch('invoice_generation_logic.TEMPLATES_DIR', "/fake/templates_root_dir") # Patch module-level constant
    def test_successful_generation(self, mock_path_exists, mock_file_open, mock_get_context, mock_render_html, mock_convert_pdf):
        # --- Setup Mocks ---
        mock_path_exists.return_value = True # Assume template file exists
        mock_file_open.return_value.read.return_value = "<html><body>Invoice: {{ doc.invoice_number }} for {{ client.company_name }}</body></html>"

        mock_context_data = {
            "doc": {
                "invoice_number": "INV-2024-TEST001",
                # other doc fields...
            },
            "client": {
                "company_name": "ClientX Corp",
                "representative_name": "Mr. X", # For filename fallback if company_name is N/A
                # other client fields...
            },
            # other top-level context keys like 'seller', 'products' etc.
        }
        mock_get_context.return_value = mock_context_data

        rendered_html_content = f"<html><body>Invoice: {mock_context_data['doc']['invoice_number']} for {mock_context_data['client']['company_name']}</body></html>"
        mock_render_html.return_value = rendered_html_content

        dummy_pdf_bytes = b"%PDF-1.4 dummy content..."
        mock_convert_pdf.return_value = dummy_pdf_bytes

        # --- Call the function ---
        pdf_bytes, filename, context_used = generate_final_invoice_pdf(
            client_id='client_id_123',
            company_id='company_id_abc',
            target_language_code='en',
            line_items=[{'product_id': 1, 'quantity': 1, 'unit_price': 100, 'name': 'Test Item'}], # name for context
            additional_context_overrides={'issue_date': '2024-01-01'}
        )

        # --- Assertions ---
        self.assertEqual(pdf_bytes, dummy_pdf_bytes)
        self.assertIsNotNone(filename)
        self.assertIn("INV-2024-TEST001", filename)
        self.assertIn("ClientX_Corp", filename) # Check for cleaned client name
        current_date_str = datetime.now().strftime("%Y%m%d")
        self.assertIn(current_date_str, filename)
        self.assertEqual(context_used, mock_context_data)

        # Assert that dependent functions were called correctly
        expected_template_path = os.path.join("/fake/templates_root_dir", "en", "final_invoice_template.html")

        mock_get_context.assert_called_once_with(
            client_id='client_id_123',
            company_id='company_id_abc',
            target_language_code='en',
            project_id=None, # Default
            additional_context={
                'line_items': [{'product_id': 1, 'quantity': 1, 'unit_price': 100, 'name': 'Test Item'}],
                'issue_date': '2024-01-01'
            }
        )
        mock_path_exists.assert_called_with(expected_template_path)
        mock_file_open.assert_called_with(expected_template_path, 'r', encoding='utf-8')
        mock_render_html.assert_called_with("<html><body>Invoice: {{ doc.invoice_number }} for {{ client.company_name }}</body></html>", mock_context_data)
        mock_convert_pdf.assert_called_with(rendered_html_content, base_url=os.path.dirname(expected_template_path))


    @patch('invoice_generation_logic.get_final_invoice_context_data', return_value=None)
    def test_context_generation_fails(self, mock_get_context):
        pdf_bytes, filename, context_used = generate_final_invoice_pdf(
            client_id='c1', company_id='comp1', target_language_code='en', line_items=[]
        )
        self.assertIsNone(pdf_bytes)
        self.assertIsNone(filename)
        self.assertIsNone(context_used) # Context generation itself failed
        mock_get_context.assert_called_once()

    @patch('invoice_generation_logic.TEMPLATES_DIR', "/fake/templates")
    @patch('os.path.exists', return_value=False) # Simulate template not found
    @patch('invoice_generation_logic.get_final_invoice_context_data')
    def test_template_not_found(self, mock_get_context, mock_path_exists):
        mock_get_context.return_value = {"doc": {}, "client": {}} # Minimal valid context

        pdf_bytes, filename, context_used = generate_final_invoice_pdf(
            client_id='c1', company_id='comp1', target_language_code='fr', line_items=[]
        )
        self.assertIsNone(pdf_bytes)
        self.assertIsNone(filename)
        self.assertEqual(context_used, {"doc": {}, "client": {}}) # Context was generated

        expected_template_path = os.path.join("/fake/templates", "fr", "final_invoice_template.html")
        mock_path_exists.assert_called_with(expected_template_path)

    @patch('invoice_generation_logic.TEMPLATES_DIR', "/fake/templates")
    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data="dummy template data")
    @patch('invoice_generation_logic.render_html_template')
    @patch('invoice_generation_logic.convert_html_to_pdf', side_effect=WeasyPrintError("PDF Conversion Error From Test"))
    @patch('invoice_generation_logic.get_final_invoice_context_data')
    def test_pdf_conversion_fails(self, mock_get_context, mock_convert_pdf, mock_render_html, mock_file_open, mock_path_exists):
        mock_get_context.return_value = {"doc": {}, "client": {}} # Minimal context
        mock_render_html.return_value = "dummy rendered html"

        pdf_bytes, filename, context_used = generate_final_invoice_pdf(
            client_id='c1', company_id='comp1', target_language_code='en', line_items=[]
        )
        self.assertIsNone(pdf_bytes)
        self.assertIsNone(filename)
        self.assertEqual(context_used, {"doc": {}, "client": {}}) # Context and HTML were processed

        expected_template_path = os.path.join("/fake/templates", "en", "final_invoice_template.html")
        mock_path_exists.assert_called_with(expected_template_path)
        mock_file_open.assert_called_with(expected_template_path, 'r', encoding='utf-8')
        mock_render_html.assert_called_with("dummy template data", {"doc": {}, "client": {}})
        mock_convert_pdf.assert_called_with("dummy rendered html", base_url=os.path.dirname(expected_template_path))

if __name__ == '__main__':
    unittest.main()
```
