import xml.etree.ElementTree as ET
import subprocess

# Placeholder for actual translation logic
def get_best_effort_translation(text, lang_code):
    return f"[{lang_code.upper()}_BEST_EFFORT] {text}"

# --- Dictionary of French to Russian translations ---
fr_to_ru_specific_translations = {
    "Actions": "Действия",
    "Actualiser": "Обновить",
    "Annuler": "Отмена",
    "Bonjour,\n\nVeuillez trouver ci-joint les documents compilés pour le projet {0}.\n\nCordialement,\nVotre équipe": "Здравствуйте,\n\nПожалуйста, найдите в приложении скомпилированные документы для проекта {0}.\n\nС уважением,\nВаша команда",
    "Fermer": "Закрыть",
    "Sauvegarder": "Сохранить",
    "Oui": "Да",
    "Non": "Нет",
    "Couleur du Texte Principal:": "Основной цвет текста:",
    "Charger Logo": "Загрузить логотип",
    "Ajouter un Nouveau Client": "Добавить нового клиента",
    "Clients Totaux": "Всего клиентов",
    "Projets en Cours": "Текущие проекты",
    "Projets Urgents": "Срочные проекты",
    "Valeur Totale": "Общая стоимость",
    "À propos": "О программе",
    "Éditer": "Редактировать",
    "Langue:": "Язык:",
    "Paramètres": "Настройки"
    # ... more translations by the AI
}

def translate_file(ts_file_path, lang_code, specific_translations_dict):
    print(f"Starting update of {ts_file_path} for language {lang_code}")
    tree = ET.parse(ts_file_path)
    root = tree.getroot()

    expected_lang_attrib = f"{lang_code.lower()}_{lang_code.upper()}"
    if root.get('language') != expected_lang_attrib:
        print(f"Updating language attribute from '{root.get('language')}' to '{expected_lang_attrib}'")
        root.set('language', expected_lang_attrib)

    for context_node in root.findall('context'):
        for message_node in context_node.findall('message'):
            source_node = message_node.find('source')
            translation_node = message_node.find('translation')

            if source_node is not None and source_node.text is not None and translation_node is not None:
                source_text = source_node.text
                translated_text = "" # Initialize
                if source_text in specific_translations_dict:
                    translated_text = specific_translations_dict[source_text]
                else:
                    # If the translation was marked 'unfinished' but no specific entry, use placeholder
                    translated_text = get_best_effort_translation(source_text, lang_code)

                translation_node.text = translated_text
                if 'type' in translation_node.attrib: # Remove 'unfinished' attribute
                    del translation_node.attrib['type']
            elif source_node is None or source_node.text is None:
                print("Warning: Found a message entry with no source text. Skipping.")
            elif translation_node is None: # Should not happen for app_ru.ts as it was prepared
                print(f"Warning: Found message for source '{source_node.text}' with no translation node. Creating one.")
                new_translation_node = ET.SubElement(message_node, 'translation')
                new_translation_node.text = get_best_effort_translation(source_node.text, lang_code)

    tree.write(ts_file_path, encoding='utf-8', xml_declaration=True)
    print(f"Finished updating {ts_file_path}")

    try:
        result = subprocess.run(["xmllint", "--noout", ts_file_path], check=True)
        print(f"XML syntax check passed for {ts_file_path}.")
    except subprocess.CalledProcessError as e:
        print(f"XML syntax check FAILED for {ts_file_path}. Error: {e}")
        raise Exception(f"XML validation failed for {ts_file_path}")
    except FileNotFoundError:
        print(f"Error: xmllint command not found. Please ensure libxml2-utils is installed.")
        raise

# --- Main script execution ---
translate_file("translations/ts/app_ru.ts", "ru", fr_to_ru_specific_translations)
print("Subtask for app_ru.ts completed.")
