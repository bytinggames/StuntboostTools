"""
Sets up the material and textures for the exported visual mesh
"""

# pylint: disable=import-error
import bpy
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_TARGET_MATERIALS
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.sbe_collection_util import get_bake_collections
from bake_v3.sbe_custom_properties import (
    SBE_IMG_BAKE_COMBINED_PROP, SBE_IMG_BAKE_COMBINED_PROCESSED_PROP,
    SBE_IMG_BAKE_DIRECT_PROP, SBE_IMG_BAKE_DIRECT_PROCESSED_PROP,
    SBE_IMG_BAKE_AO_PROP, SBE_OBJECT_BAKE_TARGET_PROP
)
from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties

def create_image_node(material: bpy.types.Material, resolution: int, name: str, color_grid = False) -> bpy.types.ShaderNodeTexImage:
    node: bpy.types.ShaderNodeTexImage = material.node_tree.nodes.new('ShaderNodeTexImage')
    node.interpolation = 'Closest'

    if name in bpy.data.images:
        SBE_Logger.error(f"Image {name} already exists")
        node.image = bpy.data.images[name]
        return node

    if color_grid:
        # This is a little slower than below, but will add the checker gird for inspection of UVs
        # We could move this into a own operator and only call it in the inspection sequence
        # Not worth it at he moment
        bpy.ops.image.new(
            name=name, width=resolution, height=resolution,
            alpha=True, generated_type='COLOR_GRID', float=False)
        node.image = bpy.data.images[name]
    else:
        node.image = bpy.data.images.new(name=name, width=resolution, height=resolution)
    # node.image.colorspace_settings.name = maybe force other colorspace?
    # viewport preview and bake look quite different rn, partly expected because
    # different view angles but still.
    return node


class SBE_TargetMaterial(SBE_ExportOperatorBase):
    """Create material for bake targets"""
    bl_idname = SBE_OP_TARGET_MATERIALS
    bl_label = "Generate bake materials"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        bake_collections = get_bake_collections(context)

        for i in bake_collections:
            col: bpy.types.Collection = i
            for j in col.objects:
                obj: bpy.types.Object = j
                if SBE_OBJECT_BAKE_TARGET_PROP not in obj:
                    continue # skip over bake collections in another scene, can't bake across scenes
                index: int = obj[SBE_OBJECT_BAKE_TARGET_PROP]
                bake_props = SBE_CollectionProperties.evaluate_bake_prop(owner=col)
                resolution = int(bake_props.resolution * bake_props.resolution_relative)

                bake_material = bpy.data.materials.new("bake_mat_" + str(index))
                bake_material.use_nodes = True
                # principled should be in the node tree by default
                principled: bpy.types.ShaderNodeBsdfPrincipled = bake_material.node_tree.nodes['Principled BSDF']

                SBE_Logger.print(f"Bake Texture {col.name} at {resolution}px")

                combined_node = create_image_node(bake_material, resolution, "bake_" + str(index) + "_tex", color_grid=False)
                combined_node.image[SBE_IMG_BAKE_COMBINED_PROP] = index
                combined_node.location.x = -400
                combined_node.location.y = 0

                combined_processed_node: bpy.types.ShaderNodeTexImage = None
                if bake_props.post_process:
                    combined_processed_node = create_image_node(bake_material, resolution, "bake_processed_" + str(index) + "_tex", color_grid=True)
                    combined_processed_node.image[SBE_IMG_BAKE_COMBINED_PROCESSED_PROP] = index
                    combined_processed_node.location.x = -800
                    combined_processed_node.location.y = 0
                    # Will be used in the exported gltf
                    bake_material.node_tree.links.new(combined_processed_node.outputs['Color'], principled.inputs['Base Color'])
                else:
                    bake_material.node_tree.links.new(combined_node.outputs['Color'], principled.inputs['Base Color'])


                if bake_props.passes == 'COMBINED_AO_DIRECT': # This pass type is introduced in our custom blender build
                    # custom blender build will match "_DIRECT" in the name and save the direct light pass there
                    direct_node = create_image_node(bake_material, resolution, "bake_" + str(index) + "_tex_DIRECT")
                    direct_node.image[SBE_IMG_BAKE_DIRECT_PROP] = index
                    direct_node.location.x = -400
                    direct_node.location.y = -400

                    if bake_props.post_process:
                        # Lower case "_direct" spelling is important here, we can only have one node match each pass!
                        direct_processed_node = create_image_node(bake_material, resolution, "bake_processed_" + str(index) + "_tex_direct")
                        direct_processed_node.image[SBE_IMG_BAKE_DIRECT_PROCESSED_PROP] = index
                        direct_processed_node.location.x = -800
                        direct_processed_node.location.y = -400
                        # Specular tint controls realtime shadows in game
                        bake_material.node_tree.links.new(direct_processed_node.outputs['Color'], principled.inputs['Specular Tint'])
                    else:
                        bake_material.node_tree.links.new(direct_node.outputs['Color'], principled.inputs['Specular Tint'])

                    # custom blender build will match "_AO" in the name and save the direct light pass there
                    ao_node = create_image_node(bake_material, resolution, "bake_" + str(index) + "_tex_AO")
                    ao_node.image[SBE_IMG_BAKE_AO_PROP] = index
                    ao_node.location.x = -400
                    ao_node.location.y = -800

                assert len(obj.data.materials) == 0, "There should be no material left before joining"
                obj.data.materials.append(bake_material)

                # The bake step also sets the proper node active again
                # This is only needed so the solid viewport shows the checker texture
                if combined_processed_node:
                    bake_material.node_tree.nodes.active = combined_processed_node
