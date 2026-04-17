import time
import framebuf

class DisplayBuffer(framebuf.FrameBuffer):
    def __init__(self, buf, width, height):
        self.width = width
        self.height = height
        super().__init__(buf, width, height, framebuf.MONO_HLSB)

class BaseDisplay:
    def __init__(self, width, height, buf_size, bytes_per_row, font_large, font_small, rotate=False):
        self.width = width
        self.height = height
        self.buf_size = buf_size
        self.bytes_per_row = bytes_per_row
        self.font_large = font_large
        self.font_small = font_small
        self.rotate = rotate
        self._prev_buf = None
        self._partial_count = 0
        
    def send_command(self, cmd):
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytes([cmd]))
        self.cs.value(1)

    def send_data(self, data):
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(bytes([data]))
        self.cs.value(1)

    def wait_busy(self):
        while self.busy.value() == 1:
            time.sleep_ms(10)

    def reset(self):
        self.rst.value(1)
        time.sleep_ms(10)
        self.rst.value(0)
        time.sleep_ms(10)
        self.rst.value(1)
        time.sleep_ms(10)
        self.wait_busy()

    def write_image(self, buf):
        self.send_command(0x24)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(buf)
        self.cs.value(1)

    def write_previous_image(self, buf):
        self.send_command(0x26)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(buf)
        self.cs.value(1)

    def refresh(self):
        self.send_command(0x22)
        self.send_data(0xF7)
        self.send_command(0x20)
        self.wait_busy()

    def refresh_partial(self):
        self.send_command(0x22)
        self.send_data(0xC7)
        self.send_command(0x20)
        self.wait_busy()

    def update_display(self, dst_buf):
        self.write_image(dst_buf)

        if self._prev_buf:
            self.write_previous_image(self._prev_buf)
        else:
            self.write_previous_image(dst_buf)

        if self._prev_buf is None or self._partial_count >= 5:
            self._partial_count = 0
            self.refresh()
        else:
            self._partial_count += 1
            self.refresh_partial()

        self._prev_buf = bytearray(dst_buf)

    @staticmethod
    def truncate(text, max_chars):
        if len(text) > max_chars:
            return text[:max_chars - 2] + ".."
        return text