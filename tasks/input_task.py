# === FILE: tasks/input_task.py ===
import uasyncio as asyncio
import time
from drivers.input.keys import FiveWaySwitch
from config import KEY_MID_PIN, KEY_UP_PIN, KEY_DOWN_PIN, KEY_LEFT_PIN, KEY_RIGHT_PIN, KEY_SET_PIN

DEBOUNCE_MS = 20
LONGPRESS_MS = 1500

async def input_handler_task(system_state, lock):
    """五向+SET按键处理：开关灯、亮度、色温、夜灯快捷键。"""
    keys = FiveWaySwitch(
        KEY_MID_PIN,
        KEY_UP_PIN,
        KEY_DOWN_PIN,
        KEY_LEFT_PIN,
        KEY_RIGHT_PIN,
        set_pin=KEY_SET_PIN
    )

    presets = [5000, 4000, 3000]  # color temperature presets (K)

    while True:
        try:
            k = keys.read()  # returns None or 'mid','up','down','left','right'
            if k:
                # debounce
                await asyncio.sleep_ms(DEBOUNCE_MS)
                if not keys.is_pressed(k):
                    await asyncio.sleep_ms(10)
                    continue

                # record press start
                start = keys.press_time(k)

                # wait for release
                while keys.is_pressed(k):
                    await asyncio.sleep_ms(50)

                duration = keys.release_time(k) - start

                # update global state
                await lock.acquire()
                try:
                    if k == 'mid':
                        # single press toggle lamp (long按不再切夜灯)
                        system_state['lamp']['is_on'] = not system_state['lamp']['is_on']

                    elif k == 'up':
                        system_state['lamp']['brightness'] = min(
                            100, system_state['lamp']['brightness'] + 5
                        )

                    elif k == 'down':
                        system_state['lamp']['brightness'] = max(
                            0, system_state['lamp']['brightness'] - 5
                        )

                    elif k == 'left':
                        cur = system_state['lamp'].get('color_temp_k', 4000)
                        try:
                            idx = presets.index(cur)
                        except Exception:
                            idx = 0
                        system_state['lamp']['color_temp_k'] = presets[(idx - 1) % len(presets)]
                        system_state['lamp']['color_mode'] = 'temp'

                    elif k == 'right':
                        cur = system_state['lamp'].get('color_temp_k', 4000)
                        try:
                            idx = presets.index(cur)
                        except Exception:
                            idx = 0
                        system_state['lamp']['color_temp_k'] = presets[(idx + 1) % len(presets)]
                        system_state['lamp']['color_mode'] = 'temp'

                    elif k == 'set':
                        # 专用夜灯键：琥珀色，低亮度
                        system_state['lamp']['is_on'] = True
                        system_state['lamp']['animation'] = None
                        system_state['lamp']['color_mode'] = 'temp'
                        system_state['lamp']['color_temp_k'] = 3200
                        system_state['lamp']['brightness'] = max(15, min(system_state['lamp']['brightness'], 30))

                finally:
                    try:
                        lock.release()
                    except:
                        pass

            await asyncio.sleep_ms(50)

        except Exception as e:
            print("input_task error:", e)
            await asyncio.sleep_ms(200)
