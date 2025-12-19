# === FILE: tasks/display_task.py ===
import uasyncio as asyncio
from drivers.display.ssd1306 import SSD1306Display

DISPLAY_INTERVAL_MS = 500

async def display_task(system_state, lock):
    """OLED 刷新任务：定期渲染传感器与网络/灯状态。"""
    oled = SSD1306Display()
    while True:
        try:
            await lock.acquire()
            s = system_state.copy()
            try:
                lock.release()
            except:
                pass

            oled.clear()
            oled.text('T:{:.1f}C H:{:.1f}%'.format(s['sensor']['temperature'], s['sensor']['humidity']), 0, 0)
            oled.text('eCO2:{} TVOC:{}'.format(s['sensor']['eco2'], s['sensor']['tvoc']), 0, 12)
            oled.text('LUX:{}'.format(s['sensor']['light']), 0, 24)
            oled.text('W:{} M:{}'.format(s['network']['wifi_status'][0], s['network']['mqtt_status'][0]), 0, 36)
            oled.text('ON:{},B:{}'.format(s['lamp']['is_on'], s['lamp']['brightness']), 0, 48)
            oled.show()
        except Exception as e:
            print('display_task error', e)
        await asyncio.sleep_ms(DISPLAY_INTERVAL_MS)
