# ElyxBuilder

CLI tool for building Elyx plugins.

## Installation

```
pip install ElyxBuilder
```

## Requirements

- Python >= 3.10
- Python 3.11 — required only for `.pyc` compilation
- pyzipper — required only for archive encryption

---

## Commands

> All commands must be run from the project root — the directory containing `refmap.yml`.

### `elyb --version`

Prints the ElyxBuilder version.

---

### `elyb new`

Scaffolds a new plugin in the current directory.

By default, opens an interactive prompt for each `meta.yml` field. Each field shows a generated default in brackets — press Enter to accept it.

```bash
elyb new
```

With `-g` / `--gen`, skips the prompt and generates the plugin immediately using the provided flags:

```bash
elyb new -g -n "My Plugin" -a myname
elyb new -g -n "My Plugin" -a myname -zf eaf
```

| Flag | Description |
|---|---|
| `-g`, `--gen` | Fast generation (non-interactive) |
| `-n`, `--name` | Plugin name (required with `--gen`) |
| `-a`, `--author` | Author identifier (required with `--gen`) |
| `-zf`, `--zipformat` | Archive extension (default: `eaf`, only with `--gen`) |

The name is normalized for file/folder names: spaces are removed with the next word capitalized (CamelCase), special characters except `_`, `-`, letters, and digits are stripped. In `meta.yml` the name is stored as-is.

Plugin ID is built as `author_PluginName`, truncated to 32 characters.

`description` is always auto-generated as a `{description}` placeholder and is not prompted.

---

### `elyb build`

Packages the plugin into an archive. Must be run from the directory containing `refmap.yml`.

```bash
elyb build
elyb build -v
elyb build --no-assets
elyb build --no-folder
elyb build --ast
elyb build --compile
elyb build --compile 2
elyb build --compile --reset
elyb build --compile -o
elyb build --compile -o src/module.py src/other.py
elyb build -p aes-256 mypassword
elyb build -sv 1.0.0
elyb build -sv 1.0.0 true
elyb build -sc com.example.client
elyb build -sc com.example.client myclient
```

| Flag | Description |
|---|---|
| `--no-assets` | Exclude files listed in `optionalAssets` |
| `-nf`, `--no-folder` | Exclude the `elyxbuilder` directory from the archive |
| `-v`, `--verbose` | Print a detailed build log |
| `-a`, `--ast` | Check `.py` syntax via AST before building |
| `-c [LEVEL]`, `--compile [LEVEL]` | Compile `.py` → `.pyc` (Python 3.11); LEVEL is 0–2 (default: 1) |
| `-r`, `--reset` | Clear the compilation cache before building (requires `--compile`) |
| `-o [FILE...]`, `--obfuscation [FILE...]` | Obfuscate source before packaging; omit files to obfuscate everything |
| `-p METHOD PASS` | Encrypt the archive |
| `-ni`, `--no-info` | Skip appending the elyxbuilder info block to `meta.yml` |
| `-sv VERSION [APPEND]` | Add `staticVer` to the build info block; optional `APPEND=true` appends `-{version}` to the archive name (default: `false`) |
| `-sc PACKAGE [NAME]` | Add `client` to the build info block; optional `NAME` appends `-{name}` to the archive name |

`--ast` and `--compile` are mutually exclusive.

Output is written to `builds/`.

#### Build info

Before packaging, elyxbuilder appends a comment block to `meta.yml` inside the archive. The source file on disk is not modified.

```yaml
# elyxbuilder info
compiled: true/false
buildNum: 5
buildDate: 2026-05-09
pythonVer: 3.11
sourceHash: a3f2...
elybVer: 0.3.0
staticVer: "1.0.0"
client: "com.example.client"
```

`staticVer` is only present when `-sv` / `--static-version` is passed. When the optional second argument is `true`, `-{version}` is appended to the archive name (e.g. `MyPlugin-1.0.0.eaf`).

`client` is only present when `-sc` / `--static-client` is passed. When the optional second argument is provided, `-{name}` is appended to the archive name (e.g. `MyPlugin-myclient.eaf`).

