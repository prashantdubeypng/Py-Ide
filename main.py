import sys, os, io, subprocess, json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QPlainTextEdit, QTextEdit, QSplitter, QFileSystemModel,
    QTreeView, QInputDialog, QMessageBox, QMenuBar, QMenu, QAction,
    QStatusBar, QLabel, QTabWidget, QToolBar, QFileDialog, QLineEdit, QToolButton,
    QCompleter, QToolTip
)
from PyQt5.QtGui import QFont, QColor, QPalette, QTextCharFormat, QSyntaxHighlighter, QPainter, QTextFormat, QIcon, QTextCursor, QKeyEvent, QBrush
from PyQt5.QtCore import Qt, QDir, QRect, QRegExp, QSize, QProcess, QTimer, QStringListModel, QPoint

# Import Jedi for autocomplete and hover docs
try:
    import jedi
    JEDI_AVAILABLE = True
except ImportError:
    JEDI_AVAILABLE = False


# Line number widget for editor
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


# Linter Error Highlighter
class LintHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.errors = []

    def set_errors(self, errors):
        """Set linting errors and rehighlight"""
        self.errors = errors
        self.rehighlight()

    def highlightBlock(self, text):
        """Underline errors in red"""
        for err in self.errors:
            if self.currentBlock().blockNumber() + 1 == err.get("line", -1):
                fmt = QTextCharFormat()
                fmt.setUnderlineColor(QColor("#FF5555"))
                fmt.setUnderlineStyle(QTextCharFormat.WaveUnderline)
                column = err.get("column", 0)
                length = len(text) - column if column < len(text) else len(text)
                self.setFormat(column, length, fmt)


