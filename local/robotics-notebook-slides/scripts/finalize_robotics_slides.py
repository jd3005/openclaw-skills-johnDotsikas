#!/usr/bin/env python3
import re
from pathlib import Path
from urllib.parse import quote

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive',
]
TOKEN_PATH = Path('/home/john/.openclaw/workspace/.secrets/google-slides-token.json')
PRESENTATION_ID = '1wfU-ey12BIzLIPBbt1wSTg5H1J5STG2ngqtVZzMmUso'
IMG1 = Path('/home/john/.openclaw/media/inbound/253b049f-eabb-4f30-9329-2db6ee5991c6.jpg')
IMG2 = Path('/home/john/.openclaw/media/inbound/25fe2b16-6dac-4877-8a46-e4cc5d164f00.jpg')


def img_path_to_uri(path: Path) -> str:
    return 'file://' + quote(str(path))


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
    texts, images = [], []
    for pe in slide.get('pageElements', []):
        if 'shape' in pe:
            texts.append((pe, extract_text(pe['shape']).strip()))
        elif 'image' in pe:
            images.append(pe)
    return texts, images


def update_slide(requests, slide, date_text, body_text, image_uri, slide_num):
    texts, images = find_slide_elements(slide)
    title = next(pe for pe, txt in texts if txt.strip() == 'Fisherman Pull Toy')
    name = next(pe for pe, txt in texts if txt.strip() == 'John Dotsikas')
    date = next(pe for pe, txt in texts if re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}', txt.strip()))
    num = next(pe for pe, txt in texts if txt.strip() == '7')
    body = max(texts, key=lambda x: len(x[1]))[0]
    image = images[0] if images else None

    for elem, new_text in [(title, 'Fisherman Pull Toy'), (name, 'John Dotsikas'), (date, date_text), (num, slide_num), (body, body_text)]:
        requests.append({'deleteText': {'objectId': elem['objectId'], 'textRange': {'type': 'ALL'}}})
        requests.append({'insertText': {'objectId': elem['objectId'], 'insertionIndex': 0, 'text': new_text}})
    if image:
        requests.append({'replaceImage': {'imageObjectId': image['objectId'], 'url': image_uri}})


def main():
    creds = get_credentials()
    slides = build('slides', 'v1', credentials=creds)
    pres = slides.presentations().get(presentationId=PRESENTATION_ID).execute()
    s1 = next(s for s in pres['slides'] if s['objectId'] == 'auto_robotics_slide_1')
    s2 = next(s for s in pres['slides'] if s['objectId'] == 'auto_robotics_slide_2')
    requests = []
    update_slide(
        requests,
        s1,
        '04/10/2026',
        'Drivetrain Construction and Initial Assembly:\n\nThe drivetrain moved from the CAD stage into physical construction during this work session. The chassis was assembled using VEX structural members to establish the final wheelbase, overall frame geometry, and mounting locations for the drive components. Multiple driven wheels were installed along each side of the robot, and a gear-driven transmission layout was integrated in order to transfer rotational power across the drivetrain.\n\nThis stage of the build provided important engineering feedback that could not be fully confirmed in CAD alone. During physical assembly, attention had to be given to axle spacing, shaft support, and the positioning of the gears relative to the frame rails. Battery placement and component packaging also became more significant once the real parts were mounted inside the chassis. As a result, the drivetrain was not treated as a simple copy of the CAD model, but rather as a functional prototype that could be evaluated for rigidity, accessibility, and manufacturability.\n\nOverall, this iteration established the physical foundation of the robot and confirmed that the drivetrain could support both autonomous motion and future integration of the pull-toy mechanisms.',
        img_path_to_uri(IMG1),
        '9'
    )
    update_slide(
        requests,
        s2,
        '04/13/2026',
        'Drivetrain Revisions and Differences from CAD:\n\nAfter the initial assembly was completed, the physical drivetrain was reviewed against the original CAD model and several practical differences became evident. While the CAD established the intended concept, the built version required adjustments to improve real-world assembly, packaging, and structural reliability. The battery arrangement, gear spacing, and support geometry were refined so that the drivetrain could be mounted more securely and serviced more easily.\n\nThe completed chassis demonstrates that physical implementation introduced constraints that were less obvious in the digital model. In particular, the spacing between structural members and drive components had to be balanced carefully to maintain gear engagement while still leaving room for batteries and future mechanism integration. The final build also reflects more deliberate reinforcement of the frame, which is important for a robot that must operate autonomously while driving a mechanically linked pull-toy system.\n\nThese revisions improved the drivetrain beyond the original CAD by making the design more realistic to build, more structurally stable, and better suited for continued subsystem development.',
        img_path_to_uri(IMG2),
        '10'
    )
    slides.presentations().batchUpdate(presentationId=PRESENTATION_ID, body={'requests': requests}).execute()
    print('Finalized slides 9 and 10.')

if __name__ == '__main__':
    main()
