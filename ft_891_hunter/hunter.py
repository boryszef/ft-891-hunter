import sys
from importlib.resources import files

import serial
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QLabel, QMainWindow, QPushButton,  # pylint: disable=E0401,E0611
                             QStackedLayout, QVBoxLayout, QHBoxLayout, QWidget)

from ft_891_hunter.config import STATUS_TIMEOUT, UPDATE_PERIOD, serial_settings
from ft_891_hunter.dialogs import LogViewer, SpotTable, FilterSelector
from ft_891_hunter.log import logger
from ft_891_hunter.worker import ApiManager


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

        button_container = QWidget()
        button_layout = QHBoxLayout()
        button_container.setLayout(button_layout)

        filters_button = QPushButton("Filters")
        filters_button.clicked.connect(self.set_filters)

        logs_button = QPushButton("Logs")
        logs_button.setCheckable(True)
        logs_button.clicked.connect(self.show_logs)

        quit_button = QPushButton("Quit")
        quit_button.clicked.connect(QApplication.instance().quit)

        button_layout.addWidget(filters_button)
        button_layout.addWidget(logs_button)
        button_layout.addWidget(quit_button)

        main_layout.addWidget(stacked_container)
        main_layout.addWidget(button_container)

        self.resize(1400, 800)

        self.statusBar().showMessage("Starting", STATUS_TIMEOUT)
        #self.table_updater = SpotTableUpdater(self.table)
        self.api = ApiManager(self.table, UPDATE_PERIOD)

    def show_logs(self):
        """Show dialog with recent log records"""

        dlg = LogViewer(self)
        dlg.show()

    def set_filters(self):
        dlg = FilterSelector(self)
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


def get_app():
    app = QApplication(sys.argv)
    css_path = files("ft_891_hunter.resources").joinpath("dark.css")
    with open(css_path, encoding='ascii') as css:
        app.setStyleSheet(css.read())
    return app
