// node stills.mjs <slug> <outdir> : one still per shot at 75% of its duration, then a contact sheet via ffmpeg.
import { bundle } from '@remotion/bundler';
import { renderStill, selectComposition } from '@remotion/renderer';
import fs from 'fs'; import path from 'path';
const [slug, out] = process.argv.slice(2);
const props = JSON.parse(fs.readFileSync(`props/${slug}.json`, 'utf8'));
const browserExecutable = process.env.REMOTION_BROWSER || null; // e.g. a local chrome-headless-shell
const serveUrl = await bundle({ entryPoint: path.resolve('src/index.ts') });
const comp = await selectComposition({ serveUrl, id: 'LoreShort', inputProps: props, browserExecutable });
fs.mkdirSync(out, { recursive: true });
const at = process.argv[4] ? Number(process.argv[4]) : 0.75;
for (const s of props.shots) {
  const frame = Math.min(comp.durationInFrames - 1, Math.round((s.from + s.dur * at) * 30));
  await renderStill({ composition: comp, serveUrl, output: `${out}/${s.id}.png`, frame, inputProps: props, browserExecutable, scale: 0.5 });
}
console.log('stills', props.shots.length);
