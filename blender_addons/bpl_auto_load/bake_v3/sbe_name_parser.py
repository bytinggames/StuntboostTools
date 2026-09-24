"""
Names contain a lot of logic, all the parsing should be here so it's not duplicated.
Remove this once name system is phased out
"""

import re
from dataclasses import dataclass

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_custom_properties import (
    SBE_OBJECT_BAKE_TARGET_PROP, SBE_OBJECT_BAKE_SOURCE_PROP
)

def in_bake_target(obj: bpy.types.Object) -> bool:
    if SBE_OBJECT_BAKE_SOURCE_PROP in obj:
        return False
    if obj.type != 'MESH' and obj.type != 'CURVE' and obj.type != 'FONT':
        return False
    return obj.sbe_properties.visibility == 'VISIBLE'

def in_bake_source(obj: bpy.types.Object) -> bool:
    if SBE_OBJECT_BAKE_TARGET_PROP in obj:
        return False
    if obj.type != 'MESH' and obj.type != 'CURVE' and obj.type != 'FONT':
        return False
    return obj.sbe_properties.visibility == 'VISIBLE' or obj.sbe_properties.visibility == 'ONLY_BAKE'

def only_in_bake_source(obj: bpy.types.Object) -> bool:
    return obj.sbe_properties.visibility == 'ONLY_BAKE'

def only_in_game_visible(obj: bpy.types.Object) -> bool:
    if obj.type != 'MESH':
        return False
    if not obj.name.startswith("/") and obj.name.find("°") != -1:
        return obj.name.find("_<") == -1 and obj.name.find("_#") == -1
    return False

def collection_is_discard(col: bpy.types.Collection) -> bool:
    return col.name.startswith("//")

def collection_is_only_bake(col: bpy.types.Collection) -> bool:
    return col.name.startswith("/") and not col.name.startswith("//")

def object_is_discard(obj: bpy.types.Object) -> bool:
    return obj.name.startswith("//")

def object_is_only_bake(obj: bpy.types.Object) -> bool:
    if obj.name.startswith("/") and not obj.name.startswith("//"):
        return True
    return obj.name.find("*") != -1

def scene_is_discard(scene: bpy.types.Scene) -> bool:
    return scene.name.startswith("//")

def name_starts_with_independent_of_comment(name, startswith):
    return name.startswith(startswith) or name.startswith("/" + startswith) or name.startswith("//" + startswith)

def prevent_join(obj: bpy.types.Object) -> bool:
    """Returns true for everything that should not be joined for export"""
    if obj.name.find("=Transparent") != -1:
        return True
    if obj.name.find("=Booster") != -1:
        return True
    if obj.users_collection[0].name.find("prevent_join") != -1:
        return True
    return False


def shadow_group_name(bake_group_name: str, obj: bpy.types.Object) -> str:
    name = obj.name
    if name.find("DynamicShadow(") == -1:
        return None
    name = strip_duplicate_post_fix(name)
    name = strip_comment(name)
    name = name.split("=")[1]
    bake_group_name = clean_name(bake_group_name)
    return f"{bake_group_name}={name}"


def object_is_only_game(obj: bpy.types.Object) -> bool:
    if not obj.name.startswith("/") and obj.name.find("°") != -1:
        return True
    return obj.name.find("_<") != -1 or obj.name.find("_#") != -1

def object_is_solid_collision(obj: bpy.types.Object) -> bool:
    return obj.name.find("<") != -1

def object_is_trigger_collision(obj: bpy.types.Object) -> bool:
    return obj.name.find("#") != -1

def is_physics_material(mat: bpy.types.Material | None) -> bool:
    return mat is not None and mat.name.startswith("C_")


def is_no_export_modifier(mod: bpy.types.Modifier) -> bool:
    return mod.name.find("no_export") != -1 or mod.name.startswith("/")


def is_delete_physics(collection: bpy.types.Collection) -> bool:
    return collection.name.find('delete_collisions') != -1

def get_physics_replacement_material(collection: bpy.types.Collection) -> bpy.types.Material | None:
    name: str = strip_comment(collection.name)
    name: str = strip_duplicate_post_fix(name)
    parts = name.split("swap_collision_materials=")
    if len(parts) <= 1:
        return None
    assert len(parts) == 2, "Wrong number of string parts"
    material_name = parts[1]
    if material_name not in bpy.data.materials:
        SBE_Logger.print(f"Warning replacement material {material_name} not found.")
        return None
    return bpy.data.materials[material_name]


def get_name_replacer(collection: bpy.types.Collection) -> list[str] | None:
    name: str = strip_comment(collection.name)
    name: str = strip_duplicate_post_fix(name)
    find = "rename="
    if not name.startswith(find):
        return None
    args = name[len(find):]
    if len(args) <= 1:
        return None
    parts = args.split("|")
    assert len(parts) == 2, "Wrong number of replacer parts"
    return parts


