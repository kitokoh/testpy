# -*- coding: utf-8 -*-
import os
import shutil
import sqlite3 # Should be checked if still needed directly, db_manager should handle most
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QMessageBox, QDialog, QInputDialog # QInputDialog was used in add_new_country/city, not directly in moved methods but good to keep context
# from PyQt5.QtCore import QStandardPaths # Removed as not used by these functions

# -*- coding: utf-8 -*-
import os
import shutil
import sqlite3 # Should be checked if still needed directly, db_manager should handle most
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QMessageBox, QDialog, QInputDialog # QInputDialog was used in add_new_country/city, not directly in moved methods but good to keep context
# from PyQt5.QtCore import QStandardPaths # Removed as not used by these functions

# Import necessary functions directly from their new CRUD module locations
from controllers.client_controller import ClientController # Added
from db.cruds.locations_crud import get_country_by_id, get_city_by_id # These are fine as locations_crud is not refactored to class yet
from db.cruds.status_settings_crud import get_status_setting_by_name, get_status_setting_by_id # Fine
from db.cruds.clients_crud import clients_crud_instance # Import the instance
from db.cruds.projects_crud import add_project, get_project_by_id, delete_project # Fine
from db.cruds.tasks_crud import add_task # Fine
from db.cruds.contacts_crud import get_contact_by_email, add_contact, update_contact, link_contact_to_client, get_contacts_for_client, update_client_contact_link # Fine
from db.cruds.products_crud import get_product_by_name, add_product
from db.cruds.client_project_products_crud import add_product_to_client_or_project, get_products_for_client_or_project

# Import dialogs that are used within the moved logic
# Assuming these dialogs are in a 'dialogs.py' or similar accessible location.
# If they are defined in main.py and not moved yet, this will cause an issue.
# For this step, we assume they are accessible.
from dialogs import (
    ContactDialog, ProductDialog, CreateDocumentDialog, EditClientDialog
)
# If ClientWidget is used by any logic here (e.g. for refreshing tabs), it would also need to be importable.
# from client_widget import ClientWidget # Not directly used in the functions being moved, but DocumentManager uses it.

import logging # For logging errors or info

