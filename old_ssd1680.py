from machine import Pin, SPI
import time
import framebuf
import writer
import font32 as font24
import font20
import font14

_prev_buf = None
_partial_count = 0

class Display(framebuf.FrameBuffer):
    def __init__(self, buf, width, height):
        self.width = width
        self.height = height
        super().__init__(buf, width, height, framebuf.MONO_HLSB)

# Pin numbers match the Seeed breakout board wiring
RST  = Pin(2,  Pin.OUT)
CS   = Pin(3,  Pin.OUT)
DC   = Pin(5,  Pin.OUT)
BUSY = Pin(7,  Pin.IN)

spi = SPI(1, baudrate=4_000_000, polarity=0, phase=0,
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

    send_command(0x74)  # analog block control
    send_data(0x54)

    send_command(0x7E)  # digital block control
    send_data(0x3B)

    send_command(0x0C)  # soft start
    send_data(0x8E)
    send_data(0x8C)
    send_data(0x85)
    send_data(0x3F)

    send_command(0x2B)  # ACVCOM
    send_data(0x04)
    send_data(0x63)

    send_command(0x01)  # driver output control: 299 = 300 gates - 1
    send_data(0x2B)     # low byte
    send_data(0x01)     # high byte
    send_data(0x00)

    send_command(0x3A)  # dummy line period
    send_data(0x2C)

    send_command(0x3B)  # gate line width
    send_data(0x0A)

    send_command(0x3C)  # border waveform
    send_data(0x05)

    send_command(0x11)  # data entry mode: x increment, y increment
    send_data(0x03)

    send_command(0x44)  # set RAM x address range: 0 to 49 (50 bytes = 400px)
    send_data(0x00)
    send_data(0x31)

    send_command(0x45)  # set RAM y address range: 0 to 299
    send_data(0x00)
    send_data(0x00)
    send_data(0x2B)     # low byte
    send_data(0x01)     # high byte

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
    send_data(0xC7)     # partial refresh
    send_command(0x20)
    wait_busy()

def refresh():
    send_command(0x22)  # display update control 2
    send_data(0xF7)     # full update sequence
    send_command(0x20)  # activate display update
    wait_busy()

def print_word(word):
    buf = bytearray(b'\xff' * 15000)

    display = Display(buf, 400, 300)

    wri = writer.Writer(display, font24, verbose=False)
    writer.Writer.set_textpos(display, 10, 10)
    wri.printstring(word, invert=True)
    init()
    write_previous_image(buf) 
    write_image(buf)
    refresh()
    print("done")

def render_screen(event_name, event_time, event_countdown, notif_app, notif_text):
    global _prev_buf, _partial_count

    # Native landscape framebuffer: 400 wide x 300 tall
    # 400px / 8 = 50 bytes per row; 50 * 300 = 15000 bytes
    buf = bytearray(b'\xff' * 15000)
    display = Display(buf, 300, 400)

    # -- Calendar section --
    wri_big = writer.Writer(display, font20, verbose=False)
    writer.Writer.set_textpos(display, 4, 4)
    wri_big.printstring(truncate(event_name, 16), invert=True)

    wri_sm = writer.Writer(display, font14, verbose=False)
    time_line = event_time
    if event_countdown:
        time_line = event_time + "  " + event_countdown
    writer.Writer.set_textpos(display, 50, 4)
    wri_sm.printstring(truncate(time_line, 23), invert=True)

    # -- Divider line --
    y_div = 56
    for x in range(4, 399):
        byte_idx = (y_div * 50) + (x // 8)
        bit_idx = 7 - (x % 8)
        buf[byte_idx] &= ~(1 << bit_idx)

    # -- Notification section --
    if notif_app:
        writer.Writer.set_textpos(display, y_div + 6, 4)
        wri_big.printstring(truncate(notif_app, 20), invert=True)

    if notif_text:
        writer.Writer.set_textpos(display, y_div + 34, 4)
        wri_sm.printstring(truncate(notif_text, 23), invert=True)

    write_image(buf)

    if _prev_buf:
        write_previous_image(_prev_buf)
    else:
        write_previous_image(buf)

    if _prev_buf is None or _partial_count >= 5:
        _partial_count = 0
        refresh()
    else:
        _partial_count += 1
        refresh_partial()

    _prev_buf = bytearray(buf)


def truncate(text, max_chars):
    if len(text) > max_chars:
        return text[:max_chars - 2] + ".."
    return text