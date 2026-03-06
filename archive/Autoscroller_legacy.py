#!/usr/bin/env python3
"""
DEPRECATED: This file is a legacy entry point.
Please use src/main.py to launch the application.
"""
import sys
import os

def deprecation_warning():
    print("=" * 60, file=sys.stderr)
    print("WARNING: 'Autoscroller.py' is deprecated.", file=sys.stderr)
    print("Please use 'src/main.py' as the entry point.", file=sys.stderr)
    print("Forwarding execution to src/main.py...", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

def main():
    deprecation_warning()
    
    # Setup paths to ensure we can import src.main
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add root directory to sys.path
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        
    try:
        from src.main import main as app_main
        app_main()
    except ImportError as e:
        print(f"CRITICAL ERROR: Failed to import src.main: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"CRITICAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
