"""
This will look at the current context and determine which collections to bake
When starting a bake in the outliner it will use the selected bake groups there.
If starting from any other view, the selected objects will be used to figure out
the groups to bake.
TODO local view isn't handled yet
"""

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_SKIP_GROUPS
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties
from bake_v3.sbe_custom_properties import SBE_TEMP_NO_SKIP_BAKE_PROP
from bake_v3.sbe_temp_storage import retrieve_temp


def set_bake_skip(collections: list[bpy.types.Collection], skip: bool):
    for i in collections:
        col: bpy.types.Collection = i
        props: SBE_CollectionProperties = SBE_CollectionProperties.get(col)
        props.skip_bake = skip

def print_bake(message: str, context: bpy.types.Context) -> None:
    SBE_Logger.print(message, cut_stack=2)
    for i in context.scene.collection.children:
        col: bpy.types.Collection = i
        props: SBE_CollectionProperties = SBE_CollectionProperties.get(col)
        SBE_Logger.print(f'\t{col.name}\t{"Skipped" if props.skip_bake else "=> Baked"}', cut_stack=2)

class SBE_SkipGroups(SBE_ExportOperatorBase):
    """Will look at the current context and skip bake groups based on it."""
    bl_idname = SBE_OP_SKIP_GROUPS
    bl_label = "Skip bake Groups"
    bpl_auto_load = True
    keep_selection = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        # because blender has one collection as a default below the scene collection
        # mark it at the bake collection for normal scenes for convenience.
        if not context.scene.name.startswith("//") and context.scene.name.find("Skybox") == -1:
            # The skybox has its own logic for bake collection fallbacks, so skip it here
            if len(context.scene.collection.children) == 1:
                col: bpy.types.Collection = context.scene.collection.children[0]
                props: SBE_CollectionProperties = SBE_CollectionProperties.get(col)
                props.is_bake_group = True

        if retrieve_temp(SBE_TEMP_NO_SKIP_BAKE_PROP) is True:
            # No skip logic on cli bakes at all
            return

        bake_collections: list[bpy.types.Collection] = []
        for i in context.scene.collection.children:
            col: bpy.types.Collection = i
            props: SBE_CollectionProperties = SBE_CollectionProperties.get(col)
            if not props.skip_bake:
                bake_collections.append(col)

        # all not already skipped collections will be until otherwise stated
        set_bake_skip(bake_collections, True)

        if context.area and context.area.type == 'OUTLINER':
            # When in outliner, look at the outliner selection
            if len(context.selected_ids) == 0:
                # no selection, bake all
                set_bake_skip(bake_collections, False)
            else:
                # only bake selected
                selected = []
                for i in context.selected_ids:
                    if not isinstance(i, bpy.types.Collection):
                        continue
                    col: bpy.types.Collection = i
                    if col not in bake_collections:
                        continue
                    selected.append(col)
                set_bake_skip(selected, False)
            print_bake("Using Outliner selection", context)
        else:
            selected_objects = context.selected_objects
            if len(selected_objects) == 0:
                # no selection, bake all
                set_bake_skip(bake_collections, False)
            else:
                for i in bake_collections:
                    col: bpy.types.Collection = i
                    for j in col.all_objects:
                        obj: bpy.types.Object = j
                        if obj in selected_objects:
                            props: SBE_CollectionProperties = SBE_CollectionProperties.get(col)
                            props.skip_bake = False
                            break
            print_bake("Using 3d View selection", context)
