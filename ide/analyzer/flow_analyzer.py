"""
Function Flow Analyzer
Uses AST to safely parse Python code and build call graphs
"""
import ast
import os
from pathlib import Path
from typing import Dict, Set, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
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
    class_name: Optional[str] = None
    signature: str = ""
    docstring: str = ""
    source: str = ""
    end_line: Optional[int] = None
    loc: int = 0
    parameters: List[str] = field(default_factory=list)


class FunctionCallVisitor(ast.NodeVisitor):
    """AST visitor to extract function definitions and calls"""
    
    def __init__(self, filepath: str, source: str):
        self.filepath = filepath
        self.functions: Dict[str, FunctionInfo] = {}
        self.current_function = None
        self.current_class = None
        self.source = source
    
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
        
        signature, params = self._build_signature(node)
        docstring = ast.get_docstring(node) or ""
        source_snippet = self._get_source_snippet(node)
        end_line = getattr(node, 'end_lineno', node.lineno)
        loc = max(1, end_line - node.lineno + 1)

        # Create function info
        func_info = FunctionInfo(
            name=full_name,
            file=self.filepath,
            line=node.lineno,
            calls=set(),
            is_async=False,
            is_method=is_method,
            class_name=self.current_class,
            signature=signature,
            docstring=docstring,
            source=source_snippet,
            end_line=end_line,
            loc=loc,
            parameters=params
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
        
        signature, params = self._build_signature(node)
        docstring = ast.get_docstring(node) or ""
        source_snippet = self._get_source_snippet(node)
        end_line = getattr(node, 'end_lineno', node.lineno)
        loc = max(1, end_line - node.lineno + 1)

        func_info = FunctionInfo(
            name=full_name,
            file=self.filepath,
            line=node.lineno,
            calls=set(),
            is_async=True,
            is_method=is_method,
            class_name=self.current_class,
            signature=signature,
            docstring=docstring,
            source=source_snippet,
            end_line=end_line,
            loc=loc,
            parameters=params
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

    def _build_signature(self, node: ast.AST) -> Tuple[str, List[str]]:
        """Build function signature string"""
        params = []
        args = node.args
        pieces = []

        def format_arg(arg: ast.arg) -> str:
            annotation = None
            if getattr(arg, 'annotation', None) is not None:
                annotation = ast.get_source_segment(self.source, arg.annotation)
            text = arg.arg
            if annotation:
                text += f": {annotation}"
            return text

        positional = [format_arg(arg) for arg in args.args]
        params.extend(arg.arg for arg in args.args)

        defaults = [ast.get_source_segment(self.source, d) or "..." for d in args.defaults]
        # Align defaults with rightmost positional args
        for default, index in zip(reversed(defaults), range(len(positional) - 1, -1, -1)):
            positional[index] = f"{positional[index]}={default}"

        pieces.extend(positional)

        if args.vararg:
            pieces.append(f"*{format_arg(args.vararg)}")
            params.append(args.vararg.arg)
        elif args.kwonlyargs:
            pieces.append("*")

        for kw_arg, default in zip(args.kwonlyargs, args.kw_defaults):
            entry = format_arg(kw_arg)
            if default is not None:
                default_text = ast.get_source_segment(self.source, default) or "None"
                entry = f"{entry}={default_text}"
            pieces.append(entry)
            params.append(kw_arg.arg)

        if args.kwarg:
            pieces.append(f"**{format_arg(args.kwarg)}")
            params.append(args.kwarg.arg)

        signature = f"({', '.join(pieces)})"
        return signature, params

    def _get_source_snippet(self, node: ast.AST) -> str:
        """Get source code snippet for node"""
        if not self.source:
            return ""
        snippet = ast.get_source_segment(self.source, node)
        if snippet and len(snippet) > 800:
            return snippet[:800] + "\n..."
        return snippet or ""


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
            visitor = FunctionCallVisitor(filepath, source)
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
