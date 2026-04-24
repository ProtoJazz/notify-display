from machine import Pin, SPI
from base_display import BaseDisplay, DisplayBuffer
import writer

class SSD1683(BaseDisplay):
    def __init__(self, font_large, font_small, width=400, height=300):
        self.rst = Pin(2, Pin.OUT)
        self.cs = Pin(3, Pin.OUT)
        self.dc = Pin(5, Pin.OUT)
        self.busy = Pin(7, Pin.IN)
        self.spi = SPI(1, baudrate=4000000, polarity=0, phase=0,
                       sck=Pin(8), mosi=Pin(10), miso=Pin(9))

        bytes_per_row = (width + 7) // 8
        buf_size = bytes_per_row * height

        super().__init__(width, height, buf_size, bytes_per_row, font_large, font_small, rotate=False)

    def init(self):
        self.reset()

        self.send_command(0x12)
        self.wait_busy()

        self.send_command(0x74)  # analog block control
        self.send_data(0x54)

        self.send_command(0x7E)  # digital block control
        self.send_data(0x3B)

        self.send_command(0x0C)  # soft start
        self.send_data(0x8E)
        self.send_data(0x8C)
        self.send_data(0x85)
        self.send_data(0x3F)

        self.send_command(0x2B)  # ACVCOM
        self.send_data(0x04)
        self.send_data(0x63)

        self.send_command(0x21)   # Display update control 1
        self.send_data(0x40)      # Red RAM: bypass as 0
        self.send_data(0x00)      # BW RAM: normal

        self.send_command(0x01)  # driver output control
        self.send_data((self.height - 1) & 0xFF)
        self.send_data((self.height - 1) >> 8)
        self.send_data(0x00)

        self.send_command(0x3A)  # dummy line period
        self.send_data(0x2C)

        self.send_command(0x3B)  # gate line width
        self.send_data(0x0A)

        self.send_command(0x3C)  # border waveform
        self.send_data(0x05)

        self.send_command(0x11)  # data entry mode
        self.send_data(0x03)

        self.send_command(0x44)  # set RAM x address range
        self.send_data(0x00)
        self.send_data(self.bytes_per_row - 1)

        self.send_command(0x45)  # set RAM y address range
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_data((self.height - 1) & 0xFF)
        self.send_data((self.height - 1) >> 8)

        self.send_command(0x4E)  # set RAM x address counter to 0
        self.send_data(0x00)

        self.send_command(0x4F)  # set RAM y address counter to 0
        self.send_data(0x00)
        self.send_data(0x00)

        self.wait_busy()
