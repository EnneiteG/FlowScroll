import time
from pynput.mouse import Controller

def test_float_scroll():
    mouse = Controller()
    
    print("Waiting 3 seconds... Switch to a scrollable window.")
    time.sleep(3)
    
    print("Starting float scroll (-0.2 * 50 times)...")
    try:
        for _ in range(50):
            mouse.scroll(0, -0.2)
            time.sleep(0.02)
        print("Float scroll completed without raising exception.")
    except Exception as e:
        print(f"Float scroll failed: {e}")

    time.sleep(1)
    
    print("Starting integer scroll (-1 * 10 times)...")
    try:
        for _ in range(10):
            mouse.scroll(0, -1)
            time.sleep(0.1)
        print("Integer scroll completed without raising exception.")
    except Exception as e:
        print(f"Integer scroll failed: {e}")

if __name__ == "__main__":
    test_float_scroll()
