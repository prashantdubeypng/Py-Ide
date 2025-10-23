"""
Simple Interactive Terminal Widget (without pywinpty dependency)
Uses subprocess with proper stdin/stdout handling
"""
import subprocess
import threading
import queue
import sys
import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTextBrowser
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor, QFont


class ProcessReader(QObject):
    """Background thread to read process output"""
    output_ready = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, process):
        super().__init__()
        self.process = process
        self.running = True
    
    def read_output(self):
        """Read from process stdout and stderr"""
        try:
            while self.running and self.process.poll() is None:
                # Read character by character to avoid buffering issues
                char = self.process.stdout.read(1)
                if char:
                    self.output_ready.emit(char)
                
        except Exception as e:
            self.output_ready.emit(f"\n[Error reading output: {e}]\n")
        finally:
            # Read any remaining output
            try:
                remaining = self.process.stdout.read()
                if remaining:
                    self.output_ready.emit(remaining)
            except:
                pass
            self.finished.emit()
    
    def stop(self):
        """Stop reading"""
        self.running = False


class SimpleInteractiveTerminal(QWidget):
    """Simple interactive terminal without pywinpty dependency"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.reader = None
        self.reader_thread = None
        self.command_history = []
        self.history_index = -1
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Output display
        self.output_display = QTextBrowser()
        self.output_display.setStyleSheet("""
            QTextBrowser {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        font = QFont("Consolas", 10)
        self.output_display.setFont(font)
        layout.addWidget(self.output_display)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type input and press Enter...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #2D2D30;
                color: #D4D4D4;
                border: 1px solid #3E3E42;
                padding: 5px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        self.input_field.returnPressed.connect(self._send_input)
        self.input_field.setEnabled(False)
        input_layout.addWidget(self.input_field)
        
        # Buttons
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send_input)
        self.send_btn.setEnabled(False)
        input_layout.addWidget(self.send_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear)
        input_layout.addWidget(self.clear_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop_process)
        self.stop_btn.setEnabled(False)
        input_layout.addWidget(self.stop_btn)
        
        layout.addLayout(input_layout)
        
        # Welcome message
        self._append_output("=== Simple Interactive Terminal ===\n")
        self._append_output("Ready to run Python scripts with input() support.\n")
        self._append_output("Note: Colors and some advanced features not available.\n\n")
    
    def run_command(self, command, cwd=None):
        """Run a command in the terminal"""
        if self.process and self.process.poll() is None:
            self._append_output("\n[Process already running. Stop it first.]\n")
            return
        
        self.clear()
        self._append_output(f"$ {command}\n")
        self._append_output("-" * 60 + "\n")
        
        try:
            # Set environment variables for proper encoding and unbuffered output
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'  # Force UTF-8 encoding for Python
            
            # Create process with proper stdin/stdout handling
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                shell=True,
                text=True,
                bufsize=0,  # Unbuffered
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                env=env
            )
            
            # Enable input controls
            self.input_field.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.input_field.setFocus()
            
            # Start reader thread
            self.reader = ProcessReader(self.process)
            self.reader.output_ready.connect(self._append_output)
            self.reader.finished.connect(self._on_process_finished)
            
            self.reader_thread = threading.Thread(target=self.reader.read_output, daemon=True)
            self.reader_thread.start()
            
        except Exception as e:
            self._append_output(f"\n[Error starting process: {e}]\n")
            self._on_process_finished()
    
    def _send_input(self):
        """Send input to the process"""
        if not self.process or self.process.poll() is not None:
            return
        
        text = self.input_field.text()
        if not text:
            return
        
        try:
            # Echo input
            self._append_output(f"{text}\n")
            
            # Send to process
            self.process.stdin.write(text + "\n")
            self.process.stdin.flush()
            
            # Add to history
            self.command_history.append(text)
            self.history_index = len(self.command_history)
            
            # Clear input
            self.input_field.clear()
            
        except Exception as e:
            self._append_output(f"\n[Error sending input: {e}]\n")
    
    def _stop_process(self):
        """Stop the running process"""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self._append_output("\n[Process terminated]\n")
            except Exception as e:
                self._append_output(f"\n[Error stopping process: {e}]\n")
        
        self._on_process_finished()
    
    def _on_process_finished(self):
        """Handle process completion"""
        # Disable input controls
        self.input_field.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        # Show exit code if available
        if self.process:
            code = self.process.poll()
            if code is not None:
                self._append_output(f"\n[Process exited with code {code}]\n")
        
        # Clean up reader
        if self.reader:
            self.reader.stop()
        
        self._append_output("\n" + "=" * 60 + "\n")
    
    def _append_output(self, text):
        """Append text to output display"""
        cursor = self.output_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.output_display.setTextCursor(cursor)
        self.output_display.ensureCursorVisible()
    
    def clear(self):
        """Clear the output"""
        self.output_display.clear()
    
    def cleanup(self):
        """Clean up resources"""
        if self.reader:
            self.reader.stop()
        
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                try:
                    self.process.kill()
                except:
                    pass
