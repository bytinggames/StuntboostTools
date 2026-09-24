# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from check_blend.check_blend_types import ProblemItem

def check_nodes(tree: bpy.types.ShaderNodeTree) -> list[ProblemItem]:
    problems: list[ProblemItem] = []

    for j in tree.nodes:
        node: bpy.types.Node = j
        if isinstance(node, bpy.types.ShaderNodeMath):
            # Don't check math nodes
            continue
        if isinstance(node, bpy.types.ShaderNodeTexCoord):
            tex_cord: bpy.types.ShaderNodeTexCoord = node
            if 0 < len(node.outputs['UV'].links):
                problems.append(ProblemItem(
                    message="Implicit reference to active UV map.",
                    solution="Use 'UV Map' node instead.",
                    objects=[tree, node], icon="UV"))
            elif tex_cord.object is None:
                problems.append(ProblemItem(
                    message="Generated UVs will be wrong during bake.",
                    solution="Reference a extra reference object which is not included in the bake in the Texture",
                    objects=[node], icon="UV"))
        elif isinstance(node, bpy.types.ShaderNodeUVMap):
            uv_node: bpy.types.ShaderNodeUVMap = node
            if uv_node.uv_map == "":
                problems.append(ProblemItem(
                    message="Implicit reference to active UV map.",
                    solution="Set a UV Map",
                    objects=[tree, node], icon="UV"))
        for k in node.inputs:
            if not isinstance(k, bpy.types.NodeSocketVector):
                continue
            vector_socket: bpy.types.NodeSocketVector = k
            if 0 < len(vector_socket.links):
                continue
            if vector_socket.name.lower() == "vector" and vector_socket.name.lower() == "uv":
                # This probably needs a few exceptions because not all vectors are UVs
                problems.append(ProblemItem(
                    message="Implicit reference to active UV map.",
                    solution="Connect a 'UV Map' node to the vector input",
                    objects=[tree, node], icon="NODETREE"))
    return problems


def check_materials() -> list[ProblemItem]:
    problems: list[ProblemItem] = []
    for i in bpy.data.materials:
        mat: bpy.types.Material = i
        if mat.name.startswith("C_"):
            continue
        if not mat.use_nodes:
            continue
        problems.extend(check_nodes(mat.node_tree))

    for i in bpy.data.node_groups:
        if i.type == 'SHADER': # 'GEOMETRY' is also in there
            problems.extend(check_nodes(i))
    return problems


def get_collection_parents(collection: bpy.types.Collection) -> list[bpy.types.Collection]:
    result: list[bpy.types.Collection] = []
    for i in bpy.data.collections:
        col: bpy.types.Collection = i
        if collection.name in col.children:
            result.append(col)
    return result


def check_multiple_parents() -> list[ProblemItem]:
    problems: list[ProblemItem] = []
    for i in bpy.data.collections:
        col: bpy.types.Collection = i
        parents = get_collection_parents(col)
        if 1 < len(parents):
            problems.append(ProblemItem(
                message="Collection has multiple parents",
                solution="Collection should only have one parent so the export works as expected.",
                objects=[col], icon="OUTLINER_COLLECTION"))

    for i in bpy.data.objects:
        obj: bpy.types.Object = i
        if len(obj.users_collection) == 0:
            problems.append(ProblemItem(
                message="Object not in any Collection",
                solution="Add the object to a collection or purge it from the file.",
                objects=[obj], icon="OUTLINER_COLLECTION"))
        if 1 < len(obj.users_collection):
            problems.append(ProblemItem(
                message="Object in multiple Collections",
                solution="Objects should only be in one collection so the export works as expected.",
                objects=[obj], icon="OUTLINER_COLLECTION"))
    return problems


def check_uv_layers() -> list[ProblemItem]:
    problems: list[ProblemItem] = []
    for i in bpy.data.objects:
        obj: bpy.types.Object = i
        if obj.name.find("_<") != -1:
            # TODO name parser
            continue
        if not hasattr(obj.data, "uv_layers"):
            continue
        if len(obj.data.uv_layers) == 0:
            problems.append(ProblemItem(
                message="No UV Map!",
                solution="Assign a uv map to the object",
                objects=[obj], icon="MOD_UVPROJECT"))
            continue
        if 1 < len(obj.data.uv_layers):
            problems.append(ProblemItem(
                message="Multiple UV layers.",
                solution="Only use one UV layer.",
                objects=[obj], icon="MOD_UVPROJECT"))
        if obj.data.uv_layers[0].name != "UVMap":
            # Is there still a point to smart project?
            if obj.data.uv_layers[0].name == "smart_project":
                continue
            problems.append(ProblemItem(
                message="Non standard UV Layer name.",
                solution="Make sure UV layers are only named 'UVMap'.",
                objects=[obj, obj.data.uv_layers[0]], icon="MOD_UVPROJECT"))
    return problems


