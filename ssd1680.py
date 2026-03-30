from machine import Pin, SPI
import time
import framebuf

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

def refresh():
    send_command(0x22)  # display update control 2
    send_data(0xF7)     # full update sequence
    send_command(0x20)  # activate display update
    wait_busy()

buf = bytearray([0xFF] * 4000)
fb = framebuf.FrameBuffer(buf, 250, 122, framebuf.MONO_HLSB)

# Rotate text 90 degrees by drawing into a temp buffer first
tmp = bytearray([0xFF] * 4000)
tfb = framebuf.FrameBuffer(tmp, 122, 250, framebuf.MONO_HLSB)
tfb.text("penis", 10, 10, 0)

# Copy rotated
for y in range(122):
    for x in range(250):
        src_x = 121 - y
        src_y = x
        src_byte = (src_y * 16) + (src_x // 8)
        src_bit = 7 - (src_x % 8)
        pixel = (tmp[src_byte] >> src_bit) & 1
        dst_byte = (y * 16) + (x // 8)
        dst_bit = 7 - (x % 8)
        if pixel == 0:
            buf[dst_byte] &= ~(1 << dst_bit)

init()
write_image(buf)
refresh()
print("done")