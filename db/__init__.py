"""
DB Package Facade
This __init__.py re-exports all public CRUD functions and other key DB utilities.
"""

# --- Utilities ---
from .utils import get_document_context_data, get_db_connection, format_currency
# Note: _get_batch_products_and_equivalents is internal to utils

# --- CA (Certificate Authority / DB Initialization) ---
from .ca import initialize_database

# --- CRUDs ---

# Application Settings
from .cruds.application_settings_crud import (
    get_setting,
    set_setting,
)

# Clients
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
    add_client_note, # Belongs here or a separate client_notes_crud.py? Assuming here for now.
    get_client_notes, # Belongs here or a separate client_notes_crud.py? Assuming here for now.
)

# Companies
from .cruds.companies_crud import (
    add_company,
    get_company_by_id,
    get_all_companies,
    update_company,
    delete_company,
    set_default_company,
    get_default_company,
)

# Company Personnel
from .cruds.company_personnel_crud import (
    add_company_personnel,
    get_personnel_for_company,
    update_company_personnel,
    delete_company_personnel,
)

# Contacts
from .cruds.contacts_crud import (
    add_contact,
    get_contact_by_id,
    get_contact_by_email,
    get_all_contacts,
    update_contact,
    delete_contact,
    link_contact_to_client,
    unlink_contact_from_client,
    get_contacts_for_client,
    get_clients_for_contact,
    get_contacts_for_client_count,
    update_client_contact_link,
    get_specific_client_contact_link_details,
)

# Client Documents
from .cruds.client_documents_crud import (
    add_client_document,
    get_document_by_id,
    get_documents_for_client,
    get_documents_for_project,
    update_client_document,
    delete_client_document,
    add_client_document_note,
    get_client_document_notes,
    update_client_document_note,
    delete_client_document_note,
    get_client_document_note_by_id,
)


# Client Project Products
from .cruds.client_project_products_crud import (
    add_product_to_client_or_project,
    get_products_for_client_or_project,
    update_client_project_product,
    remove_product_from_client_or_project,
    get_client_project_product_by_id,
)

# Cover Page Templates
from .cruds.cover_page_templates_crud import (
    add_cover_page_template,
    get_cover_page_template_by_id,
    get_cover_page_template_by_name,
    get_all_cover_page_templates,
    update_cover_page_template,
    delete_cover_page_template,
)

# Cover Pages
from .cruds.cover_pages_crud import (
    add_cover_page,
    get_cover_page_by_id,
    get_cover_pages_for_client,
    get_cover_pages_for_project,
    update_cover_page,
    delete_cover_page,
    get_cover_pages_for_user,
)

# Generic (if any public functions)
# from .cruds.generic_crud import ...


# Locations (Countries, Cities)
from .cruds.locations_crud import (
    get_all_countries,
    get_country_by_id,
    get_country_by_name,
    add_country,
    get_all_cities,
    get_city_by_id,
    get_city_by_name_and_country_id,
    add_city,
)

# Partners
from .cruds.partners_crud import (
    add_partner_category,
    get_all_partner_categories,
    add_partner,
    get_partner_by_id,
    get_all_partners,
    update_partner,
    delete_partner,
    get_partners_by_category_id,
)


# Products
from .cruds.products_crud import (
    add_product,
    get_product_by_id,
    get_product_by_name,
    get_all_products,
    update_product,
    delete_product,
    get_products, # often a more filtered version of get_all_products
    update_product_price,
    get_products_by_name_pattern,
    get_all_products_for_selection_filtered, # or get_all_products_for_selection_filtered
    add_product_equivalence,
    get_equivalent_products,
    get_all_product_equivalencies,
    remove_product_equivalence,
    add_or_update_product_dimension, # ProductDimensions
    get_product_dimension,
    delete_product_dimension,
)

# Projects
from .cruds.projects_crud import (
    add_project,
    get_project_by_id,
    get_projects_for_client,
    update_project,
    delete_project,
)

# Tasks
from .cruds.tasks_crud import (
    add_task,
    get_task_by_id,
    get_tasks_by_project_id,
    update_task,
    delete_task,
    get_all_tasks,
    get_tasks_by_assignee_id,
)

# KPIs (often linked to projects or other entities)
from .cruds.kpis_crud import ( # Assuming a kpis_crud.py exists
    add_kpi,
    get_kpi_by_id,
    get_kpis_for_project,
    update_kpi,
    delete_kpi,
)


