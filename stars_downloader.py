import os
import random
import time
from typing import Iterable

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()


class StarsDownloader:
    def __init__(self, headless=False):
        self.username = str(os.getenv("stars_id"))
        self.password = str(os.getenv("stars_password"))
        self.base_url = "https://wish.wis.ntu.edu.sg/pls/webexe/ldap_login.login?w_url=https://wish.wis.ntu.edu.sg/pls/webexe/aus_stars_planner.main"

        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        self.wait = WebDriverWait(self.driver, 12)

    def _random_delay(self, min_s=0.5, max_s=1.5):
        time.sleep(random.uniform(min_s, max_s))

    def login(self):
        """Handles the multi-step LDAP login process."""
        try:
            self.driver.get(self.base_url)

            # 1. Enter Username
            uid_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "UID"))
            )
            uid_field.send_keys(self.username)
            self._random_delay()
            self.driver.find_element(By.XPATH, "//input[@value='OK']").click()

            # 2. Enter Password
            pw_field = self.wait.until(
                EC.visibility_of_element_located((By.NAME, "PW"))
            )
            pw_field.send_keys(self.password)
            self._random_delay()
            self.driver.find_element(By.XPATH, "//input[@value='OK']").click()

            # 3. Verify Landing
            self.wait.until(EC.url_contains("AUS_STARS_PLANNER.planner"))
            print("Successfully logged into STARS.")
            return True
        except Exception as e:
            print(f"Login failed: {e}")
            return False

    def is_module_in_planner(self, course_code):
        """Checks if a specific course code is currently visible in the planner table."""
        try:
            # Use a shorter wait for checking existence to keep the script fast
            short_wait = WebDriverWait(self.driver, 3)
            module_xpath = f"//span[@title='Click link for more details']//font[text()='{course_code}']"

            short_wait.until(EC.presence_of_element_located((By.XPATH, module_xpath)))
            print(f"Module {course_code} found in planner.")
            return True
        except Exception:
            print(f"Module {course_code} is NOT present in the planner.")
            return False

    def add_module(self, course_code: str):
        print(f"Adding {course_code} to planner...")
        add_btn = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//span[@title='Add Course Code']"))
        )
        add_btn.click()

        self.wait.until(EC.alert_is_present())
        alert = self.driver.switch_to.alert
        alert.send_keys(course_code)
        alert.accept()
        self._random_delay(2.0, 3.0)  # Allow time for DOM refresh

    def download_module_html(self, course_code: str):
        module_xpath = f"//span[@title='Click link for more details']//font[text()='{course_code}']"
        module_link = self.driver.find_element(By.XPATH, module_xpath)
        module_link.click()
        print(f"Proceeding to download HTML for {course_code}.")
        original_window = self.driver.current_window_handle
        self.wait.until(lambda d: len(d.window_handles) > 1)
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            if "AUS_STARS_PLANNER.course_info" in self.driver.current_url:
                print(f"Switched to Course Info tab: {self.driver.current_url}")
                break
        else:
            print("Course Info tab not found. Returning to original window.")
            self.driver.switch_to.window(original_window)
        self.wait.until(EC.url_contains("AUS_STARS_PLANNER.course_info"))
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

        with open(f"mods/{course_code}.html", "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        print(f"Page source saved to {course_code}.html")
        self.driver.close()
        self.driver.switch_to.window(original_window)

    def download_stars_page(self):
        with open(f"mods/stars.html", "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        print(f"Page source saved to stars.html")

    def scrape_modules(self, course_codes: Iterable[str]):
        """Navigates to course info and saves source, with pre-check logic."""
        for code in course_codes:
            try:
                if not self.is_module_in_planner(code):
                    self.add_module(code)
                if self.is_module_in_planner(code):
                    self.download_module_html(code)
                else:
                    print(
                        f"Skipping download: {code} could not be added to the planner."
                    )
            except Exception as e:
                print(f"Error processing {code}: {e}")
        self.download_stars_page()

    def quit(self):
        self.driver.quit()


# --- Execution ---
if __name__ == "__main__":
    downloader = StarsDownloader(headless=True)
    if downloader.login():
        # You can now loop through multiple modules
        target_mods = [
            "AD1102",
            "AB1201",
            "AB1601",
            # "AB1501",
            # "AB2008",
            # "BC2406",
            "SC1006",
            "SC2001",
            "SC2002",
            # "SC2203",
            "CC0001",
        ]
        downloader.scrape_modules(target_mods)
    downloader.quit()
