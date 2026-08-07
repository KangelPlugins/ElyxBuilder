# ElyxBuilder

Fork of [shareui/ElyxBuilder](https://github.com/sahreui/ElyxBuilder) — a CLI tool for building **ElyxCore** plugins.

## Changes from upstream

- **Decoupled `obfuscationIgnore` from `compilationIgnore`** — new config key allows independent control over which files get obfuscated vs compiled. Files in `compilationIgnore` are now obfuscated as source (not compiled to `.pyc`).
- Saves obfuscation mapping after compilation.
- **`elyb watch`** — watch mode for automatic rebuilds on file changes.
- **Building progress** — visual progress indicator during build.
- **Fix: `runNew()` zipformat argument** — `elyb new -zf` now correctly writes the format to config instead of crashing.
- **Fix: typo `"Built failed"` → `"Build failed"`** in watch output.
- **Fix: `shlex.split()` crash** on unbalanced quotes in watch args — now shows a clean error instead of a traceback.

## Features

- **Scaffolding** — generate a ready-to-go plugin structure with a single command
- **AST validation** — catch syntax errors before packaging
- **Python 3.11 compilation** — ship `.pyc` instead of source, with incremental cache
- **Flexible ignore lists** — fine-grained control over what goes into the archive
- **Encryption** — protect your archive with AES-128/192/256 or ZipCrypto (Elyx Supports)

## Installation

pip install elyxbuilder-cli -U (--break-system-packages if you on Linux and install global)

## Quick start

```bash
elyb new "My Plugin" myname
elyb build -c -v
```

## Documentation

- [English](https://github.com/KangelPlugins/ElyxBuilder/blob/main/docs)
- [Русский](https://github.com/KangelPlugins/ElyxBuilder/blob/main/docs)

## Requirements

- Python >= 3.10
- Python 3.11 — compilation only
- pyzipper — encryption only (`pip install pyzipper`)

## License

MIT
