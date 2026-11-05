#!/usr/bin/env python3
"""Generate the built-in demo sticker pack.

Development tool only (needs Pillow). The committed PNG/GIF output is what the
CLI uses, so the runtime stays standard-library only. Art is original and
released under CC0-1.0; see NOTICE.

Usage: python3 tools/make_demo_pack.py
"""
from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFilter

SIZE = 512
SS = 2                      # supersampling factor
S = SIZE * SS
OUT = Path(__file__).resolve().parents[1] / 'stickers' / 'demo'

INK = (30, 41, 82, 255)
BODY_TOP = (147, 224, 255)
BODY_BOTTOM = (56, 152, 236)
BODY_EDGE = (28, 84, 148, 90)
BLUSH = (255, 138, 168, 150)
WHITE = (255, 255, 255, 255)


def p(v):
    return int(round(v * SS))


def new_canvas():
    return Image.new('RGBA', (S, S), (0, 0, 0, 0))


def gradient(top, bottom):
    image = Image.new('RGBA', (S, S))
    draw = ImageDraw.Draw(image)
    for y in range(S):
        t = y / (S - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
        draw.line([(0, y), (S, y)], fill=color)
    return image


def body(canvas, top=BODY_TOP, bottom=BODY_BOTTOM):
    mask = Image.new('L', (S, S), 0)
    md = ImageDraw.Draw(mask)
    box = [p(58), p(56), p(454), p(456)]
    md.ellipse(box, fill=255)
    fill = gradient(top, bottom)
    canvas.alpha_composite(Image.composite(fill, Image.new('RGBA', (S, S), (0, 0, 0, 0)), mask))
    glow = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([p(120), p(104), p(288), p(226)], fill=(255, 255, 255, 96))
    glow = glow.filter(ImageFilter.GaussianBlur(p(26)))
    mask2 = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask2).ellipse(box, fill=255)
    canvas.alpha_composite(Image.composite(glow, Image.new('RGBA', (S, S), (0, 0, 0, 0)), mask2))
    ImageDraw.Draw(canvas).ellipse(box, outline=BODY_EDGE, width=p(5))


def eye_open(d, cx, cy, r=27, look=(0, 0)):
    d.ellipse([p(cx - r), p(cy - r), p(cx + r), p(cy + r)], fill=INK)
    d.ellipse([p(cx + look[0] - 9), p(cy + look[1] - 13), p(cx + look[0] + 7), p(cy + look[1] + 3)], fill=WHITE)


def eye_closed(d, cx, cy, r=27):
    d.arc([p(cx - r), p(cy - r + 6), p(cx + r), p(cy + r + 6)], 200, 340, fill=INK, width=p(7))


def eye_happy(d, cx, cy, r=27):
    d.arc([p(cx - r), p(cy - r + 2), p(cx + r), p(cy + r + 2)], 190, 350, fill=INK, width=p(8))


def eye_wide(d, cx, cy, r=34):
    d.ellipse([p(cx - r), p(cy - r), p(cx + r), p(cy + r)], fill=WHITE, outline=INK, width=p(6))
    d.ellipse([p(cx - 13), p(cy - 13), p(cx + 13), p(cy + 13)], fill=INK)
    d.ellipse([p(cx - 6), p(cy - 9), p(cx + 1), p(cy - 2)], fill=WHITE)


def eye_half(d, cx, cy, r=30):
    d.pieslice([p(cx - r), p(cy - r - 4), p(cx + r), p(cy + r)], 0, 180, fill=INK)
    d.line([(p(cx - r), p(cy)), (p(cx + r), p(cy))], fill=INK, width=p(7))


def eye_heart(d, cx, cy, s=26):
    d.ellipse([p(cx - s), p(cy - s), p(cx), p(cy + s * 0.2)], fill=(235, 76, 120, 255))
    d.ellipse([p(cx), p(cy - s), p(cx + s), p(cy + s * 0.2)], fill=(235, 76, 120, 255))
    d.polygon([p(cx - s), p(cy), p(cx + s), p(cy), p(cx), p(cy + s)], fill=(235, 76, 120, 255))


def eye_cross(d, cx, cy, r=24):
    d.line([p(cx - r), p(cy - r), p(cx + r), p(cy + r)], fill=INK, width=p(8))
    d.line([p(cx - r), p(cy + r), p(cx + r), p(cy - r)], fill=INK, width=p(8))


