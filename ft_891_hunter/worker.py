"""Worker classes related to fetching spots from APIs"""

import itertools
import json
from collections import namedtuple
from typing import Iterable

import humanize
from PyQt6.QtCore import QObject, QThread, QTimer, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtNetwork import (QNetworkAccessManager, QNetworkReply,
                             QNetworkRequest)

from ft_891_hunter.log import logger
from ft_891_hunter.models import POTA, SOTA, DXHeat, DXSummit
from ft_891_hunter.config import PREFERRED_BANDS, PREFERRED_MODES


SpotData = namedtuple(
        "SpotData",
        ['idx', 'timestamp', 'frequency', 'mode', 'programme', 'reference',
         'activator', 'comment', 'locator', 'distance', 'origin']
)


class SpotHandler(QObject):
    models = {'pota': POTA, 'sota': SOTA, 'dxsummit': DXSummit, 'dxheat': DXHeat}
    band_ranges = {
        '80m': (3500, 3800),
        '40m': (7000, 7200),
        '30m': (10100, 10150),
        '20m': (14000, 14350),
        '15m': (21000, 21450),
        '10m': (28000, 29700),
        '6m': (50000, 52000),
        '2m': (144000, 146000),
        '70cm': (430000, 440000)
    }
    store_finished = pyqtSignal()

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
        self.spots[name] = spots
        logger.debug("Storing {} {} spots", len(self.spots[name]), name)
        self.store_finished.emit()


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
    filter_spots = pyqtSignal(dict)

    def __init__(self, table_updater, spot_handler, poll_time):
        super().__init__(None)
        self.table_updater = table_updater
        self.spot_handler = spot_handler
        self.manager = QNetworkAccessManager()
        self.manager.finished.connect(self.handle_response)

        self.active_requests = {}

        self.store_spots.connect(self.spot_handler.store_spots)
        self.spot_handler.store_finished.connect(self.trigger_table_update)

        self.timer = QTimer()
        self.timer.timeout.connect(self.fetch_all)
        self.timer.start(poll_time)

        self.filter_spots.connect(self.table_updater.run)

        self.table_timer = QTimer(self)
        self.table_timer.timeout.connect(lambda: self.filter_spots.emit(self.spot_handler.spots))
        self.table_timer.setInterval(10_000)
        self.table_timer.setSingleShot(True)

        self.fetch_all()

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
    
    @pyqtSlot()
    def trigger_table_update(self):
        if not self.table_timer.isActive():
            logger.debug("Starting timer to update table")
            self.table_timer.start()
        else:
            logger.debug("Skipping update, timer is active")


class SpotTableUpdater(QObject):
    finished = pyqtSignal(list)

    @pyqtSlot(dict)
    def run(self, spots):
        """
        Filter spots, sort them by time and then pick unique items;
        The same spot might be returned from more than one API.
        """

        logger.debug("Filtering spots")
        spots_copy = list(itertools.chain(*spots.values()))
        sdata = sorted(
            self.filter_spots(spots_copy),
            key=lambda item: getattr(item, 'timestamp'),
            reverse=True
        )
        logger.debug("Filtered {} spots", len(sdata))
        unique = []
        idx = 0
        for item in sdata:
            found = False
            for ex in unique:
                if item.activator == ex.activator and abs(item.frequency - float(ex.frequency)) < 1:
                    found = True
                    break
            if not found:
                spot = SpotData(
                    idx=idx,
                    timestamp=humanize.naturaltime(item.timestamp),
                    frequency=str(item.frequency),
                    mode=item.mode,
                    programme=item.programme,
                    reference=getattr(item, 'reference', ''),
                    activator=item.activator,
                    comment=item.comment,
                    locator=item.locator,
                    distance=f"{item.distance:.0f}" if item.distance else "",
                    origin=item.origin
                )
                unique.append(spot)
                idx += 1
        logger.debug("{} unique spots", len(unique))
        self.finished.emit(unique)

    @staticmethod
    def filter_spots(spots: Iterable, bands=None, mode=None):
        """Filter spots that match selected bands and modes"""

        if bands is None:
            bands = PREFERRED_BANDS
        if mode is None:
            mode = PREFERRED_MODES
        band_map = [SpotHandler.band_ranges[k] for k in bands]
        logger.debug("Filter parameters: {} {}", band_map, mode)

        def band_ok(f):
            return f and any(f > b[0] and f < b[1] for b in band_map)

        def mode_ok(m):
            return m.upper() in mode

        return filter(
            lambda s: mode_ok(s.mode) and band_ok(s.frequency),
            spots
        )
