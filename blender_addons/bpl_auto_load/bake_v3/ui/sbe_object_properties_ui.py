# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_util import nameof
from bake_v3.properties.sbe_object_props import SBE_ObjectProperties

class SBE_ObjectPropertiesPanel(bpy.types.Panel):
    """Panel shown in object settings"""
    bl_label = "STUNTBOOST Object Properties"
    bl_idname = "SCENE_PT_sbe_object"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bpl_auto_load = True

    def draw(self: bpy.types.Panel, context: bpy.types.Context):
        layout: bpy.types.UILayout = self.layout

        sbe_props: SBE_ObjectProperties = SBE_ObjectProperties.get(context.active_object)
        layout.prop(sbe_props, nameof(sbe_props.visibility))
        layout.prop(sbe_props, nameof(sbe_props.physics))
        if context.active_object.type == 'MESH' or\
            context.active_object.type == 'CURVE' or\
            context.active_object.type == 'EMPTY' or\
            context.active_object.type != 'FONT':
            layout.prop(sbe_props, nameof(sbe_props.uv_scale))
            layout.prop(sbe_props, nameof(sbe_props.skip_mesh_uv_scale))
