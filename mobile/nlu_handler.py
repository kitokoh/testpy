import re

# Predefined lists for matching
SUPPORTED_LANGUAGES = ["english", "french", "spanish", "german", "italian", "portuguese"]
SUPPORTED_COUNTRIES = ["usa", "canada", "uk", "france", "germany", "spain", "italy"] # Example countries
SUPPORTED_TEMPLATES = ["modern", "classic", "compact"]


def parse_command(text: str) -> dict:
    """
    Parses a text command to identify an intent and extract entities.

    Examples of commands it's designed to understand:
        - "generate PDF" -> {"intent": "GENERATE_PDF", "entities": {}}
        - "create the invoice" -> {"intent": "GENERATE_PDF", "entities": {}}
        - "email the PDF" -> {"intent": "EMAIL_PDF", "entities": {}}
        - "send the invoice to test@example.com" -> {"intent": "EMAIL_PDF", "entities": {"recipient": "test@example.com"}}
        - "email the document to user1@example.com and user2@example.com with subject Hello there" -> {"intent": "EMAIL_PDF", "entities": {"recipient": "user1@example.com and user2@example.com", "subject": "Hello there"}}
        - "send invoice subject Important" -> {"intent": "EMAIL_PDF", "entities": {"subject": "Important"}}
        - "add 3 Super Gadget to the document" -> {"intent": "ADD_PRODUCT", "entities": {"product_name": "Super Gadget", "quantity": 3}}
        - "add Super Gadget to the document" -> {"intent": "ADD_PRODUCT", "entities": {"product_name": "Super Gadget", "quantity": 1}}
        - "put 5 Awesome Widget" -> {"intent": "ADD_PRODUCT", "entities": {"product_name": "Awesome Widget", "quantity": 5}}
        - "set language to French" -> {"intent": "SELECT_LANGUAGE", "entities": {"language_name": "French"}}
        - "use spanish language" -> {"intent": "SELECT_LANGUAGE", "entities": {"language_name": "spanish"}}
        - "change country to Germany" -> {"intent": "SELECT_COUNTRY", "entities": {"country_name": "Germany"}}
        - "set country usa" -> {"intent": "SELECT_COUNTRY", "entities": {"country_name": "usa"}}
        - "select classic template" -> {"intent": "SELECT_TEMPLATE", "entities": {"template_name": "classic"}}
        - "use modern design" -> {"intent": "SELECT_TEMPLATE", "entities": {"template_name": "modern"}}
        - "what can I say" -> {"intent": "HELP", "entities": {}}
        - "help me" -> {"intent": "HELP", "entities": {}}

    Args:
        text: The input string command from the user.

    Returns:
        A dictionary containing the identified 'intent' and 'entities'.
        Returns {"intent": "UNKNOWN", "entities": {}} if the command is not understood.
    """
    text_lower = text.lower()
    intent = "UNKNOWN"
    entities = {}

    # Intent: GENERATE_PDF
    if ("generate" in text_lower and "pdf" in text_lower) or \
       ("create" in text_lower and ("invoice" in text_lower or "document" in text_lower or "pdf" in text_lower)):
        intent = "GENERATE_PDF"

    # Intent: EMAIL_PDF
    elif ("email" in text_lower and ("pdf" in text_lower or "invoice" in text_lower or "document" in text_lower)) or \
         ("send" in text_lower and ("invoice" in text_lower or "document" in text_lower or "pdf" in text_lower)):
        intent = "EMAIL_PDF"
        # Try to extract recipient: "to <email_address>" or just find emails.
        # Regex to find email addresses. This is a common, but not perfectly RFC-compliant pattern.
        email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"

        # Look for "to <emails>" pattern first.
        # This regex tries to capture one or more emails separated by 'and' or ',', after 'to'.
        recipient_match_to = re.search(r"to\s+((?:{0})(?:\s*(?:and|,)\s*{0})*)".format(email_pattern), text_lower)
        if recipient_match_to:
            entities["recipient"] = recipient_match_to.group(1)
        else:
            # Fallback: if "to" pattern not found, find all emails in the command.
            # This is more permissive and might pick up emails not intended as recipients if the command is phrased ambiguously.
            found_emails = re.findall(email_pattern, text_lower)
            if found_emails:
                # Avoid picking up emails if they are part of the command itself like "email test@example.com the ..."
                # This is a simple heuristic: if the command starts with "email <email>" or "send <email>",
                # it might be the command itself rather than a recipient if "to" was not used.
                # For simplicity, we'll take all found emails if "to" is not present.
                # More sophisticated logic would be needed to differentiate in complex phrasings.
                entities["recipient"] = ", ".join(found_emails)

        # Try to extract subject: "subject <text_for_subject>"
        # This will capture text until a new potential keyword like "to" (for recipient) or end of string.
        # It tries to avoid capturing a recipient email as part of the subject.
        subject_match = re.search(r"subject\s+([^,]+?)(?:\s+to\s+{0}|$|\s+send\s+to\s+{0}|$)".format(email_pattern), text_lower, re.IGNORECASE)
        if subject_match:
            subject_text = subject_match.group(1).strip()
            if subject_text and not re.fullmatch(email_pattern, subject_text): # Ensure subject is not just an email itself
                entities["subject"] = subject_text
            elif subject_text and "recipient" not in entities:
                # If the subject looks like an email and we haven't found a recipient yet via "to",
                # it's possible this email was meant as a recipient. This is heuristic.
                # For now, we prioritize "subject" keyword. If it's an email, it's a subject.
                 entities["subject"] = subject_text


    # Intent: ADD_PRODUCT
    # Pattern 1: cmd qty product_name (e.g., "add 3 apples")
    product_match_qty_first = re.search(r"(add|put)\s+(\d+)\s+([\w\s]+?)(?:\s+to\s+the\s+document|\s+to\s+invoice|\s*$)", text_lower)
    # Pattern 2: cmd product_name quantity qty (e.g., "add apples quantity 3")
    product_match_qty_last = re.search(r"(add|put)\s+([\w\s]+?)\s+quantity\s+(\d+)(?:\s+to\s+the\s+document|\s+to\s+invoice|\s*$)", text_lower)
    # Pattern 3: cmd product_name (e.g., "add apples")
    product_match_no_qty = re.search(r"(add|put)\s+([\w\s]+?)(?:\s+to\s+the\s+document|\s+to\s+invoice|\s*$)", text_lower)

    if product_match_qty_first:
        intent = "ADD_PRODUCT"
        quantity_str = product_match_qty_first.group(2)
        product_name = product_match_qty_first.group(3).strip()
        entities["product_name"] = product_name.title()
        entities["quantity"] = int(quantity_str) if quantity_str else 1
    elif product_match_qty_last:
        intent = "ADD_PRODUCT"
        product_name = product_match_qty_last.group(2).strip()
        quantity_str = product_match_qty_last.group(3)
        entities["product_name"] = product_name.title()
        entities["quantity"] = int(quantity_str) if quantity_str else 1
    elif product_match_no_qty: # Must be checked after specific qty patterns
        # Check if the general match isn't part of a more specific one already handled
        # This avoids "add 3 apples" being matched by this less specific regex too.
        # A simple way is to ensure the text doesn't contain "quantity" if this matches.
        # Or, ensure the product name derived doesn't end with " quantity <number>"
        potential_product_name = product_match_no_qty.group(2).strip()
        if not re.search(r"quantity\s+\d+$", potential_product_name): # Avoid double match with qty_last if it failed for other reasons
            # Also, ensure it's not capturing the quantity from "qty first" pattern as part of product name
            if not re.match(r"^\d+\s+", potential_product_name):
                intent = "ADD_PRODUCT"
                entities["product_name"] = potential_product_name.title()
                entities["quantity"] = 1 # Default quantity


    # Intent: SELECT_LANGUAGE
    elif ("language" in text_lower or "speak" in text_lower):
        for lang in SUPPORTED_LANGUAGES:
            if lang in text_lower:
                intent = "SELECT_LANGUAGE"
                entities["language_name"] = lang.capitalize()
                break
        if intent == "UNKNOWN" and "language" in text_lower: # If "language" was mentioned but not a specific one
            intent = "SELECT_LANGUAGE" # Allow to ask for language without specifying one yet


    # Intent: SELECT_COUNTRY
    elif "country" in text_lower:
        for country in SUPPORTED_COUNTRIES:
            if country in text_lower:
                intent = "SELECT_COUNTRY"
                entities["country_name"] = country.upper() # Or .title()
                break
        if intent == "UNKNOWN": # If "country" was mentioned but not a specific one
             intent = "SELECT_COUNTRY"


    # Intent: SELECT_TEMPLATE
    elif "template" in text_lower or "design" in text_lower or "layout" in text_lower:
        for template in SUPPORTED_TEMPLATES:
            if template in text_lower:
                intent = "SELECT_TEMPLATE"
                entities["template_name"] = template.capitalize()
                break
        if intent == "UNKNOWN": # If "template" or "design" was mentioned but not a specific one
            intent = "SELECT_TEMPLATE"

    # Intent: HELP
    elif "help" in text_lower or "what can i say" in text_lower or "options" in text_lower:
        intent = "HELP"

    # Intent: DISPLAY_PDF
    elif ("show" in text_lower and "pdf" in text_lower) or \
         ("display" in text_lower and ("document" in text_lower or "pdf" in text_lower or "invoice" in text_lower)) or \
         ("open" in text_lower and ("pdf" in text_lower or "document" in text_lower or "invoice" in text_lower)):
        intent = "DISPLAY_PDF"

    return {"intent": intent, "entities": entities}

