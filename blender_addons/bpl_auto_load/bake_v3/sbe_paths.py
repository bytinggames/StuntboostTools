"""All file paths referenced in the bake script are collected here"""

import os
import pathlib

# pylint: disable=import-error
import stuntboost_bpl_runtime
# pylint: enable=import-error


def get_repo_folder() -> str:
    """Return the developer repository or the selected tools root."""
    return stuntboost_bpl_runtime.get_repo_path()

def ensure_folder(path: str) -> None:
    """Recursively create folders for a given path"""
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)

EXPORT_CUSTOM_MAPS = os.path.isdir(stuntboost_bpl_runtime.get_game_path())
"""When the game folder exists, we're doing custom level exports."""

if EXPORT_CUSTOM_MAPS:
    if os.name == "nt":
        _app_data = os.environ["APPDATA"]
    else:
        _app_data = os.environ.get("XDG_CONFIG_HOME") or str(pathlib.Path.home() / ".config")
    _game_app_data = os.path.join(_app_data, "STUNTBOOST")
    _custom_maps_folder = os.path.join(_game_app_data, "custom_maps")


def get_export_folder(level_name: str) -> str:
    """Return full folder path where level should be saved to."""
    if EXPORT_CUSTOM_MAPS:
        return os.path.join(_custom_maps_folder, level_name)
    return os.path.join(get_repo_folder(), "SE/Content/Models/Export")


def get_texture_folder(level_name: str) -> str:
    """Return foll folder path wehere level textures should be saved to."""
    if EXPORT_CUSTOM_MAPS:
        return os.path.join(get_export_folder(level_name), "textures")
    return os.path.join(get_repo_folder(), "SE/Content/Models/Resources", level_name + ".export")

_props_folder = (
    os.path.join(stuntboost_bpl_runtime.get_game_path(), "StuntboostTools/assets/Models/Props")
    if EXPORT_CUSTOM_MAPS
    else os.path.join(get_repo_folder(), "SE/Content/Models/Props")
)

POSTPRO_BLEND_PATH = os.path.join(_props_folder, "PostProcessing.blend")
"""File used to append post processing node tree"""

PROPS_BLEND_PATH = os.path.join(_props_folder, "Props.blend")
"""File used to append materials and geometry node groups"""

EXPORT_BLEND_FOLDER = (
    os.path.join(_game_app_data, "build_blends") if EXPORT_CUSTOM_MAPS
    else os.path.join(get_repo_folder(), "SE/Content/Models/build_blends")
)
""".export blends will be saved here"""

LOG_FOLDER = (
    os.path.join(_game_app_data, "build_logs") if EXPORT_CUSTOM_MAPS
    else os.path.join(get_repo_folder(), "SE/Content/Models/build_logs")
)
"""Logfiles from bakes are saved here"""

# Node Group names

NODE_GROUP_IS_GAME_MESH='IsGameMesh'
"""True for meshes ending up in game"""

NODE_GROUP_IS_RELEASE_BAKE='IsReleaseBake'
"""True when doing a release bake"""

NODE_GROUP_IS_PREVIEW='IsPreview'
"""True when not in bake process"""
