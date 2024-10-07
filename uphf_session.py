import os
import pickle
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


class UPHFSession:
    def __init__(self):
        load_dotenv(".env.local")
        self.driver: Optional[WebDriver] = None
        self.cookies_file_path = 'cookies.pkl'

    def load_cookies(self) -> dict:
        """
        Charge les cookies à partir du fichier spécifié.

        :return: Dictionnaire des cookies chargés.

        :Example:
            cookies = UPHFSession().load_cookies()
            """
        if os.path.exists(self.cookies_file_path):
            with open(self.cookies_file_path, 'rb') as file:
                cookies, loaded_time = pickle.load(file)
                current_time = datetime.now()
                if (current_time - loaded_time) < timedelta(hours=1):
                    return cookies
        return {}

    def save_cookies(self, cookies: list[dict]):
        """
        Sauvegarde les cookies dans le fichier spécifié.

        :param cookies: Dictionnaire des cookies à sauvegarder.
        :Example:
            UPHFSession().save_cookies(cookies)
        """
        with open(self.cookies_file_path, 'wb') as file:
            pickle.dump((cookies, datetime.now()), file)

    def login(self):
        """
        Effectue une connexion et sauvegarde les cookies si nécessaire.

        :Example:
            uphf_session = UPHFSession()
            uphf_session.login()
        """
        if self.driver is None:
            options = Options()
            # options.add_argument("--headless")
            # options.add_experimental_option("detach", True)
            service = Service(ChromeDriverManager().install())
            self.driver: WebDriver = webdriver.Chrome(service=service, options=options)

        existing_cookies = self.load_cookies()
        if existing_cookies:
            print("Loading existing cookies...")
            self.driver.delete_all_cookies()
            self.driver.get(os.getenv("LOGIN_URL"))
            for cookie in existing_cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    print(f"Error adding cookie: {e}")

        else:
            print("No existing cookies found. Proceeding with login...")
            self.driver.get(os.getenv("LOGIN_URL"))
            self.driver.find_element(By.NAME, "username").send_keys(os.getenv("UPHF_USERNAME"))
            self.driver.find_element(By.NAME, "password").send_keys(os.getenv("UPHF_PASSWORD"))
            self.driver.find_element(By.NAME, "submitBtn").click()
            new_cookies: list[dict] = self.driver.get_cookies()
            self.save_cookies(new_cookies)
            print("New cookies saved.")

    def close(self):
        """
        Ferme la session et le driver Selenium.

        :Example:
            uphf_session = UPHFSession()
            uphf_session.login()
            uphf_session.close()
        """
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
