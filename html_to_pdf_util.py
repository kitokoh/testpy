import os
from weasyprint import HTML
from weasyprint.urls import URLFetchingError # Corrected import

class WeasyPrintError(Exception):
    """Custom exception for WeasyPrint conversion errors."""
    pass

def populate_html(template_content: str, data: dict) -> str:
    """
    Populates an HTML template string with data from a dictionary.

    Args:
        template_content: The HTML content as a string with placeholders.
        data: A dictionary where keys are placeholder names (e.g., "TITLE")
              and values are the data to insert.

    Returns:
        The populated HTML string.
    """
    populated_html_string = template_content
    for key, value in data.items():
        placeholder = f"{{{{{key}}}}}" # e.g. {{TITLE}}
        populated_html_string = populated_html_string.replace(placeholder, str(value))
    return populated_html_string

def convert_html_to_pdf(html_string: str, base_url: str = None) -> bytes | None:
    """
    Converts a populated HTML string to PDF bytes using WeasyPrint.

    Args:
        html_string: The populated HTML string to convert.
        base_url: The base URL for resolving relative paths (e.g., for images).
                  This should typically be the directory of the HTML templates.

    Returns:
        The PDF content as bytes if successful, None otherwise.
        Raises WeasyPrintError if WeasyPrint encounters an error during PDF generation.
    """
    try:
        # The base_url is crucial for WeasyPrint to find local resources like images or CSS files
        # that are referenced with relative paths in the HTML.
        return HTML(string=html_string, base_url=base_url).write_pdf()
    except URLFetchingError as e: # Corrected specific exception
        # This specific catch is for URL fetching errors, which might be common
        # if LOGO_PATH is relative and base_url is not set correctly.
        error_message = f"WeasyPrint URL fetching error: {e}. Ensure base_url is set correctly for relative image paths or use absolute URLs for resources."
        # Consider logging this error
        print(error_message) # Or use a proper logger
        raise WeasyPrintError(error_message) from e
    except Exception as e:
        # Catching a general exception for other WeasyPrint errors.
        error_message = f"An error occurred during PDF conversion with WeasyPrint: {e}"
        # Consider logging this error
        print(error_message) # Or use a proper logger
        raise WeasyPrintError(error_message) from e

