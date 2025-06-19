# db/cruds/__init__.py
from . import activity_logs_crud
from . import application_settings_crud
from . import client_assigned_personnel_crud # Added
from . import client_documents_crud
from . import client_freight_forwarders_crud # Added
from . import client_project_products_crud
from . import client_transporters_crud # Added
from . import clients_crud
from . import companies_crud
from . import company_personnel_crud
from . import contacts_crud
from . import cover_page_templates_crud
from . import cover_pages_crud
from . import freight_forwarders_crud # Added
from . import google_sync_crud
from . import internal_stock_items_crud # Added
from . import kpis_crud
from . import item_locations_crud # Added
from . import locations_crud
from . import milestones_crud
from . import partners_crud
from . import product_media_links_crud
from . import products_crud
from . import projects_crud
from . import status_settings_crud
from . import tasks_crud
from . import team_members_crud
from . import template_categories_crud
from . import templates_crud
from . import transporters_crud # Added
from . import users_crud

# Recruitment CRUDs
from . import recruitment_job_openings_crud
from . import recruitment_candidates_crud
from . import recruitment_interviews_crud
from . import recruitment_steps_crud
from . import recruitment_candidate_progress_crud

# generic_crud.py is typically not imported directly into __all__ or here
# unless it provides functions intended for direct use from db.cruds.generic_crud
# For now, assuming it's primarily for internal use by other CRUD modules.

# Ensure all .py files in db/cruds that define CRUD operations are imported here
# so they can be accessed like db.cruds.module_name.function_name
