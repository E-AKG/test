import os
import time
import json
import requests

# === Konfiguration laden ===
with open("config.json") as f:
    config = json.load(f)

API_KEY = config["api_key"]
workspace_mapping = config["workspace_mapping"]
ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt"]

# === Bereits verarbeitete Dateien merken ===
seen_files = set()

# === Datei hochladen ===
def upload_file(api_key, workspace_slug, file_path):
    url = f"http://localhost:3001/api/v1/document/upload/{workspace_slug}"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(url, headers=headers, files=files)

        if response.status_code == 200:
            print(f"✅ Hochgeladen: {file_path} → Workspace '{workspace_slug}'")
            file_name = os.path.basename(file_path)
            move_to_workspace_folder(api_key, file_name, workspace_slug)
        else:
            print(f"❌ Upload-Fehler ({response.status_code}) bei {file_path}: {response.text}")
    except Exception as e:
        print(f"❌ Ausnahme beim Hochladen von {file_path}: {e}")

# === Datei in Ordner verschieben ===
def move_to_workspace_folder(api_key, file_name, workspace_slug):
    url = "http://localhost:3001/api/v1/document/move-files"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "files": [
            {
                "from": f"{workspace_slug}/{file_name}",
                "to": f"folder/{workspace_slug}/{file_name}"
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"📂 Verschoben: {file_name} → folder/{workspace_slug}")
        else:
            error_msg = response.json().get("message", "Unbekannter Fehler")
            print(f"⚠️ Fehler beim Verschieben von {file_name}: {response.status_code} - {error_msg}")
    except Exception as e:
        print(f"❌ Ausnahme beim Verschieben von {file_name}: {e}")

# === Ordner überwachen und hochladen ===
def scan_and_upload():
    for mapping in workspace_mapping:
        for folder in mapping["folders"]:
            abs_folder = os.path.abspath(folder)
            if not os.path.exists(abs_folder):
                print(f"⚠️ Ordner nicht gefunden: {abs_folder}")
                continue

            for root, dirs, files in os.walk(abs_folder):
                for file in files:
                    if not any(file.lower().endswith(ext) for ext in ACCEPTED_EXTENSIONS):
                        continue

                    full_path = os.path.join(root, file)
                    if full_path in seen_files:
                        continue

                    for workspace_slug in mapping["workspace_slugs"]:
                        upload_file(API_KEY, workspace_slug, full_path)

                    seen_files.add(full_path)

# === Hauptschleife ===
if __name__ == "__main__":
    print("🚀 Dokumenten-Watcher läuft... Änderungen werden alle 15 Sekunden verarbeitet.")
    while True:
        scan_and_upload()
        time.sleep(15)