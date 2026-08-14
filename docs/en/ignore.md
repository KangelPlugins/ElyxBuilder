# elyb add-ignore <path> <target>

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

# elyb del-ignore <index> <target>

Removes an entry from an ignore list by its zero-based index.

```bash
elyb del-ignore 0 --all
elyb del-ignore 2 --no-assets
elyb del-ignore 1 --compile
```

Flags are the same as `add-ignore`. The index corresponds to the position in the list in `config.yml`.
