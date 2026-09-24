"""Start debugpy when BPL loads this plugin."""

import sys


class SB_PythonDebugger:
    @staticmethod
    def bpl_load() -> None:
        try:
            import debugpy
        except ModuleNotFoundError as ex:
            if ex.name != "debugpy":
                raise
            print(
                "BPL Python debugger requires debugpy. Install it into Blender's Python with: "
                f'"{sys.executable}" -m pip install debugpy'
            )
            return

        # The imported module survives BPL reloads; this plugin's class does not.
        if getattr(debugpy, "_stuntboost_listener_started", False):
            return

        try:
            debugpy.listen(("localhost", 5678))
        except Exception as ex:
            print(f"BPL Failed to start Python debugger on localhost:5678: {ex}")
            return

        debugpy._stuntboost_listener_started = True
        print("BPL Python debugger listening on localhost:5678")

    @staticmethod
    def bpl_unload() -> None:
        """Keep listening until Blender exits, debugpy has no public stop API."""
