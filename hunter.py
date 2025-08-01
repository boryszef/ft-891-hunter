import sys

import serial
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton,
                             QVBoxLayout, QWidget, QStackedLayout, QLabel)

from config import STATUS_TIMEOUT, UPDATE_PERIOD, serial_settings
from dialogs import LogViewer, SpotTable
from log import logger
from worker import ApiManager


class MainWindow(QMainWindow):

    serial = None

    def __init__(self):
        try:
            self.serial = serial.Serial(**serial_settings)
        except (FileNotFoundError, serial.serialutil.SerialException):
            pass
        super().__init__()

        self.setWindowTitle("FT-891 Hunter")

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        stacked_container = QWidget()
        self.stack = QStackedLayout()
        stacked_container.setLayout(self.stack)

        spinner_label = QLabel("Loading...", alignment=Qt.AlignmentFlag.AlignCenter)

        self.table = SpotTable(self.stack)
        self.table.cellClicked.connect(self.cell_clicked)

        self.stack.addWidget(spinner_label)
        self.stack.addWidget(self.table)

        button = QPushButton("Logs")
        button.setCheckable(True)
        button.clicked.connect(self.show_logs)

        main_layout.addWidget(stacked_container)
        main_layout.addWidget(button)

        self.resize(1400, 800)

        self.statusBar().showMessage("Starting", STATUS_TIMEOUT)
        self.api = ApiManager(self.table, UPDATE_PERIOD)

    def show_logs(self):
        """Show dialog with recent log records"""

        dlg = LogViewer(self)
        dlg.show()

    def cell_clicked(self, row, column):
        """When frequency cell clicked, tune the rig to that frequency"""

        if column == self.table.freq_index:
            freq = self.table.get_selected_freq(row)
            if freq:
                self.tune_in(freq)

    def tune_in(self, freq):
        """Given the frequency, use serial port of the rig to send tune request"""

        self.statusBar().showMessage(f"Tuning to {freq}", STATUS_TIMEOUT)
        msg = f"FA{freq:09d};".encode('ascii')
        try:
            self.serial.write(msg)
        except (FileNotFoundError, serial.serialutil.SerialException):
            logger.exception("Serial port not available")
            return


app = QApplication(sys.argv)
with open('dark.css', encoding='ascii') as css:
    app.setStyleSheet(css.read())

main_window = MainWindow()
main_window.show()


if __name__ == '__main__':
    logger.debug('Application starting')
    app.exec()
    logger.debug('Application exited')

