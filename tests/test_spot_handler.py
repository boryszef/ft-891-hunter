import pytest
from pydantic import BaseModel

from ft_891_hunter.worker import SpotHandler


def test_spot_handler():
    handler = SpotHandler()
    with open('tests/pota_response.json', encoding='utf-8') as pota_file:
        handler.store_spots(('pota', pota_file.read()))

    assert len(handler.spots['pota']) == 3

    spot = handler.spots['pota'][0]
    assert isinstance(spot, BaseModel)
    assert spot.locator == 'JO87kb'
    assert pytest.approx(spot.distance, 1) == 6520