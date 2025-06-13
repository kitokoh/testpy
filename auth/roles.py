# User Roles
SUPER_ADMIN = "super_admin"
ADMINISTRATOR = "administrator"
STANDARD_USER = "standard_user"
READ_ONLY_USER = "read_only_user"

ALL_ROLES = {SUPER_ADMIN, ADMINISTRATOR, STANDARD_USER, READ_ONLY_USER}

# Role Permissions (Module-level access for now)
# These are more like "capabilities" or "access rights to modules"
# For very granular permissions, a different structure might be needed.
ROLE_PERMISSIONS = {
    SUPER_ADMIN: {
        "all_access"  # Special permission granting access to everything
    },
    ADMINISTRATOR: {
        "manage_clients",
        "manage_projects",
        "manage_documents", # This implies creation, editing, deletion
        "view_documents",   # Explicit view permission
        "manage_templates",
        "administer_standard_users",
        "manage_settings",
        "manage_partners",
        "view_reports",
        "view_audit_logs",
    },
    STANDARD_USER: {
        "edit_clients",
        "edit_projects",
        "edit_documents",   # This implies creation, editing of own/allowed documents
        "view_documents",   # Explicit view permission
        "use_templates",
        "view_reports",
    },
    READ_ONLY_USER: {
        "view_clients",
        "view_projects",
        "view_documents",
        "view_reports", # General viewing rights
    }
}

# --- Permission Checking Functions ---

def has_permission(user_role: str, required_permission: str) -> bool:
    """
    Checks if a user role has a specific permission.
    The SUPER_ADMIN role with "all_access" implicitly has all permissions.
    """
    if not user_role or user_role not in ROLE_PERMISSIONS:
        return False

    user_permissions = ROLE_PERMISSIONS.get(user_role, set())

    if "all_access" in user_permissions: # SUPER_ADMIN with "all_access"
        return True

    return required_permission in user_permissions

def check_user_role(user_role: str, allowed_roles: set[str]) -> bool:
    """
    Checks if the user's role is one of the allowed roles.
    """
    if not user_role: # Handle cases where user_role might be None or empty
        return False
    return user_role in allowed_roles

# Example usage (for demonstration, not for direct use in FastAPI deps yet):
# def require_role(user_role: str, target_roles: set[str]):
#     if not check_user_role(user_role, target_roles):
#         raise Exception(f"User role '{user_role}' not authorized. Requires one of: {target_roles}")

# def require_permission_explicit(user_role: str, permission_needed: str):
#     if not has_permission(user_role, permission_needed):
#         raise Exception(f"User role '{user_role}' lacks permission: '{permission_needed}'")
