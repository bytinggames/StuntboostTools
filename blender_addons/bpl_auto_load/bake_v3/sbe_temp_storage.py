"""Temporary bake state stored in window manager object."""

# pylint: disable=import-error
import bpy
# pylint: enable=import-error


def store_temp(key: str, value: any) -> None:
    """
    Store a session temporary global value. Not saved in blend and will be wiped when loading new blend.
    Types like lists will be converted to blender internal types!
    """
    bpy.data.window_managers['WinMan'][key] = value


def retrieve_temp(key: str) -> any:
    """Get a session temporary value previously set by store_temp, or None if nothing was stored"""
    if key in bpy.data.window_managers['WinMan']:
        return bpy.data.window_managers['WinMan'][key]
    return None