#!/usr/bin/env python3
"""画像生成AIが出した 3x3 のグリッド1枚を、札の絵 img/1.png 〜 img/9.png に切り分ける。

img/PROMPT.md のプロンプトで出したグリッド画像（白背景、コマの区切りに細い黒線）を受け取り、

  1. 区切り線を自動で見つけて9コマに切り分け
  2. 外側とつながっている白を塗りつぶして透過（絵の内側の白は残す）
  3. 中身の外周で切りつめ、正方形に余白を足して 512x512 に統一

したPNGを img/ に書き出します。コマの順番は左上から右へ、上の段から。

つかいかた:

    pip install pillow numpy
    python3 tools/split_grid.py grid.png

    python3 tools/split_grid.py grid.png --out img --size 512
    python3 tools/split_grid.py grid.png --only 5      # 5番だけ描き直したとき
    python3 tools/split_grid.py grid.png --bold 5      # 線が細すぎたとき太らせる

札の中で絵が出るのは幅40pxほどしかないので、書き出しながら「実寸での黒の割合」を
表示します。20%を下回ると灰色の塊になって何か分からなくなるので、そのときは
--bold で線を太らせるか、絵を描き直してください。

札は白背景のままでも mix-blend-mode: multiply で地色に抜けるので、
透過は必須ではありません。手で9分割して 1.png〜9.png と名前を付けても動きます。

guns-germs-and-diamond の tools/make_cards.py を、このゲーム用に単純化したものです。
"""

import sys
import os
import argparse
from collections import deque

from PIL import Image, ImageFilter
import numpy as np

SIZE = 512          # 出力の一辺
STAGE = ['', '樹上のサル', '火のボノボ', '直立二足歩行', '石器', 'ゴリラ',
         '言語', '農耕', '文字と都市', '現生人類']
PAD_RATIO = 0.04    # 正方形化したあとに足す余白の比率
FULL_CLEAR = 28     # この差までは完全に透過
SOFT_CLEAR = 60     # この差までは半透明（輪郭のギザギザを抑える）


def find_lines(dark_ratio, frame_skip=8, min_ratio=0.9, max_width=0.03):
    """区切り線の位置（範囲）を拾う。

    区切り線は「その行／列のほぼ全長が暗い」細い帯。キャラクターの銃なども
    暗いが、全長は暗くならないので dark_ratio で見分けられる。
    """
    n = len(dark_ratio)
    idx = [i for i, v in enumerate(dark_ratio) if v >= min_ratio]
    groups = []
    for i in idx:
        if groups and i - groups[-1][-1] <= 2:
            groups[-1].append(i)
        else:
            groups.append([i])
    return [(g[0], g[-1]) for g in groups
            if (g[-1] - g[0] + 1) <= n * max_width
            and g[0] > frame_skip and g[-1] < n - frame_skip]


def spans(size, lines):
    """区切り線の間（＝コマ）の範囲を返す。"""
    out = []
    start = 0
    for a, b in lines:
        if a - start > size * 0.05:
            out.append((start, a))
        start = b + 1
    if size - start > size * 0.05:
        out.append((start, size))
    return out


DARK = 300  # RGB合計がこれ未満なら「暗い画素」


def cut_cells(path):
    im = Image.open(path).convert('RGB')
    arr = np.asarray(im).astype(int).sum(axis=2)
    h, w = arr.shape
    is_dark = arr < DARK
    col_spans = spans(w, find_lines(is_dark.mean(axis=0)))
    row_spans = spans(h, find_lines(is_dark.mean(axis=1)))
    cells = []
    for (y0, y1) in row_spans:
        for (x0, x1) in col_spans:
            # 区切り線と、画像のいちばん外側の枠線を確実に落とすための内側マージン
            inset_x = max(8, int((x1 - x0) * 0.015))
            inset_y = max(8, int((y1 - y0) * 0.015))
            cells.append(im.crop((x0 + inset_x, y0 + inset_y,
                                  x1 - inset_x, y1 - inset_y)))
    return cells, len(col_spans), len(row_spans)


