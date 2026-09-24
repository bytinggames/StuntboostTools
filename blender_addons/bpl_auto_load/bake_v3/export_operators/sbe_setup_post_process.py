"""Handles saving and post processing of the cycles bake output."""

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_SETUP_POST_PROCESS
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.sbe_collection_util import get_bake_collections, get_all_bake_collections
from bake_v3.sbe_custom_properties import (
    SBE_IMG_BAKE_COMBINED_PROP, SBE_IMG_BAKE_DIRECT_PROP,
    SBE_IMG_BAKE_AO_PROP
)
from bake_v3.sbe_util import find_or_get_node_tree

from bake_v3.export_operators.sbe_save_bake_map import (
    COLOR_DEPTH, COMPRESSION, FILE_FORMAT, CHANNELS_BW, CHANNELS_RGBA,
    COLOR_MANAGEMENT, EXR_CODEC,
    get_output_bake_map_directory, get_output_bake_map_name
)
from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties
from bake_v3.sbe_paths import POSTPRO_BLEND_PATH

GROUP_RESOLUTION_IN_SOCKET = "Resolution"
GROUP_AO_IN_SOCKET = "AO"
GROUP_COMBINED_IN_SOCKET = "Image"
GROUP_DIRECT_IN_SOCKET = "Direct"

GROUP_DIRECT_OUT_SOCKET = "Direct"
GROUP_COMBINED_OUT_SOCKET = "Combined"


def find_image_for_layer(index: int, tag: str) -> bpy.types.Image:
    for i in bpy.data.images:
        if tag in i and i[tag] == index:
            return i
    return None


def create_image_node_for_layer(compositor: bpy.types.CompositorNodeTree, index: int, tag: str, x: int = 0, y: int = 0) -> bpy.types.NodeSocket:
    """Create an image input node, point it to the bake map and return the output socket"""
    img_src = find_image_for_layer(index, tag)
    if img_src is None:
        return None
    img: bpy.types.CompositorNodeImage = compositor.nodes.new("CompositorNodeImage")
    img.location.x = x
    img.location.y = y
    img.image = img_src
    if img.image is None:
        SBE_Logger.print(f"Warning: Could not find bake image for layer {index} of type {tag}")
    return img.outputs['Image']


def create_output_node(compositor: bpy.types.CompositorNodeTree,
    out_folder: str, color_mode: str, x: int = 0, y: int = 0) -> bpy.types.CompositorNodeOutputFile:
    """Create a output node with the output folder and supplied formats"""
    file_out: bpy.types.CompositorNodeOutputFile = compositor.nodes.new("CompositorNodeOutputFile")
    file_out.location.x = x
    file_out.location.y = y
    if hasattr(file_out, "file_slots"):
        # blender 5.0 deprecated
        file_out.file_slots.clear()
        file_out.base_path = out_folder
    else:
        file_out.file_name = "" # slots have their own names
        file_out.directory = out_folder
        if FILE_FORMAT == 'PNG':
            file_out.format.media_type = 'IMAGE'
        else:
            file_out.format.media_type = 'MULTI_LAYER_IMAGE'
        file_out.file_output_items.clear()

    file_out.format.file_format = FILE_FORMAT
    file_out.format.compression = COMPRESSION
    file_out.format.exr_codec = EXR_CODEC
    file_out.format.color_mode = color_mode
    file_out.format.color_depth = COLOR_DEPTH
    file_out.format.color_management = COLOR_MANAGEMENT
    # file_out.format.linear_colorspace_settings.name = LINEAR_COLORSPACE_SETTINGS
    
    return file_out


def add_out_slot(file_out: bpy.types.CompositorNodeOutputFile, name: str, out_type: str) -> bpy.types.NodeSocket:
    if hasattr(file_out, "file_slots"):
        # blender 5.0 deprecated
        return file_out.file_slots.new(name)
    else:
        file_out.file_output_items.new(out_type, name)
        return file_out.inputs[-2]


