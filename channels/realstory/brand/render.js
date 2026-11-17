// node render.js  -> renders brand pieces from brand.html into ../
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 2600, height: 1500 } });
  const photos = ['godwit_flight.jpg','S66-24465.jpg','s66-18602.jpg','s66-25779.jpg','godwit_band.jpg','s66-26037.jpg'].map(x=>'photos/'+x).join(',');
  await p.goto('file://' + path.resolve(__dirname, 'brand.html') + '?photos=' + photos); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(400);
  const out = path.resolve(__dirname, '..');
  await p.evaluate(() => { document.body.style.background = 'transparent'; });
  await p.locator('#wordmark').screenshot({ path: out + '/logo_wordmark.png', omitBackground: true });
  await p.locator('#avatar').screenshot({ path: out + '/avatar_800.png' });
  await p.locator('#watermark').screenshot({ path: out + '/watermark_300.png', omitBackground: true });
  await p.locator('#banner').screenshot({ path: out + '/banner_2560x1440.jpg', type: 'jpeg', quality: 90 });
  await p.locator('#watermark150').screenshot({ path: out + '/watermark_150.png', omitBackground: true });
  await p.locator('#endscreen').screenshot({ path: out + '/endscreen_1920x1080.png' });
  await p.goto('file://' + path.resolve(__dirname, 'brand.html') + '?photos=' + photos + '&guide'); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(300);
  await p.locator('#endscreen').screenshot({ path: out + '/previews/endscreen_guide.jpg', type: 'jpeg', quality: 85 });
  await b.close();
})();
