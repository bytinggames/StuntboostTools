"""
Operator to switch between the export.blend file and the original source blend file.
"""

import os

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_TOGGLE_ORIGINAL
from bake_v3.sbe_util import is_export_file, retrieve_persistent, export_blend_path
from bake_v3.sbe_custom_properties import SBE_GLOBAL_ORIGINAL_BLEND_PATH

class SBE_LoadOriginal(bpy.types.Operator):
    """Switch between original/export blend file, THIS WILL NOT SAVE"""
    bl_idname = SBE_OP_TOGGLE_ORIGINAL
    bl_label = "SBE Load Export/Original"
    bpl_auto_load = True

    @classmethod
    def poll(cls, _context: bpy.types.Context) -> bool:
        if is_export_file():
            return True
        return os.access(export_blend_path(), os.R_OK)

    def execute(self, _context: bpy.types.Context):
        if not bpy.data.filepath:
            return {'FINISHED'}

        if is_export_file():
            original = retrieve_persistent(SBE_GLOBAL_ORIGINAL_BLEND_PATH)
            if not bpy.data.is_saved and bpy.data.filepath != '':
                bpy.ops.wm.save_as_mainfile()
            bpy.ops.wm.open_mainfile(filepath=original)
            return {'FINISHED'}

        export_blend = export_blend_path()
        if os.access(export_blend, os.R_OK):
            if not bpy.data.is_saved and bpy.data.filepath != '':
                bpy.ops.wm.save_as_mainfile()
            bpy.ops.wm.open_mainfile(filepath=export_blend)
            return {'FINISHED'}

        # TODO import gltfs
        return {'FINISHED'}
