"""
Developer-First AI Chat Panel
Professional, Context-Aware, Interactive Chat UI
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QComboBox, QDoubleSpinBox, QScrollArea, QFrame,
    QListWidget, QListWidgetItem, QToolButton, QMenu, QAction,
    QSplitter, QTextBrowser, QApplication, QCompleter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QStringListModel, QSize
from PyQt5.QtGui import QFont, QTextCursor, QColor, QTextCharFormat, QSyntaxHighlighter
import re
from datetime import datetime
from ide.utils.ai_manager import AIManager
from ide.utils.settings import SettingsManager
from ide.utils.logger import logger


class AIWorker(QThread):
    """Worker thread for async AI requests"""
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    chunk_received = pyqtSignal(str)
    
    def __init__(self, ai_manager: AIManager, prompt: str, context: str = ""):
        super().__init__()
        self.ai_manager = ai_manager
        self.prompt = prompt
        self.context = context
    
    def run(self):
        try:
            response = self.ai_manager.generate_sync(self.prompt, self.context)
            self.response_ready.emit(response)
        except Exception as e:
            logger.error(f"AI Worker error: {e}")
            self.error_occurred.emit(str(e))


class CodeBlockHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for code blocks"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Define formats
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#569CD6"))
        self.keyword_format.setFontWeight(QFont.Bold)
        
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#CE9178"))
        
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6A9955"))
        self.comment_format.setFontItalic(True)
        
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor("#DCDCAA"))
        
    def highlightBlock(self, text):
        # Keywords
        keywords = ['def', 'class', 'import', 'from', 'if', 'else', 'elif', 'for', 'while', 'return', 'try', 'except']
        for word in keywords:
            pattern = r'\b' + word + r'\b'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)
        
        # Strings
        for match in re.finditer(r'["\'].*?["\']', text):
            self.setFormat(match.start(), match.end() - match.start(), self.string_format)
        
        # Comments
        for match in re.finditer(r'#.*$', text):
            self.setFormat(match.start(), match.end() - match.start(), self.comment_format)


class ChatMessage(QFrame):
    """Individual chat message with code support"""
    
    insert_code_requested = pyqtSignal(str)
    explain_requested = pyqtSignal(str)
    
    def __init__(self, content: str, is_user: bool, timestamp: str = None):
        super().__init__()
        self.content = content
        self.is_user = is_user
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Header: Avatar + Role + Timestamp
        header = QHBoxLayout()
        header.setSpacing(10)
        
        # Avatar
        avatar = QLabel()
        if self.is_user:
            avatar.setText("👤")
            role_text = "You"
            role_color = "#007ACC"
        else:
            avatar.setText("✨")
            role_text = "AI Assistant"
            role_color = "#6A8759"
        
        avatar.setFont(QFont("Segoe UI", 16))
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(f"""
            background-color: {role_color};
            border-radius: 16px;
            padding: 2px;
        """)
        header.addWidget(avatar)
        
        # Role
        role = QLabel(role_text)
        role.setFont(QFont("Segoe UI", 11, QFont.Bold))
        role.setStyleSheet("color: #CCCCCC;")
        header.addWidget(role)
        
        # Timestamp
        time_label = QLabel(self.timestamp)
        time_label.setFont(QFont("Segoe UI", 9))
        time_label.setStyleSheet("color: #888888;")
        header.addWidget(time_label)
        header.addStretch()
        
        layout.addLayout(header)
        
        # Parse content for code blocks
        self.render_content(layout)
        
        # Action buttons for AI responses
        if not self.is_user and "```" in self.content:
            self.add_action_buttons(layout)
        
        self.setLayout(layout)
        
        # Styling
        bg = "#1E1E1E" if not self.is_user else "#252526"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border-radius: 12px;
                border: 1px solid #3C3C3C;
                margin: 4px;
            }}
            QFrame:hover {{
                border: 1px solid #555555;
            }}
        """)
    
    def render_content(self, layout):
        """Parse and render markdown + code blocks"""
        parts = re.split(r'(```[\w]*\n.*?\n```)', self.content, flags=re.DOTALL)
        
        for part in parts:
            if part.startswith('```'):
                # Code block
                self.add_code_block(layout, part)
            elif part.strip():
                # Text content
                self.add_text_block(layout, part)
    
    def add_text_block(self, layout, text):
        """Add formatted text block"""
        text_widget = QTextBrowser()
        text_widget.setPlainText(text.strip())
        text_widget.setFont(QFont("Segoe UI", 10))
        text_widget.setFrameStyle(QFrame.NoFrame)
        text_widget.setOpenExternalLinks(False)
        text_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        text_widget.setMaximumHeight(400)
        text_widget.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                color: #D4D4D4;
                border: none;
                padding: 4px 0px;
            }
        """)
        layout.addWidget(text_widget)
    
    def add_code_block(self, layout, code_text):
        """Add syntax-highlighted code block with actions"""
        # Extract language and code
        match = re.match(r'```(\w*)\n(.*)\n```', code_text, re.DOTALL)
        if match:
            lang = match.group(1) or "python"
            code = match.group(2)
        else:
            lang = "python"
            code = code_text.replace('```', '').strip()
        
        # Container
        code_container = QFrame()
        code_layout = QVBoxLayout()
        code_layout.setContentsMargins(0, 0, 0, 0)
        code_layout.setSpacing(0)
        
        # Header with language and copy button
        code_header = QHBoxLayout()
        code_header.setContentsMargins(12, 8, 12, 8)
        
        lang_label = QLabel(f"📄 {lang}")
        lang_label.setFont(QFont("Consolas", 9))
        lang_label.setStyleSheet("color: #858585;")
        code_header.addWidget(lang_label)
        code_header.addStretch()
        
        # Copy button
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setFixedHeight(24)
        copy_btn.setFont(QFont("Segoe UI", 9))
        copy_btn.clicked.connect(lambda: self.copy_code(code))
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #CCCCCC;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #3C3C3C;
                border: 1px solid #007ACC;
            }
        """)
        code_header.addWidget(copy_btn)
        
        # Insert button
        insert_btn = QPushButton("📥 Insert")
        insert_btn.setFixedHeight(24)
        insert_btn.setFont(QFont("Segoe UI", 9))
        insert_btn.clicked.connect(lambda: self.insert_code_requested.emit(code))
        insert_btn.setStyleSheet("""
            QPushButton {
                background-color: #0E639C;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
        """)
        code_header.addWidget(insert_btn)
        
        code_layout.addLayout(code_header)
        
        # Code display
        code_display = QTextEdit()
        code_display.setPlainText(code)
        code_display.setFont(QFont("Consolas", 10))
        code_display.setReadOnly(True)
        code_display.setMaximumHeight(300)
        code_display.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                border-top: 1px solid #3C3C3C;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QScrollBar:vertical {
                background: #2D2D2D;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 6px;
            }
        """)
        
        # Apply syntax highlighting
        highlighter = CodeBlockHighlighter(code_display.document())
        
        code_layout.addWidget(code_display)
        code_container.setLayout(code_layout)
        code_container.setStyleSheet("""
            QFrame {
                background-color: #0D1117;
                border: 1px solid #30363D;
                border-radius: 6px;
            }
        """)
        
        layout.addWidget(code_container)
    
    def add_action_buttons(self, layout):
        """Add quick action buttons after AI response"""
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.setContentsMargins(0, 8, 0, 0)
        
        for icon, text, tooltip in [
            ("🧠", "Explain", "Get detailed explanation"),
            ("🧹", "Refactor", "Suggest improvements"),
            ("🧪", "Test", "Generate test cases"),
            ("📚", "Docs", "Add documentation")
        ]:
            btn = QPushButton(f"{icon} {text}")
            btn.setFixedHeight(28)
            btn.setFont(QFont("Segoe UI", 9))
            btn.setToolTip(tooltip)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #CCCCCC;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background-color: #2D2D2D;
                    border: 1px solid #007ACC;
                }
            """)
            actions.addWidget(btn)
        
        actions.addStretch()
        layout.addLayout(actions)
    
    def copy_code(self, code):
        """Copy code to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(code)
        logger.info("Code copied to clipboard")


class ContextIndicator(QFrame):
    """Shows what files/context are included"""
    
    context_removed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.contexts = []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # Title
        title = QLabel("📎 Context")
        title.setFont(QFont("Segoe UI", 9, QFont.Bold))
        title.setStyleSheet("color: #858585;")
        layout.addWidget(title)
        
        # Context list
        self.context_list = QVBoxLayout()
        self.context_list.setSpacing(4)
        layout.addLayout(self.context_list)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QFrame {
                background-color: #2D2D2D;
                border-radius: 6px;
                border: 1px solid #3C3C3C;
            }
        """)
        self.hide()  # Hidden by default
    
    def add_context(self, filename: str):
        """Add a context file indicator"""
        if filename not in self.contexts:
            self.contexts.append(filename)
            self.update_display()
            self.show()
    
    def remove_context(self, filename: str):
        """Remove a context file"""
        if filename in self.contexts:
            self.contexts.remove(filename)
            self.update_display()
            if not self.contexts:
                self.hide()
            self.context_removed.emit(filename)
    
    def update_display(self):
        """Refresh the context display"""
        # Clear existing
        while self.context_list.count():
            child = self.context_list.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add current contexts
        for ctx in self.contexts:
            item = QHBoxLayout()
            
            label = QLabel(f"📄 {ctx}")
            label.setFont(QFont("Segoe UI", 9))
            label.setStyleSheet("color: #CCCCCC;")
            item.addWidget(label)
            
            remove_btn = QPushButton("✖")
            remove_btn.setFixedSize(18, 18)
            remove_btn.setFont(QFont("Segoe UI", 8))
            remove_btn.clicked.connect(lambda checked, f=ctx: self.remove_context(f))
            remove_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #888888;
                    border: none;
                    border-radius: 9px;
                }
                QPushButton:hover {
                    background-color: #FF5555;
                    color: #FFFFFF;
                }
            """)
            item.addWidget(remove_btn)
            
            self.context_list.addLayout(item)
    
    def get_contexts(self):
        """Return list of active contexts"""
        return self.contexts.copy()
    
    def clear_all(self):
        """Clear all contexts"""
        self.contexts.clear()
        self.update_display()
        self.hide()


class SlashCommandCompleter(QCompleter):
    """Auto-complete for slash commands"""
    
    def __init__(self, parent=None):
        commands = [
            "/explain - Explain selected code",
            "/fix - Debug and fix issues",
            "/refactor - Optimize and improve code",
            "/test - Generate test cases",
            "/docs - Write documentation",
            "/review - Code review suggestions"
        ]
        super().__init__(commands, parent)
        self.setCompletionMode(QCompleter.PopupCompletion)
        self.setCaseSensitivity(Qt.CaseInsensitive)


class AIChatPanel(QWidget):
    """Main AI Chat Panel - Developer-First Design"""
    
    def __init__(self, settings_manager: SettingsManager, parent_ide=None):
        super().__init__()
        self.settings = settings_manager
        self.parent_ide = parent_ide
        self.ai_manager = AIManager(settings_manager)
        self.worker = None
        self.chat_history = []
        self.current_context = {}
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Create the minimal, clean UI layout"""
        self.setMinimumWidth(400)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ===== TOP BAR (Simple Header) =====
        top_bar = QFrame()
        top_bar.setFixedHeight(48)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(16, 12, 16, 12)
        
        # Title
        title = QLabel("💬 AI Assistant")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title.setStyleSheet("color: #CCCCCC;")
        top_layout.addWidget(title)
        
        # Status indicator
        self.status_indicator = QLabel("🟢")
        self.status_indicator.setFont(QFont("Segoe UI", 10))
        self.status_indicator.setToolTip("Connected")
        top_layout.addWidget(self.status_indicator)
        
        top_layout.addStretch()
        
        # Clear button
        clear_btn = QToolButton()
        clear_btn.setText("🗑")
        clear_btn.setFont(QFont("Segoe UI", 13))
        clear_btn.setToolTip("Clear chat")
        clear_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                color: #CCCCCC;
                border: none;
                border-radius: 4px;
                padding: 6px;
            }
            QToolButton:hover {
                background-color: #2D2D2D;
            }
        """)
        clear_btn.clicked.connect(self.clear_chat)
        top_layout.addWidget(clear_btn)
        
        # Settings button
        settings_btn = QToolButton()
        settings_btn.setText("⚙")
        settings_btn.setFont(QFont("Segoe UI", 13))
        settings_btn.setToolTip("Settings")
        settings_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                color: #CCCCCC;
                border: none;
                border-radius: 4px;
                padding: 6px;
            }
            QToolButton:hover {
                background-color: #2D2D2D;
            }
        """)
        settings_btn.clicked.connect(self.open_settings)
        top_layout.addWidget(settings_btn)
        
        top_bar.setLayout(top_layout)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-bottom: 1px solid #3C3C3C;
            }
        """)
        main_layout.addWidget(top_bar)
        
        # ===== CHAT AREA (Full Height) =====
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout()
        self.chat_layout.setContentsMargins(16, 16, 16, 16)
        self.chat_layout.setSpacing(16)
        self.chat_layout.addStretch()
        self.chat_container.setLayout(self.chat_layout)
        
        self.chat_scroll.setWidget(self.chat_container)
        self.chat_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1E1E1E;
                border: none;
            }
            QScrollBar:vertical {
                background: #1E1E1E;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }
        """)
        main_layout.addWidget(self.chat_scroll, 1)  # Give it stretch factor
        
        # ===== INPUT BAR (Bottom) =====
        input_bar = self.create_input_bar()
        main_layout.addWidget(input_bar)
        
        self.setLayout(main_layout)
    
    def create_top_bar(self):
        """Create top bar with title and controls"""
        top_bar = QFrame()
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Title with icon
        title_layout = QHBoxLayout()
        title_icon = QLabel("💬")
        title_icon.setFont(QFont("Segoe UI", 16))
        title_layout.addWidget(title_icon)
        
        title = QLabel("AI Assistant")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: #CCCCCC;")
        title_layout.addWidget(title)
        
        # Status indicator
        self.status_indicator = QLabel("🟢")
        self.status_indicator.setFont(QFont("Segoe UI", 12))
        self.status_indicator.setToolTip("Connected")
        title_layout.addWidget(self.status_indicator)
        
        layout.addLayout(title_layout)
        layout.addStretch()
        
        # Quick action buttons
        btn_style = """
            QToolButton {
                background-color: transparent;
                color: #CCCCCC;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 6px;
            }
            QToolButton:hover {
                background-color: #2D2D2D;
                border: 1px solid #555555;
            }
        """
        
        # Add context button
        add_context_btn = QToolButton()
        add_context_btn.setText("📎")
        add_context_btn.setFont(QFont("Segoe UI", 14))
        add_context_btn.setToolTip("Add context files")
        add_context_btn.setStyleSheet(btn_style)
        add_context_btn.clicked.connect(self.add_context_files)
        layout.addWidget(add_context_btn)
        
        # Clear chat
        clear_btn = QToolButton()
        clear_btn.setText("🧹")
        clear_btn.setFont(QFont("Segoe UI", 14))
        clear_btn.setToolTip("Clear chat")
        clear_btn.setStyleSheet(btn_style)
        clear_btn.clicked.connect(self.clear_chat)
        layout.addWidget(clear_btn)
        
        # Save conversation
        save_btn = QToolButton()
        save_btn.setText("💾")
        save_btn.setFont(QFont("Segoe UI", 14))
        save_btn.setToolTip("Save conversation")
        save_btn.setStyleSheet(btn_style)
        save_btn.clicked.connect(self.save_conversation)
        layout.addWidget(save_btn)
        
        # Settings
        settings_btn = QToolButton()
        settings_btn.setText("⚙️")
        settings_btn.setFont(QFont("Segoe UI", 14))
        settings_btn.setToolTip("Settings")
        settings_btn.setStyleSheet(btn_style)
        settings_btn.clicked.connect(self.open_settings)
        layout.addWidget(settings_btn)
        
        top_bar.setLayout(layout)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-bottom: 1px solid #3C3C3C;
            }
        """)
        return top_bar
    
    def create_history_panel(self):
        """Create chat history sidebar"""
        panel = QFrame()
        panel.setMinimumWidth(150)
        panel.setMaximumWidth(250)
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("💬 History")
        title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(title)
        
        # History list
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget {
                background-color: #1E1E1E;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                color: #CCCCCC;
                padding: 4px;
                font-size: 9pt;
            }
            QListWidget::item {
                padding: 6px;
                border-radius: 3px;
            }
            QListWidget::item:hover {
                background-color: #2D2D2D;
            }
            QListWidget::item:selected {
                background-color: #007ACC;
            }
        """)
        layout.addWidget(self.history_list)
        
        # New chat button
        new_chat_btn = QPushButton("➕ New Chat")
        new_chat_btn.setFont(QFont("Segoe UI", 9))
        new_chat_btn.setFixedHeight(30)
        new_chat_btn.clicked.connect(self.new_chat_session)
        new_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #0E639C;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
        """)
        layout.addWidget(new_chat_btn)
        
        panel.setLayout(layout)
        panel.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-right: 1px solid #3C3C3C;
            }
        """)
        return panel
    
    def create_input_bar(self):
        """Create simple bottom input area"""
        input_frame = QFrame()
        input_frame.setFixedHeight(120)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        
        # Input text area
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Ask AI about your code...")
        self.input_text.setFont(QFont("Segoe UI", 10))
        self.input_text.setFixedHeight(60)
        self.input_text.setStyleSheet("""
            QTextEdit {
                background-color: #2D2D2D;
                color: #CCCCCC;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 10px;
            }
            QTextEdit:focus {
                border: 1px solid #007ACC;
            }
        """)
        layout.addWidget(self.input_text)
        
        # Bottom row: model selector + send button
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        
        # Model selector
        model_label = QLabel("Model:")
        model_label.setStyleSheet("color: #858585;")
        bottom_row.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["GPT-4", "Gemini Pro"])
        self.model_combo.setFixedHeight(32)
        self.model_combo.setFixedWidth(120)
        self.model_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2D2D;
                color: #CCCCCC;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QComboBox:hover {
                border: 1px solid #007ACC;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        bottom_row.addWidget(self.model_combo)
        
        bottom_row.addStretch()
        
        # Send button
        self.send_btn = QPushButton("Send")
        self.send_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.send_btn.setFixedSize(100, 32)
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0E639C;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:pressed {
                background-color: #0D5A8F;
            }
            QPushButton:disabled {
                background-color: #3C3C3C;
                color: #858585;
            }
        """)
        bottom_row.addWidget(self.send_btn)
        
        layout.addLayout(bottom_row)
        
        input_frame.setLayout(layout)
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-top: 1px solid #3C3C3C;
            }
        """)
        
        return input_frame
        
        layout.addLayout(bottom_row)
        
        input_frame.setLayout(layout)
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-top: 1px solid #3C3C3C;
            }
        """)
        return input_frame
    
    def check_slash_command(self):
        """Check for slash commands and show completer"""
        text = self.input_text.toPlainText()
        if text.startswith('/'):
            cursor = self.input_text.textCursor()
            rect = self.input_text.cursorRect(cursor)
            self.slash_completer.complete(rect)
    
    def insert_command(self, command):
        """Insert a slash command"""
        self.input_text.setPlainText(command + " ")
        self.input_text.setFocus()
        cursor = self.input_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.input_text.setTextCursor(cursor)
    
    def send_message(self):
        """Send user message and get AI response"""
        message = self.input_text.toPlainText().strip()
        if not message:
            return
        
        # Check if provider is initialized
        if not self.ai_manager.provider:
            self.add_system_message(
                "❌ AI Provider not initialized.\n\n"
                "Please configure your API key in Settings (⚙️) first."
            )
            return
        
        # Add user message
        user_msg = ChatMessage(message, is_user=True)
        self.add_message_to_chat(user_msg)
        self.input_text.clear()
        
        # Get context
        context = self._get_current_context()
        
        # Show thinking indicator
        thinking_msg = ChatMessage("Thinking...", is_user=False)
        self.add_message_to_chat(thinking_msg)
        
        # Disable send button
        self.send_btn.setEnabled(False)
        self.status_indicator.setText("🟡")
        self.status_indicator.setToolTip("Generating...")
        
        # Start AI worker
        self.worker = AIWorker(self.ai_manager, message, context)
        self.worker.response_ready.connect(self.on_response_ready)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()
    
    def on_response_ready(self, response):
        """Handle AI response"""
        # Remove thinking indicator
        if self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(self.chat_layout.count() - 2)
            if item.widget():
                item.widget().deleteLater()
        
        # Add AI response
        ai_msg = ChatMessage(response, is_user=False)
        ai_msg.insert_code_requested.connect(self.insert_code_to_editor)
        self.add_message_to_chat(ai_msg)
        
        # Re-enable
        self.send_btn.setEnabled(True)
        self.status_indicator.setText("🟢")
        self.status_indicator.setToolTip("Connected")
        
        # Scroll to bottom
        QTimer.singleShot(100, self.scroll_to_bottom)
    
    def on_error(self, error):
        """Handle errors"""
        # Remove thinking indicator
        if self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(self.chat_layout.count() - 2)
            if item.widget():
                item.widget().deleteLater()
        
        # Show error
        error_msg = ChatMessage(f"❌ Error: {error}", is_user=False)
        self.add_message_to_chat(error_msg)
        
        self.send_btn.setEnabled(True)
        self.status_indicator.setText("🔴")
        self.status_indicator.setToolTip("Error occurred")
    
    def add_message_to_chat(self, message_widget):
        """Add message widget to chat"""
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, message_widget)
        self.chat_history.append(message_widget)
    
    def add_system_message(self, message: str):
        """Add a system/info message to chat"""
        system_msg = ChatMessage(message, is_user=False)
        self.add_message_to_chat(system_msg)
        QTimer.singleShot(100, self.scroll_to_bottom)
    
    def scroll_to_bottom(self):
        """Scroll chat to bottom"""
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _get_current_context(self):
        """Get current file context from parent IDE"""
        # Auto-detect from parent IDE
        if self.parent_ide:
            try:
                current_file = self.parent_ide.get_current_file()
                if current_file:
                    content = self.parent_ide.get_file_content(current_file)
                    if content:
                        # Limit context to first 5000 characters
                        return f"File: {current_file}\n\n{content[:5000]}"
            except Exception as e:
                logger.error(f"Error getting context: {e}")
        
        return ""
    
    def insert_code_to_editor(self, code):
        """Insert code into parent IDE editor"""
        if self.parent_ide:
            try:
                self.parent_ide.insert_text(code)
                logger.info("Code inserted to editor")
            except Exception as e:
                logger.error(f"Error inserting code: {e}")
    
    def add_context_files(self):
        """Open file dialog to add context"""
        # TODO: Implement file picker
        logger.info("Add context files requested")
    
    def on_context_removed(self, filename):
        """Handle context removal"""
        if filename in self.current_context:
            del self.current_context[filename]
    
    def clear_chat(self):
        """Clear all chat messages"""
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.chat_history.clear()
        logger.info("Chat cleared")
    
    def save_conversation(self):
        """Save conversation to file"""
        # TODO: Implement save functionality
        logger.info("Save conversation requested")
    
    def new_chat_session(self):
        """Start a new chat session"""
        self.clear_chat()
    
    def open_settings(self):
        """Open AI settings dialog"""
        if self.parent_ide:
            try:
                self.parent_ide.open_ai_settings()
            except Exception as e:
                logger.error(f"Error opening settings: {e}")
    
    def load_settings(self):
        """Load settings from manager and initialize AI provider"""
        ai_settings = self.settings.get("ai", {})
        provider = ai_settings.get("provider", "gemini")
        
        # Initialize AI provider
        if not self.ai_manager.initialize_provider(provider):
            logger.warning(f"Failed to initialize AI provider: {provider}")
            # Show welcome message with setup instructions
            self.add_system_message(
                "⚠️ AI Provider not initialized.\n\n"
                "Please configure your API key:\n"
                "1. Click the ⚙️ Settings button in the navbar\n"
                "2. Add your OpenAI or Gemini API key\n"
                "3. Test the connection\n"
                "4. Return here to start chatting!"
            )
        else:
            logger.info(f"AI provider initialized: {provider}")
            # Set the provider in combo box
            if hasattr(self, 'model_selector'):
                index = 0 if provider.lower() == "gemini" else 1
                self.model_selector.setCurrentIndex(index)
    
    def on_provider_changed(self, provider):
        """Handle provider change"""
        success = self.ai_manager.initialize_provider(provider.lower())
        if success:
            self.add_system_message(f"✅ Switched to {provider}")
        else:
            self.add_system_message(f"❌ Failed to switch to {provider}. Check API key in settings.")
