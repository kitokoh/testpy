# Manual Test Plan: New Client Workflow & UI Enhancements

## Objective:
To verify the correct functionality of the sequential dialogs (Contact, Product, Create Document) after a new client is created, and to check the UI enhancements made to these dialogs.

## Prerequisites:
- The application is running.
- Ensure `main.py` is the entry point.

## Test Cases:

### Test Case 1: Full Successful Workflow
1.  **Action:** Launch the application.
2.  **Action:** In the 'Ajouter un Nouveau Client' form, fill in all required fields (Nom Client, Pays, ID Projet) and any optional fields.
3.  **Action:** Click the "Créer Client" button.
4.  **Expected Result:**
    *   The "Ajouter Contact" dialog should appear.
    *   Verify its title is "Ajouter Contact".
    *   Verify the UI enhancements (styling, padding, button appearance).
5.  **Action:** Fill in the contact details and click "OK".
6.  **Expected Result:**
    *   The "Ajouter Produit" dialog should appear.
    *   Verify its title is "Ajouter Produit".
    *   Verify the UI enhancements (styling, padding, button appearance, total price label).
7.  **Action:** Fill in product details (name, quantity, unit price) and click "OK".
8.  **Expected Result:**
    *   The "Créer des Documents" dialog should appear.
    *   Verify its title is "Créer des Documents".
    *   Verify the UI enhancements (styling, padding, button appearance).
9.  **Action:** Select at least one document template and a language, then click "Créer Documents".
10. **Expected Result:**
    *   A success message for document creation should appear (e.g., "X documents ont été créés avec succès.").
    *   The main application window should show the standard "Client Créé" success message.
    *   The new client's tab should open automatically.
    *   The client list should update with the new client.
    *   Statistics should update.
11. **Verification:**
    *   Check the client's folder (as specified in `clients_dir` in `config.json` and the client's subfolder) to ensure documents were created in the correct language subfolder.
    *   Check the client's details in the UI:
        *   Open the client's tab.
        *   Navigate to the "Contacts" tab within `ClientWidget` and verify the added contact is listed.
        *   Navigate to the "Produits" tab and verify the added product is listed with correct quantity and total price.
        *   Navigate to the "Documents" tab and verify the created documents are listed.

### Test Case 2: Cancellation at Contact Dialog
1.  **Action:** Launch the application.
2.  **Action:** Fill in new client details (Nom Client, Pays, ID Projet) and click "Créer Client".
3.  **Expected Result:** The "Ajouter Contact" dialog appears.
4.  **Action:** Click "Annuler" or close the "Ajouter Contact" dialog using the window's close button.
5.  **Expected Result:**
    *   The "Ajouter Produit" dialog should NOT appear.
    *   The "Créer des Documents" dialog should NOT appear.
    *   The main application window should show the standard "Client Créé" success message.
    *   The new client's tab should open.
    *   The client is created and visible in the client list.
    *   Verification: Check the "Contacts", "Produits", and "Documents" tabs for this new client; they should be empty or not contain items from this workflow.

### Test Case 3: Cancellation at Product Dialog
1.  **Action:** Launch the application.
2.  **Action:** Fill in new client details and click "Créer Client".
3.  **Action:** In the "Ajouter Contact" dialog, fill in contact details and click "OK".
4.  **Expected Result:** The "Ajouter Produit" dialog appears.
5.  **Action:** Click "Annuler" or close the "Ajouter Produit" dialog.
6.  **Expected Result:**
    *   The "Créer des Documents" dialog should NOT appear.
    *   The main application window should show the standard "Client Créé" success message.
    *   The new client's tab should open.
    *   The client is created.
    *   Verification: Check the "Contacts" tab for the new client; the contact from step 3 should be listed. The "Produits" and "Documents" tabs should be empty or not contain items from this workflow.

### Test Case 4: Cancellation at Create Document Dialog
1.  **Action:** Launch the application.
2.  **Action:** Fill in new client details and click "Créer Client".
3.  **Action:** In the "Ajouter Contact" dialog, add a contact and click "OK".
4.  **Action:** In the "Ajouter Produit" dialog, add a product and click "OK".
5.  **Expected Result:** The "Créer des Documents" dialog appears.
6.  **Action:** Click "Annuler" or close the "Créer des Documents" dialog.
7.  **Expected Result:**
    *   The main application window should show the standard "Client Créé" success message.
    *   The new client's tab should open.
    *   The client is created.
    *   Verification: Check the "Contacts" tab (contact should be present), "Produits" tab (product should be present). The "Documents" tab should be empty or not list documents from this specific attempt.

### Test Case 5: Dialog UI Verification (General)
1.  **Action:** Trigger each dialog in the sequence by successfully creating a client and accepting previous dialogs (similar to Test Case 1, up to the point of showing each dialog).
2.  **Verification for `ContactDialog`:**
    *   Window title is "Ajouter Contact" (if new) or "Modifier Contact" (if editing an existing one - though this flow is for new client). Check for correct translation.
    *   Layout has adequate spacing (e.g., QFormLayout spacing is 10).
    *   Input fields (QLineEdit, QCheckBox) have visible padding (e.g., 3px).
    *   "OK" button is styled (green background, white text, padding e.g., 5px 15px).
    *   "Annuler" button is standard or styled with consistent padding.
3.  **Verification for `ProductDialog`:**
    *   Window title is "Ajouter Produit" (if new) or "Modifier Produit". Check for correct translation.
    *   Layout has adequate spacing.
    *   Input fields (QLineEdit, QTextEdit, QDoubleSpinBox) have visible padding.
    *   "Prix Total" label is bold, has a slightly larger font, and updates correctly when quantity/unit price change.
    *   "OK" button is styled as a primary action button.
    *   "Annuler" button is standard or styled with consistent padding.
4.  **Verification for `CreateDocumentDialog`:**
    *   Window title is "Créer des Documents". Check for correct translation.
    *   Layout has adequate spacing.
    *   Widgets (QComboBox for language, QListWidget for templates) have visible padding.
    *   "Créer Documents" button is styled as a primary action button (green).
    *   "Annuler" button is standard or styled with consistent padding.

## Notes:
- Check the application's console output for any errors, "FIXME" messages, or unexpected print statements (e.g., "CreateDocumentDialog cancelled.") during the tests.
- Verify that data entered (client name, contact details, product details) is correctly saved and reflected in the application where applicable (e.g., opening the client tab and checking its sub-tabs).
- The test plan mentions "Gestion des Contacts" for ContactDialog title from the original prompt, but the implementation was corrected to "Ajouter Contact" / "Modifier Contact". The test case reflects the corrected version ("Ajouter Contact").
```
