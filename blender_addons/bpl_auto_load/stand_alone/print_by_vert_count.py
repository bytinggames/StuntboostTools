"""
Simply print the mesh name and vertex count by descending order to the console.
"""


# pylint: disable=import-error
import bpy
# pylint: enable=import-error


class SB_PrintByVertCount(bpy.types.Operator):
    """Print mesh names and vert/face count to console"""
    bl_idname = "object.sb_print_by_vert_count"
    bl_label = "Print poly counts to console"
    bpl_auto_load = True

    def execute(self, _context: bpy.types.Context):
        results = []
        for i in bpy.data.meshes:
            mesh: bpy.types.Mesh = i
            results.append((mesh.name, len(mesh.vertices), len(mesh.polygons)))
        results.sort(key=lambda tup: tup[1], reverse=True)

        for i in range(0, min(50, len(results))):
            result = results[i]
            print(f"Vertices {result[1]}\tFaces {result[2]}\t {result[0]}")
        return {'FINISHED'}
