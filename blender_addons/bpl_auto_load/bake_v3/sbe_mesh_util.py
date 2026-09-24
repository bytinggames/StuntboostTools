# pylint: disable=import-error
import bpy
import bmesh
import mathutils
# pylint: enable=import-error

from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_name_parser import is_physics_material

def find_physics_material_slot_indices(obj: bpy.types.Object) -> list[int]:
    physics_materials: list[int] = []
    for j in obj.material_slots:
        mat_slot: bpy.types.MaterialSlot = j
        if is_physics_material(mat_slot.material):
            physics_materials.append(mat_slot.slot_index)
    return physics_materials


def delete_faces_by_material_indices(obj_mesh: bpy.types.Mesh, indices: list[int], invert: bool = False) -> None:
    """Remove all faces from their material indices"""
    if len(indices) == 0:
        return
    with SBE_Logger("delete_faces_by_material_indices"):
        obj_bmesh = bmesh.new()
        obj_bmesh.from_mesh(obj_mesh)
        obj_bmesh.faces.ensure_lookup_table()

        split_faces: list[bmesh.types.BMFace] = []
        if not invert:
            for i in obj_bmesh.faces:
                face: bmesh.types.BMFace = i
                if face.material_index in indices:
                    split_faces.append(face)
        else:
            for i in obj_bmesh.faces:
                face: bmesh.types.BMFace = i
                if face.material_index not in indices:
                    split_faces.append(face)

        bmesh.ops.delete(obj_bmesh, geom=split_faces, context='FACES')
        obj_bmesh.to_mesh(obj_mesh)
        obj_bmesh.free()


def split_by_material_indices(obj: bpy.types.Object, indices: list[int]) -> bpy.types.Object | None:
    """
    The object will be split and the new returned object will
    contain the geometry with the provided material slot indices.
    Unused materials will not be removed from either object.
    """
    if len(indices) == 0:
        return None
    with SBE_Logger("split_by_material_indices"):
        dest_obj: bpy.types.Object = obj.copy()
        dest_obj.data = dest_obj.data.copy()
        dest_obj.name = dest_obj.name

        delete_faces_by_material_indices(obj_mesh=obj.data, indices=indices)
        delete_faces_by_material_indices(obj_mesh=dest_obj.data, indices=indices, invert=True)
        assert len(obj.users_collection) == 1
        obj.users_collection[0].objects.link(dest_obj)
        return dest_obj


def join_without_materials(target: bpy.types.Object, sources: list[bpy.types.Object]) -> bpy.types.Object:
    """Simpler join which does not preserve materials and vertex groups"""
    with SBE_Logger("join_without_materials"):
        obj_bmesh = bmesh.new()
        for i in sources:
            obj: bpy.types.Object = i
            mat = obj.matrix_local
            obj.data.transform(mat)
            obj.matrix_local = mathutils.Matrix()
            obj_bmesh.from_mesh(obj.data)
        obj_bmesh.to_mesh(target.data)
        obj_bmesh.free()
        if target in sources:
            sources.remove(target)
        bpy.data.batch_remove(sources)
    return target


def join_complete(target: bpy.types.Object, sources: list[bpy.types.Object],
    context: bpy.types.Context) -> bpy.types.Object:
    """Wrapper for join with context override"""
    with SBE_Logger("join_complete"):
        if target not in sources:
            sources.append(target)
        assert target.scale[0] * target.scale[1] * target.scale[2] == 1, "Join target object is scaled"
        with context.temp_override(selected_editable_objects=sources, active_object=target):
            bpy.ops.object.join()
    return target


