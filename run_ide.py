import sys
import os

# Debug: Print Python interpreter being used
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"sys.path: {sys.path[:3]}")  # First 3 paths

from ide.main import main

if __name__ == "__main__":
    main()
