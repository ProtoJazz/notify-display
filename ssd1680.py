from machine import Pin, SPI
import time
import framebuf
import writer
import font24
import font20
import font14

_prev_buf = None
_partial_count = 0

class Display(framebuf.FrameBuffer):
    def __init__(self, buf, width, height):
        self.width = width
        self.height = height
        super().__init__(buf, width, height, framebuf.MONO_HLSB)
    
    def pixel(self, x, y, color):
        self._fb.pixel(x, y, color)
    
    def fill_rect(self, x, y, w, h, color):
        self._fb.fill_rect(x, y, w, h, color)
# Pin numbers match the Seeed breakout board wiring
RST  = Pin(2,  Pin.OUT)
CS   = Pin(3,  Pin.OUT)
DC   = Pin(5,  Pin.OUT)
BUSY = Pin(7,  Pin.IN)

spi = SPI(1, baudrate=2000000, polarity=0, phase=0,
          sck=Pin(8), mosi=Pin(10), miso=Pin(9))

def send_command(cmd):
    DC.value(0)   # DC low = command
    CS.value(0)   # CS low = select the chip
    spi.write(bytes([cmd]))
    CS.value(1)   # CS high = deselect

def send_data(data):
    DC.value(1)   # DC high = data
    CS.value(0)
    spi.write(bytes([data]))
    CS.value(1)

def wait_busy():
    while BUSY.value() == 1:
        time.sleep_ms(10)

def reset():
    RST.value(1)
    time.sleep_ms(10)
    RST.value(0)
    time.sleep_ms(10)
    RST.value(1)
    time.sleep_ms(10)
    wait_busy()

def init():
    reset()

    send_command(0x12)  # software reset
    wait_busy()

    send_command(0x01)  # gate setting (display height)
    send_data(0xF9)     # 249 = 250 lines - 1
    send_data(0x00)
    send_data(0x00)

    send_command(0x11)  # data entry mode
    send_data(0x03)     # x increment, y increment, update in x direction

    send_command(0x44)  # set RAM x address range
    send_data(0x00)     # start: 0
    send_data(0x0F)     # end: 15 (16 bytes * 8 bits = 128, covers 122 pixels)

    send_command(0x45)  # set RAM y address range
    send_data(0x00)     # start: 0
    send_data(0x00)
    send_data(0xF9)     # end: 249
    send_data(0x00)

    send_command(0x3C)  # border waveform
    send_data(0x05)

    send_command(0x21)  # display update control
    send_data(0x00)
    send_data(0x80)

    send_command(0x18)  # use built-in temperature sensor
    send_data(0x80)

    send_command(0x4E)  # set RAM x address counter to 0
    send_data(0x00)

    send_command(0x4F)  # set RAM y address counter to 0
    send_data(0x00)
    send_data(0x00)

    wait_busy()

def write_image(buf):
    send_command(0x24)  # write to RAM
    DC.value(1)
    CS.value(0)
    spi.write(buf)
    CS.value(1)

def write_previous_image(buf):
    send_command(0x26)  # write to RED/previous RAM
    DC.value(1)
    CS.value(0)
    spi.write(buf)
    CS.value(1)

def refresh_partial():
    send_command(0x22)
    send_data(0xC7)     # partial: no LUT reload, display Mode 1
    send_command(0x20)
    wait_busy()

def refresh():
    send_command(0x22)  # display update control 2
    send_data(0xF7)     # full update sequence
    send_command(0x20)  # activate display update
    wait_busy()

def print_word(word):
    # Source: landscape framebuffer for drawing into
    src_buf = bytearray(32 * 122)
    src_buf[:] = b'\xff' * len(src_buf)
    display = Display(src_buf, 250, 122)

    wri = writer.Writer(display, font24, verbose=False)
    writer.Writer.set_textpos(display, 10, 10)
    wri.printstring(word, invert=True)

    # Destination: portrait buffer to send to display
    dst_buf = bytearray(b'\xff' * 4000)

    # Rotate 90 degrees clockwise
    for y in range(122):
        for x in range(250):
            src_byte = (y * 32) + (x // 8)
            src_bit = 7 - (x % 8)
            pixel = (src_buf[src_byte] >> src_bit) & 1
            dst_x = 121 - y
            dst_y = x
            dst_byte = (dst_y * 16) + (dst_x // 8)
            dst_bit = 7 - (dst_x % 8)
            if pixel == 0:
                dst_buf[dst_byte] &= ~(1 << dst_bit)

    init()
    write_image(dst_buf)
    refresh()
    print("done")

def render_screen(event_name, event_time, event_countdown, notif_app, notif_text):
    global _prev_buf, _partial_count
    src_buf = bytearray(32 * 122)
    src_buf[:] = b'\xff' * len(src_buf)
    display = Display(src_buf, 250, 122)

    # -- Calendar section --
    wri_big = writer.Writer(display, font20, verbose=False)
    writer.Writer.set_textpos(display, 4, 4)
    wri_big.printstring(truncate(event_name, 16), invert=True)

    # Time + countdown on one line: "12:00-12:15 PM  in 45m"
    wri_sm = writer.Writer(display, font14, verbose=False)
    time_line = event_time
    if event_countdown:
        time_line = event_time + "  " + event_countdown
    writer.Writer.set_textpos(display, 32, 4)
    wri_sm.printstring(truncate(time_line, 23), invert=True)

    # -- Divider line --
    y_div = 56
    for x in range(4, 246):
        byte_idx = (y_div * 32) + (x // 8)
        bit_idx = 7 - (x % 8)
        src_buf[byte_idx] &= ~(1 << bit_idx)

    # -- Notification section --
    if notif_app:
        writer.Writer.set_textpos(display, y_div + 6, 4)
        wri_big.printstring(truncate(notif_app, 20), invert=True)

    if notif_text:
        writer.Writer.set_textpos(display, y_div + 34, 4)
        wri_sm.printstring(truncate(notif_text, 23), invert=True)

    # Rotate and send to display
    dst_buf = bytearray(b'\xff' * 4000)
    for y in range(122):
        for x in range(250):
            src_byte = (y * 32) + (x // 8)
            src_bit = 7 - (x % 8)
            pixel = (src_buf[src_byte] >> src_bit) & 1
            dst_x = 121 - y
            dst_y = x
            dst_byte = (dst_y * 16) + (dst_x // 8)
            dst_bit = 7 - (dst_x % 8)
            if pixel == 0:
                dst_buf[dst_byte] &= ~(1 << dst_bit)

    write_image(dst_buf)
    
    if _prev_buf:
        write_previous_image(_prev_buf)
    else:
        write_previous_image(dst_buf)

    if _prev_buf is None or _partial_count >= 5:
        # Full refresh — clean slate
        _partial_count = 0
        refresh()
    else:
        # Partial refresh — no flicker
        _partial_count += 1
        refresh_partial()
    
    _prev_buf = bytearray(dst_buf)
        
    

def truncate(text, max_chars):
    if len(text) > max_chars:
        return text[:max_chars - 2] + ".."
    return text