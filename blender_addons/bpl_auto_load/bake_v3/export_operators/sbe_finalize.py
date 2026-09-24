"""
Setup the view and some minor clean up for easier inspections of the export
TODO move the blend file into a subfolder, but don't move too early when baking multiple scenes?
"""

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_FINALIZE
from bake_v3.sbe_custom_properties import SBE_TEMP_CLI_BAKE_PROP, SBE_OBJECT_BAKE_SOURCE_PROP
from bake_v3.sbe_util import retrieve_temp
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.sbe_collection_util import delete_collection_hierarchy
from bake_v3.sbe_sound import success_sound

def delete_empty_collections():
    """Clean up empty collection left by joining meshes for easier navigation"""
    empty_collections: list[bpy.types.Collection] = []
    for i in bpy.data.collections:
        col: bpy.types.Collection = i
        if len(col.all_objects) == 0:
            empty_collections.append(col)
    delete_collection_hierarchy(empty_collections)

class SBE_Finalize(SBE_ExportOperatorBase):
    """Last step of bake to clean up blend files"""
    bl_idname = SBE_OP_FINALIZE
    bl_label = "Finalize export"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        delete_empty_collections()
        for i in context.screen.areas:
            area: bpy.types.Area = i
            if area.type != 'VIEW_3D':
                continue
            for j in area.spaces:
                space: bpy.types.Space = j
                if space.type != 'VIEW_3D':
                    continue
                view_space: bpy.types.SpaceView3D = space
                view_space.shading.type = 'SOLID'
                view_space.shading.light = 'FLAT'
                view_space.shading.color_type = 'TEXTURE'
                view_space.shading.show_xray = False
                view_space.shading.show_cavity = False
                view_space.shading.show_shadows = False
                view_space.shading.show_backface_culling = True
                view_space.shading.show_object_outline = True

        for i in context.scene.objects:
            obj: bpy.types.Object = i
            if SBE_OBJECT_BAKE_SOURCE_PROP in obj:
                obj.hide_set(state=True, view_layer=context.view_layer)

        bpy.ops.wm.save_as_mainfile()
        # TODO check if all gltfs exist and delete any other ones
        # TODO on changes to count call t4?
        if retrieve_temp(SBE_TEMP_CLI_BAKE_PROP) is not True:
            success_sound()
        SBE_Logger.print("================> !EXPORT FINISHED! <================")
