import sqlite3
import uuid
import hashlib # Keep if any remaining stubs might imply its use, or if imported functions need it re-exported.
from datetime import datetime
import json
import os
import logging

# Import from generic_crud
from .cruds.generic_crud import _manage_conn, get_db_connection

# Import from entity-specific CRUD files
# These imports should cover all functions previously implemented or stubbed in crud.py
# and now residing in their respective cruds/ files.

from .cruds.users_crud import (
    add_user, get_user_by_id, get_user_by_username, get_user_by_email,
    update_user, delete_user, verify_user_password
)
from .cruds.companies_crud import (
    add_company, get_company_by_id, get_all_companies, update_company,
    delete_company, set_default_company, get_default_company
)
from .cruds.company_personnel_crud import (
    add_company_personnel, get_personnel_for_company,
    update_company_personnel, delete_company_personnel
)
from .cruds.application_settings_crud import (
    get_setting, set_setting
)
from .cruds.template_categories_crud import (
    add_template_category, get_template_category_by_id, get_template_category_by_name,
    get_all_template_categories, update_template_category, delete_template_category,
    get_template_category_details
)
from .cruds.templates_crud import (
    add_template, add_default_template_if_not_exists, get_template_by_id,
    get_templates_by_type, get_templates_by_category_id, update_template, delete_template,
    get_distinct_template_languages, get_distinct_template_types,
    get_filtered_templates, get_template_details_for_preview,
    get_template_path_info, delete_template_and_get_file_info,
    set_default_template_by_id, get_template_by_type_lang_default,
    get_all_templates, get_distinct_languages_for_template_type,
    get_all_file_based_templates
)
from .cruds.cover_page_templates_crud import (
    add_cover_page_template, get_cover_page_template_by_id,
    get_cover_page_template_by_name, get_all_cover_page_templates,
    update_cover_page_template, delete_cover_page_template
)
from .cruds.locations_crud import (
    get_country_by_name, get_country_by_id, get_or_add_country,
    get_city_by_name_and_country_id, get_city_by_id, get_or_add_city,
    get_all_countries, get_all_cities # Added get_all_*
)
from .cruds.status_settings_crud import (
    get_status_setting_by_name, get_status_setting_by_id, get_all_status_settings # Added get_all_*
)
from .cruds.clients_crud import (
    add_client, get_client_by_id, get_all_clients, update_client, delete_client,
    get_all_clients_with_details, get_active_clients_count,
    get_client_counts_by_country, get_client_segmentation_by_city,
    get_client_segmentation_by_status, get_client_segmentation_by_category,
    get_clients_by_archival_status,
    add_client_note, get_client_notes # ClientNotes moved here
)
from .cruds.products_crud import (
    add_product, get_product_by_id, get_product_by_name, get_all_products,
    update_product, delete_product, get_products, update_product_price,
    get_products_by_name_pattern, get_all_products_for_selection,
    get_all_products_for_selection_filtered, get_total_products_count,
    add_or_update_product_dimension, get_product_dimension, delete_product_dimension,
    add_product_equivalence, get_equivalent_products, get_all_product_equivalencies,
    remove_product_equivalence
)
from .cruds.client_project_products_crud import (
    add_product_to_client_or_project, get_products_for_client_or_project,
    update_client_project_product, remove_product_from_client_or_project,
    get_client_project_product_by_id
)
from .cruds.projects_crud import (
    add_project, get_project_by_id, get_projects_by_client_id, get_all_projects,
    update_project, delete_project, get_total_projects_count, get_active_projects_count
)
from .cruds.contacts_crud import (
    add_contact, get_contact_by_id, get_contact_by_email, get_all_contacts,
    update_contact, delete_contact,
    link_contact_to_client, unlink_contact_from_client, get_contacts_for_client,
    get_contacts_for_client_count, get_clients_for_contact,
    get_specific_client_contact_link_details, update_client_contact_link
    # Stubs for ContactList related functions will be added below
)
from .cruds.client_documents_crud import (
    add_client_document, get_document_by_id, get_documents_for_client,
    get_documents_for_project, update_client_document, delete_client_document,
    add_client_document_note, get_client_document_note_by_id,
    get_client_document_notes, update_client_document_note, delete_client_document_note
)
from .cruds.cover_pages_crud import (
    add_cover_page, get_cover_page_by_id, get_cover_pages_for_client,
    get_cover_pages_for_project, update_cover_page, delete_cover_page,
    get_cover_pages_for_user
)
from .cruds.tasks_crud import (
    add_task, get_task_by_id, get_tasks_by_project_id, update_task,
    delete_task, get_all_tasks, get_tasks_by_assignee_id
)
from .cruds.team_members_crud import (
    add_team_member, get_team_member_by_id, get_all_team_members,
    update_team_member, delete_team_member
)
from .cruds.sav_tickets_crud import (
    add_sav_ticket, get_sav_ticket_by_id, get_sav_tickets_for_client,
    update_sav_ticket, delete_sav_ticket
)
from .cruds.important_dates_crud import (
    add_important_date, get_important_date_by_id, get_all_important_dates,
    update_important_date, delete_important_date
)
from .cruds.transporters_crud import (
    add_transporter, get_transporter_by_id, get_all_transporters,
    update_transporter, delete_transporter
)
from .cruds.freight_forwarders_crud import (
    add_freight_forwarder, get_freight_forwarder_by_id, get_all_freight_forwarders,
    update_freight_forwarder, delete_freight_forwarder
)
from .cruds.client_assigned_personnel_crud import (
    assign_personnel_to_client, get_assigned_personnel_for_client,
    unassign_personnel_from_client
)
from .cruds.client_transporters_crud import (
    assign_transporter_to_client, get_assigned_transporters_for_client,
    unassign_transporter_from_client
)
from .cruds.client_freight_forwarders_crud import (
    assign_forwarder_to_client, get_assigned_forwarders_for_client,
    unassign_forwarder_from_client
)
from .cruds.kpis_crud import (
    add_kpi, get_kpi_by_id, get_kpis_for_project, update_kpi, delete_kpi
)
from .cruds.google_sync_crud import (
    add_user_google_account, get_user_google_account_by_user_id,
    get_user_google_account_by_google_account_id, get_user_google_account_by_id,
    update_user_google_account, delete_user_google_account, get_all_user_google_accounts,
    add_contact_sync_log, get_contact_sync_log_by_local_contact,
    get_contact_sync_log_by_google_contact_id, get_contact_sync_log_by_id,
    update_contact_sync_log, delete_contact_sync_log,
    get_contacts_pending_sync, get_all_sync_logs_for_account
)
from .cruds.partners_crud import (
    add_partner_category, get_partner_category_by_id, get_partner_category_by_name,
    get_all_partner_categories, update_partner_category, delete_partner_category,
    # get_or_add_partner_category, # This was a helper in partners_crud, not usually exposed
    add_partner, get_partner_by_id, get_all_partners, update_partner, delete_partner,
    get_partners_by_category_id, get_partner_by_email,
    add_partner_contact, get_partner_contact_by_id, get_contacts_for_partner,
    update_partner_contact, delete_partner_contact, delete_contacts_for_partner,
    link_partner_to_category, unlink_partner_from_category,
    get_categories_for_partner, # Already have get_partners_by_category_id (same as get_partners_in_category)
    # get_partners_in_category, # Renamed/covered by get_partners_by_category_id
    add_partner_document, get_documents_for_partner, get_partner_document_by_id,
    update_partner_document, delete_partner_document
)
from .cruds.activity_logs_crud import ( # Assuming this file exists for the stub
    add_activity_log, get_activity_logs
)