# Status Settings
from .cruds.status_settings_crud import (
    get_all_status_settings,
    get_status_setting_by_id,
    get_status_setting_by_name,
    add_status_setting, # Assuming this exists
    update_status_setting, # Assuming this exists
    delete_status_setting, # Assuming this exists
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

# Activity Log
from .cruds.activity_log_crud import ( # Assuming activity_log_crud.py
    add_activity_log,
    get_activity_logs,
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

# --- FreightForwarders (Moved in previous step) ---
from .cruds.freight_forwarders_crud import (
    add_freight_forwarder,
    get_freight_forwarder_by_id,
    get_all_freight_forwarders,
    update_freight_forwarder,
    delete_freight_forwarder,
)

# --- Client_AssignedPersonnel (Moved in previous step) ---
from .cruds.client_assigned_personnel_crud import (
    assign_personnel_to_client,
    get_assigned_personnel_for_client,
    unassign_personnel_from_client,
)

# --- Client_Transporters (Moved in previous step) ---
from .cruds.client_transporters_crud import (
    assign_transporter_to_client,
    get_assigned_transporters_for_client,
    unassign_transporter_from_client,
    update_client_transporter_email_status,
)

# --- Client_FreightForwarders (Moved in previous step) ---
from .cruds.client_freight_forwarders_crud import (
    assign_forwarder_to_client,
    get_assigned_forwarders_for_client,
    unassign_forwarder_from_client,
)


__all__ = [
    # Utilities
    "get_document_context_data", "get_db_connection", "format_currency",
    # CA
    "initialize_database",
    # Application Settings
    "get_setting", "set_setting",
    # Clients
    "add_client", "get_client_by_id", "get_all_clients", "update_client", "delete_client",
    "get_all_clients_with_details", "get_active_clients_count", "get_client_counts_by_country",
    "get_client_segmentation_by_city", "get_client_segmentation_by_status",
    "get_client_segmentation_by_category", "get_clients_by_archival_status",
    "add_client_note", "get_client_notes",
    # Companies
    "add_company", "get_company_by_id", "get_all_companies", "update_company", "delete_company",
    "set_default_company", "get_default_company",
    # Company Personnel
    "add_company_personnel", "get_personnel_for_company", "update_company_personnel", "delete_company_personnel",
    # Contacts
    "add_contact", "get_contact_by_id", "get_contact_by_email", "get_all_contacts", "update_contact", "delete_contact",
    "link_contact_to_client", "unlink_contact_from_client", "get_contacts_for_client", "get_clients_for_contact",
    "get_contacts_for_client_count", "update_client_contact_link", "get_specific_client_contact_link_details",
    # Client Documents
    "add_client_document", "get_document_by_id", "get_documents_for_client", "get_documents_for_project",
    "update_client_document", "delete_client_document",
    "add_client_document_note", "get_client_document_notes", "update_client_document_note",
    "delete_client_document_note", "get_client_document_note_by_id",
    # Client Project Products
    "add_product_to_client_or_project", "get_products_for_client_or_project", "update_client_project_product",
    "remove_product_from_client_or_project", "get_client_project_product_by_id",
    # Cover Page Templates
    "add_cover_page_template", "get_cover_page_template_by_id", "get_cover_page_template_by_name",
    "get_all_cover_page_templates", "update_cover_page_template", "delete_cover_page_template",
    # Cover Pages
    "add_cover_page", "get_cover_page_by_id", "get_cover_pages_for_client", "get_cover_pages_for_project",
    "update_cover_page", "delete_cover_page", "get_cover_pages_for_user",
    # Locations
    "get_all_countries", "get_country_by_id", "get_country_by_name", "add_country", "get_all_cities",
    "get_city_by_id", "get_city_by_name_and_country_id", "add_city",
    # Partners
    "add_partner_category", "get_all_partner_categories", "add_partner", "get_partner_by_id",
    "get_all_partners", "update_partner", "delete_partner", "get_partners_by_category_id",
    # Products
    "add_product", "get_product_by_id", "get_product_by_name", "get_all_products", "update_product", "delete_product",
    "get_products", "update_product_price", "get_products_by_name_pattern", "get_all_products_for_selection_filtered",
    "add_product_equivalence", "get_equivalent_products", "get_all_product_equivalencies", "remove_product_equivalence",
    "add_or_update_product_dimension", "get_product_dimension", "delete_product_dimension",
    # Projects
    "add_project", "get_project_by_id", "get_projects_for_client", "update_project", "delete_project",
    # Tasks
    "add_task", "get_task_by_id", "get_tasks_by_project_id", "update_task", "delete_task", "get_all_tasks", "get_tasks_by_assignee_id",
    # KPIs
    "add_kpi", "get_kpi_by_id", "get_kpis_for_project", "update_kpi", "delete_kpi",
    # Status Settings
    "get_all_status_settings", "get_status_setting_by_id", "get_status_setting_by_name",
    "add_status_setting", "update_status_setting", "delete_status_setting",
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
    "verify_user_password", "delete_user",
    # SAV Tickets
    "add_sav_ticket", "get_sav_ticket_by_id", "get_sav_tickets_for_client", "update_sav_ticket", "delete_sav_ticket",
    # Important Dates
    "add_important_date", "get_important_date_by_id", "get_all_important_dates", "update_important_date", "delete_important_date",
    # Scheduled Emails & Reminders
    "add_scheduled_email", "get_scheduled_email_by_id", "get_pending_scheduled_emails", "update_scheduled_email_status", "delete_scheduled_email",
    "add_email_reminder", "get_pending_reminders", "update_reminder_status", "delete_email_reminder",
    # Activity Log
    "add_activity_log", "get_activity_logs",
    # SmtpConfigs
    "add_smtp_config", "get_smtp_config_by_id", "get_default_smtp_config", "get_all_smtp_configs",
    "update_smtp_config", "delete_smtp_config", "set_default_smtp_config",
    # Transporters
    "add_transporter", "get_transporter_by_id", "get_all_transporters", "update_transporter", "delete_transporter",
    # FreightForwarders
    "add_freight_forwarder", "get_freight_forwarder_by_id", "get_all_freight_forwarders", "update_freight_forwarder", "delete_freight_forwarder",
    # Client_AssignedPersonnel
    "assign_personnel_to_client", "get_assigned_personnel_for_client", "unassign_personnel_from_client",
    # Client_Transporters
    "assign_transporter_to_client", "get_assigned_transporters_for_client", "unassign_transporter_from_client", "update_client_transporter_email_status",
    # Client_FreightForwarders
    "assign_forwarder_to_client", "get_assigned_forwarders_for_client", "unassign_forwarder_from_client",
]
