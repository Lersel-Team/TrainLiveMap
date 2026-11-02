#!/usr/bin/env python3
"""Paints livery atlases for the QSY and BTC models. Hand-drawn from reference photos, no photo pixels used.
Atlas: 2048x2048. v .75-1 = side seen from +Y, v .5-.75 = side seen from -Y, bottom-left 512x512 = end face.
Needs: pip install pillow. Run from anywhere."""
import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
S, ROW = 2048, 512
BOLDIT = '/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf'
BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
SILVER, RED, WHITE, DARK, GLASS = (186, 190, 194), (214, 36, 44), (240, 240, 238), (38, 40, 44), (34, 48, 60)

def side_layer(paint):
    im = Image.new('RGB', (S, ROW), SILVER); paint(ImageDraw.Draw(im), im); return im

def qsy_side(flip):
    """Seen with cab 1 on the left; flip draws the mirrored layout with lettering still readable."""
    X = (lambda p: S - p) if flip else (lambda p: p)
    def paint(d, im):
        P = lambda pts, c: d.polygon([(X(x), y) for x, y in pts], fill=c)
        R = lambda a, b, c, e, **k: d.rectangle([min(X(a), X(c)), b, max(X(a), X(c)), e], **k)
        # red sweep under the cab windows, narrowing along the lower body
        P([(0, 150), (150, 90), (235, 90), (235, 300), (620, 330), (980, 330), (1120, 400), (1120, 512), (0, 512)], RED)
        # white stripe through the sweep
        P([(235, 365), (640, 305), (980, 305), (1100, 365), (1000, 345), (660, 330), (235, 395)], WHITE)
        # rear sweep
        P([(1500, 512), (1660, 365), (2048, 335), (2048, 512)], RED)
        P([(1660, 345), (2048, 318), (2048, 335), (1660, 365)], WHITE)
        P([(1880, 0), (2048, 0), (2048, 210), (1960, 210)], RED)
        # cab door and window
        R(70, 120, 225, 500, outline=(120, 124, 128), width=4)
        R(105, 150, 190, 300, fill=GLASS, outline=DARK, width=5)
        # engine room doors
        for a in (340, 480, 620, 760): R(a, 90, a + 130, 430, outline=(130, 134, 138), width=4)
        # radiator louvres
        R(1600, 90, 1860, 300, fill=DARK)
        for y in range(100, 300, 14): R(1604, y, 1856, y + 5, fill=(74, 76, 80))
        R(1880, 120, 1960, 300, outline=(120, 124, 128), width=4); R(1895, 150, 1945, 250, fill=GLASS)
        # speed lines and SRT lettering
        f = ImageFont.truetype(BOLDIT, 220)
        tx = 598 if flip else 1000
        for i, (dy, ln) in enumerate(((150, 170), (205, 130), (270, 90))):
            x = tx - 30 - ln; d.polygon([(x, dy), (x + ln + 20, dy), (x + ln, dy + 13), (x - 20, dy + 13)], fill=RED)
        d.text((tx, 85), 'SRT', font=f, fill=RED)
        n = ImageFont.truetype(BOLD, 34); nx = (S - 200) if flip else 60
        d.text((nx, 455), '5203', font=n, fill=WHITE)
    return side_layer(paint)

def qsy_end():
    im = Image.new('RGB', (ROW, ROW), SILVER); d = ImageDraw.Draw(im)
    # texture covers z 1.1 to the roof; windscreen in the sloped upper part
    d.rectangle([0, 0, ROW, 70], fill=RED)
    d.polygon([(55, 95), (457, 95), (435, 245), (77, 245)], fill=GLASS)
    d.line([(256, 95), (256, 245)], fill=DARK, width=9)
    d.rectangle([0, 395, ROW, ROW], fill=RED)
    d.polygon([(0, 300), (90, 330), (90, 395), (0, 395)], fill=RED); d.polygon([(512, 300), (422, 330), (422, 395), (512, 395)], fill=RED)
    for x in (60, 410): d.ellipse([x, 300, x + 42, 342], fill=(250, 248, 215), outline=DARK, width=4)
    f = ImageFont.truetype(BOLDIT, 56); d.text((110, 425), 'SRT', font=f, fill=WHITE)
    f = ImageFont.truetype(BOLD, 42); d.text((300, 432), '5203', font=f, fill=WHITE)
    return im

BLUE, CREAM, FRAME = (28, 84, 170), (236, 236, 228), (54, 110, 192)
def btc_side(flip):
    def paint(d, im):
        d.rectangle([0, 0, S, ROW], fill=CREAM)
        d.rectangle([0, 318, S, ROW], fill=BLUE)
        # end vestibule doors
        for a in (24, 1924):
            d.rectangle([a, 60, a + 100, 500], fill=(222, 222, 214), outline=(110, 120, 140), width=4)
            d.rectangle([a + 22, 90, a + 78, 215], fill=GLASS)
        # windows: louvred blue shutters, some open
        n, x0, gap = 9, 190, 186
        for i in range(n):
            x = x0 + i * gap; open_ = i in (2, 5, 7)
            d.rectangle([x, 95, x + 130, 280], fill=FRAME if not open_ else GLASS, outline=(18, 60, 130), width=5)
            if not open_:
                for y in range(106, 276, 13): d.line([(x + 5, y), (x + 125, y)], fill=(22, 72, 150), width=3)
        d.line([(0, 318), (S, 318)], fill=(14, 52, 110), width=5)
        d.text((1000 if not flip else 900, 335), 'B.T.C.', font=ImageFont.truetype(BOLD, 38), fill=WHITE)
    return side_layer(paint)

def btc_end():
    im = Image.new('RGB', (ROW, ROW), CREAM); d = ImageDraw.Draw(im)
    d.rectangle([0, 300, ROW, ROW], fill=BLUE)
    d.rectangle([166, 40, 346, ROW], fill=(70, 74, 80)); d.rectangle([186, 70, 326, 220], fill=GLASS)
    return im

def atlas(a, b, e, path):
    im = Image.new('RGB', (S, S), (120, 120, 120)); im.paste(a, (0, 0)); im.paste(b, (0, ROW)); im.paste(e, (0, S - ROW))
    im.save(path, optimize=True); print(path, os.path.getsize(path))
atlas(qsy_side(False), qsy_side(True), qsy_end(), os.path.join(HERE, 'qsy.png'))
atlas(btc_side(False), btc_side(True), btc_end(), os.path.join(HERE, 'btc.png'))
