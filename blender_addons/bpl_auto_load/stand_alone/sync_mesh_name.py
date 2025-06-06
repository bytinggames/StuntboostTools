"""
Uses the object name with "_mesh" appended as the mesh data block name.
"""

# pylint: disable=import-error
import bpy
# pylint: enable=import-error


class SBE_SyncMeshName(bpy.types.Operator):
    """Rename all meshes according to the object the belong to"""
    bl_idname = "object.sb_sync_mesh_names"
    bl_label = "Sync Mesh names to owning Object"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, _context: bpy.types.Context):
        for i in bpy.data.objects:
            obj: bpy.types.Object = i
            if obj.data is None:
                continue
            if not hasattr(obj.data, "name"):
                continue
            if hasattr(obj.data, "asset_data"):
                if obj.data.asset_data is not None:
                    continue
            if 1 < obj.data.users:
                return # only rename single user meshes
            try:
                obj.data.name = obj.name + "_mesh"
            except Exception as e:
                print(f"Renaming mesh of object {obj.name} failed with:")
                print(e)
        return {'FINISHED'}
