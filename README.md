# Client Document Manager

## Brief Description

Client Document Manager is a desktop application designed to streamline the management of client information, associated documents, and document templates. It allows users to create, organize, and generate client-specific documents, including technical specifications, proforma invoices, sales contracts, and packing lists, using Excel and Word templates. The application also features PDF compilation capabilities, including the generation of customizable cover pages, and an in-app editor for Excel files.

## Features

*   **Client Management:**
    *   Add, view, and edit client details (name, company, contact info, project identifiers, specific needs, etc.).
    *   Filter and search clients based on various criteria (name, project ID, status).
    *   Manage client-specific data, notes, and associated documents within a dedicated client folder structure.
    *   Track client project status (e.g., "En cours", "Archivé", "Urgent").
*   **Document Management:**
    *   Organize and access client-specific documents (Excel, PDF, and DOCX files).
    *   Generate new documents from predefined templates.
*   **Template Management:**
    *   Manage `.xlsx` (Excel) and `.docx` (Word) templates.
    *   Categorize templates by language (fr, ar, tr) and type.
    *   Set default templates for specific document types.
    *   Includes a dedicated module for cover page design and generation (`pagedegrde.py`).
*   **PDF Generation:**
    *   Compile multiple PDF documents into a single PDF file.
    *   Automatically add a dynamically generated cover page to compiled PDFs.
*   **DOCX Population:**
    *   Populate `.docx` templates with client-specific data using placeholders (e.g., `{{CLIENT_NAME}}`).
*   **Excel Editor:**
    *   A basic in-app editor for viewing and modifying `.xlsx` files.
*   **Cover Page Generator:**
    *   A module (`pagedegrde.py`) for designing and generating customizable cover pages for documents and PDF compilations.
*   **Configuration:**
    *   Settings for SMTP (for emailing documents), default template directories, and client file storage locations.

## Core Technologies Used

*   **Python 3.x**
*   **PyQt5:** For the graphical user interface (GUI).
*   **SQLite:** For storing client data, template information, and application settings.
*   **openpyxl:** For reading and writing Excel (`.xlsx`) files.
*   **python-docx:** For reading, writing, and populating Word (`.docx`) files.
*   **ReportLab:** For generating PDF documents, including cover pages.
*   **pandas:** Used for initial default template creation (can be a development dependency).

## Prerequisites

*   Python 3.x (Python 3.7 or newer recommended)
*   pip (Python package installer, usually comes with Python)

## Setup and Installation

1.  **Clone the Repository (if applicable):**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Create a Virtual Environment:**
    It's highly recommended to use a virtual environment to manage project dependencies.
    ```bash
    python -m venv venv
    ```

3.  **Activate the Virtual Environment:**
    *   On Windows:
        ```bash
        venv\Scripts\activate
        ```
    *   On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```

4.  **Install Dependencies:**
    Install the dependencies using the provided `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

Once the setup is complete and dependencies are installed, run the application using:

```bash
python main.py
```

## Fonts

The application uses custom fonts for PDF generation, particularly for cover pages created by the `pagedegrde.py` module (e.g., Arial, Arial Bold, Showcard Gothic).
*   These fonts (as `.ttf` files) should be placed in a `fonts` subdirectory within the application's root folder (i.e., alongside `main.py`).
*   If these font files are missing, PDF output (especially cover pages) may not appear as intended. The application attempts to log warnings when specific fonts cannot be found and may fall back to default PDF fonts, which can alter the appearance.

## Troubleshooting

*   **Missing Fonts:** If PDF documents (especially cover pages) have incorrect fonts, ensure the required `.ttf` files (e.g., `arial.ttf`, `arialbd.ttf`, `ShowcardGothic.ttf` or `showg.ttf`) are present in the `fonts` directory at the root of the application.
*   **Database Issues:** If the application reports database errors on startup, ensure you have write permissions in the application's configuration directory. The database file (`client_manager.db` or similar) is typically stored in a user-specific application data folder (e.g., `~/.config/ClientDocumentManager` on Linux, or `%APPDATA%\ClientDocumentManager` on Windows). Deleting the database file might allow the application to recreate it, but this will erase existing data.
*   **Template Not Found:** Ensure your template files are correctly placed in the configured templates directory (by default, a `templates` subfolder, further organized by language codes like `fr`, `ar`, `tr`).

## Directory Structure (Simplified)

```
.
├── main.py                 # Main application entry point
├── excel_editor.py         # Module for the Excel editing functionality
├── pagedegrde.py           # Module for cover page design and generation logic
├── fonts/                  # Directory for .ttf font files (e.g., arial.ttf, ShowcardGothic.ttf)
│   ├── arial.ttf
│   ├── arialbd.ttf
│   └── ShowcardGothic.ttf  # or showg.ttf
├── templates/              # Default directory for document templates (configurable)
│   ├── fr/
│   │   ├── specification_technique_template.xlsx
│   │   └── ... (other French templates)
│   ├── ar/
│   └── tr/
├── clients/                # Default directory for client-specific files (configurable)
├── icons/                  # (Optional) For UI icons, if using a Qt resource file
└── README.md               # This file
```

This structure provides a general overview. The exact names for database files or default template files might vary slightly based on the implementation.
