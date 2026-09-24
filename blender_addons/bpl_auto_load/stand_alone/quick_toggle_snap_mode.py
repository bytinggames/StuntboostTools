# pylint: disable=import-error
import bpy
# pylint: enable=import-error


class SB_ToggleSnapMode(bpy.types.Operator):
    """Toggle between closest->vertex and center->face+rotation snap"""
    bl_idname = "wm.sb_toggle_snap_mode"
    bl_label = "Toggle Custom Snap Mode"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':

                settings = bpy.context.scene.tool_settings

                if settings.snap_elements_base == {'VERTEX'}:
                    settings.snap_target = 'CENTER'
                    settings.snap_elements_base = {'FACE'}
                    settings.use_snap_align_rotation = True
                    if settings.transform_pivot_point == 'CURSOR':
                        settings.transform_pivot_point = 'MEDIAN_POINT'
                else:
                    settings.snap_target = 'CLOSEST'
                    settings.snap_elements_base = {'VERTEX'}
                    settings.use_snap_align_rotation = False
                break

        return {'FINISHED'}
