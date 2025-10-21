"""
Graph Builder for Function Flow
Manages and optimizes large call graphs
"""
import json
from typing import Dict, Set, List, Tuple
from collections import defaultdict, deque
from dataclasses import asdict

from ide.analyzer.flow_analyzer import FunctionInfo
from ide.analyzer.security import MAX_NODES, sanitize_node_name


class CallGraph:
    """Represents a directed call graph"""
    
    def __init__(self):
        self.nodes: Dict[str, FunctionInfo] = {}
        self.edges: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_edges: Dict[str, Set[str]] = defaultdict(set)
        self._stats = None
    
    def add_function(self, func_info: FunctionInfo):
        """Add a function node to the graph"""
        self.nodes[func_info.name] = func_info
        
        # Add edges for each call
        for called_func in func_info.calls:
            self.add_edge(func_info.name, called_func)
    
    def add_edge(self, from_func: str, to_func: str):
        """Add a directed edge (function call)"""
        self.edges[from_func].add(to_func)
        self.reverse_edges[to_func].add(from_func)
    
    def get_callers(self, func_name: str) -> Set[str]:
        """Get all functions that call this function"""
        return self.reverse_edges.get(func_name, set())
    
    def get_callees(self, func_name: str) -> Set[str]:
        """Get all functions called by this function"""
        return self.edges.get(func_name, set())
    
    def get_stats(self) -> Dict:
        """Get graph statistics"""
        if self._stats:
            return self._stats
        
        total_nodes = len(self.nodes)
        total_edges = sum(len(calls) for calls in self.edges.values())
        
        # Find nodes with most connections
        node_degrees = {
            node: len(self.edges.get(node, set())) + len(self.reverse_edges.get(node, set()))
            for node in self.nodes
        }
        
        top_connected = sorted(node_degrees.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Find isolated nodes
        isolated = [node for node in self.nodes if node not in self.edges and node not in self.reverse_edges]
        
        # Count async functions
        async_count = sum(1 for func in self.nodes.values() if func.is_async)
        
        self._stats = {
            'total_functions': total_nodes,
            'total_calls': total_edges,
            'async_functions': async_count,
            'isolated_functions': len(isolated),
            'top_connected': top_connected[:5],
            'average_calls_per_function': total_edges / total_nodes if total_nodes > 0 else 0
        }
        
        return self._stats
    
    def find_cycles(self) -> List[List[str]]:
        """Detect circular call chains"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.edges.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle)
            
            rec_stack.remove(node)
        
        for node in self.nodes:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def get_subgraph(self, root_nodes: List[str], max_depth: int = 3) -> 'CallGraph':
        """
        Extract a subgraph starting from root nodes
        
        Args:
            root_nodes: Starting nodes
            max_depth: Maximum depth to traverse
            
        Returns:
            New CallGraph with subset of nodes
        """
        subgraph = CallGraph()
        visited = set()
        queue = deque([(node, 0) for node in root_nodes])
        
        while queue:
            node, depth = queue.popleft()
            
            if node in visited or depth > max_depth:
                continue
            
            visited.add(node)
            
            # Add node if it exists in original graph
            if node in self.nodes:
                subgraph.add_function(self.nodes[node])
            
            # Add neighbors
            if depth < max_depth:
                for neighbor in self.edges.get(node, []):
                    if neighbor not in visited:
                        queue.append((neighbor, depth + 1))
        
        return subgraph
    
    def to_dict(self) -> Dict:
        """Convert graph to dictionary for serialization"""
        return {
            'nodes': {
                name: {
                    'name': info.name,
                    'file': info.file,
                    'line': info.line,
                    'is_async': info.is_async,
                    'is_method': info.is_method,
                    'class_name': info.class_name
                }
                for name, info in self.nodes.items()
            },
            'edges': {
                node: list(calls) for node, calls in self.edges.items()
            }
        }
    
    def save_to_json(self, filepath: str):
        """Save graph to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CallGraph':
        """Load graph from dictionary"""
        graph = cls()
        
        # Reconstruct nodes
        for name, node_data in data.get('nodes', {}).items():
            func_info = FunctionInfo(
                name=node_data['name'],
                file=node_data['file'],
                line=node_data['line'],
                calls=set(),
                is_async=node_data.get('is_async', False),
                is_method=node_data.get('is_method', False),
                class_name=node_data.get('class_name')
            )
            graph.nodes[name] = func_info
        
        # Reconstruct edges
        for node, calls in data.get('edges', {}).items():
            for called in calls:
                graph.add_edge(node, called)
        
        return graph
    
    @classmethod
    def load_from_json(cls, filepath: str) -> 'CallGraph':
        """Load graph from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


class GraphBuilder:
    """Builds optimized call graphs from function data"""
    
    def __init__(self):
        self.graph = CallGraph()
    
    def build_from_functions(self, functions: Dict[str, FunctionInfo]) -> CallGraph:
        """
        Build graph from function data
        
        Args:
            functions: Dictionary of FunctionInfo objects
            
        Returns:
            CallGraph object
        """
        print(f"Building graph from {len(functions)} functions...")
        
        # Add all functions as nodes
        for func_info in functions.values():
            self.graph.add_function(func_info)
        
        # Calculate stats
        stats = self.graph.get_stats()
        print(f"Graph built: {stats['total_functions']} functions, {stats['total_calls']} calls")
        
        return self.graph
    
    def optimize_for_visualization(self, max_nodes: int = 100) -> CallGraph:
        """
        Optimize graph for visualization by limiting size
        
        Args:
            max_nodes: Maximum nodes to include
            
        Returns:
            Optimized CallGraph
        """
        if len(self.graph.nodes) <= max_nodes:
            return self.graph
        
        print(f"Optimizing graph: {len(self.graph.nodes)} -> {max_nodes} nodes")
        
        # Get most connected nodes
        stats = self.graph.get_stats()
        top_nodes = [node for node, degree in stats['top_connected']]
        
        # Expand from top nodes
        return self.graph.get_subgraph(top_nodes, max_depth=2)
