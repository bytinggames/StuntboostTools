"""
Some logic shared between multiple steps.
"""

import os
import dis
import inspect
import csv
from functools import lru_cache

# pylint: disable=import-error
import bpy
import stuntboost_bpl_runtime
# pylint: enable=import-error

from bake_v3.sbe_custom_properties import (
    SBE_OBJECT_BAKE_TARGET_PROP, SBE_OBJECT_BAKE_SOURCE_PROP,
    SBE_TEMP_CLI_BAKE_PROP, SBE_GLOBAL_ORIGINAL_BLEND_PATH
)
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_paths import EXPORT_BLEND_FOLDER, POSTPRO_BLEND_PATH, ensure_folder
from bake_v3.sbe_temp_storage import retrieve_temp


def version_has_new_geo_nodes_accessor():
    """Blender 5 has a different geo node input/output API"""
    return 5 <= bpy.app.version[0]


def get_bake_target_objects(context: bpy.types.Context) -> list[bpy.types.Object]:
    return [i for i in context.scene.objects if SBE_OBJECT_BAKE_TARGET_PROP in i]


def get_bake_source_objects(context: bpy.types.Context) -> list[bpy.types.Object]:
    return [i for i in context.scene.objects if SBE_OBJECT_BAKE_SOURCE_PROP in i]

SBE_PERSISTENT_DATA_BLOCK="sbe_blend_storage_block"
"""Name of the persistent text data block"""


def ensure_saved_as_bake_blend() -> None:
    """Ensures the current file is saved as ".export" so the original won't be overwritten accidentally"""
    if not bpy.data.filepath:
        return # new unsaved file
    if is_export_file():
        return
    if retrieve_temp(SBE_TEMP_CLI_BAKE_PROP) is not True:
        # save current file first. except for cli bake, we don't want changes to blender when just baking them
        if os.access(bpy.data.filepath, os.W_OK):
            bpy.ops.wm.save_as_mainfile()
        else:
            SBE_Logger.print("Warning: blend file is read only, changes before bake can't be saved!")
    store_persistent(SBE_GLOBAL_ORIGINAL_BLEND_PATH, bpy.data.filepath)
    ensure_folder(EXPORT_BLEND_FOLDER)

    new_path = export_blend_path()
    bpy.ops.wm.save_as_mainfile(copy=False, check_existing=False, filepath=new_path)


def get_persistent_data_block() -> bpy.types.Text:
    if SBE_PERSISTENT_DATA_BLOCK not in bpy.data.texts:
        block = bpy.data.texts.new(SBE_PERSISTENT_DATA_BLOCK)
        block.from_string("This is a placeholder for the STUNTBOOST export plugin, don't delete it.")
        # Text blocks have fake users by default, so it shouldn't be needed to keep the block around
        # Also in some contexts, like drawing UI, setting properties isn't allowed
        # We might end up here from a UI call once, if the block didn't exist before
        return block
    else:
        return bpy.data.texts[SBE_PERSISTENT_DATA_BLOCK]

def store_persistent(key: str, value: any) -> None:
    """Stores data permanently in blend attach to a dummy text data block"""
    block = get_persistent_data_block()
    block[key] = value


def retrieve_persistent(key: str) -> any:
    """Get persistent data block value or None if non existent"""
    block = get_persistent_data_block()
    if key in block:
        return block[key]
    return None


def cut_out_room_id(filename: str) -> str:
    """
    remove the room index from filename
    example: Level_0_AirCrouch -> Level_AirCrouch
    """
    try:
        level_index = filename.index("Level_")
        if level_index == -1:
            return

        first_underscore_index = level_index + len("Level_") - 1
        second_underscore_index = filename.index("_", first_underscore_index + 1)
        if second_underscore_index != -1:
            str_between = filename[first_underscore_index + 1:second_underscore_index]
            if str_between.isnumeric():
                filename = filename[0:first_underscore_index] + filename[second_underscore_index:]
    except ValueError:
        pass # string not found, then skip this
    return filename


def get_filename_without_extension() -> str:
    """Returns the file name without path and without .blend or .export.blend"""
    file_name = bpy.path.display_name_from_filepath(bpy.data.filepath)

    # trim ".export" from exported name
    if file_name.lower().endswith(".export"):
        file_name = file_name[:len(file_name) - len(".export")]
    return cut_out_room_id(file_name)