def handle_create_client_execution(doc_manager, client_data_dict=None):
    client_controller = ClientController() # Instantiate controller

    if not client_data_dict:
        # This path should ideally not be taken if AddNewClientDialog is always used
        QMessageBox.critical(doc_manager, "Erreur", "Données client non fournies.")
        return

    # Basic validation of data from dialog (raw names)
    client_name_val = client_data_dict.get("client_name", "").strip()
    country_name_for_folder = client_data_dict.get("country_name", "").strip() # Used for folder name
    project_identifier_val = client_data_dict.get("project_identifier", "").strip()

    if not client_name_val or not country_name_for_folder or not project_identifier_val:
        QMessageBox.warning(doc_manager, doc_manager.tr("Champs Requis"), doc_manager.tr("Nom client, Pays et ID Projet sont obligatoires."))
        doc_manager.notify(title=doc_manager.tr("Champs Requis Manquants"),
                           message=doc_manager.tr("Nom client, Pays et ID Projet sont obligatoires pour la création."),
                           type='WARNING')
        return

    # --- Client Creation via Controller ---
    client_data_dict_for_controller = client_data_dict.copy()
    client_data_dict_for_controller['created_by_user_id'] = doc_manager.current_user_id

    created_client_info = client_controller.create_client(client_data_dict_for_controller)

    actual_new_client_id = None
    new_project_id_central_db = None # Define for later use in error handling

    if not created_client_info or not created_client_info.get("client_id"):
        QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"),
                             doc_manager.tr("Impossible de créer le client via le contrôleur."))
        doc_manager.notify(title=doc_manager.tr("Erreur Création Client"),
                           message=created_client_info.get("error", doc_manager.tr("Le contrôleur n'a pas pu créer le client.")),
                           type='ERROR')
        return

    actual_new_client_id = created_client_info.get("client_id")
    country_id_val = created_client_info.get("country_id") # Resolved by controller
    city_id_val = created_client_info.get("city_id")       # Resolved by controller

    # --- Folder Creation ---
    folder_name_str = f"{client_name_val}_{country_name_for_folder}_{project_identifier_val}".replace(" ", "_").replace("/", "-")
    base_folder_full_path = os.path.join(doc_manager.config["clients_dir"], folder_name_str)

    # Note: project_identifier uniqueness should ideally be handled by client_controller.create_client
    # If it returns successfully, we assume project_identifier is unique.
    # The folder path uniqueness is a separate check.
    if os.path.exists(base_folder_full_path):
        QMessageBox.warning(doc_manager, doc_manager.tr("Dossier Existant"),
                            doc_manager.tr("Un dossier client avec un chemin similaire existe déjà: {0}. Le client a été créé en DB, mais le dossier n'est pas unique.").format(base_folder_full_path))
        doc_manager.notify(title=doc_manager.tr("Dossier Client Existant"),
                           message=doc_manager.tr("Un dossier client avec le chemin '{0}' existe déjà. Le client ID {1} a été créé en DB mais le dossier n'est pas unique.").format(base_folder_full_path, actual_new_client_id),
                           type='WARNING')
        # Client exists in DB. We might want to update it with this path, or allow user to change, or rollback.
        # For now, proceed and update client with this path, assuming user might consolidate.
        # This behavior might need refinement based on product requirements.

    try:
        os.makedirs(base_folder_full_path, exist_ok=True)
        # Update client record with the base_folder_full_path
        if actual_new_client_id: # Ensure client ID is valid
            clients_crud_instance.update_client(actual_new_client_id, {'default_base_folder_path': base_folder_full_path})
            created_client_info['default_base_folder_path'] = base_folder_full_path # Keep our local copy updated

        # Create language subfolders
        # Ensure selected_languages is a string from controller, then split.
        selected_langs_str = created_client_info.get("languages", "fr") # 'languages' is the key from controller
        selected_langs_list = selected_langs_str.split(',') if isinstance(selected_langs_str, str) else ["fr"]


        for lang_code in selected_langs_list:
            os.makedirs(os.path.join(base_folder_full_path, lang_code.strip()), exist_ok=True)

    except OSError as e_os:
        QMessageBox.critical(doc_manager, doc_manager.tr("Erreur Dossier"), doc_manager.tr("Erreur de création du dossier client:\n{0}").format(str(e_os)))
        doc_manager.notify(title=doc_manager.tr("Erreur Création Dossier"), message=doc_manager.tr("Erreur de création du dossier pour le client '{0}'.").format(client_name_val), type='ERROR')
        if actual_new_client_id:
            clients_crud_instance.delete_client(actual_new_client_id) # Rollback client creation
            doc_manager.notify(title=doc_manager.tr("Rollback DB"), message=doc_manager.tr("Entrée client (ID: {0}) annulée suite à l'erreur de dossier.").format(actual_new_client_id), type='INFO')
        return # Stop further execution

    # --- Project and Task Creation (remains largely the same, using actual_new_client_id) ---
    try:
        project_status_planning_obj = get_status_setting_by_name("Planning", "Project")
        project_status_id_for_pm = project_status_planning_obj['status_id'] if project_status_planning_obj else None

        if not project_status_id_for_pm:
            QMessageBox.warning(doc_manager, doc_manager.tr("Erreur Configuration Projet"),
                                doc_manager.tr("Statut de projet par défaut 'Planning' non trouvé. Le projet ne sera pas créé avec un statut initial."))
            doc_manager.notify(title=doc_manager.tr("Erreur Configuration Projet"),
                               message=doc_manager.tr("Statut projet par défaut 'Planning' non trouvé."),
                               type='WARNING')

        project_data_for_db = {
            'client_id': actual_new_client_id,
            'project_name': f"Projet pour {created_client_info.get('client_name', client_name_val)}", # Use name from controller if available
            'description': f"Projet pour client: {created_client_info.get('client_name', client_name_val)}. Besoin initial: {created_client_info.get('primary_need_description', '')}",
            'start_date': datetime.now().strftime("%Y-%m-%d"),
            'deadline_date': (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
            'budget': created_client_info.get('price', 0.0), # Price from controller (likely 0 or default)
            'status_id': project_status_id_for_pm,
            'priority': 1
        }
        new_project_id_central_db = add_project(project_data_for_db)

        if new_project_id_central_db:
            QMessageBox.information(doc_manager, doc_manager.tr("Projet Créé (Central DB)"),
                                    doc_manager.tr("Un projet associé a été créé pour {0}.").format(created_client_info.get('client_name', client_name_val)))

            task_status_todo_obj = get_status_setting_by_name("To Do", "Task")
            task_status_id_for_todo = task_status_todo_obj['status_id'] if task_status_todo_obj else None

            if not task_status_id_for_todo:
                QMessageBox.warning(doc_manager, doc_manager.tr("Erreur Configuration Tâche"),
                                    doc_manager.tr("Statut de tâche par défaut 'To Do' non trouvé."))

            standard_tasks = [
                {"name": "Initial Client Consultation & Needs Assessment", "description": "Understand client requirements, objectives, target markets, and budget.", "priority_val": 2, "deadline_days": 3},
                {"name": "Market Research & Analysis", "description": "Research target international markets, including competition, regulations, and cultural nuances.", "priority_val": 1, "deadline_days": 7},
                {"name": "Post-Sales Follow-up & Support", "description": "Follow up with the client after delivery.", "priority_val": 1, "deadline_days": 60}
            ]

            for task_item in standard_tasks:
                task_deadline = (datetime.now() + timedelta(days=task_item["deadline_days"])).strftime("%Y-%m-%d")
                add_task({
                    'project_id': new_project_id_central_db,
                    'task_name': task_item["name"],
                    'description': task_item["description"],
                    'status_id': task_status_id_for_todo,
                    'priority': task_item["priority_val"],
                    'due_date': task_deadline
                })
            QMessageBox.information(doc_manager, doc_manager.tr("Tâches Créées (Central DB)"),
                                    doc_manager.tr("Des tâches standard ont été ajoutées au projet pour {0}.").format(created_client_info.get('client_name', client_name_val)))
        else:
            QMessageBox.warning(doc_manager, doc_manager.tr("Erreur DB Projet"),
                                doc_manager.tr("Le client a été créé, mais la création du projet associé a échoué."))
            doc_manager.notify(title=doc_manager.tr("Erreur Création Projet Associé"),
                               message=doc_manager.tr("Client créé (ID: {0}), mais échec de la création du projet associé.").format(actual_new_client_id),
                               type='WARNING')

        # --- Update UI Map Data (ui_map_data) ---
        client_dict_from_controller = created_client_info # Use the data from controller

        ui_map_data = None
        if client_dict_from_controller:
            # Fetch names for IDs obtained from controller
            country_obj = get_country_by_id(client_dict_from_controller.get('country_id')) if client_dict_from_controller.get('country_id') else None
            city_obj = get_city_by_id(client_dict_from_controller.get('city_id')) if client_dict_from_controller.get('city_id') else None
            # Status should be part of created_client_info if controller sets it, or fetch if controller returns status_id
            status_id_from_controller = client_dict_from_controller.get('client_status_id') # Key used in controller
            status_obj = get_status_setting_by_id(status_id_from_controller) if status_id_from_controller else None

            sel_langs_str_ui = client_dict_from_controller.get('languages', 'fr') # Key used in controller
            sel_langs_list_ui = sel_langs_str_ui.split(',') if isinstance(sel_langs_str_ui, str) else ['fr']

            ui_map_data = {
                "client_id": client_dict_from_controller.get('client_id'),
                "client_name": client_dict_from_controller.get('client_name'),
                "company_name": client_dict_from_controller.get('company_name'),
                "need": client_dict_from_controller.get('primary_need_description'),
                "country": country_obj['country_name'] if country_obj else client_data_dict.get("country_name", "N/A"), # Fallback to original input if needed
                "country_id": client_dict_from_controller.get('country_id'),
                "city": city_obj['city_name'] if city_obj else client_data_dict.get("city_name", "N/A"), # Fallback to original input if needed
                "city_id": client_dict_from_controller.get('city_id'),
                "project_identifier": client_dict_from_controller.get('project_identifier'),
                "base_folder_path": client_dict_from_controller.get('default_base_folder_path'), # Updated earlier
                "selected_languages": sel_langs_list_ui,
                "price": client_dict_from_controller.get('price', 0), # Price from controller
                "notes": client_dict_from_controller.get('notes', ''), # Notes from controller
                "status": status_obj['status_name'] if status_obj else "N/A",
                "status_id": status_id_from_controller,
                "creation_date": client_dict_from_controller.get('created_at','').split("T")[0] if client_dict_from_controller.get('created_at') else datetime.now().strftime("%Y-%m-%d"),
                "category": client_dict_from_controller.get('category', 'Standard') # Category from controller
            }
            doc_manager.clients_data_map[actual_new_client_id] = ui_map_data
            doc_manager.add_client_to_list_widget(ui_map_data)

        if ui_map_data:
            contact_dialog = ContactDialog(client_id=actual_new_client_id, parent=doc_manager)
            if contact_dialog.exec_() == QDialog.Accepted:
                contact_form_data = contact_dialog.get_data()
                try:
                    existing_contact = get_contact_by_email(contact_form_data['email'])
                    contact_id_to_link = None
                    if existing_contact:
                        contact_id_to_link = existing_contact['contact_id']
                        update_data = {k: v for k, v in contact_form_data.items() if k in ['name', 'phone', 'position'] and v != existing_contact.get(k)}
                        if update_data: update_contact(contact_id_to_link, update_data)
                    else:
                        new_contact_id = add_contact({
                            'name': contact_form_data['name'], 'email': contact_form_data['email'],
                            'phone': contact_form_data['phone'], 'position': contact_form_data['position']
                        })
                        if new_contact_id: contact_id_to_link = new_contact_id
                        else: QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"), doc_manager.tr("Impossible de créer le nouveau contact global."))

                    if contact_id_to_link:
                        if contact_form_data['is_primary_for_client']:
                            client_contacts = get_contacts_for_client(actual_new_client_id)
                            if client_contacts:
                                for cc in client_contacts:
                                    if cc['is_primary_for_client'] and cc.get('client_contact_id'):
                                        update_client_contact_link(cc['client_contact_id'], {'is_primary_for_client': False})
                        link_id = link_contact_to_client(actual_new_client_id, contact_id_to_link, is_primary=contact_form_data['is_primary_for_client'])
                        if not link_id: QMessageBox.warning(doc_manager, doc_manager.tr("Erreur DB"), doc_manager.tr("Impossible de lier le contact au client (le lien existe peut-être déjà)."))
                except Exception as e_contact_save:
                    QMessageBox.critical(doc_manager, doc_manager.tr("Erreur Sauvegarde Contact"), doc_manager.tr("Une erreur est survenue lors de la sauvegarde du contact : {0}").format(str(e_contact_save)))

            # ProductDialog and subsequent price calculation
            product_dialog = ProductDialog(client_id=actual_new_client_id, app_root_dir=doc_manager.app_root_dir, parent=doc_manager)
            if product_dialog.exec_() == QDialog.Accepted:
                products_list_data = product_dialog.get_data()
                for product_item_data in products_list_data:
                    try:
                        global_product = get_product_by_name(product_item_data['name'])
                        global_product_id = None; current_base_unit_price = None
                        if global_product:
                            global_product_id = global_product['product_id']; current_base_unit_price = global_product.get('base_unit_price')
                        else:
                            new_global_product_id = add_product({
                                'product_name': product_item_data['name'], 'description': product_item_data['description'],
                                'base_unit_price': product_item_data['unit_price'], 'language_code': product_item_data.get('language_code', 'fr')
                            })
                            if new_global_product_id: global_product_id = new_global_product_id; current_base_unit_price = product_item_data['unit_price']
                            else: QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"), doc_manager.tr("Impossible de créer le produit global '{0}' (lang: {1}).").format(product_item_data['name'], product_item_data.get('language_code', 'fr'))); continue

                        if global_product_id:
                            unit_price_override_val = product_item_data['unit_price'] if current_base_unit_price is None or product_item_data['unit_price'] != current_base_unit_price else None
                            link_data = {'client_id': actual_new_client_id, 'project_id': None, 'product_id': global_product_id, 'quantity': product_item_data['quantity'], 'unit_price_override': unit_price_override_val}
                            cpp_id = add_product_to_client_or_project(link_data)
                            if not cpp_id: QMessageBox.warning(doc_manager, doc_manager.tr("Erreur DB"), doc_manager.tr("Impossible de lier le produit '{0}' au client.").format(product_item_data['name']))
                    except Exception as e_product_save:
                        QMessageBox.critical(doc_manager, doc_manager.tr("Erreur Sauvegarde Produit"), doc_manager.tr("Une erreur est survenue lors de la sauvegarde du produit '{0}': {1}").format(product_item_data.get('name', 'Inconnu'), str(e_product_save)))

            # Recalculate price after product dialog (whether accepted or cancelled)
            linked_products = get_products_for_client_or_project(client_id=actual_new_client_id, project_id=None)
            if linked_products is None: linked_products = []
            calculated_total_sum = sum(p.get('total_price_calculated', 0.0) for p in linked_products if p.get('total_price_calculated') is not None)
            clients_crud_instance.update_client(actual_new_client_id, {'price': calculated_total_sum})
            ui_map_data['price'] = calculated_total_sum # Update the map
            if actual_new_client_id in doc_manager.clients_data_map: doc_manager.clients_data_map[actual_new_client_id]['price'] = calculated_total_sum

            # CreateDocumentDialog call
            create_document_dialog = CreateDocumentDialog(client_info=ui_map_data, config=doc_manager.config, parent=doc_manager)
            if create_document_dialog.exec_() == QDialog.Accepted: logging.info("CreateDocumentDialog accepted.")
            else: logging.info("CreateDocumentDialog cancelled.")

        else: # ui_map_data was not populated (should not happen if controller succeeded)
             QMessageBox.warning(doc_manager, doc_manager.tr("Erreur Données Client"), doc_manager.tr("Les données du client (ui_map_data) ne sont pas disponibles pour la séquence de dialogue."))

        doc_manager.notify(title=doc_manager.tr("Client Créé"),
                           message=doc_manager.tr("Le client '{0}' (ID: {1}) a été créé avec succès.").format(created_client_info.get('client_name', client_name_val), actual_new_client_id),
                           type='SUCCESS')
        doc_manager.open_client_tab_by_id(actual_new_client_id)
        doc_manager.stats_widget.update_stats()

    except sqlite3.IntegrityError as e_sqlite_integrity: # This might be caught by controller now
        logging.error(f"Database integrity error: {client_name_val}", exc_info=True)
        error_msg_detail = str(e_sqlite_integrity).lower()
        user_message = doc_manager.tr("Erreur de base de données.")
        if "unique constraint failed: clients.project_identifier" in error_msg_detail: # Should be caught by controller
            user_message = doc_manager.tr("L'ID de Projet '{0}' existe déjà.").format(project_identifier_val)
        elif "unique constraint failed: clients.default_base_folder_path" in error_msg_detail: # Path created from user input
             user_message = doc_manager.tr("Un client avec un nom ou un chemin de dossier résultant similaire existe déjà.")
        QMessageBox.critical(doc_manager, doc_manager.tr("Erreur de Données"), user_message)
        doc_manager.notify(title=doc_manager.tr("Erreur Données Client"), message=user_message, type='ERROR')
        # If client was created by controller but project/task fails here, client still exists.
        # Consider if rollback is needed for controller-created client if subsequent steps fail.
        # For now, if controller created client, it remains.
    except Exception as e_general:
        QMessageBox.critical(doc_manager, doc_manager.tr("Erreur Inattendue"), doc_manager.tr("Une erreur s'est produite:\n{0}").format(str(e_general)))
        doc_manager.notify(title=doc_manager.tr("Erreur Inattendue Création"), message=doc_manager.tr("Erreur inattendue."), type='ERROR')
        # Rollback for project/tasks if created
        if new_project_id_central_db and get_project_by_id(new_project_id_central_db):
            delete_project(new_project_id_central_db)
        # Client created by controller remains unless explicitly rolled back.
        # This part needs careful consideration of transactional behavior.
        # If client was created (actual_new_client_id is not None), but this later part fails,
        # the client exists in DB, but project/tasks might not.
        # The original code had some rollback logic for client if os.makedirs failed after client creation.
        # That specific OSError is handled above with rollback. This is for other exceptions.


def load_and_display_clients(doc_manager, filters: dict = None, limit: int = None, offset: int = 0, include_deleted: bool = False):
    """
    Loads client data from the database and displays it in the UI.
    Now accepts filters, pagination, and include_deleted parameters.
    """
    doc_manager.clients_data_map.clear()
    doc_manager.client_list_widget.clear()
    try:
        # Use get_all_clients_with_details for richer data for UI map
        # The 'filters' dict here is for the CRUD method, not the UI search term yet.
        # UI search term will be applied on top of this loaded data or by refining the filters dict.
        all_clients_dicts = clients_crud_instance.get_all_clients_with_details(
            filters=filters,
            limit=limit,
            offset=offset,
            include_deleted=include_deleted
        )
        # get_all_clients_with_details already sorts by client_name
        # if all_clients_dicts is None: all_clients_dicts = [] # Already returns list
        # all_clients_dicts.sort(key=lambda c: c.get('client_name', '')) # Sorting done by CRUD

        for client_data in all_clients_dicts:
            country_name = "N/A"
            if client_data.get('country_id'):
                country_obj = get_country_by_id(client_data['country_id'])
                if country_obj: country_name = country_obj['country_name']
            city_name = "N/A"
            if client_data.get('city_id'):
                city_obj = get_city_by_id(client_data['city_id'])
                if city_obj: city_name = city_obj['city_name']
            status_name = "N/A"
            status_id_val = client_data.get('status_id')
            if status_id_val:
                status_obj = get_status_setting_by_id(status_id_val)
                if status_obj: status_name = status_obj['status_name']

            adapted_client_dict = {
                "client_id": client_data.get('client_id'), "client_name": client_data.get('client_name'),
                "company_name": client_data.get('company_name'), "need": client_data.get('primary_need_description'),
                "country": country_name, "country_id": client_data.get('country_id'),
                "city": city_name, "city_id": client_data.get('city_id'),
                "project_identifier": client_data.get('project_identifier'), "base_folder_path": client_data.get('default_base_folder_path'),
                "selected_languages": client_data.get('selected_languages', '').split(',') if client_data.get('selected_languages') else ['fr'],
                "price": client_data.get('price', 0), "notes": client_data.get('notes'),
                "status": status_name, "status_id": status_id_val,
                "creation_date": client_data.get('created_at', '').split('T')[0] if client_data.get('created_at') else "N/A",
                "category": client_data.get('category', 'Standard')
            }
            doc_manager.clients_data_map[adapted_client_dict["client_id"]] = adapted_client_dict
            doc_manager.add_client_to_list_widget(adapted_client_dict) # add_client_to_list_widget is a method of DocumentManager
    except Exception as e:
        QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"), doc_manager.tr("Erreur de chargement des clients:\n{0}").format(str(e)))

def filter_and_display_clients(doc_manager):
    search_term = doc_manager.search_input_field.text().lower()
    selected_status_id = doc_manager.status_filter_combo.currentData()

    doc_manager.client_list_widget.clear()
    for client_id_key, client_data_val in doc_manager.clients_data_map.items():
        if selected_status_id is not None:
            if client_data_val.get("status_id") != selected_status_id:
                continue
        if search_term and not (search_term in client_data_val.get("client_name","").lower() or \
                               search_term in client_data_val.get("project_identifier","").lower() or \
                               search_term in client_data_val.get("company_name","").lower()):
            continue
        doc_manager.add_client_to_list_widget(client_data_val) # add_client_to_list_widget is a method of DocumentManager

def perform_old_clients_check(doc_manager):
    try:
        reminder_days_val = doc_manager.config.get("default_reminder_days", 30)
        s_archived_obj = get_status_setting_by_name('Archivé', 'Client')
        s_archived_id = s_archived_obj['status_id'] if s_archived_obj else -1
        s_complete_obj = get_status_setting_by_name('Complété', 'Client')
        s_complete_id = s_complete_obj['status_id'] if s_complete_obj else -2

        # Get all non-deleted clients for this check by default
        all_clients = clients_crud_instance.get_all_clients(include_deleted=False)
        # if all_clients is None: all_clients = [] # get_all_clients returns list
        old_clients_to_notify = []
        cutoff_date = datetime.now() - timedelta(days=reminder_days_val)

        for client in all_clients:
            if client.get('status_id') not in [s_archived_id, s_complete_id]:
                creation_date_str = client.get('created_at')
                if creation_date_str:
                    try:
                        if 'T' in creation_date_str and '.' in creation_date_str:
                            client_creation_date = datetime.fromisoformat(creation_date_str.split('.')[0])
                        elif 'T' in creation_date_str:
                             client_creation_date = datetime.fromisoformat(creation_date_str.replace('Z', ''))
                        else:
                            client_creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d")
                        if client_creation_date <= cutoff_date:
                            old_clients_to_notify.append({
                                'client_id': client.get('client_id'),
                                'client_name': client.get('client_name'),
                                'creation_date_str': client_creation_date.strftime("%Y-%m-%d")
                            })
                    except ValueError as ve:
                        logging.warning(f"Could not parse creation_date '{creation_date_str}' for client {client.get('client_id')}: {ve}")
                        continue
        if old_clients_to_notify:
            client_names_str = "\n".join([f"- {c['client_name']} (créé le {c['creation_date_str']})" for c in old_clients_to_notify])
            reply = QMessageBox.question(
                doc_manager, doc_manager.tr("Clients Anciens Actifs"),
                doc_manager.tr("Les clients suivants sont actifs depuis plus de {0} jours:\n{1}\n\nVoulez-vous les archiver?").format(reminder_days_val, client_names_str),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                for c_info in old_clients_to_notify:
                    archive_client_status(doc_manager, c_info['client_id']) # Call the refactored function
    except Exception as e:
        logging.error(f"Erreur vérification clients anciens: {str(e)}")

def handle_open_edit_client_dialog(doc_manager, client_id):
    current_client_data = doc_manager.clients_data_map.get(client_id)
    if not current_client_data:
        QMessageBox.warning(doc_manager, doc_manager.tr("Erreur"), doc_manager.tr("Client non trouvé."))
        doc_manager.notify(title=doc_manager.tr("Client Introuvable"),
                           message=doc_manager.tr("Les données du client (ID: {0}) n'ont pas pu être chargées pour modification.").format(client_id),
                           type='ERROR')
        return

    dialog = EditClientDialog(current_client_data, doc_manager.config, doc_manager) # Pass doc_manager as parent
    if dialog.exec_() == QDialog.Accepted:
        updated_form_data = dialog.get_data()
        data_for_db_update = {
            'client_name': updated_form_data.get('client_name'), 'company_name': updated_form_data.get('company_name'),
            'primary_need_description': updated_form_data.get('primary_need_description'), 'project_identifier': updated_form_data.get('project_identifier'),
            'country_id': updated_form_data.get('country_id'), 'city_id': updated_form_data.get('city_id'),
            'selected_languages': updated_form_data.get('selected_languages'), 'status_id': updated_form_data.get('status_id'),
            'notes': updated_form_data.get('notes'), 'category': updated_form_data.get('category')
        }
        # Use clients_crud_instance.update_client
        update_result = clients_crud_instance.update_client(client_id, data_for_db_update)
        if update_result['success']:
            # load_and_display_clients needs to be called with current filters/pagination
            # This might require main_window to handle the refresh.
            # For now, assume a simple refresh.
            doc_manager.load_clients_from_db_slot() # Call the slot in main_window for full refresh logic
            # The following lines might be redundant if load_clients_from_db_slot updates clients_data_map
            # and refreshes tabs correctly.
            # load_and_display_clients(doc_manager) # Refresh map and list widget
            updated_client_data_for_tab = doc_manager.clients_data_map.get(client_id) # Get fresh data after load_and_display_clients
            client_name_for_notify = updated_client_data_for_tab.get('client_name', str(client_id)) if updated_client_data_for_tab else str(client_id)
            doc_manager.notify(title=doc_manager.tr("Client Mis à Jour"),
                               message=doc_manager.tr("Les informations du client '{0}' ont été mises à jour.").format(client_name_for_notify),
                               type='SUCCESS')
            tab_refreshed = False
            for i in range(doc_manager.client_tabs_widget.count()):
                tab_widget = doc_manager.client_tabs_widget.widget(i)
                if hasattr(tab_widget, 'client_info') and tab_widget.client_info.get("client_id") == client_id:
                    if hasattr(tab_widget, 'refresh_display'):
                        if updated_client_data_for_tab: # Ensure it's not None
                            tab_widget.refresh_display(updated_client_data_for_tab)
                            doc_manager.client_tabs_widget.setTabText(i, updated_client_data_for_tab.get('client_name', 'Client'))
                            tab_refreshed = True
                    break
            doc_manager.stats_widget.update_stats()
        else:
            QMessageBox.warning(doc_manager, doc_manager.tr("Erreur"), doc_manager.tr("Échec de la mise à jour du client."))
            doc_manager.notify(title=doc_manager.tr("Erreur Mise à Jour Client"),
                               message=doc_manager.tr("Impossible de mettre à jour les informations du client ID: {0}.").format(client_id),
                               type='ERROR')

def archive_client_status(doc_manager, client_id):
    if client_id not in doc_manager.clients_data_map: return
    try:
        status_archived_obj = get_status_setting_by_name('Archivé', 'Client')
        if not status_archived_obj:
            QMessageBox.critical(doc_manager, doc_manager.tr("Erreur Configuration"),
                                 doc_manager.tr("Statut 'Archivé' non trouvé. Veuillez configurer les statuts."))
            doc_manager.notify(title=doc_manager.tr("Erreur Configuration Statut"),
                               message=doc_manager.tr("Statut 'Archivé' non trouvé. Impossible d'archiver."),
                               type='ERROR')
            return
        archived_status_id = status_archived_obj['status_id']
        client_name_for_notify = doc_manager.clients_data_map[client_id].get('client_name', str(client_id))

        # Update client to archived status and also set soft delete flags
        update_data = {
            'status_id': archived_status_id,
            'is_deleted': True, # Explicitly mark as soft-deleted
            'deleted_at': datetime.utcnow().isoformat() + "Z"
        }
        update_result = clients_crud_instance.update_client(client_id, update_data)

        if update_result['success'] and update_result.get('updated_count', 0) > 0:
            # Update local map, though a full refresh might be better
            if client_id in doc_manager.clients_data_map:
                doc_manager.clients_data_map[client_id]["status"] = status_archived_obj['status_name'] # "Archivé"
                doc_manager.clients_data_map[client_id]["status_id"] = archived_status_id
                doc_manager.clients_data_map[client_id]["is_deleted"] = True # Reflect soft delete in map

            # Refresh display considering current filters (especially include_deleted)
            doc_manager.filter_client_list_display_slot() # Use the main_window slot
            # load_and_display_clients(doc_manager) # Or call with current filters
            filter_and_display_clients(doc_manager) # Refresh list display
            for i in range(doc_manager.client_tabs_widget.count()):
                tab_w = doc_manager.client_tabs_widget.widget(i)
                if hasattr(tab_w, 'client_info') and tab_w.client_info["client_id"] == client_id:
                    if hasattr(tab_w, 'status_combo'): # Check if ClientWidget has status_combo
                        tab_w.status_combo.setCurrentText("Archivé") # Update status combo in open tab
                    break
            doc_manager.stats_widget.update_stats()
            # QMessageBox.information(doc_manager, doc_manager.tr("Client Archivé"),
            #                         doc_manager.tr("Le client '{0}' a été archivé.").format(client_name_for_notify))
            doc_manager.notify(title=doc_manager.tr("Client Archivé"),
                               message=doc_manager.tr("Le client '{0}' a été archivé.").format(client_name_for_notify),
                               type='INFO')
        else:
            QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"),
                                 doc_manager.tr("Erreur d'archivage du client. Vérifiez les logs."))
            doc_manager.notify(title=doc_manager.tr("Erreur Archivage"),
                               message=doc_manager.tr("Erreur d'archivage du client '{0}'.").format(client_name_for_notify),
                               type='ERROR')
    except Exception as e:
        QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"), doc_manager.tr("Erreur d'archivage du client:\n{0}").format(str(e)))
        doc_manager.notify(title=doc_manager.tr("Erreur Archivage Inattendue"),
                           message=doc_manager.tr("Erreur inattendue lors de l'archivage du client '{0}'.").format(client_name_for_notify),
                           type='ERROR')

def permanently_delete_client(doc_manager, client_id):
    if client_id not in doc_manager.clients_data_map: return
    client_name_val = doc_manager.clients_data_map[client_id]['client_name']
    client_folder_path = doc_manager.clients_data_map[client_id]["base_folder_path"]

    reply = QMessageBox.question(
        doc_manager, doc_manager.tr("Confirmer Suppression"),
        doc_manager.tr("Supprimer '{0}'?\nCeci supprimera le client de la base de données et son dossier de fichiers (si possible).\nCette action est irréversible.").format(client_name_val),
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if reply == QMessageBox.Yes:
        try:
            # Use clients_crud_instance.delete_client for soft delete
            logging.info("INFO: permanently_delete_client now performs a SOFT delete due to CRUD changes. For hard delete, a new CRUD method is needed.")
            delete_result = clients_crud_instance.delete_client(client_id)

            if delete_result['success']:
                # Folder removal logic might be re-evaluated.
                # For soft delete, typically data isn't removed from filesystem immediately.
                # For now, keeping the rmtree logic but it's less common with soft delete.
                # Consider making folder archival a separate process or based on a longer-term policy.
                if os.path.exists(client_folder_path):
                    # shutil.rmtree(client_folder_path, ignore_errors=True) # Reconsider this line for soft delete
                    logging.warning(f"Client {client_id} soft-deleted. Folder {client_folder_path} was NOT removed as part of soft delete.")

                # Update UI: remove from active list (if not showing deleted), update map
                if client_id in doc_manager.clients_data_map:
                    # If not showing deleted items, remove from map. Otherwise, update its state.
                    # A full refresh via load_and_display_clients with current filters is better.
                    del doc_manager.clients_data_map[client_id] # Or mark as deleted if map handles it

                # Refresh display considering current filters (especially include_deleted)
                doc_manager.filter_client_list_display_slot() # Use the main_window slot
                # load_and_display_clients(doc_manager)
                for i in range(doc_manager.client_tabs_widget.count()):
                    if hasattr(doc_manager.client_tabs_widget.widget(i), 'client_info') and \
                       doc_manager.client_tabs_widget.widget(i).client_info["client_id"] == client_id:
                        doc_manager.close_client_tab(i); break # close_client_tab is a method of DocumentManager
                doc_manager.stats_widget.update_stats()
                # QMessageBox.information(doc_manager, doc_manager.tr("Client Supprimé"),
                #                         doc_manager.tr("Client '{0}' supprimé avec succès.").format(client_name_val))
                doc_manager.notify(title=doc_manager.tr("Client Supprimé"),
                                   message=doc_manager.tr("Client '{0}' supprimé avec succès.").format(client_name_val),
                                   type='SUCCESS')
            else:
                error_message = delete_result.get('error', doc_manager.tr("Erreur inconnue."))
                QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"),
                                     doc_manager.tr("Erreur lors de la suppression (soft) du client: {0}").format(error_message))
                doc_manager.notify(title=doc_manager.tr("Erreur Suppression (Soft)"),
                                   message=doc_manager.tr("Erreur de suppression (soft) du client '{0}': {1}").format(client_name_val, error_message),
                                   type='ERROR')
        except OSError as e_os: # This error is now less likely if rmtree is removed for soft delete
            QMessageBox.critical(doc_manager, doc_manager.tr("Erreur Dossier"),
                                 doc_manager.tr("Le client a été marqué comme supprimé, mais une erreur est survenue lors d'une opération sur son dossier:\n{0}").format(str(e_os)))
            doc_manager.notify(title=doc_manager.tr("Erreur Opération Dossier"),
                               message=doc_manager.tr("Client '{0}' marqué supprimé, mais erreur d'opération sur dossier.").format(client_name_val),
                               type='WARNING')
            # Refresh client list even if folder operation had issues
            if client_id in doc_manager.clients_data_map:
                 del doc_manager.clients_data_map[client_id] # Or mark deleted
            doc_manager.filter_client_list_display_slot()
            # load_and_display_clients(doc_manager)
            for i in range(doc_manager.client_tabs_widget.count()):
                if hasattr(doc_manager.client_tabs_widget.widget(i), 'client_info') and \
                   doc_manager.client_tabs_widget.widget(i).client_info["client_id"] == client_id:
                    doc_manager.close_client_tab(i); break
            doc_manager.stats_widget.update_stats()
        except Exception as e_db:
             QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"),
                                  doc_manager.tr("Erreur lors de la suppression du client:\n{0}").format(str(e_db)))
             doc_manager.notify(title=doc_manager.tr("Erreur Suppression Inattendue"),
                                message=doc_manager.tr("Erreur inattendue lors de la suppression du client '{0}'.").format(client_name_val),
                                type='ERROR')

