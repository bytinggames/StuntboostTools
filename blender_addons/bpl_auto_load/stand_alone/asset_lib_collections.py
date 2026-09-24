# pylint: disable=import-error
import bpy
# pylint: enable=import-error

# quick setup function for props
# - set up function for colliders
# - duplicate current object
# - change name accordingly
# - dummy plastic physics material
# - set to wireframe
# - parent to main object to keep transforms even when hidden, will this cause issues when exporting?
# - add triangulate modifier


class SB_SetCollectionOffsetToSelection(bpy.types.Operator):
    """Sync offset of parent Collection to object"""
    bl_idname = "object.sb_collection_offset_to_selection"
    bl_label = "Sync offset of parent Collection to object"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        if context.active_object is None:
            return False
        return 0 < len(context.active_object.users_collection)

    def execute(self, context: bpy.types.Context) -> None:
        context.active_object.users_collection[0].instance_offset = context.active_object.location
        return {'FINISHED'}

class SB_CreateAssetCollection(bpy.types.Operator):
    """Create a collection marked as instance with the current selection as the contents"""
    bl_idname = "object.sb_create_collection_asset"
    bl_label = "Create Asset Collection"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.active_object is not None or len(context.selected_objects) != 0

    def execute(self, context: bpy.types.Context) -> None:
        main_obj: bpy.types.Object = None
        if context.active_object is not None:
            main_obj = context.active_object
        elif len(context.selected_objects) != 0:
            main_obj = context.selected_objects[0]

        collection = bpy.data.collections.new(main_obj.name)

        old_collection = main_obj.users_collection[0]
        old_collection.children.link(collection)
        for i in context.selected_objects[:]:
            obj: bpy.types.Object = i
            obj.users_collection[0].objects.unlink(obj)
            collection.objects.link(obj)

        collection.instance_offset = main_obj.location

        collection.asset_mark()
        collection.asset_generate_preview()

        return {'FINISHED'}
