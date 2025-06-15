import uuid
import os
import datetime # Added for datetime.date.today()
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from sqlalchemy import func # Added for func.now()

# Assuming db managing and models are structured as previously discussed
# Adjust paths if your project structure is different
from db.cruds import proforma_invoices_crud
# For other db operations (like fetching client, company, or adding ClientDocument)
# that use the main sqlite3-based 'db' facade:
from db import get_client_by_id as get_client_by_id_sqlite
from db import add_client_document as add_client_document_sqlite
from db import get_company_by_id as get_company_by_id_sqlite
from db.utils import get_proforma_invoice_context_data # Assuming this is sqlite based
from api.models import ProformaInvoiceStatusEnum, User # Assuming User model for auth
# from api import models as api_models # Not explicitly used, can be removed if ProformaInvoice Pydantic models are self-contained here
# Assuming proforma_invoice_utils.py will exist or be created later
# from proforma_invoice_utils import get_proforma_invoice_context_data # Replaced by direct import from db.utils
from html_to_pdf_util import render_html_template, convert_html_to_pdf, WeasyPrintError
# Placeholder for current_user and db session dependency
from .dependencies import get_db, get_current_active_user # Assuming these exist

# Pydantic models for request/response
from pydantic import BaseModel, Field

class ProformaInvoiceItemBase(BaseModel):
    product_id: Optional[str] = None
    description: str
    quantity: float
    unit_price: float
    total_price: float # quantity * unit_price, can be validated

class ProformaInvoiceItemCreate(ProformaInvoiceItemBase):
    pass

class ProformaInvoiceItemResponse(ProformaInvoiceItemBase):
    id: str
    # proforma_invoice_id: str # Usually included if item is fetched independently, but often omitted if part of ProformaInvoiceResponse

    class Config:
        orm_mode = True

class ProformaInvoiceBase(BaseModel):
    client_id: str
    project_id: Optional[str] = None
    company_id: str # Seller
    proforma_invoice_number: Optional[str] = None # Can be auto-generated if not provided
    currency: str = "EUR"
    payment_terms: Optional[str] = "Paiement anticipé"
    delivery_terms: Optional[str] = "Selon accord"
    incoterms: Optional[str] = "EXW"
    named_place_of_delivery: Optional[str] = "Lieu du vendeur"
    notes: Optional[str] = None
    status: Optional[ProformaInvoiceStatusEnum] = ProformaInvoiceStatusEnum.DRAFT

class ProformaInvoiceCreate(ProformaInvoiceBase):
    items: List[ProformaInvoiceItemCreate]
    vat_rate_percentage: float = 20.0
    discount_rate_percentage: float = 0.0
    target_language_code: str = "fr"


class ProformaInvoiceResponse(ProformaInvoiceBase):
    id: str
    created_date: datetime.datetime # Adjusted type hint
    sent_date: Optional[datetime.datetime] = None # Adjusted type hint
    subtotal_amount: float
    discount_amount: Optional[float]
    vat_amount: float
    grand_total_amount: float
    linked_document_id: Optional[str] = None
    generated_invoice_id: Optional[str] = None
    items: List[ProformaInvoiceItemResponse] = []
    proforma_pdf_url: Optional[str] = None
    final_invoice_pdf_url: Optional[str] = None

    class Config:
        orm_mode = True
        # use_enum_values = True # For Pydantic v1 if status is returned as string

router = APIRouter(
    prefix="/api/proformas",
    tags=["Proforma Invoices"],
    responses={404: {"description": "Not found"}},
)

