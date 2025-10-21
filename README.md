# PyC-IDE

A professional, modular Python IDE with advanced features inspired by PyCharm and VS Code.

## 🏗️ Architecture

```
DTC/
├── ide/
│   ├── __init__.py
│   ├── main.py          # Main IDE window
│   ├── editor.py        # Code editor with syntax highlighting
│   ├── terminal.py      # Interactive terminal
│   ├── explorer.py      # File explorer widget
│   └── utils/
│       ├── __init__.py
│       ├── settings.py  # Settings persistence (JSON)
│       ├── logger.py    # Thread-safe logging
│       └── workers.py   # Background thread workers
├── run_ide.py           # Launcher script
└── main.py              # Legacy monolithic version
```

## ✨ Features

### Core Features
- **Modular Architecture**: Clean separation of concerns
- **Dark Theme**: Py Darcula-inspired color scheme
- **Tabbed Editor**: Multiple files open simultaneously
- **File Explorer**: Browse, create, delete files and folders
- **Interactive Terminal**: Run shell commands and Python scripts

### Advanced Features
- **Syntax Highlighting**: Python code with PyCharm colors
- **Line Numbers**: Professional code editor feel
- **Autocomplete**: Jedi-powered IntelliSense
- **Autosave**: Automatic file saving (1-second delay)
- **Settings Persistence**: Remembers last project, theme, preferences
- **Thread-Safe Logging**: All operations logged to file
- **QProcess Execution**: Non-blocking code execution with live output
- **Background Workers**: File I/O and linting in separate threads

### UI Components
- **Vertical Navbar**: Quick access to file explorer and terminal
- **Status Bar**: Shows line/column position
- **Menu Bar**: File, Edit, View, Run, Help menus
- **Toolbar**: Quick action buttons
- **Context Menus**: Right-click on files for operations

## 🚀 Usage

### Running the IDE

```bash
python run_ide.py
```

### Keyboard Shortcuts

- `Ctrl+N` - New File
- `Ctrl+Alt+N` - New Python File
- `Ctrl+O` - Open File
- `Ctrl+K` - Open Folder
- `Ctrl+S` - Save
- `Ctrl+Shift+S` - Save As
- `Shift+F10` - Run Code
- `Alt+1` - Toggle File Explorer

### Terminal Commands

- `run` - Run current editor file
- `python filename.py` - Run specific file
- `cd <path>` - Change directory
- `clear` or `cls` - Clear terminal
- Any shell command works!

## 🔧 Performance Optimizations

1. **Background Threading**: File operations don't block UI
2. **QProcess**: Async code execution with live streaming
3. **Lazy Loading**: Components loaded on demand
4. **Settings Caching**: Fast startup with persistent settings
5. **Error-Safe Logging**: All exceptions logged automatically

## 📁 Settings Location

Settings are stored in: `~/.pycharm_ide/settings.json`
Logs are stored in: `~/.pycharm_ide/logs/`

## 🎨 Customization

Edit `ide/utils/settings.py` to add more settings:
- Theme customization
- Font family and size
- Autosave interval
- Default project directory
- AI API keys

## 🐛 Debugging

Check logs in `~/.pycharm_ide/logs/` for error details.

## 📦 Dependencies

```bash
pip install PyQt5 jedi pylint
```

## 🔮 Future Enhancements

- AI code suggestions (GPT integration)
- Data structure visualizer
- Git integration
- Debugging tools
- Plugin system
- More language support

---

**Built with PyQt5 | Modular | Production-Ready**