if __name__ == '__main__':
    # Example Usage (for testing purposes)

    # 1. Define some sample data
    sample_data = {
        "TITLE": "My Awesome Document",
        "SUBTITLE": "A deep dive into modern technology",
        "AUTHOR": "John Doe",
        "INSTITUTION": "Tech University",
        "DEPARTMENT": "Computer Science",
        "DOC_TYPE": "Research Paper",
        "DATE": "October 26, 2023",
        "VERSION": "1.0",
        "LOGO_PATH": "path/to/your/logo.png" # This needs to be a valid path or URL
    }

    # 2. Create a dummy HTML template string
    # In a real scenario, you'd load this from a file (e.g., modern_template.html)
    dummy_template_html = """
    <!DOCTYPE html>
    <html>
    <head><title>{{TITLE}}</title></head>
    <body>
        <img src="{{LOGO_PATH}}" alt="Logo" width="100">
        <h1>{{TITLE}}</h1>
        <h2>{{SUBTITLE}}</h2>
        <p>By: {{AUTHOR}}</p>
        <p>Date: {{DATE}}</p>
    </body>
    </html>
    """

    # 3. Populate the template
    print("Populating HTML template...")
    populated_content = populate_html(dummy_template_html, sample_data)
    print("Populated HTML:")
    print(populated_content)
    print("-" * 30)

    # 4. Convert to PDF
    # For local file paths in LOGO_PATH to work, base_url should point to a directory
    # from which these files can be accessed.
    # For example, if logo.png is in 'assets/logo.png', and your script is in 'src',
    # and templates are in 'src/templates', base_url might be 'file:///path/to/your/project/assets/'
    # or WeasyPrint might need an absolute file path for LOGO_PATH if base_url is tricky.

    # Let's assume the logo is in a directory 'test_assets' relative to this script.
    # We need to construct an absolute file URI for base_url.
    # This example will likely fail to load the logo unless 'path/to/your/logo.png' is valid
    # and accessible, or if LOGO_PATH is an absolute file URI or a web URL.

    # For testing without a real image, LOGO_PATH can be a placeholder or a URL to an online image.
    # To make this runnable, let's change LOGO_PATH for the example:
    sample_data_for_pdf = sample_data.copy()
    # Replace with a public image URL for testing if local path is not set up
    sample_data_for_pdf["LOGO_PATH"] = "https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png"

    populated_content_for_pdf = populate_html(dummy_template_html, sample_data_for_pdf)

    print("\nConverting to PDF...")
    # Setting base_url to current directory for relative path resolution if any (though logo is URL here)
    # For file:// base_url to work correctly, it needs to be an absolute path.
    # current_dir_path = os.path.abspath(os.path.dirname(__file__))
    # base_url_path = f"file://{current_dir_path}/"

    # If LOGO_PATH is a full URL, base_url might not be strictly necessary for that resource,
    # but it's good practice for other potential relative links (CSS, other images).
    # For simplicity in this example, if LOGO_PATH is a web URL, base_url's role for it is minor.

    pdf_bytes = None
    try:
        # If WeasyPrint is not installed, this will fail.
        # The user running this needs to have WeasyPrint and its dependencies installed.
        # (e.g., by running `pip install WeasyPrint` using the updated requirements.txt)
        pdf_bytes = convert_html_to_pdf(populated_content_for_pdf, base_url=None) # No base_url if all resources are absolute URLs
    except WeasyPrintError as e:
        print(f"PDF Conversion Error: {e}")
    except ImportError:
        print("WeasyPrint is not installed. Please install it to run the PDF conversion example.")
        print("You can typically install it using: pip install WeasyPrint")


    if pdf_bytes:
        output_pdf_path = "example_output.pdf"
        with open(output_pdf_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"PDF successfully generated: {output_pdf_path}")
    else:
        print("PDF generation failed or was skipped.")

    print("\nNote: For local logo paths in templates (e.g., {{LOGO_PATH}} pointing to a local file),")
    print("ensure 'base_url' in 'convert_html_to_pdf' is set to the absolute path of the directory")
    print("containing the logo, formatted as a 'file://' URI.")
    print("Example: base_url='file:///path/to/your/templates/directory/'")

    # To test with a template file:
    # try:
    #     with open('templates/cover_pages/html/modern_template.html', 'r', encoding='utf-8') as f:
    #         modern_template_content = f.read()
    #
    #     test_data_modern = sample_data.copy()
    #     # Ensure LOGO_PATH is a valid URL or an accessible file path relative to base_url
    #     test_data_modern["LOGO_PATH"] = "https_logo_url_or_absolute_file_uri" # Adjust as needed
    #
    #     populated_modern = populate_html(modern_template_content, test_data_modern)
    #
    #     # Define base_url for template resources (e.g., if logo was relative in template)
    #     # template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates/cover_pages/html'))
    #     # base_url_for_template = f"file://{template_dir}/"
    #
    #     pdf_modern_bytes = convert_html_to_pdf(populated_modern, base_url=None) # Adjust base_url if needed
    #     if pdf_modern_bytes:
    #         with open("modern_template_output.pdf", "wb") as f:
    #             f.write(pdf_modern_bytes)
    #         print("Modern template PDF generated: modern_template_output.pdf")
    # except FileNotFoundError:
    #     print("modern_template.html not found. Skipping file-based template test.")
    # except WeasyPrintError as e:
    #     print(f"Error generating PDF from modern_template.html: {e}")
    # except ImportError:
    #     print("WeasyPrint not installed for modern_template.html test.")