def _internal_save_pdf_and_create_document_record(
    db_session: Session,
    pdf_bytes: bytes,
    client_id: str,
    project_id: Optional[str],
    document_name: str,
    file_name_prefix: str,
    template_id_source: Optional[str], # This was integer in db schema for Templates.template_id
    user_id: str,
    # company_id: str # If ClientDocument needs company_id
) -> Optional[str]:
    try:
        # Determine project_root_dir without db.__file__ as db is no longer directly imported
        # This might require passing APP_ROOT_DIR or using a configuration setting
        # For now, let's assume a relative path structure or that this helper will be updated
        # to receive such configuration.
        # Placeholder:
        project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")) # Assuming api/proformas.py
        clients_base_storage_dir = os.path.join(project_root_dir, "clients")

        client_info = get_client_by_id_sqlite(client_id) # Uses sqlite connection
        # client_info is a dict from sqlite, not an ORM object, so access via get()
        if not client_info or not client_info.get('default_base_folder_path'):
            client_folder_name_safe = str(client_id).replace('-', '')
            target_dir_base = os.path.join(clients_base_storage_dir, client_folder_name_safe)
        else:
            # Ensure client_info['default_base_folder_path'] is treated as relative to project_root_dir
            client_base_path = client_info['default_base_folder_path']
            if client_base_path.startswith("clients" + os.sep):
                 target_dir_base = os.path.join(project_root_dir, client_base_path)
            else: # Or if it's an absolute path already
                 target_dir_base = client_base_path


        generated_docs_subfolder = "generated_documents"
        specific_folder_name = str(project_id).replace('-', '') if project_id else "general"
        target_dir = os.path.join(target_dir_base, generated_docs_subfolder, specific_folder_name)
        os.makedirs(target_dir, exist_ok=True)

        timestamp = uuid.uuid4().hex[:8]
        generated_file_name = f"{file_name_prefix}_{timestamp}.pdf"
        file_path_on_disk = os.path.join(target_dir, generated_file_name)

        with open(file_path_on_disk, "wb") as f:
            f.write(pdf_bytes)

        # Relative path for ClientDocument.file_path_relative, should be relative to clients_base_storage_dir or similar root
        # If target_dir_base is /abs/path/to/project_root/clients/client_xyz_folder
        # And file_path_on_disk is /abs/path/to/project_root/clients/client_xyz_folder/generated_documents/general/file.pdf
        # Then relative_to_target_dir_base should be generated_documents/general/file.pdf
        # However, ClientDocument.file_path_relative in schema seems to be relative to client's default_base_folder_path
        # So, if default_base_folder_path is "clients/client_xyz_folder", then relative path is "generated_documents/general/file.pdf"

        # Path relative to the client's base folder path
        relative_path_for_db = os.path.join(generated_docs_subfolder, specific_folder_name, generated_file_name)

        doc_metadata = {
            'client_id': client_id,
            'project_id': project_id,
            'document_name': document_name,
            'file_name_on_disk': generated_file_name, # Just the name of the file
            'file_path_relative': relative_path_for_db, # Path relative to client's base folder
            'document_type_generated': 'proforma_invoice' if 'proforma' in file_name_prefix.lower() else 'invoice',
            'source_template_id': template_id_source, # This should be an integer if it refers to Templates.template_id
            'created_by_user_id': user_id, # Ensure column name matches DB (e.g. created_by_user_id)
        }

        # The ClientDocument table has source_template_id as INTEGER.
        # If template_id_source is a string (like a UUID from a different system), this will fail.
        # For now, assuming template_id_source can be None or an int-like string if converted.
        # If template_id_source is not an integer, it should be set to None or handled.
        if doc_metadata['source_template_id'] is not None:
            try:
                int(doc_metadata['source_template_id']) # Check if it can be an int
            except ValueError:
                # print(f"Warning: template_id_source '{doc_metadata['source_template_id']}' is not an integer. Setting to None for ClientDocument.")
                doc_metadata['source_template_id'] = None

        # Use the new sqlite function for add_client_document
        # add_client_document_sqlite returns an ID directly
        db_document_id = add_client_document_sqlite(doc_metadata)

        if not db_document_id:
            # print(f"Error: Failed to save ClientDocument metadata for {generated_file_name}")
            # Consider os.remove(file_path_on_disk) # Cleanup if DB record fails
            return None
        return db_document_id
    except Exception as e:
        # print(f"Error in _internal_save_pdf_and_create_document_record: {e}")
        # import traceback; traceback.print_exc();
        return None


