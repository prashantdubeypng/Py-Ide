"""
AI Code Assistant - Advanced Features
Docstring generation, refactoring hints, function summaries with caching
"""
import os
import ast
import json
import hashlib
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from pathlib import Path

from ide.utils.logger import logger


class CodeExtractor:
    """Extract code snippets from Python files"""
    
    @staticmethod
    def extract_function_code(file_path: str, func_name: str) -> Optional[str]:
        """Extract function code by name"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                    return ast.get_source_segment(source, node)
            
            return None
        except Exception as e:
            logger.error(f"Failed to extract function {func_name} from {file_path}: {e}")
            return None
    
    @staticmethod
    def extract_class_code(file_path: str, class_name: str) -> Optional[str]:
        """Extract class code by name"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    return ast.get_source_segment(source, node)
            
            return None
        except Exception as e:
            logger.error(f"Failed to extract class {class_name} from {file_path}: {e}")
            return None
    
    @staticmethod
    def get_function_signature(file_path: str, func_name: str) -> Optional[Dict]:
        """Get function signature details"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                    args = [arg.arg for arg in node.args.args]
                    defaults = [ast.unparse(d) for d in node.args.defaults] if node.args.defaults else []
                    returns = ast.unparse(node.returns) if node.returns else None
                    
                    return {
                        "name": func_name,
                        "args": args,
                        "defaults": defaults,
                        "returns": returns,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "lineno": node.lineno
                    }
            
            return None
        except Exception as e:
            logger.error(f"Failed to get signature for {func_name}: {e}")
            return None
    
    @staticmethod
    def has_docstring(file_path: str, func_name: str) -> bool:
        """Check if function has docstring"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                    return ast.get_docstring(node) is not None
            
            return False
        except Exception as e:
            logger.error(f"Failed to check docstring for {func_name}: {e}")
            return False
    
    @staticmethod
    def compute_code_hash(code: str) -> str:
        """Compute MD5 hash of code"""
        return hashlib.md5(code.encode('utf-8')).hexdigest()


class CodeMetrics:
    """Compute code quality metrics"""
    
    @staticmethod
    def get_function_metrics(code: str) -> Dict:
        """Get complexity metrics for function"""
        try:
            tree = ast.parse(code)
            func_node = None
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_node = node
                    break
            
            if not func_node:
                return {}
            
            # Count lines (excluding docstring and comments)
            lines = [l for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]
            loc = len(lines)
            
            # Count parameters
            param_count = len(func_node.args.args)
            
            # Estimate cyclomatic complexity (simplified)
            complexity = 1  # Base complexity
            for node in ast.walk(func_node):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
            
            # Nesting depth
            max_depth = CodeMetrics._get_max_nesting_depth(func_node)
            
            return {
                "lines_of_code": loc,
                "parameter_count": param_count,
                "cyclomatic_complexity": complexity,
                "max_nesting_depth": max_depth,
                "needs_refactoring": loc > 50 or complexity > 10 or max_depth > 4
            }
        
        except Exception as e:
            logger.error(f"Failed to compute metrics: {e}")
            return {}
    
    @staticmethod
    def _get_max_nesting_depth(node, current_depth=0):
        """Get maximum nesting depth"""
        max_depth = current_depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                child_depth = CodeMetrics._get_max_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = CodeMetrics._get_max_nesting_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)
        
        return max_depth


