import datetime
import platform
import threading
import time

import chromedriver_autoinstaller as chromedriver
from selenium import webdriver
from selenium.common.exceptions import TimeoutException as SeleniumTimeoutException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType

"""
Usage:
python3 reserve_specific.py

Customize the SETTINGS below, then run the script slightly
before reservations are released.

Details:
This is a custom version of the script for reserving a specific
experience (e.g. normal dining vs private room) on a specific date.
You can also specify the release date/time of the reservations and 
the script will pull up the page and only begin refreshing when the 
reservation release time is reached. This is much faster than the
original script and avoids potentially reserving the wrong experience
(e.g. normal dining room vs caviar tasting), but it does not offer the
date flexibility of the original script.


SETTINGS
To understand the below descriptions, please refer to this example
URL for The French Laundry:
https://www.exploretock.com/tfl/experience/273030/dining-room?date=2022-08-17&size=4&time=20%3A00

RESTAURANT_NAME:
    For the French Laundry link above you'd want to set this
    to "tfl"

EXPERIENCE_ID:
    To find the experience id, click on the desired dining option 
    on the restaurants main page. This should result in a calendar 
    which shows the dates and reservations for that specific experience 
    only. The id should then appear in the url. In the link above it 
    would be "273030".

TEST_MODE:
    Will not actually click on the reservation when True.
    Useful for making sure the script works without actually 
    holding reservations.

REFRESH_DELAY_MSEC:
    Time between each page refresh in milliseconds. Decrease this time to
    increase the number of reservation attempts.

Other settings should be self explanatory.
"""

# ------------------------------------------------------------------------
# EDIT SETTINGS WITHIN DASHED LINES

TEST_MODE = False 

RESTAURANT_NAME = "tfl"
EXPERIENCE_ID = "273030"
RESERVATION_SIZE = 4
RESERVATION_MONTH = 'August'
RESERVATION_DAY = '17' # Enter in dd format
RESERVATION_YEAR = '2022' # Enter in yyyy format
EARLIEST_TIME = "5:30 PM"
LATEST_TIME = "8:30 PM"
RELEASE_TIME = "2022-07-01 10:00 AM" # Based on your LOCAL TIME

REFRESH_DELAY_MSEC = 200

# Login not required for Tock. Could be useful if Tock 
# requires login to hold reservations one day. Best bet
# is to just login manually after the script holds the 
# reservation.
ENABLE_LOGIN = False
TOCK_USERNAME = ""
TOCK_PASSWORD = ""

# ***ADVANCED USER SETTINGS BELOW***

RESERVATION_TIME_FORMAT = "%I:%M %p"
RELEASE_TIME_FORMAT = "%Y-%m-%d %I:%M %p"

USE_CHROME_BETA = False

# Multithreading configurations
NUM_THREADS = 1
THREAD_DELAY_SEC = 1

# Delay for how long the browser remains open so that 
# the reservation can be finalized. Tock holds the reservation
# for 10 minutes before releasing.
BROWSER_CLOSE_DELAY_SEC = 600

# In this script's context, this is how long we wait for the
# reservation buttons to appear before we decide to refresh page.
# We assume that if the buttons don't appear that the reservations 
# haven't opened on the backend yet.
WEBDRIVER_TIMEOUT_DELAY_MS = 2000

# Chrome extension configurations that are used with Luminati.io proxy.
# Enable proxy to avoid getting IP potentially banned. This should be enabled only if the REFRESH_DELAY_MSEC
# is extremely low (sub hundred) and NUM_THREADS > 1.
ENABLE_PROXY = False
USER_DATA_DIR = '~/Library/Application Support/Google/Chrome'
PROFILE_DIR = 'Default'
# https://chrome.google.com/webstore/detail/luminati/efohiadmkaogdhibjbmeppjpebenaool
EXTENSION_PATH = USER_DATA_DIR + '/' + PROFILE_DIR + '/Extensions/efohiadmkaogdhibjbmeppjpebenaool/1.149.316_0'

# NORMAL USERS DO NOT EDIT CODE BELOW THIS LINE
# ------------------------------------------------------------------------

# BEGIN SCRIPT CODE

chromedriver.install()

RESERVATION_FOUND = False

MONTH_NUM = {
    'january':   '01',
    'february':  '02',
    'march':     '03',
    'april':     '04',
    'may':       '05',
    'june':      '06',
    'july':      '07',
    'august':    '08',
    'september': '09',
    'october':   '10',
    'november':  '11',
    'december':  '12'
}

RESERVATION_TIME_MIN = datetime.datetime.strptime(EARLIEST_TIME, RESERVATION_TIME_FORMAT)
RESERVATION_TIME_MAX = datetime.datetime.strptime(LATEST_TIME, RESERVATION_TIME_FORMAT)
if RELEASE_TIME is not None:
    RELEASE_TIME_DATETIME = datetime.datetime.strptime(RELEASE_TIME, RELEASE_TIME_FORMAT)

