import network
import config
import time
import ssd1680

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

while not wlan.isconnected():
    time.sleep_ms(10)

print(wlan.isconnected())
print(wlan.ifconfig())
ssd1680.init()
ssd1680.print_word(f"Connected to {wlan.config('essid')}")