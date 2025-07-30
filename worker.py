import itertools
import json

from loguru import logger
from PyQt6.QtCore import QObject, QThread, QTimer, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtNetwork import (QNetworkAccessManager, QNetworkReply,
                             QNetworkRequest)

from models import POTA, SOTA, DXHeat, DXSummit


class SpotHandler(QObject):
    models = {'pota': POTA, 'sota': SOTA, 'dxsummit': DXSummit, 'dxheat': DXHeat}
    band_ranges = {
        '40m': (7000, 7200),
        '15m': (21000, 21450),
        '2m': (144000, 146000),
        '70cm': (430000, 440000)
    }
    default_bands = ['40m', '15m', '2m', '70cm']
    default_modes = ['SSB', 'FM', '']

    def __init__(self):
        super().__init__()
        self.spots = {}

    @pyqtSlot(tuple)
    def store_spots(self, payload):
        """
        For a given API ID (name), remove existing spots and replace them with new;
        Convert from plain dict into a list of pydantic model instances.
        """

        name, raw_data = payload
        data = json.loads(raw_data)
        model = self.models[name]
        spots = [model(**sp) for sp in data]
        if name in self.spots:
            del self.spots[name]
        logger.debug("Storing {} {} spots", len(spots), name)
        self.spots[name] = spots

    def get_unique(self):
        """
        Filter spots, sort them by time and then pick unique items;
        The same spot might be returned from more than one API.
        """

        sdata = sorted(
            self.filter_spots(itertools.chain(*self.spots.values())),
            key=lambda item: getattr(item, 'timestamp'),
            reverse=True
        )
        unique = []
        for item in sdata:
            found = False
            for ex in unique:
                if item.activator == ex.activator and abs(item.frequency - ex.frequency) < 1:
                    found = True
                    break
            if not found:
                unique.append(item)
        return unique

    @staticmethod
    def filter_spots(spots: list, bands=None, mode=None):
        """Filter spots that match selected bands and modes"""

        if bands is None:
            bands = SpotHandler.default_bands
        if mode is None:
            mode = SpotHandler.default_modes
        band_map = [SpotHandler.band_ranges[k] for k in bands]
        band_ok = lambda f: any([f > b[0] and f < b[1] for b in band_map])
        mode_ok = lambda m: m.upper() in mode
        return filter(
            lambda s: mode_ok(s.mode) and band_ok(s.frequency),
            spots
        )


class ApiManager(QNetworkAccessManager):
    apis = {
        'pota': QUrl("https://api.pota.app/v1/spots"),
        'sota': QUrl("https://api-db2.sota.org.uk/api/spots/-2/all/all"),
        'dxsummit': QUrl("http://www.dxsummit.fi/api/v1/spots"),
        'dxheat': QUrl(
            "https://dxheat.com/source/spots/?a=65&b=15&b=40&m=CW&m=PHONE&m=DIGI&valid=1&spam=1"
        )
    }
    store_spots = pyqtSignal(tuple)

    def __init__(self, table, poll_time):
        super().__init__(None)
        self.table = table
        self.manager = QNetworkAccessManager()
        self.manager.finished.connect(self.handle_response)

        self.active_requests = {}
        self.spot_processor_thread = QThread()
        self.spot_handler = SpotHandler()
        self.spot_handler.moveToThread(self.spot_processor_thread)
        self.store_spots.connect(self.spot_handler.store_spots)
        self.spot_processor_thread.start()

        self.timer = QTimer()
        self.timer.timeout.connect(self.fetch_all)
        self.timer.start(poll_time)

        self.table_timer = QTimer()
        self.table_timer.timeout.connect(self.rebuild_table)
        self.table_timer.start(poll_time)

        self.fetch_all()
        QTimer().singleShot(5000, self.rebuild_table)

    def fetch_all(self):
        """Start asynchronous fetch from each defined API and mark as work-in-progress"""

        for name, url in self.apis.items():
            if name in self.active_requests.values():
                logger.info("Skipping fetch from {}, because another is pending", name)
                continue
            logger.debug("Fetching from {}", url.toString())
            request = QNetworkRequest(url)
            reply = self.manager.get(request)
            self.active_requests[reply] = name

    @pyqtSlot("QNetworkReply*")
    def handle_response(self, reply):
        """Once the API replies, check for errors, mark job as done and store collected spots"""

        name = self.active_requests.pop(reply, "UNKNOWN")
        logger.debug("{} has finished", name)

        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll().data().decode()
            self.store_spots.emit((name, data))
        else:
            status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            logger.warning("Error for {}: {}, code = {}", name, reply.errorString(), status_code)

        reply.deleteLater()

    def rebuild_table(self):
        """Get unique spots and pass to the table"""

        unique = self.spot_handler.get_unique()
        self.table.populate_table(unique)

