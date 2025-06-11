"""
NLU Controller for the Mobile Application.

This module takes the structured output from the NLU handler and translates it
into specific action commands that the UI layer can understand and execute.
It acts as a bridge between natural language understanding and UI interactions.
"""
from typing import Dict, Any

def process_nlu_result(nlu_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes the NLU data and converts it into a UI-consumable action dictionary.

    Args:
        nlu_data: A dictionary containing 'intent' and 'entities' as output
                  from nlu_handler.parse_command().
                  Example: {"intent": "ADD_PRODUCT", "entities": {"product_name": "Gadget", "quantity": 2}}

    Returns:
        A dictionary representing the action to be taken by the UI.
        Examples:
            {"action_type": "TRIGGER_PDF_GENERATION"}
            {"action_type": "ADD_UI_PRODUCT", "product_name": "Gadget", "quantity": 2}
            {"action_type": "NLU_ERROR", "message": "Sorry, I didn't understand."}
    """
    if not nlu_data or 'intent' not in nlu_data:
        return {"action_type": "NLU_ERROR", "message": "Sorry, I didn't understand that command (invalid NLU data)."}

    intent = nlu_data.get('intent')
    entities = nlu_data.get('entities', {})

    if intent == "GENERATE_PDF":
        return {"action_type": "TRIGGER_PDF_GENERATION"}

    elif intent == "EMAIL_PDF":
        recipient = entities.get("recipient")
        subject = entities.get("subject")
        return {"action_type": "TRIGGER_EMAIL_SENDING", "recipient": recipient, "subject": subject}

    elif intent == "ADD_PRODUCT":
        product_name = entities.get("product_name")
        if product_name:
            quantity = entities.get("quantity", 1) # Default to 1 if not specified
            return {"action_type": "ADD_UI_PRODUCT", "product_name": product_name, "quantity": quantity}
        else:
            return {"action_type": "NLU_ERROR", "message": "Please specify which product to add and optionally the quantity (e.g., 'add 3 Super Gadgets')."}

    elif intent == "SELECT_LANGUAGE":
        language_name = entities.get("language_name")
        if language_name:
            return {"action_type": "UPDATE_UI_LANGUAGE", "language_name": language_name}
        else:
            # This case might occur if NLU recognized "language" but not a specific one.
            return {"action_type": "NLU_ERROR", "message": "Please specify which language (e.g., 'set language to French')."}

    elif intent == "SELECT_COUNTRY":
        country_name = entities.get("country_name")
        if country_name:
            return {"action_type": "UPDATE_UI_COUNTRY", "country_name": country_name}
        else:
            return {"action_type": "NLU_ERROR", "message": "Please specify which country (e.g., 'change country to Germany')."}

    elif intent == "SELECT_TEMPLATE":
        template_name = entities.get("template_name")
        if template_name:
            return {"action_type": "UPDATE_UI_TEMPLATE", "template_name": template_name}
        else:
            return {"action_type": "NLU_ERROR", "message": "Please specify which template (e.g., 'select modern template')."}

    elif intent == "HELP":
        help_message = (
            "You can ask me to:\n"
            "- Generate PDF (e.g., 'create invoice')\n"
            "- Email PDF (e.g., 'send PDF to name@example.com subject Hello')\n"
            "- Display PDF (e.g., 'show the PDF')\n"
            "- Add a product (e.g., 'add 2 Super Gadget' or 'add Super Gadget quantity 2')\n"
            "- Select language (e.g., 'use French')\n"
            "- Select country (e.g., 'set country to USA')\n"
            "- Select template (e.g., 'choose classic design')"
        )
        return {"action_type": "DISPLAY_NLU_HELP", "message": help_message}

    elif intent == "DISPLAY_PDF":
        return {"action_type": "TRIGGER_PDF_DISPLAY"}

    elif intent == "UNKNOWN":
        return {"action_type": "NLU_ERROR", "message": "Sorry, I didn't understand that command. Try 'help' for options."}

    else: # Fallback for any other recognized but unhandled intents
        return {"action_type": "NLU_ERROR", "message": f"I understood the intent '{intent}', but I can't do that yet."}

if __name__ == '__main__':
    # Test cases to demonstrate functionality
    test_nlu_results = [
        {"intent": "GENERATE_PDF", "entities": {}},
        {"intent": "EMAIL_PDF", "entities": {}},
        {"intent": "EMAIL_PDF", "entities": {"recipient": "test@example.com"}},
        {"intent": "EMAIL_PDF", "entities": {"subject": "My Report"}},
        {"intent": "EMAIL_PDF", "entities": {"recipient": "another@example.com", "subject": "Project Docs"}},
        {"intent": "ADD_PRODUCT", "entities": {"product_name": "Super Gadget", "quantity": 3}},
        {"intent": "ADD_PRODUCT", "entities": {"product_name": "Awesome Widget"}}, # quantity defaults to 1
        {"intent": "ADD_PRODUCT", "entities": {}}, # Missing product_name
        {"intent": "SELECT_LANGUAGE", "entities": {"language_name": "French"}},
        {"intent": "SELECT_LANGUAGE", "entities": {}}, # Missing language_name
        {"intent": "SELECT_COUNTRY", "entities": {"country_name": "Germany"}},
        {"intent": "SELECT_COUNTRY", "entities": {}}, # Missing country_name
        {"intent": "SELECT_TEMPLATE", "entities": {"template_name": "Modern"}},
        {"intent": "SELECT_TEMPLATE", "entities": {}}, # Missing template_name
        {"intent": "HELP", "entities": {}},
        {"intent": "DISPLAY_PDF", "entities": {}},
        {"intent": "UNKNOWN", "entities": {}},
        {"intent": "SOME_OTHER_INTENT", "entities": {}}, # Unhandled intent
        None, # Invalid NLU data
        {},   # Invalid NLU data (missing intent)
    ]

    print("Testing nlu_controller.process_nlu_result:\n")
    for nlu_result in test_nlu_results:
        action = process_nlu_result(nlu_result)
        print(f"NLU Input: {nlu_result}")
        print(f"Action Output: {action}\n")

    print("Specific test for ADD_PRODUCT with only quantity (should be an error):")
    test_add_qty_only = {"intent": "ADD_PRODUCT", "entities": {"quantity": 5}}
    action = process_nlu_result(test_add_qty_only)
    print(f"NLU Input: {test_add_qty_only}")
    print(f"Action Output: {action}\n")

    print("Specific test for SELECT_LANGUAGE with partial match (e.g. NLU returned intent but no entity):")
    test_lang_no_entity = {"intent": "SELECT_LANGUAGE", "entities": {}}
    action = process_nlu_result(test_lang_no_entity)
    print(f"NLU Input: {test_lang_no_entity}")
    print(f"Action Output: {action}\n")