def eye_spiral(d, cx, cy, r=28):
    steps = 46
    points = []
    for i in range(steps):
        t = i / steps
        a = t * math.pi * 3.4
        points.append((p(cx + math.cos(a) * r * t), p(cy + math.sin(a) * r * t)))
    d.line(points, fill=INK, width=p(6), joint='curve')


def mouth_smile(d, cx, cy, w=54):
    d.arc([p(cx - w), p(cy - w * 0.7), p(cx + w), p(cy + w * 0.7)], 20, 160, fill=INK, width=p(8))


def mouth_big(d, cx, cy, w=64):
    d.pieslice([p(cx - w), p(cy - w * 0.75), p(cx + w), p(cy + w * 0.95)], 10, 170, fill=INK)
    d.pieslice([p(cx - w * 0.45), p(cy + w * 0.12), p(cx + w * 0.45), p(cy + w * 0.75)], 0, 180, fill=(255, 120, 140, 255))


def mouth_frown(d, cx, cy, w=50):
    d.arc([p(cx - w), p(cy - w * 0.4), p(cx + w), p(cy + w * 1.1)], 200, 340, fill=INK, width=p(8))


def mouth_flat(d, cx, cy, w=42):
    d.line([p(cx - w), p(cy), p(cx + w), p(cy)], fill=INK, width=p(8))


def mouth_o(d, cx, cy, r=24):
    d.ellipse([p(cx - r), p(cy - r), p(cx + r), p(cy + r * 1.2)], fill=INK)
    d.ellipse([p(cx - r * 0.55), p(cy - r * 0.35), p(cx + r * 0.55), p(cy + r * 0.45)], fill=(255, 110, 130, 255))


def mouth_wavy(d, cx, cy, w=54):
    pts = []
    for i in range(9):
        t = i / 8
        pts.append((p(cx - w + 2 * w * t), p(cy + (10 if i % 2 else -10))))
    d.line(pts, fill=INK, width=p(7), joint='curve')


def mouth_cat(d, cx, cy, w=44):
    d.arc([p(cx - w), p(cy - w * 0.5), p(cx), p(cy + w * 0.4)], 0, 150, fill=INK, width=p(7))
    d.arc([p(cx), p(cy - w * 0.5), p(cx + w), p(cy + w * 0.4)], 30, 180, fill=INK, width=p(7))


def mouth_tongue(d, cx, cy, w=46):
    d.arc([p(cx - w), p(cy - w * 0.6), p(cx + w), p(cy + w * 0.8)], 20, 160, fill=INK, width=p(8))
    d.rounded_rectangle([p(cx - 14), p(cy + 10), p(cx + 14), p(cy + 44)], radius=p(14), fill=(255, 120, 140, 255))


def blush(d, y=300):
    for cx in (150, 362):
        d.ellipse([p(cx - 34), p(y - 18), p(cx + 34), p(y + 18)], fill=BLUSH)


def tear(d, cx, cy, flip=1):
    d.ellipse([p(cx - 12), p(cy), p(cx + 12), p(cy + 32)], fill=(96, 190, 255, 235))
    d.polygon([p(cx - 10), p(cy + 6), p(cx + 10), p(cy + 6), p(cx), p(cy - 18)], fill=(96, 190, 255, 235))


def sweat(d, cx=380, cy=206):
    d.ellipse([p(cx - 13), p(cy), p(cx + 13), p(cy + 30)], fill=(140, 214, 255, 230))
    d.polygon([p(cx - 11), p(cy + 6), p(cx + 11), p(cy + 6), p(cx), p(cy - 16)], fill=(140, 214, 255, 230))


def zzz(d, x=382, y=150):
    for scale, dx, dy in ((1.0, 0, 0), (0.72, 34, -34), (0.5, 62, -62)):
        w, h = 44 * scale, 34 * scale
        d.line([p(x + dx), p(y + dy), p(x + dx + w), p(y + dy)], fill=INK, width=p(7))
        d.line([p(x + dx + w), p(y + dy), p(x + dx), p(y + dy + h)], fill=INK, width=p(7))
        d.line([p(x + dx), p(y + dy + h), p(x + dx + w), p(y + dy + h)], fill=INK, width=p(7))