def get_append_string(collection: bpy.types.Collection) -> str | None:
    name: str = strip_comment(collection.name)
    name: str = strip_duplicate_post_fix(name)
    parts = name.split("append_prop=")
    if len(parts) <= 1:
        return None
    assert len(parts) == 2, "Wrong number of string parts"
    return parts[1]


def append_property(obj: bpy.types.Object, prop: str) -> None:
    if obj.name.find(prop) != -1:
        return
    name: str = strip_comment(obj.name)
    name: str = strip_duplicate_post_fix(name)
    if name.endswith(")"):
        obj.name = name + "." + prop
    else:
        obj.name = name + "=." + prop

def needs_physics_mesh(obj: bpy.types.Object) -> bool:
    if prevent_join(obj):
        # if the object will be split after bake, then no need for a extra physics mesh, needed for boosters
        return False
    return obj.sbe_properties.visibility == 'VISIBLE' and obj.sbe_properties.physics != 'NONE'

def make_invisible_collision(obj: bpy.types.Object) -> None:
    name: str = strip_comment(obj.name)
    name: str = strip_duplicate_post_fix(name)
    if name.find("<") != -1:
        name = name.replace("<", "_<")
    elif name.find("#") != -1:
        name = name.replace("#", "_#")
    else:
        # Assume invisible collision otherwise
        parts = name.split("=")
        if len(parts) == 2:
            # physics act up when any properties are appended #245
            name = parts[0]
        name = name + "_<"
    obj.name = name
    obj.hide_render = True
    obj.display_type = 'WIRE'


def is_cut_collection(col: bpy.types.Collection) -> bool:
    return col.name.find("cut") != -1

def is_cutter(obj: bpy.types.Object) -> bool:
    return obj.name.startswith("//cut")


def strip_comment(name: str) -> str:
    if name.startswith("//"):
        return name
    comment_index = name.find('//')
    if comment_index == -1:
        comment_index = len(name)

    # we can only remove the .001 comment, if there is no = sign. otherwise it could be that .001 is an argument
    dot_index = len(name)
    if name.find('=') == -1:
        dot_index = name.find('.')
        if dot_index == -1:
            dot_index = len(name)
    end = min(comment_index,dot_index)
    if end == len(name):
        return name
    return name[:end]

def strip_duplicate_post_fix(name: str) -> str:
    """Strip numeric post fix for duplicate names e.g. .001 """
    result = re.search("\\d\\d\\d$", name)
    if result:
        cropped = name.rstrip(name[-4:])
        parts = cropped.split("=")
        if len(parts) == 2:
            if len(parts[1]) < 4:
                return name
            else:
                return cropped
        else:
            return cropped
    return name

def strip_comment_and_post_fix(name: str) -> str:
    name: str = strip_comment(name)
    name: str = strip_duplicate_post_fix(name)
    return name

def clean_name(name: str) -> str:
    name = strip_duplicate_post_fix(name)
    name = strip_comment(name)
    parts = name.split("=")
    if len(parts) == 2:
        return parts[0]
    return name

def is_sky_box(obj: bpy.types.Object) -> bool:
    return obj.name.find("=Skybox()") != -1

def get_bake_collection_scale(col: bpy.types.Collection) -> float:
    name: str = strip_comment(col.name)
    name: str = strip_duplicate_post_fix(name)
    float_str = ""
    if name.find("bake_group") != -1:
        parts = name.split("bake_group=")
        if len(parts) != 2:
            return 1.0
        float_str = parts[1]
    else:
        parts = name.split("bake_size=")
        if len(parts) != 2:
            return 1.0
        float_str = parts[1]
    try:
        return float(float_str)
    except Exception:
        SBE_Logger.print(f"Failed to parse bake group scale for {col.name}")
        return 1.0


def is_bake_group(col: bpy.types.Collection) -> float:
    name: str = strip_comment(col.name)
    name: str = strip_duplicate_post_fix(name)
    return name.find("bake_group") != -1


def get_function_arguments(full_name, function_name):
    name = strip_comment(full_name)
    if name.startswith('/') and not name.startswith('//'):
        name = name[1:]
    if name == function_name or name.startswith(function_name + '='):
        function_name += '='
        if not name.startswith(function_name):
            return []
        arguments = name[len(function_name):]
        if len(arguments) == 0:
            return []
        return arguments.split('|')
    return None

@dataclass
class BakeScaleVertexGroup():
    group: bpy.types.VertexGroup
    index: int
    scale: float


def get_bake_scale_vertex_groups(obj: bpy.types.Object) -> list[BakeScaleVertexGroup]:
    result: list[BakeScaleVertexGroup] = []
    for i in obj.vertex_groups:
        group: bpy.types.VertexGroup = i
        name: str = group.name
        prefix = "bake_size="
        if not name.startswith(prefix):
            continue
        name: str = strip_comment(name)
        name: str = strip_duplicate_post_fix(name)
        parts = name.split(prefix)
        if len(parts) != 2:
            SBE_Logger.print(f"Failed to parse vertex group {group.name} on object {obj.name}")
            continue
        result.append(BakeScaleVertexGroup(group=group, index=group.index, scale=float(parts[1])))
    return result
