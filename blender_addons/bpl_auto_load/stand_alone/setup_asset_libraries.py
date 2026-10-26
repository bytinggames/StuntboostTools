"""Configure STUNTBOOST asset libraries and level storage on startup.

Every direct subfolder of the AssetLibrary folder beside Blender becomes its own
asset library named "StuntboostUser: <folder>".
"""

import os

# pylint: disable=import-error
import bpy
import stuntboost_bpl_runtime
# pylint: enable=import-error

USER_LIBRARY_PREFIX = "StuntboostUser: "


class SB_SetupAssetLibraries:
    @staticmethod
    def bpl_load():
        executable_folder = os.path.dirname(bpy.app.binary_path)
        os.makedirs(os.path.join(executable_folder, "levels"), exist_ok=True)
        # This folder might not exist in a normal blender build, we create it.
        user_library_path = os.path.join(executable_folder, "AssetLibrary")
        os.makedirs(user_library_path, exist_ok=True)
        libraries = bpy.context.preferences.filepaths.asset_libraries
        models_path = os.path.join(
            stuntboost_bpl_runtime.get_game_path(),
            "SE/Content/Models" if stuntboost_bpl_runtime.is_repo()
            else "StuntboostTools/assets/Models",
        )
        for name, folder in (
            ("StuntboostRooms", "Rooms"),
            ("StuntboostProps", "Props"),
        ):
            path = os.path.join(models_path, folder)
            if stuntboost_bpl_runtime.is_repo():
                path = os.path.realpath(path)
            SB_SetupAssetLibraries._ensure_library(libraries, name, path)
        SB_SetupAssetLibraries._sync_user_libraries(libraries, user_library_path)

    @staticmethod
    def _sync_user_libraries(libraries, user_library_path):
        # Keyed by path: Blender truncates library names to 63 characters.
        folders = {
            os.path.normpath(entry.path): entry.name
            for entry in sorted(os.scandir(user_library_path), key=lambda entry: entry.name)
            if entry.is_dir() and not entry.name.startswith(".")
        }
        # Drop libraries of removed folders and the former single root library.
        for library in list(libraries):
            if library.name == "StuntboostUser" or (
                library.name.startswith(USER_LIBRARY_PREFIX)
                and os.path.normpath(library.path) not in folders
            ):
                libraries.remove(library)
        existing = {
            os.path.normpath(library.path): library
            for library in libraries
            if library.name.startswith(USER_LIBRARY_PREFIX)
        }
        for path, folder_name in folders.items():
            library = existing.get(path)
            if library is None:
                library = libraries.new(name=USER_LIBRARY_PREFIX + folder_name, directory=path)
            SB_SetupAssetLibraries._apply_library_settings(library)

    @staticmethod
    def _ensure_library(libraries, name, path):
        library = libraries.get(name)
        if library is None:
            library = libraries.new(name=name, directory=path)
        else:
            library.path = path
        SB_SetupAssetLibraries._apply_library_settings(library)

    @staticmethod
    def _apply_library_settings(library):
        library.import_method = 'LINK'
        library.use_relative_path = True

    @staticmethod
    def bpl_unload():
        # Keep the folders and global preferences when the loader stops or reloads.
        pass

