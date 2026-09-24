# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_util import nameof
from bake_v3.sbe_collection_util import is_top_level_collection
from bake_v3.ui.sbe_bake_shared_ui import draw_bake_properties
from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties

class SBE_CollectionPropertiesPanel(bpy.types.Panel):
    """Panel shown in collection settings"""
    bl_label = "STUNTBOOST Collection Properties"
    bl_idname = "SCENE_PT_sbe_collection"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "collection"
    bpl_auto_load = True


    def draw(self: bpy.types.Panel, context: bpy.types.Context):
        layout: bpy.types.UILayout = self.layout

        collection = context.view_layer.active_layer_collection.collection
        sbe_props: SBE_CollectionProperties = SBE_CollectionProperties.get(collection)

        layout.label(text="Collection Properties")
        row: bpy.types.UILayout = layout.row()
        row.prop(sbe_props, nameof(sbe_props.visibility))
        row.prop(sbe_props, nameof(sbe_props.uv_scale))
        row.enabled = not sbe_props.is_bake_group

        if is_top_level_collection(collection):
            layout.prop(sbe_props, nameof(sbe_props.is_bake_group))
            if sbe_props.is_bake_group:
                layout.prop(sbe_props, nameof(sbe_props.skip_bake))
                draw_bake_properties(layout=layout, owner=collection)