# STUB Functions that remain (implement or remove these in future tasks)
# These were the ones listed with "logging.warning" in the original crud.py
# and not explicitly moved to a specific cruds file yet.

# ContactLists stubs (related to contacts_crud.py but kept as stubs here for now if not implemented there)
@_manage_conn
def add_contact_list(data: dict, conn: sqlite3.Connection = None) -> int | None:
    logging.warning(f"Called stub function add_contact_list with data: {data}. Full implementation is missing.")
    return None

@_manage_conn
def add_contact_to_list(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function add_contact_to_list with data: {data}. Full implementation is missing.")
    return None

@_manage_conn
def delete_contact_list(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function delete_contact_list with data: {data}. Full implementation is missing.")
    return None

@_manage_conn
def get_all_contact_lists(data: dict = None, conn: sqlite3.Connection = None) -> object | None: # data dict often not used in "get_all" stubs
    logging.warning(f"Called stub function get_all_contact_lists with data: {data}. Full implementation is missing.")
    return None

@_manage_conn
def get_contact_list_by_id(data: dict, conn: sqlite3.Connection = None) -> object | None: # data dict for ID
    logging.warning(f"Called stub function get_contact_list_by_id with data: {data}. Full implementation is missing.")
    return None

@_manage_conn
def get_contacts_in_list(data: dict, conn: sqlite3.Connection = None) -> object | None: # data dict for list_id
    logging.warning(f"Called stub function get_contacts_in_list with data: {data}. Full implementation is missing.")
    return None

@_manage_conn
def remove_contact_from_list(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function remove_contact_from_list with data: {data}. Full implementation is missing.")
    return None

@_manage_conn
def update_contact_list(data: dict, conn: sqlite3.Connection = None) -> object | None:
    logging.warning(f"Called stub function update_contact_list with data: {data}. Full implementation is missing.")
    return None

# SmtpConfigs and ScheduledEmails related stubs (assuming these cruds files exist or will be made)
from .cruds.smtp_configs_crud import (
    add_smtp_config, get_smtp_config_by_id, get_default_smtp_config, get_all_smtp_configs,
    update_smtp_config, delete_smtp_config, set_default_smtp_config
)
from .cruds.scheduled_emails_crud import (
    add_scheduled_email, get_scheduled_email_by_id, get_pending_scheduled_emails,
    update_scheduled_email_status, delete_scheduled_email,
    add_email_reminder, get_pending_reminders, update_reminder_status, delete_email_reminder
)


# Define __all__ based on imported and remaining stub functions
# Start with a list of all imported function names, then add stubs.
imported_function_names = [
    # Users
    'add_user', 'get_user_by_id', 'get_user_by_username', 'get_user_by_email',
    'update_user', 'delete_user', 'verify_user_password',
    # Companies
    'add_company', 'get_company_by_id', 'get_all_companies', 'update_company',
    'delete_company', 'set_default_company', 'get_default_company',
    # CompanyPersonnel
    'add_company_personnel', 'get_personnel_for_company',
    'update_company_personnel', 'delete_company_personnel',
    # ApplicationSettings
    'get_setting', 'set_setting',
    # TemplateCategories
    'add_template_category', 'get_template_category_by_id', 'get_template_category_by_name',
    'get_all_template_categories', 'update_template_category', 'delete_template_category',
    'get_template_category_details',
    # Templates
    'add_template', 'add_default_template_if_not_exists', 'get_template_by_id',
    'get_templates_by_type', 'get_templates_by_category_id', 'update_template', 'delete_template',
    'get_distinct_template_languages', 'get_distinct_template_types',
    'get_filtered_templates', 'get_template_details_for_preview',
    'get_template_path_info', 'delete_template_and_get_file_info',
    'set_default_template_by_id', 'get_template_by_type_lang_default',
    'get_all_templates', 'get_distinct_languages_for_template_type',
    'get_all_file_based_templates',
    # CoverPageTemplates
    'add_cover_page_template', 'get_cover_page_template_by_id',
    'get_cover_page_template_by_name', 'get_all_cover_page_templates',
    'update_cover_page_template', 'delete_cover_page_template',
    # Locations
    'get_country_by_name', 'get_country_by_id', 'get_or_add_country', 'get_all_countries',
    'get_city_by_name_and_country_id', 'get_city_by_id', 'get_or_add_city', 'get_all_cities',
    # StatusSettings
    'get_status_setting_by_name', 'get_status_setting_by_id', 'get_all_status_settings',
    # Clients & ClientNotes
    'add_client', 'get_client_by_id', 'get_all_clients', 'update_client', 'delete_client',
    'get_all_clients_with_details', 'get_active_clients_count',
    'get_client_counts_by_country', 'get_client_segmentation_by_city',
    'get_client_segmentation_by_status', 'get_client_segmentation_by_category',
    'get_clients_by_archival_status', 'add_client_note', 'get_client_notes',
    # Products & related
    'add_product', 'get_product_by_id', 'get_product_by_name', 'get_all_products',
    'update_product', 'delete_product', 'get_products', 'update_product_price',
    'get_products_by_name_pattern', 'get_all_products_for_selection',
    'get_all_products_for_selection_filtered', 'get_total_products_count',
    'add_or_update_product_dimension', 'get_product_dimension', 'delete_product_dimension',
    'add_product_equivalence', 'get_equivalent_products', 'get_all_product_equivalencies',
    'remove_product_equivalence',
    # ClientProjectProducts
    'add_product_to_client_or_project', 'get_products_for_client_or_project',
    'update_client_project_product', 'remove_product_from_client_or_project',
    'get_client_project_product_by_id',
    # Projects
    'add_project', 'get_project_by_id', 'get_projects_by_client_id', 'get_all_projects',
    'update_project', 'delete_project', 'get_total_projects_count', 'get_active_projects_count',
    # Contacts & ClientContacts
    'add_contact', 'get_contact_by_id', 'get_contact_by_email', 'get_all_contacts',
    'update_contact', 'delete_contact', 'link_contact_to_client', 'unlink_contact_from_client',
    'get_contacts_for_client', 'get_contacts_for_client_count', 'get_clients_for_contact',
    'get_specific_client_contact_link_details', 'update_client_contact_link',
    # ClientDocuments & ClientDocumentNotes
    'add_client_document', 'get_document_by_id', 'get_documents_for_client',
    'get_documents_for_project', 'update_client_document', 'delete_client_document',
    'add_client_document_note', 'get_client_document_note_by_id',
    'get_client_document_notes', 'update_client_document_note', 'delete_client_document_note',
    # CoverPages
    'add_cover_page', 'get_cover_page_by_id', 'get_cover_pages_for_client',
    'get_cover_pages_for_project', 'update_cover_page', 'delete_cover_page',
    'get_cover_pages_for_user',
    # Tasks
    'add_task', 'get_task_by_id', 'get_tasks_by_project_id', 'update_task',
    'delete_task', 'get_all_tasks', 'get_tasks_by_assignee_id',
    # TeamMembers
    'add_team_member', 'get_team_member_by_id', 'get_all_team_members',
    'update_team_member', 'delete_team_member',
    # SAVTickets
    'add_sav_ticket', 'get_sav_ticket_by_id', 'get_sav_tickets_for_client',
    'update_sav_ticket', 'delete_sav_ticket',
    # ImportantDates
    'add_important_date', 'get_important_date_by_id', 'get_all_important_dates',
    'update_important_date', 'delete_important_date',
    # Transporters
    'add_transporter', 'get_transporter_by_id', 'get_all_transporters',
    'update_transporter', 'delete_transporter',
    # FreightForwarders
    'add_freight_forwarder', 'get_freight_forwarder_by_id', 'get_all_freight_forwarders',
    'update_freight_forwarder', 'delete_freight_forwarder',
    # Client_AssignedPersonnel
    'assign_personnel_to_client', 'get_assigned_personnel_for_client',
    'unassign_personnel_from_client',
    # Client_Transporters
    'assign_transporter_to_client', 'get_assigned_transporters_for_client',
    'unassign_transporter_from_client',
    # Client_FreightForwarders
    'assign_forwarder_to_client', 'get_assigned_forwarders_for_client',
    'unassign_forwarder_from_client',
    # KPIs
    'add_kpi', 'get_kpi_by_id', 'get_kpis_for_project', 'update_kpi', 'delete_kpi',
    # GoogleSync
    'add_user_google_account', 'get_user_google_account_by_user_id',
    'get_user_google_account_by_google_account_id', 'get_user_google_account_by_id',
    'update_user_google_account', 'delete_user_google_account', 'get_all_user_google_accounts',
    'add_contact_sync_log', 'get_contact_sync_log_by_local_contact',
    'get_contact_sync_log_by_google_contact_id', 'get_contact_sync_log_by_id',
    'update_contact_sync_log', 'delete_contact_sync_log',
    'get_contacts_pending_sync', 'get_all_sync_logs_for_account',
    # Partners
    'add_partner_category', 'get_partner_category_by_id', 'get_partner_category_by_name',
    'get_all_partner_categories', 'update_partner_category', 'delete_partner_category',
    'add_partner', 'get_partner_by_id', 'get_all_partners', 'update_partner', 'delete_partner',
    'get_partners_by_category_id', 'get_partner_by_email',
    'add_partner_contact', 'get_partner_contact_by_id', 'get_contacts_for_partner',
    'update_partner_contact', 'delete_partner_contact', 'delete_contacts_for_partner',
    'link_partner_to_category', 'unlink_partner_from_category', 'get_categories_for_partner',
    'add_partner_document', 'get_documents_for_partner', 'get_partner_document_by_id',
    'update_partner_document', 'delete_partner_document',
    # ActivityLog
    'add_activity_log', 'get_activity_logs',
    # SmtpConfigs
    'add_smtp_config', 'get_smtp_config_by_id', 'get_default_smtp_config', 'get_all_smtp_configs',
    'update_smtp_config', 'delete_smtp_config', 'set_default_smtp_config',
    # ScheduledEmails & EmailReminders
    'add_scheduled_email', 'get_scheduled_email_by_id', 'get_pending_scheduled_emails',
    'update_scheduled_email_status', 'delete_scheduled_email',
    'add_email_reminder', 'get_pending_reminders', 'update_reminder_status', 'delete_email_reminder',
]

stub_function_names = [
    'add_contact_list', 'add_contact_to_list', 'delete_contact_list',
    'get_all_contact_lists', 'get_contact_list_by_id', 'get_contacts_in_list',
    'remove_contact_from_list', 'update_contact_list',
]

__all__ = sorted(list(set(imported_function_names + stub_function_names)))
