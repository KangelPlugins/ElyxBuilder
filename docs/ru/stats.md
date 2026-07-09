# elyb stats

> Все команды запускаются из корня проекта — директории, в которой находится `refmap.yml`.

## elyb stats builds

Показывает статистику сборок.

```bash
elyb stats builds
```

Пример вывода:

```
Total builds: 10
Uncompiled: 6 (60%)
Compiled: 3 (30%)
Failed: 1 (10%)
```

## elyb stats lines

Считает строки кода в плагине.

```bash
elyb stats lines
```

Считает только `.py` файлы в директории `source` (из `config.yml`). Пример вывода:

```
Lines count statistics for plugin MyPlugin:
MyPlugin/src: 142 (Python only)
```

С флагом `-a` / `--all` считает все не-бинарные файлы в корне плагина и `refmap.yml`:

```bash
elyb stats lines --all
```

Пример вывода:

```
Total lines count statistics for plugin MyPlugin:
.py: 142
.yml: 30
Total: 172
```

С флагом `-add` / `--additional` добавляет дополнительные директории относительно `cwd` (требует `--all`):

```bash
elyb stats lines --all --additional docs scripts
```

| Флаг | Описание |
|---|---|
| `-a`, `--all` | Считать все не-бинарные файлы в корне плагина |
| `-add DIR...`, `--additional DIR...` | Добавить дополнительные директории (требует `--all`) |

## elyb stats size

Показывает статистику размера файлов.

```bash
elyb stats size
```

Показывает суммарный размер `.py` файлов в директории `source` (из `config.yml`). Пример вывода:

```
The size of the directory MyPlugin/src: 4.21 KB (0.0 MB)
Python only
```

С флагом `-a` / `--all` считает все не-бинарные файлы в корне плагина и `refmap.yml`:

```bash
elyb stats size --all
```

Пример вывода:

```
File size statistics for plugin MyPlugin:
.py: 4.21 KB (0.0 MB)
.yml: 0.83 KB (0.0 MB)
```

С флагом `-add` / `--additional` добавляет дополнительные директории относительно `cwd` (требует `--all`):

```bash
elyb stats size --all --additional docs scripts
```

| Флаг | Описание |
|---|---|
| `-a`, `--all` | Считать все не-бинарные файлы в корне плагина |
| `-add DIR...`, `--additional DIR...` | Добавить дополнительные директории (требует `--all`) |

## elyb stats files

Показывает количество файлов по расширению.

```bash
elyb stats files
```

Считает все файлы в корне плагина по расширению. Пример вывода:

```
File count statistics for plugin MyPlugin:
.py: 5
.yml: 3
Total: 8
```

С флагом `-a` / `--all` также включает `refmap.yml`:

```bash
elyb stats files --all
```

С флагом `-add` / `--additional` добавляет дополнительные директории относительно `cwd`:

```bash
elyb stats files --all --additional docs scripts
```

| Флаг | Описание |
|---|---|
| `-a`, `--all` | Включить `refmap.yml` и дополнительные директории |
| `-add DIR...`, `--additional DIR...` | Добавить дополнительные директории (требует `--all`) |
