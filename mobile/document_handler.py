import os
# import sys # For sys.path modification
# from PyQt5.QtWidgets import QMessageBox
# from PyQt5.QtGui import QDesktopServices
# from PyQt5.QtCore import QUrl

# Adjust sys.path to include the parent directory for db and utils
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # TODO: Re-evaluate path adjustments for mobile context or API structure.
# import db as db_manager # TODO: Direct DB access replaced by API calls via mobile_data_api. `html_to_pdf_util` dependency also needs review for mobile.
import html_to_pdf_util # TODO: `html_to_pdf_util` for HTML rendering (Jinja2) might be kept. PDF conversion itself is now via API call.
from app_config import CONFIG # TODO: This will need to be replaced with mobile config solution
# from PyQt5.QtGui import QDesktopServices # Added
# from PyQt5.QtCore import QUrl # Added
from . import data_handler as mobile_data_api

# try:
    # from email_service import EmailSenderService # TODO: Mobile email functionality should use native sharing/email intents.
# except ImportError:
    # if os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) not in sys.path:
        # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # TODO: Re-evaluate path adjustments for mobile context or API structure.
    # from email_service import EmailSenderService # TODO: Mobile email functionality should use native sharing/email intents.


class LiteDocumentHandler:
    def __init__(self): # parent_modal removed
        # self.parent_modal = parent_modal
        pass

    def _get_client_and_company_ids(self) -> tuple[str | None, str | None]:
        api_response = mobile_data_api.get_client_and_company_ids_from_api()
        company_id = api_response.get('company_id') if api_response else None
        client_id = api_response.get('client_id') if api_response else None

        if not company_id:
            print("Warning: No default company found.")
            # Optionally show message box if parent_modal is available
            # if self.parent_modal:
            #     print(f"WARNING: Setup Warning: No default company found. Please configure one.")

        if not client_id:
            print("Warning: No clients found in DB or client data is invalid. PDF context will be incomplete.")
            # Optionally show message box
            # if self.parent_modal:
            #     print(f"WARNING: Data Warning: No clients found. PDF context will be incomplete.")

        return client_id, company_id

    def _prepare_document_context(self, selected_language_code: str, selected_country_data: dict, selected_products_with_qty: list, additional_doc_context: dict = None) -> dict | None:
        client_id_override = (additional_doc_context or {}).pop('client_id_override', None) # pop to remove it
        temp_client_id, company_id = self._get_client_and_company_ids()
        final_client_id = client_id_override if client_id_override else temp_client_id

        if not final_client_id or not company_id:
            error_message = "Company ID or a Client ID is missing. Cannot prepare document context."
            # if self.parent_modal:
            print(f"CRITICAL: Error: {error_message}")
            # else:
            #     print(f"Error: {error_message}")
            return None

        additional_context_for_db = {'lite_selected_products': selected_products_with_qty}
        if additional_doc_context: # additional_doc_context has had client_id_override popped
            additional_context_for_db.update(additional_doc_context)

        context = mobile_data_api.get_document_context_data_from_api(
            client_id=final_client_id,
            company_id=company_id,
            target_language_code=selected_language_code,
            selected_products_with_qty=selected_products_with_qty, # Pass this through
            additional_doc_context=additional_context_for_db # Pass this through
        )

        if context and selected_country_data:
            context['doc_specific_country_selection'] = selected_country_data

        return context

    # Placeholder methods for main actions
    def generate_and_visualize_pdfs(self, language_code: str, country_data: dict, products_with_qty: list, templates_data: list[dict], pdf_action: str):
        print("generate_and_visualize_pdfs called with:")
        print(f"  Language: {language_code}, Country: {country_data.get('country_name') if country_data else 'N/A'}, PDF Action: {pdf_action}")
        # print(f"  Products: {products_with_qty}") # Can be verbose
        # print(f"  Templates: {[t.get('template_name') for t in templates_data]}") # Can be verbose

        doc_context = self._prepare_document_context(language_code, country_data, products_with_qty)
        if not doc_context:
            # Error message already shown by _prepare_document_context or its sub-calls
            print("Document context preparation failed. Aborting PDF generation.")
            return # Can't proceed without context

        pdf_outputs = self._generate_pdf_outputs(doc_context, templates_data, pdf_action)

        if not pdf_outputs:
            # Warning already shown by _generate_pdf_outputs if it returned None
            print("No PDF outputs were generated by _generate_pdf_outputs.")
            return

        # At this point, pdf_outputs is a list of (name, pdf_bytes) tuples
        print(f"Successfully generated {len(pdf_outputs)} PDF document(s).")

        # For visualization, save to temp files and open
        # TODO: Implement get_mobile_temp_dir() for mobile platform
        temp_dir = mobile_data_api.get_mobile_temp_dir() # Use the one from data_handler CONFIG.get("document_generation_temp_dir", "temp_generated_docs")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)

        opened_files_count = 0
        for i, (name, pdf_bytes) in enumerate(pdf_outputs):
            # Sanitize name for use as a filename
            safe_name = "".join(c if c.isalnum() else "_" for c in name)
            # Ensure unique filename if multiple PDFs might have similar names (e.g. from same template name but different context)
            temp_pdf_path = os.path.join(temp_dir, f"{safe_name}_{i+1}.pdf")

            try:
                with open(temp_pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                print(f"Saved PDF to: {temp_pdf_path}")

                # Open the PDF using the default system viewer
                # TODO: Implement mobile-specific PDF opening/sharing
                # if not QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(temp_pdf_path))):
                #     if self.parent_modal:
                #         print(f"WARNING: Opening PDF Failed: Could not open {temp_pdf_path}.\nPlease check if you have a default PDF viewer configured.")
                #     else:
                #         print(f"Warning: Could not open {temp_pdf_path}. Please check default PDF viewer.")
                # else:
                #     opened_files_count +=1
                print(f"INFO: PDF saved to {temp_pdf_path}. Mobile opening/sharing to be implemented.")
                opened_files_count +=1 # Assume success for now
            except Exception as e_save:
                print(f"Error saving or opening PDF {temp_pdf_path}: {e_save}")
                # if self.parent_modal:
                print(f"CRITICAL: File Error: Could not save or open PDF: {temp_pdf_path}\n{e_save}")

        if opened_files_count > 0: # and self.parent_modal:
            print(f"INFO: PDFs Generated: {opened_files_count} PDF(s) generated and saved to '{temp_dir}'.\nAttempted to open them with system viewer.")
        elif opened_files_count == 0: # and self.parent_modal:
             print(f"WARNING: PDFs Not Opened: PDFs were generated but could not be saved or opened. Check console/logs.")


    def _generate_single_pdf_bytes(self, html_content: str, base_url_for_resources: str) -> bytes | None: # Renamed template_directory
        """Helper to convert a single HTML string to PDF bytes via API."""
        try:
            # The base_url_for_resources is now passed to the API,
            # which might use it to resolve relative paths for images, CSS, etc.
            # No local path manipulation for base_url here.
            pdf_bytes = mobile_data_api.convert_html_to_pdf_api(html_content, base_url=base_url_for_resources)
            return pdf_bytes
        except Exception as e:
            print(f"Error generating single PDF via API: {e}")
            # Optionally, show message to user
            # print(f"CRITICAL: PDF Conversion Error via API: Failed to convert HTML to PDF: {e}")
            return None

    def _generate_pdf_outputs(self, context_data: dict, templates_data: list[dict], pdf_action: str) -> list[tuple[str, bytes]] | None:
        generated_pdfs = []
        rendered_html_parts = []
        # Use a default if CONFIG or templates_dir is not found, or handle error more gracefully
        # TODO: Implement get_mobile_templates_dir() or fetch templates via API
        template_base_dir_config = mobile_data_api.get_mobile_templates_dir() # CONFIG.get("templates_dir", "templates")
        # Ensure template_base_dir is an absolute path from the application root
        # Assuming CONFIG refers to app_config.py in the root, and templates_dir is relative to that.
        # If CONFIG['application_path'] is available:
        # TODO: Templates might be bundled or fetched via API. Adapt loading.
        # app_root = CONFIG.get("application_path", os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        # template_base_dir = os.path.join(app_root, template_base_dir_config)
        template_base_dir = template_base_dir_config # Placeholder, assuming get_mobile_templates_dir returns a usable path or object


        for template_info in templates_data:
            template_name = template_info.get('template_name', 'Untitled Document')
            template_html_content = None

            if template_info.get('raw_template_file_data'):
                raw_data = template_info['raw_template_file_data']
                if isinstance(raw_data, bytes):
                    try:
                        template_html_content = raw_data.decode('utf-8')
                    except UnicodeDecodeError:
                        print(f"Error decoding raw template data for {template_name}. Assuming it's not text.")
                        # Potentially handle non-text raw data if applicable, or skip
                        continue
                elif isinstance(raw_data, str):
                    template_html_content = raw_data
                else:
                    print(f"Warning: Raw template data for {template_name} is of unexpected type: {type(raw_data)}")
                    continue

            elif template_info.get('base_file_name') and template_info.get('language_code'):
                # Attempt to get template_id if available, otherwise use base_file_name as a fallback key
                template_id_for_api = template_info.get('template_id')
                if not template_id_for_api:
                    print(f"Warning: 'template_id' missing for template '{template_name}'. API call for content might fail or be incorrect.")
                    # Fallback or skip logic can be here if template_id is strictly required by API
                    # For mock, we might allow base_file_name or skip
                    template_html_content = f"<html><body>Error: Missing template_id for {template_name}</body></html>"
                else:
                    template_html_content = mobile_data_api.get_template_content_from_api(template_id=template_id_for_api)

                if not template_html_content: # Ensure content was actually fetched
                    print(f"Error: Could not fetch template content from API for template: {template_name} (ID: {template_id_for_api})")
                    template_html_content = f"<html><body>Error loading {template_name}</body></html>" # Placeholder on error

            if not template_html_content:
                print(f"Could not load content for template: {template_name}")
                continue

            try:
                rendered_html = html_to_pdf_util.render_html_template(template_html_content, context_data)
            except Exception as e_render: # Catch errors during Jinja2 rendering
                print(f"Error rendering HTML for template {template_name}: {e_render}")
                # if self.parent_modal:
                print(f"WARNING: Template Error: Error rendering template '{template_name}':\n{e_render}")
                continue # Skip this template

            if pdf_action == "separate":
                # For separate PDFs, the base_url for resource loading should point to the specific template's directory
                # or a common resource directory. Here, template_base_dir is common.
                pdf_bytes = self._generate_single_pdf_bytes(rendered_html, template_base_dir)
                if pdf_bytes:
                    generated_pdfs.append((template_name, pdf_bytes))
            elif pdf_action == "combine":
                rendered_html_parts.append(rendered_html)
            else: # Should not happen with radio buttons
                print(f"Unknown PDF action: {pdf_action}")


        if pdf_action == "combine" and rendered_html_parts:
            page_break_html = '<div style="page-break-after:always;"></div>'
            # Avoid adding page break after the last part
            combined_html = ""
            for i, part_html in enumerate(rendered_html_parts):
                combined_html += part_html
                if i < len(rendered_html_parts) - 1: # Not the last part
                    combined_html += page_break_html

            pdf_bytes = self._generate_single_pdf_bytes(combined_html, template_base_dir)
            if pdf_bytes:
                generated_pdfs.append(("Combined Document", pdf_bytes))

        if not generated_pdfs:
            # if self.parent_modal:
            print(f"WARNING: PDF Generation Failed: No PDF documents could be generated. Check logs for errors.")
            # else:
            #     print("Warning: No PDF documents were generated.")
            return None

        return generated_pdfs

    # TODO: Mobile email functionality should use native sharing/email intents.
    def generate_and_send_email(self, client_id_for_context: str, language_code: str, country_data: dict, products_with_qty: list, templates_data: list[dict], pdf_action: str, recipients: list[str], subject: str, body_html: str) -> bool:
        print(f"generate_and_send_email called for client: {client_id_for_context}")

        doc_context = self._prepare_document_context(
            selected_language_code=language_code,
            selected_country_data=country_data,
            selected_products_with_qty=products_with_qty,
            additional_doc_context={'client_id_override': client_id_for_context}
        )

        if not doc_context:
            # if self.parent_modal:
            print(f"CRITICAL: Email Error: Failed to prepare document context for email.")
            # else:
            #     print("Email Error: Failed to prepare document context.")
            return False

        generated_pdf_data_list = self._generate_pdf_outputs(doc_context, templates_data, pdf_action)

        if not generated_pdf_data_list:
            # Error message already shown by _generate_pdf_outputs
            return False

        # TODO: Implement get_mobile_temp_dir() for mobile platform
        temp_dir = mobile_data_api.get_mobile_temp_dir() # CONFIG.get("document_generation_temp_dir", "temp_docs")
        if not os.path.exists(temp_dir): # Ensure temp_dir is usable
             os.makedirs(temp_dir, exist_ok=True)
        attachment_paths = []

        try:
            for pdf_name, pdf_bytes in generated_pdf_data_list:
                safe_filename = "".join([c if c.isalnum() else "_" for c in pdf_name]) + ".pdf"
                temp_pdf_path = os.path.join(temp_dir, safe_filename)
                with open(temp_pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                attachment_paths.append(temp_pdf_path)
                print(f"Prepared attachment: {temp_pdf_path}")

            # email_service = EmailSenderService() # Assumes default SMTP config or one is set via settings # TODO: Mobile email functionality should use native sharing/email intents.

            # if not email_service.smtp_config: # TODO: Mobile email functionality should use native sharing/email intents.
                # if self.parent_modal:
                    # print(f"CRITICAL: Email Error: SMTP configuration not found or invalid. Cannot send email.")
                # else:
                    # print("Email Error: SMTP configuration not found or invalid.")
                # return False # Must return False after cleanup
            print("INFO: Skipping actual email sending for mobile. Attachments prepared at:", attachment_paths)
            # success, message = email_service.send_email( # TODO: Mobile email functionality should use native sharing/email intents.
            #     client_id=client_id_for_context, # For logging/tracking purposes in email_service
            #     recipients=recipients,
            #     subject_template=subject, # Passed as already rendered/final string
            #     body_html_template=body_html, # Passed as already rendered/final string
            #     attachments=attachment_paths,
            #     template_language_code=language_code, # For potential use in email_service if it does further templating
            #     project_id=doc_context.get('project', {}).get('id') # For logging/tracking
            # )
            success = True # Placeholder
            message = "Email sending skipped for mobile." # Placeholder


            if success:
                # if self.parent_modal:
                print(f"INFO: Email Sent: Email successfully sent. Message: {message}")
                # print(f"Email successfully sent. Message: {message}")
                return True
            else:
                # if self.parent_modal:
                print(f"WARNING: Email Failed: Failed to send email. Error: {message}")
                # print(f"Failed to send email. Error: {message}")
                return False

        except Exception as e:
            print(f"An error occurred during email preparation or sending: {e}")
            # if self.parent_modal:
            print(f"CRITICAL: Email System Error: An unexpected error occurred: {e}")
            return False
        finally:
            # Cleanup temporary files
            for path in attachment_paths:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        print(f"Cleaned up attachment: {path}")
                except Exception as e_cleanup:
                    print(f"Error cleaning up attachment {path}: {e_cleanup}")

# Ensure this file is not executable as a script
