import speech_recognition as sr
import logging
import re

class VoiceInputService:
    def __init__(self):
        """
        Initializes the voice input service, recognizer, microphone, and logger.
        """
        self.recognizer = sr.Recognizer()
        self.microphone = None  # Initialize as None

        # Configure logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        # Create a console handler if no handlers are present
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        try:
            # Attempt to import PyAudio first to give a more specific error if it's the root cause
            import pyaudio
            self.microphone = sr.Microphone()
            self.logger.info("Microphone initialized successfully.")
        except ImportError:
            self.microphone = None # Ensure microphone is None
            self.logger.warning("PyAudio library not found. Microphone input will not be available. Please install PyAudio.")
        except AttributeError as ae: # speech_recognition can raise AttributeError if PyAudio is missing during Microphone class definition
            self.microphone = None
            if 'pyaudio' in str(ae).lower():
                self.logger.warning(f"Could not initialize microphone due to a PyAudio-related issue (AttributeError): {ae}. Ensure PyAudio is correctly installed. Microphone input will be disabled.")
            else:
                self.logger.warning(f"Could not initialize microphone (AttributeError): {ae}. Microphone input will be disabled.")
        except OSError as oe: # OSError can be raised by PyAudio if it can't find audio devices or PortAudio is misconfigured
            self.microphone = None
            self.logger.warning(f"Could not initialize microphone (OSError): {oe}. This might be due to no microphone being connected, or an issue with system audio libraries like PortAudio. Microphone input will be disabled.")
        except Exception as e: # Catch-all for other unexpected errors during microphone initialization
            self.microphone = None # Ensure microphone is None
            self.logger.warning(f"An unexpected error occurred while initializing microphone: {e}. Speech recognition will fail if attempted. Microphone input will be disabled.")
            # This allows the service to be instantiated for NLP tasks even if no mic is present.

    def recognize_speech(self, language="fr-FR"):
        """
        Captures audio from the microphone, recognizes speech, and returns the text.

        Args:
            language (str): The language for speech recognition (e.g., "fr-FR", "en-US").

        Returns:
            dict: A dictionary containing:
                  - "success" (bool): True if recognition was successful, False otherwise.
                  - "text" (str, optional): The recognized text if successful.
                  - "error" (str, optional): An error code if not successful
                                            ('unknown_value', 'request_error', 'unexpected_error', 'microphone_error').
                  - "message" (str, optional): A descriptive error message if not successful.
        """
        if not self.microphone:
            self.logger.error("Microphone not initialized. Cannot recognize speech.")
            return {"success": False, "error": "microphone_error", "message": "Microphone not available or not initialized."}

        with self.microphone as source:
            self.logger.info("Ajustement au bruit ambiant pendant 1 seconde...")
            # Notify user: "Adjusting for ambient noise..." (can be done via UI callback)
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            except Exception as e:
                self.logger.error(f"Erreur pendant adjust_for_ambient_noise: {e}")
                # It might be possible that the microphone is not available.
                # sr.Microphone() itself can raise exceptions if no mic is found,
                # but adjust_for_ambient_noise can also fail.
                return {"success": False, "error": "microphone_error", "message": f"Impossible d'ajuster le bruit ambiant. Problème de microphone? {str(e)}"}

            self.logger.info("En écoute...")
            # Notify user: "Listening..." (can be done via UI callback)
            try:
                audio = self.recognizer.listen(source)
            except Exception as e:
                self.logger.error(f"Erreur pendant l'écoute: {e}")
                return {"success": False, "error": "listen_error", "message": f"Impossible d'écouter le microphone. {str(e)}"}

            self.logger.info("Traitement de la parole...")
            # Notify user: "Processing speech..." (can be done via UI callback)

            try:
                text = self.recognizer.recognize_google(audio, language=language)
                self.logger.info(f"Texte reconnu: {text}")
                return {"success": True, "text": text}
            except sr.UnknownValueError:
                self.logger.warning("L'API Google Web Speech n'a pas pu comprendre l'audio.")
                return {"success": False, "error": "unknown_value", "message": "Impossible de comprendre l'audio"}
            except sr.RequestError as e:
                self.logger.error(f"Impossible de demander des résultats au service Google Web Speech API; {e}")
                return {"success": False, "error": "request_error", "message": f"Service API indisponible ou requête échouée: {e}"}
            except Exception as e:
                self.logger.error(f"Une erreur inattendue est survenue lors de la reconnaissance vocale: {e}", exc_info=True)
                return {"success": False, "error": "unexpected_error", "message": str(e)}

    def extract_client_info(self, text: str) -> dict:
        """
        Extracts client information from a given text using regex patterns.

        Args:
            text (str): The text from which to extract information.

        Returns:
            dict: A dictionary containing extracted client information.
                  Keys: 'client_name', 'company_name', 'primary_need_description',
                        'country_name', 'city_name', 'project_identifier'.
        """
        client_info = {}

        # Define regex patterns - designed to be non-greedy and handle common sentence structures
        # Using non-capturing groups (?:...) for keywords and capturing groups (.+?) for the values.
        # The lookahead (?=\s+(?:et|pour|alors|concernant|venant de|de la ville de)|,|$) helps to stop capturing before conjunctions or end of sentence.

        patterns = {
            'client_name': r"(?:le client s'appelle|le nom du client est|le client est|nom client|client name is|client)\s+(.+?)(?=\s+(?:et|pour la société|pour|alors|concernant|venant de|de la ville de)|,|\.|$)",
            'company_name': r"(?:la société est|sa société est|la compagnie est|l'entreprise est|société|compagnie|entreprise|company is|company)\s+(.+?)(?=\s+(?:et|pour|alors|concernant|venant de|de la ville de)|,|\.|$)",
            'primary_need_description': r"(?:son besoin est|il a besoin de|le besoin est|besoin de|besoin|needs|need is|il cherche à|recherche)\s+(.+?)(?=\s+(?:et|pour|alors|concernant|venant de|de la ville de|pour le projet)|,|\.|$)",
            'country_name': r"(?:il vient de|son pays est|pays d'origine|pays|country is|country)\s+(.+?)(?=\s+(?:et|pour|alors|concernant|de la ville de)|,|\.|$)",
            'city_name': r"(?:la ville est|sa ville est|ville de|ville|city is|city)\s+(.+?)(?=\s+(?:et|pour|alors|concernant|pour le projet)|,|\.|$)",
            'project_identifier': r"(?:le projet est|son projet est|identifiant du projet|projet|project ID|project identifier|project)\s+(.+?)(?=\s+(?:et|pour|alors|concernant)|,|\.|$)"
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract the first capturing group, which is the desired value
                value = match.group(1).strip()
                # Further clean up if value ends with a common conjunction that wasn't caught by lookahead (less likely now)
                common_conjunctions = [" et", " pour", " alors", " concernant"]
                for conj in common_conjunctions:
                    if value.endswith(conj):
                        value = value[:-len(conj)].strip()
                client_info[key] = value

        self.logger.info(f"Extracted client info: {client_info}")
        return client_info

if __name__ == '__main__':
    # Basic configuration for logging to console for the test
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    service = VoiceInputService()

    # --- Test NLP extraction logic with hardcoded text ---
    test_sentences = [
        "Le client s'appelle Jean Dupont et sa société est Dupont et Fils. Il vient de France, ville Paris. Son besoin est une consultation pour le projet Alpha123.",
        "Nom client: Marie Curie, compagnie: Institut du Radium, besoin: recherche sur la radioactivité, pays: Pologne, ville: Varsovie, projet: Becquerel-001.",
        "Client: Alain Bernard. Il a besoin de coaching sportif. Il vient de Belgique et sa ville est Bruxelles. Le projet est JO2024.",
        "Le client est Société Générale et ils ont besoin d'une nouvelle plateforme de trading pour le projet SGTradeNG. La société est basée en France, ville de Paris La Défense.", # Company as client name
        "Je voudrais enregistrer un nouveau client. Son nom est Pierre Martin. Il travaille pour la société Tech Solutions Inc. Il a besoin d'une migration cloud. Il est en Suisse, ville Genève. L'identifiant du projet est CloudMig24.",
        "Client name is John Doe, company is Doe Exports, country USA, city New York. He needs a new website for project WebRevamp." # English example
    ]

    for i, test_text in enumerate(test_sentences):
        print(f"\n--- Test Case {i+1} ---")
        logging.info(f"Input text: {test_text}")
        extracted_info = service.extract_client_info(test_text)
        print(f"Extracted info: {extracted_info}")
        # You can add assertions here if you were using a test framework
        # e.g., assert extracted_info.get('client_name') == "Jean Dupont" for the first case

    # --- Test speech recognition (will likely fail in sandbox due to no microphone) ---
    print("\n--- Attempting Speech Recognition (expect failure in sandbox) ---")
    try:
        mic_names = sr.Microphone.list_microphone_names()
        if mic_names:
            logging.info(f"Available microphones: {mic_names}")
        else:
            logging.warning("No microphones found by sr.Microphone.list_microphone_names(). This is expected in a sandbox.")
    except Exception as e:
        logging.error(f"Could not list microphones (this often indicates PyAudio/PortAudio issues or no mics, expected in sandbox): {e}")

    logging.info("Attempting to recognize speech (French)... (This part will likely fail or timeout in a sandbox)")
    # Set a short timeout for listen in sandbox environments to avoid hanging too long
    # This is a parameter of recognizer.listen(source, timeout=X)
    # However, the current structure calls listen without timeout.
    # For now, we just accept it might hang or fail quickly.

    result = service.recognize_speech(language="fr-FR")

    if result["success"]:
        print(f"Success! Recognized text: {result['text']}")
        extracted_info_speech = service.extract_client_info(result['text'])
        print(f"Extracted info from speech: {extracted_info_speech}")
    else:
        print(f"Speech recognition failed. Error: {result.get('error')}, Message: {result.get('message')}")
        print("This failure is expected if no microphone is available or if running in a restricted environment.")
