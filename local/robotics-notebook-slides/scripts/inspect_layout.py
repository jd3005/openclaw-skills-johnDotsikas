#!/usr/bin/env python3
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive',
]
TOKEN_PATH = Path('/home/john/.openclaw/workspace/.secrets/google-slides-token.json')
PRESENTATION_ID = '1wfU-ey12BIzLIPBbt1wSTg5H1J5STG2ngqtVZzMmUso'


def get_credentials():
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())
    return creds


def extract_text(shape):
    out=[]
    for te in shape.get('text', {}).get('textElements', []):
        tr=te.get('textRun')
        if tr and tr.get('content'):
            out.append(tr['content'])
    return ''.join(out).strip()

creds = get_credentials()
slides = build('slides','v1',credentials=creds)
pres = slides.presentations().get(presentationId=PRESENTATION_ID).execute()
for target in [pres['slides'][5], pres['slides'][6], next(s for s in pres['slides'] if s['objectId']=='auto_robotics_slide_1'), next(s for s in pres['slides'] if s['objectId']=='auto_robotics_slide_2')]:
    print('\nSLIDE', target['objectId'])
    for pe in target.get('pageElements', []):
        if 'shape' in pe:
            txt = extract_text(pe['shape'])
            size = pe.get('size', {})
            tr = pe.get('transform', {})
            print(json.dumps({
                'id': pe.get('objectId'),
                'text': txt[:120],
                'width': size.get('width'),
                'height': size.get('height'),
                'transform': tr,
            }, indent=2))
        elif 'image' in pe:
            size = pe.get('size', {})
            tr = pe.get('transform', {})
            print(json.dumps({
                'id': pe.get('objectId'),
                'image': True,
                'width': size.get('width'),
                'height': size.get('height'),
                'transform': tr,
            }, indent=2))
