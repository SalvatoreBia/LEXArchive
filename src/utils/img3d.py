import subprocess
import os


FILE = 'resources/blender/star_script.txt'
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


def get_star_color_rgba(string):
    for key in spec_types:
        if key in string:
            return spec_types[key]

    return spec_types['G']


def run_blender_star_script(chat, name, spec_type):
    color = get_star_color_rgba(spec_type)
    command = f'/opt/blender/blender -b -P {FILE} -- {color} -- {chat}'
    shell = subprocess.Popen(command, shell=True, cwd=WORKING_DIRECTORY, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdin, stderr = shell.communicate(input=b'python\njava\nc++\npython\n')
    print(stderr)


def delete_render_png(file_id):
    os.remove(f'{IMG_DIR}{file_id}.png')
