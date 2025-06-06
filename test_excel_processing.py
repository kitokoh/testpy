import sys # For QApplication
import logging
from PyQt5.QtWidgets import QApplication # Required for QWidget instantiation
from excel_editor import ExcelTableModel, PDFGenerator, PDFExportSettings, ClientData, ExcelTableWidget

# Setup basic logging to capture output from excel_editor's logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("test_script")

def main():
    # QApplication instance is required for any QWidget based class like ExcelTableWidget
    # Even if not showing UI, it needs to be initialized.
    app = QApplication(sys.argv if hasattr(sys, 'argv') else [])
    logger.info("Starting Excel processing test...")

    model = ExcelTableModel()

    # Attempt to load the workbook
    # Ensure 'invoicefileexemp.xlsx' is in the root directory or provide the correct path
    # For the test environment, assume it's in the root if not specified otherwise.
    workbook_path = "invoicefileexemp.xlsx"
    logger.info(f"Loading workbook: {workbook_path}")
    if not model.load_workbook(workbook_path):
        logger.error(f"Failed to load workbook: {model.load_error_message}")
        return

    logger.info(f"Workbook loaded successfully. Sheets: {model.sheets}")
    if model.current_sheet:
        logger.info(f"Current active sheet: {model.current_sheet.title}")
    else:
        logger.warning("No active sheet found after loading workbook.")
        # Attempt to set current_sheet to the first sheet if available
        if model.sheets:
            model.current_sheet = model.workbook[model.sheets[0]]
            logger.info(f"Manually set current sheet to: {model.current_sheet.title}")
        else:
            logger.error("No sheets available in the workbook.")
            return

    # Image Extraction Check
    logger.info("--- Image Extraction Check ---")
    if model.sheet_images:
        logger.info(f"model.sheet_images content: {model.sheet_images}")
        for sheet_title, images in model.sheet_images.items():
            logger.info(f"Sheet '{sheet_title}' contains {len(images)} image(s).")
            for i, img in enumerate(images):
                logger.info(f"  Image {i+1}: type={type(img)}, ref={getattr(img, 'ref', 'N/A')}, format={getattr(img, 'format', 'N/A')}, size={getattr(img, 'width', 'N/A')}x{getattr(img, 'height', 'N/A')}")
    else:
        logger.info("model.sheet_images is empty.")

    # Header/Footer Extraction Check
    logger.info("--- Header/Footer Extraction Check ---")
    if model.sheet_headers_footers:
        logger.info(f"model.sheet_headers_footers content: {model.sheet_headers_footers}")
        for sheet_title, hf_data in model.sheet_headers_footers.items():
            logger.info(f"Sheet '{sheet_title}' Header/Footer Data:")
            for hf_type, content in hf_data.items():
                logger.info(f"  {hf_type}:")
                for part, details in content.items():
                    if details['text']: # Check only for 'text' as 'image' key was removed
                        logger.info(f"    {part}: Text='{details['text']}'") # Log only text
    else:
        logger.info("model.sheet_headers_footers is empty.")

    # PDF Generation Check (Simulated)
    logger.info("--- PDF Generation Check (Simulated) ---")
    if model.workbook and model.current_sheet:
        # Simulate a QTableWidget for PDFGenerator if needed, or ensure PDFGenerator handles None
        # For this test, we are not creating a full QTableWidget.
        # PDFGenerator's prepare_table_data expects a QTableWidget.
        # We need a mock or ensure it's robust.
        # The current PDFGenerator tries to access table.rowCount(), table.columnCount() etc.
        # Let's create a dummy ExcelTableWidget for the purpose of this test,
        # even if it's not populated from the UI.

        dummy_table_widget = ExcelTableWidget() # Create a dummy table
        # Optionally, load the sheet into this dummy table if full data rendering is desired for PDF
        # This might be too complex for a unit test of data extraction.
        # For now, PDFGenerator might log warnings or errors if table data is empty, which is acceptable for this test.
        # The subtask focused on image and hf data flow.

        logger.info(f"Preparing PDFGenerator for sheet: {model.current_sheet.title}")
        pdf_settings = PDFExportSettings()
        client_data = ClientData(company="Test Corp", project_id="ProjTest") # Add some dummy client data

        pdf_gen = PDFGenerator(
            table=dummy_table_widget, # Pass the dummy table
            client_data=client_data,
            settings=pdf_settings,
            current_sheet_title=model.current_sheet.title,
            sheet_images_data=model.sheet_images,
            sheet_headers_footers_data=model.sheet_headers_footers
        )

        output_pdf_path = "test_output.pdf"
        logger.info(f"Attempting to generate PDF: {output_pdf_path}")
        success, message = pdf_gen.generate(output_pdf_path)

        if success:
            logger.info(f"PDF generated successfully: {message}")
            logger.info(f"Please check '{output_pdf_path}' and logs from excel_editor.PDFGenerator for details on image/header/footer processing.")
        else:
            logger.error(f"PDF generation failed: {message}")
    else:
        logger.warning("Skipping PDF generation check as workbook or current_sheet is not loaded.")

    logger.info("Excel processing test finished.")

if __name__ == "__main__":
    main()
