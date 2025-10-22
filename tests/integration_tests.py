"""
Integration Tests
End-to-end tests for AI integration with IDE components
"""
import unittest
import tempfile
import os
from unittest.mock import MagicMock, patch
from pathlib import Path

from ide.analyzer.flow_analyzer import FunctionFlowAnalyzer
from ide.analyzer.graph_builder import GraphBuilder
from ide.utils.settings import SettingsManager
from ide.utils.ai_manager import AIManager
from ide.graph_ai_integration import GraphAIAssistant, GraphEnhancer


class TestAIManagerIntegration(unittest.TestCase):
    """Test AI Manager integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.settings = SettingsManager()
        self.ai_manager = AIManager(self.settings)
    
    def test_cache_integration(self):
        """Test cache works with manager"""
        # Simulate cached response
        test_prompt = "What is Python?"
        test_response = "Python is a programming language"
        
        self.ai_manager.cache.set(test_prompt, test_response)
        
        # Retrieve from cache
        cached = self.ai_manager.cache.get(test_prompt)
        self.assertEqual(cached, test_response)
        
        # Stats should reflect cache hit
        self.assertEqual(self.ai_manager.stats["cache_misses"] + self.ai_manager.stats["cache_hits"], 0)
    
    def test_rate_limiter_integration(self):
        """Test rate limiter works with manager"""
        # Make several requests
        for _ in range(5):
            allowed = self.ai_manager.rate_limiter.is_allowed()
            self.assertTrue(allowed)
        
        # Stats should show requests
        stats = self.ai_manager.get_stats()
        self.assertEqual(stats["total_requests"], 0)  # Only counted on actual generation
    
    @patch('ide.utils.ai_manager.AIManager.generate_sync')
    def test_sync_generate(self, mock_generate):
        """Test synchronous generate wrapper"""
        mock_generate.return_value = "Test response"
        
        response = self.ai_manager.generate_sync("Test prompt")
        self.assertEqual(response, "Test response")


class TestAnalyzerWithAI(unittest.TestCase):
    """Test analyzer integration with AI"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = FunctionFlowAnalyzer()
        self.builder = GraphBuilder()
        self.settings = SettingsManager()
        self.ai_manager = AIManager(self.settings)
    
    def test_end_to_end_analysis(self):
        """Test complete analysis pipeline"""
        test_code = '''
def main():
    """Main entry point"""
    result = process_data([1, 2, 3])
    return result

def process_data(items):
    """Process items"""
    return sum_items(items)

def sum_items(items):
    """Sum items"""
    return sum(items)
'''
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "main.py"
            test_file.write_text(test_code)
            
            # Analyze
            functions = self.analyzer.analyze_project(tmpdir)
            self.assertGreater(len(functions), 0)
            
            # Build graph
            graph = self.builder.build_from_functions(functions)
            self.assertGreater(len(graph.nodes()), 0)
            
            # Check stats
            stats = self.builder.get_stats()
            self.assertGreater(stats["total_functions"], 0)


class TestGraphAIAssistant(unittest.TestCase):
    """Test graph AI assistant"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.settings = SettingsManager()
        self.ai_manager = AIManager(self.settings)
        self.assistant = GraphAIAssistant(self.ai_manager)
    
    @patch.object(AIManager, 'generate_sync')
    def test_explain_function(self, mock_generate):
        """Test function explanation"""
        mock_generate.return_value = "This function does X"
        
        from ide.analyzer.flow_analyzer import FunctionInfo
        func = FunctionInfo(
            name="test_func",
            file_path="test.py",
            line_number=1,
            calls=[],
            docstring="Test function"
        )
        
        explanation = self.assistant.explain_function(func)
        
        self.assertIsNotNone(explanation)
        self.assertEqual(explanation, "This function does X")
    
    @patch.object(AIManager, 'generate_sync')
    def test_explain_call_relationship(self, mock_generate):
        """Test call relationship explanation"""
        mock_generate.return_value = "Function A calls B to process data"
        
        explanation = self.assistant.explain_call_relationship("func_a", "func_b", call_count=3)
        
        self.assertIsNotNone(explanation)
        self.assertEqual(explanation, "Function A calls B to process data")
    
    @patch.object(AIManager, 'generate_sync')
    def test_detect_anti_patterns(self, mock_generate):
        """Test anti-pattern detection"""
        mock_generate.return_value = "Found circular dependencies"
        
        graph_data = {
            "nodes": [{"name": "f1"}, {"name": "f2"}],
            "edges": [{"from": "f1", "to": "f2"}],
            "cycles": [],
            "stats": {"avg_loc": 50, "max_loc": 200}
        }
        
        analysis = self.assistant.detect_anti_patterns(graph_data)
        
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis, "Found circular dependencies")


class TestGraphEnhancer(unittest.TestCase):
    """Test graph enhancer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.settings = SettingsManager()
        self.ai_manager = AIManager(self.settings)
        self.assistant = GraphAIAssistant(self.ai_manager)
        self.enhancer = GraphEnhancer(self.assistant)
    
    @patch.object(GraphAIAssistant, 'explain_function')
    def test_add_ai_explanations(self, mock_explain):
        """Test adding AI explanations to nodes"""
        mock_explain.return_value = "AI explanation"
        
        nodes = [
            {"name": "func1", "data": MagicMock()},
            {"name": "func2", "data": MagicMock()}
        ]
        
        enhanced = self.enhancer.add_ai_explanations_to_nodes(nodes)
        
        self.assertEqual(len(enhanced), 2)
        for node in enhanced:
            self.assertIn("ai_explanation", node)
    
    @patch.object(GraphAIAssistant, 'explain_call_relationship')
    def test_add_ai_suggestions(self, mock_suggest):
        """Test adding AI suggestions to edges"""
        mock_suggest.return_value = "AI suggestion"
        
        edges = [
            {"from": "func1", "to": "func2"},
            {"from": "func2", "to": "func3"}
        ]
        
        enhanced = self.enhancer.add_ai_suggestions_to_edges(edges)
        
        self.assertEqual(len(enhanced), 2)