def star(d, cx, cy, r=22, fill=(255, 214, 102, 255)):
    d.polygon([(p(cx), p(cy - r)), (p(cx + r * 0.3), p(cy - r * 0.3)), (p(cx + r), p(cy)),
               (p(cx + r * 0.3), p(cy + r * 0.3)), (p(cx), p(cy + r)), (p(cx - r * 0.3), p(cy + r * 0.3)),
               (p(cx - r), p(cy)), (p(cx - r * 0.3), p(cy - r * 0.3))], fill=fill)


def heart(d, cx, cy, s=22, fill=(235, 76, 120, 255)):
    d.ellipse([p(cx - s), p(cy - s), p(cx), p(cy + s * 0.2)], fill=fill)
    d.ellipse([p(cx), p(cy - s), p(cx + s), p(cy + s * 0.2)], fill=fill)
    d.polygon([p(cx - s), p(cy), p(cx + s), p(cy), p(cx), p(cy + s)], fill=fill)


def cat_ears(d):
    d.polygon([p(104), p(150), p(150), p(46), p(228), p(104)], fill=BODY_BOTTOM + (255,), outline=INK[:3] + (255,))
    d.polygon([p(408), p(150), p(362), p(46), p(284), p(104)], fill=BODY_BOTTOM + (255,), outline=INK[:3] + (255,))
    d.polygon([p(128), p(136), p(156), p(78), p(198), p(112)], fill=(255, 168, 190, 255))
    d.polygon([p(384), p(136), p(356), p(78), p(314), p(112)], fill=(255, 168, 190, 255))


def hat(d):
    d.polygon([p(256), p(58), p(168), p(170), p(344), p(170)], fill=(255, 106, 130, 255), outline=INK[:3] + (255,))
    d.ellipse([p(316), p(52), p(342), p(78)], fill=(255, 214, 102, 255))


def shades(d):
    d.rounded_rectangle([p(150), p(198), p(246), p(258)], radius=p(16), fill=(24, 32, 58, 255))
    d.rounded_rectangle([p(266), p(198), p(362), p(258)], radius=p(16), fill=(24, 32, 58, 255))
    d.line([p(246), p(222), p(266), p(222)], fill=(24, 32, 58, 255), width=p(8))


def coin(d):
    d.ellipse([p(330), p(318), p(430), p(418)], fill=(255, 205, 86, 255), outline=(196, 140, 24, 255), width=p(5))
    d.ellipse([p(350), p(338), p(410), p(398)], outline=(196, 140, 24, 255), width=p(4))
    d.line([p(366), p(368), p(394), p(368)], fill=(196, 140, 24, 255), width=p(6))


def thought(d):
    for cx, cy, r in ((408, 128, 10), (432, 100, 14), (462, 64, 20)):
        d.ellipse([p(cx - r), p(cy - r), p(cx + r), p(cy + r)], fill=(255, 255, 255, 235), outline=BODY_EDGE, width=p(3))


def sun(d):
    d.ellipse([p(388), p(58), p(470), p(140)], fill=(255, 214, 102, 255))
    for i in range(8):
        a = i * math.pi / 4
        x0, y0 = p(429 + math.cos(a) * 52), p(99 + math.sin(a) * 52)
        x1, y1 = p(429 + math.cos(a) * 70), p(99 + math.sin(a) * 70)
        d.line([x0, y0, x1, y1], fill=(255, 214, 102, 255), width=p(8))


def confetti(d):
    for i, (x, y) in enumerate(((120, 110), (168, 74), (386, 104), (420, 150))):
        color = [(255, 106, 130, 255), (255, 214, 102, 255), (110, 220, 190, 255), (170, 150, 255, 255)][i]
        d.rectangle([p(x) - p(5), p(y) - p(12), p(x) + p(5), p(y) + p(12)], fill=color)


def hands(d):
    d.arc([p(96), p(292), p(196), p(392)], 20, 160, fill=INK, width=p(9))
    d.arc([p(316), p(292), p(416), p(392)], 20, 160, fill=INK, width=p(9))


def arms_open(d):
    d.arc([p(48), p(260), p(156), p(420)], 300, 80, fill=INK, width=p(10))
    d.arc([p(356), p(260), p(464), p(420)], 100, 240, fill=INK, width=p(10))


