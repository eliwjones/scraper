import os
import platform
from collections import deque
from pathlib import Path
from time import sleep

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from splinter import Browser as SplinterBrowser


def Browser(work_dir='/tmp', download_path='/tmp', headless=False, verify=True):
    if verify:
        verify_chromedriver(work_dir=work_dir)

    chrome_options, extra_args = get_chrome_options_and_extra_args(work_dir=work_dir, download_path=download_path)
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36'

    browser = SplinterBrowser('chrome', headless=headless, user_agent=user_agent, options=chrome_options, **extra_args)
    browser.driver.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': download_path})

    return browser


def browser_await_download(download_path, downloading_ext='.crdownload', sleep_count=10):
    """
      Downloads must be done to a directory with nothing in it, so no more than 1 file can even be present at runtime.
    """
    current_files = list(Path(download_path).glob('*'))
    if len(current_files) > 1:
        raise Exception(f"[browser_await_download] Chrome downloads must be done to empty directories, but found many files: {current_files}.")

    download_files = list(Path(download_path).glob('*'))
    downloading_files = [filepath for filepath in download_files if filepath.name.endswith(downloading_ext)]
    downloaded_files = [filepath for filepath in download_files if not filepath.name.endswith(downloading_ext)]

    counter = 0
    while not downloading_files and counter < sleep_count and not downloaded_files:
        print("[browser_await_download] Waiting for download to start.")
        sleep(2)
        counter += 1

        download_files = list(Path(download_path).glob('*'))
        downloading_files = [filepath for filepath in download_files if filepath.name.endswith(downloading_ext)]
        downloaded_files = [filepath for filepath in download_files if not filepath.name.endswith(downloading_ext)]

    if len(downloaded_files) == 1:
        download_filepath = downloaded_files.pop()
    elif len(downloading_files) == 1 and len(downloaded_files) == 0:
        downloading_filepath = downloading_files.pop()
        downloading_file_name = downloading_filepath.name.replace(downloading_ext, '')

        download_filepath = downloading_filepath.with_name(downloading_file_name)
    else:
        message = f"[browser_await_download] Something is wrong.  We have:\n\n\t{len(downloading_files)} downloading files"
        message += f"\n\t{len(downloaded_files)} downloaded files."
        message += f"\n\nBut we expect only 1 file to be downloading or downloaded."
        message += f"\n\n\tdownloading_files: {downloading_files}\n\tdownloaded_files: {downloaded_files}"

        raise Exception(message)

    last_five_stats = deque([1, 1, 1, 1, 1], maxlen=5)
    previous_file_size = 0
    while not download_filepath.exists():
        sleep(10)
        try:
            current_file_size = downloading_filepath.stat().st_size
            last_five_stats.append(current_file_size - previous_file_size)
            previous_file_size = current_file_size

            if not sum(last_five_stats):
                raise Exception(f"[browser_await_download] Download appears frozen at size: '{current_file_size}'")

            print(f"[browser_await_download] Downloading.  Current File Size: {current_file_size}.  Sleeping 10 seconds.")
        except FileNotFoundError:
            print(f"[browser_await_download] Could not stat '{downloading_filepath}.  Presumably, we are done downloading.'")

    return download_filepath


def get_chrome_options_and_extra_args(work_dir, download_path='/tmp'):
    chrome_options = webdriver.ChromeOptions()

    chrome_options.add_experimental_option(
        'prefs', {
            'download.default_directory': download_path,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': False,
            'safebrowsing.disable_download_protection': True
        })

    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--window-size=1920,1080")

    extra_args = {}

    if platform.system() == 'Linux' and os.getenv('CI', 'false') == 'false':
        chrome_options.binary_location = f"{work_dir}/chrome-linux/chrome"
        extra_args['executable_path'] = f"{work_dir}/chromedriver_linux64/chromedriver"

    return chrome_options, extra_args


def patient(func, retry_interval=2, max_retries=5, exception=None):
    from selenium.common.exceptions import ElementNotInteractableException
    from splinter.exceptions import ElementDoesNotExist

    if not exception:
        exceptions = (ElementNotInteractableException, ElementDoesNotExist)
    else:
        exceptions = (ElementNotInteractableException, ElementDoesNotExist, exception)

    exception = None
    result = None

    successful = False
    retries = 0
    while not successful:
        if retries == max_retries:
            print('[scraper.patient] permanently failed.  Raising exception.')
            raise exception

        try:
            result = func()
            successful = True
        except exceptions as e:
            print(f"[scraper.patient] failed. Exception: {e}")
            exception = e

            sleep(retry_interval)
            retries += 1

    return result


def verify_chromedriver(work_dir, install=True):
    try:
        with Browser(headless=True, verify=False) as b:
            print("Chrome and chromedriver are installed.")
    except WebDriverException as e:
        if platform.system() == 'Darwin':
            message = 'Please install chromedriver.  Try:\n\n\t$ brew cask install chromedriver\n\n\t\tOR\n\n\t$ brew upgrade chromedriver'
            message += '\n\nThen run:\n\n\t$ xattr -d com.apple.quarantine $(which chromedriver)'
            raise Exception(message)
        else:
            """
              TODO: Add code to auto-install to:
              
                  chrome_options.binary_location = f"{work_dir}/chrome-linux/chrome"
                  extra_args['executable_path'] = f"{work_dir}/chromedriver_linux64/chromedriver"
                  
              NOTE: Fancy way would be to:
              
                  1. Get 'LAST_CHANGE' file from:
                  
                      https://commondatastorage.googleapis.com/chromium-browser-snapshots/index.html?prefix=Linux_x64/
                  
                  2. Go to:
                  
                      https://commondatastorage.googleapis.com/chromium-browser-snapshots/index.html?prefix=Linux_x64/<value_from_LAST_CHANGE>/
                  
                  3. Download:
                  
                      chrome-linux.zip
                      chromedriver_linux64.zip
                      
                  4. Unzip files to 'work_dir' from above.
                  
              REQUIRES: Some version of chrome to have been installed on machine at some point (which should slurp in X11 requirements).
            """
            raise Exception(f"Please install chromedriver for: {platform.system()}")
