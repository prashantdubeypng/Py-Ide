#!/usr/bin/env python
"""
Test Runner
Execute all test suites with reporting and coverage
"""
import sys
import os
import unittest
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Run all tests"""
    print("=" * 80)
    print("PY-IDE TEST SUITE")
    print("=" * 80)
    
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Load unit tests
    print("\n📋 Loading unit tests...")
    try:
        unit_tests = loader.discover('tests', pattern='test_suite.py')
        suite.addTests(unit_tests)
        print("✓ Unit tests loaded")
    except Exception as e:
        print(f"✗ Failed to load unit tests: {e}")
    
    # Load integration tests
    print("\n📋 Loading integration tests...")
    try:
        integration_tests = loader.discover('tests', pattern='integration_tests.py')
        suite.addTests(integration_tests)
        print("✓ Integration tests loaded")
    except Exception as e:
        print(f"✗ Failed to load integration tests: {e}")
    
    # Run tests
    print("\n" + "=" * 80)
    print("RUNNING TESTS")
    print("=" * 80 + "\n")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    successes = total_tests - failures - errors
    
    print(f"\nTotal Tests Run:  {total_tests}")
    print(f"✓ Successes:       {successes}")
    print(f"✗ Failures:        {failures}")
    print(f"⚠️  Errors:         {errors}")
    
    success_rate = (successes / total_tests * 100) if total_tests > 0 else 0
    print(f"Success Rate:      {success_rate:.1f}%")
    
    # Print failed tests
    if failures > 0:
        print("\n" + "-" * 80)
        print("FAILED TESTS:")
        for test, traceback in result.failures:
            print(f"\n❌ {test}")
            print(traceback)
    
    # Print errors
    if errors > 0:
        print("\n" + "-" * 80)
        print("ERRORS:")
        for test, traceback in result.errors:
            print(f"\n⚠️  {test}")
            print(traceback)
    
    print("\n" + "=" * 80)
    
    # Return exit code
    return 0 if (failures == 0 and errors == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
