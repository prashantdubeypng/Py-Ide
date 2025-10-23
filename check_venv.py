"""
Diagnostic script to check Python environment setup
"""
import sys
import os

print("=" * 70)
print("PYTHON ENVIRONMENT DIAGNOSTIC")
print("=" * 70)

# Check Python executable
print(f"\n1. Python Executable:")
print(f"   {sys.executable}")

# Check if running in venv
in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
print(f"\n2. Running in Virtual Environment: {in_venv}")
if in_venv:
    print(f"   Base: {sys.base_prefix}")
    print(f"   Venv: {sys.prefix}")
else:
    print(f"   Prefix: {sys.prefix}")

# Check Python version
print(f"\n3. Python Version:")
print(f"   {sys.version}")

# Check site-packages
print(f"\n4. Site-packages directories:")
site_packages = [p for p in sys.path if 'site-packages' in p]
for sp in site_packages[:3]:
    print(f"   - {sp}")

# Try to import pywinpty
print(f"\n5. Checking pywinpty:")
try:
    import pywinpty
    print(f"   ✓ Successfully imported!")
    print(f"   Version: {pywinpty.__version__ if hasattr(pywinpty, '__version__') else 'unknown'}")
    print(f"   Location: {pywinpty.__file__}")
except ImportError as e:
    print(f"   ✗ Failed to import")
    print(f"   Error: {e}")

# Try to import ansi2html
print(f"\n6. Checking ansi2html:")
try:
    import ansi2html
    print(f"   ✓ Successfully imported!")
    print(f"   Location: {ansi2html.__file__}")
except ImportError as e:
    print(f"   ✗ Failed to import")
    print(f"   Error: {e}")

# Check if .venv exists
print(f"\n7. Virtual Environment Directory:")
venv_path = os.path.join(os.path.dirname(__file__), '.venv')
if os.path.exists(venv_path):
    print(f"   ✓ Found: {venv_path}")
    scripts_path = os.path.join(venv_path, 'Scripts')
    if os.path.exists(scripts_path):
        python_exe = os.path.join(scripts_path, 'python.exe')
        if os.path.exists(python_exe):
            print(f"   ✓ Python exe: {python_exe}")
            current_exe = sys.executable.lower()
            expected_exe = python_exe.lower()
            if current_exe == expected_exe:
                print(f"   ✓ Using correct Python!")
            else:
                print(f"   ✗ Wrong Python!")
                print(f"     Expected: {expected_exe}")
                print(f"     Current:  {current_exe}")
else:
    print(f"   ✗ Not found: {venv_path}")

print("\n" + "=" * 70)
print("RECOMMENDATIONS:")
print("=" * 70)

if not in_venv:
    print("\n⚠️  You are NOT running in the virtual environment!")
    print("\nTo fix:")
    print("1. Close this program")
    print("2. In PowerShell, run: .venv\\Scripts\\Activate.ps1")
    print("3. Verify prompt shows (.venv)")
    print("4. Run: python check_venv.py")
    print("5. If pywinpty still missing, run: pip install pywinpty ansi2html")
    print("6. Then run: python run_ide.py")
else:
    print("\n✓ Running in virtual environment!")
    try:
        import pywinpty
        print("✓ pywinpty is available!")
        print("\nYou're all set! Run: python run_ide.py")
    except ImportError:
        print("✗ pywinpty not installed in this venv")
        print("\nTo fix:")
        print("1. Run: pip install pywinpty ansi2html")
        print("2. Run: python run_ide.py")

print("\n" + "=" * 70)
