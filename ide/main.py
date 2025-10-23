"""
Py-IDE - Main Window
Modular, high-performance architecture with threading and persistence
"""
import sys
import os
import time
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QToolBar, QAction, QFileDialog, QMessageBox,
    QStatusBar, QLabel, QToolButton, QApplication, QTextBrowser
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer, QProcess, QUrl

# Import modular components
from ide.editor import CodeEditor, PythonHighlighter, LintHighlighter
from ide.terminal import TerminalWidget
# Try to import pywinpty-based terminal, fall back to simple version
try:
    from ide.interactive_terminal import InteractiveTerminalWidget
except Exception:
    from ide.interactive_terminal_simple import SimpleInteractiveTerminal as InteractiveTerminalWidget
from ide.explorer import FileExplorer
from ide.utils.settings import SettingsManager
from ide.utils.logger import logger
from ide.utils.workers import FileOperationWorker, LintWorker

# Import flow analyzer components
from ide.analyzer.flow_analyzer import FunctionFlowAnalyzer
from ide.analyzer.graph_builder import GraphBuilder
from ide.analyzer.visualizer import Visualizer

# Import AI components
from ide.ai_chat_panel import AIChatPanel
from ide.graph_ai_integration import GraphAIAssistant
from ide.ai_code_assistant import AICodeAssistant
from ide.ai_settings_dialog import AISettingsDialog


