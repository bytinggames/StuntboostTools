"""Final .gltf export. This step is non destructive and can be repeated."""

import json
import os

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_EXPORT
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_util import get_filename_without_extension
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.sbe_collection_util import get_all_bake_collections, get_bake_collections
from bake_v3.sbe_paths import use_custom_map_export, ensure_folder, get_export_folder

class SBE_ExportLevel(SBE_ExportOperatorBase):
    """Export the level to .gltf"""
    bl_idname = SBE_OP_EXPORT
    bl_label = "Export STUNTBOOST level"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        # I had some crashes in the export, so save here just in case
        if not bpy.data.filepath:
            return
        bpy.ops.wm.save_as_mainfile()

        blend_name = get_filename_without_extension()
        custom_map_export = use_custom_map_export()
        export_folder = bpy.path.abspath(get_export_folder(blend_name))
        ensure_folder(export_folder)

        bake_collections = get_bake_collections(context)
        all_bake_collections = get_all_bake_collections()

        for i, collection in enumerate(all_bake_collections):
            if collection not in bake_collections:
                continue # Only export what was scheduled for bake

            filename = f"{blend_name}_{i}.gltf"
            target_path = os.path.join(export_folder, filename)
            SBE_Logger.print(f"Export to {target_path}")

            # apparently the context override doesn't work here
            # There's also the option of using the selected collection as a export filter
            # But the mono game pipeline breaks at that point
            # context.view_layer.active_layer_collection = context.view_layer.layer_collection.children[collection.name]
            bpy.ops.export_scene.gltf(
                filepath=target_path,
                export_format='GLTF_SEPARATE',
                use_active_collection=False,
                # use_active_collection_with_nested=True,
                use_selection=False,
                use_visible=False,
                use_renderable=False,

                # This is important, because otherwise
                # the active scene can be wrong and selected objects from others scenes will be exported too
                use_active_scene=True,
                collection=collection.name,

                export_yup=True,
                export_apply=True, # apply modifiers
                will_save_settings=False,
                export_cameras=True, # for exporting PreviewCameras
                # this forces the textures to be next to the gltf for custom levels so they're portable
                export_keep_originals=not custom_map_export,
                export_texture_dir="",
                export_materials='EXPORT',
                export_image_format='AUTO',
                export_force_sampling=True,
                # or 'NLA_TRACKS' or 'ACTIONS' 'SCENE' maybe we don't need to bake nla actions before then?
                export_animation_mode='ACTIONS',
                export_bake_animation=True,
                export_optimize_animation_size=False,
                export_lights=True,
                export_extras=True, # We want to move the name logic in here
                export_attributes=True, # this ensures exporting attributes starting with an '_'
                export_vertex_color='NONE', # we only need our custom _color_shift attribute, so disable this
                export_all_vertex_colors=False, # we only need our custom _color_shift attribute, so disable this 
                export_active_vertex_color_when_no_material=False, # we only need our custom _color_shift attribute, so disable this
                export_unused_images=False,
                export_unused_textures=False,
            )

        filename = os.path.join(export_folder, blend_name + "_.json")
        try:
            metadata = {}
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                if not isinstance(metadata, dict):
                    raise ValueError("Level sidecar must contain a JSON object")
            metadata["modelCount"] = len(all_bake_collections)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False)
        except Exception as e:
            SBE_Logger.print(f"Failed to open {filename} for export")
            SBE_Logger.print(str(e))
        # TODO check if the written file count matches what's actually on disk
