"""Draw the program's icon (`ComicToolkit.ico`): the yellow block with the square, circle and triangle of the sidebar logo.
Run it again after changing the drawing:  python packaging/make_icon.py"""
from pathlib import Path

from PIL import Image, ImageDraw

INK, YELLOW, PINK, CYAN, WHITE = "#111111", "#FFD60A", "#FF4FA3", "#2EC4E6", "#FFFFFF"
SIZE = 512


def draw():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((64, 64, 500, 500), fill=INK)                                  # the hard shadow
    d.rectangle((24, 24, 448, 448), fill=YELLOW, outline=INK, width=22)
    d.rectangle((92, 190, 262, 380), fill=WHITE, outline=INK, width=20)       # square
    d.polygon([(240, 380), (410, 380), (325, 220)], fill=CYAN, outline=INK)   # triangle
    d.line([(240, 380), (410, 380), (325, 220), (240, 380)], fill=INK, width=20, joint="curve")
    d.ellipse((70, 70, 250, 250), fill=PINK, outline=INK, width=20)           # circle
    return img


if __name__ == "__main__":
    out = Path(__file__).with_name("ComicToolkit.ico")
    draw().save(out, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("wrote", out)
