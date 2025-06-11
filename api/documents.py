from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import FileResponse
from typing import Optional
import uuid
import os
import datetime

import db as db_manager
from html_to_pdf_util import render_html_template, convert_html_to_pdf, WeasyPrintError
from .models import DocumentGenerationRequest, DocumentGenerationResponse, UserInDB # UserInDB for type hint
from .auth import get_current_active_user

router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"],
    responses={404: {"description": "Not found"}},
)

# Helper function to ensure directory exists and save PDF
def _save_generated_pdf(client_id: str, project_id: Optional[str], file_name: str, pdf_bytes: bytes, base_clients_dir: str) -> Optional[str]:
    try:
        # Determine the target directory
        # Ensure base_clients_dir is an absolute path from config or a known location
        # For this subtask, assume base_clients_dir is the root for all client folders.
        # Example: clients_data/client_uuid/project_uuid_or_general/file.pdf

        client_folder_name = None
        client_info = db_manager.get_client_by_id(client_id)
        if client_info and client_info.get('default_base_folder_path'):
            # Use the client's pre-defined base folder path
            # This path is already unique and structured, e.g., "clients/ClientName_Country_ProjectID"
            # We might want to save generated documents into a subfolder of this, e.g., "generated_documents"
            target_dir_base = client_info['default_base_folder_path']
        else:
            # Fallback if default_base_folder_path is not set or client not found (should not happen if client_id is valid)
            # This fallback might be problematic if base_clients_dir is not configured well.
            # It's better to rely on client_info.default_base_folder_path
            print(f"Warning: Client default_base_folder_path not found for client {client_id}. Using generic path.")
            client_folder_name_safe = str(client_id).replace('-', '') # Basic sanitization
            target_dir_base = os.path.join(base_clients_dir, client_folder_name_safe)

        # Add a subfolder for generated documents within the client's base folder
        generated_docs_subfolder = "generated_documents"
        if project_id:
            specific_folder_name = str(project_id).replace('-', '')
            target_dir = os.path.join(target_dir_base, generated_docs_subfolder, specific_folder_name)
        else:
            target_dir = os.path.join(target_dir_base, generated_docs_subfolder, "general")

        os.makedirs(target_dir, exist_ok=True)

        # Ensure unique filename if needed, or overwrite
        # For now, using the provided file_name directly.
        # A more robust approach might add a timestamp or UUID to file_name if collisions are a concern.
        # Example: unique_file_name = f"{os.path.splitext(file_name)[0]}_{uuid.uuid4().hex[:8]}{os.path.splitext(file_name)[1]}"

        file_path_on_disk = os.path.join(target_dir, file_name)

        with open(file_path_on_disk, "wb") as f:
            f.write(pdf_bytes)

        # Return the relative path from the *application root* or a *consistent base for documents*
        # This depends on how file_path_relative in ClientDocuments table is interpreted.
        # Assuming ClientDocuments.file_path_relative is relative to the client's base folder path.
        # So, if target_dir_base = "clients/ClientFoo_Country_ProjID",
        # and file_path_on_disk = "clients/ClientFoo_Country_ProjID/generated_documents/general/my_doc.pdf",
        # then relative_path = "generated_documents/general/my_doc.pdf"

        # To achieve this, we need the part of file_path_on_disk that comes AFTER target_dir_base.
        # os.path.relpath(file_path_on_disk, start=target_dir_base) could work if target_dir_base is a prefix.

        # A simpler way, given our construction:
        relative_to_client_base = os.path.join(generated_docs_subfolder,
                                               str(project_id).replace('-', '') if project_id else "general",
                                               file_name)
        return relative_to_client_base # This path is relative to the client's specific base folder.

    except Exception as e:
        print(f"Error saving PDF '{file_name}' for client {client_id}: {e}") # Basic print logging
        return None

