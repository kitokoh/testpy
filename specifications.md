# Application Specifications (Cahier de Charges)

## Introduction

This document serves as the "Cahier de Charges" or Application Specifications for the comprehensive Client Document and Project Management system. Its purpose is to provide a detailed overview of the application's architecture, modules, core functionalities, data structures, user roles, workflows, and non-functional requirements. This system is designed to streamline client interactions, document generation, project management, and various related business processes through a desktop application, a supporting API, and a mobile interface.

## Database Schema Overview

The application utilizes an SQLite database, with its schema defined and initialized via `db/init_schema.py`. The database is structured to support a wide range of functionalities and can be broadly categorized into the following groups of tables:

*   **Core Entities:**
    *   `Users`: Stores user account information, credentials, and roles.
    *   `Clients`: Central table for client details, including company information, primary needs, and links to location and status.
    *   `Projects`: Manages projects linked to clients, including details like name, description, dates, budget, status, and assigned manager. This table also handles Production Orders as a type of project.
    *   `Products`: Master list of global products/services offered, with details like name, description, pricing, language versions, and categorization.
    *   `Companies`: Manages details of the user's own company(ies) (seller information).
    *   `Contacts`: A central repository for contact persons, linked to clients, partners, or company personnel.
*   **Document & Template Management:**
    *   `Templates`: Stores metadata for various document templates (Excel, Word, HTML) used for generation, including global and client-specific templates.
    *   `ClientDocuments`: Tracks generated documents, linking them to clients, projects, and source templates, and storing file paths.
    *   `CoverPageTemplates` & `CoverPages`: Manages templates for and instances of generated document cover pages.
*   **Linking & Association Tables:**
    *   `ClientContacts`, `PartnerContacts`, `CompanyPersonnelContacts`: Link contacts to clients, partners, and internal personnel respectively.
    *   `ClientProjectProducts`: Links products from the master list to specific clients/projects, allowing for quantity and price overrides.
    *   `ProductMediaLinks`, `AssetMediaLinks`: Link products and company assets to media items.
    *   `MediaItemTags`: Links media items to descriptive tags.
*   **Operational & Feature-Specific Tables:**
    *   `ProformaInvoices` & `ProformaInvoiceItems`: Manage proforma invoice details and their line items.
    *   `Invoices`: Manages final sales invoices and payment tracking.
    *   `SAVTickets`: Tracks after-sales service tickets, linking to clients, products, technicians, and statuses.
    *   `Partners`, `PartnerCategories`, `PartnerDocuments`, `PartnerInteractions`: Manage business partner information and related activities.
    *   `TeamMembers`: Stores details about internal team members, linking to users.
    *   `Tasks`: Manages tasks (including production steps) linked to projects, with assignments, statuses, and dependencies.
    *   `StatusSettings`: Defines various status types (e.g., for clients, projects, tasks, SAV tickets) with associated properties like color and archival status.
    *   `ApplicationSettings`: Stores global application configuration key-value pairs.
    *   `CompanyAssets`, `AssetAssignments`: Manage company-owned assets and their assignments.
    *   `MediaItems`, `Tags`: Core tables for the Media Manager module.
    *   `ItemLocations`, `InternalStockItems`, `ItemStorageLocations`, `ProductStorageLocations`: For inventory and stock management.
    *   `ReportConfigurations`, `ReportConfigFields`, `ReportConfigFilters`: For the dynamic reporting system.
*   **Integration Support Tables:**
    *   `UserGoogleAccounts`, `ContactSyncLog`: Support Google Contacts synchronization.
    *   (Botpress integration uses its own separate `botpress_integration.db` with tables like `UserBotpressSettings`, `UserPrompt`, `Conversation`, `Message`).
*   **Utility & Logging:**
    *   `Countries`, `Cities`: Store geographical data.
    *   `ActivityLog`: Records user actions and system events.
    *   `ScheduledEmails`, `EmailReminders`, `SmtpConfigs`: Support email functionalities.

The schema utilizes primary keys (often UUIDs or auto-incrementing integers), foreign keys for relationships (with `ON DELETE CASCADE` or `ON DELETE SET NULL` where appropriate), unique constraints, and indexes for performance. Soft delete (`is_deleted`, `deleted_at`) is implemented on several key tables.

## Application Modules

This section provides a detailed description of each application module, including its purpose, key functionalities, main data entities (tables) it interacts with, and main CRUD operations.

### 1. API Module (`api/`)

*   **Purpose:** Provides HTTP endpoints for interacting with the application's features and data. It uses FastAPI for building the API.
*   **Key Functionalities:**
    *   **Assets Management (`api/assets.py`):** Manages company assets, asset assignments to personnel, and links between assets and media items (including uploads).
    *   **Authentication (`api/auth.py`):** Handles user authentication using JWT tokens (OAuth2PasswordBearer), token generation, and user verification for API access.
    *   **Dependencies (`api/dependencies.py`):** Manages role-based and permission-based access control for API endpoints.
    *   **Document Generation (`api/documents.py`):** Generates PDF documents from HTML templates using client-specific data, saves them, and provides download links.
    *   **Main Application (`api/main.py`):** Initializes the FastAPI application and includes routers from other API submodules.
    *   **Data Models (`api/models.py`):** Defines Pydantic models for API request/response data structures and includes some SQLAlchemy model definitions.
    *   **Payments & Invoices (`api/payments.py`):** Manages invoices (CRUD operations, filtering).
    *   **Product Management (`api/products.py`):** Manages products (CRUD), including linking media (images) and reordering them.
    *   **Proforma Invoices (`api/proformas.py`):** Manages proforma invoices (CRUD, status updates, PDF generation), including conversion to final invoices.
    *   **Reporting (`api/reports.py`):** Manages report configurations (fields, filters, target entities) and allows execution of these configurations to fetch data.
    *   **Template Listing (`api/templates.py`):** Lists available document templates with filtering options.
*   **Main Data Entities (Tables inferred):** `CompanyAssets`, `AssetAssignments`, `AssetMediaLinks`, `MediaItems`, `Users`, `ClientDocuments`, `Templates`, `Clients`, `Companies`, `Projects`, `Invoices`, `Products`, `ProductMediaLinks`, `ProformaInvoices`, `ProformaInvoiceItems`, `ReportConfigurations`, `ReportConfigFields`, `ReportConfigFilters`.
*   **Main CRUD Operations:**
    *   Company Assets: Create, Read, Update, Soft Delete.
    *   Asset Assignments: Create, Read, Update.
    *   Asset Media Links: Create (link/upload), Read, Delete (unlink), Update (reorder).
    *   Client Documents (Generated PDFs): Create, Read (download).
    *   Invoices: Create, Read, Update, Delete.
    *   Products: Create, Read, Update, Soft Delete.
    *   Product Media Links: Create, Update, Delete (unlink).
    *   Proforma Invoices: Create, Read, Update.
    *   Report Configurations: Create, Read, Update, Delete.
    *   Report Execution: Read (execute configuration).
    *   Templates: Read (list).

### 2. Authentication Module (GUI) (`auth/`)

