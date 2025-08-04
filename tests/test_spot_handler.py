from datetime import timezone

import pytest
from pydantic import BaseModel

from ft_891_hunter.worker import SpotHandler


@pytest.fixture(scope="module")
def pota():
    handler = SpotHandler()
    with open('tests/pota_response.json', encoding='utf-8') as pota_file:
        handler.store_spots(('pota', pota_file.read()))
    return handler.spots['pota']


def test_correct_structure(pota):
    assert len(pota) == 3
    assert isinstance(pota[0], BaseModel)


def test_simple_fields(pota):
    assert pytest.approx(pota[0].frequency, 1) == 14322
    assert pota[0].mode == 'SSB'
    assert pota[0].activator == 'SM5YRA/P'
    assert pota[0].reference == 'SE-0375'
    assert pota[0].comment == "THANK YOU 73+ QRV 2-fer: SE-0375 SE-0376"
    assert pytest.approx(pota[0].latitude, 0.0001) == 57.0522
    assert pytest.approx(pota[0].longitude, 0.0001) == 16.8460
    assert pota[0].origin == 'POTA'


def test_properties(pota):
    assert pota[0].locator == 'JO87kb'
    assert pytest.approx(pota[0].distance, 1) == 6520
    assert pota[0].programme == 'POTA 🏞'


def test_timestamp(pota):
    assert pota[0].timestamp.year == 2025
    assert pota[0].timestamp.month == 8
    assert pota[0].timestamp.day == 1
    assert pota[0].timestamp.hour == 11
    assert pota[0].timestamp.minute == 28
    assert pota[0].timestamp.second == 40
    assert pota[0].timestamp.tzinfo == timezone.utc
