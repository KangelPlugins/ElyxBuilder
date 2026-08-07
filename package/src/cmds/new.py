import json
import os
import random
import re
import sys
import shutil
import time
import threading

from elyb.cmds.components.rawterm import RawTerminal, readKey

CYAN  = "\033[96m"
GREEN = "\033[92m"
DIM   = "\033[2m"
BOLD  = "\033[1m"
RESET = "\033[0m"

HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

BLINK_INTERVAL = 0.53

# fields that are allowed to be empty
OPTIONAL_KEYS = {"icon", "author", "elyxVersion"}


def normalizeName(raw: str) -> str:
    # letter-control xD
    cleaned = re.sub(r"[^ _\-a-zA-Z0-9]", "", raw)
    parts = cleaned.split(" ")
    result = parts[0]
    for part in parts[1:]:
        if part:
            result += part[0].upper() + part[1:]
    return result


def writeFile(path: str, content: str):
    dirName = os.path.dirname(path)
    if dirName:
        os.makedirs(dirName, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def loadConfig() -> dict:
    configPath = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(configPath, "r", encoding="utf-8") as f:
        return json.load(f)


def termSize() -> tuple[int, int]:
    s = shutil.get_terminal_size()
    return s.columns, s.lines


class Field:
    def __init__(self, key: str, label: str, value: str, hint: str = "", emptyHint: str = ""):
        self.key       = key
        self.label     = label
        self.value     = value
        self.default   = value
        self.hint      = hint
        self.emptyHint = emptyHint
        self.cursor    = len(value)
        self.touched   = False
    def reset(self):
        self.value   = self.default
        self.cursor  = len(self.default)
        self.touched = False
    def insert(self, ch: str):
        self.value  = self.value[:self.cursor] + ch + self.value[self.cursor:]
        self.cursor += 1
        self.touched = True
    def backspace(self):
        if self.cursor > 0:
            self.value  = self.value[:self.cursor - 1] + self.value[self.cursor:]
            self.cursor -= 1
            self.touched = True
    def delete(self):
        if self.cursor < len(self.value):
            self.value   = self.value[:self.cursor] + self.value[self.cursor + 1:]
            self.touched = True
    def moveLeft(self):
        if self.cursor > 0:
            self.cursor -= 1
    def moveRight(self):
        if self.cursor < len(self.value):
            self.cursor += 1


def buildFields(cfg: dict) -> list[Field]:
    return [
        Field("name",        "name",         "MyPlugin"),
        Field("author",      "author",        "NoName"),
        Field("id",          "id",            "NoName_MyPlugin",  hint="auto"),
        Field("version",     "version",       "0.1.0"),
        Field("appVersion",  "app_version",   cfg["appVersion"]),
        Field("sdkVersion",  "sdk_version",   cfg["sdkVersion"]),
        Field("elyxVersion", "elyx_version",  cfg["elyxVersion"]),
        Field("icon",        "icon",          "",                 hint="optional", emptyHint="(pack/index)"),
    ]


def syncId(fields: list[Field]):
    idField = next(f for f in fields if f.key == "id")
    if idField.touched:
        return
    nameField   = next(f for f in fields if f.key == "name")
    authorField = next(f for f in fields if f.key == "author")
    norm   = normalizeName(nameField.value)   or "Plugin"
    normAu = normalizeName(authorField.value) or "NoName"
    newId  = f"{normAu}_{norm}"
    if len(newId) > 32:
        newId = newId[:32]
    if idField.value != newId:
        idField.value  = newId
        idField.cursor = len(newId)


def resolveHint(field: Field) -> str:
    if field.key == "id":
        return "" if field.touched else field.hint
    if field.key == "icon":
        if not field.value:
            parts = []
            if field.hint:
                parts.append(field.hint)
            if field.emptyHint:
                parts.append(field.emptyHint)
            return "  ".join(parts) if parts else ""
        return ""
    return field.hint


def renderFrame(fields: list[Field], active: int, blinkOn: bool, extraHint: str = "") -> str:
    cols, rows = termSize()

    HEADER = 2  # title + separator
    FOOTER = 4  # sep + input + sep + keybinds

    fieldAreaRows = rows - HEADER - FOOTER
    fieldCount    = len(fields)
    labelWidth    = max(len(f.label) for f in fields) + 2
    rowContent: dict[int, str] = {}

    # title
    title = "ElyxBuilder / New Elyx plugin"
    pad   = max(0, (cols - len(title)) // 2)
    rowContent[1] = DIM + " " * pad + title + RESET

    # top separator
    rowContent[2] = DIM + "=" * cols + RESET

    # fields
    totalFieldRows = fieldCount + (fieldCount - 1)
    startRow = HEADER + 1 + max(0, (fieldAreaRows - totalFieldRows) // 2)

    for i, field in enumerate(fields):
        row = startRow + i * 2
        if row > rows - FOOTER:
            break
        isActive = (i == active)
        arrow    = (CYAN + "➜" + RESET) if isActive else " "
        label    = field.label.ljust(labelWidth)
        labelStr = (CYAN + BOLD + label + RESET) if isActive else (DIM + label + RESET)
        if isActive:
            valueStr = CYAN + field.value + RESET
        else:
            valueStr = field.value
        hintText = resolveHint(field)
        hint = (DIM + "  " + hintText + RESET) if hintText else ""
        rowContent[row] = f"  {arrow} {labelStr} {valueStr}{hint}"

    # bottom separator (above input)
    sepRow = rows - FOOTER + 1
    rowContent[sepRow] = DIM + "=" * cols + RESET

    # input line
    inputRow = rows - FOOTER + 2
    f        = fields[active]
    before   = f.value[:f.cursor]
    after    = f.value[f.cursor:]
    cur      = "_" if blinkOn else " "
    rowContent[inputRow] = f"  {DIM}>{RESET} {CYAN}{before}{cur}{after}{RESET}"

    # separator below input
    rowContent[rows - FOOTER + 3] = DIM + "=" * cols + RESET

    # keybinds
    baseHint = "  [↑] Prev   [↓] Next   [Enter] Confirm   [Ctrl+R] Reset   [Ctrl+C] Cancel"
    extra    = ("   " + extraHint) if extraHint else ""
    rowContent[rows] = DIM + baseHint + extra + RESET

    buf: list[str] = []
    for r in range(1, rows + 1):
        buf.append(f"\033[{r};1H\033[2K")
        content = rowContent.get(r)
        if content is not None:
            buf.append(content)
    buf.append(f"\033[{rows};1H")
    return "".join(buf)


class Renderer:
    def __init__(self, fields: list[Field]):
        self.fields     = fields
        self.active     = 0
        self.blinkOn    = True
        self.extraHint  = ""
        self._lock   = threading.Lock()
        self._stop   = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self._thread.start()
    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1)
    def update(self, fn):
        with self._lock:
            fn()

    def _loop(self):
        sys.stdout.write("\033[2J")
        sys.stdout.flush()
        prevFrame  = ""
        nextBlink  = time.monotonic() + BLINK_INTERVAL

        while not self._stop.is_set():
            now = time.monotonic()
            if now >= nextBlink:
                with self._lock:
                    self.blinkOn = not self.blinkOn
                nextBlink = now + BLINK_INTERVAL

            with self._lock:
                frame = renderFrame(self.fields, self.active, self.blinkOn, self.extraHint)

            if frame != prevFrame:
                sys.stdout.write("\033[H" + frame)
                sys.stdout.flush()
                prevFrame = frame
            time.sleep(0.016)

def collectValues(fields: list[Field]) -> dict:
    return {f.key: f.value for f in fields}

def validateFields(fields: list[Field]) -> str | None:
    for f in fields:
        if f.key not in OPTIONAL_KEYS and not f.value.strip():
            return f.label
    return None



# format options: (key, label, choices, default_index)
FORMAT_ITEMS = [
    ("refmap_format",   "refmap_format",   ["yaml", "json"], 0),
    ("metainfo_format", "metainfo_format", ["yaml", "json"], 0),
]


def animateFormatScreen(fields: list[Field], renderer: "Renderer", fd: int) -> list[int]:
    N          = len(FORMAT_ITEMS)
    selections = [item[3] for item in FORMAT_ITEMS]
    active     = 0

    cols, rows = termSize()
    HEADER = 2
    FOOTER = 4
    fieldAreaRows  = rows - HEADER - FOOTER
    fieldCount     = len(fields)
    totalFieldRows = fieldCount + (fieldCount - 1)
    startRow       = HEADER + 1 + max(0, (fieldAreaRows - totalFieldRows) // 2)
    labelWidth     = max(len(f.label) for f in fields) + 2

    def fieldRow(i: int) -> int:
        return startRow + i * 2

    def writeRow(row: int, content: str):
        sys.stdout.write(f"\033[{row};1H\033[2K{content}")
        sys.stdout.flush()

    def formatLine(i: int, vis: str | None = None) -> str:
        _, label, choices, _ = FORMAT_ITEMS[i]
        isActive = (i == active)
        lbl = (CYAN + BOLD + label.ljust(labelWidth) + RESET) if isActive else (DIM + label.ljust(labelWidth) + RESET)
        if vis is not None:
            return f"   {lbl} {DIM}{vis}{RESET}_"
        sel = selections[i]
        parts: list[str] = []
        for j, ch in enumerate(choices):
            if j == sel:
                parts.append(BOLD + ch + RESET)
            else:
                parts.append(DIM + ch + RESET)
        # active row: cyan arrow; inactive: space
        arrow = (CYAN + "➜" + RESET if isActive else " ")
        return f"  {arrow} {lbl} " + "  ".join(parts)
    renderer.stop()

    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

    # tyank you for the logo, claude
    LOGO_LINES = [
        "███████╗██╗  ██╗   ██╗██╗  ██╗",
        "██╔════╝██║  ╚██╗ ██╔╝╚██╗██╔╝",
        "█████╗  ██║   ╚████╔╝  ╚███╔╝ ",
        "██╔══╝  ██║    ╚██╔╝   ██╔██╗ ",
        "███████╗███████╗██║   ██╔╝ ██╗",
        "╚══════╝╚══════╝╚═╝   ╚═╝  ╚═╝",
    ]
    LOGO_H      = len(LOGO_LINES)
    LOGO_NEEDED = LOGO_H + 2

    # is he Epstein!?
    def _logo_color(row: int, col: int, max_row: int, max_col: int) -> str:
        t = (row / max(max_row, 1) + col / max(max_col, 1)) / 2
        r = round(0x00 + (0x63 - 0x00) * t)
        g = round(0x4e + (0x9f - 0x4e) * t)
        b = round(0xcc + (0xff - 0xcc) * t)
        return f"\033[38;2;{r};{g};{b}m"

    sepRow    = rows - FOOTER + 1
    lastField = fieldRow(N - 1)
    gapStart  = lastField + 1
    gapEnd    = sepRow - 1
    gapSize   = gapEnd - gapStart + 1

    # redraw chrome (title + separators)
    title = "ElyxBuilder / New Elyx plugin"
    padT  = max(0, (cols - len(title)) // 2)
    buf: list[str] = []
    buf.append(f"\033[1;1H\033[2K{DIM}{' ' * padT}{title}{RESET}")
    buf.append(f"\033[2;1H\033[2K{DIM}{'=' * cols}{RESET}")
    buf.append(f"\033[{sepRow};1H\033[2K{DIM}{'=' * cols}{RESET}")
    kaomoji = random.choice(["^-^", "^w^", "QwQ", "UwU", "OwO"])
    kao_pad = max(0, (cols - len(kaomoji)) // 2)
    buf.append(f"\033[{rows - FOOTER + 2};1H\033[2K{DIM}{' ' * kao_pad}{kaomoji}{RESET}")
    buf.append(f"\033[{rows - FOOTER + 3};1H\033[2K{DIM}{'=' * cols}{RESET}")
    buf.append(f"\033[{rows};1H\033[2K")

    # draw logo only if it fits in the gap
    if gapSize >= LOGO_NEEDED:
        logoWidth    = max(len(l) for l in LOGO_LINES)
        logoPad      = max(0, (cols - logoWidth) // 2)
        logoStartRow = gapStart + (gapSize - LOGO_H) // 2
        max_row      = LOGO_H - 1
        max_col      = logoWidth - 1
        for li, line in enumerate(LOGO_LINES):
            r        = logoStartRow + li
            segments = []
            prev_esc = None
            for ci, ch in enumerate(line):
                esc = _logo_color(li, ci, max_row, max_col)
                if esc != prev_esc:
                    segments.append(esc)
                    prev_esc = esc
                segments.append(ch)
            buf.append(f"\033[{r};1H\033[2K{' ' * logoPad}{''.join(segments)}{RESET}")

    sys.stdout.write("".join(buf))
    sys.stdout.flush()

    hint = DIM + "  [↑] Prev   [↓] Next   [Enter] Confirm   [Ctrl+C] Cancel   [←] [→] Choice" + RESET
    sys.stdout.write(f"\033[{rows};1H\033[2K{hint}")

    sys.stdout.flush()

    # typing
    for i, (_, label, choices, defIdx) in enumerate(FORMAT_ITEMS):
        row    = fieldRow(i)
        target = "  ".join(choices)
        for n in range(1, len(target) + 1):
            writeRow(row, formatLine(i, target[:n]))
            time.sleep(0.018)
        writeRow(row, formatLine(i))

    # loop
    while True:
        key = readKey(fd)
        if key in ("\x03", "\x1b"):
            break
        elif key == "\x1b[A":
            if active > 0:
                prev   = active
                active -= 1
                writeRow(fieldRow(prev),   formatLine(prev))
                writeRow(fieldRow(active), formatLine(active))
        elif key == "\x1b[B":
            if active < N - 1:
                prev   = active
                active += 1
                writeRow(fieldRow(prev),   formatLine(prev))
                writeRow(fieldRow(active), formatLine(active))

        elif key == "\r":
            if active < N - 1:
                prev   = active
                active += 1
                writeRow(fieldRow(prev),  formatLine(prev))
                writeRow(fieldRow(active), formatLine(active))
            else:
                break
        elif key == "\x1b[C":
            _, _, choices, _ = FORMAT_ITEMS[active]
            selections[active] = (selections[active] + 1) % len(choices)
            writeRow(fieldRow(active), formatLine(active))
        elif key == "\x1b[D":
            _, _, choices, _ = FORMAT_ITEMS[active]
            selections[active] = (selections[active] - 1) % len(choices)
            writeRow(fieldRow(active), formatLine(active))
    return selections


def drawCreating(shown: list[str], done: bool, cols: int, rows: int, pluginName: str):
    totalFiles = 7
    centerCol  = cols // 2
    titleRow   = max(1, rows // 2 - totalFiles // 2 - 2)

    buf: list[str] = []
    for r in range(1, rows + 1):
        buf.append(f"\033[{r};1H\033[2K")
    buf.append(f"\033[{titleRow};1H")
    rawTitle = f"creating {pluginName}"
    pad = max(0, centerCol - len(rawTitle) // 2)
    buf.append(" " * pad + DIM + "creating " + RESET + CYAN + pluginName + RESET)
    for i, fname in enumerate(shown):
        row     = titleRow + 2 + i
        rawLine = f"  x {fname}"
        lpad    = max(0, centerCol - len(rawLine) // 2)
        buf.append(f"\033[{row};1H")
        buf.append(" " * lpad + f"  {GREEN}✦{RESET} {fname}")
    if done:
        doneRow = titleRow + 2 + totalFiles + 2
        buf.append(f"\033[{doneRow};1H")
        doneRaw = "✓  done"
        buf.append(" " * max(0, centerCol - len(doneRaw) // 2) + GREEN + doneRaw + RESET)
    sys.stdout.write("".join(buf))
    sys.stdout.flush()


def animateCreating(normalized: str, pluginName: str, refmapFmt: str = "yaml", metainfoFmt: str = "yaml"):
    cols, rows = termSize()
    sys.stdout.write("\033[2J")
    sys.stdout.flush()
    metaExt   = "json" if metainfoFmt == "json" else "yml"
    refmapExt = "json" if refmapFmt   == "json" else "yml"

    fileList = [
        f"{normalized}/.elyxbuilder/config.yml",
        f"{normalized}/locales/strings_en.json",
        f"{normalized}/locales/strings_ru.json",
        f"{normalized}/meta.{metaExt}",
        f"{normalized}/res/.gitkeep",
        f"{normalized}/src/main.py",
        f"refmap.{refmapExt}",
    ]

    shown: list[str] = []
    for fname in fileList:
        shown.append(fname)
        drawCreating(shown, False, cols, rows, pluginName)
        time.sleep(0.05)
    drawCreating(shown, True, cols, rows, pluginName)
    time.sleep(0.7)


def runInteractive():
    cfg    = loadConfig()
    fields = buildFields(cfg)
    fd     = sys.stdin.fileno()
    rawTerminal = RawTerminal(fd)
    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()
    renderer  = Renderer(fields)
    renderer.start()
    cancelled = False
    try:
        rawTerminal.__enter__()
        while True:
            key = readKey(fd)
            if key in ("\x03", "\x1b"):
                cancelled = True
                break
            elif key == "\x1b[B":
                def _next():
                    renderer.active = (renderer.active + 1) % len(fields)
                renderer.update(_next)
            elif key == "\x1b[A":
                def _prev():
                    renderer.active = (renderer.active - 1) % len(fields)
                renderer.update(_prev)

            elif key == "\x1b[C":
                def _right():
                    fields[renderer.active].moveRight()
                renderer.update(_right)
            elif key == "\x1b[D":
                def _left():
                    fields[renderer.active].moveLeft()
                renderer.update(_left)

            elif key in ("\r", "\n"):
                with renderer._lock:
                    isLast = renderer.active == len(fields) - 1
                if isLast:
                    break
                def _enter():
                    renderer.active += 1
                renderer.update(_enter)

            elif key == "\x7f":
                def _bs():
                    fields[renderer.active].backspace()
                    syncId(fields)
                renderer.update(_bs)

            elif key == "\x04":
                def _del():
                    fields[renderer.active].delete()
                    syncId(fields)
                renderer.update(_del)

            elif key == "\x12":
                # ctrl+r
                def _reset():
                    fields[renderer.active].reset()
                    syncId(fields)
                renderer.update(_reset)

            elif len(key) == 1 and ord(key) >= 32:
                ch = key
                def _ins():
                    fields[renderer.active].insert(ch)
                    syncId(fields)
                renderer.update(_ins)
    except KeyboardInterrupt:
        cancelled = True

    if not cancelled:
        missingLabel = validateFields(fields)
        if missingLabel:
            renderer.stop()
            rawTerminal.__exit__(None, None, None)
            sys.stdout.write(SHOW_CURSOR + "\033[2J\033[H")
            sys.stdout.flush()
            print(f"error: field \"{missingLabel}\" is required")
            sys.exit(1)

        # fmt selection screen
        formatSelections = animateFormatScreen(fields, renderer, fd)

    if cancelled:
        renderer.stop()
    rawTerminal.__exit__(None, None, None)
    sys.stdout.write(SHOW_CURSOR)
    sys.stdout.flush()

    if cancelled:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
        return

    vals = collectValues(fields)
    pluginname = vals["name"]
    normalized = normalizeName(pluginname) or "MyPlugin"
    author = vals["author"]
    pluginId = vals["id"] or f"{normalizeName(author)}_{normalized}"
    if len(pluginId) > 32:
        pluginId = pluginId[:32]
    version = vals["version"] or "0.1.0"
    appVersion = vals["appVersion"]
    sdkVersion = vals["sdkVersion"]
    elyxVersion = vals["elyxVersion"]
    iconRaw = vals["icon"]

    refmapFmt   = FORMAT_ITEMS[0][2][formatSelections[0]]
    metainfoFmt = FORMAT_ITEMS[1][2][formatSelections[1]]
    animateCreating(normalized, pluginname, refmapFmt, metainfoFmt)
    writePlugin(pluginname, normalized, author, pluginId, version,
                appVersion, sdkVersion, elyxVersion, iconRaw,
                refmapFmt, metainfoFmt)
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def runNew(pluginname: str, author: str, zipformat: str = "eaf"):
    normalized       = normalizeName(pluginname)
    normalizedAuthor = normalizeName(author)
    cfg              = loadConfig()
    pluginId         = f"{normalizedAuthor}_{normalized}"
    if len(pluginId) > 32:
        pluginId = pluginId[:32]
    writePlugin(
        pluginname, normalized, author, pluginId,
        "0.1.0", cfg["appVersion"], cfg["sdkVersion"], cfg["elyxVersion"],
        "", zipformat=zipformat
    )


def writePlugin(
    pluginname: str,
    normalized: str,
    author: str,
    pluginId: str,
    version: str,
    appVersion: str,
    sdkVersion: str,
    elyxVersion: str,
    icon: str,
    refmapFmt: str = "yaml",
    metainfoFmt: str = "yaml",
    zipformat: str = "eaf",
):
    base = normalized

    writeFile(
        f"{base}/.elyxbuilder/config.yml",
        f'zipFormat: {zipformat}\n'
        f'source: {normalized}/src\n'
        f'buildNameUncompiled: "{{name}}-{{version}}"\n'
        f'buildNameCompiled: "{{name}}-{{version}}-3.11"\n'
        f'ignoreAll:\n'
        f'  - {normalized}/.elyxbuilder/cache/*\n'
        f'compilationIgnore:\n'
        f'  - {normalized}/src/main.py\n'
        f'RemoveLogs: true # removes logs during obfuscation\n'
    )

    writeFile(
        f"{base}/locales/strings_en.json",
        '{\n  "description": "Enter plugin description"\n}\n'
    )

    writeFile(
        f"{base}/locales/strings_ru.json",
        '{\n  "description": "Введите описание плагина"\n}\n'
    )

    metaExt  = "json" if metainfoFmt == "json" else "yml"
    metaPath = f"{base}/meta.{metaExt}"

    if metainfoFmt == "json":
        iconVal = icon if icon else None
        metaData: dict = {
            "name":         pluginname,
            "description":  "{description}",
            "id":           pluginId,
            "version":      version,
            "author":       author,
            "app_version":  appVersion,
            "sdk_version":  sdkVersion,
            "elyx_version": elyxVersion,
        }
        if iconVal:
            metaData["icon"] = iconVal
        writeFile(metaPath, json.dumps(metaData, indent=2, ensure_ascii=False) + "\n")
    else:
        iconLine = f'icon: {icon}\n' if icon else '# icon: \n'
        writeFile(
            metaPath,
            f'name: {pluginname}\n'
            f'description: "{{description}}"\n'
            f'id: {pluginId}\n'
            f'version: "{version}"\n'
            f'author: "{author}"\n'
            f'app_version: "{appVersion}"\n'
            f'sdk_version: "{sdkVersion}"\n'
            f'elyx_version: "{elyxVersion}"\n'
            f'{iconLine}'
        )

    os.makedirs(f"{base}/res", exist_ok=True)
    open(f"{base}/res/.gitkeep", "w").close()

    writeFile(
        f"{base}/src/main.py",
        f'from base_plugin import BasePlugin\n'
        f'from android_utils import log\n'
        f'\n'
        f'class {normalized}Main(BasePlugin):\n'
        f'    def on_plugin_load(self):\n'
        f'        log("Hello, Elyx!")\n'
        f'\n'
        f'    def on_plugin_unload(self):\n'
        f'        log("Bye, Elyx!")\n'
    )

    refmapExt = "json" if refmapFmt == "json" else "yml"

    if refmapFmt == "json":
        refmapData = {
            "metainfo":    metaPath,
            "main":        f"{normalized}/src/main.py",
            "assets":      f"{normalized}/res",
            "strings":     f"{normalized}/locales",
            "elyxbuilder": f"{normalized}/.elyxbuilder",
        }
        writeFile(f"refmap.{refmapExt}", json.dumps(refmapData, indent=2) + "\n")
    else:
        writeFile(
            f"refmap.{refmapExt}",
            f'metainfo: {metaPath}\n'
            f'main: {normalized}/src/main.py\n'
            f'assets: {normalized}/res\n'
            f'strings: {normalized}/locales\n'
            f'elyxbuilder: {normalized}/.elyxbuilder\n'
        )

if __name__ == "__main__":
    runInteractive()
