# === FILE: drivers/communication/wifi/wifi_manager.py ===
import network
import socket
import ure
import ujson
import time
import uasyncio as asyncio
from machine import Pin

WIFI_CONFIG_FILE = 'wifi.dat'

class WifiManager:
    def __init__(self):
        # keep separate interfaces; re-created when needed
        self.wlan = network.WLAN(network.STA_IF)
        self.ap = network.WLAN(network.AP_IF)

    # ---------------- STA helpers -----------------
    async def connect_saved(self, timeout=30):
        """读取 wifi.dat 连接 STA，超时返回 False。"""
        # try to load wifi.dat
        try:
            with open(WIFI_CONFIG_FILE, 'r') as f:
                j = ujson.loads(f.read())
                ssid = j.get('ssid')
                pwd = j.get('password')
        except Exception:
            ssid = None
            pwd = None
        if not ssid:
            return False
        try:
            self.wlan.active(False)
        except Exception:
            pass
        # fresh interface helps avoid "Wifi Internal Error"
        try:
            self.wlan = network.WLAN(network.STA_IF)
            self.wlan.active(True)
            self.wlan.connect(ssid, pwd)
        except Exception as e:
            print('STA start/connect error', e)
            return False
        t0 = time.time()
        while not self.wlan.isconnected():
            await asyncio.sleep_ms(500)
            if time.time() - t0 > timeout:
                return False
        return True

    def is_connected(self):
        return self.wlan.isconnected()

    # ---------------- AP + 配网 -----------------
    async def start_ap_and_captive(self, ssid, password):
        """启动 AP 并关闭 STA，避免接口状态冲突。"""
        # start AP; re-create interface to avoid stale state
        try:
            self.ap.active(False)
        except Exception:
            pass
        try:
            # disable STA to avoid simultaneous state issues on some boards
            self.wlan.active(False)
        except Exception:
            pass
        try:
            self.ap = network.WLAN(network.AP_IF)
            self.ap.active(True)
            # WPA2-PSK auth (MicroPython 1.26默认)；channel 默认 1
            self.ap.config(essid=ssid, password=password)
            print('AP started', ssid)
            return True
        except Exception as e:
            print('start_ap_and_captive failed', e)
            return False

    def _parse_form(self, body):
        # parse application/x-www-form-urlencoded payload
        params = {}
        for pair in body.split('&'):
            if '=' in pair:
                k, v = pair.split('=', 1)
                params[self._urldecode(k)] = self._urldecode(v)
        return params

    def _urldecode(self, s):
        res = ''
        i = 0
        while i < len(s):
            c = s[i]
            if c == '+':
                res += ' '
            elif c == '%' and i + 2 < len(s):
                try:
                    res += chr(int(s[i+1:i+3], 16))
                    i += 2
                except Exception:
                    res += c
            else:
                res += c
            i += 1
        return res

    def save_config(self, conf):
        """将 Wi-Fi 配置写入 wifi.dat。"""
        try:
            with open(WIFI_CONFIG_FILE, 'w') as f:
                f.write(ujson.dumps(conf))
            return True
        except Exception as e:
            print('save wifi config error', e)
            return False

    async def stop_ap(self):
        ap = network.WLAN(network.AP_IF)
        ap.active(False)
        await asyncio.sleep_ms(100)

    async def captive_portal(self, timeout_s=300):
        """
        在 AP 模式下开启一个极简 HTTP 服务器，POST /save 保存 ssid/password。
        成功返回保存的配置 dict，失败或超时返回 None。
        """
        saved_conf = None

        async def handle(reader, writer):
            nonlocal saved_conf
            try:
                line = await reader.readline()
                if not line:
                    await writer.wait_closed()
                    return
                try:
                    parts = line.decode().split()
                    method, path = parts[0], parts[1]
                except Exception:
                    method, path = 'GET', '/'

                headers = {}
                while True:
                    h = await reader.readline()
                    if not h or h == b'\r\n':
                        break
                    try:
                        k, v = h.decode().split(':', 1)
                        headers[k.strip().lower()] = v.strip()
                    except Exception:
                        pass

                body = b''
                if 'content-length' in headers:
                    try:
                        length = int(headers['content-length'])
                        if length > 0:
                            body = await reader.readexactly(length)
                    except Exception:
                        pass

                if method == 'POST' and path.startswith('/save'):
                    try:
                        params = self._parse_form(body.decode())
                    except Exception:
                        params = {}
                    ssid = params.get('ssid', '').strip()
                    pwd = params.get('password', '').strip()
                    if ssid:
                        conf = {'ssid': ssid, 'password': pwd}
                        if self.save_config(conf):
                            saved_conf = conf
                            resp = 'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\nSaved, device will reconnect.'
                        else:
                            resp = 'HTTP/1.0 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nSave failed.'
                    else:
                        resp = 'HTTP/1.0 400 Bad Request\r\nContent-Type: text/plain\r\n\r\nSSID required.'
                    await writer.awrite(resp)
                else:
                    html = """<html><body><h3>ESP32 WiFi Setup</h3>
                    <form method='POST' action='/save'>
                    SSID: <input name='ssid'/><br/>
                    Password: <input name='password' type='password'/><br/>
                    <input type='submit' value='Save & Reboot'/>
                    </form></body></html>"""
                    resp = 'HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n' + html
                    await writer.awrite(resp)
            except Exception as e:
                print('captive handler error', e)
            try:
                await writer.wait_closed()
            except Exception:
                pass

        try:
            srv = await asyncio.start_server(handle, '0.0.0.0', 80)
            print('Captive portal running on 0.0.0.0:80')
        except Exception as e:
            print('start_server failed', e)
            return None

        start = time.time()
        try:
            while saved_conf is None:
                if timeout_s and (time.time() - start) > timeout_s:
                    break
                await asyncio.sleep_ms(200)
        finally:
            try:
                srv.close()
                await srv.wait_closed()
            except Exception:
                pass

        return saved_conf