# Code editor with line numbers, autocomplete, and hover docs
class CodeEditor(QPlainTextEdit):
    def __init__(self, parent_ide=None):
        super().__init__()
        self.parent_ide = parent_ide
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()
        
        # Autocomplete
        self.completer = None
        self.autocomplete_timer = QTimer()
        self.autocomplete_timer.setSingleShot(True)
        self.autocomplete_timer.timeout.connect(self.show_autocomplete)
        
        # Linter highlighter
        self.lint_highlighter = LintHighlighter(self.document())
        
        # Enable mouse tracking for hover
        self.setMouseTracking(True)
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.show_hover_doc)
        
    def lineNumberAreaWidth(self):
        digits = len(str(max(1, self.blockCount())))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor(49, 51, 53))  # PyCharm line number bg

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor(128, 128, 128))  # Line number color
                painter.drawText(0, int(top), self.lineNumberArea.width() - 5, 
                               self.fontMetrics().height(), Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(47, 51, 55) 
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)
    
    def keyPressEvent(self, event):
        """Handle key press for autocomplete trigger"""
        super().keyPressEvent(event)
        
        # Trigger autocomplete after typing letters
        if event.text() and (event.text().isalnum() or event.text() == '.'):
            self.autocomplete_timer.start(150)
        
        # Accept autocomplete suggestion
        if self.completer and self.completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
                self.completer.activated.emit(self.completer.currentCompletion())
                return
    
    def show_autocomplete(self):
        """Show autocomplete suggestions using Jedi"""
        if not JEDI_AVAILABLE:
            return
        
        try:
            cursor = self.textCursor()
            code = self.toPlainText()
            line = cursor.blockNumber() + 1
            column = cursor.positionInBlock()
            
            # Get completions from Jedi
            script = jedi.Script(code)
            completions = script.complete(line, column)
            
            if completions:
                words = [c.name for c in completions[:20]]  # Limit to 20
                
                # Create completer
                self.completer = QCompleter(words, self)
                self.completer.setWidget(self)
                self.completer.setCompletionMode(QCompleter.PopupCompletion)
                self.completer.setCaseSensitivity(Qt.CaseInsensitive)
                self.completer.activated.connect(self.insert_completion)
                
                # Show popup
                rect = self.cursorRect()
                rect.setWidth(self.completer.popup().sizeHintForColumn(0)
                             + self.completer.popup().verticalScrollBar().sizeHint().width())
                self.completer.complete(rect)
        except Exception as e:
            pass  # Silently fail
    
    def insert_completion(self, completion):
        """Insert the selected completion"""
        if self.completer:
            cursor = self.textCursor()
            # Get current word
            cursor.select(QTextCursor.WordUnderCursor)
            cursor.removeSelectedText()
            cursor.insertText(completion)
            self.setTextCursor(cursor)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for hover docs"""
        super().mouseMoveEvent(event)
        if JEDI_AVAILABLE:
            self.hover_position = event.pos()
            self.hover_timer.start(300)
    
    def show_hover_doc(self):
        """Show documentation tooltip on hover"""
        if not JEDI_AVAILABLE or not hasattr(self, 'hover_position'):
            return
        
        try:
            cursor = self.cursorForPosition(self.hover_position)
            line = cursor.blockNumber() + 1
            column = cursor.positionInBlock()
            code = self.toPlainText()
            
            script = jedi.Script(code)
            help_text = script.help(line, column)
            
            if help_text:
                doc = help_text[0].docstring()
                if doc:
                    # Show tooltip
                    QToolTip.showText(
                        self.mapToGlobal(self.hover_position),
                        f"<pre>{doc[:500]}</pre>",  # Limit length
                        self
                    )
        except Exception:
            pass  # Silently fail
    
    def set_lint_errors(self, errors):
        """Set linting errors from external linter"""
        self.lint_highlighter.set_errors(errors)


# Python syntax highlighter
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        
        
        self.highlightingRules = []
        
        # Keywords
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor(204, 120, 50))  # Orange
        keywords = ["def", "class", "import", "from", "as", "if", "elif", "else",
                   "for", "while", "return", "try", "except", "finally", "with",
                   "True", "False", "None", "and", "or", "not", "in", "is", "lambda",
                   "yield", "break", "continue", "pass", "raise", "assert", "del",
                   "global", "nonlocal", "async", "await"]
        for word in keywords:
            pattern = QRegExp(f"\\b{word}\\b")
            self.highlightingRules.append((pattern, keywordFormat))
        
        # Built-in functions
        builtinFormat = QTextCharFormat()
        builtinFormat.setForeground(QColor(152, 118, 170))  # Purple
        builtins = ["print", "len", "range", "str", "int", "float", "list", "dict",
                   "set", "tuple", "open", "input", "type", "isinstance", "enumerate",
                   "zip", "map", "filter", "sum", "max", "min", "abs", "all", "any"]
        for word in builtins:
            pattern = QRegExp(f"\\b{word}\\b")
            self.highlightingRules.append((pattern, builtinFormat))
        
        # Strings
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor(106, 135, 89))  # Green
        self.highlightingRules.append((QRegExp("\".*\""), stringFormat))
        self.highlightingRules.append((QRegExp("'.*'"), stringFormat))
        
        # Comments
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor(128, 128, 128))  # Gray
        self.highlightingRules.append((QRegExp("#[^\n]*"), commentFormat))
        
        # Numbers
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor(104, 151, 187))  # Blue
        self.highlightingRules.append((QRegExp("\\b[0-9]+\\b"), numberFormat))

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)


# Interactive Terminal Widget
class TerminalWidget(QWidget):
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
        
        # Process
        self.process = None
        
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
        
        # Handle 'run' command - execute current file in editor
        if command == "run":
            if self.parent_ide:
                self.parent_ide.run_code()
            else:
                self.output.append(f"<span style='color:#BC3F3C;'>Error: No file to run</span>")
            self.show_prompt()
            return
        
        # Handle 'python run <file>' - run specific Python file
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
        
        # Handle cd command specially
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
        if command == "clear" or command == "cls":
            self.output.clear()
            self.output.append(f"<span style='color:#6A8759;'>Terminal ready. Working directory: {self.working_dir}</span>")
            self.show_prompt()
            return
        
        # Execute other commands
        try:
            # Use shell for Windows compatibility
            if sys.platform == "win32":
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=self.working_dir
                )
            else:
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
                safe_stdout = stdout.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                self.output.insertHtml(f"<span style='color:#A9B7C6;'>{safe_stdout}</span>")

            if stderr:
                safe_stderr = stderr.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                self.output.insertHtml(f"<span style='color:#BC3F3C;'>{safe_stderr}</span>")

                
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


class IDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Py-IDE")
        self.resize(1600, 1000)
        
        # Track current project directory
        self.project_dir = os.getcwd()
        self.current_file = None
        self.open_files = {}  # Track open files by tab index
        
        # Autosave timer - saves 1 second after typing stops
        self.autosave_timer = QTimer()
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.timeout.connect(self.auto_save_file)
        
        # QProcess for running code asynchronously
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        
        self.apply_pycharm_theme()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # === File Explorer ===
        self.model = QFileSystemModel()
        self.model.setRootPath(self.project_dir)
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self.project_dir))
        self.tree.setColumnWidth(0, 250)
        self.tree.doubleClicked.connect(self.open_file)
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        for i in range(1, self.model.columnCount()):
            self.tree.hideColumn(i)
        self.tree.setStyleSheet("""
            QTreeView {
                background-color: #2B2B2B;
                color: #BBBBBB;
                border: none;
                border-right: 1px solid #323232;
                outline: 0;
            }
            QTreeView::item {
                padding: 4px;
            }
            QTreeView::item:hover {
                background-color: #3C3F41;
            }
            QTreeView::item:selected {
                background-color: #4B6EAF;
                color: white;
            }
        """)

        # === Tab Widget for multiple files ===
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #2B2B2B;
            }
            QTabBar::tab {
                background-color: #3C3F41;
                color: #BBBBBB;
                padding: 8px 20px;
                border: none;
                border-right: 1px solid #2B2B2B;
            }
            QTabBar::tab:selected {
                background-color: #2B2B2B;
                color: #FFFFFF;
            }
            QTabBar::tab:hover {
                background-color: #4B4F51;
            }
        """)
        
        # Create initial editor tab
        self.create_new_editor_tab("Untitled")

        # === Terminal (replacing Console) ===
        self.terminal = TerminalWidget(self.project_dir, self)

        # === Vertical Splitter (Editor Tabs | Terminal) ===
        editor_splitter = QSplitter(Qt.Orientation.Vertical)
        editor_splitter.addWidget(self.tab_widget)
        editor_splitter.addWidget(self.terminal)
        editor_splitter.setSizes([700, 200])
        editor_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #323232;
                height: 1px;
            }
        """)

        # === Vertical Navigation Bar ===
        self.navbar = QVBoxLayout()
        self.navbar.setContentsMargins(0, 0, 0, 0)
        self.navbar.setSpacing(10)
        self.folder_btn = QToolButton()
        self.folder_btn.setIcon(QIcon.fromTheme("folder"))
        self.folder_btn.setToolTip("Show/Hide File Explorer")
        self.folder_btn.setStyleSheet("background-color: #2B2B2B; color: #BBBBBB; border-radius: 6px; padding: 8px;")
        self.folder_btn.clicked.connect(self.toggle_file_explorer)
        self.navbar.addWidget(self.folder_btn)
        self.terminal_btn = QToolButton()
        self.terminal_btn.setIcon(QIcon.fromTheme("terminal"))
        self.terminal_btn.setToolTip("Show/Hide Terminal")
        self.terminal_btn.setStyleSheet("background-color: #2B2B2B; color: #BBBBBB; border-radius: 6px; padding: 8px;")
        self.terminal_btn.clicked.connect(self.toggle_terminal)
        self.navbar.addWidget(self.terminal_btn)
        self.navbar.addStretch(1)
        self.navbar_widget = QWidget()
        self.navbar_widget.setLayout(self.navbar)
        self.navbar_widget.setFixedWidth(48)

        # === Main Splitter (Files | Editor/Console) ===
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(self.navbar_widget)
        self.main_splitter.addWidget(self.tree)
        self.main_splitter.addWidget(editor_splitter)
        self.main_splitter.setSizes([48, 250, 1350])
        self.main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #323232;
                width: 1px;
            }
        """)

        # Set central widget
        self.setCentralWidget(self.main_splitter)
        
        # Create status bar
        self.create_status_bar()
    
    def apply_pycharm_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2B2B2B;
            }
            QMenuBar {
                background-color: #3C3F41;
                color: #BBBBBB;
                border-bottom: 1px solid #323232;
                padding: 2px;
            }
            QMenuBar::item {
                padding: 5px 10px;
                background-color: transparent;
            }
            QMenuBar::item:selected {
                background-color: #4B6EAF;
            }
            QMenu {
                background-color: #3C3F41;
                color: #BBBBBB;
                border: 1px solid #555555;
            }
            QMenu::item {
                padding: 5px 30px;
            }
            QMenu::item:selected {
                background-color: #4B6EAF;
            }
            QToolBar {
                background-color: #3C3F41;
                border: none;
                border-bottom: 1px solid #323232;
                spacing: 3px;
                padding: 3px;
            }
            QToolButton {
                background-color: transparent;
                color: #BBBBBB;
                padding: 5px;
                border: none;
                border-radius: 3px;
            }
            QToolButton:hover {
                background-color: #4B4F51;
            }
            QToolButton:pressed {
                background-color: #555555;
            }
            QStatusBar {
                background-color: #3C3F41;
                color: #BBBBBB;
                border-top: 1px solid #323232;
            }
        """)
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New File", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        new_py_file_action = QAction("New Python File...", self)
        new_py_file_action.setShortcut("Ctrl+Alt+N")
        new_py_file_action.triggered.connect(self.new_python_file)
        file_menu.addAction(new_py_file_action)
        
        file_menu.addSeparator()
        
        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)
        
        open_folder_action = QAction("Open Folder...", self)
        open_folder_action.setShortcut("Ctrl+K")
        open_folder_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_folder_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(lambda: self.get_current_editor().undo())
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(lambda: self.get_current_editor().redo())
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("Cut", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(lambda: self.get_current_editor().cut())
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(lambda: self.get_current_editor().copy())
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(lambda: self.get_current_editor().paste())
        edit_menu.addAction(paste_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        toggle_files_action = QAction("Project Files", self)
        toggle_files_action.setShortcut("Alt+1")
        toggle_files_action.triggered.connect(self.toggle_file_explorer)
        view_menu.addAction(toggle_files_action)
        
        # Run menu
        run_menu = menubar.addMenu("Run")
        
        run_action = QAction("Run", self)
        run_action.setShortcut("Shift+F10")
        run_action.triggered.connect(self.run_code)
        run_menu.addAction(run_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        ai_action = QAction("AI Suggestion", self)
        ai_action.triggered.connect(self.ai_suggestion)
        tools_menu.addAction(ai_action)
        
        visualize_action = QAction("Visualize Code", self)
        visualize_action.triggered.connect(self.visualize_code)
        tools_menu.addAction(visualize_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(lambda: QMessageBox.about(self, "About", 
            "IDE\nBuilt with PyQt5"))
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Add toolbar actions
        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)
        
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file_dialog)
        toolbar.addAction(open_action)
        
        open_folder_action = QAction("📁 Open Folder", self)
        open_folder_action.triggered.connect(self.open_folder)
        toolbar.addAction(open_folder_action)
        
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        run_action = QAction("▶ Run", self)
        run_action.triggered.connect(self.run_code)
        toolbar.addAction(run_action)
        
        toolbar.addSeparator()
        
        ai_action = QAction("AI", self)
        ai_action.triggered.connect(self.ai_suggestion)
        toolbar.addAction(ai_action)
    
    def create_status_bar(self):
        """Create PyCharm-like status bar"""
        status = QStatusBar()
        self.setStatusBar(status)
        
        # Line and column indicator
        self.line_col_label = QLabel("Ln 1, Col 1")
        status.addPermanentWidget(self.line_col_label)
        
        # Update line/col on cursor movement
        def update_cursor_position():
            editor = self.get_current_editor()
            if editor:
                cursor = editor.textCursor()
                line = cursor.blockNumber() + 1
                col = cursor.columnNumber() + 1
                self.line_col_label.setText(f"Ln {line}, Col {col}")
        
        # Connect to current editor if exists
        if self.tab_widget.count() > 0:
            editor = self.get_current_editor()
            if editor:
                editor.cursorPositionChanged.connect(update_cursor_position)
        
        status.showMessage("Ready")
    
    def create_new_editor_tab(self, title="Untitled", content=""):
        """Create a new editor tab with minimap"""
        # Main editor
        editor = CodeEditor(parent_ide=self)
        editor.setFont(QFont("Consolas", 12))
        editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #2B2B2B;
                color: #A9B7C6;
                border: none;
                selection-background-color: #214283;
            }
        """)
        editor.setPlainText(content)
        
        # Add syntax highlighting
        highlighter = PythonHighlighter(editor.document())
        
        # Create minimap
        minimap = QPlainTextEdit()
        minimap.setReadOnly(True)
        minimap.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        minimap.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        minimap.setFont(QFont("Consolas", 2))
        minimap.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1A1A1A;
                color: #555555;
                border: none;
                border-left: 1px solid #323232;
            }
        """)
        minimap.setPlainText(content)
        minimap.setFixedWidth(120)
        
        # Sync minimap with editor
        editor.textChanged.connect(lambda: minimap.setPlainText(editor.toPlainText()))
        editor.verticalScrollBar().valueChanged.connect(
            lambda v: minimap.verticalScrollBar().setValue(int(v * minimap.verticalScrollBar().maximum() / max(1, editor.verticalScrollBar().maximum())))
        )
        
        # Container for editor + minimap
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(editor)
        layout.addWidget(minimap)
        container.setLayout(layout)
        
        # Add tab
        index = self.tab_widget.addTab(container, title)
        self.tab_widget.setCurrentIndex(index)
        
        # Store editor reference in container for easy access
        container.editor = editor
        container.minimap = minimap
        
        # Connect cursor position change
        editor.cursorPositionChanged.connect(self.update_cursor_position)
        
        # Connect text changes to autosave and linting
        editor.textChanged.connect(self.trigger_autosave)
        editor.textChanged.connect(lambda: self.trigger_linting(editor))
        
        return editor
    
    def get_current_editor(self):
        """Get the currently active editor"""
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, CodeEditor):
            return current_widget
        elif hasattr(current_widget, 'editor'):
            return current_widget.editor
        return None
    
    def update_cursor_position(self):
        """Update cursor position in status bar"""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.line_col_label.setText(f"Ln {line}, Col {col}")
    
    def new_file(self):
        """Create a new file tab"""
        self.create_new_editor_tab("Untitled")
        self.statusBar().showMessage("New file created")
    
    def close_tab(self, index):
        """Close a tab"""
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(index)
            if index in self.open_files:
                del self.open_files[index]
        else:
            self.statusBar().showMessage("Cannot close the last tab")

    def toggle_file_explorer(self):
        """Toggle file explorer visibility"""
        visible = not self.tree.isVisible()
        self.tree.setVisible(visible)
        if visible:
            self.main_splitter.setSizes([250, 1350])
            self.statusBar().showMessage("Project view opened")
        else:
            self.main_splitter.setSizes([0, 1600])
            self.statusBar().showMessage("Project view closed")
    
    def toggle_terminal(self):
        visible = self.terminal.isVisible()
        self.terminal.setVisible(not visible)
        if not visible:
            self.statusBar().showMessage("Terminal opened")
        else:
            self.statusBar().showMessage("Terminal hidden")
    
    def open_file_dialog(self):
        """Open file dialog to select and open a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", self.project_dir,
            "Python Files (*.py);;All Files (*.*)"
        )
        if file_path:
            self.open_file_by_path(file_path)
    
    def open_file(self, index):
        """Open file from tree view"""
        path = self.model.filePath(index)
        if os.path.isfile(path):
            self.open_file_by_path(path)
    
    def open_file_by_path(self, path):
        """Open a file by its path"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check if file is already open
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == os.path.basename(path):
                    self.tab_widget.setCurrentIndex(i)
                    self.statusBar().showMessage(f"Switched to {os.path.basename(path)}")
                    return
            
            # Create new tab
            filename = os.path.basename(path)
            editor = self.create_new_editor_tab(filename, content)
            
            # Store file path
            current_index = self.tab_widget.currentIndex()
            self.open_files[current_index] = path
            self.current_file = path
            
            self.terminal.output.append(f"<span style='color:#6A8759;'>Opened: {path}</span>")
            self.statusBar().showMessage(f"Opened {filename}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open file: {str(e)}")
            self.statusBar().showMessage("Error opening file")
    
    def save_file(self):
        """Save the current file"""
        current_index = self.tab_widget.currentIndex()
        
        if current_index in self.open_files:
            # Save to existing file
            path = self.open_files[current_index]
            self.save_to_path(path)
        else:
            # No path yet, use Save As
            self.save_file_as()
    
    def save_file_as(self):
        """Save current file with a new name"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File As", self.project_dir,
            "Python Files (*.py);;All Files (*.*)"
        )
        if file_path:
            self.save_to_path(file_path)
            # Update tab title and stored path
            current_index = self.tab_widget.currentIndex()
            self.open_files[current_index] = file_path
            self.tab_widget.setTabText(current_index, os.path.basename(file_path))
            self.current_file = file_path
    
    def save_to_path(self, path):
        """Save content to specified path"""
        try:
            editor = self.get_current_editor()
            if editor:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(editor.toPlainText())
                self.terminal.output.append(f"<span style='color:#6A8759;'>Saved: {path}</span>")
                self.statusBar().showMessage(f"Saved {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not save file: {str(e)}")
            self.statusBar().showMessage("Error saving file")
    
    def trigger_autosave(self):
        """Trigger autosave with 1 second delay after typing stops"""
        current_index = self.tab_widget.currentIndex()
        
        # Only autosave if file has a path (not "Untitled")
        if current_index in self.open_files:
            self.autosave_timer.start(1000)  # Wait 1 second after last keystroke
    
    def auto_save_file(self):
        """Automatically save the current file"""
        current_index = self.tab_widget.currentIndex()
        
        if current_index not in self.open_files:
            return  # Don't autosave untitled files
        
        filepath = self.open_files[current_index]
        
        try:
            editor = self.get_current_editor()
            if editor:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(editor.toPlainText())
                
                # Show subtle save indicator
                filename = os.path.basename(filepath)
                self.statusBar().showMessage(f"💾 Auto-saved: {filename}", 2000)
                
        except Exception as e:
            self.terminal.output.append(f"<span style='color:#BC3F3C;'>Auto-save failed: {str(e)}</span>")
    
    def trigger_linting(self, editor):
        """Trigger linting with delay"""
        if not hasattr(self, 'lint_timer'):
            self.lint_timer = QTimer()
            self.lint_timer.setSingleShot(True)
            self.lint_timer.timeout.connect(lambda: self.run_linter(editor))
        
        self.lint_timer.start(2000)  # Wait 2 seconds after last edit
    
    def run_linter(self, editor):
        """Run pylint on current file"""
        current_index = self.tab_widget.currentIndex()
        
        if current_index not in self.open_files:
            return  # Don't lint unsaved files
        
        filepath = self.open_files[current_index]
        
        if not filepath.endswith('.py'):
            return  # Only lint Python files
        
        # Run pylint using QProcess
        if not hasattr(self, 'lint_process'):
            self.lint_process = QProcess(self)
            self.lint_process.finished.connect(lambda: self.handle_lint_results(editor))
        
        if self.lint_process.state() == QProcess.Running:
            return  # Already running
        
        # Run pylint with JSON output
        self.lint_process.start(sys.executable, [
            '-m', 'pylint',
            '--output-format=json',
            '--disable=C,R',  # Disable convention and refactoring messages
            filepath
        ])
    
    def handle_lint_results(self, editor):
        """Handle pylint results"""
        try:
            output = self.lint_process.readAllStandardOutput().data().decode()
            if output:
                issues = json.loads(output)
                errors = []
                
                for issue in issues:
                    if issue.get('type') in ['error', 'warning']:
                        errors.append({
                            'line': issue.get('line', 0),
                            'column': issue.get('column', 0),
                            'message': issue.get('message', '')
                        })
                
                # Update editor's lint highlighter
                editor.set_lint_errors(errors)
                
                if errors:
                    self.statusBar().showMessage(f"⚠️ {len(errors)} linting issue(s) found", 3000)
        except Exception:
            pass  # Silently fail
    
    def run_code(self):
        """Run the current Python code using QProcess for real-time output"""
        # Auto-save before running
        self.auto_save_file()
        
        editor = self.get_current_editor()
        if not editor:
            self.statusBar().showMessage("No file to run")
            return
        
        code = editor.toPlainText()
        
        # If already running, kill the old process
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.terminal.output.append("<span style='color:#BC3F3C;'>⚠ Previous process terminated.</span><br>")
        
        # Clear terminal and show running message
        self.terminal.output.clear()
        self.terminal.output.append("<span style='color:#6A8759;'>▶ Running code...</span><br>")
        self.terminal.show_prompt()
        
        # Set up QProcess to run Python code
        self.process.setProgram(sys.executable)
        self.process.setArguments(["-u", "-c", code])  # -u for unbuffered output
        self.process.setWorkingDirectory(self.project_dir)
        self.process.setProcessChannelMode(QProcess.MergedChannels)  # Merge stdout and stderr
        
        # Start the process
        self.process.start()
        
        if not self.process.waitForStarted(3000):
            self.terminal.output.append("<span style='color:#BC3F3C;'>Error: Failed to start process</span>")
            self.statusBar().showMessage("Failed to start process")
        else:
            self.statusBar().showMessage("🔄 Running code...")
    
    def handle_stdout(self):
        """Handle standard output from QProcess (real-time streaming)"""
        data = self.process.readAllStandardOutput().data().decode(errors='replace')
        if data:
            # Escape HTML and convert newlines to <br>
            safe_data = data.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            self.terminal.output.insertHtml(f"<span style='color:#A9B7C6;'>{safe_data}</span>")
            self.terminal.output.moveCursor(QTextCursor.End)
    
    def handle_stderr(self):
        """Handle standard error from QProcess (real-time streaming)"""
        data = self.process.readAllStandardError().data().decode(errors='replace')
        if data:
            # Escape HTML and convert newlines to <br>
            safe_data = data.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            self.terminal.output.insertHtml(f"<span style='color:#BC3F3C;'>{safe_data}</span>")
            self.terminal.output.moveCursor(QTextCursor.End)
    
    def process_finished(self, exit_code, exit_status):
        """Handle process completion"""
        self.terminal.output.append("<br>")
        
        if exit_status == QProcess.NormalExit:
            if exit_code == 0:
                self.terminal.output.append("<span style='color:#6A8759;'>✓ Process finished with exit code 0</span>")
                self.statusBar().showMessage("✓ Execution completed successfully")
            else:
                self.terminal.output.append(f"<span style='color:#BC3F3C;'>✗ Process finished with exit code {exit_code}</span>")
                self.statusBar().showMessage(f"✗ Execution completed with errors (exit code {exit_code})")
        else:
            self.terminal.output.append("<span style='color:#BC3F3C;'>✗ Process crashed or was terminated</span>")
            self.statusBar().showMessage("✗ Process crashed")
        
        self.terminal.output.append("<br>")
        self.terminal.show_prompt()
    
    def ai_suggestion(self):
        """Provide AI code suggestions"""
        editor = self.get_current_editor()
        if not editor:
            return
        
        code = editor.toPlainText()
        self.terminal.output.clear()
        # self.terminal.output.append("<span style='color:#6A8759;'>🤖 AI Analyzing code...</span>")
        # self.terminal.output.append("\n<span style='color:#A9B7C6;'>💡 <b>Suggestions:</b></span>")
        # self.terminal.output.append("<span style='color:#A9B7C6;'>  • Consider using list comprehensions for better readability</span>")
        # self.terminal.output.append("<span style='color:#A9B7C6;'>  • Add type hints to function parameters</span>")
        # self.terminal.output.append("<span style='color:#A9B7C6;'>  • Use descriptive variable names</span>")
        # self.terminal.output.append("<span style='color:#A9B7C6;'>  • Consider adding docstrings to functions</span>")
        # self.statusBar().showMessage("AI suggestions generated")
    
    def visualize_code(self):
        """Visualize data structures and algorithms"""
        self.terminal.output.clear()
        # self.terminal.output.append("<span style='color:#6A8759;'>📊 Visualizing code structure...</span>")
        # self.terminal.output.append("\n<span style='color:#A9B7C6;'>Data structure visualization coming soon!</span>")
        # self.terminal.output.append("<span style='color:#A9B7C6;'>This will show visual representations of:</span>")
        # self.terminal.output.append("<span style='color:#A9B7C6;'>  • Lists and Arrays</span>")
        # self.terminal.output.append("<span style='color:#A9B7C6;'>  • Trees and Graphs</span>")
        # self.terminal.output.append("<span style='color:#A9B7C6;'>  • Algorithm execution flow</span>")
        # self.statusBar().showMessage("Visualization initialized")
    
    def open_folder(self):
        """Let user pick a new project folder and update the file tree"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Project Folder", 
            self.project_dir,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder:
            self.project_dir = folder
            self.model.setRootPath(self.project_dir)
            self.tree.setRootIndex(self.model.index(self.project_dir))
            
            # Update window title with folder name
            folder_name = os.path.basename(folder)
            self.setWindowTitle(f"{folder_name}")
            
            # Show the file explorer if it's hidden
            if not self.tree.isVisible():
                self.tree.setVisible(True)
                self.main_splitter.setSizes([250, 1350])
            
            # Log to terminal
            self.terminal.output.append(f"<span style='color:#6A8759;'>📂 Opened folder: {folder}</span>")
            self.statusBar().showMessage(f"Opened folder: {folder_name}")
            
            # Update terminal working directory
            self.terminal.working_dir = folder
    
    def new_python_file(self):
        """Create a new Python file in the project directory"""
        filename, ok = QInputDialog.getText(
            self, 
            "New Python File", 
            "Enter file name (without .py extension):"
        )
        
        if ok and filename:
            if not filename.endswith('.py'):
                filename += '.py'
            
            filepath = os.path.join(self.project_dir, filename)
            
            # Check if file already exists
            if os.path.exists(filepath):
                QMessageBox.warning(self, "File Exists", f"File '{filename}' already exists!")
                return
            
            try:
                # Open the file in editor
                self.open_file_by_path(filepath)
                self.terminal.output.append(f"<span style='color:#6A8759;'>✓ Created Python file: {filename}</span>")
                self.statusBar().showMessage(f"Created {filename}")
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create file: {str(e)}")
                self.statusBar().showMessage("Error creating file")
    
    def show_tree_context_menu(self, position):
        """Show context menu on right-click in file tree"""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #3C3F41;
                color: #BBBBBB;
                border: 1px solid #555555;
            }
            QMenu::item {
                padding: 5px 30px;
            }
            QMenu::item:selected {
                background-color: #4B6EAF;
            }
        """)
        
        index = self.tree.indexAt(position)
        
        # New Python File action
        new_py_action = QAction("New Python File", self)
        new_py_action.triggered.connect(self.new_python_file)
        menu.addAction(new_py_action)
        
        menu.addSeparator()
        
        # Delete action (only if item is selected)
        if index.isValid():
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.delete_file(index))
            menu.addAction(delete_action)
        
        # Refresh action
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_tree)
        menu.addAction(refresh_action)
        
        menu.exec_(self.tree.viewport().mapToGlobal(position))
    
    def delete_file(self, index):
        """Delete the selected file or folder"""
        path = self.model.filePath(index)
        filename = os.path.basename(path)
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{filename}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                
                self.terminal.output.append(f"<span style='color:#6A8759;'>✓ Deleted: {filename}</span>")
                self.statusBar().showMessage(f"Deleted {filename}")
                self.refresh_tree()
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not delete: {str(e)}")
                self.statusBar().showMessage("Error deleting file")
    
    def refresh_tree(self):
        """Refresh the file tree"""
        self.model.setRootPath("")
        self.model.setRootPath(self.project_dir)
        self.tree.setRootIndex(self.model.index(self.project_dir))
        self.statusBar().showMessage("File tree refreshed")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ide = IDE()
    ide.show()
    sys.exit(app.exec_())