# --- Invoice Generation and DB Update Logic ---
# Assuming invoice_generation_logic.py is at the same level or in PYTHONPATH
from invoice_generation_logic import generate_final_invoice_pdf
from db.cruds import client_documents_crud, invoices_crud # clients_crud is already imported
import uuid # For ClientDocument ID if not generated by CRUD

def create_final_invoice_and_update_db(
    client_id: str,
    company_id: str,
    target_language_code: str,
    line_items: list,
    project_id: str = None,
    additional_context_overrides: dict = None,
    created_by_user_id: str = None
) -> tuple[bool, str | None, str | None]:
    """
    Generates a final invoice PDF, saves it, and creates corresponding entries
    in ClientDocuments and Invoices tables.

    Args:
        client_id: ID of the client.
        company_id: ID of the seller company.
        target_language_code: Language for the invoice.
        line_items: List of product/service line items.
        project_id: Optional project ID.
        additional_context_overrides: Optional dict to override context values.
        created_by_user_id: Optional ID of the user creating the document.

    Returns:
        Tuple: (success_status, new_invoice_table_id, new_client_document_id)
    """
    logging.info(f"Attempting to create final invoice for client {client_id}, project {project_id}")

    pdf_bytes, suggested_filename, full_context = generate_final_invoice_pdf(
        client_id=client_id,
        company_id=company_id,
        target_language_code=target_language_code,
        line_items=line_items,
        project_id=project_id,
        additional_context_overrides=additional_context_overrides
    )

    if pdf_bytes is None or full_context is None:
        logging.error(f"Failed to generate PDF bytes or context for client {client_id}.")
        return False, None, None

    # Determine Save Path & Save PDF
    try:
        client_data = clients_crud.get_client_by_id(client_id) # Assumes this returns a dict-like object
        if not client_data or not client_data.get('default_base_folder_path'):
            logging.error(f"Client data or base folder path not found for client_id: {client_id}")
            return False, None, None

        # Construct save directory: <client_base_folder>/<lang>/Invoices/
        # Ensure lang code is filesystem-friendly; it usually is (e.g., "en", "fr")
        save_directory = os.path.join(client_data['default_base_folder_path'], target_language_code, "Invoices")
        os.makedirs(save_directory, exist_ok=True)

        final_pdf_path = os.path.join(save_directory, suggested_filename)

        with open(final_pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        logging.info(f"Successfully saved final invoice PDF to: {final_pdf_path}")

    except IOError as e:
        logging.error(f"IOError saving PDF for client {client_id}: {e}", exc_info=True)
        return False, None, None
    except Exception as e: # Catch other potential errors from client_data fetching or os ops
        logging.error(f"Error during PDF saving prep for client {client_id}: {e}", exc_info=True)
        return False, None, None

    # Create ClientDocuments Entry
    new_client_doc_id = None
    try:
        # Ensure default_base_folder_path ends with a separator for clean relpath, or handle robustly
        base_path_for_rel = client_data['default_base_folder_path']
        if not base_path_for_rel.endswith(os.path.sep):
            base_path_for_rel += os.path.sep

        # Check if final_pdf_path is indeed under base_path_for_rel before making relpath
        # This is a basic check. os.path.commonpath can be more robust if paths are complex.
        if not final_pdf_path.startswith(base_path_for_rel):
            logging.error(f"Generated PDF path '{final_pdf_path}' is not under client base folder '{base_path_for_rel}'. Cannot determine relative path.")
            # Consider cleanup: os.remove(final_pdf_path)
            return False, None, None

        relative_pdf_path = os.path.relpath(final_pdf_path, base_path_for_rel)


        client_doc_data = {
            'document_id': str(uuid.uuid4()), # Generate a new UUID for the document
            'client_id': client_id,
            'project_id': project_id,
            'order_identifier': full_context.get("doc", {}).get("invoice_number"), # Use invoice number as order_identifier
            'document_name': suggested_filename,
            'file_name_on_disk': suggested_filename,
            'file_path_relative': relative_pdf_path,
            'document_type_generated': "FINAL_INVOICE", # Specific type for final invoices
            'source_template_id': None, # Not directly from a template record in DB in this flow
            'version_tag': "1.0",
            'notes': f"Final Invoice generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'created_by_user_id': created_by_user_id
        }
        new_client_doc_id_from_crud = client_documents_crud.add_client_document(client_doc_data)

        if not new_client_doc_id_from_crud: # add_client_document should return the ID string
            logging.error(f"Failed to create ClientDocuments entry for invoice {suggested_filename}, client {client_id}.")
            # Consider cleanup: os.remove(final_pdf_path)
            return False, None, None
        new_client_doc_id = client_doc_data['document_id'] # Use the UUID we generated
        logging.info(f"ClientDocuments entry created with ID: {new_client_doc_id} (CRUD returned: {new_client_doc_id_from_crud})")

    except Exception as e:
        logging.error(f"Error creating ClientDocuments entry for client {client_id}: {e}", exc_info=True)
        # Consider cleanup: os.remove(final_pdf_path) if it was saved
        return False, None, None

    # Create Invoices Table Entry
    new_invoice_table_id = None
    try:
        doc_ctx = full_context.get("doc", {})
        invoice_table_data = {
            'invoice_id': str(uuid.uuid4()), # Generate a new UUID for the invoice table primary key
            'client_id': client_id,
            'project_id': project_id,
            'document_id': new_client_doc_id, # Link to the ClientDocuments entry
            'invoice_number': doc_ctx.get("invoice_number"),
            'issue_date': doc_ctx.get("issue_date"),
            'due_date': doc_ctx.get("due_date"),
            'total_amount': doc_ctx.get("grand_total_amount_raw"), # Use raw numeric value
            'currency': doc_ctx.get("currency_symbol"), # Ensure this is just symbol or code as per DB
            'payment_status': 'unpaid', # Default for new final invoices
            'payment_date': None,
            'payment_method': None,
            'transaction_id': None,
            'notes': doc_ctx.get("notes", ""),
            # created_at, updated_at are usually handled by DB defaults in Invoices table
        }

        # Ensure currency is just the code/symbol, not amount + symbol
        if invoice_table_data['currency'] and ' ' in invoice_table_data['currency']: # e.g. "1,234.00 EUR"
             invoice_table_data['currency'] = invoice_table_data['currency'].split(' ')[-1]
        elif len(invoice_table_data.get('currency', '')) > 3 : # e.g. "EUR" is fine, but "Euro" might be too long if schema expects code
             # This logic depends on how currency_symbol is formatted by format_currency and what DB expects
             # For now, assume currency_symbol from context is just the code like "USD", "EUR"
             pass


        new_invoice_table_id_from_crud = invoices_crud.add_invoice(invoice_table_data)
        if not new_invoice_table_id_from_crud:
            logging.error(f"Failed to create Invoices table entry for invoice number {doc_ctx.get('invoice_number')}.")
            # Consider cleanup: os.remove(final_pdf_path) and client_documents_crud.delete_client_document(new_client_doc_id)
            return False, None, new_client_doc_id
        new_invoice_table_id = invoice_table_data['invoice_id'] # Use the UUID we generated
        logging.info(f"Invoices table entry created with ID: {new_invoice_table_id} (CRUD returned: {new_invoice_table_id_from_crud})")

    except Exception as e:
        logging.error(f"Error creating Invoices table entry for client {client_id}: {e}", exc_info=True)
        # Consider cleanup: os.remove(final_pdf_path) and client_documents_crud.delete_client_document(new_client_doc_id) if new_client_doc_id exists
        return False, None, new_client_doc_id

    logging.info(f"Successfully created final invoice, ClientDocument, and Invoice DB entry for client {client_id}. Invoice ID: {new_invoice_table_id}, Document ID: {new_client_doc_id}")
    return True, new_invoice_table_id, new_client_doc_id
