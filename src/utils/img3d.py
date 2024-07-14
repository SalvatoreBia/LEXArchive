import math


FILE = 'resources/temp/blender_script.txt'
AU_TO_KM = 149597870.7
SOLAR_RADIUS_AU = 695700 / AU_TO_KM
EARTH_RADIUS_AU = 6371 / AU_TO_KM


def get_orbit_semi_minor_axis(semi_major_axis, eccentricity):
    return semi_major_axis * math.sqrt(1 - eccentricity ** 2)


def generate_bpy_script(host, planets: list):
    script = (
        'import bpy\n\n'
        'bpy.ops.object.select_all(action=\'SELECT\')\n'
        'bpy.ops.object.delete(use_global=False)\n'
        'bpy.ops.outliner.orphans_purge()\n\n'
        f'bpy.ops.mesh.primitive_uv_sphere_add(location=(0,0,0), scale=(1,1,1), radius={host.radius * SOLAR_RADIUS_AU })\n'
        'bpy.ops.object.shade_smooth()\n'
        'host = bpy.context.object\n\n'
    )

    for p in planets:
        radius = p.radius * EARTH_RADIUS_AU
        semi_major_axis = p.semi_major_axis
        semi_minor_axis = get_orbit_semi_minor_axis(semi_major_axis, p.eccentricity)
        script += (
            f'bpy.ops.mesh.primitive_circle_add(location=(0,0,0), radius=1)\n'
            'orbit = bpy.context.object\n'
            f'orbit.scale = ({semi_major_axis}, {semi_minor_axis}, 1)\n'
            'bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)\n'
            f'bpy.ops.mesh.primitive_uv_sphere_add(location=(0,0,0), scale=(1,1,1), radius={radius})\n'
            'bpy.ops.object.shade_smooth()\n'
            'planet = bpy.context.object\n'
            'planet.parent = orbit\n'
            'orbit_rad = orbit.data.vertices[0].co.length\n'
            f'planet.location = ({semi_major_axis}, 0, 0)\n\n'
        )

    script += 'bpy.context.view_layer.update()'

    with open(FILE, 'w') as file:
        file.write(script)
