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


def find_shapes(slide):
    return [(pe, extract_text(pe['shape'])) for pe in slide.get('pageElements',[]) if 'shape' in pe]


def copy_transform(reqs, source_obj, target_obj):
    reqs.append({
        'updatePageElementTransform': {
            'objectId': target_obj,
            'applyMode': 'ABSOLUTE',
            'transform': source_obj['transform']
        }
    })


def main():
    creds = get_credentials()
    slides = build('slides','v1',credentials=creds)
    pres = slides.presentations().get(presentationId=PRESENTATION_ID).execute()
    ref = next(s for s in pres['slides'] if s['objectId']==REF_SLIDE_ID)
    ref_shapes = find_shapes(ref)
    ref_title = next(pe for pe, txt in ref_shapes if txt == 'Initial CAD - First Mechanism')
    ref_body = next(pe for pe, txt in ref_shapes if txt.startswith('Requirements and Initial Design:'))

    targets = {
        'auto_robotics_slide_1': {
            'title': 'Drivetrain Construction and Initial Assembly',
            'body': 'Requirements and Initial Design:\n\nThis stage documents the transition from the drivetrain CAD into physical construction. The chassis was assembled using VEX structural members to establish the final wheelbase, overall frame geometry, and mounting locations for the drive components. Multiple driven wheels were installed along each side of the robot, and a gear-driven transmission layout was integrated to transfer rotational power across the drivetrain.\n\nDuring physical assembly, several practical factors became clearer than they were in CAD. Axle spacing, shaft support, and gear positioning had to be adjusted carefully relative to the frame rails. Battery placement and internal packaging also became more significant once the real components were mounted. These decisions improved manufacturability and helped verify that the drivetrain could support both autonomous motion and later mechanism integration.'
        },
        'auto_robotics_slide_2': {
            'title': 'Physical Drivetrain, Revisions from CAD',
            'body': 'Requirements and Initial Design:\n\nAfter the initial assembly was completed, the physical drivetrain was compared against the original CAD model and several important differences became evident. While the CAD established the intended concept, the built version required revisions to improve real-world assembly, packaging, and structural reliability.\n\nThe physical build showed that component spacing had to be balanced carefully to preserve gear engagement while still leaving room for the battery and future mechanism integration. Structural support was also refined to make the drivetrain more stable and easier to assemble. These revisions improved the drivetrain beyond the original CAD by making the design more realistic to build, more structurally sound, and better suited for continued subsystem development.'
        }
    }

    reqs=[]
    for sid, content in targets.items():
        slide = next(s for s in pres['slides'] if s['objectId']==sid)
        shapes = find_shapes(slide)
        title = next(pe for pe, txt in shapes if txt.startswith('Insert Photo') or txt == 'Initial CAD - First Mechanism')
        body = max(shapes, key=lambda x: len(x[1]))[0]
        for elem, txt in [(title, content['title']), (body, content['body'])]:
            reqs.append({'deleteText': {'objectId': elem['objectId'], 'textRange': {'type': 'ALL'}}})
            reqs.append({'insertText': {'objectId': elem['objectId'], 'insertionIndex': 0, 'text': txt}})
        copy_transform(reqs, ref_title, title['objectId'])
        copy_transform(reqs, ref_body, body['objectId'])
    slides.presentations().batchUpdate(presentationId=PRESENTATION_ID, body={'requests': reqs}).execute()
    print('Matched reference layout.')

if __name__=='__main__':
    main()
