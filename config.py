import os
from dotenv import load_dotenv


load_dotenv()


UPDATE_PERIOD = int(os.getenv("SPOT_UPDATE_PERIOD", 30)) * 1000
API_TIMEOUT = 5
STATUS_TIMEOUT = 5_000
PREFERRED_BANDS = os.getenv("PREFERRED_BANDS", "").lower().split(',')
PREFERRED_MODES = os.getenv("PREFERRED_MODES", "").lower().split(',')
MY_LATITUDE = float(os.getenv("MY_LATITUDE", 0.0))
MY_LONGITUDE = float(os.getenv("MY_LONGITUDE", 0.0))


serial_settings = {
    'port': os.getenv("RIG_SERIAL_PORT", "/dev/ttyUSB0"),
    'baudrate': int(os.getenv("RIG_BAUD_RATE", 38400)),
    'bytesize': 8,
    'parity': 'N',
    'stopbits': 1,
    'timeout': 3
}

