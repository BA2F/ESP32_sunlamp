# config.py

# WifiManager 强制门户配置
AP_SSID = "ESP32_Configurator"
AP_PASSWORD = "12345678" # 至少8位

# MQTT 配置
MQTT_SERVER = '8.138.213.43'
MQTT_PORT = 21883
MQTT_USER = b"esp32"
MQTT_PASSWORD = b"esp32"
MQTT_TOPIC_PUB = 'esp32/sunlamp/status'
MQTT_TOPIC_SUB = 'esp32/sunlamp/cmd'

# 传感器引脚配置 (请根据您的实际接线修改！)
DHT22_PIN = 15          # DHT22 数据引脚
SGP30_I2C_SDA = 8       # SGP30 SDA 引脚
SGP30_I2C_SCL = 9       # SGP30 SCL 引脚
LIGHT_SENSOR_PIN = 7    # 光敏电阻 ADC 引脚

# 传感器读取间隔 (秒)
SENSOR_READ_INTERVAL_S = 1

# OLED 显示器引脚配置
OLED_SDA_PIN = 8  # 可以是任何支持 I2C 的引脚
OLED_SCL_PIN = 9  # 可以是任何支持 I2C 的引脚

# RGB-LED指示信号灯引脚配置（板载单灯珠）
RGB_PIN = 38

# WS2812 太阳灯灯条
SUN_LAMP_PIN = 2
SUN_LAMP_COUNT = 8


# 五向开关引脚配置（新增）
KEY_MID_PIN = 3
KEY_UP_PIN = 4
KEY_DOWN_PIN = 5
KEY_LEFT_PIN = 6
KEY_RIGHT_PIN = 10
KEY_SET_PIN = 11