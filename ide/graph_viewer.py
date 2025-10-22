"""
Graph Viewer Widget
Displays flow analysis results with option to open in browser
"""
import os
import webbrowser
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QTextBrowser
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont


class GraphViewer(QWidget):
    """Widget to display flow graph analysis"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_html_path = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Function Flow Graph")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #6A8759; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # HTML Viewer (embedded)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #2B2B2B;
                color: #A9B7C6;
                border: 1px solid #3C3F41;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.browser)
        
        # Button to open in browser
        self.open_browser_btn = QPushButton("🌐 Open in Browser (Interactive)")
        self.open_browser_btn.setFont(QFont("Segoe UI", 11))
        self.open_browser_btn.setStyleSheet("""
            QPushButton {
                background-color: #4B6EAF;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5A7EBF;
            }
            QPushButton:pressed {
                background-color: #3A5E9F;
            }
            QPushButton:disabled {
                background-color: #3C3F41;
                color: #666666;
            }
        """)
        self.open_browser_btn.clicked.connect(self.open_in_browser)
        self.open_browser_btn.setEnabled(False)
        layout.addWidget(self.open_browser_btn)
        
        # Info label
        info = QLabel("💡 The browser view is fully interactive with drag, zoom, and hover tooltips")
        info.setStyleSheet("color: #888888; padding: 5px;")
        info.setAlignment(Qt.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)
        
        self.setLayout(layout)
        
        # Show welcome message
        self.show_welcome()
    
    def show_welcome(self):
        """Show welcome message"""
        welcome_html = """
        <div style='text-align: center; padding: 50px; color: #A9B7C6;'>
            <h2 style='color: #6A8759;'>Welcome to Flow Graph Analyzer</h2>
            <p style='font-size: 14px; margin-top: 20px;'>
                Click the <strong>📊 Analyze Flow</strong> button in the toolbar to generate 
                a function call graph for your project.
            </p>
            <hr style='border: 1px solid #3C3F41; margin: 30px 0;'>
            <h3 style='color: #CC7832;'>Features:</h3>
            <ul style='text-align: left; display: inline-block; font-size: 13px;'>
                <li>📍 <strong>Directional arrows</strong> show function call flow</li>
                <li>🎨 <strong>Color coding</strong>: Purple (functions), Orange (methods), Green (async)</li>
                <li>🔍 <strong>Interactive</strong>: Hover for details, drag to rearrange</li>
                <li>📊 <strong>Statistics</strong>: Function counts, call relationships</li>
                <li>⚠️ <strong>Cycle detection</strong>: Find circular dependencies</li>
            </ul>
        </div>
        """
        self.browser.setHtml(welcome_html)
    
    def load_graph(self, html_path):
        """Load and display graph from HTML file"""
        self.current_html_path = html_path
        
        # Read HTML file
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Create embedded preview (simplified)
            preview_html = f"""
            <div style='text-align: center; padding: 30px; color: #A9B7C6;'>
                <h2 style='color: #6A8759;'>✓ Flow Graph Generated!</h2>
                <p style='font-size: 14px; margin: 20px 0;'>
                    Your function flow graph has been successfully generated.
                </p>
                <div style='background: #3C3F41; padding: 20px; border-radius: 8px; margin: 20px 0;'>
                    <p style='color: #CC7832; font-weight: bold; font-size: 16px;'>
                        📂 Graph Location:
                    </p>
                    <p style='color: #6A9FE0; font-size: 12px; word-break: break-all;'>
                        {html_path}
                    </p>
                </div>
                <hr style='border: 1px solid #3C3F41; margin: 30px 0;'>
                <h3 style='color: #CC7832;'>How to View:</h3>
                <div style='text-align: left; display: inline-block; font-size: 13px;'>
                    <p>🌐 Click the <strong>"Open in Browser"</strong> button below for the full interactive experience:</p>
                    <ul style='margin: 10px 0;'>
                        <li>✨ <strong>Zoom</strong> with mouse wheel</li>
                        <li>🖱️ <strong>Drag nodes</strong> to rearrange</li>
                        <li>📍 <strong>Hover</strong> over nodes for details</li>
                        <li>➡️ <strong>Follow arrows</strong> to see call direction</li>
                        <li>📊 <strong>View statistics</strong> in the top-right panel</li>
                    </ul>
                </div>
            </div>
            """
            
            self.browser.setHtml(preview_html)
            self.open_browser_btn.setEnabled(True)
            
        except Exception as e:
            error_html = f"""
            <div style='text-align: center; padding: 50px; color: #BC3F3C;'>
                <h2>❌ Error Loading Graph</h2>
                <p>{str(e)}</p>
            </div>
            """
            self.browser.setHtml(error_html)
            self.open_browser_btn.setEnabled(False)
    
    def open_in_browser(self):
        """Open the graph in default browser"""
        if self.current_html_path and os.path.exists(self.current_html_path):
            webbrowser.open(f"file:///{self.current_html_path.replace(os.sep, '/')}")