if __name__ == '__main__':
    # Test cases
    commands = [
        "generate PDF",
        "create the invoice",
        "email the PDF",
        "send the invoice to client@example.com",
        "email the PDF to boss@work.com subject Weekly Report",
        "send document to alice@test.com and bob@test.com",
        "email invoice with subject Urgent Payment",
        "send the invoice to charlie@example.net with subject Final Invoice",
        "email pdf to dave@example.org subject Regarding Project X",
        "add 3 Super Gadget to the document",
        "add Super Gadget to the document",
        "put 5 Awesome Widget",
        "add 2 another item",
        "set language to French",
        "use spanish language",
        "speak in german",
        "change country to Germany",
        "set country usa",
        "select classic template",
        "use modern design",
        "what can I say",
        "help me",
        "show my options",
        "make a new document in italian", # Multiple intents, will pick first match by order
        "add 10 widgets and send it", # Multiple intents
        "show the pdf",
        "display the invoice",
        "open document"
    ]

    for cmd in commands:
        parsed = parse_command(cmd)
        print(f"Command: '{cmd}' -> Parsed: {parsed}")

    print("\nTesting edge cases and specific entity extraction:")
    print(parse_command("add 10 Ultra Boosters"))
    print(parse_command("add Mega Phone to the invoice"))
    print(parse_command("set language to portuguese, please"))
    print(parse_command("I want to use the compact template"))
    print(parse_command("change my country to UK"))
    print(parse_command("generate pdf and email it")) # will be generate
    print(parse_command("email and generate pdf")) # will be email
    print(parse_command("add product")) # Should ideally not match or ask for product name
                                     # Current: {'intent': 'ADD_PRODUCT', 'entities': {'product_name': 'Product', 'quantity': 1}} - needs refinement if this is an issue
    print(parse_command("set language")) #  {'intent': 'SELECT_LANGUAGE', 'entities': {}}
    print(parse_command("set country"))  #  {'intent': 'SELECT_COUNTRY', 'entities': {}}
    print(parse_command("select template")) # {'intent': 'SELECT_TEMPLATE', 'entities': {}}
