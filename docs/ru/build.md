# elyb build

Собирает плагин в архив. Запускается из директории с `refmap.yml`.

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

| Флаг | Описание |
|---|---|
| `--no-assets` | Исключить файлы из `optionalAssets` |
| `-nf`, `--no-folder` | Исключить директорию `elyxbuilder` из архива |
| `-v`, `--verbose` | Подробный лог сборки |
| `-a`, `--ast` | Проверить синтаксис `.py` через AST перед сборкой |
| `-c [LEVEL]`, `--compile [LEVEL]` | Скомпилировать `.py` → `.pyc` (Python 3.11); LEVEL — уровень 0–2 (по умолчанию: 1) |
| `-r`, `--reset` | Очистить кэш компиляции перед сборкой (только с `--compile`) |
| `-o [FILE...]`, `--obfuscation [FILE...]` | Обфусцировать исходники перед упаковкой; без файлов — весь source |
| `-p METHOD PASS` | Зашифровать архив |
| `-ni`, `--no-info` | Не добавлять блок с информацией elyxbuilder в `meta.yml` |
| `-sv VERSION [APPEND]` | Добавить `staticVer` в блок информации о сборке; необязательный `APPEND=true` добавляет `-{version}` к имени архива (по умолчанию: `false`) |
| `-sc PACKAGE [NAME]` | Добавить `client` в блок информации о сборке; необязательный `NAME` добавляет `-{name}` к имени архива |

`--ast` и `--compile` взаимоисключающие.

Результат кладётся в `builds/`.

## Информация о сборке

Перед упаковкой elyxbuilder дописывает блок с комментарием в `meta.yml` внутри архива. Файл на диске не изменяется.

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

`staticVer` присутствует только при передаче `-sv` / `--static-version`. Если необязательный второй аргумент равен `true`, к имени архива добавляется `-{version}` (например, `MyPlugin-1.0.0.eaf`).

`client` присутствует только при передаче `-sc` / `--static-client`. Если указан необязательный второй аргумент, к имени архива добавляется `-{name}` (например, `MyPlugin-myclient.eaf`).

Используйте `-ni` / `--no-info`, чтобы пропустить этот блок.

## Компиляция (`--compile`)

Файлы из `compilationIgnore` не компилируются и попадают в архив как `.py`. Остальные `.py` заменяются скомпилированными `.pyc`. Используется инкрементальный кэш — повторная сборка перекомпилирует только изменённые файлы.

Необязательный аргумент уровня (0–2) соответствует уровням оптимизации `py_compile`:

| Уровень | Эффект |
|---|---|
| `0` | Без оптимизации (assert'ы и docstring'и сохраняются) |
| `1` (по умолчанию) | Удаляет assert-выражения |
| `2` | Удаляет assert-выражения и docstring'и |

Изменение уровня инвалидирует кэш — все файлы будут перекомпилированы.

## Шифрование (`-p`)

Требует: `pip install pyzipper`

| Метод | Описание |
|---|---|
| `zipcrypto` | Стандартное ZIP-шифрование |
| `aes-128` | AES 128-bit |
| `aes-192` | AES 192-bit |
| `aes-256` | AES 256-bit (рекомендуется) |

```bash
elyb build -p aes-256 mypassword
```
