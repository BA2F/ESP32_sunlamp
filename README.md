# ESP32 Sunlamp (MicroPython + EMQX + Node-RED + InfluxDB)

本项目包含 ESP32-S3 微控端、MQTT 中转（EMQX）、Node-RED 编排、InfluxDB 持久化，以及 uibuilder 前端（简单版）。目标是快速搭建「环境监测 + 太阳灯控制」的端到端链路。

目录：
- 架构与数据流
- 设备端说明（MicroPython）
- SGP30 湿度补偿原理
- MQTT 主题与载荷
- Node-RED 流程说明
- 前端控件与协议映射
- 后端部署（Docker Compose）
- InfluxDB / Grafana 配置
- 常见问题

------------------------------------
架构与数据流
------------------------------------
- 设备端（ESP32-S3 / MicroPython）：采集 DHT22 / SGP30 / 光敏数据，上报 MQTT；执行灯控与动画；本地按键/OLED 状态。
- 中转：EMQX（21883，账号 esp32/esp32）转发所有 MQTT 消息。
- 编排：Node-RED（flows2.json）。mqtt in 订阅状态 → Function 处理 → InfluxDB 写入；uibuilder 前端接收状态、下发表单 → switch → set/anim Function → mqtt out 下发。
- 存储/大屏：InfluxDB 存传感数据，Grafana 读取 InfluxDB 画大屏。
- 部署：阿里云 Ubuntu 22.04（2C2G），Docker Compose 启动 EMQX/Node-RED/InfluxDB（可选 Grafana）。

------------------------------------
设备端（MicroPython）任务
------------------------------------
- main.py：初始化全局状态 system_state，启动各异步任务（wifi/mqtt/sensor/display/input/actuator/monitor）。
- wifi_task：优先读取 wifi.dat 连接 STA，失败则启用 AP（默认 SSID ESP32_Configurator / 密码 12345678），简单 HTTP 表单保存后重连；状态写入 system_state['network']。
- mqtt_task：连接 EMQX（21883，esp32/esp32）；每 5s 发布 status（sensor/network/lamp）；订阅 cmd，处理 set/anim。
- sensor_task：读 DHT22/SGP30/光敏；将 DHT22 温湿度用于 SGP30 湿度补偿；结果写入 system_state['sensor']。
- input_task：五向+SET 按键（开关、亮度、色温三档 5000/4000/3000K、夜灯 2200K 低亮度）。
- actuator_task：WS2812 控制，支持动画：
  - wakeup：红→橙→黄-白渐亮（日出）。
  - sunset：黄→琥珀→暗红渐灭，结束关灯（日落）。
  - breathe：平滑变色呼吸（青→品→蓝→青）。
  - warning：红色闪烁。
- display_task：OLED 显示传感与网络/灯状态。
- monitor_tasks：子任务异常退出时尝试重启。

------------------------------------
SGP30 湿度补偿原理（用 DHT22 校准）
------------------------------------
- 地址/命令：I2C 地址 0x58；初始化 0x2003；测量 0x2008；湿度补偿 0x2061（参数为绝对湿度 g/m³ × 256 的 16 位值）。
- 绝对湿度计算（Magnus 公式）：
  - sat(hPa) = 6.112 * exp((17.62 * T)/(243.12+T))
  - vap = RH% * sat / 100
  - AH(g/m³) = 216.7 * vap / (273.15 + T)
  - ticks = int(AH * 256)，写入 0x2061。
- 流程：sensor_task 中读取 DHT22 → sgp.set_humidity(T,H) → sgp.read() 获取 eCO2/TVOC。

------------------------------------
MQTT 主题与载荷
------------------------------------
- 上行（设备→EMQX→Node-RED）：`esp32/sunlamp/status`
  ```json
  {
    "device_id": "esp32_sunlamp",
    "ts": 1700000000,
    "sensor": {"temperature":23.9,"humidity":71.1,"eco2":1216,"tvoc":222,"light":3433},
    "network": {"wifi":"connected","mqtt":"connected"},
    "lamp": {
      "is_on": true,
      "brightness": 60,
      "color_mode": "temp",
      "color_temp_k": 4000,
      "custom_rgb": [255,120,40],
      "animation": null
    }
  }
  ```
- 下行（Node-RED/前端→设备）：`esp32/sunlamp/cmd`
  - set 示例：
    - `{"cmd":"set","is_on":true}`
    - `{"cmd":"set","brightness":70}`
    - `{"cmd":"set","color_temp_k":4000}`（色温模式）
    - `{"cmd":"set","rgb":[255,120,40]}` 或 `{"cmd":"set","color_hex":"#ff7828"}`（自定义色）
  - anim 示例：
    - `{"cmd":"anim","type":"wakeup","duration_s":600}`
    - `{"cmd":"anim","type":"sunset","duration_s":900}`
    - `{"cmd":"anim","type":"breathe","duration_s":3}`
    - `{"cmd":"anim","type":"warning"}`

