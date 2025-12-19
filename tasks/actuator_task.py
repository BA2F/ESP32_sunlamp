# === FILE: tasks/actuator_task.py ===# === FILE: tasks/actuator_task.py ===
import uasyncio as asyncio
import time
from drivers.actuator.ws2811 import WS2811
from config import SUN_LAMP_PIN, SUN_LAMP_COUNT

NUM_PIXELS = SUN_LAMP_COUNT

def clamp(v, a, b):
    return max(a, min(v, b))

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def scale_color(rgb, factor):
    return tuple(int(clamp(c * factor, 0, 255)) for c in rgb)

def ease_in_out(t):
    return 3 * t * t - 2 * t * t * t

def wakeup_palette(p):
    # red -> orange -> yellow-white
    if p < 0.33:
        return lerp((255, 50, 20), (255, 120, 40), p / 0.33)
    elif p < 0.66:
        return lerp((255, 120, 40), (255, 190, 90), (p - 0.33) / 0.33)
    else:
        return lerp((255, 190, 90), (255, 240, 180), (p - 0.66) / 0.34)

def sunset_palette(p):
    # yellow -> amber -> deep red
    if p < 0.5:
        return lerp((255, 230, 160), (255, 160, 80), p / 0.5)
    else:
        return lerp((255, 160, 80), (60, 20, 5), (p - 0.5) / 0.5)

def breathe_palette(p):
    # loop through a soft cool gradient: cyan -> magenta -> blue -> cyan
    if p < 1/3:
        return lerp((80, 200, 255), (220, 120, 255), p * 3)
    elif p < 2/3:
        return lerp((220, 120, 255), (80, 120, 255), (p - 1/3) * 3)
    else:
        return lerp((80, 120, 255), (80, 200, 255), (p - 2/3) * 3)

def color_temp_to_rgb(k):
    # simple preset mapping near 5000/4000/3000/2200K
    if k >= 4800:
        return (255, 255, 240)
    if k >= 4200:
        return (255, 230, 210)
    if k >= 3300:
        return (255, 205, 170)
    return (255, 120, 40)  # cockpit-style deep amber for night

import math

async def actuator_controller_task(system_state, lock):
    """灯带控制：根据灯状态/动画计算 WS2812 像素输出。"""
    strip = WS2811(SUN_LAMP_PIN, NUM_PIXELS, min_gap_ms=system_state['meta'].get('neopixel_min_write_gap_ms', 20))
    while True:
        try:
            await lock.acquire()
            lamp = dict(system_state['lamp'])
            meta = dict(system_state['meta'])
            try:
                lock.release()
            except:
                pass

            pixels = [(0,0,0)] * NUM_PIXELS
            if lamp['is_on']:
                if lamp['animation'] == 'wakeup':
                    now = time.time()
                    start = lamp.get('animation_start_ts', now)
                    dur = max(1, lamp.get('animation_duration_s', 600))
                    progress = clamp((now - start) / dur, 0.0, 1.0)
                    e = ease_in_out(progress)
                    col = wakeup_palette(e)
                    b = clamp(lamp.get('brightness', 100) * e, 0, 100) / 100.0
                    col = scale_color(col, b)
                    pixels = [col] * NUM_PIXELS
                    if progress >= 1.0:
                        await lock.acquire()
                        system_state['lamp']['animation'] = None
                        system_state['lamp']['animation_progress'] = 1.0
                        try:
                            lock.release()
                        except:
                            pass
                elif lamp['animation'] == 'sunset':
                    now = time.time()
                    start = lamp.get('animation_start_ts', now)
                    dur = max(1, lamp.get('animation_duration_s', 900))
                    progress = clamp((now - start) / dur, 0.0, 1.0)
                    e = ease_in_out(progress)
                    col = sunset_palette(e)
                    start_b = clamp(lamp.get('brightness', 100), 0, 100)
                    b = clamp(start_b * (1.0 - e), 0, 100) / 100.0
                    col = scale_color(col, b)
                    pixels = [col] * NUM_PIXELS
                    if progress >= 1.0:
                        await lock.acquire()
                        system_state['lamp']['animation'] = None
                        system_state['lamp']['animation_progress'] = 1.0
                        system_state['lamp']['is_on'] = False
                        try:
                            lock.release()
                        except:
                            pass
                elif lamp['animation'] == 'breathe':
                    period = lamp.get('animation_duration_s', 3)
                    phase = (time.time() % period) / period
                    wave = ease_in_out(0.5 + 0.5 * math.sin(2 * math.pi * phase))
                    base = breathe_palette(phase)
                    b = clamp(lamp.get('brightness', 60) * (0.3 + 0.7 * wave), 0, 100) / 100.0
                    col = scale_color(base, b)
                    pixels = [col] * NUM_PIXELS
                elif lamp['animation'] == 'warning':
                    period_ms = 500
                    elapsed = int((time.time() - lamp.get('animation_start_ts', time.time())) * 1000)
                    on = (elapsed // period_ms) % 2 == 0
                    if on:
                        pixels = [(255,0,0)] * NUM_PIXELS
                    else:
                        pixels = [(0,0,0)] * NUM_PIXELS
                else:
                    b = lamp['brightness'] / 100.0
                    if lamp.get('color_mode') == 'custom':
                        base = tuple(lamp.get('custom_rgb') or (255, 200, 120))
                    else:  # 'temp' or fallback
                        base = color_temp_to_rgb(lamp.get('color_temp_k', 4000))
                    col = scale_color(base, b)
                    pixels = [col] * NUM_PIXELS

            strip.write_pixels(pixels)

        except Exception as e:
            print('actuator_task error', e)
        await asyncio.sleep_ms(system_state['meta'].get('frame_interval_ms', 100))
