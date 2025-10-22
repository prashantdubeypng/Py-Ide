"""
Comprehensive Test Suite
Tests for analyzer, secret manager, AI manager, and chat panel
"""
import unittest
import tempfile
import os
import json
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Test imports
from ide.analyzer.flow_analyzer import FunctionFlowAnalyzer, FunctionInfo
from ide.analyzer.graph_builder import GraphBuilder
from ide.utils.secret_manager import SecretManager
from ide.utils.settings import SettingsManager
from ide.utils.ai_manager import (
    AIManager, OpenAIProvider, GeminiProvider,
    RequestCache, RateLimiter
)


class TestFunctionFlowAnalyzer(unittest.TestCase):
    """Test function flow analyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = FunctionFlowAnalyzer()
        self.test_code = '''
def func_a():
    """Function A"""
    return func_b()

def func_b():
    """Function B"""
    return func_c()

def func_c():
    """Function C"""
    return 42

class TestClass:
    def method_a(self):
        return self.method_b()
    
    def method_b(self):
        return 100
'''
    
    def test_analyzer_initialization(self):
        """Test analyzer initializes correctly"""
        self.assertIsNotNone(self.analyzer)
        self.assertEqual(self.analyzer.max_file_size_mb, 10)
        self.assertEqual(self.analyzer.max_workers, 4)
    
    def test_parse_simple_functions(self):
        """Test parsing simple functions"""
        functions = self.analyzer._parse_functions(self.test_code, "test.py")
        
        self.assertGreater(len(functions), 0)
        func_names = [f.name for f in functions]
        self.assertIn("func_a", func_names)
        self.assertIn("func_b", func_names)
        self.assertIn("func_c", func_names)
    
    def test_function_info_attributes(self):
        """Test FunctionInfo has required attributes"""
        functions = self.analyzer._parse_functions(self.test_code, "test.py")
        
        func = next((f for f in functions if f.name == "func_a"), None)
        self.assertIsNotNone(func)
        
        # Check required attributes
        self.assertIsNotNone(func.name)
        self.assertIsNotNone(func.file_path)
        self.assertIsNotNone(func.line_number)
        self.assertIsNotNone(func.calls)
        self.assertIsNotNone(func.docstring)
        self.assertIsNotNone(func.signature)
        self.assertIsNotNone(func.loc)
    
    def test_analyze_project(self):
        """Test analyzing a temporary project"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_file = Path(tmpdir) / "test_module.py"
            test_file.write_text(self.test_code)
            
            functions = self.analyzer.analyze_project(tmpdir)
            
            self.assertGreater(len(functions), 0)
            self.assertTrue(any(f.name == "func_a" for f in functions))
    
    def test_skip_large_files(self):
        """Test large files are skipped"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create large file
            large_file = Path(tmpdir) / "large.py"
            large_file.write_text("x = 1\n" * 20000)
            
            with patch.object(self.analyzer, 'max_file_size_mb', 0.001):
                functions = self.analyzer.analyze_project(tmpdir)
                
                # Should skip large file
                self.assertFalse(any(f.file_path.endswith("large.py") for f in functions))
    
    def test_calls_extraction(self):
        """Test call extraction"""
        code = '''
def caller():
    return callee1() + callee2()

def callee1():
    return 1

def callee2():
    return 2
'''
        functions = self.analyzer._parse_functions(code, "test.py")
        caller = next((f for f in functions if f.name == "caller"), None)
        
        self.assertIsNotNone(caller)
        self.assertEqual(len(caller.calls), 2)
        self.assertIn("callee1", caller.calls)
        self.assertIn("callee2", caller.calls)


class TestGraphBuilder(unittest.TestCase):
    """Test call graph builder"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.builder = GraphBuilder()
        
        # Create mock functions
        self.func_a = FunctionInfo(
            name="func_a",
            file_path="test.py",
            line_number=1,
            calls=["func_b"],
            docstring="Test A"
        )
        
        self.func_b = FunctionInfo(
            name="func_b",
            file_path="test.py",
            line_number=5,
            calls=["func_c"],
            docstring="Test B"
        )
        
        self.func_c = FunctionInfo(
            name="func_c",
            file_path="test.py",
            line_number=10,
            calls=[],
            docstring="Test C"
        )
    
    def test_builder_initialization(self):
        """Test builder initializes"""
        self.assertIsNotNone(self.builder)
        self.assertEqual(len(self.builder.graph.nodes()), 0)
    
    def test_build_from_functions(self):
        """Test building graph from functions"""
        functions = [self.func_a, self.func_b, self.func_c]
        graph = self.builder.build_from_functions(functions)
        
        self.assertGreater(len(graph.nodes()), 0)
        self.assertGreater(len(graph.edges()), 0)
    
    def test_find_cycles(self):
        """Test cycle detection"""
        # Create cyclic functions
        func1 = FunctionInfo("f1", "test.py", 1, calls=["f2"], docstring="")
        func2 = FunctionInfo("f2", "test.py", 2, calls=["f3"], docstring="")
        func3 = FunctionInfo("f3", "test.py", 3, calls=["f1"], docstring="")
        
        self.builder.build_from_functions([func1, func2, func3])
        cycles = self.builder.find_cycles()
        
        self.assertGreater(len(cycles), 0)
    
    def test_get_stats(self):
        """Test statistics generation"""
        functions = [self.func_a, self.func_b, self.func_c]
        self.builder.build_from_functions(functions)
        
        stats = self.builder.get_stats()
        
        self.assertIn("total_functions", stats)
        self.assertIn("total_calls", stats)
        self.assertIn("avg_loc", stats)
        self.assertGreater(stats["total_functions"], 0)


