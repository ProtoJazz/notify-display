import time
import framebuf
import writer


class DisplayBuffer(framebuf.FrameBuffer):
    def __init__(self, buf, width, height):
        self.width = width
        self.height = height
        super().__init__(buf, width, height, framebuf.MONO_HLSB)


class BaseDisplay:
    # Subclass must set self.spi, self.cs, self.dc, self.rst, self.busy
    # before calling super().__init__()

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
        self._calculate_layout()

    def _calculate_layout(self):
        pad = 4
        large_h = self.font_large.height()
        small_h = self.font_small.height()
        half = self.height // 2

        # Check if we have room for wrapped lines
        top_2_lines = pad + (large_h * 2) + pad + small_h + pad
        self.event_wrap = top_2_lines < half

        bot_2_lines = pad + large_h + pad + (small_h * 2) + pad
        self.notif_wrap = bot_2_lines < half

        # Top half — calendar
        y = pad
        self.event_name_y = y
        y += large_h + pad
        if self.event_wrap:
            self.event_name2_y = y
            y += large_h + pad
        self.time_y = y

        # Divider at halfway
        self.divider_y = half

        # Bottom half — notifications
        y = half + pad
        self.notif_app_y = y
        y += large_h + pad
        self.notif_text_y = y
        if self.notif_wrap:
            y += small_h + pad
            self.notif_text2_y = y

        self.pad = pad

    def _fit_text(self, wri, text):
        usable = self.width - (self.pad * 2)
        if wri.stringlen(text) <= usable:
            return text
        while len(text) > 0 and wri.stringlen(text + "..") > usable:
            text = text[:-1]
        return text + ".."

    def _wrap_text(self, wri, text):
        usable = self.width - (self.pad * 2)
        if wri.stringlen(text) <= usable:
            return [text]

        words = text.split(' ')
        line = ''
        for word in words:
            test = (line + ' ' + word).strip()
            if wri.stringlen(test) > usable:
                break
            line = test

        if not line:
            return [self._fit_text(wri, text)]

        remainder = text[len(line):].strip()
        return [line, self._fit_text(wri, remainder)]

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
        self.send_command(0x4E)
        self.send_data(0x00)
        self.send_command(0x4F)
        self.send_data(0x00)
        self.send_data(0x00)

        self.write_image(dst_buf)

        if self._prev_buf:
            self.write_previous_image(self._prev_buf)
        else:
            self.write_previous_image(dst_buf)

        if True or self._prev_buf is None or self._partial_count >= 5:
            self._partial_count = 0
            self.refresh()
        else:
            self._partial_count += 1
            self.refresh_partial()

        self._prev_buf = bytearray(dst_buf)

    def _rotate_cw(self, src_buf, src_width, src_height):
        src_stride = (src_width + 7) // 8
        dst_stride = (src_height + 7) // 8
        dst_buf = bytearray(b'\xff' * (src_width * dst_stride))

        for y in range(src_height):
            for x in range(src_width):
                src_byte = (y * src_stride) + (x // 8)
                src_bit = 7 - (x % 8)
                pixel = (src_buf[src_byte] >> src_bit) & 1
                dst_x = src_height - 1 - y
                dst_y = x
                dst_byte = (dst_y * dst_stride) + (dst_x // 8)
                dst_bit = 7 - (dst_x % 8)
                if pixel == 0:
                    dst_buf[dst_byte] &= ~(1 << dst_bit)

        return dst_buf

    def render_screen(self, event_name, event_time, event_countdown, notif_app, notif_text):
        draw_stride = (self.width + 7) // 8
        draw_size = draw_stride * self.height
        buf = bytearray(b'\xff' * draw_size)
        display = DisplayBuffer(buf, self.width, self.height)

        wri_big = writer.Writer(display, self.font_large, verbose=False)
        wri_sm = writer.Writer(display, self.font_small, verbose=False)

        # -- Event name --
        if self.event_wrap:
            lines = self._wrap_text(wri_big, event_name)
            writer.Writer.set_textpos(display, self.event_name_y, self.pad)
            wri_big.printstring(lines[0], invert=True)
            if len(lines) > 1:
                writer.Writer.set_textpos(display, self.event_name2_y, self.pad)
                wri_big.printstring(lines[1], invert=True)
        else:
            writer.Writer.set_textpos(display, self.event_name_y, self.pad)
            wri_big.printstring(self._fit_text(wri_big, event_name), invert=True)

        # -- Time + countdown --
        time_line = event_time
        if event_countdown:
            time_line = event_time + "  " + event_countdown
        writer.Writer.set_textpos(display, self.time_y, self.pad)
        wri_sm.printstring(self._fit_text(wri_sm, time_line), invert=True)

        # -- Divider --
        for x in range(self.pad, self.width - self.pad):
            byte_idx = (self.divider_y * draw_stride) + (x // 8)
            bit_idx = 7 - (x % 8)
            buf[byte_idx] &= ~(1 << bit_idx)

        # -- Notification app --
        if notif_app:
            writer.Writer.set_textpos(display, self.notif_app_y, self.pad)
            wri_big.printstring(self._fit_text(wri_big, notif_app), invert=True)

        # -- Notification text --
        if notif_text:
            if self.notif_wrap:
                lines = self._wrap_text(wri_sm, notif_text)
                writer.Writer.set_textpos(display, self.notif_text_y, self.pad)
                wri_sm.printstring(lines[0], invert=True)
                if len(lines) > 1:
                    writer.Writer.set_textpos(display, self.notif_text2_y, self.pad)
                    wri_sm.printstring(lines[1], invert=True)
            else:
                writer.Writer.set_textpos(display, self.notif_text_y, self.pad)
                wri_sm.printstring(self._fit_text(wri_sm, notif_text), invert=True)

        if self.rotate:
            buf = self._rotate_cw(buf, self.width, self.height)

        self.update_display(buf)

    def print_word(self, word):
        draw_stride = (self.width + 7) // 8
        draw_size = draw_stride * self.height
        buf = bytearray(b'\xff' * draw_size)
        display = DisplayBuffer(buf, self.width, self.height)

        wri = writer.Writer(display, self.font_large, verbose=False)
        writer.Writer.set_textpos(display, 10, 10)
        wri.printstring(word, invert=True)

        if self.rotate:
            buf = self._rotate_cw(buf, self.width, self.height)

        self.init()
        self.write_image(buf)
        self.refresh()
        print("done")