Use `-ni` / `--no-info` to skip this block entirely.

#### Compilation (`--compile`)

Files in `compilationIgnore` are not compiled and are included in the archive as `.py`. All other `.py` files are replaced with compiled `.pyc`. An incremental cache is used — subsequent builds only recompile changed files.

The optional level argument (0–2) maps to `py_compile` optimization levels:

| Level | Effect |
|---|---|
| `0` | No optimization (keeps asserts and docstrings) |
| `1` (default) | Strips assert statements |
| `2` | Strips assert statements and docstrings |

Changing the level invalidates the cache, so all files are recompiled.

#### Encryption (`-p`)

Requires: `pip install pyzipper`

| Method | Description |
|---|---|
| `zipcrypto` | Standard ZIP encryption |
| `aes-128` | AES 128-bit |
| `aes-192` | AES 192-bit |
| `aes-256` | AES 256-bit (recommended) |

```bash
elyb build -p aes-256 mypassword
```

---

### `elyb cached`

Shows which files have changed since the last compilation. Must be run from the directory containing `refmap.yml`.

```bash
elyb cached
```

Requires a prior build with `--compile`.

| Status | Description |
|---|---|
| `ok` | File unchanged, cache is up to date |
| `modified` | File has changed since last compilation |
| `new` | File has never been compiled |
| `ignored` | File is in `compilationIgnore` |

---

### `elyb watch <seconds>`

Watches the plugin directory for changes and rebuilds automatically. Must be run from the directory containing `refmap.yml`.

```bash
elyb watch 20
elyb watch 20 --args "-c -v -nf -sv 12.6.4 true"
elyb watch 10 -a "-c"
```

| Flag | Description |
|---|---|
| `-a`, `--args` | Arguments to pass to `elyb build` (quoted string) |

Enters an interactive fullscreen mode. Every `<seconds>` seconds it scans the plugin directory for changes. If any file was added, removed, or modified since the last check, a build is triggered with the provided arguments.

The output archive is always saved as `builds/latest.eaf` (or the appropriate extension). Build logs are suppressed — only watch events appear on screen.

**Controls:**

| Key | Action |
|---|---|
| `Q` | Quit |
| `P` | Pause / Resume polling |

**Log messages:**

| Message | When |
|---|---|
| `• Polling started` | On startup |
| `• Checking` | Each poll tick |
| `• Nothing has changed` | No changes detected |
| `• Changes found` | Changes detected |
| `• Starting the built` | Build is about to start |
| `• Built successfully: builds/latest.eaf` | Build succeeded (green) |
| `• Built failed: {error}` | Build failed (red) |
| `• Paused` | Polling paused |
| `• Resumed` | Polling resumed |
| `• Bye-bye` | On quit |

---

### `elyb add-ignore <path> <target>`

Adds a path to one of the ignore lists in `.elyxbuilder/config.yml`.

```bash
elyb add-ignore "MyPlugin/res/heavy.png" --no-assets
elyb add-ignore "MyPlugin/.elyxbuilder/cache/*" --all
elyb add-ignore "MyPlugin/src/helpers.py" --compile
```

| Flag | List | Effect |
|---|---|---|
| `-a`, `--all` | `ignoreAll` | Exclude from every build |
| `-na`, `--no-assets` | `optionalAssets` | Exclude when `--no-assets` is passed |
| `-c`, `--compile` | `compilationIgnore` | Skip compilation for this file |

Backslashes are normalized to forward slashes. Duplicates are not added.

---

### `elyb del-ignore <index> <target>`

Removes an entry from an ignore list by its zero-based index.

```bash
elyb del-ignore 0 --all
elyb del-ignore 2 --no-assets
elyb del-ignore 1 --compile
```

Flags are the same as `add-ignore`. The index corresponds to the position in the list in `config.yml`.

---

### `elyb stats builds`

Shows build count statistics. Must be run from the directory containing `refmap.yml`.

```bash
elyb stats builds
```

Example output:

