# Manual Test Plan: New Client Workflow & UI Enhancements

## Objective:
To verify the correct functionality of the sequential dialogs (Contact, Product, Create Document) after a new client is created, including data persistence for contacts and products, product name suggestions/autofill, multi-line product entry, and to check the UI/UX enhancements made to these dialogs. Also, to verify the temporary disablement of the product edit feature.

## Prerequisites:
- The application is running.
- Ensure `main.py` is the entry point.
- Database (`app_data.db`) is initialized and accessible.
- Optional: For product suggestion testing (Test Case 6), ensure some products like "Laptop Pro", "Standard Mouse", "USB Hub" exist in the `Products` table in the database.

## Test Cases:

### Test Case 1: Full Successful Workflow (Multi-Line Products, Data Persistence, TypeError Fix)
1.  **Action:** Launch the application.
2.  **Action:** In the 'Ajouter un Nouveau Client' form, fill in all required fields (Nom Client, Pays, ID Projet) and any optional fields with unique data for this test run (e.g., Client: "MultiProd Client", ID Projet: "TC1-Multi").
3.  **Action:** Click the "Créer Client" button.
4.  **Expected Result:**
    *   The "Ajouter Contact" dialog appears.
    *   Verify its title is "Ajouter Contact".
    *   Verify UI (header, icons, padding, button styles, button frame).
5.  **Action:** Fill in contact details (e.g., Name: "Contact Multi1", Email: "tc1multi@example.com", Mark as "Contact principal"). Click "OK".
6.  **Expected Result:**
    *   The "Ajouter Produits au Client" dialog appears (new title for multi-line).
    *   Verify UI (header "Ajouter Lignes de Produits", input group, "Add Product to List" button, product table, "Remove Selected Product" button, overall total label, OK/Cancel button frame).
7.  **Action (Add Product 1):**
    *   In "Détails de la Ligne de Produit Actuelle" group:
        *   Name: "Laptop X1"
        *   Quantity: 1, Unit Price: 1200.00.
    *   **Expected:** "Total Ligne Actuelle" updates to "€ 1200.00".
    *   Click "Ajouter Produit à la Liste".
    *   **Expected:** "Laptop X1" appears as a row in the products table. Input fields clear. "Total Général" updates to "€ 1200.00".
8.  **Action (Add Product 2 - Test TypeError Fix behavior):**
    *   Name: "Mousepad Basic"
    *   Quantity: Clear it (or set to 0), then type 5. Unit Price: Clear it (or set to 0), then type 10.00.
    *   **Expected:** "Total Ligne Actuelle" updates correctly as values are typed (e.g., shows "€ 0.00" if a field is temporarily empty/zero, then "€ 50.00"). No `TypeError` should occur.
    *   Click "Ajouter Produit à la Liste".
    *   **Expected:** "Mousepad Basic" appears in the table. "Total Général" updates to "€ 1250.00".
9.  **Action:** Click "OK" on the "Ajouter Produits au Client" dialog.
10. **Expected Result:**
    *   The "Créer des Documents" dialog appears. Verify its UI elements as per Test Case 5.
11. **Action:** Select at least one document template and a language. Click "Créer Documents".
12. **Expected Result:**
    *   A success message for document creation appears.
    *   The main application "Client Créé" success message appears.
    *   The "MultiProd Client" tab opens. Client list and statistics update.
13. **Verification (Data Persistence & Display):**
    *   Navigate to the "MultiProd Client" tab.
    *   **Contacts Tab:** Verify "Contact Multi1" is listed and primary.
    *   **Produits Tab:** Verify "Laptop X1" (Qty: 1, Price: €1200.00, Total: €1200.00) AND "Mousepad Basic" (Qty: 5, Price: €10.00, Total: €50.00) are listed with correct details.
    *   **Documents Tab:** Verify created documents.
    *   **Client Folder:** Check for created document files.

### Test Case 2: Cancellation at Contact Dialog
1.  **Action:** Launch the application.
2.  **Action:** Fill in new client details (e.g., "Client Cancel Contact", select Pays, ID Projet "TC2") and click "Créer Client".
3.  **Expected Result:** The "Ajouter Contact" dialog appears.
4.  **Action:** Click "Annuler" or close the "Ajouter Contact" dialog.
5.  **Expected Result:**
    *   The "Ajouter Produits au Client" dialog should NOT appear.
    *   The "Créer des Documents" dialog should NOT appear.
    *   The main application "Client Créé" success message for "Client Cancel Contact".
    *   New client tab opens. Client is in list.
