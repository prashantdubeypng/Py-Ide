"""
Interactive Terminal Widget
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTextEdit
from PyQt5.QtGui import QFont, QTextCursor, QKeyEvent
from PyQt5.QtCore import Qt
import subprocess
import sys
import os


class TerminalWidget(QWidget):
    """Interactive terminal with command history and IDE integration"""
    
    def __init__(self, working_dir, parent_ide=None):
        super().__init__()
        self.working_dir = working_dir
        self.parent_ide = parent_ide
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Output area
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setStyleSheet("""
            QTextEdit {
                background-color: #1E1F22;
                color: #A9B7C6;
                border: none;
            }
        """)
        
        # Input line
        self.input_line = QLineEdit()
        self.input_line.setFont(QFont("Consolas", 10))
        self.input_line.setStyleSheet("""
            QLineEdit {
                background-color: #2B2B2B;
                color: #A9B7C6;
                border: none;
                border-top: 1px solid #323232;
                padding: 5px;
            }
        """)
        self.input_line.setPlaceholderText("Type command and press Enter...")
        self.input_line.returnPressed.connect(self.execute_command)
        
        layout.addWidget(self.output)
        layout.addWidget(self.input_line)
        self.setLayout(layout)
        
        # Command history
        self.history = []
        self.history_index = -1
        
        # Welcome message
        self.output.append(f"<span style='color:#6A8759;'>Terminal ready. Working directory: {self.working_dir}</span>")
        self.show_prompt()
    
    def show_prompt(self):
        """Show command prompt"""
        prompt = f"<span style='color:#6897BB;'>{os.path.basename(self.working_dir)}></span> "
        self.output.insertHtml(prompt)
        self.output.moveCursor(QTextCursor.End)
    
    def execute_command(self):
        """Execute the command entered by user"""
        command = self.input_line.text().strip()
        if not command:
            return
        
        # Add to history
        self.history.append(command)
        self.history_index = len(self.history)
        
        # Display command
        self.output.insertHtml(f"<span style='color:#A9B7C6;'>{command}</span><br>")
        self.output.moveCursor(QTextCursor.End)
        self.input_line.clear()
        
        # Handle 'run' command
        if command == "run":
            if self.parent_ide:
                self.parent_ide.run_code()
            else:
                self.output.append(f"<span style='color:#BC3F3C;'>Error: No file to run</span>")
            self.show_prompt()
            return
        
        # Handle 'python run <file>'
        if command.startswith("python run "):
            filename = command[11:].strip()
            filepath = os.path.join(self.working_dir, filename) if not os.path.isabs(filename) else filename
            
            if os.path.isfile(filepath):
                try:
                    process = subprocess.Popen(
                        [sys.executable, filepath],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=self.working_dir
                    )
                    stdout, stderr = process.communicate(timeout=30)
                    
                    if stdout:
                        self.output.insertHtml(f"<span style='color:#A9B7C6;'>{stdout.replace('<', '&lt;').replace('>', '&gt;').replace(chr(10), '<br>')}</span>")
                    if stderr:
                        self.output.insertHtml(f"<span style='color:#BC3F3C;'>{stderr.replace('<', '&lt;').replace('>', '&gt;').replace(chr(10), '<br>')}</span>")
                    
                    if process.returncode == 0:
                        self.output.append(f"<span style='color:#6A8759;'>Process finished with exit code 0</span>")
                    else:
                        self.output.append(f"<span style='color:#BC3F3C;'>Process finished with exit code {process.returncode}</span>")
                        
                except subprocess.TimeoutExpired:
                    self.output.append(f"<span style='color:#BC3F3C;'>Command timeout (30 seconds)</span>")
                except Exception as e:
                    self.output.append(f"<span style='color:#BC3F3C;'>Error: {str(e)}</span>")
            else:
                self.output.append(f"<span style='color:#BC3F3C;'>python: can't open file '{filepath}': [Errno 2] No such file or directory</span>")
            
            self.show_prompt()
            return
        
        # Handle cd command
        if command.startswith("cd "):
            path = command[3:].strip().strip('"').strip("'")
            if path:
                new_dir = os.path.join(self.working_dir, path) if not os.path.isabs(path) else path
                if os.path.isdir(new_dir):
                    self.working_dir = os.path.abspath(new_dir)
                    self.output.append(f"<span style='color:#6A8759;'>Changed directory to: {self.working_dir}</span>")
                else:
                    self.output.append(f"<span style='color:#BC3F3C;'>Directory not found: {path}</span>")
            self.show_prompt()
            return
        
        # Handle clear command
        if command in ["clear", "cls"]:
            self.output.clear()
            self.output.append(f"<span style='color:#6A8759;'>Terminal ready. Working directory: {self.working_dir}</span>")
            self.show_prompt()
            return
        
        # Execute other commands
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.working_dir
            )
            
            stdout, stderr = process.communicate(timeout=30)
            
            if stdout:
                self.output.insertHtml(f"<span style='color:#A9B7C6;'>{stdout.replace('<', '&lt;').replace('>', '&gt;').replace(chr(10), '<br>')}</span>")
            if stderr:
                self.output.insertHtml(f"<span style='color:#BC3F3C;'>{stderr.replace('<', '&lt;').replace('>', '&gt;').replace(chr(10), '<br>')}</span>")
                
        except subprocess.TimeoutExpired:
            self.output.append(f"<span style='color:#BC3F3C;'>Command timeout (30 seconds)</span>")
        except Exception as e:
            self.output.append(f"<span style='color:#BC3F3C;'>Error: {str(e)}</span>")
        
        self.show_prompt()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events for history navigation"""
        if event.key() == Qt.Key_Up:
            if self.history and self.history_index > 0:
                self.history_index -= 1
                self.input_line.setText(self.history[self.history_index])
        elif event.key() == Qt.Key_Down:
            if self.history and self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.input_line.setText(self.history[self.history_index])
            else:
                self.history_index = len(self.history)
                self.input_line.clear()
        else:
            super().keyPressEvent(event)
