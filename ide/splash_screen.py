"""
Splash Screen for Py-IDE
Displays logo/icon for 2 seconds on startup
"""

import os
from PyQt5.QtWidgets import QSplashScreen, QApplication
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QTimer


class SplashScreen(QSplashScreen):
    """Custom splash screen with logo and version info"""
    
    def __init__(self, icon_path, version="1.0.0"):
        # Load the icon/logo
        pixmap = QPixmap(icon_path)
        
        # Scale to appropriate size (400x400 for splash)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            # Fallback: create a simple colored splash
            pixmap = QPixmap(400, 400)
            pixmap.fill(QColor("#2B2B2B"))
        
        super().__init__(pixmap, Qt.WindowStaysOnTopHint)
        
        self.version = version
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Show the splash screen
        self.show()
        
        # Update message
        self.showMessage(
            f"Py-IDE v{self.version}\nLoading...",
            Qt.AlignBottom | Qt.AlignCenter,
            QColor("#FFFFFF")
        )
        
        # Process events to ensure splash is shown
        QApplication.processEvents()
    
    def drawContents(self, painter):
        """Custom drawing for splash screen"""
        super().drawContents(painter)
        
        # Draw version text at bottom
        painter.setPen(QColor("#BBBBBB"))
        painter.setFont(QFont("Segoe UI", 10))
        
        rect = self.rect()
        text_rect = rect.adjusted(10, 0, -10, -10)
        
        painter.drawText(
            text_rect,
            Qt.AlignBottom | Qt.AlignCenter,
            f"Py-IDE v{self.version}\nLoading..."
        )


def show_splash(icon_path, version="1.0.0", duration=2000):
    """
    Show splash screen for specified duration
    
    Args:
        icon_path: Path to icon/logo image
        version: Version string to display
        duration: Display duration in milliseconds (default: 2000ms = 2 seconds)
    
    Returns:
        SplashScreen instance
    """
    splash = SplashScreen(icon_path, version)
    
    # Auto-close after duration
    QTimer.singleShot(duration, splash.close)
    
    return splash