class TestSecretManager(unittest.TestCase):
    """Test secret manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.secret_file = os.path.join(self.temp_dir, "secrets.json")
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('ide.utils.secret_manager.SecretManager.secret_file', new_callable=lambda: property(lambda self: os.path.join(tempfile.gettempdir(), "test_secrets.json")))
    def test_secret_manager_initialization(self, mock_file):
        """Test secret manager initializes"""
        manager = SecretManager()
        self.assertIsNotNone(manager)
    
    def test_set_and_get_secret(self):
        """Test storing and retrieving secrets"""
        with patch.object(SecretManager, 'secret_file', new_callable=lambda: property(lambda self: self.test_file)):
            manager = SecretManager()
            manager.test_file = os.path.join(self.temp_dir, "test_secrets.json")
            
            # Set secret
            manager.set_secret("test_key", "test_value")
            
            # Get secret
            value = manager.get_secret("test_key")
            self.assertEqual(value, "test_value")
    
    def test_secret_encryption(self):
        """Test secrets are encrypted"""
        with patch.object(SecretManager, 'secret_file', new_callable=lambda: property(lambda self: self.test_file)):
            manager = SecretManager()
            manager.test_file = os.path.join(self.temp_dir, "test_secrets.json")
            
            manager.set_secret("encrypted_key", "secret_value")
            
            # Read file to verify encryption
            if os.path.exists(manager.test_file):
                with open(manager.test_file, 'r') as f:
                    content = f.read()
                    # Content should not contain plaintext
                    self.assertNotIn("secret_value", content)
    
    def test_delete_secret(self):
        """Test deleting secrets"""
        with patch.object(SecretManager, 'secret_file', new_callable=lambda: property(lambda self: self.test_file)):
            manager = SecretManager()
            manager.test_file = os.path.join(self.temp_dir, "test_secrets.json")
            
            manager.set_secret("to_delete", "value")
            manager.delete_secret("to_delete")
            
            value = manager.get_secret("to_delete")
            self.assertIsNone(value)


class TestRequestCache(unittest.TestCase):
    """Test request cache"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.cache = RequestCache(ttl_seconds=10)
    
    def test_cache_set_and_get(self):
        """Test cache storage and retrieval"""
        self.cache.set("test_prompt", "test_response")
        
        value = self.cache.get("test_prompt")
        self.assertEqual(value, "test_response")
    
    def test_cache_with_context(self):
        """Test cache with context"""
        self.cache.set("prompt", "response", context="ctx1")
        
        value = self.cache.get("prompt", context="ctx1")
        self.assertEqual(value, "response")
        
        # Different context should not match
        value = self.cache.get("prompt", context="ctx2")
        self.assertIsNone(value)
    
    def test_cache_expiration(self):
        """Test cache TTL"""
        cache = RequestCache(ttl_seconds=1)
        cache.set("key", "value")
        
        # Should exist
        self.assertIsNotNone(cache.get("key"))
        
        # Wait for expiration
        import time
        time.sleep(1.1)
        
        # Should be gone
        self.assertIsNone(cache.get("key"))
    
    def test_cache_clear(self):
        """Test clearing cache"""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        
        self.cache.clear()
        
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))


