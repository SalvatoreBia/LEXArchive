from astropy.coordinates import SkyCoord, get_constellation
import matplotlib.pyplot as plt
from astropy.wcs import WCS
from astroquery.skyview import SkyView
from io import BytesIO
import astropy.units as u
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


def fetch_sky_image(pair):
    coord = SkyCoord(ra=pair[0], dec=pair[1], unit=(u.hourangle, u.deg))
    image_list = SkyView.get_images(position=coord, survey=['DSS'], pixels=750)
    data = image_list[0][0].data
    wcs = WCS(image_list[0][0].header)

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection=wcs)
    ax.imshow(data, origin='lower', cmap='gray')

    ax.plot(coord.ra.deg, coord.dec.deg, 'ro', transform=ax.get_transform('world'))
    plt.xlabel('RA (degrees)')
    plt.ylabel('Dec (degrees)')
    plt.grid(color='white', linestyle='--', linewidth=0.5)
    plt.title(f'Night Sky Image (constellation: {get_constellation(coord)})')
    plt.xlabel('RA (degrees)')
    plt.ylabel('Dec (degrees)')
    plt.grid(color='white', linestyle='--', linewidth=0.5)
    plt.title(f'Night Sky Image (constellation: {get_constellation(coord)})')

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close(fig)
    return buffer
