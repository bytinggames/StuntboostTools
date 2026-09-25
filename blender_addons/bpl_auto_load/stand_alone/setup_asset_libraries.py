"""Configure STUNTBOOST asset libraries and level storage on startup."""

import os

# pylint: disable=import-error
import bpy
import stuntboost_bpl_runtime
# pylint: enable=import-error


class SB_SetupAssetLibraries:
    @staticmethod
    def bpl_load():
        executable_folder = os.path.dirname(bpy.app.binary_path)
        os.makedirs(os.path.join(executable_folder, "levels"), exist_ok=True)
        libraries = bpy.context.preferences.filepaths.asset_libraries
        models_path = os.path.join(
            executable_folder, "game",
            "SE/Content/Models" if stuntboost_bpl_runtime.is_repo()
            else "StuntboostTools/assets/Models",
        )
        for name, folder in (
            ("StuntboostRooms", "Rooms"),
            ("StuntboostProps", "Props"),
        ):
            path = os.path.join(models_path, folder)
            library = libraries.get(name)
            if library is None:
                library = libraries.new(name=name, directory=path)
            else:
                library.path = path
            library.import_method = 'LINK'
            library.use_relative_path = True

    @staticmethod
    def bpl_unload():
        # Keep the folders and global preferences when the loader stops or reloads.
        pass

