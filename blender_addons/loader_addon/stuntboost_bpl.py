import importlib.util
import os
from pathlib import Path
import stat
import sys
import tempfile
import traceback

import bpy

bl_info = {
    "name": "STUNTBOOST Blender Plugin Loader",
    "blender": (4, 3, 0),
    "version": (0, 0, 1),
    "category": "Generic",
    "author": "tobi",
}

_runtime = None
_load_error = ""
_RUNTIME_FILE = Path("blender_addons") / "stuntboost_bpl_runtime.py"


def has_game_tools(path):
    tools = path / "StuntboostTools" / "blender_addons"
    return (tools / _RUNTIME_FILE.name).is_file() and (tools / "bpl_auto_load").is_dir()


def find_game_path():
    if os.name == "nt":
        steam_roots = (
            Path("C:/Program Files (x86)/Steam"),
            Path("C:/Program Files/Steam"),
        )
    else:
        steam = Path.home() / ".steam"
        steam_roots = (steam / "steam", steam / "root", steam)
    for steam in steam_roots:
        game = steam / "steamapps" / "common" / "STUNTBOOST"
        if has_game_tools(game):
            return game
    return None


def load_runtime():
    global _runtime, _load_error
    root = Path(bpy.app.binary_path).parent
    if not os.path.lexists(root / "game"):
        try:
            game = find_game_path()
            if game is not None:
                set_game_path(game)
        except (OSError, ValueError) as exc:
            _load_error = f"Automatic game setup failed: {exc}. Ensure the Blender folder is writable."
            return
    path = root / "game" / "StuntboostTools" / _RUNTIME_FILE
    if not path.is_file():
        _load_error = "Tools not found. Choose the STUNTBOOST game folder or SE repository root below."
        return
    spec = importlib.util.spec_from_file_location("stuntboost_bpl_runtime", path)
    runtime = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runtime
    try:
        spec.loader.exec_module(runtime)
        runtime.register()
    except Exception as exc:
        sys.modules.pop(spec.name, None)
        _load_error = f"Could not load {path}: {exc}"
        traceback.print_exc()
        return
    _runtime = runtime
    _load_error = ""


def is_directory_link(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or (
        os.name == "nt" and info.st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT
    )


def set_game_path(target):
    link = Path(bpy.app.binary_path).parent / "game"
    target = target.resolve(strict=True)
    if not has_game_tools(target):
        raise ValueError("Choose a game folder containing StuntboostTools/blender_addons and its runtime and plugins.")
    if link.resolve() != target:
        if link.exists() and not is_directory_link(link):
            raise ValueError(f"Refusing to replace an existing file or directory: {link}")
        # Test permission errors first
        with tempfile.TemporaryDirectory(prefix=".stuntboost-link-", dir=link.parent) as temporary:
            replacement = Path(temporary) / "game"
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(str(target), str(replacement))
            else:
                replacement.symlink_to(target, target_is_directory=True)
            # Windows cannot replace a directory link directly.
            previous = Path(temporary) / "previous"
            if is_directory_link(link):
                link.rename(previous)
            try:
                replacement.rename(link)
            except OSError:
                if is_directory_link(previous):
                    previous.rename(link)
                raise


class BPL_SetGamePath(bpy.types.Operator):
    """Link game and load its tools on first-time setup"""
    bl_idname = "wm.bpl_set_game_path"
    bl_label = "Choose STUNTBOOST Game folder"

    directory: bpy.props.StringProperty(subtype='DIR_PATH', options={'SKIP_SAVE'})

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, _context):
        try:
            if not self.directory:
                raise ValueError("Choose the STUNTBOOST installation folder.")
            set_game_path(Path(bpy.path.abspath(self.directory)))
        except (OSError, ValueError) as exc:
            if isinstance(exc, PermissionError):
                message = f"Cannot write beside Blender. Use a writable Blender installation folder. {exc}"
            else:
                message = str(exc)
            self.report({'ERROR'}, message)
            return {'CANCELLED'}
        if _runtime is None:
            load_runtime()
            if _runtime is None:
                self.report({'ERROR'}, _load_error)
                return {'CANCELLED'}
            for window in _context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
            self.report({'INFO'}, "Game folder linked. STUNTBOOST tools loaded.")
        else:
            self.report({'INFO'}, "Game folder linked. Restart Blender to switch tools.")
        return {'FINISHED'}


class BPL_Preferences(bpy.types.AddonPreferences):
    bl_idname = "stuntboost_bpl"

    def update_hot_reload(self, _context):
        if _runtime is not None:
            _runtime.set_file_watching(self.watch_python_files)

    export_custom_maps: bpy.props.BoolProperty(
        name="Export as Custom Map",
        description=(
            "Force export to custom_maps folder. CLI bakes ignore this option! "
            "SAVE PREFERENCE if you want this to be respected in separate process bakes! "
        ),
        default=False,
    )

    watch_python_files: bpy.props.BoolProperty(
        name="Python Hot Reload",
        description="Watch plugin files for changes; when disabled, plugins only load when BPL starts",
        default=False,
        update=update_hot_reload,
    )

    module_blacklist: bpy.props.StringProperty(
        name="Module Blacklist",
        description=(
            "Comma-separated file names to exclude from BPL loading in any folder. "
            "Save preferences and restart Blender to apply changes"
        ),
        default="python_debugger.py, lfs_file_locking.py",
    )

    revert_on_reload: bpy.props.BoolProperty(
        name="Revert File on Hot Reload",
        description="Restore original blend state when a python module is reloaded for faster debugging.",
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        if _load_error:
            layout.label(text=_load_error, icon='ERROR')
        layout.label(text=f"Game: {(Path(bpy.app.binary_path).parent / 'game').resolve()}")
        layout.operator(BPL_SetGamePath.bl_idname, icon='FILE_FOLDER')
        if _runtime is None:
            layout.label(text="Tools load immediately after first-time setup.")
        else:
            layout.label(text="Restart Blender to switch to a different game folder.")
        layout.prop(self, "watch_python_files")
        layout.prop(self, "module_blacklist")
        if _runtime is not None:
            layout.separator()
            layout.label(text=f"Runtime: {_runtime.__file__}")
            _runtime.draw_preferences(self, context)


def register():
    bpy.utils.register_class(BPL_SetGamePath)
    bpy.utils.register_class(BPL_Preferences)
    load_runtime()


def unregister():
    global _runtime, _load_error
    if _runtime is not None:
        _runtime.unregister()
        sys.modules.pop(_runtime.__name__, None)
        _runtime = None
    _load_error = ""
    bpy.utils.unregister_class(BPL_Preferences)
    bpy.utils.unregister_class(BPL_SetGamePath)
