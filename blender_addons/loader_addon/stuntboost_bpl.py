# TODO report reloads and errors in the UI
# TODO no restart when repo path is set
# TODO gather all paths first
# TODO manage deps properly https://www.indelible.org/ink/python-reloading/
# move out the debugger starter into sub plugin
# Auto self replace from repo version?

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
from bpy.types import AddonPreferences
from bpy.app.handlers import persistent
# pylint: enable=import-error

bl_info = {
    "name": "STUNTBOOST Blender Plugin Loader",
    "blender": (4, 3, 0),
    "version": (0,0,1),
    "category": "Generic",
    "author": "tobi"
}

BPL_ADDON_ID = "stuntboost_bpl"
BPL_AUTO_LOAD_PATH = ["blender_addons", "bpl_auto_load"] # subfolder for our sub-plugins

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
    debugger = False
    """Whether the debugger should start. TODO the debugger should be moved out here"""
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
        if (self.debugger) and hasattr(bpy.ops, "debug"):
            try:
                bpy.ops.debug.connect_debugger_vscode()
                self.debugger = False
            except Exception:
                pass
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


    def start_watching(self) -> None:
        if not bpy.app.background:
            bpy.app.timers.register(
                function=self.__check, first_interval=self.interval_seconds, persistent=True)
        self.__check()

    def stop_watching(self) -> None:
        try:
            if not bpy.app.background:
                bpy.app.timers.unregister(self.__check)
        except Exception:
            pass

    def unload_all(self) -> None:
        for module, _loader in self.modules.copy().items():
            self.__unload_module(module)
        self.files = {}
        self.modules = {}


BPL_MANAGER: ModuleManager = None

class BPL_Preferences(AddonPreferences):
    bl_idname = BPL_ADDON_ID

    stuntboost_repo_path: bpy.props.StringProperty(
        name="STUNTBOOST Repo (restart blender after changing)",
        subtype='FILE_PATH',
    )

    autostart_py_debugger: bpy.props.BoolProperty(
        name="Auto start Python debugger")
    revert_on_reload: bpy.props.BoolProperty(
        name="Revert File on Hot Reload", description="Restore original blend state when a python module is reloaded for faster debugging.")

    def draw(self, _context):
        layout = self.layout
        layout.label(text="STUNTBOOST BPL Preferences")
        layout.prop(self, "stuntboost_repo_path")
        layout.prop(self, "autostart_py_debugger")
        layout.prop(self, "revert_on_reload")
        layout.separator()
        layout.label(text="Loaded Modules")
        if BPL_MANAGER is not None:
            for module, _loader in BPL_MANAGER.modules.items():
                layout.label(text=module.__file__)

def get_repo_path() -> str:
    """THIS IS REFERENCED FROM OTHER ADDONS"""
    return bpy.context.preferences.addons[BPL_ADDON_ID].preferences.stuntboost_repo_path

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
    preferences: BPL_Preferences = bpy.context.preferences.addons[BPL_ADDON_ID].preferences
    repo_folder = preferences.stuntboost_repo_path
    auto_load_path = os.path.join(repo_folder, *BPL_AUTO_LOAD_PATH)
    print("BPL Auto Load folder: " + auto_load_path)
    if not os.path.exists(auto_load_path):
        return
    BPL_MANAGER = ModuleManager(auto_load_path, 1)
    BPL_MANAGER.debugger = preferences.autostart_py_debugger
    BPL_MANAGER.revert_on_reload = preferences.revert_on_reload
    BPL_MANAGER.start_watching()


def stop_bpl_and_unload() -> None:
    global BPL_MANAGER
    if BPL_MANAGER is None:
        return
    BPL_MANAGER.stop_watching()
    BPL_MANAGER.unload_all()
    del BPL_MANAGER
    BPL_MANAGER = None


def register():
    bpy.utils.register_class(BPL_Preferences)
    bpy.utils.register_class(BPL_Reload)
    start_bpl()


def unregister():
    stop_bpl_and_unload()
    bpy.utils.unregister_class(BPL_Preferences)
    bpy.utils.unregister_class(BPL_Reload)