class IDE(QMainWindow):
    """Main IDE window with modular architecture"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize settings and logger
        self.settings = SettingsManager()
        logger.info("IDE starting...")
        
        # Load last project or use current directory
        self.project_dir = self.settings.get("last_project", os.getcwd())
        if not os.path.exists(self.project_dir):
            self.project_dir = os.getcwd()
        
        self.current_file = None
        self.open_files = {}
        
        # Setup UI
        self.setWindowTitle("Py-IDE")
        self.resize(1600, 1000)
        
        # Apply theme
        self.apply_pycharm_theme()
        
        # Create menu and toolbar
        self.create_menu_bar()
        self.create_toolbar()
        
        # === Vertical Navigation Bar ===
        self.create_navbar()
        
        # === File Explorer ===
        self.file_explorer = FileExplorer(self.project_dir, self)
        self.file_explorer.setVisible(self.settings.get("file_explorer_visible", True))
        
        # === Tab Widget for Editors ===
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
        
        # Create initial editor
        self.create_new_editor_tab("Untitled")
        
        # === Terminal ===
        # Create tab widget for terminals
        self.terminal_tabs = QTabWidget()
        self.terminal_tabs.setTabPosition(QTabWidget.South)
        
        # Old terminal (output only)
        self.terminal = TerminalWidget(self.project_dir, self)
        self.terminal_tabs.addTab(self.terminal, "Output")
        
        # New interactive terminal
        self.interactive_terminal = InteractiveTerminalWidget(self)
        self.terminal_tabs.addTab(self.interactive_terminal, "Interactive")
        
        self.terminal_tabs.setVisible(self.settings.get("terminal_visible", True))
        
        # === AI Chat Panel ===
        self.ai_chat_panel = AIChatPanel(self.settings, parent_ide=self)
        self.ai_chat_panel.setVisible(self.settings.get("ai_chat_visible", False))
        self.ai_chat_panel.setMinimumWidth(300)
        
        # === Vertical Splitter (Editor | Terminal) ===
        editor_splitter = QSplitter(Qt.Vertical)
        editor_splitter.addWidget(self.tab_widget)
        editor_splitter.addWidget(self.terminal_tabs)
        editor_splitter.setSizes([500, 150])
        
        # === Main Splitter (Navbar | Explorer | Editor | AI Chat) - VS Code style ===
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(self.navbar_widget)
        self.main_splitter.addWidget(self.file_explorer)
        self.main_splitter.addWidget(editor_splitter)
        self.main_splitter.addWidget(self.ai_chat_panel)  # AI Chat on right side
        self.main_splitter.setSizes([48, 250, 900, 350])
        
        self.setCentralWidget(self.main_splitter)
        
        # === Status Bar ===
        self.create_status_bar()
        
        # === Autosave Timer ===
        self.autosave_timer = QTimer()
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.timeout.connect(self.auto_save_file)
        
        # === QProcess for code execution ===
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        
        # Worker threads
        self.workers = []
        
        # AI components
        self.graph_ai_assistant = GraphAIAssistant(self.ai_chat_panel.ai_manager)
        self.ai_code_assistant = AICodeAssistant(self.ai_chat_panel.ai_manager)
        
        logger.info("IDE initialized successfully")
    
    def create_navbar(self):
        """Create vertical navigation bar"""
        navbar_layout = QVBoxLayout()
        navbar_layout.setContentsMargins(0, 10, 0, 10)
        navbar_layout.setSpacing(5)
        
        # Folder button
        self.folder_btn = QToolButton()
        self.folder_btn.setText("📁")
        self.folder_btn.setFont(QFont("Segoe UI Emoji", 16))
        self.folder_btn.setToolTip("Toggle File Explorer (Alt+1)")
        self.folder_btn.setFixedSize(40, 40)
        self.folder_btn.setStyleSheet("""
            QToolButton {
                background-color: #2B2B2B;
                color: #BBBBBB;
                border: 1px solid #3C3F41;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #3C3F41;
                border: 1px solid #4B6EAF;
            }
        """)
        self.folder_btn.clicked.connect(self.toggle_file_explorer)
        navbar_layout.addWidget(self.folder_btn)
        
        # Terminal button
        self.terminal_btn = QToolButton()
        self.terminal_btn.setText("📥")
        self.terminal_btn.setFont(QFont("Segoe UI Emoji", 16))
        self.terminal_btn.setToolTip("Toggle Terminal")
        self.terminal_btn.setFixedSize(40, 40)
        self.terminal_btn.setStyleSheet("""
            QToolButton {
                background-color: #2B2B2B;
                color: #BBBBBB;
                border: 1px solid #3C3F41;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #3C3F41;
                border: 1px solid #4B6EAF;
            }
        """)
        self.terminal_btn.clicked.connect(self.toggle_terminal)
        navbar_layout.addWidget(self.terminal_btn)
        
        # AI Chat button
        self.ai_btn = QToolButton()
        self.ai_btn.setText("🤖")
        self.ai_btn.setFont(QFont("Segoe UI Emoji", 16))
        self.ai_btn.setToolTip("Toggle AI Chat (Ctrl+Shift+A)")
        self.ai_btn.setFixedSize(40, 40)
        self.ai_btn.setStyleSheet("""
            QToolButton {
                background-color: #2B2B2B;
                color: #BBBBBB;
                border: 1px solid #3C3F41;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #3C3F41;
                border: 1px solid #4B6EAF;
            }
        """)
        self.ai_btn.clicked.connect(self.toggle_ai_chat)
        navbar_layout.addWidget(self.ai_btn)
        
        navbar_layout.addStretch(1)
        
        # Settings button (at bottom)
        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙️")
        self.settings_btn.setFont(QFont("Segoe UI Emoji", 16))
        self.settings_btn.setToolTip("AI Settings")
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.setStyleSheet("""
            QToolButton {
                background-color: #2B2B2B;
                color: #BBBBBB;
                border: 1px solid #3C3F41;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #3C3F41;
                border: 1px solid #4B6EAF;
            }
        """)
        self.settings_btn.clicked.connect(self.open_ai_settings)
        navbar_layout.addWidget(self.settings_btn)
        
        self.navbar_widget = QWidget()
        self.navbar_widget.setLayout(navbar_layout)
        self.navbar_widget.setFixedWidth(48)
        self.navbar_widget.setStyleSheet("background-color: #2B2B2B; border-right: 1px solid #323232;")
    
    def apply_pycharm_theme(self):
        """Apply dark theme"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2B2B2B;
            }
            QMenuBar {
                background-color: #3C3F41;
                color: #BBBBBB;
                border-bottom: 1px solid #323232;
            }
            QMenuBar::item:selected {
                background-color: #4B6EAF;
            }
            QMenu {
                background-color: #3C3F41;
                color: #BBBBBB;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #4B6EAF;
            }
            QToolBar {
                background-color: #3C3F41;
                border-bottom: 1px solid #323232;
            }
            QStatusBar {
                background-color: #3C3F41;
                color: #BBBBBB;
                border-top: 1px solid #323232;
            }
        """)
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New File", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        new_py_action = QAction("New Python File...", self)
        new_py_action.setShortcut("Ctrl+Alt+N")
        new_py_action.triggered.connect(self.new_python_file)
        file_menu.addAction(new_py_action)
        
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
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        toggle_explorer_action = QAction("Toggle File Explorer", self)
        toggle_explorer_action.setShortcut("Alt+1")
        toggle_explorer_action.triggered.connect(self.toggle_file_explorer)
        view_menu.addAction(toggle_explorer_action)
        
        # Run menu
        run_menu = menubar.addMenu("Run")
        
        run_action = QAction("Run", self)
        run_action.setShortcut("Shift+F10")
        run_action.triggered.connect(self.run_code)
        run_menu.addAction(run_action)
        
        run_interactive_action = QAction("▶️ Run in Interactive Terminal", self)
        run_interactive_action.setShortcut("Ctrl+F10")
        run_interactive_action.setToolTip("Run in interactive terminal (supports input())")
        run_interactive_action.triggered.connect(self.run_in_interactive_terminal)
        run_menu.addAction(run_interactive_action)
        
        run_trace_action = QAction("🔍 Run with Trace", self)
        run_trace_action.setShortcut("Ctrl+Shift+F10")
        run_trace_action.setToolTip("Run with live function tracing and visualization")
        run_trace_action.triggered.connect(self.run_with_trace)
        run_menu.addAction(run_trace_action)
        
        run_menu.addSeparator()
        
        view_trace_action = QAction("📊 View Last Trace", self)
        view_trace_action.setToolTip("Visualize the most recent execution trace")
        view_trace_action.triggered.connect(self.view_last_trace)
        run_menu.addAction(view_trace_action)
        
        # AI Tools menu
        ai_menu = menubar.addMenu("AI Tools")
        
        gen_docstring_action = QAction("📝 Generate Docstring", self)
        gen_docstring_action.setShortcut("Ctrl+Shift+D")
        gen_docstring_action.setToolTip("Generate AI docstring for current function")
        gen_docstring_action.triggered.connect(self.generate_docstring_for_current)
        ai_menu.addAction(gen_docstring_action)
        
        refactor_hints_action = QAction("🔄 Refactoring Hints", self)
        refactor_hints_action.setShortcut("Ctrl+Shift+R")
        refactor_hints_action.setToolTip("Get AI refactoring suggestions")
        refactor_hints_action.triggered.connect(self.show_refactoring_hints)
        ai_menu.addAction(refactor_hints_action)
        
        analyze_func_action = QAction("🧠 Analyze Function", self)
        analyze_func_action.setShortcut("Ctrl+Shift+F")
        analyze_func_action.setToolTip("Complete AI analysis with metrics and summary")
        analyze_func_action.triggered.connect(self.analyze_current_function)
        ai_menu.addAction(analyze_func_action)
        
        ai_menu.addSeparator()
        
        scan_project_action = QAction("🔍 Scan Project", self)
        scan_project_action.setToolTip("Scan and cache function summaries for entire project")
        scan_project_action.triggered.connect(self.scan_project_with_ai)
        ai_menu.addAction(scan_project_action)
        
        clear_cache_action = QAction("🗑️ Clear AI Cache", self)
        clear_cache_action.triggered.connect(self.clear_ai_cache)
        ai_menu.addAction(clear_cache_action)
        
        ai_menu.addSeparator()
        
        ai_stats_action = QAction("📊 AI Statistics", self)
        ai_stats_action.triggered.connect(self.show_ai_stats)
        ai_menu.addAction(ai_stats_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(lambda: QMessageBox.about(self, "About", 
            "Py-IDE\nModular Architecture with Advanced Features"))
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create toolbar"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
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
        
        # Sandbox toggle button
        self.sandbox_action = QAction("🔒 Sandbox: OFF", self)
        self.sandbox_action.setToolTip("Toggle Docker Sandbox (Secure Execution)")
        self.sandbox_action.setCheckable(True)
        self.sandbox_action.setChecked(self.settings.get("use_docker_sandbox", False))
        self.sandbox_action.triggered.connect(self.toggle_sandbox)
        self._update_sandbox_button()
        toolbar.addAction(self.sandbox_action)
        
        toolbar.addSeparator()
        
        # Flow Analyzer button
        flow_action = QAction("📊 Analyze Flow", self)
        flow_action.setToolTip("Analyze Function Call Flow")
        flow_action.triggered.connect(self.run_flow_analysis)
        toolbar.addAction(flow_action)
        
        toolbar.addSeparator()
        
        # AI Chat button in toolbar
        ai_chat_action = QAction("💬 AI Chat", self)
        ai_chat_action.setToolTip("Toggle AI Chat (Ctrl+Shift+A)")
        ai_chat_action.setShortcut("Ctrl+Shift+A")
        ai_chat_action.triggered.connect(self.toggle_ai_chat)
        toolbar.addAction(ai_chat_action)
        
        # AI Suggestions button
        ai_action = QAction("✨ Suggest", self)
        ai_action.setToolTip("Get AI Suggestions")
        ai_action.triggered.connect(self.ai_suggestion)
        toolbar.addAction(ai_action)
    
    def create_status_bar(self):
        """Create status bar"""
        status = QStatusBar()
        self.setStatusBar(status)
        
        self.line_col_label = QLabel("Ln 1, Col 1")
        status.addPermanentWidget(self.line_col_label)
        
        status.showMessage("Ready")
    
    def create_new_editor_tab(self, title="Untitled", content=""):
        """Create a new editor tab"""
        editor = CodeEditor(self)
        editor.setPlainText(content)
        
        # Syntax highlighting is already set up in CodeEditor.__init__
        
        # Connect text changed for autosave
        editor.textChanged.connect(self.trigger_autosave)
        editor.cursorPositionChanged.connect(self.update_cursor_position)
        
        index = self.tab_widget.addTab(editor, title)
        self.tab_widget.setCurrentIndex(index)
        
        return editor
    
    def get_current_editor(self):
        """Get currently active editor"""
        return self.tab_widget.currentWidget()
    
    def update_cursor_position(self):
        """Update cursor position in status bar"""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.line_col_label.setText(f"Ln {line}, Col {col}")
    
    def trigger_autosave(self):
        """Trigger autosave with delay"""
        if self.settings.get("autosave_enabled", True):
            current_index = self.tab_widget.currentIndex()
            if current_index in self.open_files:
                self.autosave_timer.start(self.settings.get("autosave_interval", 1000))
    
    def auto_save_file(self):
        """Auto save current file"""
        current_index = self.tab_widget.currentIndex()
        if current_index in self.open_files:
            filepath = self.open_files[current_index]
            editor = self.get_current_editor()
            if editor:
                try:
                    worker = FileOperationWorker("write", filepath, editor.toPlainText())
                    worker.finished.connect(lambda op, path: self.statusBar().showMessage(f"💾 Auto-saved: {os.path.basename(path)}", 2000))
                    worker.start()
                    self.workers.append(worker)
                    logger.info(f"Auto-saved: {filepath}")
                except Exception as e:
                    logger.error(f"Auto-save failed: {e}")
    
    def new_file(self):
        """Create new file tab"""
        self.create_new_editor_tab("Untitled")
        self.statusBar().showMessage("New file created")
    
    def new_python_file(self):
        """Create new Python file"""
        if self.file_explorer:
            self.file_explorer.new_python_file()
    
    def close_tab(self, index):
        """Close editor tab"""
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(index)
            if index in self.open_files:
                del self.open_files[index]
    
    def toggle_file_explorer(self):
        """Toggle file explorer visibility"""
        visible = not self.file_explorer.isVisible()
        self.file_explorer.setVisible(visible)
        self.settings.set("file_explorer_visible", visible)
        self.statusBar().showMessage("File explorer " + ("opened" if visible else "closed"))
    
    def toggle_terminal(self):
        """Toggle terminal visibility"""
        visible = not self.terminal_tabs.isVisible()
        self.terminal_tabs.setVisible(visible)
        self.settings.set("terminal_visible", visible)
        self.statusBar().showMessage("Terminal " + ("opened" if visible else "closed"))
    
    def toggle_ai_chat(self):
        """Toggle AI chat panel visibility"""
        visible = not self.ai_chat_panel.isVisible()
        self.ai_chat_panel.setVisible(visible)
        self.settings.set("ai_chat_visible", visible)
        self.statusBar().showMessage("AI Chat " + ("opened" if visible else "closed"))
    
    def open_ai_settings(self):
        """Open AI settings dialog"""
        try:
            dialog = AISettingsDialog(self.settings, self)
            dialog.settings_changed.connect(self.on_ai_settings_changed)
            
            if dialog.exec_() == dialog.Accepted:
                self.statusBar().showMessage("AI settings updated successfully")
                logger.info("AI settings updated")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error opening AI settings: {e}\n{error_details}")
            QMessageBox.warning(
                self,
                "Settings Error",
                f"Failed to open AI settings:\n{str(e)}\n\nCheck logs for details."
            )
    
    def on_ai_settings_changed(self):
        """Handle AI settings changes - reinitialize AI providers"""
        try:
            # Reinitialize AI manager with new settings
            from ide.utils.ai_manager import AIManager
            new_ai_manager = AIManager(self.settings)
            
            # Update AI chat panel's manager
            self.ai_chat_panel.ai_manager = new_ai_manager
            
            # Update AI assistants
            self.graph_ai_assistant = GraphAIAssistant(new_ai_manager)
            self.ai_code_assistant = AICodeAssistant(new_ai_manager)
            
            logger.info("AI providers reinitialized with new settings")
            self.statusBar().showMessage("AI providers updated")
        except Exception as e:
            logger.error(f"Error reinitializing AI providers: {e}")
            QMessageBox.warning(
                self,
                "AI Update Error",
                f"Failed to update AI providers: {str(e)}"
            )
    
    def toggle_sandbox(self):
        """Toggle Docker sandbox mode"""
        enabled = self.sandbox_action.isChecked()
        self.settings.set("use_docker_sandbox", enabled)
        self._update_sandbox_button()
        
        status = "enabled" if enabled else "disabled"
        self.statusBar().showMessage(f"Docker sandbox {status}")
        logger.info(f"Docker sandbox {status}")
    
    def _update_sandbox_button(self):
        """Update sandbox button text and style"""
        enabled = self.settings.get("use_docker_sandbox", False)
        if enabled:
            self.sandbox_action.setText("🔒 Sandbox: ON")
            self.sandbox_action.setToolTip("Docker Sandbox Enabled - Code runs securely in container")
        else:
            self.sandbox_action.setText("🔓 Sandbox: OFF")
            self.sandbox_action.setToolTip("Local Execution - Click to enable Docker sandbox")
    
    def open_file_dialog(self):
        """Open file dialog"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open File", self.project_dir, "Python Files (*.py);;All Files (*.*)"
        )
        if filepath:
            self.open_file_by_path(filepath)
    
    def open_file_by_path(self, filepath):
        """Open file by path"""
        # Check if already open
        for i in range(self.tab_widget.count()):
            if i in self.open_files and self.open_files[i] == filepath:
                self.tab_widget.setCurrentIndex(i)
                return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            filename = os.path.basename(filepath)
            editor = self.create_new_editor_tab(filename, content)
            
            current_index = self.tab_widget.currentIndex()
            self.open_files[current_index] = filepath
            self.current_file = filepath
            
            self.settings.add_recent_file(filepath)
            self.statusBar().showMessage(f"Opened {filename}")
            logger.info(f"Opened file: {filepath}")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open file: {str(e)}")
            logger.error(f"Error opening file: {e}")
    
    def save_file(self):
        """Save current file"""
        current_index = self.tab_widget.currentIndex()
        
        if current_index in self.open_files:
            filepath = self.open_files[current_index]
            self.save_to_path(filepath)
        else:
            self.save_file_as()
    
    def save_file_as(self):
        """Save file as"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save File As", self.project_dir, "Python Files (*.py);;All Files (*.*)"
        )
        if filepath:
            self.save_to_path(filepath)
            current_index = self.tab_widget.currentIndex()
            self.open_files[current_index] = filepath
            self.tab_widget.setTabText(current_index, os.path.basename(filepath))
    
    def save_to_path(self, filepath):
        """Save to specific path"""
        editor = self.get_current_editor()
        if editor:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(editor.toPlainText())
                self.statusBar().showMessage(f"Saved {os.path.basename(filepath)}")
                logger.info(f"Saved file: {filepath}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not save file: {str(e)}")
                logger.error(f"Error saving file: {e}")
    
    def open_folder(self):
        """Open project folder"""
        folder = QFileDialog.getExistingDirectory(self, "Open Folder", self.project_dir)
        if folder:
            self.project_dir = folder
            self.file_explorer.set_project_dir(folder)
            self.terminal.working_dir = folder
            self.settings.set("last_project", folder)
            
            folder_name = os.path.basename(folder)
            self.setWindowTitle(f"Py-IDE - {folder_name}")
            self.statusBar().showMessage(f"Opened folder: {folder_name}")
            logger.info(f"Opened folder: {folder}")
    
    def run_code(self):
        """Run current code using SecureExecutor (Docker sandbox) or QProcess fallback"""
        editor = self.get_current_editor()
        if not editor:
            return
        
        # Autosave before running
        self.auto_save_file()
        
        # Show terminal if hidden
        if not self.terminal.isVisible():
            self.terminal.setVisible(True)
        
        code = editor.toPlainText()
        self.terminal.output.clear()
        
        # Try secure execution first
        use_sandbox = self.settings.get("use_docker_sandbox", False)
        
        if use_sandbox:
            self._run_code_sandboxed(code)
        else:
            self._run_code_qprocess(code)
    
    def _run_code_sandboxed(self, code: str):
        """Run code in Docker sandbox"""
        try:
            from ide.utils.secure_executor import get_executor
            
            self.terminal.output.append("<span style='color:#6A8759;'>🔒 Running in secure sandbox...</span>")
            self.statusBar().showMessage("Running code in sandbox...")
            
            # Get executor
            executor = get_executor(
                mem_limit=self.settings.get("sandbox_mem_limit", "256m"),
                cpu_quota=self.settings.get("sandbox_cpu_quota", 50000),
                enable_validation=self.settings.get("sandbox_validation", True)
            )
            
            # Check Docker availability
            if not executor.is_docker_available():
                self.terminal.output.append("<span style='color:#CC7832;'>⚠️ Docker not available, falling back to local execution</span>")
                self._run_code_qprocess(code)
                return
            
            # Run in background thread to keep UI responsive
            from PyQt5.QtCore import QThread, pyqtSignal
            
            class SandboxWorker(QThread):
                finished = pyqtSignal(dict)
                
                def __init__(self, executor, code):
                    super().__init__()
                    self.executor = executor
                    self.code = code
                
                def run(self):
                    result = self.executor.run_code(self.code, timeout=10)
                    self.finished.emit(result)
            
            self.sandbox_worker = SandboxWorker(executor, code)
            self.sandbox_worker.finished.connect(self._on_sandbox_finished)
            self.sandbox_worker.start()
            
        except ImportError:
            self.terminal.output.append("<span style='color:#CC7832;'>⚠️ Docker library not installed, using local execution</span>")
            self.terminal.output.append("<span style='color:#A9B7C6;'>Install with: pip install docker</span>")
            self._run_code_qprocess(code)
        except Exception as e:
            self.terminal.output.append(f"<span style='color:#BC3F3C;'>❌ Sandbox error: {str(e)}</span>")
            self.terminal.output.append("<span style='color:#A9B7C6;'>Falling back to local execution...</span>")
            self._run_code_qprocess(code)
    
    def _on_sandbox_finished(self, result: dict):
        """Handle sandbox execution completion"""
        exit_code = result.get("exit_code", 1)
        output = result.get("output", "")
        error = result.get("error")
        
        # Display output
        if output:
            safe_output = output.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            color = "#A9B7C6" if exit_code == 0 else "#BC3F3C"
            self.terminal.output.append(f"<span style='color:{color};'>{safe_output}</span>")
        
        # Display error if any
        if error:
            self.terminal.output.append(f"<span style='color:#BC3F3C;'>Error: {error}</span>")
        
        # Status message
        if exit_code == 0:
            self.terminal.output.append("<span style='color:#6A8759;'>✓ Execution completed successfully</span>")
            self.statusBar().showMessage("Sandbox execution completed")
        else:
            self.terminal.output.append(f"<span style='color:#BC3F3C;'>✗ Execution failed (exit code {exit_code})</span>")
            self.statusBar().showMessage("Sandbox execution failed")
        
        logger.info(f"Sandbox execution completed with exit code {exit_code}")
    
    def _run_code_qprocess(self, code: str):
        """Run code using QProcess (local, unsandboxed)"""
        self.terminal.output.append("<span style='color:#6A8759;'>Running locally...</span>")
        
        # Kill previous process if running
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.terminal.output.append("<span style='color:#BC3F3C;'>Previous process terminated.</span>")
        
        # Start new process
        self.process.start(sys.executable, ["-c", code])
        self.process.setWorkingDirectory(self.project_dir)
        self.statusBar().showMessage("Running code...")
        logger.info("Running code execution (QProcess)")
    
    def handle_stdout(self):
        """Handle stdout from process"""
        data = self.process.readAllStandardOutput().data().decode()
        safe = data.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        self.terminal.output.insertHtml(f"<span style='color:#A9B7C6;'>{safe}</span>")
        self.terminal.output.moveCursor(self.terminal.output.textCursor().End)
    
    def handle_stderr(self):
        """Handle stderr from process"""
        data = self.process.readAllStandardError().data().decode()
        safe = data.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        self.terminal.output.insertHtml(f"<span style='color:#BC3F3C;'>{safe}</span>")
        self.terminal.output.moveCursor(self.terminal.output.textCursor().End)
    
    def process_finished(self):
        """Handle process completion"""
        exit_code = self.process.exitCode()
        if exit_code == 0:
            self.terminal.output.append("<br><span style='color:#6A8759;'>Process finished with exit code 0</span>")
            self.statusBar().showMessage("Execution completed successfully")
            
            # If this was a traced execution, offer to view the trace
            if hasattr(self, 'current_trace_path') and os.path.exists(self.current_trace_path):
                self.terminal.output.append(
                    f"<br><span style='color:#6A8759;'>📊 Trace saved: {os.path.basename(self.current_trace_path)}</span>"
                )
                self.terminal.output.append(
                    "<span style='color:#A9B7C6;'>Use 'View Last Trace' from Run menu to visualize</span>"
                )
        else:
            self.terminal.output.append(f"<br><span style='color:#BC3F3C;'>Process finished with exit code {exit_code}</span>")
            self.statusBar().showMessage("Execution completed with errors")
        logger.info(f"Process finished with exit code {exit_code}")
    
    def view_last_trace(self):
        """Visualize the last execution trace"""
        if not hasattr(self, 'current_trace_path') or not os.path.exists(self.current_trace_path):
            QMessageBox.information(
                self,
                "No Trace Available",
                "No trace data found.\n\n"
                "To generate a trace:\n"
                "1. Open a Python file (without input() calls)\n"
                "2. Press Ctrl+Shift+F10 (Run with Trace)\n"
                "3. After execution, use this option to visualize\n\n"
                "Note: Scripts with input() cannot be traced.\n"
                "Use test_trace_demo.py as an example."
            )
            return
        
        try:
            import json
            from ide.runtime_tracer import TraceReplay
            
            # Load trace data
            with open(self.current_trace_path, 'r') as f:
                trace_data = json.load(f)
            
            events = trace_data.get('events', [])
            stats = trace_data.get('stats', {})
            
            if not events:
                QMessageBox.information(self, "Empty Trace", "The trace file contains no events.")
                return
            
            # Show trace statistics in terminal
            if not self.terminal.isVisible():
                self.terminal.setVisible(True)
            
            self.terminal.output.clear()
            self.terminal.output.append("<span style='color:#6A8759;'>📊 Trace Statistics</span>")
            self.terminal.output.append(f"<span style='color:#A9B7C6;'>File: {os.path.basename(self.current_trace_path)}</span>")
            self.terminal.output.append(f"<span style='color:#A9B7C6;'>Total events: {len(events)}</span>")
            self.terminal.output.append(f"<span style='color:#A9B7C6;'>Functions traced: {len(stats)}</span>")
            self.terminal.output.append("<br><span style='color:#6A8759;'>Top Functions by Call Count:</span>")
            
            # Sort by call count
            sorted_stats = sorted(stats.items(), key=lambda x: x[1].get('call_count', 0), reverse=True)[:15]
            
            self.terminal.output.append(f"<span style='color:#A9B7C6;'>{'Function':<35} {'Calls':<8} {'Total(ms)':<12} {'Avg(ms)':<10}</span>")
            self.terminal.output.append("<span style='color:#555555;'>" + "-" * 70 + "</span>")
            
            for func_name, data in sorted_stats:
                call_count = data.get('call_count', 0)
                total_time = data.get('total_time', 0) * 1000  # Convert to ms
                avg_time = (total_time / call_count) if call_count > 0 else 0
                
                # Color code by performance
                if avg_time > 10:
                    color = "#BC3F3C"  # Red for slow
                elif avg_time > 1:
                    color = "#CC7832"  # Orange for medium
                else:
                    color = "#6A8759"  # Green for fast
                
                self.terminal.output.append(
                    f"<span style='color:{color};'>{func_name[:35]:<35} {call_count:<8} {total_time:<12.2f} {avg_time:<10.2f}</span>"
                )
            
            self.statusBar().showMessage(f"Loaded trace: {os.path.basename(self.current_trace_path)}")
            
            # Ask user if they want to visualize the call graph
            reply = QMessageBox.question(
                self,
                "Visualize Trace",
                "Do you want to create an interactive call graph visualization with trace overlay?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self._create_trace_visualization(trace_data)
            
        except Exception as e:
            logger.error(f"Error viewing trace: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(
                self,
                "Trace Error",
                f"Failed to load trace:\n{str(e)}"
            )
    
    def _create_trace_visualization(self, trace_data: dict):
        """Create interactive call graph with trace overlay"""
        try:
            self.terminal.output.append("<br><span style='color:#6A8759;'>📊 Creating trace visualization...</span>")
            
            # Determine which file/directory to analyze
            # Option 1: Analyze the traced file's directory
            traced_file = self.current_file
            if traced_file and os.path.exists(traced_file):
                analyze_dir = os.path.dirname(traced_file)
            else:
                analyze_dir = self.project_dir
            
            # Run flow analysis on the directory
            analyzer = FunctionFlowAnalyzer()
            self.terminal.output.append(f"<span style='color:#A9B7C6;'>Analyzing: {analyze_dir}</span>")
            functions = analyzer.analyze_project(analyze_dir)
            
            if not functions:
                self.terminal.output.append("<span style='color:#CC7832;'>⚠️ No functions found to visualize</span>")
                return
            
            # Build call graph
            builder = GraphBuilder()
            graph = builder.build_from_functions(functions)
            
            self.terminal.output.append(f"<span style='color:#A9B7C6;'>✓ Built graph with {len(functions)} functions</span>")
            
            # Get AI explanations if available
            ai_explanations = {}
            if self.settings.get("flow_ai_enabled", True):
                try:
                    self.terminal.output.append("<span style='color:#A9B7C6;'>🤖 Generating AI insights...</span>")
                    
                    # Generate explanations for functions that were actually executed
                    trace_stats = trace_data.get('stats', {})
                    executed_functions = [name for name, stats in trace_stats.items() if stats.get('call_count', 0) > 0]
                    
                    for func_name in executed_functions[:10]:  # Limit to top 10 for speed
                        if func_name in [f.name for f in functions]:
                            func = next((f for f in functions if f.name == func_name), None)
                            if func:
                                explanation = self.graph_ai_assistant.get_node_explanation(func_name, func.signature or "", func.docstring or "")
                                if explanation:
                                    ai_explanations[func_name] = explanation
                    
                    self.terminal.output.append(f"<span style='color:#A9B7C6;'>✓ Generated {len(ai_explanations)} AI explanations</span>")
                except Exception as e:
                    logger.error(f"Error generating AI explanations: {e}")
                    self.terminal.output.append(f"<span style='color:#CC7832;'>⚠️ AI explanations unavailable: {str(e)}</span>")
            
            # Create visualization with trace overlay
            visualizer = Visualizer()
            html_path = visualizer.render_with_trace_overlay(
                graph,
                trace_data,
                ai_explanations=ai_explanations if ai_explanations else None,
                output_filename="traced_flow.html"
            )
            
            self.terminal.output.append(f"<span style='color:#6A8759;'>✓ Visualization created!</span>")
            
            # Open in IDE's web view
            self._open_visualization(html_path)
            
        except Exception as e:
            logger.error(f"Error creating trace visualization: {e}")
            import traceback
            traceback.print_exc()
            self.terminal.output.append(f"<span style='color:#BC3F3C;'>❌ Visualization error: {str(e)}</span>")
    
    def _open_visualization(self, html_path: str):
        """Open visualization in browser"""
        try:
            import webbrowser
            self.terminal.output.append("<span style='color:#A9B7C6;'>🌐 Opening visualization in browser...</span>")
            webbrowser.open(f"file:///{html_path.replace(os.sep, '/')}")
            self.statusBar().showMessage("Trace visualization opened in browser")
        except Exception as e:
            logger.error(f"Error opening visualization: {e}")
            self.terminal.output.append(f"<span style='color:#BC3F3C;'>❌ Failed to open browser: {str(e)}</span>")
    
    def run_in_interactive_terminal(self):
        """Run current file in the interactive terminal"""
        if not self.current_file:
            QMessageBox.warning(
                self,
                "No File",
                "Please save the current file before running."
            )
            return
        
        # Autosave
        self.auto_save_file()
        
        # Show terminal and switch to interactive tab
        if not self.terminal_tabs.isVisible():
            self.terminal_tabs.setVisible(True)
        self.terminal_tabs.setCurrentWidget(self.interactive_terminal)
        
        # Build command using interactive_runner.py wrapper for UTF-8 support
        python_exe = sys.executable
        wrapper_script = os.path.join(os.path.dirname(__file__), 'interactive_runner.py')
        
        # Check if wrapper exists
        if not os.path.exists(wrapper_script):
            logger.warning(f"Wrapper script not found: {wrapper_script}")
            # Fallback to direct execution
            command = f'"{python_exe}" -u "{self.current_file}"'
        else:
            command = f'"{python_exe}" -u "{wrapper_script}" "{self.current_file}"'
            logger.info(f"Using wrapper: {wrapper_script}")
        
        working_dir = os.path.dirname(self.current_file)
        
        # Run in interactive terminal
        self.interactive_terminal.run_command(command, working_dir)
        
        self.statusBar().showMessage(f"Running {os.path.basename(self.current_file)} in interactive terminal...")
        logger.info(f"Running in interactive terminal: {self.current_file}")
    
    def run_with_trace(self):
        """Run current file with live tracing enabled"""
        # Must have a saved file to trace
        if not self.current_file:
            QMessageBox.warning(
                self,
                "No File",
                "Please save the current file before running with trace."
            )
            return
        
        # Check if file contains input() calls
        try:
            with open(self.current_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'input(' in content:
                    reply = QMessageBox.information(
                        self,
                        "Interactive Input Detected",
                        "This script uses input() which cannot be traced.\n\n"
                        "Tracing requires capturing function calls, but interactive\n"
                        "input blocks the tracer and prevents visualization.\n\n"
                        "Options:\n"
                        "• Click 'OK' to run in Interactive Terminal (no trace)\n"
                        "• Click 'Cancel' to modify code and remove input()\n\n"
                        "Tip: Use Ctrl+F10 to run scripts with input() normally.",
                        QMessageBox.Ok | QMessageBox.Cancel,
                        QMessageBox.Ok
                    )
                    if reply == QMessageBox.Ok:
                        # Run in interactive terminal instead (without tracing)
                        self.statusBar().showMessage("Running in interactive terminal (tracing disabled for input() scripts)...")
                        self.run_in_interactive_terminal()
                        return
                    else:
                        return
                        return
        except Exception as e:
            logger.warning(f"Could not check for input() calls: {e}")
        
        # Autosave
        self.auto_save_file()
        
        # Show terminal
        if not self.terminal.isVisible():
            self.terminal.setVisible(True)
        
        self.terminal.output.clear()
        self.terminal.output.append("<span style='color:#6A8759;'>🔍 Running with live tracing...</span>")
        self.statusBar().showMessage("Running with trace...")
        
        try:
            # Prepare trace output path
            import tempfile
            trace_dir = os.path.join(tempfile.gettempdir(), "py_ide_traces")
            os.makedirs(trace_dir, exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = os.path.splitext(os.path.basename(self.current_file))[0]
            trace_path = os.path.join(trace_dir, f"trace_{filename}_{timestamp}.json")
            
            # Get path to traced_runner.py
            ide_dir = os.path.dirname(os.path.abspath(__file__))
            runner_path = os.path.join(ide_dir, "traced_runner.py")
            
            if not os.path.exists(runner_path):
                raise FileNotFoundError(f"Traced runner not found: {runner_path}")
            
            # Kill previous process if running
            if self.process.state() == QProcess.Running:
                self.process.kill()
                self.terminal.output.append("<span style='color:#BC3F3C;'>Previous process terminated.</span>")
            
            # Start traced execution
            args = [runner_path, self.current_file, "--output", trace_path]
            self.process.start(sys.executable, args)
            self.process.setWorkingDirectory(os.path.dirname(self.current_file))
            
            # Store trace path for later visualization
            self.current_trace_path = trace_path
            
            logger.info(f"Started traced execution: {self.current_file}")
            
        except Exception as e:
            logger.error(f"Error starting traced execution: {e}")
            self.terminal.output.append(f"<span style='color:#BC3F3C;'>❌ Trace error: {str(e)}</span>")
            QMessageBox.warning(
                self,
                "Trace Error",
                f"Failed to start traced execution:\n{str(e)}"
            )
    
    def run_flow_analysis(self):
        """Run function flow analysis on project and display in IDE panel"""
        if not os.path.isdir(self.project_dir):
            QMessageBox.warning(self, "Error", "Please open a project folder first")
            return
        
        # Show progress in terminal
        if not self.terminal.isVisible():
            self.terminal.setVisible(True)
        
        self.terminal.output.clear()
        self.terminal.output.append("<span style='color:#6A8759;'>📊 Analyzing function flow...</span>")
        self.statusBar().showMessage("Running flow analysis...")
        
        try:
            # Step 1: Analyze project
            analyzer = FunctionFlowAnalyzer()
            self.terminal.output.append("<span style='color:#A9B7C6;'>🔍 Scanning Python files...</span>")
            functions = analyzer.analyze_project(self.project_dir)
            
            if not functions:
                self.terminal.output.append("<span style='color:#CC7832;'>⚠️ No functions found in project</span>")
                self.statusBar().showMessage("No functions found")
                return
            
            self.terminal.output.append(f"<span style='color:#A9B7C6;'>✓ Found {len(functions)} functions</span>")
            
            # Step 2: Build graph
            builder = GraphBuilder()
            graph = builder.build_from_functions(functions)
            
            stats = graph.get_stats()
            self.terminal.output.append(f"<span style='color:#A9B7C6;'>✓ Built graph with {stats['total_calls']} calls</span>")
            
            # Check for cycles
            cycles = graph.find_cycles()
            if cycles:
                self.terminal.output.append(f"<span style='color:#CC7832;'>⚠️ Found {len(cycles)} circular call chain(s)</span>")
            
            # Step 2.5: Generate AI insights (if enabled in settings)
            if self.settings.get("flow_ai_enabled", True):
                self.terminal.output.append("<span style='color:#A9B7C6;'>🤖 Generating AI insights...</span>")
                try:
                    complexity_insight = self.graph_ai_assistant.get_complexity_assessment({
                        "nodes": [{"name": f.name} for f in functions],
                        "edges": [(f.name, c) for f in functions for c in f.calls],
                        "cycles": cycles,
                        "stats": stats
                    })
                    self.terminal.output.append(f"<span style='color:#B8D4A8;'>💡 AI Insight: {complexity_insight[:150]}...</span>")
                    
                    # Generate function-specific explanations if enabled
                    if self.settings.get("flow_explain_enabled", True):
                        self.terminal.output.append("<span style='color:#A9B7C6;'>📝 Analyzing key functions...</span>")
                        # Analyze top 5 most complex/important functions
                        for func in sorted(functions, key=lambda f: len(f.calls), reverse=True)[:5]:
                            try:
                                explanation = self.ai_code_assistant.generate_function_summary(
                                    func.name,
                                    func.source_code if hasattr(func, 'source_code') else ""
                                )
                                if explanation:
                                    self.terminal.output.append(
                                        f"<span style='color:#9876AA;'>  • {func.name}: {explanation[:80]}...</span>"
                                    )
                            except Exception as func_err:
                                logger.debug(f"Skipping function explanation for {func.name}: {func_err}")
                except Exception as e:
                    logger.debug(f"AI insight generation optional, skipping: {e}")
                    self.terminal.output.append("<span style='color:#BBB529;'>⚠️ AI insights unavailable (check API keys)</span>")
            
            # Step 3: Optimize for visualization
            optimized_graph = builder.optimize_for_visualization(max_nodes=100)
            self.terminal.output.append("<span style='color:#A9B7C6;'>✓ Optimized graph for visualization</span>")
            
            # Step 4: Generate AI explanations for nodes (if enabled)
            ai_explanations = {}
            if self.settings.get("flow_ai_enabled", True) and self.settings.get("flow_explain_enabled", True):
                self.terminal.output.append("<span style='color:#A9B7C6;'>🤖 Generating AI explanations for interactive nodes...</span>")
                
                # Ensure AI provider is initialized
                if not self.ai_chat_panel.ai_manager.provider:
                    ai_settings = self.settings.get("ai", {})
                    provider_name = ai_settings.get("provider", "gemini")
                    self.ai_chat_panel.ai_manager.initialize_provider(provider_name)
                
                # Generate explanations for all functions (limit to top 50)
                for func_name, func_info in list(optimized_graph.nodes.items())[:50]:
                    try:
                        if func_info.source:
                            prompt = f"""Explain what this Python function does in 2-3 sentences:

