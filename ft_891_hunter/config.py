"""Static configuration plus user settings from the env file"""

import os
import sys

from dotenv import load_dotenv
from platformdirs import user_cache_dir, user_config_dir


APP_NAME = "ft_891_hunter"
config_dir = user_config_dir(APP_NAME)
ENV_PATH = os.path.join(config_dir, ".env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    print(
        f"No .env file found at {ENV_PATH} -"
        " there is a sample env.template distributed with this package"
    )
    sys.exit(1)


UPDATE_PERIOD = int(os.getenv("SPOT_UPDATE_PERIOD", "30")) * 1000
API_TIMEOUT = 5
STATUS_TIMEOUT = 5_000
PREFERRED_BANDS = os.getenv("PREFERRED_BANDS", "").lower().split(',')
PREFERRED_MODES = os.getenv("PREFERRED_MODES", "").upper().split(',')
MY_LATITUDE = float(os.getenv("MY_LATITUDE", "0.0"))
MY_LONGITUDE = float(os.getenv("MY_LONGITUDE", "0.0"))

cache_dir = user_cache_dir(APP_NAME)
os.makedirs(cache_dir, exist_ok=True)
SHELVE_PATH = os.path.join(cache_dir, "sota.db")


serial_settings = {
    'port': os.getenv("RIG_SERIAL_PORT", "/dev/ttyUSB0"),
    'baudrate': int(os.getenv("RIG_BAUD_RATE", "38400")),
    'bytesize': 8,
    'parity': 'N',
    'stopbits': 1,
    'timeout': 3
}
