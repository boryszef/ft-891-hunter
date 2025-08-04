"""
Pydantic models for incoming spot data
together with logic related to unification and alignment of data
"""

import re
import shelve
from datetime import datetime, timezone
from typing import Optional

import haversine
import maidenhead
import requests
from pydantic import BaseModel, Field, field_validator, model_validator

from ft_891_hunter.config import MY_LATITUDE, MY_LONGITUDE, SHELVE_PATH, API_TIMEOUT
from ft_891_hunter.log import logger

summit_re = re.compile(r"(?P<country>[A-Z0-9]{1,3})\/(?P<region>[A-Z]{2})-\d+")
wwff_re = re.compile(r"[A-Za-z0-9]{1,2}[Ff]{2}-[0-9]{4}")
iota_re = re.compile(r"(^|\s)iota($|\s)", re.I)
pota_re = re.compile(r"(^|\s)pota($|\s)", re.I)
SOTA_REGION_URL = "https://api-db2.sota.org.uk/api/regions/{}/{}"


class PropMixin:

    @property
    def distance(self):
        """Measure distance with respect to own coordinates (from the env)"""

        if self.latitude is not None and self.longitude is not None:
            return haversine.haversine((MY_LATITUDE, MY_LONGITUDE), (self.latitude, self.longitude))
        return None

    @property
    def programme(self):
        """Guess programme based on the comment parameter"""

        try:
            return getattr(self, 'programme_')
        except AttributeError:
            if wwff_re.search(self.comment or ''):
                return 'WWFF ☘'
            if iota_re.search(self.comment or ''):
                return 'IOTA 🏝'
            if pota_re.search(self.comment or ''):
                return 'POTA 🏞'
        return ''

    @property
    def locator(self):
        """Get the Maidenhead locator from coordinates"""

        try:
            return getattr(self, 'locator_')
        except AttributeError:
            return maidenhead.to_maiden(self.latitude, self.longitude, 3)


class POTA(BaseModel, PropMixin):
    frequency: float
    mode: str
    activator: str
    reference: str
    timestamp: datetime = Field(alias='spotTime')
    locator_: str = Field(alias='grid6')
    comment: str = Field(alias='comments')
    latitude: float
    longitude: float
    origin: str = 'POTA'
    programme_: str = Field(default='POTA 🏞')

    @field_validator('timestamp', mode='before')
    @classmethod
    def ensure_utc(cls, v: str):
        """Add UTC timezone to the timestamp"""

        dt = datetime.fromisoformat(v)

        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)


def store_summits(db, country, region):
    """Get missing summit info and store in the shelve cache"""

    response = requests.get(SOTA_REGION_URL.format(country, region), timeout=API_TIMEOUT)
    if response.status_code != 200:
        logger.debug("Failed to get summit codes")
        return
    data = response.json()
    for summit in data['summits']:
        db[summit['summitCode']] = summit['locator'], summit['latitude'], summit['longitude']


def get_coordinates_from_summit_code(summit):
    """
    Get coordinates from the cached summit information based on the summit code;
    call API if not found.
    """

    with shelve.open(SHELVE_PATH) as db:
        if summit not in db:
            logger.debug("Summit {} not found locally", summit)
            match = summit_re.match(summit)
            if match:
                store_summits(db, match.group("country"), match.group("region"))
        return db.get(summit, (None, None, None))


class SOTA(BaseModel, PropMixin):
    frequency: Optional[float]
    mode: str
    timestamp: datetime = Field(alias='timeStamp')
    activator: str = Field(alias='activatorCallsign')
    reference: str = Field(alias='summitCode')
    comment: Optional[str] = Field(alias='comments', default='')
    origin: str = 'SOTA'
    latitude: float = None
    longitude: float = None
    programme_: str = Field(default='SOTA ⛰')
    locator_: str = None

    @model_validator(mode="after")
    def get_coordinates(self):
        """Get activator coordinates based on the summit code"""

        (
            self.locator_,
            self.latitude,
            self.longitude
        ) = get_coordinates_from_summit_code(self.reference)
        return self

    @field_validator('timestamp', mode='before')
    @classmethod
    def ensure_utc(cls, v: str):
        """Add UTC timezone to the timestamp"""

        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))

        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @field_validator("frequency", mode="before")
    @classmethod
    def scale_value(cls, v: str | None) -> float:
        """Frequency should be stored in kHz"""

        return float(v) * 1000 if v else None

    @field_validator("comment", mode="before")
    @classmethod
    def convert_null_to_empty(cls, v: str | None):
        return v or ""


class DXSummit(BaseModel, PropMixin):
    frequency: float
    activator: str = Field(alias='dx_call')
    timestamp: datetime = Field(alias='time')
    comment: Optional[str] = Field(alias='info')
    mode: str = Field(default='')
    latitude: float = Field(alias='dx_latitude')
    longitude: float = Field(alias='dx_longitude')
    origin: str = 'DXSummit'

    @field_validator('timestamp', mode='before')
    @classmethod
    def ensure_utc(cls, v: str):
        """Add UTC timezone to the timestamp"""

        try:
            dt = datetime.fromisoformat(v)
        except Exception as exc:
            logger.exception(v)
            raise exc

        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)


class DXHeat(BaseModel, PropMixin):
    frequency: float = Field(alias='Frequency')
    activator: str = Field(alias='DXCall')
    Time: str
    Date: str
    mode: Optional[str] = Field(alias='Mode', default='')
    locator_: Optional[str] = Field(alias='DXLocator', default='')
    comment: str = Field(alias='Comment')
    latitude: float = None
    longitude: float = None
    origin: str = 'DXHeat'

    @model_validator(mode="after")
    def get_coordinates_from_locator(self):
        if not self.locator:
            return self
        self.latitude, self.longitude = maidenhead.to_location(self.locator_)
        return self

    @field_validator('mode', mode='before')
    @classmethod
    def convert_mode(cls, v):
        """Mode should be stored as SSB"""

        return 'SSB' if v in ('LSB', 'USB') else v

    @property
    def timestamp(self):
        """Combine date and time into a single timestamp"""

        return datetime.strptime(f"{self.Date} {self.Time} +0000", "%d/%m/%y %H:%M %z")
