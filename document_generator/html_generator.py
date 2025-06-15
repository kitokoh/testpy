import os
import logging

# Assuming context_builder is in the same package
from .context_builder import get_document_context

# Assuming html_to_pdf_util.py is in the parent directory of the document_generator package
# Adjust the import path if html_to_pdf_util.py is located elsewhere.
# For example, if it's a top-level module: from html_to_pdf_util import ...
# If it's a utility module within document_generator: from .html_to_pdf_util import ...
try:
    from ..html_to_pdf_util import render_html_template, convert_html_to_pdf
except ImportError:
    # Fallback if running directly or if structure is different, try direct import
    # This might happen if document_generator is not run as part of a package
    # or if html_to_pdf_util is in the same directory (though less likely for a util)
    try:
        import html_to_pdf_util
        render_html_template = html_to_pdf_util.render_html_template
        convert_html_to_pdf = html_to_pdf_util.convert_html_to_pdf
    except ImportError:
        logging.error(
            "Failed to import html_to_pdf_util. Ensure it's accessible. "
            "render_html_template and convert_html_to_pdf will not be available."
        )
        # Define dummy functions if import fails, to allow module to load for other purposes
        # but these will not work.
        def render_html_template(template_content, context):
            raise NotImplementedError("html_to_pdf_util.render_html_template not imported")

        def convert_html_to_pdf(html_content, base_url=None):
            raise NotImplementedError("html_to_pdf_util.convert_html_to_pdf not imported")


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_html_document(
    client_id: int,
    company_id: int,
    template_path: str,
    language_code: str,
    project_id: int = None,
    document_type: str = None, # Added to pass to get_document_context
    additional_context: dict = None,
    db_conn=None
) -> str | None:
    """
    Generates an HTML document by fetching context and rendering a template.

    Args:
        client_id: ID of the client.
        company_id: ID of the seller company.
        template_path: Absolute path to the HTML template file.
        language_code: Language code for translations.
        project_id: Optional ID of the project.
        document_type: Optional type of document (e.g. 'proforma_invoice') for context.
        additional_context: Optional dictionary for overrides or extra information
                              to be passed to get_document_context.
        db_conn: Optional existing database connection.

    Returns:
        The generated HTML content as a string, or None on failure.
    """
    if not os.path.exists(template_path):
        logger.error(f"HTML template not found at: {template_path}")
        return None

    if additional_context is None:
        additional_context = {}

    # Ensure document_type from additional_context is also passed to get_document_context
    # if not directly provided as a parameter.
    effective_document_type = document_type or additional_context.get('document_type')


    logger.info(f"Generating HTML document: client_id={client_id}, company_id={company_id}, "
                f"template='{os.path.basename(template_path)}', lang='{language_code}', project_id={project_id}")

    try:
        # 1. Fetch document context
        context = get_document_context(
            client_id=client_id,
            company_id=company_id,
            language_code=language_code,
            project_id=project_id,
            document_type=effective_document_type, # Pass it here
            additional_data=additional_context,
            db_conn=db_conn
        )
        if not context:
            logger.error("Failed to retrieve document context.")
            return None

        # 2. Read HTML template content
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        # 3. Render HTML template
        # Assuming render_html_template is a Jinja2 based renderer
        # It should take the template string and the context dictionary
        html_output = render_html_template(template_content, context)
        if not html_output:
            logger.error("HTML template rendering failed. render_html_template returned empty.")
            return None

        logger.info("HTML document generated successfully.")
        return html_output

    except FileNotFoundError:
        logger.error(f"HTML template file not found at: {template_path}")
        return None
    except Exception as e:
        logger.error(f"Error generating HTML document: {e}", exc_info=True)
        return None


