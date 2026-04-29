#!/usr/bin/env python3
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

BODY_TRANSFORM = {'scaleX': 2.286, 'scaleY': 0.42, 'translateX': 457200, 'translateY': 1399575, 'unit': 'EMU'}
PLACEHOLDER_TRANSFORM = {'scaleX': 2.2, 'scaleY': 0.11, 'translateX': 650000, 'translateY': 4700000, 'unit': 'EMU'}


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


def main():
    creds = get_credentials()
    slides = build('slides','v1',credentials=creds)
    pres = slides.presentations().get(presentationId=PRESENTATION_ID).execute()
    reqs=[]
    for sid in ['auto_robotics_slide_1','auto_robotics_slide_2']:
        slide = next(s for s in pres['slides'] if s['objectId']==sid)
        text_shapes = [(pe, extract_text(pe['shape'])) for pe in slide.get('pageElements',[]) if 'shape' in pe]
        body = max(text_shapes, key=lambda x: len(x[1]))[0]
        placeholder = next(pe for pe, txt in text_shapes if txt.startswith('Insert Photo'))
        reqs.append({'updatePageElementTransform': {'objectId': body['objectId'], 'applyMode': 'ABSOLUTE', 'transform': BODY_TRANSFORM}})
        reqs.append({'updatePageElementTransform': {'objectId': placeholder['objectId'], 'applyMode': 'ABSOLUTE', 'transform': PLACEHOLDER_TRANSFORM}})
    slides.presentations().batchUpdate(presentationId=PRESENTATION_ID, body={'requests': reqs}).execute()
    print('Geometry fixed.')
