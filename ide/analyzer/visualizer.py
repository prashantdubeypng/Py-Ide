"""
Visualizer for Function Flow Graphs
Uses PyVis for interactive HTML-based visualization
"""
import os
import tempfile
from pathlib import Path
from typing import Optional
from pyvis.network import Network

from ide.analyzer.graph_builder import CallGraph
from ide.analyzer.security import sanitize_text


class Visualizer:
    """
    Creates interactive visualizations of function call graphs
    """
    
    def __init__(self):
        self.output_dir = Path(tempfile.gettempdir()) / "Py_ide_flow"
        self.output_dir.mkdir(exist_ok=True)
    
    def render(self, graph: CallGraph, output_filename: str = "function_flow.html") -> str:
        """
        Render graph to interactive HTML
        
        Args:
            graph: CallGraph to visualize
            output_filename: Name of output HTML file
            
        Returns:
            Path to generated HTML file
        """
        output_path = self.output_dir / output_filename
        
        # Create PyVis network
        net = Network(
            height="800px",
            width="100%",
            bgcolor="#2B2B2B",
            font_color="#A9B7C6",
            directed=True
        )
        
        # Configure physics for better layout with prominent arrows
        net.set_options("""
        {
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -80,
              "centralGravity": 0.015,
              "springLength": 150,
              "springConstant": 0.08
            },
            "maxVelocity": 50,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {"iterations": 200}
          },
          "nodes": {
            "font": {
              "size": 16,
              "color": "#A9B7C6",
              "face": "Consolas"
            },
            "borderWidth": 2,
            "borderWidthSelected": 3
          },
          "edges": {
            "arrows": {
              "to": {
                "enabled": true,
                "scaleFactor": 1.2,
                "type": "arrow"
              }
            },
            "color": {
              "inherit": false,
              "color": "#6A9FE0",
              "highlight": "#8FC34B",
              "hover": "#FFC66D"
            },
            "width": 2,
            "smooth": {
              "type": "cubicBezier",
              "forceDirection": "horizontal",
              "roundness": 0.5
            },
            "selectionWidth": 3
          },
          "interaction": {
            "hover": true,
            "navigationButtons": true,
            "keyboard": true
          }
        }
        """)
        
        # Add nodes
        for func_name, func_info in graph.nodes.items():
            # Sanitize for security
            safe_name = sanitize_text(func_name)
            safe_file = sanitize_text(os.path.basename(func_info.file))
            
            # Determine node color
            if func_info.is_async:
                color = "#6A8759"  # Green for async
            elif func_info.is_method:
                color = "#CC7832"  # Orange for methods
            else:
                color = "#9876AA"  # Purple for functions
            
            # Create tooltip
            tooltip = f"{safe_name}\\n{safe_file}:{func_info.line}"
            if func_info.is_async:
                tooltip += "\\n[async]"
            if func_info.class_name:
                tooltip += f"\\nClass: {sanitize_text(func_info.class_name)}"
            
            # Add node
            net.add_node(
                safe_name,
                label=safe_name,
                title=tooltip,
                color=color,
                size=20 + len(graph.get_callers(func_name)) * 5  # Size by popularity
            )
        
        # Add edges
        for from_func, to_funcs in graph.edges.items():
            safe_from = sanitize_text(from_func)
            for to_func in to_funcs:
                safe_to = sanitize_text(to_func)
                # Only add edge if both nodes exist
                if safe_to in [sanitize_text(n) for n in graph.nodes.keys()]:
                    net.add_edge(safe_from, safe_to)
        
        # Generate HTML
        net.save_graph(str(output_path))
        
        # Add custom styles
        self._enhance_html(output_path)
        
        print(f"Visualization saved to: {output_path}")
        return str(output_path)
    
    def _enhance_html(self, html_path: Path):
        """Add custom CSS and JavaScript to generated HTML"""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html = f.read()
            
            # Add custom styles
            custom_css = """
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    background-color: #2B2B2B;
                    font-family: 'Consolas', monospace;
                }
                #info-panel {
                    position: fixed;
                    top: 10px;
                    left: 10px;
                    background-color: #3C3F41;
                    color: #A9B7C6;
                    padding: 15px;
                    border-radius: 5px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.5);
                    z-index: 1000;
                    max-width: 300px;
                }
                #info-panel h3 {
                    margin: 0 0 10px 0;
                    color: #6A8759;
                }
                #info-panel p {
                    margin: 5px 0;
                    font-size: 12px;
                }
                .legend {
                    position: fixed;
                    bottom: 10px;
                    right: 10px;
                    background-color: #3C3F41;
                    color: #A9B7C6;
                    padding: 15px;
                    border-radius: 5px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.5);
                    z-index: 1000;
                }
                .legend-item {
                    display: flex;
                    align-items: center;
                    margin: 5px 0;
                }
                .legend-color {
                    width: 20px;
                    height: 20px;
                    border-radius: 50%;
                    margin-right: 10px;
                }
            </style>
            """
            
            info_panel = """
            <div id="info-panel">
                <h3>Function Flow Graph</h3>
                <p>🔵 Hover over nodes for details</p>
                <p>📌 Click and drag to move</p>
                <p>🔍 Scroll to zoom</p>
            </div>
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #9876AA;"></div>
                    <span>Function</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #CC7832;"></div>
                    <span>Method</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #6A8759;"></div>
                    <span>Async</span>
                </div>
            </div>
            """
            
            # Insert custom elements
            html = html.replace('<body>', '<body>' + info_panel)
            html = html.replace('</head>', custom_css + '</head>')
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
                
        except Exception as e:
            print(f"Error enhancing HTML: {e}")
    
    def render_subgraph(
        self, 
        graph: CallGraph, 
        root_functions: list, 
        max_depth: int = 2,
        output_filename: str = "subgraph.html"
    ) -> str:
        """
        Render a subgraph starting from specific functions
        
        Args:
            graph: Full call graph
            root_functions: Starting functions
            max_depth: Maximum depth to explore
            output_filename: Output file name
            
        Returns:
            Path to HTML file
        """
        subgraph = graph.get_subgraph(root_functions, max_depth)
        return self.render(subgraph, output_filename)
    
    def render_with_stats(self, graph: CallGraph, output_filename: str = "flow_with_stats.html") -> str:
        """
        Render graph with statistics panel
        
        Args:
            graph: CallGraph to visualize
            output_filename: Output file name
            
        Returns:
            Path to HTML file
        """
        # Generate base visualization
        html_path = self.render(graph, output_filename)
        
        # Get statistics
        stats = graph.get_stats()
        
        # Create stats HTML
        stats_html = f"""
        <div id="stats-panel" style="
            position: fixed;
            top: 10px;
            right: 10px;
            background-color: #3C3F41;
            color: #A9B7C6;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.5);
            z-index: 1000;
            min-width: 200px;
        ">
            <h3 style="margin: 0 0 10px 0; color: #6A8759;">Statistics</h3>
            <p><strong>Functions:</strong> {stats['total_functions']}</p>
            <p><strong>Calls:</strong> {stats['total_calls']}</p>
            <p><strong>Async Functions:</strong> {stats['async_functions']}</p>
            <p><strong>Isolated:</strong> {stats['isolated_functions']}</p>
            <p><strong>Avg Calls/Function:</strong> {stats['average_calls_per_function']:.2f}</p>
        </div>
        """
        
        # Add stats to HTML
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html = f.read()
            
            html = html.replace('<body>', '<body>' + stats_html)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
        except Exception as e:
            print(f"Error adding stats: {e}")
        
        return html_path
