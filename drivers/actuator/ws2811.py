# === FILE: drivers/actuator/ws2811.py ===
import time
import neopixel
from machine import Pin

class WS2811:
    def __init__(self, pin, count, min_gap_ms=20):
        """简易 WS2812 封装，包含最小写入间隔保护。"""
        self.pin = Pin(pin, Pin.OUT)
        self.count = count
        self.np = neopixel.NeoPixel(self.pin, count)
        self.min_gap_ms = min_gap_ms
        self._last_write = time.ticks_ms() - min_gap_ms

    def write_pixels(self, pixels):
        # pixels: list of tuples length == count
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_write) < self.min_gap_ms:
            return False
        for i in range(min(self.count, len(pixels))):
            self.np[i] = pixels[i]
        try:
            self.np.write()
            self._last_write = time.ticks_ms()
            return True
        except Exception as e:
            print('ws2811 write error', e)
            return False

    def fill(self, color):
        pixels = [color] * self.count
        return self.write_pixels(pixels)









