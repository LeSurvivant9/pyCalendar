import os
import pickle
from datetime import datetime, timezone

import questionary
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def main():
    change_account = questionary.confirm("Voulez-vous changer de compte Google ?", default=False).ask()

    if change_account or not os.path.exists('token.pickle'):
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=3001)
    else:
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    calendar_list = service.calendarList().list().execute()

    calendar_choices = [calendar['id'] for calendar in calendar_list['items']]

    selected_calendar_id = questionary.select("Choisissez un calendrier:", choices=calendar_choices).ask()

    now = datetime.now(timezone.utc).isoformat()

    print(f"\nLes 10 prochains événements du calendrier sélectionné :")
    events_result = service.events().list(calendarId=selected_calendar_id,
                                          timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print("Pas d'événements à venir.")
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])


if __name__ == '__main__':
    main()