class SBE_PostProcess(SBE_ExportOperatorBase):
    """Runs postprocessing on the baked textures and saves them to disk"""
    bl_idname = SBE_OP_SETUP_POST_PROCESS
    bl_label = "Setup Post process STUNTBOOST textures"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        context.scene.render.compositor_device = 'GPU'
        context.scene.render.compositor_precision = 'FULL'

        compositor: bpy.types.CompositorNodeTree = None

        if hasattr(context.scene, "node_tree"):
            # blender 5.0 deprecated stuff
            context.scene.use_nodes = True
            compositor = context.scene.node_tree
            context.scene.cycles.use_auto_tile = False
            compositor.nodes.clear()
        else:
            # I think auto tiling can't be disabled in 5.0? so set the size hight
            # context.scene.cycles.tile_size = 4096
            compositor = bpy.data.node_groups.new("SBE_Export_Compositor", "CompositorNodeTree")
            context.scene.compositing_node_group = compositor

        # TODO the noise textures inside the post processing group
        # apparently are affected by this, i hope it's only the aspect ration
        # because this would mess up batch processing all textures if they
        # differ in resolutions
        context.scene.render.resolution_x = 4096
        context.scene.render.resolution_y = 4096

        out_folder = get_output_bake_map_directory()

        bake_collections = get_bake_collections(context)
        all_bake_collections = get_all_bake_collections()

        bw_file_out = create_output_node(compositor, out_folder, CHANNELS_BW, x=200, y=0)
        rgba_file_out = create_output_node(compositor, out_folder, CHANNELS_RGBA, x=200, y=-200)

        for i, _ in enumerate(all_bake_collections):
            collection: bpy.types.Collection = all_bake_collections[i]
            if collection not in bake_collections:
                continue # Only export what was scheduled for bake

            # Post processing node group
            bake_props = SBE_CollectionProperties.evaluate_bake_prop(owner=collection)

            processing_node: bpy.types.CompositorNodeGroup = compositor.nodes.new("CompositorNodeGroup")
            processing_node.location.x = -400
            processing_node.location.y = -400 * (i + 1)
            # We could reroute the signal or use the save_bake_map operator for no post process but this is more convenient.
            # Might be some performance to gain for fast bakes tho
            processing_node.mute = not bake_props.post_process
            post_pro_tree = find_or_get_node_tree(bake_props.post_process_node, POSTPRO_BLEND_PATH)
            processing_node.node_tree = post_pro_tree

            color_grade_node: bpy.types.CompositorNodeGroup = None
            if bake_props.color_grade_node:
                color_grade_tree = find_or_get_node_tree(bake_props.color_grade_node, POSTPRO_BLEND_PATH)
                if color_grade_tree:
                    color_grade_node = compositor.nodes.new("CompositorNodeGroup")
                    color_grade_node.node_tree = color_grade_tree
                    color_grade_node.location.x = 0
                    color_grade_node.location.y = -200 * (i + 1)

            # Connect group inputs to images
            if GROUP_COMBINED_IN_SOCKET in processing_node.inputs:
                socket = create_image_node_for_layer(compositor, i, SBE_IMG_BAKE_COMBINED_PROP, x=-600, y=processing_node.location.y)
                compositor.links.new(socket, processing_node.inputs[GROUP_COMBINED_IN_SOCKET])

            if GROUP_AO_IN_SOCKET in processing_node.inputs:
                socket = create_image_node_for_layer(compositor, i, SBE_IMG_BAKE_AO_PROP, x=-800, y=processing_node.location.y)
                if socket is not None:
                    compositor.links.new(socket, processing_node.inputs[GROUP_AO_IN_SOCKET])

            if GROUP_DIRECT_IN_SOCKET in processing_node.inputs:
                socket = create_image_node_for_layer(compositor, i, SBE_IMG_BAKE_DIRECT_PROP, x=-1000, y=processing_node.location.y)
                if socket is not None:
                    compositor.links.new(socket, processing_node.inputs[GROUP_DIRECT_IN_SOCKET])

            if GROUP_RESOLUTION_IN_SOCKET in processing_node.inputs:
                resolution = int(bake_props.resolution * bake_props.resolution_relative)
                processing_node.inputs[GROUP_RESOLUTION_IN_SOCKET].default_value = resolution

            # Connect group outputs to the image out nodes
            if GROUP_COMBINED_OUT_SOCKET in processing_node.outputs:
                combined_name = get_output_bake_map_name(i, False, True)
                combined_out_socket = add_out_slot(rgba_file_out, combined_name, 'RGBA')
                if color_grade_node:
                    compositor.links.new(processing_node.outputs[GROUP_COMBINED_OUT_SOCKET], color_grade_node.inputs[0])
                    compositor.links.new(color_grade_node.outputs[0], combined_out_socket)
                else:
                    compositor.links.new(processing_node.outputs[GROUP_COMBINED_OUT_SOCKET], combined_out_socket)

            if GROUP_DIRECT_OUT_SOCKET in processing_node.outputs:
                direct_name = get_output_bake_map_name(i, True, True)
                direct_out_socket = add_out_slot(bw_file_out, direct_name, 'FLOAT')
                compositor.links.new(processing_node.outputs[GROUP_DIRECT_OUT_SOCKET], direct_out_socket)

