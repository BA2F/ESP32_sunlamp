# === FILE: tasks/sensor_task.py ===
import uasyncio as asyncio
import time
from drivers.sensor.dht22 import DHT22
from drivers.sensor.sgp30 import SGP30
from drivers.sensor.light_sensor import LightSensor
from config import DHT22_PIN, SGP30_I2C_SDA, SGP30_I2C_SCL, LIGHT_SENSOR_PIN, SENSOR_READ_INTERVAL_S

async def sensor_reader_task(system_state, lock):
    """周期读取 DHT22/SGP30/光敏传感器，并写入共享状态。"""
    dht = DHT22(DHT22_PIN)
    sgp = SGP30(SGP30_I2C_SDA, SGP30_I2C_SCL)
    light = LightSensor(LIGHT_SENSOR_PIN)

    while True:
        try:
            t, h = dht.read()
            # humidity compensation for SGP30 using DHT22 temp/humidity
            if t is not None and h is not None:
                try:
                    sgp.set_humidity(t, h)
                except Exception as e:
                    print('SGP30 humidity compensation error', e)
            eco2, tvoc = sgp.read()
            lx = light.read()
            try:
                await lock.acquire()
                if t is not None:
                    system_state['sensor']['temperature'] = round(t, 1)
                if h is not None:
                    system_state['sensor']['humidity'] = round(h, 1)
                if eco2 is not None:
                    system_state['sensor']['eco2'] = int(eco2)
                if tvoc is not None:
                    system_state['sensor']['tvoc'] = int(tvoc)
                system_state['sensor']['light'] = int(lx)
            finally:
                try:
                    lock.release()
                except:
                    pass
        except Exception as e:
            print('sensor_task error', e)
        await asyncio.sleep(SENSOR_READ_INTERVAL_S)