class FunctionSummaryCache:
    """Cache function summaries with hash-based validation"""
    
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            cache_dir = os.path.expanduser("~/.py_ide_cache")
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_file = self.cache_dir / "function_summaries.json"
        self.cache: Dict = self._load_cache()
        
        logger.info(f"Function summary cache initialized at {self.cache_file}")
    
    def _load_cache(self) -> Dict:
        """Load cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
                return {}
        return {}
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def get_summary(self, file_path: str, func_name: str, code_hash: str) -> Optional[Dict]:
        """Get cached summary if valid"""
        file_path = os.path.abspath(file_path)
        
        if file_path not in self.cache:
            return None
        
        if func_name not in self.cache[file_path]:
            return None
        
        entry = self.cache[file_path][func_name]
        
        # Validate hash
        if entry.get("hash") != code_hash:
            logger.debug(f"Cache miss for {func_name}: hash mismatch")
            return None
        
        logger.debug(f"Cache hit for {func_name}")
        return entry
    
    def set_summary(
        self,
        file_path: str,
        func_name: str,
        code_hash: str,
        summary: str,
        docstring: str = None,
        refactoring_hints: str = None,
        metrics: Dict = None
    ):
        """Cache function summary"""
        file_path = os.path.abspath(file_path)
        
        if file_path not in self.cache:
            self.cache[file_path] = {}
        
        self.cache[file_path][func_name] = {
            "summary": summary,
            "docstring": docstring,
            "refactoring_hints": refactoring_hints,
            "metrics": metrics or {},
            "hash": code_hash,
            "last_updated": datetime.now().isoformat(),
            "timestamp": datetime.now().timestamp()
        }
        
        self._save_cache()
        logger.debug(f"Cached summary for {func_name}")
    
    def invalidate_file(self, file_path: str):
        """Remove all cached entries for a file"""
        file_path = os.path.abspath(file_path)
        if file_path in self.cache:
            del self.cache[file_path]
            self._save_cache()
            logger.info(f"Invalidated cache for {file_path}")
    
    def clear_all(self):
        """Clear entire cache"""
        self.cache = {}
        self._save_cache()
        logger.info("Cleared all function summaries")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_files = len(self.cache)
        total_functions = sum(len(funcs) for funcs in self.cache.values())
        
        return {
            "total_files": total_files,
            "total_functions": total_functions,
            "cache_file": str(self.cache_file),
            "cache_size_kb": self.cache_file.stat().st_size / 1024 if self.cache_file.exists() else 0
        }


class DocstringGenerator:
    """Generate docstrings using AI"""
    
    def __init__(self, ai_manager):
        self.ai_manager = ai_manager
        self.style = "google"  # google, numpy, sphinx
    
    def generate(self, code: str, style: str = None) -> str:
        """Generate docstring for code"""
        style = style or self.style
        
        prompt = self._build_prompt(code, style)
        
        try:
            docstring = self.ai_manager.generate_sync(prompt, use_cache=True)
            return self._clean_docstring(docstring)
        except Exception as e:
            logger.error(f"Failed to generate docstring: {e}")
            return f'"""TODO: Add docstring\n\n    Generated by AI Assistant\n    Error: {str(e)[:100]}\n    """'
    
    def _build_prompt(self, code: str, style: str) -> str:
        """Build AI prompt for docstring generation"""
        style_examples = {
            "google": """Example format:
    \"\"\"
    Brief description of what the function does.
    
    Args:
        param1 (type): Description of param1.
        param2 (type): Description of param2.
    
    Returns:
        type: Description of return value.
    
    Raises:
        ErrorType: When this error occurs.
    \"\"\"
""",
            "numpy": """Example format:
    \"\"\"
    Brief description of what the function does.
    
    Parameters
    ----------
    param1 : type
        Description of param1.
    param2 : type
        Description of param2.
    
    Returns
    -------
    type
        Description of return value.
    \"\"\"
""",
            "sphinx": """Example format:
    \"\"\"
    Brief description of what the function does.
    
    :param param1: Description of param1.
    :type param1: type
    :param param2: Description of param2.
    :type param2: type
    :return: Description of return value.
    :rtype: type
    \"\"\"
"""
        }
        
        example = style_examples.get(style.lower(), style_examples["google"])
        
        return f"""Generate a comprehensive {style.upper()}-style docstring for this Python code.
Be specific about parameters, return values, and exceptions.
Return ONLY the docstring (triple-quoted), no additional text.

{example}

Code to document:
```python
{code}
```