def render(spec, frame=0):
    canvas = new_canvas()
    d = ImageDraw.Draw(canvas)
    if spec.get('ears'):
        cat_ears(d)
    body(canvas)
    d = ImageDraw.Draw(canvas)
    ex, ey = 186, 244
    eyes = spec['eyes']
    if eyes == 'open':
        eye_open(d, ex, ey, look=(spec.get('look', 0), spec.get('look_y', 0)))
        eye_open(d, 326, ey, look=(spec.get('look', 0), spec.get('look_y', 0)))
    elif eyes == 'happy':
        eye_happy(d, ex, ey)
        eye_happy(d, 326, ey)
    elif eyes == 'closed':
        eye_closed(d, ex, ey)
        eye_closed(d, 326, ey)
    elif eyes == 'wide':
        eye_wide(d, ex, ey)
        eye_wide(d, 326, ey)
    elif eyes == 'half':
        eye_half(d, ex, ey)
        eye_half(d, 326, ey)
    elif eyes == 'heart':
        eye_heart(d, ex, ey)
        eye_heart(d, 326, ey)
    elif eyes == 'cross':
        eye_cross(d, ex, ey)
        eye_cross(d, 326, ey)
    elif eyes == 'spiral':
        eye_spiral(d, ex, ey)
        eye_spiral(d, 326, ey)
    elif eyes == 'wink':
        eye_happy(d, ex, ey)
        eye_open(d, 326, ey)
    elif eyes == 'blink' and frame % 2:
        eye_closed(d, ex, ey)
        eye_closed(d, 326, ey)
    else:
        eye_open(d, ex, ey)
        eye_open(d, 326, ey)

    if spec.get('brows') == 'angry':
        d.line([p(ex - 42), p(ey - 58), p(ex + 24), p(ey - 42)], fill=INK, width=p(9))
        d.line([p(326 + 42), p(ey - 58), p(326 - 24), p(ey - 42)], fill=INK, width=p(9))
    if spec.get('brows') == 'question':
        d.arc([p(ex - 40), p(ey - 76), p(ex + 34), p(ey - 26)], 200, 340, fill=INK, width=p(8))

    if spec.get('shades'):
        shades(d)
    m = spec['mouth']
    my = 348
    {'smile': mouth_smile, 'big': mouth_big, 'frown': mouth_frown, 'flat': mouth_flat,
     'o': mouth_o, 'wavy': mouth_wavy, 'cat': mouth_cat, 'tongue': mouth_tongue}[m](d, 256, my)

    if spec.get('blush'):
        blush(d)
    if spec.get('tear'):
        tear(d, 158, 300)
    if spec.get('tear2'):
        tear(d, 358, 300, flip=-1)
    if spec.get('sweat'):
        sweat(d)
    if spec.get('zzz'):
        zzz(d)
    if spec.get('stars'):
        for cx, cy, r in ((92, 160, 20), (420, 132, 24), (112, 344, 15)):
            star(d, cx, cy, r)
    if spec.get('hearts'):
        for cx, cy, s in ((110, 148, 20), (412, 168, 24), (86, 340, 15)):
            heart(d, cx, cy, s)
    if spec.get('coin'):
        coin(d)
    if spec.get('hat'):
        hat(d)
    if spec.get('sun'):
        sun(d)
    if spec.get('confetti'):
        confetti(d)
    if spec.get('thought'):
        thought(d)
    if spec.get('hands'):
        hands(d)
    if spec.get('arms'):
        arms_open(d)
    if spec.get('puff'):
        for cx, cy, r in ((80, 386, 20), (70, 350, 12), (72, 318, 8)):
            d.ellipse([p(cx - r), p(cy - r), p(cx + r), p(cy + r)], outline=(255, 255, 255, 180), width=p(4))
    return canvas.resize((SIZE, SIZE), Image.LANCZOS)


