"""
Generate TerahBank splash screen PNG for Expo.
Output: apps/mobile/assets/splash.png (1284×2778)
"""
from PIL import Image, ImageDraw, ImageFont
import math, os

W, H = 1284, 2778

NAVY     = (11, 31, 74)      # #0B1F4A
TEAL     = (0, 180, 216)     # #00B4D8
TEAL_D   = (0, 150, 180)     # #0096B4  (darker teal for depth)
WHITE    = (255, 255, 255)
GREY     = (107, 122, 153)   # #6B7A99

img  = Image.new("RGB", (W, H), NAVY)
draw = ImageDraw.Draw(img)

cx = W // 2
cy = H // 2 - 80   # slightly above mid

# ── Subtle radial glow behind logo ────────────────────────────────────────────
glow = Image.new("RGB", (W, H), NAVY)
gd   = ImageDraw.Draw(glow)
for r in range(380, 0, -4):
    alpha = int(18 * (1 - r / 380))
    col = tuple(min(255, c + alpha) for c in NAVY)
    gd.ellipse([cx - r, cy - r - 60, cx + r, cy + r - 60], fill=col)
img.paste(glow, (0, 0))
draw = ImageDraw.Draw(img)

# ── Shield shape ───────────────────────────────────────────────────────────────
SH_W = 220   # half-width
SH_H = 300   # half-height
top  = cy - SH_H - 60
mid  = cy - SH_H//3 - 60
bot  = cy + SH_H//2 - 60

def bezier_points(p0, p1, p2, steps=30):
    """Quadratic bezier from p0 to p2 with control p1."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = (1-t)**2*p0[0] + 2*t*(1-t)*p1[0] + t**2*p2[0]
        y = (1-t)**2*p0[1] + 2*t*(1-t)*p1[1] + t**2*p2[1]
        pts.append((x, y))
    return pts

# Build shield polygon: flat top, straight sides, bezier curves to bottom point
def shield_poly(cx, top, mid, bot, sw):
    pts = []
    pts += [(cx - sw, top), (cx + sw, top)]        # top edge
    pts += [(cx + sw, mid)]                          # right side
    pts += bezier_points((cx + sw, mid), (cx + sw, bot + 30), (cx, bot))   # right curve
    pts += bezier_points((cx, bot), (cx - sw, bot + 30), (cx - sw, mid))   # left curve
    pts += [(cx - sw, top)]                          # close
    return pts

poly = shield_poly(cx, top, mid, bot, SH_W)

# Shadow layer (slightly larger, darker, offset)
shadow_poly = shield_poly(cx + 6, top + 8, mid + 8, bot + 8, SH_W + 4)
draw.polygon(shadow_poly, fill=(4, 12, 30))

# Shield fill — slightly lighter navy so it reads against background
draw.polygon(poly, fill=(18, 48, 100))

# Teal accent bar across top of shield
bar_y  = top
bar_h  = 22
bar_rx = 6
draw.rounded_rectangle(
    [cx - SH_W + 2, bar_y, cx + SH_W - 2, bar_y + bar_h],
    radius=bar_rx, fill=TEAL
)

# White T — horizontal bar
T_W, T_H = 100, 18
T_Y = top + bar_h + 28
draw.rounded_rectangle([cx - T_W//2, T_Y, cx + T_W//2, T_Y + T_H], radius=5, fill=WHITE)

# White T — vertical stem
S_W = 22
S_Y  = T_Y + T_H
S_BOT = bot - 50
draw.rounded_rectangle([cx - S_W//2, S_Y, cx + S_W//2, S_BOT], radius=5, fill=WHITE)

# Teal dot at shield base
dot_r = 16
draw.ellipse([cx - dot_r, S_BOT + 10, cx + dot_r, S_BOT + 10 + dot_r*2], fill=TEAL)

# Thin white border on shield
# thin white border on shield
border_poly = shield_poly(cx, top+1, mid+1, bot-1, SH_W-2)
draw.polygon(border_poly, outline=(255, 255, 255), width=2)

# ── Text: TerahBank ────────────────────────────────────────────────────────────
FONT_PATHS = [
    "C:/Windows/Fonts/Poppins-Bold.ttf",
    "C:/Windows/Fonts/seguisb.ttf",    # Segoe UI Semibold
    "C:/Windows/Fonts/segoeuib.ttf",   # Segoe UI Bold
    "C:/Windows/Fonts/arialbd.ttf",
]
FONT_SMALL_PATHS = [
    "C:/Windows/Fonts/Poppins-Regular.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
]

def load_font(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

font_main   = load_font(FONT_PATHS, 112)
font_tag    = load_font(FONT_SMALL_PATHS, 26)

TEXT_Y = bot + 55

terah_bb = draw.textbbox((0, 0), "Terah", font=font_main)
bank_bb  = draw.textbbox((0, 0), "Bank",  font=font_main)
terah_w  = terah_bb[2] - terah_bb[0]
bank_w   = bank_bb[2]  - bank_bb[0]
total_w  = terah_w + bank_w
tx       = cx - total_w // 2

draw.text((tx,            TEXT_Y), "Terah", font=font_main, fill=WHITE)
draw.text((tx + terah_w,  TEXT_Y), "Bank",  font=font_main, fill=TEAL)

# ── Tagline ────────────────────────────────────────────────────────────────────
TAGLINE    = "SAVE. GROW. THRIVE."
tg_bb      = draw.textbbox((0, 0), TAGLINE, font=font_tag)
tg_w       = tg_bb[2] - tg_bb[0]
tg_h       = tg_bb[3] - tg_bb[1]
TAG_Y      = TEXT_Y + (terah_bb[3] - terah_bb[1]) + 22
draw.text((cx - tg_w // 2, TAG_Y), TAGLINE, font=font_tag, fill=GREY)

# Teal underline
UL_W = tg_w + 20
UL_Y = TAG_Y + tg_h + 12
draw.rounded_rectangle([cx - UL_W//2, UL_Y, cx + UL_W//2, UL_Y + 4], radius=2, fill=TEAL)

# ── Save ───────────────────────────────────────────────────────────────────────
out = os.path.join(os.path.dirname(__file__),
                   "apps", "mobile", "assets", "splash.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
img.save(out, "PNG", optimize=True)
print(f"Saved {out}  ({W}×{H})")
