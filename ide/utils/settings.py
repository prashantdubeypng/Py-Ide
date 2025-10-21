"""
Settings Manager for Py-IDE
Handles persistent configuration storage
"""
import json
import os
from pathlib import Path


class SettingsManager:
    """Manages IDE settings with JSON persistence"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".py_ide"
        self.config_file = self.config_dir / "settings.json"
        self.config_dir.mkdir(exist_ok=True)
        
        self.default_settings = {
            "last_project": "",
            "theme": "dark",
            "font_size": 12,
            "font_family": "Consolas",
            "ai_api_key": "",
            "autosave_enabled": True,
            "autosave_interval": 1000,
            "recent_files": [],
            "window_geometry": {},
            "file_explorer_visible": True,
            "terminal_visible": True,
            "linting_enabled": True,
            "autocomplete_enabled": True,
        }
        
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from JSON file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return {**self.default_settings, **loaded}
            except Exception as e:
                print(f"Error loading settings: {e}")
                return self.default_settings.copy()
        return self.default_settings.copy()
    
    def save_settings(self):
        """Save settings to JSON file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Set a setting value"""
        self.settings[key] = value
        self.save_settings()
    
    def add_recent_file(self, filepath):
        """Add file to recent files list"""
        recent = self.settings.get("recent_files", [])
        if filepath in recent:
            recent.remove(filepath)
        recent.insert(0, filepath)
        self.settings["recent_files"] = recent[:10]  # Keep only 10 recent
        self.save_settings()
    
    def get_recent_files(self):
        """Get list of recent files"""
        return self.settings.get("recent_files", [])
