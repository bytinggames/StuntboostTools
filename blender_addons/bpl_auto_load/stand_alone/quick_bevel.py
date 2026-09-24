# pylint: disable=import-error
import bpy
# pylint: enable=import-error


class SB_QuickBevel(bpy.types.Operator):
    """Setup bevel and shade smooth"""
    bl_idname = "object.sb_quick_bevel"
    bl_label = "Setup bevel and shade smooth"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context):
        if not context.active_object or context.active_object.type != 'MESH' and context.active_object.type != 'CURVE':
            return {'FINISHED'} # TODO poll function
        try:
            if bpy.ops.object.shade_smooth.poll():
                bpy.ops.object.shade_smooth()
        except:
            pass
        bevel: bpy.types.BevelModifier = context.active_object.modifiers.new("/Bevel", 'BEVEL')
        bevel.segments = 2
        bevel.profile = 1.0
        return {'FINISHED'}
