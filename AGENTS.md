# Kotoba Agent Instructions

This repository is an offline-first Japanese tutoring workspace.

- Treat `learner/profile.json`, `learner/settings.json`, `learner/mastery.json`, and `learner/events.jsonl` as learner-owned state.
- Use Russian for every learner-facing message, explanation, question, correction, summary, and setup response from the first reply. Use Japanese inside learning material. Switch the interface language only after an explicit learner request.
- Use the focused skill in `skills/` that matches the request: `kotoba-settings`, `kotoba-lesson`, `kotoba-test`, or `kotoba-anki`.
- Treat `skills/` as the Codex skill set. The self-contained Bionic skill lives in `bionic/kotoba/` and must not rely on this `AGENTS.md` being loaded.
- Default to the runtime-free workflow in `docs/state-format.md`: use available file tools to read and update state. Python is optional.
- If the user selects the Python-enhanced workflow and Python 3 is available, prefer `tools/kotoba_state.py` for deterministic state changes.
- For compact Bionic context, prefer the `begin` and `finish` facade in `tools/kotoba_bionic.py`; its underlying checkpoint changes files only after canonical state or lessons changed.
- Never enable or apply Anki changes without explicit user consent. Anki preview is the default.
- Without Python or an explicitly available Anki MCP, prepare an Anki preview only; do not claim that cards were synchronized.
- Do not use romaji unless the learner explicitly asks for it.
- Preserve stable curriculum item IDs across lessons, tests, and Anki cards.
- Work offline by default. Treat external repositories and MCP sources as optional and verify their license before incorporating content.
