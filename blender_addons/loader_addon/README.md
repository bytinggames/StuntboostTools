# BPL Blender Plugin Loader

Install `stuntboost_bpl.py` in Blender and select Choose STUNTBOOST Game in the addon preferences.

The loader creates a single `game` directory link besides the blender exe so everything is portable.
The loader will look for the `stuntboost_bpl_runtime.py` in the game folder which contains the bulk of the logic.
The runtime searches `bpl_auto_load` recursively for classes with `bpl_load` /
`bpl_unload` methods or a `bpl_auto_load` property. When Python Hot Reload is enabled, changed plugin modules are reloaded.

## User scripts
The runtime creates a `ScriptsLibrary` folder beside the blender exe and loads it after `bpl_auto_load`, using the same rules:
recursive `*.py` search, `.bplignore`, the Module Blacklist preference and Python Hot Reload.
Scripts must use the BPL convention; plain `register()` / `unregister()` addon modules are not loaded:

```python
import bpy

class MY_OT_Example(bpy.types.Operator):
    bl_idname = "my.example"
    bl_label = "Example"
    bpl_auto_load = True  # registered/unregistered by BPL

    def execute(self, _context):
        return {'FINISHED'}

class MY_Setup:
    @staticmethod
    def bpl_load():  # called on load, e.g. append menus or handlers
        pass

    @staticmethod
    def bpl_unload():  # must undo bpl_load
        pass
```

Every script in `ScriptsLibrary` runs automatically when Blender starts. Only put trusted scripts there!
Shipped tool folders come first on `sys.path`, so avoid module names that already exist in `bpl_auto_load`.
