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


def main():
    creds = get_credentials()
    slides = build('slides', 'v1', credentials=creds)

    # delete old slides
    delete_requests = [
        {'deleteObject': {'objectId': 'auto_robotics_slide_1'}},
        {'deleteObject': {'objectId': 'auto_robotics_slide_2'}},
    ]
    slides.presentations().batchUpdate(
        presentationId=PRESENTATION_ID,
        body={'requests': delete_requests}
    ).execute()

    # create fresh slides
    create_requests = [
        {'createSlide': {'objectId': 'fresh_robotics_slide_9', 'insertionIndex': 8, 'slideLayoutReference': {'predefinedLayout': 'BLANK'}}},
        {'createSlide': {'objectId': 'fresh_robotics_slide_10', 'insertionIndex': 9, 'slideLayoutReference': {'predefinedLayout': 'BLANK'}}},
    ]
    slides.presentations().batchUpdate(
        presentationId=PRESENTATION_ID,
        body={'requests': create_requests}
    ).execute()

    reqs = []
    slide_specs = [
        {
            'slideId': 'fresh_robotics_slide_9',
            'date': '04/10/2026',
            'num': '9',
            'blueTitle': 'Drivetrain Construction and Initial Assembly',
            'body': 'Requirements and Initial Design:\n\nThis stage documents the transition from the drivetrain CAD into physical construction. The chassis was assembled using VEX structural members to establish the final wheelbase, frame geometry, and mounting locations for the drivetrain components. Multiple driven wheels were installed along each side, and a gear-driven transmission layout was integrated to transfer rotational power across the system.\n\nPhysical assembly also revealed important differences from the CAD. Axle spacing, shaft support, gear positioning, and battery packaging all required adjustment once the real components were installed. These revisions improved manufacturability and confirmed that the drivetrain could support both autonomous motion and later mechanism integration.',
            'photoLabel': 'Insert Photo 1 Here'
        },
        {
            'slideId': 'fresh_robotics_slide_10',
            'date': '04/13/2026',
            'num': '10',
            'blueTitle': 'Physical Drivetrain, Revisions from CAD',
            'body': 'Requirements and Initial Design:\n\nAfter the initial assembly was completed, the physical drivetrain was compared against the original CAD model and several important differences became evident. While the CAD established the intended concept, the built version required revisions to improve real-world assembly, packaging, and structural reliability.\n\nThe physical build showed that component spacing had to be balanced carefully to preserve gear engagement while still leaving room for the battery and future mechanism integration. Structural support was also refined to make the drivetrain more stable and easier to assemble. These revisions made the drivetrain more realistic to build and better suited for continued subsystem development.',
            'photoLabel': 'Insert Photo 2 Here'
        }
    ]

    for spec in slide_specs:
        sid = spec['slideId']
        # footer texts
        reqs += [
            {'createShape': {'objectId': f'{sid}_project', 'shapeType': 'TEXT_BOX', 'elementProperties': {'pageObjectId': sid, 'size': {'width': {'magnitude': 6858000, 'unit': 'EMU'}, 'height': {'magnitude': 228600, 'unit': 'EMU'}}, 'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 688375, 'translateY': 9380417, 'unit': 'EMU'}}}},
            {'insertText': {'objectId': f'{sid}_project', 'insertionIndex': 0, 'text': 'Fisherman Pull Toy'}},
            {'createShape': {'objectId': f'{sid}_name', 'shapeType': 'TEXT_BOX', 'elementProperties': {'pageObjectId': sid, 'size': {'width': {'magnitude': 3196800, 'unit': 'EMU'}, 'height': {'magnitude': 228600, 'unit': 'EMU'}}, 'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 688375, 'translateY': 9618529, 'unit': 'EMU'}}}},
            {'insertText': {'objectId': f'{sid}_name', 'insertionIndex': 0, 'text': 'John Dotsikas'}},
            {'createShape': {'objectId': f'{sid}_date', 'shapeType': 'TEXT_BOX', 'elementProperties': {'pageObjectId': sid, 'size': {'width': {'magnitude': 2516700, 'unit': 'EMU'}, 'height': {'magnitude': 228600, 'unit': 'EMU'}}, 'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 4349575, 'translateY': 9618500, 'unit': 'EMU'}}}},
            {'insertText': {'objectId': f'{sid}_date', 'insertionIndex': 0, 'text': spec['date']}},
            {'createShape': {'objectId': f'{sid}_num', 'shapeType': 'TEXT_BOX', 'elementProperties': {'pageObjectId': sid, 'size': {'width': {'magnitude': 487500, 'unit': 'EMU'}, 'height': {'magnitude': 228600, 'unit': 'EMU'}}, 'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 7221650, 'translateY': 9618500, 'unit': 'EMU'}}}},
            {'insertText': {'objectId': f'{sid}_num', 'insertionIndex': 0, 'text': spec['num']}},
        ]
        # blue title bar background + title text
        reqs += [
            {'createShape': {'objectId': f'{sid}_titlebar', 'shapeType': 'RECTANGLE', 'elementProperties': {'pageObjectId': sid, 'size': {'width': {'magnitude': 7010400, 'unit': 'EMU'}, 'height': {'magnitude': 457200, 'unit': 'EMU'}}, 'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 457200, 'translateY': 457200, 'unit': 'EMU'}}}},
            {'updateShapeProperties': {'objectId': f'{sid}_titlebar', 'shapeProperties': {'shapeBackgroundFill': {'solidFill': {'color': {'rgbColor': {'red': 0.36, 'green': 0.63, 'blue': 0.84}}, 'alpha': 1}}, 'outline': {'propertyState': 'NOT_RENDERED'}}, 'fields': 'shapeBackgroundFill.solidFill.color,shapeBackgroundFill.solidFill.alpha,outline.propertyState'}},
            {'createShape': {'objectId': f'{sid}_titletext', 'shapeType': 'TEXT_BOX', 'elementProperties': {'pageObjectId': sid, 'size': {'width': {'magnitude': 6400800, 'unit': 'EMU'}, 'height': {'magnitude': 304800, 'unit': 'EMU'}}, 'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 762000, 'translateY': 533400, 'unit': 'EMU'}}}},
            {'insertText': {'objectId': f'{sid}_titletext', 'insertionIndex': 0, 'text': spec['blueTitle']}},
        ]
        # image placeholder region
        reqs += [
            {'createShape': {'objectId': f'{sid}_photobox', 'shapeType': 'RECTANGLE', 'elementProperties': {'pageObjectId': sid, 'size': {'width': {'magnitude': 6096000, 'unit': 'EMU'}, 'height': {'magnitude': 2819400, 'unit': 'EMU'}}, 'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 838200, 'translateY': 1219200, 'unit': 'EMU'}}}},
            {'updateShapeProperties': {'objectId': f'{sid}_photobox', 'shapeProperties': {'shapeBackgroundFill': {'solidFill': {'color': {'rgbColor': {'red': 1, 'green': 1, 'blue': 1}}, 'alpha': 0}}, 'outline': {'outlineFill': {'solidFill': {'color': {'rgbColor': {'red': 0.7, 'green': 0.7, 'blue': 0.7}}, 'alpha': 1}}, 'weight': {'magnitude': 1, 'unit': 'PT'}}}, 'fields': 'shapeBackgroundFill.solidFill.alpha,outline.outlineFill.solidFill.color,outline.outlineFill.solidFill.alpha,outline.weight'}},
            {'createShape': {'objectId': f'{sid}_photolabel', 'shapeType': 'TEXT_BOX', 'elementProperties': {'pageObjectId': sid, 'size': {'width': {'magnitude': 3048000, 'unit': 'EMU'}, 'height': {'magnitude': 304800, 'unit': 'EMU'}}, 'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 2362200, 'translateY': 2438400, 'unit': 'EMU'}}}},
            {'insertText': {'objectId': f'{sid}_photolabel', 'insertionIndex': 0, 'text': spec['photoLabel']}},
        ]
        # bottom bordered text box sized to text
        reqs += [
            {'createShape': {'objectId': f'{sid}_body', 'shapeType': 'TEXT_BOX', 'elementProperties': {'pageObjectId': sid, 'size': {'width': {'magnitude': 6858000, 'unit': 'EMU'}, 'height': {'magnitude': 1828800, 'unit': 'EMU'}}, 'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 457200, 'translateY': 4381500, 'unit': 'EMU'}}}},
            {'insertText': {'objectId': f'{sid}_body', 'insertionIndex': 0, 'text': spec['body']}},
            {'updateShapeProperties': {'objectId': f'{sid}_body', 'shapeProperties': {'shapeBackgroundFill': {'solidFill': {'color': {'rgbColor': {'red': 1, 'green': 1, 'blue': 1}}, 'alpha': 1}}, 'outline': {'outlineFill': {'solidFill': {'color': {'rgbColor': {'red': 0, 'green': 0, 'blue': 0}}, 'alpha': 1}}, 'weight': {'magnitude': 1.5, 'unit': 'PT'}}}, 'fields': 'shapeBackgroundFill.solidFill.color,shapeBackgroundFill.solidFill.alpha,outline.outlineFill.solidFill.color,outline.outlineFill.solidFill.alpha,outline.weight'}},
        ]

    slides.presentations().batchUpdate(
        presentationId=PRESENTATION_ID,
        body={'requests': reqs}
    ).execute()

    print('Fresh slides rebuilt from scratch.')

if __name__ == '__main__':
    main()
