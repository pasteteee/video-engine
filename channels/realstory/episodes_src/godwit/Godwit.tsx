// S1E03 Godwit: episode renderer. Reads ep/shotlist.json + ep/media.json + ep/words.json and maps every scene_type to a component.
// Palette comes from shotlist.look through kit/tokens (mudflat brown ground, rufous accent from the bird's plumage).
import React from 'react';
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { geoDistance, geoGraticule10, geoInterpolate, geoMercator, geoOrthographic, geoPath } from 'd3-geo';
import SL from './ep/shotlist.json';
import MEDIA_J from './ep/media.json';
import LINES from './ep/lines.json';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, GROUND2, MUTED, SHADOW, SIGNAL, SPRING_SOFT, TINT, io, out, rgba, rng, travel } from './kit/tokens';
import { Hairline, Kinetic, Mono, Odometer, StopBlock, Unredact } from './kit/Type';
import { Grain, HandNote, Tag, Vignette } from './kit/Brand';
import { LonLat, makeRoute, useLand } from './kit/Geo';

type Shot = { id: string; line_ids: string[]; scene_type: string; duration_s: number; params: any; variant?: string; custom?: { component: string }; media_ids?: string[]; source_line?: string; transition_in?: string; sfx?: string[] };
const FPS = 30;
const SHOTS = (SL as any).shots as Shot[];
const END_S = SHOTS[SHOTS.length - 1].params.start_s + SHOTS[SHOTS.length - 1].duration_s;
export const GW_FRAMES = Math.round(END_S * FPS);
const MEDIA = MEDIA_J as Record<string, { src: string; w: number; h: number }>;
const med = (id: string) => staticFile('ep/' + MEDIA[id].src);
const durF = (s: Shot) => Math.round(s.duration_s * FPS);
const ACC = ACCENT_EP;
const SEA = '#211810', LANDC = '#4b3b2b', LANDS = rgba(TINT, 0.55);

// ---------- route (approximate, rebuilt from published waypoints) ----------
const PTS: LonLat[] = [[-162.3, 60.4], [-168.5, 54.2], [-171, 45], [-171.5, 33], [-167.5, 22], [-172.5, 10], [-178.5, 0],
  [170.5, -12], [168.2, -16.5], [165.6, -21.5], [160.2, -29], [157.8, -34], [156.4, -41.4], [148.35, -41.05]];
const R = makeRoute(PTS);
const PLACE: Record<string, LonLat> = { kusko: [-162.3, 60.4], aleut: [-168.5, 54.2], hawaii: [-157.8, 20.8], kiribati: [-178.5, 0], vanuatu: [168.2, -16.5],
  newcal: [165.6, -21.5], sydney: [151.21, -33.87], offSydney: [157.8, -34], turn: [156.4, -41.4], nz: [172.5, -41.4], ansons: [148.35, -41.05] };
const NAMES: Record<string, string> = { hawaii: 'HAWAII', sydney: 'SYDNEY', nz: 'NEW ZEALAND', kiribati: 'KIRIBATI', vanuatu: 'VANUATU', newcal: 'NEW CALEDONIA' };
const fracOf = (c: LonLat) => { let best = 0, bd = 9; for (let k = 0; k <= 1000; k++) { const d = geoDistance(R.along(k / 1000), c); if (d < bd) { bd = d; best = k / 1000; } } return best; };
const FR = Object.fromEntries(Object.entries(PLACE).map(([k, v]) => [k, fracOf(v)])) as Record<string, number>;
const heading = (f: number) => { const a = R.along(Math.max(0, f - 0.004)), b = R.along(Math.min(1, f + 0.004)); return [b[0] - a[0], b[1] - a[1]]; };

const CHAPTERS: Record<string, [number, string] | null> = { cold: null, chick: [1, 'THE CHICK'], fuel: [2, 'FUEL'], wind: [3, 'THE WIND'], crossing: [4, 'THE CROSSING'], turn: [5, 'THE TURN'], record: [6, 'THE RECORD'] };
const chapterOf = (s: Shot) => CHAPTERS[(LINES as any[]).find((l) => l.id === s.line_ids[0])?.chapter ?? 'cold'];

