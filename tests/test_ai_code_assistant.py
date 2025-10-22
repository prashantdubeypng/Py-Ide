"""
Tests for AI Code Assistant
Testing docstring generation, refactoring hints, and function summary caching
"""
import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ide.ai_code_assistant import (
    CodeExtractor,
    CodeMetrics,
    FunctionSummaryCache,
    DocstringGenerator,
    RefactoringAdvisor,
    AICodeAssistant
)
from ide.utils.settings import SettingsManager
from ide.utils.ai_manager import AIManager


class TestCodeExtractor(unittest.TestCase):
    """Test code extraction utilities"""
    
    def setUp(self):
        """Create temporary test file"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.py")
        
        test_code = '''
def simple_function(x, y):
    """A simple function"""
    return x + y

class TestClass:
    def method_one(self):
        pass
    
    async def async_method(self):
        await something()

def no_docstring():
    return 42
'''
        
        with open(self.test_file, 'w') as f:
            f.write(test_code)
    
    def tearDown(self):
        """Cleanup"""
        shutil.rmtree(self.test_dir)
    
    def test_extract_function_code(self):
        """Test function code extraction"""
        code = CodeExtractor.extract_function_code(self.test_file, "simple_function")
        self.assertIsNotNone(code)
        self.assertIn("def simple_function", code)
        self.assertIn("return x + y", code)
    
    def test_extract_nonexistent_function(self):
        """Test extraction of non-existent function"""
        code = CodeExtractor.extract_function_code(self.test_file, "nonexistent")
        self.assertIsNone(code)
    
    def test_extract_class_code(self):
        """Test class code extraction"""
        code = CodeExtractor.extract_class_code(self.test_file, "TestClass")
        self.assertIsNotNone(code)
        self.assertIn("class TestClass", code)
        self.assertIn("def method_one", code)
    
    def test_get_function_signature(self):
        """Test function signature extraction"""
        sig = CodeExtractor.get_function_signature(self.test_file, "simple_function")
        self.assertIsNotNone(sig)
        self.assertEqual(sig["name"], "simple_function")
        self.assertEqual(sig["args"], ["x", "y"])
        self.assertFalse(sig["is_async"])
    
    def test_has_docstring(self):
        """Test docstring detection"""
        has_doc = CodeExtractor.has_docstring(self.test_file, "simple_function")
        self.assertTrue(has_doc)
        
        no_doc = CodeExtractor.has_docstring(self.test_file, "no_docstring")
        self.assertFalse(no_doc)
    
    def test_compute_code_hash(self):
        """Test code hashing"""
        code1 = "def test(): pass"
        code2 = "def test(): pass"
        code3 = "def test(): return 1"
        
        hash1 = CodeExtractor.compute_code_hash(code1)
        hash2 = CodeExtractor.compute_code_hash(code2)
        hash3 = CodeExtractor.compute_code_hash(code3)
        
        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)


class TestCodeMetrics(unittest.TestCase):
    """Test code metrics computation"""
    
    def test_simple_function_metrics(self):
        """Test metrics for simple function"""
        code = """
def simple(x):
    return x + 1
"""
        metrics = CodeMetrics.get_function_metrics(code)
        
        self.assertIn("lines_of_code", metrics)
        self.assertIn("cyclomatic_complexity", metrics)
        self.assertEqual(metrics["parameter_count"], 1)
        self.assertEqual(metrics["cyclomatic_complexity"], 1)
        self.assertFalse(metrics["needs_refactoring"])
    
    def test_complex_function_metrics(self):
        """Test metrics for complex function"""
        code = """
def complex_function(a, b, c, d, e):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        return a + b + c + d + e
    return 0
"""
        metrics = CodeMetrics.get_function_metrics(code)
        
        self.assertGreater(metrics["cyclomatic_complexity"], 5)
        self.assertGreater(metrics["max_nesting_depth"], 3)
        self.assertTrue(metrics["needs_refactoring"])
    
    def test_function_with_loops(self):
        """Test metrics for function with loops"""
        code = """
def with_loops(items):
    total = 0
    for item in items:
        if item > 0:
            total += item
        else:
            total -= item
    return total
