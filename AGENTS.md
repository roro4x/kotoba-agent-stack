# Kotoba Agent Instructions

This repository is an offline-first Japanese tutoring workspace.

- Treat `learner/profile.json`, `learner/settings.json`, `learner/mastery.json`, and `learner/events.jsonl` as learner-owned state.
- Use the focused skill in `skills/` that matches the request: `kotoba-settings`, `kotoba-lesson`, `kotoba-test`, or `kotoba-anki`.
- Prefer `tools/kotoba_state.py` over editing learner state manually.
- Never enable or apply Anki changes without explicit user consent. Anki dry-run is the default.
- Do not use romaji unless the learner explicitly asks for it.
- Preserve stable curriculum item IDs across lessons, tests, and Anki cards.
- Work offline by default. Treat external repositories and MCP sources as optional and verify their license before incorporating content.
