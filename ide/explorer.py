"""
File Explorer Widget
"""
from PyQt5.QtWidgets import QTreeView, QFileSystemModel, QMenu, QAction, QInputDialog, QMessageBox
from PyQt5.QtCore import Qt, QDir
import os
import shutil


class FileExplorer(QTreeView):
    """File explorer with context menu and file operations"""
    
    def __init__(self, project_dir, parent_ide=None):
        super().__init__()
        self.parent_ide = parent_ide
        self.project_dir = project_dir
        
        # Setup model
        self.model = QFileSystemModel()
        self.model.setRootPath(self.project_dir)
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)
        
        # Setup view
        self.setModel(self.model)
        self.setRootIndex(self.model.index(self.project_dir))
        self.setColumnWidth(0, 250)
        self.setHeaderHidden(True)
        
        # Hide extra columns
        for i in range(1, self.model.columnCount()):
            self.hideColumn(i)
        
        # Context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Double click to open
        self.doubleClicked.connect(self.open_file)
        
        # Styling
        self.setStyleSheet("""
            QTreeView {
                background-color: #2B2B2B;
                color: #BBBBBB;
                border: none;
                border-right: 1px solid #323232;
                outline: 0;
            }
            QTreeView::item {
                padding: 4px;
            }
            QTreeView::item:hover {
                background-color: #3C3F41;
            }
            QTreeView::item:selected {
                background-color: #4B6EAF;
                color: white;
            }
        """)
    
    def open_file(self, index):
        """Open file in editor"""
        path = self.model.filePath(index)
        if os.path.isfile(path) and self.parent_ide:
            self.parent_ide.open_file_by_path(path)
    
    def show_context_menu(self, position):
        """Show context menu on right-click"""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #3C3F41;
                color: #BBBBBB;
                border: 1px solid #555555;
            }
            QMenu::item {
                padding: 5px 30px;
            }
            QMenu::item:selected {
                background-color: #4B6EAF;
            }
        """)
        
        index = self.indexAt(position)
        
        # New Python File action
        new_py_action = QAction("New Python File", self)
        new_py_action.triggered.connect(self.new_python_file)
        menu.addAction(new_py_action)
        
        menu.addSeparator()
        
        # Delete action (only if item is selected)
        if index.isValid():
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.delete_file(index))
            menu.addAction(delete_action)
        
        # Refresh action
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_tree)
        menu.addAction(refresh_action)
        
        menu.exec_(self.viewport().mapToGlobal(position))
    
    def new_python_file(self):
        """Create a new Python file"""
        filename, ok = QInputDialog.getText(
            self, 
            "New Python File", 
            "Enter file name (without .py extension):"
        )
        
        if ok and filename:
            if not filename.endswith('.py'):
                filename += '.py'
            
            filepath = os.path.join(self.project_dir, filename)
            
            if os.path.exists(filepath):
                QMessageBox.warning(self, "File Exists", f"File '{filename}' already exists!")
                return
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("# Python file created in Py-IDE\n\n")
                    f.write("def main():\n")
                    f.write("    pass\n\n")
                    f.write("if __name__ == '__main__':\n")
                    f.write("    main()\n")
                
                if self.parent_ide:
                    self.parent_ide.open_file_by_path(filepath)
                    self.parent_ide.statusBar().showMessage(f"Created {filename}")
                
                self.refresh_tree()
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create file: {str(e)}")
    
    def delete_file(self, index):
        """Delete the selected file or folder"""
        path = self.model.filePath(index)
        filename = os.path.basename(path)
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{filename}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                
                if self.parent_ide:
                    self.parent_ide.statusBar().showMessage(f"Deleted {filename}")
                
                self.refresh_tree()
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not delete: {str(e)}")
    
    def refresh_tree(self):
        """Refresh the file tree"""
        self.model.setRootPath("")
        self.model.setRootPath(self.project_dir)
        self.setRootIndex(self.model.index(self.project_dir))
    
    def set_project_dir(self, new_dir):
        """Change the project directory"""
        self.project_dir = new_dir
        self.model.setRootPath(self.project_dir)
        self.setRootIndex(self.model.index(self.project_dir))