*   **Purpose:** Manages user authentication for the PyQt5 desktop application, including login and registration UI, and defines application-wide user roles and permissions.
*   **Key Functionalities:**
    *   **Login Window (`auth/login_window.py`):** Provides a QDialog for user login, "Remember Me" feature, and links to registration. Uses `db.verify_user_password` (via `users_crud_instance`).
    *   **Registration Window (`auth/registration_window.py`):** Provides a QDialog for new user registration, performs validation, and uses `users_crud_instance.add_user()`.
    *   **Roles and Permissions (`auth/roles.py`):** Defines user roles (`SUPER_ADMIN`, `ADMINISTRATOR`, `STANDARD_USER`, `READ_ONLY_USER`) and maps them to permissions/capabilities. Provides `has_permission()` and `check_user_role()` helpers.
*   **Main Data Entities (Interacted with via `db.cruds.users_crud`):** `Users`.
*   **Main CRUD Operations (via `users_crud`):** Users: Create (Register), Read (Verify credentials, check existence).

### 3. Botpress Integration Module (`botpress_integration/`)

*   **Purpose:** Integrates Botpress chatbot functionalities into the main application, handling API communication, local data storage for settings and conversations, and providing a UI for these interactions.
*   **Key Functionalities:**
    *   **API Client (`api_client.py`):** `BotpressClient` class for Botpress HTTP API communication (send message, get conversations, get bot info).
    *   **CRUD Operations (`crud.py`):** Manages local SQLite storage (via SQLAlchemy) for `UserBotpressSettings`, `UserPrompt`, `Conversation`, and `Message` tables.
    *   **Data Models (`models.py`):** Defines SQLAlchemy models for the local Botpress integration database (`botpress_integration.db`).
    *   **UI Components (`ui_components.py`):** `BotpressIntegrationUI` (PyQt5 QWidget) for configuring API settings, managing prompts, and displaying/interacting with chat conversations.
*   **Main Data Entities (Local SQLite - `botpress_integration.db`):** `UserBotpressSettings`, `UserPrompt`, `Conversation`, `Message`.
*   **Main CRUD Operations (Local DB):**
    *   UserBotpressSettings: Create, Read, Update, Delete.
    *   UserPrompt: Create, Read, Update, Delete.
    *   Conversation: Create, Read, Update.
    *   Message: Create, Read.
*   **External Interactions:** Communicates with a Botpress instance (cloud or self-hosted) via its HTTP API.

### 4. Clients Data Module (File-based) (`clients/`)

*   **Purpose:** Stores client-specific HTML templates for various documents, organized by client identifiers and language.
*   **Key Functionalities:** Provides raw template files for processing by other modules (e.g., `document_generator`). This is not a code module.
*   **Main Data Entities:** HTML template files (e.g., `packing_list_template.html`, `sales_contract_template.html`).
*   **Structure:** `clients/<client_identifier>/<language_code>/<template_name>.html`.
*   **Main CRUD Operations:** Not applicable (Read operations performed by other modules).

### 5. Contact Manager Module (`contact_manager/`)

*   **Purpose:** Manages contacts from platform sources (clients, partners, personnel) and synchronizes them with Google Contacts.
*   **Key Functionalities:**
    *   **Contact List Widget (`contact_list_widget.py`):** PyQt5 widget to display a unified list of contacts with filtering. Placeholder actions for view/edit, assign role, manual sync.
    *   **Google Authentication (`google_auth.py`):** Manages Google OAuth 2.0 flow, token storage (`UserGoogleAccounts` table), and authenticated session retrieval.
    *   **Google People API (`google_people_api.py`):** Wrapper for Google People API calls (list, get, create, update, delete contacts). Currently uses placeholder API responses.
    *   **Google Settings Dialog (`google_settings_dialog.py`):** PyQt5 dialog for linking/unlinking Google accounts.
    *   **Synchronization Service (`sync_service.py`):** Orchestrates two-way contact sync between platform and Google. Includes data transformation logic and uses `ContactSyncLog` table for tracking. Platform-side update/creation logic from Google data is largely placeholder.
*   **Main Data Entities (Interacted With):** `Contacts` (platform), `ClientContacts`, `PartnerContacts`, `CompanyPersonnelContacts`, `Clients`, `Partners`, `UserGoogleAccounts`, `ContactSyncLog`, Google Person resources (API).
*   **Main CRUD Operations:**
    *   UserGoogleAccounts: Create, Read, Update, Delete.
    *   ContactSyncLog: Create, Read, Update, Delete.
    *   Google Contacts (API): Create, Read, Update, Delete.
    *   Platform Contacts: Reads various types for display/sync. Updates/creations from Google data are placeholder.

### 6. Database Core Module (`db/connection.py`, `db/init_schema.py`, `db/utils.py`, `db/db_seed.py`)

*   **Purpose:** Handles database setup, connectivity, core utility functions, and initial data population.
*   **Key Functionalities:**
    *   **`connection.py`:** Provides `get_db_connection()` for SQLite connections using `app_setup.CONFIG`.
    *   **`init_schema.py`:** `initialize_database()` defines and creates the entire database schema (all tables, columns, indexes), handles schema migrations (e.g., adding columns), and seeds essential data (admin user, default statuses, default template categories, cover page templates).
    *   **`utils.py`:** Contains `get_document_context_data()` for document generation context, currency formatting, and general template file helpers.
    *   **`db_seed.py`:** `seed_initial_data()` populates the database with more extensive sample/default data (clients, products, projects, email templates, partner categories, etc.) after schema creation.
*   **Main Data Entities:** Defines and interacts with nearly all tables in the application's SQLite database.
*   **Main CRUD Operations:** Primarily Schema: CREATE TABLE, ALTER TABLE, CREATE INDEX. Seeding: INSERT. Utils: READ (via CRUDs).

### 7. Database CRUD Modules (`db/cruds/`)

*   **Purpose:** Provide structured Create, Read, Update, Delete operations for specific database tables/entities.
*   **Structure:**
    *   Often inherit from `GenericCRUD` (from `db/cruds/generic_crud.py`).
    *   Use `_manage_conn` decorator for connection and transaction management.
    *   Instantiate a CRUD class and export methods as module-level functions.
*   **Key Functionalities (Common Patterns):**
    *   `add_<entity>()`: Creates new records with validation and default values.
    *   `get_<entity>_by_id()`, `get_all_<entities>()`: Read records with filtering, pagination, and soft-delete handling.
    *   `update_<entity>()`: Updates records, handles `updated_at` timestamps.
    *   `delete_<entity>()`: Performs soft deletes (sets `is_deleted=1`, `deleted_at`).
    *   Specialized getters for specific query needs.
*   **Examples Reviewed:** `clients_crud.py`, `products_crud.py`, `users_crud.py`.
    *   `generic_crud.py`: Base class and `_manage_conn` decorator.
    *   `users_crud.py`: Manages `Users` table with secure password hashing (salt + SHA256) and soft deletes.
    *   `clients_crud.py`: Manages `Clients` and `ClientNotes`, provides various client segmentation queries.
    *   `products_crud.py`: Manages `Products`, `ProductDimensions`, `ProductEquivalencies`, and interacts with `product_media_links_crud`.

### 8. Document Generator Module (`document_generator/`)

