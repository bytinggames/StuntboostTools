# pylint: disable=import-error
import bpy
# pylint: enable=import-error


_UNAVAILABLE = "The source is no longer available. Run Check Blend again."


def _window_region(area):
    return next((region for region in area.regions if region.type == 'WINDOW'), None)


def _areas(context, area_type):
    if context.screen is None:
        return []
    areas = [area for area in context.screen.areas if area.type == area_type]
    if context.area in areas:
        areas.remove(context.area)
        areas.insert(0, context.area)
    return areas


def _object_unavailable(obj, context):
    if context.mode != 'OBJECT':
        return "Switch to Object Mode yourself, then locate the source again."
    if context.view_layer.objects.get(obj.name) != obj:
        return "The source object is outside the active view layer. Switch scene or view layer to inspect it."
    if obj.hide_select or not obj.visible_get(view_layer=context.view_layer):
        return "The source object is hidden or unselectable. Enable it manually, then locate it again."
    if obj not in context.selectable_objects:
        return "The source object is hidden or selection-disabled in this view. Enable it manually."
    return None


def _select_object(obj, context):
    unavailable = _object_unavailable(obj, context)
    if unavailable:
        return False, unavailable
    # Establish the new selection before touching any existing selection.
    obj.select_set(True, view_layer=context.view_layer)
    if not obj.select_get(view_layer=context.view_layer):
        return False, "Blender could not select the source. Check its collection selection restrictions."
    context.view_layer.objects.active = obj
    for selected in tuple(context.selected_objects):
        if selected != obj:
            selected.select_set(False, view_layer=context.view_layer)
    for area in _areas(context, 'VIEW_3D'):
        region = _window_region(area)
        if region is None or not obj.visible_get(view_layer=context.view_layer, viewport=area.spaces.active):
            continue
        try:
            with context.temp_override(area=area, region=region):
                if bpy.ops.view3d.view_selected.poll():
                    bpy.ops.view3d.view_selected(use_all_regions=False)
        except (RuntimeError, TypeError):
            # Selection is useful even when this viewport cannot frame it.
            pass
        break
    return True, f'Selected object "{obj.name}".'


def _preferred_object(objects, candidates, context):
    for obj in objects:
        if isinstance(obj, bpy.types.Object) and obj in candidates and not _object_unavailable(obj, context):
            return obj
    return next((obj for obj in sorted(candidates, key=lambda item: item.name_full)
                 if not _object_unavailable(obj, context)), None)


def _preferred_user(objects, candidates, context):
    if not candidates:
        return None
    instances = [obj for obj in context.view_layer.objects
                 if obj.instance_type == 'COLLECTION' and obj.instance_collection is not None
                 and any(member in candidates for member in obj.instance_collection.all_objects)]
    preferred = _preferred_object(objects, candidates + instances, context)
    return preferred


def _material_objects(material):
    return [obj for obj in bpy.data.objects
            if any(slot.material == material for slot in obj.material_slots)]


def _material_slot(obj, material):
    for index, slot in enumerate(obj.material_slots):
        if slot.material == material:
            obj.active_material_index = index
            return True
    return False


def _show_shader_tree(tree, node, context):
    for area in _areas(context, 'NODE_EDITOR'):
        space = area.spaces.active
        if space.tree_type != 'ShaderNodeTree':
            continue
        region = _window_region(area)
        if region is None:
            continue
        # Pinning also exposes standalone, unused node groups without assigning
        # them to an object or modifying any material's node graph.
        try:
            space.pin = True
            space.node_tree = tree
            space.path.start(tree)
            if space.edit_tree != tree:
                continue
            if node is not None:
                for other in tree.nodes:
                    other.select = other == node
                tree.nodes.active = node
        except (AttributeError, RuntimeError, TypeError):
            continue
        area.tag_redraw()
        try:
            with context.temp_override(area=area, region=region):
                operator = bpy.ops.node.view_selected if node is not None else bpy.ops.node.view_all
                if operator.poll():
                    operator()
        except (RuntimeError, TypeError):
            pass
        if node is not None:
            return True, f'Selected node "{node.name}" in the pinned Shader Editor.'
        return True, f'Opened "{tree.name}" in the pinned Shader Editor.'
    return False, "Open a Shader Editor in this window, then locate the source again."


def _tree_uses(tree, target, visited):
    if tree == target:
        return True
    if tree is None or tree.as_pointer() in visited:
        return False
    visited.add(tree.as_pointer())
    return any(_tree_uses(node.node_tree, target, visited)
               for node in tree.nodes if node.type == 'GROUP' and node.node_tree is not None)


def _navigate_shader(tree, node, objects, context):
    materials = [material for material in bpy.data.materials
                 if _tree_uses(material.node_tree, tree, set())]
    candidates = [obj for obj in bpy.data.objects
                  if any(slot.material in materials for slot in obj.material_slots)]
    obj = _preferred_user(objects, candidates, context)
    selected = False
    if obj is not None:
        selected, _ = _select_object(obj, context)
        if selected:
            for index, slot in enumerate(obj.material_slots):
                if slot.material in materials:
                    obj.active_material_index = index
                    break
    shown, message = _show_shader_tree(tree, node, context)
    if shown:
        return True, message
    if selected:
        return True, f'Selected shader user "{obj.name}". {message}'
    return False, f'No visible, selectable shader user. {message}'


