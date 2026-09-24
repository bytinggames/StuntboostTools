import os

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_RUN_POST_PROCESS
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.sbe_util import get_bake_target_objects

from bake_v3.export_operators.sbe_save_bake_map import (
    FILE_EXTENSION, get_output_bake_map_directory, get_output_bake_map_name
)

from bake_v3.sbe_custom_properties import (
    SBE_IMG_BAKE_COMBINED_PROCESSED_PROP, SBE_IMG_BAKE_DIRECT_PROCESSED_PROP, SBE_IMG_BAKE_COMBINED_PROP
)

from bake_v3.sbe_collection_util import get_bake_collections, get_all_bake_collections

def find_image_for_layer(index: int, tag: str) -> bpy.types.Image:
    for i in bpy.data.images:
        if tag in i and i[tag] == index:
            return i
    return None

def move_single_written_texture(out_folder: str, name: str, current_frame: str) -> str:
    desired_path = os.path.join(out_folder, name + "." + FILE_EXTENSION)

    if (bpy.app.version[0] <= 4):
        # blender 5.0 deprecated, doesn't append frame number any longer
        if os.path.isfile(desired_path):
            os.remove(desired_path)

        actual_path = os.path.join(out_folder, name + current_frame + "." + FILE_EXTENSION)
        os.rename(actual_path, desired_path)

    SBE_Logger.print(f"Saved image {desired_path}")
    return desired_path

def move_written_textures(context: bpy.types.Context) -> None:
    """Blender appends the current frame number when using output nodes in the compositor.
    This is annoying, but I want clean file names.
    also thinking about submitting a patch to blender for this."""

    current_frame: str = f"{context.scene.frame_current:04}"
    out_folder = get_output_bake_map_directory()

    bake_collections = get_bake_collections(context)
    all_bake_collections = get_all_bake_collections()

    for i, _ in enumerate(all_bake_collections):
        collection: bpy.types.Collection = all_bake_collections[i]
        if collection not in bake_collections:
            continue # Only move what was scheduled for bake

        combined_name = get_output_bake_map_name(i, False, True)
        new_combined_path = move_single_written_texture(out_folder, combined_name, current_frame)

        combined_img = find_image_for_layer(i, SBE_IMG_BAKE_COMBINED_PROCESSED_PROP)
        if not combined_img:
            # fallback to non processed image when not using post pro
            combined_img = find_image_for_layer(i, SBE_IMG_BAKE_COMBINED_PROP)

        combined_img.filepath_raw = new_combined_path
        combined_img.source = 'FILE'

        direct_img = find_image_for_layer(i, SBE_IMG_BAKE_DIRECT_PROCESSED_PROP)
        if direct_img is None:
            continue # image might not exist in certain configurations
        direct_name = get_output_bake_map_name(i, True, True)
        new_direct_path = move_single_written_texture(out_folder, direct_name, current_frame)
        direct_img.filepath_raw = new_direct_path
        direct_img.source = 'FILE'


class SBE_RunPostProcess(SBE_ExportOperatorBase):
    """Runs postprocessing on the baked textures and saves them to disk"""
    bl_idname = SBE_OP_RUN_POST_PROCESS
    bl_label = "Post process STUNTBOOST textures"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        context.scene.render.compositor_device = 'GPU'
        bpy.ops.render.render()
        move_written_textures(context)

        targets: list[bpy.types.Object] = get_bake_target_objects(context)
        for obj in targets:
            material: bpy.types.Material = obj.data.materials[0]
            for j in material.node_tree.nodes:
                if not isinstance(j, bpy.types.ShaderNodeTexImage):
                    continue
                img_node: bpy.types.ShaderNodeTexImage = j
                if SBE_IMG_BAKE_COMBINED_PROCESSED_PROP in img_node.image:
                    # The active node will be the target of the combined bake
                    material.node_tree.nodes.active = img_node
                    break
