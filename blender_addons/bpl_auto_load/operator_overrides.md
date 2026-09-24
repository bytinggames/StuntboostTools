Operators can have the context they interact on overridden.
This is poorly documented and doesn't always work, so here are some notes.

https://blender.stackexchange.com/a/248275


# object delete
```py
with bpy.context.temp_override(selected_objects=deleted_objects):
    bpy.ops.object.delete(use_global=False)
```

# modifier delete
```py
# view_layer and scene optional
with bpy.context.temp_override(object=obj):
    bpy.ops.object.modifier_remove(modifier=obj.modifiers[0].name)
```

# Duplicate
```py
bpy.ops.object.duplicate()
```
# modifier apply
```py
# view_layer and scene optional
with bpy.context.temp_override(object=obj):
    bpy.ops.object.modifier_apply(modifier=obj.modifiers[0].name)
```

# duplicates make real
```py
with bpy.context.temp_override(selected_objects=list):
    bpy.ops.object.duplicates_make_real()
```

# Join
```py
with bpy.context.temp_override(selected_editable_objects=list, active_object=obj):
    bpy.ops.object.join()
```

# make local
TODO no context?
```py
bpy.ops.object.make_local(type="ALL")
```

# Convert to mesh
https://projects.blender.org/blender/blender/issues/93188
Override not working :/
```py
bpy.ops.object.convert(target="MESH")
```

# Bake
```py
with bpy.context.temp_override(selected_objects=list, active_object=obj):
    bpy.ops.object.bake(
        type='COMBINED',
        pass_filter={},
        filepath='',
        margin=16, margin_type='EXTEND',
        use_selected_to_active=False, max_ray_distance=0.0,
        use_cage=False, cage_object='', cage_extrusion=0.0,
        target='IMAGE_TEXTURES',
        save_mode='INTERNAL',
        use_clear=False,
        use_split_materials=False,
        use_automatic_name=False,
        uv_layer='')
```