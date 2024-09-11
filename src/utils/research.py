from astropy.coordinates import SkyCoord, get_constellation
import matplotlib
import matplotlib.pyplot as plt
from astropy.wcs import WCS
from astroquery.skyview import SkyView
from io import BytesIO
import astropy.units as u
import random
from bs4 import BeautifulSoup
import math
from src.utils import text
import asyncio
from playwright.sync_api import sync_playwright


matplotlib.use('Agg')
FILE = 'resources/data/news.txt'
SOLAR_TEFF = 5778
UG_CONST = 6.67e-11
EARTH_MASS = 5.9722e24
SOLAR_MASS = 1.989e30
EARTH_RAD = 6371e3
ALBEDO = 0.3
STEFAN_BOLTZMANN_CONST = 5.67e-8
C = 3e8
user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/94.0'


def fetch_news(keyword='astronomy'):
    url = f'https://www.google.com/search?q={keyword}'
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=user_agent)
        page = context.new_page()

        page.goto(url)
        page.click('button:has-text("Accetta tutto")')
        page.wait_for_load_state('networkidle')
        page.click('a:has-text("Notizie")')
        page.wait_for_load_state('networkidle')

        page_source = page.content()
        browser.close()

        soup = BeautifulSoup(page_source, 'html.parser')
        a = soup.find_all('a', class_='WlydOe')
        return ','.join([link.get('href') for link in a]) if len(a) > 0 else ''


def get_rand_news():
    with open(FILE, 'r') as file:
        links = file.read().strip().split(',')

    return random.choice(links)


def get_constellation_from_coordinates(coord, convert_to_sky_coord=False):
    if not convert_to_sky_coord:
        return get_constellation(coord)
    sky_coord = SkyCoord(ra=coord[0], dec=coord[1], unit=(u.hourangle, u.deg))
    return get_constellation(sky_coord)


async def fetch_sky_image(pair, constellation):
    coord = SkyCoord(ra=pair[0], dec=pair[1], unit=(u.hourangle, u.deg ))
    image_list = await asyncio.to_thread(SkyView.get_images, position=coord, survey=['DSS'], pixels=750)
    data = image_list[0][0].data
    wcs = WCS(image_list[0][0].header)

    icrs_coord = coord.transform_to('icrs')
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection=wcs)
    ax.imshow(data, origin='lower', cmap='gray')
    ax.plot(icrs_coord.ra.deg, icrs_coord.dec.deg, 'ro', transform=ax.get_transform('world'))
    plt.xlabel('RA (degrees)')
    plt.ylabel('Dec (degrees)')
    plt.grid(color='white', linestyle='--', linewidth=0.5)
    plt.title(f'Constellation: {constellation}')

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close(fig)
    return buffer


def calculate_luminosity(st_rad, st_teff):
    if st_rad is None or st_teff is None:
        return None
    return (st_rad ** 2) * ((st_teff / SOLAR_TEFF) ** 4)

def calculate_habitable_zone_edges(luminosity):
    hab_zone_inner = round(math.sqrt(luminosity / 1.1), 2)
    hab_zone_outer = round(math.sqrt(luminosity / 0.35), 2)
    return hab_zone_inner, hab_zone_outer


def calculate_habitability(data, multiple):
    if not multiple:
        return __calculate_habitability_index(data, multiple)

    summaries = []
    for planet in data:
        summary = __calculate_habitability_index(planet, multiple)
        summaries.append(summary)

    return summaries


def __calculate_habitability_index(data, multiple, threshold=0.35):
    def pl_gravity(mass, rad):
        return UG_CONST * (mass / rad ** 2)

    conditions = {
        'inner_zone_condition': False,
        'outer_zone_condition': False,
        'gravity_condition': False,
        'temperature_condition': False,
        'spectral_type_condition': False
    }

    luminosity = None
    if data['st_rad'] is not None and data['st_teff'] is not None:
        luminosity = calculate_luminosity(data['st_rad'], data['st_teff'])

    if luminosity is not None:
        hab_zone_inner, hab_zone_outer = calculate_habitable_zone_edges(luminosity)
        if data['pl_orbsmax'] is not None and data['pl_orbeccen'] is not None:
            peri = data['pl_orbsmax'] * (1 - data['pl_orbeccen'])
            apo = data['pl_orbsmax'] * (1 + data['pl_orbeccen'])
            conditions['inner_zone_condition'] = hab_zone_inner <= peri <= hab_zone_outer
            conditions['outer_zone_condition'] = hab_zone_inner <= apo <= hab_zone_outer

    if data['pl_bmasse'] is not None and data['pl_rade'] is not None:
        gravity = pl_gravity(data['pl_bmasse'] * EARTH_MASS, data['pl_rade'] * EARTH_RAD)
        conditions['gravity_condition'] = 0.4 <= round(gravity, 1) / 9.8 <= 3

    if data['st_teff'] is not None:
        conditions['temperature_condition'] = 3900 <= data['st_teff'] <= 7100

    if data['st_spectype'] is not None:
        conditions['spectral_type_condition'] = 'F' in data['st_spectype'] or 'G' in data['st_spectype'] or 'K' in data['st_spectype']

    valid_conditions = {k: v for k, v in conditions.items() if v is not None}
    habitability_index = sum(valid_conditions.values()) / len(valid_conditions)

    is_habitable = habitability_index >= threshold

    research_group = ''
    if multiple:
        match = text.get_href_match(data['pl_refname'])
        if match:
            research_group = f"The following summary is based on the data observed by [{match.group(2)}]({match.group(1)})\n\n"
        else:
            research_group = "Could not retrieve the research group.\n\n"

    summary = (
        research_group +
        f"The planet has a habitability index of *{habitability_index:.2f}*. "
        f"It {'meets' if is_habitable else 'does not meet'} the minimum habitability threshold of {threshold:.2f}. "
        f"The conditions evaluated include: \n"
        f"- *Inner Habitable Zone*: {'Met' if conditions['inner_zone_condition'] else 'Not Met'}\n"
        f"- *Outer Habitable Zone*: {'Met' if conditions['outer_zone_condition'] else 'Not Met'}\n"
        f"- *Gravity Condition*: {'Met' if conditions['gravity_condition'] else 'Not Met'}\n"
        f"- *Stellar Temperature Condition*: {'Met' if conditions['temperature_condition'] else 'Not Met'}\n"
        f"- *Spectral Type Condition*: {'Met' if conditions['spectral_type_condition'] else 'Not Met'}\n\n"
        f"{'Here are the reasons why the planet does not meet the habitability criteria:' if not is_habitable else ''}\n"
        f"{'' if conditions['inner_zone_condition'] else '- The planet\'s orbit does not fall within the inner habitable zone.\n'}"
        f"{'' if conditions['outer_zone_condition'] else '- The planet\'s orbit does not fall within the outer habitable zone.\n'}"
        f"{'' if conditions['gravity_condition'] else '- The planet\'s gravity is not within the acceptable range for habitability.\n'}"
        f"{'' if conditions['temperature_condition'] else '- The star\'s temperature is not within the suitable range for habitability.\n'}"
        f"{'' if conditions['spectral_type_condition'] else '- The star\'s spectral type is not suitable for habitability.'}"
    )

    return summary



def calculate_schwarzschild_radius(mass, is_planet):
    radius = (2 * UG_CONST / C ** 2) * (mass * EARTH_MASS if is_planet else mass * SOLAR_MASS)
    return round(radius, 3)
