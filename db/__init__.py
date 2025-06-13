# db/__init__.py

# Initialize the database schema if run directly (e.g., for setup)
# This also makes the initialize_database function available for import.
from .init_schema import initialize_database

# Import key utilities
from .connection import get_db_connection # Moved from utils
from .utils import format_currency, get_document_context_data

# Import all CRUD functions from their respective modules
# This makes them available via db.function_name()

from .cruds.activity_logs_crud import (
    add_activity_log,
    get_activity_logs,
    get_activity_log_by_id,
)
from .cruds.application_settings_crud import (
    get_setting,
    set_setting,
)
from .cruds.client_assigned_personnel_crud import (
    assign_personnel_to_client,
    get_assigned_personnel_for_client,
    unassign_personnel_from_client,
)
from .cruds.client_documents_crud import (
    add_client_document,
    get_document_by_id,
    get_documents_for_client,
    get_documents_for_project,
    update_client_document,
    delete_client_document,
)
from .cruds.client_freight_forwarders_crud import (
    assign_forwarder_to_client,
    get_assigned_forwarders_for_client,
    unassign_forwarder_from_client,
)
from .cruds.client_project_products_crud import (
    add_product_to_client_or_project,
    update_client_project_product,
    remove_product_from_client_or_project,
    get_client_project_product_by_id,
    get_products_for_client_or_project,
)
from .cruds.client_transporters_crud import (
    assign_transporter_to_client,
    get_assigned_transporters_for_client,
    unassign_transporter_from_client,
    update_client_transporter_email_status,
)
from .cruds.clients_crud import (
    add_client,
    get_client_by_id,
    get_all_clients,
    update_client,
    delete_client,
    get_all_clients_with_details,
    get_active_clients_count,
    get_client_counts_by_country,
    get_client_segmentation_by_city,
    get_client_segmentation_by_status,
    get_client_segmentation_by_category,
    get_clients_by_archival_status,
    get_active_clients_per_country,
    add_client_note,
    get_client_notes,
)
from .cruds.companies_crud import (
    add_company,
    get_company_by_id,
    get_all_companies,
    update_company,
    delete_company,
    set_default_company,
    get_default_company,
)
from .cruds.company_personnel_crud import (
    add_company_personnel,
    get_personnel_for_company,
    update_company_personnel,
    delete_company_personnel,
)
from .cruds.contacts_crud import (
    get_contacts_for_client,
    add_contact,
    get_contact_by_id,
    get_contact_by_email,
    get_all_contacts,
    update_contact,
    delete_contact,
    add_contact_list, # Stub
    add_contact_to_list, # Stub
    delete_contact_list, # Stub
    get_all_contact_lists, # Stub
    get_contact_list_by_id, # Stub
    get_contacts_in_list, # Stub
    remove_contact_from_list, # Stub
    link_contact_to_client,
    unlink_contact_from_client,
    get_contacts_for_client_count,
    get_clients_for_contact,
    get_specific_client_contact_link_details,
    update_client_contact_link,
)
from .cruds.cover_pages_crud import (
    add_cover_page,
    get_cover_page_by_id,
    get_cover_pages_for_client,
    get_cover_pages_for_project,
    update_cover_page,
    delete_cover_page,
    get_cover_pages_for_user,
)
from .cruds.freight_forwarders_crud import (
    add_freight_forwarder,
    get_freight_forwarder_by_id,
    get_all_freight_forwarders,
    update_freight_forwarder,
    delete_freight_forwarder,
)
from .cruds.google_sync_crud import (
    add_user_google_account,
    get_user_google_account_by_user_id,
    get_user_google_account_by_google_account_id,
    get_user_google_account_by_id,
    update_user_google_account,
    delete_user_google_account,
    get_all_user_google_accounts,
    add_contact_sync_log,
    get_contact_sync_log_by_local_contact,
    get_contact_sync_log_by_google_contact_id,
    get_contact_sync_log_by_id,
    update_contact_sync_log,
    delete_contact_sync_log,
    get_contacts_pending_sync,
    get_all_sync_logs_for_account,
)
from .cruds.kpis_crud import ( # Stubs
    get_kpis_for_project,
    add_kpi_to_project,
    update_kpi,
    delete_kpi,
    add_kpi,
    get_kpi_by_id,
)
from .cruds.locations_crud import (
    get_country_by_name,
    get_country_by_id,
    get_or_add_country,
    add_country,
    get_all_countries,
    get_city_by_name_and_country_id,
    get_city_by_id,
    add_city,
    get_or_add_city,
    get_all_cities,
)
from .cruds.milestones_crud import (
    get_milestones_for_project,
    add_milestone,
    get_milestone_by_id,
    update_milestone,
    delete_milestone,
)
from .cruds.partners_crud import (
    add_partner_category,
    get_partner_category_by_id,
    get_partner_category_by_name,
    get_all_partner_categories,
    update_partner_category,
    delete_partner_category,
    get_or_add_partner_category,
    add_partner,
    get_partner_by_id,
    get_partner_by_email,
    get_all_partners,
    update_partner,
    delete_partner,
    get_partners_by_category_id,
    add_partner_contact,
    get_partner_contact_by_id,
    get_contacts_for_partner,
    update_partner_contact,
    delete_partner_contact,
    delete_contacts_for_partner,
    link_partner_to_category,
    unlink_partner_from_category,
    get_categories_for_partner,
    get_partners_in_category,
    add_partner_document,
    get_documents_for_partner,
    get_partner_document_by_id,
    update_partner_document,
    delete_partner_document,
)
from .cruds.product_media_links_crud import (
    link_media_to_product,
    get_media_links_for_product,
    get_media_link_by_ids,
    get_media_link_by_link_id,
    update_media_link,
    unlink_media_from_product,
    unlink_media_by_ids,
    unlink_all_media_from_product,
    update_product_media_display_orders,
)
from .cruds.products_crud import (
    get_product_by_id as get_product_by_id_details, # Renamed to avoid conflict with simple get_product_by_id if it existed
    add_product,
    get_product_by_name,
    get_all_products,
    update_product,
    delete_product,
    get_products,
    update_product_price,
    get_products_by_name_pattern,
    get_all_products_for_selection_filtered,
    get_total_products_count,
    add_or_update_product_dimension,
    get_product_dimension,
    delete_product_dimension,
    add_product_equivalence,
    get_equivalent_products,
    get_all_product_equivalencies,
    remove_product_equivalence,
)

