"""Main logging and timing mechanism used in the bake script."""

import os
import sys
import time
import datetime
import inspect
import shutil
import typing
import threading

# pylint: disable=import-error
import bpy
# pylint: enable=import-error


SBE_LEFT_COL = 44
SBE_TIME_COL = 16
SBE_COUNT_COL = 4
SBE_ZERO_TIME = datetime.timedelta(seconds=0)
SBE_MIN_TIME = datetime.timedelta(seconds=0.05)
"""Don't log anything shorter than 50 ms"""
is_windows = os.name == 'nt'

SBE_LOG_SKIP_CLEAR = os.environ.get("SBE_LOG_SKIP_CLEAR") is not None
SBE_LOG_SILENT = os.environ.get("SBE_LOG_SILENT") is not None

def threaded_log():
    while SBE_Logger.SBE_LOG_THREAD_RUNNING:
        SBE_Logger.update()
        time.sleep(1.0)

class SBE_Timer():
    name: str = "Total"
    start_time: float = 0
    count: int = 0
    time: datetime.timedelta
    parents: list[str]
    children: dict[str, typing.Self]

    def get_time(self) -> datetime.timedelta:
        active = self.start_time != 0
        running_time = self.time
        if active:
            # Add current runtime
            running_time += datetime.timedelta(seconds=time.time() - self.start_time)
        return running_time



    def __init__(self, name: str = "Total", parents: list[str] = None, start: float = 0, count: int = 0):
        self.name = name
        self.start_time = start
        self.count = count
        self.time = datetime.timedelta(seconds=0)
        self.children = {}
        if parents is not None:
            self.parents = parents[:]
        else:
            self.parents = []


    def start(self, parents: list[str], timer: str, depth: int = 0):
        if self.start_time == 0:
            self.start_time = time.time()
        if depth < len(parents):
            parent = parents[depth]
            current = self.children[parent]
            current.start(parents=parents, timer=timer, depth=depth + 1)
            return
        if timer in self.children:
            existing: SBE_Timer = self.children[timer]
            existing.start_time = time.time()
            existing.count += 1
        else:
            self.children[timer] = SBE_Timer(
                name=timer, parents=parents,
                count=1, start=time.time())


    def stop(self, parents: list[str], timer: str):
        if len(parents):
            first = parents[:1][0]
            current = self.children[first]
            current.stop(parents[1:], timer)
            return
        assert self.name == timer, "Stopped timer wasn't most recently started"
        delta = datetime.timedelta(seconds=time.time() - self.start_time)
        self.time += delta
        self.start_time = 0


    def get_text(self, show_all = False) -> list[str]:
        result = []
        active = self.start_time != 0
        running_time = self.get_time()

        if SBE_MIN_TIME < running_time or show_all:
            line = ""
            if not self.parents:
                line += "\n"
            timer = " " * len(self.parents) * 2
            timer += self.name
            time_str = "0:00:00.000000"
            if SBE_ZERO_TIME < running_time:
                time_str = str(running_time)
            line += timer.ljust(SBE_LEFT_COL)
            line += time_str.ljust(SBE_TIME_COL)
            line += str(self.count).ljust(SBE_COUNT_COL)
            if active:
                line += "<=="
            result.append(line)

        descending = sorted(self.children.items(), key=lambda item: item[1].get_time(), reverse=True)
        for _, timer in descending:
            child_result = timer.get_text()
            result.extend(child_result)

        return result

