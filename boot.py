import config

wlan = None

if not config.TEST_MODE:
    import network
    import time

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

    while not wlan.isconnected():
        time.sleep_ms(10)

    print(wlan.ifconfig())