"""
        metrics = CodeMetrics.get_function_metrics(code)
        
        self.assertGreater(metrics["cyclomatic_complexity"], 1)


class TestFunctionSummaryCache(unittest.TestCase):
    """Test function summary caching"""
    
    def setUp(self):
        """Create temporary cache directory"""
        self.cache_dir = tempfile.mkdtemp()
        self.cache = FunctionSummaryCache(self.cache_dir)
    
    def tearDown(self):
        """Cleanup"""
        shutil.rmtree(self.cache_dir)
    
    def test_cache_set_and_get(self):
        """Test setting and getting cache entries"""
        file_path = "/test/file.py"
        func_name = "test_function"
        code_hash = "abc123"
        summary = "This function does something"
        
        # Set cache
        self.cache.set_summary(file_path, func_name, code_hash, summary)
        
        # Get cache
        result = self.cache.get_summary(file_path, func_name, code_hash)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["summary"], summary)
        self.assertEqual(result["hash"], code_hash)
    
    def test_cache_miss_wrong_hash(self):
        """Test cache miss with wrong hash"""
        file_path = "/test/file.py"
        func_name = "test_function"
        
        self.cache.set_summary(file_path, func_name, "hash1", "Summary 1")
        
        # Try to get with different hash
        result = self.cache.get_summary(file_path, func_name, "hash2")
        
        self.assertIsNone(result)
    
    def test_cache_with_all_fields(self):
        """Test caching with all optional fields"""
        file_path = "/test/file.py"
        func_name = "test_function"
        code_hash = "abc123"
        
        self.cache.set_summary(
            file_path, func_name, code_hash,
            summary="Summary",
            docstring="Docstring",
            refactoring_hints="Hints",
            metrics={"loc": 10}
        )
        
        result = self.cache.get_summary(file_path, func_name, code_hash)
        
        self.assertEqual(result["summary"], "Summary")
        self.assertEqual(result["docstring"], "Docstring")
        self.assertEqual(result["refactoring_hints"], "Hints")
        self.assertEqual(result["metrics"]["loc"], 10)
    
    def test_invalidate_file(self):
        """Test file cache invalidation"""
        file_path = "/test/file.py"
        
        self.cache.set_summary(file_path, "func1", "hash1", "Summary 1")
        self.cache.set_summary(file_path, "func2", "hash2", "Summary 2")
        
        # Invalidate
        self.cache.invalidate_file(file_path)
        
        # Verify cleared
        result1 = self.cache.get_summary(file_path, "func1", "hash1")
        result2 = self.cache.get_summary(file_path, "func2", "hash2")
        
        self.assertIsNone(result1)
        self.assertIsNone(result2)
    
    def test_clear_all(self):
        """Test clearing all cache"""
        self.cache.set_summary("/file1.py", "func1", "hash1", "Summary 1")
        self.cache.set_summary("/file2.py", "func2", "hash2", "Summary 2")
        
        self.cache.clear_all()
        
        result1 = self.cache.get_summary("/file1.py", "func1", "hash1")
        result2 = self.cache.get_summary("/file2.py", "func2", "hash2")
        
        self.assertIsNone(result1)
        self.assertIsNone(result2)
    
    def test_cache_stats(self):
        """Test cache statistics"""
        self.cache.set_summary("/file1.py", "func1", "hash1", "Summary 1")
        self.cache.set_summary("/file1.py", "func2", "hash2", "Summary 2")
        self.cache.set_summary("/file2.py", "func3", "hash3", "Summary 3")
        
        stats = self.cache.get_stats()
        
        self.assertEqual(stats["total_files"], 2)
        self.assertEqual(stats["total_functions"], 3)
        self.assertIn("cache_file", stats)
        self.assertGreater(stats["cache_size_kb"], 0)
    
    def test_persistence(self):
        """Test cache persistence across instances"""
        file_path = "/test/file.py"
        func_name = "test_function"
        code_hash = "abc123"
        summary = "Persisted summary"
        
        # Set in first instance
        cache1 = FunctionSummaryCache(self.cache_dir)
        cache1.set_summary(file_path, func_name, code_hash, summary)
        
        # Load in second instance
        cache2 = FunctionSummaryCache(self.cache_dir)
        result = cache2.get_summary(file_path, func_name, code_hash)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["summary"], summary)


class TestDocstringGenerator(unittest.TestCase):
    """Test docstring generation (mocked)"""
    
    def setUp(self):
        """Setup mock AI manager"""
        class MockAIManager:
            def generate_sync(self, prompt, use_cache=True):
                return '''"""
    Calculate the sum of two numbers.
    
    Args:
        x (int): First number
        y (int): Second number
    
    Returns:
        int: Sum of x and y
    """'''
        
        self.ai_manager = MockAIManager()
        self.generator = DocstringGenerator(self.ai_manager)
    
    def test_generate_docstring(self):
        """Test docstring generation"""
        code = "def add(x, y):\n    return x + y"
        
        docstring = self.generator.generate(code, style="google")
        
        self.assertIn('"""', docstring)
        self.assertIn("Args:", docstring)
        self.assertIn("Returns:", docstring)
    
    def test_clean_docstring(self):
        """Test docstring cleaning"""
        dirty = '```python\n"""\nTest docstring\n"""\n```'
        clean = self.generator._clean_docstring(dirty)
        
        self.assertNotIn("```", clean)
        self.assertIn('"""', clean)


