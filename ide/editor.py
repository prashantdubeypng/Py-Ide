"""
Code Editor Widget with syntax highlighting, line numbers, and IntelliSense
"""
from PyQt5.QtWidgets import QPlainTextEdit, QWidget, QTextEdit, QCompleter
from PyQt5.QtGui import (QFont, QColor, QPainter, QTextCharFormat, 
                        QSyntaxHighlighter, QTextCursor, QKeyEvent, QTextFormat)
from PyQt5.QtCore import Qt, QRect, QSize, QRegExp, QTimer, QStringListModel
import jedi


class LineNumberArea(QWidget):
    """Line number widget for code editor"""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


class PythonHighlighter(QSyntaxHighlighter):
    """Python syntax highlighter  colors"""
    
    def __init__(self, document):
        super().__init__(document)
        self.highlightingRules = []
        
        # Keywords
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor(204, 120, 50))
        keywords = ["def", "class", "import", "from", "as", "if", "elif", "else",
                   "for", "while", "return", "try", "except", "finally", "with",
                   "True", "False", "None", "and", "or", "not", "in", "is", "lambda",
                   "yield", "break", "continue", "pass", "raise", "assert", "del",
                   "global", "nonlocal", "async", "await"]
        for word in keywords:
            pattern = QRegExp(f"\\b{word}\\b")
            self.highlightingRules.append((pattern, keywordFormat))
        
        # Built-in functions
        builtinFormat = QTextCharFormat()
        builtinFormat.setForeground(QColor(152, 118, 170))
        builtins = ["print", "len", "range", "str", "int", "float", "list", "dict",
                   "set", "tuple", "open", "input", "type", "isinstance", "enumerate",
                   "zip", "map", "filter", "sum", "max", "min", "abs", "all", "any"]
        for word in builtins:
            pattern = QRegExp(f"\\b{word}\\b")
            self.highlightingRules.append((pattern, builtinFormat))
        
        # Strings
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor(106, 135, 89))
        self.highlightingRules.append((QRegExp("\".*\""), stringFormat))
        self.highlightingRules.append((QRegExp("'.*'"), stringFormat))
        
        # Comments
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor(128, 128, 128))
        self.highlightingRules.append((QRegExp("#[^\n]*"), commentFormat))
        
        # Numbers
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor(104, 151, 187))
        self.highlightingRules.append((QRegExp("\\b[0-9]+\\b"), numberFormat))

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)


class LintHighlighter(QSyntaxHighlighter):
    """Highlights linting errors"""
    
    def __init__(self, document):
        super().__init__(document)
        self.errors = []

    def set_errors(self, errors):
        self.errors = errors
        self.rehighlight()

    def highlightBlock(self, text):
        for err in self.errors:
            if self.currentBlock().blockNumber() + 1 == err.get("line", 0):
                fmt = QTextCharFormat()
                fmt.setUnderlineColor(QColor("#FF5555"))
                fmt.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
                col = err.get("column", 0)
                self.setFormat(col, len(text) - col, fmt)


class CodeEditor(QPlainTextEdit):
    """Advanced code editor with line numbers, autocomplete, and linting"""
    
    def __init__(self, parent_ide=None):
        super().__init__()
        self.parent_ide = parent_ide
        self.highlighter = PythonHighlighter(self.document())

        # Line numbers
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()
        
        # Autocomplete
        self.completer = None
        self.autocomplete_timer = QTimer()
        self.autocomplete_timer.setSingleShot(True)
        self.autocomplete_timer.timeout.connect(self.show_autocomplete)
        
        # Styling
        self.setFont(QFont("Consolas", 12))
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #2B2B2B;
                color: #A9B7C6;
                border: none;
                selection-background-color: #214283;
            }
        """)
    
    def lineNumberAreaWidth(self):
        digits = len(str(max(1, self.blockCount())))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor(49, 51, 53))

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor(128, 128, 128))
                painter.drawText(0, int(top), self.lineNumberArea.width() - 5, 
                               self.fontMetrics().height(), Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(47, 51, 55)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)
    
    def keyPressEvent(self, event: QKeyEvent):
        super().keyPressEvent(event)
        
        # Trigger autocomplete on alphanumeric input
        if event.text() and event.text().isalnum():
            self.autocomplete_timer.start(150)
    
    def show_autocomplete(self):
        """Show autocomplete suggestions using Jedi"""
        cursor = self.textCursor()
        code = self.toPlainText()
        line = cursor.blockNumber() + 1
        column = cursor.positionInBlock()
        
        try:
            script = jedi.Script(code)
            completions = script.complete(line, column)
            words = [c.name for c in completions if c.name]
            
            if words:
                if not self.completer:
                    self.completer = QCompleter(self)
                    self.completer.setWidget(self)
                    self.completer.setCaseSensitivity(Qt.CaseInsensitive)
                    self.completer.setCompletionMode(QCompleter.PopupCompletion)
                    self.completer.activated.connect(self.insert_completion)
                
                model = QStringListModel(words)
                self.completer.setModel(model)
                
                # Show popup
                rect = self.cursorRect()
                rect.setWidth(self.completer.popup().sizeHintForColumn(0)
                            + self.completer.popup().verticalScrollBar().sizeHint().width())
                self.completer.complete(rect)
        except Exception:
            pass
    
    def insert_completion(self, completion):
        """Insert selected completion"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Left)
        cursor.movePosition(QTextCursor.EndOfWord)
        cursor.insertText(completion)
        self.setTextCursor(cursor)
