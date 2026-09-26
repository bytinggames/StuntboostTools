"""All file paths referenced in the bake script are collected here"""

import os
import pathlib

# pylint: disable=import-error
import bpy
import stuntboost_bpl_runtime
# pylint: enable=import-error

from bake_v3.sbe_custom_properties import SBE_TEMP_CLI_BAKE_PROP
from bake_v3.sbe_temp_storage import retrieve_temp


def ensure_folder(path: str) -> None:
    """Recursively create folders for a given path"""
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)

def use_custom_map_export() -> bool:
    """Whether to use custom-map exports. Repository CLI bakes always use content paths."""
    if not stuntboost_bpl_runtime.is_repo():
        return True
    if retrieve_temp(SBE_TEMP_CLI_BAKE_PROP) is True:
        return False
    return bpy.context.preferences.addons[stuntboost_bpl_runtime.BPL_ADDON_ID].preferences.export_custom_maps


if os.name == "nt":
    _app_data = os.environ["APPDATA"]
else:
    _app_data = os.environ.get("XDG_CONFIG_HOME") or str(pathlib.Path.home() / ".config")
_game_app_data = os.path.join(_app_data, "STUNTBOOST")
_custom_maps_folder = os.path.join(_game_app_data, "custom_maps")


def get_export_folder(level_name: str) -> str:
    """Return full folder path where level should be saved to."""
    if use_custom_map_export():
        return os.path.join(_custom_maps_folder, level_name)
    return os.path.join(stuntboost_bpl_runtime.get_game_path(), "SE/Content/Models/Export")


def get_texture_folder(level_name: str) -> str:
    """Return foll folder path wehere level textures should be saved to."""
    if use_custom_map_export():
        return get_export_folder(level_name)
    return os.path.join(stuntboost_bpl_runtime.get_game_path(), "SE/Content/Models/Resources", level_name + ".export")

_props_folder = (
    os.path.join(stuntboost_bpl_runtime.get_game_path(), "StuntboostTools/assets/Models/Props")
    if not stuntboost_bpl_runtime.is_repo()
    else os.path.join(stuntboost_bpl_runtime.get_game_path(), "SE/Content/Models/Props")
)

POSTPRO_BLEND_PATH = os.path.join(
    _props_folder,
    "PostProcessing_blender_5.blend" if bpy.app.version[0] >= 5 else "PostProcessing.blend"
)
"""Version-compatible file used to append post processing node trees"""

PROPS_BLEND_PATH = os.path.join(_props_folder, "Props.blend")
"""File used to append materials and geometry node groups"""

EXPORT_BLEND_FOLDER = (
    os.path.join(_game_app_data, "build_blends") if not stuntboost_bpl_runtime.is_repo()
    else os.path.join(stuntboost_bpl_runtime.get_game_path(), "SE/Content/Models/build_blends")
)
""".export blends will be saved here"""

LOG_FOLDER = (
    os.path.join(_game_app_data, "build_logs") if not stuntboost_bpl_runtime.is_repo()
    else os.path.join(stuntboost_bpl_runtime.get_game_path(), "SE/Content/Models/build_logs")
)
"""Logfiles from bakes are saved here"""

# Node Group names

NODE_GROUP_IS_GAME_MESH='IsGameMesh'
"""True for meshes ending up in game"""

NODE_GROUP_IS_RELEASE_BAKE='IsReleaseBake'
"""True when doing a release bake"""

NODE_GROUP_IS_PREVIEW='IsPreview'
"""True when not in bake process"""
