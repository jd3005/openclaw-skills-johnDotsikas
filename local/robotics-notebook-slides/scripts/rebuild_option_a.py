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

BODY_TRANSFORM = {
    'scaleX': 2.286,
    'scaleY': 0.42,
    'translateX': 457200,
    'translateY': 1100000,
    'unit': 'EMU'
}
PLACEHOLDER_TRANSFORM = {
    'scaleX': 2.45,
    'scaleY': 0.16,
    'translateX': 457200,
    'translateY': 4950000,
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
    reqs=[]
    data = {
        'auto_robotics_slide_1': {
            'title': 'Drivetrain Construction and Initial Assembly:',
            'body': 'Drivetrain Construction and Initial Assembly:\n\nThe drivetrain moved from the CAD stage into physical construction during this work session. The chassis was assembled using VEX structural members to establish the final wheelbase, overall frame geometry, and mounting locations for the drive components. Multiple driven wheels were installed along each side of the robot, and a gear-driven transmission layout was integrated to transfer rotational power across the drivetrain.\n\nThis build stage provided important engineering feedback that could not be fully confirmed in CAD alone. Physical assembly revealed the need to monitor axle spacing, shaft support, and gear positioning relative to the frame rails. Battery placement and packaging also became more significant once the real components were mounted inside the chassis.\n\nOverall, this iteration established the physical foundation of the robot and confirmed that the drivetrain could support both autonomous motion and future integration of the pull-toy mechanisms.',
            'placeholder': 'Insert Photo 1 Here, drivetrain build progress'
        },
        'auto_robotics_slide_2': {
            'title': 'Drivetrain Revisions and Differences from CAD:',
            'body': 'Drivetrain Revisions and Differences from CAD:\n\nAfter the initial assembly was completed, the physical drivetrain was reviewed against the original CAD model and several practical differences became evident. While the CAD established the intended concept, the built version required adjustments to improve real-world assembly, packaging, and structural reliability.\n\nThe physical build showed that component spacing had to be balanced carefully to maintain gear engagement while still leaving room for the battery and future mechanism integration. Structural support was also refined to make the drivetrain more stable and easier to assemble.\n\nThese revisions improved the drivetrain beyond the original CAD by making the design more realistic to build, more structurally sound, and better suited for continued subsystem development.',
            'placeholder': 'Insert Photo 2 Here, revised physical drivetrain'
        }
    }

    for sid, content in data.items():
        slide = next(s for s in pres['slides'] if s['objectId']==sid)
        text_shapes = [(pe, extract_text(pe['shape'])) for pe in slide.get('pageElements',[]) if 'shape' in pe]
        body = max(text_shapes, key=lambda x: len(x[1]))[0]
        placeholder = next(pe for pe, txt in text_shapes if txt.startswith('Insert Photo'))
        for elem, txt in [(body, content['body']), (placeholder, content['placeholder'])]:
            reqs.append({'deleteText': {'objectId': elem['objectId'], 'textRange': {'type': 'ALL'}}})
            reqs.append({'insertText': {'objectId': elem['objectId'], 'insertionIndex': 0, 'text': txt}})
        reqs.append({'updatePageElementTransform': {'objectId': body['objectId'], 'applyMode': 'ABSOLUTE', 'transform': BODY_TRANSFORM}})
        reqs.append({'updatePageElementTransform': {'objectId': placeholder['objectId'], 'applyMode': 'ABSOLUTE', 'transform': PLACEHOLDER_TRANSFORM}})
    slides.presentations().batchUpdate(presentationId=PRESENTATION_ID, body={'requests': reqs}).execute()
    print('Rebuilt Option A.')

if __name__=='__main__':
    main()
