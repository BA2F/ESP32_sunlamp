# === FILE: main.py ===

"""
Main entry for ESP32-S3 MicroPython Sun Lamp
Place this file at the project root as main.py
Requires: config.py and drivers/ and tasks/ as per project structure
"""
import uasyncio as asyncio
import sys
import gc
from tasks.wifi_task import wifi_manager_task
from tasks.mqtt_task import mqtt_client_task
from tasks.sensor_task import sensor_reader_task
from tasks.display_task import display_task
from tasks.input_task import input_handler_task
from tasks.actuator_task import actuator_controller_task
from config import *

# shared state (single source of truth)
system_state = {
    "sensor": {
        "temperature": 0.0,
        "humidity": 0.0,
        "eco2": 0,
        "tvoc": 0,
        "light": 0
    },
    "lamp": {
        "is_on": False,
        "brightness": 50,
        "color_mode": "temp",  # 'temp' (color_temp_k) or 'custom'
        "color_temp_k": 4000,
        "custom_rgb": (255, 220, 200),
        "animation": None,
        "animation_start_ts": 0,
        "animation_duration_s": 0,
        "animation_progress": 0.0
    },
    "network": {
        "wifi_status": "offline",
        "mqtt_status": "offline",
        "last_mqtt_pub_ts": 0
    },
    "meta": {
        "frame_interval_ms": 100,
        "neopixel_min_write_gap_ms": 20
    }
}

# simple lock compatibility for older uasyncio
try:
    Lock = asyncio.Lock
except AttributeError:
    class Lock:
        def __init__(self):
            self._locked = False
        async def acquire(self):
            while self._locked:
                await asyncio.sleep_ms(20)
            self._locked = True
        def release(self):
            self._locked = False

state_lock = Lock()

async def monitor_tasks(tasks):
    """监控所有子任务，若异常退出则尝试重启一次。

    Args:
        tasks: 任务名到 asyncio.Task 的映射，生命周期内会被更新。
    """
    # monitor, restart if any task dies
    while True:
        for tname, task in list(tasks.items()):
            if task.done():
                try:
                    exc = task.exception()
                except Exception:
                    exc = None
                print('Task', tname, 'finished unexpectedly,', exc)
                # attempt restart once
                if tname == 'wifi':
                    tasks[tname] = asyncio.create_task(wifi_manager_task(system_state, state_lock))
                elif tname == 'mqtt':
                    tasks[tname] = asyncio.create_task(mqtt_client_task(system_state, state_lock))
                elif tname == 'sensor':
                    tasks[tname] = asyncio.create_task(sensor_reader_task(system_state, state_lock))
                elif tname == 'display':
                    tasks[tname] = asyncio.create_task(display_task(system_state, state_lock))
                elif tname == 'input':
                    tasks[tname] = asyncio.create_task(input_handler_task(system_state, state_lock))
                elif tname == 'actuator':
                    tasks[tname] = asyncio.create_task(actuator_controller_task(system_state, state_lock))
        await asyncio.sleep(5)

async def main():
    """系统入口：创建全局任务并启动调度。"""
    print('Starting main...')
    gc.collect()

    # start tasks
    tasks = {}
    tasks['wifi'] = asyncio.create_task(wifi_manager_task(system_state, state_lock))
    # mqtt depends on wifi but task can run and wait for network
    tasks['mqtt'] = asyncio.create_task(mqtt_client_task(system_state, state_lock))
    tasks['sensor'] = asyncio.create_task(sensor_reader_task(system_state, state_lock))
    tasks['display'] = asyncio.create_task(display_task(system_state, state_lock))
    tasks['input'] = asyncio.create_task(input_handler_task(system_state, state_lock))
    tasks['actuator'] = asyncio.create_task(actuator_controller_task(system_state, state_lock))

    tasks['monitor'] = asyncio.create_task(monitor_tasks(tasks))

    await asyncio.gather(*tasks.values())

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print('Fatal in main', e)
        sys.print_exception(e)
        # optionally reset
        try:
            import machine
            machine.reset()
        except Exception:
            pass


