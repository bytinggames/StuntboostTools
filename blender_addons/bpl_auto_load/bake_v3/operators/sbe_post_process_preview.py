"""
Operator to setup the realtime compositing to preview colorgrading or run the complete post processing step again.
"""


# pylint: disable=import-error
import bpy
# pylint: enable=import-error


from bake_v3.sbe_operator_ids import SBE_OP_PREVIEW_POST_PROCESS, SBE_OP_RUN_POST_PROCESS
from bake_v3.sbe_util import execute_by_idname, is_export_file, find_or_get_node_tree

from bake_v3.sbe_custom_properties import SBE_IMG_BAKE_COMBINED_PROCESSED_PROP
from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties
from bake_v3.sbe_paths import POSTPRO_BLEND_PATH

def post_color_grade_back(_context: bpy.types.Context):
    """TODO this should append the color grade node group from the export file back into the original file
    so the color grade isn't lost.
    """



def run_full_post_process(context: bpy.types.Context):
    """This will only work in a export file and will run the whole post process step again on the bake"""
    execute_by_idname(SBE_OP_RUN_POST_PROCESS)

    for i in bpy.data.images:
        if SBE_IMG_BAKE_COMBINED_PROCESSED_PROP in i:
            i.reload()

    # Set the active node in the materials to the processed bake texture so
    # the viewport show that
    for i in bpy.data.materials:
        mat: bpy.types.Material = i
        if not mat.node_tree:
            continue
        for j in mat.node_tree.nodes:
            if not isinstance(j, bpy.types.ShaderNodeTexImage):
                continue
            img: bpy.types.ShaderNodeTexImage = j
            if not SBE_IMG_BAKE_COMBINED_PROCESSED_PROP in img.image:
                continue
            mat.node_tree.nodes.active = img
    # Set viewport to shadeless textured
    for i in context.screen.areas:
        area: bpy.types.Area = i
        if area.type != 'VIEW_3D':
            continue
        for j in area.spaces:
            space: bpy.types.Space = j
            if space.type != 'VIEW_3D':
                continue
            view_space: bpy.types.SpaceView3D = space
            view_space.shading.type = 'SOLID'
            view_space.shading.light = 'FLAT'
            view_space.shading.color_type = 'TEXTURE'
            view_space.overlay.show_overlays = False
            view_space.shading.show_xray = False


def setup_realtime_post_process(context: bpy.types.Context):
    """Wire up the post processing nodes according to the scene settings."""
    bake_props = SBE_CollectionProperties.evaluate_bake_prop(owner=context.scene.collection)

    # post_pro_tree = find_or_get_node_tree(bake_props.post_process_node, POSTPRO_BLEND_PATH)
    # The post processing doesn't really work since we can't get AO and direct light here.
    # This is mostly interesting for the color grade.

    if not bake_props.color_grade_node:
        return # nothing todo here



    # These are copied from the bake step so the light matches as much as possible
    context.scene.cycles.use_adaptive_sampling = False

    context.scene.cycles.use_light_tree = True # causes brighter image
    context.scene.cycles.sampling_pattern = 'AUTOMATIC' # I think this uses blue noise?

    

    context.scene.render.compositor_device = 'GPU'
    compositor: bpy.types.CompositorNodeTree = None
    if hasattr(context.scene, "node_tree"):
        # blender 5.0 deprecated stuff
        context.scene.use_nodes = True
        compositor = context.scene.node_tree
    else:
        # I think auto tiling can't be disabled in 5.0? so set the size hight
        # context.scene.cycles.tile_size = 4096
        compositor = bpy.data.node_groups.new("SBE_Export_Compositor", "CompositorNodeTree")
        context.scene.compositing_node_group = compositor

    compositor.nodes.clear()

    color_grade_tree = find_or_get_node_tree(
        node_group_name=bake_props.color_grade_node,
        blend_file=POSTPRO_BLEND_PATH, link=True)

    color_grade_node = compositor.nodes.new("CompositorNodeGroup")
    color_grade_node.node_tree = color_grade_tree

    render_layer_node = compositor.nodes.new("CompositorNodeRLayers")
    render_layer_node.location.x = -400
    preview_node = compositor.nodes.new("CompositorNodeViewer")
    preview_node.location.x = 200
    output_node = compositor.nodes.new("CompositorNodeComposite")
    output_node.location.x = 200
    output_node.location.y = 200

    compositor.links.new(render_layer_node.outputs[0], color_grade_node.inputs[0])
    compositor.links.new(color_grade_node.outputs[0], preview_node.inputs[0])
    compositor.links.new(color_grade_node.outputs[0], output_node.inputs[0])
    
    # make sure walls and ceilings are visible
    execute_by_idname("object.sb_show_all")
    # then hide all collision and game logic things
    execute_by_idname("object.sb_hide_colliders")

    # TODO split compositor add 3d view and set it up.
    # context.window.workspace = bpy.data.workspaces['Compositing']
    # with context.temp_override(area=area):
    #     bpy.ops.screen.area_split(direction='VERTICAL', factor=0.3)


    for i in context.screen.areas:
        area: bpy.types.Area = i
        if area.type != 'VIEW_3D':
            continue
        for j in area.spaces:
            space: bpy.types.Space = j
            if space.type != 'VIEW_3D':
                continue
            view_space: bpy.types.SpaceView3D = space
            view_space.shading.type = 'RENDERED' # or MATERIAL
            view_space.shading.show_xray = False
            view_space.shading.use_compositor = 'ALWAYS'
            view_space.overlay.show_overlays = False
            view_space.lens = 24.0
            view_space.clip_start = 1.0
            view_space.clip_end = 1000.0





class SBEPreviewPostProcess(bpy.types.Operator):
    """Run the post process step and prepare the viewport"""
    bl_idname = SBE_OP_PREVIEW_POST_PROCESS
    bl_label = "Preview STUNTBOOST post processing"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context):
        if is_export_file():
            run_full_post_process(context=context)
        else:
            setup_realtime_post_process(context=context)
        return {'FINISHED'}
