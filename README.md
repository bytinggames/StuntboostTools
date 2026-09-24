# STUNTBOOST Tools & Friends

This contains modding tools for the game [STUNBOOST](https://store.steampowered.com/app/2999500/STUNTBOOST/) as well as documentation and the source code to the exporter.

## Requirements
- Some patience and/or familiarity with Blender
    - Blender is not a easy level editor, but a giant 3D Modelling animation Tool!
    - There is a bit of a learning curve, but we're trying our best to make it straight forward.
- A decent computer with a supported GPU
    - This depends on how complex the levels are, and how close the original game look should be matched.
- The Full Game downloaded
    - Bundles the required assets
    - Bundles the exports scripts from this repository
        - You do not need to download/clone anything from here unless you wont to develop the exporter!


## Getting Started
- [Setup](./docs/01-setup.md)
- [Export a example level](./docs/02-test-export.md)
- [Basics](./docs/03-basics.md)
- [Advanced](./docs/04-advanced.md)


## FAQ
Check out the [FAQ here](./docs/faq.md)


## Troubleshooting
Having issues? Checkout or ever expanding list of common pitfals and erros:
[Common Issues and troubleshooting](./docs/troubleshooting.md)


Still having problems?
- (Join or Discord community)[https://discord.gg/stuntboost] (I know discord is bad for search engines and public discourse)
- (Open a issue on github)[https://github.com/bytinggames/StuntboostTools/issues] (If you're sure it's a bug)


## Contributing
- Clone the repo
- Replace `.../steamapps/common/STUNTBOOST/StuntboostTools/blender_addons` with a symlink to `blender_addons` from the cloned repo.
    - TODO tk this is not tested
- `blender_addons/bpl_auto_load/python_debugger._py` to `python_debugger.py` for a python debugger
- Small fixes are welcome
- Let us know before implementing large features. We might not be able to merge those without breaking our iternal tooling, which also relies on this repo.