def background_color(cell):
    """四隅の色の中央値を背景色とみなす。"""
    a = np.asarray(cell).astype(int)
    h, w, _ = a.shape
    k = max(3, min(h, w) // 40)
    corners = np.concatenate([
        a[:k, :k].reshape(-1, 3), a[:k, -k:].reshape(-1, 3),
        a[-k:, :k].reshape(-1, 3), a[-k:, -k:].reshape(-1, 3),
    ])
    return np.median(corners, axis=0)


def drop_background(cell):
    """外側とつながっている背景色だけを透過する（内側の同色は残す）。"""
    a = np.asarray(cell).astype(int)
    h, w, _ = a.shape
    bg = background_color(cell)
    dist = np.abs(a - bg).max(axis=2)          # 背景色との差
    soft = dist <= SOFT_CLEAR

    seen = np.zeros((h, w), dtype=bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if soft[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if soft[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and soft[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))

    alpha = np.full((h, w), 255, dtype=np.uint8)
    # 完全に背景の画素は透明、輪郭のきわは差に応じて半透明にする
    ramp = np.clip((dist - FULL_CLEAR) / float(SOFT_CLEAR - FULL_CLEAR), 0, 1) * 255
    alpha[seen] = ramp[seen].astype(np.uint8)

    out = np.dstack([np.asarray(cell).astype(np.uint8), alpha])
    return Image.fromarray(out, 'RGBA')


def ink_ratio(im, px=38):
    """札の中の実寸まで落としたときに、黒がどれだけ残るか。"""
    flat = Image.new('RGB', im.size, (255, 255, 255))
    flat.paste(im, (0, 0), im)
    small = flat.resize((px, px), Image.LANCZOS).convert('L')
    dark = sum(small.histogram()[:140])          # 140未満を「黒」とみなす
    return dark / float(px * px)


def square(im):
    """中身で切りつめて、透明の余白で正方形にし、512pxに揃える。"""
    bbox = im.split()[-1].point(lambda v: 255 if v > 8 else 0).getbbox()
    if bbox:
        im = im.crop(bbox)
    side = int(max(im.size) * (1 + PAD_RATIO * 2))
    canvas = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    return canvas.resize((SIZE, SIZE), Image.LANCZOS)


def main(argv):
    ap = argparse.ArgumentParser(description='グリッド画像を img/1.png〜9.png に切り分ける')
    ap.add_argument('grid', help='画像生成AIが出した 3x3 のグリッド画像')
    ap.add_argument('--out', default='img', help='書き出し先（既定: img）')
    ap.add_argument('--size', type=int, default=SIZE, help='出力の一辺（既定: 512）')
    ap.add_argument('--only', type=int, nargs='*', metavar='N',
                    help='この番号だけ書き出す（例: --only 5 9）')
    ap.add_argument('--bold', type=int, default=0, metavar='N',
                    help='線を太らせる量。細い輪郭線だけの絵を救う（3か5。既定: 0＝そのまま）')
    a = ap.parse_args(argv)

    os.makedirs(a.out, exist_ok=True)
    cells, cols, rows = cut_cells(a.grid)
    print('grid: {}列 x {}行 = {}コマ'.format(cols, rows, len(cells)))
    if len(cells) != 9:
        print('9コマに割れませんでした。区切り線がはっきりしているか、')
        print('画像のいちばん外側に枠線が入っていないかを確かめてください。')
        return 1

    want = set(a.only) if a.only else set(range(1, 10))
    for i, cell in enumerate(cells, 1):
        if i not in want:
            continue
        path = os.path.join(a.out, '{}.png'.format(i))
        if a.bold:
            cell = cell.filter(ImageFilter.MinFilter(a.bold | 1))
        im = square(drop_background(cell))
        if a.size != SIZE:
            im = im.resize((a.size, a.size), Image.LANCZOS)
        im.save(path, optimize=True)
        ink = ink_ratio(im)
        note = '  ← 薄い。--bold か描き直しを' if ink < 0.20 else ''
        print('wrote {} {}  実寸での黒 {:.0f}%{}'.format(path, STAGE[i], ink * 100, note))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
