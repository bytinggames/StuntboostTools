"""currently disabled since it converts all boosters in the blend file. It should probably only go through selected objects"""

# pylint: disable=import-error
import bpy
import os
from bake_v3.sbe_paths import PROPS_BLEND_PATH
# pylint: enable=import-error


TARGET_PREFIX = "#=Booster()"
OLD_MOD_NAME = "BoosterAuto"
NEW_MOD_NAME = "Booster"
VALUE_KEY = "Socket_2"
ASSET_BLEND_PATH = PROPS_BLEND_PATH
NODETREE_PATH = os.path.join(PROPS_BLEND_PATH, "NodeTree")
    
def load_node_group(name):
    # Already loaded → reuse
    ng = bpy.data.node_groups.get(name)
    if ng:
        return ng

    # Append from external blend
    with bpy.data.libraries.load(ASSET_BLEND_PATH, link=False) as (data_from, data_to):
        if name in data_from.node_groups:
            data_to.node_groups = [name]
        else:
            return None

    return bpy.data.node_groups.get(name)

class SB_AutoBooster(bpy.types.Operator):
    """Auto Booster"""
    bl_idname = "object.sb_auto_booster"
    bl_label = "Auto Booster"
    # bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context):

        for obj in bpy.data.objects:

            # Check name prefix
            if not obj.name.startswith(TARGET_PREFIX):
                continue

            # Find the old modifier
            old_mod = None
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.name == OLD_MOD_NAME:
                    old_mod = mod
                    break

            if old_mod is None:
                self.report({'INFO'}, f"Skipping {obj.name}: no '{OLD_MOD_NAME}' modifier")
                continue

            # Read stored value
            try:
                value = old_mod[VALUE_KEY]
            except KeyError:
                self.report({'WARNING'}, f"{obj.name}: '{VALUE_KEY}' not found")
                continue

            # Remove old modifier
            obj.modifiers.remove(old_mod)

            # Get new node group
            node_group = load_node_group(NEW_MOD_NAME)
            if node_group is None:
                self.report({'ERROR'}, f"Node group '{NEW_MOD_NAME}' not found")
                return {'CANCELLED'}

            # Add new modifier
            new_mod = obj.modifiers.new(name=NEW_MOD_NAME, type='NODES')
            new_mod.node_group = node_group

            # Assign stored value
            try:
                new_mod[VALUE_KEY] = value
            except Exception as e:
                self.report({'WARNING'}, f"{obj.name}: could not set value ({e})")

            self.report({'INFO'}, f"Updated {obj.name}")

        return {'FINISHED'}