def fast_join(target: bpy.types.Object, sources: list[bpy.types.Object]) -> bpy.types.Object:
    """Attempt at a bmesh join, if this is causing trouble, use join_complete instead"""
    with SBE_Logger("fast_join"):
        target_mesh = target.data
        target_materials = set()
        source_obj_to_material_slots_map = {}

        for i in sources:
            obj: bpy.types.Object = i
            source_obj_to_material_slots_map[obj] = []
            for j in i.material_slots:
                slot: bpy.types.MaterialSlot = j
                target_materials.add(slot.material)
        if None in target_materials:
            target_materials.remove(None)
        target_materials = list(target_materials)
        target_materials.append(None)

        for i in sources:
            obj: bpy.types.Object = i
            cur_map = source_obj_to_material_slots_map[obj]
            for j in obj.material_slots:
                slot: bpy.types.MaterialSlot = j
                assert slot.slot_index == len(cur_map), "bad logic"
                index = target_materials.index(slot.material)
                assert index < len(target_materials), "bad logic2"
                cur_map.append(index)
        target_mesh.materials.clear()
        for i in target_materials:
            if i is not None:
                target_mesh.materials.append(i)
        target_materials = None

        for i in sources:
            obj: bpy.types.Object = i
            mat = obj.matrix_local
            obj.data.transform(mat)
            obj.matrix_local = mathutils.Matrix()

        temp_mesh = target_mesh.copy()
        target_bm = bmesh.new()
        target_bm.from_mesh(target_mesh)

        for i in sources:
            obj: bpy.types.Object = i
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            cur_map = source_obj_to_material_slots_map[obj]
            if not cur_map:
                SBE_Logger.print(f"No material on object {obj.name}")
                continue
            out_of_bounds = set()

            bm.faces.ensure_lookup_table()
            for face in bm.faces:
                if len(cur_map) <= face.material_index:
                    out_of_bounds.add(face.material_index)
                else:
                    face.material_index = cur_map[face.material_index]
            for j in list(out_of_bounds):
                SBE_Logger.print(f"Material index {j} on {obj.name} out of bounds {len(cur_map)}?")

            bm.to_mesh(temp_mesh)
            bm.free()

            # Join the remapped mesh into the target
            target_bm.from_mesh(temp_mesh)

        target_bm.to_mesh(target_mesh)
        target_bm.free()

        if target in sources:
            sources.remove(target)

        sources.extend([temp_mesh])
        bpy.data.batch_remove(sources)
    return target


def ensure_unique_data(obj: bpy.types.Object) -> None:
    """Copies the mesh data block if it has multiple users"""
    if not obj.data:
        return
    if  obj.data.users <= 1:
        return
    obj.data = obj.data.copy()


def ensure_outside_normals(obj: bpy.types.Object) -> None:
    """
    Some objects may have negative scale, so after joining the normals are flipped,
    which messes with the bake and in game visibility.
    """
    if obj.type != 'MESH':
        return
    if obj.scale.x * obj.scale.y * obj.scale.z >= 0:
        return

    ensure_unique_data(obj)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces, flip_multires=False)
    bm.to_mesh(obj.data)
    bm.free()


def convert_to_mesh(context: bpy.types.Context, objects: list[bpy.types.Object]) -> None:
    """Applies all modifiers and converts curves to meshes. Will not preserve current selection!"""
    with SBE_Logger("convert_to_mesh"):
        if len(objects) == 0:
            return

        temp_linked = []
        for i in objects[:]:
            obj: bpy.types.Object = i
            if obj not in context.selectable_objects:
                objects.remove(obj)
                continue
            obj.hide_set(state=False, view_layer=context.view_layer)
            if obj.name in context.scene.objects:
                continue
            temp_linked.append(obj)
            context.scene.collection.objects.link(obj)

        if len(objects) == 0:
            SBE_Logger.print("No selectable objects for mesh conversion!")
            return

        # Can't use context overrides for convert. won't work without active object either :/
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = objects[0]
        for i in objects:
            obj: bpy.types.Object = i
            ensure_unique_data(obj)
            if obj.hide_get():
                raise Exception(f"Object {obj.name} must be visible for this operation to work")
            for j in obj.modifiers:
                mod: bpy.types.Modifier = j
                if mod.show_viewport != mod.show_render:
                    # ensure everything visible in render mode should
                    # is in the applied mesh.
                    # bpy.ops.object.convert only cares about show_viewport
                    mod.show_viewport = mod.show_render
            obj.select_set(state=True, view_layer=context.view_layer)
        bpy.ops.object.convert(target='MESH')

        for i in temp_linked:
            obj: bpy.types.Object = i
            context.scene.collection.objects.unlink(obj)


def smart_project(context: bpy.types.Context, obj: bpy.types.Object, unwrap_method: str, margin: float = 0.0) -> None:
    """Runs smart UV projection on an object. This switches contexts and is pretty slow for many objects"""
    if len(obj.data.vertices) == 0:
        SBE_Logger.print("Can't unwrap object with no vertices " + obj.name)
        return
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    context.view_layer.objects.active = obj
    obj.select_set(state=True, view_layer=context.view_layer)

    bpy.ops.object.mode_set(mode='EDIT')
    context.scene.tool_settings.use_uv_select_sync = False # Maybe faster?

    bpy.ops.mesh.reveal()
    bpy.ops.mesh.select_all(action='SELECT')
    # bpy.ops.uv.select_all(action='SELECT')

    if unwrap_method == 'smart_project':
        bpy.ops.uv.smart_project(
            margin_method='FRACTION',
            island_margin=margin,
            rotate_method='AXIS_ALIGNED',
        )
    elif unwrap_method == 'unwrap':
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=margin)
    else:
        raise Exception(f"Object {obj.name} has unknown unwrap method {unwrap_method}")

    bpy.ops.object.mode_set(mode='OBJECT')
