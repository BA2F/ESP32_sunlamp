# === FILE: tasks/wifi_task.py ===
import uasyncio as asyncio
import time
from drivers.communication.wifi.wifi_manager import WifiManager
from drivers.display.rgb import IndicatorRGB
from config import AP_SSID, AP_PASSWORD, RGB_PIN

AP_TIMEOUT_S = 30

async def wifi_manager_task(system_state, lock):
    """管理 Wi-Fi：优先读取保存配置，失败则开启 AP 配网。

    流程：
      1) 置状态为 connecting，尝试加载 wifi.dat 并连接 STA。
      2) 成功则维持心跳，掉线后重试。
      3) 失败则进入 AP 模式 + Captive Portal，等待用户提交 ssid/password，
         保存后重启连接。
    Args:
        system_state: 全局状态字典，更新网络状态。
        lock: 协程锁，保护共享状态。
    """
    wm = WifiManager()
    try:
        led = IndicatorRGB(RGB_PIN)
    except Exception as e:
        print('IndicatorRGB init failed', e)
        led = None

    def show(state):
        if not led:
            return
        colors = {
            'connecting': (0, 0, 64),#蓝
            'connected': (0, 64, 0),#绿
            'ap_mode': (64, 40, 0),#橙黄
            'offline': (64, 0, 0),#红
            'error': (100, 0, 0),#深红
        }
        led.set_color(colors.get(state, (0, 0, 0)))

    while True:
        try:
            system_state['network']['wifi_status'] = 'connecting'
            show('connecting')
            ok = await wm.connect_saved(timeout=AP_TIMEOUT_S)
            if ok:
                system_state['network']['wifi_status'] = 'connected'
                show('connected')
                # monitor
                while wm.is_connected():
                    await asyncio.sleep(1)
                system_state['network']['wifi_status'] = 'offline'
                show('offline')
                await asyncio.sleep(1)
                continue
            else:
                system_state['network']['wifi_status'] = 'ap_mode'
                show('ap_mode')
                ap_ok = await wm.start_ap_and_captive(AP_SSID, AP_PASSWORD)
                if not ap_ok:
                    print('AP start failed, retrying...')
                    show('error')
                    await asyncio.sleep(3)
                    continue
                # captive portal to accept POST /save with ssid/password
                conf = await wm.captive_portal(timeout_s=300)
                if conf:
                    print('WiFi config saved via captive portal:', conf.get('ssid'))
                    system_state['network']['wifi_status'] = 'connecting'
                    show('connecting')
                    await wm.stop_ap()
                    # retry connect immediately with new config
                    continue
                else:
                    print('Captive portal timeout, retrying AP...')
                    await wm.stop_ap()
                    system_state['network']['wifi_status'] = 'offline'
                    show('offline')
                    await asyncio.sleep(5)
        except Exception as e:
            print('wifi_manager_task error', e)
            show('error')
            await asyncio.sleep(5)
