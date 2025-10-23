"""
Wrapper script to run Python code with live tracing
This is executed as a subprocess by the IDE
"""
import sys
import argparse
import queue
import json
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add IDE path to import runtime_tracer
import os
ide_path = Path(__file__).parent.parent
sys.path.insert(0, str(ide_path))

from ide.runtime_tracer import LiveTracer


def run_with_trace(script_path: str, output_trace: str = None):
    """
    Run a Python script with live tracing enabled
    
    Args:
        script_path: Path to Python script to execute
        output_trace: Path to save trace JSON (optional)
    """
    # Create tracer
    event_queue = queue.Queue()
    tracer = LiveTracer(event_queue)
    
    # Start tracing
    tracer.start()
    
    try:
        # Run the script
        import runpy
        runpy.run_path(script_path, run_name="__main__")
        
    except Exception as e:
        print(f"Error running script: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        
    finally:
        # Stop tracing
        tracer.stop()
        
        # Save trace if output path provided
        if output_trace:
            tracer.save_trace(output_trace)
            try:
                print(f"\n📊 Trace saved to: {output_trace}")
            except UnicodeEncodeError:
                print(f"\n[Trace] Saved to: {output_trace}")
        
        # Print statistics
        stats = tracer.get_stats()
        if stats:
            try:
                print("\n📈 Function Call Statistics:")
            except UnicodeEncodeError:
                print("\n[Stats] Function Call Statistics:")
            print(f"{'Function':<30} {'Calls':<8} {'Total(s)':<10} {'Avg(ms)':<10}")
            print("-" * 60)
            
            for func_name, data in sorted(stats.items(), key=lambda x: x[1]['call_count'], reverse=True)[:20]:
                avg_time = (data['total_time'] / data['call_count']) * 1000
                print(f"{func_name:<30} {data['call_count']:<8} {data['total_time']:<10.3f} {avg_time:<10.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Python script with live tracing")
    parser.add_argument("script", help="Path to Python script to run")
    parser.add_argument("--output", "-o", help="Path to save trace JSON", default=None)
    
    args = parser.parse_args()
    
    run_with_trace(args.script, args.output)
