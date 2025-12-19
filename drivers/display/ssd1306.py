# === FILE: drivers/display/ssd1306.py ===
from machine import I2C, Pin
import ssd1306

class SSD1306Display:
    def __init__(self, width=128, height=64, scl_pin=None, sda_pin=None):
        """封装 SSD1306 初始化，默认使用配置文件中的 I2C 引脚。"""
        if scl_pin is None:
            from config import OLED_SCL_PIN
            scl_pin = OLED_SCL_PIN
        if sda_pin is None:
            from config import OLED_SDA_PIN
            sda_pin = OLED_SDA_PIN
        self.i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin))
        self.oled = ssd1306.SSD1306_I2C(width, height, self.i2c)

    def fill(self, col):
        self.oled.fill(col)

    def text(self, t, x, y):
        self.oled.text(t, x, y)

    def show(self):
        self.oled.show()

    def clear(self):
        self.oled.fill(0)
        self.oled.show()