```python
{func_info.source[:500]}
```

Focus on: purpose, inputs, outputs, and key logic."""
                            explanation = self.ai_chat_panel.ai_manager.generate_sync(prompt)
                            ai_explanations[func_name] = explanation
                    except Exception as e:
                        logger.debug(f"Skipping AI explanation for {func_name}: {e}")
                
                self.terminal.output.append(f"<span style='color:#B8D4A8;'>✓ Generated {len(ai_explanations)} AI explanations</span>")
            
            # Step 5: Visualize with AI explanations
            visualizer = Visualizer()
            html_path = visualizer.render_with_ai_explanations(optimized_graph, ai_explanations, "function_flow.html")
            
            self.terminal.output.append(f"<span style='color:#6A8759;'>✓ Visualization complete!</span>")
            self.terminal.output.append(f"<span style='color:#A9B7C6;'>📂 Saved to: {html_path}</span>")
            
            # Open directly in browser
            self.terminal.output.append("<span style='color:#A9B7C6;'>� Opening in browser...</span>")
            
            import webbrowser
            webbrowser.open(f"file:///{html_path.replace(os.sep, '/')}")
            
            self.statusBar().showMessage("Flow analysis complete! Graph opened in browser.")
            logger.info(f"Flow analysis completed: {html_path}")
            
        except Exception as e:
            self.terminal.output.append(f"<span style='color:#BC3F3C;'>❌ Error: {str(e)}</span>")
            self.statusBar().showMessage("Flow analysis failed")
            logger.error(f"Flow analysis error: {e}", exc_info=True)
    
    def ai_suggestion(self):
        """Show AI suggestions for current code"""
        editor = self.get_current_editor()
        if not editor:
            self.statusBar().showMessage("No editor open")
            return
        
        code = editor.toPlainText()
        if not code.strip():
            self.statusBar().showMessage("No code to analyze")
            return
        
        # Show terminal if hidden
        if not self.terminal.isVisible():
            self.terminal.setVisible(True)
        
        self.terminal.output.clear()
        self.terminal.output.append("<span style='color:#6A8759;'>🤖 AI Analyzing code...</span>")
        
        # Ensure AI provider is initialized
        if not self.ai_chat_panel.ai_manager.provider:
            ai_settings = self.settings.get("ai", {})
            provider_name = ai_settings.get("provider", "gemini")
            
            if not self.ai_chat_panel.ai_manager.initialize_provider(provider_name):
                self.terminal.output.append(
                    "<span style='color:#BC3F3C;'>❌ AI Provider not initialized. "
                    "Please configure API key in settings (⚙️ button).</span>"
                )
                self.statusBar().showMessage("AI not configured")
                return
        
        # Get AI suggestions
        try:
            suggestions = self.ai_chat_panel.ai_manager.get_optimization_suggestions(code[:500])  # Limit size
            self.terminal.output.append(f"<span style='color:#B8D4A8;'>💡 <b>Suggestions:</b></span>")
            self.terminal.output.append(f"<span style='color:#A9B7C6;'>{suggestions}</span>")
            self.statusBar().showMessage("AI suggestions generated")
        except Exception as e:
            self.terminal.output.append(f"<span style='color:#BC3F3C;'>❌ Error: {str(e)}</span>")
            logger.error(f"AI suggestion error: {e}")
    
    # ==================== AI Code Assistant Features ====================
    
    def _get_current_function_name(self):
        """Get the name of the function at cursor position"""
        editor = self.get_current_editor()
        if not editor:
            return None
        
        # Get cursor position
        cursor = editor.textCursor()
        line_number = cursor.blockNumber() + 1
        
        # Parse code to find function at this line
        code = editor.toPlainText()
        
        # Method 1: Try AST parsing (works only if code has no syntax errors)
        try:
            import ast
            tree = ast.parse(code)
            
            # Find all functions with their line ranges
            functions = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    start_line = node.lineno
                    # Get end line - try multiple methods
                    end_line = getattr(node, 'end_lineno', None)
                    
                    if end_line is None:
                        # Fallback: estimate end line from body
                        if node.body:
                            last_node = node.body[-1]
                            end_line = getattr(last_node, 'end_lineno', None) or getattr(last_node, 'lineno', start_line)
                        else:
                            end_line = start_line
                    
                    functions.append({
                        'name': node.name,
                        'start': start_line,
                        'end': end_line
                    })
            
            # Find the function containing the cursor
            for func in functions:
                if func['start'] <= line_number <= func['end']:
                    logger.debug(f"Found function '{func['name']}' at line {line_number}")
                    return func['name']
            
        except SyntaxError as e:
            logger.warning(f"Syntax error in code, using regex fallback: {e}")
        except Exception as e:
            logger.error(f"Error parsing code to find function: {e}")
        
        # Method 2: Regex-based fallback (works even with syntax errors)
        import re
        lines = code.split('\n')
        
        # Look backwards from cursor to find the most recent function definition
        current_func = None
        current_indent = None
        
        for i in range(line_number - 1, -1, -1):
            line = lines[i] if i < len(lines) else ""
            
            # Check if this is a function definition
            func_match = re.match(r'^(\s*)(def|async\s+def)\s+(\w+)\s*\(', line)
            if func_match:
                indent = len(func_match.group(1))
                func_name = func_match.group(3)
                
                # If we haven't found a function yet, or this function has less/equal indent
                if current_func is None or (current_indent is not None and indent <= current_indent):
                    current_func = func_name
                    current_indent = indent
                    logger.debug(f"Found function '{func_name}' at line {i+1} using regex")
                    break
        
        return current_func
    
    def generate_docstring_for_current(self):
        """Generate docstring for function at cursor"""
        if not self.current_file:
            QMessageBox.warning(self, "No File", "Please save the file first")
            return
        
        func_name = self._get_current_function_name()
        if not func_name:
            QMessageBox.warning(self, "No Function", "Cursor is not inside a function")
            return
        
        # Check if AI provider is initialized
        if not self.ai_chat_panel.ai_manager.is_provider_initialized():
            reply = QMessageBox.question(
                self,
                "AI Not Configured",
                "AI provider is not configured. Would you like to open settings?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.open_ai_settings()
            return
        
        # Show progress
        self.statusBar().showMessage(f"Generating docstring for {func_name}...")
        QApplication.processEvents()
        
        try:
            docstring = self.ai_code_assistant.generate_docstring_for_function(
                self.current_file,
                func_name,
                style="google",
                insert=False  # Don't auto-insert, let user review
            )
            
            # Show in dialog
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Generated Docstring for '{func_name}'")
            dialog.resize(600, 400)
            
            layout = QVBoxLayout()
            
            text_edit = QTextEdit()
            text_edit.setPlainText(docstring)
            text_edit.setStyleSheet("""
                QTextEdit {
                    background-color: #2B2B2B;
                    color: #A9B7C6;
                    font-family: Consolas;
                    font-size: 10pt;
                }
            """)
            layout.addWidget(text_edit)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            insert_btn = QPushButton("Insert into Code")
            insert_btn.clicked.connect(lambda: self._insert_docstring_and_close(
                func_name, docstring, dialog
            ))
            button_layout.addWidget(insert_btn)
            
            copy_btn = QPushButton("Copy to Clipboard")
            copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(docstring))
            button_layout.addWidget(copy_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.close)
            button_layout.addWidget(cancel_btn)
            
            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate docstring:\n{str(e)}")
            logger.error(f"Docstring generation error: {e}")
        finally:
            self.statusBar().clearMessage()
    
    def _insert_docstring_and_close(self, func_name: str, docstring: str, dialog):
        """Insert docstring and close dialog"""
        try:
            success = self.ai_code_assistant.docstring_gen.insert_docstring(
                self.current_file, func_name, docstring
            )
            
            if success:
                # Reload file content in current editor
                editor = self.get_current_editor()
                if editor and self.current_file:
                    with open(self.current_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    editor.setPlainText(content)
                    self.statusBar().showMessage(f"Docstring inserted for {func_name}")
                
                dialog.close()
                QMessageBox.information(self, "Success", "Docstring inserted successfully!")
            else:
                QMessageBox.warning(self, "Failed", "Could not insert docstring")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to insert docstring:\n{str(e)}")
    
    def show_refactoring_hints(self):
        """Show refactoring suggestions for current function"""
        if not self.current_file:
            QMessageBox.warning(self, "No File", "Please save the file first")
            return
        
        func_name = self._get_current_function_name()
        if not func_name:
            QMessageBox.warning(self, "No Function", "Cursor is not inside a function")
            return
        
        # Check if AI provider is initialized
        if not self.ai_chat_panel.ai_manager.is_provider_initialized():
            reply = QMessageBox.question(
                self,
                "AI Not Configured",
                "AI provider is not configured. Would you like to open settings?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.open_ai_settings()
            return
        
        # Show progress
        self.statusBar().showMessage(f"Analyzing {func_name}...")
        QApplication.processEvents()
        
        try:
            advice = self.ai_code_assistant.get_refactoring_advice(self.current_file, func_name)
            
            # Show in terminal with AI chat visible
            if not self.ai_chat_panel.isVisible():
                self.ai_chat_panel.setVisible(True)
            
            self.terminal.output.append(f"<br><span style='color:#6A8759; font-weight:bold;'>🔄 Refactoring Hints for '{func_name}':</span>")
            self.terminal.output.append(f"<span style='color:#A9B7C6;'>{advice.replace(chr(10), '<br>')}</span><br>")
            
            self.statusBar().showMessage(f"Refactoring hints displayed for {func_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get refactoring hints:\n{str(e)}")
            logger.error(f"Refactoring hints error: {e}")
        finally:
            self.statusBar().clearMessage()
    
    def analyze_current_function(self):
        """Complete AI analysis of current function"""
        if not self.current_file:
            QMessageBox.warning(self, "No File", "Please save the file first")
            return
        
        func_name = self._get_current_function_name()
        if not func_name:
            QMessageBox.warning(self, "No Function", "Cursor is not inside a function")
            return
        
        # Check if AI provider is initialized
        if not self.ai_chat_panel.ai_manager.is_provider_initialized():
            reply = QMessageBox.question(
                self,
                "AI Not Configured",
                "AI provider is not configured. Would you like to open settings?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.open_ai_settings()
            return
        
        # Show progress
        self.statusBar().showMessage(f"Analyzing {func_name}...")
        QApplication.processEvents()
        
        try:
            result = self.ai_code_assistant.analyze_function(
                self.current_file,
                func_name,
                force_refresh=False
            )
            
            if "error" in result:
                QMessageBox.warning(self, "Error", result["error"])
                return
            
            # Display comprehensive results
            if not self.terminal.isVisible():
                self.terminal.setVisible(True)
            
            self.terminal.output.append(f"<br><span style='color:#4B6EAF; font-weight:bold; font-size:12pt;'>🧠 AI Analysis: '{func_name}'</span><br>")
            
            # Summary
            if result.get("summary"):
                self.terminal.output.append(f"<span style='color:#6A8759; font-weight:bold;'>📝 Summary:</span>")
                self.terminal.output.append(f"<span style='color:#A9B7C6;'>{result['summary']}</span><br>")
            
            # Metrics
            if result.get("metrics"):
                metrics = result["metrics"]
                self.terminal.output.append(f"<span style='color:#CC7832; font-weight:bold;'>📊 Metrics:</span>")
                self.terminal.output.append(f"<span style='color:#A9B7C6;'>")
                self.terminal.output.append(f"  • Lines of Code: {metrics.get('lines_of_code', 'N/A')}<br>")
                self.terminal.output.append(f"  • Complexity: {metrics.get('cyclomatic_complexity', 'N/A')}<br>")
                self.terminal.output.append(f"  • Max Nesting: {metrics.get('max_nesting_depth', 'N/A')}<br>")
                self.terminal.output.append(f"  • Parameters: {metrics.get('parameter_count', 'N/A')}<br>")
                if metrics.get('needs_refactoring'):
                    self.terminal.output.append(f"  ⚠️  <span style='color:#BC3F3C;'>Refactoring Recommended</span><br>")
                else:
                    self.terminal.output.append(f"  ✅ <span style='color:#6A8759;'>Code Quality: Good</span><br>")
                self.terminal.output.append("</span><br>")
            
            # Docstring status
            if result.get("has_docstring"):
                self.terminal.output.append(f"<span style='color:#6A8759;'>✓ Has docstring</span><br>")
            else:
                self.terminal.output.append(f"<span style='color:#FFC66D;'>⚠️  Missing docstring (use Ctrl+Shift+D to generate)</span><br>")
            
            # Refactoring hints
            if result.get("refactoring_hints"):
                self.terminal.output.append(f"<br><span style='color:#CC7832; font-weight:bold;'>🔄 Refactoring Suggestions:</span>")
                self.terminal.output.append(f"<span style='color:#A9B7C6;'>{result['refactoring_hints'].replace(chr(10), '<br>')}</span><br>")
            
            self.terminal.output.append("<span style='color:#808080;'>---</span><br>")
            
            self.statusBar().showMessage(f"Analysis complete for {func_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to analyze function:\n{str(e)}")
            logger.error(f"Function analysis error: {e}")
        finally:
            self.statusBar().clearMessage()
    
    def scan_project_with_ai(self):
        """Scan entire project and cache function summaries"""
        reply = QMessageBox.question(
            self,
            "Scan Project",
            f"This will analyze all Python files in:\n{self.project_dir}\n\n"
            "This may take several minutes and use AI API credits.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Show progress
        self.statusBar().showMessage("Scanning project... This may take a while...")
        QApplication.processEvents()
        
        try:
            if not self.terminal.isVisible():
                self.terminal.setVisible(True)
            
            self.terminal.output.append("<br><span style='color:#4B6EAF; font-weight:bold;'>🔍 Starting project scan...</span><br>")
            QApplication.processEvents()
            
            results = self.ai_code_assistant.scan_project(self.project_dir)
            
            self.terminal.output.append(f"<span style='color:#6A8759; font-weight:bold;'>✓ Scan Complete!</span>")
            self.terminal.output.append(f"<span style='color:#A9B7C6;'>")
            self.terminal.output.append(f"  • Files scanned: {results['scanned_files']}<br>")
            self.terminal.output.append(f"  • Functions found: {results['total_functions']}<br>")
            self.terminal.output.append(f"  • Functions cached: {results['cached_functions']}<br>")
            if results['errors']:
                self.terminal.output.append(f"  • Errors: {len(results['errors'])}<br>")
                for error in results['errors'][:5]:  # Show first 5 errors
                    self.terminal.output.append(f"    - {error}<br>")
            self.terminal.output.append("</span><br>")
            
            QMessageBox.information(
                self,
                "Scan Complete",
                f"Scanned {results['scanned_files']} files\n"
                f"Cached {results['cached_functions']} function summaries"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to scan project:\n{str(e)}")
            logger.error(f"Project scan error: {e}")
        finally:
            self.statusBar().clearMessage()
    
    def clear_ai_cache(self):
        """Clear AI function summary cache"""
        reply = QMessageBox.question(
            self,
            "Clear Cache",
            "This will clear all cached function summaries and docstrings.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.ai_code_assistant.cache.clear_all()
                self.ai_chat_panel.ai_manager.clear_cache()
                QMessageBox.information(self, "Success", "AI cache cleared successfully!")
                logger.info("AI cache cleared")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear cache:\n{str(e)}")
    
    def show_ai_stats(self):
        """Show AI statistics and cache info"""
        try:
            stats = self.ai_code_assistant.get_stats()
            
            cache_stats = stats.get("cache_stats", {})
            ai_stats = stats.get("ai_stats", {})
            
            msg = f"""AI Code Assistant Statistics

Function Cache:
  • Cached files: {cache_stats.get('total_files', 0)}
  • Cached functions: {cache_stats.get('total_functions', 0)}
  • Cache size: {cache_stats.get('cache_size_kb', 0):.2f} KB
  • Location: {cache_stats.get('cache_file', 'N/A')}

AI Manager:
  • Total requests: {ai_stats.get('total_requests', 0)}
  • Cache hits: {ai_stats.get('cache_hits', 0)}
  • API calls: {ai_stats.get('api_calls', 0)}
  • Errors: {ai_stats.get('errors', 0)}
  • Provider: {ai_stats.get('provider', 'Not initialized')}

Cache Hit Rate: {(ai_stats.get('cache_hits', 0) / max(ai_stats.get('total_requests', 1), 1) * 100):.1f}%
"""
            
            QMessageBox.information(self, "AI Statistics", msg)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get statistics:\n{str(e)}")
    
    # ==================== End AI Code Assistant Features ====================
    
    def closeEvent(self, event):
        """Handle window close"""
        # Save window geometry
        self.settings.set("window_geometry", {
            "width": self.width(),
            "height": self.height()
        })
        logger.info("IDE closing...")
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    ide = IDE()
    ide.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
