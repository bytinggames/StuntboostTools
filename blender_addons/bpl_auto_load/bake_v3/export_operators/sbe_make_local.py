# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_MAKE_LOCAL
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_name_parser import collection_is_discard
from bake_v3.sbe_collection_util import delete_collection_hierarchy
from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.sbe_util import adapt_post_processing_libraries

def check_missing() -> bool:
    block_lists = [
        bpy.data.meshes,
        bpy.data.objects,
        bpy.data.curves,
        bpy.data.collections,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.node_groups,
        bpy.data.cameras,
        bpy.data.fonts,
        bpy.data.libraries,
        bpy.data.lights,
        bpy.data.worlds,
        bpy.data.textures,
        bpy.data.metaballs,
        bpy.data.lattices,
        bpy.data.particles,
    ]
    # has_missing = False
    for block_list in block_lists:
        for i in block_list:
            block: bpy.types.ID = i
            if not block.is_missing:
                continue
            if block.library:
                SBE_Logger.error(f"Missing Data block {repr(block)} from {block.library.filepath}")
            else:
                SBE_Logger.error(f"Missing Data block {repr(block)}")
            # has_missing = True
    # if has_missing:
    #     raise Exception("Missing linked data blocks!")


class SBE_MakeLocal(SBE_ExportOperatorBase):
    """Pull in all the linked data into the current blend"""
    bl_idname = SBE_OP_MAKE_LOCAL
    bl_label = "Import linked libs and sever links."
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        if start.has_run:
            return # Only should run once

        adapt_post_processing_libraries()

        # We need to check for missing stuff before severing the library links,
        # otherwise we won't know where the missing data block was linked from.
        check_missing()

        # Blender will put all linked orphans into the currently active collection
        # so they don't get lost. We direct that to nothing, since we probably don't care.
        # at least for now
        with context.temp_override(collection=None):
            if bpy.ops.object.make_local.poll():
                # Move all linked references into file
                bpy.ops.object.make_local(type='ALL')
            else:
                SBE_Logger.error("Invalid context for bpy.ops.object.make_local")

        # In release this works fine, but in debug this triggers an assertion.
        # If this turns out to be a problem, we try batch_remove
        # This is also mostly used to avoid name collisions, but not completely necessary
        for i in bpy.data.libraries[:]:
            lib: bpy.types.Library = i
            bpy.data.libraries.remove(lib)

        # Get rid of anything unneeded as early as possible
        hidden_collections: list[bpy.types.Collection] = []
        for i in bpy.data.collections:
            col: bpy.types.Collection = i
            props: SBE_CollectionProperties = SBE_CollectionProperties.get(col)
            if props.visibility == 'DISCARD' or collection_is_discard(col):
                hidden_collections.append(col)
        delete_collection_hierarchy(hidden_collections)

        bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
