# FlowScroll Changelog

## 0.1.1

- Fixed clicker and scroller runtime states so the UI now reports `Idle`, `Running`, `Paused`, and `Finished` correctly.
- Raised the practical limits for start delay and smart-pause resume delay.
- Moved settings, profiles, and logs to `%LocalAppData%\\FlowScroll` with legacy file migration.
- Restored strict single-instance startup handling.
- Versioned `FlowScroll.spec`, cleaned tracked runtime data from git, and documented the `release/FlowScroll.exe` local test workflow.

## 0.1.0

- Added local test builds in `release/FlowScroll.exe` while keeping installer packaging separate.
- Added auto-clicker and multi-directional auto-scroller tabs with stop conditions, smart pause, overlay, hotkeys, and profiles.
- Fixed settings persistence to use a writable per-user application data directory with legacy migration support.
- Fixed runtime status reporting so clicker and scroller now switch cleanly between `Idle`, `Running`, `Paused`, and `Finished`.
- Fixed delay controls so start delay and smart-pause resume delay support much larger values.
- Restored strict single-instance startup protection.
- Updated packaging metadata and repository docs to match the current FlowScroll app structure.
