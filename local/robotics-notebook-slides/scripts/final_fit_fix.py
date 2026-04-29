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
BODY_TRANSFORM = {
    'scaleX': 2.286,
    'scaleY': 0.34,
    'translateX': 685800,
    'translateY': 5200000,
    'unit': 'EMU'
}


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
    texts = {
        'auto_robotics_slide_1': 'Requirements and Initial Design:\n\nThis stage documents the transition from the drivetrain CAD into physical construction. The chassis was assembled using VEX structural members to establish the final wheelbase, overall frame geometry, and mounting locations for the drive components. Multiple driven wheels were installed along each side of the robot, and a gear-driven transmission layout was integrated to transfer rotational power across the drivetrain.\n\nPhysical assembly also revealed important differences from the CAD. Axle spacing, shaft support, gear positioning, and battery packaging all required adjustment once the real components were installed. These revisions improved manufacturability and helped verify that the drivetrain could support both autonomous motion and later mechanism integration.',
        'auto_robotics_slide_2': 'Requirements and Initial Design:\n\nAfter the initial assembly was completed, the physical drivetrain was compared against the original CAD model and several important differences became evident. While the CAD established the intended concept, the built version required revisions to improve real-world assembly, packaging, and structural reliability.\n\nThe physical build showed that component spacing had to be balanced carefully to preserve gear engagement while still leaving room for the battery and future mechanism integration. Structural support was also refined to make the drivetrain more stable and easier to assemble. These revisions made the drivetrain more realistic to build and better suited for continued subsystem development.'
    }
    reqs=[]
    for sid, txt in texts.items():
        slide = next(s for s in pres['slides'] if s['objectId']==sid)
        shapes = [(pe, extract_text(pe['shape'])) for pe in slide.get('pageElements',[]) if 'shape' in pe]
        body = next(pe for pe, t in shapes if t.startswith('Requirements and Initial Design:'))
        reqs.append({'deleteText': {'objectId': body['objectId'], 'textRange': {'type': 'ALL'}}})
        reqs.append({'insertText': {'objectId': body['objectId'], 'insertionIndex': 0, 'text': txt}})
        reqs.append({'updatePageElementTransform': {'objectId': body['objectId'], 'applyMode': 'ABSOLUTE', 'transform': BODY_TRANSFORM}})
    slides.presentations().batchUpdate(presentationId=PRESENTATION_ID, body={'requests': reqs}).execute()
    print('Final fit fixed.')

if __name__=='__main__':
    main()
