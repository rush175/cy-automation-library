# -*- coding: utf-8 -*-
"""cyschoolhouse Suite
This suite is a set of helper functions which address the broader task of
accessing data on cyschoolhouse. This will include navigation functions, logins,
and other common tasks we can antipicate needing to do for multiple products.
"""

from configparser import ConfigParser
import io, getpass, logging
from pathlib import Path
from time import time, sleep

import pandas as pd
from seleniumrequests import Firefox
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile


creds_path = str(Path(__file__).parent / 'credentials.ini')
gecko_path = str(Path(__file__).parents[2] / 'geckodriver/geckodriver.exe')
log_path = str(Path(__file__).parent / 'log')
temp_path = str(Path(__file__).parent / 'temp')
templates_path =str(Path(__file__).parent / 'templates')
instance_url = "https://na82.salesforce.com"
sb_instance_url = "https://cs59.salesforce.com"

def get_login_credentials(prompt_user_pass=False):
    """Extract login information from credentials.ini

    Expects a file named `credentials.ini` in the same directory as this module, formatted as:
        [Single Sign On]
        username = <your Okta username>
        password = <your Okta password>

    Optionally, set prompt_user_pass to `True` and supply credentials interactively.
    It's a little more secure to enter the user/pass every time, but it requires the user to
    be present at script initialization. If you intend to run on a schedule, then
    be prepared to store your credentials in a file.
    """

    if prompt_user_pass == False:
        config = ConfigParser()
        config.read(creds_path)

        creds = config['Salesforce']
        user = creds['username']
        pwd = creds['password']
    else:
        print('Please enter your City Year Okta credential below.')
        print('It is used for sign in only and is not stored in any way after the script closes.')
        user = input('Username:')
        # If you run from the cmd prompt, it won't show your password.  It will in an interactive
        # console though, so keep that in mind.
        pwd = getpass.getpass()

    return user, pwd

def get_driver():
    """Get Firefox driver

    Returns the Firefox driver object and handles the path.
    """
    configure_log(log_path)

    profile = FirefoxProfile()
    profile.set_preference('browser.download.folderList', 2)
    profile.set_preference('browser.download.manager.showWhenStarting', False)
    profile.set_preference('browser.download.dir', temp_path)
    profile.set_preference('browser.helperApps.neverAsk.saveToDisk', ('application/csv,text/csv,application/vnd.ms-excel,application/x-msexcel,application/excel,application/x-excel,text/comma-separated-values'))
    return Firefox(firefox_profile=profile, executable_path=gecko_path)

def standard_login(driver, prompt_user_pass=False):
    """ Login to salesforce using the standard element names "username" and "password"
    """

    user, pwd = get_login_credentials(prompt_user_pass)

    driver.find_element_by_name("username").send_keys(user)
    driver.find_element_by_name("pw").send_keys(pwd + Keys.RETURN)
    return driver

def open_cyschoolhouse(driver=None, prompt_user_pass=False, sandbox=False):
    """Opens the cyschoolhouse instance

    """
    if driver is None:
        driver = get_driver()

    if sandbox == True:
        driver.get(sb_instance_url)
    else:
        driver.get(instance_url)

    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.NAME, "username")))

    driver = standard_login(driver, prompt_user_pass)

    # Wait for next page to load - user will need to supply 2 Factor Authentication during this time
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "tsidLabel")))
    assert 'salesforce' in driver.current_url
    return driver

def configure_log(log_folder):
    """Configures the log for update cycle

    Generates a log file for this session. Uses a timestamp from the time library to as a part
    of the name.
    """
    timestamp = str(time()).split(".")[0]
    logging.basicConfig(filename=str(Path(log_path) / f"update_{timestamp}.log"), level=logging.INFO)

def get_report(report_key):
    driver = get_driver()
    open_cyschoolhouse(driver)
    url = 'https://na30.salesforce.com/' + report_key + '?export=1&enc=UTF-8&xf=csv'
    response = driver.request('GET', url)
    df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
    driver.quit()
    return df

def delete_folder(pth):
    for sub in pth.iterdir():
        if sub.is_dir():
            delete_folder(sub)
        else:
            sub.unlink()
    pth.rmdir()

def fancy_box_wait(driver, waittime=10):
    WebDriverWait(driver, waittime).until(EC.presence_of_element_located((By.XPATH, ".//div[contains(@id, 'fancybox-wrap')]")))
    WebDriverWait(driver, (waittime+30)).until(EC.invisibility_of_element_located((By.XPATH, ".//div[contains(@id, 'fancybox-wrap')]")))
    sleep(2)
    return driver

if __name__ == '__main__':
    driver = get_driver()
    driver = open_cyschoolhouse(driver, sandbox=True)
    driver.quit()
