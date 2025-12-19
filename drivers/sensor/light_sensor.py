# === FILE: drivers/sensor/light_sensor.py ===
from machine import ADC, Pin

class LightSensor:
    def __init__(self, pin):
        adc_pin = Pin(pin)
        self.adc = ADC(adc_pin)
        try:
            self.adc.atten(ADC.ATTN_11DB)
        except Exception:
            pass

    def read(self):
        """读取 ADC 光照值，异常返回 0。"""
        try:
            return self.adc.read()
        except Exception as e:
            print('LightSensor read error', e)
            return 0
