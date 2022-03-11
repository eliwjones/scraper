Quickstart
==========

```
import scraper
from time import sleep

download_path = f"/tmp/chrome_download/"

with scraper.Browser(download_path=download_path, headless=True) as browser:
    browser.visit('https://www.unitedstateszipcodes.org/zip-code-database/')
    
    browser.find_by_text('Download Now').click()
    browser.find_by_value('University Research').click() 
    browser.find_by_text('Submit and Download').click()
    
    scraper.patient(func=lambda: browser.links.find_by_partial_href('zip_code_database.csv').click())

    file_path = scraper.browser_await_download(download_path=download_path)
```