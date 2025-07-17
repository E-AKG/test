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

# === Datei hochladen und automatisch den Workspace zuordnen ===
def upload_file_to_workspaces(api_key, file_path, workspace_slugs):
    url = "http://localhost:3001/api/v1/document/upload"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    workspace_list = ",".join(workspace_slugs)

    try:
        with open(file_path, "rb") as f:
            files = {
                "file": f
            }
            data = {
                "addToWorkspaces": workspace_list
            }

            response = requests.post(url, headers=headers, files=files, data=data)

        if response.status_code == 200:
            print(f"✅ Hochgeladen: {file_path} → Workspaces: {workspace_list}")
        else:
            print(f"❌ Upload-Fehler: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Ausnahme beim Upload von {file_path}: {e}")

# === Ordner scannen und neue Dateien hochladen ===
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

                    upload_file_to_workspaces(API_KEY, full_path, mapping["workspace_slugs"])
                    seen_files.add(full_path)

# === Hauptschleife ===
if __name__ == "__main__":
    print("🚀 Dokumenten-Watcher läuft... Änderungen werden alle 15 Sekunden verarbeitet.")
    while True:
        scan_and_upload()
        time.sleep(15)
