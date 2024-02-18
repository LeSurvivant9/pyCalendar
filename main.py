import os
import os.path
import pickle
import time
from datetime import datetime
from datetime import timezone
from typing import Any

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from icalendar import Calendar
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/userinfo.email',
          'https://www.googleapis.com/auth/userinfo.profile', 'openid']


def get_user_email(credentials: Credentials) -> str:
    """
    Fetches the primary email address of the authenticated user.

    :param credentials: Google OAuth2 credentials.
    :return: The primary email address of the user.
    """
    people_service = build('people', 'v1', credentials=credentials)
    profile = people_service.people().get(resourceName='people/me', personFields='emailAddresses').execute()
    email_addresses = profile.get('emailAddresses', [])
    primary_email = next((email['value'] for email in email_addresses if email.get('metadata', {}).get('primary')),
                         None)

    return primary_email


def authenticate() -> Any:
    """
    Authenticates the user with Google Calendar API.

    This function checks if a token.pickle file exists in the current directory. If it does, the function loads the
    credentials from the file. If the credentials are not valid (either because they are None or because they have
    expired), the function refreshes them if a refresh token is available, or prompts the user to log in.

    After the credentials have been obtained, the function saves them to the token.pickle file for future use.

    Finally, the function builds a Google Calendar service instance using the credentials and returns it.

    :return: An authenticated Google Calendar service instance.
    """
    creds: Credentials | None = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=3001)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service


def create_calendar(service, calendar_name):
    """
    Creates a new Google Calendar with a specified name.

    This function retrieves the list of all calendars that the authenticated user has access to, and checks if a
    calendar with the provided name already exists. If such a calendar exists, the function returns a message
    indicating that a calendar with the provided name already exists.

    If no such calendar exists, the function creates a new Google Calendar with the provided name and the time zone
    set to 'Europe/Paris', and returns a message indicating that the calendar was created successfully.

    :param service: An authenticated Google Calendar service instance.
    :param calendar_name: The name of the calendar to create.
    :return: A message indicating the result of the operation.
    """
    existing_calendars = service.calendarList().list().execute()
    for calendar in existing_calendars['items']:
        if calendar['summary'] == calendar_name:
            return f"Un calendrier nommé '{calendar_name}' existe déjà."

    print(f"Création du calendrier '{calendar_name}'...")
    calendar_body = {'summary': calendar_name, 'timeZone': 'Europe/Paris'}
    created_calendar = service.calendars().insert(body=calendar_body).execute()
    return f"Calendrier '{calendar_name}' créé avec succès, ID: {created_calendar['id']}"


def update_calendar_visibility(service, calendar_id):
    """
    Updates the visibility settings of a specified Google Calendar.

    This function retrieves the access control list (ACL) of the specified Google Calendar, and checks if there is
    an existing rule that matches the desired rule. The desired rule is to make the calendar readable by all users
    in the 'jinnov-insa.fr' domain.

    If such a rule already exists, the function returns a message indicating that the visibility settings of the
    calendar already match the desired settings.

    If no such rule exists, the function adds the desired rule to the calendar's ACL, and returns a message indicating
    that the visibility settings of the calendar have been updated.

    If an error occurs while retrieving the ACL or while updating the visibility settings, the function returns an
    error message.

    :param service: An authenticated Google Calendar service instance.
    :param calendar_id: The ID of the calendar whose visibility settings to update.
    :return: A message indicating the result of the operation.
    """
    desired_rule = {
        'scope': {
            'type': 'domain',
            'value': 'jinnov-insa.fr'
        },
        'role': 'reader'
    }

    try:
        acl = service.acl().list(calendarId=calendar_id).execute()
        for rule in acl.get('items', []):
            if rule.get('scope', {}).get('type') == desired_rule['scope']['type'] and \
                    rule.get('scope', {}).get('value') == desired_rule['scope']['value'] and \
                    rule.get('role') == desired_rule['role']:
                return "Les paramètres de visibilité du calendrier correspondent déjà à ceux souhaités."

        service.acl().insert(calendarId=calendar_id, body=desired_rule).execute()
        return "La visibilité du calendrier a été mise à jour pour votre organisation."
    except Exception as e:
        return f"Une erreur est survenue lors de la mise à jour de la visibilité du calendrier : {e}"


def get_calendar_id_by_name(service, calendar_name: str) -> str | None:
    """
    Retrieves the ID of a Google Calendar with a specified name.

    This function retrieves the list of all calendars that the authenticated user has access to, and iterates over
    them to find a calendar with the provided name. If a calendar with the provided name is found, its ID is returned.
    If no such calendar is found, the function returns None.

    If an error occurs while retrieving the list of calendars or while searching for the calendar, an error message
    is printed and the function returns None.

    :param service: An authenticated Google Calendar service instance.
    :param calendar_name: The name of the calendar to find.
    :return: The ID of the calendar if found, None otherwise.
    """
    try:
        calendar_list = service.calendarList().list().execute()
        for calendar_list_entry in calendar_list['items']:
            if calendar_list_entry['summary'] == calendar_name:
                return calendar_list_entry['id']
        return None
    except Exception as e:
        print(f"Une erreur est survenue : {e}")
        return None