```
Total builds: 10
Uncompiled: 6 (60%)
Compiled: 3 (30%)
Failed: 1 (10%)
```

---

### `elyb stats lines`

Counts lines of code in the plugin. Must be run from the directory containing `refmap.yml`.

```bash
elyb stats lines
```

Counts only `.py` files in the `source` directory (from `config.yml`). Example output:

```
Lines count statistics for plugin MyPlugin:
MyPlugin/src: 142 (Python only)
```

With `-a` / `--all`, counts all non-binary files in the plugin root directory and `refmap.yml`:

```bash
elyb stats lines --all
```

Example output:

```
Total lines count statistics for plugin MyPlugin:
.py: 142
.yml: 30
Total: 172
```

With `-add` / `--additional`, includes additional directories relative to `cwd` (requires `--all`):

```bash
elyb stats lines --all --additional docs scripts
```

| Flag | Description |
|---|---|
| `-a`, `--all` | Count all non-binary files in plugin root |
| `-add DIR...`, `--additional DIR...` | Add extra directories to count (requires `--all`) |

---

### `elyb stats size`

Shows file size statistics. Must be run from the directory containing `refmap.yml`.

```bash
elyb stats size
```

Shows the total size of `.py` files in the `source` directory (from `config.yml`). Example output:

```
The size of the directory MyPlugin/src: 4.21 KB (0.0 MB)
Python only
```

With `-a` / `--all`, counts all non-binary files in the plugin root directory and `refmap.yml`:

```bash
elyb stats size --all
```

Example output:

```
File size statistics for plugin MyPlugin:
.py: 4.21 KB (0.0 MB)
.yml: 0.83 KB (0.0 MB)
```

With `-add` / `--additional`, includes additional directories relative to `cwd` (requires `--all`):

```bash
elyb stats size --all --additional docs scripts
```

| Flag | Description |
|---|---|
| `-a`, `--all` | Count all non-binary files in plugin root |
| `-add DIR...`, `--additional DIR...` | Add extra directories to count (requires `--all`) |

---

### `elyb stats files`

Shows file count by extension. Must be run from the directory containing `refmap.yml`.

```bash
elyb stats files
```

Counts all files in the plugin root directory by extension. Example output:

```
File count statistics for plugin MyPlugin:
.py: 5
.yml: 3
Total: 8
```

With `-a` / `--all`, also includes `refmap.yml`:

```bash
elyb stats files --all
```

With `-add` / `--additional`, includes additional directories relative to `cwd`:

```bash
elyb stats files --all --additional docs scripts
```

| Flag | Description |
|---|---|
| `-a`, `--all` | Include `refmap.yml` and additional directories |
| `-add DIR...`, `--additional DIR...` | Add extra directories to count (requires `--all`) |

---

## Obfuscation

> **Beta.** Obfuscated builds may produce unexpected behavior at runtime. Test thoroughly before distributing. Use at your own risk.

Obfuscation transforms Python source via AST before packaging. It can be used standalone or together with `-c`:

```bash
elyb build -o                 # obfuscate all source files, include as .py
elyb build -o src/module.py  # obfuscate specific files only
elyb build -c -o              # obfuscate + compile to .pyc
elyb build -c -o src/a.py    # obfuscate specific files + compile
```

Without file arguments, every `.py` file in the `source` directory is obfuscated. With file arguments, only the listed paths (relative to the project root) are obfuscated; the rest are processed as usual.

When used with `-c`, obfuscated files are never cached — every build recompiles them from scratch to guarantee a fresh random result.

After a successful obfuscated build, a mapping file is saved to `builds/latest_mapping.json`. It records how top-level function and class names were renamed, which is useful for debugging.

### Pipeline stages

