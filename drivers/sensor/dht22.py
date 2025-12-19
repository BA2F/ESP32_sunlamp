# === FILE: drivers/sensor/dht22.py ===
import dht
from machine import Pin

class DHT22:
    def __init__(self, pin):
        self.pin = Pin(pin)
        self.dev = dht.DHT22(self.pin)

    def read(self):
        """读取一次温湿度，异常时返回 (None, None)。"""
        try:
            self.dev.measure()
            t = self.dev.temperature()
            h = self.dev.humidity()
            return float(t), float(h)
        except Exception as e:
            # return None to indicate error; caller should handle
            print('DHT22 read error', e)
            return None, None
