#!/usr/bin/env python3
"""Paints livery atlases for the QSY and BTC models, by hand from reference photos (no photo pixels used).
Atlas 4096x4096. v .75-1 = side seen from +Y, v .5-.75 = side seen from -Y, bottom-left 1024x1024 = end face.
Needs: pip install pillow numpy."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
S, ROW = 4096, 1024
F = '/System/Library/Fonts/Supplemental/'
BOLDIT, BOLD, THAI = F + 'Arial Bold Italic.ttf', F + 'Arial Bold.ttf', F + 'Thonburi.ttc' if os.path.exists(F + 'Thonburi.ttc') else F + 'Ayuthaya.ttf'
rng = np.random.default_rng(7)

def weather(im, streak=.6, grime=.1):
    """Vertical rain streaks and soft dirt, heavier toward the bottom, so nothing looks freshly painted."""
    a = np.asarray(im.convert('RGB')).astype(np.float32) / 255; h, w = a.shape[:2]
    cols = np.asarray(Image.fromarray((rng.random((1, w // 8)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255
    blot = np.asarray(Image.fromarray((rng.random((h // 64, w // 64)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255
    depth = (np.arange(h, dtype=np.float32) / h)[:, None]
    shade = 1 - (cols - .5) * .07 * streak - (blot - .5) * .09 - grime * depth ** 2
    fine = rng.normal(0, .006, (h, w))
    return Image.fromarray((np.clip(a * shade[..., None] + fine[..., None], 0, 1) * 255).astype(np.uint8))

# ---------------- QSY. Length 21 m, sill 1.14 to eave 3.12 m. Colours sampled by eye from loco 5203.
QL, Qz0, QzE = 21.0, 1.14, 3.12
SILVER, RED, WHITE, DARK, GLASS = (168, 172, 176), (196, 34, 40), (232, 232, 228), (34, 36, 40), (24, 34, 44)
PANEL = (150, 154, 158)
def qsy_side(flip):
    # Drawn at 4096 wide: 195 px per metre. Seen with cab 1 on the left; flip mirrors the layout, not the lettering.
    im = Image.new('RGB', (S, ROW), SILVER); d = ImageDraw.Draw(im)
    X = (lambda p: S - p) if flip else (lambda p: p)
    P = lambda pts, c: d.polygon([(X(x), y) for x, y in pts], fill=c)
    def R(a, b, c, e, **k): d.rectangle([min(X(a), X(c)), b, max(X(a), X(c)), e], **k)
    # Silver front corner, then a red surround at the cab window that sweeps down and back below the doors (see 5203)
    P([(250, 150), (480, 120), (560, 120), (560, 640), (1250, 720), (1950, 720), (2300, 860), (2300, 1024), (760, 1024), (250, 760)], RED)
    P([(560, 770), (1280, 650), (1950, 650), (2230, 780), (1980, 720), (1300, 695), (560, 830)], WHITE)
    # Rear sweep and the red at the far cab, which mirrors the front treatment
    P([(3000, 1024), (3320, 760), (3846, 700), (3846, 1024)], RED)
    P([(3320, 720), (3846, 666), (3846, 700), (3320, 760)], WHITE)
    P([(3520, 150), (3846, 150), (3846, 640), (3620, 640)], RED)
    # Panel for the lettering, then engine room doors with handles and hinge lines
    R(2020, 150, 2980, 660, fill=PANEL)
    for a, b in ((700, 960), (970, 1230), (1240, 1500), (1510, 1770)):
        R(a, 150, b, 700, outline=(104, 108, 112), width=6)
        R(b - 40, 400, b - 22, 470, fill=(70, 72, 76))
        for y in (220, 620): R(a + 6, y, a + 22, y + 26, fill=(120, 122, 126))
    for a in (2020, 2500, 2980): R(a, 150, a + 5, 660, fill=(104, 108, 112))
    # Lifting points, number and data panels
    for a in (560, 3560): R(a, 880, a + 60, 950, fill=(60, 62, 66))
    # SRT lettering with speed lines
    f = ImageFont.truetype(BOLDIT, 400); tx = S - 2960 if flip else 2060
    for dy, ln in ((300, 330), (400, 250), (520, 170)):
        x = tx - 40 - ln; d.polygon([(x, dy), (x + ln + 40, dy), (x + ln, dy + 24), (x - 40, dy + 24)], fill=RED)
    d.text((tx, 190), 'SRT', font=f, fill=RED)
    n = ImageFont.truetype(BOLD, 70); d.text(((S - 500) if flip else 300, 900), '5203', font=n, fill=WHITE)
    im = weather(im, streak=.5, grime=.14)
    return im
def qsy_end():
    im = Image.new('RGB', (ROW, ROW), SILVER); d = ImageDraw.Draw(im)
    # z runs from sill (bottom) to roof peak (top). Glass is separate geometry; this paints what surrounds it.
    d.rectangle([0, 0, ROW, 190], fill=RED)
    d.polygon([(0, 560), (150, 640), (874, 640), (1024, 560), (1024, 1024), (0, 1024)], fill=(150, 154, 158))
    d.rectangle([0, 800, ROW, ROW], fill=RED)
    d.rectangle([300, 800, 724, ROW], fill=(150, 154, 158))
    d.rectangle([20, 280, 1004, 560], fill=(20, 24, 30))
    f = ImageFont.truetype(BOLDIT, 110); d.text((60, 860), 'SRT', font=f, fill=WHITE)
    f = ImageFont.truetype(BOLD, 90); d.text((760, 870), '5203', font=f, fill=WHITE)
    d.ellipse([452, 620, 572, 740], outline=(150, 40, 44), width=9)
    return weather(im, streak=.5, grime=.12)

# ---------------- BTC third class, after B.T.C. 294. Length 20 m, sill 1.0 to eave 3.1 m.
BL, Bz0, BzE = 20.0, 1.0, 3.1
BLUE, BLUE_D, CREAM = (24, 74, 156), (14, 48, 110), (228, 228, 218)
WINDOWS = (-7.35, -5.25, -3.15, -1.05, 1.05, 3.15, 5.25, 7.35)
OPEN = {(1, 2), (1, 5), (-1, 1), (-1, 6)}   # (side, window) left open
WIN_W, WZ1, WZ2 = 1.25, 1.72, 2.52
def bxy(x, z, seen): return ((BL / 2 - x) if seen > 0 else (x + BL / 2)) / BL * S, (1 - (z - Bz0) / (BzE - Bz0)) * ROW
def btc_side(seen):
    im = Image.new('RGB', (S, ROW), CREAM); d = ImageDraw.Draw(im)
    Y = lambda z: (1 - (z - Bz0) / (BzE - Bz0)) * ROW
    d.rectangle([0, Y(1.66), S, ROW], fill=BLUE)
    d.rectangle([0, Y(1.66), S, Y(1.66) + 8], fill=BLUE_D)
    for x in (-8.4, -5.25 + 1.05, 0, 4.2, 8.4):                    # body panel seams
        u = bxy(x, 2, seen)[0]; d.line([(u, 0), (u, ROW)], fill=(190, 192, 186), width=3)
    for i, c in enumerate(WINDOWS):
        a, top = bxy(c - WIN_W / 2 * seen, WZ2, seen); b, bot = bxy(c + WIN_W / 2 * seen, WZ1, seen)
        a, b = min(a, b), max(a, b)
        if (seen, i) in OPEN:
            d.rectangle([a, top, b, bot], fill=(36, 40, 44))
            d.rectangle([a, top + (bot - top) * .62, b, bot], fill=(70, 50, 34))   # seat back seen through the opening
            d.line([(a, top + (bot - top) * .33), (b, top + (bot - top) * .33)], fill=(120, 124, 128), width=6)
        else:
            d.rectangle([a, top, b, bot], fill=(38, 92, 180))
            for y in np.arange(top + 12, bot - 6, 24): d.rectangle([a + 8, y, b - 8, y + 10], fill=(24, 70, 150))
            d.line([((a + b) / 2, top), ((a + b) / 2, bot)], fill=(20, 60, 130), width=8)
    u = bxy(-6.3 if seen > 0 else 6.3, 1.4, seen)[0]
    d.text((u, Y(1.56)), 'บชส.', font=ImageFont.truetype(THAI, 64), fill=WHITE)
    d.text((u, Y(1.35)), '294', font=ImageFont.truetype(BOLD, 60), fill=WHITE)
    tu = bxy(-7.95 if seen > 0 else 7.95, 2.65, seen)[0]
    d.text((tu - 16, Y(2.98)), '3', font=ImageFont.truetype(BOLD, 74), fill=(180, 40, 40))
    return weather(im, streak=1, grime=.2)
def btc_end():
    im = Image.new('RGB', (ROW, ROW), CREAM); d = ImageDraw.Draw(im)
    y = lambda z: (1 - (z - 1.0) / (3.72 - 1.0)) * ROW
    d.rectangle([0, y(1.66), ROW, ROW], fill=BLUE)
    return weather(im, streak=1, grime=.2)

def atlas(a, b, e, path):
    im = Image.new('RGB', (S, S), (110, 110, 110)); im.paste(a, (0, 0)); im.paste(b, (0, ROW)); im.paste(e, (0, S - ROW))
    im.save(path, quality=88); print(path, os.path.getsize(path))
atlas(qsy_side(False), qsy_side(True), qsy_end(), os.path.join(HERE, 'qsy.jpg'))
atlas(btc_side(1), btc_side(-1), btc_end(), os.path.join(HERE, 'btc.jpg'))
