"""
Operator running the bake and writing the results in the textures setup on the materials beforehand.
This step is non destructive and can be repeated.
The images will not be saved to disk here.
"""

# TODO the collection scheduled for bake should be store somewhere in the scene
# TODO use same names for image destination

# pylint: disable=import-error
import bpy
import cycles
# pylint: enable=import-error

from bake_v3.sbe_operator_ids import SBE_OP_BAKE
from bake_v3.sbe_custom_properties import SBE_IMG_BAKE_COMBINED_PROP
from bake_v3.sbe_logger import SBE_Logger
from bake_v3.sbe_util import (
    get_bake_target_objects, get_bake_source_objects, set_cycles_visibility
)
from bake_v3.sbe_export_operator_base import SBE_ExportOperatorBase, SBE_Operator_Start_Result
from bake_v3.properties.sbe_collection_props import SBE_CollectionProperties
from bake_v3.sbe_util import (
    supports_extend_early_bake_margin, supports_multi_pass_bake,
    supports_spill_control
)


def cycles_set_full_gi(cycles_settings: cycles.properties.CyclesRenderSettings) -> None:
    cycles_settings.max_bounces = 32
    cycles_settings.diffuse_bounces = 32
    cycles_settings.glossy_bounces = 32
    cycles_settings.transmission_bounces = 32
    cycles_settings.transparent_max_bounces = 32
    cycles_settings.volume_bounces = 32

    # cycles_settings.sample_clamp_indirect = 0.0
    # this can actually impact the brightness significantly when strong indirect light illuminates the scene
    # cycles_settings.sample_clamp_direct = 0.0

    cycles_settings.caustics_refractive = True # needed for decals?
    cycles_settings.caustics_reflective = True # optional
    cycles_settings.blur_glossy = 1.0


def cycles_use_optix(cycles_settings: cycles.properties.CyclesRenderSettings) -> None:
    try: 
        cycles_settings.use_denoising = True
        cycles_settings.denoiser = 'OPTIX'
        cycles_settings.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    except:
        cycles_use_oidn_fast(cycles_settings=cycles_settings)


def cycles_use_oidn_fast(cycles_settings: cycles.properties.CyclesRenderSettings) -> None:
    try:
        cycles_settings.use_denoising = True
        cycles_settings.denoiser = 'OPENIMAGEDENOISE'
        cycles_settings.denoising_input_passes = 'RGB'
        cycles_settings.denoising_prefilter = 'NONE'
        cycles_settings.denoising_quality = 'FAST'
        cycles_settings.denoising_use_gpu = True
    except:
        pass


def cycles_use_oidn(cycles_settings: cycles.properties.CyclesRenderSettings) -> None:
    cycles_settings.use_denoising = True
    cycles_settings.denoiser = 'OPENIMAGEDENOISE'
    cycles_settings.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    cycles_settings.denoising_prefilter = 'ACCURATE'
    cycles_settings.denoising_quality = 'HIGH'
    cycles_settings.denoising_use_gpu = True

class SBE_Bake(SBE_ExportOperatorBase):
    """Will bake all target bake meshes set up"""
    bl_idname = SBE_OP_BAKE
    bl_label = "Bake STUNTBOOST level"
    bpl_auto_load = True

    def execute_internal(self, context: bpy.types.Context, start: SBE_Operator_Start_Result):
        # context.scene.unit_settings.scale_length = 1.0
        # with context.temp_override(selected_editable_objects=context.view_layer.objects):
        #     bpy.ops.transform.resize(value=(0.01, 0.01, 0.01), center_override=(0,0,0))

        context.scene.render.engine = 'CYCLES'
        context.scene.cycles.device = 'GPU'

         # TODO benchmark, this also brightens the image slightly?
        context.scene.cycles.use_light_tree = True

        # I think this uses blue noise?
        context.scene.cycles.sampling_pattern = 'AUTOMATIC'

        # No Tiling is faster but requires the whole buffer to be in vram
        # blender 5.0 deprecated, since this can't be disabled 
        # we can force the tile size to be bigger than the texture
        context.scene.cycles.use_auto_tile = False
        context.scene.cycles.tile_size = 1024 * 8

        supports_multi_pass = True
        if not supports_multi_pass_bake(context):
            supports_multi_pass = False
            SBE_Logger.print("Warning, multi pass bake with 'COMBINED_AO_DIRECT' not supported!")
            SBE_Logger.print("No fallback yet. AO and direct light will be missing!")

        margin_type = 'EXTEND_EARLY'
        if not supports_extend_early_bake_margin(context):
            margin_type = 'EXTEND'
            SBE_Logger.print("Warning, bake margin 'EXTEND_EARLY' not supported!")
            SBE_Logger.print("No fallback yet. There will be dark borders when denoising!")


        targets: list[bpy.types.Object] = get_bake_target_objects(context)
        sources: list[bpy.types.Object] = get_bake_source_objects(context)

        for target in targets:
            set_cycles_visibility(target, False) # TODO test if we even need this

        for target in targets:
            if len(target.data.vertices) == 0:
                continue

            collection = target.users_collection[0]

            bake_props = SBE_CollectionProperties.evaluate_bake_prop(owner=collection)

            if bake_props.samples == 0:
                continue # just skip the bake for 0 samples

            context.scene.cycles.samples = bake_props.samples

            # We force this off
            context.scene.cycles.use_adaptive_sampling = False

            SBE_Logger.print(f"Bake {collection.name} with {context.scene.cycles.samples} samples")
            if bake_props.denoise == 'OPTIX':
                cycles_use_optix(context.scene.cycles)
            elif bake_props.denoise == 'OPENIMAGEDENOISE':
                cycles_use_oidn(context.scene.cycles)
            else:
                context.scene.cycles.use_denoising = False

            if bake_props.global_illumination == 'FULL':
                cycles_set_full_gi(context.scene.cycles)

            if supports_spill_control(context):
                if context.scene.cycles.color_spill_strength <= 0.01:
                    context.scene.cycles.color_spill_strength = 4 # hammer it in for now and dial back as needed
                    context.scene.cycles.color_spill_max_gain = 5.0
                    context.scene.cycles.color_spill_ray_length = 60

            bake_passes = 'COMBINED'
            if supports_multi_pass:
                bake_passes = bake_props.passes

            material: bpy.types.Material = target.data.materials[0]
            for i in material.node_tree.nodes:
                if not isinstance(i, bpy.types.ShaderNodeTexImage):
                    continue
                img_node: bpy.types.ShaderNodeTexImage = i
                if SBE_IMG_BAKE_COMBINED_PROP in img_node.image:
                    # The active node will be the target of the combined bake
                    material.node_tree.nodes.active = img_node
                    break

            with SBE_Logger("bpy.ops.object.bake"):
                with context.temp_override(selected_objects=sources, active_object=target):
                    bpy.ops.object.bake(
                        type=bake_passes,
                        margin=bake_props.margin,
                        margin_type=margin_type,
                        use_selected_to_active=True,
                        use_clear=True, # the custom border extension won't work otherwise
                        max_ray_distance=0,
                        cage_extrusion=bake_props.cage_distance,
                        target='IMAGE_TEXTURES',
                        save_mode='INTERNAL')

        for target in targets:
            set_cycles_visibility(target, True)

        for source in sources:
            source.hide_viewport = True
            # source.hide_render = True
