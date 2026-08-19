# Kotoba Agent Stack

Локальный набор Agent Skills для персонального изучения японского языка. Проект работает в Codex или в Bionic Code Project с локальной моделью из LM Studio, например Bonsai.

**Python для основного режима не нужен.** Профиль, настройки и прогресс хранятся в обычных JSON/JSONL-файлах, которые агент читает и обновляет своими файловыми инструментами. Python 3 — только опциональный способ выполнять те же операции детерминированно из терминала и автоматически обращаться к AnkiConnect.

## Стек

- Agent Skills: Markdown-файлы `SKILL.md` с YAML frontmatter;
- агентная оболочка: Codex или Bionic Code Project;
- локальный inference: LM Studio, настроенная через графический интерфейс;
- модель: Bonsai или любая другая локальная instruct/tool-use модель;
- данные: JSON и JSONL в каталоге `learner/`, без базы данных;
- учебный каталог: JSON в `curriculum/`;
- опционально: Python 3, только стандартная библиотека, без `pip install`;
- опционально: Anki + AnkiConnect для автоматической синхронизации;
- TTS: планируемый отдельный адаптер, в MVP не реализован.

Для базового режима не требуются Python, Node.js, Docker, база данных или облачный API.

## Возможности MVP

- старт после изучения хираганы и катаканы;
- короткая входная диагностика слов и грамматики;
- выбор цели `jlpt` или `conversation`;
- изменяемая длительность урока и режим фуриганы;
- отметка уже известного материала без повторного урока;
- тесты значения, активного словаря и чтения с фуриганой или без;
- локальный журнал прогресса;
- безопасный предварительный просмотр и опциональная синхронизация с Anki.

## Быстрый старт без Python

### Codex

1. Открыть этот репозиторий как проект.
2. Попросить Codex прочитать `AGENTS.md` и нужный скилл из `skills/`.
3. Начать сообщением:

```text
Прочитай AGENTS.md и skills/kotoba-settings/SKILL.md. Настрой мне курс японского языка и проведи входную диагностику. Работай в режиме без Python.
```

Можно установить скиллы глобально без терминала: скопировать четыре каталога `skills/kotoba-*` в пользовательский каталог `.agents/skills`, затем перезапустить Codex. После этого доступны `$kotoba-settings`, `$kotoba-lesson`, `$kotoba-test` и `$kotoba-anki`.

### Bionic + LM Studio

1. Настроить и запустить локальный сервер в интерфейсе LM Studio по [инструкции](docs/lmstudio-bionic.md).
2. В Bionic создать Code Project с корнем этого репозитория и выбрать модель LM Studio.
3. Отправить тот же стартовый промпт, указав режим без Python.

В этом режиме агент создаст `learner/profile.json`, `settings.json`, `mastery.json` и `events.jsonl` по правилам из [формата состояния](docs/state-format.md).

## Расширенный режим с Python

Выбирать его необязательно. Он полезен для воспроизводимых команд, проверки формата и автоматической интеграции с Anki. Достаточно Python 3; сторонних пакетов нет.

```bash
python3 tools/kotoba_state.py init --name "Ученик" --goal conversation --minutes 25 --furigana adaptive
python3 tools/kotoba_state.py configure --goal jlpt --minutes 40
python3 tools/kotoba_state.py mark-known grammar.topic-wa vocab.gakusei
python3 tools/kotoba_state.py record vocab.gakusei --score 0.75 --mode reading-no-furigana
python3 tools/kotoba_state.py summary
```

Опциональная установка скиллов из терминала:

```bash
python3 tools/install_skills.py --target codex-user
```

## Anki

Anki выключен по умолчанию. Без Python скилл `$kotoba-anki` может проверить урок и подготовить предварительный просмотр карточек, но не отправляет изменения в Anki. Добавить карточки можно вручную либо через будущий совместимый MCP-адаптер.

Для автоматической синхронизации нужны Python 3, запущенный Anki и дополнение AnkiConnect. Сначала выполнить preview:

```bash
python3 tools/kotoba_state.py configure --anki true
python3 tools/kotoba_anki.py examples/lesson-001.json
```

И только после проверки применить:

```bash
python3 tools/kotoba_anki.py examples/lesson-001.json --apply
```

Инструмент не удаляет карточки и изменяет только заметки с тегом `kotoba-managed`.

## Варианты развертывания

Полная матрица для Codex, Bionic + LM Studio, Python и Anki находится в [инструкции по развертыванию](docs/deployment.md).

## Документация

- [Развертывание](docs/deployment.md)
- [Формат состояния без Python](docs/state-format.md)
- [Архитектура](docs/architecture.md)
- [LM Studio, Bionic и Bonsai](docs/lmstudio-bionic.md)
- [Дополнительные источники](docs/content-sources.md)

Проект находится на стадии MVP: базовый каталог намеренно небольшой и должен расширяться после проверки реальных уроков.
