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

    delete_requests=[]
    for sid in ['redo_robotics_slide_9','redo_robotics_slide_10']:
        delete_requests.append({'deleteObject': {'objectId': sid}})
    slides.presentations().batchUpdate(presentationId=PRESENTATION_ID, body={'requests': delete_requests}).execute()

    dup_requests = [
        {'duplicateObject': {'objectId': 'g3d0d60760f6_1_0', 'objectIds': {'g3d0d60760f6_1_0': 'final_robotics_slide_9'}}},
        {'duplicateObject': {'objectId': 'g3d0d60760f6_1_0', 'objectIds': {'g3d0d60760f6_1_0': 'final_robotics_slide_10'}}},
    ]
    slides.presentations().batchUpdate(presentationId=PRESENTATION_ID, body={'requests': dup_requests}).execute()

    pres = slides.presentations().get(presentationId=PRESENTATION_ID).execute()
    specs = {
        'final_robotics_slide_9': {
            'date': '04/10/2026',
            'num': '9',
            'title': 'Drivetrain Construction and Initial Assembly',
            'body': 'Requirements and Initial Design:\n\nThis stage documents the transition from the drivetrain CAD into physical construction. The chassis was assembled using VEX structural members to establish the frame geometry and mounting locations for the drivetrain components. Multiple driven wheels were installed along each side, and a gear-driven transmission layout was integrated to transfer rotational power across the system.\n\nPhysical assembly also revealed important differences from the CAD. Axle spacing, shaft support, gear positioning, and battery packaging all required adjustment once the real components were installed. These revisions improved manufacturability and confirmed that the drivetrain could support both autonomous motion and later mechanism integration.'
        },
        'final_robotics_slide_10': {
            'date': '04/13/2026',
            'num': '10',
            'title': 'Physical Drivetrain, Revisions from CAD',
            'body': 'Requirements and Initial Design:\n\nAfter the initial assembly was completed, the physical drivetrain was compared against the original CAD model and several important differences became evident. While the CAD established the intended concept, the built version required revisions to improve real-world assembly, packaging, and structural reliability.\n\nThe physical build showed that component spacing had to be balanced carefully to preserve gear engagement while still leaving room for the battery and future mechanism integration. Structural support was also refined to make the drivetrain more stable and easier to assemble. These revisions made the drivetrain more realistic to build and better suited for continued subsystem development.'
        }
    }

    reqs=[]
    for sid, spec in specs.items():
        slide = next(s for s in pres['slides'] if s['objectId']==sid)
        shapes = [(pe, extract_text(pe['shape'])) for pe in slide.get('pageElements',[]) if 'shape' in pe]
        project = next(pe for pe, txt in shapes if txt == 'Fisherman Pull Toy')
        name = next(pe for pe, txt in shapes if txt == 'John Dotsikas')
        date = next(pe for pe, txt in shapes if txt == '3/21/2026')
        num = next(pe for pe, txt in shapes if txt == '6')
        top = next(pe for pe, txt in shapes if txt == 'Initial CAD - Drivetrain')
        body = next(pe for pe, txt in shapes if txt.startswith('Requirements and Initial Design:'))
        for elem, txt in [(project,'Fisherman Pull Toy'),(name,'John Dotsikas'),(date,spec['date']),(num,spec['num']),(top,spec['title']),(body,spec['body'])]:
            reqs.append({'deleteText': {'objectId': elem['objectId'], 'textRange': {'type': 'ALL'}}})
            reqs.append({'insertText': {'objectId': elem['objectId'], 'insertionIndex': 0, 'text': txt}})
        reqs.append({'updatePageElementTransform': {'objectId': body['objectId'], 'applyMode': 'ABSOLUTE', 'transform': {'scaleX': 2.286, 'scaleY': 0.30, 'translateX': 457200, 'translateY': 6100000, 'unit': 'EMU'}}})
    slides.presentations().batchUpdate(presentationId=PRESENTATION_ID, body={'requests': reqs}).execute()
    print('Rebuilt clean single-image slides.')

if __name__=='__main__':
    main()
