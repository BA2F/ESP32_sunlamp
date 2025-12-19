# === FILE: drivers/sensor/sgp30.py ===
from machine import I2C
from machine import Pin
import time
import math

SGP30_ADDR = 0x58

class SGP30:
    def __init__(self, sda, scl, id=0):
        # create I2C instance id 0
        self.i2c = I2C(id, scl=Pin(scl), sda=Pin(sda))
        time.sleep_ms(10)
        try:
            # init air quality
            self.i2c.writeto(SGP30_ADDR, b"\x20\x03")
            time.sleep_ms(10)
            # start measurement
            self.i2c.writeto(SGP30_ADDR, b"\x20\x08")
            time.sleep_ms(10)
        except Exception as e:
            print('SGP30 init error', e)

    def read(self):
        try:
            # request measurement
            self.i2c.writeto(SGP30_ADDR, b"\x20\x08")
            time.sleep_ms(12)
            data = self.i2c.readfrom(SGP30_ADDR, 6)
            eco2 = (data[0] << 8) | data[1]
            tvoc = (data[3] << 8) | data[4]
            return int(eco2), int(tvoc)
        except Exception as e:
            print('SGP30 read error', e)
            return None, None

    def _abs_humidity_gm3(self, t_c, rh):
        """Compute absolute humidity (g/m^3) using Magnus formula."""
        if t_c is None or rh is None:
            return None
        try:
            sat = 6.112 * math.exp((17.62 * t_c) / (243.12 + t_c))  # hPa
            vap = (rh / 100.0) * sat
            return 216.7 * vap / (273.15 + t_c)  # g/m^3
        except Exception as e:
            print('SGP30 abs humidity error', e)
            return None

    def set_humidity(self, t_c, rh):
        """
        Set humidity compensation using temperature (°C) and relative humidity (%) from DHT22.
        Converts absolute humidity to "ticks" (g/m^3 * 256) per SGP30 datasheet.
        """
        ah = self._abs_humidity_gm3(t_c, rh)
        if ah is None:
            return False
        ticks = int(ah * 256)
        if ticks < 0:
            ticks = 0
        if ticks > 0xFFFF:
            ticks = 0xFFFF
        try:
            buf = bytes([0x20, 0x61, (ticks >> 8) & 0xFF, ticks & 0xFF])
            self.i2c.writeto(SGP30_ADDR, buf)
            return True
        except Exception as e:
            print('SGP30 set_humidity error', e)
            return False


