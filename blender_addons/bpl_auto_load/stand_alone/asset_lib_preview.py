# pylint: disable=import-error
import bpy
import gpu
# pylint: enable=import-error


class SB_RefreshLibraryPreviews(bpy.types.Operator):
    """This should all assets defined in this file to generate new previews"""
    bl_idname = "object.sb_refresh_library_previews"
    bl_label = "Rerender all the previews for the asset library"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, _context: bpy.types.Context):
        for i in bpy.data.objects:
            obj: bpy.types.Object = i
            if obj.asset_data is not None:
                if not obj.preview.is_image_custom:
                    obj.asset_generate_preview()
        for i in bpy.data.collections:
            col: bpy.types.Collection = i
            if col.asset_data is not None:
                if not col.preview.is_image_custom:
                    col.asset_generate_preview()
        return {'FINISHED'}


def find_view_port(context: bpy.types.Context) -> bpy.types.SpaceView3D:
    for i in context.screen.areas:
        area: bpy.types.Area = i
        if area.type != 'VIEW_3D':
            continue
        for j in area.spaces:
            space: bpy.types.Space = j
            if space.type != 'VIEW_3D':
                continue
            return space
    return None

def refresh_asset_browser(context: bpy.types.Context):
    for i in context.screen.areas:
        area: bpy.types.Area = i
        if area.type != 'FILE_BROWSER':
            continue
        for j in area.spaces:
            space: bpy.types.Space = j
            if space.type != 'FILE_BROWSER' or not hasattr(space, 'params'):
                continue
            if isinstance(space.params, bpy.types.FileAssetSelectParams):
                with context.temp_override(area=area, space_data=space):
                    bpy.ops.asset.library_refresh()


class SB_LibraryPreviewFromViewPort(bpy.types.Operator):
    """TODO"""
    bl_idname = "object.sb_library_previews_from_viewport"
    bl_label = "Rerender preview for asset from viewport"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context):
        space = find_view_port(context)
        if not space or not context.active_object:
            # TODO warn about no space
            return {'FINISHED'}

        # we could also hook the viewport pixels with
        # bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')
        # and then get the active framebuffer which would also allow cycles
        # viewport screenshots, but we'd need to do scaling and so on
        # gpu.state.active_framebuffer_get()

        width = 128
        height = 128
        offscreen = gpu.types.GPUOffScreen(width=width, height=height, format='RGBA8')

        #  = scene.camera.matrix_world.inverted()
        view_matrix = space.region_3d.view_matrix

        # projection_matrix = scene.camera.calc_matrix_camera(
        #     context.evaluated_depsgraph_get(), x=WIDTH, y=HEIGHT)
        projection_matrix = space.region_3d.view_matrix

        offscreen.draw_view3d(
            scene=context.scene,
            view_layer=context.view_layer,
            view3d=space,
            region=context.region,
            view_matrix=view_matrix,
            projection_matrix=projection_matrix,
            do_color_management=True)

        preview_data: bpy.types.ImagePreview = None
        if context.active_object.asset_data:
            preview_data = context.active_object.preview
        else:
            preview_data = context.active_object.users_collection[0].preview

        preview_data.image_size[0] = width
        preview_data.image_size[1] = height

        source = offscreen.texture_color.read()
        pixel_index = 0
        for line in source:
            for pixel in line:
                preview_data.image_pixels[pixel_index] = int.from_bytes(
                    [pixel[0], pixel[1], pixel[2], 0], signed=False, byteorder='little')
                # Alpha channel is ignored, also the offscreen buffer doesn't have any as well
                pixel_index += 1

        offscreen.free()
        preview_data.is_image_custom = True

        refresh_asset_browser(context=context)
        return {'FINISHED'}
