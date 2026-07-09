# ElyxBuilder

A CLI tool for building **ElyxCore** plugins — scaffold, compile, and package your plugin in one package.

## Features

- **Scaffolding** — generate a ready-to-go plugin structure with a single command
- **AST validation** — catch syntax errors before packaging
- **Python 3.11 compilation** — ship `.pyc` instead of source, with incremental cache
- **Flexible ignore lists** — fine-grained control over what goes into the archive
- **Encryption** — protect your archive with AES-128/192/256 or ZipCrypto (Elyx Supports)

## Installation

Please use the releases page on GitHub: [shareui/ElyxBuilder/releases](https://github.com/shareui/ElyxBuilder/releases)

## Quick start

```bash
elyb new "My Plugin" myname
elyb build -c -v
```

## Documentation

- [English](https://github.com/shareui/ElyxBuilder/blob/main/docs)
- [Русский](https://github.com/shareui/ElyxBuilder/blob/main/docs)

## Requirements

- Python >= 3.10
- Python 3.11 — compilation only
- pyzipper — encryption only (`pip install pyzipper`)

## License

MIT
