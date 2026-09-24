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

EXPORT_FOLDER = os.path.join(get_repo_folder(), "SE/Content/Models/Export")
"""Gltfs will land here"""

TEXTURE_FOLDER = os.path.join(get_repo_folder(), "SE/Content/Models/Resources")
"""Bake maps will land here"""

POSTPRO_BLEND_PATH = os.path.join(get_repo_folder(), "SE/Content/Models/Props/PostProcessing.blend")
"""File used to append post processing node tree"""

PROPS_BLEND_PATH = os.path.join(get_repo_folder(), "SE/Content/Models/Props/Props.blend")
"""File used to append post processing node tree"""

EXPORT_BLEND_FOLDER = os.path.join(get_repo_folder(), "SE/Content/Models/build_blends")
""".export blends will be saved here"""

LOG_FOLDER = os.path.join(get_repo_folder(), "SE/Content/Models/build_logs")
"""Logfiles from bakes are saved here"""

# Node Group names

NODE_GROUP_IS_GAME_MESH='IsGameMesh'
"""True for meshes ending up in game"""

NODE_GROUP_IS_RELEASE_BAKE='IsReleaseBake'
"""True when doing a release bake"""

NODE_GROUP_IS_PREVIEW='IsPreview'
"""True when not in bake process"""

# does Export folder exist?
if not os.path.isdir(EXPORT_FOLDER):
    game_path = stuntboost_bpl_runtime.get_game_path()

    if os.path.isdir(game_path):

        output_mod = os.path.join(game_path, "ContentMod")

        EXPORT_FOLDER = os.path.join(output_mod, "Models/Export")
        TEXTURE_FOLDER = os.path.join(output_mod, "Models/Resources")

        if not os.path.exists(EXPORT_FOLDER):
            os.makedirs(EXPORT_FOLDER)
        if not os.path.exists(TEXTURE_FOLDER):
            os.makedirs(TEXTURE_FOLDER)
