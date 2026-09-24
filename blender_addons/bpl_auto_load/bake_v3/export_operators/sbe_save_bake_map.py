"""Only save the bakes without post processing."""

import os

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_util import get_filename_without_extension
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.sbe_operator_ids import SBE_OP_SAVE_BAKE_MAP
from bake_v3.sbe_custom_properties import (
    SBE_IMG_BAKE_DIRECT_PROP, SBE_IMG_BAKE_COMBINED_PROP,
)
from bake_v3.sbe_paths import get_texture_folder

COMPRESSION = 15 # too much is slow, this compresses ok
CHANNELS_RGBA = 'RGBA'

# PNG
COLOR_DEPTH = '8'
FILE_FORMAT = 'PNG'
FILE_EXTENSION = 'png'
CHANNELS_BW = 'BW'

# EXR
# COLOR_DEPTH = '16'
# FILE_FORMAT = 'OPEN_EXR'
# FILE_EXTENSION = 'exr'
# CHANNELS_BW = 'RGB'

EXR_CODEC = 'DWAB'
COLOR_MANAGEMENT = 'FOLLOW_SCENE' # 'OVERRIDE'
LINEAR_COLORSPACE_SETTINGS = 'sRGB'

def get_output_bake_map_directory() -> str:
    return get_texture_folder(get_filename_without_extension())


def get_output_bake_map_name(index: int, direct: bool, denoised: bool) -> str:
    texture_name = f"Bake{str(index)}"
    if direct:
        texture_name += "_DIRECT"
    if denoised:
        texture_name += "_Denoised"
    return texture_name


def get_output_bake_map_path(index: int, direct: bool, denoised: bool) -> str:
    folder = get_output_bake_map_directory()
    texture = get_output_bake_map_name(index, direct, denoised)
    texture += f".{FILE_EXTENSION}"
    result = os.path.join(folder, texture)
    return result


class SBE_SaveBake(SBE_ExportOperatorBase):
    """Directly saves the unprocessed bake."""
    bl_idname = SBE_OP_SAVE_BAKE_MAP
    bl_label = "Post process STUNTBOOST textures"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        context.scene.render.image_settings.file_format = FILE_FORMAT
        context.scene.render.image_settings.color_depth = COLOR_DEPTH
        context.scene.render.image_settings.compression = COMPRESSION

        for i in bpy.data.images:
            img: bpy.types.Image = i
            if SBE_IMG_BAKE_COMBINED_PROP in img:
                with SBE_Logger("Bake Save"):
                    context.scene.render.image_settings.color_mode = CHANNELS_RGBA
                    img_path = get_output_bake_map_path(img[SBE_IMG_BAKE_COMBINED_PROP], False, True)
                    img.save_render(
                        filepath=img_path,
                        scene=context.scene,
                        # quality=0 # doesn't matter?
                    )
                    img.filepath_raw = img_path
                    img.source = 'FILE'
                    # img.reload()
            if SBE_IMG_BAKE_DIRECT_PROP in img:
                with SBE_Logger("Bake Save"):
                    context.scene.render.image_settings.color_mode = CHANNELS_BW
                    img_path = get_output_bake_map_path(img[SBE_IMG_BAKE_DIRECT_PROP], True, True)
                    img.save_render(
                        filepath=img_path,
                        scene=context.scene,
                        # quality=0 # doesn't matter?
                    )
                    img.filepath_raw = img_path
                    img.source = 'FILE'
