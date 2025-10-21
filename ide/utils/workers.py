"""
Thread workers for background tasks
Non-blocking file operations and code analysis
"""
from PyQt5.QtCore import QThread, pyqtSignal
import os
import json
import subprocess
import sys


class FileOperationWorker(QThread):
    """Worker thread for file I/O operations"""
    
    finished = pyqtSignal(str, str)  # (operation_type, result)
    error = pyqtSignal(str, str)  # (operation_type, error_message)
    
    def __init__(self, operation, *args):
        super().__init__()
        self.operation = operation
        self.args = args
    
    def run(self):
        try:
            if self.operation == "read":
                filepath = self.args[0]
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.finished.emit("read", content)
            
            elif self.operation == "write":
                filepath, content = self.args
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.finished.emit("write", filepath)
            
            elif self.operation == "delete":
                filepath = self.args[0]
                if os.path.isfile(filepath):
                    os.remove(filepath)
                elif os.path.isdir(filepath):
                    import shutil
                    shutil.rmtree(filepath)
                self.finished.emit("delete", filepath)
                
        except Exception as e:
            self.error.emit(self.operation, str(e))


class LintWorker(QThread):
    """Worker thread for code linting"""
    
    finished = pyqtSignal(list)  # List of lint issues
    error = pyqtSignal(str)
    
    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
    
    def run(self):
        try:
            result = subprocess.run(
                ["pylint", "--output-format=json", self.filepath],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.stdout:
                issues = json.loads(result.stdout)
                self.finished.emit(issues)
            else:
                self.finished.emit([])
                
        except subprocess.TimeoutExpired:
            self.error.emit("Linting timeout")
        except FileNotFoundError:
            self.error.emit("Pylint not installed")
        except Exception as e:
            self.error.emit(str(e))


class CodeAnalysisWorker(QThread):
    """Worker thread for code analysis with Jedi"""
    
    completions_ready = pyqtSignal(list)  # List of completion suggestions
    
    def __init__(self, code, line, column):
        super().__init__()
        self.code = code
        self.line = line
        self.column = column
    
    def run(self):
        try:
            import jedi
            script = jedi.Script(self.code)
            completions = script.complete(self.line, self.column)
            results = [c.name for c in completions]
            self.completions_ready.emit(results)
        except Exception:
            self.completions_ready.emit([])
