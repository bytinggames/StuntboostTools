# Trouble Shooting
## Help us gather info on the problem
- TODO Explain how to open/analyze `.export.blend` in `%APPDATA%\STUNTBOOST\build_blends`
- `STUNTBOOST` > `SBE Load Export/Origin`
    - Change to the `Scripting` tab, then choose `STUNTBOOST` > `SBE Show build log`.
- `%APPDATA%\STUNTBOOST\build_logs` / `~/.config/STUNTBOOST`
    - TODO only written on succesful exports?
- TODO explain step by step debugging


## Common problems Section

### I'm seeing red wireframe boxes in game
This means enteties unknown to the game were exported.
- Look for any lamps or empties not prefixed by '/'
