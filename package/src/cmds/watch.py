import io
import os
import shutil
import sys
import threading
import time
from contextlib import redirect_stdout, redirect_stderr

from elyb.cmds.components.rawterm import RawTerminal, readByte

GREEN = "\033[32m"
RED   = "\033[31m"
DIM   = "\033[2m"
RESET = "\033[0m"

HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"


def termSize() -> tuple[int, int]:
    s = shutil.get_terminal_size()
    return s.columns, s.lines


def scanPluginFiles(cwd: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for root, dirs, files in os.walk(cwd):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            path = os.path.join(root, name)
            try:
                result[path] = os.path.getmtime(path)
            except OSError:
                pass
    return result


def hasChanged(prev: dict[str, float], curr: dict[str, float]) -> bool:
    if set(prev.keys()) != set(curr.keys()):
        return True
    for path, mtime in curr.items():
        if prev.get(path) != mtime:
            return True
    return False


class WatchUI:
    def __init__(self, intervalSeconds: int):
        self._logs: list[str] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._paused = False
        self._interval = intervalSeconds
        self._timerReset = time.time()

    def start(self):
        sys.stdout.write(HIDE_CURSOR + "\033[2J")
        sys.stdout.flush()
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1)

    def addLog(self, msg: str):
        with self._lock:
            self._logs.append(msg)

    def resetTimer(self):
        with self._lock:
            self._timerReset = time.time()

    def setPaused(self, paused: bool):
        with self._lock:
            self._paused = paused

    def isPaused(self) -> bool:
        with self._lock:
            return self._paused

    def _render(self) -> str:
        cols, rows = termSize()
        sep = DIM + "=" * cols + RESET
        footer = DIM + "  [Q] Quit   [P] Pause/Resume" + RESET

        with self._lock:
            elapsed = time.time() - self._timerReset
            remaining = max(0, self._interval - elapsed)
            logs = list(self._logs)

        timerLabel = f"  Next check: {remaining:.0f}s"

        logAreaRows = rows - 4
        buf: list[str] = []

        buf.append(f"\033[1;1H\033[2K{DIM}{timerLabel}{RESET}")
        buf.append(f"\033[2;1H\033[2K{sep}")

        visible = logs[-logAreaRows:] if len(logs) > logAreaRows else logs
        for i, entry in enumerate(visible):
            row = 3 + i
            buf.append(f"\033[{row};1H\033[2K{entry}{RESET}")

        for i in range(len(visible), logAreaRows):
            row = 3 + i
            buf.append(f"\033[{row};1H\033[2K{RESET}")

        buf.append(f"\033[{rows - 1};1H\033[2K{sep}")
        buf.append(f"\033[{rows};1H\033[2K{footer}")

        return "".join(buf)

    def _loop(self):
        while not self._stop.is_set():
            frame = self._render()
            sys.stdout.write("\033[H" + frame)
            sys.stdout.flush()
            time.sleep(0.25)


def _dispatchBuild(args: list[str]) -> None:
    import argparse
    from elyb.cmds.build import runBuild

    parser = argparse.ArgumentParser(prog="elyb build")
    parser.add_argument("--no-assets", action="store_true", dest="noAssets")
    parser.add_argument("-nf", "--no-folder", action="store_true", dest="noFolder")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose")
    parser.add_argument("-r", "--reset", action="store_true", dest="reset")
    parser.add_argument("-p", "--password", nargs=2, metavar=("METHOD", "PASSWORD"), dest="encrypt")
    parser.add_argument("-ni", "--no-info", action="store_true", dest="noInfo")
    parser.add_argument("-sv", "--static-version", nargs="+", metavar=("VERSION", "APPEND"), dest="staticVersion", default=None)
    parser.add_argument("-sc", "--static-client", nargs="+", metavar=("PACKAGE", "NAME"), dest="staticClient", default=None)
    modeGroup = parser.add_mutually_exclusive_group()
    modeGroup.add_argument("-a", "--ast", action="store_true", dest="checkAst")
    modeGroup.add_argument("-c", "--compile", nargs="?", type=int, choices=[0, 1, 2], const=1, default=None, dest="compile", metavar="LEVEL")
    parser.add_argument("-o", "--obfuscation", nargs="*", metavar="FILE", dest="obfuscation", default=None)

    parsed = parser.parse_args(args)

    encryptMethod, encryptPassword = (parsed.encrypt[0], parsed.encrypt[1]) if parsed.encrypt else (None, None)

    if parsed.staticVersion is not None:
        staticVersion = parsed.staticVersion[0]
        staticVersionInName = parsed.staticVersion[1].lower() == "true" if len(parsed.staticVersion) == 2 else False
    else:
        staticVersion = None
        staticVersionInName = False

    if parsed.staticClient is not None:
        staticClientPackage = parsed.staticClient[0]
        staticClientName = parsed.staticClient[1] if len(parsed.staticClient) == 2 else None
    else:
        staticClientPackage = None
        staticClientName = None

    runBuild(
        parsed.noAssets, parsed.noFolder, parsed.verbose,
        parsed.checkAst, parsed.compile, parsed.reset,
        encryptMethod, encryptPassword, parsed.noInfo,
        staticVersion, staticVersionInName,
        staticClientPackage, staticClientName,
        parsed.obfuscation
    )


