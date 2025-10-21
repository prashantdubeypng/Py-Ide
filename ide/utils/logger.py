"""
Logger utility for Py-IDE
Thread-safe logging with file output
"""
import logging
import os
from pathlib import Path
from datetime import datetime


class IDELogger:
    """Singleton logger for the IDE"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Create logs directory
        log_dir = Path.home() / ".py_ide" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"ide_{timestamp}.log"
        
        # Configure logger
        self.logger = logging.getLogger("Py-IDE")
        self.logger.setLevel(logging.DEBUG)
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("IDE Logger initialized")
    
    def debug(self, message, exc_info=False):
        self.logger.debug(message, exc_info=exc_info)
    
    def info(self, message, exc_info=False):
        self.logger.info(message, exc_info=exc_info)
    
    def warning(self, message, exc_info=False):
        self.logger.warning(message, exc_info=exc_info)
    
    def error(self, message, exc_info=False):
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message, exc_info=False):
        self.logger.critical(message, exc_info=exc_info)


# Singleton instance
logger = IDELogger()