def add_ics_events_to_google_calendar(service, calendar_id, ics_file_path, max_events=None):
    """
    Adds events from an ICS file to a specified Google Calendar.

    This function reads an ICS file from the provided path, and adds each event from the file to the specified Google
    Calendar. Only events that are scheduled to start after the current time are added.

    The function creates a Google Calendar event for each ICS event, with the summary, location, description, start
    time, and end time set to the corresponding values from the ICS event.

    If the max_events parameter is provided and is not None, the function stops after adding the specified number of
    events.

    If an error occurs while adding an event, an error message is printed and the function continues with the next
    event.

    After all events have been added, the function prints a message indicating the number of events that were added.

    :param service: An authenticated Google Calendar service instance.
    :param calendar_id: The ID of the calendar to which to add events.
    :param ics_file_path: The path to the ICS file from which to read events.
    :param max_events: The maximum number of events to add, or None to add all events.
    :return: None
    """
    now = datetime.now(timezone.utc)
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    user_email: str = get_user_email(creds)
    added_events_count = 0

    with open(ics_file_path, 'rb') as ics_file:
        ics_calendar = Calendar.from_ical(ics_file.read())

    print("\nCréation des événements...")
    for component in ics_calendar.walk():
        if component.name == "VEVENT":
            event_start = component.get('dtstart').dt
            if event_start > now:
                google_event = {
                    'summary': component.get('summary'),
                    'location': str(component.get('location')),
                    'description': component.get('description'),
                    'start': {
                        'dateTime': component.get('dtstart').dt.isoformat(),
                        'timeZone': 'UTC',
                    },
                    'end': {
                        'dateTime': component.get('dtend').dt.isoformat(),
                        'timeZone': 'UTC',
                    },
                    'attendees': [
                        {'email': user_email}
                    ],
                }

                try:
                    service.events().insert(calendarId=calendar_id, body=google_event).execute()
                    added_events_count += 1
                    if max_events is not None and added_events_count >= max_events:
                        break
                except HttpError as error:
                    print(f"An error occurred: {error}")

    if added_events_count > 0:
        print(
            f"{added_events_count} événement{'s' if added_events_count > 1 else ''} "
            f"{"ont" if added_events_count > 1 else 'a'} "
            f"été ajouté{'s' if added_events_count > 1 else ''} au calendrier.")
    else:
        print("Aucun événement futur n'a été ajouté au calendrier.")


