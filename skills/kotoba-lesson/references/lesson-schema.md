# Формат файла урока

```json
{
  "id": "lesson-001",
  "number": 1,
  "date": "2026-08-19",
  "title": "Знакомство",
  "goal": "conversation",
  "items": [
    {
      "id": "vocab.gakusei",
      "type": "vocabulary",
      "expression": "学生",
      "reading": "がくせい",
      "meaning": "студент",
      "example": "私は学生です。",
      "example_reading": "わたしはがくせいです。",
      "tags": ["people", "lesson-001"]
    }
  ]
}
```

Требования:

- `id` каждого элемента должен быть стабильным и существовать в каталоге либо начинаться с `custom.`.
- Не сохранять ромадзи.
- Для грамматики использовать `expression` как краткий шаблон, а `meaning` как функцию конструкции.
- Для Anki обязательны `expression`, `reading`, `meaning` и `tags`.
