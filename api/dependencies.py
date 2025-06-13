from fastapi import Depends, HTTPException, status
from typing import Set

# Adjust imports based on your project structure for UserInDB and get_current_active_user
# Assuming api.models and api.auth are correct paths from within api directory
from .models import UserInDB  # Or from api.models if running from project root context
from .auth import get_current_active_user # Or from api.auth

# Assuming auth.roles is accessible from the root of the project
from auth.roles import has_permission, check_user_role, ALL_ROLES

class RoleRequired:
    def __init__(self, allowed_roles: Set[str]):
        # Ensure all provided roles are valid
        if not allowed_roles.issubset(ALL_ROLES):
            # This error is primarily for the developer, indicating incorrect RoleRequired usage
            raise ValueError(f"Invalid role(s) in allowed_roles {allowed_roles - ALL_ROLES}. Must be a subset of {ALL_ROLES}")
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: UserInDB = Depends(get_current_active_user)):
        if not check_user_role(current_user.role, self.allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' is not authorized. Allowed roles: {self.allowed_roles}"
            )
        return current_user

class PermissionRequired:
    def __init__(self, permission_identifier: str):
        self.permission_identifier = permission_identifier

    async def __call__(self, current_user: UserInDB = Depends(get_current_active_user)):
        if not has_permission(current_user.role, self.permission_identifier):
            # Log this attempt for security monitoring if logging is available
            # print(f"Permission denied for user {current_user.username} (role: {current_user.role}) for permission: {self.permission_identifier}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' lacks the required permission: '{self.permission_identifier}'"
            )
        return current_user

# Example of how these might be used in an endpoint (do not add this to dependencies.py):
# from auth.roles import ADMINISTRATOR, SUPER_ADMIN
# @router.post("/some_admin_action", dependencies=[Depends(RoleRequired({ADMINISTRATOR, SUPER_ADMIN}))])
# async def create_item(item: Item, current_user: UserInDB = Depends(PermissionRequired("manage_items"))):
#     # current_user is already validated for role and permission by this point
#     pass