// ---------- shared pieces ----------
const Ground: React.FC<{ children?: React.ReactNode; at?: string; style?: React.CSSProperties }> = ({ children, at = '50% 42%', style }) =>
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at ${at}, ${GROUND2} 0%, ${GROUND} 75%)`, ...style }}>{children}</AbsoluteFill>;
const Shade: React.FC<{ top?: number; bottom?: number; left?: number }> = ({ top = 0.3, bottom = 0.8, left = 0 }) =>
  <AbsoluteFill style={{ background: `linear-gradient(180deg, ${rgba(GROUND, top)} 0%, ${rgba(GROUND, 0)} 24%, ${rgba(GROUND, 0)} 55%, ${rgba(GROUND, bottom)} 100%)${left ? `, linear-gradient(90deg, ${rgba(GROUND, left)} 0%, ${rgba(GROUND, 0)} 55%)` : ''}` }} />;
const Label: React.FC<{ text: string; f0: number; x?: number; y?: number; size?: number; color?: string; red?: boolean }> = ({ text, f0, x = 96, y = 820, size = 78, color = BONE, red }) => {
  const f = useCurrentFrame(); const p = spring({ frame: f - f0, fps: FPS, config: SPRING_SOFT }); if (f < f0 || !text) return null;
  const words = text.split(' ');
  return <div style={{ position: 'absolute', left: x, top: y, display: 'flex', gap: size * 0.22, flexWrap: 'wrap', width: 1500 }}>
    {words.map((w, i) => { const q = spring({ frame: f - f0 - i * 3, fps: FPS, config: SPRING_SOFT });
      return <span key={i} style={{ display: 'inline-block', overflow: 'hidden', height: size * 1.02 }}><span style={{ display: 'inline-block', ...DISP(size, 100 - 36 * q, 820), lineHeight: `${size}px`, color: i === words.length - 1 && red ? ACC : color, transform: `translateY(${(1 - q) * 105}%)`, textShadow: SHADOW }}>{w}</span></span>; })}
    {red ? <StopBlock size={size} p={Math.min(1, p)} /> : null}
  </div>;
};
const cover = (iw: number, ih: number, bw: number, bh: number) => { const s = Math.max(bw / iw, bh / ih); return { s, w: iw * s, h: ih * s }; };
// Camera into an image: centre (fractions) and zoom, clamped to the image.
const ImageCam: React.FC<{ id: string; from: number[]; to: number[]; dur: number; filter?: string; children?: (map: (x: number, y: number) => [number, number]) => React.ReactNode }> = ({ id, from, to, dur, filter, children }) => {
  const f = useCurrentFrame(); const W = 1920, H = 1080; const m = MEDIA[id];
  const p = interpolate(f, [0, dur], [0, 1], { ...C, easing: io });
  const cx = from[0] + (to[0] - from[0]) * p, cy = from[1] + (to[1] - from[1]) * p, z = from[2] * Math.pow(to[2] / from[2], p);
  const cv = cover(m.w, m.h, W, H);
  const px = Math.min(Math.max(cx * cv.w, W / 2 / z), cv.w - W / 2 / z), py = Math.min(Math.max(cy * cv.h, H / 2 / z), cv.h - H / 2 / z);
  const map = (x: number, y: number): [number, number] => [W / 2 + (x * cv.w - px) * z, H / 2 + (y * cv.h - py) * z];
  return <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: GROUND }}>
    <Img src={med(id)} style={{ position: 'absolute', left: 0, top: 0, width: cv.w, height: cv.h, transformOrigin: '0 0', transform: `translate(${W / 2}px, ${H / 2}px) scale(${z}) translate(${-px}px, ${-py}px)`, filter }} />
    {children ? children(map) : null}
  </AbsoluteFill>;
};
const Ring: React.FC<{ x: number; y: number; r: number; f0: number }> = ({ x, y, r, f0 }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [f0, f0 + 24], [0, 1], { ...C, easing: io });
  return <svg width={1920} height={1080} style={{ position: 'absolute', filter: 'drop-shadow(0 0 8px rgba(0,0,0,0.6))' }}>
    <ellipse cx={x} cy={y} rx={r * 1.12} ry={r} fill="none" stroke={ACC} strokeWidth={5} strokeLinecap="round" strokeDasharray={`${2 * Math.PI * r * 1.1 * p * 1.05} 4000`} transform={`rotate(-100 ${x} ${y})`} /></svg>;
};
const Dust: React.FC = () => { const f = useCurrentFrame(); return <svg width={1920} height={1080} style={{ position: 'absolute' }}>{DUST.map((d, i) => { const x = (d.x + f * d.z * 0.8 + 7680) % 1920; const y = (d.y - f * d.z * 0.3 + Math.sin(f / 30 + d.ph) * 6 + 4320) % 1080; return <circle key={i} cx={x} cy={y} r={d.z * 1.6} fill={`rgba(255,236,210,${d.a})`} />; })}</svg>; };
const DUST = (() => { const r = rng(7); return Array.from({ length: 60 }, () => ({ x: r() * 1920, y: r() * 1080, z: 0.3 + r() * 1.4, a: 0.04 + r() * 0.18, ph: r() * 6 })); })();
const GRADE = 'sepia(0.22) saturate(0.85) contrast(1.05) brightness(0.95)';
const VGRADE = 'sepia(0.4) saturate(0.7) hue-rotate(-8deg) contrast(1.06) brightness(0.92)';

// ---------- archival ----------
const FilmClip: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const v = s.variant ?? 'full_frame';
  const z = 1.04 + 0.06 * interpolate(f, [0, d], [0, 1], C);
  const flick = v === 'projector_flicker' ? 0.94 + 0.06 * Math.sin(f * 2.3) * Math.sin(f * 0.7) : 1;
  const weave = v === 'projector_flicker' ? Math.sin(f * 1.7) * 2 : 0;
  const vid = (style: React.CSSProperties, extra = 0) => <OffthreadVideo src={med(s.media_ids![0])} startFrom={Math.round((s.params.trim + extra) * FPS)} muted style={{ width: '100%', height: '100%', objectFit: 'cover', filter: VGRADE, ...style }} />;
  return <AbsoluteFill style={{ backgroundColor: GROUND }}>
    {v === 'split_reel'
      ? <><div style={{ position: 'absolute', left: 0, top: 0, width: 955, height: 1080, overflow: 'hidden' }}>{vid({ transform: `scale(${z * 1.2})` })}</div>
        <div style={{ position: 'absolute', left: 965, top: 0, width: 955, height: 1080, overflow: 'hidden' }}>{vid({ transform: `scale(${z * 1.5}) translateX(-8%)` }, 9)}</div></>
      : <AbsoluteFill style={{ transform: `scale(${z}) translateY(${weave}px)`, opacity: flick }}>{vid({})}</AbsoluteFill>}
    <Shade />
    {s.params.tag ? <Label text={s.params.tag} f0={10} y={860} size={56} /> : null}
  </AbsoluteFill>;
};
const StockBroll: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s);
  return <AbsoluteFill style={{ backgroundColor: GROUND }}>
    <AbsoluteFill style={{ transform: `scale(${1.15 - 0.08 * interpolate(f, [0, d], [0, 1], C)}) rotate(${interpolate(f, [0, d], [-1.5, 0], C)}deg)` }}>
      <OffthreadVideo src={med(s.media_ids![0])} startFrom={Math.round(s.params.trim * FPS)} muted style={{ width: '100%', height: '100%', objectFit: 'cover', filter: VGRADE }} /></AbsoluteFill>
    <Shade bottom={0.6} />
    <div style={{ position: 'absolute', left: 96, top: 400 }}><Odo text={s.params.label} f0={8} /></div>
  </AbsoluteFill>;
};
// date typed in big mono-like display
const Odo: React.FC<{ text: string; f0: number }> = ({ text, f0 }) => { const f = useCurrentFrame(); const n = Math.floor(interpolate(f, [f0, f0 + text.length * 2], [0, text.length], C));
  return <div style={{ ...DISP(200, 70, 860), color: BONE, textShadow: SHADOW }}>{text.slice(0, n)}<span style={{ color: ACC, opacity: n < text.length ? 1 : 0 }}>▍</span></div>; };

const FilmFreeze: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const fr = Math.round(d * 0.35);
  const frozen = f >= fr; const p = interpolate(f, [fr, fr + 30], [0, 1], { ...C, easing: io });
  const pts = Array.from({ length: 40 }, (_, i) => [300 + i * 34, 640 - 180 * Math.sin(i / 7) + 30 * Math.sin(i * 1.3)]);
  const shown = pts.slice(0, Math.max(2, Math.round(pts.length * p)));
  return <AbsoluteFill style={{ backgroundColor: GROUND }}>
    <AbsoluteFill style={{ transform: `scale(${1.08})`, filter: frozen ? 'grayscale(0.6) brightness(0.7)' : undefined }}>
      <OffthreadVideo src={med(s.media_ids![0])} startFrom={Math.round(s.params.trim * FPS)} muted style={{ width: '100%', height: '100%', objectFit: 'cover', filter: VGRADE }} playbackRate={frozen ? 0.0001 : 1} /></AbsoluteFill>
    {frozen ? <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <polyline points={shown.map((q) => q.join(',')).join(' ')} fill="none" stroke={BONE} strokeWidth={4} strokeDasharray="14 12" opacity={0.85} />
      {shown.length > 2 ? <circle cx={shown[shown.length - 1][0]} cy={shown[shown.length - 1][1]} r={10} fill={ACC} /> : null}</svg> : null}
    <Shade />
    {frozen ? <Label text={s.params.note} f0={fr + 12} y={170} size={70} red /> : null}
  </AbsoluteFill>;
};

const PhotoParallax: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const p = interpolate(f, [0, d], [0, 1], { ...C, easing: io }); const v = s.variant ?? 'push_in';
  const tr = v === 'lateral_drift' ? `scale(1.14) translateX(${-40 + 80 * p}px)` : v === 'rack_focus' ? `scale(${1.1 + 0.04 * p})` : `scale(${1.04 + 0.12 * p}) translateY(${-10 * p}px)`;
  const blur = v === 'rack_focus' ? interpolate(f, [0, 24], [8, 0], C) : 0;
  return <AbsoluteFill style={{ backgroundColor: GROUND, overflow: 'hidden' }}>
    <AbsoluteFill style={{ transform: tr }}><Img src={med(s.media_ids![0])} style={{ width: '100%', height: '100%', objectFit: 'cover', filter: `${GRADE} blur(${blur}px)` }} /></AbsoluteFill>
    <Dust />
    <AbsoluteFill style={{ background: `linear-gradient(${100 + 40 * p}deg, rgba(255,220,170,0) 30%, rgba(255,220,170,0.08) 50%, rgba(255,220,170,0) 70%)`, mixBlendMode: 'screen' }} />
    <Shade bottom={0.85} />
    <Label text={s.params.label} f0={10} y={820} size={78} />
  </AbsoluteFill>;
};
const PhotoDetail: React.FC<{ s: Shot }> = ({ s }) => {
  const d = durF(s); const P = s.params; const v = s.variant; const f = useCurrentFrame();
  return <AbsoluteFill>
    <ImageCam id={s.media_ids![0]} from={P.fr} to={P.to} dur={d} filter={GRADE}>{(map) => <>
      {P.circle ? (() => { const [x, y] = map(P.circle[0], P.circle[1]); const f0 = Math.round(d * 0.4); return <><Ring x={x} y={y} r={v === 'magnifier' ? 170 : 120} f0={f0} />
        {P.hand ? <HandNote lines={[P.hand]} x={Math.min(1350, x + 150)} y={Math.max(120, y - 230)} f0={f0 + 16} size={72} color={ACC} /> : null}</>; })() : null}
      {v === 'crop_marks' ? <svg width={1920} height={1080} style={{ position: 'absolute' }}>{[[560, 240], [1360, 240], [560, 840], [1360, 840]].map(([x, y], i) => { const q = interpolate(f, [8 + i * 3, 24 + i * 3], [0, 1], { ...C, easing: out }); const sx = x < 960 ? 1 : -1, sy = y < 540 ? 1 : -1;
        return <path key={i} d={`M${x} ${y + sy * 60 * q} L${x} ${y} L${x + sx * 60 * q} ${y}`} stroke={BONE} strokeWidth={3} fill="none" opacity={0.85} />; })}</svg> : null}
    </>}</ImageCam>
    <Shade />
  </AbsoluteFill>;
};
const PhotoLighttable: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const ids = s.media_ids!; const multi = ids.length > 1;
  const z = 1 + 0.06 * interpolate(f, [0, d], [0, 1], { ...C, easing: io });
  return <Ground>
    <Img src={med(ids[0])} style={{ position: 'absolute', inset: -60, width: 2040, height: 1200, objectFit: 'cover', filter: 'blur(30px) brightness(0.32) saturate(0.7)' }} />
    {ids.map((id, i) => { const m = MEDIA[id]; const p = spring({ frame: f - 2 - i * 7, fps: FPS, config: { damping: 20, stiffness: 90 } });
      const h = multi ? 560 : 820; const w = Math.min(multi ? 520 : 1100, (h * m.w) / m.h); const x = multi ? 760 + i * 380 - w / 2 : 1840 - w; const y = multi ? 170 + (i % 2) * 90 : 130;
      return <div key={id} style={{ position: 'absolute', left: x, top: y, width: w, height: h, transform: `translateX(${(1 - p) * 500}px) rotate(${(1 - p) * 6 + (i - 1) * 2.4}deg) scale(${z})`, opacity: Math.min(1, p * 2), boxShadow: '0 30px 80px rgba(0,0,0,0.65)' }}>
        <Img src={med(id)} style={{ width: '100%', height: '100%', objectFit: 'cover', filter: GRADE }} /></div>; })}
    <Label text={s.params.label} f0={14} x={96} y={multi ? 820 : 760} size={multi ? 76 : 64} />
  </Ground>;
};
const PhotoCompare: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const ids = s.media_ids!;
  return <Ground>{ids.map((id, i) => { const p = spring({ frame: f - i * 10, fps: FPS, config: { damping: 18, stiffness: 110 } }); const zz = interpolate(f, [0, d], [1, 1.08], C);
    return <div key={id} style={{ position: 'absolute', left: i === 0 ? 96 : 980, top: 150, width: 844, height: 600, overflow: 'hidden', transform: `translateY(${(1 - p) * 80}px)`, opacity: Math.min(1, p * 2), boxShadow: '0 30px 80px rgba(0,0,0,0.55)' }}>
      <Img src={med(id)} style={{ width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${zz})`, filter: GRADE }} />
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 200, background: `linear-gradient(180deg, ${rgba(GROUND, 0)}, ${rgba(GROUND, 0.85)})` }} /></div>; })}
    {ids.map((_, i) => { const t = s.params.labels[i].split(' · '); return <div key={i} style={{ position: 'absolute', left: i === 0 ? 96 : 980, top: 790 }}>
      <Label text={t[0]} f0={14 + i * 10} x={0} y={0} size={78} color={i === 1 ? ACC : BONE} />
      <Mono text={t[1] ?? ''} f0={26 + i * 10} size={26} color={MUTED} style={{ position: 'absolute', top: 100, left: 0 }} /></div>; })}
  </Ground>;
};
const SatelliteReveal: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const v = s.variant ?? 'orbit_dive';
  const tiles = v === 'tile_assemble';
  return <AbsoluteFill style={{ backgroundColor: GROUND }}>
    <ImageCam id={s.media_ids![0]} from={[P.fr[0], P.fr[1], P.fr[2] * 1.0]} to={P.to} dur={d} filter="saturate(0.75) sepia(0.2) contrast(1.08)" />
    {tiles ? <svg width={1920} height={1080} style={{ position: 'absolute' }}>{Array.from({ length: 48 }, (_, i) => { const x = (i % 8) * 240, y = Math.floor(i / 8) * 180; const o = interpolate(f, [2 + ((i * 7) % 23), 14 + ((i * 7) % 23)], [1, 0], C); return <rect key={i} x={x} y={y} width={241} height={181} fill={GROUND} opacity={o} />; })}</svg>
      : <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 50%, rgba(0,0,0,0) ${interpolate(f, [0, 30], [0, 70], C)}%, ${GROUND} ${interpolate(f, [0, 30], [8, 95], C)}%)` }} />}
    <Shade />
    <svg width={1920} height={1080} style={{ position: 'absolute' }}><circle cx={960} cy={540} r={interpolate(f, [20, 50], [0, 26], { ...C, easing: out })} fill="none" stroke={ACC} strokeWidth={3} /><line x1={960} y1={540} x2={960 + 140 * interpolate(f, [34, 56], [0, 1], C)} y2={540 - 140 * interpolate(f, [34, 56], [0, 1], C)} stroke={ACC} strokeWidth={2} /></svg>
    <Label text={P.label} f0={40} x={96} y={830} size={72} />
  </AbsoluteFill>;
};

// ---------- blueprint ----------
const KineticType: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const words: string[] = s.params.words; const n = words.length; const d = durF(s);
  const red = s.params.red; const v = s.variant ?? 'rise_narrow';
  const longest = Math.max(...words.map((w) => w.length));
  const lines: string[][] = n <= 3 ? words.map((w) => [w]) : [words.slice(0, Math.ceil(n / 2)), words.slice(Math.ceil(n / 2))];
  const maxLine = Math.max(...lines.map((l) => l.join(' ').length));
  const size = Math.min(n <= 3 ? 230 : 200, Math.floor(1650 / (maxLine * 0.5)), longest > 9 ? 190 : 260);
  let acc: [number, number] = [0, 0]; { let k = 0; lines.forEach((l, li) => l.forEach((_, wi) => { if (k++ === red) acc = [li, wi]; })); }
  const top = 540 - (lines.length * size * 0.98) / 2;
  const step = Math.max(3, Math.min(8, Math.round((d * 0.35) / n)));
  if (v === 'type_on') {
    const text = words.join(' '); const k = Math.floor(interpolate(f, [4, 4 + text.length * 1.5], [0, text.length], C));
    return <Ground style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}><div style={{ position: 'absolute', left: 140, right: 140, top: 380, ...DISP(170, 70, 840), color: BONE, textShadow: SHADOW }}>{text.slice(0, k)}<span style={{ color: ACC }}>▍</span></div></Ground>;
  }
  return <Ground style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})` }}>
    <Kinetic lines={lines} top={top} size={size} f0={4} step={step} variant={v} accent={acc} exitAt={d - 8} />
  </Ground>;
};
const ChapterCard: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const big = s.variant === 'big_index';
  if (P.end) return <AbsoluteFill style={{ backgroundColor: GROUND }}>
    <Unredact lines={['REAL STORY']} top={360} size={190} f0={8} />
    <Mono text="REAL STORIES, SHOWN WITH THE REAL RECORDS" f0={40} size={26} color={MUTED} style={{ position: 'absolute', left: 0, right: 0, top: 600, textAlign: 'center' }} />
    <Mono text="SOURCES IN THE DESCRIPTION" f0={58} size={20} color={rgba(BONE, 0.55)} weight={400} style={{ position: 'absolute', left: 0, right: 0, top: 650, textAlign: 'center' }} />
  </AbsoluteFill>;
  const hp = interpolate(f, [8, 24], [0, 1], { ...C, easing: (t) => 1 - Math.pow(1 - t, 4) });
  return <Ground style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    {big ? <div style={{ position: 'absolute', right: 140, top: 120, ...DISP(560, 62, 880), color: rgba(ACC, 0.18 * hp), lineHeight: 1 }}>{String(P.n).padStart(2, '0')}</div> : null}
    <Mono text={String(P.n).padStart(2, '0') + ' / 06'} f0={2} size={30} color={ACC} style={{ position: 'absolute', left: 214, top: 370 }} />
    <div style={{ position: 'absolute', left: 210, top: 430, height: 230, overflow: 'hidden' }}>
      <div style={{ ...DISP(230), color: BONE, transform: `translateY(${(1 - hp) * 100}%)`, lineHeight: '230px', whiteSpace: 'nowrap' }}>{P.title}</div></div>
    <Hairline x={214} y={676} w={1400} f0={4} dur={26} />
  </Ground>;
};
const QuestionCard: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const q: string[] = s.params.q; const d = durF(s); const v = s.variant;
  const size = Math.min(190, Math.floor(1600 / (Math.max(...q.map((x) => x.length)) * 0.5)));
  const top = 540 - (q.length * size * 0.98) / 2 - 40;
  return <Ground style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})` }}>
    {v === 'unredact' ? <Unredact lines={q} top={top} size={size} f0={6} step={10} x={200} exitAt={d - 8} />
      : <Kinetic lines={q.map((l) => l.split(' '))} top={top} size={size} f0={4} step={5} variant="rise_narrow" accent={[q.length - 1, q[q.length - 1].split(' ').length - 1]} x={200} exitAt={d - 8} />}
    {v === 'hold_cursor' ? <div style={{ position: 'absolute', left: 200 + 40, top: top + q.length * size * 0.98 + 10, width: 26, height: 8, background: ACC, opacity: Math.floor(f / 12) % 2 }} /> : null}
    <Mono text={s.params.sub} f0={40} size={28} color={MUTED} style={{ position: 'absolute', left: 204, top: top + q.length * size * 0.98 + 50 }} />
  </Ground>;
};
const BigNumber: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const v = s.variant;
  const up = interpolate(f, [26, 40], [0, 1], { ...C, easing: out });
  const fill = interpolate(f, [6, 46], [0, 1], { ...C, easing: io });
  return <Ground style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})` }}>
    <Mono text={P.label} f0={2} size={30} color={MUTED} style={{ position: 'absolute', left: 214, top: 250 }} />
    <div style={{ position: 'absolute', left: 206, top: 320, display: 'flex', alignItems: 'flex-end', gap: 36 }}>
      {v === 'unredact' ? <Unredact lines={['≈' + P.value]} top={0} size={400} f0={6} x={0} stop={false} />
        : v === 'fill_count' ? <span style={{ ...DISP(400, 62, 880), color: BONE, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>{Math.round(P.value * fill)}</span>
          : <Odometer value={P.value} size={400} f0={6} />}
      <div style={{ ...DISP(150, 62, 840), color: ACC, opacity: up, transform: `translateY(${(1 - up) * 30}px)`, marginBottom: 6, marginLeft: v === 'unredact' ? 520 : 0 }}>{P.unit}</div>
    </div>
    <Hairline x={214} y={704} w={1100} f0={30} />
    <Mono text={P.note} f0={44} size={28} color={BONE} style={{ position: 'absolute', left: 214, top: 736 }} />
  </Ground>;
};
const CounterTicker: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const total = P.days * 24 + P.hours;
  const p = interpolate(f, [6, Math.max(30, d - 24)], [0, 1], { ...C, easing: io }); const h = Math.round(total * p);
  const dd = Math.floor(h / 24), hh = h % 24; const dial = s.variant === 'clock_dial';
  return <Ground style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <Mono text={P.label} f0={2} size={30} color={MUTED} style={{ position: 'absolute', left: 214, top: 250 }} />
    <div style={{ position: 'absolute', left: 206, top: 320, ...DISP(330, 62, 880), color: BONE, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
      {String(dd).padStart(2, '0')}<span style={{ color: ACC, fontSize: 150 }}> DAYS </span>{String(hh).padStart(2, '0')}<span style={{ color: ACC, fontSize: 150 }}> H</span></div>
    {dial ? <svg width={1920} height={1080} style={{ position: 'absolute' }}><circle cx={1560} cy={300} r={120} fill="none" stroke={rgba(TINT, 0.35)} strokeWidth={3} />
      <line x1={1560} y1={300} x2={1560 + 110 * Math.sin(h / 24 * 2 * Math.PI)} y2={300 - 110 * Math.cos(h / 24 * 2 * Math.PI)} stroke={ACC} strokeWidth={6} strokeLinecap="round" /><circle cx={1560} cy={300} r={8} fill={ACC} /></svg>
      : <svg width={1920} height={1080} style={{ position: 'absolute' }}>{Array.from({ length: 12 }, (_, i) => <rect key={i} x={214 + i * 118} y={690} width={100} height={14} fill={i < Math.ceil(p * 11.04) ? ACC : rgba(TINT, 0.25)} />)}</svg>}
    <Mono text={P.note} f0={30} size={30} color={BONE} style={{ position: 'absolute', left: 214, top: 740 }} />
  </Ground>;
};
const ChartBars: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const bars: [string, number, number][] = P.bars;
  const top = 540 - bars.length * 90; const d = durF(s);
  return <Ground style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.08], { ...C, easing: io })}) translateX(${interpolate(f, [0, d], [0, -30], C)}px)`, transformOrigin: '30% 50%' }}>
    <Mono text="LONGEST TRACKED NONSTOP FLIGHTS · KM" f0={2} size={26} color={MUTED} style={{ position: 'absolute', left: 140, top: top - 80 }} />
    {bars.map(([lab, val, hero], i) => { const p = interpolate(f, [8 + i * 12, 50 + i * 12], [0, 1], { ...C, easing: io }); const w = 1300 * (val / P.max) * p;
      return <div key={i} style={{ position: 'absolute', left: 140, top: top + i * 180 }}>
        <Mono text={lab} f0={4 + i * 12} size={26} color={hero ? ACC : BONE} />
        <div style={{ marginTop: 14, height: 64, width: w, background: hero ? ACC : rgba(TINT, 0.55), boxShadow: hero ? `0 0 ${20 + 14 * Math.sin(f / 8)}px ${rgba(ACC, 0.5)}` : undefined }} />
        <div style={{ position: 'absolute', left: w + 24, top: 34, ...DISP(84, 62, 860), color: hero ? ACC : BONE, textShadow: SHADOW }}>{Math.round(val * p).toLocaleString('en-US')}</div>
      </div>; })}
  </Ground>;
};
// Fuel diagram: the body weight as one bar; the fat share grows to more than half.
const DiagramBuild: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const draw = interpolate(f, [2, 24], [0, 1], { ...C, easing: io });
  const fat = interpolate(f, [24, d - 24], [0.12, 0.55], { ...C, easing: io }); const W0 = 1500;
  return <Ground style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <Mono text="BODY WEIGHT OF AN ADULT GODWIT BEFORE DEPARTURE" f0={2} size={26} color={MUTED} style={{ position: 'absolute', left: 210, top: 300 }} />
    <div style={{ position: 'absolute', left: 210, top: 360, width: W0 * draw, height: 150, background: rgba(TINT, 0.22) }} />
    <div style={{ position: 'absolute', left: 210, top: 360, width: W0 * fat * draw, height: 150, background: ACC }} />
    <div style={{ position: 'absolute', left: 210 + W0 * 0.5, top: 330, width: 3, height: 210, background: BONE, opacity: draw }} />
    <Mono text="HALF" f0={20} size={22} color={BONE} style={{ position: 'absolute', left: 210 + W0 * 0.5 + 12, top: 520 }} />
    <div style={{ position: 'absolute', left: 210, top: 580, display: 'flex', alignItems: 'flex-end', gap: 24 }}>
      <span style={{ ...DISP(220, 62, 880), color: ACC, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW }}>{Math.round(fat * 100)}%</span>
      <span style={{ ...DISP(110, 62, 840), color: BONE, marginBottom: 14 }}>FAT</span></div>
    <Mono text="SCHEMATIC · GILL ET AL. 2009" f0={30} size={20} color={MUTED} style={{ position: 'absolute', left: 214, top: 840 }} />
  </Ground>;
};
const OrganShift: React.FC<{ s: Shot }> = ({ s }) => null;
const TimelineScroll: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const ev: string[][] = P.events;
  const gap = 640; const cam = interpolate(f, [8, d - 30], [0, (ev.length - 1) * gap], { ...C, easing: io }); const x0 = 300;
  return <Ground>
    <div style={{ position: 'absolute', left: 0, top: 0, width: 4000, height: 1080, transform: `translateX(${-cam}px)` }}>
      <svg width={4000} height={1080} style={{ position: 'absolute' }}><line x1={0} y1={560} x2={4000} y2={560} stroke={rgba(TINT, 0.4)} strokeWidth={2} /><line x1={0} y1={560} x2={x0 + cam + 300} y2={560} stroke={ACC} strokeWidth={5} /></svg>
      {ev.map((e, i) => { const x = x0 + i * gap; const hl = i === P.hl; const p = spring({ frame: f - (8 + i * ((d - 30) / Math.max(1, ev.length - 1)) * 0.7), fps: FPS, config: SPRING_SOFT });
        return <div key={i} style={{ position: 'absolute', left: x - 14, top: 546 }}>
          <div style={{ width: 22, height: 22, marginLeft: 7, marginTop: 7, background: ACC, transform: `scale(${p})` }} />
          <div style={{ position: 'absolute', left: 0, top: -120, fontFamily: FONT.mono, fontSize: 36, letterSpacing: 4, color: hl ? ACC : BONE, whiteSpace: 'nowrap', opacity: p }}>{e[0]}</div>
          <div style={{ position: 'absolute', left: 0, top: 70, ...DISP(hl ? 96 : 68), color: BONE, textShadow: SHADOW, width: 560, opacity: p, transform: `translateY(${(1 - p) * 30}px)` }}>{e[1]}</div>
        </div>; })}
    </div>
    <Mono text="APPROXIMATE TIMING · USGS" f0={20} size={20} color={MUTED} style={{ position: 'absolute', left: 140, top: 140 }} />
  </Ground>;
};
const SplitScreen: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s);
  const half = (t: string[], x: number, i: number, yes: boolean) => { const p = spring({ frame: f - 4 - i * 14, fps: FPS, config: SPRING_SOFT });
    return <div style={{ position: 'absolute', left: x, top: 330, opacity: p, transform: `translateY(${(1 - p) * 40}px)` }}>
      <div style={{ ...DISP(150), color: BONE, textShadow: SHADOW }}>{t[0]}</div>
      <div style={{ marginTop: 40, ...DISP(70, 80, 700), color: yes ? ACC : MUTED }}>{t[1]}</div></div>; };
  return <Ground style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    {half(P.a, 160, 0, true)}{half(P.b, 1010, 1, false)}
    <div style={{ position: 'absolute', left: 958, top: 260, width: 3, height: 460 * interpolate(f, [2, 20], [0, 1], C), background: rgba(TINT, 0.5) }} />
  </Ground>;
};

// ---------- geo ----------
const GlobeRoute: React.FC<{ s: Shot; land: any }> = ({ s, land }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const v = s.variant;
  const p = interpolate(f, [10, d - 16], [P.a, P.b], { ...C, easing: travel });
  const c = R.along(p); const center: LonLat = v === 'flat_unroll' ? [150, -38] : [c[0], c[1] * 0.6];
  const sc = v === 'flat_unroll' ? 900 : 430 - 50 * Math.sin(Math.PI * (p - P.a) / Math.max(0.01, P.b - P.a));
  const proj = v === 'flat_unroll' ? geoMercator().center(center).scale(sc * 1.4).translate([900, 520]) : geoOrthographic().scale(sc).translate([960, 560]).rotate([-center[0], -center[1], 0]).clipAngle(90);
  const path = geoPath(proj as any); const grat = geoGraticule10();
  const pos = proj(c as any) as [number, number] | null; const hd = heading(p); const ang = Math.atan2(-hd[1], hd[0]) * 180 / Math.PI;
  const km = Math.round(13560 * (p - P.a) / Math.max(0.01, P.b - P.a) * (P.b - P.a));
  return <Ground at="50% 55%">
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {v !== 'flat_unroll' ? <circle cx={960} cy={560} r={sc * 1.08} fill={rgba(ACC, 0.05)} /> : null}
      <path d={path({ type: 'Sphere' } as any) || ''} fill={SEA} />
      <path d={path(grat) || ''} fill="none" stroke={rgba(TINT, 0.12)} strokeWidth={1} />
      <path d={path(land) || ''} fill={LANDC} stroke={LANDS} strokeWidth={1.2} />
      {v === 'terminator_line' ? <path d={path({ type: 'Sphere' } as any) || ''} fill="url(#term)" /> : null}
      <defs><linearGradient id="term" x1="0" x2="1"><stop offset="0.55" stopColor="rgba(0,0,0,0)" /><stop offset="1" stopColor="rgba(0,0,0,0.55)" /></linearGradient></defs>
      <path d={path(R.upTo(1)) || ''} fill="none" stroke={rgba(BONE, 0.18)} strokeWidth={2} strokeDasharray="6 8" />
      <path d={path(R.upTo(p, P.a)) || ''} fill="none" stroke={ACC} strokeWidth={5} strokeLinecap="round" />
      {P.wind ? Array.from({ length: 26 }, (_, i) => { const q = ((i / 26) + f / 240) % 1; const ll = R.along(q); const xy = proj(ll as any) as any; if (!xy) return null; const h2 = heading(q); const a2 = Math.atan2(-h2[1], h2[0]);
        return <line key={i} x1={xy[0] - 22 * Math.cos(a2) + 40} y1={xy[1] - 22 * Math.sin(a2)} x2={xy[0] + 22 * Math.cos(a2) + 40} y2={xy[1] + 22 * Math.sin(a2)} stroke={rgba(BONE, 0.5)} strokeWidth={3} strokeLinecap="round" />; }) : null}
      {pos ? <g transform={`translate(${pos[0]} ${pos[1]}) rotate(${ang})`}><circle r={26} fill={rgba(ACC, 0.18)} /><circle r={9} fill={BONE} /></g> : null}
      {[R.along(P.a), R.along(P.b)].map((ll, i) => { const xy = proj(ll as any) as any; const lab = P.labels[i]; if (!xy || !lab || (i === 1 && p < P.b - 0.02)) return null;
        return <text key={i} x={xy[0] + 24} y={xy[1] + (i ? 40 : -16)} fontFamily={FONT.mono} fontSize={26} letterSpacing={3} fill={i ? ACC : MUTED}>{lab}</text>; })}
    </svg>
    {P.km ? <div style={{ position: 'absolute', left: 96, top: 120, ...DISP(140, 62, 880), color: BONE, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>{km.toLocaleString('en-US')}<span style={{ color: ACC, fontSize: 70 }}> KM</span></div> : null}
    <Mono text="ROUTE APPROXIMATE" f0={16} size={20} color={MUTED} style={{ position: 'absolute', left: 1500, top: 70 }} />
  </Ground>;
};
const MapZoom: React.FC<{ s: Shot; land: any }> = ({ s, land }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const v = s.variant;
  const zoom = v === 'dive' ? interpolate(f, [0, d], [0.75, 1.1], { ...C, easing: io }) : interpolate(f, [0, d], [1, 1.08], C);
  const panX = v === 'pan_along' ? interpolate(f, [0, d], [60, -60], { ...C, easing: io }) : 0;
  const proj = geoMercator().rotate([-180, 0]).center([P.center[0] - 180 + (P.center[0] < 0 ? 360 : 0), P.center[1]]).scale(P.scale * zoom).translate([960 + panX, 540]);
  const path = geoPath(proj as any); const p = interpolate(f, [8, d - 10], [P.a, P.b], { ...C, easing: travel });
  const pos = proj(R.along(p) as any) as any;
  return <AbsoluteFill style={{ background: SEA }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {v === 'topo_lines' ? Array.from({ length: 14 }, (_, i) => <path key={i} d={path(R.upTo(1)) || ''} fill="none" stroke={rgba(TINT, 0.05)} strokeWidth={30 + i * 40} />) : null}
      <path d={path(land) || ''} fill={LANDC} stroke={LANDS} strokeWidth={1.4} />
      <path d={path(R.upTo(1)) || ''} fill="none" stroke={rgba(BONE, 0.2)} strokeWidth={2} strokeDasharray="6 8" />
      <path d={path(R.upTo(p, 0)) || ''} fill="none" stroke={ACC} strokeWidth={5} strokeLinecap="round" />
      {P.dots ? PTS.map((q, i) => { const xy = proj(q as any) as any; return <circle key={i} cx={xy[0]} cy={xy[1]} r={7} fill={GROUND} stroke={ACC} strokeWidth={3} opacity={interpolate(f, [6 + i * 3, 12 + i * 3], [0, 1], C)} />; }) : null}
      {(P.pins as string[]).map((k, i) => { const xy = proj(PLACE[k] as any) as any; return <g key={k} opacity={interpolate(f, [12 + i * 8, 24 + i * 8], [0, 1], C)}>
        <circle cx={xy[0]} cy={xy[1]} r={P.usual ? 46 : 9} fill={P.usual ? rgba(BONE, 0.08) : BONE} stroke={P.usual ? rgba(BONE, 0.6) : 'none'} strokeWidth={2} strokeDasharray={P.usual ? '6 6' : undefined} />
        <text x={xy[0] + (P.usual ? 56 : 20)} y={xy[1] + 8} fontFamily={FONT.mono} fontSize={24} letterSpacing={3} fill={BONE}>{NAMES[k]}</text></g>; })}
      {pos ? <g><circle cx={pos[0]} cy={pos[1]} r={24} fill={rgba(ACC, 0.2)} /><circle cx={pos[0]} cy={pos[1]} r={9} fill={BONE} /></g> : null}
    </svg>
    <Vignette />
    <Label text={P.label} f0={14} x={96} y={110} size={64} />
    <Mono text="ROUTE APPROXIMATE" f0={20} size={20} color={MUTED} style={{ position: 'absolute', left: 100, top: 196 }} />
  </AbsoluteFill>;
};
// 600 km off Sydney: distance line drawn from the coast to the route.
const MapCompareScale: React.FC<{ s: Shot; land: any }> = ({ s, land }) => {
  const f = useCurrentFrame(); const d = durF(s);
  const proj = geoMercator().center([158, -36]).scale(1700 * interpolate(f, [0, d], [1.08, 1], { ...C, easing: io })).translate([960, 520]);
  const path = geoPath(proj as any); const p = interpolate(f, [6, d * 0.6], [FR.newcal, FR.turn], { ...C, easing: travel });
  const sy = proj(PLACE.sydney as any) as any, os = proj(PLACE.offSydney as any) as any; const lp = interpolate(f, [20, 50], [0, 1], { ...C, easing: io });
  const km = Math.round(geoDistance(PLACE.sydney, PLACE.offSydney) * 6371 / 10) * 10;
  const pos = proj(R.along(p) as any) as any;
  return <AbsoluteFill style={{ background: SEA }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <path d={path(land) || ''} fill={LANDC} stroke={LANDS} strokeWidth={1.4} />
      <path d={path(R.upTo(p, FR.newcal - 0.05)) || ''} fill="none" stroke={ACC} strokeWidth={5} strokeLinecap="round" />
      <circle cx={sy[0]} cy={sy[1]} r={9} fill={BONE} /><text x={sy[0] - 20} y={sy[1] + 8} textAnchor="end" fontFamily={FONT.mono} fontSize={24} letterSpacing={3} fill={BONE}>SYDNEY</text>
      <line x1={sy[0]} y1={sy[1]} x2={sy[0] + (os[0] - sy[0]) * lp} y2={sy[1] + (os[1] - sy[1]) * lp} stroke={BONE} strokeWidth={3} strokeDasharray="12 10" />
      <circle cx={pos[0]} cy={pos[1]} r={24} fill={rgba(ACC, 0.2)} /><circle cx={pos[0]} cy={pos[1]} r={9} fill={BONE} />
    </svg>
    <Label text={`≈${km} KM OUT TO SEA`} f0={50} x={(sy[0] + os[0]) / 2 - 200} y={(sy[1] + os[1]) / 2 - 140} size={64} />
    <Mono text="ROUTE APPROXIMATE · USGS WAYPOINTS" f0={20} size={20} color={MUTED} style={{ position: 'absolute', left: 100, top: 90 }} />
  </AbsoluteFill>;
};

// ---------- custom scenes made for this episode ----------
// TagPing: the 5 g solar satellite tag on the bird's back, and the log it sent.
const TagPing: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s);
  const log = ['2022-10-13  60.4N 162.3W  DEPART', '2022-10-15  45.0N 171.0W  OVER OCEAN', '2022-10-19  00.0N 178.5W  KIRIBATI', '2022-10-21  16.5S 168.2E  VANUATU', '2022-10-23  41.4S 156.4E  TURN WEST', '2022-10-24  41.0S 148.4E  TASMANIA'];
  const shown = Math.floor(interpolate(f, [10, d - 10], [0, log.length], C));
  return <Ground>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {[0, 1, 2].map((k) => { const q = ((f / 40 + k / 3) % 1); return <circle key={k} cx={560} cy={500} r={60 + q * 380} fill="none" stroke={rgba(ACC, 0.5 * (1 - q))} strokeWidth={3} />; })}
      <g transform={`translate(560 500) scale(${spring({ frame: f, fps: FPS, config: SPRING_SOFT })})`}>
        <rect x={-110} y={-48} width={220} height={96} rx={18} fill={GROUND2} stroke={BONE} strokeWidth={4} />
        {Array.from({ length: 6 }, (_, i) => <rect key={i} x={-92 + i * 31} y={-32} width={26} height={64} fill={rgba(ACC, 0.25 + 0.2 * ((i + Math.floor(f / 6)) % 2))} />)}
        <line x1={110} y1={0} x2={250} y2={-90} stroke={BONE} strokeWidth={3} />
      </g>
    </svg>
    <Mono text="SOLAR SATELLITE TAG · ~5 G · SCHEMATIC" f0={6} size={22} color={MUTED} style={{ position: 'absolute', left: 300, top: 760 }} />
    <div style={{ position: 'absolute', left: 1000, top: 300 }}>
      {log.slice(0, shown).map((l, i) => <div key={i} style={{ fontFamily: FONT.mono, fontSize: 30, letterSpacing: '0.06em', color: i === 4 ? ACC : BONE, marginBottom: 22, textShadow: SHADOW }}>{l}</div>)}
    </div>
    <Mono text="POSITIONS APPROXIMATE · FROM PUBLISHED WAYPOINTS" f0={20} size={18} color={MUTED} style={{ position: 'absolute', left: 1000, top: 250 }} />
  </Ground>;
};
// WindBelts: the route with streaming wind arrows; helping arrows in accent; a gauge fills to 9 of 10 hours.
const WindBelts: React.FC<{ s: Shot; land: any }> = ({ s, land }) => {
  const f = useCurrentFrame(); const d = durF(s); const mode = s.params.mode;
  const proj = geoMercator().rotate([180, 0]).center([0, 8]).scale(330).translate([760, 520]); const path = geoPath(proj as any);
  const gauge = interpolate(f, [16, d - 20], [0, 0.9], { ...C, easing: io });
  const r = rng(3); const arrows = Array.from({ length: 70 }, () => { const q = r(); const help = r() < 0.9; const jit = (r() - 0.5) * 3; return { q, help, jit }; });
  return <AbsoluteFill style={{ background: SEA }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <path d={path(land) || ''} fill={LANDC} stroke={LANDS} strokeWidth={1.2} />
      <path d={path(R.upTo(1)) || ''} fill="none" stroke={rgba(BONE, 0.35)} strokeWidth={3} />
      {arrows.map((a, i) => { const q = (a.q + f / 400) % 1; const ll = R.along(q); const xy = proj([ll[0] + a.jit, ll[1] + a.jit] as any) as any; const h = heading(q); const ang = Math.atan2(-h[1], h[0]) + (a.help ? 0 : Math.PI);
        const lat = Math.abs(ll[1]); const len = mode === 'lat' ? 8 + 34 * Math.min(1, lat / 45) : 22; const vis = interpolate(f, [4 + i * 0.4, 14 + i * 0.4], [0, 1], C);
        return <g key={i} opacity={vis} transform={`translate(${xy[0]} ${xy[1]}) rotate(${ang * 180 / Math.PI})`}><line x1={-len} y1={0} x2={len} y2={0} stroke={a.help ? ACC : rgba(BONE, 0.6)} strokeWidth={3.5} strokeLinecap="round" /><path d={`M${len} 0 L${len - 9} -6 L${len - 9} 6 Z`} fill={a.help ? ACC : rgba(BONE, 0.6)} /></g>; })}
    </svg>
    {mode === 'lat' ? <>
      <Label text="STRONGEST IN THE NORTH" f0={10} x={1180} y={180} size={56} />
      <Label text="WEAKEST NEAR THE EQUATOR" f0={30} x={1180} y={480} size={56} color={MUTED} /></>
      : <div style={{ position: 'absolute', left: 1240, top: 300 }}>
        <Mono text="WIND AT ~1,500 M ALONG THE ROUTE" f0={4} size={22} color={MUTED} />
        <div style={{ ...DISP(260, 62, 880), color: BONE, textShadow: SHADOW, marginTop: 20 }}>{Math.round(gauge * 10)}<span style={{ color: MUTED, fontSize: 140 }}>/10</span></div>
        <div style={{ ...DISP(64, 80, 700), color: ACC, marginTop: 10 }}>HOURS OF TAILWIND</div>
        <div style={{ width: 520, height: 14, background: rgba(TINT, 0.25), marginTop: 30 }}><div style={{ width: 520 * gauge, height: 14, background: ACC }} /></div></div>}
    <Mono text="NOAA GFS · OUR CALCULATION · SCHEMATIC ARROWS" f0={20} size={18} color={MUTED} style={{ position: 'absolute', left: 1240, top: 90 }} />
  </AbsoluteFill>;
};
// TurnWind: the Tasman Sea; the track bends west on Oct 23 while the model wind comes from the north, then from the northeast.
const TurnWind: React.FC<{ s: Shot; land: any }> = ({ s, land }) => {
  const f = useCurrentFrame(); const d = durF(s); const mode = s.params.mode;
  const proj = geoMercator().center([153, -38]).scale(2100).translate([960, 520]); const path = geoPath(proj as any);
  const p = mode === 'turn' ? interpolate(f, [6, d - 6], [FR.offSydney, 1], { ...C, easing: travel }) : 1;
  const pos = proj(R.along(p) as any) as any; const tp = proj(PLACE.turn as any) as any;
  const windDeg = mode === 'ne' ? interpolate(f, [10, d * 0.6], [180, 225], { ...C, easing: io }) : 180; // direction the air moves to (180 = southward)
  const clock = mode === 'north' ? `OCT 23 · ${String(Math.floor(interpolate(f, [0, d], [0, 9], C))).padStart(2, '0')}:00 UTC` : mode === 'ne' ? 'OCT 23 · LATER' : 'OCT 23';
  const field = Array.from({ length: 30 }, (_, i) => [300 + (i % 6) * 260, 200 + Math.floor(i / 6) * 160]);
  const wa = (windDeg - 90) * Math.PI / 180; // screen angle: 180deg (south) -> down
  return <AbsoluteFill style={{ background: SEA }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <path d={path(land) || ''} fill={LANDC} stroke={LANDS} strokeWidth={1.6} />
      {mode !== 'turn' ? field.map(([x, y], i) => { const o = ((f * 2 + i * 23) % 60) - 30; return <g key={i} transform={`translate(${x + Math.cos(wa) * o} ${y + Math.sin(wa) * o})`} opacity={0.75}>
        <line x1={-Math.cos(wa) * 26} y1={-Math.sin(wa) * 26} x2={Math.cos(wa) * 26} y2={Math.sin(wa) * 26} stroke={rgba(BONE, 0.7)} strokeWidth={3} strokeLinecap="round" />
        <circle cx={Math.cos(wa) * 26} cy={Math.sin(wa) * 26} r={4} fill={rgba(BONE, 0.7)} /></g>; }) : null}
      <path d={path(R.upTo(p, FR.offSydney - 0.03)) || ''} fill="none" stroke={ACC} strokeWidth={6} strokeLinecap="round" />
      <circle cx={tp[0]} cy={tp[1]} r={interpolate(f, [10, 30], [0, 40], C)} fill="none" stroke={ACC} strokeWidth={3} strokeDasharray="8 8" />
      <circle cx={pos[0]} cy={pos[1]} r={24} fill={rgba(ACC, 0.25)} /><circle cx={pos[0]} cy={pos[1]} r={9} fill={BONE} />
    </svg>
    <Label text={mode === 'turn' ? 'TURNS WEST' : mode === 'north' ? 'WIND FROM THE NORTH' : 'THEN FROM THE NORTHEAST'} f0={12} x={96} y={110} size={68} red={mode === 'turn'} />
    <Mono text={clock} f0={4} size={30} color={ACC} style={{ position: 'absolute', left: 100, top: 210 }} />
    <Mono text="ROUTE APPROXIMATE · WIND: NOAA GFS, OUR CHECK" f0={20} size={18} color={MUTED} style={{ position: 'absolute', left: 100, top: 260 }} />
  </AbsoluteFill>;
};
const CUSTOM: Record<string, React.FC<{ s: Shot; land: any }>> = { TagPing, WindBelts, TurnWind };

// ---------- transitions + chrome ----------
const TransitionIn: React.FC<{ kind?: string; children: React.ReactNode }> = ({ kind, children }) => {
  const f = useCurrentFrame();
  if (kind === 'dissolve') return <AbsoluteFill style={{ opacity: interpolate(f, [0, 12], [0, 1], C) }}>{children}</AbsoluteFill>;
  if (kind === 'push') { const p = interpolate(f, [0, 10], [1, 0], { ...C, easing: out }); return <AbsoluteFill style={{ transform: `scale(${1 + p * 0.08})`, opacity: 1 - p * 0.8 }}>{children}</AbsoluteFill>; }
  return <AbsoluteFill>{children}</AbsoluteFill>;
};
const Chrome: React.FC<{ s: Shot }> = ({ s }) => {
  const ch = chapterOf(s); const show = ch && !['chapter_card', 'kinetic_type', 'question_card'].includes(s.scene_type) && !s.params.end;
  return <>{show ? <Tag text={`${String(ch![0]).padStart(2, '0')}  ${ch![1]}`} f0={8} x={60} y={52} size={18} color={ACC} /> : null}
    {s.source_line ? <Tag text={s.source_line.toUpperCase()} f0={14} x={60} y={1080 - 56} size={16} color={rgba(BONE, 0.72)} /> : null}</>;
};
const Scene: React.FC<{ s: Shot; l50: any; l110: any }> = ({ s, l50, l110 }) => {
  switch (s.scene_type) {
    case 'film_clip': return <FilmClip s={s} />;
    case 'stock_broll': return <StockBroll s={s} />;
    case 'film_freeze_annotate': return <FilmFreeze s={s} />;
    case 'photo_parallax': return <PhotoParallax s={s} />;
    case 'photo_detail_zoom': return <PhotoDetail s={s} />;
    case 'photo_lighttable': return <PhotoLighttable s={s} />;
    case 'photo_compare': return <PhotoCompare s={s} />;
    case 'satellite_reveal': return <SatelliteReveal s={s} />;
    case 'kinetic_type': return <KineticType s={s} />;
    case 'chapter_card': return <ChapterCard s={s} />;
    case 'question_card': return <QuestionCard s={s} />;
    case 'big_number': return <BigNumber s={s} />;
    case 'counter_ticker': return <CounterTicker s={s} />;
    case 'chart_bar_race': return <ChartBars s={s} />;
    case 'diagram_build': return <DiagramBuild s={s} />;
    case 'timeline_scroll': return <TimelineScroll s={s} />;
    case 'split_screen': return <SplitScreen s={s} />;
    case 'globe_route': return <GlobeRoute s={s} land={l110} />;
    case 'map_zoom': return <MapZoom s={s} land={l50} />;
    case 'map_compare_scale': return <MapCompareScale s={s} land={l50} />;
    case 'custom': { const Comp = CUSTOM[s.custom?.component ?? '']; return Comp ? <Comp s={s} land={l50} /> : <Ground><div style={{ color: SIGNAL, fontSize: 60 }}>MISSING {s.custom?.component}</div></Ground>; }
    default: return <Ground><div style={{ color: SIGNAL, fontSize: 60 }}>MISSING {s.scene_type}</div></Ground>;
  }
};
const SFX: Record<string, [string, number]> = {
  whoosh: ['sfx/whoosh-fast.mp3', 0.18], whoosh_big: ['sfx/whoosh-big.mp3', 0.2], impact: ['sfx/impact-deep-whoosh.mp3', 0.2], hit: ['sfx/impact-deep-whoosh.mp3', 0.14],
  paper: ['sfx/paper-slide.mp3', 0.22], riser_soft: ['sfx/swoosh-slow.mp3', 0.14], tick: ['sfx2/tick.wav', 0.2],
};
export const GodwitEpisode: React.FC = () => {
  const l110 = useLand('countries-110m.json'); const l50 = useLand('countries-50m.json');
  if (!l110 || !l50) return null;
  return <AbsoluteFill style={{ backgroundColor: GROUND }}>
    {SHOTS.map((s, i) => { const from = Math.round(s.params.start_s * FPS); const next = SHOTS[i + 1]; const tail = next && next.transition_in === 'dissolve' ? 12 : 0;
      return <Sequence key={s.id} from={from} durationInFrames={durF(s) + tail} name={`${s.id} ${s.scene_type}`}>
        <TransitionIn kind={s.transition_in}><Scene s={s} l50={l50} l110={l110} /><Chrome s={s} /></TransitionIn>
      </Sequence>; })}
    <Vignette /><Grain opacity={0.05} />
    <Audio src={staticFile('ep/voice.wav')} volume={1} />
    <Audio src={staticFile('ep/bed.wav')} volume={1} />
    {SHOTS.flatMap((s) => (s.sfx ?? []).map((k, j) => { const m = SFX[k]; if (!m) return null; const from = Math.max(0, Math.round(s.params.start_s * FPS) - (k.startsWith('whoosh') || k === 'riser_soft' ? 6 : 0) + j * 12);
      return <Sequence key={s.id + k + j} from={from} durationInFrames={120}><Audio src={staticFile(m[0])} volume={m[1]} /></Sequence>; }))}
  </AbsoluteFill>;
};
