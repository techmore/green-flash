#!/usr/bin/env python3
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Import and run the menu bar app
    from menu_bar_app import UGreenMenuBarApp
    UGreenMenuBarApp().run()