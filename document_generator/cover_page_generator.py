import os
import logging
import datetime
import io

# Assuming context_builder is in the same package
from .context_builder import get_document_context

# Assuming pagedegrde.py is in the parent directory of document_generator package
# Adjust import path if pagedegrde.py is located elsewhere.
try:
    from ..pagedegrde import generate_cover_page_logic, APP_CONFIG as PAGEDEGARDE_APP_CONFIG, _register_fonts
    # If _register_fonts needs APP_ROOT_DIR and it's defined in pagedegrde:
    # from ..pagedegrde import APP_ROOT_DIR as PAGEDEGARDE_APP_ROOT_DIR
    PAGEDEGARDE_APP_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Define if not from pagedegrde
except ImportError:
    logging.warning(
        "Failed to import 'pagedegrde' module from parent directory. "
        "Cover page generation will likely fail. "
        "Attempting direct import for standalone testing or alternative structures."
    )
    try:
        # Fallback for direct execution or if pagedegrde is in PYTHONPATH
        import pagedegrde
        generate_cover_page_logic = pagedegrde.generate_cover_page_logic
        PAGEDEGARDE_APP_CONFIG = pagedegrde.APP_CONFIG
        _register_fonts = pagedegrde._register_fonts
        # PAGEDEGARDE_APP_ROOT_DIR = pagedegrde.APP_ROOT_DIR
        PAGEDEGARDE_APP_ROOT_DIR = os.getcwd() # Define if not from pagedegrde
    except ImportError as e:
        logging.error(f"Failed to import 'pagedegrde' directly: {e}. Cover page functionality is unavailable.")
        # Define dummy functions/vars if import fails, to allow module to load
        def generate_cover_page_logic(config_dict):
            raise NotImplementedError("pagedegrde.generate_cover_page_logic not imported")
        PAGEDEGARDE_APP_CONFIG = {}
        def _register_fonts(app_root_dir=None):
            logging.info("pagedegrde._register_fonts not imported - skipping font registration.")
        PAGEDEGARDE_APP_ROOT_DIR = os.getcwd()


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# It's good practice for generate_cover_page_logic to handle its own font registration if possible.
# If not, call it once, e.g., when this module is loaded or before the first PDF generation.
try:
    # Pass PAGEDEGARDE_APP_ROOT_DIR if _register_fonts expects it and it's defined.
    # Some ReportLab setups might need a path to find fonts.
    if callable(_register_fonts):
        logger.info(f"Registering fonts for pagedegrde using APP_ROOT_DIR: {PAGEDEGARDE_APP_ROOT_DIR}")
        _register_fonts(PAGEDEGARDE_APP_ROOT_DIR)
except Exception as e:
    logger.error(f"Error during initial font registration for pagedegrde: {e}", exc_info=True)