# mood -> (sticker id, drawing spec). Ids stay ASCII; mood directories carry semantics.
SPECS = {
    'happy': [
        ('happy', {'eyes': 'happy', 'mouth': 'big', 'blush': True, 'stars': True}),
        ('cheer', {'eyes': 'happy', 'mouth': 'big', 'hat': True, 'confetti': True}),
    ],
    'angry': [
        ('angry', {'eyes': 'open', 'mouth': 'frown', 'brows': 'angry', 'puff': True}),
        ('steam', {'eyes': 'cross', 'mouth': 'wavy', 'brows': 'angry', 'sweat': True}),
    ],
    'sad': [
        ('sad', {'eyes': 'open', 'mouth': 'frown', 'tear': True}),
        ('cry', {'eyes': 'closed', 'mouth': 'wavy', 'tear': True, 'tear2': True}),
    ],
    'shy': [('shy', {'eyes': 'closed', 'mouth': 'smile', 'blush': True, 'hands': True})],
    'confused': [('confused', {'eyes': 'open', 'mouth': 'wavy', 'brows': 'question', 'sweat': True})],
    'surprised': [('surprised', {'eyes': 'wide', 'mouth': 'o', 'sweat': True})],
    'sleep': [('sleep', {'eyes': 'closed', 'mouth': 'o', 'zzz': True})],
    'work': [('work', {'eyes': 'open', 'look': 0, 'look_y': 10, 'mouth': 'flat', 'sweat': True})],
    'daily': [('daily', {'eyes': 'open', 'mouth': 'smile'})],
    'like': [('like', {'eyes': 'heart', 'mouth': 'smile', 'hearts': True})],
    'fool': [('fool', {'eyes': 'wink', 'mouth': 'tongue', 'blush': True})],
    'sigh': [('sigh', {'eyes': 'half', 'mouth': 'flat', 'puff': True})],
    'see': [('see', {'eyes': 'wide', 'mouth': 'o', 'stars': True})],
    'cpu': [('cpu', {'eyes': 'spiral', 'mouth': 'wavy', 'sweat': True})],
    'morning': [('morning', {'eyes': 'happy', 'mouth': 'smile', 'sun': True})],
    'meow': [('meow', {'eyes': 'happy', 'mouth': 'cat', 'ears': True, 'blush': True})],
    'givemoney': [('givemoney', {'eyes': 'open', 'mouth': 'flat', 'coin': True})],
    'baka': [('baka', {'eyes': 'cross', 'mouth': 'tongue'})],
    'think': [('think', {'eyes': 'open', 'look': -8, 'look_y': -10, 'mouth': 'flat', 'thought': True})],
    'celebrate': [('celebrate', {'eyes': 'happy', 'mouth': 'big', 'hat': True, 'stars': True})],
    'thanks': [('thanks', {'eyes': 'happy', 'mouth': 'smile', 'hands': True, 'blush': True})],
    'sorry': [('sorry', {'eyes': 'open', 'mouth': 'frown', 'sweat': True, 'hands': True})],
    'cool': [('cool', {'eyes': 'open', 'mouth': 'smile', 'shades': True})],
    'hug': [('hug', {'eyes': 'happy', 'mouth': 'smile', 'arms': True})],
    'color': [('color', {'eyes': 'open', 'mouth': 'smile', 'confetti': True})],
}


def main():
    count = 0
    for mood, items in SPECS.items():
        directory = OUT / mood
        directory.mkdir(parents=True, exist_ok=True)
        for sticker_id, spec in items:
            target = directory / f'{sticker_id}.png'
            render(spec).save(target, optimize=True)
            count += 1
    # Two animations so `--prefer-gif` and the animated filter can be exercised.
    frames = [render({'eyes': 'blink', 'mouth': 'big', 'blush': True, 'stars': True}, i) for i in (0, 1)]
    frames[0].save(OUT / 'happy' / 'happy-blink.gif', save_all=True, append_images=frames[1:],
                   duration=[900, 120], loop=0, disposal=2, optimize=True)
    sleep_frames = [render({'eyes': 'closed', 'mouth': 'o', 'zzz': True}),
                    render({'eyes': 'half', 'mouth': 'o', 'zzz': True})]
    sleep_frames[0].save(OUT / 'sleep' / 'sleep-zzz.gif', save_all=True, append_images=sleep_frames[1:],
                         duration=[700, 700], loop=0, disposal=2, optimize=True)
    manifest = {
        'id': 'demo',
        'name': 'Demo Orb (CC0)',
        'version': '1.0.0',
        'license': 'CC0-1.0',
        'description': 'Original orb mascot stickers generated by tools/make_demo_pack.py. Replace or extend with your own packs.',
    }
    (OUT / 'manifest.json').write_text(__import__('json').dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'wrote {count + 2} stickers to {OUT}')


if __name__ == '__main__':
    main()
