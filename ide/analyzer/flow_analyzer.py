"""
Function Flow Analyzer
Uses AST to safely parse Python code and build call graphs
"""
import ast
import os
from pathlib import Path
from typing import Dict, Set, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib

from ide.analyzer.security import SecurityValidator, sanitize_node_name


@dataclass
class FunctionInfo:
    """Information about a function"""
    name: str
    file: str
    line: int
    calls: Set[str]
    is_async: bool = False
    is_method: bool = False
    class_name: str = None


class FunctionCallVisitor(ast.NodeVisitor):
    """AST visitor to extract function definitions and calls"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.functions: Dict[str, FunctionInfo] = {}
        self.current_function = None
        self.current_class = None
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition"""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition"""
        func_name = node.name
        
        # Build full name with class if it's a method
        if self.current_class:
            full_name = f"{self.current_class}.{func_name}"
            is_method = True
        else:
            full_name = func_name
            is_method = False
        
        # Create function info
        func_info = FunctionInfo(
            name=full_name,
            file=self.filepath,
            line=node.lineno,
            calls=set(),
            is_async=False,
            is_method=is_method,
            class_name=self.current_class
        )
        
        self.functions[full_name] = func_info
        
        # Visit function body to find calls
        old_function = self.current_function
        self.current_function = full_name
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definition"""
        func_name = node.name
        
        if self.current_class:
            full_name = f"{self.current_class}.{func_name}"
            is_method = True
        else:
            full_name = func_name
            is_method = False
        
        func_info = FunctionInfo(
            name=full_name,
            file=self.filepath,
            line=node.lineno,
            calls=set(),
            is_async=True,
            is_method=is_method,
            class_name=self.current_class
        )
        
        self.functions[full_name] = func_info
        
        old_function = self.current_function
        self.current_function = full_name
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_Call(self, node: ast.Call):
        """Visit function call"""
        if self.current_function:
            called_func = self._get_call_name(node.func)
            if called_func:
                self.functions[self.current_function].calls.add(called_func)
        
        self.generic_visit(node)
    
    def _get_call_name(self, node) -> str:
        """Extract function name from call node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # Handle method calls like obj.method()
            if isinstance(node.value, ast.Name):
                return f"{node.value.id}.{node.attr}"
            return node.attr
        return None


class FunctionFlowAnalyzer:
    """
    Main analyzer class - coordinates multi-file analysis
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.security_validator = None
        self.cache = {}  # File hash -> parsed data
    
    def analyze_project(self, project_root: str) -> Dict[str, FunctionInfo]:
        """
        Analyze entire project directory
        
        Args:
            project_root: Root directory of project
            
        Returns:
            Dictionary mapping function names to FunctionInfo
        """
        self.security_validator = SecurityValidator(project_root)
        
        # Get safe file list
        from ide.analyzer.security import get_safe_file_list
        python_files = get_safe_file_list(project_root)
        
        if not python_files:
            return {}
        
        print(f"Analyzing {len(python_files)} Python files...")
        
        # Parallel processing
        all_functions = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._analyze_file, filepath): filepath 
                for filepath in python_files
            }
            
            for future in as_completed(future_to_file):
                filepath = future_to_file[future]
                try:
                    functions = future.result()
                    all_functions.update(functions)
                except Exception as e:
                    print(f"Error analyzing {filepath}: {e}")
        
        print(f"Found {len(all_functions)} functions")
        return all_functions
    
    def _analyze_file(self, filepath: str) -> Dict[str, FunctionInfo]:
        """
        Analyze a single Python file
        
        Args:
            filepath: Path to Python file
            
        Returns:
            Dictionary of functions found in file
        """
        # Security validation
        is_valid, error = self.security_validator.validate_file(filepath)
        if not is_valid:
            print(f"Skipping {filepath}: {error}")
            return {}
        
        # Check cache
        file_hash = self._get_file_hash(filepath)
        if file_hash in self.cache:
            return self.cache[file_hash]
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Parse with AST (safe - never executes code)
            tree = ast.parse(source, filename=filepath)
            
            # Visit nodes
            visitor = FunctionCallVisitor(filepath)
            visitor.visit(tree)
            
            # Sanitize function names for security
            sanitized_functions = {}
            for name, info in visitor.functions.items():
                safe_name = sanitize_node_name(name)
                info.name = safe_name
                sanitized_functions[safe_name] = info
            
            # Cache result
            self.cache[file_hash] = sanitized_functions
            
            return sanitized_functions
            
        except SyntaxError as e:
            print(f"Syntax error in {filepath}: {e}")
            return {}
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return {}
    
    def _get_file_hash(self, filepath: str) -> str:
        """Get hash of file for caching"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def analyze_file(self, filepath: str) -> Dict[str, FunctionInfo]:
        """
        Analyze a single file (public interface)
        
        Args:
            filepath: Path to Python file
            
        Returns:
            Dictionary of functions
        """
        return self._analyze_file(filepath)
