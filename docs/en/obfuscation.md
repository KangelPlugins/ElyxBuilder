# Obfuscation

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

## Pipeline stages

The pipeline runs in the following order. Each stage can be disabled independently via `config.yml` (see [Config](#obfuscation-config) below).

### 1. Strip docstrings (`stripDocstrings`)

Removes all docstrings from modules, classes, and functions. The first string literal in each body is dropped; if the body becomes empty, a `pass` statement is inserted.

Skipped for nodes marked with `@ELYBNoObf`.

### 2. Remove log calls (`removeLogs`)

Removes all bare `log(...)` call statements. Lines marked with `# ELYBsaveLog` are kept.

### 3. Rename locals (`renameLocals`)

Renames local variables, function parameters, and local function/class names to random identifiers (4–12 alphanumeric characters, e.g. `xKt3p`). The renaming is per-scope and consistent within a scope — the same original name always maps to the same obfuscated name within one function.

Names that are never renamed:

- `self` and `cls`
- dunder names (`__init__`, `__name__`, etc.)
- names imported or exported between modules in the project
- parameter names used as keyword arguments anywhere in the project
- names referenced via `nonlocal` or `global`
- names inside nodes marked with `@ELYBNoObf`

For classes that inherit from an external base (not defined in the project), method names and parameter names are preserved — the Java/external bridge resolves them by their original names.

### 4. Encode strings (`encodeStrings`)

Replaces string literals with a XOR-decode expression using a dynamic multi-byte key:

```python
# original
x = "hello"

# obfuscated
x = (lambda d, k: bytes((b ^ k[i % len(k)] for i, b in enumerate(b'\xa5\x9c$\xc6\x7f'))).decode())(b'\xa5\x9c$\xc6\x7f', (205, 249, 72, 170, 16, 171, 20, 51, 221))
```

The key is multi-byte (8–16 bytes), deterministically derived from the string content and the build key. Decoding is wrapped in a lambda, hiding the decode logic from static analysis. Import statements are never touched. Lines marked with `# ELYBnoStrobf` are skipped. F-strings are preserved as-is (extracted before the pipeline, restored after).

### 5. Encode numbers (`encodeNumbers`)

Replaces integer literals with a XOR expression using a random 16-bit mask:

```python
# original
x = 1000

# obfuscated
x = 27736 ^ 26792
```

Trivial values `0`, `1`, and `-1` are not encoded — they are too common and the noise would outweigh the benefit. Booleans are never touched. Lines marked with `# ELYBnoIntObf` are skipped.

### 6. Junk code injection (`junkCode`)

Inserts 2–5 decoy functions with useless code (random assignments, `len(...)` calls, `pass`) at the top of every module — noise that slows manual analysis:

```python
def _x93566():
    len([43, 66])
    YwVE = 993
    nZvavo4Pg4 = 384

def _x98820():
    len([90, 11, 79])
    nJdEA = 873
```

The functions are deterministic per build (seed derived from source and key) and get random names. Enabled by default.

### 7. zlib compression (`zlibCompression`)

The final stage. Compresses the obfuscated source with zlib (level 9), base64-encodes it, reverses the bytes, and wraps the whole file in a two-line exec launcher:

```python
_ = lambda __ : __import__('zlib').decompress(__import__('base64').b64decode(__[::-1]))
exec((_)(b'...'), globals(), locals())
```

The payload is executed with `globals()` and `locals()` passed explicitly so the module's namespace behaves correctly at runtime (Chaquopy 17.0.1 / Python 3.11).

This stage runs after all AST passes and operates on the already-obfuscated source text. It is disabled by default (`zlibCompression: false`) because it produces output that cannot be compiled to `.pyc` — do not combine with `--compile`.

### 8. Loader stub (`loaderStub`)

The final stage, ported from the obfuscation technique observed in the reversed Elyx plugin `text_animation (3).plugin`:

- Metadata (`__id__`, `__name__`, `__author__`, `__version__`, `__description__`, `__icon__`), if present at the top of the module, is kept in plain text — the plugin must be able to read it on startup.
- The rest of the module is compressed (`zlib`, level 9), base64-encoded, XOR-encrypted with a random multi-byte key, then split into chunks.
- Imports are aliased to long mangled names (`import base64 as _audq6m0uixf6rnbvzf6vtls`).
- The standard base64 alphabet is disguised — split into random fragments and reassembled at runtime.
- Helper strings (`decompress`, `b64decode`) are hidden in a table: `b64(string) XOR key`; access via the `dec(i)` helper.
- Attribute access goes through `getattr(mod, dec(i))`, hiding names from static analysis.
- Junk code with self-canceling XOR pairs (`c ^ 0x55 ^ 0x55`) is injected — the same trick as the dead opcodes in the original plugin's VM.
- The payload is executed via `exec(decrypt(...), globals(), globals())` — restored and executed at runtime.

Disabled by default (`loaderStub: false`). Unlike `zlibCompression`, the output **can** be compiled to `.pyc` (it is a plain `.py` launcher), but no function mapping is generated — the payload is hidden inside the encrypted blob, so `builds/latest_mapping.json` for such files contains empty `functions`/`classes`.

> **Note:** `zlibCompression`, `loaderStub`, and `loaderStubDynamic` are mutually exclusive terminal stages. If multiple are enabled, `loaderStubDynamic` takes precedence over `loaderStub`, which takes precedence over `zlibCompression`.

### 9. Dynamic loader stub (`loaderStubDynamic`)

Extended variant of `loaderStub`, ported from the technique used in the real obfuscated plugin `eblan_update.plugin`. Instead of a static XOR key, it generates a runtime key that the stub recomputes at execution time — making static extraction of the payload impossible.

#### How it works

**Build-time:**
1. Metadata (`__id__`, `__name__`, etc.) is extracted from the source module and kept in plain text.
2. After metadata, a plaintext stub class is inserted:
   ```python
   from base_plugin import BasePlugin
   class Plugin(BasePlugin): pass
   ```
   The ElyxCore host scans the AST for a `BasePlugin` subclass **before** exec — the stub is required, otherwise the plugin won't load.
3. The rest of the code is compressed (zlib, level 9), encrypted with RC4, and base85-encoded.
4. A dynamic stub is appended to the source file: derives the key from `dir(LayoutHelper)`, decrypts the payload, and executes it.

**Runtime (on device):**
1. ElyxCore imports the module, sees the plaintext stub — passes the AST check.
2. On exec, the stub runs:
   - `hook_utils.find_class("org.telegram.ui.Components.LayoutHelper")` — finds the Java LayoutHelper class.
   - `sha256(sorted(dir(cl))).digest()` — computes SHA256 of the sorted attribute list.
   - The resulting 32-byte key is used for RC4 decryption.
3. The decrypted code replaces the stub — `Plugin` inherits all methods and attributes from the original source.

#### Why this is more secure

| | `loaderStub` (static) | `loaderStubDynamic` |
|---|---|---|
| Key | Random, baked into archive | Computed from `dir(LayoutHelper)` on device |
| Extraction | XOR/brute-force on PC | Impossible without running inside Telegram context |
| Key changes? | No | Yes, on Telegram updates (new methods in LayoutHelper) |
| Static analysis | Payload can be decrypted | Impossible — key is not in the file |

#### Key capture plugin

Before building, you must obtain the `dir(LayoutHelper)` hash from the target device. Example helper plugin:

```python
__id__ = "layouthelper_key"
__name__ = "LayoutHelper Key Dumper"
__author__ = "helper"
__version__ = "1.0"

from base_plugin import BasePlugin
from hook_utils import find_class
from hashlib import sha256
from android_utils import log

class LayoutHelperKeyPlugin(BasePlugin):
    def on_plugin_load(self):
        try:
            cl = find_class("org.telegram.ui.Components.LayoutHelper")
            if cl is None:
                log("LayoutHelper class not found!")
                return

            attrs = sorted(str(x) for x in dir(cl) if not str(x).startswith("__"))
            joined = "".join(attrs)
            key = sha256(joined.encode("utf-8")).digest()

            log("SHA256 (hex): " + key.hex())
        except Exception as e:
            log(f"Error: {e}")
```

Install this plugin, open Logcat — the SHA256 hex string will appear in the logs. Paste it into `loaderStubDynamicKey`.

#### Config

```yaml
obfuscation:
  loaderStub: false          # disable static loaderStub
  loaderStubDynamic: true    # enable dynamic
  loaderStubDynamicKey: "70d3305abb8644c27683463b52d6338168728bc90ac0ebd9313be6754bc9cc84"
```

`loaderStubDynamicKey` — 64-character hex string (SHA256). If not set, falls back to the `xorKey`-derived key.

> **Note:** `loaderStub` and `loaderStubDynamic` are mutually exclusive. If both are enabled, `loaderStubDynamic` takes precedence.

## Source markers

Markers are inline comments that control obfuscation behavior per line or per node.

| Marker | Scope | Effect |
|---|---|---|
| `# ELYBsaveLog` | line | Keeps the `log(...)` call on this line |
| `# ELYBnoStrobf` | line | Skips string encoding on this line |
| `# ELYBnoIntObf` | line | Skips number encoding on this line |

## `@ELYBNoObf` decorator

Apply `@ELYBNoObf` to a function or class to exclude it entirely from obfuscation. The decorator itself is stripped from the output — it does not appear in the compiled archive.

```python
@ELYBNoObf
def myHandler(event, data):
    # this function is not obfuscated: no renaming, no string/number encoding
    log("event received")  # ELYBsaveLog
```

Applying `@ELYBNoObf` to a class skips the entire class body. Applying it to a method skips that method only.

## Obfuscation config

Obfuscation behavior can be tuned in `.elyxbuilder/config.yml` under the `obfuscation` key:

```yaml
obfuscation:
  stripDocstrings: true
  removeLogs: true
  renameLocals: true
  encodeStrings: true
  encodeNumbers: true
  junkCode: true
  stringSplitting: true
  zlibCompression: false
  loaderStub: false
  loaderStubDynamic: false
  loaderStubDynamicKey: ""
```

All keys are optional. The default for each is `true`, except `zlibCompression`, `loaderStub`, and `loaderStubDynamic` which default to `false`. Set a key to `false` to disable the corresponding pipeline stage.

`junkCode` injects decoy functions at the top of the module. `stringSplitting` prepares long strings to be split into fragments before encoding.

`loaderStubDynamic` is an extended variant of `loaderStub` that uses a runtime-derived key. Requires `loaderStubDynamicKey` (hex SHA256). See [Dynamic loader stub](#9-dynamic-loader-stub-loaderstubdynamic) for details.

The `removeLogs` setting also applies to plain (non-obfuscated) builds — log calls are stripped from `.py` files that are included in the archive as source.

### `obfuscationIgnore`

New config key that allows independent control over which files are obfuscated vs compiled. Previously `compilationIgnore` was used for both.

```yaml
compilationIgnore:
  - MyPlugin/src/helpers.py
obfuscationIgnore:
  - MyPlugin/src/helpers.py
```

- Files in `compilationIgnore` are **not compiled** to `.pyc` but **are obfuscated as source** (remain `.py`).
- Files in `obfuscationIgnore` are **not obfuscated** — included in the archive as-is.
- If a file is in both lists, it is neither compiled nor obfuscated.

> **Note:** `zlibCompression` is incompatible with `--compile`. When enabled, the output is a plain `.py` launcher; it cannot be compiled to `.pyc`.