# Proforma Invoices & Items
from .cruds.proforma_invoices_crud import (
    create_proforma_invoice,
    get_proforma_invoice_by_id,
    get_proforma_invoice_by_number,
    list_proforma_invoices,
    update_proforma_invoice,
    delete_proforma_invoice,
    create_proforma_invoice_item,
    get_proforma_invoice_item_by_id,
    update_proforma_invoice_item,
    delete_proforma_invoice_item,
)

from .cruds.projects_crud import ( # Placeholders
    add_project,
    get_project_by_id,
    delete_project,
    get_projects_by_client_id,
    update_project,
    get_all_projects,
    get_total_projects_count, # Already correctly added in previous step
)
from .cruds.status_settings_crud import (
    get_status_setting_by_name,
    get_status_setting_by_id,
    get_all_status_settings,
)
from .cruds.tasks_crud import ( # Placeholders
    add_task,
    get_task_by_id,
    get_tasks_by_project_id,
    update_task,
    delete_task,
    get_tasks_by_assignee_id, # Already correctly added in previous step
    get_all_tasks,
    add_task_dependency,
    remove_task_dependency,
)


# KPIs (often linked to projects or other entities)
from .cruds.kpis_crud import ( # Assuming a kpis_crud.py exists
    add_kpi_to_project,
    get_kpis_for_project,
    update_kpi,
    delete_kpi,
)

# Team Members
from .cruds.team_members_crud import (
    add_team_member,
    get_team_member_by_id,
    get_all_team_members,
    update_team_member,
    delete_team_member,
)

