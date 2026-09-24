# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_FAST_PACK_UVS
from bake_v3.sbe_util import get_bake_target_objects
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.sbe_mesh_util import smart_project
from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties

class SBE_PackUVs(SBE_ExportOperatorBase):
    """Setup the uvs for the generated bake mesh"""
    bl_idname = SBE_OP_FAST_PACK_UVS
    bl_label = "Fast Pack UVs"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        targets: list[bpy.types.Object] = get_bake_target_objects(context)
        for target in targets:
            collection = target.users_collection[0]
            bake_props = SBE_CollectionProperties.evaluate_bake_prop(owner=collection)
            resolution = int(bake_props.resolution * bake_props.resolution_relative)
            smart_project(context=context, obj=target, margin=((bake_props.margin / 2.0) / resolution), unwrap_method='unwrap')
