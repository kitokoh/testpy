from fastapi import APIRouter, HTTPException, Depends
from typing import List
import db as db_manager  # Assuming db.py is accessible in the parent directory
from .models import TemplateInfo, UserInDB # Import from local models.py, UserInDB for type hint
from .auth import get_current_active_user

router = APIRouter(
    prefix="/api/templates",
    tags=["Templates"],
    responses={404: {"description": "Not found"}},
)

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
            raise HTTPException(status_code=404, detail="No templates found or error fetching templates.")

        # Filter for templates that are likely to be base templates for PDF generation
        # For now, we'll assume that most templates could be sources for PDFs.
        # A more specific filter might be needed if certain template_type values are not relevant.
        # e.g., template_type like '%html%' or specific types like 'proforma_invoice_html', 'sales_contract_html'
        # For this iteration, let's include all templates fetched by get_all_templates.

        response_templates = []
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