*   **Purpose:** Generates documents in HTML, DOCX, and PDF (cover pages) using templates and dynamic data.
*   **Key Functionalities:**
    *   **Context Builder (`context_builder.py`):** `get_document_context()` aggregates data from various DB tables (via `db.cruds`) to build a comprehensive context dictionary for templates.
    *   **Cover Page Generator (`cover_page_generator.py`):** `generate_cover_page_pdf()` creates PDF cover pages using `pagedegrde` module (ReportLab based) and data from `get_document_context()`.
    *   **DOCX Generator (`docx_generator.py`):** `generate_docx_document()` populates `.docx` templates using `python-docx` library and placeholders from context.
    *   **HTML Generator (`html_generator.py`):** `generate_html_document()` renders HTML templates (using `html_to_pdf_util.render_html_template`) with context data. `generate_html_and_convert_to_pdf()` then converts this HTML to PDF (using `html_to_pdf_util.convert_html_to_pdf`).
    *   **Exceptions (`exceptions.py`):** Placeholder for custom exceptions.
*   **Main Data Entities (Interacted With via `context_builder`):** Clients, Companies, Projects, Products, Contacts, etc. Also template files (.html, .docx).
*   **Dependencies:** `db.cruds`, `pagedegrde`, `python-docx`, `html_to_pdf_util`.

### 9. E-commerce Integrations Module (`ecommerce_integrations/`)

*   **Purpose:** Defines an interface and provides implementations (currently WooCommerce placeholder) for connecting to e-commerce platforms to manage/synchronize product data.
*   **Key Functionalities:**
    *   **Base Connector (`base_connector.py`):** `BaseProductData` class (platform-agnostic product data) and `EcommerceConnector` (Abstract Base Class defining connection and product CRUD methods).
    *   **WooCommerce Connector (`woocommerce_connector.py`):** `WooCommerceConnector` class (placeholder implementation) for WooCommerce, outlining API interaction methods and data transformation helpers.
*   **Main Data Entities:** Products (local and platform), E-commerce store configuration.
*   **Main CRUD Operations (on E-commerce Platform API):** Create, Read, Update, Delete products.
*   **Dependencies:** Potentially `httpx` or platform-specific SDKs (e.g., `woocommerce`).
*   **Status:** Abstract structure is present; concrete WooCommerce implementation is placeholder.

### 10. Invoicing Module (UI) (`invoicing/`)

*   **Purpose:** Provides PyQt5 UI components for managing financial invoices within the desktop application.
*   **Key Functionalities & UI Components:**
    *   **Final Invoice Data Dialog (`final_invoice_data_dialog.py`):** Dialog to prepare data for a final invoice, including line item management (from products or client-project products) and invoice header details.
    *   **Invoice Details Dialog (`invoice_details_dialog.py`):** Read-only dialog to display detailed information of an invoice.
    *   **Invoice Management Widget (`invoice_management_widget.py`):** Main widget for listing invoices with filtering (search, status, date range) and actions (record payment, view details, add new manual invoice).
    *   **Manual Invoice Dialog (`manual_invoice_dialog.py`):** Dialog for manually creating new invoices.
    *   **Record Payment Dialog (`record_payment_dialog.py`):** Dialog to record/update payment details for an invoice.
*   **Main Data Entities (Interacted With via CRUDs):** `Invoices`, `Clients`, `Projects`, `Products`, `ClientProjectProducts`.
*   **Main CRUD Operations (via other CRUDs):** Invoices: Create, Read, Update. Clients/Projects/Products: Read.
*   **Dependencies:** PyQt5, `db.cruds.invoices_crud`, `clients_crud`, `projects_crud`, `products_crud`, `client_project_products_crud`.

### 11. Media Manager Module (`media_manager/`)

*   **Purpose:** Manages a library of media items (videos, images, links), including storage, metadata extraction, database persistence, and basic sharing placeholders.
*   **Key Functionalities:**
    *   **Data Models (`models.py`):** `MediaItem` base class and `VideoItem`, `ImageItem`, `LinkItem` subclasses.
    *   **Operations (`operations.py`):**
        *   Metadata extraction (Pillow for images, OpenCV for videos).
        *   Thumbnail generation (Pillow, OpenCV).
        *   Asynchronous addition of new media items (copies files, extracts metadata/thumbnails, stores in DB).
        *   Listing, searching, and fetching media items by ID.
        *   Asynchronous download of selected media.
        *   Placeholder sharing functions (email, WhatsApp).
        *   Direct database interaction with `MediaItems`, `Tags`, `MediaItemTags` tables.
*   **Main Data Entities (Database Tables):** `MediaItems`, `Tags`, `MediaItemTags`.
*   **Main CRUD Operations (Local DB):** MediaItems: Create, Read. Tags/MediaItemTags: Create, Read.
*   **Configuration:** Uses `MEDIA_FILES_BASE_PATH` and `DEFAULT_DOWNLOAD_PATH` from `config.py`.
*   **Dependencies:** `db` (for connection), `Pillow`, `OpenCV (cv2)`, `aiofiles`, `config.py`.

### 12. Mobile Module (`mobile/`)

*   **Purpose:** Provides a Kivy-based mobile application front-end, primarily for document generation, with a basic NLU system for command processing.
*   **Key Functionalities & Components:**
    *   **Data Handler (`data_handler.py`):** Mock API layer simulating backend data fetching for the mobile app.
    *   **Document Handler (`document_handler.py`):** `LiteDocumentHandler` for mobile document context preparation and PDF generation (uses `mobile_data_api` and `html_to_pdf_util`).
    *   **Main Application (`main.py`):** Kivy `App` class setting up `ScreenManager` with `DocumentGenerationScreen`.
    *   **Kivy UI (`mobile.kv`):** Placeholder KV language layout for `DocumentGenerationScreen`.
    *   **NLU Controller (`nlu_controller.py`):** `process_nlu_result()` translates NLU handler output into UI actions.
    *   **NLU Handler (`nlu_handler.py`):** `parse_command()` performs rule-based intent recognition and entity extraction from text commands.
    *   **UI Screen (`ui.py`):** `DocumentGenerationScreen` (Kivy) for selecting language, country, template, products, and generating/emailing PDFs (using `plyer`).
*   **Main Data Entities (Simulated via `mobile_data_api`):** Clients, Companies, Products, Countries, Document Templates.
*   **Dependencies:** `kivy`, `plyer`, `html_to_pdf_util`.
*   **Status:** Mobile app with mocked backend data, focusing on document generation UI and NLU.

### 13. General UI Dialogs Module (`dialogs/`)

*   **Purpose:** Contains a collection of reusable and specialized PyQt5 `QDialog` subclasses for various data entry, modification, selection, and interaction tasks within the main desktop application.
*   **Key Functionalities & UI Components (Examples):**
    *   **Data Entry/Editing:** `AddNewClientDialog`, `EditClientDialog`, `ContactDialog`, `ProductDialog`, `EditProductLineDialog`, `ManageProductMasterDialog`, `ProductDimensionUIDialog`, `ClientDocumentNoteDialog`, `TransporterDialog`, `FreightForwarderDialog`, `AddEditMilestoneDialog`, `UserDialog`, `StatisticsAddClientDialog`.
    *   **Assignment/Linking:** `AssignPersonnelDialog`, `AssignTransporterDialog`, `AssignFreightForwarderDialog`, `AssignDocumentToClientDialog`, `ProductEquivalencyDialog`.
    *   **Selection/Interaction:** `SelectContactsDialog`, `SelectClientAttachmentDialog`, `SelectUtilityAttachmentDialog`, `CreateDocumentDialog`, `CompilePdfDialog`, `SendEmailDialog`, `SettingsDialog`, `CarrierMapDialog`.
