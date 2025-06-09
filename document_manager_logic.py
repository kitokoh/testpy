# -*- coding: utf-8 -*-
import os
import shutil
import sqlite3 # Should be checked if still needed directly, db_manager should handle most
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QMessageBox, QDialog, QInputDialog # QInputDialog was used in add_new_country/city, not directly in moved methods but good to keep context
# from PyQt5.QtCore import QStandardPaths # Removed as not used by these functions
import db as db_manager

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

def handle_create_client_execution(doc_manager):
    client_name_val = doc_manager.client_name_input.text().strip()
    company_name_val = doc_manager.company_name_input.text().strip()
    need_val = doc_manager.client_need_input.text().strip()

    country_id_val = doc_manager.country_select_combo.currentData()
    country_name_for_folder = doc_manager.country_select_combo.currentText().strip()
    city_id_val = doc_manager.city_select_combo.currentData()

    project_identifier_val = doc_manager.project_id_input_field.text().strip()
    price_val = doc_manager.final_price_input.value()
    lang_option_text = doc_manager.language_select_combo.currentText()

    if not client_name_val or not country_id_val or not project_identifier_val:
        QMessageBox.warning(doc_manager, doc_manager.tr("Champs Requis"), doc_manager.tr("Nom client, Pays et ID Projet sont obligatoires."))
        return

    lang_map_from_display = {
        doc_manager.tr("English only (en)"): ["en"],
        doc_manager.tr("French only (fr)"): ["fr"],
        doc_manager.tr("Arabic only (ar)"): ["ar"],
        doc_manager.tr("Turkish only (tr)"): ["tr"],
        doc_manager.tr("Portuguese only (pt)"): ["pt"],
        doc_manager.tr("All supported languages (en, fr, ar, tr, pt)"): ["en", "fr", "ar", "tr", "pt"]
    }
    selected_langs_list = lang_map_from_display.get(lang_option_text, ["en"])

    folder_name_str = f"{client_name_val}_{country_name_for_folder}_{project_identifier_val}".replace(" ", "_").replace("/", "-")
    base_folder_full_path = os.path.join(doc_manager.config["clients_dir"], folder_name_str)

    if os.path.exists(base_folder_full_path):
        QMessageBox.warning(doc_manager, doc_manager.tr("Dossier Existant"),
                            doc_manager.tr("Un dossier client avec un chemin similaire existe déjà. Veuillez vérifier les détails ou choisir un ID Projet différent."))
        return

    default_status_name = "En cours"
    status_setting_obj = db_manager.get_status_setting_by_name(default_status_name, 'Client')
    if not status_setting_obj or not status_setting_obj.get('status_id'):
        QMessageBox.critical(doc_manager, doc_manager.tr("Erreur Configuration"),
                             doc_manager.tr("Statut par défaut '{0}' non trouvé pour les clients. Veuillez configurer les statuts.").format(default_status_name))
        return
    default_status_id = status_setting_obj['status_id']

    client_data_for_db = {
        'client_name': client_name_val,
        'company_name': company_name_val if company_name_val else None,
        'primary_need_description': need_val,
        'project_identifier': project_identifier_val,
        'country_id': country_id_val,
        'city_id': city_id_val if city_id_val else None,
        'default_base_folder_path': base_folder_full_path,
        'selected_languages': ",".join(selected_langs_list),
        'price': price_val,
        'status_id': default_status_id,
        'category': 'Standard',
        'notes': '',
    }

    actual_new_client_id = None
    new_project_id_central_db = None

    try:
        actual_new_client_id = db_manager.add_client(client_data_for_db)
        if not actual_new_client_id:
            QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"),
                                 doc_manager.tr("Impossible de créer le client. L'ID de projet ou le chemin du dossier existe peut-être déjà, ou autre erreur de contrainte DB."))
            return

        os.makedirs(base_folder_full_path, exist_ok=True)
        for lang_code in selected_langs_list:
            os.makedirs(os.path.join(base_folder_full_path, lang_code), exist_ok=True)

        project_status_planning_obj = db_manager.get_status_setting_by_name("Planning", "Project")
        project_status_id_for_pm = project_status_planning_obj['status_id'] if project_status_planning_obj else None

        if not project_status_id_for_pm:
             QMessageBox.warning(doc_manager, doc_manager.tr("Erreur Configuration Projet"),
                                 doc_manager.tr("Statut de projet par défaut 'Planning' non trouvé. Le projet ne sera pas créé avec un statut initial."))

        project_data_for_db = {
            'client_id': actual_new_client_id,
            'project_name': f"Projet pour {client_name_val}",
            'description': f"Projet pour client: {client_name_val}. Besoin initial: {need_val}",
            'start_date': datetime.now().strftime("%Y-%m-%d"),
            'deadline_date': (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
            'budget': 0.0,
            'status_id': project_status_id_for_pm,
            'priority': 1
        }
        new_project_id_central_db = db_manager.add_project(project_data_for_db)

        if new_project_id_central_db:
            QMessageBox.information(doc_manager, doc_manager.tr("Projet Créé (Central DB)"),
                                    doc_manager.tr("Un projet associé a été créé dans la base de données centrale pour {0}.").format(client_name_val))

            task_status_todo_obj = db_manager.get_status_setting_by_name("To Do", "Task")
            task_status_id_for_todo = task_status_todo_obj['status_id'] if task_status_todo_obj else None

            if not task_status_id_for_todo:
                QMessageBox.warning(doc_manager, doc_manager.tr("Erreur Configuration Tâche"),
                                    doc_manager.tr("Statut de tâche par défaut 'To Do' non trouvé. Les tâches standard ne seront pas créées avec un statut initial."))

            standard_tasks = [
                {"name": "Initial Client Consultation & Needs Assessment", "description": "Understand client requirements, objectives, target markets, and budget.", "priority_val": 2, "deadline_days": 3},
                {"name": "Market Research & Analysis", "description": "Research target international markets, including competition, regulations, and cultural nuances.", "priority_val": 1, "deadline_days": 7},
                {"name": "Post-Sales Follow-up & Support", "description": "Follow up with the client after delivery.", "priority_val": 1, "deadline_days": 60}
            ]

            for task_item in standard_tasks:
                task_deadline = (datetime.now() + timedelta(days=task_item["deadline_days"])).strftime("%Y-%m-%d")
                db_manager.add_task({
                    'project_id': new_project_id_central_db,
                    'task_name': task_item["name"],
                    'description': task_item["description"],
                    'status_id': task_status_id_for_todo,
                    'priority': task_item["priority_val"],
                    'due_date': task_deadline
                })
            QMessageBox.information(doc_manager, doc_manager.tr("Tâches Créées (Central DB)"),
                                    doc_manager.tr("Des tâches standard ont été ajoutées au projet pour {0}.").format(client_name_val))
        else:
            QMessageBox.warning(doc_manager, doc_manager.tr("Erreur DB Projet"),
                                doc_manager.tr("Le client a été créé, mais la création du projet associé dans la base de données centrale a échoué."))

        client_dict_from_db = db_manager.get_client_by_id(actual_new_client_id)
        ui_map_data = None
        if client_dict_from_db:
            country_obj = db_manager.get_country_by_id(client_dict_from_db.get('country_id')) if client_dict_from_db.get('country_id') else None
            city_obj = db_manager.get_city_by_id(client_dict_from_db.get('city_id')) if client_dict_from_db.get('city_id') else None
            status_obj = db_manager.get_status_setting_by_id(client_dict_from_db.get('status_id')) if client_dict_from_db.get('status_id') else None
            ui_map_data = {
                "client_id": client_dict_from_db.get('client_id'), "client_name": client_dict_from_db.get('client_name'),
                "company_name": client_dict_from_db.get('company_name'), "need": client_dict_from_db.get('primary_need_description'),
                "country": country_obj['country_name'] if country_obj else "N/A", "country_id": client_dict_from_db.get('country_id'),
                "city": city_obj['city_name'] if city_obj else "N/A", "city_id": client_dict_from_db.get('city_id'),
                "project_identifier": client_dict_from_db.get('project_identifier'), "base_folder_path": client_dict_from_db.get('default_base_folder_path'),
                "selected_languages": client_dict_from_db.get('selected_languages','').split(',') if client_dict_from_db.get('selected_languages') else [],
                "price": client_dict_from_db.get('price'), "notes": client_dict_from_db.get('notes'),
                "status": status_obj['status_name'] if status_obj else "N/A", "status_id": client_dict_from_db.get('status_id'),
                "creation_date": client_dict_from_db.get('created_at','').split("T")[0] if client_dict_from_db.get('created_at') else "N/A",
                "category": client_dict_from_db.get('category')
            }
            doc_manager.clients_data_map[actual_new_client_id] = ui_map_data
            doc_manager.add_client_to_list_widget(ui_map_data)

        doc_manager.client_name_input.clear(); doc_manager.company_name_input.clear(); doc_manager.client_need_input.clear()
        doc_manager.project_id_input_field.clear(); doc_manager.final_price_input.setValue(0)

        if ui_map_data: # Ensure ui_map_data is populated
            contact_dialog = ContactDialog(client_id=actual_new_client_id, parent=doc_manager)
            if contact_dialog.exec_() == QDialog.Accepted:
                contact_form_data = contact_dialog.get_data()
                try:
                    existing_contact = db_manager.get_contact_by_email(contact_form_data['email'])
                    contact_id_to_link = None
                    if existing_contact:
                        contact_id_to_link = existing_contact['contact_id']
                        update_data = {k: v for k, v in contact_form_data.items() if k in ['name', 'phone', 'position'] and v != existing_contact.get(k)}
                        if update_data: db_manager.update_contact(contact_id_to_link, update_data)
                    else:
                        new_contact_id = db_manager.add_contact({
                            'name': contact_form_data['name'], 'email': contact_form_data['email'],
                            'phone': contact_form_data['phone'], 'position': contact_form_data['position']
                        })
                        if new_contact_id: contact_id_to_link = new_contact_id
                        else: QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"), doc_manager.tr("Impossible de créer le nouveau contact global."))

                    if contact_id_to_link:
                        if contact_form_data['is_primary']:
                            client_contacts = db_manager.get_contacts_for_client(actual_new_client_id)
                            if client_contacts:
                                for cc in client_contacts:
                                    if cc['is_primary_for_client'] and cc.get('client_contact_id'):
                                        db_manager.update_client_contact_link(cc['client_contact_id'], {'is_primary_for_client': False})
                        link_id = db_manager.link_contact_to_client(actual_new_client_id, contact_id_to_link, is_primary=contact_form_data['is_primary'])
                        if not link_id: QMessageBox.warning(doc_manager, doc_manager.tr("Erreur DB"), doc_manager.tr("Impossible de lier le contact au client (le lien existe peut-être déjà)."))
                except Exception as e_contact_save:
                    QMessageBox.critical(doc_manager, doc_manager.tr("Erreur Sauvegarde Contact"), doc_manager.tr("Une erreur est survenue lors de la sauvegarde du contact : {0}").format(str(e_contact_save)))

                product_dialog = ProductDialog(client_id=actual_new_client_id, parent=doc_manager)
                if product_dialog.exec_() == QDialog.Accepted:
                    products_list_data = product_dialog.get_data()
                    for product_item_data in products_list_data:
                        try:
                            global_product = db_manager.get_product_by_name(product_item_data['name'])
                            global_product_id = None; current_base_unit_price = None
                            if global_product:
                                global_product_id = global_product['product_id']; current_base_unit_price = global_product.get('base_unit_price')
                            else:
                                new_global_product_id = db_manager.add_product({
                                    'product_name': product_item_data['name'], 'description': product_item_data['description'],
                                    'base_unit_price': product_item_data['unit_price'], 'language_code': product_item_data.get('language_code', 'fr')
                                })
                                if new_global_product_id: global_product_id = new_global_product_id; current_base_unit_price = product_item_data['unit_price']
                                else: QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"), doc_manager.tr("Impossible de créer le produit global '{0}' (lang: {1}).").format(product_item_data['name'], product_item_data.get('language_code', 'fr'))); continue

                            if global_product_id:
                                unit_price_override_val = product_item_data['unit_price'] if current_base_unit_price is None or product_item_data['unit_price'] != current_base_unit_price else None
                                link_data = {'client_id': actual_new_client_id, 'project_id': None, 'product_id': global_product_id, 'quantity': product_item_data['quantity'], 'unit_price_override': unit_price_override_val}
                                cpp_id = db_manager.add_product_to_client_or_project(link_data)
                                if not cpp_id: QMessageBox.warning(doc_manager, doc_manager.tr("Erreur DB"), doc_manager.tr("Impossible de lier le produit '{0}' au client.").format(product_item_data['name']))
                        except Exception as e_product_save:
                            QMessageBox.critical(doc_manager, doc_manager.tr("Erreur Sauvegarde Produit"), doc_manager.tr("Une erreur est survenue lors de la sauvegarde du produit '{0}': {1}").format(product_item_data.get('name', 'Inconnu'), str(e_product_save)))

                    linked_products = db_manager.get_products_for_client_or_project(client_id=actual_new_client_id, project_id=None)
                    if linked_products is None: linked_products = []
                    calculated_total_sum = sum(p.get('total_price_calculated', 0.0) for p in linked_products if p.get('total_price_calculated') is not None)
                    db_manager.update_client(actual_new_client_id, {'price': calculated_total_sum})
                    ui_map_data['price'] = calculated_total_sum # Update the map for CreateDocumentDialog
                    if actual_new_client_id in doc_manager.clients_data_map: doc_manager.clients_data_map[actual_new_client_id]['price'] = calculated_total_sum

                    create_document_dialog = CreateDocumentDialog(client_info=ui_map_data, config=doc_manager.config, parent=doc_manager)
                    if create_document_dialog.exec_() == QDialog.Accepted: logging.info("CreateDocumentDialog accepted.")
                    else: logging.info("CreateDocumentDialog cancelled.")
                else: # ProductDialog cancelled
                    logging.info("ProductDialog cancelled.")
                    if actual_new_client_id and ui_map_data: # Recalculate price
                        linked_products_on_cancel = db_manager.get_products_for_client_or_project(client_id=actual_new_client_id, project_id=None)
                        if linked_products_on_cancel is None: linked_products_on_cancel = []
                        calculated_total_sum_on_cancel = sum(p.get('total_price_calculated', 0.0) for p in linked_products_on_cancel if p.get('total_price_calculated') is not None)
                        db_manager.update_client(actual_new_client_id, {'price': calculated_total_sum_on_cancel})
                        ui_map_data['price'] = calculated_total_sum_on_cancel
                        if actual_new_client_id in doc_manager.clients_data_map: doc_manager.clients_data_map[actual_new_client_id]['price'] = calculated_total_sum_on_cancel
            else: # ContactDialog cancelled
                logging.info("ContactDialog cancelled.")
                if actual_new_client_id and ui_map_data: # Recalculate price
                    linked_products_on_contact_cancel = db_manager.get_products_for_client_or_project(client_id=actual_new_client_id, project_id=None)
                    if linked_products_on_contact_cancel is None: linked_products_on_contact_cancel = []
                    calculated_total_sum_on_contact_cancel = sum(p.get('total_price_calculated', 0.0) for p in linked_products_on_contact_cancel if p.get('total_price_calculated') is not None)
                    db_manager.update_client(actual_new_client_id, {'price': calculated_total_sum_on_contact_cancel})
                    ui_map_data['price'] = calculated_total_sum_on_contact_cancel
                    if actual_new_client_id in doc_manager.clients_data_map: doc_manager.clients_data_map[actual_new_client_id]['price'] = calculated_total_sum_on_contact_cancel
        else: # ui_map_data was not populated
             QMessageBox.warning(doc_manager, doc_manager.tr("Erreur Données Client"), doc_manager.tr("Les données du client (ui_map_data) ne sont pas disponibles pour la séquence de dialogue."))


        QMessageBox.information(doc_manager, doc_manager.tr("Client Créé"),
                                doc_manager.tr("Client {0} créé avec succès (ID Interne: {1}).").format(client_name_val, actual_new_client_id))
        doc_manager.open_client_tab_by_id(actual_new_client_id)
        doc_manager.stats_widget.update_stats()

    except sqlite3.IntegrityError as e_sqlite_integrity:
        logging.error(f"Database integrity error during client creation: {client_name_val}", exc_info=True)
        error_msg = str(e_sqlite_integrity).lower()
        user_message = doc_manager.tr("Erreur de base de données lors de la création du client.")
        if "unique constraint failed: clients.project_identifier" in error_msg:
            user_message = doc_manager.tr("L'ID de Projet '{0}' existe déjà. Veuillez en choisir un autre.").format(project_identifier_val)
        elif "unique constraint failed: clients.default_base_folder_path" in error_msg:
             user_message = doc_manager.tr("Un client avec un nom ou un chemin de dossier résultant similaire existe déjà. Veuillez modifier le nom du client ou l'ID de projet.")
        QMessageBox.critical(doc_manager, doc_manager.tr("Erreur de Données"), user_message)
    except OSError as e_os:
        QMessageBox.critical(doc_manager, doc_manager.tr("Erreur Dossier"), doc_manager.tr("Erreur de création du dossier client:\n{0}").format(str(e_os)))
        if actual_new_client_id:
             db_manager.delete_client(actual_new_client_id)
             QMessageBox.information(doc_manager, doc_manager.tr("Rollback"), doc_manager.tr("Le client a été retiré de la base de données suite à l'erreur de création de dossier."))
    except Exception as e_db:
        QMessageBox.critical(doc_manager, doc_manager.tr("Erreur Inattendue"), doc_manager.tr("Une erreur s'est produite lors de la création du client, du projet ou des tâches:\n{0}").format(str(e_db)))
        if new_project_id_central_db and db_manager.get_project_by_id(new_project_id_central_db):
            db_manager.delete_project(new_project_id_central_db)
        if actual_new_client_id and db_manager.get_client_by_id(actual_new_client_id):
             db_manager.delete_client(actual_new_client_id)
             QMessageBox.information(doc_manager, doc_manager.tr("Rollback"), doc_manager.tr("Le client et le projet associé (si créé) ont été retirés de la base de données suite à l'erreur."))

def load_and_display_clients(doc_manager):
    doc_manager.clients_data_map.clear()
    doc_manager.client_list_widget.clear()
    try:
        all_clients_dicts = db_manager.get_all_clients()
        if all_clients_dicts is None: all_clients_dicts = []
        all_clients_dicts.sort(key=lambda c: c.get('client_name', ''))

        for client_data in all_clients_dicts:
            country_name = "N/A"
            if client_data.get('country_id'):
                country_obj = db_manager.get_country_by_id(client_data['country_id'])
                if country_obj: country_name = country_obj['country_name']
            city_name = "N/A"
            if client_data.get('city_id'):
                city_obj = db_manager.get_city_by_id(client_data['city_id'])
                if city_obj: city_name = city_obj['city_name']
            status_name = "N/A"
            status_id_val = client_data.get('status_id')
            if status_id_val:
                status_obj = db_manager.get_status_setting_by_id(status_id_val)
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
        s_archived_obj = db_manager.get_status_setting_by_name('Archivé', 'Client')
        s_archived_id = s_archived_obj['status_id'] if s_archived_obj else -1
        s_complete_obj = db_manager.get_status_setting_by_name('Complété', 'Client')
        s_complete_id = s_complete_obj['status_id'] if s_complete_obj else -2

        all_clients = db_manager.get_all_clients()
        if all_clients is None: all_clients = []
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
        success = db_manager.update_client(client_id, data_for_db_update)
        if success:
            QMessageBox.information(doc_manager, doc_manager.tr("Succès"), doc_manager.tr("Client mis à jour avec succès."))
            load_and_display_clients(doc_manager) # Refresh map and list widget
            tab_refreshed = False
            for i in range(doc_manager.client_tabs_widget.count()):
                tab_widget = doc_manager.client_tabs_widget.widget(i)
                if hasattr(tab_widget, 'client_info') and tab_widget.client_info.get("client_id") == client_id:
                    if hasattr(tab_widget, 'refresh_display'):
                        updated_client_data_for_tab = doc_manager.clients_data_map.get(client_id)
                        if updated_client_data_for_tab:
                            tab_widget.refresh_display(updated_client_data_for_tab)
                            doc_manager.client_tabs_widget.setTabText(i, updated_client_data_for_tab.get('client_name', 'Client'))
                            tab_refreshed = True
                    break
            doc_manager.stats_widget.update_stats()
        else:
            QMessageBox.warning(doc_manager, doc_manager.tr("Erreur"), doc_manager.tr("Échec de la mise à jour du client."))

def archive_client_status(doc_manager, client_id):
    if client_id not in doc_manager.clients_data_map: return
    try:
        status_archived_obj = db_manager.get_status_setting_by_name('Archivé', 'Client')
        if not status_archived_obj:
            QMessageBox.critical(doc_manager, doc_manager.tr("Erreur Configuration"),
                                 doc_manager.tr("Statut 'Archivé' non trouvé. Veuillez configurer les statuts."))
            return
        archived_status_id = status_archived_obj['status_id']
        updated = db_manager.update_client(client_id, {'status_id': archived_status_id})
        if updated:
            doc_manager.clients_data_map[client_id]["status"] = "Archivé"
            doc_manager.clients_data_map[client_id]["status_id"] = archived_status_id
            filter_and_display_clients(doc_manager) # Refresh list display
            for i in range(doc_manager.client_tabs_widget.count()):
                tab_w = doc_manager.client_tabs_widget.widget(i)
                if hasattr(tab_w, 'client_info') and tab_w.client_info["client_id"] == client_id:
                    if hasattr(tab_w, 'status_combo'): # Check if ClientWidget has status_combo
                        tab_w.status_combo.setCurrentText("Archivé") # Update status combo in open tab
                    break
            doc_manager.stats_widget.update_stats()
            QMessageBox.information(doc_manager, doc_manager.tr("Client Archivé"),
                                    doc_manager.tr("Le client '{0}' a été archivé.").format(doc_manager.clients_data_map[client_id]['client_name']))
        else:
            QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"),
                                 doc_manager.tr("Erreur d'archivage du client. Vérifiez les logs."))
    except Exception as e:
        QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"), doc_manager.tr("Erreur d'archivage du client:\n{0}").format(str(e)))

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
            deleted_from_db = db_manager.delete_client(client_id)
            if deleted_from_db:
                if os.path.exists(client_folder_path):
                    shutil.rmtree(client_folder_path, ignore_errors=True)
                del doc_manager.clients_data_map[client_id]
                filter_and_display_clients(doc_manager) # Refresh list display
                for i in range(doc_manager.client_tabs_widget.count()):
                    if hasattr(doc_manager.client_tabs_widget.widget(i), 'client_info') and \
                       doc_manager.client_tabs_widget.widget(i).client_info["client_id"] == client_id:
                        doc_manager.close_client_tab(i); break # close_client_tab is a method of DocumentManager
                doc_manager.stats_widget.update_stats()
                QMessageBox.information(doc_manager, doc_manager.tr("Client Supprimé"),
                                        doc_manager.tr("Client '{0}' supprimé avec succès.").format(client_name_val))
            else:
                QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"),
                                     doc_manager.tr("Erreur lors de la suppression du client de la base de données. Le dossier n'a pas été supprimé."))
        except OSError as e_os:
            QMessageBox.critical(doc_manager, doc_manager.tr("Erreur Dossier"),
                                 doc_manager.tr("Le client a été supprimé de la base de données, mais une erreur est survenue lors de la suppression de son dossier:\n{0}").format(str(e_os)))
            if client_id in doc_manager.clients_data_map: # Check if still in map before attempting del
                 del doc_manager.clients_data_map[client_id]
            filter_and_display_clients(doc_manager)
            for i in range(doc_manager.client_tabs_widget.count()):
                if hasattr(doc_manager.client_tabs_widget.widget(i), 'client_info') and \
                   doc_manager.client_tabs_widget.widget(i).client_info["client_id"] == client_id:
                    doc_manager.close_client_tab(i); break
            doc_manager.stats_widget.update_stats()
        except Exception as e_db:
             QMessageBox.critical(doc_manager, doc_manager.tr("Erreur DB"),
                                  doc_manager.tr("Erreur lors de la suppression du client:\n{0}").format(str(e_db)))