6.  **Verification:** Open client tab. "Contacts", "Produits", "Documents" sub-tabs should be empty or not contain items from this workflow.

### Test Case 3: Cancellation at Product Dialog
1.  **Action:** Launch the application.
2.  **Action:** Fill in new client details (e.g., "Client Cancel ProdList", select Pays, ID Projet "TC3") and click "Créer Client".
3.  **Action:** In "Ajouter Contact" dialog, add a contact (e.g., "Contact For TC3") and click "OK".
4.  **Expected Result:** "Ajouter Produits au Client" dialog appears.
5.  **Action (Optional):** Add one product line to the table using "Ajouter Produit à la Liste".
6.  **Action:** Click "Annuler" or close the "Ajouter Produits au Client" dialog.
7.  **Expected Result:**
    *   "Créer des Documents" dialog should NOT appear.
    *   Main "Client Créé" success message appears.
    *   New client tab opens.
8.  **Verification:** Open client tab.
    *   **Contacts Tab:** "Contact For TC3" is listed.
    *   **Produits Tab:** Should be empty (no products saved from the cancelled dialog).
    *   **Documents Tab:** Should be empty.

### Test Case 4: Cancellation at Create Document Dialog
1.  **Action:** Launch the application.
2.  **Action:** Fill in new client details (e.g., "Client Cancel Docs", select Pays, ID Projet "TC4") and click "Créer Client".
3.  **Action:** In "Ajouter Contact" dialog, add "Contact For TC4", click "OK".
4.  **Action:** In "Ajouter Produits au Client" dialog:
    *   Add "Product X" (Qty 1, Price 100). Click "Ajouter Produit à la Liste".
    *   Click "OK".
5.  **Expected Result:** "Créer des Documents" dialog appears.
6.  **Action:** Click "Annuler" or close the "Créer des Documents" dialog.
7.  **Expected Result:**
    *   Main "Client Créé" success message.
    *   New client tab opens.
8.  **Verification:** Open client tab.
    *   **Contacts Tab:** "Contact For TC4" is listed.
    *   **Produits Tab:** "Product X" is listed with correct details.
    *   **Documents Tab:** Should be empty.

### Test Case 5: Dialog UI Verification (Comprehensive)
1.  **Action:** Trigger each dialog in the sequence (as per Test Case 1 steps, stopping at each dialog to verify).
2.  **Verification for `ContactDialog` ("Ajouter Contact"):**
    *   **Header:** Present, styled, text "Ajouter Nouveau Contact".
    *   **Window Title:** "Ajouter Contact".
    *   **Icons:** Present for "Nom complet:", "Email:", "Téléphone:", "Poste:", "Principal:".
    *   **Layout & Padding:** Adequate spacing. Inputs (QLineEdit, QCheckBox) have padding.
    *   **Primary Contact Cue:** Checking "Contact principal" changes "Nom complet" background; unchecking reverts it.
    *   **Button Grouping:** OK/Cancel buttons within a bottom frame with a top border.
    *   **Button Styling:** "OK" button green with icon. "Annuler" button standard with icon.
3.  **Verification for `ProductDialog` ("Ajouter Produits au Client"):**
    *   **Header:** Present, styled, text "Ajouter Lignes de Produits".
    *   **Window Title:** "Ajouter Produits au Client".
    *   **Input Group:** "Détails de la Ligne de Produit Actuelle" group box is present.
    *   **Icons (within group):** Present for "Nom du Produit:", "Quantité:", "Prix Unitaire:".
    *   **Current Line Total:** `current_line_total_label` updates as quantity/price change.
    *   **"Add Product to List" Button:** Styled as a primary action button (e.g., blue).
    *   **Products Table:** Headers are correct. Items align correctly (text left, numbers right).
    *   **Overall Total Label:** Prominently styled and updates correctly.
    *   **Button Grouping (OK/Cancel):** Within a bottom frame with a top border.
    *   **Button Styling:** "OK" (green), "Annuler" (standard), with icons.
4.  **Verification for `CreateDocumentDialog` ("Créer des Documents"):**
    *   **Header:** Present, styled, text "Sélectionner Documents à Créer".
    *   **Window Title:** "Créer des Documents".
    *   **Icons:** Present for "Langue:" and "Sélectionnez les documents à créer:".
    *   **List Hover Effect:** Items in `templates_list` change background on hover.
    *   **Button Grouping:** Buttons in a bottom frame.
    *   **Button Styling:** "Créer Documents" (green), "Annuler" (standard), with icons.

