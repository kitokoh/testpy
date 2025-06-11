import xml.etree.ElementTree as ET

# Define translations from French source to English
# This is a partial list based on common patterns observed.
# A more comprehensive approach would use a translation service or a human translator.
# For now, providing direct translations for the identified French source strings.
# Any string not in this dict will have its placeholder [EN] removed, making the translation same as source.
# This is a fallback for source strings that might already be English or don't need specific translation.

fr_to_en_translations = {
    "Actions": "Actions",
    "Actualiser": "Refresh",
    "Adresse email du destinataire:": "Recipient's email address:",
    "Afficher la ligne horizontale": "Show horizontal line",
    "Ajouter Contact": "Add Contact",
    "Ajouter Modèle": "Add Template",
    "Ajouter PDF": "Add PDF",
    "Ajouter Produit": "Add Product",
    "Ajouter colonne": "Add column",
    "Ajouter des notes sur ce client...": "Add notes about this client...",
    "Ajouter ligne": "Add row",
    "Ajouter un Nouveau Client": "Add New Client",
    "Ajouter un nouveau pays": "Add new country",
    "Ajouter une nouvelle ville": "Add new city",
    "Annuler": "Cancel",
    "Aucun document n'a pu être créé.": "No document could be created.",
    "Aucun document sélectionné": "No document selected",
    "Aucun logo chargé.": "No logo loaded.",
    "Auteur par défaut:": "Default author:",
    "Auteur:": "Author:",
    "Besoin Client:": "Client Need:",
    "Besoin Principal:": "Main Need:",
    "Besoin:": "Need:",
    "Bonjour,\n\nVeuillez trouver ci-joint les documents compilés pour le projet {0}.\n\nCordialement,\nVotre équipe": "Hello,\n\nPlease find attached the compiled documents for project {0}.\n\nRegards,\nYour Team",
    "Ce pays existe déjà.": "This country already exists.",
    "Cette ville existe déjà pour ce pays.": "This city already exists for this country.",
    "Champs Requis": "Required Fields",
    "Charger Logo": "Load Logo",
    "Charger Modèle": "Load Template",
    "Charger": "Load",
    "Chemin base de données:": "Database path:",
    "Chemin Dossier:": "Folder Path:",
    "Chemin vers l'image du logo": "Path to logo image",
    "Choisir Couleur": "Choose Color",
    "Choisir un Logo": "Choose a Logo",
    "Client: {0}": "Client: {0}",
    "Clients Totaux": "Total Clients",
    "Client Créé": "Client Created",
    "Client Supprimé": "Client Deleted",
    "Client {0} créé (ID: {1}).": "Client {0} created (ID: {1}).",
    "Colonne {0}": "Column {0}",
    "Compilation de Documents - Projet: {0}": "Document Compilation - Project: {0}",
    "Compilation de Documents": "Document Compilation",
    "Compilation réussie": "Compilation successful",
    "Compiler PDF": "Compile PDF",
    "Compiler des PDF": "Compile PDFs",
    "Confirmer Suppression": "Confirm Deletion",
    "Confirmer la suppression": "Confirm deletion",
    "Configuration manquante": "Missing configuration",
    "Conflit de Données": "Data Conflict",
    "Contact principal": "Main contact",
    "Contacts": "Contacts",
    "Couleur du Texte Principal:": "Main Text Color:",
    "Créer Client": "Create Client",
    "Créer Documents": "Create Documents",
    "Créer des Documents": "Create Documents",
    "Date (YYYY-MM-DD):": "Date (YYYY-MM-DD):",
    "Date Création:": "Creation Date:",
    "Date d'émission:": "Issue Date:",
    "Date": "Date",
    "Descendre": "Move Down",
    "Description du besoin": "Description of need",
    "Description:": "Description:",
    "Document compilé le {0}": "Document compiled on {0}",
    "Documents créés": "Documents created",
    "Documents": "Documents",
    "Dossier Existant": "Existing Folder",
    "Dossier des Clients:": "Clients Folder:",
    "Dossier des Modèles:": "Templates Folder:",
    "Définir par Défaut": "Set as Default",
    "Département ou faculté (optionnel)": "Department or faculty (optional)",
    "Département/Faculté:": "Department/Faculty:",
    "Défaut": "Default",
    "Email envoyé": "Email sent",
    "Email:": "Email:",
    "Email": "Email",
    "Entrez le nom de la nouvelle ville pour {0}:": "Enter the name of the new city for {0}:",
    "Entrez le nom du nouveau pays:": "Enter the name of the new country:",
    "Entrez un nom pour ce modèle:": "Enter a name for this template:",
    "Envoyer par email": "Send by email",
    "Erreur DB Gestion de Projet": "Project Management DB Error",
    "Erreur DB": "DB Error",
    "Erreur DB recherche email: {0}": "DB email search error: {0}",
    "Erreur DOCX": "DOCX Error",
    "Erreur HTML": "HTML Error",
    "Erreur Modèle": "Template Error",
    "Erreur Page de Garde": "Cover Page Error",
    "Erreur PDF": "PDF Error",
    "Erreur lors de la compilation du PDF:\n{0}": "Error compiling PDF:\n{0}",
    "Erreur lors de la génération de la page de garde via pagedegrde: {0}": "Error generating cover page via pagedegrde: {0}",
    "Erreur lors de l'ajout de {0}:\n{1}": "Error adding {0}:\n{1}",
    "Erreur lors de l'envoi de l'email:\n{0}": "Error sending email:\n{0}",
    "Erreur": "Error",
    "Erreur Base de Données": "Database Error",
    "Erreur de Configuration": "Configuration Error",
    "Erreur de Chargement": "Loading Error",
    "Erreur de Sauvegarde": "Save Error",
    "Erreur de chargement des contacts:\n{0}": "Error loading contacts:\n{0}",
    "Erreur de chargement des modèles:\n{str(e)}": "Error loading templates:\n{str(e)}", # Keep as is, specific Python formatting
    "Erreur de chargement des modèles:\n{0}": "Error loading templates:\n{0}",
    "Erreur de chargement des pays:\n{0}": "Error loading countries:\n{0}",
    "Erreur de chargement des produits:\n{0}": "Error loading products:\n{0}",
    "Erreur de chargement des statuts:\n{0}": "Error loading statuses:\n{0}",
    "Erreur de chargement de la feuille": "Sheet loading error",
    "Erreur de chargement statuts pour filtre: {0}": "Error loading statuses for filter: {0}",
    "Erreur de mise à jour du modèle:\n{str(e)}": "Error updating template:\n{str(e)}", # Keep as is
    "Erreur de mise à jour du statut:\n{0}": "Error updating status:\n{0}",
    "Erreur de sauvegarde des notes:\n{0}": "Error saving notes:\n{0}",
    "Erreur de suppression du contact:\n{0}": "Error deleting contact:\n{0}",
    "Erreur de suppression du modèle:\n{str(e)}": "Error deleting template:\n{str(e)}", # Keep as is
    "Erreur de suppression du produit:\n{0}": "Error deleting product:\n{0}",
    "Erreur d'Ouverture Fichier": "File Open Error",
    "Erreur d'accès au modèle:\n{str(e)}": "Error accessing template:\n{str(e)}", # Keep as is
    "Erreur d'ajout de la ville:\n{0}": "Error adding city:\n{0}",
    "Erreur d'ajout du contact:\n{0}": "Error adding contact:\n{0}",
    "Erreur d'ajout du modèle:\n{str(e)}": "Error adding template:\n{str(e)}", # Keep as is
    "Erreur d'ajout du pays:\n{0}": "Error adding country:\n{0}",
    "Erreur d'ajout du produit:\n{0}": "Error adding product:\n{0}",
    "Erreur d'export PDF": "PDF Export Error",
    "Erreur d'export PDF: {0}": "PDF Export Error: {0}",
    "Erreur d'envoi": "Send Error",
    "Erreur d'ouverture du PDF: {0}": "Error opening PDF: {0}",
    "Excel": "Excel",
    "Exporter PDF": "Export PDF",
    "Exporter en PDF": "Export to PDF",
    "Fermer": "Close",
    "Fichier Inexistant": "File Not Found",
    "Fichier Modèles (*.xlsx *.docx *.html);;Fichiers Excel (*.xlsx);;Documents Word (*.docx);;Documents HTML (*.html);;Tous les fichiers (*)": "Template Files (*.xlsx *.docx *.html);;Excel Files (*.xlsx);;Word Documents (*.docx);;HTML Documents (*.html);;All files (*)",
    "Fichier PDF (*.pdf);;Tous les fichiers (*)": "PDF Files (*.pdf);;All files (*)",
    "Fichier PDF compilé": "Compiled PDF File",
    "Fichier introuvable.": "File not found.",
    "Fichier modèle '{0}' introuvable pour '{1}'.": "Template file '{0}' not found for '{1}'.",
    "Fichier non trouvé": "File not found",
    "Fichier supprimé": "File deleted",
    "Fichier": "File",
    "Filtrer par statut:": "Filter by status:",
    "Formulaire d'Offre": "Offer Form",
    "Français (fr)": "French (fr)",
    "Français uniquement (fr)": "French only (fr)",
    "Gestion des Contacts": "Contact Management",
    "Gestion des Modèles": "Template Management",
    "Gestion des Statuts": "Status Management",
    "Gestionnaire de Documents Client": "Client Document Manager",
    "Général": "General",
    "HTML": "HTML",
    "ID Projet Existant": "Existing Project ID",
    "ID Projet:": "Project ID:",
    "ID": "ID",
    "Identifiant du projet": "Project identifier",
    "Identifiant unique du projet": "Unique project identifier",
    "Impossible d'initialiser la base de données: {0}\nL'application pourrait ne pas fonctionner correctement.": "Could not initialize database: {0}\nThe application may not function correctly.",
    "Impossible d'enregistrer la configuration: {0}": "Could not save configuration: {0}",
    "Impossible d'ouvrir le fichier:\n{0}": "Could not open file:\n{0}",
    "Impossible de charger la feuille '{0}':\n{1}": "Could not load sheet '{0}':\n{1}",
    "Impossible de charger le fichier Excel:\n{0}\n\nUn tableau vide sera créé.": "Could not load Excel file:\n{0}\n\nAn empty table will be created.",
    "Impossible de générer la page de garde personnalisée: {0}": "Could not generate custom cover page: {0}",
    "Impossible de populer le modèle HTML '{0}':\n{1}": "Could not populate HTML template '{0}':\n{1}",
    "Impossible de populer le modèle Word '{0}':\n{1}": "Could not populate Word template '{0}':\n{1}",
    "Impossible de supprimer le fichier:\n{0}": "Could not delete file:\n{0}",
    "Informations Client": "Client Information",
    "Institution par défaut:": "Default institution:",
    "Inconnu": "Unknown",
    "Jours avant rappel client ancien:": "Days before old client reminder:",
    "L'ID Projet '{0}' est déjà utilisé.": "Project ID '{0}' is already in use.",
    "Langue Interface (redémarrage requis):": "Interface Language (restart required):",
    "Langue du Modèle": "Template Language",
    "Langue:": "Language:",
    "Langues:": "Languages:",
    "Le PDF compilé a été sauvegardé dans:\n{0}": "The compiled PDF has been saved to:\n{0}",
    "Le client {0} a été créé, mais la création du projet correspondant a échoué : {1}": "Client {0} was created, but the corresponding project creation failed: {1}",
    "Le document a été envoyé avec succès.": "The document was sent successfully.",
    "Le fichier PDF a été créé avec succès:\n{0}\n\nVoulez-vous l'ouvrir ?": "The PDF file was created successfully:\n{0}\n\nDo you want to open it?",
    "Le fichier {0} n'existe pas.\nUn nouveau fichier sera créé.": "File {0} does not exist.\nA new file will be created.",
    "Le fichier a été sauvegardé avec succès:\n{0}": "The file was saved successfully:\n{0}",
    "Le fichier n'existe plus.": "The file no longer exists.",
    "Le tableau est vide. Impossible d'exporter en PDF.": "The table is empty. Cannot export to PDF.",
    "Les préférences ont été appliquées.": "Preferences have been applied.",
    "Modifications Non Sauvegardées": "Unsaved Changes",
    "Modèle Copié": "Template Copied",
    "Modèle Existant": "Existing Template",
    "Modèle Supprimé": "Template Deleted",
    "Modèle défini comme modèle par défaut pour sa catégorie et langue.": "Template set as default for its category and language.",
    "Modèle ajouté avec succès.": "Template added successfully.",
    "Modèle supprimé avec succès.": "Template deleted successfully.",
    "Modèle {0} chargé": "Template {0} loaded",
    "Modèle enregistre.": "Template saved.", # Note: "enregistre" seems like a typo for "enregistré"
    "Modèles": "Templates",
    "Moderne": "Modern",
    "Modifier Contact": "Edit Contact",
    "Modifier Produit": "Edit Product",
    "Modifier": "Edit",
    "Monter": "Move Up",
    "Mot de passe SMTP:": "SMTP Password:",
    "N/A": "N/A",
    "Nouveau Modèle": "New Template",
    "Nouveau Pays": "New Country",
    "Nouvelle Ville": "New City",
    "Nom Client:": "Client Name:",
    "Nom Entreprise:": "Company Name:",
    "Nom Produit": "Product Name",
    "Nom de fichier manquant pour le modèle '{0}'. Impossible de créer.": "Missing filename for template '{0}'. Cannot create.",
    "Nom du Modèle": "Template Name",
    "Nom du Produit:": "Product Name:",
    "Nom du client": "Client name",
    "Nom du client:": "Client name:",
    "Nom du fichier compilé:": "Compiled file name:",
    "Nom du fichier": "File name",
    "Nom entreprise (optionnel)": "Company name (optional)",
    "Nom complet:": "Full name:",
    "Nom manquant": "Name missing",
    "Nom:": "Name:",
    "Nom": "Name",
    "Notes": "Notes",
    "Nous contacter": "Contact us",
    "OK": "OK",
    "Ouvrir Dossier Client": "Open Client Folder",
    "Ouvrir Fiche Client": "Open Client File",
    "Ouvrir": "Open",
    "PDF": "PDF",
    "Paramètres de l'Application": "Application Settings",
    "Paramètres Sauvegardés": "Settings Saved",
    "Paramètres": "Settings",
    "Parcourir...": "Browse...",
    "Pays Client:": "Client Country:",
    "Pays Existant": "Existing Country",
    "Pays Inconnu": "Unknown Country",
    "Pays Requis": "Country Required",
    "Pays:": "Country:",
    "Police par défaut:": "Default font:",
    "Port SMTP:": "SMTP Port:",
    "Poste:": "Position:",
    "Pour toute question: contact@example.com": "For any questions: contact@example.com",
    "Préférences": "Preferences",
    "Principal": "Main",
    "Prix Final:": "Final Price:",
    "Prix Total:": "Total Price:",
    "Prix Unitaire:": "Unit Price:",
    "Prix:": "Price:",
    "Produits": "Products",
    "Projet Créé": "Project Created",
    "Projet: {0}": "Project: {0}",
    "Projets Urgents": "Urgent Projects",
    "Projets en Cours": "Ongoing Projects",
    "Prêt": "Ready",
    "Qté": "Qty",
    "Quantité:": "Quantity:",
    "Quitter": "Exit",
    "Rechercher client...": "Search client...",
    "Retirer Logo": "Remove Logo",
    "Réessayer": "Retry",
    "Réussi": "Successful",
    "Sauvegarde Réussie": "Save Successful",
    "Sauvegarde en cours...": "Saving...",
    "Sauvegarder": "Save",
    "Serveur SMTP:": "SMTP Server:",
    "Statut:": "Status:",
    "Succès": "Success",
    "Supprimer Client": "Delete Client",
    "Supprimer Contact": "Delete Contact",
    "Supprimer Modèle": "Delete Template",
    "Supprimer Produit": "Delete Product",
    "Supprimer": "Delete",
    "Sélection": "Selection",
    "Sélectionner dossier clients": "Select clients folder",
    "Sélectionner dossier modèles": "Select templates folder",
    "Sélectionner la langue:": "Select language:",
    "Sélectionner les PDF à compiler:": "Select PDFs to compile:",
    "Sélectionner les documents à créer:": "Select documents to create:",
    "Sélectionner un modèle": "Select a template",
    "Taille de police par défaut:": "Default font size:",
    "Tous les statuts": "All statuses",
    "Toutes les langues (fr, ar, tr)": "All languages (fr, ar, tr)", # This might need context. "fr, ar, tr" are language codes.
    "Turc (tr)": "Turkish (tr)",
    "Turc uniquement (tr)": "Turkish only (tr)",
    "Type de document:": "Document type:",
    "Type": "Type",
    "Télécharger": "Download",
    "Téléphone:": "Phone:",
    "Un client avec un chemin de dossier similaire existe déjà ou autre contrainte DB violée: {0}": "A client with a similar folder path already exists or other DB constraint violated: {0}",
    "Un dossier client avec ces identifiants (nom, pays, projet) existe déjà.": "A client folder with these identifiers (name, country, project) already exists.",
    "Un projet correspondant pour {0} a été automatiquement créé dans le système de gestion de projet.": "A corresponding project for {0} has been automatically created in the project management system.",
    "Une erreur inattendue s'est produite:\n{0}": "An unexpected error occurred:\n{0}",
    "Urgent": "Urgent",
    "Utilisateur SMTP:": "SMTP User:",
    "Valeur Totale": "Total Value",
    "Version:": "Version:",
    "Veuillez configurer les paramètres SMTP dans les paramètres de l'application.": "Please configure SMTP settings in the application settings.",
    "Veuillez d'abord sélectionner un pays.": "Please select a country first.",
    "Veuillez sélectionner au moins un document à créer.": "Please select at least one document to create.",
    "Veuillez spécifier un nom de fichier pour la compilation.": "Please specify a filename for compilation.",
    "Ville Client:": "Client City:",
    "Ville Existante": "Existing City",
    "Ville:": "City:",
    "Votre Entreprise": "Your Company",
    "Vous avez des modifications non sauvegardées.\nÊtes-vous sûr de vouloir annuler ?": "You have unsaved changes.\nAre you sure you want to cancel?",
    "Vous avez des modifications non sauvegardées.\nVoulez-vous sauvegarder avant de fermer ?": "You have unsaved changes.\nDo you want to save before closing?",
    "Vous avez des modifications non sauvegardées dans '{0}'.\nVoulez-vous sauvegarder avant de changer de feuille ?": "You have unsaved changes in '{0}'.\nDo you want to save before switching sheets?",
    "Word": "Word",
    "all ou 1-3,5": "all or 1-3,5", # Technical instruction, likely keep as is
    "compilation": "compilation", # Technical, likely keep as is
    "<b>Gestionnaire de Documents Client</b><br><br>Version 4.0<br>Application de gestion de documents clients avec templates Excel.<br><br>Développé par Saadiya Management (Concept)": "<b>Client Document Manager</b><br><br>Version 4.0<br>Client document management application with Excel templates.<br><br>Developed by Saadiya Management (Concept)",
    "<b>Personnel responsable:</b> Ramazan Demirci    <b>Tél:</b> +90 533 548 27 29    <b>Email:</b> bilgi@hidrogucpres.com": "<b>Contact person:</b> Ramazan Demirci    <b>Tel:</b> +90 533 548 27 29    <b>Email:</b> bilgi@hidrogucpres.com", # Proper nouns and contact details, keep as is or adapt format.
    "<b>Conditions d'achat:</b>": "<b>Purchase Conditions:</b>",
    "À propos": "About",
    "Éditer": "Edit",
    "Éditeur Excel - {0}": "Excel Editor - {0}",
    "Êtes-vous sûr de vouloir supprimer ce contact?": "Are you sure you want to delete this contact?",
    "Êtes-vous sûr de vouloir supprimer ce modèle ?": "Are you sure you want to delete this template?",
    "Êtes-vous sûr de vouloir supprimer le fichier {0} ?": "Are you sure you want to delete file {0}?",
    "Êtes-vous sûr de vouloir supprimer le produit '{0}'?": "Are you sure you want to delete product '{0}'?",
    "&Fichier": "&File",
    "&Nouveau": "&New",
    # Strings that were originally English sources from app_fr.ts (and translated to French there)
    # Need to ensure these are correctly set in app_en.ts (source and translation matching)
    "Client Info Placeholder for: {0}": "Client Info Placeholder for: {0}",
    "Close": "Close",
    "Could not load HTML file: {0}\n{1}": "Could not load HTML file: {0}\n{1}",
    "Could not save HTML file: {0}\n{1}": "Could not save HTML file: {0}\n{1}",
    "Enter HTML content here...": "Enter HTML content here...",
    "HTML Editor - {0}": "HTML Editor - {0}",
    "Load Error": "Load Error",
    "Refresh Preview": "Refresh Preview",
    "Save Error": "Save Error",
    "Save": "Save",
}

