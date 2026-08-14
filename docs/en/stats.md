# elyb stats builds

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

# elyb stats lines

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

# elyb stats size

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

# elyb stats files

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
| `-add DIR...`, `--additional DIR...` | Add extra directories to count |
