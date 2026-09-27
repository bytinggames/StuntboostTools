# deprecations
- auto projections
  - smart_project
  - angle_project
  - Don't use these any longer whenever possible, manual unwraps always look better
    - when in a rush just smart project in blender, so it's not every time in the export
    - when projection at export time is needed try the modifier group SmartProject instead
- BackfaceShadowCaster()
  - there's no need since we can flip normals in geo nodes


# TODOs
  - bugs
    - post processing shader noise size to big for low res textures
  - /decals are not removed once they are merged into the large source object
  - merge by distance?
  - ray depth limit
  - Introduce max UV scale for objects?
  - whitelist attributes to be exported
    - bake uv
    - material index
    - outline shift stuff
    - vertex colors?
    - sharp edge and face?
  - fast baking
    - Direct light or no bake export operator
    - fix fast bake/release bake being two separate settings visible at once
      - CLI bake ignore skip bake flag on collections
    - minimal export without bake for level block out


# Nice to haves
  - workflow speed
    - Local view export
    - hide heavy objects in fast bake?
    - way to execute post processing step again to dial in values
    - inspect for bake source mesh
    - delete unused export gltfs and textures
      - run t4 from blender when new textures are created or some are deleted
      - warn about missing gltfs
    - load bake operator to load export blend or import gltf if export blend doesn't exist
    - display outline shift with gpu module or geo nodes?
    - Try to get some sort of property on instancer that also works before running the bake script
      - or go all in on geo nodes
    - auto select collection of the current selected object
  - performance
    - separate bake mesh and drawable mesh for game
    - do some bmesh operations in one go, mostly affects target mesh generation
      - probably now worth more than half a second though
  - cleanup
    - Handle disabled collections
    - better way to get collections queued for bake
    - don't export problem list on scene
    - don't export sbe_properties
    - don't export MeasureGenerator
  - output quality
    - Ensure each face has a minimum of one pixel on the bake map