def get_level_name(path: str) -> str:
    """Get the name of a level as referenced in game logic"""
    result = os.path.basename(path)
    result = cut_out_room_id(result)
    result = result.replace("Level_", "")
    result = os.path.splitext(result)[0]
    return result


def get_level_order() -> list[str]:
    """Get repository CSV level ordering, or no ordering for shipped games."""
    if not stuntboost_bpl_runtime.is_repo():
        return []
    repo_path: str = stuntboost_bpl_runtime.get_game_path()
    levels_dir = os.path.join(repo_path, "SE", "Content", "Other")
    level_order_csv = os.path.join(levels_dir, "Levels.csv")
    result = []
    levels = []
    columns = []

    # Read Levels.csv
    with open(level_order_csv, 'r', encoding="utf-8") as file:
        reader = csv.reader(file)
        temp = list(reader)
        columns = temp[0]
        levels = temp[1:]

    name_column_index = columns.index("Name")
    gltf_column_index = columns.index("Gltf")
    for i in levels:
        name = i[gltf_column_index]
        if not name:
            name = i[name_column_index]
        if name:
            result.append(name)
    return result


def is_export_file() -> bool:
    file_name = bpy.path.display_name_from_filepath(bpy.data.filepath)
    return file_name.lower().endswith(".export")

def export_blend_path() -> str:
    if is_export_file():
        return bpy.data.filepath
    file_name = bpy.path.display_name_from_filepath(bpy.data.filepath)
    path = os.path.join(EXPORT_BLEND_FOLDER, file_name + ".export.blend")
    return path


def execute_by_idname(bl_idname: str):
    """Execute a operator by bl_idname for convenience."""
    op_name = bl_idname.split(".")
    assert len(op_name) == 2, "Wrong amount of parts in bl_idname for operator"
    op_cat = getattr(bpy.ops, op_name[0])
    op = getattr(op_cat, op_name[1])
    return op()


def nameof(_) -> str:
    """
    Return the name of the provided variable, MIT licensed https://github.com/alexmojaki/nameof
    This is absolutely insane but at least I get type hints
    """
    frame = inspect.currentframe().f_back
    return _nameof(frame.f_code, frame.f_lasti)


@lru_cache()
def _nameof(code: inspect.types.CodeType, offset: int) -> str:
    instructions = list(dis.get_instructions(code))
    (current_instruction_index, current_instruction) = max(
        (
            (index, instruction)
            for index, instruction in enumerate(instructions)
            if instruction.offset <= offset
        ),
        key=lambda index_instruction: index_instruction[1].offset
    )
    assert current_instruction.opname in ("CALL", "CALL_FUNCTION", "CALL_METHOD"), "Did you call nameof in a weird way?"
    name_instruction = instructions[current_instruction_index - 1]
    if name_instruction.opname == "PRECALL":  # python 3.11
        name_instruction = instructions[current_instruction_index - 2]
    assert name_instruction.opname.startswith("LOAD_"), "Argument must be a variable or attribute"
    return name_instruction.argrepr


def set_cycles_visibility(obj: bpy.types.Object, visible: bool):
    """TODO this probably doesn't belong here"""
    obj.visible_camera = visible
    obj.visible_diffuse = visible
    obj.visible_glossy = visible
    obj.visible_shadow = visible
    obj.visible_transmission = visible
    obj.visible_volume_scatter = visible


def supports_multi_pass_bake(context: bpy.types.Context) -> bool:
    """Part of our blender fork saving AO and direct in the same material if textures ending in _AO and _DIRECT exist"""
    try:
        or_type = context.scene.cycles.bake_type
        # TODO there's probably a smarter way, like checking the enum prop, but I can't find it
        context.scene.cycles.bake_type = 'COMBINED_AO_DIRECT'
        context.scene.cycles.bake_type = or_type
        return True
    except Exception:
        pass
    return False


def supports_extend_early_bake_margin(context: bpy.types.Context) -> bool:
    """Part of our blender fork to extend borders before denoise to mitigate dark borders"""
    try:
        or_type = context.scene.render.bake.margin_type
        # TODO there's probably a smarter way, like checking the enum prop, but I can't find it
        context.scene.render.bake.margin_type = 'EXTEND_EARLY'
        context.scene.render.bake.margin_type = or_type
        return True
    except Exception:
        pass
    return False


