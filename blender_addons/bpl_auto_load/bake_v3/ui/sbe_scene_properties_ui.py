# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.ui.sbe_bake_shared_ui import draw_bake_properties

class SBE_ScenePropertiesPanel(bpy.types.Panel):
    """Panel shown in scene settings"""
    bl_label = "STUNTBOOST Scene Properties"
    bl_idname = "SCENE_PT_sbe_scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bpl_auto_load = True


    def draw(self: bpy.types.Panel, context: bpy.types.Context):
        layout: bpy.types.UILayout = self.layout
        collection = context.scene.collection
        draw_bake_properties(layout=layout, owner=collection)