@router.post("/generate", response_model=DocumentGenerationResponse)
async def generate_document_api(request: DocumentGenerationRequest = Body(...), current_user: UserInDB = Depends(get_current_active_user)):
    """
    Generates a new document based on a template and client data.

    Requires a valid template ID, client ID, company ID, and target language.
    Optional fields include project ID, document title, line items for products,
    and additional context data.

    The generated document (PDF) is saved to the server, and its metadata is
    stored in the database. Returns information about the generated document,
    including a download URL.
    """
    try:
        # 1. Fetch Template
        template_data = db_manager.get_template_by_id(request.template_id)
        if not template_data:
            raise HTTPException(status_code=404, detail=f"Template with ID {request.template_id} not found.")

        # For HTML templates, content might be in 'raw_template_file_data' or need to be loaded
        # from 'base_file_name' (relative to a templates directory).
        # The db_manager.get_template_by_id should ideally provide the content or enough info.
        # Let's assume 'raw_template_file_data' holds the HTML string for HTML templates.
        # Or, if it's a file-based template, construct path and read.

        html_template_str = None
        template_base_path = None # For resolving relative resources like images in HTML

        if template_data.get('raw_template_file_data'):
            # Assuming raw_template_file_data is bytes, decode it.
            try:
                html_template_str = template_data['raw_template_file_data'].decode('utf-8')
            except Exception as e_decode:
                 raise HTTPException(status_code=500, detail=f"Error decoding template content for template ID {request.template_id}: {e_decode}")
            # base_url for Weasyprint might need to point to where general assets are, or template-specific assets.
            # If raw_template_file_data is used, relative paths within it are harder to resolve without a known base.
            # Let's assume APP_ROOT_DIR can be used as a fallback base if template files are stored there.
            # This needs to be configured or passed appropriately.
            # For now, we'll assume templates might be under "templates/{lang}/{filename}"
            # This part is tricky without knowing the exact template storage strategy.
            # Let's assume a 'templates' dir in the app root.
            # APP_ROOT_DIR needs to be available here (e.g. from config or env var)
            # For subtask, we'll mock this path.
            app_root_for_templates = os.path.abspath(os.path.join(os.path.dirname(db_manager.__file__), "..")) # Assumption
            template_folder = os.path.join(app_root_for_templates, "templates", template_data.get('language_code', ''))
            template_base_path = f"file://{template_folder.replace(os.sep, '/')}/"


        elif template_data.get('base_file_name') and template_data.get('language_code'):
            # Construct path: APP_ROOT/templates/<lang_code>/<base_file_name>
            # This requires knowing APP_ROOT_DIR. Let's assume db_manager is in root or subdir.
            # This is a common pattern in the existing codebase.
            # If db.py is in root, then os.path.dirname(db_manager.__file__) is an empty string if run from root,
            # or the path to db.py if imported.
            # Let's assume APP_ROOT_DIR is the parent of where db.py is, if db.py is in a subdir.
            # A more robust way would be to get APP_ROOT_DIR from a config.

            # Simplified assumption for subtask: db_manager.__file__ gives path to db.py
            # project_root would be os.path.dirname(os.path.dirname(db_manager.__file__)) if db.py is in a 'core' subdir for example.
            # Or just os.path.dirname(db_manager.__file__) if db.py is in root.
            # For now, let's assume a 'templates' dir relative to where db.py is.
            # This might need adjustment based on actual project structure.

            # Let's assume app_setup.APP_ROOT_DIR is the correct reference.
            # Since this subtask can't import app_setup directly, we'll construct a plausible path.
            # Fallback: parent of db.py location
            app_root_for_templates = os.path.abspath(os.path.join(os.path.dirname(db_manager.__file__), "..")) # Assumption

            file_path = os.path.join(app_root_for_templates, "templates",
                                     template_data['language_code'],
                                     template_data['base_file_name'])
            if not os.path.exists(file_path):
                # Try another common location if templates are directly under APP_ROOT_DIR/templates (no lang subfolder)
                file_path_alt = os.path.join(app_root_for_templates, "templates", template_data['base_file_name'])
                if os.path.exists(file_path_alt):
                    file_path = file_path_alt
                else:
                    raise HTTPException(status_code=404, detail=f"Template file {template_data['base_file_name']} not found at expected paths for template ID {request.template_id}.")

            with open(file_path, 'r', encoding='utf-8') as f:
                html_template_str = f.read()
            # Set base_url for WeasyPrint to resolve relative paths (e.g. for images)
            # This should be the directory containing the HTML template file.
            template_base_path = f"file://{os.path.dirname(file_path).replace(os.sep, '/')}/"
        else:
            raise HTTPException(status_code=500, detail=f"Template ID {request.template_id} has no content or file defined.")

        # 2. Get Context Data
        # The `get_document_context_data` function expects `linked_product_ids_for_doc`
        # and `additional_context` which includes `lite_selected_products`.
        # We need to map `request.line_items` to one of these.
        # Let's assume `request.line_items` corresponds to `lite_selected_products` for simplicity.

        additional_context_for_db = request.additional_context if request.additional_context else {}
        if request.line_items:
            # If API provides line_items, treat them as 'lite_selected_products'
            additional_context_for_db['lite_selected_products'] = request.line_items
            # linked_product_ids_for_doc (which are ClientProjectProduct IDs) would be None in this case
            linked_cpp_ids = None
        else:
            # If no line_items from API, perhaps the document relies on all products linked to client/project.
            # In this case, get_document_context_data will fetch them.
            # Or, if specific linked_product_ids (ClientProjectProduct IDs) are needed,
            # they should be part of additional_context.
            linked_cpp_ids = additional_context_for_db.get('linked_client_project_product_ids')


        context_data = db_manager.get_document_context_data(
            client_id=request.client_id,
            company_id=request.company_id,
            target_language_code=request.target_language_code,
            project_id=request.project_id,
            linked_product_ids_for_doc=linked_cpp_ids, # List of ClientProjectProduct IDs
            additional_context=additional_context_for_db # Contains lite_selected_products or other overrides
        )

        # Override document title if provided in request
        if request.document_title:
            context_data['doc']['document_title'] = request.document_title


        # 3. Render HTML
        rendered_html = render_html_template(html_template_str, context_data)

        # 4. Convert to PDF
        # Base URL for WeasyPrint to resolve relative paths (e.g. for images in template)
        # This is crucial. If template_base_path was not set, it might fail for relative images.
        # If template_base_path is None, WeasyPrint might try to use current working dir, which is unreliable.
        pdf_bytes = convert_html_to_pdf(rendered_html, base_url=template_base_path)
        if not pdf_bytes:
            raise HTTPException(status_code=500, detail="PDF generation failed (convert_html_to_pdf returned None).")

        # 5. Save PDF and store metadata
        # Construct a filename, e.g., from template name, client name, date
        # Ensure filename is filesystem-safe.
        safe_template_name = "".join(c if c.isalnum() else "_" for c in template_data.get('template_name', 'document'))
        safe_client_name = "".join(c if c.isalnum() else "_" for c in context_data.get('client',{}).get('company_name', context_data.get('client',{}).get('contact_person_name','unknown_client')))
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        generated_file_name = f"{safe_template_name}_{safe_client_name}_{timestamp}.pdf"

        # Get base client directory from config (needs to be accessible)
        # For subtask, this is a placeholder. In real app, get from app_setup.CONFIG
        # app_config_py_path = os.path.join(os.path.dirname(db_manager.__file__), "..", "app_config.py")
        # If app_config.py defines CONFIG dictionary, it could be loaded.
        # For now, let's assume a "clients_data" directory in the project root.
        # Project root relative to db.py (assuming db.py is in root or a direct subdir like 'core')
        project_root_dir = os.path.abspath(os.path.join(os.path.dirname(db_manager.__file__), ".."))
        clients_base_storage_dir = os.path.join(project_root_dir, "clients") # Matches existing structure for client assets

        relative_file_path = _save_generated_pdf(
            client_id=request.client_id,
            project_id=request.project_id,
            file_name=generated_file_name,
            pdf_bytes=pdf_bytes,
            base_clients_dir=clients_base_storage_dir # This is the root of all client folders
        )

        if not relative_file_path:
            raise HTTPException(status_code=500, detail="Failed to save generated PDF.")

        doc_metadata = {
            'client_id': request.client_id,
            'project_id': request.project_id,
            'document_name': request.document_title or template_data.get('template_name', 'Generated Document'),
            'file_name_on_disk': generated_file_name, # Name of the file itself
            'file_path_relative': relative_file_path, # Path relative to client's base folder
            'document_type_generated': template_data.get('template_type', 'generic_pdf'),
            'source_template_id': request.template_id,
            # 'created_by_user_id': # TODO: Get from authenticated user
        }
        db_document_id = db_manager.add_client_document(doc_metadata)
        if not db_document_id:
            # Attempt to clean up saved PDF if DB entry fails
            # full_saved_path = os.path.join(clients_base_storage_dir, client_info['default_base_folder_path'], relative_file_path) # This path construction is complex
            # For simplicity, don't cleanup in subtask, but log it.
            print(f"Warning: PDF saved to {relative_file_path} but failed to add metadata to DB.")
            raise HTTPException(status_code=500, detail="Failed to save document metadata to database after PDF generation.")

        # 6. Prepare Response
        # Construct download URL (relative to API base)
        download_url = f"/api/documents/{db_document_id}/download" # Assuming /api prefix for all API routes

        return DocumentGenerationResponse(
            message="Document generated successfully.",
            document_id=db_document_id,
            client_id=request.client_id,
            file_name=generated_file_name,
            download_url=download_url
        )

    except WeasyPrintError as wpe:
        # Log wpe for details
        print(f"WeasyPrintError during PDF generation: {wpe}")
        raise HTTPException(status_code=500, detail=f"PDF Generation Error: {str(wpe)}")
    except HTTPException as he:
        raise he # Re-raise HTTPExceptions directly
    except Exception as e:
        # Log the exception e for debugging
        print(f"Error in generate_document_api endpoint: {e}") # Basic print logging
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during document generation: {str(e)}")


