"""
AI Settings Dialog
Configure API keys, providers, and AI preferences
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTabWidget, QWidget, QGroupBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QMessageBox, QFormLayout,
    QScrollArea, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

from ide.utils.secret_manager import SecretManager
from ide.utils.settings import SettingsManager
from ide.utils.logger import logger


class AIProviderWidget(QWidget):
    """Widget for configuring a single AI provider"""
    
    def __init__(self, provider_name: str, secret_manager: SecretManager):
        super().__init__()
        self.provider_name = provider_name
        self.secret_manager = secret_manager
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup provider configuration UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Provider info
        title = QLabel(f"🔑 {self.provider_name.upper()} Configuration")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title.setStyleSheet("color: #4B6EAF;")
        layout.addWidget(title)
        
        # API Key input
        key_layout = QHBoxLayout()
        key_label = QLabel("API Key:")
        key_label.setFixedWidth(80)
        key_layout.addWidget(key_label)
        
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setPlaceholderText(f"Enter your {self.provider_name.upper()} API key")
        self.key_input.setStyleSheet("""
            QLineEdit {
                background-color: #2B2B2B;
                color: #A9B7C6;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
                font-family: Consolas;
            }
            QLineEdit:focus {
                border: 1px solid #4B6EAF;
            }
        """)
        key_layout.addWidget(self.key_input)
        
        # Show/Hide button
        self.show_btn = QPushButton("👁")
        self.show_btn.setFixedSize(30, 30)
        self.show_btn.setCheckable(True)
        self.show_btn.setStyleSheet("""
            QPushButton {
                background-color: #3C3F41;
                border: 1px solid #555555;
                border-radius: 3px;
            }
            QPushButton:checked {
                background-color: #4B6EAF;
            }
        """)
        self.show_btn.clicked.connect(self.toggle_key_visibility)
        key_layout.addWidget(self.show_btn)
        
        layout.addLayout(key_layout)
        
        # Model selection
        if self.provider_name == "openai":
            model_layout = QHBoxLayout()
            model_label = QLabel("Model:")
            model_label.setFixedWidth(80)
            model_layout.addWidget(model_label)
            
            self.model_combo = QComboBox()
            self.model_combo.addItems([
                "gpt-3.5-turbo",
                "gpt-4",
                "gpt-4-turbo",
                "gpt-4o",
                "gpt-4o-mini"
            ])
            self.model_combo.setStyleSheet("""
                QComboBox {
                    background-color: #2B2B2B;
                    color: #A9B7C6;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    padding: 5px;
                }
            """)
            model_layout.addWidget(self.model_combo)
            layout.addLayout(model_layout)
        
        elif self.provider_name == "gemini":
            model_layout = QHBoxLayout()
            model_label = QLabel("Model:")
            model_label.setFixedWidth(80)
            model_layout.addWidget(model_label)
            
            self.model_combo = QComboBox()
            self.model_combo.addItems([
                "gemini-2.0-flash-exp",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-pro",
                "gemini-pro-vision"
            ])
            self.model_combo.setStyleSheet("""
                QComboBox {
                    background-color: #2B2B2B;
                    color: #A9B7C6;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    padding: 5px;
                }
            """)
            model_layout.addWidget(self.model_combo)
            layout.addLayout(model_layout)
        
        # Test button
        test_btn = QPushButton("Test Connection")
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #3C3F41;
                color: #A9B7C6;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #4B4F51;
            }
        """)
        test_btn.clicked.connect(self.test_connection)
        layout.addWidget(test_btn)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def toggle_key_visibility(self):
        """Toggle API key visibility"""
        if self.show_btn.isChecked():
            self.key_input.setEchoMode(QLineEdit.Normal)
        else:
            self.key_input.setEchoMode(QLineEdit.Password)
    
    def load_settings(self):
        """Load saved API key"""
        api_key = self.secret_manager.get_secret(self.provider_name)
        if api_key:
            self.key_input.setText(api_key)
    
    def save_settings(self):
        """Save API key"""
        api_key = self.key_input.text().strip()
        if api_key:
            self.secret_manager.set_secret(self.provider_name, api_key)
            logger.info(f"Saved API key for {self.provider_name}")
            return True
        return False
    
    def get_model(self):
        """Get selected model"""
        if hasattr(self, 'model_combo'):
            return self.model_combo.currentText()
        return None
    
    def test_connection(self):
        """Test API connection"""
        api_key = self.key_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "No API Key", "Please enter an API key first")
            return
        
        # Save temporarily for test
        self.secret_manager.set_secret(self.provider_name, api_key)
        
        # Test based on provider
        try:
            if self.provider_name == "openai":
                self._test_openai()
            elif self.provider_name == "gemini":
                self._test_gemini()
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", f"Error: {str(e)}")
    
    def _test_openai(self):
        """Test OpenAI connection"""
        try:
            import requests
            
            api_key = self.key_input.text().strip()
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                QMessageBox.information(
                    self, 
                    "Success!", 
                    "OpenAI connection successful!\n\nAPI key is valid."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Connection Failed",
                    f"Status: {response.status_code}\n{response.text[:200]}"
                )
        except ImportError:
            QMessageBox.warning(
                self,
                "Missing Library",
                "Please install requests: pip install requests"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def _test_gemini(self):
        """Test Gemini connection"""
        try:
            import requests
            
            api_key = self.key_input.text().strip()
            # Use Gemini 2.0 Flash for testing (requires v1beta API)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
            
            # Send a simple test request
            payload = {
                "contents": [{
                    "parts": [{"text": "Hello"}]
                }]
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                QMessageBox.information(
                    self,
                    "Success!",
                    "Gemini connection successful!\n\nAPI key is valid."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Connection Failed",
                    f"Status: {response.status_code}\n{response.text[:200]}"
                )
        except ImportError:
            QMessageBox.warning(
                self,
                "Missing Library",
                "Please install requests: pip install requests"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class AISettingsDialog(QDialog):
    """Dialog for AI configuration"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings_manager
        self.secret_manager = SecretManager()
        
        self.setWindowTitle("⚙️ AI Settings")
        self.resize(600, 500)
        self.setup_ui()
        self.load_settings()
        
        # Apply dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2B2B2B;
            }
            QLabel {
                color: #BBBBBB;
            }
            QTabWidget::pane {
                border: 1px solid #3C3F41;
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
                color: #4B6EAF;
            }
        """)
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget
        tabs = QTabWidget()
        
        # Tab 1: API Keys
        keys_tab = self.create_keys_tab()
        tabs.addTab(keys_tab, "🔑 API Keys")
        
        # Tab 2: General Settings
        general_tab = self.create_general_tab()
        tabs.addTab(general_tab, "⚙️ General")
        
        # Tab 3: Advanced
        advanced_tab = self.create_advanced_tab()
        tabs.addTab(advanced_tab, "🔧 Advanced")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(10, 10, 10, 10)
        
        save_btn = QPushButton("💾 Save")
        save_btn.setFixedHeight(32)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4B6EAF;
                color: #FFFFFF;
                border: none;
                border-radius: 3px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5C7FBF;
            }
        """)
        save_btn.clicked.connect(self.save_and_close)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(32)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3C3F41;
                color: #BBBBBB;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #4B4F51;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def create_keys_tab(self):
        """Create API keys tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # OpenAI provider
        self.openai_widget = AIProviderWidget("openai", self.secret_manager)
        layout.addWidget(self.openai_widget)
        
        # Separator
        separator = QLabel()
        separator.setFixedHeight(2)
        separator.setStyleSheet("background-color: #3C3F41;")
        layout.addWidget(separator)
        
        # Gemini provider
        self.gemini_widget = AIProviderWidget("gemini", self.secret_manager)
        layout.addWidget(self.gemini_widget)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def create_general_tab(self):
        """Create general settings tab"""
        widget = QWidget()
        layout = QFormLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Default provider
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "Gemini"])
        self.provider_combo.setStyleSheet("""
            QComboBox {
                background-color: #2B2B2B;
                color: #A9B7C6;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        layout.addRow("Default Provider:", self.provider_combo)
        
        # Temperature
        self.temp_spinbox = QDoubleSpinBox()
        self.temp_spinbox.setMinimum(0.0)
        self.temp_spinbox.setMaximum(2.0)
        self.temp_spinbox.setValue(0.7)
        self.temp_spinbox.setSingleStep(0.1)
        self.temp_spinbox.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2B2B2B;
                color: #A9B7C6;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        layout.addRow("Temperature:", self.temp_spinbox)
        
        # Max tokens
        self.tokens_spinbox = QSpinBox()
        self.tokens_spinbox.setMinimum(100)
        self.tokens_spinbox.setMaximum(8000)
        self.tokens_spinbox.setValue(4000)
        self.tokens_spinbox.setSingleStep(100)
        self.tokens_spinbox.setStyleSheet("""
            QSpinBox {
                background-color: #2B2B2B;
                color: #A9B7C6;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        layout.addRow("Max Tokens:", self.tokens_spinbox)
        
        # Docstring style
        self.docstring_combo = QComboBox()
        self.docstring_combo.addItems(["Google", "NumPy", "Sphinx"])
        self.docstring_combo.setStyleSheet("""
            QComboBox {
                background-color: #2B2B2B;
                color: #A9B7C6;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        layout.addRow("Docstring Style:", self.docstring_combo)
        
        widget.setLayout(layout)
        return widget
    
    def create_advanced_tab(self):
        """Create advanced settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Cache settings group
        cache_group = QGroupBox("Cache Settings")
        cache_group.setStyleSheet("""
            QGroupBox {
                color: #BBBBBB;
                border: 1px solid #3C3F41;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        cache_layout = QFormLayout()
        
        self.cache_ttl_spinbox = QSpinBox()
        self.cache_ttl_spinbox.setMinimum(300)
        self.cache_ttl_spinbox.setMaximum(86400)
        self.cache_ttl_spinbox.setValue(3600)
        self.cache_ttl_spinbox.setSingleStep(300)
        self.cache_ttl_spinbox.setSuffix(" seconds")
        self.cache_ttl_spinbox.setStyleSheet("""
            QSpinBox {
                background-color: #2B2B2B;
                color: #A9B7C6;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        cache_layout.addRow("Cache TTL:", self.cache_ttl_spinbox)
        
        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)
        
        # Rate limiting group
        rate_group = QGroupBox("Rate Limiting")
        rate_group.setStyleSheet(cache_group.styleSheet())
        rate_layout = QFormLayout()
        
        self.rate_requests_spinbox = QSpinBox()
        self.rate_requests_spinbox.setMinimum(1)
        self.rate_requests_spinbox.setMaximum(100)
        self.rate_requests_spinbox.setValue(10)
        self.rate_requests_spinbox.setStyleSheet(self.cache_ttl_spinbox.styleSheet())
        rate_layout.addRow("Max Requests:", self.rate_requests_spinbox)
        
        self.rate_window_spinbox = QSpinBox()
        self.rate_window_spinbox.setMinimum(10)
        self.rate_window_spinbox.setMaximum(300)
        self.rate_window_spinbox.setValue(60)
        self.rate_window_spinbox.setSuffix(" seconds")
        self.rate_window_spinbox.setStyleSheet(self.cache_ttl_spinbox.styleSheet())
        rate_layout.addRow("Time Window:", self.rate_window_spinbox)
        
        rate_group.setLayout(rate_layout)
        layout.addWidget(rate_group)
        
        # Flow analysis settings
        flow_group = QGroupBox("Flow Analysis")
        flow_group.setStyleSheet(cache_group.styleSheet())
        flow_layout = QVBoxLayout()
        
        self.flow_ai_check = QCheckBox("Enable AI-powered flow analysis")
        self.flow_ai_check.setChecked(True)
        self.flow_ai_check.setStyleSheet("color: #A9B7C6;")
        flow_layout.addWidget(self.flow_ai_check)
        
        self.flow_explain_check = QCheckBox("Show function explanations in graph")
        self.flow_explain_check.setChecked(True)
        self.flow_explain_check.setStyleSheet("color: #A9B7C6;")
        flow_layout.addWidget(self.flow_explain_check)
        
        flow_group.setLayout(flow_layout)
        layout.addWidget(flow_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def load_settings(self):
        """Load current settings"""
        ai_settings = self.settings.get("ai", {})
        
        # General
        provider = ai_settings.get("provider", "openai")
        self.provider_combo.setCurrentText(provider.title())
        
        self.temp_spinbox.setValue(ai_settings.get("temperature", 0.7))
        self.tokens_spinbox.setValue(ai_settings.get("max_tokens", 4000))
        
        docstring_style = ai_settings.get("docstring_style", "google")
        self.docstring_combo.setCurrentText(docstring_style.title())
        
        # Advanced
        self.cache_ttl_spinbox.setValue(ai_settings.get("cache_ttl", 3600))
        self.rate_requests_spinbox.setValue(ai_settings.get("rate_limit_requests", 10))
        self.rate_window_spinbox.setValue(ai_settings.get("rate_limit_window", 60))
        
        # Flow analysis
        self.flow_ai_check.setChecked(ai_settings.get("flow_ai_enabled", True))
        self.flow_explain_check.setChecked(ai_settings.get("flow_explain_enabled", True))
    
    def save_and_close(self):
        """Save all settings and close"""
        # Save API keys
        openai_saved = self.openai_widget.save_settings()
        gemini_saved = self.gemini_widget.save_settings()
        
        if not openai_saved and not gemini_saved:
            reply = QMessageBox.question(
                self,
                "No API Keys",
                "No API keys configured. AI features will not work.\n\nContinue anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Save general settings
        ai_settings = {
            "provider": self.provider_combo.currentText().lower(),
            "temperature": self.temp_spinbox.value(),
            "max_tokens": self.tokens_spinbox.value(),
            "docstring_style": self.docstring_combo.currentText().lower(),
            "cache_ttl": self.cache_ttl_spinbox.value(),
            "rate_limit_requests": self.rate_requests_spinbox.value(),
            "rate_limit_window": self.rate_window_spinbox.value(),
            "flow_ai_enabled": self.flow_ai_check.isChecked(),
            "flow_explain_enabled": self.flow_explain_check.isChecked()
        }
        
        # Save model selections
        openai_model = self.openai_widget.get_model()
        if openai_model:
            ai_settings["openai_model"] = openai_model
        
        gemini_model = self.gemini_widget.get_model()
        if gemini_model:
            ai_settings["gemini_model"] = gemini_model
        
        # Unpack dictionary to use **kwargs
        self.settings.update_ai_settings(**ai_settings)
        
        QMessageBox.information(
            self,
            "Settings Saved",
            "✅ AI settings saved successfully!\n\nRestart AI features to apply changes."
        )
        
        self.settings_changed.emit()
        self.accept()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    settings = SettingsManager()
    dialog = AISettingsDialog(settings)
    dialog.show()
    
    sys.exit(app.exec_())