def generate_html_and_convert_to_pdf(
    client_id: int,
    company_id: int,
    template_path: str,
    language_code: str,
    output_pdf_path: str,
    project_id: int = None,
    document_type: str = None, # Added to pass to generate_html_document
    additional_context: dict = None,
    db_conn=None
) -> bool:
    """
    Generates an HTML document, converts it to PDF, and saves it.

    Args:
        client_id: ID of the client.
        company_id: ID of the seller company.
        template_path: Absolute path to the HTML template file.
        language_code: Language code for translations.
        output_pdf_path: Path where the generated PDF should be saved.
        project_id: Optional ID of the project.
        document_type: Optional type of document (e.g. 'proforma_invoice') for context.
        additional_context: Optional dictionary for overrides or extra information.
        db_conn: Optional existing database connection.

    Returns:
        True on success, False on failure.
    """
    logger.info(f"Starting PDF generation: client_id={client_id}, company_id={company_id}, "
                f"template='{os.path.basename(template_path)}', output='{output_pdf_path}'")

    # 1. Generate HTML content
    html_content = generate_html_document(
        client_id=client_id,
        company_id=company_id,
        template_path=template_path,
        language_code=language_code,
        project_id=project_id,
        document_type=document_type,
        additional_context=additional_context,
        db_conn=db_conn
    )

    if not html_content:
        logger.error("HTML generation failed, cannot proceed to PDF conversion.")
        return False

    try:
        # 2. Determine base_url for PDF conversion (for relative assets)
        # The base_url should point to the directory containing the template,
        # so that relative paths to CSS, images, etc., in the HTML are resolved.
        base_url = os.path.dirname(template_path)
        # For WeasyPrint, local paths need to be in file:// URI form
        if not base_url.startswith('file://'):
             base_url = f"file://{base_url}/"


        # 3. Convert HTML to PDF
        # convert_html_to_pdf should take HTML string and base_url, return PDF bytes
        pdf_bytes = convert_html_to_pdf(html_content, base_url=base_url)

        if not pdf_bytes:
            logger.error("PDF conversion failed. convert_html_to_pdf returned empty.")
            return False

        # 4. Save PDF to output_pdf_path
        output_dir = os.path.dirname(output_pdf_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Created output directory: {output_dir}")

        with open(output_pdf_path, 'wb') as f:
            f.write(pdf_bytes)

        logger.info(f"PDF successfully generated and saved to: {output_pdf_path}")
        return True

    except Exception as e:
        logger.error(f"Error during PDF generation or saving: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    logger.info("Starting HTML generator test run...")

    # This test requires:
    # 1. `context_builder.py` to be functional (or mocked).
    # 2. `html_to_pdf_util.py` with `render_html_template` and `convert_html_to_pdf` (or mocked).
    # 3. A sample HTML template file.
    # 4. A running database instance accessible by `get_document_context` or full mocks.

    # Create a dummy template file for testing
    sample_template_dir = "temp_test_templates"
    os.makedirs(sample_template_dir, exist_ok=True)
    sample_template_path = os.path.join(sample_template_dir, "test_template.html")

    with open(sample_template_path, "w", encoding="utf-8") as f:
        f.write("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Document</title>
            <style> body { font-family: sans-serif; } </style>
        </head>
        <body>
            <h1>Hello, {{ client.name }}!</h1>
            <p>This is a test document for client ID: {{ client.id }}.</p>
            <p>Seller: {{ seller.name }}</p>
            <p>Date: {{ doc.current_date }}</p>
            <p>Project: {{ project.name|default('N/A') }}</p>
            <p>Currency: {{ doc.currency_symbol }}</p>
            <h2>Products:</h2>
            <ul>
            {% for product in products %}
                <li>{{ product.name }} ({{ product.quantity }} x {{ product.unit_price }}) = {{ product.total_price }}</li>
            {% else %}
                <li>No products listed.</li>
            {% endfor %}
            </ul>
            <p><strong>Total: {{ doc.grand_total_amount }}</strong></p>
            <p><em>Notes: {{ doc.client_specific_notes|join(', ') }}</em></p>
        </body>
        </html>
        """)

    # --- MOCKING ---
    # For a standalone test without a live DB or full utils, you'd mock:
    # - get_document_context
    # - render_html_template
    # - convert_html_to_pdf

    # Example of how you might mock get_document_context if it's imported directly
    original_get_document_context = get_document_context # Save original
    def mock_get_document_context(client_id, company_id, language_code, project_id=None, document_type=None, additional_data=None, db_conn=None):
        logger.info("[MOCK] get_document_context called")
        return {
            "doc": {
                "current_date": "2023-01-01", "current_year": 2023, "currency_symbol": "$",
                "vat_rate": 0.1, "discount_rate": 0.0,
                "subtotal_amount": "$100.00", "discount_amount": "$0.00",
                "vat_amount": "$10.00", "grand_total_amount": "$110.00",
                "client_specific_notes": ["Test note 1", "Test note 2"]
            },
            "client": {"id": client_id, "name": "Mock Client", "company_name": "Mock Client Inc."},
            "seller": {"id": company_id, "name": "Mock Seller Co."},
            "project": {"id": project_id, "name": "Mock Project"},
            "products": [
                {"name": "Product A", "quantity": 2, "unit_price": "$25.00", "total_price": "$50.00"},
                {"name": "Product B", "quantity": 1, "unit_price": "$50.00", "total_price": "$50.00"},
            ],
            "lang": {"code": language_code},
            "placeholders": {}, "additional": additional_data or {}
        }
    # Apply the mock
    # Note: This type of direct patching is simple but has limitations.
    # For more robust testing, consider using unittest.mock.
    # To make this work, we need to ensure that html_generator.get_document_context is this mock.
    # If html_generator.py is `main`, this won't work as easily as it seems.
    # The import `from .context_builder import get_document_context` means we'd need to patch
    # `document_generator.context_builder.get_document_context`.
    # For simplicity in this example, we'll assume direct import or that the test runner handles patching.

    # To properly mock for this test, we'd need to assign to the imported name:
    # For example:
    # import document_generator.context_builder
    # document_generator.context_builder.get_document_context = mock_get_document_context
    # OR if the import was `from . import context_builder`:
    # context_builder.get_document_context = mock_get_document_context

    # As a simple workaround for this script, if html_to_pdf_util is also mocked,
    # we can pass the mock context directly if needed.
    # For now, let's assume get_document_context works or is mocked externally.

    # --- Test generate_html_document ---
    logger.info(f"\n--- Testing generate_html_document (using mock context if direct patch applied) ---")
    # To ensure the mock is used if this script is run directly and imports are tricky:
    # One way is to temporarily re-assign it in this module's scope if it's imported as `get_document_context`
    # For this example, let's assume the real one is called and might fail if DB not set up.
    # To use the mock, you would need to ensure the `get_document_context` used by `generate_html_document`
    # is the mocked version.

    # For demonstration, let's assume we can pass a 'mock_context' via additional_context
    # and modify generate_html_document to use it if present (not ideal for production code).
    # Or, rely on external test setup to patch `get_document_context`.

    # Assuming some form of `get_document_context` mocking is in place or it can partially run:
    html_output = generate_html_document(
        client_id=100,
        company_id=200,
        template_path=sample_template_path,
        language_code='en',
        project_id=300,
        document_type='test_document',
        additional_context={"use_mock_context": True} # Imaginary flag for testing
    )

    if html_output:
        logger.info("generate_html_document returned HTML (first 200 chars):")
        logger.info(html_output[:200] + "...")
        # Optionally save it
        with open("test_output.html", "w", encoding="utf-8") as f:
            f.write(html_output)
        logger.info("Saved test_output.html")
    else:
        logger.error("generate_html_document failed to return HTML.")

    # --- Test generate_html_and_convert_to_pdf ---
    logger.info(f"\n--- Testing generate_html_and_convert_to_pdf ---")
    output_pdf_file = "test_output.pdf"

    # Mock `convert_html_to_pdf` from `html_to_pdf_util` for this test to avoid actual PDF generation
    try:
        # Assuming html_to_pdf_util was imported and we can patch its functions
        # This is a bit tricky due to the try-except import logic earlier.
        # If `convert_html_to_pdf` is already a global in this module:
        global convert_html_to_pdf
        original_convert_html_to_pdf = convert_html_to_pdf # Save original
        def mock_convert_html_to_pdf(html_content, base_url=None):
            logger.info(f"[MOCK] convert_html_to_pdf called with base_url: {base_url}")
            logger.info(f"[MOCK] HTML content (first 100 chars): {html_content[:100]}")
            return b"%PDF-1.4-mock-content" # Return dummy PDF bytes
        convert_html_to_pdf = mock_convert_html_to_pdf
    except NameError: # convert_html_to_pdf might not be defined if initial import failed
        logger.warning("Could not mock convert_html_to_pdf as it was not imported.")


    pdf_success = generate_html_and_convert_to_pdf(
        client_id=101,
        company_id=201,
        template_path=sample_template_path,
        language_code='fr',
        output_pdf_path=output_pdf_file,
        project_id=301,
        document_type='test_document_pdf',
        additional_context={"another_param": "value"}
    )

    if pdf_success:
        logger.info(f"generate_html_and_convert_to_pdf succeeded (mocked PDF). Check for {output_pdf_file}")
        if os.path.exists(output_pdf_file):
             logger.info(f"Mock PDF file size: {os.path.getsize(output_pdf_file)} bytes")
    else:
        logger.error("generate_html_and_convert_to_pdf failed.")

    # --- Cleanup ---
    # Restore mocks if they were applied globally and tests are over
    # For example:
    # get_document_context = original_get_document_context (if patched directly)
    # convert_html_to_pdf = original_convert_html_to_pdf (if patched directly)

    # Clean up dummy files
    # os.remove(sample_template_path)
    # os.rmdir(sample_template_dir)
    # if os.path.exists("test_output.html"): os.remove("test_output.html")
    # if os.path.exists(output_pdf_file): os.remove(output_pdf_file) # If mock creates the file

    logger.info("HTML generator test run finished.")
    # Note: The mocking strategy here is simplified for a single-file script context.
    # In a larger project, use `unittest.mock.patch` for cleaner and more reliable mocking.
    # e.g. @patch('document_generator.context_builder.get_document_context')
    #      @patch('document_generator.html_generator.convert_html_to_pdf')
    #      def test_my_function(mock_convert_pdf, mock_get_ctx): ...

```
