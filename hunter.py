import os
import sys

import humanize
import serial
from dotenv import load_dotenv
from loguru import logger
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QMainWindow,  # QPushButton,
                             QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)

from worker import ApiManager
from config import UPDATE_PERIOD, STATUS_TIMEOUT, serial_settings


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

    def __init__(self):
        super().__init__()
        self.setRowCount(0)
        self.setColumnCount(len(self.spot_columns))
        self.setHorizontalHeaderLabels(self.spot_columns)
        self.freq_index = self.spot_columns.index("Freq")

    def populate_table(self, unique):
        self.setRowCount(len(unique))
        logger.debug('Populating table with {} spots', len(unique))
        for idx, item in enumerate(unique):
            timestamp = QTableWidgetItem(humanize.naturaltime(item.timestamp))
            timestamp.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(idx, 0, timestamp)
            freq = QTableWidgetItem(str(item.frequency))
            freq.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(idx, 1, freq)
            self.setItem(idx, 2, QTableWidgetItem(item.mode))
            self.setItem(idx, 3, QTableWidgetItem(item.programme))
            self.setItem(idx, 4, QTableWidgetItem(getattr(item, 'reference', '')))
            self.setItem(idx, 5, QTableWidgetItem(item.activator))
            self.setItem(idx, 6, QTableWidgetItem(item.comment))
            self.setItem(idx, 7, QTableWidgetItem(item.locator))
            dist = QTableWidgetItem(f"{item.distance:.0f}")
            dist.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(idx, 8, dist)
            self.setItem(idx, 9, QTableWidgetItem(item.origin))
        logger.debug('Table finished')
        self.resizeColumnsToContents()
        self.clearSelection()
        self.setCurrentCell(-1, -1)

    def get_selected_freq(self, row):
        item = self.item(row, self.freq_index)
        try:
            return int(round(float(item.text()) * 1000))
        except (ValueError, TypeError):
            return None


class MainWindow(QMainWindow):

    serial = None

    def __init__(self):
        self.serial = serial.Serial(**serial_settings)
        super().__init__()

        self.setWindowTitle("Hunter")

        self.table = SpotTable()
        self.table.cellClicked.connect(self.cell_clicked)

#        button = QPushButton("Press Me!")
#        button.setCheckable(True)
#        button.clicked.connect(self.the_button_was_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
#        layout.addWidget(button)

        self.resize(1400, 800)
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.statusBar().showMessage("Starting", STATUS_TIMEOUT)
        self.api = ApiManager(self.table, UPDATE_PERIOD)

    def the_button_was_clicked(self):
        self.serial.write(b'FA;')
        print(self.serial.read(12))
        self.serial.write(b'FB;')
        print(self.serial.read(12))

    def cell_clicked(self, row, column):
        if column == self.table.freq_index:
            freq = self.table.get_selected_freq(row)
            if freq:
                self.tune_in(freq)

    def tune_in(self, freq):
        logger.debug("Tuning to {}", freq)
        msg = f"FA{freq:09d};".encode('ascii')
        self.serial.write(msg)
        try:
            msg = self.serial.read(12).decode('utf-8')
            self.statusBar().showMessage(f"Response: {msg}", STATUS_TIMEOUT)
        except UnicodeDecodeError:
            pass


app = QApplication(sys.argv)
with open('dark.css') as css:
    app.setStyleSheet(css.read())

main_window = MainWindow()
main_window.show()


if __name__ == '__main__':
    logger.debug('Application starting')
    load_dotenv()
    app.exec()
    logger.debug('Application exited')

