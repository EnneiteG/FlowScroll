import sys, time, types, os
import time as _t
import importlib

# Inject a dummy pyautogui module to simulate blocking OS calls
dummy = types.ModuleType('pyautogui')

def _sleep_short():
    _t.sleep(0.05)

def click(x=None, y=None, clicks=1, button='left'):
    # simulate blocking click
    _sleep_short()

def moveTo(x, y):
    _sleep_short()

def mouseDown(x=None, y=None, button='left'):
    _sleep_short()

def mouseUp(x=None, y=None, button='left'):
    _sleep_short()

def position():
    return (100, 100)

# Attach functions to the dummy module (use setattr to satisfy static type checkers)
setattr(dummy, 'click', click)
setattr(dummy, 'moveTo', moveTo)
setattr(dummy, 'mouseDown', mouseDown)
setattr(dummy, 'mouseUp', mouseUp)
setattr(dummy, 'position', position)

# Ensure our dummy module is used when importing pyautogui
sys.modules['pyautogui'] = dummy

# Import the app by path to ensure we load the local module
import importlib.util
spec = importlib.util.spec_from_file_location('Autoscroller', r'e:\Developpement\AutoScroller\Autoscroller.py')
if spec is None or spec.loader is None:
    raise ImportError('Could not load Autoscroller module spec')
module = importlib.util.module_from_spec(spec)
sys.modules['Autoscroller'] = module
# Ensure project root is on sys.path so local modules (workers) can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
spec.loader.exec_module(module)
AutoScroller = module.AutoScroller
import tkinter as tk

print('Starting automated UI test (3s clicker).')
root = tk.Tk()
root.withdraw()  # hide window to avoid stealing focus during test
app = AutoScroller(root)

# Start the clicker
app.toggle_clicker()

# Schedule stop and shutdown after 3 seconds
root.after(3000, lambda: (app.stop_clicker(), root.quit()))
start = time.time()
try:
    root.mainloop()
except Exception as e:
    print('Mainloop error:', e)
end = time.time()
print('Mainloop finished, duration:', round(end - start, 2), 's')
# Check that executors exist and are not None
thread_exec = getattr(app, '_thread_executor', None)
proc_exec = getattr(app, '_process_executor', None)
print('Thread executor:', 'present' if thread_exec else 'missing')
print('Process executor:', 'present' if proc_exec else 'missing')

# graceful shutdown
try:
    if thread_exec:
        thread_exec.shutdown(wait=False)
except Exception:
    pass
print('Test complete.')
import sys, time, types, os
import time as _t
import importlib

# Inject a dummy pyautogui module to simulate blocking OS calls
dummy = types.ModuleType('pyautogui')

def _sleep_short():
    _t.sleep(0.05)

def click(x=None, y=None, clicks=1, button='left'):
    # simulate blocking click
    _sleep_short()

def moveTo(x, y):
    _sleep_short()

def mouseDown(x=None, y=None, button='left'):
    _sleep_short()

def mouseUp(x=None, y=None, button='left'):
    _sleep_short()

def position():
    return (100, 100)

# Attach functions to the dummy module (use setattr to satisfy static type checkers)
setattr(dummy, 'click', click)
setattr(dummy, 'moveTo', moveTo)
setattr(dummy, 'mouseDown', mouseDown)
setattr(dummy, 'mouseUp', mouseUp)
setattr(dummy, 'position', position)

# Ensure our dummy module is used when importing pyautogui
sys.modules['pyautogui'] = dummy

# Import the app by path to ensure we load the local module
import importlib.util
spec = importlib.util.spec_from_file_location('Autoscroller', r'e:\Developpement\AutoScroller\Autoscroller.py')
if spec is None or spec.loader is None:
    raise ImportError('Could not load Autoscroller module spec')
module = importlib.util.module_from_spec(spec)
sys.modules['Autoscroller'] = module
# Ensure project root is on sys.path so local modules (workers) can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
spec.loader.exec_module(module)
AutoScroller = module.AutoScroller
import tkinter as tk

print('Starting automated UI test (3s clicker).')
root = tk.Tk()
root.withdraw()  # hide window to avoid stealing focus during test
app = AutoScroller(root)

# Start the clicker
app.toggle_clicker()

# Schedule stop and shutdown after 3 seconds
root.after(3000, lambda: (app.stop_clicker(), root.quit()))
start = time.time()
try:
    root.mainloop()
except Exception as e:
    print('Mainloop error:', e)
end = time.time()
print('Mainloop finished, duration:', round(end - start, 2), 's')
# Check that executors exist and are not None
thread_exec = getattr(app, '_thread_executor', None)
proc_exec = getattr(app, '_process_executor', None)
print('Thread executor:', 'present' if thread_exec else 'missing')
print('Process executor:', 'present' if proc_exec else 'missing')

# graceful shutdown
try:
    if thread_exec:
        thread_exec.shutdown(wait=False)
except Exception:
    pass
print('Test complete.')
