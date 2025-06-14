# This file makes the 'db' directory a Python package.
# It also conveniently re-exports symbols from submodules.

from .cruds.status_settings_crud import (
    get_status_setting_by_id,
    get_all_status_settings,
    get_status_setting_by_name
)
from .cruds.projects_crud import (
    get_all_projects,
    get_project_by_id,
    add_project,
    update_project,
    delete_project
)
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
    get_tasks_by_project_id_ordered_by_sequence
)
from .cruds.kpis_crud import (
    get_kpis_for_project
)
from .cruds.activity_logs_crud import (
    add_activity_log,
    get_activity_logs
)
from .cruds.users_crud import (
    get_user_by_id,
    get_all_users,
    update_user,
    verify_user_password
)
from .cruds.team_members_crud import (
    get_all_team_members,
    get_team_member_by_id,
    add_team_member,
    update_team_member,
    delete_team_member
)
from .cruds.clients_crud import clients_crud_instance
get_all_clients = clients_crud_instance.get_all_clients
# Ensure other methods from ClientsCRUD that projectManagement.py might use in the future
# are also exposed similarly if they are intended to be part of the db facade.
# For now, only get_all_clients is explicitly mentioned in projectManagement.py's import block for clients.
from .cruds.cover_pages_crud import (
    get_cover_pages_for_client,
    add_cover_page,
    update_cover_page,
    delete_cover_page,
    get_cover_page_by_id
)
from .cruds.templates_crud import ( # Assuming get_all_file_based_templates is here
    get_all_file_based_templates,
    get_cover_page_template_by_id # Assuming get_cover_page_template_by_id is here based on previous context
)
from .cruds.milestones_crud import (
    get_milestones_for_project,
    add_milestone,
    get_milestone_by_id,
    update_milestone,
    delete_milestone
)
from .init_schema import (
    initialize_database
)

# It's good practice to define __all__ if you want to control what `from db import *` imports
# For now, we'll rely on the explicit imports.