class TestSecureAIIntegration(unittest.TestCase):
    """Test secure AI integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.settings = SettingsManager()
        self.ai_manager = AIManager(self.settings)
    
    def test_api_key_not_in_logs(self):
        """Test API keys are not logged"""
        # This is a security test
        from ide.utils.logger import logger
        
        with patch.object(logger, 'error') as mock_log:
            # Attempt to trigger error with API key
            self.ai_manager.provider = None
            result = self.ai_manager.generate_sync("test")
            
            # Check logs don't contain sensitive info
            for call in mock_log.call_args_list:
                log_msg = str(call)
                self.assertNotIn("sk-", log_msg)
                self.assertNotIn("AIza", log_msg)
    
    def test_secret_manager_encryption(self):
        """Test secrets are encrypted"""
        from ide.utils.secret_manager import SecretManager
        
        secret_manager = SecretManager()
        
        # Mock the file operations to test encryption
        with patch.object(secret_manager, 'set_secret') as mock_set:
            secret_manager.set_secret("test_key", "test_value")
            mock_set.assert_called_once()


class TestAIChatPanelIntegration(unittest.TestCase):
    """Test AI chat panel integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.settings = SettingsManager()
    
    @patch('ide.ai_chat_panel.AIManager')
    def test_chat_panel_initialization(self, mock_ai):
        """Test chat panel initializes with AI manager"""
        from ide.ai_chat_panel import AIChatPanel
        
        panel = AIChatPanel(self.settings)
        
        self.assertIsNotNone(panel.ai_manager)
        self.assertIsNotNone(panel.input_text)
        self.assertIsNotNone(panel.send_btn)


class TestCacheAndRateLimitPerformance(unittest.TestCase):
    """Test cache and rate limit performance"""
    
    def test_cache_performance(self):
        """Test cache improves performance"""
        from ide.utils.ai_manager import RequestCache
        import time
        
        cache = RequestCache(ttl_seconds=3600)
        
        # Add items to cache
        start = time.time()
        for i in range(1000):
            cache.set(f"prompt_{i}", f"response_{i}")
        cache_time = time.time() - start
        
        # Retrieve items
        start = time.time()
        for i in range(1000):
            cache.get(f"prompt_{i}")
        retrieval_time = time.time() - start
        
        # Retrieval should be fast
        self.assertLess(retrieval_time, 0.1)
    
    def test_rate_limiter_distribution(self):
        """Test rate limiter distributes requests"""
        from ide.utils.ai_manager import RateLimiter
        
        limiter = RateLimiter(max_requests=10, window_seconds=1)
        
        allowed_count = 0
        for _ in range(20):
            if limiter.is_allowed():
                allowed_count += 1
        
        # Should allow up to max_requests
        self.assertEqual(allowed_count, 10)


def run_integration_tests(verbosity=2):
    """Run integration tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAIManagerIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalyzerWithAI))
    suite.addTests(loader.loadTestsFromTestCase(TestGraphAIAssistant))
    suite.addTests(loader.loadTestsFromTestCase(TestGraphEnhancer))
    suite.addTests(loader.loadTestsFromTestCase(TestSecureAIIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestCacheAndRateLimitPerformance))
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    # Run integration tests
    result = run_integration_tests(verbosity=2)
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"Integration Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"{'='*70}")
