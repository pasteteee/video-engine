// node render.js  -> renders brand pieces from brand.html into ../
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 2600, height: 1500 } });
  const photos = ['S66-24465','s66-25779','s66-18602','LRC-1963-B701_P-09365','S66-44886','s66-26037'].map(x=>'photos/'+x+'.jpg').join(',');
  await p.goto('file://' + path.resolve(__dirname, 'brand.html') + '?photos=' + photos); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(400);
  const out = path.resolve(__dirname, '..');
  await p.locator('#wordmark').screenshot({ path: out + '/logo_wordmark.png', omitBackground: true });
  await p.locator('#avatar').screenshot({ path: out + '/avatar_800.png' });
  await p.locator('#watermark').screenshot({ path: out + '/watermark_300.png', omitBackground: true });
  await p.locator('#banner').screenshot({ path: out + '/banner_2560x1440.jpg', type: 'jpeg', quality: 90 });
  await b.close();
})();
