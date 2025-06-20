from fastapi import APIRouter, HTTPException, Depends
from typing import List
import db as db_manager  # Assuming db.py is accessible in the parent directory
from .models import TemplateInfo, UserInDB, TemplateVisibilityInfo, UpdateTemplateVisibilityRequest # Added new models
from .auth import get_current_active_user

router = APIRouter(
    prefix="/api/templates",
    tags=["Templates"],
    responses={404: {"description": "Not found"}},
)

@router.get("/visibility_settings", response_model=List[TemplateVisibilityInfo])
async def get_template_visibility_settings(current_user: UserInDB = Depends(get_current_active_user)):
    '''
    Lists all available document templates along with their current visibility status.
    '''
    try:
        # Pass apply_visibility_filter=False to get all templates for the settings UI
        all_db_templates = db_manager.get_all_templates(apply_visibility_filter=False)
        if all_db_templates is None: # Should be an empty list if no templates, but good to be safe
            all_db_templates = []

        response_templates = []
        for t_dict in all_db_templates:
            template_id = t_dict.get('template_id')
            if not template_id:
                continue # Should not happen if data is clean

            visibility_key = f"template_visibility_{template_id}_enabled"
            # Ensure default is 'True' as string for get_setting
            is_visible_str = db_manager.get_setting(visibility_key, default='True')
            is_visible_bool = is_visible_str.lower() == 'true'

            response_templates.append(
                TemplateVisibilityInfo(
                    template_id=template_id,
                    template_name=t_dict.get('template_name'),
                    description=t_dict.get('description'),
                    template_type=t_dict.get('template_type'),
                    language_code=t_dict.get('language_code'),
                    is_visible=is_visible_bool
                )
            )
        return response_templates
    except Exception as e:
        print(f"Error in get_template_visibility_settings: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.post("/visibility_settings")
async def set_template_visibility_settings(
    request: UpdateTemplateVisibilityRequest,
    current_user: UserInDB = Depends(get_current_active_user)
):
    '''
    Updates the visibility status for multiple templates.
    '''
    try:
        for item in request.preferences:
            visibility_key = f"template_visibility_{item.template_id}_enabled"
            db_manager.set_setting(visibility_key, str(item.is_visible))
        return {"message": "Template visibility settings updated successfully."}
    except Exception as e:
        print(f"Error in set_template_visibility_settings: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get("", response_model=List[TemplateInfo])
async def list_templates(
    template_type: str = None, # Optional filter by template_type
    language_code: str = None,  # Optional filter by language_code
    current_user: UserInDB = Depends(get_current_active_user)
):
    '''
    Lists available document templates.
    Can be filtered by template_type (e.g., 'document_excel', 'document_word', 'html_cover_page', 'proforma_invoice_html')
    and/or language_code (e.g., 'en', 'fr').
    '''
    try:
        # Use the existing db_manager function to get all templates
        # It already supports filtering by type and language if needed
        db_templates = db_manager.get_all_templates(
            template_type_filter=template_type,
            language_code_filter=language_code
        )

        if db_templates is None:
            # This case might occur if db_manager.get_all_templates returns None on error
            # or if the table is empty and it returns None instead of []
            # However, the current db_manager.get_all_templates returns [] on error or empty.
            # So, this explicit check might be redundant but kept for safety.
            # The db_manager.get_all_templates now returns [] on error or empty, and handles visibility.
            db_templates = [] if db_templates is None else db_templates


        response_templates = []
        # db_templates is now already filtered for visibility by db_manager.get_all_templates
        for t_dict in db_templates:
            response_templates.append(
                TemplateInfo(
                    template_id=t_dict.get('template_id'),
                    template_name=t_dict.get('template_name'),
                    description=t_dict.get('description'),
                    template_type=t_dict.get('template_type'),
                    language_code=t_dict.get('language_code')
                )
            )
        return response_templates
    except Exception as e:
        # Log the exception e for debugging
        print(f"Error in list_templates endpoint: {e}") # Basic print logging
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
