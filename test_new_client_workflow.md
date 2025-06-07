# Manual Test Plan: New Client Workflow & UI Enhancements

## Objective:
To verify the correct functionality of the sequential dialogs (Contact, Product, Create Document) after a new client is created, including data persistence for contacts and products, and to check the UI/UX enhancements made to these dialogs.

## Prerequisites:
- The application is running.
- Ensure `main.py` is the entry point.
- Database (db.py related) is initialized and accessible.

## Test Cases:

### Test Case 1: Full Successful Workflow (with Data Persistence)
1.  **Action:** Launch the application.
2.  **Action:** In the 'Ajouter un Nouveau Client' form, fill in all required fields (Nom Client, Pays, ID Projet) and any optional fields with unique data for this test run.
3.  **Action:** Click the "Créer Client" button.
4.  **Expected Result:**
    *   The "Ajouter Contact" dialog should appear.
    *   Verify its title is "Ajouter Contact".
    *   Verify UI: Header label ("Ajouter Nouveau Contact"), icons next to fields, padding, button styling, and bottom button frame.
5.  **Action:** Fill in the contact details (e.g., Name: "Test Contact 1", Email: "tc1@example.com", Phone: "12345", Position: "Tester", Mark as "Contact principal"). Click "OK".
6.  **Expected Result:**
    *   The "Ajouter Produit" dialog should appear.
    *   Verify its title is "Ajouter Produit".
    *   Verify UI: Header label ("Ajouter Détails Produit"), icons, padding, button styling, total price label appearance, and bottom button frame.
7.  **Action:** Fill in product details (e.g., Name: "Test Product A", Quantité: 2, Prix Unitaire: 50.00). Verify "Prix Total" updates to "€ 100.00". Click "OK".
8.  **Expected Result:**
    *   The "Créer des Documents" dialog should appear.
    *   Verify its title is "Créer des Documents".
    *   Verify UI: Header label ("Sélectionner Documents à Créer"), icons for labels, list hover effect, padding, button styling, and bottom button frame.
9.  **Action:** Select at least one document template and a language (if multiple available). Click "Créer Documents".
10. **Expected Result:**
    *   A success message for document creation (e.g., "X documents ont été créés avec succès.") should appear.
    *   The main application window should show the standard "Client Créé" success message (e.g., "Client [Client Name] créé avec succès...").
    *   The new client's tab should open automatically in `DocumentManager`.
    *   The client list should update and display the new client.
    *   Statistics should update to reflect the new client and their price (if applicable).
11. **Verification (Data Persistence & Display):**
    *   Navigate to the newly opened client's tab in `DocumentManager`.
    *   **Contacts Tab:** Verify the contact ("Test Contact 1") added in step 5 is listed, and marked as principal if checked.
    *   **Produits Tab:** Verify the product ("Test Product A") added in step 7 is listed with the correct quantity (2), unit price (€ 50.00), and total price (€ 100.00).
    *   **Documents Tab:** If documents were created in step 9, verify they are listed.
    *   **Client Folder:** Check the client's folder on the filesystem (path derived from `clients_dir` in `config.json` and client details) to ensure documents were created in the correct language subfolder (if applicable).
    *   **Database (Optional):** If possible, query the database to confirm the client, contact, client-contact link (with primary status), product, and client-product link records were created correctly.

### Test Case 2: Cancellation at Contact Dialog
1.  **Action:** Launch the application.
2.  **Action:** Fill in new client details (e.g., "Client Cancel Contact", select Pays, ID Projet "TC2") and click "Créer Client".
3.  **Expected Result:** The "Ajouter Contact" dialog appears.
4.  **Action:** Click "Annuler" or close the "Ajouter Contact" dialog using the window's close button.
5.  **Expected Result:**
    *   The "Ajouter Produit" dialog should NOT appear.
    *   The "Créer des Documents" dialog should NOT appear.
    *   The main application window shows the "Client Créé" success message for "Client Cancel Contact".
    *   The new client's tab ("Client Cancel Contact") opens.
    *   The client is created and visible in the client list.
6.  **Verification:** Open the "Client Cancel Contact" tab. Navigate to the "Contacts", "Produits", and "Documents" sub-tabs. They should be empty (no items related to this workflow).

### Test Case 3: Cancellation at Product Dialog
1.  **Action:** Launch the application.
2.  **Action:** Fill in new client details (e.g., "Client Cancel Product", select Pays, ID Projet "TC3") and click "Créer Client".
3.  **Action:** In the "Ajouter Contact" dialog, add a contact (e.g., "Contact For TC3") and click "OK".
4.  **Expected Result:** The "Ajouter Produit" dialog appears.
5.  **Action:** Click "Annuler" or close the "Ajouter Produit" dialog.
6.  **Expected Result:**
    *   The "Créer des Documents" dialog should NOT appear.
    *   The main application window shows the "Client Créé" success message for "Client Cancel Product".
    *   The new client's tab ("Client Cancel Product") opens.
