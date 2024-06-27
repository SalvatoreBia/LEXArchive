from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random

FILE = 'config/news.txt'


def fetch_news(keyword='exoplanets news'):
    url = f'https://www.google.com/search?q={keyword}'
    options = Options()
    options.add_argument('--headless')
    service = Service('/snap/bin/geckodriver')
    driver = webdriver.Firefox(service=service, options=options)
    driver.get(url)
    driver.implicitly_wait(20)

    try:
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="L2AGLb"]'))
        ).click()
    except Exception as e:
        print(f"Cookie consent button not found: {e}")

    try:
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div[5]/div/div[4]/div/div[1]/div/'
                                                  'div/div[1]/div/div/div/div/div[1]/div/div[2]/a'))).click()
    except Exception as e:
        print(f"News tab not found: {e}")

    driver.implicitly_wait(20)

    try:
        href = [a.get_attribute('href') for a in WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'WlydOe'))
        )]

    except Exception as e:
        print(f"Error finding elements: {e}")
        href = []

    driver.quit()

    with open(FILE, 'w') as file:
        file.write('\n'.join(href))


def get_rand_news():
    rand = []
    with open(FILE, 'r') as file:
        for line in file:
            rand.append(line.strip())
    return random.choice(rand) if len(rand) > 0 else None