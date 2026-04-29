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
REF_SLIDE_ID = 'g39693704674_0_0'


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
    ref = next(s for s in pres['slides'] if s['objectId']==REF_SLIDE_ID)
    ref_shapes = [pe for pe in ref.get('pageElements',[]) if 'shape' in pe]
    ref_border = next(pe for pe in ref_shapes if pe['shape'].get('shapeType') == 'RECTANGLE' and not extract_text(pe['shape']))

    reqs=[]
    for sid in ['auto_robotics_slide_1','auto_robotics_slide_2']:
        slide = next(s for s in pres['slides'] if s['objectId']==sid)
        border_candidates = [pe for pe in slide.get('pageElements',[]) if 'shape' in pe and pe['shape'].get('shapeType') == 'RECTANGLE' and not extract_text(pe['shape'])]
        if not border_candidates:
            continue
        border = border_candidates[0]
        reqs.append({
            'updatePageElementTransform': {
                'objectId': border['objectId'],
                'applyMode': 'ABSOLUTE',
                'transform': ref_border['transform']
            }
        })
    slides.presentations().batchUpdate(presentationId=PRESENTATION_ID, body={'requests': reqs}).execute()
    print('Border shape fixed.')

if __name__=='__main__':
    main()
