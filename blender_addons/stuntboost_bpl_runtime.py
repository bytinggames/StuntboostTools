"""
Most of the loader logic lives here, so it's not copied into
the blender prefernces folder where we can't update it.
"""
# TODO auto setup the libs when the symlinks exist

import sys
import os
import inspect
import importlib
import importlib.util
import pathlib
import glob
import types

# pylint: disable=import-error
import bpy
from bpy.app.handlers import persistent
# pylint: enable=import-error

BPL_ADDON_ID = "stuntboost_bpl"

BPL_LOAD_FUNC = "bpl_load"
BPL_UNLOAD_FUNC = "bpl_unload"
BPL_AUTO_LOAD_PROP = "bpl_auto_load"
"""If a class has this property set to true, it will be registered to blender"""

class ModuleManager:
    """Loads modules from file paths and keeps track of changes to reload them"""

    files: dict[str, float] = {}
    """Holds the absolute file path and a timestamp when the file was last changed"""
    modules: dict[types.ModuleType, list[object]] = {}
    """Holds the module type and the "loader classes" with the "bpl_load" functions or "bpl_auto_load" """
    interval_seconds: float = 10
    """Interval to check for file changes"""
    folder: str = ""
    """Folder to watch"""
    revert_on_reload = False
    """Whether to revert the current file on hot reload"""
    def __init__(self, folder: str, interval_seconds: float):
        self.interval_seconds = interval_seconds
        self.folder = folder

    def __get_files(self) -> list[str]:
        pattern_ignore = os.path.join(self.folder, "**", ".bplignore")
        result_ignore = []
        for i in glob.glob(pattern_ignore, recursive=True):
            result_ignore.append(os.path.dirname(i))

        pattern = os.path.join(self.folder, "**", "*.py")
        result = []
        for i in glob.glob(pattern, recursive=True):
            in_ignore = False
            for j in result_ignore:
                if i.find(j) != -1:
                    in_ignore = True
                    break
            if not in_ignore:
                result.append(i)
        return result

    def __load_module(self, full_module_path: str) -> int:
        loaded_count = 0
        try:
            path = pathlib.Path(full_module_path)
            if not path.is_file:
                print(f"BPL Filed to load {full_module_path}, not a .py file")
                return
            file_name = path.with_suffix("").name
            folder = str(path.parent)

            if folder not in sys.path:
                # print(f"BPL Added {folder} to sys.path")
                sys.path.append(folder)

            spec = importlib.util.spec_from_file_location(
                file_name, full_module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if module not in self.modules:
                self.modules[module] = []

            for name in dir(module):
                attr = getattr(module, name)
                if not inspect.isclass(attr):
                    continue

                if hasattr(attr, BPL_AUTO_LOAD_PROP):
                    bpy.utils.register_class(attr)
                    self.modules[module].append(attr)
                    loaded_count += 1
                    # print(f"BPL auto loaded module: {module.__name__} {attr.__name__}")
                elif hasattr(attr, BPL_LOAD_FUNC):
                    load_func = getattr(attr, BPL_LOAD_FUNC)
                    _ = getattr(attr, BPL_UNLOAD_FUNC)
                    load_func()
                    self.modules[module].append(attr)
                    loaded_count += 1
                    # print(f"BPL loaded module: {module.__name__} {attr.__name__}")
        except Exception as ex:
            print("BPL Failed to load " + full_module_path)
            print(ex)
            if module in self.modules:
                if len(self.modules[module]) == 0:
                    del self.modules[module]
        return loaded_count

    def __unload_module(self, module: types.ModuleType) -> None:
        if module not in self.modules:
            return
        for loader_class in self.modules[module]:
            if hasattr(loader_class, BPL_AUTO_LOAD_PROP):
                bpy.utils.unregister_class(loader_class)
            else:
                unload_func = getattr(loader_class, BPL_UNLOAD_FUNC)
                unload_func()
        del self.modules[module]

        for key, value  in sys.modules.items():
            # We can't use the name directly because it's missing package prefixes
            # which are not respected in importlib
            if not hasattr(value, "__file__"):
                continue
            if value.__file__ == module.__file__:
                del sys.modules[key]
                break
        del module # just to be sure?

    def __reload(self, full_path: str) -> int:
        for module in self.modules.copy().keys():
            loaded_file = module.__file__
            if loaded_file == full_path:
                if len(self.modules[module]) == 0:
                    return -1
                self.__unload_module(module)
        print(f"BPL reloading module: {full_path}")
        return self.__load_module(full_path)

    @persistent
    def __check(self):
        loaded_count = 0
        reload_count = 0
        for full_path in self.__get_files():
            current_modified_time = os.path.getmtime(full_path)
            if full_path in self.files:
                if current_modified_time != self.files[full_path]:
                    result = self.__reload(full_path)
                    if result == -1:
                        # until dependencies are tracked, we need a full reload
                        print("BPL full reload needed.")
                        self.unload_all()
                        return 0
                    reload_count += result
            else:
                loaded_count += self.__load_module(full_path)
            self.files[full_path] = current_modified_time
        if reload_count != 0 and self.revert_on_reload:
            try:
                bpy.ops.wm.revert_mainfile()
            except Exception:
                pass
        if (reload_count + loaded_count) != 0:
            print(f"BPL loaded {loaded_count} modules and reloaded {reload_count}.")
        return self.interval_seconds


    def start(self, watch_files: bool) -> None:
        self.__check()
        self.set_file_watching(watch_files)

    def set_file_watching(self, enabled: bool) -> None:
        registered = bpy.app.timers.is_registered(self.__check)
        if enabled and not bpy.app.background:
            if not registered:
                bpy.app.timers.register(
                    function=self.__check, first_interval=self.interval_seconds, persistent=True)
        elif registered:
            bpy.app.timers.unregister(self.__check)

    def unload_all(self) -> None:
        for module, _loader in self.modules.copy().items():
            self.__unload_module(module)
        self.files = {}
        self.modules = {}


BPL_MANAGER: ModuleManager = None

def set_file_watching(enabled: bool) -> None:
    if BPL_MANAGER is not None:
        BPL_MANAGER.set_file_watching(enabled)

def draw_preferences(preferences, _context):
    layout = preferences.layout
    layout.label(text=f"Repository: {get_repo_path()}")
    row = layout.row()
    row.enabled = preferences.watch_python_files
    row.prop(preferences, "revert_on_reload")
    layout.separator()
    layout.label(text="Loaded Modules")
    if BPL_MANAGER is not None:
        for module, _loader in BPL_MANAGER.modules.items():
            layout.label(text=module.__file__)

def get_repo_path() -> str:
    """Return the developer repository, or the selected tools root without one."""
    repo = pathlib.Path(bpy.app.binary_path).parent / "repo"
    if repo.is_dir():
        return str(repo.resolve())
    return str(pathlib.Path(__file__).resolve().parent.parent)

def get_game_path() -> str:
    """Return the game installation linked beside the Blender executable."""
    return str((pathlib.Path(bpy.app.binary_path).parent / "game").resolve())

class BPL_Reload(bpy.types.Operator):
    """Reload all modules"""
    bl_idname = "wm.bpl_reload"
    bl_label = "BPL Reload all"

    def execute(self, _context: bpy.types.Context):
        stop_bpl_and_unload()
        # start_bpl()
        return {'FINISHED'}


def start_bpl() -> None:
    global BPL_MANAGER
    preferences = bpy.context.preferences.addons[BPL_ADDON_ID].preferences
    auto_load_path = str(pathlib.Path(__file__).resolve().parent / "bpl_auto_load")
    print("BPL Auto Load folder: " + auto_load_path)
    if not os.path.isdir(auto_load_path):
        raise FileNotFoundError(f"BPL plugin folder not found: {auto_load_path}")
    BPL_MANAGER = ModuleManager(auto_load_path, 1)
    BPL_MANAGER.revert_on_reload = preferences.revert_on_reload
    BPL_MANAGER.start(preferences.watch_python_files)


def stop_bpl_and_unload() -> None:
    global BPL_MANAGER
    if BPL_MANAGER is None:
        return
    BPL_MANAGER.set_file_watching(False)
    BPL_MANAGER.unload_all()
    del BPL_MANAGER
    BPL_MANAGER = None


def register():
    bpy.utils.register_class(BPL_Reload)
    try:
        start_bpl()
    except Exception:
        unregister()
        raise


def unregister():
    stop_bpl_and_unload()
    bpy.utils.unregister_class(BPL_Reload)

