# TODO move the hotkey stuff in the blender plugin loader, because boilerplate

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

class SB_SetOriginToSelected(bpy.types.Operator):
    """Set origin directly with edit mode selection"""
    bl_idname = "object.sb_set_origin_to_selected"
    bl_label = "Set Origin to Selected"
    bl_options = {'REGISTER', 'UNDO'}
    keymap_item: bpy.types.KeyMapItem = None
    keymap: bpy.types.KeyMaps = None

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context: bpy.types.Context):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                cursorSave = context.scene.cursor.location.copy()
                bpy.ops.view3d.snap_cursor_to_selected()
                prev = context.active_object.mode
                if prev != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
                if prev != context.active_object.mode:
                    bpy.ops.object.mode_set(mode=prev)
                context.scene.cursor.location = cursorSave
                break
        return {'FINISHED'}

    @staticmethod
    def bpl_load():
        bpy.utils.register_class(SB_SetOriginToSelected)

        wm = bpy.context.window_manager
        kc = wm.keyconfigs.active
        SB_SetOriginToSelected.keymap = kc.keymaps.find("Mesh")
        SB_SetOriginToSelected.keymap_item = SB_SetOriginToSelected.keymap.keymap_items.new(
            SB_SetOriginToSelected.bl_idname, 'C', 'PRESS', alt=True)

    @staticmethod
    def bpl_unload():
        bpy.utils.unregister_class(SB_SetOriginToSelected)
        SB_SetOriginToSelected.keymap.keymap_items.remove(
            SB_SetOriginToSelected.keymap_item)
