"""
UI for the custom level props written to the json meta data file
"""

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_GENERATE_LEVEL_ID
from bake_v3.sbe_paths import use_custom_map_export, is_custom_level_blend
from bake_v3.properties.sbe_level_props import SBE_LevelProperties, MEDALS, SETTINGS, GAMEPLAY_PROPS


class SBE_LevelPropertiesPanel(bpy.types.Panel):
    """Custom map metadata written to the <level>_.json sidecar"""
    bl_label = "STUNTBOOST Custom Map"
    bl_idname = "SCENE_PT_sbe_level"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bpl_auto_load = True

    @classmethod
    def poll(cls, _context: bpy.types.Context) -> bool:
        # only for custom levels
        return is_custom_level_blend(bpy.data.filepath)

    def draw(self: bpy.types.Panel, _context: bpy.types.Context):
        layout: bpy.types.UILayout = self.layout
        props: SBE_LevelProperties = SBE_LevelProperties.get()

        if not use_custom_map_export():
            layout.label(text="Only written for custom map exports", icon='INFO')

        box = layout.box()
        box.label(text="Map")
        row = box.row()
        row.prop(props, "map_id")
        if not props.map_id.strip():
            row.operator(SBE_OP_GENERATE_LEVEL_ID, text="", icon='FILE_REFRESH')
        box.prop(props, "map_name")
        box.prop(props, "author")
        box.prop(props, "preview")

        box = layout.box()
        box.label(text="Medal Times (seconds)")
        for medal in MEDALS:
            box.prop(props, medal)
        error = props.medal_order_error()
        if error:
            box.label(text=error, icon='ERROR')

        box = layout.box()
        box.label(text="Gameplay (changes start a new record version)")
        box.prop(props, "version")
        for prop in GAMEPLAY_PROPS:
            box.prop(props, prop)

        box = layout.box()
        box.label(text="Visuals")
        for _, prop, _ in SETTINGS:
            if prop != "version" and prop not in GAMEPLAY_PROPS:
                box.prop(props, prop)
