# BPL Blender Plugin Loader

Install `stuntboost_bpl.py` in Blender and select Choose STUNTBOOST Game in the addon preferences.

The loader creates a single `game` directory link besides the blender exe so everything is portable.
The loader will look for the `stuntboost_bpl_runtime.py` in the game folder which contains the bulk of the logic.
The runtime searches `bpl_auto_load` recursively for classes with `bpl_load` /
`bpl_unload` methods or a `bpl_auto_load` property. When Python Hot Reload is enabled, changed plugin modules are reloaded.