# Template Categories
from .cruds.template_categories_crud import (
    add_template_category,
    get_template_category_by_id,
    get_template_category_by_name,
    get_all_template_categories,
    update_template_category,
    delete_template_category,
    get_template_category_details,
)

# Templates
from .cruds.templates_crud import (
    add_template,
    get_template_by_id,
    get_templates_by_type,
    update_template,
    delete_template,
    get_all_templates,
    get_distinct_template_languages,
    get_distinct_template_types,
    get_filtered_templates,
    get_template_details_for_preview,
    get_template_path_info,
    delete_template_and_get_file_info,
    set_default_template_by_id,
    get_template_by_type_lang_default,
    get_all_file_based_templates,
    get_templates_by_category_id,
    add_default_template_if_not_exists, # Often used during seeding
)

# Users
from .cruds.users_crud import (
    add_user,
    get_user_by_id,
    get_user_by_email,
    get_user_by_username,
    update_user,
    verify_user_password,
    delete_user,
    get_all_users,
)

# SAV Tickets
from .cruds.sav_tickets_crud import ( # Assuming sav_tickets_crud.py
    add_sav_ticket,
    get_sav_ticket_by_id,
    get_sav_tickets_for_client,
    update_sav_ticket,
    delete_sav_ticket,
)

# Important Dates
from .cruds.important_dates_crud import ( # Assuming important_dates_crud.py
    add_important_date,
    get_important_date_by_id,
    get_all_important_dates,
    update_important_date,
    delete_important_date,
)

# Scheduled Emails & Reminders
from .cruds.scheduled_emails_crud import ( # Assuming scheduled_emails_crud.py
    add_scheduled_email,
    get_scheduled_email_by_id,
    get_pending_scheduled_emails,
    update_scheduled_email_status,
    delete_scheduled_email,
    add_email_reminder,
    get_pending_reminders,
    update_reminder_status,
    delete_email_reminder,
)

# SmtpConfigs
from .cruds.smtp_configs_crud import ( # Assuming smtp_configs_crud.py
    add_smtp_config,
    get_smtp_config_by_id,
    get_default_smtp_config,
    get_all_smtp_configs,
    update_smtp_config,
    delete_smtp_config,
    set_default_smtp_config,
)



# --- Transporters (Moved in previous step) ---
from .cruds.transporters_crud import (
    add_transporter,
    get_transporter_by_id,
    get_all_transporters,
    update_transporter,
    delete_transporter,
)

