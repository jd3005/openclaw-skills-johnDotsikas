#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive',
]
def _secrets_dir() -> Path:
    base = os.environ.get('OPENCLAW_WORKSPACE', '/home/john/.openclaw/workspace')
    return Path(os.environ.get('ROBOTICS_SLIDES_SECRETS_DIR', f'{base}/.secrets'))


_SECRETS = _secrets_dir()
CLIENT_SECRET = _SECRETS / 'google-slides-oauth-client.json'
TOKEN_PATH = _SECRETS / 'google-slides-token.json'


def get_credentials():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return creds


def inspect_presentation(presentation_id: str):
    creds = get_credentials()
    slides = build('slides', 'v1', credentials=creds)
    drive = build('drive', 'v3', credentials=creds)

    presentation = slides.presentations().get(presentationId=presentation_id).execute()
    file_meta = drive.files().get(fileId=presentation_id, fields='id,name,owners,permissions').execute()

    summary = {
        'presentationId': presentation.get('presentationId'),
        'title': presentation.get('title'),
        'slideCount': len(presentation.get('slides', [])),
        'slides': [],
        'fileMeta': {
            'id': file_meta.get('id'),
            'name': file_meta.get('name'),
            'owners': [o.get('displayName') for o in file_meta.get('owners', [])],
        },
    }

    for idx, slide in enumerate(presentation.get('slides', []), start=1):
        texts = []
        images = 0
        shapes = 0
        for element in slide.get('pageElements', []):
            if 'shape' in element:
                shapes += 1
                text_runs = []
                for te in element['shape'].get('text', {}).get('textElements', []):
                    tr = te.get('textRun')
                    if tr and tr.get('content'):
                        text_runs.append(tr['content'])
                text = ''.join(text_runs).strip()
                if text:
                    texts.append(text[:300])
            if 'image' in element:
                images += 1
        summary['slides'].append({
            'index': idx,
            'objectId': slide.get('objectId'),
            'layout': slide.get('slideProperties', {}).get('layoutObjectId'),
            'textPreview': texts[:5],
            'imageCount': images,
            'shapeCount': shapes,
        })

    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    insp = sub.add_parser('inspect')
    insp.add_argument('--presentation', required=True)
    args = parser.parse_args()

    if args.cmd == 'inspect':
        inspect_presentation(args.presentation)
