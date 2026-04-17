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

    def render_screen(self, event_name, event_time, event_countdown, notif_app, notif_text):
        buf = bytearray(b'\xff' * self.buf_size)
        display = DisplayBuffer(buf, self.width, self.height)

        # -- Calendar section --
        wri_big = writer.Writer(display, self.font_large, verbose=False)
        writer.Writer.set_textpos(display, 4, 4)
        wri_big.printstring(self.truncate(event_name, 16), invert=True)

        wri_sm = writer.Writer(display, self.font_small, verbose=False)
        time_line = event_time
        if event_countdown:
            time_line = event_time + "  " + event_countdown
        writer.Writer.set_textpos(display, 50, 4)
        wri_sm.printstring(self.truncate(time_line, 23), invert=True)

        # -- Divider line --
        y_div = 56
        for x in range(4, self.width - 4):
            byte_idx = (y_div * self.bytes_per_row) + (x // 8)
            bit_idx = 7 - (x % 8)
            buf[byte_idx] &= ~(1 << bit_idx)

        # -- Notification section --
        if notif_app:
            writer.Writer.set_textpos(display, y_div + 6, 4)
            wri_big.printstring(self.truncate(notif_app, 20), invert=True)

        if notif_text:
            writer.Writer.set_textpos(display, y_div + 34, 4)
            wri_sm.printstring(self.truncate(notif_text, 23), invert=True)

        self.update_display(buf)

    def print_word(self, word):
        buf = bytearray(b'\xff' * self.buf_size)
        display = DisplayBuffer(buf, self.width, self.height)

        wri = writer.Writer(display, self.font_large, verbose=False)
        writer.Writer.set_textpos(display, 10, 10)
        wri.printstring(word, invert=True)

        self.init()
        self.write_previous_image(buf)
        self.write_image(buf)
        self.refresh()
        print("done")