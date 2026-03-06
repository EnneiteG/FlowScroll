# Feature Implementation Plan

## 1. Stop Conditions (Timer/Counter)
**Goal:** Stop the clicker or scroller after a specific number of actions or duration.

**Implementation:**
-   **Engine (`src/engine/clicker.py` & `scroller.py`):**
    -   Add `limit_mode` ('none', 'count', 'time') and `limit_value` to `__init__` and `update_settings`.
    -   In `run()` loop:
        -   Start timer at loop start.
        -   Increment internal counter.
        -   Check:
            -   If `limit_mode == 'count'` and `count >= limit_value`: `self.stop()`
            -   If `limit_mode == 'time'` and `elapsed >= limit_value`: `self.stop()`
-   **GUI (`src/gui/main_window.py`):**
    -   Add "Stop Condition" GroupBox to "Advanced Settings" (or a new tab).
    -   Combo: "Infinite", "Count", "Time (s/m)".
    -   SpinBox for value.
    -   Pass these to `update_clicker_settings` / `update_scroller_settings`.

## 2. Click Location (Fixed vs Current)
**Goal:** Allow clicking at a specific screen coordinate instead of current mouse position.

**Implementation:**
-   **Engine (`src/engine/clicker.py`):**
    -   Add `target_pos` (tuple `(x, y)` or `None`).
    -   In `run()` loop:
        -   If `target_pos`: `self.mouse.position = target_pos` (Wait, this moves the mouse. Might be annoying if user is doing other things. Usually autoclickers steal mouse only at the instant of click).
        -   Better: Store `target_pos`. Before `mouse.click`, move to `target_pos`.
-   **GUI:**
    -   "Click Location" GroupBox.
    -   Radio: "Current Location" (default), "Pick Location".
    -   "Pick" Button: runs a simple overlay or listens for next click to record coordinates.
    -   SpinBoxes X and Y for manual edit.

## 3. Editable Hotkeys
**Goal:** Allow user to change hotkeys in the UI.

**Implementation:**
-   **GUI (`src/gui/main_window.py`):**
    -   Enable `QKeySequenceEdit` simple editing.
    -   On `editingFinished`, validate and save new hotkey to settings.
    -   Restart `GlobalHotKeys` listener with new mapping.
    -   Handle conflicts (if same key used).

## 4. Always on Top & System Tray
**Goal:** Window management improvements.

**Implementation:**
-   **Always on Top:**
    -   Checkbox in "General/Settings".
    -   `self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, state)`.
    -   `self.show()` to apply.
-   **System Tray:**
    -   `QSystemTrayIcon`.
    -   Menu: "Show", "Exit".
    -   Override `closeEvent` to `hide()` instead of exit if "Minimize to Tray" is checked.
    -   Or just standard Tray icon for access.

## 5. Sound Feedback
**Goal:** Beep when starting/stopping.

**Implementation:**
-   Add "Sound Feedback" checkbox in Settings.
-   In `toggle_clicker_state`/`toggle_scroller_state`:
    -   If enabled, call `winsound.Beep(frequency, duration)`.
    -   Distinct sounds for Start vs Stop (e.g., High pitch start, Low pitch stop).

## 6. Sequence Recording (Macro) - *Lower Priority*
-   Complex. Requires a new Engine `SequenceEngine`.
-   List of actions (Move, Click, Wait, Scroll).
-   Recorder class to hook inputs and save to list.
