"""Settings dialog for configuring API keys and AI options."""
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QMessageBox,
    QCheckBox
)
from PyQt5.QtCore import Qt

from ide.utils.secret_manager import SecretManager


class SettingsDialog(QDialog):
    """Dialog allowing the user to configure AI provider settings."""

    PLACEHOLDER = "Stored"

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.settings = settings_manager
        self.secret_manager = SecretManager()

        self.default_provider_combo = QComboBox()
        self.default_provider_combo.addItems(["openai", "gemini"])

        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setEchoMode(QLineEdit.Password)
        self.openai_key_edit.setPlaceholderText("OpenAI API Key")

        self.gemini_key_edit = QLineEdit()
        self.gemini_key_edit.setEchoMode(QLineEdit.Password)
        self.gemini_key_edit.setPlaceholderText("Gemini API Key")

        self.cache_checkbox = QCheckBox("Enable response caching")

        self.temperature_edit = QLineEdit()
        self.temperature_edit.setPlaceholderText("0.2")

        self._build_ui()
        self._load_existing()

    def _build_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        form.addRow(QLabel("Default AI Provider"), self.default_provider_combo)
        form.addRow(QLabel("OpenAI API Key"), self.openai_key_edit)
        form.addRow(QLabel("Gemini API Key"), self.gemini_key_edit)
        form.addRow(QLabel("Temperature"), self.temperature_edit)
        form.addRow(self.cache_checkbox)

        layout.addLayout(form)

        button_bar = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        test_btn = QPushButton("Test Key")

        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        test_btn.clicked.connect(self._test_keys)

        button_bar.addStretch(1)
        button_bar.addWidget(test_btn)
        button_bar.addWidget(cancel_btn)
        button_bar.addWidget(save_btn)

        layout.addLayout(button_bar)
        self.setLayout(layout)

    def _load_existing(self):
        ai_settings = self.settings.get_ai_settings()
        provider = ai_settings.get("default_provider", "openai")
        index = self.default_provider_combo.findText(provider)
        if index >= 0:
            self.default_provider_combo.setCurrentIndex(index)

        temperature = ai_settings.get("temperature", 0.2)
        self.temperature_edit.setText(str(temperature))
        self.cache_checkbox.setChecked(ai_settings.get("cache_enabled", True))

        # Do not display stored keys in plain text, only indicator
        if self.secret_manager.get_secret("openai"):
            self.openai_key_edit.setPlaceholderText(self.PLACEHOLDER)
        if self.secret_manager.get_secret("gemini"):
            self.gemini_key_edit.setPlaceholderText(self.PLACEHOLDER)

    def accept(self):  # noqa: D401
        if not self._save_settings():
            return
        super().accept()

    def _save_settings(self) -> bool:
        default_provider = self.default_provider_combo.currentText()
        try:
            temperature = float(self.temperature_edit.text() or 0.2)
        except ValueError:
            QMessageBox.warning(self, "Invalid input", "Temperature must be a number.")
            return False

        openai_input = self.openai_key_edit.text().strip()
        gemini_input = self.gemini_key_edit.text().strip()

        try:
            if openai_input and openai_input != "-":
                self._store_key("openai", openai_input)
            if gemini_input and gemini_input != "-":
                self._store_key("gemini", gemini_input)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid key", str(exc))
            return False

        # Allow user to clear keys by typing a single dash
        if openai_input == "-":
            self.secret_manager.delete_secret("openai")
        if gemini_input == "-":
            self.secret_manager.delete_secret("gemini")

        self.settings.update_ai_settings(
            default_provider=default_provider,
            temperature=temperature,
            cache_enabled=self.cache_checkbox.isChecked()
        )
        return True

    def _store_key(self, provider: str, raw_key: str):
        trimmed = raw_key.strip()
        if not trimmed:
            return
        if len(trimmed) < 10:
            raise ValueError("API key appears invalid (too short)")
        self.secret_manager.set_secret(provider, trimmed)

    def _test_keys(self):
        provider = self.default_provider_combo.currentText()
        key = self.secret_manager.get_secret(provider)
        if not key and self._active_input(provider):
            key = self._active_input(provider)
        if not key:
            QMessageBox.information(self, "Test", f"No {provider} key configured.")
            return
        masked = key[:4] + "..." + key[-4:]
        QMessageBox.information(self, "Test", f"Key looks valid: {masked}")

    def _active_input(self, provider: str) -> str:
        if provider == "openai":
            return self.openai_key_edit.text().strip()
        if provider == "gemini":
            return self.gemini_key_edit.text().strip()
        return ""