The pipeline runs in the following order. Each stage can be disabled independently via `config.yml` (see [Config](#obfuscation-config) below).

#### 1. Strip docstrings (`stripDocstrings`)

Removes all docstrings from modules, classes, and functions. The first string literal in each body is dropped; if the body becomes empty, a `pass` statement is inserted.

Skipped for nodes marked with `@ELYBNoObf`.

#### 2. Remove log calls (`removeLogs`)

Removes all bare `log(...)` call statements. Lines marked with `# ELYBsaveLog` are kept.

#### 3. Rename locals (`renameLocals`)

Renames local variables, function parameters, and local function/class names to random identifiers (4–12 alphanumeric characters, e.g. `xKt3p`). The renaming is per-scope and consistent within a scope — the same original name always maps to the same obfuscated name within one function.

Names that are never renamed:

- `self` and `cls`
- dunder names (`__init__`, `__name__`, etc.)
- names imported or exported between modules in the project
- parameter names used as keyword arguments anywhere in the project
- names referenced via `nonlocal` or `global`
- names inside nodes marked with `@ELYBNoObf`

For classes that inherit from an external base (not defined in the project), method names and parameter names are preserved — the Java/external bridge resolves them by their original names.

#### 4. Encode strings (`encodeStrings`)

Replaces string literals with a XOR-decode expression:

```python
# original
x = "hello"

# obfuscated
x = bytes(b ^ 42 for b in b'\x66\x4f\x46\x46\x45').decode()
```

The XOR key is a random byte chosen per build. Import statements are never touched. Lines marked with `# ELYBnoStrobf` are skipped. F-strings are preserved as-is (extracted before the pipeline, restored after).

#### 5. Encode numbers (`encodeNumbers`)

Replaces integer literals with a XOR expression using a random 16-bit mask:

```python
# original
x = 1000

# obfuscated
x = 27736 ^ 26792
```

Trivial values `0`, `1`, and `-1` are not encoded — they are too common and the noise would outweigh the benefit. Booleans are never touched. Lines marked with `# ELYBnoIntObf` are skipped.

#### 6. zlib compression (`zlibCompression`)

The final stage. Compresses the obfuscated source with zlib (level 9), base64-encodes it, reverses the bytes, and wraps the whole file in a two-line exec launcher:

```python
_ = lambda __ : __import__('zlib').decompress(__import__('base64').b64decode(__[::-1]))
exec((_)(b'...'), globals(), locals())
```

The payload is executed with `globals()` and `locals()` passed explicitly so the module's namespace behaves correctly at runtime (Chaquopy 17.0.1 / Python 3.11).

This stage runs after all AST passes and operates on the already-obfuscated source text. It is disabled by default (`zlibCompression: false`) because it produces output that cannot be compiled to `.pyc` — do not combine with `--compile`.

### Source markers

Markers are inline comments that control obfuscation behavior per line or per node.

| Marker | Scope | Effect |
|---|---|---|
| `# ELYBsaveLog` | line | Keeps the `log(...)` call on this line |
| `# ELYBnoStrobf` | line | Skips string encoding on this line |
| `# ELYBnoIntObf` | line | Skips number encoding on this line |

### `@ELYBNoObf` decorator

Apply `@ELYBNoObf` to a function or class to exclude it entirely from obfuscation. The decorator itself is stripped from the output — it does not appear in the compiled archive.

```python
@ELYBNoObf
def myHandler(event, data):
    # this function is not obfuscated: no renaming, no string/number encoding
    log("event received")  # ELYBsaveLog
```

Applying `@ELYBNoObf` to a class skips the entire class body. Applying it to a method skips that method only.

### Obfuscation config

Obfuscation behavior can be tuned in `.elyxbuilder/config.yml` under the `obfuscation` key:

```yaml
obfuscation:
  stripDocstrings: true
  removeLogs: true
  renameLocals: true
  encodeStrings: true
  encodeNumbers: true
  zlibCompression: false
```

All keys are optional. The default for each is `true`, except `zlibCompression` which defaults to `false`. Set a key to `false` to disable the corresponding pipeline stage.

The `removeLogs` setting also applies to plain (non-obfuscated) builds — log calls are stripped from `.py` files that are included in the archive as source.

> **Note:** `zlibCompression` is incompatible with `--compile`. When enabled, the output is a plain `.py` launcher; it cannot be compiled to `.pyc`.
