# Client Document Manager: Technical Overview

**Client Document Manager is a desktop application built with Python, designed for managing client data and automating document generation.**

## Core Architecture:

*   **Application Type:** Desktop GUI Application.
*   **Primary Language:** Python (3.x, 3.7+ recommended).
*   **User Interface:** Built using PyQt5, providing a native desktop experience.
*   **Database:** SQLite is used for local data storage, including:
    *   Client information and metadata.
    *   Paths to client-specific document folders.
    *   Configuration for document templates.
    *   Application settings.
*   **File System Integration:** The application manages client-specific documents by organizing them into dedicated folders within the user's file system. Default locations are configurable.

## Key Technical Features & Libraries:

*   **Client Data Management:**
    *   CRUD operations for client records stored in SQLite.
    *   Functionality for filtering, searching, and status tracking of clients.

*   **Document Template System:**
    *   Supports `.xlsx` (Excel) and `.docx` (Word) file formats as templates.
    *   Templates are organized by language (e.g., `fr`, `ar`, `tr`) and type.
    *   **`openpyxl`:** Used for reading data from and writing data to Excel (`.xlsx`) templates.
    *   **`python-docx`:** Utilized for parsing `.docx` files and populating placeholders (e.g., `{{CLIENT_NAME}}`) with client-specific data.

*   **Document Generation & Output:**
    *   **Excel File Handling:** Leverages `openpyxl` for generating new Excel documents based on templates.
    *   **Word Document Population:** Uses `python-docx` to fill in Word templates.
    *   **PDF Generation:**
        *   **`ReportLab`:** Employed for creating PDF documents, particularly for generating dynamic cover pages.
        *   Capabilities include compiling multiple existing PDF files (potentially generated from Word/Excel, or pre-existing) into a single PDF.
    *   **Cover Page Module (`pagedegrde.py`):** A dedicated module likely using ReportLab to design and render cover pages with dynamic content and custom fonts. Requires `.ttf` font files (e.g., Arial, Showcard Gothic) to be present in a `fonts/` directory.

*   **In-App Excel Editor:**
    *   Provides basic functionality to view and modify `.xlsx` files directly within the application. The specific implementation details (e.g., using a Qt widget wrapping a library or a custom solution) would require deeper code inspection.

*   **Configuration & Settings:**
    *   Manages SMTP server settings for emailing documents.
    *   Stores paths for default template directories and client file storage.

*   **Packaging & Dependencies:**
    *   Dependencies are managed via a `requirements.txt` file.
    *   The application is intended to be run from a Python environment with these dependencies installed.

## Setup & Environment:

*   Requires Python 3.x and `pip`.
*   A virtual environment (`venv`) is recommended for dependency management.
*   The main entry point for the application is typically `main.py`.

## Potential Areas for Extension:

*   Cloud synchronization for database and client files.
*   Integration with other CRM or ERP systems.
*   More advanced document editing features.
*   Web-based interface or companion app.
