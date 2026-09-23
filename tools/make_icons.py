# -*- coding: utf-8 -*-
"""
アイコンの元絵（assets/icon-src.jpg、1024px の正方形。Gemini で描いたもの）から、
角を丸めたアイコン一式を書き出す。

つかいかた:
    python3 tools/make_icons.py

必要なもの: pillow （pip install pillow）
"""
import os

from PIL import Image, ImageDraw

SRC = 'assets/icon-src.jpg'
RADIUS = 0.22                    # 角の丸み（一辺に対する割合）
OUT = [
    ('assets/icon.png', 512),
    ('assets/favicon.png', 64),
]


def rounded(im, size):
    im = im.resize((size, size), Image.LANCZOS).convert('RGBA')
    big = size * 4
    mask = Image.new('L', (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * RADIUS), fill=255)
    im.putalpha(mask.resize((size, size), Image.LANCZOS))
    return im


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = Image.open(os.path.join(root, SRC)).convert('RGB')
    for rel, size in OUT:
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        rounded(src, size).save(path, optimize=True)
        print('wrote', rel)


if __name__ == '__main__':
    main()