def _navigate_material(material, objects, context):
    obj = _preferred_user(objects, _material_objects(material), context)
    if obj is not None:
        selected, message = _select_object(obj, context)
        if selected:
            material_active = _material_slot(obj, material)
            if material.node_tree is not None:
                _show_shader_tree(material.node_tree, None, context)
            if material_active:
                return True, f'Selected material "{material.name}" on "{obj.name}".'
            return True, f'Selected collection instance "{obj.name}" containing a user of material "{material.name}".'
        return False, message
    if material.node_tree is not None:
        shown, message = _show_shader_tree(material.node_tree, None, context)
        if shown:
            return True, message
    return False, ("This material has no visible, selectable object user. Inspect it in Material Properties"
                   " or open a Shader Editor for a node-based material, then locate it again.")


def _find_layer_collection(layer, collection):
    if layer.exclude or layer.hide_viewport or layer.collection.hide_viewport:
        return None
    if layer.collection == collection and layer.is_visible:
        return layer
    for child in layer.children:
        match = _find_layer_collection(child, collection)
        if match is not None:
            return match
    return None


def _navigate_collection(collection, objects, context):
    members = list(collection.all_objects)
    instances = [candidate for candidate in context.view_layer.objects
                 if candidate.instance_type == 'COLLECTION' and candidate.instance_collection == collection]
    obj = _preferred_object(objects, members + instances, context)
    if obj is not None:
        return _select_object(obj, context)
    layer = _find_layer_collection(context.view_layer.layer_collection, collection)
    if layer is not None:
        context.view_layer.active_layer_collection = layer
        for area in _areas(context, 'OUTLINER'):
            area.tag_redraw()
        return True, f'Activated collection "{collection.name}" in the active view layer, no selectable member.'
    return False, ("This collection has no visible, selectable member or instance in the active view layer. "
                   "Inspect it in the Outliner, no collections were linked or unhidden.")


def _navigate_source(source, objects, context):
    if isinstance(source, bpy.types.Object):
        return _select_object(source, context)
    if isinstance(source, bpy.types.MaterialSlot):
        obj = source.id_data
        if not isinstance(obj, bpy.types.Object):
            return False, _UNAVAILABLE
        index = next((index for index, slot in enumerate(obj.material_slots) if slot == source), None)
        if index is None:
            return False, _UNAVAILABLE
        selected, message = _select_object(obj, context)
        if selected:
            obj.active_material_index = index
            return True, f'Selected material slot {index + 1} on "{obj.name}".'
        return False, message
    if isinstance(source, (bpy.types.Mesh, bpy.types.MeshUVLoopLayer)):
        mesh = source if isinstance(source, bpy.types.Mesh) else source.id_data
        if not isinstance(mesh, bpy.types.Mesh):
            return False, _UNAVAILABLE
        index = None
        if isinstance(source, bpy.types.MeshUVLoopLayer):
            index = next((index for index, layer in enumerate(mesh.uv_layers) if layer == source), None)
            if index is None:
                return False, _UNAVAILABLE
        candidates = [obj for obj in bpy.data.objects if obj.data == mesh]
        obj = _preferred_user(objects, candidates, context)
        if obj is None:
            return False, "This mesh has no visible, selectable object user. Switch view layer or enable its user manually."
        selected, message = _select_object(obj, context)
        if selected and index is not None:
            if obj.data != mesh:
                return True, (f'Selected collection instance "{obj.name}". '
                              f'Inspect UV layer "{source.name}" on its source mesh "{mesh.name}".')
            if mesh.library is not None and mesh.override_library is None:
                return True, f'Selected "{obj.name}". Inspect UV layer "{source.name}" in the linked source file.'
            mesh.uv_layers.active_index = index
            return True, f'Selected UV layer "{source.name}" on "{obj.name}".'
        return selected, message
    if isinstance(source, bpy.types.Material):
        return _navigate_material(source, objects, context)
    if isinstance(source, bpy.types.ShaderNodeTree):
        return _navigate_shader(source, None, objects, context)
    if isinstance(source, bpy.types.Node):
        tree = source.id_data
        if not isinstance(tree, bpy.types.ShaderNodeTree):
            return False, "This node is not in a shader tree. Inspect its source in the corresponding node editor."
        if not any(node == source for node in tree.nodes):
            return False, _UNAVAILABLE
        return _navigate_shader(tree, source, objects, context)
    if isinstance(source, bpy.types.Collection):
        return _navigate_collection(source, objects, context)
    if isinstance(source, bpy.types.Library):
        return False, (f'Inspect library "{source.name}" in the Outliner\'s Blender File view. '
                       f'Use Relocate there to repair its path: {source.filepath}. No library was relinked.')
    return False, "This source has no supported navigation target. Inspect the displayed source and solution manually."


def navigate_to_problem(problem, context) -> tuple[bool, str]:
    """Locate live RNA references without interpreting display text or editing assets."""
    try:
        objects = problem.objects
        source = problem.source
        if source is None:
            return False, "This result has no source to locate. Run Check Blend again."
        for item in objects:
            if item is None or not isinstance(item, bpy.types.bpy_struct):
                return False, _UNAVAILABLE
            if not item.as_pointer():
                return False, _UNAVAILABLE
            # Accessing RNA (not just its pointer) detects removed datablocks.
            item.id_data
        return _navigate_source(source, objects, context)
    except ReferenceError:
        return False, _UNAVAILABLE
    except (AttributeError, RuntimeError, TypeError, ValueError) as error:
        return False, f'Cannot locate this source in the current context: {error}. Run Check Blend again if the source changed.'
