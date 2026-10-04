# 02 - Export an example level

[Video Tutorial](https://www.youtube.com/watch?v=w9Z_Ey-b-Z8)

## Open a copy
- Top menu > `File` > `Open`.
    - Navigate to your game `STUNTBOOST/StuntboostTools/examples/`
    - Open `Level_Simple.blend`
- `File` > `Save As` to save your own copy as `MyFirstLevel.blend` in the `levels` folder next to the blender executable [(Structure explained here)](./01-setup.md#folder-layout).
    - Don't save over the examples, changes might be gone when steam updates.
    - Always save to the `levels` so you can share them without relatives paths breaking.
    - Don't copy paste or move level files around on your computer ! this will break relative links !

## Basic navigation
- Now is a good time to familiarize yourself with the camera controls of blender to look around the scene.
- https://docs.blender.org/manual/en/4.5/editors/3dview/navigate/introduction.html
- https://www.youtube.com/watch?v=peSv5IT5Ve4


## Export
- In Blender's top bar, choose `STUNTBOOST` > `STUNTBOOST Export`.
    - A terminal should pop up
    - This will show progress and any problems
- A successful export ends with `================> !EXPORT FINISHED! <================`


## Play it
- Open STUNTBOOST and go to the room selection screen.
- Choose `Custom`, select your map, then `Play`.
    - With the filename above, the map is called `MyFirstLevel` until you give it a display name.
- Try the start, checkpoints and finish before changing anything.
- You can leave the game open while working. Exporting again reloads the active custom map and restarts the run.


## Where did it go?
- The exporter puts the playable files in their own folder automatically.
    - Windows: `%APPDATA%/STUNTBOOST/custom_maps/MyFirstLevel`
    - Linux: `~/.config/STUNTBOOST/custom_maps/MyFirstLevel` (or under `$XDG_CONFIG_HOME` if set).
- `Open maps folder` on the game's `Custom` screen opens the right location.
- If you want to share your creation with others, zip the entire `MyFirstLevel` folder.
    - They can play the level the same way by putting it in their `custom_maps` folder.


Next: [Basics](./03-basics.md) Change the track and add gameplay objects.