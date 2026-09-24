# TODO attach attribute to scene to only hide after the user has 
# actively used to operator

# pylint: disable=import-error
import bpy
from bake_v3.sbe_name_parser import clean_name
# pylint: enable=import-error


whitelist = [
    "lap_goal",
    "goal_light",
    "=Booster",
    "LapGoal",
    "Checkpoint",
    "checkpoint",
    "//anchor",
    "editor_visual"
]

def isWhiteListed(obj: bpy.types.Object) -> bool:
    for i in whitelist:
        if obj.name.find(i) != -1:
            return True
    return False


def shouldWireFrame(obj: bpy.types.Object) -> bool:
    if isWhiteListed(obj):
        return False
    return obj.name.find("#") != -1 or obj.name.find("_<") != -1 or obj.name.startswith("_") or obj.name.endswith("_")  or obj.name.find("°") != -1


def shouldHide(obj: bpy.types.Object) -> None:
    if isWhiteListed(obj):
        return False
    return obj.name.find("#") != -1 or obj.name.find("_<") != -1 or obj.name.startswith("_") or obj.name.startswith("//") or obj.name.endswith("_")  or obj.name.find("°") != -1


def set_collision_visibility(context: bpy.types.Context, hide: bool) -> None:
    _ = context
    for i in bpy.data.objects:
        obj: bpy.types.Object = i
        try:
            if shouldHide(obj):
                # obj.hide_set(state=hide, view_layer=context.view_layer)
                obj.hide_viewport = hide
                # we always exclude them from renders,
                # since they only cause z fighting
                obj.hide_render = True
            if shouldWireFrame(obj):
                obj.display_type = 'WIRE'
        except Exception:
            pass


class SB_ShowAllColliders(bpy.types.Operator):
    '''Show all collision objects'''
    bl_idname = "object.sb_show_colliders"
    bl_label = "Show collision Objects."
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context):
        set_collision_visibility(context=context, hide=False)
        return {'FINISHED'}


class SB_HideAllColliders(bpy.types.Operator):
    '''Hide all collision objects'''
    bl_idname = "object.sb_hide_colliders"
    bl_label = "Hide collision Objects."
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context):
        set_collision_visibility(context=context, hide=True)
        return {'FINISHED'}


class SB_MakeCollider(bpy.types.Operator):
    '''Duplicate current objects and turn it into a collider'''
    bl_idname = "object.sb_make_collider"
    bl_label = "Add collider for current"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context):
        for i in context.selected_objects[:]:
            obj: bpy.types.Object = i
            obj.select_set(state=False, view_layer=context.view_layer)
            if obj.name.find("_<") != -1:
                continue

            obj.name = obj.name.replace("<", "")
            org_name = clean_name(obj.name)
            copy = obj.copy()
            obj.users_collection[0].objects.link(copy)

            copy.display_type = 'WIRE'
            copy.name = org_name + "_<"
            for j in copy.modifiers:
                modifier: bpy.types.Modifier = j
                if modifier.name.find("no_export") != -1 or modifier.name.startswith("/"):
                    # this is faster than removing but same result
                    modifier.show_viewport = False
                    modifier.show_render = False
            target = None
            if 'C_Default' in bpy.data.materials:
                target = bpy.data.materials['C_Default']
            for j in copy.material_slots:
                mat: bpy.types.MaterialSlot = j
                mat.link = 'OBJECT'
                mat.material = target

            copy.select_set(state=True, view_layer=context.view_layer)

        return {'FINISHED'}


class SB_ShowAll(bpy.types.Operator):
    """Show all hidden objects, including those from linked collections (won't be saved)"""
    bl_idname = "object.sb_show_all"
    bl_label = "Unhide all objects, even linked"
    bpl_auto_load = True
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context):
        for i in bpy.data.objects:
            obj: bpy.types.Object = i
            obj.hide_viewport = False
            obj.hide_set(state=False, view_layer=context.view_layer)
        return {'FINISHED'}
