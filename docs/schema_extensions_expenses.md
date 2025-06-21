# Expense Management Module - Database Schema Extensions

This document outlines the new database tables added for the Expense Management module. These tables are integrated into the existing SQLite database managed by `db/init_schema.py`.

## Tables

### 1. `company_factures`

Stores metadata about uploaded facture (invoice/receipt) documents.

| Column                | Type    | Constraints                      | Description                                                                 |
|-----------------------|---------|----------------------------------|-----------------------------------------------------------------------------|
| `facture_id`          | INTEGER | PRIMARY KEY AUTOINCREMENT        | Unique identifier for the facture record.                                     |
| `original_file_name`  | TEXT    | NOT NULL                         | The original name of the uploaded file.                                     |
| `stored_file_path`    | TEXT    | NOT NULL                         | The path on the server/local system where the facture file is stored.         |
| `file_mime_type`      | TEXT    |                                  | MIME type of the uploaded file (e.g., "application/pdf", "image/jpeg").     |
| `upload_date`         | TIMESTAMP| DEFAULT CURRENT_TIMESTAMP        | Timestamp when the file was uploaded.                                       |
| `extraction_status`   | TEXT    | NOT NULL DEFAULT 'pending_review'| Status of the data extraction process (e.g., 'pending_extraction', 'data_extracted_pending_confirmation', 'extraction_failed', 'pending_ocr', 'data_confirmed_linked'). |
| `extracted_data_json` | TEXT    |                                  | JSON string storing extracted data (raw text and/or parsed fields like amount, date, vendor). |
| `created_at`          | TIMESTAMP| DEFAULT CURRENT_TIMESTAMP        | Timestamp of record creation.                                               |
| `updated_at`          | TIMESTAMP| DEFAULT CURRENT_TIMESTAMP        | Timestamp of last record update.                                            |
| `is_deleted`          | INTEGER | DEFAULT 0                        | Flag for soft delete (0 = active, 1 = deleted).                             |
| `deleted_at`          | TIMESTAMP|                                  | Timestamp of when the record was soft-deleted.                              |

**Indexes:**
*   `idx_company_factures_upload_date` on (`upload_date`)
*   `idx_company_factures_extraction_status` on (`extraction_status`)
*   `idx_company_factures_is_deleted` on (`is_deleted`)

### 2. `company_expenses`

Stores details of company expenses, each potentially linked to a facture.

| Column                 | Type    | Constraints                      | Description                                                                 |
|------------------------|---------|----------------------------------|-----------------------------------------------------------------------------|
| `expense_id`           | INTEGER | PRIMARY KEY AUTOINCREMENT        | Unique identifier for the expense record.                                   |
| `expense_date`         | DATE    | NOT NULL                         | Date when the expense occurred.                                             |
| `amount`               | REAL    | NOT NULL                         | Monetary value of the expense.                                              |
| `currency`             | TEXT    | NOT NULL                         | Currency code of the amount (e.g., "USD", "EUR", "XAF").                    |
| `recipient_name`       | TEXT    | NOT NULL                         | Name of the entity/person the expense was paid to.                          |
| `description`          | TEXT    |                                  | Optional description or notes about the expense.                            |
| `facture_id`           | INTEGER | UNIQUE, FOREIGN KEY (`company_factures.facture_id`) ON DELETE SET NULL | Optional link to a record in the `company_factures` table. UNIQUE constraint enforces one-to-one relationship for linked factures. |
| `created_by_user_id`   | TEXT    | FOREIGN KEY (`Users.user_id`) ON DELETE SET NULL | ID of the user who created/recorded the expense.                            |
| `created_at`           | TIMESTAMP| DEFAULT CURRENT_TIMESTAMP        | Timestamp of record creation.                                               |
| `updated_at`           | TIMESTAMP| DEFAULT CURRENT_TIMESTAMP        | Timestamp of last record update.                                            |
| `is_deleted`           | INTEGER | DEFAULT 0                        | Flag for soft delete (0 = active, 1 = deleted).                             |
| `deleted_at`           | TIMESTAMP|                                  | Timestamp of when the record was soft-deleted.                              |

**Indexes:**
*   `idx_company_expenses_expense_date` on (`expense_date`)
*   `idx_company_expenses_recipient_name` on (`recipient_name`)
*   `idx_company_expenses_facture_id` on (`facture_id`)
*   `idx_company_expenses_created_by_user_id` on (`created_by_user_id`)
*   `idx_company_expenses_is_deleted` on (`is_deleted`)

## Relationships

*   A `company_expenses` record can optionally be linked to one `company_factures` record via `company_expenses.facture_id`.
*   Due to the `UNIQUE` constraint on `company_expenses.facture_id`, a single `company_factures` record can be linked to at most one `company_expenses` record, effectively forming a one-to-one relationship when linked.

## Integration

These tables are added within the `initialize_database()` function in `db/init_schema.py`.
CRUD operations are available in `db/cruds/company_expenses_crud.py`.
API endpoints are defined in `api/company_expenses_api.py` and `api/company_factures_api.py`.
Pydantic models for API interaction are in `api/models.py`.
Utility functions for text extraction and parsing from factures are in `utils/text_extraction.py`.
Configuration for facture file storage is in `config.py` (`COMPANY_FACTURES_DIR_PATH`).
