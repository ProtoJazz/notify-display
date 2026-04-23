from machine import Pin, SPI
from base_display import BaseDisplay, DisplayBuffer
import writer

class SSD1680(BaseDisplay):
    def __init__(self, font_large, font_small, width=250, height=122, rotate=True):
        self.rst = Pin(2, Pin.OUT)
        self.cs = Pin(3, Pin.OUT)
        self.dc = Pin(5, Pin.OUT)
        self.busy = Pin(7, Pin.IN)
        self.spi = SPI(1, baudrate=2000000, polarity=0, phase=0,
                       sck=Pin(8), mosi=Pin(10), miso=Pin(9))

        bytes_per_row = (width + 7) // 8
        buf_size = bytes_per_row * height

        super().__init__(width, height, buf_size, bytes_per_row, font_large, font_small, rotate)

    def init(self):
        self.reset()

        self.send_command(0x12)
        self.wait_busy()

        self.send_command(0x01)
        self.send_data((self.height - 1) & 0xFF)
        self.send_data((self.height - 1) >> 8)
        self.send_data(0x00)

        self.send_command(0x11)
        self.send_data(0x03)

        self.send_command(0x44)
        self.send_data(0x00)
        self.send_data(self.bytes_per_row - 1)

        self.send_command(0x45)
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data((self.height - 1) & 0xFF)
        self.send_data((self.height - 1) >> 8)

        self.send_command(0x3C)
        self.send_data(0x05)

        self.send_command(0x21)
        self.send_data(0x00)
        self.send_data(0x80)

        self.send_command(0x18)
        self.send_data(0x80)

        self.send_command(0x4E)
        self.send_data(0x00)

        self.send_command(0x4F)
        self.send_data(0x00)
        self.send_data(0x00)

        self.wait_busy()