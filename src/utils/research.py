from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
import random
from bs4 import BeautifulSoup

FILE = 'data/news.txt'


def fetch_news(keyword='exoplanets news'):
    url = f'https://www.google.com/search?q={keyword}'
    options = Options()
    options.add_argument('--headless')
    service = Service('/snap/bin/geckodriver')
    driver = webdriver.Firefox(service=service, options=options)
    driver.get(url)

    driver.implicitly_wait(20)
    driver.find_element(By.XPATH, '//div[text()=\'Accetta tutto\']').click()
    driver.find_element(By.XPATH, '//div[text()=\'Notizie\']').click()

    page = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page, 'html.parser')
    a = soup.find_all('a', class_='WlydOe')

    return ','.join([link.get('href') for link in a]) if len(a) > 0 else ''


def get_rand_news():
    with open(FILE, 'r') as file:
        links = file.read().strip().split(',')

    return random.choice(links)