def check_collision_shape() -> list[ProblemItem]:
    problems: list[ProblemItem] = []
    for i in bpy.data.collections:
        col: bpy.types.Collection = i
        if col.asset_data is None:
            continue
        # TODO check if all asset collections contain at least a collision shape
    return problems


def check_texture_sizes() -> list[ProblemItem]:
    # TODO check for large texture and warn
    return []


def check_libraries() -> list[ProblemItem]:
    problems: list[ProblemItem] = []
    for i in bpy.data.objects:
        obj: bpy.types.Object = i
        if obj.instance_collection:
            lib = obj.instance_collection.library
            if not lib or not lib.is_missing:
                continue
            problems.append(ProblemItem(
                message="Library missing",
                solution="Check whether there are any missing linked assets/libraries.",
                objects=[obj]))

    for i in bpy.data.libraries:
        lib: bpy.types.Library = i
        if lib.is_missing:
            problems.append(ProblemItem(
                message="Library missing",
                solution="Check whether there are any missing linked assets/libraries.",
                objects=[lib]))
    return problems


def check_names() -> list[ProblemItem]:
    problems: list[ProblemItem] = []
    # names internally are 66 chars, which includes the \0 terminator and some 2 char prefix
    # Since we need space for .001 on duplication so 59 should be enough
    char_limit = 66 - (1 + 2 + 4)
    for i in bpy.data.objects:
        obj: bpy.types.Object = i
        if obj.name.startswith("/") and obj.asset_data is not None:
            problems.append(ProblemItem(
                message="Asset name starts with /",
                solution="Don't start asset names with a '/' as this creates issues with filesystem paths.",
                objects=[obj], icon='FILE_TEXT'))
        if len(obj.name) <= char_limit:
            continue
        problems.append(ProblemItem(
            message="Name too long",
            solution="Use a shorter name so \".001\" etc. can be added on duplicates.",
            objects=[obj], icon='FILE_TEXT'))
    for i in bpy.data.collections:
        col: bpy.types.Collection = i
        if col.name.startswith("/") and col.asset_data is not None:
            problems.append(ProblemItem(
                message="Asset name starts with /",
                solution="Don't start asset names with a '/' as this creates issues with filesystem paths.",
                objects=[col], icon='FILE_TEXT'))
        if len(col.name) <= char_limit:
            continue
        problems.append(ProblemItem(
            message="Name too long",
            solution="Use a shorter name so \".001\" etc. can be added on duplicates.",
            objects=[col], icon='FILE_TEXT'))
    return problems


def check_materials_on_non_visible() -> list[ProblemItem]:
    """TODO no normal materials on non visible objects"""
    problems: list[ProblemItem] = []
    return problems

def check_no_materials() -> list[ProblemItem]:
    """Ensure no object is without materials"""
    problems: list[ProblemItem] = []
    for i in bpy.data.objects:
        obj: bpy.types.Object = i
        if obj.type != 'MESH' and obj.type != 'CURVE':
            continue
        if len(obj.material_slots) == 0:
            problems.append(ProblemItem(
                message="No Materials assigned",
                solution="Assign a material to the object.",
                objects=[obj], icon='FILE_TEXT'))
            continue
        for j in obj.material_slots:
            slot: bpy.types.MaterialSlot = j
            if slot.material is None:
                problems.append(ProblemItem(
                    message="Empty Material Slot",
                    solution="Assign a material to the slot.",
                    objects=[obj, slot], icon='FILE_TEXT'))
    return problems

ALL_CHECKS = [
    check_materials,
    check_uv_layers,
    check_collision_shape,
    check_names,
    check_libraries,
    check_multiple_parents,
    check_texture_sizes,
    check_materials_on_non_visible,
    check_no_materials
    # TODO check for non group normal usage
    # TODO check textures for nearest neighbor sampling
]
"""Add checks that should run here"""