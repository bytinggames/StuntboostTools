# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_export_sequences import FULL_BAKE_SEQUENCE
from bake_v3.sbe_operator_ids import (
    SBE_OP_SHOW_LOGS, SBE_OP_CLEAR_LOGS, SBE_OP_BUILD_LEVEL
)
from bake_v3.sbe_export_operator_base import SBE_Operator_Start

class SBE_ExportPropertiesPanel(bpy.types.Panel):
    """Panel shown in scene settings"""
    bl_label = "STUNTBOOST Export"
    bl_idname = "SCENE_PT_sbe_export"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bpl_auto_load = True

    def draw(self: bpy.types.Panel, _context: bpy.types.Context):
        layout: bpy.types.UILayout = self.layout

        layout.label(text="Individual Steps for debugging:")
        for step in FULL_BAKE_SEQUENCE:
            row: bpy.types.UILayout = layout.row()
            row.column().operator(step)
            row.column().label(text=f"Ran: {SBE_Operator_Start.run_count(step)}")

        layout.label(text="Logging:")
        layout.operator(SBE_OP_SHOW_LOGS)
        layout.operator(SBE_OP_CLEAR_LOGS)

        layout.label(text="Full Build:")
        layout.operator(SBE_OP_BUILD_LEVEL)
