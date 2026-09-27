# -*- coding: utf-8 -*-
"""
タイトルロゴ（assets/logo.png、背景を 抜いた PNG）から、アプリの アイコン一式を つくる。
シャレード三部作（銃・病原菌・ダイヤモンド／若い類人猿のための第三のゴリラ／商人・預言者・ゴリラ・王）で おなじ 図がら。

・生成りの 角丸に、テーマ色の わく。ロゴの 紋章（上）と 題名（下）を 組みなおして のせる
・小さい アイコン（64px 以下）は 題名の 文字が つぶれるので、紋章だけを 大きく
・ロゴの 紋章と 題名の さかいは、上から 見て はじめの 横の すきまで 見つける

つかいかた:
    python3 tools/make_icons.py

必要なもの: pillow, numpy （pip install pillow numpy）
"""
import os

import numpy as np
from PIL import Image, ImageDraw

LOGO = 'assets/logo.png'
RIM = (31, 39, 36)                   # わくの 色（紹介ページの テーマ色）
PAPER = (244, 239, 228)         # 生成り #f4efe4
BASE = 1024
RADIUS = 0.22                   # 角の丸み（一辺に対する割合）
SMALL = 64                      # これ いかの 大きさは 紋章だけ
OUT = [
    ('assets/icon.png', 512),
    ('assets/favicon.png', 64),
]


def split(logo):
    """ロゴを 紋章（上）と 題名（下）に 分ける"""
    a = np.asarray(logo)[:, :, 3] > 60
    rows = np.nonzero(a.sum(1))[0]
    top = rows.min()
    y = top
    while a[y].any() or a[y + 1: y + 4].any():
        y += 1
    def crop(y0, y1):
        part = logo.crop((0, y0, logo.width, y1))
        return part.crop(part.getchannel('A').point(lambda v: 255 if v > 60 else 0).getbbox())
    return crop(top, y), crop(y, rows.max() + 1)


def fit(im, w, h):
    s = min(w / im.width, h / im.height)
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)


def build(emblem, title, small):
    c = Image.new('RGBA', (BASE, BASE), PAPER + (255,))
    if small:
        e = fit(emblem, BASE * 0.86, BASE * 0.80)
        c.alpha_composite(e, ((BASE - e.width) // 2, (BASE - e.height) // 2))
    else:
        e = fit(emblem, BASE * 0.66, BASE * 0.40)
        t = fit(title, BASE * 0.88, BASE * 0.36)
        gap = int(BASE * 0.04)
        y = (BASE - (e.height + gap + t.height)) // 2
        c.alpha_composite(e, ((BASE - e.width) // 2, y))
        c.alpha_composite(t, ((BASE - t.width) // 2, y + e.height + gap))
    ImageDraw.Draw(c).rounded_rectangle([0, 0, BASE - 1, BASE - 1], radius=int(BASE * RADIUS),
                                        outline=RIM + (255,), width=int(BASE * 0.04))
    mask = Image.new('L', (BASE, BASE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, BASE - 1, BASE - 1], radius=int(BASE * RADIUS), fill=255)
    out = Image.new('RGBA', (BASE, BASE), (0, 0, 0, 0))
    out.paste(c, (0, 0), mask)
    return out


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo = Image.open(os.path.join(root, LOGO)).convert('RGBA')
    emblem, title = split(logo)
    big, small = build(emblem, title, False), build(emblem, title, True)
    for rel, size in OUT:
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        (small if size <= SMALL else big).resize((size, size), Image.LANCZOS).save(path, optimize=True)
        print('wrote', rel)


if __name__ == '__main__':
    main()
