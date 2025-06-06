import logging
import json # For pretty printing dicts
from excel_editor import (
    ExcelTableModel,
    StyleConverter,
    PDFGenerator,
    PDFExportSettings,
    ClientData,
    ExcelCellStyle # Added for type hinting if needed, and direct inspection
)

# Configure logging to see output from excel_editor.py and this script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Excel processing test script...")

    # 1. Instantiate ExcelTableModel
    model = ExcelTableModel()

    # 2. Load the workbook
    file_to_test = "invoicefileexemp.xlsx" # Assuming it's in the same directory
    logger.info(f"Loading workbook: {file_to_test}")
    if not model.load_workbook(file_to_test):
        logger.error(f"Failed to load workbook: {model.load_error_message}")
        return

    logger.info(f"Workbook loaded. Sheets: {model.sheets}")
    if model.current_sheet:
        logger.info(f"Current sheet: {model.current_sheet.title}")
    else:
        logger.error("No current sheet found after loading workbook.")
        return

    # 3. Log Extracted Styles from Model
    if model.current_sheet:
        sample_cells_coords = ['A1', 'B2', 'C3'] # As per subtask
        logger.info("--- Logging Extracted Styles from Sample Cells ---")
        for cell_coord in sample_cells_coords:
            try:
                sample_cell = model.current_sheet[cell_coord]
                excel_style: ExcelCellStyle = StyleConverter.excel_to_qt(sample_cell)

                # Log all attributes of the dataclass instance
                style_attrs = {field: getattr(excel_style, field) for field in excel_style.__dataclass_fields__}
                logger.info(f"Style for cell {cell_coord}: {json.dumps(style_attrs, indent=2)}")

            except Exception as e:
                logger.error(f"Could not retrieve or style cell {cell_coord}: {e}")
        logger.info("--- Finished Logging Extracted Styles ---")

        # Log a snippet of model.sheet_headers_footers
        logger.info("--- Logging Snippet of Extracted Headers/Footers ---")
        if model.sheet_headers_footers:
            for sheet_title, hf_data in model.sheet_headers_footers.items():
                logger.info(f"Sheet: {sheet_title}")
                # Log first available odd_header and odd_footer as a sample
                for hf_type in ["odd_header", "odd_footer"]:
                    if hf_type in hf_data:
                        logger.info(f"  {hf_type}:")
                        for part in ["left", "center", "right"]:
                            if part in hf_data[hf_type] and (hf_data[hf_type][part].get("text") or hf_data[hf_type][part].get("image_data")):
                                logger.info(f"    {part}: Text='{hf_data[hf_type][part].get('text')}', HasImage={bool(hf_data[hf_type][part].get('image_data'))}")
                break # Just log for the first sheet with H/F data for brevity
        else:
            logger.info("No headers/footers data extracted from the model.")
        logger.info("--- Finished Logging Headers/Footers ---")

        logger.info("--- Logging Snippet of Extracted Sheet Images ---")
        if model.sheet_images:
            for sheet_title, images in model.sheet_images.items():
                logger.info(f"Sheet: {sheet_title} has {len(images)} image(s).")
                # Log info about the first image if present
                if images:
                    logger.info(f"  First image data length: {len(images[0])} bytes (if data was stored as bytes)")
                break # Just log for the first sheet with images
        else:
            logger.info("No sheet images data extracted from the model.")
        logger.info("--- Finished Logging Sheet Images ---")


    # 4. Simulate PDF Generation
    logger.info("--- Simulating PDF Generation ---")
    pdf_settings = PDFExportSettings()
    client_data = ClientData(name="Test Client", company="Test Corp") # Minimal client data for PDF

    if model.workbook and model.current_sheet:
        # The PDFGenerator in excel_editor.py expects a QTableWidget as its first argument.
        # For this test, we don't have a GUI, so we'll pass None.
        # This might cause issues if PDFGenerator strictly relies on it without fallbacks.
        # Based on current PDFGenerator structure, it seems it primarily uses current_excel_sheet
        # for data and styles if provided, which we are doing.

        logger.info(f"Instantiating PDFGenerator for sheet: {model.current_sheet.title}")
        pdf_gen = PDFGenerator(
            table=None, # Passing None as we don't have a QTableWidget here
            client_data=client_data,
            settings=pdf_settings,
            current_sheet_title=model.current_sheet.title,
            sheet_images_data=model.sheet_images,
            sheet_headers_footers_data=model.sheet_headers_footers,
            current_excel_sheet=model.current_sheet
        )

        output_pdf_filename = "test_output_invoice_styled.pdf"
        logger.info(f"Calling PDFGenerator.generate() to create {output_pdf_filename}...")
        success, message = pdf_gen.generate(output_pdf_filename)

        if success:
            logger.info(f"PDF generation successful: {message}")
            logger.info(f"Output PDF: {output_pdf_filename}")
        else:
            logger.error(f"PDF generation failed: {message}")
    else:
        logger.error("Cannot simulate PDF generation: Workbook or current sheet not available.")

    logger.info("--- Finished PDF Generation Simulation ---")
    logger.info("Test script finished successfully.")

if __name__ == "__main__":
    main()