@router.get("/{document_id}/download", response_class=FileResponse)
async def download_document_api(document_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    """
    Downloads a previously generated document by its ID.

    Requires the `document_id` of an existing document.
    The document is returned as a PDF file.
    """
    try:
        doc_meta = db_manager.get_document_by_id(document_id)
        if not doc_meta:
            raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found.")

        client_id = doc_meta.get('client_id')
        if not client_id:
            raise HTTPException(status_code=500, detail=f"Client ID missing for document {document_id}.")

        client_info = db_manager.get_client_by_id(client_id)
        if not client_info or not client_info.get('default_base_folder_path'):
            raise HTTPException(status_code=404, detail=f"Client information or base folder path not found for client ID {client_id} associated with document {document_id}.")

        # file_path_relative in ClientDocuments is relative to the client's specific base folder.
        # e.g., "generated_documents/general/my_doc.pdf"
        # default_base_folder_path is the client's root, e.g., "clients/ClientName_Country_ProjectID"

        # Construct the absolute path to the file
        # IMPORTANT: Ensure that default_base_folder_path is an absolute path or correctly resolved
        # from the project root. The _save_generated_pdf helper assumed it was relative to 'clients_base_storage_dir'.
        # For consistency, we should either store absolute paths in default_base_folder_path
        # or resolve it from a known project root here.

        # Assuming default_base_folder_path is relative to the project root (e.g. "clients/ClientX_...")
        # We need the project root.
        project_root_dir = os.path.abspath(os.path.join(os.path.dirname(db_manager.__file__), ".."))

        # Path to the client's specific root folder (e.g. /abs/path/to/project/clients/ClientX_...)
        client_specific_root_abs_path = os.path.join(project_root_dir, client_info['default_base_folder_path'])

        # The actual path to the PDF file
        # doc_meta['file_path_relative'] is like "generated_documents/general/doc.pdf"
        # doc_meta['file_name_on_disk'] is just "doc.pdf"
        # The _save_generated_pdf function saved relative_file_path which is:
        # os.path.join(generated_docs_subfolder, project_folder_or_general, file_name)
        # This is what should be stored in ClientDocuments.file_path_relative.

        absolute_file_path = os.path.join(client_specific_root_abs_path, doc_meta['file_path_relative'])

        if not os.path.exists(absolute_file_path):
            print(f"Error: File not found at path: {absolute_file_path} (constructed for doc ID {document_id})")
            # For debugging, print components:
            print(f"  Project root used: {project_root_dir}")
            print(f"  Client default_base_folder_path: {client_info['default_base_folder_path']}")
            print(f"  Client specific root (abs): {client_specific_root_abs_path}")
            print(f"  Document file_path_relative: {doc_meta['file_path_relative']}")
            raise HTTPException(status_code=404, detail=f"Generated document file not found on server for document ID {document_id}.")

        # Use file_name_on_disk for the download filename suggestion to the browser
        return FileResponse(path=absolute_file_path, filename=doc_meta.get('file_name_on_disk', 'document.pdf'), media_type='application/pdf')

    except HTTPException as he:
        raise he # Re-raise HTTPExceptions directly
    except Exception as e:
        # Log the exception e for debugging
        print(f"Error in download_document_api endpoint for doc_id {document_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while trying to download document: {str(e)}")
