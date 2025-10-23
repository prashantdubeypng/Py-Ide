"""
Test script to generate trace visualization
Run this to see the complete trace visualization in your browser
"""
import json
import os
import sys

# Add IDE path
sys.path.insert(0, os.path.dirname(__file__))

from ide.analyzer.flow_analyzer import FunctionFlowAnalyzer
from ide.analyzer.graph_builder import GraphBuilder
from ide.analyzer.visualizer import Visualizer


def main():
    print("🔍 Generating Trace Visualization")
    print("=" * 60)
    
    # 1. Load trace data
    trace_file = "demo_trace.json"
    if not os.path.exists(trace_file):
        print(f"❌ Trace file not found: {trace_file}")
        print("Run this first: python ide\\traced_runner.py test_trace_demo.py --output demo_trace.json")
        return
    
    print(f"📂 Loading trace: {trace_file}")
    with open(trace_file, 'r') as f:
        trace_data = json.load(f)
    
    events = trace_data.get('events', [])
    stats = trace_data.get('stats', {})
    
    print(f"✓ Loaded {len(events)} events")
    print(f"✓ Found {len(stats)} function statistics")
    
    # 2. Analyze the traced file
    print("\n📊 Analyzing code structure...")
    analyzer = FunctionFlowAnalyzer()
    
    # Analyze the current directory
    project_dir = os.path.dirname(__file__) or "."
    functions = analyzer.analyze_project(project_dir)
    
    print(f"✓ Analyzed {len(functions)} functions")
    
    # 3. Build call graph
    print("\n🔗 Building call graph...")
    builder = GraphBuilder()
    graph = builder.build_from_functions(functions)
    
    graph_stats = graph.get_stats()
    print(f"✓ Built graph with {graph_stats['total_functions']} nodes and {graph_stats['total_calls']} edges")
    
    # 4. Create visualization with trace overlay
    print("\n🎨 Creating interactive visualization...")
    visualizer = Visualizer()
    html_path = visualizer.render_with_trace_overlay(
        graph,
        trace_data,
        output_filename="demo_traced_flow.html"
    )
    
    print(f"\n✅ SUCCESS!")
    print(f"📂 Visualization saved to: {html_path}")
    print("\n" + "=" * 60)
    print("🌐 Opening in browser...")
    
    # 5. Open in browser
    import webbrowser
    webbrowser.open(f"file:///{html_path.replace(os.sep, '/')}")
    
    print("\n💡 What to look for:")
    print("  • 🟢 Green nodes = Fast functions")
    print("  • 🟠 Orange nodes = Medium performance")
    print("  • 🔴 Red nodes = SLOW - Optimize these!")
    print("  • ⚫ Gray nodes = Not executed")
    print("\n  Hover over nodes to see execution details!")
    print("=" * 60)


if __name__ == "__main__":
    main()
