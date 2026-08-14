# elyb cached

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
