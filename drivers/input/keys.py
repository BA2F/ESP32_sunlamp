# === FILE: drivers/input/keys.py ===
from machine import Pin
import time

class FiveWaySwitch:
    def __init__(self, mid_pin, up_pin, down_pin, left_pin, right_pin, set_pin=None):
        """初始化五向+SET开关，默认上拉，低电平为按下。"""
        self.order = ['mid', 'up', 'down', 'left', 'right']
        if set_pin is not None:
            self.order.append('set')
        self.pins = {
            'mid': Pin(mid_pin, Pin.IN, Pin.PULL_UP),
            'up': Pin(up_pin, Pin.IN, Pin.PULL_UP),
            'down': Pin(down_pin, Pin.IN, Pin.PULL_UP),
            'left': Pin(left_pin, Pin.IN, Pin.PULL_UP),
            'right': Pin(right_pin, Pin.IN, Pin.PULL_UP),
        }
        if set_pin is not None:
            self.pins['set'] = Pin(set_pin, Pin.IN, Pin.PULL_UP)
        self._press_start = {k: 0 for k in self.pins}
        self._release_time = {k: 0 for k in self.pins}

    def _raw(self, key):
        return 0 if self.pins[key].value() == 0 else 1

    def read(self):
        # returns first detected pressed key name or None
        for k in self.order:
            if self._raw(k) == 0:  # active low
                # record press start if not set
                if self._press_start[k] == 0:
                    self._press_start[k] = time.ticks_ms()
                return k
            else:
                # release
                if self._press_start[k] != 0 and self._release_time[k] == 0:
                    self._release_time[k] = time.ticks_ms()
                    # keep press_start for release_time calc; will be cleared by press_time/release_time
        return None

    def is_pressed(self, key):
        return self._raw(key) == 0

    def press_time(self, key):
        return self._press_start.get(key, 0)

    def release_time(self, key):
        rt = self._release_time.get(key, 0)
        # clear stored times to allow next press
        if rt:
            self._press_start[key] = 0
            self._release_time[key] = 0
        return rt

