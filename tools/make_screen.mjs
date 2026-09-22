// 紹介ページの ヒーローに 置く 画面は、手組みの 模型では なく app/index.html の 実物。
// 局が すこし 進んだ ところ（両者 1組 公開・捨て札 5枚）で 止めて 撮る。
//
//   node tools/make_screen.mjs        → assets/screen.png（幅600px）
//
// リポジトリの 根で 走らせること。下の 余白は ログの 下端で 切る。
// 幅600pxは deviceScaleFactor で 直接 出すので、あとから 縮める 必要は ない。

import { chromium } from 'playwright';
import fs from 'node:fs';

const W = 390, OUT_W = 600;
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: W, height: 900 }, deviceScaleFactor: OUT_W / W });
await p.goto('file://' + process.cwd() + '/app/index.html');
await p.waitForTimeout(1600);

for (let i = 0; i < 60; i++) {
  if (await p.evaluate(() => !document.getElementById('modal').hidden)) break;
  const st = await p.evaluate(() => ({
    exposed: document.querySelectorAll('#youMelds .meldset').length,
    discards: +document.getElementById('discardCount').textContent.replace(/\D/g, ''),
  }));
  if (st.exposed >= 1 && st.discards >= 5) break;          // ここで止める
  const expo = await p.$('#exposebar .expbtn');
  if (expo) { await expo.click(); await p.waitForTimeout(200); continue; }
  const win = await p.$('#actions .bigbtn.win');           // 上がると局が終わるので避ける
  const cards = await p.$$('#hand button.pick');
  if (cards.length && !win) {
    const idx = await p.evaluate(() => {                   // 相棒のいない高い札から捨てる
      const cs = [...document.querySelectorAll('#hand button.pick')].map((el, i) => {
        const t = el.getAttribute('aria-label') || '', m = t.match(/の(\d+)・/);
        return { i, n: m ? +m[1] : 5, pts: /罰10/.test(t) ? 10 : (m ? +m[1] : 5), col: t.split('の')[0] };
      });
      const has = c => cs.some(o => o !== c && (o.n === c.n || (o.col === c.col && Math.abs(o.n - c.n) <= 2)));
      cs.sort((a, z) => (has(z) ? -100 : 0) + z.pts - ((has(a) ? -100 : 0) + a.pts));
      return cs[0].i;
    });
    const cc = await p.$$('#hand button.pick');
    if (cc[idx]) { await cc[idx].click(); await p.waitForTimeout(160); continue; }
  }
  const btns = await p.$$('#actions .bigbtn:not(.win)');
  if (btns.length) { await btns[0].click(); await p.waitForTimeout(150); continue; }
  await p.waitForTimeout(200);
}

const state = await p.evaluate(() => ({
  youMelds: document.querySelectorAll('#youMelds .meldset').length,
  cpuMelds: document.querySelectorAll('#cpuMelds .meldset').length,
  discard: document.getElementById('discardCount').textContent,
  bottom: Math.ceil(document.getElementById('log').getBoundingClientRect().bottom) + 10,
}));
console.log('撮影時の状態:', JSON.stringify(state));

await p.screenshot({ path: 'assets/screen.png', clip: { x: 0, y: 0, width: W, height: state.bottom } });
await b.close();

const px = Math.round(state.bottom * OUT_W / W);
console.log('assets/screen.png  ' + OUT_W + 'x' + px);
console.log('→ index.html の <img> の width/height を ' + OUT_W + ' / ' + px + ' に合わせ、');
console.log('  assets/site.css の .screen-shot img の aspect-ratio も ' + OUT_W + ' / ' + px + ' にすること。');