def supports_spill_control(context: bpy.types.Context) -> bool:
    """Part of our blender fork to extend borders before denoise to mitigate dark borders"""
    try:
        org = context.scene.cycles.color_spill_strength
        context.scene.cycles.color_spill_strength = 3.123
        # TODO there's probably a smarter way, like checking the enum prop, but I can't find it
        context.scene.cycles.color_spill_strength = org
        return True
    except Exception:
        pass
    return False


def adapt_post_processing_libraries() -> None:
    """Reload legacy linked groups before making them local on Blender 5+."""
    if bpy.app.version[0] < 5:
        return

    for library in list(bpy.data.libraries):
        source_path = bpy.path.abspath(library.filepath)
        if os.path.basename(source_path).lower() != "postprocessing.blend":
            continue
        replacement_path = os.path.join(os.path.dirname(source_path), "PostProcessing_blender_5.blend")
        if not os.path.isfile(replacement_path):
            raise FileNotFoundError(f"Blender 5 post-processing library not found: {replacement_path}")
        SBE_Logger.print(f"Switching post-processing library to {replacement_path}")
        library.filepath = replacement_path
        library.reload()


def find_or_get_node_tree(node_group_name: str, blend_file: str, link = False) -> bpy.types.NodeTree | bpy.types.ShaderNodeTree | bpy.types.GeometryNodeTree:
    """Locate the node group by name or append/link it from the blend provided"""
    if blend_file == POSTPRO_BLEND_PATH:
        adapt_post_processing_libraries()
    if node_group_name in bpy.data.node_groups:
        return bpy.data.node_groups[node_group_name]

    props_blend_path = bpy.path.abspath(blend_file)
    if not os.path.isfile(props_blend_path):
        SBE_Logger.error(f"Could not find {props_blend_path}")
        return None

    with bpy.data.libraries.load(filepath=props_blend_path, link=link) as (data_from, data_to):
        if node_group_name in data_from.node_groups:
            data_to.node_groups.append(node_group_name)
        else:
            SBE_Logger.error(f"Failed to append {node_group_name} from {props_blend_path}")
            return None

    assert node_group_name in bpy.data.node_groups, "Logic error, the append should have worked"
    result = bpy.data.node_groups[node_group_name]
    if not link:
        result.asset_clear() # make sure it's not an asset any longer
    return result

def find_or_get_material(material_name: str, blend_file: str, link = False) -> bpy.types.NodeTree | bpy.types.ShaderNodeTree | bpy.types.GeometryNodeTree:
    """Locate the material by name or append/link it from the blend provided"""
    if material_name in bpy.data.materials:
        return bpy.data.materials[material_name]

    props_blend_path = bpy.path.abspath(blend_file)
    if not os.path.isfile(props_blend_path):
        SBE_Logger.error(f"Could not find {props_blend_path}")
        return None

    with bpy.data.libraries.load(filepath=props_blend_path, link=link) as (data_from, data_to):
        if material_name in data_from.materials:
            data_to.materials.append(material_name)
        else:
            SBE_Logger.error(f"Failed to append {material_name} from {props_blend_path}")
            return None

    assert material_name in bpy.data.materials, "Logic error, the append should have worked"
    result = bpy.data.materials[material_name]
    if not link:
        result.asset_clear() # make sure it's not an asset any longer
    return result


def set_node_group_value(node_group_name: str, value: bool) -> None:
    """Looks for a sbe_value bool node in geo node trees and sets the value accordingly."""
    is_preview_nodes = 0
    for i in bpy.data.node_groups:
        if not isinstance(i, bpy.types.GeometryNodeTree):
            continue
        tree: bpy.types.GeometryNodeTree = i
        if not tree.name.startswith(node_group_name):
            continue
        node_name = 'sbe_value'
        if node_name not in tree.nodes:
            SBE_Logger.error(f"{node_group_name} node group does not contain {node_name} node!")
            continue
        tree.nodes[node_name].boolean = value
        is_preview_nodes += 1

    if 1 < is_preview_nodes:
        SBE_Logger.print(f"Warning, multiple {node_group_name} node groups, consider remapping.")