*   **Common UI Patterns:** Use of `QFormLayout`, `QComboBox`, `QLineEdit`, `QTextEdit`, `QDialogButtonBox`, `QMessageBox`. Dialogs interact with `db_manager` or specific CRUD modules.
*   **Dependencies:** PyQt5, `db` module (facade or CRUDs), other application modules (e.g., `html_editor`, `utils`), external libraries (`PyPDF2`).

### 14. Partners Module (UI) (`partners/`)

*   **Purpose:** Manages information about business partners, including their details, contacts, documents, categories, and interactions.
*   **Key Functionalities & UI Components:**
    *   **Partner Category Dialog (`partner_category_dialog.py`):** Add, edit, delete partner categories.
    *   **Partner Dialog (`partner_dialog.py`):** Tabbed dialog for comprehensive partner data management (details, contacts via `EditPartnerContactDialog`, documents, categories, interactions via `InteractionEditDialog`).
    *   **Partner Main Widget (`partner_main_widget.py`):** Main UI for listing partners with filtering (search, category, status, type) and actions (add, manage categories, email/WhatsApp placeholders).
*   **Main Data Entities:** `Partners`, `PartnerCategories`, `PartnerContacts`, `Contacts`, `PartnerCategoryLink`, `PartnerDocuments`, `PartnerInteractions`.
*   **Main CRUD Operations (via `db` functions):** Full CRUD for partners and their related entities.
*   **Dependencies:** PyQt5, `db` module, `contact_manager.sync_service` (potential integration).

### 15. Product Management Module (UI) (`product_management/`)

*   **Purpose:** Provides a UI for managing the global master list of products.
*   **Key Functionalities & UI Components:**
    *   **Product Edit Dialog (`edit_dialog.py`):** Tabbed dialog for adding/editing global products (basic info, images via `media_manager`, technical specifications, equivalencies/translations via `SelectProductDialog`).
    *   **Product List Dialog (`list_dialog.py`):** Displays products with filtering, pagination, price editing, and PDF export. (Possibly older/alternative to `ProductManagementPage`).
    *   **Product Management Page (`page.py`):** Main `QWidget` for product management with filtering, table display, pagination, and actions (add/edit/delete, PDF export).
    *   **Tests (`tests/`):** Unit tests for dialogs.
*   **Main Data Entities:** `Products`, `ProductDimensions`, `ProductEquivalencies`, `MediaItems`, `ProductMediaLinks`.
*   **Main CRUD Operations (via CRUD instances):** Full CRUD for products and related entities.
*   **Dependencies:** PyQt5, `db.cruds.products_crud`, `product_media_links_crud`, `media_manager.operations`, `html_to_pdf_util`, `config.py`.

### 16. Project Management Module (UI & Logic) (`project_management/`)

*   **Purpose:** Provides a comprehensive interface for managing projects, tasks, production orders, cover pages, team members, and includes a dashboard and notification system.
*   **Key Functionalities & UI Components:**
    *   **Dashboard (`dashboard.py`):** `MainDashboard(QWidget)` with a top bar and stacked pages for Dashboard (KPIs, graphs), Team Management, Project Management, Task Management, Reports (placeholder), Settings, Cover Page Management, and Production Order Management.
    *   **Dialogs (`dialogs/` submodule):** `AddProductionOrderDialog`, `EditProductionOrderDialog`, `ProductionOrderDetailDialog`, `EditProductionStepDialog`, `CoverPageEditorDialog`.
    *   **Notifications (`notifications.py`):** `CustomNotificationBanner` and `NotificationManager` for displaying application alerts (e.g., overdue tasks/projects).
*   **Main Data Entities (via `db.py`):** `Projects` (incl. 'PRODUCTION' type), `Tasks`, `StatusSettings`, `TeamMembers`, `Clients`, `CoverPages`, `CoverPageTemplates`, `KPIs`, `ActivityLog`.
*   **Main CRUD Operations (via `db.py`):** Full CRUD for projects, tasks, cover pages, team members, milestones.
*   **Dependencies:** PyQt5, `db.py` (extensive use), `pyqtgraph`, `dialogs` (root), `dashboard_extensions`, `Installsweb.installmodules`.

### 17. SAV (After-Sales Service) Module (`sav/`)

*   **Purpose:** Manages after-sales service tickets, including creation, editing, and status tracking, with email notifications.
*   **Key Functionalities & UI Components:**
    *   **SAV Ticket Dialog (`ticket_dialog.py`):** `SAVTicketDialog(QDialog)` for creating/editing SAV tickets (linked product, issue description, status, assigned technician, resolution). Sends email notifications for "Opened" and "Resolved" statuses.
*   **Main Data Entities:** `SAVTickets`, `ClientProjectProducts`, `StatusSettings`, `TeamMembers`, `Templates` (email), `Clients`, `Contacts`.
*   **Main CRUD Operations (via `db_manager`):** SAVTickets: Create, Read, Update. Reads various related entities.
*   **Dependencies:** PyQt5, `db_manager`, `email_service.EmailSenderService`.

### 18. WhatsApp Module (`whatsapp/`)

*   **Purpose:** Enables sending WhatsApp messages from the application.
*   **Key Functionalities & UI Components:**
    *   **WhatsApp Service (`whatsapp_service.py`):** `WhatsAppService` class wraps `pywhatkit.sendwhatmsg_instantly()` (currently commented out).
    *   **Send WhatsApp Dialog (`whatsapp_dialog.py`):** `SendWhatsAppDialog(QDialog)` for composing and initiating WhatsApp message sending.
*   **Main Operations:** Sending WhatsApp messages via `pywhatkit` (core functionality currently disabled).
*   **Dependencies:** PyQt5, `pywhatkit`.
*   **Status:** Core sending functionality in `whatsapp_service.py` is currently disabled.

### 19. Main Application & Core Utilities (Root Directory)

*   **Purpose:** Orchestrates the entire desktop application, manages global configuration, initializes services, and provides core utility functions.
*   **Key Files & Functionalities:**
    *   **`main_window.py` (`DocumentManager`):** Main application window, integrates all UI modules, handles client management view, navigation, global actions, download monitoring, and notifications.
    *   **`app_config.py`:** Defines static configuration constants and default paths.
    *   **`app_setup.py`:** Handles application startup: logging, stylesheet loading, default template file creation, loading main `CONFIG` from `utils.load_config()`.
    *   **`utils.py`:** General utility functions including `load_config`, `save_config`, `get_document_context_data` (also found in `document_generator.context_builder`), currency formatting.
    *   **`document_manager_logic.py`:** Business logic specific to client and document management within `main_window.py`.
    *   **`company_management.py` (`CompanyTabWidget`):** UI widget for managing company details, likely embedded in `SettingsPage`.
    *   **`settings_page.py` (`SettingsPage`):** UI widget for managing all application settings, embedded in `main_window.py`.
    *   **`email_service.py` (`EmailSenderService`):** Service for sending emails via SMTP.
    *   **`html_to_pdf_util.py`:** Utilities for rendering HTML (likely Jinja2) and converting HTML to PDF (likely WeasyPrint).
    *   **`pagedegrde.py`:** Logic for generating PDF cover pages using ReportLab.
    *   **`excel_editor.py`, `html_editor.py`:** UI components for editing Excel and HTML content respectively.
    *   **`inventory_browser_widget.py`:** UI for browsing and managing workshop/internal stock.
    *   **`statistics_module.py`, `statistics_panel.py`, `statistics_page_widget.py`:** Components related to displaying statistics and maps.