@router.post("/", response_model=ProformaInvoiceResponse, status_code=201)
def create_proforma_api(
    proforma_create: ProformaInvoiceCreate,
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    proforma_dict = proforma_create.model_dump(exclude={"items", "vat_rate_percentage", "discount_rate_percentage", "target_language_code"})

    subtotal = sum(item.quantity * item.unit_price for item in proforma_create.items)
    discount_amount_calculated = (proforma_create.discount_rate_percentage / 100.0) * subtotal
    amount_after_discount = subtotal - discount_amount_calculated
    vat_amount_calculated = (proforma_create.vat_rate_percentage / 100.0) * amount_after_discount
    grand_total = amount_after_discount + vat_amount_calculated

    proforma_dict["subtotal_amount"] = subtotal
    proforma_dict["discount_amount"] = discount_amount_calculated
    proforma_dict["vat_amount"] = vat_amount_calculated
    proforma_dict["grand_total_amount"] = grand_total
    proforma_dict["status"] = ProformaInvoiceStatusEnum.DRAFT

    items_dict_list = [item.model_dump() for item in proforma_create.items]

    try:
        db_proforma = proforma_invoices_crud.create_proforma_invoice(db_session, proforma_data=proforma_dict, items_data=items_dict_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create proforma invoice in DB: {str(e)}")

    additional_context_for_pdf = {
        "proforma_id": db_proforma.proforma_invoice_number,
        "current_date": db_proforma.created_date.strftime('%Y-%m-%d'),
        "vat_rate_percentage": proforma_create.vat_rate_percentage,
        "discount_rate_percentage": proforma_create.discount_rate_percentage,
        "lite_selected_products": [{
            "product_id": item.product_id, "name": item.description, "description": item.description,
            "quantity": item.quantity, "unit_price_override": item.unit_price
        } for item in db_proforma.items],
        # "db_session": db_session # db_session (SQLAlchemy) should not be passed to context for sqlite utils
    }

    try:
        # app_root_for_templates determination needs to be independent of 'db' module import
        project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        app_root_for_templates = os.path.join(project_root_dir, "templates")
        template_file_path = os.path.join(app_root_for_templates, proforma_create.target_language_code, "proforma_invoice_template.html")

        if not os.path.exists(template_file_path):
            template_file_path = os.path.join(app_root_for_templates, "en", "proforma_invoice_template.html")
            if not os.path.exists(template_file_path):
                 raise HTTPException(status_code=404, detail=f"Proforma invoice HTML template not found in {proforma_create.target_language_code} or en.")

        with open(template_file_path, 'r', encoding='utf-8') as f:
            html_template_str = f.read()
        # Ensure template_base_path correctly uses file URI scheme and forward slashes
        template_base_path = f"file://{os.path.dirname(template_file_path).replace(os.sep, '/')}/"

        context_data = get_proforma_invoice_context_data(
            client_id=db_proforma.client_id, company_id=db_proforma.company_id,
            project_id=db_proforma.project_id, target_language_code=proforma_create.target_language_code,
            additional_context=additional_context_for_pdf
        )
        rendered_html = render_html_template(html_template_str, context_data)
        pdf_bytes = convert_html_to_pdf(rendered_html, base_url=template_base_path)
        if not pdf_bytes:
            raise WeasyPrintError("PDF generation returned no bytes.")

        pdf_document_name = f"Proforma Invoice {db_proforma.proforma_invoice_number}"
        pdf_file_prefix = f"proforma_{db_proforma.proforma_invoice_number.replace('/', '_').replace(' ', '_')}"
        user_id_for_doc = getattr(current_user, 'id', getattr(current_user, 'user_id', None))
        if not user_id_for_doc:
             raise HTTPException(status_code=500, detail="User ID not found for document attribution.")

        generated_doc_id = _internal_save_pdf_and_create_document_record(
            db_session=db_session, pdf_bytes=pdf_bytes, client_id=db_proforma.client_id,
            project_id=db_proforma.project_id, document_name=pdf_document_name,
            file_name_prefix=pdf_file_prefix, template_id_source=None,
            user_id=user_id_for_doc
        )

        if generated_doc_id:
            # Use the CRUD function for update, ensuring Session is the first argument if needed
            proforma_invoices_crud.update_proforma_invoice(db_session, db_proforma.id, {"linked_document_id": generated_doc_id})
            db_proforma.linked_document_id = generated_doc_id # Update the instance for the response
            db_session.refresh(db_proforma) # Refresh to get the updated state if update_proforma_invoice doesn't
    except WeasyPrintError as wpe:
        # print(f"WeasyPrintError during PDF generation for proforma {db_proforma.id}: {wpe}")
        pass
    except HTTPException: # Re-raise HTTPExceptions
        raise
    except Exception as pdf_exc:
        # print(f"Generic error during PDF generation for proforma {db_proforma.id}: {pdf_exc}")
        pass

    response = ProformaInvoiceResponse.from_orm(db_proforma)
    if db_proforma.linked_document_id:
        response.proforma_pdf_url = f"/api/documents/{db_proforma.linked_document_id}/download"
    return response


@router.get("/", response_model=List[ProformaInvoiceResponse])
def list_proformas_api(
    client_id: Optional[str] = Query(None), project_id: Optional[str] = Query(None),
    company_id: Optional[str] = Query(None), status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500),
    db_session: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    status_enum: Optional[ProformaInvoiceStatusEnum] = None
    if status:
        try:
            status_enum = ProformaInvoiceStatusEnum[status.upper()]
        except KeyError:
            valid_statuses = [s.value for s in ProformaInvoiceStatusEnum]
            raise HTTPException(status_code=400, detail=f"Invalid status value: {status}. Valid are: {valid_statuses}")

    proformas = proforma_invoices_crud.list_proforma_invoices(
        db_session, client_id=client_id, project_id=project_id,
        company_id=company_id, status=status_enum, skip=skip, limit=limit
    )

    response_list = []
    for p_inv in proformas:
        resp_obj = ProformaInvoiceResponse.from_orm(p_inv)
        if p_inv.linked_document_id:
            resp_obj.proforma_pdf_url = f"/api/documents/{p_inv.linked_document_id}/download"
        if p_inv.generated_invoice_id:
            resp_obj.final_invoice_pdf_url = f"/api/documents/{p_inv.generated_invoice_id}/download"
        response_list.append(resp_obj)
    return response_list

@router.get("/{proforma_id}", response_model=ProformaInvoiceResponse)
def get_proforma_api(
    proforma_id: str, db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_proforma = proforma_invoices_crud.get_proforma_invoice_by_id(db_session, proforma_id)
    if not db_proforma:
        raise HTTPException(status_code=404, detail="Proforma Invoice not found")

    response = ProformaInvoiceResponse.from_orm(db_proforma)
    if db_proforma.linked_document_id:
        response.proforma_pdf_url = f"/api/documents/{db_proforma.linked_document_id}/download"
    if db_proforma.generated_invoice_id:
        response.final_invoice_pdf_url = f"/api/documents/{db_proforma.generated_invoice_id}/download"
    return response


class ProformaStatusUpdate(BaseModel):
    status: str

@router.put("/{proforma_id}/status", response_model=ProformaInvoiceResponse)
def update_proforma_status_api(
    proforma_id: str, status_update: ProformaStatusUpdate,
    db_session: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    try:
        new_status_enum = ProformaInvoiceStatusEnum[status_update.status.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid status value: {status_update.status}")

    update_data = {"status": new_status_enum}
    # Using sqlalchemy.func for server-side timestamp
    # Need to fetch the proforma again to check sent_date, using the CRUD
    existing_proforma_for_check = proforma_invoices_crud.get_proforma_invoice_by_id(db_session, proforma_id)
    if not existing_proforma_for_check:
        raise HTTPException(status_code=404, detail="Proforma Invoice not found for status update check")

    if new_status_enum == ProformaInvoiceStatusEnum.SENT and not existing_proforma_for_check.sent_date:
        update_data["sent_date"] = func.now()

    updated_proforma = proforma_invoices_crud.update_proforma_invoice(db_session, proforma_id, update_data)
    if not updated_proforma:
        raise HTTPException(status_code=404, detail="Proforma Invoice not found for status update")

    response = ProformaInvoiceResponse.from_orm(updated_proforma)
    if updated_proforma.linked_document_id:
        response.proforma_pdf_url = f"/api/documents/{updated_proforma.linked_document_id}/download"
    if updated_proforma.generated_invoice_id:
        response.final_invoice_pdf_url = f"/api/documents/{updated_proforma.generated_invoice_id}/download"
    return response


class GenerateInvoiceRequest(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None # YYYY-MM-DD
    target_language_code: Optional[str] = None
    # final_invoice_template_id: Optional[str] = None # Integer in DB

@router.post("/{proforma_id}/generate-invoice", response_model=ProformaInvoiceResponse)
def generate_final_invoice_api(
    proforma_id: str, request_data: Optional[GenerateInvoiceRequest] = Body(None),
    db_session: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    db_proforma = proforma_invoices_crud.get_proforma_invoice_by_id(db_session, proforma_id)
    if not db_proforma:
        raise HTTPException(status_code=404, detail="Proforma Invoice not found")
    if db_proforma.status != ProformaInvoiceStatusEnum.ACCEPTED:
        raise HTTPException(status_code=400, detail=f"Proforma Invoice must be 'accepted'. Status: {db_proforma.status.value}")
    if db_proforma.generated_invoice_id:
        raise HTTPException(status_code=400, detail="Final invoice already generated.")

    invoice_number_final = (request_data.invoice_number if request_data and request_data.invoice_number
                            else f"INV-{db_proforma.proforma_invoice_number}")
    invoice_date_final = (request_data.invoice_date if request_data and request_data.invoice_date
                          else datetime.date.today().strftime('%Y-%m-%d'))

    # Determine target language: request -> proforma's (if exists) -> default 'fr'
    # This assumes ProformaInvoice model in DB might have a target_language_code field from earlier steps.
    # If not, ProformaCreate.target_language_code is not stored on db_proforma.
    # For this example, let's assume we need to fetch it or use a default.
    # A default 'fr' is used if no other source is found.
    target_lang = 'fr' # Default
    if request_data and request_data.target_language_code:
        target_lang = request_data.target_language_code
    # else: # Logic to derive from db_proforma if it stored target_language_code
    #     if hasattr(db_proforma, 'target_language_code') and db_proforma.target_language_code:
    #         target_lang = db_proforma.target_language_code

    # Simplified way to get vat/discount if not stored on proforma model
    # This would ideally be part of the ProformaInvoice model or settings
    temp_proforma_create_obj_for_rates = ProformaInvoiceCreate( # Dummy create obj just to access defaults
        client_id=db_proforma.client_id, company_id=db_proforma.company_id, items=[]
    )
    vat_rate_to_use = temp_proforma_create_obj_for_rates.vat_rate_percentage
    # discount_rate_to_use = temp_proforma_create_obj_for_rates.discount_rate_percentage
    # Or, calculate from proforma amounts if possible:
    discount_rate_to_use = (db_proforma.discount_amount / db_proforma.subtotal_amount * 100
                            if db_proforma.subtotal_amount and db_proforma.discount_amount else 0.0)


    additional_context_for_invoice_pdf = {
        "invoice_id": invoice_number_final, "proforma_id": db_proforma.proforma_invoice_number,
        "current_date": invoice_date_final, "document_title": "INVOICE",
        "vat_rate_percentage": vat_rate_to_use,
        "discount_rate_percentage": discount_rate_to_use,
        "lite_selected_products": [{
            "product_id": item.product_id, "name": item.description, "description": item.description,
            "quantity": item.quantity, "unit_price_override": item.unit_price
        } for item in db_proforma.items],
        # "db_session": db_session, # Removed for sqlite context
        "payment_terms": db_proforma.payment_terms,
    }

    try:
        project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        app_root_for_templates = os.path.join(project_root_dir, "templates")
        invoice_template_file_path = os.path.join(app_root_for_templates, target_lang, "invoice_template.html")

        if not os.path.exists(invoice_template_file_path): # Fallback to EN
            invoice_template_file_path = os.path.join(app_root_for_templates, "en", "invoice_template.html")
            if not os.path.exists(invoice_template_file_path): # Fallback to proforma template
                invoice_template_file_path = os.path.join(app_root_for_templates, target_lang, "proforma_invoice_template.html")
                if not os.path.exists(invoice_template_file_path): # Fallback to EN proforma template
                    invoice_template_file_path = os.path.join(app_root_for_templates, "en", "proforma_invoice_template.html")
                    if not os.path.exists(invoice_template_file_path):
                        raise HTTPException(status_code=404, detail="Invoice HTML template (and fallbacks) not found.")

        with open(invoice_template_file_path, 'r', encoding='utf-8') as f:
            html_template_str = f.read()
        template_base_path = f"file://{os.path.dirname(invoice_template_file_path).replace(os.sep, '/')}/"

        context_data = get_proforma_invoice_context_data(
            client_id=db_proforma.client_id, company_id=db_proforma.company_id,
            project_id=db_proforma.project_id, target_language_code=target_lang,
            additional_context=additional_context_for_invoice_pdf
        )
        rendered_html = render_html_template(html_template_str, context_data)
        pdf_bytes = convert_html_to_pdf(rendered_html, base_url=template_base_path)
        if not pdf_bytes:
            raise WeasyPrintError("Final Invoice PDF generation returned no bytes.")

        pdf_document_name = f"Invoice {invoice_number_final} (Proforma {db_proforma.proforma_invoice_number})"
        pdf_file_prefix = f"invoice_{invoice_number_final.replace('/', '_').replace(' ', '_')}"
        user_id_for_doc = getattr(current_user, 'id', getattr(current_user, 'user_id', None))
        if not user_id_for_doc:
             raise HTTPException(status_code=500, detail="User ID not found for document attribution.")


        generated_invoice_doc_id = _internal_save_pdf_and_create_document_record(
            db_session=db_session, pdf_bytes=pdf_bytes, client_id=db_proforma.client_id,
            project_id=db_proforma.project_id, document_name=pdf_document_name,
            file_name_prefix=pdf_file_prefix, template_id_source=None,
            user_id=user_id_for_doc
        )

        if generated_invoice_doc_id:
            update_payload = {"generated_invoice_id": generated_invoice_doc_id, "status": ProformaInvoiceStatusEnum.INVOICED}
            updated_proforma = proforma_invoices_crud.update_proforma_invoice(db_session, proforma_id, update_payload)
            if not updated_proforma:
                raise HTTPException(status_code=500, detail="Failed to update proforma after generating final invoice.")

            # Refresh to ensure all fields are current, including any from update_proforma_invoice
            db_session.refresh(updated_proforma)

            response = ProformaInvoiceResponse.from_orm(updated_proforma)
            # Ensure URLs are correctly set on the response object
            if updated_proforma.linked_document_id:
                 response.proforma_pdf_url = f"/api/documents/{updated_proforma.linked_document_id}/download"
            if updated_proforma.generated_invoice_id: # This is the one we just created
                response.final_invoice_pdf_url = f"/api/documents/{updated_proforma.generated_invoice_id}/download"
            return response
        else:
            raise HTTPException(status_code=500, detail="Failed to save generated final invoice PDF.")

    except WeasyPrintError as wpe:
        raise HTTPException(status_code=500, detail=f"PDF generation error for final invoice: {str(wpe)}")
    except HTTPException: # Re-raise HTTPExceptions
        raise
    except Exception as exc:
        # import traceback; traceback.print_exc(); # For debugging
        raise HTTPException(status_code=500, detail=f"Error generating final invoice: {str(exc)}")

# Ensure `datetime` is imported for `datetime.date` and `datetime.datetime`
# Ensure `sqlalchemy.func` is imported for `func.now()`
# Ensure `os` is imported for path operations.
# Ensure `uuid` is imported for `uuid.uuid4()`.
# Ensure `proforma_invoices_crud` provides all necessary SQLAlchemy CRUDs.
# Ensure `get_client_by_id_sqlite`, `add_client_document_sqlite`, etc. are correctly imported from `db`.
# Ensure `db.utils.get_proforma_invoice_context_data` is correctly imported.
# Ensure `api.models.User` and `ProformaInvoiceStatusEnum` are correct.
# Ensure `html_to_pdf_util` is available.
# Ensure `api.dependencies.get_db` and `get_current_active_user` are correct.
