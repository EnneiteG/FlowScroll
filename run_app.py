#!/usr/bin/env python3
"""
Entry point wrapper for FlowScroll.
 Redirects to src.main.
"""
import sys
import os

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import multiprocessing

try:
    from src.main import main
    if __name__ == "__main__":
        multiprocessing.freeze_support()
        main()
except ImportError as e:
    print(f"Failed to start application: {e}")
    sys.exit(1)
