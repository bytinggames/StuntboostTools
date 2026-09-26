# 03 - Basics

- Start with a level you can already export and play: [02 - Test export](./02-test-export.md).


## Asset browser
- An asset is a reusable object, material or modifier supplied with the tools.
- In our example files the bottom half of the screen usually is set to the `Asset Browser` type.
- On the left there's a Tree to which contains groups for the STUNTBOOST assets.
    - You can expand and filter categories by clicking on them in the tree
    - `gameplay` and `props` are the most important ones
    - `rooms` contains the mostly empty rooms
- Drag an object asset into the 3D Viewport, then move, rotate and scale its placement.
    - You usually want to have snapping set to face and `align rotation to target`


## Cardboard modifiers
- Drag and drop it onto meshes to convert them into card board. Use thin planes as a source
- Open `Modifiers` in the Properties editor (the wrench icon). Here tickness and some other properties can be changed.
- Shape the mesh in `Edit Mode` (Tab), leave `Edit Mode` again with Tab.
- Drag and Drop `C_Default` from the `gameplay` category in the asset browser onto the cardboard.
    - Now it has collision in game
    - `C_Ramp` turns it into a ramp.
    - Material can be defined per face.

### Booster
- Add a plane, enter `Edit Mode` to scale it to size.
- Leave edit mode and drag the `Booster` asset from the `Asset Browser` onto the plane.
- In the object `Modifiers`, set `CM/S` to the booster speed.
- No manual naming is needed: if the name does not contain `#=Booster`, the exporter renames the object to `#=Booster(speed)` using the modifier's `CM/S` value.


Next: [04 - Advanced](./04-advanced.md).