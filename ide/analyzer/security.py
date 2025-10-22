"""
Security utilities for Function Flow Analyzer
Prevents code execution, path traversal, and resource exhaustion
"""
import os
import html
from pathlib import Path
from typing import Tuple

# Security limits
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB per file
MAX_FILES = 1000  # Maximum files to analyze
MAX_DEPTH = 100  # Maximum recursion depth in call chains
MAX_NODES = 5000  # Maximum nodes in graph


def is_safe_path(base_path: str, target_path: str) -> bool:
    """
    Verify that target_path is within base_path (no directory traversal)
    
    Args:
        base_path: Root project directory
        target_path: File path to validate
        
    Returns:
        True if path is safe, False otherwise
    """
    try:
        base = Path(base_path).resolve()
        target = Path(target_path).resolve()
        
        # Check if target is within base
        return str(target).startswith(str(base))
    except Exception:
        return False


def is_safe_file_size(filepath: str) -> bool:
    """
    Check if file size is within safety limits
    
    Args:
        filepath: Path to file
        
    Returns:
        True if file size is acceptable
    """
    try:
        size = os.path.getsize(filepath)
        return size <= MAX_FILE_SIZE
    except Exception:
        return False


def sanitize_text(text: str) -> str:
    """
    Sanitize text for HTML rendering (prevent XSS)
    
    Args:
        text: Raw text
        
    Returns:
        HTML-escaped text
    """
    return html.escape(str(text), quote=True)


def sanitize_node_name(name: str) -> str:
    """
    Sanitize function/node names for safe display
    
    Args:
        name: Function or node name
        
    Returns:
        Sanitized name
    """
    # Remove any potentially dangerous characters
    safe_name = name.replace("<", "&lt;").replace(">", "&gt;")
    safe_name = safe_name.replace("'", "&#39;").replace('"', "&quot;")
    return safe_name[:200]  # Limit length


def is_python_file(filepath: str) -> bool:
    """
    Check if file is a Python source file
    
    Args:
        filepath: Path to file
        
    Returns:
        True if .py file
    """
    return filepath.endswith('.py')


def get_safe_file_list(root_dir: str, max_files: int = MAX_FILES) -> list:
    """
    Get list of safe Python files to analyze
    
    Args:
        root_dir: Root directory to scan
        max_files: Maximum number of files to return
        
    Returns:
        List of safe file paths
    """
    safe_files = []
    
    try:
        for root, dirs, files in os.walk(root_dir):
            # Skip common ignored directories
            dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', '.venv', 'venv', 
                'node_modules', '.idea', 'build', 'dist'
            }]
            
            for file in files:
                if len(safe_files) >= max_files:
                    break
                    
                if is_python_file(file):
                    filepath = os.path.join(root, file)
                    
                    # Validate path and size
                    if is_safe_path(root_dir, filepath) and is_safe_file_size(filepath):
                        safe_files.append(filepath)
            
            if len(safe_files) >= max_files:
                break
                
    except Exception as e:
        print(f"Error scanning directory: {e}")
    
    return safe_files


class SecurityValidator:
    """Validates operations for security compliance"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.files_processed = 0
        self.nodes_created = 0
    
    def validate_file(self, filepath: str) -> Tuple[bool, str]:
        """
        Validate if file can be safely analyzed
        
        Returns:
            (is_valid, error_message)
        """
        # Check file count
        if self.files_processed >= MAX_FILES:
            return False, f"Maximum file limit reached ({MAX_FILES})"
        
        # Check path safety
        if not is_safe_path(str(self.project_root), filepath):
            return False, "Path is outside project directory"
        
        # Check file existence
        if not os.path.exists(filepath):
            return False, "File does not exist"
        
        # Check file type
        if not is_python_file(filepath):
            return False, "Not a Python file"
        
        # Check file size
        if not is_safe_file_size(filepath):
            return False, f"File too large (max {MAX_FILE_SIZE} bytes)"
        
        self.files_processed += 1
        return True, ""
    
    def validate_node_creation(self) -> Tuple[bool, str]:
        """
        Validate if new node can be created
        
        Returns:
            (is_valid, error_message)
        """
        if self.nodes_created >= MAX_NODES:
            return False, f"Maximum node limit reached ({MAX_NODES})"
        
        self.nodes_created += 1
        return True, ""
    
    def reset(self):
        """Reset counters"""
        self.files_processed = 0
        self.nodes_created = 0
