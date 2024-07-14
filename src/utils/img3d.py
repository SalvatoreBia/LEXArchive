import src.utils.lex_dtypes as dt
FILE = 'resources/temp/blender_script.txt'


def generate_bpy_script(host, planets: list):
    script = (
        'import bpy\n\n'
        'bpy.ops.object.select_all(action=\'SELECT\')\n'
        'bpy.ops.object.delete(use_global=False)\n'
        'bpy.ops.outliner.orphans_purge()\n\n'
        f'bpy.ops.mesh.primitive_uv_sphere_add(location=(0,0,0), scale=(1,1,1), radius={host.radius})\n'
        'bpy.ops.object.shade_smooth()\n'
        'host = bpy.context.object\n\n'
    )

    for p in planets:
        script += (
            f'bpy.ops.mesh.primitive_circle_add(location=(0,0,0), radius={p.semi_major_axis})\n'
            'orbit = bpy.context.object\n'
            f'bpy.ops.mesh.primitive_uv_sphere_add(location=(0,0,0), scale=(1,1,1), radius={p.radius})\n'
            'bpy.ops.object.shade_smooth()\n'
            'planet = bpy.context.object\n'
            'planet.parent = orbit\n'
            'orbit_rad = orbit.data.vertices[0].co.length\n'
            'planet.location = (orbit_rad, 0, 0)\n\n'
        )

    script += 'bpy.context.view_layer.update()'

    with open(FILE, 'w') as file:
        file.write(script)


'''
if __name__ == '__main__':
    h = d.Host(4, 6)
    p1 = d.Planet(0.5, 7)
    p2 = d.Planet(3, 15)
    generate_bpy_script(h, [p1, p2])
'''