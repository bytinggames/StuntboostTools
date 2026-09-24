"""
Custom property names used to attach additional data to objects.
These are used to share information between operators and are only relevant while the scripts are running.
If an operator attaches a property only for its own usage, they won't be defined here.

Naming conventions is SBE_{DATA BLOCK TYPE}_{NAME}_{PROP or ATTRIBUTE}
"""

SBE_TEMP_CLI_BAKE_PROP="sbe_temp_cli_bake"
"""
True when baking from the CLI, will override some settings the user
can set in blends to ensure a proper final bake
"""
SBE_TEMP_NO_SKIP_BAKE_PROP="sbe_temp_no_skip_bake_prop"
"""When set, no bake collection will be skipped"""

SBE_IMG_BAKE_COMBINED_PROP="SBE_IMG_BAKE_COMBINED_PROP"
"""Image data block will be tagged with this and store the bake group index as an int."""
SBE_IMG_BAKE_DIRECT_PROP="SBE_IMG_BAKE_DIRECT_PROP"
"""Image data block will be tagged with this and store the bake group index as an int."""
SBE_IMG_BAKE_AO_PROP="SBE_IMG_BAKE_AO_PROP"
"""Image data block will be tagged with this and store the bake group index as an int."""

SBE_IMG_BAKE_COMBINED_PROCESSED_PROP="SBE_IMG_BAKE_COMBINED_PROCESSED_PROP"
"""Image data block will be tagged with this and store the bake group index as an int."""
SBE_IMG_BAKE_DIRECT_PROCESSED_PROP="SBE_IMG_BAKE_DIRECT_PROCESSED_PROP"
"""Image data block will be tagged with this and store the bake group index as an int."""

# Tags are in the name of the object/collection/modifier
# We try to avoid putting any logic only needed in the bake in there
SBE_OBJECT_BAKE_TARGET_PROP="sbe_object_bake_target"
"""Name used to identify the generated bake target objects"""
SBE_OBJECT_BAKE_SOURCE_PROP="sbe_object_bake_source"
"""Name used to identify the generated bake source objects"""
SBE_MESH_UV_SCALE_ATTRIBUTE="sbe_mesh_uv_scale"
"""All vertices of bake geometry will have this custom attribute to scale the uvs"""
SBE_MESH_UV_ASPECT_ATTRIBUTE="sbe_mesh_uv_aspect"
"""Texture aspect ratio to ensure square pixels on the target bake atlas"""
SBE_OBJ_SMART_PROJECT_ATTRIBUTE="sbe_obj_smart_project"
"""TODO move this into a object/collection attribute"""

SBE_EXPORT_VERTEX_SHIFT_ATTRIBUTE="_color_shift"
"""Export name used in gltf"""
SBE_VERTEX_SHIFT_ATTRIBUTE="shift"
"""Outline shift directions defined in objects or generated"""
SBE_FORCE_VERTEX_SHIFT_ATTRIBUTE="force_shift"
"""Will bypass all shrinking, relative shifting etc and use the vertex colors as is"""

SBE_VERTEX_RANDOM_ATTRIBUTE="random"
"""Per object random used in shading, not exported to game"""

SBE_VERTEX_SPLIT_ID="sbe_split_id"
"""Vertex integer attribute, see below."""
SBE_GLOBAL_SPLIT_ID_NAME_MAP="sbe_split_id_names"
"""Holds an array of objects names which map to SBE_VERTEX_SPLIT_ID on the bake meshes to be split again after bake"""

SBE_GLOBAL_ORIGINAL_BLEND_PATH="sbe_global_original_blend_path"
"""
Holds the absolute path of the original blend file before the bake started.
This is not portable, but the export blends are not meant to be shared between pcs.
"""
