from machine import Pin
import time

button = Pin(4, Pin.IN, Pin.PULL_UP)

last_press = 0

def check_button():
    global last_press
    if button.value() == 0:
        now = time.ticks_ms()
        if time.ticks_diff(now, last_press) > 200:
            last_press = now
            return True
    return False

current_mode = 0
NUM_MODES = 2

while True:
    if check_button():
        current_mode = (current_mode + 1) % NUM_MODES
        print("Mode:", current_mode)
    time.sleep_ms(50)