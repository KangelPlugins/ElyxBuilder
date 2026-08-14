# elyb build

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

## Build info

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

## Compilation (`--compile`)

Files in `compilationIgnore` are not compiled and are included in the archive as `.py`. All other `.py` files are replaced with compiled `.pyc`. An incremental cache is used — subsequent builds only recompile changed files.

The optional level argument (0–2) maps to `py_compile` optimization levels:

| Level | Effect |
|---|---|
| `0` | No optimization (keeps asserts and docstrings) |
| `1` (default) | Strips assert statements |
| `2` | Strips assert statements and docstrings |

Changing the level invalidates the cache, so all files are recompiled.

## Encryption (`-p`)

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
