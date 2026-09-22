// ヒーローの画面は 手組みの模型では なく、app/index.html を 390px幅で 撮った 実物。
// 局が すこし 進んだ ところ（両者 1組 公開・捨て札 5枚）で 止めて 撮る。
//
//   npm i -g playwright   （または npx playwright）
//   node tools/make_screen.mjs      → assets/screen.png
//
// 撮ったあと、下の 余白を 切り、幅600pxに 縮めて 書き出す。

import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
const b = await chromium.launch();
const p = await b.newPage({viewport:{width:390,height:780}, deviceScaleFactor:2});
await p.goto('file://' + process.cwd() + '/app/index.html');
await p.waitForTimeout(1600);

// 局が進んだ見た目にする（捨て札が積まれ、公開組が出ている状態を狙う）
for (let i = 0; i < 60; i++) {
  if (await p.evaluate(() => !document.getElementById('modal').hidden)) break;
  const exposed = await p.evaluate(() => document.querySelectorAll('#youMelds .meldset').length);
  const discards = await p.evaluate(() => +document.getElementById('discardCount').textContent.replace(/\D/g,''));
  if (exposed >= 1 && discards >= 5) break;                 // ここで止める
  const expo = await p.$('#exposebar .expbtn');
  if (expo) { await expo.click(); await p.waitForTimeout(200); continue; }
  const win = await p.$('#actions .bigbtn.win');            // 上がると局が終わるので避ける
  const cards = await p.$$('#hand button.pick');
  if (cards.length && !win) {
    // 相棒のいない札から捨てて、組ができやすいようにする
    const idx = await p.evaluate(() => {
      const cs = [...document.querySelectorAll('#hand button.pick')].map((el,i)=>{
        const t = el.getAttribute('aria-label')||''; const m = t.match(/の(\d+)・/);
        return {i, n:m?+m[1]:5, pts:/罰10/.test(t)?10:(m?+m[1]:5), col:t.split('の')[0]};
      });
      const has = c => cs.some(o=>o!==c && (o.n===c.n || (o.col===c.col && Math.abs(o.n-c.n)<=2)));
      cs.sort((a,z)=>(has(z)?-100:0)+z.pts-((has(a)?-100:0)+a.pts));
      return cs[0].i;
    });
    const cc = await p.$$('#hand button.pick');
    if (cc[idx]) { await cc[idx].click(); await p.waitForTimeout(160); continue; }
  }
  const btns = await p.$$('#actions .bigbtn:not(.win)');
  if (btns.length) { await btns[0].click(); await p.waitForTimeout(150); continue; }
  await p.waitForTimeout(200);
}
const st = await p.evaluate(() => ({
  公開組: document.querySelectorAll('#youMelds .meldset').length,
  CPU公開: document.querySelectorAll('#cpuMelds .meldset').length,
  捨て札: document.getElementById('discardCount').textContent,
  山札: document.getElementById('deckCount').textContent,
  手の内: document.getElementById('youCount').textContent,
}));
console.log('撮影時の状態:', JSON.stringify(st));
await p.screenshot({path:'assets/screen_raw.png'});
await b.close();
