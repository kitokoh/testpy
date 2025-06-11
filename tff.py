import os
import requests

def download_fonts():
    os.makedirs("fonts", exist_ok=True)

    font_urls = {
        # Polices similaires gratuites (remplace Arial/Showcard Gothic si tu ne peux pas distribuer Arial directement)
        "arial.ttf": "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf",
        "arialbd.ttf": "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf",
        "showg.ttf": "https://github.com/google/fonts/raw/main/ofl/bangers/Bangers-Regular.ttf",
        "sitka.ttf": "https://github.com/google/fonts/raw/main/ofl/merriweather/Merriweather-Regular.ttf",  # Alternative libre à Sitka
        "sitkabd.ttf": "https://github.com/google/fonts/raw/main/ofl/merriweather/Merriweather-Bold.ttf",
    }

    for filename, url in font_urls.items():
        path = os.path.join("fonts", filename)
        if os.path.exists(path):
            print(f"{filename} existe déjà. Ignoré.")
            continue

        try:
            print(f"Téléchargement de {filename}...")
            response = requests.get(url)
            response.raise_for_status()
            with open(path, "wb") as f:
                f.write(response.content)
            print(f"{filename} téléchargé avec succès.")
        except Exception as e:
            print(f"Erreur lors du téléchargement de {filename}: {str(e)}")

if __name__ == "__main__":
    download_fonts()
