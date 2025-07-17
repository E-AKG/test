import os
import time
import json
import requests
import hashlib
import re

# === Konfiguration laden ===
with open("config.json") as f:
    config = json.load(f)

API_KEY = config["api_key"]
workspace_mapping = config["workspace_mapping"]
ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt"]

UPLOAD_TRACKER_FILE = "uploaded_files.json"

# === Bereits bekannte Dateien laden
if os.path.exists(UPLOAD_TRACKER_FILE):
    with open(UPLOAD_TRACKER_FILE, "r") as f:
        uploaded_files = json.load(f)
else:
    uploaded_files = {}

# === Hash berechnen
def get_file_hash(path):
    try:
        hasher = hashlib.md5()
        with open(path, "rb") as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Fehler beim Hashing: {path}: {e}")
        return None

# === Ist eine typische Kopie?
def is_probable_copy(filename):
    patterns = [r" - Kopie", r" - Copy", r"\(\d+\)", r"MacBook"]
    return any(re.search(p, filename, re.IGNORECASE) for p in patterns)

# === Ist temporäre oder gesperrte Datei?
def is_temporary_or_locked(filename):
    return (
        filename.startswith("~$") or
        filename.startswith("._") or
        filename.endswith(".tmp") or
        filename.endswith(".lock") or
        filename.startswith(".sb-")
    )

# === Datei hochladen
def upload_file_to_workspaces(api_key, file_path, workspace_slugs):
    url = "http://localhost:3001/api/v1/document/upload"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    workspace_list = ",".join(workspace_slugs)

    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"addToWorkspaces": workspace_list}
            response = requests.post(url, headers=headers, files=files, data=data)

        if response.status_code == 200:
            print(f"Hochgeladen: {file_path} → Workspaces: {workspace_list}")
        else:
            print(f"Upload-Fehler: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Ausnahme beim Upload von {file_path}: {e}")

# === Upload-Daten speichern
def save_uploaded_files():
    with open(UPLOAD_TRACKER_FILE, "w") as f:
        json.dump(uploaded_files, f)

# === Ordner scannen & Upload durchführen
def scan_and_upload():
    for mapping in workspace_mapping:
        for folder in mapping["folders"]:
            abs_folder = os.path.abspath(folder)
            if not os.path.exists(abs_folder):
                print(f"Ordner nicht gefunden: {abs_folder}")
                continue

            for root, dirs, files in os.walk(abs_folder):
                for file in files:
                    if is_temporary_or_locked(file):
                        continue
                    if not any(file.lower().endswith(ext) for ext in ACCEPTED_EXTENSIONS):
                        continue

                    full_path = os.path.join(root, file)

                    try:
                        mtime = os.path.getmtime(full_path)
                        if time.time() - mtime < 5:
                            continue  # Datei wurde gerade geändert, warten

                        file_hash = get_file_hash(full_path)
                        if file_hash is None:
                            continue
                    except Exception as e:
                        print(f"⚠️ Fehler bei {full_path}: {e}")
                        continue

                    # Schon bekannt und unverändert → skip
                    if full_path in uploaded_files:
                        if (
                            uploaded_files[full_path]["mtime"] == mtime and
                            uploaded_files[full_path]["hash"] == file_hash
                        ):
                            continue

                    # Kopien behandeln
                    if is_probable_copy(file):
                        for existing_path, meta in uploaded_files.items():
                            if meta.get("hash") == file_hash:
                                print(f"Kopie erkannt (kein Upload): {file} ≈ {os.path.basename(existing_path)}")
                                break
                        else:
                            upload_file_to_workspaces(API_KEY, full_path, mapping["workspace_slugs"])
                            uploaded_files[full_path] = {"mtime": mtime, "hash": file_hash}
                            save_uploaded_files()
                    else:
                        upload_file_to_workspaces(API_KEY, full_path, mapping["workspace_slugs"])
                        uploaded_files[full_path] = {"mtime": mtime, "hash": file_hash}
                        save_uploaded_files()

# === Start
if __name__ == "__main__":
    print("Dokumenten-Watcher läuft... Änderungen werden alle 15 Sekunden verarbeitet.")
    while True:
        scan_and_upload()
        time.sleep(15)
        time.sleep(15)
