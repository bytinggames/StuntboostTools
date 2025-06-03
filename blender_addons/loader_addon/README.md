# BPL Blender Plugin Loader

After installing the plugin and setting the SE repo path in the plugin
preferences, it will search all classes in the `SE/blender_addons/bpl_auto_load`
folder recursively and call a static function `bpl_load` and `bpl_load` or look
for a `bpl_auto_load` property.

On File changes, the module will be reloaded and the function called again.
