# 04 - Advanced

- Start from the `Level_Room.blend` example

## Skybox
- Besides the normal `Scene` which contains the level, there's also a `Skybox` Scene.
- It contains a simple environment and is rendered to a cubemap.
- You can adjust the clouds by adjusting parameters on the modifier.


## Bake Groups
- `Scene` has two top level `Collections`
    - `Level` Containing the direct level parts
    - `Room` Containing mostly the room and unreachable clutter.
- Both of these top level `Collections` are `Bake Groups`, which means they are split and don't share a texture.
- This means they can be exported individually to save time.
- Do a normal `STUNTBOOST Export` first, then, when only working on the level `Collection`, do just `STUNTBOOST Export Selection` which is quicker.


## Lighting

### Sun
- Sky texture defines the shadow direction in game
- It can be found in the `World` Properties and allows changing sun elevation and direction which also afftects the `Skybox`.

## Texture detail and materials

### UV Scale
- **UVs** tell Blender which part of an image belongs on each face of a mesh. `UV Scale` here controls how much space an object gets in the baked texture, not how large the object is.
- Select an object, then open **Object Properties** > `STUNTBOOST Object Properties` > `UV Scale`.
    - Increase it for important surfaces whose baked detail looks blurry.
    - Decrease it for small or distant decoration. For example, try `0.5` rather than `1`.
    - The texture has limited space: giving one object more detail leaves less for the others in its bake group.
- For several objects together, select their collection and use **Collection Properties** > `STUNTBOOST Collection Properties` > `UV Scale`. This control is for ordinary collections, not bake groups.
- Collection and object scales multiply. Some assets also have per-part scaling; the object's `Skip Mesh UV Scale` ignores the older `bake_size=` vertex-group settings, not every modifier's UV controls.

## What gets exported?

- The Outliner's eye and camera icons are not a reliable way to exclude something from the game. The exporter has its own rules.
- The `Visibility` controls are still marked unfinished in the add-on. For these common cases, use the established object-name prefixes instead:
    - `//unused_prop`: excluded from both the bake and the game.
    - `/shadow_helper`: affects the bake, but is removed before export. Useful for extra shadow-casting geometry or lights.
    - An ordinary visual object without these prefixes is baked and exported.
- The same `/` and `//` prefixes work on collections. Do not put playable objects inside an excluded collection.
- Preserve special names on gameplay assets. In particular, `_#` marks an invisible trigger and `_<` marks invisible collision; neither means the object is unused.

### Invisible lights
- To brighten a dark corner without adding a visible lamp, use `Add` > `Light` > `Point`, `Spot` or `Area` in the 3D Viewport.
- Prefix the name with a `/` to turn it into a `shadow_helper`

## Export quality and speed

- Open `Scene Properties` > `STUNTBOOST Scene Properties`.
    - Use `Fast Bake` while adjusting the route; switch to `Release Bake` to judge the finished lighting. They keep separate settings.
    - To change a value, enable its checkbox, such as `Resolution set` or `Samples set`. Unchecked rows show the inherited value instead.
- Start with these controls:
    - `Resolution`: baked image size. Higher values give more detail but use more texture memory. Try improving an important object's UV Scale before raising the whole image's resolution.
    - `Samples`: lighting quality. More samples can reduce noise but take longer; `0` skips baking, so it is not a low-quality preview setting.
    - `Denoise`: smooths noisy lighting. `Open Image Denoise` is an option if you cannot use `OptiX Denoising`.
    - `Margin`: padding around pieces of the texture. Keep it above zero to help avoid dark seams.
- Leave `Cage distance`, the processing-node names and other advanced controls at their existing values unless you are fixing a specific baking problem.
- A `bake group` is a top-level collection exported with its own baked texture. Its settings are in `Collection Properties > `STUNTBOOST Collection Properties`.
    - `Skip Bake` can save time by leaving an unchanged group alone during an interactive export. Turn it off for your final export, especially after changing shared lighting.
- Remove unused decoration with `//`, reduce excessive mesh detail and keep collision shapes simple. Higher-resolution textures cannot fix unnecessarily complex geometry.

## Physics materials

- A `physics material` tells the game how a surface behaves when you ride on it. They are prefixed with `C_`.
- Common supplied materials include:
    - `C_Default`: ordinary solid surface
    - `C_Ramp`: ramp handling
    - `C_Kill`: deadly surface
    - `C_RailBoost` and `C_RailNoBoost`
- Assign these to collision geometry `_<` not visual meshes.
- To change an existing asset's collision material without editing its source
    - Create a collection, name it `swap_collision_materials=C_Kill`, and put the relevant asset instances or objects inside it.


## Changing the room
- The room comes in some default configurations and can be assembled as needed.
- Sometimes more control is needed
    - Right click the room instance in the outliner and override `selection and content`
    - Now individual parts can be selected and overridden as well to be repositioned.


## Laps and ordered checkpoints


### Laps
- Add the `lap_goal` asset from the Asset Browser at the end of a loop, instead of an ordinary `goal`.
- Place `checkpoint_mandatory` around the loop so the player has to complete the route before the lap goal activates.


### Ordered checkpoints
- TODO

- Return to [03 - Basics](./03-basics.md) for placing gameplay objects, or [02 - Test Export](./02-test-export.md) for the export-and-play loop.


## Level metadata
- Metadata is the title, author, preview and medal targets shown for your map.
- Open the exported `<level-name>_.json` in a text editor. It sits beside the `.gltf` files inside your map folder.
- Add whichever of these optional fields you need:
    - `id`: a UUID, a unique identifier for your map. Generate one once with a UUID generator and keep it for later versions. Use a new one for a different map. Without it, moving or renaming the map folder changes the map ID.
    - `version`: a integer. Increase it when you want a new record version.
    - `name`: the displayed title. Falls back to filename.
    - `author`: your displayed name. Falls back to `Unknown`.
    - `preview`: the path to a PNG inside the map folder shown in the level selection.
    - `medalTimesSeconds`: medal targets in seconds, using `silver`, `gold`, `diamond`, `obsidian` and `developer`.
        - Use positive numbers, with `silver >= gold >= diamond >= obsidian >= developer`.
- Example:
```json
{
  "modelCount": 1,
  "version": 1,
  "name": "grind_machine_2",
  "author": "gamertag",
  "medalTimesSeconds": {
    "silver": 60, "gold": 45, "diamond": 35,
    "obsidian": 30, "developer": 28
  }
}
```


- Save the file and check the map's details in `Custom`. If the file is rejected, open `Map errors (...)` for the reason.