------------------------------------
Node-RED 流程（flows2.json 示意图）
------------------------------------
- mqtt in (`esp32/sunlamp/status`)：订阅设备上报。
- debug1：查看原始消息。
- Flattening JSON：提取/扁平化传感字段（temp/humid/eco2/tvoc/light）供 Influx 写入。
- influxdb out：写入 measurement=sensor_readings（bucket 例：sensor_data）。
- function1：缓存最新 state（flow/global），输出 `{topic:'state', payload: state}` 给 uibuilder，便于前端初始/实时同步。
- uibuilder：承载前端页面，收/发消息。
- switch：按 msg.topic 分发 set/anim。
- set Function：校验/裁剪后构造 `{"cmd":"set",...}` 字符串。
- anim Function：构造 `{"cmd":"anim",...}` 字符串。
- mqtt out (`esp32/sunlamp/cmd`)：下发到设备。

------------------------------------
前端与 Node-RED（uibuilder）交互
------------------------------------
- 技术：IIFE 版 uibuilder，前端 JS 中 `const ui = window.uibuilder`。
- 接收：`ui.onChange('msg', msg => { if (msg.topic==='state') renderState(msg.payload) })`，显示 Wi-Fi/MQTT/传感/灯状态，更新控件。
- 发送：
  - set：开关、亮度、色温按钮、夜灯、RGB 取色 → `ui.send({topic:'set', payload:{...}})`.
  - anim：下拉/快捷按钮 → `ui.send({topic:'anim', payload:{type, duration_s}})`.
  - 刷新：`ui.send({topic:'get_state'})`（function1 返回缓存 state）。
- 阈值（本地）：前端保存到 localStorage，超限时发 warning 动画，恢复后发空 set 清除动画。
- 亮度保护：滑条调整时前端锁定，防止被上报状态弹回，松手后自动同步。

------------------------------------
后端部署（Docker Compose 概览）
------------------------------------
- 服务：EMQX（21883）、Node-RED（1880）、InfluxDB（8086），可选 Grafana（3000）。
- EMQX：创建用户 esp32/esp32；开放 21883。
- Node-RED：导入 flows2.json；MQTT 节点填 EMQX 地址/账号；Influx 节点填 org/bucket/token；uibuilder 指向前端文件。
- InfluxDB：初始化 org/bucket/token，给 Node-RED influx 节点配置；measurement 为 sensor_readings。
- Grafana：添加 InfluxDB 数据源（Flux），用 Flux 查询绘制曲线/大屏。
- 启动：`docker-compose up -d` → 验证端口 → 打开 Node-RED 部署 → 前端访问 `/sunlamp/` → 设备连接。

------------------------------------
InfluxDB / Grafana 示例
------------------------------------
- Flux 查询（近 24h 温湿度等，按 5m 聚合）：
  ```flux
  from(bucket:"sensor_data")
    |> range(start: -24h)
    |> filter(fn:(r)=> r._measurement=="sensor_readings")
    |> filter(fn:(r)=> r._field=="temp" or r._field=="humid" or r._field=="eco2" or r._field=="tvoc" or r._field=="light")
    |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
    |> yield(name:"mean")
  ```
- Grafana：添加数据源（InfluxDB/Flux），面板选时间序列，字段映射 temp/humid/eco2/tvoc/light。

------------------------------------
常见问题
------------------------------------
- 前端无状态：检查 mqtt in 是否连接、function1 是否输出 topic=state、uibuilder 控制台是否报错。
- 指令无效：检查 mqtt out topic=esp32/sunlamp/cmd、账号密码；设备串口是否提示 MQTT offline。
- 湿度补偿无效：确认 DHT22 正常，sgp.set_humidity 被调用；I2C 连线/地址正确（0x58）。
- Influx 无数据：节点 org/bucket/token 是否正确；measurement/字段名与查询一致。

------------------------------------
快速上手步骤
------------------------------------
1) 后端：docker-compose up -d（EMQX/Node-RED/InfluxDB/Grafana）。  
2) EMQX 创建用户 esp32/esp32。  
3) Node-RED 导入 flows2.json，配置 MQTT/Influx，部署。  
4) 前端：通过 uibuilder 路径访问（如 http://服务器:1880/sunlamp/）。  
5) 设备：config.py 填 MQTT_SERVER 指向服务器，用户 esp32/esp32，端口 21883；上传代码并上电。  
6) 验证：Node-RED debug1 看到 status，前端能控灯，Influx 有数据，Grafana 可读。