class TestRateLimiter(unittest.TestCase):
    """Test rate limiter"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.limiter = RateLimiter(max_requests=3, window_seconds=1)
    
    def test_rate_limit_allows_requests(self):
        """Test rate limiter allows requests within limit"""
        self.assertTrue(self.limiter.is_allowed())
        self.assertTrue(self.limiter.is_allowed())
        self.assertTrue(self.limiter.is_allowed())
    
    def test_rate_limit_blocks_excess(self):
        """Test rate limiter blocks excess requests"""
        # Use up limit
        for _ in range(3):
            self.limiter.is_allowed()
        
        # Next should be blocked
        self.assertFalse(self.limiter.is_allowed())
    
    def test_rate_limit_wait(self):
        """Test wait calculation"""
        wait = self.limiter.wait_if_needed()
        self.assertEqual(wait, 0.0)  # First request has no wait


class TestAIManager(unittest.TestCase):
    """Test AI Manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_settings = MagicMock()
        self.manager = AIManager(self.mock_settings)
    
    def test_manager_initialization(self):
        """Test AI Manager initializes"""
        self.assertIsNotNone(self.manager)
        self.assertIsNotNone(self.manager.cache)
        self.assertIsNotNone(self.manager.rate_limiter)
    
    def test_get_stats(self):
        """Test stats retrieval"""
        stats = self.manager.get_stats()
        
        self.assertIn("total_requests", stats)
        self.assertIn("cache_hits", stats)
        self.assertIn("cache_misses", stats)
        self.assertIn("api_calls", stats)
    
    def test_reset_stats(self):
        """Test stats reset"""
        self.manager.stats["total_requests"] = 100
        self.manager.reset_stats()
        
        self.assertEqual(self.manager.stats["total_requests"], 0)
    
    def test_clear_cache(self):
        """Test cache clearing"""
        self.manager.cache.set("key", "value")
        self.manager.clear_cache()
        
        self.assertIsNone(self.manager.cache.get("key"))
    
    @patch('ide.utils.ai_manager.OpenAIProvider.validate_key')
    def test_provider_initialization(self, mock_validate):
        """Test provider initialization"""
        mock_validate.return_value = True
        
        with patch.object(self.manager.secret_manager, 'get_secret', return_value="sk-test"):
            self.mock_settings.get.return_value = {"provider": "openai", "temperature": 0.7}
            
            result = self.manager.initialize_provider("openai")
            
            self.assertTrue(result)
            self.assertIsNotNone(self.manager.provider)


class TestOpenAIProvider(unittest.TestCase):
    """Test OpenAI provider"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.provider = OpenAIProvider(api_key="sk-test123")
    
    def test_provider_initialization(self):
        """Test provider initializes"""
        self.assertEqual(self.provider.api_key, "sk-test123")
        self.assertEqual(self.provider.model, "gpt-3.5-turbo")
    
    def test_key_validation(self):
        """Test API key validation"""
        self.assertTrue(self.provider.validate_key())
        
        invalid_provider = OpenAIProvider(api_key="invalid")
        self.assertFalse(invalid_provider.validate_key())


class TestGeminiProvider(unittest.TestCase):
    """Test Gemini provider"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.provider = GeminiProvider(api_key="AIza" + "x" * 30)
    
    def test_provider_initialization(self):
        """Test provider initializes"""
        self.assertIsNotNone(self.provider.api_key)
        self.assertEqual(self.provider.model, "gemini-pro")
    
    def test_key_validation(self):
        """Test API key validation"""
        self.assertTrue(self.provider.validate_key())
        
        invalid_provider = GeminiProvider(api_key="short")
        self.assertFalse(invalid_provider.validate_key())


class TestSettingsManager(unittest.TestCase):
    """Test settings manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.settings_file = os.path.join(self.temp_dir, "settings.json")
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_settings_initialization(self):
        """Test settings manager initializes"""
        manager = SettingsManager()
        self.assertIsNotNone(manager)
    
    def test_get_and_set(self):
        """Test get/set operations"""
        manager = SettingsManager()
        
        manager.set("test_key", "test_value")
        value = manager.get("test_key")
        
        self.assertEqual(value, "test_value")
    
    def test_ai_settings(self):
        """Test AI settings update"""
        manager = SettingsManager()
        
        manager.update_ai_settings({"temperature": 0.8})
        ai_settings = manager.get("ai", {})
        
        self.assertEqual(ai_settings.get("temperature"), 0.8)


def run_tests(verbosity=2):
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFunctionFlowAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestGraphBuilder))
    suite.addTests(loader.loadTestsFromTestCase(TestSecretManager))
    suite.addTests(loader.loadTestsFromTestCase(TestRequestCache))
    suite.addTests(loader.loadTestsFromTestCase(TestRateLimiter))
    suite.addTests(loader.loadTestsFromTestCase(TestAIManager))
    suite.addTests(loader.loadTestsFromTestCase(TestOpenAIProvider))
    suite.addTests(loader.loadTestsFromTestCase(TestGeminiProvider))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsManager))
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    # Run tests
    result = run_tests(verbosity=2)
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"{'='*70}")
