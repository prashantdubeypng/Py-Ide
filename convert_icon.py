"""
Convert PNG icon to ICO format for Windows executable
Run this before building if you have a PNG icon
"""

import os
from PIL import Image

def png_to_ico(png_path, ico_path=None, sizes=None):
    """
    Convert PNG to ICO format
    
    Args:
        png_path: Path to input PNG file
        ico_path: Path to output ICO file (optional)
        sizes: List of icon sizes to include (default: [16, 32, 48, 256])
    """
    if sizes is None:
        sizes = [16, 32, 48, 64, 128, 256]
    
    if ico_path is None:
        ico_path = png_path.rsplit('.', 1)[0] + '.ico'
    
    try:
        # Open the PNG image
        img = Image.open(png_path)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create a list of resized images
        icon_sizes = []
        for size in sizes:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            icon_sizes.append(resized)
        
        # Save as ICO with multiple sizes
        icon_sizes[0].save(
            ico_path,
            format='ICO',
            sizes=[(s, s) for s in sizes]
        )
        
        print(f"✓ Successfully converted {png_path} to {ico_path}")
        print(f"  Icon sizes: {sizes}")
        return True
        
    except Exception as e:
        print(f"✗ Error converting icon: {e}")
        print(f"  You can still build without an ICO file.")
        print(f"  The PNG icon will be included in the splash screen.")
        return False


if __name__ == "__main__":
    # Check for icon files in assets folder
    assets_dir = "assets"
    
    if not os.path.exists(assets_dir):
        print(f"✗ Assets folder not found: {assets_dir}")
        exit(1)
    
    # Look for PNG icon
    icon_files = [
        "py-ide icon.png",
        "icon.png",
        "logo.png"
    ]
    
    png_path = None
    for icon_file in icon_files:
        full_path = os.path.join(assets_dir, icon_file)
        if os.path.exists(full_path):
            png_path = full_path
            print(f"Found icon: {full_path}")
            break
    
    if png_path is None:
        print("✗ No PNG icon found in assets folder")
        print(f"  Looking for: {', '.join(icon_files)}")
        exit(1)
    
    # Check if PIL is installed
    try:
        from PIL import Image
    except ImportError:
        print("✗ Pillow library not installed")
        print("  Install with: pip install Pillow")
        print("  Or continue without ICO file (PNG will still work for splash)")
        exit(1)
    
    # Convert to ICO
    ico_path = os.path.join(assets_dir, "icon.ico")
    
    if png_to_ico(png_path, ico_path):
        print(f"\n✓ Icon ready for building!")
        print(f"  ICO file: {ico_path}")
        print(f"  PNG file: {png_path} (for splash screen)")
        print(f"\nYou can now run: build.bat")
    else:
        print(f"\n⚠ Build can continue without ICO file")
        print(f"  The PNG icon will still show in the splash screen")