class SBE_Logger():
    SBE_LOG_THREAD: threading.Thread = None
    SBE_LOG_THREAD_RUNNING = False
    SBE_ROOT_TIMER = SBE_Timer()
    SBE_MESSAGES: list[str] = []
    """Plain list of logged messages"""
    SBE_TIMER_STACK: list[str] = []
    """Stack of timer names currently running"""
    SBE_LAST_UPDATE: float = 0

    SBE_SKIP_LOG_CLEAR = False
    SBE_EXTRA_TEXT = " "
    """Additional text shown at the top of log output, needed for cli bake progress reporting"""


    @staticmethod
    def _chunk_string(string: str, length: int) -> list[str]:
        return (string[0 + i : length + i] for i in range(0, len(string), length))

    @staticmethod
    def start_auto_update():
        SBE_Logger.stop_auto_update()
        SBE_Logger.SBE_LOG_THREAD = threading.Thread(target=threaded_log)
        SBE_Logger.SBE_LOG_THREAD_RUNNING = True
        SBE_Logger.SBE_LOG_THREAD.start()

    @staticmethod
    def stop_auto_update():
        SBE_Logger.SBE_LOG_THREAD_RUNNING = False
        SBE_Logger.update(force=True)
        if SBE_Logger.SBE_LOG_THREAD:
            SBE_Logger.SBE_LOG_THREAD.join()

    @staticmethod
    def start(timer: str, push_update = True) -> None:
        SBE_Logger.SBE_ROOT_TIMER.start(SBE_Logger.SBE_TIMER_STACK, timer)
        SBE_Logger.SBE_TIMER_STACK.append(timer)
        if push_update:
            SBE_Logger.update()


    @staticmethod
    def stop(timer: str, push_update = True) -> None:
        SBE_Logger.SBE_ROOT_TIMER.stop(SBE_Logger.SBE_TIMER_STACK, timer)
        SBE_Logger.SBE_TIMER_STACK.pop()
        if push_update:
            SBE_Logger.update()


    @staticmethod
    def print(message: str, cut_stack: int = 1) -> None:
        stack = inspect.stack()
        caller_frame = stack[cut_stack]
        caller: str = f"{os.path.basename(caller_frame.filename)}:{caller_frame.lineno}".ljust(SBE_LEFT_COL)
        SBE_Logger.SBE_MESSAGES.append(f"{caller} {message}")
        SBE_Logger.update()

    @staticmethod
    def error(message: str, cut_stack: int = 1) -> None:
        stack = inspect.stack()
        caller_frame = stack[cut_stack]
        caller: str = f"{os.path.basename(caller_frame.filename)}:{caller_frame.lineno}".ljust(SBE_LEFT_COL)
        SBE_Logger.SBE_MESSAGES.append(f"  => ERROR: {caller} {message}")
        SBE_Logger.update()


    @staticmethod
    def get_log_text() -> str:
        lines = SBE_Logger.get_timings_window(show_all=True)
        lines.extend(SBE_Logger.SBE_MESSAGES)
        return "\n".join(lines)


    @staticmethod
    def get_timings_window(width: int = 80, height: int = 40, show_all = False) -> list[str]:
        lines: list[str] = []
        lines.append("=" * width)
        lines.append(f"Timer {bpy.app.version} {SBE_Logger.SBE_EXTRA_TEXT}{bpy.data.filepath}")
        lines.append("-" * width)

        text = SBE_Logger.SBE_ROOT_TIMER.get_text(show_all=show_all)
        text = text[:height - 3]
        lines.extend(text)

        padding = ["" for _ in range(0, max((height) - len(lines), 0))]
        lines.extend(padding)

        lines.append("=" * width)

        return lines


    @staticmethod
    def get_log_window(width: int = 80, height: int = sys.maxsize) -> list[str]:
        log_lines = len(SBE_Logger.SBE_MESSAGES)

        lines: list[str] = []
        lines.append(f"Logs ({str(log_lines)}):")
        lines.append("-" * width)

        height -= 1 # The footer line
        for i in range(max(0, log_lines - height), log_lines):
            for j in SBE_Logger._chunk_string(SBE_Logger.SBE_MESSAGES[i], width):
                lines.append(j)

        padding = ["" for _ in range(0, max(height - len(lines), 0))]
        lines.extend(padding)

        lines.append("=" * width)
        return lines


    @staticmethod
    def update(clear: bool = True, force: bool = False):
        current_time = time.time()
        if not force and current_time - SBE_Logger.SBE_LAST_UPDATE < (1.0 / 2.0):
            # prevent too many updates since the windows terminal slows down the bake a lot
            return
        SBE_Logger.SBE_LAST_UPDATE = current_time
        if clear and not SBE_LOG_SKIP_CLEAR and not SBE_LOG_SILENT:
            if is_windows:
                os.system("cls")
            else:
                os.system("clear")

        size: os.terminal_size = shutil.get_terminal_size((80, 40))
        size_y = size.lines - 10 # remove a few lines because blender also logs stuff
        size_y = max(size_y, 8)
        lines = SBE_Logger.get_timings_window(size.columns, int(size_y / 2) - 1)
        lines.extend(SBE_Logger.get_log_window(size.columns, int(size_y / 2)))
        if not SBE_LOG_SILENT:
            print('\n'.join(lines), flush=True)


    @staticmethod
    def clear():
        if SBE_Logger.SBE_SKIP_LOG_CLEAR:
            return
        SBE_Logger.SBE_ROOT_TIMER = SBE_Timer()
        SBE_Logger.SBE_MESSAGES = []

    def __init__(self, timer: str, push_update = True):
        self.timer = timer
        self.push_update = push_update

    def __enter__(self):
        SBE_Logger.start(self.timer, self.push_update)

    def __exit__(self, *args):
        SBE_Logger.stop(self.timer, self.push_update)
