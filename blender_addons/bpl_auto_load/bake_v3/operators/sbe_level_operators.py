"""
Operators for the custom map metadata panel
"""

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_GENERATE_LEVEL_ID
from bake_v3.properties.sbe_level_props import SBE_LevelProperties, new_map_id


class SBE_GenerateLevelId(bpy.types.Operator):
    """Generate a new unique map ID. Only do this once per map: a new ID orphans existing local records"""
    bl_idname = SBE_OP_GENERATE_LEVEL_ID
    bl_label = "Generate ID"
    bl_options = {'REGISTER', 'UNDO'}
    bpl_auto_load = True

    def execute(self, _context: bpy.types.Context):
        SBE_LevelProperties.get().map_id = new_map_id()
        return {'FINISHED'}
