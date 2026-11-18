// node thumbs.js <variants.json> <outdir>  — Real Story thumbnails from thumb.html (or v.tpl, e.g. thumb_s1.html for season 1)
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
const [cfg, out] = process.argv.slice(2); const vs = JSON.parse(fs.readFileSync(cfg, 'utf8'));
(async () => { fs.mkdirSync(out, { recursive: true }); const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
  for (const v of vs) { await p.goto('file://' + path.resolve(__dirname, v.tpl || 'thumb.html') + '?v=' + encodeURIComponent(JSON.stringify(v)));
    await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(400); await p.screenshot({ path: path.join(out, v.id + '.jpg'), type: 'jpeg', quality: 92 }); console.log(v.id); }
  await b.close(); })();
