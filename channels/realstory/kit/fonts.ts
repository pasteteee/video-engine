// Import once in Root.tsx. Blocks rendering until the channel fonts are loaded.
import { staticFile, continueRender, delayRender } from 'remotion';
const h = delayRender('fonts');
const faces = [
  new FontFace('Archivo', `url(${staticFile('Archivo-wdth-wght.woff2')})`, { weight: '100 900', stretch: '62% 125%' }),
  new FontFace('Newsreader', `url(${staticFile('Newsreader-opsz-italic.woff2')})`, { weight: '200 800', style: 'italic' }),
  new FontFace('Plex', `url(${staticFile('IBMPlexMono-500.woff2')})`, { weight: '500' }),
  new FontFace('Plex', `url(${staticFile('IBMPlexMono-400.woff2')})`, { weight: '400' }),
  new FontFace('Caveat', `url(${staticFile('Caveat.ttf')})`, { weight: '400 700' }),
];
Promise.all(faces.map((f) => f.load().then(() => document.fonts.add(f)))).then(() => continueRender(h));
