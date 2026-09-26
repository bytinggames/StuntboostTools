# FAQ

## Not implemented yet
- Changing the vehicle type
- Wheels
- Eyes/Doors
- Change Godrays
- Change Fog


## Not yet Documented features
- Creating own assets
- Detours/Short cut detection
- Domain specific entety name language
    - Physics delete
    - material replace
    - rename logic
    - outline magic
- Overriding post processing/color grading


# What is this custom Blender Build?
- [Source Code](https://projects.blender.org/Tobiasked/blender/src/branch/bake_experiments_4_3/)
- It adds a couple of features to speed up the export process
    - Multi core pre bake step (Already merged in upstream blender 4.5.0)
    - Bake multiple passes at once (Will not make it into upstream blender in the current state)
- It Fixes a couple of artifacts
    - Fix black borders with denoised bakes (Will be fixed in upstream blender 5.3.0)
- It Breaks the PBR a little to get more "nostalgic" lighting
    - Adds Cycles `Light Paths` > `Color Spill` Render Settings to boost first bounce indirect lighting
    - [Example (Left disabled/Right enabled)](./images/spill_light_explained.webp)
## Do I need Blender 4.3.2 or the Custom build?
- The custom build is optional, the features above are nice to have
    - The game will look a little different, you will have longer export times
- Using newer blender versions might work (I tested up to 5.2)
    - The export might break
- The exporter extension does most of the game specific work and has fallbacks when the custom build isn't used