def _extractBuiltPath(output: str) -> str | None:
    for line in output.splitlines():
        clean = line.replace(GREEN, "").replace(RED, "").replace(DIM, "").replace(RESET, "")
        if "Successful build at " in clean:
            parts = clean.split("Successful build at ", 1)
            if len(parts) == 2:
                return parts[1].rstrip("!")
    return None


def _renameToLatest(cwd: str, builtRelPath: str) -> str | None:
    srcPath = os.path.join(cwd, builtRelPath)
    if not os.path.isfile(srcPath):
        return None
    ext = os.path.splitext(builtRelPath)[1]
    destPath = os.path.join(cwd, "builds", f"latest{ext}")
    try:
        shutil.copy2(srcPath, destPath)
        return f"builds/latest{ext}"
    except OSError:
        return None


def runWatch(intervalSeconds: int, buildArgs: list[str]) -> None:
    cwd = os.getcwd()
    ui = WatchUI(intervalSeconds)
    ui.start()

    ui.addLog("• Polling started")

    def pollLoop():
        prevSnapshot = scanPluginFiles(cwd)

        while not ui._stop.is_set():
            for _ in range(intervalSeconds * 20):
                if ui._stop.is_set():
                    return
                time.sleep(0.05)

            if ui.isPaused():
                continue

            ui.resetTimer()
            ui.addLog("• Checking")
            currSnapshot = scanPluginFiles(cwd)

            if not hasChanged(prevSnapshot, currSnapshot):
                ui.addLog("• Nothing has changed")
                prevSnapshot = currSnapshot
                ui.resetTimer()
                continue

            ui.addLog("• Changes found")
            ui.addLog("• Starting the built")

            buf = io.StringIO()
            exitedClean = False
            try:
                with redirect_stdout(buf), redirect_stderr(buf):
                    _dispatchBuild(buildArgs)
                exitedClean = True
            except SystemExit as e:
                exitedClean = (e.code == 0 or e.code is None)
            except Exception as e:
                ui.addLog(f"{RED}• Build failed: {e}{RESET}")
                prevSnapshot = scanPluginFiles(cwd)
                ui.resetTimer()
                continue

            output = buf.getvalue()
            failPatterns = ("error:", "compilation failed:", "failed to complete build:")
            outputHasError = any(
                any(p in line.replace(GREEN, "").replace(RED, "").replace(DIM, "").replace(RESET, "").lower() for p in failPatterns)
                for line in output.splitlines()
            )
            success = exitedClean and not outputHasError

            if success:
                builtRelPath = _extractBuiltPath(output)
                if builtRelPath:
                    latestPath = _renameToLatest(cwd, builtRelPath)
                    label = latestPath if latestPath else builtRelPath
                else:
                    label = "builds/latest.eaf"
                ui.addLog(f"{GREEN}• Built successfully: {label}{RESET}")
            else:
                errorLine = ""
                for line in output.splitlines():
                    clean = line.replace(GREEN, "").replace(RED, "").replace(DIM, "").replace(RESET, "")
                    if "error:" in clean.lower():
                        errorLine = clean.strip()
                        break
                if not errorLine:
                    errorLine = output.splitlines()[-1] if output.strip() else "unknown error"
                ui.addLog(f"{RED}• Build failed: {errorLine}{RESET}")

            prevSnapshot = scanPluginFiles(cwd)
            ui.resetTimer()

    pollThread = threading.Thread(target=pollLoop, daemon=True)
    pollThread.start()

    fd = sys.stdin.fileno()
    try:
        with RawTerminal(fd):
            while True:
                ch = readByte(fd)
                key = ch.decode("utf-8", errors="ignore").lower()
                if key == "q" or ch == b"\x03":
                    break
                if key == "p":
                    paused = ui.isPaused()
                    ui.setPaused(not paused)
                    if paused:
                        ui.addLog("• Resumed")
                    else:
                        ui.addLog("• Paused")
    except Exception:
        pass

    ui.addLog("• Bye-bye")
    time.sleep(0.3)
    ui.stop()
    sys.stdout.write(SHOW_CURSOR + "\033[2J\033[H")
    sys.stdout.flush()