class TestRefactoringAdvisor(unittest.TestCase):
    """Test refactoring advisor (mocked)"""
    
    def setUp(self):
        """Setup mock AI manager"""
        class MockAIManager:
            def generate_sync(self, prompt, use_cache=True):
                return """Refactoring Suggestions:
1. Reduce function complexity
2. Extract nested logic into helper methods
3. Add type hints for better code clarity"""
        
        self.ai_manager = MockAIManager()
        self.advisor = RefactoringAdvisor(self.ai_manager)
    
    def test_analyze_code(self):
        """Test code analysis"""
        code = "def complex(): pass"
        
        advice = self.advisor.analyze(code)
        
        self.assertIn("Refactoring", advice)
        self.assertIsInstance(advice, str)
    
    def test_analyze_with_metrics(self):
        """Test analysis with metrics"""
        code = "def test(): pass"
        metrics = {"lines_of_code": 100, "cyclomatic_complexity": 15}
        
        advice = self.advisor.analyze(code, metrics)
        
        self.assertIsInstance(advice, str)


class TestAICodeAssistantIntegration(unittest.TestCase):
    """Integration tests for AI Code Assistant (mocked)"""
    
    def setUp(self):
        """Setup"""
        self.test_dir = tempfile.mkdtemp()
        self.cache_dir = tempfile.mkdtemp()
        
        # Create test file
        self.test_file = os.path.join(self.test_dir, "test.py")
        test_code = '''
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        if num > 0:
            total += num
    return total
'''
        with open(self.test_file, 'w') as f:
            f.write(test_code)
        
        # Mock AI Manager
        class MockAIManager:
            def generate_sync(self, prompt, use_cache=True):
                if "Summarize" in prompt:
                    return "Calculates sum of positive numbers"
                elif "docstring" in prompt:
                    return '"""Sum positive numbers"""'
                elif "refactoring" in prompt or "Provide" in prompt:
                    return "Use list comprehension for better performance"
                return "Mock response"
            
            def get_stats(self):
                return {
                    "total_requests": 10,
                    "cache_hits": 5,
                    "api_calls": 5,
                    "errors": 0,
                    "provider": "MockProvider"
                }
        
        self.ai_manager = MockAIManager()
        self.assistant = AICodeAssistant(self.ai_manager, self.cache_dir)
    
    def tearDown(self):
        """Cleanup"""
        shutil.rmtree(self.test_dir)
        shutil.rmtree(self.cache_dir)
    
    def test_analyze_function(self):
        """Test complete function analysis"""
        result = self.assistant.analyze_function(
            self.test_file,
            "calculate_sum",
            force_refresh=True
        )
        
        self.assertNotIn("error", result)
        self.assertIn("summary", result)
        self.assertIn("metrics", result)
        self.assertIn("hash", result)
    
    def test_analyze_function_with_cache(self):
        """Test cached function analysis"""
        # First call
        result1 = self.assistant.analyze_function(self.test_file, "calculate_sum")
        
        # Second call (should hit cache)
        result2 = self.assistant.analyze_function(self.test_file, "calculate_sum")
        
        self.assertEqual(result1["hash"], result2["hash"])
        self.assertEqual(result1["summary"], result2["summary"])
    
    def test_generate_docstring_for_function(self):
        """Test docstring generation for function"""
        docstring = self.assistant.generate_docstring_for_function(
            self.test_file,
            "calculate_sum",
            style="google",
            insert=False
        )
        
        self.assertIsNotNone(docstring)
        self.assertIsInstance(docstring, str)
    
    def test_get_refactoring_advice(self):
        """Test refactoring advice"""
        advice = self.assistant.get_refactoring_advice(self.test_file, "calculate_sum")
        
        self.assertIsNotNone(advice)
        self.assertIsInstance(advice, str)
    
    def test_get_stats(self):
        """Test statistics retrieval"""
        # Generate some activity
        self.assistant.analyze_function(self.test_file, "calculate_sum")
        
        stats = self.assistant.get_stats()
        
        self.assertIn("cache_stats", stats)
        self.assertIn("ai_stats", stats)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCodeExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestCodeMetrics))
    suite.addTests(loader.loadTestsFromTestCase(TestFunctionSummaryCache))
    suite.addTests(loader.loadTestsFromTestCase(TestDocstringGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestRefactoringAdvisor))
    suite.addTests(loader.loadTestsFromTestCase(TestAICodeAssistantIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
