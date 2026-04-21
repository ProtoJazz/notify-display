import config
import json
import socket
from machine import Pin
current_mode = 0
NUM_MODES = 2 # mode 0 main display, mode 1 info

def check_button():
    global last_press
    if button.value() == 0:
        now = time.ticks_ms()
        if time.ticks_diff(now, last_press) > 200:
            last_press = now
            return True
    return False


if config.DISPLAY == "ssd1680":
    from ssd1680 import SSD1680
    import font20
    import font14
    display = SSD1680(font_large=font20, font_small=font14)
elif config.DISPLAY == "ssd1683":
    from ssd1683 import SSD1683
    import font32
    import font20
    display = SSD1683(font_large=font32, font_small=font20)

display.init()

if config.TEST_MODE:
    display.render_screen(
        "Union Meeting",
        "14:00-15:30",
        "in 2h30m",
        "Slack",
        "Dental plan! Lisa needs braces"
    )
else:
    import boot
    needs_render = True
    button = Pin(4, Pin.IN, Pin.PULL_UP)

    last_press = 0

    ip = boot.wlan.ifconfig()[0]
    display.render_screen(
        "Waiting....",
        "",
        "",
        "IP Address",
        f"{ip}"
    )

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 80))
    s.listen(1)

    s.settimeout(0)

    print(f"Listening on {ip}:80")
    previous_parse = None

    while True:
        try:
            conn, addr = s.accept()
            print("Connection from", addr)
            content_length = 1024
            data = conn.recv(content_length)

            data_string = data.decode()
            parts = data_string.split("\r\n\r\n")
            body = parts[1]
            headers = parts[0]

            for line in headers.split("\r\n"):
                if line.startswith("content-length:"):
                    content_length = int(line.split(":")[1].strip())

            while len(body) < content_length:
                more = conn.recv(content_length - len(body))
                body += more.decode()

            parsed = json.loads(body)
            print(parsed)
            conn.send('HTTP/1.1 200 OK\r\n\r\nOK')
            conn.close()

            if previous_parse is not None and previous_parse == parsed:
                print("No update")
            else:
                previous_parse = parsed
                needs_render = True
        except OSError:
            pass

        if check_button():
            current_mode = (current_mode + 1) % NUM_MODES
            needs_render = True
            print("Mode:", current_mode)
        

        if needs_render:
            print("TRying to render")
            if current_mode == 0 and previous_parse is not None:
                display.render_screen(
                        previous_parse.get("event_name", ""),
                        previous_parse.get("event_time", ""),
                        previous_parse.get("event_countdown", ""),
                        previous_parse.get("notif_app", ""),
                        previous_parse.get("notif_text", ""),
                )

            if current_mode == 1:
                display.render_screen(
                    "Stroking....",
                    "",
                    "",
                    "IP Address",
                    f"{ip}"
                )
            
            needs_render = False
        


        time.sleep_ms(50)