"""
Live Runtime Tracing for Python Code Execution
Captures function calls and returns with timing information
"""
import sys
import time
import threading
import queue
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, List
from ide.utils.logger import logger


class LiveTracer:
    """Captures live function call/return events during code execution"""
    
    def __init__(self, event_queue: Optional[queue.Queue] = None):
        self.event_queue = event_queue or queue.Queue()
        self.start_time = time.time()
        self.enabled = False
        self.call_stack: List[Dict] = []
        self.stats: Dict[str, Dict] = {}  # Function call statistics
        
    def _trace(self, frame, event, arg):
        """Trace function for sys.settrace()"""
        if not self.enabled:
            return None
            
        func_name = frame.f_code.co_name
        module = frame.f_globals.get("__name__", "")
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        
        # Filter out internal/library functions
        if self._should_trace(filename, func_name):
            if event == "call":
                call_event = {
                    "event": "call",
                    "func": func_name,
                    "module": module,
                    "filename": filename,
                    "lineno": lineno,
                    "time": time.time() - self.start_time,
                    "caller": self.call_stack[-1]["func"] if self.call_stack else None
                }
                
                self.call_stack.append(call_event)
                self.event_queue.put(call_event)
                
                # Update statistics
                if func_name not in self.stats:
                    self.stats[func_name] = {
                        "call_count": 0,
                        "total_time": 0,
                        "min_time": float('inf'),
                        "max_time": 0
                    }
                self.stats[func_name]["call_count"] += 1
                
            elif event == "return":
                if self.call_stack:
                    call_info = self.call_stack.pop()
                    duration = (time.time() - self.start_time) - call_info["time"]
                    
                    return_event = {
                        "event": "return",
                        "func": func_name,
                        "time": time.time() - self.start_time,
                        "duration": duration
                    }
                    
                    self.event_queue.put(return_event)
                    
                    # Update statistics
                    if func_name in self.stats:
                        stats = self.stats[func_name]
                        stats["total_time"] += duration
                        stats["min_time"] = min(stats["min_time"], duration)
                        stats["max_time"] = max(stats["max_time"], duration)
        
        return self._trace
    
    def _should_trace(self, filename: str, func_name: str) -> bool:
        """Filter out library/internal functions"""
        # Skip built-in functions
        if func_name.startswith('_') and func_name != '__init__':
            return False
        
        # Only trace user code (not libraries)
        if 'site-packages' in filename or 'lib\\' in filename:
            return False
        
        # Skip <frozen> and <string> modules
        if filename.startswith('<'):
            return False
            
        return True
    
    def start(self):
        """Start tracing"""
        self.enabled = True
        self.start_time = time.time()
        sys.settrace(self._trace)
        logger.info("Live tracer started")
    
    def stop(self):
        """Stop tracing"""
        sys.settrace(None)
        self.enabled = False
        logger.info("Live tracer stopped")
    
    def get_stats(self) -> Dict:
        """Get call statistics"""
        return self.stats
    
    def save_trace(self, filepath: str):
        """Save trace events to JSON file"""
        events = []
        while not self.event_queue.empty():
            events.append(self.event_queue.get())
        
        with open(filepath, 'w') as f:
            json.dump({
                "events": events,
                "stats": self.stats,
                "duration": time.time() - self.start_time
            }, f, indent=2)
        
        logger.info(f"Trace saved to {filepath}")
        return filepath


class TraceEventServer:
    """WebSocket server for streaming trace events to visualization"""
    
    def __init__(self, event_queue: queue.Queue, port: int = 8765):
        self.event_queue = event_queue
        self.port = port
        self.running = False
        self.clients = set()
        
    async def handler(self, websocket):
        """Handle WebSocket connections"""
        self.clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
    
    async def broadcast_events(self):
        """Broadcast events to all connected clients"""
        while self.running:
            try:
                # Get event with timeout
                event = self.event_queue.get(timeout=0.1)
                
                # Send to all clients
                if self.clients:
                    import websockets
                    await websockets.broadcast(self.clients, json.dumps(event))
                    
            except queue.Empty:
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Error broadcasting event: {e}")
    
    async def start_server(self):
        """Start WebSocket server"""
        try:
            import websockets
            import asyncio
            
            self.running = True
            
            async with websockets.serve(self.handler, "localhost", self.port):
                logger.info(f"Trace event server started on ws://localhost:{self.port}")
                await self.broadcast_events()
                
        except ImportError:
            logger.warning("websockets not installed. Install with: pip install websockets")
        except Exception as e:
            logger.error(f"Failed to start trace server: {e}")
    
    def stop(self):
        """Stop server"""
        self.running = False


class TraceReplay:
    """Replay recorded trace events"""
    
    def __init__(self, trace_file: str):
        self.trace_file = trace_file
        self.events = []
        self.stats = {}
        self.load()
    
    def load(self):
        """Load trace from file"""
        try:
            with open(self.trace_file, 'r') as f:
                data = json.load(f)
                self.events = data.get("events", [])
                self.stats = data.get("stats", {})
            logger.info(f"Loaded {len(self.events)} trace events")
        except Exception as e:
            logger.error(f"Failed to load trace: {e}")
    
    def replay(self, event_callback, speed: float = 1.0):
        """
        Replay trace events with timing
        
        Args:
            event_callback: Function to call for each event
            speed: Playback speed multiplier (1.0 = normal, 2.0 = 2x speed)
        """
        if not self.events:
            return
        
        start_time = self.events[0]["time"]
        
        for event in self.events:
            # Calculate delay
            delay = (event["time"] - start_time) / speed
            time.sleep(delay)
            
            # Send event to callback
            event_callback(event)
            
            # Update start time for next iteration
            start_time = event["time"]
