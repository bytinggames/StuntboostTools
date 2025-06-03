import os

# pylint: disable=import-error
import bpy
from bpy.app.handlers import persistent
# pylint: enable=import-error

CHECK_INTERVAL_SEC = 5

class AssetLibReloader():
    files: dict[str, float] = {}
    """Holds the absolute file path and a timestamp when the file was last changed"""

    def __get_files(self) -> list[str]:
        result = []
        for i in bpy.data.libraries:
            lib: bpy.types.Library = i
            result.append(lib.filepath)
        return result

    def __reload(self, lib_path: str) -> None:
        for i in bpy.data.libraries:
            lib: bpy.types.Library = i
            if lib.filepath == lib_path:
                print(f"Hot reloading {lib_path}")
                lib.reload()
                return
        print(f"Warning, could not hot reload library {lib_path}. Doesn't exist in current file.")

    def update(self):
        times = self.files
        self.files = {}
        for rel_path in self.__get_files():
            full_path = bpy.path.abspath(rel_path)
            current_modified_time = os.path.getmtime(full_path)
            if rel_path in times:
                if current_modified_time != times[rel_path]:
                    self.__reload(rel_path)
            self.files[rel_path] = current_modified_time

reloader = AssetLibReloader()

class SB_AssetLibHotReload:
    @staticmethod
    @persistent
    def poll_libraries():
        reloader.update()
        return CHECK_INTERVAL_SEC


    @staticmethod
    def bpl_load():
        if bpy.app.background:
            return
        bpy.app.timers.register(
            function=SB_AssetLibHotReload.poll_libraries,
            first_interval=CHECK_INTERVAL_SEC, persistent=True)

    @staticmethod
    def bpl_unload():
        if bpy.app.background:
            return
        bpy.app.timers.unregister(SB_AssetLibHotReload.poll_libraries)
