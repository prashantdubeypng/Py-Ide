"""
Graph AI Integration
AI-powered explanations and suggestions for graph nodes and edges
"""
from typing import Optional, Dict, Any
from ide.utils.ai_manager import AIManager
from ide.utils.logger import logger


class GraphAIAssistant:
    """AI-powered assistance for call graphs"""
    
    def __init__(self, ai_manager: AIManager):
        self.ai_manager = ai_manager
    
    def explain_function(self, func_info) -> str:
        """Generate AI explanation for a function"""
        if not func_info:
            return "No function selected"
        
        context = "You are a Python code expert. Provide concise, technical explanations."
        
        prompt = f"""Explain this Python function in 2-3 sentences:

**Function:** {func_info.name}
**Signature:** {getattr(func_info, 'signature', 'N/A')}
**Docstring:** {getattr(func_info, 'docstring', 'No docstring')}
**Lines of Code:** {getattr(func_info, 'loc', 'Unknown')}

Code preview:
```python
{getattr(func_info, 'source_snippet', 'N/A')}
```

Focus on: purpose, inputs/outputs, and key functionality."""
        
        return self.ai_manager.generate_sync(prompt, context)
    
    def explain_call_relationship(
        self,
        caller_name: str,
        callee_name: str,
        call_count: int = 1
    ) -> str:
        """Explain why functions are connected"""
        context = "You are analyzing call graphs in Python projects."
        
        prompt = f"""Explain the relationship between these functions:
- **Caller:** {caller_name}
- **Callee:** {callee_name}
- **Call Count:** {call_count}

Why might {caller_name} call {callee_name}? What's the likely data flow?"""
        
        return self.ai_manager.generate_sync(prompt, context)
    
    def detect_anti_patterns(self, graph_data: Dict[str, Any]) -> str:
        """Detect and explain anti-patterns in the graph"""
        context = "You are a Python architecture expert analyzing call graphs for design issues."
        
        # Build description of graph structure
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        cycles = graph_data.get("cycles", [])
        
        node_summary = f"{len(nodes)} functions, {len(edges)} calls"
        
        prompt = f"""Analyze this Python call graph for anti-patterns:

**Graph Statistics:**
- {node_summary}
- {len(cycles)} circular dependencies found

Potential issues to check:
1. Circular dependencies/deadlocks
2. Deep call chains (>5 levels)
3. Functions with too many callers (>10)
4. Tight coupling patterns
5. God objects or utility function anti-patterns

Provide 2-3 specific, actionable suggestions for improving the architecture."""
        
        return self.ai_manager.generate_sync(prompt, context)
    
    def suggest_refactoring(self, func_info, related_functions: list) -> str:
        """Suggest refactoring for a function and its context"""
        context = "You are a Python refactoring expert."
        
        related_names = ", ".join(f.name for f in related_functions[:5]) if related_functions else "none"
        
        prompt = f"""Suggest refactoring improvements for this function:

**Function:** {func_info.name}
**Related Functions:** {related_names}
**Lines of Code:** {getattr(func_info, 'loc', 'Unknown')}

Code:
```python
{getattr(func_info, 'source_snippet', 'N/A')}
```

Provide 2-3 specific refactoring suggestions that would improve:
- Readability
- Maintainability
- Performance (if applicable)
- Testability"""
        
        return self.ai_manager.generate_sync(prompt, context)
    
    def analyze_call_chain(self, call_chain: list) -> str:
        """Analyze a sequence of function calls"""
        context = "You are analyzing execution paths in Python programs."
        
        chain_str = " → ".join(call_chain)
        
        prompt = f"""Analyze this call chain:

{chain_str}

Questions to address:
1. What is the likely purpose of this call sequence?
2. Are there any potential issues (infinite recursion, data flow problems)?
3. How could this chain be optimized or simplified?
4. What edge cases should be handled?

Provide 2-3 actionable insights."""
        
        return self.ai_manager.generate_sync(prompt, context)
    
    def get_complexity_assessment(self, graph_data: Dict[str, Any]) -> str:
        """Assess overall code complexity from graph perspective"""
        context = "You are assessing software architecture complexity."
        
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        stats = graph_data.get("stats", {})
        
        max_loc = stats.get("max_loc", 0)
        avg_loc = stats.get("avg_loc", 0)
        
        prompt = f"""Assess the complexity of this Python codebase based on its call graph:

**Metrics:**
- Total Functions: {len(nodes)}
- Total Calls: {len(edges)}
- Max Function Size: {max_loc} LOC
- Average Function Size: {avg_loc:.0f} LOC

Rate the complexity (Low/Medium/High) and provide:
1. Key complexity drivers
2. Top 3 areas for simplification
3. Recommended refactoring priorities"""
        
        return self.ai_manager.generate_sync(prompt, context)
    
    def format_explanation(self, title: str, explanation: str) -> str:
        """Format AI explanation with title"""
        return f"**{title}**\n\n{explanation}"
    
    def generate_interactive_suggestions(self, selected_node=None, selected_edge=None) -> Dict[str, str]:
        """Generate multiple suggestions based on selection"""
        suggestions = {}
        
        if selected_node:
            func_info = selected_node.get("data", {})
            suggestions["explain"] = self.format_explanation(
                f"Function: {func_info.get('name', 'Unknown')}",
                self.explain_function(func_info)
            )
        
        if selected_edge:
            caller = selected_edge.get("from", "Unknown")
            callee = selected_edge.get("to", "Unknown")
            suggestions["relationship"] = self.format_explanation(
                f"Call: {caller} → {callee}",
                self.explain_call_relationship(caller, callee)
            )
        
        return suggestions


class GraphEnhancer:
    """Enhances graph visualization with AI metadata"""
    
    def __init__(self, ai_assistant: GraphAIAssistant):
        self.ai = ai_assistant
    
    def add_ai_explanations_to_nodes(self, nodes: list) -> list:
        """Add AI explanations to each node"""
        for node in nodes:
            try:
                func_info = node.get("data")
                if func_info:
                    explanation = self.ai.explain_function(func_info)
                    node["ai_explanation"] = explanation[:200] + "..." if len(explanation) > 200 else explanation
            except Exception as e:
                logger.error(f"Error adding AI explanation to node: {e}")
                node["ai_explanation"] = "Unable to generate explanation"
        
        return nodes
    
    def add_ai_suggestions_to_edges(self, edges: list) -> list:
        """Add AI suggestions to significant edges"""
        for i, edge in enumerate(edges):
            if i % 5 == 0:  # Sample every 5th edge to avoid overload
                try:
                    caller = edge.get("from", "Unknown")
                    callee = edge.get("to", "Unknown")
                    relationship = self.ai.explain_call_relationship(caller, callee)
                    edge["ai_suggestion"] = relationship[:150] + "..." if len(relationship) > 150 else relationship
                except Exception as e:
                    logger.error(f"Error adding AI suggestion to edge: {e}")
        
        return edges


if __name__ == "__main__":
    from ide.utils.settings import SettingsManager
    
    settings = SettingsManager()
    ai_manager = AIManager(settings)
    
    # Test
    assistant = GraphAIAssistant(ai_manager)
    print("Graph AI Assistant initialized")
