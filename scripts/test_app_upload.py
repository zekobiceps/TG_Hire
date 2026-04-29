#!/usr/bin/env python3
"""
Simule l'upload effectué par l'application : crée (ou récupère)
une folder YEAR / <folder_name> sous le Shared Drive parent puis
uploade un fichier test.
Usage: python scripts/test_app_upload.py <PARENT_ID> <FOLDER_NAME>
"""
import sys
import os
import io
import datetime
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

PARENT = sys.argv[1] if len(sys.argv) > 1 else None
FOLDER_NAME = sys.argv[2] if len(sys.argv) > 2 else f"TEST_UPLOAD_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

if not PARENT:
    print("Usage: python scripts/test_app_upload.py <PARENT_ID> [FOLDER_NAME]")
    sys.exit(2)

GAC = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
if not GAC or not os.path.exists(GAC):
    print('ERROR: GOOGLE_APPLICATION_CREDENTIALS not set or file missing.')
    sys.exit(1)

sa_info = json.load(open(GAC, 'r'))
creds = service_account.Credentials.from_service_account_info(sa_info, scopes=["https://www.googleapis.com/auth/drive"])
service = build('drive', 'v3', credentials=creds)

# helper to get/create folder
def get_or_create_folder(name, parent_id):
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    res = service.files().list(q=q, fields='files(id,name)', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    files = res.get('files', [])
    if files:
        return files[0]['id']
    meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
    f = service.files().create(body=meta, fields='id', supportsAllDrives=True).execute()
    return f['id']

try:
    year = str(datetime.date.today().year)
    year_id = get_or_create_folder(year, PARENT)
    print('Year folder id:', year_id)
    folder_id = get_or_create_folder(FOLDER_NAME.upper(), year_id)
    print('Target folder id:', folder_id)

    # upload a small text file
    content = b"This is a test file uploaded by scripts/test_app_upload.py"
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype='text/plain')
    meta = {'name': f'{FOLDER_NAME}.txt', 'parents': [folder_id]}
    created = service.files().create(body=meta, media_body=media, fields='id,webViewLink', supportsAllDrives=True).execute()
    print('Created file:', created)

    # list files in target folder
    q = f"'{folder_id}' in parents and trashed=false"
    lst = service.files().list(q=q, supportsAllDrives=True, includeItemsFromAllDrives=True, fields='files(id,name,webViewLink)').execute()
    print('Files in folder:', json.dumps(lst.get('files', [])))

    # cleanup: delete created file
    fid = created.get('id')
    if fid:
        service.files().delete(fileId=fid, supportsAllDrives=True).execute()
        print('Deleted file id:', fid)
except Exception as e:
    print('ERROR:', str(e))
    sys.exit(3)
