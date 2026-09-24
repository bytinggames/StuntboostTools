# pylint: disable=import-error
import bpy
# pylint: enable=import-error

class SB_SyncTransparentShadow(bpy.types.Operator):
    """Sync Use Transparent shadows material properties based on the nodes used"""
    bl_idname = "object.sb_sync_transparent_shadow"
    bl_label = "Sync Transparent Shadow"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, _context: bpy.types.Context):
        for i in bpy.data.materials:
            mat: bpy.types.Material = i
            if not mat.node_tree:
                continue
            has_transparency = False
            for j in mat.node_tree.nodes:
                if isinstance(j, bpy.types.ShaderNodeBsdfTransparent):
                    has_transparency = True
                elif isinstance(j, bpy.types.ShaderNodeBsdfGlass):
                    has_transparency = True
                elif isinstance(j, bpy.types.ShaderNodeBsdfRefraction):
                    has_transparency = True
            if mat.use_transparent_shadow != has_transparency:
                mat.use_transparent_shadow = has_transparency
                print(f"Changed transparent shadow on {mat.name}")
        return {'FINISHED'}