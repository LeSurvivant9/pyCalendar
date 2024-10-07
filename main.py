import os
import time

from google_session import GoogleSession
from uphf_session import UPHFSession


def download_latest_ical():
    uphf_session.login()
    uphf_session.driver.get("https://vtmob.uphf.fr/esup-vtclient-up4/stylesheets/desktop/welcome.xhtml")
    uphf_session.driver.execute_script("return oamSubmitForm('j_id12','j_id12:j_id15');")
    time.sleep(1)
    uphf_session.close()


def rename_and_move_ical():
    download_path: str = "C:/Users/LS/Downloads/"
    ics_files = [file for file in os.listdir(download_path) if file.endswith('.ics')]

    if not ics_files:
        print("Aucun fichier .ics trouvé.")
        return

    most_recent_file = max(ics_files, key=lambda f: os.path.getmtime(os.path.join(download_path, f)))

    source_path = os.path.join(download_path, most_recent_file)
    destination_path = os.path.join(os.getcwd(), "EDT.ics")

    os.replace(source_path, destination_path)
    print(f"Le fichier {most_recent_file} a été déplacé et remplacé s'il existait déjà.")


def main():
    download_latest_ical()
    rename_and_move_ical()
    google_session.create_calendar("Cours")
    cours_calendar_id = google_session.get_calendar_id("Cours")
    if cours_calendar_id:
        google_session.import_events_from_ics(ICS_FILE, cours_calendar_id, True)


if __name__ == '__main__':
    uphf_session = UPHFSession()
    google_session = GoogleSession()
    CREDENTIALS_FILE: str = "credentials.json"
    ICS_FILE: str = "EDT.ics"
    main()
