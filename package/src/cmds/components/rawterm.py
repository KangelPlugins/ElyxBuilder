import sys

isWindows = sys.platform == "win32"

if isWindows:
    import msvcrt
else:
    import os
    import select
    import termios
    import tty

class RawTerminal:
    # unix
    def __init__(self, fd: int):
        self.fd = fd
        self._oldSettings = None

    def __enter__(self):
        if not isWindows:
            self._oldSettings = termios.tcgetattr(self.fd)
            tty.setraw(self.fd)
        return self

    def __exit__(self, excType, excVal, excTb):
        if not isWindows and self._oldSettings is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self._oldSettings)
        return False

def readByte(fd: int) -> bytes:
    if isWindows:
        return msvcrt.getch()
    return os.read(fd, 1)

def byteReady(fd: int, timeoutSeconds: float) -> bool:
    if isWindows:
        return msvcrt.kbhit()
    ready, _, _ = select.select([fd], [], [], timeoutSeconds)
    return bool(ready)

# win
WINDOWS_ARROW_MAP = {
    b"H": "A",  # up
    b"P": "B",  # down
    b"M": "C",  # right
    b"K": "D",  # left
}

def readKey(fd: int) -> str:
    if isWindows:
        ch = readByte(fd)
        if ch in (b"\xe0", b"\x00"):
            ch2 = readByte(fd)
            suffix = WINDOWS_ARROW_MAP.get(ch2)
            return "\x1b[" + suffix if suffix else "\x1b"
        if ch == b"\r":
            return "\r"
        return ch.decode("utf-8", errors="ignore")

    ch = readByte(fd)
    if ch != b"\x1b":
        return ch.decode("utf-8", errors="ignore")
    if not byteReady(fd, 0.05):
        return "\x1b"
    ch2 = readByte(fd)
    if ch2 != b"[":
        return "\x1b"
    if not byteReady(fd, 0.05):
        return "\x1b["
    ch3 = readByte(fd)
    return "\x1b[" + ch3.decode("utf-8", errors="ignore")
