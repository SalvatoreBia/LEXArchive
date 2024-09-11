import os
import math
import asyncio


STAR_FILE = 'resources/blender/star_script.txt'
ROCKY_FILE = 'resources/blender/rocky_planet_script.txt'
GASSY_FILE = 'resources/blender/gassy_planet_script.txt'
IMG_DIR = 'resources/img/'
WORKING_DIRECTORY = '/home/salvatore/Scrivania/lexarchive'
spec_types = {
    "O": "0.0 0.0 1.0 1.0",
    "B": "0.0 0.0 1.0 1.0",
    "A": "1.0 1.0 1.0 1.0",
    "F": "1.0 0.9 0.2 1.0",
    "G": "1.0 1.0 0.0 1.0",
    "K": "1.0 0.65 0.0 1.0",
    "M": "1.0 0.0 0.0 1.0",
    "L": "0.55 0.0 0.0 1.0",
    "T": "0.55 0.0 0.0 1.0",
    "Y": "0.5 0.0 0.5 1.0"
}
SOLAR_RAD = 695700
AU_TO_KM = 1.496e8


def get_star_color_rgba(string):
    for key in spec_types:
        if key in string:
            return spec_types[key]

    return spec_types['G']


async def run_blender_star_script(chat, data):
    color = get_star_color_rgba(data['st_spectype'])
    command = f'/opt/blender/blender -b -P {STAR_FILE} -- {color} -- {chat}'
    shell = await asyncio.create_subprocess_shell(command, cwd=WORKING_DIRECTORY, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdin, stderr = await shell.communicate()
    print(stderr)


async def run_blender_planet_script(chat, data):
    if data['pl_rade'] <= 2 and data['pl_bmasse'] <= 10:
        await run_rocky_planet_script(chat, data)
    else:
        await run_gassy_planet_script(chat, data)


async def run_rocky_planet_script(chat, data):
    command = f'/opt/blender/blender -b -P {ROCKY_FILE} -- {chat}'
    shell = await asyncio.create_subprocess_shell(command, cwd=WORKING_DIRECTORY, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdin, stderr = await shell.communicate()
    print(stderr)


async def run_gassy_planet_script(chat, data):
    command = f'/opt/blender/blender -b -P {GASSY_FILE} -- {chat}'
    shell = await asyncio.create_subprocess_shell(command, cwd=WORKING_DIRECTORY, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdin, stderr = await shell.communicate()
    print(stderr)

def delete_render_png(file_id):
    os.remove(f'{IMG_DIR}{file_id}.png')
