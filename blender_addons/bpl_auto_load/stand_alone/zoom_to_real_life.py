# pylint: disable=import-error
import bpy
# pylint: enable=import-error

class SB_ZoomToRealLife(bpy.types.Operator):
    """Zoom the current active object to real live dimensions"""
    bl_idname = "object.sb_zoom_to_reallife"
    bl_label = "Zoom to real life"
    bpl_auto_load = True

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.active_object is not None

    def execute(self, context: bpy.types.Context):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                region_3d = space.region_3d

                window_matrix = region_3d.window_matrix
                
                if area.width > area.height:
                    scale = area.width 
                else:
                    scale = area.height

                region_3d.view_distance = 0.0172 * scale
        return {'FINISHED'}
