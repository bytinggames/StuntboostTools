# pylint: disable=import-error
import bpy
# pylint: enable=import-error


class SBE_SetupViewPortCameras(bpy.types.Operator):
    """Sets clipping distance and fov for all view ports"""
    bl_idname = "object.sb_setup_viewport_cameras"
    bl_label = "Setup Viewport clipping distance and FOV"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, _context: bpy.types.Context):
        for i in bpy.data.scenes:
            scene: bpy.types.Scene = i
            scene.unit_settings.scale_length = 0.01
            scene.unit_settings.length_unit = 'CENTIMETERS'
        for i in bpy.data.screens:
            screen: bpy.types.Screen = i
            for j in screen.areas:
                area: bpy.types.Area = j
                if area.type != 'VIEW_3D':
                    continue
                for k in area.spaces:
                    space: bpy.types.Space = k
                    if space.type != 'VIEW_3D':
                        continue
                    view_space: bpy.types.SpaceView3D = space
                    view_space.clip_end = 10000.0
                    view_space.clip_start = 1.0
                    view_space.lens = 24.0
        return {'FINISHED'}
