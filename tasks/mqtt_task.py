# === FILE: tasks/mqtt_task.py ===
import ujson
import uasyncio as asyncio
import time
from umqtt.simple import MQTTClient
from config import MQTT_SERVER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, MQTT_TOPIC_PUB, MQTT_TOPIC_SUB

PUBLISH_INTERVAL_S = 5

async def mqtt_client_task(system_state, lock):
    """MQTT 客户端主循环：建立连接、发布状态、消费指令。"""
    client = None
    last_pub = 0
    while True:
        try:
            if system_state['network']['wifi_status'] != 'connected':
                system_state['network']['mqtt_status'] = 'offline'
                await asyncio.sleep(1)
                continue
            if client is None:
                system_state['network']['mqtt_status'] = 'connecting'
                try:
                    client = MQTTClient('esp32_sunlamp', MQTT_SERVER, port=MQTT_PORT, user=MQTT_USER, password=MQTT_PASSWORD)
                    client.set_callback(lambda t, m: asyncio.create_task(on_mqtt_msg(t, m, system_state, lock)))
                    client.connect()
                    client.subscribe(MQTT_TOPIC_SUB)
                    system_state['network']['mqtt_status'] = 'connected'
                except Exception as e:
                    print('MQTT connect failed', e)
                    system_state['network']['mqtt_status'] = 'offline'
                    client = None
                    await asyncio.sleep(5)
                    continue

            now = time.time()
            if now - last_pub >= PUBLISH_INTERVAL_S:
                try:
                    await lock.acquire()
                    payload = {
                        'device_id': 'esp32_sunlamp',
                        'ts': int(now),
                        'sensor': dict(system_state['sensor']),
                        'network': {
                            'wifi': system_state['network']['wifi_status'],
                            'mqtt': system_state['network']['mqtt_status']
                        },
                        'lamp': dict(system_state.get('lamp', {})),
                    }
                    client.publish(MQTT_TOPIC_PUB, ujson.dumps(payload))
                    system_state['network']['last_mqtt_pub_ts'] = int(now)
                    last_pub = now
                finally:
                    try:
                        lock.release()
                    except:
                        pass

            try:
                client.check_msg()
            except Exception as e:
                print('MQTT check_msg error', e)
                system_state['network']['mqtt_status'] = 'offline'
                try:
                    client.disconnect()
                except:
                    pass
                client = None
                await asyncio.sleep(1)
                continue

            await asyncio.sleep_ms(100)
        except Exception as e:
            print('mqtt_client_task top error', e)
            await asyncio.sleep(2)

async def on_mqtt_msg(topic, msg, system_state, lock):
    """处理 MQTT 下行：set（开关/亮度/色彩）与 anim（动画）。"""
    try:
        s = msg.decode() if isinstance(msg, bytes) else str(msg)
        j = ujson.loads(s)
    except Exception as e:
        print('Invalid mqtt payload', e)
        return
    try:
        await lock.acquire()
        if j.get('cmd') == 'set':
            if 'is_on' in j:
                system_state['lamp']['is_on'] = bool(j['is_on'])
            if 'brightness' in j:
                bv = int(j['brightness'])
                system_state['lamp']['brightness'] = max(0, min(100, bv))
            if 'color_mode' in j:
                cm = j['color_mode']
                if cm in ('temp', 'custom'):
                    system_state['lamp']['color_mode'] = cm
            if 'color_temp_k' in j:
                try:
                    system_state['lamp']['color_temp_k'] = int(j['color_temp_k'])
                    system_state['lamp']['color_mode'] = 'temp'
                except Exception:
                    pass
            # custom RGB from list or hex
            if 'rgb' in j and isinstance(j['rgb'], (list, tuple)) and len(j['rgb']) == 3:
                try:
                    r, g, b = [max(0, min(255, int(x))) for x in j['rgb']]
                    system_state['lamp']['custom_rgb'] = (r, g, b)
                    system_state['lamp']['color_mode'] = 'custom'
                except Exception:
                    pass
            elif 'color_hex' in j and isinstance(j['color_hex'], str) and len(j['color_hex']) in (6,7):
                hx = j['color_hex'][1:] if j['color_hex'].startswith('#') else j['color_hex']
                try:
                    r = int(hx[0:2], 16); g = int(hx[2:4], 16); b = int(hx[4:6], 16)
                    system_state['lamp']['custom_rgb'] = (r, g, b)
                    system_state['lamp']['color_mode'] = 'custom'
                except Exception:
                    pass
            system_state['lamp']['animation'] = None
        elif j.get('cmd') == 'anim':
            typ = j.get('type')
            if typ == 'wakeup':
                duration = int(j.get('duration_s', 600))
                system_state['lamp']['animation'] = 'wakeup'
                system_state['lamp']['animation_start_ts'] = time.time()
                system_state['lamp']['animation_duration_s'] = duration
                system_state['lamp']['animation_progress'] = 0.0
                system_state['lamp']['is_on'] = True
            elif typ == 'warning':
                system_state['lamp']['animation'] = 'warning'
                system_state['lamp']['animation_start_ts'] = time.time()
                system_state['lamp']['animation_duration_s'] = 0
                system_state['lamp']['is_on'] = True
            elif typ == 'sunset':
                duration = int(j.get('duration_s', 900))
                system_state['lamp']['animation'] = 'sunset'
                system_state['lamp']['animation_start_ts'] = time.time()
                system_state['lamp']['animation_duration_s'] = duration
                system_state['lamp']['animation_progress'] = 0.0
                system_state['lamp']['is_on'] = True
            elif typ == 'breathe':
                duration = int(j.get('duration_s', 3))
                system_state['lamp']['animation'] = 'breathe'
                system_state['lamp']['animation_start_ts'] = time.time()
                system_state['lamp']['animation_duration_s'] = duration  # used as period
                system_state['lamp']['animation_progress'] = 0.0
                system_state['lamp']['is_on'] = True
    finally:
        try:
            lock.release()
        except:
            pass
    
