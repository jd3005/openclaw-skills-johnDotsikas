#!/usr/bin/env python3
import re
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

UPPER_IMAGE_TRANSFORM = {
    'scaleX': 2.286,
    'scaleY': 0.7671,
    'translateX': 457200,
    'translateY': 1399575,
    'unit': 'EMU'
}
SUBTITLE_TRANSFORM = {
    'scaleX': 2.5908,
    'scaleY': 0.1839,
    'translateX': 457200,
    'translateY': 3937000,
    'unit': 'EMU'
}


def get_credentials():
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())
    return creds


def extract_text(shape):
    out = []
    for te in shape.get('text', {}).get('textElements', []):
        tr = te.get('textRun')
        if tr and tr.get('content'):
            out.append(tr['content'])
    return ''.join(out)


def find_slide_elements(slide):
    texts = []
    for pe in slide.get('pageElements', []):
        if 'shape' in pe:
            texts.append((pe, extract_text(pe['shape']).strip()))
    return texts


def restyle_slide(requests, slide, body_text, subtitle_text):
    texts = find_slide_elements(slide)
    body = max(texts, key=lambda x: len(x[1]))[0]
    leftover = [pe for pe, txt in texts if txt.strip() == 'Initial CAD - First Mechanism']

    requests.append({
        'updatePageElementTransform': {
            'objectId': body['objectId'],
            'applyMode': 'ABSOLUTE',
            'transform': UPPER_IMAGE_TRANSFORM
        }
    })
    if leftover:
        sub = leftover[0]
        requests.append({'deleteText': {'objectId': sub['objectId'], 'textRange': {'type': 'ALL'}}})
        requests.append({'insertText': {'objectId': sub['objectId'], 'insertionIndex': 0, 'text': subtitle_text}})
        requests.append({
            'updatePageElementTransform': {
                'objectId': sub['objectId'],
                'applyMode': 'ABSOLUTE',
                'transform': SUBTITLE_TRANSFORM
            }
        })


def main():
    creds = get_credentials()
    slides = build('slides', 'v1', credentials=creds)
    pres = slides.presentations().get(presentationId=PRESENTATION_ID).execute()
    s1 = next(s for s in pres['slides'] if s['objectId'] == 'auto_robotics_slide_1')
    s2 = next(s for s in pres['slides'] if s['objectId'] == 'auto_robotics_slide_2')
    requests = []
    restyle_slide(requests, s1, 'Drivetrain Construction and Initial Assembly', 'Insert Photo 1: Drivetrain Build Progress')
    restyle_slide(requests, s2, 'Drivetrain Revisions and Differences from CAD', 'Insert Photo 2: Revised Physical Drivetrain')
    slides.presentations().batchUpdate(presentationId=PRESENTATION_ID, body={'requests': requests}).execute()
    print('Layout fixed.')

if __name__ == '__main__':
    main()
