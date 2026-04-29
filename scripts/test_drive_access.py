#!/usr/bin/env python3
"""
Test d'accès Google Drive avec un service account.
Usage: python scripts/test_drive_access.py <SHARED_DRIVE_ID>

Le script tente de créer un petit fichier texte dans le Shared Drive
puis liste quelques fichiers du dossier.

Credentials:
- Il cherche d'abord la variable d'environnement `GOOGLE_APPLICATION_CREDENTIALS`
  (fichier JSON de service account).
- Sinon il tente de lire les variables d'environnement `GCP_*` (ex: GCP_PRIVATE_KEY).

Retourne JSON minimal sur stdout.
"""
import sys
import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


def load_sa_info_from_env():
    # map env -> service account fields
    mapping = {
        "type": "GCP_TYPE",
        "project_id": "GCP_PROJECT_ID",
        "private_key_id": "GCP_PRIVATE_KEY_ID",
        "private_key": "GCP_PRIVATE_KEY",
        "client_email": "GCP_CLIENT_EMAIL",
        "client_id": "GCP_CLIENT_ID",
        "auth_uri": "GCP_AUTH_URI",
        "token_uri": "GCP_TOKEN_URI",
        "auth_provider_x509_cert_url": "GCP_AUTH_PROVIDER_CERT_URL",
        "client_x509_cert_url": "GCP_CLIENT_CERT_URL",
    }
    info = {}
    for k, envk in mapping.items():
        v = os.environ.get(envk)
        if v:
            info[k] = v
    if "private_key" in info:
        # if user exported with literal \n sequences, restore newlines
        info["private_key"] = info["private_key"].replace('\\n', '\n')
    return info


def load_sa_info():
    # 1) from GOOGLE_APPLICATION_CREDENTIALS file
    gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if gac and os.path.exists(gac):
        with open(gac, "r", encoding="utf-8") as f:
            return json.load(f)
    # 2) from individual env vars
    info = load_sa_info_from_env()
    required = ["type", "project_id", "private_key", "client_email"]
    if all(k in info for k in required):
        return info
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_drive_access.py <SHARED_DRIVE_ID>")
        sys.exit(2)
    shared_drive_id = sys.argv[1]

    sa_info = load_sa_info()
    if not sa_info:
        print("ERROR: service account info not found. Set GOOGLE_APPLICATION_CREDENTIALS or GCP_* env vars.")
        sys.exit(1)

    try:
        creds = service_account.Credentials.from_service_account_info(
            sa_info, scopes=["https://www.googleapis.com/auth/drive"]
        )
        service = build("drive", "v3", credentials=creds)

        # 1) create a small test file
        media = MediaIoBaseUpload(io.BytesIO(b"tg-hire service account test"), mimetype="text/plain")
        meta = {"name": "svc-account-test.txt", "parents": [shared_drive_id]}
        created = service.files().create(body=meta, media_body=media,
                                         supportsAllDrives=True, fields="id,webViewLink").execute()
        print("CREATED:", json.dumps(created))

        # 2) list up to 10 files in the folder
        q = f"'{shared_drive_id}' in parents and trashed=false"
        lst = service.files().list(q=q, supportsAllDrives=True, includeItemsFromAllDrives=True,
                                   fields="files(id,name,webViewLink)", pageSize=10).execute()
        print("LIST:", json.dumps(lst.get("files", [])))

        # 3) cleanup: delete created file
        fid = created.get("id")
        if fid:
            service.files().delete(fileId=fid, supportsAllDrives=True).execute()
            print("CLEANUP: deleted", fid)

    except Exception as e:
        print("ERROR:", str(e))
        sys.exit(3)


if __name__ == "__main__":
    main()
