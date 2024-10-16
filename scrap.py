"""
import requests
from bs4 import BeautifulSoup
import time

def extract_text_from_page(url):
    
    This function extracts all paragraphs from a given URL
    and returns the combined text as a string.
    
    try:
        response = requests.get(url)
        response.encoding = 'utf-8'  # Ensure correct encoding
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract paragraphs or other specific content as needed
            page_content = '\n'.join([p.get_text() for p in soup.find_all('p')])
            return page_content
        else:
            print(f"Page not found: {url}")
            return None
    except Exception as e:
        print(f"Error accessing {url}: {str(e)}")
        return None

def main():
    base_url = 'https://www.zhouyi.cc/zhouyi/yijing64/'
    valid_pages = []
    
    # Open a file to store all the content sequentially
    with open('/Users/rx/Downloads/yijing_full_content.txt', 'w', encoding='utf-8') as file:
        # Loop through the range of page numbers
        for i in range(4103, 4264):  # Assuming 4263 is the last page
            url = f"{base_url}{i}.html"
            print(f"Processing: {url}")
            content = extract_text_from_page(url)
            if content:
                valid_pages.append(i)
                # Write the content to the file
                file.write(f"\n---- Page {i} ----\n")
                file.write(content + '\n')
            # Delay between requests to avoid overloading the server
            time.sleep(1)  # Adjust the delay if needed
    
    print("Scraping completed. Valid pages found:", valid_pages)

if __name__ == "__main__":
    main()

import requests
from bs4 import BeautifulSoup

# List of valid URLs
url_range = range(4103, 4114)

valid_content = []

for page_number in url_range:
    url = f'https://www.zhouyi.cc/zhouyi/yijing64/{page_number}.html'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Try extracting the main content; adjust tags as needed
    content = soup.find('div', class_='content')  # Change to the correct tag and class
    if content:
        text = content.get_text(strip=True)
        valid_content.append(f"---- Page {page_number} ----\n\n{text}\n")

# Save the results to a file
with open('yijing_full_content.txt', 'w', encoding='utf-8') as file:
    for item in valid_content:
        file.write(item)

"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

# Set path to ChromeDriver
service = Service('/Users/rx/Downloads/chromedriver-mac-arm64/chromedriver')  # Path to ChromeDriver

# Set up options for Arc Browser
chrome_options = Options()
chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
chrome_options.add_argument("--remote-debugging-port=9222")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--headless")  # Opti
# Initialize WebDriver with ChromeDriver and Arc Browser
driver = webdriver.Chrome(service=service, options=chrome_options)

# URL range for scraping
url_range = range(4103, 4264)
valid_content = []

for page_number in url_range:
    url = f'https://www.zhouyi.cc/zhouyi/yijing64/{page_number}.html'
    try:
        driver.get(url)
        time.sleep(2)  # Wait for the page to fully load

        # Find the content using class name
        content = driver.find_element(By.CLASS_NAME, 'main_left')

        if content:
            page_text = content.text
            valid_content.append(f"---- Page {page_number} ----\n\n{page_text}\n")
            print(f"Page {page_number} scraped successfully.")
        else:
            print(f"Content not found for Page {page_number}.")
    
    except Exception as e:
        print(f"Error scraping Page {page_number}: {e}")

# Save the results to a file
with open('yijing_full_content.txt', 'w', encoding='utf-8') as file:
    for item in valid_content:
        file.write(item)

# Close the browser
driver.quit()
