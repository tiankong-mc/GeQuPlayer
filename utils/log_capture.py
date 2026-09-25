"""捕获 stdout/stderr，通过 Qt 信号发送到 UI（线程安全）"""
import sys
import threading

from PyQt6.QtCore import QObject, pyqtSignal


class LogCapture(QObject):
    """把 print 的输出同时送到原始终端和 UI"""
    message_written = pyqtSignal(str)

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        super().__init__()
        self._original_stdout = None
        self._original_stderr = None
        self._buffer = ""
        self._max_buffer = 50000
        self._max_line = 5000

    @classmethod
    def instance(cls) -> "LogCapture":
        with cls._lock:
            if cls._instance is None:
                cls._instance = LogCapture()
        return cls._instance

    def install(self):
        if self._original_stdout is not None:
            return
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self

    def uninstall(self):
        if self._original_stdout is not None:
            sys.stdout = self._original_stdout
            sys.stderr = self._original_stderr
            self._original_stdout = None
            self._original_stderr = None

    def write(self, text):
        if self._original_stdout:
            try:
                self._original_stdout.write(text)
                self._original_stdout.flush()
            except Exception:
                pass

        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.rstrip("\r")
            if len(line) > self._max_line:
                line = line[:self._max_line] + "...[truncated]"
            if line:
                try:
                    self.message_written.emit(line)
                except Exception:
                    pass

        if len(self._buffer) > self._max_buffer:
            self._buffer = self._buffer[-self._max_buffer:]

    def flush(self):
        if self._original_stdout:
            try:
                self._original_stdout.flush()
            except Exception:
                pass

    def isatty(self):
        return False
