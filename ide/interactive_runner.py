"""
Interactive Runner - Wrapper for running Python scripts in interactive terminal
Ensures proper UTF-8 encoding on Windows
"""
import sys
import io
import os

# Force UTF-8 encoding on Windows to handle emojis and special characters
if sys.platform == 'win32':
    # Wrap stdout and stderr with UTF-8 encoding
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding='utf-8',
        errors='replace',
        line_buffering=False,
        write_through=True
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer,
        encoding='utf-8',
        errors='replace',
        line_buffering=False,
        write_through=True
    )
    sys.stdin = io.TextIOWrapper(
        sys.stdin.buffer,
        encoding='utf-8',
        errors='replace'
    )

# Get the script to run from command line arguments
if len(sys.argv) < 2:
    print("Error: No script specified")
    sys.exit(1)

script_path = sys.argv[1]
script_args = sys.argv[2:]  # Additional arguments to pass to the script

# Verify script exists
if not os.path.exists(script_path):
    print(f"Error: Script not found: {script_path}")
    sys.exit(1)

# Set up sys.argv for the target script
sys.argv = [script_path] + script_args

# Change to script directory
script_dir = os.path.dirname(os.path.abspath(script_path))
os.chdir(script_dir)

# Execute the script
try:
    with open(script_path, 'r', encoding='utf-8') as f:
        code = compile(f.read(), script_path, 'exec')
        exec(code, {'__name__': '__main__', '__file__': script_path})
except Exception as e:
    import traceback
    print(f"\nError executing script:", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
