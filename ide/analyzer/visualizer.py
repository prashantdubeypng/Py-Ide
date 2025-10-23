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
            
            # Prepare additional metadata
            signature = sanitize_text(func_info.signature or "()")
            doc_preview = sanitize_text((func_info.docstring or "").strip().replace('\n', ' '))
            if len(doc_preview) > 200:
                doc_preview = doc_preview[:200] + "..."
            loc = func_info.loc or 0
            callers = len(graph.get_callers(func_name))
            callees = len(graph.get_callees(func_name))
            code_preview = sanitize_text((func_info.source or "").strip())
            if len(code_preview) > 400:
                code_preview = code_preview[:400] + "\n..."
            code_preview = code_preview.replace('\n', '<br>')

            async_badge = "<span style='color:#6A8759;'>async</span>" if func_info.is_async else ""
            class_line = (
                f"<span style='color:#808080;'>Class:</span> {sanitize_text(func_info.class_name)}<br>"
                if func_info.class_name else ""
            )
            tooltip = (
                f"<div style='font-family:Consolas,monospace;font-size:12px;color:#A9B7C6;'>"
                f"<strong style='color:#6A8759;'>{safe_name}{signature}</strong> {async_badge}<br>"
                f"<span style='color:#808080;'>File:</span> {safe_file}:{func_info.line}<br>"
                f"{class_line}"
                f"<span style='color:#808080;'>Lines:</span> {loc} | "
                f"<span style='color:#808080;'>Calls:</span> {callees} | "
                f"<span style='color:#808080;'>Called by:</span> {callers}<br>"
                f"<span style='color:#808080;'>Docstring:</span> {doc_preview or '—'}<br>"
                f"<hr style='border:1px solid #3C3F41;'>"
                f"<div style='max-height:140px;overflow:auto;background:#2B2B2B;padding:6px;border-radius:4px;'>"
                f"<code>{code_preview or 'No source snippet available.'}</code>"
                f"</div>"
                f"</div>"
            )
            
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
    
    def render_with_ai_explanations(self, graph: CallGraph, ai_explanations: dict, output_filename: str = "function_flow.html") -> str:
        """
        Render graph with AI-powered explanations for nodes
        
        Args:
            graph: CallGraph to visualize
            ai_explanations: Dictionary mapping function names to AI explanations
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
        
        # Configure physics
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
        
        # Store AI explanations for JavaScript access
        explanations_js = {}
        
        # Add nodes
        for func_name, func_info in graph.nodes.items():
            safe_name = sanitize_text(func_name)
            safe_file = sanitize_text(os.path.basename(func_info.file))
            
            # Determine node color
            if func_info.is_async:
                color = "#6A8759"
            elif func_info.is_method:
                color = "#CC7832"
            else:
                color = "#9876AA"
            
            # Build clean tooltip (without AI explanation to avoid HTML rendering issues)
            signature = sanitize_text(func_info.signature or "()")
            doc_preview = sanitize_text((func_info.docstring or "").strip().replace('\n', ' '))
            if len(doc_preview) > 150:
                doc_preview = doc_preview[:150] + "..."
            
            loc = func_info.loc or 0
            callers = len(graph.get_callers(func_name))
            callees = len(graph.get_callees(func_name))
            
            # Store AI explanation for modal
            ai_explanation = ai_explanations.get(func_name, "")
            if ai_explanation:
                explanations_js[safe_name] = ai_explanation
            
            async_badge = "<span style='color:#6A8759;'>async</span>" if func_info.is_async else ""
            class_line = (
                f"<span style='color:#808080;'>Class:</span> {sanitize_text(func_info.class_name)}<br>"
                if func_info.class_name else ""
            )
            
            # Show AI indicator in tooltip if explanation exists
            ai_indicator = ""
            if ai_explanation:
                ai_indicator = "<br><div style='margin-top:6px;padding:6px;background:#1E1E1E;border-left:3px solid #6A8759;border-radius:3px;'><small style='color:#6A8759;'>🤖 AI Explanation Available - Click to view</small></div>"
            
            tooltip = (
                f"<div style='font-family:Consolas,monospace;font-size:12px;color:#A9B7C6;'>"
                f"<strong style='color:#6A8759;'>{safe_name}{signature}</strong> {async_badge}<br>"
                f"<span style='color:#808080;'>File:</span> {safe_file}:{func_info.line}<br>"
                f"{class_line}"
                f"<span style='color:#808080;'>Lines:</span> {loc} | "
                f"<span style='color:#808080;'>Calls:</span> {callees} | "
                f"<span style='color:#808080;'>Called by:</span> {callers}<br>"
                f"<span style='color:#808080;'>Docstring:</span> {doc_preview or '—'}"
                f"{ai_indicator}"
                f"</div>"
            )
            
            net.add_node(
                safe_name,
                label=safe_name,
                title=tooltip,
                color=color,
                size=20 + len(graph.get_callers(func_name)) * 5
            )
        
        # Add edges
        for from_func, to_funcs in graph.edges.items():
            safe_from = sanitize_text(from_func)
            for to_func in to_funcs:
                safe_to = sanitize_text(to_func)
                if safe_to in [sanitize_text(n) for n in graph.nodes.keys()]:
                    net.add_edge(safe_from, safe_to)
        
        # Generate HTML
        net.save_graph(str(output_path))
        
        # Enhance HTML with click handlers and AI modal
        self._add_ai_modal(output_path, explanations_js, graph)
        
        print(f"AI-enhanced visualization saved to: {output_path}")
        return str(output_path)
    
    def _add_ai_modal(self, html_path: Path, explanations: dict, graph: CallGraph):
        """Add modal dialog for AI explanations on node click"""
        try:
            import json
            
            with open(html_path, 'r', encoding='utf-8') as f:
                html = f.read()
            
            # Properly encode explanations as JSON
            explanations_json = json.dumps(explanations)
            
            modal_html = f"""
            <style>
                #ai-modal {{
                    display: none;
                    position: fixed;
                    z-index: 10000;
                    left: 50%;
                    top: 50%;
                    transform: translate(-50%, -50%);
                    background: linear-gradient(135deg, #2B2B2B 0%, #1E1E1E 100%);
                    border: 2px solid #6A8759;
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.9), 0 0 20px rgba(106,143,89,0.3);
                    width: 700px;
                    max-width: 90vw;
                    max-height: 80vh;
                    overflow: hidden;
                }}
                #ai-modal-content {{
                    padding: 25px;
                    color: #A9B7C6;
                    font-family: 'Segoe UI', 'Consolas', monospace;
                    max-height: 80vh;
                    overflow-y: auto;
                }}
                #ai-modal-content::-webkit-scrollbar {{
                    width: 10px;
                }}
                #ai-modal-content::-webkit-scrollbar-track {{
                    background: #1E1E1E;
                    border-radius: 5px;
                }}
                #ai-modal-content::-webkit-scrollbar-thumb {{
                    background: #6A8759;
                    border-radius: 5px;
                }}
                #ai-modal-content::-webkit-scrollbar-thumb:hover {{
                    background: #8FC34B;
                }}
                #ai-modal-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    padding-bottom: 15px;
                    border-bottom: 2px solid #3C3F41;
                }}
                #ai-modal-header h2 {{
                    margin: 0;
                    color: #6A8759;
                    font-size: 20px;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                #ai-modal-close {{
                    background: #3C3F41;
                    border: none;
                    color: #CC7832;
                    font-size: 24px;
                    cursor: pointer;
                    width: 35px;
                    height: 35px;
                    border-radius: 50%;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                #ai-modal-close:hover {{
                    background: #FF6B6B;
                    color: #FFFFFF;
                    transform: rotate(90deg);
                }}
                #ai-modal-body {{
                    line-height: 1.8;
                    font-size: 14px;
                }}
                #ai-modal-overlay {{
                    display: none;
                    position: fixed;
                    z-index: 9999;
                    left: 0;
                    top: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0,0,0,0.85);
                    backdrop-filter: blur(3px);
                }}
                @keyframes slideIn {{
                    from {{
                        opacity: 0;
                        transform: translate(-50%, -60%);
                    }}
                    to {{
                        opacity: 1;
                        transform: translate(-50%, -50%);
                    }}
                }}
                #ai-modal.show {{
                    animation: slideIn 0.3s ease-out;
                }}
            </style>
            
            <div id="ai-modal-overlay"></div>
            <div id="ai-modal">
                <div id="ai-modal-content">
                    <div id="ai-modal-header">
                        <h2>🤖 AI Function Explanation</h2>
                        <button id="ai-modal-close">×</button>
                    </div>
                    <div id="ai-modal-body"></div>
                </div>
            </div>
            
            <script>
                const aiExplanations = {explanations_json};
                const modal = document.getElementById('ai-modal');
                const overlay = document.getElementById('ai-modal-overlay');
                const modalBody = document.getElementById('ai-modal-body');
                const closeBtn = document.getElementById('ai-modal-close');
                
                // Show modal with animation
                function showModal() {{
                    overlay.style.display = 'block';
                    modal.style.display = 'block';
                    modal.classList.add('show');
                }}
                
                // Close modal
                function closeModal() {{
                    modal.classList.remove('show');
                    setTimeout(() => {{
                        modal.style.display = 'none';
                        overlay.style.display = 'none';
                    }}, 100);
                }}
                
                closeBtn.onclick = closeModal;
                overlay.onclick = closeModal;
                
                // Handle node clicks
                network.on("click", function(params) {{
                    if (params.nodes.length > 0) {{
                        const nodeId = params.nodes[0];
                        const explanation = aiExplanations[nodeId];
                        
                        if (explanation) {{
                            // Escape HTML and format nicely
                            const escapeHtml = (text) => {{
                                const div = document.createElement('div');
                                div.textContent = text;
                                return div.innerHTML;
                            }};
                            
                            const formattedExplanation = escapeHtml(explanation)
                                .replace(/\\n\\n/g, '<br><br>')
                                .replace(/\\n/g, '<br>');
                            
                            modalBody.innerHTML = `
                                <div style="background:#1E1E1E;padding:25px;border-radius:10px;border-left:5px solid #6A8759;box-shadow:0 2px 10px rgba(0,0,0,0.3);">
                                    <div style="margin-bottom:20px;">
                                        <strong style="color:#6A8759;font-size:16px;display:block;margin-bottom:8px;">📌 Function:</strong> 
                                        <code style="color:#FFC66D;font-size:16px;background:#2B2B2B;padding:8px 12px;border-radius:6px;display:inline-block;">${{escapeHtml(nodeId)}}</code>
                                    </div>
                                    <hr style="border:none;border-top:2px solid #3C3F41;margin:20px 0;">
                                    <div style="color:#B8D4A8;line-height:1.8;font-size:15px;letter-spacing:0.3px;">
                                        ${{formattedExplanation}}
                                    </div>
                                </div>
                            `;
                            showModal();
                        }} else {{
                            modalBody.innerHTML = `
                                <div style="background:#3C3F41;padding:30px;border-radius:10px;text-align:center;">
                                    <div style="font-size:48px;margin-bottom:15px;">⚠️</div>
                                    <span style="color:#BBB529;font-size:18px;font-weight:500;">No AI explanation available</span><br><br>
                                    <small style="color:#808080;font-size:14px;">AI explanations may not be generated for all functions.<br>Try re-running flow analysis with AI enabled.</small>
                                </div>
                            `;
                            showModal();
                        }}
                    }}
                }});
                
                // Close on Escape key
                document.addEventListener('keydown', function(event) {{
                    if (event.key === 'Escape') {{
                        closeModal();
                    }}
                }});
            </script>
            """
            
            html = html.replace('</body>', modal_html + '</body>')
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
                
        except Exception as e:
            print(f"Error adding AI modal: {e}")
    
    def render_with_trace_overlay(self, graph: CallGraph, trace_data: dict, 
                                   ai_explanations: dict = None,
                                   output_filename: str = "traced_flow.html") -> str:
        """
        Render graph with execution trace overlay
        
        Args:
            graph: CallGraph to visualize
            trace_data: Trace data with 'stats' and 'events'
            ai_explanations: Optional AI explanations
            output_filename: Name of output HTML file
            
        Returns:
            Path to generated HTML file
        """
        output_path = self.output_dir / output_filename
        
        # Extract trace statistics
        trace_stats = trace_data.get('stats', {})
        trace_events = trace_data.get('events', [])
        
        # Calculate performance percentiles for color coding
        all_avg_times = []
        for func_name, stats in trace_stats.items():
            if stats.get('call_count', 0) > 0:
                avg_time = stats['total_time'] / stats['call_count']
                all_avg_times.append(avg_time)
        
        all_avg_times.sort()
        if all_avg_times:
            p50 = all_avg_times[len(all_avg_times) // 2] if len(all_avg_times) > 0 else 0.001
            p90 = all_avg_times[int(len(all_avg_times) * 0.9)] if len(all_avg_times) > 1 else 0.01
        else:
            p50, p90 = 0.001, 0.01
        
        # Create PyVis network
        net = Network(
            height="800px",
            width="100%",
            bgcolor="#2B2B2B",
            font_color="#A9B7C6",
            directed=True
        )
        
        # Configure physics
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
            "borderWidth": 3,
            "borderWidthSelected": 4
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
            }
          },
          "interaction": {
            "hover": true,
            "navigationButtons": true,
            "keyboard": true
          }
        }
        """)
        
        # Add nodes with performance-based coloring
        for func_name, func_info in graph.nodes.items():
            safe_name = sanitize_text(func_name)
            safe_file = sanitize_text(os.path.basename(func_info.file))
            
            # Get trace statistics for this function
            func_stats = trace_stats.get(func_name, {})
            call_count = func_stats.get('call_count', 0)
            total_time = func_stats.get('total_time', 0)
            avg_time = (total_time / call_count) if call_count > 0 else 0
            
            # Performance-based color coding
            if call_count == 0:
                # Not executed - gray
                color = "#555555"
                border_color = "#777777"
            elif avg_time < p50:
                # Fast - green
                color = "#6A8759"
                border_color = "#8FC34B"
            elif avg_time < p90:
                # Medium - orange
                color = "#CC7832"
                border_color = "#FFC66D"
            else:
                # Slow - red
                color = "#BC3F3C"
                border_color = "#FF6B6B"
            
            # Build enhanced tooltip with trace data
            signature = sanitize_text(func_info.signature or "()")
            doc_preview = sanitize_text((func_info.docstring or "").strip().replace('\n', ' '))
            if len(doc_preview) > 100:
                doc_preview = doc_preview[:100] + "..."
            
            # Performance metrics
            perf_section = ""
            if call_count > 0:
                min_time = func_stats.get('min_time', 0) * 1000  # to ms
                max_time = func_stats.get('max_time', 0) * 1000
                avg_time_ms = avg_time * 1000
                total_time_ms = total_time * 1000
                
                perf_section = f"""
                <div style='margin-top:8px;padding:8px;background:#1E1E1E;border-left:3px solid {border_color};border-radius:3px;'>
                    <strong style='color:{border_color};'>⚡ Execution Trace</strong><br>
                    <span style='color:#808080;'>Calls:</span> <strong>{call_count}</strong><br>
                    <span style='color:#808080;'>Total:</span> {total_time_ms:.2f}ms<br>
                    <span style='color:#808080;'>Avg:</span> {avg_time_ms:.3f}ms<br>
                    <span style='color:#808080;'>Min:</span> {min_time:.3f}ms | <span style='color:#808080;'>Max:</span> {max_time:.3f}ms
                </div>
                """
            else:
                perf_section = """
                <div style='margin-top:8px;padding:8px;background:#1E1E1E;border-left:3px solid #555555;border-radius:3px;'>
                    <span style='color:#808080;'>⚠️ Not executed in trace</span>
                </div>
                """
            
            # AI explanation indicator
            ai_indicator = ""
            if ai_explanations and func_name in ai_explanations:
                ai_indicator = "<br><small style='color:#6A8759;'>🤖 AI Explanation Available</small>"
            
            async_badge = "<span style='color:#6A8759;'>async</span>" if func_info.is_async else ""
            class_line = (
                f"<span style='color:#808080;'>Class:</span> {sanitize_text(func_info.class_name)}<br>"
                if func_info.class_name else ""
            )
            
            tooltip = (
                f"<div style='font-family:Consolas,monospace;font-size:12px;color:#A9B7C6;'>"
                f"<strong style='color:#6A8759;'>{safe_name}{signature}</strong> {async_badge}<br>"
                f"<span style='color:#808080;'>File:</span> {safe_file}:{func_info.line}<br>"
                f"{class_line}"
                f"<span style='color:#808080;'>LOC:</span> {func_info.loc or 0}<br>"
                f"<span style='color:#808080;'>Docstring:</span> {doc_preview or '—'}"
                f"{perf_section}"
                f"{ai_indicator}"
                f"</div>"
            )
            
            # Size based on call count (with minimum size)
            node_size = 20 + min(call_count * 2, 50)
            
            net.add_node(
                safe_name,
                label=safe_name,
                title=tooltip,
                color={'background': color, 'border': border_color},
                size=node_size,
                borderWidth=3
            )
        
        # Add edges (could enhance with execution frequency if needed)
        for from_func, to_funcs in graph.edges.items():
            safe_from = sanitize_text(from_func)
            for to_func in to_funcs:
                safe_to = sanitize_text(to_func)
                if safe_to in [sanitize_text(n) for n in graph.nodes.keys()]:
                    net.add_edge(safe_from, safe_to)
        
        # Generate HTML
        net.save_graph(str(output_path))
        
        # Add trace overlay enhancements
        self._add_trace_overlay_ui(output_path, trace_stats, trace_events)
        
        # Add AI modal if explanations provided
        if ai_explanations:
            explanations_js = {sanitize_text(k): v for k, v in ai_explanations.items()}
            self._add_ai_modal(output_path, explanations_js, graph)
        
        print(f"Trace-enhanced visualization saved to: {output_path}")
        return str(output_path)
    
    def _add_trace_overlay_ui(self, html_path: Path, stats: dict, events: list):
        """Add trace statistics panel and legend to visualization"""
        try:
            import json
            
            with open(html_path, 'r', encoding='utf-8') as f:
                html = f.read()
            
            # Calculate totals
            total_calls = sum(s.get('call_count', 0) for s in stats.values())
            total_time = sum(s.get('total_time', 0) for s in stats.values()) * 1000  # to ms
            functions_executed = sum(1 for s in stats.values() if s.get('call_count', 0) > 0)
            
            # Top 5 slowest functions
            top_slow = sorted(
                [(name, s) for name, s in stats.items() if s.get('call_count', 0) > 0],
                key=lambda x: x[1]['total_time'],
                reverse=True
            )[:5]
            
            top_slow_html = ""
            for func_name, func_stats in top_slow:
                time_ms = func_stats['total_time'] * 1000
                calls = func_stats['call_count']
                top_slow_html += f"<div style='padding:4px;margin:2px 0;background:#1E1E1E;border-radius:3px;'><small>{sanitize_text(func_name)[:25]}: {time_ms:.1f}ms ({calls} calls)</small></div>"
            
            overlay_html = f"""
            <div id="trace-stats-panel" style="
                position: fixed;
                top: 10px;
                right: 10px;
                background: linear-gradient(135deg, #2B2B2B 0%, #1E1E1E 100%);
                color: #A9B7C6;
                padding: 15px;
                border-radius: 8px;
                border: 2px solid #6A8759;
                box-shadow: 0 4px 16px rgba(0,0,0,0.7), 0 0 10px rgba(106,143,89,0.2);
                z-index: 1000;
                min-width: 250px;
                font-family: 'Segoe UI', Consolas, monospace;
                font-size: 13px;
            ">
                <h3 style="margin: 0 0 12px 0; color: #6A8759; font-size: 16px;">⚡ Trace Statistics</h3>
                <div style="margin-bottom: 10px;">
                    <strong>Total Events:</strong> {len(events)}<br>
                    <strong>Functions Executed:</strong> {functions_executed}<br>
                    <strong>Total Calls:</strong> {total_calls}<br>
                    <strong>Total Time:</strong> {total_time:.2f}ms
                </div>
                
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #555;">
                    <strong style="color: #CC7832;">Top Time Consumers:</strong>
                    {top_slow_html}
                </div>
            </div>
            
            <div id="trace-legend" style="
                position: fixed;
                bottom: 10px;
                left: 10px;
                background: linear-gradient(135deg, #2B2B2B 0%, #1E1E1E 100%);
                color: #A9B7C6;
                padding: 12px 15px;
                border-radius: 8px;
                border: 2px solid #6A8759;
                box-shadow: 0 4px 16px rgba(0,0,0,0.7);
                z-index: 1000;
                font-family: 'Segoe UI', Consolas, monospace;
                font-size: 12px;
            ">
                <strong style="color: #6A8759;">Performance Legend:</strong><br>
                <div style="margin-top: 6px;">
                    <span style="display:inline-block;width:12px;height:12px;background:#6A8759;border-radius:50%;margin-right:6px;"></span>Fast (p50)<br>
                    <span style="display:inline-block;width:12px;height:12px;background:#CC7832;border-radius:50%;margin-right:6px;"></span>Medium (p50-p90)<br>
                    <span style="display:inline-block;width:12px;height:12px;background:#BC3F3C;border-radius:50%;margin-right:6px;"></span>Slow (p90+)<br>
                    <span style="display:inline-block;width:12px;height:12px;background:#555555;border-radius:50%;margin-right:6px;"></span>Not executed
                </div>
            </div>
            """
            
            html = html.replace('<body>', '<body>' + overlay_html)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
                
        except Exception as e:
            print(f"Error adding trace overlay UI: {e}")
