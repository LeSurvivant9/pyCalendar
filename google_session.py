import os
import sys
from datetime import datetime, timedelta
from pprint import pprint

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSession:

    def __init__(self) -> None:
        self.service: build = self._get_calendar_service()

    @staticmethod
    def _get_calendar_service() -> build:
        """
        Récupère le service Google Calendar à partir du fichier credentials.json.
        :return: Service Google Calendar initialisé.
        """
        SCOPES: list[str] = ["https://www.googleapis.com/auth/calendar"]

        creds: Credentials | None = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=3001)
            assert creds is not None
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return build("calendar", "v3", credentials=creds)

    def get_all_calendars(self) -> list[dict]:
        """
        Récupère la liste de tous les calendriers Google.
        :return: Liste des calendriers Google.
        """
        calendars: dict = self.service.calendarList().list().execute()
        return calendars['items']

    def get_events_of(self, day: int, calendar_id: str) -> list[dict]:
        """
        Récupère les événements du jour spécifié dans le calendrier spécifié.
        :param calendar_id: ID du calendrier à rechercher.
        :param day: Nombre de jours à partir d'aujourd'hui pour récupérer les événements.
        :return: Liste des événements du jour spécifié.
        """
        now: datetime = datetime.now()
        future_time: datetime = now + timedelta(days=day)

        events_result = self.service.events().list(calendarId=calendar_id, timeMin=now.isoformat() + 'Z',
                                                   timeMax=future_time.isoformat() + 'Z', singleEvents=True,
                                                   orderBy='startTime').execute()
        events = events_result.get('items', [])
        return events

    def get_calendar_id(self, calendar_name: str) -> str | None:
        """
        Récupère l'ID du calendrier spécifié.
        :param calendar_name: Nom du calendrier à rechercher.
        :return: ID du calendrier ou None si le calendrier n'existe pas.
        """
        calendars: dict = self.service.calendarList().list().execute()
        for calendar in calendars['items']:
            if calendar['summary'] == calendar_name:
                return calendar['id']
        return None

    def create_calendar(self, calendar_name: str) -> str:
        """
        Crée un nouveau calendrier avec le nom spécifié.
        :param calendar_name: Nom du calendrier à créer.
        :return: ID du calendrier créé.
        """
        calendars: dict = self.service.calendarList().list().execute()
        for calendar in calendars['items']:
            if calendar['summary'] == calendar_name:
                print(f'Le calendrier "{calendar_name}" existe déjà.')
                return calendar['id']

        new_calendar: dict = {'summary': calendar_name, 'timeZone': "Europe/Paris", }
        created_calendar = self.service.calendars().insert(body=new_calendar).execute()
        print(f'Création du nouveau calendrier : {calendar_name}')
        return created_calendar['id']

    def import_events_to_calendar(self, events: list[dict], calendar_id: str,
                                  min_date: datetime) -> None:
        """
        Importe les événements dans le calendrier spécifié à partir de la date minimale spécifiée.
        :param events: Liste des événements à importer.
        :param calendar_id: ID du calendrier.
        :param min_date: Date minimale pour les événements à importer.
        """
        filtered_events = [event for event in events if datetime.fromisoformat(event['start']['dateTime']) >= min_date]
        total_events = len(filtered_events)
        print(f"Importation de {total_events} événement(s) dans le calendrier...")
        for index, event in enumerate(filtered_events):
            self.add_event_to_calendar(event, calendar_id)
            display_progress_bar(index + 1, total_events, f"Évènement importé : {event['summary']}")

    def add_event_to_calendar(self, event: dict, calendar_id: str):
        """
        Ajoute d'un événement au calendrier spécifié.
        :param event: Dictionnaire de l'événements à ajouter.
        :param calendar_id: ID du calendrier.
        :return: 
        """
        try:
            self.service.events().insert(calendarId=calendar_id, body=event).execute()
        except HttpError as error:
            print(f"An error occurred: {error}")

    def delete_event(self, event_id: str, calendar_id: str) -> None:
        """
        Supprime l'événement spécifié du calendrier spécifié.
        :param event_id: ID de l'événement à supprimer.
        :param calendar_id: ID du calendrier.
        """
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

    def delete_events_from_date(self, calendar_id: str, date: datetime = datetime.min) -> None:
        """
        Supprime tous les événements à partir de la date spécifiée dans le calendrier spécifié.
        Si la date est None, supprime tous les événements du calendrier.
        :param calendar_id: ID du calendrier.
        :param date: Date minimale pour la suppression des événements.
        """
        print(f"Suppression des événements du calendrier à partir de la date {date}...")
        events_result = self.service.events().list(calendarId=calendar_id, timeMin=date.isoformat() + 'Z',
                                                   singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])
        total_events = len(events)
        print(f"Nombre total d'événements à supprimer : {total_events}")
        for index, event in enumerate(events):
            self.delete_event(event['id'], calendar_id)
            display_progress_bar(index + 1, total_events, f"Évènement supprimé : {event['summary']}")


def display_progress_bar(current: int, total: int, message: str) -> None:
    """
    Affiche une barre de progression pour la suppression des événements.
    :param current: Nombre d'événements supprimés jusqu'à présent.
    :param total: Nombre total d'événements à supprimer.
    :param message: Message à afficher.
    """
    progress = (current / total) * 100
    bar_length = 25
    filled_length = int(bar_length * current // total)
    bar = '%' * filled_length + '_' * (bar_length - filled_length)
    sys.stdout.write(f"\r{message} - Progression: [{bar}] {progress:.2f}%")
    sys.stdout.flush()


if __name__ == '__main__':
    separator: str = '-' * 100
    google_session: GoogleSession = GoogleSession()
    all_calendars: list[dict] = google_session.get_all_calendars()
    pprint(all_calendars)
    print(separator)
    course_calendar_id: str | None = google_session.get_calendar_id('Cours')
    assert course_calendar_id is not None
    event_of_day: list[dict] = google_session.get_events_of(7, course_calendar_id)
    pprint(event_of_day)
    print(separator)
