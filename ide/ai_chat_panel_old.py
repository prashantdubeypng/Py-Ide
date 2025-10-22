"""
AI Chat Panel
PyQt5-based chat interface integrated with AI Manager
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QMessageBox,
    QScrollArea, QFrame, QApplication, QTextBrowser
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QColor, QTextOption

from ide.utils.ai_manager import AIManager
from ide.utils.settings import SettingsManager
from ide.utils.logger import logger


class AIWorker(QThread):
    """Worker thread for async AI requests"""
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, ai_manager: AIManager, prompt: str, context: str = ""):
        super().__init__()
        self.ai_manager = ai_manager
        self.prompt = prompt
        self.context = context
    
    def run(self):
        """Run AI request in worker thread"""
        try:
            response = self.ai_manager.generate_sync(self.prompt, self.context)
            self.response_ready.emit(response)
        except Exception as e:
            logger.error(f"AI Worker error: {e}")
            self.error_occurred.emit(str(e))


class ChatBubble(QFrame):
    """Modern VS Code-style chat message bubble"""
    
    def __init__(self, message: str, is_user: bool = True):
        super().__init__()
        self.is_user = is_user
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(8)
        
        # Header with avatar and role
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # Avatar (simple colored circle with initial)
        avatar = QLabel()
        if is_user:
            avatar_text = "U"
            avatar_bg = "#007ACC"
            role_name = "You"
        else:
            avatar_text = "AI"
            avatar_bg = "#6A8759"
            role_name = "Copilot"
        
        avatar.setText(avatar_text)
        avatar.setFont(QFont("Segoe UI", 10, QFont.Bold))
        avatar.setFixedSize(28, 28)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(f"""
            QLabel {{
                background-color: {avatar_bg};
                color: #FFFFFF;
                border-radius: 14px;
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(avatar)
        
        # Role label
        role_label = QLabel(role_name)
        role_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        role_label.setStyleSheet(f"color: #CCCCCC; font-weight: 600;")
        header_layout.addWidget(role_label)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Message text
        self.text_browser = QTextBrowser()
        self.text_browser.setPlainText(message)
        self.text_browser.setFont(QFont("Segoe UI", 10))
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.setFrameStyle(QFrame.NoFrame)
        self.text_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_browser.setLineWrapMode(QTextBrowser.WidgetWidth)
        self.text_browser.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        
        # Dynamic height calculation - wait for proper sizing
        self.text_browser.document().setDocumentMargin(0)
        self.text_browser.setMinimumHeight(60)
        self.text_browser.setMaximumHeight(800)
        
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                color: #CCCCCC;
                border: none;
                padding: 4px 0px;
                line-height: 1.6;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        main_layout.addWidget(self.text_browser)
        
        self.setLayout(main_layout)
        
        # Bubble styling
        bg_color = "#252526" if is_user else "#1E1E1E"
        border_color = "#3C3C3C" if is_user else "#2D2D2D"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                margin: 4px 8px;
            }}
            QFrame:hover {{
                background-color: {'#2D2D2D' if is_user else '#252525'};
                border: 1px solid #555555;
            }}
        """)
    
    def set_thinking(self):
        """Show thinking animation"""
        self.setStyleSheet("""
            QFrame {
                background-color: #3C3F41;
                border-left: 3px solid #CC7832;
                border-radius: 4px;
                margin: 5px 5px 5px 5px;
            }
        """)


class AIChatPanel(QWidget):
    """AI Chat Panel integrated with IDE"""
    
    def __init__(self, settings_manager: SettingsManager = None, parent_ide=None):
        super().__init__()
        self.settings = settings_manager or SettingsManager()
        self.ai_manager = AIManager(self.settings)
        self.parent_ide = parent_ide  # Reference to IDE for getting current file
        
        # Initialize provider
        if not self.ai_manager.initialize_provider():
            logger.warning("AI Provider not initialized - will attempt initialization on first use")
        
        self.current_worker = None
        self.setup_ui()
        logger.info("AI Chat Panel initialized")
    
    def setup_ui(self):
        """Setup modern VS Code-style UI layout"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # === Modern Header (VS Code style) ===
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-bottom: 1px solid #3C3C3C;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        
        # Title with icon
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        
        icon_label = QLabel("💬")
        icon_label.setFont(QFont("Segoe UI Emoji", 14))
        title_layout.addWidget(icon_label)
        
        title = QLabel("Copilot Chat")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet("color: #CCCCCC;")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        header_layout.addLayout(title_layout)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(4)
        
        # Clear button (icon style)
        clear_btn = QPushButton("🗑")
        clear_btn.setFixedSize(32, 32)
        clear_btn.setFont(QFont("Segoe UI Emoji", 12))
        clear_btn.setToolTip("Clear chat")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #CCCCCC;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3C3C3C;
            }
        """)
        clear_btn.clicked.connect(self.clear_chat)
        action_layout.addWidget(clear_btn)
        
        # Settings button
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(32, 32)
        settings_btn.setFont(QFont("Segoe UI", 14))
        settings_btn.setToolTip("Settings")
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #CCCCCC;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3C3C3C;
            }
        """)
        settings_btn.clicked.connect(self.show_settings)
        action_layout.addWidget(settings_btn)
        
        header_layout.addLayout(action_layout)
        
        main_layout.addWidget(header)
        
        # === Chat Area (VS Code style) ===
        chat_scroll_area = QScrollArea()
        chat_scroll_area.setWidgetResizable(True)
        chat_scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1E1E1E;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1E1E1E;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout()
        self.chat_layout.setContentsMargins(5, 5, 5, 5)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch()
        self.chat_container.setLayout(self.chat_layout)
        
        chat_scroll_area.setWidget(self.chat_container)
        main_layout.addWidget(chat_scroll_area)
        
        # === Input Area (VS Code style) ===
        input_container = QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-top: 1px solid #3C3C3C;
            }
        """)
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(12, 12, 12, 12)
        input_layout.setSpacing(8)
        
        # Context indicator (at top)
        self.context_label = QLabel()
        self.context_label.setStyleSheet("""
            QLabel {
                color: #858585;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #2D2D2D;
                border-radius: 4px;
            }
        """)
        self.context_label.setVisible(False)
        input_layout.addWidget(self.context_label)
        
        # Message input (VS Code style)
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Ask Copilot or type / for commands")
        self.input_text.setMaximumHeight(100)
        self.input_text.setFont(QFont("Segoe UI", 10))
        self.input_text.setStyleSheet("""
            QTextEdit {
                background-color: #3C3C3C;
                color: #CCCCCC;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 10px;
                font-size: 10pt;
            }
            QTextEdit:focus {
                border: 1px solid #007ACC;
                background-color: #404040;
            }
        """)
        self.input_text.keyPressEvent = self._handle_key_press
        input_layout.addWidget(self.input_text)
        
        # Bottom action bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)
        
        # Provider selector (compact)
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "Gemini"])
        self.provider_combo.setFixedHeight(32)
        self.provider_combo.setStyleSheet("""
            QComboBox {
                background-color: #3C3C3C;
                color: #CCCCCC;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10pt;
            }
            QComboBox:hover {
                border: 1px solid #007ACC;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        action_bar.addWidget(self.provider_combo)
        
        # Temperature control (compact)
        self.temp_spinbox = QDoubleSpinBox()
        self.temp_spinbox.setMinimum(0.0)
        self.temp_spinbox.setMaximum(2.0)
        self.temp_spinbox.setValue(0.7)
        self.temp_spinbox.setSingleStep(0.1)
        self.temp_spinbox.setFixedSize(70, 32)
        self.temp_spinbox.setPrefix("T:")
        self.temp_spinbox.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3C3C3C;
                color: #CCCCCC;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px;
                font-size: 9pt;
            }
            QDoubleSpinBox:hover {
                border: 1px solid #007ACC;
            }
        """)
        action_bar.addWidget(self.temp_spinbox)
        
        action_bar.addStretch()
        
        # Send button (VS Code style)
        self.send_btn = QPushButton("Send")
        self.send_btn.setFixedHeight(32)
        self.send_btn.setFixedWidth(80)
        self.send_btn.setFont(QFont("Segoe UI", 10))
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0E639C;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                font-weight: 500;
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
        self.send_btn.clicked.connect(self.send_message)
        action_bar.addWidget(self.send_btn)
        
        input_layout.addLayout(action_bar)
        
        main_layout.addWidget(input_container)
        self.setLayout(main_layout)
        
        # Apply panel styling
        self.setStyleSheet("""
            AIChatPanel {
                background-color: #2B2B2B;
                border-left: 1px solid #3C3F41;
            }
        """)
    
    def _handle_key_press(self, event):
        """Handle keyboard input (Ctrl+Enter to send)"""
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            self.send_message()
        else:
            QTextEdit.keyPressEvent(self.input_text, event)
    
    def send_message(self):
        """Send user message and get AI response"""
        message = self.input_text.toPlainText().strip()
        
        if not message:
            return
        
        if not self.ai_manager.provider:
            if not self.ai_manager.initialize_provider():
                QMessageBox.warning(
                    self,
                    "AI Not Available",
                    "AI Provider not configured. Please set up API key in settings."
                )
                return
        
        # Get context from current file
        context = self._get_current_file_context()
        
        # Update context indicator
        if context:
            file_name = self.parent_ide.current_file.split('/')[-1] if self.parent_ide.current_file else "untitled"
            self.context_label.setText(f"📎 Including context from: {file_name}")
            self.context_label.setVisible(True)
        else:
            self.context_label.setVisible(False)
        
        # Add user message to chat
        self.add_chat_bubble(message, is_user=True)
        self.input_text.clear()
        
        # Disable send button
        self.send_btn.setEnabled(False)
        
        # Show thinking bubble
        thinking_bubble = ChatBubble("🤔 Thinking...", is_user=False)
        thinking_bubble.set_thinking()
        bubble_index = len(self.chat_layout) - 1
        self.chat_layout.insertWidget(bubble_index, thinking_bubble)
        
        # Start worker with context
        self.current_worker = AIWorker(self.ai_manager, message, context)
        self.current_worker.response_ready.connect(
            lambda resp: self._on_response(resp, thinking_bubble)
        )
        self.current_worker.error_occurred.connect(
            lambda err: self._on_error(err, thinking_bubble)
        )
        self.current_worker.start()
    
    def _get_current_file_context(self) -> str:
        """Get context from currently open file in IDE"""
        if not self.parent_ide:
            return ""
        
        try:
            # Get current editor
            editor = self.parent_ide.get_current_editor()
            if not editor:
                return ""
            
            # Get file path and code
            current_file = self.parent_ide.current_file
            code = editor.toPlainText()
            
            if not code or len(code.strip()) == 0:
                return ""
            
            # Limit context size to avoid token limits
            max_lines = 200
            lines = code.split('\n')
            if len(lines) > max_lines:
                code = '\n'.join(lines[:max_lines])
                code += f"\n\n... ({len(lines) - max_lines} more lines)"
            
            # Build context
            file_name = current_file.split('/')[-1] if current_file else "untitled"
            context = f"Current file: {file_name}\n\n```python\n{code}\n```"
            
            return context
        except Exception as e:
            logger.debug(f"Error getting file context: {e}")
            return ""
    
    def _on_response(self, response: str, thinking_bubble):
        """Handle AI response"""
        self.chat_layout.removeWidget(thinking_bubble)
        thinking_bubble.deleteLater()
        
        self.add_chat_bubble(response, is_user=False)
        self.send_btn.setEnabled(True)
        
        # Scroll to bottom
        QApplication.processEvents()
    
    def _on_error(self, error: str, thinking_bubble):
        """Handle AI error"""
        self.chat_layout.removeWidget(thinking_bubble)
        thinking_bubble.deleteLater()
        
        self.add_chat_bubble(f"❌ Error: {error}", is_user=False)
        self.send_btn.setEnabled(True)
    
    def add_chat_bubble(self, message: str, is_user: bool = True):
        """Add message bubble to chat"""
        bubble = ChatBubble(message, is_user)
        bubble_index = len(self.chat_layout) - 1
        self.chat_layout.insertWidget(bubble_index, bubble)
    
    def clear_chat(self):
        """Clear chat history"""
        # Remove all bubbles except stretch
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.ai_manager.clear_cache()
        logger.info("Chat cleared")
    
    def on_provider_changed(self, provider_name: str):
        """Handle provider selection change"""
        if self.ai_manager.initialize_provider(provider_name.lower()):
            logger.info(f"Switched to {provider_name}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to initialize {provider_name} provider")
    
    def show_settings(self):
        """Show AI settings dialog"""
        # Update temperature
        ai_settings = self.settings.get("ai", {})
        self.settings.update_ai_settings(
            temperature=self.temp_spinbox.value()
        )
        logger.info("AI settings updated")
        QMessageBox.information(self, "Settings", "AI settings updated!")
    
    def get_stats(self):
        """Get AI manager statistics"""
        return self.ai_manager.get_stats()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    settings = SettingsManager()
    panel = AIChatPanel(settings)
    panel.setWindowTitle("AI Chat Panel")
    panel.resize(400, 600)
    panel.show()
    
    sys.exit(app.exec_())
