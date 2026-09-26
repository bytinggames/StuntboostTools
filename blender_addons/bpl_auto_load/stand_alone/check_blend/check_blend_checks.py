# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from check_blend.check_blend_types import ProblemItem


_GENERATED_TEXTURE_NODES = frozenset({
    'ShaderNodeTexBrick',
    'ShaderNodeTexChecker',
    'ShaderNodeTexGabor',
    'ShaderNodeTexGradient',
    'ShaderNodeTexMagic',
    'ShaderNodeTexNoise',
    'ShaderNodeTexVoronoi',
    'ShaderNodeTexWave',
})


def _output_linked(node: bpy.types.Node, name: str) -> bool:
    socket = node.outputs.get(name)
    return socket is not None and socket.is_linked


def check_nodes(tree: bpy.types.ShaderNodeTree, sources=None) -> list[ProblemItem]:
    problems: list[ProblemItem] = []
    if tree is None:
        return problems
    sources = [tree] if sources is None else sources

    for node in tree.nodes:
        objects = [*sources, node]
        if isinstance(node, bpy.types.ShaderNodeTexCoord):
            if _output_linked(node, 'UV'):
                problems.append(ProblemItem(
                    message="Implicit reference to active UV map.",
                    solution="Use a UV Map node with an explicit UV layer name.",
                    objects=objects, icon='UV', category='Materials'))
            if _output_linked(node, 'Generated'):
                problems.append(ProblemItem(
                    message="Generated coordinates can change during baking.",
                    solution="Use explicit UV coordinates or Object coordinates from a reference object outside the bake.",
                    objects=objects, icon='UV', category='Materials'))
            if _output_linked(node, 'Object') and node.object is None:
                problems.append(ProblemItem(
                    message="Object coordinates implicitly reference the baked object.",
                    solution="Choose a reference object outside the bake in the Texture Coordinate node.",
                    objects=objects, icon='UV', category='Materials'))
        elif isinstance(node, bpy.types.ShaderNodeUVMap):
            if not node.uv_map and _output_linked(node, 'UV'):
                problems.append(ProblemItem(
                    message="Implicit reference to active UV map.",
                    solution="Set an explicit UV layer name in the UV Map node.",
                    objects=objects, icon='UV', category='Materials'))
        elif node.bl_idname == 'ShaderNodeTexImage' or node.bl_idname in _GENERATED_TEXTURE_NODES:
            vector = node.inputs.get('Vector')
            if (vector is None or not vector.enabled or vector.is_unavailable or vector.is_linked
                    or not any(output.is_linked for output in node.outputs)):
                continue
            if node.bl_idname == 'ShaderNodeTexImage':
                problems.append(ProblemItem(
                    message="Image texture implicitly uses the active UV map.",
                    solution="Connect a UV Map node with an explicit UV layer name to Vector.",
                    objects=objects, icon='UV', category='Materials'))
            else:
                problems.append(ProblemItem(
                    message="Texture implicitly uses Generated coordinates.",
                    solution="Connect explicit UV coordinates or Object coordinates from a reference object outside the bake to Vector.",
                    objects=objects, icon='UV', category='Materials'))
    return problems


def _walk_node_trees(tree, sources, visited):
    pending = [(tree, sources)]
    while pending:
        current, path = pending.pop()
        if current is None or current.as_pointer() in visited:
            continue
        visited.add(current.as_pointer())
        yield current, path
        for node in reversed(current.nodes):
            if isinstance(node, bpy.types.ShaderNodeGroup) and node.node_tree is not None:
                pending.append((node.node_tree, [*path, node, node.node_tree]))


def check_materials() -> list[ProblemItem]:
    problems: list[ProblemItem] = []
    collision_trees = set()
    for material in bpy.data.materials:
        if material.name.startswith('C_'):
            for _tree, _sources in _walk_node_trees(material.node_tree, [], collision_trees):
                pass

    visited = set()
    for material in bpy.data.materials:
        if material.name.startswith('C_') or not material.use_nodes or material.node_tree is None:
            continue
        for tree, sources in _walk_node_trees(material.node_tree, [material, material.node_tree], visited):
            problems.extend(check_nodes(tree, sources))

    for group in bpy.data.node_groups:
        if group.type != 'SHADER' or group.as_pointer() in collision_trees:
            continue
        for tree, sources in _walk_node_trees(group, [group], visited):
            problems.extend(check_nodes(tree, sources))
    return problems


