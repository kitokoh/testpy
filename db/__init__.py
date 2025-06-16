import sys
import os

# Temporarily add the parent directory to sys.path to allow importing from config.py
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from config import DATABASE_PATH
finally:
    # Remove the parent directory from sys.path
    if parent_dir in sys.path:
        sys.path.remove(parent_dir)

DATABASE_NAME = DATABASE_PATH

from .cruds.status_settings_crud import (
    get_status_setting_by_id,
    get_all_status_settings,
    get_status_setting_by_name,
)
from .cruds.templates_crud import get_all_templates, get_template_by_id
from .cruds.client_documents_crud import (
    add_client_document,
    get_document_by_id,
    get_documents_for_client,
    get_client_document_notes,
    add_client_document_note,
    update_client_document_note,
    delete_client_document_note,
    get_client_document_note_by_id,
)
from .utils import get_document_context_data
# For proforma_invoices_crud, we will NOT add them here due to SQLAlchemy vs sqlite3 differences.
# Files using proforma_invoices_crud will import it directly.
from .cruds.application_settings_crud import get_setting, set_setting
from .cruds.projects_crud import (
    get_all_projects,
    get_project_by_id,
    add_project,
    update_project,
    delete_project,
    get_total_projects_count, # Added
    get_active_projects_count, # Added
)
from .cruds.products_crud import get_total_products_count, get_all_products, get_all_products_for_selection_filtered # Added

from .cruds.tasks_crud import (
    get_tasks_by_project_id,
    add_task,
    update_task,
    delete_task,
    get_task_by_id,
    get_tasks_by_assignee_id,
)
from .cruds.kpis_crud import get_kpis_for_project
from .cruds.activity_logs_crud import add_activity_log, get_activity_logs
from .cruds.users_crud import (
    get_user_by_id,
    get_all_users,
    update_user,
    verify_user_password,
)
from .cruds.team_members_crud import (
    get_all_team_members,
    get_team_member_by_id,
    add_team_member,
    update_team_member,
    delete_team_member,
)
from .cruds.clients_crud import ( # Modified
    get_all_clients,
    get_active_clients_count,
    get_client_counts_by_country,
    get_client_segmentation_by_city,
    get_client_segmentation_by_status,
    get_client_segmentation_by_category,
    get_total_clients_count, # Added
    update_client, # Added
)
from .cruds.contacts_crud import (
    get_contacts_for_client,
    add_contact,
    get_contact_by_id,
    get_contact_by_email,
    get_all_contacts,
    update_contact,
    delete_contact,
    link_contact_to_client,
    unlink_contact_from_client,
    get_contacts_for_client_count,
    get_clients_for_contact,
    get_specific_client_contact_link_details,
    update_client_contact_link
)
from .cruds.client_project_products_crud import (
    get_products_for_client_or_project,
    get_distinct_purchase_confirmed_at_for_client,
    add_product_to_client_or_project,
    update_client_project_product,
    remove_product_from_client_or_project,
    get_client_project_product_by_id
)
from .cruds.cover_pages_crud import (
    get_cover_pages_for_client,
    add_cover_page,
    update_cover_page,
    delete_cover_page,
    get_cover_page_by_id,
)
from .cruds.template_categories_crud import get_all_template_categories # Added
from .cruds.templates_crud import ( # Modified
    get_all_file_based_templates,
    get_distinct_template_languages,
    get_distinct_template_types,
    get_filtered_templates
)
from .cruds.cover_page_templates_crud import get_cover_page_template_by_id
from .cruds.milestones_crud import (
    get_milestones_for_project,
    add_milestone,
    get_milestone_by_id,
    update_milestone,
    delete_milestone,
)
from .cruds.companies_crud import ( # Added
    add_company,
    get_company_by_id,
    get_all_companies,
    update_company,
    delete_company,
    set_default_company,
    get_default_company,
)
from .cruds.company_personnel_crud import ( # Added
    add_company_personnel,
    get_personnel_for_company,
    update_company_personnel,
    delete_company_personnel,
)
from .cruds.google_sync_crud import ( # Modified
    get_user_google_account_by_google_account_id,
    update_user_google_account,
    add_user_google_account,
    get_user_google_account_by_user_id,
    get_user_google_account_by_id,
    delete_user_google_account,
    add_contact_sync_log,
    get_contact_sync_log_by_local_contact, # Added
    get_contact_sync_log_by_google_contact_id, # Added
    get_contact_sync_log_by_id, # Added
    update_contact_sync_log, # Added
    delete_contact_sync_log, # Added
    get_contacts_pending_sync, # Added
    get_all_sync_logs_for_account, # Added
)
from .cruds.partners_crud import (
    get_all_partner_categories,
    get_all_partners,
    get_partners_in_category,
    get_categories_for_partner,
    get_partner_by_id,
    get_documents_for_partner,
    add_partner_document,
    update_partner_document,
    delete_partner_document,
    get_partner_document_by_id,
    get_contacts_for_partner,
    add_partner_contact,
    update_partner_contact,
    delete_partner_contact,
    add_partner,
    update_partner,
    delete_partner,
    link_partner_to_category,
    unlink_partner_from_category,
    get_or_add_partner_category,
    get_partner_category_by_name,
    add_partner_category,
    delete_partner_category,
    update_partner_category,
    get_partner_category_by_id, # Added
)
from .cruds.locations_crud import get_all_countries, add_country, get_or_add_country, get_all_cities, add_city, get_or_add_city, get_country_by_id, get_city_by_id, get_country_by_name, get_city_by_name_and_country_id
from .cruds.transporters_crud import get_all_transporters, add_transporter, get_transporter_by_id, update_transporter, delete_transporter
from .cruds.freight_forwarders_crud import get_all_freight_forwarders, add_freight_forwarder, get_freight_forwarder_by_id, update_freight_forwarder, delete_freight_forwarder
from .cruds.client_assigned_personnel_crud import (
    get_assigned_personnel_for_client,
    assign_personnel_to_client,
    unassign_personnel_from_client,
)
from .cruds.client_transporters_crud import (
    get_assigned_transporters_for_client,
    assign_transporter_to_client,
    unassign_transporter_from_client,
    update_client_transporter_email_status,
)
from .cruds.client_freight_forwarders_crud import (
    get_assigned_forwarders_for_client,
    assign_forwarder_to_client,
    unassign_forwarder_from_client,
)
from .cruds.application_settings_crud import get_setting, set_setting
from .init_schema import initialize_database

