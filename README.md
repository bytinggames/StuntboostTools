# STUNTBOOST Tools & Friends

This contains the level exporter for the game [STUNTBOOST](https://store.steampowered.com/app/2999500/STUNTBOOST/) as well as documentation and the source code to the blender exporter.

This is work and progress. We'll work on improving the feature set and documentation if there's a real demand for custom levels.

## There's NO online leaderboard and replays for custom maps currently!!!


## Requirements
- Some patience and/or familiarity with Blender
    - Blender is not a level editor, but a giant 3D Modelling animation Tool!
        - It'll look intimidating, but we won't need most of the functionality.
    - There is a bit of a learning curve, but we're trying our best to make it straight forward.
        - There's also a million key binds
        - Don't press random buttons, some hidden state will change and subtly alter behavior, leaving you frustrated (I've been there)
- A decent computer with a supported GPU
    - This depends on how complex the levels are and how close the original game look should be matched.
- The Full Game downloaded
    - Contains the required assets
    - Contains the exports scripts from this repository
        - You do not need to download/clone anything from here unless you want to work on the exporter!


## Getting Started
- [Setup](./docs/01-setup.md)
- [Export a example level](./docs/02-test-export.md)
- [Basics](./docs/03-basics.md)
- [Advanced](./docs/04-advanced.md)


## FAQ
Check out the [FAQ here](./docs/faq.md)
[And the currently missing features](./docs/faq.md#not-implemented-yet)


## Troubleshooting
Having issues? Checkout or ever expanding list of common pitfals and erros:
[Common Issues and troubleshooting](./docs/troubleshooting.md)


Still having problems?
- [Join or Discord community](https://discord.gg/stuntboost) (I know discord is bad for search engines and public discourse)
- [Open a issue on github](https://github.com/bytinggames/StuntboostTools/issues) (If you're sure it's a bug, or the documentation should be updated)


## Contributing
- Open issues
- Clone the repo
    - Help us write better user documentation by editing the .md files
    - Implement small fixes or features
        - Let us know before implementing large features. We might not be able to merge those without breaking our iternal tooling, which also relies on this repo.


## Development Setup
- Replace `.../steamapps/common/STUNTBOOST/StuntboostTools/blender_addons` with a symlink/mklink to `blender_addons` from the cloned repo.
    - Hasn't been testsed yet.
- [How to enable Python debugger](./blender_addons/bpl_auto_load/bake_v3/README.md#how-to-debug)
- Enable python hot reload in the loader addon preferences
- [Bare bones overview of the exporter internals](./blender_addons/bpl_auto_load/bake_v3/README.md#development)

