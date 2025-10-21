"""
Py-IDE - Main Window
Modular, high-performance architecture with threading and persistence
"""
import sys
import os
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
from ide.explorer import FileExplorer
from ide.utils.settings import SettingsManager
from ide.utils.logger import logger
from ide.utils.workers import FileOperationWorker, LintWorker

# Import flow analyzer components
from ide.analyzer.flow_analyzer import FunctionFlowAnalyzer
from ide.analyzer.graph_builder import GraphBuilder
from ide.analyzer.visualizer import Visualizer


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
        self.terminal = TerminalWidget(self.project_dir, self)
        self.terminal.setVisible(self.settings.get("terminal_visible", True))
        
        # === Vertical Splitter (Editor | Terminal) ===
        editor_splitter = QSplitter(Qt.Vertical)
        editor_splitter.addWidget(self.tab_widget)
        editor_splitter.addWidget(self.terminal)
        editor_splitter.setSizes([700, 200])
        
        # === Main Splitter (Navbar | Explorer | Editor) ===
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(self.navbar_widget)
        self.main_splitter.addWidget(self.file_explorer)
        self.main_splitter.addWidget(editor_splitter)
        self.main_splitter.setSizes([48, 250, 1350])
        
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
        
        navbar_layout.addStretch(1)
        
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
        
        toolbar.addSeparator()
        
        # Flow Analyzer button
        flow_action = QAction("📊 Analyze Flow", self)
        flow_action.setToolTip("Analyze Function Call Flow")
        flow_action.triggered.connect(self.run_flow_analysis)
        toolbar.addAction(flow_action)
        
        toolbar.addSeparator()
        
        ai_action = QAction("AI", self)
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
        
        # Add syntax highlighting
        highlighter = PythonHighlighter(editor.document())
        
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
        visible = not self.terminal.isVisible()
        self.terminal.setVisible(visible)
        self.settings.set("terminal_visible", visible)
        self.statusBar().showMessage("Terminal " + ("opened" if visible else "closed"))
    
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
        """Run current code using QProcess"""
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
        self.terminal.output.append("<span style='color:#6A8759;'>Running...</span>")
        
        # Kill previous process if running
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.terminal.output.append("<span style='color:#BC3F3C;'>Previous process terminated.</span>")
        
        # Start new process
        self.process.start(sys.executable, ["-c", code])
        self.process.setWorkingDirectory(self.project_dir)
        self.statusBar().showMessage("Running code...")
        logger.info("Running code execution")
    
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
        else:
            self.terminal.output.append(f"<br><span style='color:#BC3F3C;'>Process finished with exit code {exit_code}</span>")
            self.statusBar().showMessage("Execution completed with errors")
        logger.info(f"Process finished with exit code {exit_code}")
    
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
            
            # Step 3: Optimize for visualization
            optimized_graph = builder.optimize_for_visualization(max_nodes=100)
            self.terminal.output.append("<span style='color:#A9B7C6;'>✓ Optimized graph for visualization</span>")
            
            # Step 4: Visualize
            visualizer = Visualizer()
            html_path = visualizer.render_with_stats(optimized_graph, "function_flow.html")
            
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
        """Show AI suggestions"""
        self.terminal.output.clear()
        self.terminal.output.append("<span style='color:#6A8759;'>🤖 AI Analyzing code...</span>")
        self.terminal.output.append("\n<span style='color:#A9B7C6;'>💡 <b>Suggestions:</b></span>")
        self.terminal.output.append("<span style='color:#A9B7C6;'>  • Use type hints for better code clarity</span>")
        self.terminal.output.append("<span style='color:#A9B7C6;'>  • Add docstrings to functions</span>")
        self.terminal.output.append("<span style='color:#A9B7C6;'>  • Consider using list comprehensions</span>")
        self.statusBar().showMessage("AI suggestions generated")
    
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
