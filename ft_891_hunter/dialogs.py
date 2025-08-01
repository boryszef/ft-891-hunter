"""Application specific widgets and popups"""

from collections import deque

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (QDialog, QLabel, QPlainTextEdit, QStackedLayout,
                             QTableWidget, QTableWidgetItem, QVBoxLayout)

from ft_891_hunter.log import log_buffer, logger


class LogViewer(QDialog):
    send_logs = pyqtSignal(deque)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Logs")
        self.resize(1400, 900)

        layout = QVBoxLayout(self)

        spinner_label = QLabel("Loading...", alignment=Qt.AlignmentFlag.AlignCenter)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)

        self.stack = QStackedLayout()
        self.stack.addWidget(spinner_label)
        self.stack.addWidget(self.log_text)

        layout.addLayout(self.stack)

        self.load_content()

    def load_content(self):
        """
        Call log renderer in a separate thread to serialize logs
        into a sigle blob of text, suitable for QPlainTextEdit widget
        """

        self.render_thread = QThread()
        self.renderer = LogRenderer()
        self.renderer.moveToThread(self.render_thread)
        self.render_thread.started.connect(self.renderer.run)
        self.renderer.finished.connect(self.update_logs)
        self.renderer.finished.connect(self.render_thread.quit)
        self.renderer.finished.connect(self.renderer.deleteLater)
        self.render_thread.finished.connect(self.render_thread.deleteLater)
        self.render_thread.start()

    def update_logs(self, logs):
        """
        Called when the worker finishes rendering text -
        switch from the spinner widget to text.
        """

        self.log_text.setPlainText(logs)
        self.stack.setCurrentIndex(1)


class LogRenderer(QObject):
    finished = pyqtSignal(str)

    def run(self):
        render = "\n".join(reversed(log_buffer))
        self.finished.emit(render)


class SpotTable(QTableWidget):
    spot_columns = [
        "Time",
        "Freq",
        "Mode",
        "Prog",
        "Ref",
        "Activator",
        "Comment",
        "Locator",
        "Dist [km]",
        "Source"
    ]

    def __init__(self, stack):
        super().__init__()
        self.setRowCount(0)
        self.setColumnCount(len(self.spot_columns))
        self.setHorizontalHeaderLabels(self.spot_columns)
        self.setSortingEnabled(False)
        self.freq_index = self.spot_columns.index("Freq")
        self.stack = stack

    @pyqtSlot(list)
    def populate_table(self, unique):
        """
        Given the list of spots, populate table.
        unique is a list of namedtuples, containing values serialized to text -
        ready to display. All conversion is done in a task.
        """

        self.stack.setCurrentIndex(0)
        self.setUpdatesEnabled(False)
        self.setRowCount(len(unique))
        logger.debug('Populating table with {} spots', len(unique))
        for item in unique:
            idx =item.idx
            timestamp = QTableWidgetItem(item.timestamp)
            timestamp.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(idx, 0, timestamp)
            freq = QTableWidgetItem(item.frequency)
            freq.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(idx, 1, freq)
            self.setItem(idx, 2, QTableWidgetItem(item.mode))
            self.setItem(idx, 3, QTableWidgetItem(item.programme))
            self.setItem(idx, 4, QTableWidgetItem(item.reference))
            self.setItem(idx, 5, QTableWidgetItem(item.activator))
            self.setItem(idx, 6, QTableWidgetItem(item.comment))
            self.setItem(idx, 7, QTableWidgetItem(item.locator))
            dist = QTableWidgetItem(item.distance)
            dist.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(idx, 8, dist)
            self.setItem(idx, 9, QTableWidgetItem(item.origin))
        logger.debug('Table finished')
        self.setUpdatesEnabled(True)
        self.resizeColumnsToContents()
        self.clearSelection()
        self.setCurrentCell(-1, -1)
        self.stack.setCurrentIndex(1)

    def get_selected_freq(self, row):
        """Get frequency from the selected cell as int kHz"""

        item = self.item(row, self.freq_index)
        try:
            return int(round(float(item.text()) * 1000))
        except (ValueError, TypeError):
            return None