def check_multiple_parents() -> list[ProblemItem]:
    problems: list[ProblemItem] = []
    parents = {}
    seen = set()
    containers = [*bpy.data.collections, *(scene.collection for scene in bpy.data.scenes)]
    for parent in containers:
        pointer = parent.as_pointer()
        if pointer in seen:
            continue
        seen.add(pointer)
        for child in parent.children:
            parents.setdefault(child.as_pointer(), []).append(parent)

    for collection in bpy.data.collections:
        if len(parents.get(collection.as_pointer(), ())) > 1:
            problems.append(ProblemItem(
                message="Collection has multiple parents.",
                solution="Keep the collection under one parent, including scene roots, so export has an unambiguous hierarchy.",
                objects=[collection], icon='OUTLINER_COLLECTION', category='Collections'))

    for obj in bpy.data.objects:
        if not obj.users_collection:
            problems.append(ProblemItem(
                message="Object is not in any collection.",
                solution="Add the object to a collection or remove it if it is no longer needed.",
                objects=[obj], icon='OUTLINER_COLLECTION', category='Collections'))
        elif len(obj.users_collection) > 1:
            problems.append(ProblemItem(
                message="Object is in multiple collections.",
                solution="Keep the object in one collection so export has an unambiguous hierarchy.",
                objects=[obj], icon='OUTLINER_COLLECTION', category='Collections'))
    return problems


def check_uv_layers() -> list[ProblemItem]:
    problems: list[ProblemItem] = []
    for obj in bpy.data.objects:
        if obj.name.startswith('//') or '_<' in obj.name or '_#' in obj.name:
            continue
        if obj.type != 'MESH':
            continue
        if obj.material_slots and all(
                slot.material is not None and slot.material.name.startswith('C_')
                for slot in obj.material_slots):
            continue
        layers = obj.data.uv_layers
        if not layers:
            problems.append(ProblemItem(
                message="No UV map.",
                solution="Add a UV map to the visible mesh.",
                objects=[obj], icon='MOD_UVPROJECT', category='UV Maps'))
            continue
        if len(layers) > 1:
            problems.append(ProblemItem(
                message="Multiple UV layers.",
                solution="Use one UV layer for the export mesh.",
                objects=[obj], icon='MOD_UVPROJECT', category='UV Maps'))
        for layer in layers:
            if layer.name not in {'UVMap', 'smart_project'}:
                problems.append(ProblemItem(
                    message="Nonstandard UV layer name.",
                    solution="Name the layer 'UVMap', the legacy 'smart_project' name is also supported.",
                    objects=[obj, layer], icon='MOD_UVPROJECT', category='UV Maps'))
    return problems


def check_libraries() -> list[ProblemItem]:
    problems: list[ProblemItem] = []
    for obj in bpy.data.objects:
        if obj.instance_collection is None:
            continue
        library = obj.instance_collection.library
        if library is not None and library.is_missing:
            problems.append(ProblemItem(
                message="Instance library is missing.",
                solution="Restore or relocate the linked asset library.",
                objects=[obj], icon='LIBRARY_DATA_DIRECT', category='Libraries', severity='ERROR'))

    for library in bpy.data.libraries:
        if library.is_missing:
            problems.append(ProblemItem(
                message="Library is missing.",
                solution="Restore or relocate the linked library.",
                objects=[library], icon='LIBRARY_DATA_DIRECT', category='Libraries', severity='ERROR'))
    return problems


def check_names() -> list[ProblemItem]:
    problems: list[ProblemItem] = []
    # Blender 4.3 ID names have 63 UTF-8 bytes after the prefix and terminator.
    # Reserve four bytes for Blender's '.001' duplicate suffix.
    # TODO tk add a 5.x check here to the new 255 (?) limit
    byte_limit = 59
    for datablocks in (bpy.data.objects, bpy.data.collections):
        for datablock in datablocks:
            if datablock.name.startswith('/') and datablock.asset_data is not None:
                problems.append(ProblemItem(
                    message="Asset name starts with '/'.",
                    solution="Remove the leading '/' from the asset name to avoid filesystem path problems.",
                    objects=[datablock], icon='FILE_TEXT', category='Names'))
            byte_length = len(datablock.name.encode('utf-8'))
            if byte_length > byte_limit:
                problems.append(ProblemItem(
                    message=f"Name uses {byte_length} UTF-8 bytes (limit {byte_limit}).",
                    solution="Shorten the name to leave room for a '.001' duplicate suffix, non-ASCII characters may use multiple bytes.",
                    objects=[datablock], icon='FILE_TEXT', category='Names'))
    return problems


def check_no_materials() -> list[ProblemItem]:
    problems: list[ProblemItem] = []
    for obj in bpy.data.objects:
        if obj.type not in {'MESH', 'CURVE'}:
            continue
        if not obj.material_slots:
            problems.append(ProblemItem(
                message="No materials assigned.",
                solution="Assign a material to the object.",
                objects=[obj], icon='MATERIAL', category='Materials'))
            continue
        for index, slot in enumerate(obj.material_slots):
            if slot.material is None:
                problems.append(ProblemItem(
                    message=f"Empty material slot (index {index}, slot {index + 1}).",
                    solution="Assign a material to this slot or remove the unused slot.",
                    objects=[obj, slot], icon='MATERIAL', category='Materials'))
    return problems


ALL_CHECKS = [
    check_materials,
    check_uv_layers,
    check_names,
    check_libraries,
    check_multiple_parents,
    check_no_materials,
]