class ReserveTFL():
    def __init__(self):
        options = Options()
        if USE_CHROME_BETA:
            if platform.system() == "Darwin":
                options.binary_location = "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta"
            else:
                options.binary_location = "C:/Program Files/Google/Chrome Beta/Application/chrome.exe"
        
        options.add_argument("--incognito")
        # options.add_argument("--headless")
        # options.add_argument("--window-size=1368,768")
        if ENABLE_PROXY:
            options.add_argument('--load-extension={}'.format(EXTENSION_PATH))
            options.add_argument('--user-data-dir={}'.format(USER_DATA_DIR))
            options.add_argument('--profile-directory=Default')

        self.driver = webdriver.Chrome(
            ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install(),
            options=options
        )

    def teardown(self):
        self.driver.quit()

    # NOTE: There is a bug on M1 and in chrome webdriver v103 where
    # any driver command can crash with an ambiguous WebDriverException.
    # Details here: https://stackoverflow.com/questions/72758996
    # We can just catch and proceed as explained here: 
    # https://issuehint.com/issue/ultrafunkamsterdam/undetected-chromedriver/694
    # TODO: When this webdriver bug is fixed, remove try catch blocks
    def refresh_page(self):
        try:
            self.driver.refresh()
        except WebDriverException:
            pass

    def reserve(self):
        global RESERVATION_FOUND
        print(
            f"Looking for availability on month: {RESERVATION_MONTH}"
            f", day: {RESERVATION_DAY}, between times: {EARLIEST_TIME}"
            f" and {LATEST_TIME}"
        )

        if ENABLE_LOGIN:
            self.login_tock()

        # TODO: Get middle time based on user input
        reservation_url = (
            f"https://www.exploretock.com/{RESTAURANT_NAME}"
            f"/experience/{EXPERIENCE_ID}/dummy?date={RESERVATION_YEAR}"
            f"-{month_num(RESERVATION_MONTH)}-{RESERVATION_DAY}"
            f"&size={RESERVATION_SIZE}&time=18%3A30"
        )

        while True:
            try:
                self.driver.get(reservation_url)
                break
            except:
                continue

        if RELEASE_TIME_DATETIME is not None:
            delta = (RELEASE_TIME_DATETIME + datetime.timedelta(seconds=1)) - datetime.datetime.now()
            if delta.total_seconds() > 0:
                print(
                    f"Waiting until release time: {RELEASE_TIME_DATETIME}, "
                    f"sleeping for {delta} seconds..."
                )
                time.sleep(delta.total_seconds())
                print(
                    f"Woke up from sleep, it is now {datetime.datetime.now()}, "
                    f"refreshing page. Let's get that bread!"
                )
                self.refresh_page()
            else:
                print(
                    f"[INFO]: Release time: {RELEASE_TIME} has already passed. "
                    "Starting script immediately."
                )

        while not RESERVATION_FOUND:
            wait = WebDriverWait(self.driver, WEBDRIVER_TIMEOUT_DELAY_MS / 1000, 0.25)
            # TODO: The correct way is to wait for either the reservation
            # button to show up, the "reservations not released" message,
            # or the waitlist button to show.
            # wait.until(expected_conditions.any_of([
            #     expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "button.Consumer-resultsListItem.is-available")),
            #     expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "")),
            # ]))
            try:
                # Wait for the reservation buttons to appear
                print("Waiting for reservations to load...")
                wait.until(
                    expected_conditions.presence_of_element_located(
                        (By.CSS_SELECTOR, "button.Consumer-resultsListItem.is-available")
                    )
                )
            except SeleniumTimeoutException:
                print(
                    "No available reservations at all were detected. Assuming "
                    "reservations aren't open yet. Refreshing now."
                )
                self.refresh_page()
                continue
            except WebDriverException:
                pass
            
            # NOTE: Little bit of extra time to make sure everything is loaded
            time.sleep(100 / 1000)

            if not self.search_time():
                print("No available days found. Continuing next search iteration")
                time.sleep(REFRESH_DELAY_MSEC / 1000)
                self.refresh_page()
                continue

            print("Found availability. Sleeping for 10 minutes to complete reservation...")
            RESERVATION_FOUND = True
            time.sleep(BROWSER_CLOSE_DELAY_SEC)

    def login_tock(self):
        self.driver.get("https://www.exploretock.com/tfl/login")
        WebDriverWait(self.driver, WEBDRIVER_TIMEOUT_DELAY_MS).until(expected_conditions.presence_of_element_located((By.NAME, "email")))
        self.driver.find_element(By.NAME, "email").send_keys(TOCK_USERNAME)
        self.driver.find_element(By.NAME, "password").send_keys(TOCK_PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, ".Button").click()
        WebDriverWait(self.driver, WEBDRIVER_TIMEOUT_DELAY_MS).until(expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, ".MainHeader-accountName")))

    def search_time(self):
        for item in self.driver.find_elements(By.CSS_SELECTOR, "button.Consumer-resultsListItem.is-available"):
            span = item.find_element(By.CSS_SELECTOR, "span.Consumer-resultsListItemTime")
            span2 = span.find_element(By.CSS_SELECTOR, "span")
            print(f"Encountered time {span2.text}")

            available_time = datetime.datetime.strptime(span2.text, RESERVATION_TIME_FORMAT)
            if RESERVATION_TIME_MIN <= available_time <= RESERVATION_TIME_MAX:
                print(f"Time {span2.text} found. Clicking button")
                if not TEST_MODE:
                    item.click()
                return True

        return False


def month_num(month):
    return MONTH_NUM[month.lower()]


def run_reservation():
    r = ReserveTFL()
    r.reserve()
    r.teardown()


def execute_reservations():
    threads = []
    for _ in range(NUM_THREADS):
        t = threading.Thread(target=run_reservation)
        threads.append(t)
        t.start()
        time.sleep(THREAD_DELAY_SEC)

    for t in threads:
        t.join()


def main():
    while True:
        execute_reservations()

if __name__ == "__main__":
    main()