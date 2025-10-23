"""
Demo script to test live runtime tracing
Shows nested function calls and timing
"""
import time
import math


def calculate_fibonacci(n):
    """Calculate fibonacci number recursively"""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)


def process_data(items):
    """Process a list of items"""
    results = []
    for item in items:
        result = transform_item(item)
        results.append(result)
    return results


def transform_item(value):
    """Transform a single item"""
    # Simulate some processing
    time.sleep(0.01)
    return value ** 2


def analyze_numbers(numbers):
    """Analyze a list of numbers"""
    total = sum(numbers)
    avg = total / len(numbers)
    std_dev = calculate_std_dev(numbers, avg)
    return {
        'total': total,
        'average': avg,
        'std_dev': std_dev
    }


def calculate_std_dev(numbers, mean):
    """Calculate standard deviation"""
    variance = sum((x - mean) ** 2 for x in numbers) / len(numbers)
    return math.sqrt(variance)


def main():
    """Main entry point"""
    print("🔍 Live Tracing Demo")
    print("=" * 50)
    
    # Test 1: Recursive calls
    print("\n1. Testing Fibonacci (recursive)...")
    fib_result = calculate_fibonacci(8)
    print(f"   Fibonacci(8) = {fib_result}")
    
    # Test 2: List processing
    print("\n2. Testing data processing...")
    data = [1, 2, 3, 4, 5]
    processed = process_data(data)
    print(f"   Processed: {processed}")
    
    # Test 3: Statistical analysis
    print("\n3. Testing number analysis...")
    numbers = [10, 20, 30, 40, 50]
    stats = analyze_numbers(numbers)
    print(f"   Statistics: {stats}")
    
    print("\n" + "=" * 50)
    print("✓ Demo completed!")


if __name__ == "__main__":
    main()
