# elyb add-ignore / del-ignore

> Все команды запускаются из корня проекта — директории, в которой находится `refmap.yml`.

## elyb add-ignore

Добавляет путь в один из списков игнорирования в `.elyxbuilder/config.yml`.

```bash
elyb add-ignore "MyPlugin/res/heavy.png" --no-assets
elyb add-ignore "MyPlugin/.elyxbuilder/cache/*" --all
elyb add-ignore "MyPlugin/src/helpers.py" --compile
```

| Флаг | Список | Эффект |
|---|---|---|
| `-a`, `--all` | `ignoreAll` | Исключить из любой сборки |
| `-na`, `--no-assets` | `optionalAssets` | Исключить при `--no-assets` |
| `-c`, `--compile` | `compilationIgnore` | Не компилировать |

Обратные слеши нормализуются в прямые. Дубликаты не добавляются.

## elyb del-ignore

Удаляет запись из списка игнорирования по индексу (с нуля).

```bash
elyb del-ignore 0 --all
elyb del-ignore 2 --no-assets
elyb del-ignore 1 --compile
```

Флаги те же, что у `add-ignore`. Индекс соответствует позиции в списке в `config.yml`.
