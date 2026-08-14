# elyb new

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

The `-zf` flag correctly writes the format to `config.yml` (default: `eaf`).

Plugin ID is built as `author_PluginName`, truncated to 32 characters.

`description` is always auto-generated as a `{description}` placeholder and is not prompted.
