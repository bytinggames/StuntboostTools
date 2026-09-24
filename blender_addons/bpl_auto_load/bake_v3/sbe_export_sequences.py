"""Defines the order and which operators are used for full bake, fast bake and inspection"""


# pylint: disable=wildcard-import
# pylint: disable=unused-wildcard-import
from bake_v3.sbe_operator_ids import *
# pylint: enable=wildcard-import
# pylint: enable=unused-wildcard-import

FULL_BAKE_SEQUENCE = [
    SBE_OP_SKIP_GROUPS,
    SBE_OP_MAKE_LOCAL,
    SBE_OP_MAKE_REAL,
    SBE_OP_COMPATIBILITY,
    SBE_OP_PREPARE_MESHES,
    SBE_OP_SOURCE_MESHES,
    SBE_OP_TARGET_MESHES,
    SBE_OP_TARGET_MATERIALS,
    SBE_OP_SETUP_POST_PROCESS, # we do this early so if something goes wrong we don't wait for the long bake
    SBE_OP_PACK_UVS,
    SBE_OP_BAKE,
    SBE_OP_RUN_POST_PROCESS,
    SBE_OP_PRE_EXPORT,
    SBE_OP_EXPORT,
]
"""
The full bake sequence for a release bake with all the operators
on all scenes in the order they should be executed
"""

INSPECT_EXPORT = [
    SBE_OP_SKIP_GROUPS,
    SBE_OP_MAKE_LOCAL,
    SBE_OP_MAKE_REAL,
    SBE_OP_COMPATIBILITY,
    SBE_OP_PREPARE_MESHES,
    SBE_OP_SOURCE_MESHES, # disable this when not interested in source mesh, so inspection is faster
    SBE_OP_TARGET_MESHES,
    SBE_OP_TARGET_MATERIALS,
    SBE_OP_SETUP_POST_PROCESS,
    SBE_OP_PACK_UVS,
    SBE_OP_PRE_EXPORT,
]
"""This will skip the bake and export leaving the scene for inspection to help with debugging."""

FAST_BAKE_SEQUENCE = [
    SBE_OP_SKIP_GROUPS,
    SBE_OP_MAKE_LOCAL,
    SBE_OP_MAKE_REAL,
    SBE_OP_COMPATIBILITY,
    SBE_OP_PREPARE_MESHES,
    SBE_OP_SOURCE_MESHES,
    SBE_OP_TARGET_MESHES,
    SBE_OP_TARGET_MATERIALS,
    SBE_OP_FAST_PACK_UVS,
    SBE_OP_BAKE,
    SBE_OP_SAVE_BAKE_MAP,
    SBE_OP_PRE_EXPORT,
    SBE_OP_EXPORT,
]
"""TODO tk not used!!! Minimal bake sequence to get a level in the game."""
