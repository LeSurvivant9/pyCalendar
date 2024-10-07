import os
import os.path
from datetime import datetime
from typing import Dict

import icalendar
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSession:

    def __init__(self):
        self.service = self._get_calendar_service()

    @staticmethod
    def _get_calendar_service():
        SCOPES = ["https://www.googleapis.com/auth/calendar"]

        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=3001)
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        return build("calendar", "v3", credentials=creds)

    def get_events_of(self, day: int) -> list[dict]:
        now = datetime.datetime.now()
        future_time = now + datetime.timedelta(days=day)

        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=now.isoformat() + 'Z',
            timeMax=future_time.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        return events

    def get_calendar_id(self, calendar_name):
        calendars = self.service.calendarList().list().execute()
        for calendar in calendars['items']:
            if calendar['summary'] == calendar_name:
                return calendar['id']
        return None

    def create_calendar(self, calendar_name: str):
        calendars = self.service.calendarList().list().execute()
        for calendar in calendars['items']:
            if calendar['summary'] == calendar_name:
                print(f'The "{calendar_name}" calendar already exists.')
                return

        new_calendar = {
            'summary': calendar_name,
            'timeZone': "Europe/Paris",
        }
        created_calendar = self.service.calendars().insert(body=new_calendar).execute()
        print(f'Created new calendar: {created_calendar["summary"]}')

    def import_events_from_ics(self, ics_file_path: str, calendar_id: str, include_past_events: bool = False):
        current_date = datetime.now().date()

        with open(ics_file_path, 'rb') as file:
            calendar = icalendar.Calendar.from_ical(file.read())
            for event in calendar.walk('vevent'):
                dtstart, dtend = self._get_event_dates(event)

                if include_past_events or dtstart.date() >= current_date:
                    google_event = self.format_event_for_google_calendar(event, dtstart, dtend)
                    self.add_event_to_calendar(google_event, calendar_id)

    def format_event_for_google_calendar(self, event: icalendar.Event, dtstart: datetime, dtend: datetime) -> Dict:
        event_title = str(event.get('summary'))
        google_event = {'summary': event_title, 'location': str(event.get('location')),
                        'description': str(event.get('description')), 'start': {
                'dateTime': dtstart.isoformat(),
                'timeZone': 'Europe/Paris',
            }, 'end': {
                'dateTime': dtend.isoformat(),
                'timeZone': 'Europe/Paris',
            }, 'colorId': self.assign_color_based_on_title(event_title)}
        return google_event

    def assign_color_based_on_title(self, title: str) -> str:
        prefix = title[:2]
        match prefix:
            case "CM":
                return '6'  # Bleu
            case "TP":
                return '2'  # Vert
            case "TD":
                return '5'  # Violet
            case "DS":
                return '9'  # Orange
            case _:
                return '1'  # Par défaut, aucune couleur

    def _get_event_dates(self, event: icalendar.Event) -> tuple[datetime, datetime]:
        dtstart = event.get('dtstart').dt
        dtend = event.get('dtend').dt

        if isinstance(dtstart, datetime) is False:
            dtstart = datetime.combine(dtstart, datetime.min.time())
        if isinstance(dtend, datetime) is False:
            dtend = datetime.combine(dtend, datetime.min.time())

        return dtstart, dtend

    def add_event_to_calendar(self, google_event: Dict, calendar_id: str):
        try:
            self.service.events().insert(calendarId=calendar_id, body=google_event).execute()
            print(f"Event added to calendar with colorId {google_event['colorId']}.")
        except HttpError as error:
            print(f"An error occurred: {error}")