def generate_cover_page_pdf(
    client_id: int,
    company_id: int, # Seller company ID
    language_code: str,
    output_pdf_path: str,
    project_id: int = None,
    document_type_for_context: str = None, # e.g., "Proforma Invoice", "Technical Proposal"
    additional_context_overrides: dict = None, # For overriding specific config_dict fields
    db_conn=None
) -> bool:
    """
    Generates a PDF cover page using ReportLab logic via pagedegrde module.

    Args:
        client_id: ID of the client.
        company_id: ID of the seller company.
        language_code: Language code.
        output_pdf_path: Path to save the generated PDF.
        project_id: Optional ID of the project.
        document_type_for_context: Optional type of document for context fetching.
        additional_context_overrides: Optional dict to override/add to pagedegrde config.
        db_conn: Optional existing database connection.

    Returns:
        True on success, False on failure.
    """
    if additional_context_overrides is None:
        additional_context_overrides = {}

    logger.info(f"Generating PDF cover page: client_id={client_id}, company_id={company_id}, "
                f"output='{os.path.basename(output_pdf_path)}', lang='{language_code}'")

    try:
        # 1. Fetch document context
        # Pass document_type for context if provided, otherwise it's None
        context = get_document_context(
            client_id=client_id,
            company_id=company_id,
            language_code=language_code,
            project_id=project_id,
            document_type=document_type_for_context,
            additional_data=additional_context_overrides.get("context_builder_data", {}), # For data to context_builder
            db_conn=db_conn
        )
        if not context:
            logger.error("Failed to retrieve document context for cover page.")
            return False

        # 2. Construct config_dict for pagedegrde.generate_cover_page_logic
        # Start with defaults from pagedegrde.APP_CONFIG or define local defaults
        config_dict = {
            'output_path': output_pdf_path, # pagedegrde might use this or return bytes
            'title': "Document Title",
            'subtitle': "", # e.g., Project Name
            'author': "",   # e.g., Client Company Name or Seller Name
            'institution': "", # e.g., Seller Company Name
            'department': "", # Could be derived or fixed
            'version': "1.0",
            'date': datetime.date.today().strftime("%d/%m/%Y"),
            'logo_data': None, # Bytes of the logo
            'logo_width': None, # Optional: Inches, e.g., 1.5*inch
            'logo_height': None, # Optional: Inches
            'template_style': 'Moderne', # Default style from pagedegrde
            'language': language_code,
            # Add any other fields expected by pagedegrde.generate_cover_page_logic
        }

        # Merge defaults from pagedegrde.APP_CONFIG if they exist for cover pages
        if PAGEDEGARDE_APP_CONFIG and 'cover_page_defaults' in PAGEDEGARDE_APP_CONFIG:
            config_dict.update(PAGEDEGARDE_APP_CONFIG['cover_page_defaults'])

        # Map from context to config_dict
        # Title:
        if context.get("project") and context["project"].get("name"):
            default_title = f"Report for Project: {context['project']['name']}"
        elif document_type_for_context:
            default_title = str(document_type_for_context)
        else:
            default_title = "Project Document"
        config_dict['title'] = context.get("doc", {}).get("document_title", default_title) # If you add 'document_title' to context

        # Subtitle:
        if context.get("project") and context["project"].get("identifier"):
             config_dict['subtitle'] = f"Ref: {context['project']['identifier']}"
        elif context.get("client") and context["client"].get("company_name"):
            config_dict['subtitle'] = context["client"]["company_name"]

        # Author:
        if context.get("client") and context["client"].get("company_name"):
            config_dict['author'] = context["client"]["company_name"]
        elif context.get("client") and context["client"].get("name"):
            config_dict['author'] = context["client"]["name"]

        # Institution (typically the seller/provider):
        if context.get("seller") and context["seller"].get("name"):
            config_dict['institution'] = context["seller"]["name"]

        # Date:
        config_dict['date'] = context.get("doc", {}).get("current_date_formatted", config_dict['date']) # if specific format needed

        # Logo data:
        logo_data_bytes = None
        seller_logo_path = context.get("seller", {}).get("logo_path") # This should be file:///path from context_builder

        if seller_logo_path and seller_logo_path.startswith("file:///"):
            actual_logo_path = seller_logo_path[len("file:///"):]
            if os.path.exists(actual_logo_path):
                try:
                    with open(actual_logo_path, 'rb') as f:
                        logo_data_bytes = f.read()
                    logger.info(f"Loaded logo from seller context: {actual_logo_path}")
                except Exception as e:
                    logger.error(f"Error reading logo file {actual_logo_path}: {e}")
            else:
                logger.warning(f"Logo path from seller context does not exist: {actual_logo_path}")

        config_dict['logo_data'] = logo_data_bytes

        # Apply overrides from additional_context_overrides last
        # These are direct overrides for the pagedegrde config_dict
        if additional_context_overrides:
            # Ensure 'context_builder_data' (if used) is not directly merged into config_dict
            pagedegrde_overrides = {k: v for k, v in additional_context_overrides.items() if k != "context_builder_data"}
            config_dict.update(pagedegrde_overrides)

        # Ensure output_pdf_path is in the config_dict for pagedegrde if it saves the file directly
        config_dict['output_path'] = output_pdf_path # pagedegrde might use this or return bytes

        # 3. Call pagedegrde.generate_cover_page_logic
        # This function is expected to generate the PDF and either save it to
        # config_dict['output_path'] or return the PDF bytes.
        # For this example, let's assume it saves the file if output_path is given,
        # or returns bytes if output_path is None/not present.

        logger.debug(f"Calling generate_cover_page_logic with config: {config_dict}")
        pdf_output = generate_cover_page_logic(config_dict) # This might return bytes or status

        # 4. Save PDF (if generate_cover_page_logic returns bytes)
        # If generate_cover_page_logic saves the file itself based on 'output_path' in config_dict,
        # then this step might not be needed or pdf_output might be a success boolean.

        saved_successfully = False
        if isinstance(pdf_output, bytes):
            output_dir = os.path.dirname(output_pdf_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            with open(output_pdf_path, 'wb') as f:
                f.write(pdf_output)
            logger.info(f"PDF cover page generated and saved to: {output_pdf_path}")
            saved_successfully = True
        elif isinstance(pdf_output, bool) and pdf_output: # Assuming it returns True if saved internally
            logger.info(f"PDF cover page generated and saved by pagedegrde to: {output_pdf_path}")
            saved_successfully = True
        elif os.path.exists(output_pdf_path): # Check if pagedegrde saved it
             logger.info(f"PDF cover page seems to be generated by pagedegrde at: {output_pdf_path}")
             saved_successfully = True
        else:
            logger.error("generate_cover_page_logic did not return PDF bytes nor indicate success.")
            return False

        return saved_successfully

    except FileNotFoundError as e: # e.g. if logo file specified in overrides is not found
        logger.error(f"File not found during cover page generation: {e}", exc_info=True)
        return False
    except NotImplementedError: # If pagedegrde itself is not implemented
        logger.error("Cover page generation failed: pagedegrde functionality is not available.", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Error generating PDF cover page: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    logger.info("Starting Cover Page generator test run...")

    # This test requires:
    # 1. `context_builder.py` to be functional (or mocked).
    # 2. `pagedegrde.py` with `generate_cover_page_logic` (or mocked).
    # 3. Potentially a dummy logo file if testing logo loading.

    sample_output_dir = "temp_cover_page_test_files"
    os.makedirs(sample_output_dir, exist_ok=True)
    sample_pdf_path = os.path.join(sample_output_dir, "test_cover_page.pdf")

    # Create a dummy logo for testing logo loading from path
    dummy_logo_path_abs = os.path.join(sample_output_dir, "dummy_logo.png")
    dummy_logo_uri = f"file:///{dummy_logo_path_abs}"
    try:
        from PIL import Image, ImageDraw # Use Pillow to create a dummy image
        img = Image.new('RGB', (100, 30), color = 'red')
        draw = ImageDraw.Draw(img)
        draw.text((10,10), "LOGO", fill=(255,255,0))
        img.save(dummy_logo_path_abs, "PNG")
        logger.info(f"Dummy logo created at: {dummy_logo_path_abs}")
    except ImportError:
        logger.warning("Pillow not installed. Cannot create dummy logo for testing logo path.")
        # Create an empty file as a placeholder if Pillow is not available
        open(dummy_logo_path_abs, 'a').close()
    except Exception as e:
        logger.error(f"Error creating dummy logo: {e}")


    # --- MOCKING ---
    # Mock get_document_context
    _original_get_document_context = get_document_context
    def _mock_get_document_context_for_cover(client_id, company_id, language_code, project_id=None, document_type=None, additional_data=None, db_conn=None):
        logger.info("[MOCK] _mock_get_document_context_for_cover called")
        return {
            "doc": {"current_date_formatted": datetime.date.today().strftime("%B %d, %Y")},
            "client": {"id": client_id, "name": "Test Client Name", "company_name": "Test Client Company Ltd."},
            "seller": {"id": company_id, "name": "Awesome Seller Inc.", "logo_path": dummy_logo_uri if os.path.exists(dummy_logo_path_abs) else None},
            "project": {"id": project_id, "name": "The Grand Project", "identifier": "PRJ-007"},
            "lang": {"code": language_code},
            "placeholders": {}, "additional": additional_data or {}
        }
    get_document_context = _mock_get_document_context_for_cover

    # Mock pagedegrde.generate_cover_page_logic
    # This mock should simulate saving a file or returning bytes
    _original_generate_cover_page_logic = generate_cover_page_logic
    def _mock_pagedegrde_logic(config_dict):
        logger.info(f"[MOCK] _mock_pagedegrde_logic called with config: {config_dict}")
        output_path = config_dict.get('output_path')
        # Simulate creating a dummy PDF file if output_path is provided
        if output_path:
            try:
                with open(output_path, "wb") as f:
                    f.write(b"%PDF-1.4\n%Dummy PDF content for cover page.\n"
                            f"Title: {config_dict.get('title', '')}\n"
                            f"Author: {config_dict.get('author', '')}\n"
                            f"Institution: {config_dict.get('institution', '')}\n"
                            f"Logo present: {'Yes' if config_dict.get('logo_data') else 'No'}\n"
                            b"%%EOF")
                logger.info(f"[MOCK] Dummy PDF saved to {output_path}")
                return True # Indicate success (saved internally)
            except Exception as e:
                logger.error(f"[MOCK] Error saving dummy PDF: {e}")
                return False
        return b"%PDF-1.4\n%Dummy PDF bytes..." # Fallback: return bytes

    if 'generate_cover_page_logic' in globals() and callable(generate_cover_page_logic): # Check if it was imported
        generate_cover_page_logic = _mock_pagedegrde_logic
    else: # If the import failed, the original dummy will be used, this mock won't apply
        logger.warning("pagedegrde.generate_cover_page_logic was not imported, mock cannot be applied.")


    # --- Test generate_cover_page_pdf ---
    logger.info(f"\n--- Testing generate_cover_page_pdf (with logo from context) ---")
    success1 = generate_cover_page_pdf(
        client_id=55,
        company_id=77,
        language_code='fr',
        output_pdf_path=os.path.join(sample_output_dir, "cover_page_test1.pdf"),
        project_id=99,
        document_type_for_context="Proposition Commerciale",
        additional_context_overrides={
            "title": "Custom Title via Override", # Override title
            "template_style": "Classique" # Override style
        }
    )
    logger.info(f"Test 1 Succeeded: {success1}")

    logger.info(f"\n--- Testing generate_cover_page_pdf (with logo_data override) ---")
    dummy_logo_bytes = b"dummy_logo_bytes_content"
    success2 = generate_cover_page_pdf(
        client_id=56,
        company_id=78,
        language_code='en',
        output_pdf_path=os.path.join(sample_output_dir, "cover_page_test2.pdf"),
        project_id=100,
        additional_context_overrides={
            "logo_data": dummy_logo_bytes, # Provide logo bytes directly
            "author": "Manual Author Override"
        }
    )
    logger.info(f"Test 2 Succeeded: {success2}")

    logger.info(f"\n--- Testing generate_cover_page_pdf (no project, specific doc type) ---")
    success3 = generate_cover_page_pdf(
        client_id=57,
        company_id=79,
        language_code='es',
        output_pdf_path=os.path.join(sample_output_dir, "cover_page_test3.pdf"),
        document_type_for_context="Manual General",
        additional_context_overrides={
             "context_builder_data": {"document_title": "Manual de Usuario General"} # Pass data to context_builder
        }
    )
    logger.info(f"Test 3 Succeeded: {success3}")


    # --- Cleanup ---
    get_document_context = _original_get_document_context
    if 'generate_cover_page_logic' in globals() and callable(_original_generate_cover_page_logic):
        generate_cover_page_logic = _original_generate_cover_page_logic

    # Optional: remove test files and directory (uncomment to clean up)
    # import shutil
    # if os.path.exists(sample_output_dir):
    #     shutil.rmtree(sample_output_dir)
    #     logger.info(f"Cleaned up test directory: {sample_output_dir}")

    logger.info("Cover Page generator test run finished.")
    # Note: Requires pagedegrde.py to be correctly structured and importable.
    # The quality of the PDF depends entirely on the pagedegrde.generate_cover_page_logic function.
```
