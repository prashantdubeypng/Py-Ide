"""
Auto-updater module for Py-IDE
Handles checking for updates, downloading new versions, and installing them
"""

import requests
import os
import sys
import subprocess
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QProgressBar, 
                             QPushButton, QApplication, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal


class DownloadThread(QThread):
    """Thread for downloading update file with progress tracking"""
    progress = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, url, dest):
        super().__init__()
        self.url = url
        self.dest = dest
        self._is_cancelled = False

    def run(self):
        try:
            response = requests.get(self.url, stream=True, timeout=30)
            response.raise_for_status()
            
            total = int(response.headers.get('content-length', 0))
            
            with open(self.dest, 'wb') as f:
                downloaded = 0
                for data in response.iter_content(chunk_size=8192):
                    if self._is_cancelled:
                        return
                    if not data:
                        continue
                    f.write(data)
                    downloaded += len(data)
                    if total:
                        percent = int((downloaded / total) * 100)
                        self.progress.emit(percent)
            
            self.finished_signal.emit(self.dest)
        except Exception as e:
            self.error_signal.emit(str(e))

    def cancel(self):
        self._is_cancelled = True


class UpdaterUI(QWidget):
    """UI for downloading and installing updates"""
    
    def __init__(self, url, current_exe_path=None):
        super().__init__()
        self.url = url
        self.current_exe_path = current_exe_path or self._get_current_exe_path()
        self.downloaded_file = None
        self.init_ui()

    def _get_current_exe_path(self):
        """Get the path of the currently running executable"""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            return sys.executable
        else:
            # Running as script (for testing)
            return os.path.join(os.getcwd(), "Py-IDE.exe")

    def init_ui(self):
        self.setWindowTitle("Py-IDE Updater")
        self.setFixedSize(500, 180)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Status label
        self.label = QLabel("Downloading update...")
        self.label.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(self.label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress)
        
        # Size/Speed info label
        self.info_label = QLabel("Starting download...")
        self.info_label.setStyleSheet("font-size: 11px; color: #888;")
        layout.addWidget(self.info_label)
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                font-size: 12px;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.cancel_btn.clicked.connect(self.cancel_download)
        layout.addWidget(self.cancel_btn, alignment=Qt.AlignRight)
        
        # Start download
        dest = os.path.join(os.path.dirname(self.current_exe_path), "Py-IDE_new.exe")
        self.thread = DownloadThread(self.url, dest)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished_signal.connect(self.download_complete)
        self.thread.error_signal.connect(self.download_error)
        self.thread.start()

    def update_progress(self, percent):
        self.progress.setValue(percent)
        self.info_label.setText(f"Downloaded: {percent}%")

    def download_complete(self, downloaded_file):
        self.downloaded_file = downloaded_file
        self.label.setText("✓ Download complete!")
        self.info_label.setText("Installing update and restarting...")
        self.cancel_btn.setEnabled(False)
        
        # Wait a moment for user to see completion
        QApplication.processEvents()
        
        # Replace and restart
        self.replace_exe()

    def download_error(self, error_msg):
        self.label.setText("✗ Download failed!")
        self.info_label.setText(f"Error: {error_msg}")
        self.cancel_btn.setText("Close")
        QMessageBox.critical(self, "Update Error", 
                            f"Failed to download update:\n{error_msg}")

    def cancel_download(self):
        if hasattr(self, 'thread') and self.thread.isRunning():
            self.thread.cancel()
            self.thread.wait()
        self.close()

    def replace_exe(self):
        """Replace the old executable with the new one and restart"""
        try:
            # Create a batch script to replace the exe after this process exits
            batch_script = os.path.join(os.path.dirname(self.current_exe_path), "update_install.bat")
            
            with open(batch_script, 'w') as f:
                f.write("@echo off\n")
                f.write("timeout /t 2 /nobreak >nul\n")  # Wait for app to close
                f.write(f'del /f /q "{self.current_exe_path}"\n')
                f.write(f'move /y "{self.downloaded_file}" "{self.current_exe_path}"\n')
                f.write(f'start "" "{self.current_exe_path}"\n')
                f.write(f'del /f /q "{batch_script}"\n')  # Delete itself
            
            # Run the batch script and exit
            subprocess.Popen(['cmd', '/c', batch_script], 
                           shell=False, 
                           creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Exit the application
            QApplication.quit()
            sys.exit(0)
            
        except Exception as e:
            QMessageBox.critical(self, "Update Error", 
                               f"Failed to install update:\n{str(e)}")


def run_updater(download_url, current_exe_path=None):
    """
    Launch the updater UI
    
    Args:
        download_url: URL to download the new executable from
        current_exe_path: Path to current executable (optional, auto-detected)
    """
    # Check if we need to create a new QApplication or use existing one
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        new_app = True
    else:
        new_app = False
    
    updater_window = UpdaterUI(download_url, current_exe_path)
    updater_window.show()
    
    if new_app:
        app.exec_()
