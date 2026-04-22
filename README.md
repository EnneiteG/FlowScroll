# FlowScroll - Auto-Clicker & Auto-Scroller

FlowScroll is a Windows desktop utility for automating mouse clicks and scrolling with a PyQt6 interface, local profiles, and quick local test builds.

## Features

- Auto-clicker with fixed-rate or random-interval modes.
- Auto-scroller with vertical, horizontal, and diagonal directions.
- Smart pause that pauses on manual mouse movement and resumes after a configurable delay.
- Stop conditions based on time or count.
- Per-user settings and profiles stored in LocalAppData.
- Optional overlay, global hotkeys, tray icon, and update checker.

## Local Development

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run from source:

```powershell
python run_app.py
```

## Local Build Workflow

Create a local Windows build:

```powershell
.\build_release.ps1
```

- The local test executable is written to `release/FlowScroll.exe`.
- Use `release/FlowScroll.exe` to test new builds quickly without reinstalling the app.
- The installer output in `release/` is for packaging and distribution, not for every test cycle.

## Runtime Data

FlowScroll stores writable runtime data in `%LocalAppData%\FlowScroll`:

- `flowscroll_settings.json`
- `profiles.json`
- `logs\flowscroll.log`

On first launch, existing legacy files found next to the source tree or executable are copied into the per-user data directory automatically.

## Release Artifacts

- `FlowScroll.spec` is versioned and used by `build_release.ps1`.
- `flowscroll_installer.iss` and `FlowScroll.wxs` package the executable from `release/FlowScroll.exe`.

## License

This project is licensed under the GNU General Public License v3.0. See `LICENSE`.
