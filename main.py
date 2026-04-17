import config
import json
import socket

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

    print(f"Listening on {ip}:80")
    previous_parse = None

    while True:
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
            display.render_screen(
                parsed.get("event_name", ""),
                parsed.get("event_time", ""),
                parsed.get("event_countdown", ""),
                parsed.get("notif_app", ""),
                parsed.get("notif_text", ""),
            )