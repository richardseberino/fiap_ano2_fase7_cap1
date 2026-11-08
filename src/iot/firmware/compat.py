# Camada de compatibilidade MicroPython <-> CPython (tempo e JSON).
import sys

MICROPYTHON = sys.implementation.name == "micropython"

if MICROPYTHON:
    import time
    import ujson as json  # noqa: F401

    ticks_ms = time.ticks_ms
    ticks_diff = time.ticks_diff
    sleep_ms = time.sleep_ms
else:
    import json  # noqa: F401
    import time

    def ticks_ms():
        return int(time.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b

    def sleep_ms(ms):
        time.sleep(ms / 1000)


def plataforma():
    """'esp32' (ESP32, S2, S3, C3), 'rp2' (Raspberry Pi Pico / Pico W) ou 'linux'."""
    if MICROPYTHON:
        return sys.platform
    return "linux"
