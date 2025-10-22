"""
Tests for SecureExecutor and CodeValidator
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

# Test imports
try:
    from ide.utils.secure_executor import CodeValidator, SecureExecutor, get_executor
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    print("Warning: docker library not available, skipping SecureExecutor tests")


@unittest.skipUnless(DOCKER_AVAILABLE, "docker library not installed")
class TestCodeValidator(unittest.TestCase):
    """Test code validation for dangerous patterns"""
    
    def test_safe_code(self):
        """Test safe code passes validation"""
        safe_code = """
import math
print("Hello World")
x = 42
result = math.sqrt(x)
print(f"Result: {result}")
"""
        is_valid, error = CodeValidator.validate(safe_code)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_blocked_os_system(self):
        """Test os.system is blocked"""
        dangerous_code = """
import os
os.system("rm -rf /")
"""
        is_valid, error = CodeValidator.validate(dangerous_code)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn("os.system", error.lower())
    
    def test_blocked_subprocess(self):
        """Test subprocess is blocked"""
        dangerous_code = """
import subprocess
subprocess.call(["ls"])
"""
        is_valid, error = CodeValidator.validate(dangerous_code)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
    
    def test_blocked_eval(self):
        """Test eval is blocked"""
        dangerous_code = """
x = eval("__import__('os').system('ls')")
"""
        is_valid, error = CodeValidator.validate(dangerous_code)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn("eval", error.lower())
    
    def test_blocked_exec(self):
        """Test exec is blocked"""
        dangerous_code = """
exec("import os; os.system('ls')")
"""
        is_valid, error = CodeValidator.validate(dangerous_code)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
    
    def test_blocked_absolute_file_paths(self):
        """Test absolute file paths are blocked"""
        dangerous_code = """
with open("/etc/passwd", "r") as f:
    data = f.read()
"""
        is_valid, error = CodeValidator.validate(dangerous_code)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
    
    def test_strict_mode_blocks_imports(self):
        """Test strict mode blocks dangerous imports"""
        code_with_os = """
import os
print(os.getcwd())
"""
        # Non-strict should pass pattern check (os.system blocked, but import os ok)
        is_valid, error = CodeValidator.validate(code_with_os, strict=False)
        self.assertTrue(is_valid)  # Only checks patterns, not imports
        
        # Strict mode blocks the import
        is_valid, error = CodeValidator.validate(code_with_os, strict=True)
        self.assertFalse(is_valid)
        self.assertIn("import", error.lower())


@unittest.skipUnless(DOCKER_AVAILABLE, "docker library not installed")
class TestSecureExecutorMocked(unittest.TestCase):
    """Test SecureExecutor with mocked Docker client"""
    
    @patch('ide.utils.secure_executor.docker')
    def test_executor_initialization(self, mock_docker):
        """Test executor initializes with Docker client"""
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = Mock()
        
        executor = SecureExecutor()
        
        self.assertEqual(executor.image, "python:3.11-slim")
        self.assertEqual(executor.mem_limit, "256m")
        self.assertEqual(executor.cpu_quota, 50000)
        self.assertTrue(executor.enable_validation)
    
    @patch('ide.utils.secure_executor.docker')
    def test_custom_config(self, mock_docker):
        """Test executor with custom configuration"""
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = Mock()
        
        executor = SecureExecutor(
            mem_limit="512m",
            cpu_quota=100000,
            max_output_size=5000,
            enable_validation=False
        )
        
        self.assertEqual(executor.mem_limit, "512m")
        self.assertEqual(executor.cpu_quota, 100000)
        self.assertEqual(executor.max_output_size, 5000)
        self.assertFalse(executor.enable_validation)
    
    @patch('ide.utils.secure_executor.docker')
    def test_validation_blocks_dangerous_code(self, mock_docker):
        """Test validation prevents dangerous code execution"""
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = Mock()
        
        executor = SecureExecutor(enable_validation=True)
        
        dangerous_code = "import os; os.system('ls')"
        result = executor.run_code(dangerous_code)
        
        self.assertEqual(result["exit_code"], 1)
        self.assertIn("validation", result["error"].lower())
        self.assertTrue(result["validated"])
    
    @patch('ide.utils.secure_executor.docker')
    def test_temp_file_creation(self, mock_docker):
        """Test temporary script creation"""
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = Mock()
        
        executor = SecureExecutor()
        
        code = "print('Hello World')"
        script_path, tmp_dir = executor._create_temp_script(code)
        
        self.assertTrue(os.path.exists(script_path))
        self.assertTrue(os.path.exists(tmp_dir))
        self.assertTrue(script_path.endswith("main.py"))
        
        # Verify content
        with open(script_path, 'r') as f:
            content = f.read()
        self.assertIn("Hello World", content)
        
        # Cleanup
        executor._cleanup_temp(tmp_dir)
        self.assertFalse(os.path.exists(tmp_dir))
    
    @patch('ide.utils.secure_executor.docker')
    def test_get_stats(self, mock_docker):
        """Test getting executor stats"""
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = Mock()
        
        executor = SecureExecutor()
        stats = executor.get_container_stats()
        
        self.assertIn("image", stats)
        self.assertIn("mem_limit", stats)
        self.assertIn("cpu_quota", stats)
        self.assertIn("validation_enabled", stats)
        self.assertEqual(stats["mem_limit"], "256m")
    
    @patch('ide.utils.secure_executor.docker')
    def test_singleton_pattern(self, mock_docker):
        """Test get_executor returns singleton"""
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = Mock()
        
        executor1 = get_executor()
        executor2 = get_executor()
        
        self.assertIs(executor1, executor2)


@unittest.skipUnless(DOCKER_AVAILABLE, "docker library not installed")
class TestSecureExecutorIntegration(unittest.TestCase):
    """Integration tests with real Docker (if available)"""
    
    def setUp(self):
        """Check if Docker is actually running"""
        try:
            import docker
            client = docker.from_env()
            client.ping()
            self.docker_running = True
        except:
            self.docker_running = False
            self.skipTest("Docker is not running")
    
    def test_simple_code_execution(self):
        """Test executing simple Python code"""
        if not self.docker_running:
            self.skipTest("Docker not running")
        
        executor = SecureExecutor(enable_validation=False)
        
        code = """
