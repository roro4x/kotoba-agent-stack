# Kotoba Agent Stack

Локальный набор скиллов для персонального изучения японского языка. MVP поддерживает Codex и работу через Bionic Code Project с любой подходящей локальной моделью LM Studio, включая Bonsai.

## Возможности MVP

- старт после изучения хираганы и катаканы;
- короткая входная диагностика слов и грамматики;
- выбор цели `jlpt` или `conversation`;
- изменяемая длительность урока и режим фуриганы;
- отметка уже известного материала без повторного урока;
- тесты значения, активного словаря и чтения с фуриганой или без;
- локальный журнал прогресса;
- безопасный предварительный просмотр и опциональная синхронизация с Anki.

## Быстрый старт в Codex

Установить скиллы в пользовательский каталог Codex:

```bash
python3 tools/install_skills.py --target codex-user
```

Перезапустить Codex, если новые скиллы не появились, затем начать:

```text
$kotoba-settings Настрой мне курс японского языка и проведи входную диагностику.
```

Скиллы также можно вызывать явно: `$kotoba-lesson`, `$kotoba-test`, `$kotoba-anki`.

## Локальные команды

```bash
python3 tools/kotoba_state.py init --name "Ученик" --goal conversation --minutes 25 --furigana adaptive
python3 tools/kotoba_state.py configure --goal jlpt --minutes 40
python3 tools/kotoba_state.py mark-known grammar.topic-wa vocab.gakusei
python3 tools/kotoba_state.py record vocab.gakusei --score 0.75 --mode reading-no-furigana
python3 tools/kotoba_state.py summary
```

## Anki

Anki выключен по умолчанию. После его явного включения сначала создать preview:

```bash
python3 tools/kotoba_state.py configure --anki true
python3 tools/kotoba_anki.py examples/lesson-001.json
```

Для применения нужен открытый Anki с AnkiConnect:

```bash
python3 tools/kotoba_anki.py examples/lesson-001.json --apply
```

Инструмент не удаляет карточки и изменяет только заметки с тегом `kotoba-managed`.

## Документация

- [Архитектура](docs/architecture.md)
- [LM Studio, Bionic и Bonsai](docs/lmstudio-bionic.md)
- [Дополнительные источники](docs/content-sources.md)

Проект находится на стадии MVP: базовый каталог намеренно небольшой и должен расширяться после проверки реальных уроков.