*   **Dependencies:** PyQt5, all other application modules, various utility libraries.

## User Roles and Permissions

This section outlines the conceptual permissions for each user role across the various application modules. The roles are `SUPER_ADMIN`, `ADMINISTRATOR`, `STANDARD_USER`, and `READ_ONLY_USER`.

**General Principles:**

*   **SUPER_ADMIN:** Possesses `all_access`, granting unrestricted access and bypassing specific permission checks. This role is intended for system setup, advanced configuration, and full data oversight.
*   **ADMINISTRATOR:** Has broad permissions to manage most aspects of the application, including users (standard), clients, projects, products, templates, and system settings.
*   **STANDARD_USER:** Can perform daily operations related to their assigned clients and projects, generate documents, manage their own settings, and use communication features.
*   **READ_ONLY_USER:** Can view data across various modules but cannot make changes.

**Permissions by Module:**

**1. API Module (`api`)**
    *   Permissions are primarily governed by API keys or OAuth scopes tied to user roles.
    *   `api.access_all_endpoints`: SUPER_ADMIN, ADMINISTRATOR (actual access depends on endpoint-specific security).
    *   `api.access_standard_endpoints`: STANDARD_USER.
    *   `api.access_readonly_endpoints`: READ_ONLY_USER.

**2. Authentication Module (GUI) (`auth`)**
    *   `auth.login`: All roles.
    *   `auth.register_new_users`: ADMINISTRATOR, SUPER_ADMIN (if registration is restricted).
    *   `auth.manage_roles_permissions`: SUPER_ADMIN (to define/modify what each role can do).
    *   `auth.assign_user_roles`: SUPER_ADMIN (assign any role); ADMINISTRATOR (assign non-admin roles).

**3. Botpress Integration Module (`botpress_integration`)**
    *   `botpress.manage_system_settings`: SUPER_ADMIN (if there are global Botpress configurations).
    *   `botpress.manage_own_settings`: STANDARD_USER, ADMINISTRATOR (configure API key, bot ID for their own usage if applicable).
    *   `botpress.use_chatbot`: STANDARD_USER, ADMINISTRATOR.
    *   `botpress.manage_prompts`: STANDARD_USER, ADMINISTRATOR (for their own prompts).
    *   `botpress.view_conversations`: STANDARD_USER, ADMINISTRATOR (own/related conversations); ADMINISTRATOR (potentially wider access for support).

**4. Clients Data Module (`clients/`)** (File-based templates)
    *   `clients.manage_client_specific_templates`: ADMINISTRATOR (add/update/delete templates in client folders).
    *   `clients.use_client_specific_templates`: STANDARD_USER, ADMINISTRATOR (system uses these for document generation).

**5. Contact Manager Module (`contact_manager`)**
    *   `contacts.view_all`: ADMINISTRATOR.
    *   `contacts.view_assigned`: STANDARD_USER (contacts linked to their clients/projects).
    *   `contacts.create`: STANDARD_USER, ADMINISTRATOR.
    *   `contacts.edit_all`: ADMINISTRATOR.
    *   `contacts.edit_assigned`: STANDARD_USER.
    *   `contacts.delete`: ADMINISTRATOR.
    *   `contacts.manage_google_sync_own_settings`: STANDARD_USER, ADMINISTRATOR.
    *   `contacts.perform_google_sync_own`: STANDARD_USER, ADMINISTRATOR.
    *   `contacts.admin_manage_all_sync_settings`: SUPER_ADMIN.

**6. Document Generator Module (`document_generator`)**
    *   `documents.generate_for_assigned`: STANDARD_USER, ADMINISTRATOR (for clients/projects they can access).
    *   `documents.generate_for_all`: ADMINISTRATOR.
    *   `documents.download_own`: STANDARD_USER, ADMINISTRATOR.
    *   (Template management is covered under "Main Application & Core Utilities" -> "Template Management").