7.  **Verification:** Open the "Client Cancel Product" tab.
    *   **Contacts Tab:** Verify "Contact For TC3" is listed.
    *   **Produits Tab:** Should be empty.
    *   **Documents Tab:** Should be empty.

### Test Case 4: Cancellation at Create Document Dialog
1.  **Action:** Launch the application.
2.  **Action:** Fill in new client details (e.g., "Client Cancel Docs", select Pays, ID Projet "TC4") and click "Créer Client".
3.  **Action:** In the "Ajouter Contact" dialog, add a contact (e.g., "Contact For TC4") and click "OK".
4.  **Action:** In the "Ajouter Produit" dialog, add a product (e.g., "Product For TC4") and click "OK".
5.  **Expected Result:** The "Créer des Documents" dialog appears.
6.  **Action:** Click "Annuler" or close the "Créer des Documents" dialog.
7.  **Expected Result:**
    *   The main application window shows the "Client Créé" success message for "Client Cancel Docs".
    *   The new client's tab ("Client Cancel Docs") opens.
8.  **Verification:** Open the "Client Cancel Docs" tab.
    *   **Contacts Tab:** Verify "Contact For TC4" is listed.
    *   **Produits Tab:** Verify "Product For TC4" is listed.
    *   **Documents Tab:** Should be empty (no documents created from this specific sequence).

### Test Case 5: Dialog UI Verification (Enhanced)
1.  **Action:** Trigger each dialog in the sequence by starting to create a new client (as per Test Case 1, steps 2-3, then proceed through dialogs one by one, clicking "OK" to get to the next).
2.  **Verification for `ContactDialog`:**
    *   **Header:** Verify the presence of a header label with text like "Ajouter Nouveau Contact" and that it's styled (bold, prominent).
    *   **Window Title:** "Ajouter Contact" is displayed.
    *   **Icons:** Verify icons next to "Nom complet:", "Email:", "Téléphone:", "Poste:", "Principal:".
    *   **Layout & Padding:** General layout has adequate spacing. Input fields (QLineEdit, QCheckBox) have visible padding.
    *   **Primary Contact Cue:** Check the "Contact principal" box. Verify the "Nom complet" field background changes (e.g., to light green). Uncheck it and verify the background reverts.
    *   **Button Grouping:** Bottom buttons ("OK", "Annuler") are in a frame with a top border.
    *   **Button Styling:** "OK" button is styled (green, white text, icon). "Annuler" button is standard or consistently styled (with icon).
3.  **Verification for `ProductDialog`:**
    *   **Header:** Verify header label "Ajouter Détails Produit" and its styling.
    *   **Window Title:** "Ajouter Produit" is displayed.
    *   **Icons:** Verify icons next to "Nom du Produit:", "Quantité:", "Prix Unitaire:".
    *   **Layout & Padding:** General layout has adequate spacing. Input fields have padding.
    *   **Price Readability:** "Prix Total" label is bold, larger font, distinct color, and updates correctly.
    *   **Button Grouping:** Bottom buttons are in a frame with a top border.
    *   **Button Styling:** "OK" button styled (green). "Annuler" button standard/consistent (with icon).
4.  **Verification for `CreateDocumentDialog`:**
    *   **Header:** Verify header label "Sélectionner Documents à Créer" and its styling.
    *   **Window Title:** "Créer des Documents" is displayed.
    *   **Icons:** Verify icons next to "Langue:" and "Sélectionnez les documents à créer:" labels.
    *   **Layout & Padding:** General layout has adequate spacing. QComboBox and QListWidget have padding.
    *   **List Hover Effect:** Hovering over items in the `templates_list` shows a background color change.
    *   **Button Grouping:** Bottom buttons are in a frame with a top border.
    *   **Button Styling:** "Créer Documents" button styled (green). "Annuler" button standard/consistent (with icon).

## Notes:
- Check the application's console output for any errors, "FIXME" messages, or unexpected print statements (e.g., "CreateDocumentDialog cancelled.") during the tests.
- The "Modifier Contact" and "Modifier Produit" titles for `ContactDialog` and `ProductDialog` respectively are primarily for when these dialogs are called from `ClientWidget` to edit existing data, not during this new client creation flow.
- Ensure that if a dialog is cancelled, no data from that dialog or subsequent dialogs in the sequence is saved for the client.
```