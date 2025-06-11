import xml.etree.ElementTree as ET
import subprocess

# Placeholder for actual translation logic
def get_best_effort_translation(text, lang_code):
    return f"[{lang_code.upper()}_BEST_EFFORT] {text}"

# --- Dictionary of French to Turkish translations ---
fr_to_tr_specific_translations = {
    "Actions": "Eylemler",
    "Actualiser": "Yenile",
    "Annuler": "İptal",
    "Bonjour,\n\nVeuillez trouver ci-joint les documents compilés pour le projet {0}.\n\nCordialement,\nVotre équipe": "Merhaba,\n\n{0} projesi için derlenmiş belgeleri ekte bulabilirsiniz.\n\nSaygılarımla,\nEkibiniz",
    "Fermer": "Kapat",
    "Sauvegarder": "Kaydet",
    "Oui": "Evet",
    "Non": "Hayır",
    "Couleur du Texte Principal:": "Ana Metin Rengi:",
    "Charger Logo": "Logo Yükle",
    "Ajouter un Nouveau Client": "Yeni Müşteri Ekle",
    "Clients Totaux": "Toplam Müşteriler",
    "Projets en Cours": "Devam Eden Projeler",
    "Projets Urgents": "Acil Projeler",
    "Valeur Totale": "Toplam Değer",
    "À propos": "Hakkında",
    "Éditer": "Düzenle"
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
                translated_text = "" # Initialize to ensure it's always set
                if source_text in specific_translations_dict:
                    translated_text = specific_translations_dict[source_text]
                    # Optional: print only if actual change happens or if it was unfinished
                    # if translation_node.text != translated_text or translation_node.get('type') == 'unfinished':
                    #    print(f"Translating '{source_text}' to '{translated_text}' (specific for {lang_code})")
                else:
                    translated_text = get_best_effort_translation(source_text, lang_code)
                    # Optional: print only if actual change happens or if it was unfinished
                    # if translation_node.text != translated_text or translation_node.get('type') == 'unfinished':
                    #    print(f"Using placeholder translation for '{source_text}' to '{translated_text}' (general for {lang_code})")

                translation_node.text = translated_text
                if 'type' in translation_node.attrib:
                    del translation_node.attrib['type']
            elif source_node is None or source_node.text is None:
                print("Warning: Found a message entry with no source text. Skipping.")
            elif translation_node is None:
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
translate_file("translations/ts/app_tr.ts", "tr", fr_to_tr_specific_translations)
print("Subtask for app_tr.ts completed.")
