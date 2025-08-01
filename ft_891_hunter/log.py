"""Application wide logger settings"""

from collections import deque

from loguru import logger


log_buffer = deque(maxlen=1000)


def buffer_sink(message):
    log_buffer.append(message.strip())


logger.remove()
logger.add(buffer_sink, format="{time:HH:mm:ss} | {level} | {message}", level="DEBUG")


__all__ = ["logger", "log_buffer"]
