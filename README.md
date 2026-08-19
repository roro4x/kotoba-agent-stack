# Kotoba Agent Stack

Offline-first набор Agent Skills для персонального изучения японского языка в Codex и Bionic. Прогресс хранится локально в JSON/JSONL; облачный API и база данных не нужны.

## Статус и версии

| Компонент | Версия / статус |
|---|---|
| Проект | MVP, pre-1.0 |
| Формат состояния | schema v1 |
| Python | 3.9+ для рекомендуемого Bionic-режима |
| Codex | Python необязателен |
| Bionic | локальная модель, контекст 32k рекомендуется |

## Возможности

- персональные уроки для целей `jlpt` и `conversation`;
- диагностика, адаптивные тесты и режимы фуриганы;
- локальный прогресс со стабильными curriculum ID;
- компактный snapshot/checkpoint между чатами;
- безопасный Anki preview и синхронизация только после подтверждения;
- опциональная voice-модель Bionic без собственного TTS-сервера.

## Стек

- Agent Skills (`SKILL.md`);
- Codex или Bionic Code Project;
- Python 3.9+, только стандартная библиотека;
- JSON/JSONL для состояния и каталога;
- опционально Anki + AnkiConnect.

Не требуются Node.js, Docker, LM Studio, `pip install`, виртуальное окружение или облачный API.

## Установка

### Codex

1. Открыть репозиторий как проект.
2. Использовать `AGENTS.md` и скиллы из `skills/`.
3. Начать сообщением:

```text
Прочитай AGENTS.md и skills/kotoba-settings/SKILL.md. Настрой мне курс японского языка и проведи входную диагностику.
```

Опциональная глобальная установка скиллов:

```bash
python3 tools/install_skills.py --target codex-user
```

### Bionic

1. Открыть репозиторий как Code Project и выбрать локальную instruct-модель.
2. Вставить [prompt установки](bionic/INSTALL_PROMPT.md).
3. Выбрать выведенный каталог `bionic/kotoba` в настройке установки скилла.
4. При необходимости включить **Auto load voice model**.
5. В новом чате запустить `kotoba`.

Проверка окружения:

```bash
python3 tools/kotoba_bionic.py setup --run-tests
python3 tools/kotoba_bionic.py doctor
```

LM Studio для Bionic не нужен: модели скачиваются и запускаются самим приложением.

## Основные команды

```bash
# Компактный контекст нового Bionic-чата
python3 tools/kotoba_bionic.py begin

# Выбранные элементы без загрузки всего каталога
python3 tools/kotoba_bionic.py items grammar.topic-wa vocab.gakusei

# Пакетная запись результатов и checkpoint
python3 tools/kotoba_bionic.py finish \
  --result vocab.gakusei:0.75:meaning

# Сводка состояния
python3 tools/kotoba_state.py summary
```

## Anki

Preview является режимом по умолчанию:

```bash
python3 tools/kotoba_anki.py examples/lesson-001.json
```

Применение разрешено только после проверки и явного согласия пользователя:

```bash
python3 tools/kotoba_anki.py examples/lesson-001.json --apply
```

## Структура

```text
bionic/kotoba/   единый Bionic-скилл
skills/          скиллы Codex
curriculum/      учебный каталог
learner/         профиль и прогресс
lessons/         завершённые уроки
tools/           state, session, Bionic и Anki CLI
tests/           unit-тесты
```

## Документация

- [Bionic: окружение и установка](docs/bionic.md)
- [Варианты развёртывания](docs/deployment.md)
- [Компактные чаты и checkpoint](docs/session-workflow.md)
- [Формат состояния](docs/state-format.md)
- [Архитектура](docs/architecture.md)
- [Источники контента](docs/content-sources.md)

## Тесты

```bash
python3 -m unittest discover -s tests -v
```

Файлы `learner/` принадлежат ученику. Anki не включается и не изменяется автоматически.
