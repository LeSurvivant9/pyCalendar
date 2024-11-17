import json
import os
import pathlib
import time
from datetime import datetime, timedelta
from io import TextIOBase

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By


class UPHFSession:
    def __init__(self) -> None:
        load_dotenv(".env")
        self.download_path: str = str(pathlib.Path.home() / "Downloads")
        self.cookies_file_path: str = 'cookies.json'
        self.driver: WebDriver = self.initialize_driver()

    def initialize_driver(self) -> WebDriver:
        """
        Initialise le driver Selenium avec les options nécessaires.
        :return: Objet WebDriver initialisé.
        """
        options: Options = Options()
        options.add_argument("--headless")
        options.add_experimental_option("prefs", {
            "download.default_directory": self.download_path,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })
        return webdriver.Chrome(options=options)

    def save_cookies(self, cookies: list[dict]) -> None:
        """
        Enregistre les cookies dans un fichier json unique.
        :param cookies: Liste de dictionnaires contenant les informations des cookies à stocker.
        :raises TypeError: Si une erreur se produit pendant la sauvegarde des cookies.
        """
        try:
            data = {
                "cookies": cookies,
                "loaded_time": datetime.now().isoformat()
            }
            with open(self.cookies_file_path, 'w', encoding='utf-8') as file:  # type: TextIOBase
                json.dump(data, file)
            print("Fichier cookies.json créé avec succès.")
        except TypeError as e:
            os.remove(self.cookies_file_path)
            raise TypeError(f"Erreur pendant la sauvegarde des cookies : {e}")

    def get_existing_cookies(self) -> dict | None:
        """
        Retourne les cookies à partir du fichier json existant.
        :return: Dictionnaire des cookies existants ou None si le fichier n'existe pas.
        """
        if os.path.exists(self.cookies_file_path):
            with open(self.cookies_file_path, 'r', encoding='utf-8') as file:
                data: dict = json.load(file)
                cookies, loaded_time_str = data["cookies"], data["loaded_time"]
                loaded_time = datetime.fromisoformat(loaded_time_str)
                current_time = datetime.now()
                if (current_time - loaded_time) < timedelta(hours=1):
                    return cookies
        return None

    def load_cookies(self, cookies: dict, login_url: str) -> None:
        """
        Charge les cookies existants dans le navigateur.
        :param cookies: Dictionnaire des cookies existants 
        :param login_url: URL de la page de connexion
        :raises Exception: Si une erreur se produit pendant l'ajout des cookies.
        """
        print("Chargement des cookies existants...")
        self.driver.delete_all_cookies()
        self.driver.get(login_url)
        for cookie in cookies:
            try:
                self.driver.add_cookie(cookie)
            except Exception as e:
                raise Exception(f"Erreur pendant l'ajout des cookies : {e}")

    def login(self, login_url: str) -> None:
        """
        Effectue une connexion et sauvegarde les cookies si nécessaire.
        :param login_url: URL de la page de connexion
        :raises Exception: Si les variables d'environnement UPHF_USERNAME ou UPHF_PASSWORD ne sont pas définies
        """
        self.driver.get(login_url)
        UPHF_USERNAME: str | None = os.getenv("UPHF_USERNAME")
        UPHF_PASSWORD: str | None = os.getenv("UPHF_PASSWORD")
        if not UPHF_USERNAME or not UPHF_PASSWORD:
            raise Exception("Vous avez oublié de définir les variables d'environnement UPHF_USERNAME ou UPHF_PASSWORD.")
        self.driver.find_element(By.NAME, "username").send_keys(UPHF_USERNAME)
        self.driver.find_element(By.NAME, "password").send_keys(UPHF_PASSWORD)
        self.driver.find_element(By.NAME, "submitBtn").click()
        new_cookies: list[dict] = self.driver.get_cookies()
        self.save_cookies(new_cookies)

    def wait_for_download(self, wait_time: int = 10) -> str | None:
        """
        Attend que le fichier .ics soit téléchargé.
        :param wait_time: Temps d'attente maximal en secondes
        :return: Chemin du fichier téléchargé ou None si le téléchargement a échoué.
        """
        elapsed_time = 0
        while elapsed_time < wait_time:
            for filename in os.listdir(self.download_path):
                if filename.startswith("Edt") and filename.endswith(".ics"):
                    file_path = os.path.join(self.download_path, filename)
                    if not file_path.endswith(".crdownload"):
                        print(f"Téléchargement terminé : {filename}")
                        return file_path
            time.sleep(1)
            elapsed_time += 1
        print("Le téléchargement n'a pas été complété dans le temps imparti.")
        return None

    def download_latest_ical(self) -> str | None:
        """
        Télécharge le fichier .ics le plus récent.
        :return: Chemin du fichier téléchargé ou None si le téléchargement a échoué.
        """
        self.driver.get("https://vtmob.uphf.fr/esup-vtclient-up4/stylesheets/desktop/welcome.xhtml")
        self.driver.execute_script("return oamSubmitForm('j_id12','j_id12:j_id15');")

        file_path: str | None = self.wait_for_download()
        return file_path


if __name__ == '__main__':
    uphf_session: UPHFSession = UPHFSession()
    LOGIN_URL: str | None = os.getenv("LOGIN_URL")
    if not LOGIN_URL:
        raise Exception("Vous avez oublié de définir la variable d'environnement LOGIN_URL.")

    print("Initialisation de la session uphf...")
    existing_cookies: dict | None = uphf_session.get_existing_cookies()
    if existing_cookies:
        uphf_session.load_cookies(existing_cookies, LOGIN_URL)
    else:
        uphf_session.login(LOGIN_URL)
    uphf_session.download_latest_ical()
    uphf_session.driver.quit()
