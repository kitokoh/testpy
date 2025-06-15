from .cruds.status_settings_crud import (
    get_status_setting_by_id,
    get_all_status_settings,
    get_status_setting_by_name,
)
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
from .cruds.products_crud import get_total_products_count # Added
from .cruds.tasks_crud import (
    get_tasks_by_project_id,
    add_task,
    update_task,
    delete_task,
    get_task_by_id,
    get_tasks_by_assignee_id,
    get_predecessor_tasks,
    add_task_dependency,
    remove_task_dependency,
    get_tasks_by_project_id_ordered_by_sequence,
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
)
from .cruds.cover_pages_crud import (
    get_cover_pages_for_client,
    add_cover_page,
    update_cover_page,
    delete_cover_page,
    get_cover_page_by_id,
)
from .cruds.templates_crud import get_all_file_based_templates
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
from .cruds.locations_crud import get_all_countries, add_country, get_or_add_country, get_all_cities, add_city, get_or_add_city, get_country_by_id, get_city_by_id
from .cruds.application_settings_crud import get_setting, set_setting
from .init_schema import initialize_database

__all__ = [
    "get_setting",
    "set_setting",
    "get_status_setting_by_id",
    "get_all_status_settings",
    "get_status_setting_by_name",
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
    "get_predecessor_tasks",
    "add_task_dependency",
    "remove_task_dependency",
    "get_tasks_by_project_id_ordered_by_sequence",
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
    "get_client_counts_by_country", # Added
    "get_client_segmentation_by_city", # Added
    "get_client_segmentation_by_status", # Added
    "get_client_segmentation_by_category", # Added
    "get_cover_pages_for_client",
    "add_cover_page",
    "update_cover_page",
    "delete_cover_page",
    "get_cover_page_by_id",
    "get_all_file_based_templates", # From templates_crud
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
    "initialize_database",
    "get_setting",
    "set_setting",
]