# Path to the .ts file
ts_file_path = "translations/ts/app_en.ts"

print(f"Starting update of {ts_file_path}")
tree = ET.parse(ts_file_path)
root = tree.getroot()

for context_node in root.findall('context'):
    for message_node in context_node.findall('message'):
        source_node = message_node.find('source')
        translation_node = message_node.find('translation')

        if source_node is not None and source_node.text is not None and translation_node is not None:
            source_text = source_node.text

            # Check if there's a direct French to English translation
            if source_text in fr_to_en_translations:
                translated_text = fr_to_en_translations[source_text]
                # Ensure it's not already correctly translated (e.g. if source is English)
                if translation_node.text != translated_text :
                    print(f"Translating (FR->EN): '{source_text}' to '{translated_text}'")
                    translation_node.text = translated_text
                    if 'type' in translation_node.attrib:
                        del translation_node.attrib['type'] # Remove 'unfinished' if present
            else:
                # Fallback: If no specific translation, and it's a placeholder, remove placeholder
                # This handles cases where source might be English or doesn't need specific translation from the dict
                if translation_node.text is not None and translation_node.text.startswith("[EN]"):
                    print(f"Removing placeholder for: '{source_text}'. Setting translation to source.")
                    translation_node.text = source_text
                    if 'type' in translation_node.attrib:
                        del translation_node.attrib['type']
                elif translation_node.text is None or translation_node.get('type') == 'unfinished':
                    # If translation is empty or marked unfinished, and not in our dict, assume source is English
                    print(f"Source '{source_text}' not in dict, translation empty/unfinished. Setting to source.")
                    translation_node.text = source_text
                    if 'type' in translation_node.attrib:
                        del translation_node.attrib['type']


# Write the changes back to the file
tree.write(ts_file_path, encoding='utf-8', xml_declaration=True)
print(f"Finished updating {ts_file_path}")

# Basic check to see if the file is still valid XML (not a full validation)
# This part will be run in bash session directly
# import os
# if os.system(f"xmllint --noout {ts_file_path}") == 0:
#     print("XML syntax check passed for app_en.ts.")
# else:
#     print("XML syntax check FAILED for app_en.ts.")
#     # No automatic revert here as per subtask guidelines, but noting the failure.
#     # exit(1) # Cannot exit in agent script