**7. E-commerce Integrations Module (`ecommerce_integrations`)**
    *   `ecommerce.manage_connections`: ADMINISTRATOR, SUPER_ADMIN.
    *   `ecommerce.view_products`: ADMINISTRATOR, STANDARD_USER (if products are synced and viewable).
    *   `ecommerce.trigger_sync`: ADMINISTRATOR.
    *   `ecommerce.manage_platform_products_via_app`: ADMINISTRATOR (CRUD operations on e-commerce platform through this app's interface).

**8. Invoicing Module (UI) (`invoicing`)**
    *   `invoices.create`: STANDARD_USER, ADMINISTRATOR.
    *   `invoices.view_all`: ADMINISTRATOR.
    *   `invoices.view_assigned`: STANDARD_USER.
    *   `invoices.edit_all`: ADMINISTRATOR.
    *   `invoices.edit_assigned_payment_status`: STANDARD_USER (e.g., record payment for their invoices).
    *   `invoices.delete`: ADMINISTRATOR.

**9. Media Manager Module (`media_manager`)**
    *   `media.upload_new`: STANDARD_USER, ADMINISTRATOR.
    *   `media.view_library`: All roles with UI access.
    *   `media.manage_own_uploads`: STANDARD_USER, ADMINISTRATOR (edit details, tags of items they uploaded).
    *   `media.manage_all_library_items`: ADMINISTRATOR (delete any media, edit all details, manage global tags).
    *   `media.share_items`: STANDARD_USER, ADMINISTRATOR.

**10. Mobile Module (`mobile`)**
    *   Permissions are primarily derived from the API permissions granted to the user account used by the mobile app.
    *   `mobile.use_app_standard_features`: STANDARD_USER.
    *   `mobile.use_app_readonly_features`: READ_ONLY_USER.

**11. General UI Dialogs Module (`dialogs`)**
    *   Permissions are contextual and inherited from the primary action the dialog facilitates (e.g., opening `AddNewClientDialog` requires `clients.create` permission).

**12. Partners Module (UI) (`partners`)**
    *   `partners.view_all`: READ_ONLY_USER, STANDARD_USER, ADMINISTRATOR.
    *   `partners.create`: ADMINISTRATOR.
    *   `partners.edit_all`: ADMINISTRATOR.
    *   `partners.delete`: ADMINISTRATOR.
    *   `partners.manage_categories`: ADMINISTRATOR.
    *   `partners.manage_contacts`: ADMINISTRATOR (full CRUD); STANDARD_USER (potentially add/edit contacts for assigned partners).
    *   `partners.manage_documents`: ADMINISTRATOR (full CRUD); STANDARD_USER (potentially add documents for assigned partners).
    *   `partners.manage_interactions`: ADMINISTRATOR (full CRUD); STANDARD_USER (add/view interactions for assigned partners).

**13. Product Management Module (UI) (`product_management`)** (Global Products)
    *   `products.view_global_list`: READ_ONLY_USER, STANDARD_USER, ADMINISTRATOR.
    *   `products.manage_global_master`: ADMINISTRATOR (CRUD for global products, dimensions, equivalencies, images).

**14. Project Management Module (UI & Logic) (`project_management`)**
    *   `projects.view_dashboard_all_data`: ADMINISTRATOR.
    *   `projects.view_dashboard_assigned_data`: STANDARD_USER.
    *   `projects.manage_all_projects_and_tasks`: ADMINISTRATOR (full CRUD on projects, tasks, production orders).
    *   `projects.create_projects`: STANDARD_USER (if allowed for their clients), ADMINISTRATOR.
    *   `projects.edit_assigned_projects_tasks`: STANDARD_USER (update status, progress on their own or managed projects/tasks).
    *   `projects.view_assigned_projects_tasks`: STANDARD_USER, READ_ONLY_USER.
    *   `team.manage_members`: ADMINISTRATOR (add/edit team members within project management context).
    *   `coverpages.manage_project_specific`: ADMINISTRATOR, STANDARD_USER (for their projects).
    *   `notifications.receive_all`: ADMINISTRATOR.
    *   `notifications.receive_assigned`: STANDARD_USER.

**15. SAV (After-Sales Service) Module (`sav`)**
    *   `sav.create_ticket`: STANDARD_USER, ADMINISTRATOR (for clients they manage/can access).
    *   `sav.view_all_tickets`: ADMINISTRATOR.
    *   `sav.view_assigned_tickets`: STANDARD_USER (tickets for their clients or assigned to them).
    *   `sav.update_ticket_details`: STANDARD_USER, ADMINISTRATOR (for accessible tickets).
    *   `sav.assign_technician_to_ticket`: ADMINISTRATOR.
    *   `sav.change_ticket_status`: STANDARD_USER (e.g., to resolved if they handled it), ADMINISTRATOR.

**16. WhatsApp Module (`whatsapp`)**
    *   `whatsapp.send_messages`: STANDARD_USER, ADMINISTRATOR (to contacts they are permitted to interact with).
    *   `whatsapp.configure_service_globally`: SUPER_ADMIN (if any global service settings exist).

**17. Main Application & Core Utilities (Root Directory)**
    *   **User Account Management (via Settings or User Admin UI):**
        *   `users.create_standard_accounts`: ADMINISTRATOR.
        *   `users.edit_any_standard_account`: ADMINISTRATOR.
        *   `users.delete_standard_accounts`: ADMINISTRATOR.
        *   `users.manage_admin_accounts`: SUPER_ADMIN.
        *   `users.assign_roles_standard`: ADMINISTRATOR (can assign STANDARD_USER, READ_ONLY_USER).
        *   `users.assign_roles_all`: SUPER_ADMIN (can assign ADMINISTRATOR, SUPER_ADMIN).
        *   `users.edit_own_profile`: All roles with UI access.
    *   **Application Settings (`SettingsPage`):**
        *   `settings.view_all`: ADMINISTRATOR, SUPER_ADMIN.
        *   `settings.edit_general_paths_language`: ADMINISTRATOR.
        *   `settings.edit_smtp_company`: ADMINISTRATOR, SUPER_ADMIN.
        *   `settings.edit_download_monitor`: ADMINISTRATOR.
        *   `settings.edit_module_visibility`: SUPER_ADMIN.
    *   **Template Management (`TemplateDialog`):**
        *   `templates.view_all`: READ_ONLY_USER, STANDARD_USER, ADMINISTRATOR.
        *   `templates.manage_global_templates`: ADMINISTRATOR (CRUD on global templates, categories).
        *   `templates.manage_client_specific_templates`: ADMINISTRATOR (full CRUD); STANDARD_USER (potentially add/edit for own clients if feature exists).
        *   `templates.set_default_templates`: ADMINISTRATOR.
    *   **Company Profile Management (`CompanyTabWidget` in Settings):**
        *   `company_profile.edit_default`: ADMINISTRATOR.
        *   `company_profile.manage_multiple`: SUPER_ADMIN (if system supports multiple profiles).
    *   **Email Service (Sending capability):**
        *   `email.send_manual_compose`: STANDARD_USER, ADMINISTRATOR.
        *   (Automated emails are system-triggered based on other actions like SAV updates).
    *   **Statistics & Reporting (UI access):**
        *   `statistics.view_dashboards_and_reports`: READ_ONLY_USER, STANDARD_USER, ADMINISTRATOR.
        *   `statistics.export_data`: STANDARD_USER, ADMINISTRATOR.
    *   **Inventory Management (`InventoryBrowserWidget`):**
        *   `inventory.view_stock_and_locations`: READ_ONLY_USER, STANDARD_USER, ADMINISTRATOR.
        *   `inventory.manage_stock_items`: ADMINISTRATOR (add/edit/delete items).
        *   `inventory.manage_locations`: ADMINISTRATOR (add/edit/delete locations).
        *   `inventory.update_stock_levels`: STANDARD_USER (for specific tasks/orders), ADMINISTRATOR.

## Core Application Workflows

This section describes key operational workflows within the application, outlining the steps and involved modules.

**1. New Client Onboarding and Project Creation**

*   **Goal:** Add a new client to the system, set up their initial project, and prepare their dedicated environment.
*   **Steps:**
    1.  **Initiation (UI - `main_window.py`, `dialogs`):** An Administrator or Standard User triggers "Add New Client" using `AddNewClientDialog` or `StatisticsAddClientDialog`.
    2.  **Data Input (UI - `dialogs`):** User provides client details (name, company, contact, needs, location, initial project identifier, languages). Locations (country/city) can be selected or added dynamically.
        *   *Modules involved:* `dialogs`, `db.cruds.clients_crud`, `db.cruds.locations_crud`.
    3.  **Client Record Creation (Backend - `db.cruds.clients_crud`):** A new client record is saved to the `Clients` table.
    4.  **Folder Setup (Backend - `document_manager_logic.py` or `main_window.py` logic):**
        *   A dedicated base folder for the client is created (e.g., `clients/<client_identifier>/`).
        *   Language-specific subfolders (e.g., `en/`, `fr/`) are created within the client's folder.
        *   Default document templates may be copied to these folders.
        *   *File System Operations*.
    5.  **Initial Project Record (Backend - `db.cruds.projects_crud`):** An initial project linked to the client is created in the `Projects` table using the provided project identifier.
    6.  **Primary Contact Creation (UI/Backend):**
        *   User is prompted (e.g., via `dialogs.ContactDialog`) to add details for the client's primary contact.
        *   Contact is saved to `Contacts` table and linked via `ClientContacts` table.
        *   *Modules involved:* `dialogs.ContactDialog`, `db.cruds.contacts_crud`, `db.cruds.client_contacts_crud`.
    7.  **Feedback & UI Update (UI - `main_window.py`):**
        *   User receives notification of successful creation.
        *   The client list is refreshed.
        *   Optionally, a new tab (`ClientWidget`) for the new client is opened.

**2. Product Addition to Project and Proforma Invoice Generation**

*   **Goal:** Add products/services to a specific client project and generate a proforma invoice.
*   **Steps:**
    1.  **Navigation (UI - `main_window.py`):** User navigates to the specific `ClientWidget` tab.
    2.  **Product Linking (UI - `dialogs.ProductDialog`):**
        *   User opens the "Add Products to Client/Project" dialog.
        *   User selects products from the global product list (master data).
        *   User defines quantity and can override unit price for each product line specific to this client/project.
        *   *Modules involved:* `dialogs.ProductDialog`, `db.cruds.products_crud`.
    3.  **Saving Product Links (Backend - `db.cruds.client_project_products_crud`):** The selected products, quantities, and price overrides are saved to the `ClientProjectProducts` table, linking them to the client and project.
    4.  **Initiate Proforma (UI - `ClientWidget` or `dialogs.CreateDocumentDialog`):** User action triggers proforma invoice generation.
    5.  **Proforma Context & Details (UI/Backend):**
        *   System gathers data: client info, seller (own company) info, project details, and the `ClientProjectProducts` line items.
        *   User may be prompted to confirm/add proforma-specific details (payment terms, delivery terms, incoterms, notes, currency, VAT/discount rates) via a dialog or API payload.
        *   *Modules involved:* `api.proformas` (if via API), `document_generator.context_builder` (or `db.utils.get_document_context_data`), various `db.cruds`.
    6.  **Proforma Record (Backend - `db.cruds.proforma_invoices_crud`):** A record is created in `ProformaInvoices` and associated `ProformaInvoiceItems` tables.
    7.  **PDF Generation (Backend - `document_generator`, `api.documents`):**
        *   A suitable HTML proforma invoice template is selected.
        *   The context data is rendered into the HTML template.
        *   The HTML is converted to PDF.
        *   The PDF is saved to the client's document folder.
        *   A record is added to `ClientDocuments`, and its ID is linked to the `ProformaInvoices` record.
    8.  **Availability (UI):** The generated proforma PDF is made available for download/viewing/emailing.

**3. Sales Contract Generation**

*   **Goal:** Generate a formal sales contract document for a client and project.
*   **Steps:**
    1.  **Navigation (UI - `main_window.py`):** User is typically within a `ClientWidget` for an active client/project.
    2.  **Initiation (UI - `dialogs.CreateDocumentDialog`):** User selects an action to generate a sales contract.
    3.  **Template Selection (UI):** User chooses a sales contract template (e.g., `.docx` or `.html`) from available global or client-specific templates.
        *   *Modules involved:* `dialogs.CreateDocumentDialog`, `db.cruds.templates_crud`.
    4.  **Data Aggregation (Backend - `document_generator.context_builder`):** The system gathers all necessary data:
        *   Seller (own company) details.
        *   Client company and primary contact details.
        *   Project name and identifier.
        *   Detailed list of products/services from `ClientProjectProducts` (quantities, agreed prices).
        *   Commercial terms (payment, delivery, warranty - these might be pulled from project settings, client settings, or entered/confirmed by the user).
        *   *Modules involved:* `document_generator.context_builder`, various `db.cruds`.
    5.  **Document Population & Saving (Backend - `document_generator`):**
        *   **For DOCX:** `document_generator.docx_generator` populates placeholders in the selected Word template.
        *   **For HTML to PDF:** `document_generator.html_generator` renders the HTML template, which is then converted to PDF.
        *   The generated document is saved to the client's designated folder (e.g., `clients/<client_id>/<project_id_or_general>/<lang>/`).
        *   A record of the generated document is created in the `ClientDocuments` table.
        *   *Modules involved:* `document_generator`, `db.cruds.client_documents_crud`.
    6.  **Access (UI):** The generated sales contract is made available for download, preview, or email.

**4. SAV (After-Sales Service) Ticket Management**

*   **Goal:** Manage the lifecycle of an after-sales service ticket.
*   **Steps:**
    1.  **Ticket Creation (UI - `sav.ticket_dialog.SAVTicketDialog`):**
        *   A user (Client-facing Staff or Admin) initiates ticket creation, typically from a client's context or a dedicated SAV section.
        *   The user selects the client, optionally links a specific purchased product (from `ClientProjectProducts`), and details the issue.
        *   *Modules involved:* `sav.ticket_dialog`, `db.cruds.clients_crud`, `db.cruds.client_project_products_crud`.
    2.  **Ticket Submission & Initial Notification (Backend):**
        *   A new ticket record is created in the `SAVTickets` table with a default "Open" status.
        *   *Modules involved:* `db.cruds.sav_tickets_crud`, `db.cruds.status_settings_crud`.
        *   An email notification (using "email_sav_ticket_opened" template) is automatically sent to the client's primary contact.
        *   *Modules involved:* `email_service.EmailSenderService`, `db.cruds.templates_crud`, `db.cruds.contacts_crud`.
    3.  **Ticket Triage & Assignment (UI/Backend):**
        *   An Administrator or SAV Manager reviews the new ticket.
        *   The ticket can be assigned to a specific technician (`TeamMembers`) via the `SAVTicketDialog` (edit mode).
        *   Status might be updated (e.g., "En Investigation").
        *   *Modules involved:* `sav.ticket_dialog`, `db.cruds.sav_tickets_crud`, `db.cruds.team_members_crud`.
    4.  **Investigation & Resolution (UI/Backend):**
        *   The assigned technician investigates the issue.
        *   Resolution details are added to the ticket via `SAVTicketDialog`.
        *   Status is updated (e.g., "Pending Client Feedback", "Resolved").
    5.  **Ticket Closure & Final Notification (Backend):**
        *   When the status is set to "Résolu" (Resolved):
            *   The `closed_at` timestamp is set for the ticket.
            *   An email notification (using "email_sav_ticket_resolved" template) is sent to the client.
        *   *Modules involved:* `sav.ticket_dialog` (triggers update), `db.cruds.sav_tickets_crud`, `email_service.EmailSenderService`, `db.cruds.templates_crud`.
    6.  **Tracking & Reporting (UI):** Authorized users can view lists of SAV tickets, filter by status/client/technician, and potentially view related statistics (not explicitly detailed but a common requirement).

## Non-Functional Requirements (Inferred)

This section outlines potential non-functional requirements (NFRs) inferred from the application's described modules, functionalities, and architecture. These are characteristics of the system that define how well it performs its functions.

**1. Security**

*   **Authentication:**
    *   Desktop Application: User credentials must be securely stored (e.g., passwords hashed with salt, as implemented in `users_crud.py`). Session management should be secure (e.g., session timeout as per `SettingsDialog`).
    *   API: Secure token-based authentication (e.g., JWT as used in `api/auth.py`) must be enforced for all relevant endpoints.
*   **Authorization:**
    *   Role-Based Access Control (RBAC) must be consistently applied across all modules (desktop UI and API) as per the roles defined in `auth/roles.py` and conceptual permissions.
*   **Data Protection:**
    *   Sensitive configuration data (e.g., SMTP passwords, API keys for external services like Google Contacts, Botpress) stored in database tables or configuration files must be encrypted or appropriately protected.
    *   Client-specific data and generated documents must be protected from unauthorized access, potentially through file system permissions managed in conjunction with application logic.
*   **Input Validation:**
    *   All user inputs via UI dialogs and API request payloads must be rigorously validated to prevent common vulnerabilities (e.g., SQL injection (less critical with ORM/parameterized queries but good practice), XSS (if web components involved), data corruption).
*   **Dependency Management:**
    *   External libraries and dependencies (e.g., `pywhatkit`, `FastAPI`, Kivy, PyQt5, `python-docx`, `Pillow`, `OpenCV`) should be regularly reviewed and updated to mitigate known vulnerabilities.

**2. Data Integrity**

*   **Transactional Operations:** Database operations involving multiple steps or tables (e.g., client creation with initial project, invoice generation with line items) must be performed transactionally to ensure atomicity. The `_manage_conn` decorator in `db/cruds/generic_crud.py` aims to support this.
*   **Data Consistency:** Foreign key constraints, as defined in `db/init_schema.py`, must be maintained to ensure relational integrity between tables. Soft delete mechanisms should be applied consistently.
*   **Input Validation:** Data types, formats, and ranges must be validated at the point of entry (UI and API) to ensure correctness before database persistence.
*   **Error Handling:** Database errors and unexpected issues during data processing must be handled gracefully to prevent data corruption or inconsistent states.

**3. Usability**

*   **User Interface (Desktop & Mobile):**
    *   Navigation should be intuitive and consistent across modules.
    *   The application must remain responsive, especially during potentially long-running operations like document generation, large data fetching, or external API calls. Background processing or asynchronous operations (as seen in `media_manager` and planned for some UI interactions) should be utilized.
    *   Users must receive clear and timely feedback for their actions (e.g., success messages, error dialogs, progress indicators).
*   **Accessibility:** The application should strive to meet basic accessibility guidelines (e.g., keyboard navigability, sufficient color contrast, clear font sizes).
*   **Error Messages:** Error messages displayed to the user should be understandable and actionable, guiding them on how to proceed or report the issue.

**4. Internationalization (I18N) & Localization (L10N)**

*   **UI Language:** The desktop application UI (PyQt5) must support multiple languages using its translation mechanisms (`self.tr()`, `translations/` directory). The Kivy mobile app would require its own I18N/L10N setup.
*   **Document Language:** Generation of documents (proformas, contracts, etc.) must support multiple languages, using appropriate templates (as seen in `templates/` and `clients/` structures with language subfolders).
*   **Data Handling:** The system must correctly handle and display data containing various character sets (UTF-8 encoding should be standard).
*   **Locale Formatting:** Dates, numbers, and currencies should be formatted according to the user's locale or the selected language/client preferences (e.g., `utils.format_currency`).

**5. Performance**

*   **Database Operations:** Database queries, especially those for displaying lists (clients, products, projects) or generating reports, must be optimized for speed. Effective use of indexes (defined in `db/init_schema.py`) and pagination (implemented in several UI lists) is essential.
*   **Document Generation:** The time taken to generate documents (PDF, DOCX) should be acceptable to the user. Complex documents or large batches might require optimization or background processing.
*   **API Responsiveness:** API endpoints must process requests and return responses within acceptable timeframes to ensure a good experience for API consumers (including the mobile app).
*   **Application Startup:** The desktop application should launch and become usable within a reasonable period.
*   **Media Processing:** Asynchronous handling of media file operations (uploads, thumbnail generation as in `media_manager`) should be maintained and extended to prevent UI freezes.

**6. Scalability**

*   **Database:** While currently using SQLite, the database interaction layer (CRUD modules) should be designed to facilitate a potential future migration to a more scalable client-server database system if data volume or concurrent user load increases significantly.
*   **API Architecture:** The FastAPI-based API is generally well-suited for scaling. Maintaining statelessness in API endpoints will support horizontal scaling.
*   **File Storage:** For large-scale deployment with many clients and documents, the current file system-based storage for client documents and media might need to evolve to a more robust and scalable solution (e.g., dedicated file servers, cloud storage services).

**7. Maintainability**

*   **Modularity:** The existing modular structure (API, UI components, database CRUDs, services) should be maintained and enforced to simplify development, testing, and updates.
*   **Code Quality:** Adherence to consistent coding standards, clear naming conventions, and adequate commenting is necessary.
*   **Configuration Management:** Centralized and well-documented configuration (e.g., `app_config.py`, `app_setup.py`, `config.json`, `ApplicationSettings` table) is important.
*   **Testability:** Continued development and maintenance of unit and integration tests (`tests/` directory) are crucial for ensuring code quality and preventing regressions.
*   **Logging:** Comprehensive and configurable logging (as set up in `app_setup.py`) must be used throughout the application for effective debugging and monitoring.

**8. Reliability & Availability**

*   **Error Handling:** Robust error handling (try-except blocks, validation) must be implemented in all modules to prevent unexpected crashes and ensure graceful degradation of service where possible.
*   **Data Backup and Recovery:** A strategy for regular backups of the SQLite database and all critical application data (client documents, media files, templates) must be defined and implemented. Recovery procedures should also be established.
*   **External Service Dependencies:** The application should handle potential unavailability or errors from external services (Botpress, Google APIs, SMTP, WhatsApp/pywhatkit, E-commerce platforms) gracefully, possibly with retry mechanisms or by temporarily disabling dependent features.
*   **Resource Management:** Proper management of resources like database connections (e.g., using `_manage_conn`), file handles, and memory to prevent leaks and ensure long-term stability.

## Future Considerations/Potential Features

This section lists potential areas for future development and enhancement based on the current application structure and identified placeholders.

*   **E-commerce Integration:** Complete the implementation of the `WooCommerceConnector` and potentially add connectors for other platforms (e.g., Shopify, Magento). This includes robust product synchronization (inventory, pricing, orders).
*   **Mobile Application (`mobile/`):**
    *   Replace mock API calls in `mobile/data_handler.py` with live API interactions with the main application's backend API.
    *   Expand features beyond document generation (e.g., client lookup, project status view, SAV ticket interaction).
    *   Implement native mobile features for PDF viewing/sharing and email composition instead of relying on `plyer` workarounds where platform support is limited.
    *   Develop a more sophisticated NLU model for the mobile command interface if usage grows.
*   **WhatsApp Integration (`whatsapp/`):**
    *   Uncomment and fully integrate `pywhatkit` or explore more robust/official WhatsApp Business API solutions for message sending and potentially receiving.
    *   Provide UI for managing WhatsApp templates and viewing conversation history if two-way communication is implemented.
*   **API Enhancements (`api/`):**
    *   Add more comprehensive endpoints for all modules to support wider integration capabilities (e.g., full CRUD for all entities where appropriate).
    *   Implement more granular OAuth scopes for API access.
*   **Contact Manager (`contact_manager/`):**
    *   Complete the Google People API integration by replacing placeholder responses with actual API calls and error handling.
    *   Implement robust conflict resolution for two-way contact synchronization.
    *   Provide UI feedback during sync operations.
*   **Reporting & Statistics:**
    *   Fully implement the `Reports Page` in `project_management/dashboard.py` with dynamic report generation and visualization based on `ReportConfigurations`.
    *   Enhance the `StatisticsDashboard` with more diverse charts and data insights.
    *   Implement export options for reports in various formats (beyond PDF for product lists).
*   **Advanced Project Management:**
    *   Full implementation of task dependencies and Gantt chart visualizations.
    *   Resource allocation and workload management features.
    *   Budget tracking and expense management per project.
*   **User Management & Permissions:**
    *   Develop a more granular permission system beyond the conceptual one, possibly linking permissions directly to UI elements or API endpoints.
    *   Implement UI for `SUPER_ADMIN` to manage these granular permissions for roles.
*   **Data Import/Export:** Provide more robust data import/export functionalities for key entities (clients, products, projects) in formats like CSV or Excel.
*   **Custom Fields:** Allow administrators to define custom data fields for entities like Clients, Projects, or Products.
*   **Full PII Redaction/Encryption:** Implement more robust PII redaction or field-level encryption for sensitive data if required by compliance standards.
*   **Database Scalability:** Plan for potential migration from SQLite to a client-server database if application usage scales significantly.
*   **Automated Testing:** Expand test coverage in the `tests/` directory for all modules.
*   **Two-Factor Authentication (2FA):** Enhance security with 2FA options for user login.
*   **Audit Trails:** Expand `ActivityLog` to cover more granular actions and provide a user-friendly interface for administrators to review audit trails.
```
