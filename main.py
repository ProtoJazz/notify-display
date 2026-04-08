import socket
import ssd1680
import json

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 80))
s.listen(1)


print("Listening on port 80...")
ssd1680.init()
ssd1680.print_word("Waiting....")
previous_parse = None

while True:
    conn, addr = s.accept()
    print("Connection from", addr)
    content_length = 1024
    data = conn.recv(content_length)

    data_string = data.decode()
    print(data_string)
    parts = data_string.split("\r\n\r\n")
    body = parts[1]
    headers = parts[0]

    for line in headers.split("\r\n"):
        if line.startswith("content-length:"):
            content_length = int(line.split(":")[1].strip())
            print("We got content length!")
            print(content_length)
    
    if content_length <= len(body):
        print("Raw body:", repr(body))
        print("all g")
    else:
        print("We pooped!")
        while len(body) < content_length:
            more = conn.recv(content_length - len(body))
            print("Raw body:", repr(more))

            new_body = more.decode()
            print(new_body)
            body += new_body
    
    parsed = json.loads(body)
    print(parsed)
    conn.send('HTTP/1.1 200 OK\r\n\r\nOK')
    conn.close()

    if previous_parse is not None and previous_parse == parsed:
        print("No update")
    else:
        previous_parse = parsed
        ssd1680.render_screen(
            parsed.get("event_name", ""),
            parsed.get("event_time", ""),
            parsed.get("event_countdown", ""),
            parsed.get("notif_app", ""),
            parsed.get("notif_text", ""),
        )