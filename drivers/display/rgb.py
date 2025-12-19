# drivers/display/rgb.py
# Simple one-pixel RGB indicator (GRB channel order, e.g. WS2812/NeoPixel)
import neopixel
from machine import Pin


class IndicatorRGB:
    def __init__(self, pin):
        self.pin = Pin(pin, Pin.OUT)
        self.np = neopixel.NeoPixel(self.pin, 1)

    def _to_grb(self, rgb):
        r, g, b = rgb
        return (g, r, b)

    def set_color(self, rgb):
        """设置单像素颜色，入参为 (r,g,b) 0-255。"""
        try:
            self.np[0] = self._to_grb(rgb)
            self.np.write()
        except Exception as e:
            print('IndicatorRGB set_color error', e)

    def off(self):
        self.set_color((0, 0, 0))
