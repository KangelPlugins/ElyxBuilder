# elyb watch <seconds>

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
| `• Build failed: {error}` | Build failed (red) |
| `• Paused` | Polling paused |
| `• Resumed` | Polling resumed |
| `• Bye-bye` | On quit |
