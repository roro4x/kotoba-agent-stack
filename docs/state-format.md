# Формат состояния без Python

Этот документ задаёт правила, по которым Codex или Bionic могут вести прогресс обычными файловыми инструментами. Python не является частью формата.

## Файлы

Создать каталог `learner/` при первом запуске.

`profile.json`:

```json
{
  "schema_version": 1,
  "learner_name": "Ученик",
  "assumed_baseline": "kana-known",
  "created_at": "2026-08-19T12:00:00Z",
  "updated_at": "2026-08-19T12:00:00Z"
}
```

`settings.json`:

```json
{
  "schema_version": 1,
  "goal": "conversation",
  "lesson_minutes": 25,
  "furigana": "adaptive",
  "interface_language": "ru",
  "anki": {
    "enabled": false,
    "parent_deck": "Kotoba"
  }
}
```

`mastery.json`:

```json
{
  "schema_version": 1,
  "items": {}
}
```

`events.jsonl` содержит по одному JSON-объекту на строку. Не превращать его в JSON-массив.

Первой строкой записать событие инициализации с тем же объектом настроек, который сохранён в `settings.json`:

```json
{"type":"profile_initialized","at":"2026-08-19T12:00:00Z","settings":{"schema_version":1,"goal":"conversation","lesson_minutes":25,"furigana":"adaptive","interface_language":"ru","anki":{"enabled":false,"parent_deck":"Kotoba"}}}
```

## Допустимые значения

- `goal`: `jlpt` или `conversation`;
- `lesson_minutes`: целое число от 5 до 180;
- `furigana`: `always`, `learning`, `adaptive` или `never`;
- статус: `new`, `reported_known`, `learning` или `mastered`;
- режим результата: `meaning`, `reading-with-furigana`, `reading-no-furigana`, `production`, `grammar` или `anki`;
- оценка: `0`, `0.25`, `0.5`, `0.75` или `1`.

Все временные метки записывать в ISO 8601 UTC. Стабильный ID элемента должен соответствовать форме `group.item-name`, например `vocab.gakusei`.

## Изменение настроек

Изменять только запрошенные поля `settings.json`, обновить `profile.updated_at` и добавить в `events.jsonl`:

```json
{"type":"settings_changed","at":"2026-08-19T12:05:00Z","changes":{"lesson_minutes":40}}
```

Anki включать только по явному выбору ученика.

## Отметка «уже знаю»

Для каждого ID создать или дополнить запись в `mastery.items`:

```json
{
  "status": "reported_known",
  "reported_known_at": "2026-08-19T12:05:00Z",
  "history": [],
  "modes": {}
}
```

Добавить событие `reported_known`. Не заменять `reported_known` на `mastered` без результатов проверки.

## Запись результата

Добавить в `history` объект с `at`, `score`, `mode` и, если есть, `lesson`. В `modes[mode]` хранить:

- `attempts` — общее число попыток;
- `scores` — последние 10 оценок;
- `average` — среднее этих оценок, округлённое до трёх знаков.

В самой записи элемента обновить `last_seen_at` и `recent_average` по последним трём попыткам. Статус вычислять так:

1. последняя оценка ниже `0.5` → `learning`;
2. есть три последние оценки и их среднее не ниже `0.8` → `mastered`;
3. прежний статус `reported_known` и последняя оценка не ниже `0.5` → `reported_known`;
4. иначе → `learning`.

Затем добавить событие `assessment` в `events.jsonl`.

## Безопасная запись

- Сначала прочитать текущий файл и сохранить все неизвестные поля.
- При первом запуске не заменять уже существующий профиль без отдельного подтверждения.
- Не обнулять историю при изменении одной настройки.
- Перед записью проверить синтаксис JSON доступным средством агента.
- При повреждённом или неоднозначном состоянии остановиться и показать проблему вместо перезаписи.
- Не выдумывать события, уроки или оценки задним числом.