Docstring:"""
    
    def _clean_docstring(self, docstring: str) -> str:
        """Clean and format generated docstring"""
        # Remove markdown code blocks if present
        docstring = docstring.strip()
        if docstring.startswith("```"):
            lines = docstring.split('\n')
            docstring = '\n'.join(lines[1:-1] if len(lines) > 2 else lines)
        
        # Ensure triple quotes
        if not docstring.startswith('"""') and not docstring.startswith("'''"):
            docstring = f'"""{docstring}"""'
        
        # Add warning comment
        docstring = f'{docstring}\n    # [AI-Generated - Review Before Commit]'
        
        return docstring.strip()
    
    def insert_docstring(self, file_path: str, func_name: str, docstring: str) -> bool:
        """Insert docstring into function"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find function definition
            func_line = None
            for i, line in enumerate(lines):
                if f"def {func_name}(" in line or f"async def {func_name}(" in line:
                    func_line = i
                    break
            
            if func_line is None:
                logger.error(f"Function {func_name} not found in {file_path}")
                return False
            
            # Get indentation
            indent = len(lines[func_line]) - len(lines[func_line].lstrip())
            indent_str = ' ' * (indent + 4)
            
            # Format docstring with proper indentation
            docstring_lines = docstring.split('\n')
            formatted_docstring = [indent_str + line if line.strip() else line for line in docstring_lines]
            
            # Insert after function definition (skip decorators)
            insert_line = func_line + 1
            while insert_line < len(lines) and lines[insert_line].strip().startswith('@'):
                insert_line += 1
            
            # Insert docstring
            lines.insert(insert_line, '\n'.join(formatted_docstring) + '\n')
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            logger.info(f"Inserted docstring for {func_name} in {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to insert docstring: {e}")
            return False


class RefactoringAdvisor:
    """Provide refactoring suggestions using AI"""
    
    def __init__(self, ai_manager):
        self.ai_manager = ai_manager
    
    def analyze(self, code: str, metrics: Dict = None) -> str:
        """Analyze code and provide refactoring suggestions"""
        prompt = self._build_prompt(code, metrics)
        
        try:
            advice = self.ai_manager.generate_sync(prompt, use_cache=True)
            return advice
        except Exception as e:
            logger.error(f"Failed to get refactoring advice: {e}")
            return f"❌ Error: {str(e)[:100]}"
    
    def _build_prompt(self, code: str, metrics: Dict = None) -> str:
        """Build AI prompt for refactoring advice"""
        prompt = f"""Analyze this Python code and provide specific, actionable refactoring suggestions.
Focus on:
1. Readability improvements
2. Performance optimizations
3. Best practices
4. Design patterns

Provide 3-5 concrete suggestions with code examples where helpful.

Code to analyze:
```python
{code}
```
"""
        
        if metrics:
            prompt += f"\nCode Metrics:\n"
            if metrics.get("lines_of_code"):
                prompt += f"- Lines of code: {metrics['lines_of_code']}\n"
            if metrics.get("cyclomatic_complexity"):
                prompt += f"- Cyclomatic complexity: {metrics['cyclomatic_complexity']}\n"
            if metrics.get("max_nesting_depth"):
                prompt += f"- Max nesting depth: {metrics['max_nesting_depth']}\n"
            if metrics.get("parameter_count"):
                prompt += f"- Parameter count: {metrics['parameter_count']}\n"
        
        prompt += "\nRefactoring Suggestions:"
        return prompt


class AICodeAssistant:
    """Main AI code assistant integrating all features"""
    
    def __init__(self, ai_manager, cache_dir: str = None):
        self.ai_manager = ai_manager
        self.cache = FunctionSummaryCache(cache_dir)
        self.extractor = CodeExtractor()
        self.metrics_analyzer = CodeMetrics()
        self.docstring_gen = DocstringGenerator(ai_manager)
        self.refactoring_advisor = RefactoringAdvisor(ai_manager)
        
        logger.info("AI Code Assistant initialized")
    
    def analyze_function(
        self,
        file_path: str,
        func_name: str,
        force_refresh: bool = False
    ) -> Dict:
        """Complete analysis of a function with caching"""
        
        # Extract code
        code = self.extractor.extract_function_code(file_path, func_name)
        if not code:
            return {"error": f"Function {func_name} not found"}
        
        # Compute hash
        code_hash = self.extractor.compute_code_hash(code)
        
        # Check cache
        if not force_refresh:
            cached = self.cache.get_summary(file_path, func_name, code_hash)
            if cached:
                logger.info(f"Using cached analysis for {func_name}")
                return cached
        
        logger.info(f"Generating new analysis for {func_name}")
        
        # Compute metrics
        metrics = self.metrics_analyzer.get_function_metrics(code)
        
        # Generate summary
        summary = self._generate_summary(code)
        
        # Generate docstring (if needed)
        has_doc = self.extractor.has_docstring(file_path, func_name)
        docstring = None if has_doc else self.docstring_gen.generate(code)
        
        # Get refactoring advice (if metrics suggest refactoring needed)
        refactoring_hints = None
        if metrics.get("needs_refactoring"):
            refactoring_hints = self.refactoring_advisor.analyze(code, metrics)
        
        # Cache results
        result = {
            "summary": summary,
            "docstring": docstring,
            "refactoring_hints": refactoring_hints,
            "metrics": metrics,
            "hash": code_hash,
            "has_docstring": has_doc,
            "code_preview": code[:200] + "..." if len(code) > 200 else code
        }
        
        self.cache.set_summary(
            file_path, func_name, code_hash,
            summary, docstring, refactoring_hints, metrics
        )
        
        return result
    
    def _generate_summary(self, code: str) -> str:
        """Generate function summary"""
        prompt = f"""Summarize this Python function in 2-3 sentences.
