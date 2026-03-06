import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

_i2c = None
_oled = None
_image = None
_canvas = None
_font = None

def init():
    global _i2c, _oled, _image, _font
    _i2c = busio.I2C(board.SCL, board.SDA)
    _oled = adafruit_ssd1306.SSD1306_I2C(128, 32, _i2c)
    _font = ImageFont.load_default(size=14)

def clear():
    global _oled, _image, _canvas
    _image = Image.new("1", (_oled.width, _oled.height))
    _canvas = ImageDraw.Draw(_image)

def print(position, text):
    _canvas.text((position), text, font=_font, fill=255)

def flush():
    _oled.image(_image)
    _oled.show()