def delete_upcoming_events(service, calendar_id: str):
    """
    Deletes all upcoming events from a specified Google Calendar.

    This function retrieves the calendar using the provided calendar_id, then fetches all events that are scheduled
    to start after the current time. It then iterates over these events and deletes them one by one.

    :param service: An authenticated Google Calendar service instance.
    :param calendar_id: The ID of the calendar from which to delete events.
    :return: None

    :raises HttpError: If an error occurred while deleting the events.
    """
    try:
        # Get the calendar details
        calendar = service.calendars().get(calendarId=calendar_id).execute()
        calendar_name = calendar.get('summary', 'Calendrier inconnu')

        # Get the current time in UTC
        now = datetime.now(timezone.utc).isoformat()

        # Fetch all events that are scheduled to start after the current time
        events_result = service.events().list(calendarId=calendar_id, timeMin=now, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        # If there are no upcoming events, print a message and return
        if not events:
            print(f"\nAucun événement futur trouvé dans le calendrier '{calendar_name}'.")
            return

        print("\nSuppression des événements...")
        total: int = 0
        # Iterate over the events and delete them one by one
        for event in events:
            service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
            total += 1

        # Print a message indicating the number of events that were deleted
        print(
            f"{total} événement{'s' if total > 1 else ''} "
            f"{"ont" if total > 1 else 'a'} "
            f"été supprimé{'s' if total > 1 else ''} au calendrier '{calendar_name}'.")
    except HttpError as error:
        # If an error occurred while deleting the events, print an error message
        print(f"Une erreur est survenue lors de la suppression des événements : {error}")


def login_to_ent(url: str, user_name: str, user_password: str) -> WebDriver:
    """
    Logs into the ENT system using the provided URL, username, and password.

    This function creates a new Selenium WebDriver instance, navigates to the provided URL, and logs into the system
    using the provided username and password. The WebDriver is configured to download files to the current directory
    without prompting for a location, and to suppress logging messages.

    After logging in, the function returns the WebDriver instance for further use.

    :param url: The URL of the login page.
    :param user_name: The username to use for logging in.
    :param user_password: The password to use for logging in.
    :return: A Selenium WebDriver instance that is logged into the system.
    """
    print("\nConnexion à l'ENT...")
    current_directory = os.getcwd()
    chrome_options = Options()
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    prefs = {"download.default_directory": current_directory,
             "download.prompt_for_download": False,
             "download.directory_upgrade": True,
             "safebrowsing.enabled": True}
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_window_size(300, 300)
    driver.get(url)
    username_field = driver.find_element(By.ID, "username")
    username_field.send_keys(user_name)
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys(user_password)
    password_field.send_keys(Keys.RETURN)
    return driver


def download_ics_file(driver, ics_url):
    """
    Downloads an ICS file from a given URL using a Selenium WebDriver.

    This function navigates to the provided URL using the WebDriver, waits for the 'Export iCal' button to become
    clickable, and then clicks it to initiate the download. It then waits for the download to complete by checking
    for new files in the current directory. Once the download is complete, the function renames the downloaded file
    to 'edt.ics'.

    If a file named 'edt.ics' already exists in the current directory, it is deleted before the downloaded file is
    renamed.

    If an error occurs during the download process, an error message is printed.

    If the provided WebDriver is None, the function prints a message indicating that the session is invalid and
    does not attempt to download the file.

    :param driver: A Selenium WebDriver instance.
    :param ics_url: The URL from which to download the ICS file.
    :return: None
    """
    if driver:
        try:
            driver.get(ics_url)
            WebDriverWait(driver, 10).until(
                expected_conditions.element_to_be_clickable((By.XPATH, '//a[@title="Export iCal"]'))).click()
            current_directory = os.getcwd()
            initial_files = os.listdir(current_directory)

            print("En attente de la fin du téléchargement...")
            while True:
                time.sleep(0.2)
                current_files = os.listdir(current_directory)
                new_files = [f for f in current_files if f not in initial_files]
                if new_files:
                    latest_file = max([os.path.join(current_directory, f) for f in new_files], key=os.path.getctime)
                    if not latest_file.endswith('.crdownload'):
                        break

            new_file_name = os.path.join(current_directory, 'edt.ics')
            if os.path.exists(new_file_name):
                os.remove(new_file_name)
            os.rename(latest_file, new_file_name)
            print(f"Fichier renommé en: {new_file_name}")
        except Exception as e:
            print(f"Une erreur est survenue lors du téléchargement du fichier ICS : {e}")
    else:
        print("La session est invalide. Impossible de télécharger le fichier ICS.")


def main():
    """
       Main function to execute the Google Calendar operations.

       This function performs the following operations:
       1. Authenticates the user with Google Calendar API.
       2. Creates a new Google Calendar named "Cours" if it doesn't exist.
       3. Retrieves the ID of the created or existing calendar.
       4. Updates the visibility settings of the calendar to make it readable by users in the 'jinnov-insa.fr' domain.
       5. Logs into the ENT system using the provided URL, username, and password.
       6. Downloads an ICS file from a given URL using a Selenium WebDriver.
       7. Deletes all upcoming events from the specified Google Calendar.
       8. Adds events from the downloaded ICS file to the specified Google Calendar.

       The function also prints the time taken for each operation and the total execution time.

       :return: None
       """
    start_time = time.time()
    load_dotenv()

    service_start_time = time.time()
    service = authenticate()
    print(f"Authentification terminée en {time.time() - service_start_time:.2f} secondes.\n")

    calendar_creation_start_time = time.time()
    print(create_calendar(service, "Cours"))
    print(
        f"Création ou vérification du calendrier terminée en "
        f"{time.time() - calendar_creation_start_time:.2f} secondes.\n")

    subjects_calendar_id = get_calendar_id_by_name(service, "Cours")
    if subjects_calendar_id is None:
        print("\nLe calendrier 'Cours' n'a pas été trouvé.")
        return

    visibility_update_start_time = time.time()
    print(update_calendar_visibility(service, subjects_calendar_id))
    print(f"Mise à jour de la visibilité terminée en {time.time() - visibility_update_start_time:.2f} secondes.\n")

    login_url: str = 'https://cas.uphf.fr/cas/login?service=https://ent.uphf.fr/uPortal/Login'
    username: str = os.getenv("ENT_USERNAME")
    password: str = os.getenv("ENT_PASSWORD")

    login_start_time = time.time()
    driver_session = login_to_ent(login_url, username, password)
    print(f"Connexion à l'ENT réalisée en {time.time() - login_start_time:.2f} secondes.\n")

    protected_url: str = 'https://vtmob.uphf.fr/esup-vtclient-up4/stylesheets/desktop/welcome.xhtml'
    download_start_time = time.time()
    download_ics_file(driver_session, protected_url)
    print(f"Téléchargement du fichier ICS réalisé en {time.time() - download_start_time:.2f} secondes.\n")
    driver_session.quit()

    deletion_start_time = time.time()
    delete_upcoming_events(service, subjects_calendar_id)
    print(f"Suppression des événements terminée en {time.time() - deletion_start_time:.2f} secondes.\n")

    addition_start_time = time.time()
    add_ics_events_to_google_calendar(service, subjects_calendar_id, "edt.ics")
    print(f"Ajout d'événements terminé en {time.time() - addition_start_time:.2f} secondes.\n")

    total_time = time.time() - start_time
    print(f"Temps total d'exécution: {total_time:.2f} secondes.")


if __name__ == '__main__':
    main()
