from ssd1683 import SSD1683
import font32
import font20
display = SSD1683(font_large=font32, font_small=font20)

display.init()

display.render_screen(
        "Union Meeting",
        "14:00-15:30",
        "in 2h30m",
        "Slack",
        "Dental plan! Lisa needs braces"
    )

time.sleep_ms(50)

display.render_screen(
        "Union Meeting",
        "14:00-15:30",
        "in 2h30m",
        "Slack",
        "Dental plan! Lisa needs braces"
    )

time.sleep_ms(50)

display.render_screen(
        "Union Meeting",
        "14:00-15:30",
        "in 2h30m",
        "Slack",
        "Dental plan! Lisa needs braces"
    )

time.sleep_ms(50)

display.render_screen(
        "Union Meeting",
        "14:00-15:30",
        "in 2h30m",
        "Slack",
        "Dental plan! Lisa needs braces"
    )

time.sleep_ms(50)

display.render_screen(
        "DOOM Meeting",
        "14:00-15:30",
        "in 2h30m",
        "SDONERlack",
        "Dental plan! Lisa needs braces"
    )

time.sleep_ms(50)