Include: what it does, key inputs, and outputs.

```python
{code}
```

Summary:"""
        
        try:
            return self.ai_manager.generate_sync(prompt, use_cache=True)
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"Error generating summary: {str(e)[:100]}"
    
    def generate_docstring_for_function(
        self,
        file_path: str,
        func_name: str,
        style: str = "google",
        insert: bool = False
    ) -> str:
        """Generate and optionally insert docstring"""
        code = self.extractor.extract_function_code(file_path, func_name)
        if not code:
            return f"Error: Function {func_name} not found"
        
        docstring = self.docstring_gen.generate(code, style)
        
        if insert and docstring:
            success = self.docstring_gen.insert_docstring(file_path, func_name, docstring)
            if success:
                # Invalidate cache
                self.cache.invalidate_file(file_path)
        
        return docstring
    
    def get_refactoring_advice(self, file_path: str, func_name: str) -> str:
        """Get refactoring advice for function"""
        code = self.extractor.extract_function_code(file_path, func_name)
        if not code:
            return f"Error: Function {func_name} not found"
        
        metrics = self.metrics_analyzer.get_function_metrics(code)
        return self.refactoring_advisor.analyze(code, metrics)
    
    def scan_project(self, project_dir: str, file_pattern: str = "*.py") -> Dict:
        """Scan entire project and cache summaries"""
        from pathlib import Path
        
        project_path = Path(project_dir)
        python_files = list(project_path.rglob(file_pattern))
        
        results = {
            "scanned_files": 0,
            "total_functions": 0,
            "cached_functions": 0,
            "errors": []
        }
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                
                tree = ast.parse(source)
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        results["total_functions"] += 1
                        
                        # Analyze and cache
                        self.analyze_function(str(py_file), node.name)
                        results["cached_functions"] += 1
                
                results["scanned_files"] += 1
            
            except Exception as e:
                results["errors"].append(f"{py_file}: {str(e)[:100]}")
        
        logger.info(f"Project scan complete: {results}")
        return results
    
    def get_stats(self) -> Dict:
        """Get assistant statistics"""
        return {
            "cache_stats": self.cache.get_stats(),
            "ai_stats": self.ai_manager.get_stats()
        }


if __name__ == "__main__":
    # Test
    from ide.utils.settings import SettingsManager
    from ide.utils.ai_manager import AIManager
    
    settings = SettingsManager()
    ai_mgr = AIManager(settings)
    ai_mgr.initialize_provider()
    
    assistant = AICodeAssistant(ai_mgr)
    
    # Test with current file
    result = assistant.analyze_function(__file__, "analyze_function")
    print(json.dumps(result, indent=2))