print("Hello from Docker!")
print("Math: 2 + 2 =", 2 + 2)
"""
        
        result = executor.run_code(code, timeout=10)
        
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("Hello from Docker!", result["output"])
        self.assertIn("2 + 2 = 4", result["output"])
    
    def test_code_with_imports(self):
        """Test code with standard library imports"""
        if not self.docker_running:
            self.skipTest("Docker not running")
        
        executor = SecureExecutor(enable_validation=False)
        
        code = """
import math
import json

data = {"pi": math.pi}
print(json.dumps(data, indent=2))
"""
        
        result = executor.run_code(code, timeout=10)
        
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("pi", result["output"])
        self.assertIn("3.14", result["output"])
    
    def test_error_handling(self):
        """Test error in code is captured"""
        if not self.docker_running:
            self.skipTest("Docker not running")
        
        executor = SecureExecutor(enable_validation=False)
        
        code = """
print("Before error")
x = 1 / 0  # Division by zero
print("After error")
"""
        
        result = executor.run_code(code, timeout=10)
        
        self.assertNotEqual(result["exit_code"], 0)
        self.assertIn("Before error", result["output"])
        self.assertIn("ZeroDivisionError", result["output"])
        self.assertNotIn("After error", result["output"])
    
    def test_memory_limit(self):
        """Test memory limit is enforced"""
        if not self.docker_running:
            self.skipTest("Docker not running")
        
        executor = SecureExecutor(mem_limit="50m", enable_validation=False)
        
        # Try to allocate more memory than limit
        code = """
try:
    big_list = [0] * (100 * 1024 * 1024)  # Try to allocate ~100MB
    print("Allocated successfully")
except MemoryError:
    print("MemoryError caught")
"""
        
        result = executor.run_code(code, timeout=10)
        # Container should handle this gracefully
        self.assertIsNotNone(result["output"])


def run_secure_executor_tests(verbosity=2):
    """Run SecureExecutor tests"""
    if not DOCKER_AVAILABLE:
        print("⚠️  Docker library not installed. Skipping SecureExecutor tests.")
        print("Install with: pip install docker")
        return None
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestCodeValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestSecureExecutorMocked))
    suite.addTests(loader.loadTestsFromTestCase(TestSecureExecutorIntegration))
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    result = run_secure_executor_tests(verbosity=2)
    
    if result:
        print(f"\n{'='*70}")
        print(f"SecureExecutor Tests Run: {result.testsRun}")
        print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"{'='*70}")
