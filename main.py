import os
import pathlib
from datetime import datetime
from zoneinfo import ZoneInfo

import icalendar
from dotenv import load_dotenv

from google_session import GoogleSession
from uphf_session import UPHFSession


def rename_and_move_ical(source_path: str) -> None:
    destination_path: str = os.path.join(os.getcwd(), "edt.ics")
    os.replace(source_path, destination_path)
    print(f"Le fichier .ics a été déplacé et remplacé s'il existait déjà.")


def get_event_dates(event: icalendar.Event) -> tuple[datetime, datetime]:
    dtstart = event.get('dtstart').dt
    dtend = event.get('dtend').dt

    if isinstance(dtstart, datetime) is False:
        dtstart = datetime.combine(dtstart, datetime.min.time())
    if isinstance(dtend, datetime) is False:
        dtend = datetime.combine(dtend, datetime.min.time())

    return dtstart, dtend


def assign_color_based_on_title(title: str) -> str:
    prefix = title[:2]
    match prefix:
        case "TP":
            return '10'  # Vert
        case "CM":
            return '3'  # Violet
        case "DS":
            return '6'  # Orange
        case "TD":
            return '9'  # Bleu
        case _:
            return '8'  # Par défaut, gris


def format_event_for_google_calendar(event: icalendar.Event, dtstart: datetime, dtend: datetime) -> dict:
    event_title = str(event.get('summary'))
    google_event = {'summary': event_title, 'location': str(event.get('location')),
                    'description': str(event.get('description')), 'start': {
            'dateTime': dtstart.isoformat(),
            'timeZone': 'Europe/Paris',
        }, 'end': {
            'dateTime': dtend.isoformat(),
            'timeZone': 'Europe/Paris',
        }, 'colorId': assign_color_based_on_title(event_title)}
    return google_event


def extract_events_from_ics(ics_file_path: str) -> list[dict]:
    """
    Extrait les événements à partir du fichier ICS dans un dictionnaire.
    :param ics_file_path: Chemin du fichier ICS.
    :return: Liste des événements extraits.
    """
    print(f"Extraction des événements du fichier {ics_file_path}...")
    events: list[dict] = []

    with open(ics_file_path, 'rb') as file:
        calendar = icalendar.Calendar.from_ical(file.read().decode('utf-8'))
        for event in calendar.walk('vevent'):
            dtstart, dtend = get_event_dates(event)
            google_event = format_event_for_google_calendar(event, dtstart, dtend)
            events.append(google_event)

    return events


if __name__ == '__main__':
    CREDENTIALS_FILE: str = "credentials.json"
    ICS_FILE: str = "EDT.ics"
    download_path: str = str(pathlib.Path.home() / "Downloads")

    load_dotenv(".env")
    LOGIN_URL: str | None = os.getenv("LOGIN_URL")
    if not LOGIN_URL:
        raise Exception("Vous avez oublié de définir la variable d'environnement LOGIN_URL.")

    uphf_session: UPHFSession = UPHFSession()
    try:
        print("Initialisation de la session uphf...")
        existing_cookies: dict | None = uphf_session.get_existing_cookies()
        if existing_cookies:
            uphf_session.load_cookies(existing_cookies, LOGIN_URL)
        else:
            uphf_session.login(LOGIN_URL)

        file_path: str | None = uphf_session.download_latest_ical()
        if not file_path:
            raise Exception("Le fichier .ics n'a pas été téléchargé.")
        rename_and_move_ical(file_path)

        google_session: GoogleSession = GoogleSession()
        print("\nInitialisation de la session Google...")
        cours_calendar_id: str = google_session.create_calendar("Cours")
        if include_past_events := input(
                "Souhaitez-vous inclure les événements antérieurs à aujourd'hui ? (y/N) ").strip().lower() in ['y',
                                                                                                               'yes']:
            google_session.delete_events_from_date(cours_calendar_id)
        else:
            google_session.delete_events_from_date(cours_calendar_id, datetime.today())
        print()
        formatted_events: list[dict] = extract_events_from_ics(ICS_FILE)
        google_session.import_events_to_calendar(formatted_events, cours_calendar_id, min_date=datetime.min.replace(
            tzinfo=ZoneInfo("Europe/Paris")) if include_past_events else datetime.today().replace(
            tzinfo=ZoneInfo("Europe/Paris")))
        print("\nLes événements ont été importés avec succès.")
    finally:
        uphf_session.driver.quit()
