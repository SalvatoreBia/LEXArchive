import subprocess
import os


FILE = 'resources/temp/star_script.txt'
WORKING_DIRECTORY = '/home/salvatore/Scrivania/lexarchive/src/utils'
spec_types = {
    "O": "0.0 0.0 1.0 1.0",
    "B": "0.0 0.0 1.0 1.0",
    "A": "1.0 1.0 1.0 1.0",
    "F": "1.0 1.0 0.88 1.0",
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


def run_blender_script(spec_type):
    color = get_star_color_rgba(spec_type)
    command = f'/opt/blender/blender -P {FILE} -- {color}'
    shell = subprocess.Popen(command, shell=True, cwd=WORKING_DIRECTORY, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    shell.communicate(input=b'python\njava\nc++\npython\n')


if __name__ == '__main__':
    run_blender_script('sTe4')