### Test Case 6: Multi-Line Product Addition and Removal
1.  **Action:** Navigate to `ProductDialog` (either via new client workflow or by clicking "➕ Produit" in an existing client's `ClientWidget` - adapt based on which flow is easier to trigger for this isolated test).
2.  **Action (Add Product 1):** Name: "P-Line1", Qty: 1, Price: 10. Click "Ajouter Produit à la Liste".
3.  **Expected:** "P-Line1" in table. Overall Total: € 10.00. Inputs clear.
4.  **Action (Add Product 2):** Name: "P-Line2", Qty: 2, Price: 5. Click "Ajouter Produit à la Liste".
5.  **Expected:** "P-Line2" in table. Overall Total: € 20.00.
6.  **Action (Add Product 3):** Name: "P-Line3", Qty: 1, Price: 30. Click "Ajouter Produit à la Liste".
7.  **Expected:** "P-Line3" in table. Overall Total: € 50.00.
8.  **Action (Remove Product 2):** Select "P-Line2" in the table. Click "Supprimer Produit Sélectionné".
9.  **Expected:** "P-Line2" is removed. Overall Total updates to € 40.00.
10. **Action:** Click "OK".
11. **Expected (if part of client creation):** Workflow proceeds. If testing via `ClientWidget.add_product`, the product list in `ClientWidget` updates to show "P-Line1" and "P-Line3" only.

### Test Case 7: Multi-Line Product - Empty Line Attempt
1.  **Action:** Navigate to `ProductDialog`.
2.  **Action:** Leave "Nom du Produit" empty. Click "Ajouter Produit à la Liste".
3.  **Expected:** Warning message "Le nom du produit est requis." appears. No line added to table.
4.  **Action:** Enter Name "P-NoQty", leave Quantity as 0. Click "Ajouter Produit à la Liste".
5.  **Expected:** Warning message "La quantité doit être supérieure à zéro." appears. No line added.

### Test Case 8: Product Suggestion and Autofill
1.  **Prerequisite:** Ensure products like "Laptop Pro X", "Standard USB Mouse", "Advanced Keyboard" exist in the database (add them manually via a DB tool if necessary for a clean test, or ensure previous tests created them).
2.  **Action:** Navigate to `ProductDialog`.
3.  **Action (Product Name Input):** In the "Nom du Produit" field, type "Lap".
4.  **Expected:** A suggestion list appears below the input, containing "Laptop Pro X".
5.  **Action:** Select "Laptop Pro X" from the suggestion list (e.g., using arrow keys and Enter, or mouse click).
6.  **Expected:**
    *   "Nom du Produit" field is now "Laptop Pro X".
    *   "Description" field is autofilled with the description of "Laptop Pro X".
    *   "Prix Unitaire" field is autofilled with the `base_unit_price` of "Laptop Pro X".
    *   "Total Ligne Actuelle" updates based on the autofilled price and current quantity (which might be 0 initially).
7.  **Action:** Change quantity to 2. Click "Ajouter Produit à la Liste".
8.  **Action:** Click "OK".
9.  **Expected (if part of client creation/ClientWidget):** The product "Laptop Pro X" with its original description and unit price (but quantity 2) is saved.

### Test Case 9: Product Edit Disablement
1.  **Prerequisite:** A client with at least one product exists (e.g., from Test Case 1).
2.  **Action:** Open the application and navigate to the `ClientWidget` for the client with products.
3.  **Action:** Go to the "Produits" tab. Select a product from the table.
4.  **Action:** Click the "✏️ Produit" (Edit Product) button.
5.  **Expected Result:**
    *   A `QMessageBox` appears with a title like "Fonctionnalité en cours de révision".
    *   The message body indicates that product editing is temporarily disabled or under review.
    *   The `ProductDialog` (in its multi-add form) does NOT open.

## Notes:
- Check the application's console output for any errors, "FIXME" messages, or unexpected print statements (e.g., "CreateDocumentDialog cancelled.") during the tests.
- The "Modifier Contact" and "Modifier Produit" titles for `ContactDialog` and `ProductDialog` respectively are primarily for when these dialogs are called from `ClientWidget` to edit existing data, not during this new client creation flow. The `ProductDialog` title is now consistently "Ajouter Produits au Client" as its edit functionality is disabled.
- Ensure that if a dialog is cancelled, no data from that dialog or subsequent dialogs in the sequence is saved for the client.
```