__all__ = [
    "DATABASE_NAME",
    "get_setting",
    "set_setting",
    "get_status_setting_by_id",
    "get_all_status_settings",
    "get_status_setting_by_name",
    "get_all_templates",
    "get_template_by_id",
    "add_client_document",
    "get_document_by_id",
    "get_documents_for_client",
    "get_client_document_notes",
    "add_client_document_note",
    "update_client_document_note",
    "delete_client_document_note",
    "get_client_document_note_by_id",
    "get_document_context_data",
    "get_all_products", # Added
    "get_all_products_for_selection_filtered", # Added

    "get_all_projects",
    "get_project_by_id",
    "add_project",
    "update_project",
    "delete_project",
    "get_total_projects_count", # Added
    "get_active_projects_count", # Added
    "get_total_products_count", # Added
    "get_tasks_by_project_id",
    "add_task",
    "update_task",
    "delete_task",
    "get_task_by_id",
    "get_tasks_by_assignee_id",
    "get_kpis_for_project",
    "add_activity_log",
    "get_activity_logs",
    "get_user_by_id",
    "get_all_users",
    "update_user",
    "verify_user_password",
    "get_all_team_members",
    "get_team_member_by_id",
    "add_team_member",
    "update_team_member",
    "delete_team_member",
    "get_all_clients",
    "get_active_clients_count",
    "get_total_clients_count", # Added
    "get_client_counts_by_country", # Added
    "get_client_segmentation_by_city", # Added
    "get_client_segmentation_by_status", # Added
    "get_client_segmentation_by_category", # Added
    "update_client", # Added
    "get_contacts_for_client",
    "add_contact",
    "get_contact_by_id",
    "get_contact_by_email",
    "get_all_contacts",
    "update_contact",
    "delete_contact",
    "link_contact_to_client",
    "unlink_contact_from_client",
    "get_contacts_for_client_count",
    "get_clients_for_contact",
    "get_specific_client_contact_link_details",
    "update_client_contact_link",
    "get_products_for_client_or_project",
    "get_distinct_purchase_confirmed_at_for_client",
    "add_product_to_client_or_project",
    "update_client_project_product",
    "remove_product_from_client_or_project",
    "get_client_project_product_by_id",
    "get_cover_pages_for_client",
    "add_cover_page",
    "update_cover_page",
    "delete_cover_page",
    "get_cover_page_by_id",
    "get_all_template_categories", # Added from template_categories_crud.py
    "get_all_file_based_templates", # From templates_crud
    "get_distinct_template_languages", # Added from templates_crud.py
    "get_distinct_template_types", # Added from templates_crud.py
    "get_filtered_templates", # Added from templates_crud.py
    "get_cover_page_template_by_id", # Now from cover_page_templates_crud
    "get_milestones_for_project",
    "add_milestone",
    "get_milestone_by_id",
    "update_milestone",
    "delete_milestone",
    "add_company", # Added
    "get_company_by_id", # Added
    "get_all_companies", # Added
    "update_company", # Added
    "delete_company", # Added
    "set_default_company",
    "get_default_company",
    "add_company_personnel", # Added
    "get_personnel_for_company", # Added
    "update_company_personnel", # Added
    "delete_company_personnel",
    "get_user_google_account_by_google_account_id",
    "update_user_google_account",
    "add_user_google_account",
    "get_user_google_account_by_user_id",
    "get_user_google_account_by_id",
    "delete_user_google_account",
    "add_contact_sync_log",
    "get_contact_sync_log_by_local_contact", # Added
    "get_contact_sync_log_by_google_contact_id", # Added
    "get_contact_sync_log_by_id", # Added
    "update_contact_sync_log", # Added
    "delete_contact_sync_log", # Added
    "get_contacts_pending_sync", # Added
    "get_all_sync_logs_for_account", # Added
    "get_all_partner_categories",
    "get_all_partners", # Added
    "get_partners_in_category",
    "get_categories_for_partner",
    "get_partner_by_id",
    "get_documents_for_partner",
    "add_partner_document", # Added
    "update_partner_document", # Added
    "delete_partner_document",
    "get_partner_document_by_id",
    "get_contacts_for_partner", # Added
    "add_partner_contact", # Added
    "update_partner_contact",
    "delete_partner_contact",
    "add_partner",
    "update_partner",
    "delete_partner",
    "link_partner_to_category", # Added
    "unlink_partner_from_category", # Added
    "get_or_add_partner_category",
    "get_partner_category_by_name", # Added
    "add_partner_category",
    "delete_partner_category",
    "update_partner_category",
    "get_partner_category_by_id", # Added
    "get_all_countries",
    "add_country",
    "get_or_add_country",
    "get_all_cities",
    "add_city",
    "get_or_add_city",
    "get_country_by_id",
    "get_city_by_id",
    "get_country_by_name",
    "get_city_by_name_and_country_id",
    "initialize_database",
    "get_setting",
    "set_setting",
    "get_all_transporters",
    "add_transporter",
    "get_transporter_by_id",
    "update_transporter",
    "delete_transporter",
    "get_all_freight_forwarders",
    "add_freight_forwarder",
    "get_freight_forwarder_by_id",
    "update_freight_forwarder",
    "delete_freight_forwarder",
    "get_assigned_personnel_for_client",
    "assign_personnel_to_client",
    "unassign_personnel_from_client",
    "get_assigned_transporters_for_client",
    "assign_transporter_to_client",
    "unassign_transporter_from_client",
    "update_client_transporter_email_status",
    "get_assigned_forwarders_for_client",
    "assign_forwarder_to_client",
    "unassign_forwarder_from_client",
]
