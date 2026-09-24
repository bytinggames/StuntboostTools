
# pylint: disable=import-error
import bpy
# pylint: enable=import-error

class SB_SetOriginToSelected(bpy.types.Operator):
    """TODO"""
    bl_idname = "object.sb_copy_transform_from_active"
    bl_label = "Copy transform from active"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context: bpy.types.Context):
        for i in context.selected_editable_objects:
            obj: bpy.types.Object = i
            obj.matrix_world = context.active_object.matrix_world

        return {'FINISHED'}
