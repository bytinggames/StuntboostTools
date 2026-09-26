# 01 - Setup

## Getting Blender
- We're using a modified blender version based on 4.3.2 (which is old I know)
    - The [FAQ](./faq.md) has a section about what it does.


### Windows
- Download the preconfigured portable version
- [Blender]()TODO Link
- Unpack somewhere
    - Please don't put it 1000 folders deep somewhere, windows doesn't like long paths :(
- Run the blender.exe inside
- Continue with [Configuring Blender](#configuring-blender)


### Linux
Providing a prebuilt version isn't really as easy, so there are several options.
- Build the custom version from source [Source Code](https://projects.blender.org/Tobiasked/blender/src/branch/bake_experiments_4_3/)
    - Tested on arch, all bets are off with other distros
    - System dependencies also mean this will break constantly (especially on arch)
- Use the normal Blender 4.3.x versions if you can get them to work on your distro
    - The version is pretty old so most distros might not provide it any more
- Use even newer versions provided by your distro
    - This might break the exporter when the blender API changes
- Continue with [Export Addon Installation](#export-addon-installation)


## Export Addon Installation


- Fire up your locally sourced blender (Up to 5.2 should work)
- Go to `Edit` > `Prefernces` > `Add-ons`
- Click Small down arrow in the top right
- Click `Install from disk...`
- Navigate to your game folder > `StuntboostTools` > `blender_addons` > `loader_addon` > `stuntboost_bpl.py`
- Enable `STUNTBOOST Blender Plugin Loader`.


## Folder Layout
```text
blender/
  blender(.exe)
  game/                                       junction on Windows, symlink on Linux, can be setup from the addon preferences
    StuntboostTools/
      blender_addons/
        loader_addon/stuntboost_bpl.py        This needs to be installed into blender
        stuntboost_bpl_runtime.py             This will be loaded by stuntboost_bpl.py and contains most of the loading logic
        bpl_auto_load/                        All the extensions loaded when blender starts
      assets/                                 Contains asset lib files, textures, etc.
        Models/Props/Props.blend              Contains all the assets used in the first room                          
        Models/Props/stickers.blend           Contains sticker decals
        Models/Rooms/Room_Protagonist.blend   Contains the first room of the game
        Models/Rooms/Room_Shared.blend        Contains model shared with all rooms
      examples/                               Example levels, copy those as templates to start new level
  levels/                                     Put your level source blend files in here to avoid issues with relative paths!

%APPDATA%/STUNTBOOST/custom_maps (windows)    The exported maps will be saved here
~/.config/STUNTBOST/custom_maps (linux)
```


## Configuring Blender
- Expand `STUNTBOOST Blender Plugin Loader` in `Edit` > `Preferences` > `Add-ons`.
- If automatic discovery did not find the game, click `Choose STUNTBOOST Game` and select the game installation.
- Path handling follows the selected target:
    - **SE repository:** Fast Open and asset libraries use fully resolved filesystem paths, not the `game` junction/symlink.
    - **Shipped game:** Fast Open opens shipped assets and examples through `blender/game`, and asset libraries use that same junction/symlink. Custom levels remain in `blender/levels`, keeping relative asset links portable.
- If the top menu bar does not show `STUNTBOOST`, check the loader's preferences for an error and confirm the selected game includes the runtime and plugins.
- Go to `Edit` > `Prefernces` > `System`
- Ensure the `Cycles Render Devices` is not set to `None`
    - For AMD choose `HIP`
    - For Nvidia try `Optix`
        - If your GPU isn't listed below, choose `CUDA`
    - Intel ARC GPUs use `oneAPI`
    - If your GPU isn't listed under none of the options, you'll have to live with `None`
        - This will bake on the CPU which is about 10x slower but it should still work.
- Click small burger menu in bottom right -> `Save Preferences`
- Setup is all done :)