# List all functions to be made available through `from db import *`
__all__ = [
    # from init_schema
    "initialize_database",
    # from connection
    "get_db_connection",
    # from utils
    "format_currency",
    "get_document_context_data",
    # from activity_logs_crud
    "add_activity_log", "get_activity_logs", "get_activity_log_by_id",
    # from application_settings_crud
    "get_setting", "set_setting",
    # from client_assigned_personnel_crud
    "assign_personnel_to_client", "get_assigned_personnel_for_client",
    "unassign_personnel_from_client",
    # from client_documents_crud
    "add_client_document", "get_document_by_id", "get_documents_for_client",
    "get_documents_for_project", "update_client_document", "delete_client_document",
    # from client_freight_forwarders_crud
    "assign_forwarder_to_client", "get_assigned_forwarders_for_client",
    "unassign_forwarder_from_client",
    # from client_project_products_crud
    "add_product_to_client_or_project", "update_client_project_product",
    "remove_product_from_client_or_project", "get_client_project_product_by_id",
    "get_products_for_client_or_project",
    # from client_transporters_crud
    "assign_transporter_to_client", "get_assigned_transporters_for_client",
    "unassign_transporter_from_client", "update_client_transporter_email_status",
    # from clients_crud
    "add_client", "get_client_by_id", "get_all_clients", "update_client", "delete_client",
    "get_all_clients_with_details", "get_active_clients_count", "get_client_counts_by_country",
    "get_client_segmentation_by_city", "get_client_segmentation_by_status",
    "get_client_segmentation_by_category", "get_clients_by_archival_status",
    "get_active_clients_per_country", "add_client_note", "get_client_notes",
    # from companies_crud
    "add_company", "get_company_by_id", "get_all_companies", "update_company", "delete_company",
    "set_default_company", "get_default_company",
    # from company_personnel_crud
    "add_company_personnel", "get_personnel_for_company", "update_company_personnel", "delete_company_personnel",
    # from contacts_crud
    "get_contacts_for_client", "add_contact", "get_contact_by_id", "get_contact_by_email",
    "get_all_contacts", "update_contact", "delete_contact", "add_contact_list", "add_contact_to_list",
    "delete_contact_list", "get_all_contact_lists", "get_contact_list_by_id", "get_contacts_in_list",
    "remove_contact_from_list", "link_contact_to_client", "unlink_contact_from_client",
    "get_contacts_for_client_count", "get_clients_for_contact", "get_specific_client_contact_link_details",
    "update_client_contact_link",
    # from cover_pages_crud
    "add_cover_page", "get_cover_page_by_id", "get_cover_pages_for_client", "get_cover_pages_for_project",
    "update_cover_page", "delete_cover_page", "get_cover_pages_for_user",
    # from freight_forwarders_crud
    "add_freight_forwarder", "get_freight_forwarder_by_id", "get_all_freight_forwarders",
    "update_freight_forwarder", "delete_freight_forwarder",
    # from google_sync_crud
    "add_user_google_account", "get_user_google_account_by_user_id", "get_user_google_account_by_google_account_id",
    "get_user_google_account_by_id", "update_user_google_account", "delete_user_google_account",
    "get_all_user_google_accounts", "add_contact_sync_log", "get_contact_sync_log_by_local_contact",
    "get_contact_sync_log_by_google_contact_id", "get_contact_sync_log_by_id", "update_contact_sync_log",
    "delete_contact_sync_log", "get_contacts_pending_sync", "get_all_sync_logs_for_account",
    # from kpis_crud (stubs)
    "get_kpis_for_project", "add_kpi_to_project", "update_kpi", "delete_kpi", "add_kpi", "get_kpi_by_id",
    # from locations_crud
    "get_country_by_name", "get_country_by_id", "get_or_add_country", "add_country", "get_all_countries",
    "get_city_by_name_and_country_id", "get_city_by_id", "add_city", "get_or_add_city", "get_all_cities",
    # from milestones_crud
    "get_milestones_for_project", "add_milestone", "get_milestone_by_id", "update_milestone", "delete_milestone",
    # from partners_crud
    "add_partner_category", "get_partner_category_by_id", "get_partner_category_by_name",
    "get_all_partner_categories", "update_partner_category", "delete_partner_category",
    "get_or_add_partner_category", "add_partner", "get_partner_by_id", "get_partner_by_email",
    "get_all_partners", "update_partner", "delete_partner", "get_partners_by_category_id",
    "add_partner_contact", "get_partner_contact_by_id", "get_contacts_for_partner",
    "update_partner_contact", "delete_partner_contact", "delete_contacts_for_partner",
    "link_partner_to_category", "unlink_partner_from_category", "get_categories_for_partner",
    "get_partners_in_category", "add_partner_document", "get_documents_for_partner",
    "get_partner_document_by_id", "update_partner_document", "delete_partner_document",
    # from product_media_links_crud
    "link_media_to_product", "get_media_links_for_product", "get_media_link_by_ids",
    "get_media_link_by_link_id", "update_media_link", "unlink_media_from_product",
    "unlink_media_by_ids", "unlink_all_media_from_product", "update_product_media_display_orders",
    # from products_crud
    "get_product_by_id_details", "add_product", "get_product_by_name", "get_all_products",
    "update_product", "delete_product", "get_products", "update_product_price",
    "get_products_by_name_pattern", "get_all_products_for_selection_filtered",
    "get_total_products_count", "add_or_update_product_dimension", "get_product_dimension",
    "delete_product_dimension", "add_product_equivalence", "get_equivalent_products",
    "get_all_product_equivalencies", "remove_product_equivalence",
    # from projects_crud
    "add_project", "get_project_by_id", "delete_project", "get_projects_by_client_id", "update_project", "get_all_projects", "get_total_projects_count", # Already correct
    # from status_settings_crud
    "get_status_setting_by_name", "get_status_setting_by_id", "get_all_status_settings",
    # from tasks_crud (placeholders)
    "add_task", "get_task_by_id", "get_tasks_by_project_id", "update_task", "delete_task", "get_tasks_by_assignee_id", "get_all_tasks", "add_task_dependency", "remove_task_dependency",

    # KPIs
    "add_kpi_to_project", "get_kpis_for_project", "update_kpi", "delete_kpi", "add_kpi", "get_kpi_by_id", # Added get_kpi_by_id here too
    # Team Members
    "add_team_member", "get_team_member_by_id", "get_all_team_members", "update_team_member", "delete_team_member",
    # Template Categories
    "add_template_category", "get_template_category_by_id", "get_template_category_by_name",
    "get_all_template_categories", "update_template_category", "delete_template_category", "get_template_category_details",
    # Templates
    "add_template", "get_template_by_id", "get_templates_by_type", "update_template", "delete_template",
    "get_all_templates", "get_distinct_template_languages", "get_distinct_template_types", "get_filtered_templates",
    "get_template_details_for_preview", "get_template_path_info", "delete_template_and_get_file_info",
    "set_default_template_by_id", "get_template_by_type_lang_default", "get_all_file_based_templates",
    "get_templates_by_category_id", "add_default_template_if_not_exists",
    # Users
    "add_user", "get_user_by_id", "get_user_by_email", "get_user_by_username", "update_user",
    "verify_user_password", "delete_user", "get_all_users",
    # SAV Tickets
    "add_sav_ticket", "get_sav_ticket_by_id", "get_sav_tickets_for_client", "update_sav_ticket", "delete_sav_ticket",
    # Important Dates
    "add_important_date", "get_important_date_by_id", "get_all_important_dates", "update_important_date", "delete_important_date",
    # Scheduled Emails & Reminders
    "add_scheduled_email", "get_scheduled_email_by_id", "get_pending_scheduled_emails", "update_scheduled_email_status", "delete_scheduled_email",
    "add_email_reminder", "get_pending_reminders", "update_reminder_status", "delete_email_reminder",
    # SmtpConfigs
    "add_smtp_config", "get_smtp_config_by_id", "get_default_smtp_config", "get_all_smtp_configs",
    "update_smtp_config", "delete_smtp_config", "set_default_smtp_config",

    # Transporters
    "add_transporter", "get_transporter_by_id", "get_all_transporters", "update_transporter", "delete_transporter",
    # from proforma_invoices_crud
    "create_proforma_invoice", "get_proforma_invoice_by_id", "get_proforma_invoice_by_number",
    "list_proforma_invoices", "update_proforma_invoice", "delete_proforma_invoice",
    "create_proforma_invoice_item", "get_proforma_invoice_item_by_id",
    "update_proforma_invoice_item", "delete_proforma_invoice_item",
]

# Note: financial_reports_crud.py and media_items_crud.py were not found and are thus not included.
# If these modules are created later, their functions will need to be added here and to __all__.
# The _manage_conn decorator from generic_crud is not exposed as it's internal.
# Placeholder functions from projects_crud and tasks_crud are included for completeness of the current structure.
# Stubs from contacts_crud and kpis_crud are also included.
# The 'get_product_by_id' from products_crud was renamed to 'get_product_by_id_details' to avoid
# potential naming conflicts if a simpler 'get_product_by_id' (without media links) were desired at the top level.
# This can be adjusted based on actual usage patterns.
print(f"DB Facade Initialized. {len(__all__)} functions/variables exposed in __all__.")
