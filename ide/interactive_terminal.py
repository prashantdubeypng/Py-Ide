"""
Interactive Terminal Widget using WinPTY
Supports real input(), ANSI colors, Ctrl+C, and full terminal interaction
"""
import sys
import threading
import html
import time
from queue import Queue

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtWebEngineWidgets import QWebEngineView

try:
    import pywinpty
    WINPTY_AVAILABLE = True
    WINPTY_ERROR = None
except ImportError as e:
    WINPTY_AVAILABLE = False
    WINPTY_ERROR = str(e)
    # Raise so fallback import works
    raise
except Exception as e:
    WINPTY_AVAILABLE = False
    WINPTY_ERROR = f"Unexpected error: {str(e)}"
    # Raise so fallback import works
    raise

try:
    from ansi2html import Ansi2HTMLConverter
    ANSI2HTML_AVAILABLE = True
except ImportError:
    ANSI2HTML_AVAILABLE = False


class WorkerSignals(QObject):
    """Signals for thread-safe communication with GUI"""
    html_ready = pyqtSignal(str)
    finished = pyqtSignal(int)


class InteractiveTerminalWidget(QWidget):
    """
    Fully interactive terminal widget using WinPTY
    Supports input(), colors, Ctrl+C, and command history
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Check if dependencies are available
        if not WINPTY_AVAILABLE:
            self._init_fallback()
            return
        
        self.init_ui()
        
        # Internal state
        self._pty = None
        self._reader_thread = None
        self._signals = WorkerSignals()
        self._signals.html_ready.connect(self.append_html)
        self._signals.finished.connect(self.on_process_finished)
        
        if ANSI2HTML_AVAILABLE:
            self.ansi_converter = Ansi2HTMLConverter(inline=True)
        else:
            self.ansi_converter = None
        
        # Command history
        self.history = []
        self.hist_index = -1
        self.input_field.installEventFilter(self)
    
    def _init_fallback(self):
        """Show message if pywinpty not available"""
        layout = QVBoxLayout(self)
        from PyQt5.QtWidgets import QLabel, QTextBrowser
        import sys
        
        # Get detailed diagnostic info
        python_exe = sys.executable
        python_version = sys.version
        site_packages = [p for p in sys.path if 'site-packages' in p]
        
        msg_widget = QTextBrowser()
        msg_widget.setOpenExternalLinks(True)
        msg_widget.setHtml(f"""
            <div style='padding: 20px; font-family: Consolas, monospace;'>
                <h2 style='color: #CC7832;'>⚠️ Interactive Terminal Not Available</h2>
                <p style='color: #A9B7C6; font-size: 14px;'>
                    The interactive terminal requires <code>pywinpty</code> to be installed.
                </p>
                
                <h3 style='color: #6A8759;'>Diagnostic Info:</h3>
                <div style='background: #2B2B2B; padding: 10px; border-radius: 5px; font-size: 12px;'>
                    <p style='color: #D4D4D4; margin: 5px 0;'>
                        <strong>Python:</strong> {html.escape(python_exe)}
                    </p>
                    <p style='color: #D4D4D4; margin: 5px 0;'>
                        <strong>Version:</strong> {html.escape(python_version.split()[0])}
                    </p>
                    <p style='color: #D4D4D4; margin: 5px 0;'>
                        <strong>Site-packages:</strong><br>
                        {html.escape('<br>'.join(site_packages[:2]) if site_packages else 'None found')}
                    </p>
                </div>
                
                <h3 style='color: #BC3F3C;'>Error:</h3>
                <p style='color: #BC3F3C; font-family: monospace; font-size: 12px; background: #2B2B2B; padding: 10px; border-radius: 5px;'>
                    {html.escape(WINPTY_ERROR or "No module named 'pywinpty'")}
                </p>
                
                <h3 style='color: #6A8759;'>Solution:</h3>
                <ol style='color: #D4D4D4;'>
                    <li><strong>Close the IDE</strong></li>
                    <li>In PowerShell, activate venv:<br>
                        <code style='background: #2B2B2B; padding: 4px; display: block; margin: 5px 0;'>
                            .venv\\Scripts\\Activate.ps1
                        </code>
                    </li>
                    <li>Verify prompt shows <code>(.venv)</code></li>
                    <li>Install packages:<br>
                        <code style='background: #2B2B2B; padding: 4px; display: block; margin: 5px 0;'>
                            pip install pywinpty ansi2html
                        </code>
                    </li>
                    <li>Run IDE from venv:<br>
                        <code style='background: #2B2B2B; padding: 4px; display: block; margin: 5px 0;'>
                            python run_ide.py
                        </code>
                    </li>
                </ol>
                
                <h3 style='color: #6A8759;'>Quick Test:</h3>
                <p style='color: #D4D4D4;'>
                    After activating venv, test if pywinpty is available:<br>
                    <code style='background: #2B2B2B; padding: 4px; display: block; margin: 5px 0;'>
                        python -c "import pywinpty; print('✓ Works!')"
                    </code>
                </p>
                
                <h3 style='color: #6A8759;'>Workaround:</h3>
                <p style='color: #D4D4D4;'>
                    For now, use <strong>Shift+F10</strong> (Run) for non-interactive scripts,
                    or run your script directly in a PowerShell/CMD window.
                </p>
            </div>
        """)
        msg_widget.setStyleSheet("background-color: #1E1E1E; border: none;")
        layout.addWidget(msg_widget)
    
    def init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Control bar
        control_bar = QHBoxLayout()
        control_bar.setSpacing(5)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setToolTip("Clear terminal output")
        self.clear_btn.clicked.connect(self.clear_output)
        
        self.kill_btn = QPushButton("Stop")
        self.kill_btn.setToolTip("Terminate running process")
        self.kill_btn.clicked.connect(self.kill_process)
        self.kill_btn.setEnabled(False)
        
        self.ctrlc_btn = QPushButton("Ctrl+C")
        self.ctrlc_btn.setToolTip("Send interrupt signal (Ctrl+C)")
        self.ctrlc_btn.clicked.connect(self.send_ctrl_c)
        self.ctrlc_btn.setEnabled(False)
        
        control_bar.addWidget(self.clear_btn)
        control_bar.addWidget(self.kill_btn)
        control_bar.addWidget(self.ctrlc_btn)
        control_bar.addStretch()
        
        layout.addLayout(control_bar)
        
        # Web view for rendered output with colors
        self.web = QWebEngineView()
        self.web.setHtml(self._get_initial_html())
        self.web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.web)
        
        # Input field
        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type here and press Enter to send to process...")
        self.input_field.returnPressed.connect(self.on_send_input)
        self.input_field.setEnabled(False)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setToolTip("Send input to process")
        self.send_btn.clicked.connect(self.on_send_input)
        self.send_btn.setEnabled(False)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        
        layout.addLayout(input_layout)
    
    def _get_initial_html(self):
        """Get initial HTML for the terminal"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {
                    background-color: #1E1E1E;
                    color: #D4D4D4;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 14px;
                    margin: 0;
                    padding: 10px;
                    overflow-y: auto;
                }
                pre {
                    margin: 0;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
                .prompt {
                    color: #6A8759;
                    font-weight: bold;
                }
                .error {
                    color: #BC3F3C;
                }
                .success {
                    color: #6A8759;
                }
                .info {
                    color: #6A9FE0;
                }
            </style>
        </head>
        <body>
            <pre id="output"></pre>
        </body>
        </html>
        """
    
    def run_command(self, command: str, working_dir: str = None):
        """
        Run a command in the interactive terminal
        
        Args:
            command: Command to execute (e.g., "python script.py")
            working_dir: Working directory for the command
        """
        if not WINPTY_AVAILABLE:
            return
        
        if self._pty:
            self.append_styled("Process already running", "error")
            return
        
        try:
            # Change to working directory if specified
            if working_dir:
                import os
                os.chdir(working_dir)
            
            # Spawn PTY process
            self._pty = pywinpty.PtyProcess.spawn(command)
            
            # Enable input controls
            self.input_field.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.kill_btn.setEnabled(True)
            self.ctrlc_btn.setEnabled(True)
            self.input_field.setFocus()
            
            # Show command
            self.append_styled(f"$ {command}", "prompt")
            
            # Start reader thread
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()
            
        except Exception as e:
            self.append_styled(f"Failed to start process: {str(e)}", "error")
            self._pty = None
            self._disable_input()
    
    def _reader_loop(self):
        """Background thread to read from PTY and send to GUI"""
        try:
            while True:
                if not self._pty:
                    break
                
                try:
                    # Read bytes from PTY
                    data = self._pty.read(1024)
                except EOFError:
                    # Process closed
                    break
                
                if not data:
                    time.sleep(0.01)
                    continue
                
                # Decode bytes to text
                if isinstance(data, bytes):
                    text = data.decode('utf-8', errors='replace')
                else:
                    text = str(data)
                
                # Convert ANSI codes to HTML
                if self.ansi_converter:
                    html_fragment = self.ansi_converter.convert(text, full=False)
                else:
                    # Fallback: escape HTML and preserve formatting
                    html_fragment = html.escape(text).replace('\n', '<br>').replace(' ', '&nbsp;')
                
                # Send to GUI thread
                self._signals.html_ready.emit(html_fragment)
            
            # Get exit code
            try:
                exit_code = self._pty.wait()
            except Exception:
                exit_code = 0
            
            self._signals.finished.emit(exit_code)
            
        except Exception as e:
            self._signals.html_ready.emit(f"<span class='error'>Reader error: {html.escape(str(e))}</span>")
    
    def append_html(self, html_fragment: str):
        """Append HTML fragment to terminal output (thread-safe)"""
        js = f"""
        (function() {{
            let output = document.getElementById('output');
            if (output) {{
                output.insertAdjacentHTML('beforeend', `{html_fragment}`);
                window.scrollTo(0, document.body.scrollHeight);
            }}
        }})();
        """
        self.web.page().runJavaScript(js)
    
    def append_styled(self, text: str, style: str = "info"):
        """Append styled text to terminal"""
        escaped = html.escape(text)
        html_fragment = f"<span class='{style}'>{escaped}</span><br>"
        self.append_html(html_fragment)
    
    def on_send_input(self):
        """Send input from the input field to the process"""
        if not self._pty:
            return
        
        text = self.input_field.text()
        
        # Save to history
        if text and (not self.history or self.history[-1] != text):
            self.history.append(text)
        self.hist_index = len(self.history)
        
        try:
            # Write to PTY with newline
            self._pty.write((text + "\n").encode('utf-8'))
        except Exception as e:
            self.append_styled(f"Write error: {str(e)}", "error")
        
        self.input_field.clear()
    
    def send_ctrl_c(self):
        """Send Ctrl+C (interrupt) to the running process"""
        if self._pty:
            try:
                self._pty.write(b'\x03')
                self.append_styled("^C", "info")
            except Exception as e:
                self.append_styled(f"Failed to send Ctrl+C: {str(e)}", "error")
    
    def kill_process(self):
        """Forcefully terminate the running process"""
        if self._pty:
            try:
                self._pty.kill()
                self.append_styled("Process terminated", "info")
            except Exception as e:
                self.append_styled(f"Kill failed: {str(e)}", "error")
            finally:
                self._pty = None
                self._disable_input()
    
    def on_process_finished(self, exit_code: int):
        """Handle process completion"""
        if exit_code == 0:
            self.append_styled(f"Process finished with exit code {exit_code}", "success")
        else:
            self.append_styled(f"Process finished with exit code {exit_code}", "error")
        
        self._pty = None
        self._disable_input()
    
    def _disable_input(self):
        """Disable input controls"""
        self.input_field.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.kill_btn.setEnabled(False)
        self.ctrlc_btn.setEnabled(False)
    
    def clear_output(self):
        """Clear the terminal output"""
        self.web.setHtml(self._get_initial_html())
    
    def eventFilter(self, obj, event):
        """Handle keyboard events for input history"""
        if obj is self.input_field and event.type() == event.KeyPress:
            key = event.key()
            
            if key == Qt.Key_Up:
                # Navigate up in history
                if self.history and self.hist_index > 0:
                    self.hist_index -= 1
                    self.input_field.setText(self.history[self.hist_index])
                    return True
            
            elif key == Qt.Key_Down:
                # Navigate down in history
                if self.history and self.hist_index < len(self.history) - 1:
                    self.hist_index += 1
                    self.input_field.setText(self.history[self.hist_index])
                    return True
                elif self.hist_index == len(self.history) - 1:
                    self.hist_index = len(self.history)
                    self.input_field.clear()
                    return True
        
        return super().eventFilter(obj, event)
