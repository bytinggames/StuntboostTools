# pylint: disable=import-error
import bpy
# pylint: enable=import-error


class SB_ConvertBooster(bpy.types.Operator):
    """Convert old Booster"""
    bl_idname = "object.sb_quick_booster"
    bl_label = "Convert Booster"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context):
        if not context.active_object or context.active_object.type != 'MESH':
            return {'FINISHED'} # TODO poll function
        obj: bpy.types.Object = context.active_object
        obj.display_type = 'TEXTURED'
        obj.name = "#=Booster()"
        obj.modifiers.clear()
        obj.data.materials.clear()
        with context.temp_override(selected_editable_objects=[obj]):
            bpy.ops.object.transform_apply(scale=True, rotation=False)
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        bpy.ops.object.modifier_add_node_group(
            asset_library_type='CUSTOM', asset_library_identifier="Props", relative_asset_identifier="Props.blend/NodeTree/Booster")
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.lightmap_pack()
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}
