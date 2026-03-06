import sys, time, threading, os
project_root = r"E:\Developpement\AutoScroller"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import types
import tkinter as tk
from typing import cast

# Dummy pyautogui module (ModuleType) to simulate mouse movement
dummy = types.ModuleType('pyautogui')
_calls = {'n': 0}

def _position():
    _calls['n'] += 1
    if _calls['n'] == 1:
        return (0, 0)
    else:
        return (100, 100)

def _noop(*a, **k):
    return None

setattr(dummy, 'position', _position)
setattr(dummy, 'click', _noop)
setattr(dummy, 'moveTo', _noop)
setattr(dummy, 'mouseDown', _noop)
setattr(dummy, 'mouseUp', _noop)

sys.modules['pyautogui'] = dummy

import Autoscroller
AutoScroller = Autoscroller.AutoScroller
# Prevent GUI creation
AutoScroller.create_widgets = lambda self: None
AutoScroller.create_menu = lambda self: None
AutoScroller.load_ui_state = lambda self: None

# Simple Var
class SimpleVar:
    def __init__(self, value):
        self._v = value
        self._c = []
    def get(self):
        return self._v
    def set(self, val):
        self._v = val
        for cb in list(self._c):
            try:
                cb()
            except Exception:
                pass
    def trace_add(self, mode, cb):
        self._c.append(cb)
    def trace(self, mode, cb):
        self._c.append(cb)

class IntVar(SimpleVar):
    def get(self):
        return int(self._v)

# Fake root with after using threading.Timer
class FakeRoot:
    def __init__(self):
        self.timers = set()
    def after(self, ms, cb):
        t = threading.Timer(ms / 1000.0, cb)
        t.daemon = True
        t.start()
        self.timers.add(t)
        return t
    def after_cancel(self, handle):
        try:
            handle.cancel()
        except Exception:
            pass
    def title(self, *a, **k):
        pass

root = FakeRoot()
app = AutoScroller(root)
# Attach simple vars and minimal UI label
# Use typing.cast to satisfy static type checkers expecting tkinter types
app.smart_pause_var = cast(tk.BooleanVar, SimpleVar(True))
app.smart_pause_seconds_var = cast(tk.IntVar, IntVar(1))
app.smart_pause_status_label = cast(tk.Label, type('L', (), {'config': lambda self, **k: None})())

# Activity state
app.clicking = True
app.scrolling = False
app.h_scrolling = False

# Bind trace
try:
    app.smart_pause_var.trace_add('write', lambda *a: app._on_smart_pause_toggled())
except Exception:
    app.smart_pause_var.trace('w', lambda *a: app._on_smart_pause_toggled())

# Ensure last mouse pos is None so monitoring picks up initial positions
app._last_mouse_pos = None

# Start monitoring
app._start_smart_pause_monitoring()

# Wait enough time for activation and deactivation
time.sleep(3)
print('smart_active:', app._smart_pause_active)
print('paused_clicking stored:', getattr(app, '_paused_clicking', None))
print('clicking flag:', app.clicking)
