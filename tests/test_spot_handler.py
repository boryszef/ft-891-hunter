from datetime import timezone
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from ft_891_hunter.worker import SpotHandler


@pytest.fixture(scope="module", autouse=True)
def spot_handler():
    yield SpotHandler()


@pytest.fixture(scope="module")
def pota(spot_handler):
    with open('tests/pota_response.json', encoding='utf-8') as pota_file:
        spot_handler.store_spots(('pota', pota_file.read()))
    return spot_handler.spots['pota']


@pytest.fixture(scope="module")
@patch(
    "ft_891_hunter.models.get_coordinates_from_summit_code",
    return_value=("AB12cd", 1.23, 4.56)
)
def sota(coord_mock, spot_handler):
    with open('tests/sota_response.json', encoding='utf-8') as pota_file:
        spot_handler.store_spots(('sota', pota_file.read()))
    return spot_handler.spots['sota']


def test_correct_structure(pota, sota):
    assert len(pota) == 3
    assert all(isinstance(obj, BaseModel) for obj in pota)

    assert len(sota) == 3
    assert all(isinstance(obj, BaseModel) for obj in sota)


def test_simple_fields_pota(pota):
    assert pytest.approx(pota[0].frequency, 1) == 14322
    assert pota[0].mode == 'SSB'
    assert pota[0].activator == 'SM5YRA/P'
    assert pota[0].reference == 'SE-0375'
    assert pota[0].comment == "THANK YOU 73+ QRV 2-fer: SE-0375 SE-0376"
    assert pytest.approx(pota[0].latitude, 0.0001) == 57.0522
    assert pytest.approx(pota[0].longitude, 0.0001) == 16.8460
    assert pota[0].origin == 'POTA'


def test_simple_fields_sota(sota):
    assert sota[0].mode == 'SSB'
    assert sota[0].activator == 'F4JYM/P'
    assert sota[0].reference == "F/CR-041"
    assert sota[0].comment == ""
    assert sota[1].comment == "[RBNHole] at K2PO/7 21 WPM 13 dB SNR"
    assert sota[0].origin == 'SOTA'


def test_sota_frequency_conversion(sota):
    assert pytest.approx(sota[0].frequency, 1) == 14241
    assert sota[2].frequency == None


def test_properties(pota, sota):
    assert pota[0].locator == 'JO87kb'
    assert pytest.approx(pota[0].distance, 1) == 6520
    assert pota[0].programme == 'POTA 🏞'

    assert sota[0].locator == 'AB12cd'
    assert pytest.approx(sota[0].latitude, 0.0001) == 1.2300
    assert pytest.approx(sota[0].longitude, 0.0001) == 4.5600
    assert pytest.approx(sota[0].distance, 1) == 525
    assert sota[0].programme == 'SOTA ⛰'


def test_timestamp_pota(pota):
    assert pota[0].timestamp.year == 2025
    assert pota[0].timestamp.month == 8
    assert pota[0].timestamp.day == 1
    assert pota[0].timestamp.hour == 11
    assert pota[0].timestamp.minute == 28
    assert pota[0].timestamp.second == 40
    assert pota[0].timestamp.tzinfo == timezone.utc


def test_timestamp_sota(sota):
    assert sota[0].timestamp.year == 2025
    assert sota[0].timestamp.month == 8
    assert sota[0].timestamp.day == 4
    assert sota[0].timestamp.hour == 7
    assert sota[0].timestamp.minute == 9
    assert sota[0].timestamp.second == 21
    assert sota[0].timestamp.tzinfo == timezone.utc