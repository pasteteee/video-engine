// Hunga Tonga episode renderer: reads the shot list and maps each scene_type (and its variant) to a component.
// Built on the Apollo 12 renderer; adds globe/map, satellite, section, formula, plot, board and bar scenes.
import React from 'react';
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { geoDistance, geoEquirectangular, geoInterpolate, geoPath } from 'd3-geo';
import SL from './ep/shotlist.json';
import LINES from './ep/lines.json';
import MEDIA_RAW from './ep/media.json';
import DATA from './ep/data.json';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, GROUND2, MUTED, PAPER, SHADOW, SIGNAL, SPRING_SOFT, TINT, exitE, io, out, rgba, rng } from './kit/tokens';
import { Callout, Hairline, Kinetic, Mono, Odometer, StopBlock, Unredact } from './kit/Type';
import { Finish, Grain, SceneBg, Tag } from './kit/Brand';
import { FlatMap, Globe, Pin, makeRoute, useLand } from './kit/Geo';
import { CUSTOM } from './custom';

export type Shot = { id: string; line_ids: string[]; scene_type: string; duration_s: number; params: any; variant?: string; custom?: { component: string; brief: string; register?: string }; media_ids?: string[]; source_line?: string; transition_in?: string; sfx?: string[] };
export const FPS = 30;
const SHOTS = (SL as any).shots as Shot[];
const END_S = SHOTS[SHOTS.length - 1].params.start_s + SHOTS[SHOTS.length - 1].duration_s;
export const EP_FRAMES = Math.round(END_S * FPS) + 20;
export const MEDIA = MEDIA_RAW as Record<string, { src: string; w: number; h: number }>;
export const med = (id: string) => staticFile('ep/' + MEDIA[id].src);
export const durF = (s: Shot) => Math.round(s.duration_s * FPS);
export const D = DATA as any;
const CH: Record<string, [number, string] | null> = { cold: null, island: [1, 'AN ISLAND FOR SEVEN YEARS'], blast: [1, 'AN ISLAND FOR SEVEN YEARS'], silence: [1, 'AN ISLAND FOR SEVEN YEARS'], ring: [2, 'WE MEASURED THE RING'], sydney: [2, 'WE MEASURED THE RING'], laps: [2, 'WE MEASURED THE RING'], japan: [3, 'WARN OR WAIT'], why: [4, 'WHY THE RULES FAILED'], far: [4, 'WHY THE RULES FAILED'], answer: [5, 'THE ANSWER'], after: [6, 'WHAT CHANGED'] };
const chapterOf = (s: Shot) => CH[(LINES as any[]).find((l) => l.id === s.line_ids[0])?.chapter ?? 'cold'];
const cover = (iw: number, ih: number, bw: number, bh: number) => { const k = Math.max(bw / iw, bh / ih); return { k, w: iw * k, h: ih * k }; };
// display size that fits the longest line into `w` px (Archivo at wdth 62 ≈ 0.47 em per capital)
export const fitSize = (lines: string[], max: number, w = 1560) => Math.min(max, Math.floor(w / (Math.max(...lines.map((l) => l.length)) * 0.47)));
export const hhmm = (m: number) => { const t = ((Math.round(m) % 1440) + 1440) % 1440; return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`; };

// ---------- shared pieces ----------
export const Shade: React.FC<{ top?: number; bottom?: number; left?: number }> = ({ top = 0.3, bottom = 0.8, left = 0 }) => <>
  <AbsoluteFill style={{ background: `linear-gradient(180deg, ${rgba(GROUND, top)} 0%, ${rgba(GROUND, 0)} 24%, ${rgba(GROUND, 0)} 55%, ${rgba(GROUND, bottom)} 100%)` }} />
  {left ? <AbsoluteFill style={{ background: `linear-gradient(90deg, ${rgba(GROUND, left)} 0%, ${rgba(GROUND, 0)} 55%)` }} /> : null}
</>;
// A line of display type that rises from a mask. No plate.
export const Line: React.FC<{ text: string; f0: number; x?: number; y: number; size?: number; color?: string; stop?: boolean; accentWord?: string; wdth?: number }> = ({ text, f0, x = 90, y, size = 84, color = BONE, stop, accentWord, wdth = 62 }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [f0, f0 + 16], [0, 1], { ...C, easing: out });
  if (f < f0) return null;
  return <div style={{ position: 'absolute', left: x, top: y, overflow: 'hidden', paddingBottom: size * 0.08 }}>
    <div style={{ ...DISP(size, wdth), color, whiteSpace: 'nowrap', textShadow: SHADOW, transform: `translateY(${(1 - p) * 105}%)`, textTransform: /hPa/.test(text) ? 'none' : 'uppercase' }}>
      {text.split(' ').map((w, i) => <span key={i} style={{ color: accentWord && w.replace(/[^A-Z0-9.]/gi, '') === accentWord ? ACCENT_EP : undefined }}>{i ? ' ' : ''}{w}</span>)}
      {stop ? <StopBlock size={size} p={interpolate(f, [f0 + 10, f0 + 18], [0, 1], C)} /> : null}
    </div></div>;
};

// Camera into an image: centre (cx,cy as fractions) and zoom z, interpolated, clamped inside the image.
export const ImageCam: React.FC<{ src: string; iw: number; ih: number; from: number[]; to: number[]; dur: number; filter?: string; rot?: number; W?: number; H?: number; children?: (map: (x: number, y: number) => [number, number]) => React.ReactNode }> = ({ src, iw, ih, from, to, dur, filter, rot = 0, children, W: W0, H: H0 }) => {
  const f = useCurrentFrame(); const vc = useVideoConfig(); const W = W0 ?? vc.width, H = H0 ?? vc.height;
  const p = interpolate(f, [0, dur], [0, 1], { ...C, easing: io });
  const cx = from[0] + (to[0] - from[0]) * p, cy = from[1] + (to[1] - from[1]) * p, z = from[2] * Math.pow(to[2] / from[2], p);
  const cv = cover(iw, ih, W, H);
  const px = Math.min(Math.max(cx * cv.w, W / 2 / z), cv.w - W / 2 / z), py = Math.min(Math.max(cy * cv.h, H / 2 / z), cv.h - H / 2 / z);
  const map = (x: number, y: number): [number, number] => [W / 2 + (x * cv.w - px) * z, H / 2 + (y * cv.h - py) * z];
  return <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: '#000', width: W, height: H }}>
    <AbsoluteFill style={{ transform: rot ? `rotate(${rot * (p - 0.5)}deg) scale(${1 + Math.abs(rot) * 0.02})` : undefined }}>
      <Img src={src} style={{ position: 'absolute', left: 0, top: 0, width: cv.w, height: cv.h, transformOrigin: '0 0', transform: `translate(${W / 2}px, ${H / 2}px) scale(${z}) translate(${-px}px, ${-py}px)`, filter }} />
    </AbsoluteFill>
    {children ? children(map) : null}
  </AbsoluteFill>;
};
const MCam: React.FC<{ id: string } & Omit<React.ComponentProps<typeof ImageCam>, 'src' | 'iw' | 'ih'>> = ({ id, ...r }) => <ImageCam src={med(id)} iw={MEDIA[id].w} ih={MEDIA[id].h} {...r} />;
const Overlays: React.FC<{ items?: { at: number; text: string; red?: boolean }[]; y?: number }> = ({ items, y = 830 }) => <>{(items ?? []).map((o, i) => <Line key={i} text={o.text} f0={Math.round(o.at * FPS)} y={y - i * 110} size={fitSize([o.text], 92)} stop={o.red} />)}</>;

// ---------- archival scenes ----------
const FilmClip: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const v = s.variant ?? 'full_frame';
  const z = 1.02 + 0.06 * interpolate(f, [0, d], [0, 1], C);
  const flick = v === 'projector_flicker' ? 0.92 + 0.08 * Math.abs(Math.sin(f * 2.3) * Math.sin(f * 0.7)) : 1;
  const weave = v === 'projector_flicker' ? Math.sin(f * 1.7) * 1.5 : 0;
  const vid = (st?: React.CSSProperties) => <OffthreadVideo src={med(s.media_ids![0])} startFrom={Math.round((P.trim ?? 0) * FPS)} playbackRate={P.rate ?? 1} muted style={{ width: '100%', height: '100%', objectFit: 'cover', filter: `contrast(1.06) brightness(${flick})`, ...st }} />;
  if (v === 'split_reel') {
    const p = interpolate(f, [0, 16], [0, 1], { ...C, easing: out });
    return <SceneBg drift={0.2}>
      <div style={{ position: 'absolute', left: 90, top: 150, width: 1100, height: 620, overflow: 'hidden', transform: `translateX(${(1 - p) * -200}px)`, opacity: p, boxShadow: '0 30px 80px rgba(0,0,0,0.6)' }}>
        <AbsoluteFill style={{ transform: `scale(${z})` }}>{vid()}</AbsoluteFill></div>
      <div style={{ position: 'absolute', left: 1230, top: 150, width: 600, height: 620, overflow: 'hidden', transform: `translateX(${(1 - p) * 300}px)`, opacity: p, boxShadow: '0 30px 80px rgba(0,0,0,0.6)' }}>
        <AbsoluteFill style={{ transform: `scale(${2.2 + 0.2 * f / d})`, transformOrigin: P.origin ?? '28% 62%' }}>{vid()}</AbsoluteFill></div>
      <Mono text="FULL DISK" f0={10} size={20} color={MUTED} style={{ position: 'absolute', left: 92, top: 790 }} />
      <Mono text="AROUND THE VOLCANO ×2" f0={16} size={20} color={MUTED} style={{ position: 'absolute', left: 1232, top: 790 }} />
      {P.tag ? <Line text={P.tag} f0={14} x={90} y={840} size={84} /> : null}
    </SceneBg>;
  }
  return <AbsoluteFill style={{ backgroundColor: '#000' }}>
    <AbsoluteFill style={{ transform: `scale(${z}) translateY(${weave}px)`, transformOrigin: P.origin ?? '50% 50%' }}>{vid()}</AbsoluteFill>
    <Shade top={0.3} bottom={0.75} />
    {v === 'projector_flicker' ? <Grain opacity={0.14} /> : null}
    {P.tag ? <Line text={P.tag} f0={10} y={850} size={fitSize([P.tag], 96)} /> : null}
  </AbsoluteFill>;
};

const PhotoParallax: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const p = interpolate(f, [0, d], [0, 1], { ...C, easing: io });
  const v = s.variant ?? 'push_in';
  const tr = v === 'lateral_drift' ? `scale(1.16) translateX(${(P.dir ?? 1) * (-50 + 100 * p)}px) rotate(${(P.dir ?? 1) * (-0.6 + 1.2 * p)}deg)` : `scale(${1.04 + 0.12 * p}) translateY(${-14 * p}px)`;
  return <AbsoluteFill style={{ backgroundColor: '#000' }}>
    <AbsoluteFill style={{ transform: tr, transformOrigin: P.origin ?? '50% 40%' }}>
      <Img src={med(s.media_ids![0])} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: P.pos ?? '50% 50%' }} />
    </AbsoluteFill>
    <Shade left={P.label ? 0.35 : 0} bottom={P.label ? 0.8 : 0.45} />
    {P.label ? <Line text={P.label} f0={10} y={P.label_y ?? 830} size={fitSize([P.label], 96)} /> : null}
  </AbsoluteFill>;
};

const PhotoDetailZoom: React.FC<{ s: Shot }> = ({ s }) => {
  const d = durF(s); const P = s.params; const v = s.variant ?? 'circle_lands'; const f = useCurrentFrame();
  const at = Math.round(d * 0.4);
  return <AbsoluteFill>
    <MCam id={s.media_ids![0]} from={P.frm} to={P.to} dur={d}>{(map) => {
      if (v === 'crop_marks') { const c = P.circle ?? [P.to[0], P.to[1]]; const [x, y] = map(c[0], c[1]); const r = 170; const p = interpolate(f, [at, at + 12], [0, 1], { ...C, easing: out }); const o = (1 - p) * 70;
        return <svg width={1920} height={1080} style={{ position: 'absolute', opacity: p }}>{[[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([sx, sy], i) => <path key={i} d={`M${x + sx * (r + o)} ${y + sy * (r + o) - sy * 40} L${x + sx * (r + o)} ${y + sy * (r + o)} L${x + sx * (r + o) - sx * 40} ${y + sy * (r + o)}`} stroke={ACCENT_EP} strokeWidth={5} fill="none" />)}</svg>; }
      if (!P.circle) return null; const [x, y] = map(P.circle[0], P.circle[1]);
      if (v === 'magnifier') { const p = interpolate(f, [at - 6, at + 10], [0, 1], { ...C, easing: out }); const R = 210 * p; const m = MEDIA[s.media_ids![0]]; const cv = cover(m.w, m.h, 1920, 1080);
        return <><svg width={1920} height={1080} style={{ position: 'absolute' }}><circle cx={x} cy={y} r={R + 4} fill="none" stroke={ACCENT_EP} strokeWidth={5} /></svg>
          <div style={{ position: 'absolute', left: x - R, top: y - R, width: 2 * R, height: 2 * R, borderRadius: '50%', overflow: 'hidden', boxShadow: '0 20px 60px rgba(0,0,0,0.6)' }}>
            <Img src={med(s.media_ids![0])} style={{ position: 'absolute', width: cv.w * 2.6, height: cv.h * 2.6, left: R - P.circle[0] * cv.w * 2.6, top: R - P.circle[1] * cv.h * 2.6, filter: 'contrast(1.25)' }} /></div></>; }
      const p = interpolate(f, [at, at + 22], [0, 1], { ...C, easing: io }); const r = 120;
      return <svg width={1920} height={1080} style={{ position: 'absolute', filter: 'drop-shadow(0 0 6px rgba(0,0,0,0.6))' }}><circle cx={x} cy={y} r={r} fill="none" stroke={ACCENT_EP} strokeWidth={5} strokeDasharray={`${2 * Math.PI * r * p} 3000`} transform={`rotate(-100 ${x} ${y})`} /></svg>;
    }}</MCam>
    <Shade bottom={0.75} />
    <Overlays items={P.overlay} />
  </AbsoluteFill>;
};

const PhotoLighttable: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const d = durF(s); const P = s.params; const v = s.variant ?? 'single_print';
  const id = s.media_ids![0]; const m = MEDIA[id];
  const z = 1 + (P.push ?? 0.05) * interpolate(f, [0, d], [0, 1], { ...C, easing: io });
  const crops = v === 'contact_strip' ? [[0.3, 0.4], [0.5, 0.5], [0.7, 0.6]] : v === 'stack_shuffle' ? [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5]] : [[0.5, 0.5]];
  const n = crops.length;
  return <SceneBg drift={0.2}>
    <Img src={med(id)} style={{ position: 'absolute', inset: -60, width: 2040, height: 1200, objectFit: 'cover', filter: 'blur(30px) brightness(0.28) saturate(0.7)' }} />
    {crops.map((c, i) => {
      const p = spring({ frame: f - 2 - i * 7, fps, config: { damping: 20, stiffness: 90 } });
      let ch = 820, cw = Math.min(1000, (ch * m.w) / m.h), x0 = 1840 - cw, y0 = 110, rot = 1.2;
      if (v === 'contact_strip') { ch = 500; cw = 500; x0 = 230 + i * 540; y0 = 170 + (i % 2) * 50; rot = [-3, 2, -1.5][i]; }
      if (v === 'stack_shuffle') { ch = 760; cw = Math.min(980, (ch * m.w) / m.h); x0 = 1800 - cw - i * 40; y0 = 120 + i * 24; rot = [4, -3, 1][i]; }
      const shuffle = v === 'stack_shuffle' && i < 2 ? interpolate(f, [20 + i * 14, 36 + i * 14], [0, 1], { ...C, easing: io }) : 0;
      return <div key={i} style={{ position: 'absolute', left: x0, top: y0, width: cw, height: ch, transform: `translateY(${(1 - p) * 500}px) translateX(${shuffle * 1400}px) rotate(${(1 - p) * 8 + rot + shuffle * 10}deg) scale(${z})`, opacity: Math.min(1, p * 2) * (1 - shuffle * 0.6), boxShadow: '0 30px 80px rgba(0,0,0,0.65)', outline: `12px solid ${PAPER}`, overflow: 'hidden', zIndex: n - i }}>
        <Img src={med(id)} style={{ position: 'absolute', width: v === 'contact_strip' ? cw * 2.2 : cw, height: v === 'contact_strip' ? (cw * 2.2 * m.h) / m.w : ch, left: v === 'contact_strip' ? -c[0] * cw * 2.2 + cw / 2 : 0, top: v === 'contact_strip' ? -c[1] * (cw * 2.2 * m.h) / m.w + ch / 2 : 0, objectFit: 'cover' }} /></div>;
    })}
    <div style={{ position: 'absolute', left: 90, top: v === 'contact_strip' ? 790 : 430, width: v === 'contact_strip' ? 1500 : 700 }}>
      {v === 'contact_strip' ? <Line text={P.label} f0={14} x={0} y={0} size={fitSize([P.label], 90)} />
        : <Unredact lines={wrap(P.label, 14)} top={0} size={fitSize(wrap(P.label, 14), 96, 680)} f0={12} x={0} step={8} />}
    </div>
  </SceneBg>;
};
// split a label into lines of at most n chars, at spaces or ' · '
export const wrap = (t: string, n: number) => { const out: string[] = []; let cur = ''; for (const w of t.replace(/ · /g, ' ·· ').split(' ')) { const ww = w === '··' ? '·' : w; if ((cur + ' ' + ww).trim().length > n && cur) { out.push(cur.replace(/ ·$/, '')); cur = ww === '·' ? '' : ww; } else cur = (cur ? cur + ' ' : '') + ww; } if (cur) out.push(cur.replace(/^· /, '')); return out.map((l) => l.replace(/^· /, '')); };

const PhotoCompare: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const d = durF(s); const ids = s.media_ids!; const P = s.params;
  if (s.variant === 'wipe') {
    const p = interpolate(f, [Math.round(d * 0.35), Math.round(d * 0.65)], [0, 1], { ...C, easing: io }); const z = 1.02 + 0.08 * f / d;
    return <AbsoluteFill style={{ backgroundColor: '#000' }}>
      <AbsoluteFill style={{ transform: `scale(${z})` }}><Img src={med(ids[0])} style={{ width: '100%', height: '100%', objectFit: 'cover' }} /></AbsoluteFill>
      <AbsoluteFill style={{ transform: `scale(${z})`, clipPath: `inset(0 0 0 ${100 - p * 100}%)` }}><Img src={med(ids[1])} style={{ width: '100%', height: '100%', objectFit: 'cover' }} /></AbsoluteFill>
      <div style={{ position: 'absolute', left: 1920 * (1 - p) - 2, top: 0, width: 4, height: 1080, background: ACCENT_EP, opacity: p > 0 && p < 1 ? 1 : 0 }} />
      <Shade bottom={0.75} />
      <div style={{ position: 'absolute', left: 90, top: 860, ...DISP(96), color: p < 0.5 ? BONE : ACCENT_EP, textShadow: SHADOW }}>{p < 0.5 ? P.labels[0] : P.labels[1]}</div>
    </AbsoluteFill>;
  }
  const bw = 800, bh = 600;
  return <SceneBg drift={0.3}>{ids.map((id, i) => { const f0 = i * Math.round(0.8 * FPS); const p = spring({ frame: f - f0, fps, config: { damping: 18, stiffness: 110 } });
    if (f < f0) return null; const zz = interpolate(f, [f0, d], [1, 1.07], C); const x = i === 0 ? 120 : 1000;
    return <div key={id} style={{ position: 'absolute', left: x, top: 140, width: bw, height: bh, transform: `translateX(${(1 - p) * (i === 0 ? -300 : 400)}px)`, opacity: Math.min(1, p * 2) }}>
      <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', backgroundColor: '#000' }}><Img src={med(id)} style={{ width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${zz})` }} /></div>
      <div style={{ position: 'absolute', left: 0, top: bh + 30, ...DISP(84), color: i === 1 ? ACCENT_EP : BONE, textShadow: SHADOW }}>{P.labels[i]}</div>
    </div>; })}</SceneBg>;
};

const SatelliteReveal: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const id = s.media_ids![0];
  const v = s.variant ?? 'orbit_dive';
  const N = 6, M = 4;
  return <AbsoluteFill style={{ backgroundColor: GROUND }}>
    <MCam id={id} from={P.frm} to={P.to} dur={d} rot={v === 'orbit_dive' ? 3 : 0} />
    {v === 'tile_assemble' ? <svg width={1920} height={1080} style={{ position: 'absolute' }}>{Array.from({ length: N * M }, (_, k) => { const i = k % N, j = Math.floor(k / N); const r = rng(k + 3)(); const a = interpolate(f, [2 + r * 18, 10 + r * 18], [1, 0], C);
      return <rect key={k} x={i * 320} y={j * 270} width={321} height={271} fill={GROUND} opacity={a} />; })}
      {Array.from({ length: N - 1 }, (_, i) => <line key={i} x1={(i + 1) * 320} y1={0} x2={(i + 1) * 320} y2={1080} stroke={rgba(TINT, 0.25 * interpolate(f, [20, 40], [1, 0], C))} />)}</svg> : null}
    <Shade top={0.4} bottom={0.55} />
    {P.tag ? <Mono text={P.tag} f0={8} size={30} color={ACCENT_EP} style={{ position: 'absolute', left: 90, top: 900 }} /> : null}
  </AbsoluteFill>;
};

// Weather log page, typed on; rows highlighted.
const DocumentHighlight: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const P = s.params; const d = durF(s); const rows: string[][] = P.rows; const hl: number[] = Array.isArray(P.hl) ? P.hl : [P.hl];
  const cam = interpolate(f, [6, d], [0, 1], { ...C, easing: io }); const pin = spring({ frame: f - 2, fps, config: SPRING_SOFT });
  const per = Math.max(6, Math.min(14, Math.round((d * 0.5) / rows.length)));
  return <SceneBg drift={0.25}>
    <AbsoluteFill style={{ transform: `scale(${1 + 0.1 * cam}) translateY(${-20 * cam}px)`, transformOrigin: `50% ${30 + (hl[0] ?? 0) * 10}%` }}>
      <div style={{ position: 'absolute', left: 250, top: 120, width: 1420, padding: '54px 80px 70px', background: PAPER, boxShadow: '0 40px 120px rgba(0,0,0,0.55)', transform: `rotate(-0.6deg) translateY(${(1 - pin) * 80}px)`, opacity: pin }}>
        <div style={{ fontFamily: FONT.mono, fontSize: 22, letterSpacing: 3, color: '#5A5A55', borderBottom: '2px solid #BDB8AA', paddingBottom: 16 }}>{P.head}</div>
        {rows.map((r, i) => { const a = 8 + i * per; const txt = r[2]; const n = Math.floor(interpolate(f, [a, a + txt.length / 1.5], [0, txt.length], C)); const isH = hl.includes(i);
          const sw = isH ? interpolate(f, [a + 10, a + 26], [0, 100], C) : 0;
          return <div key={i} style={{ display: 'flex', gap: 40, marginTop: 26, fontFamily: FONT.mono, fontSize: 44, lineHeight: 1.4, color: '#26261f', opacity: f >= a ? 1 : 0 }}>
            <span style={{ color: '#7a776d', width: 190, flexShrink: 0 }}>{r[0]}</span><span style={{ width: 200, flexShrink: 0, color: isH ? '#26261f' : '#4a4840', fontWeight: isH ? 600 : 400 }}>{r[1]}</span>
            <span style={{ backgroundImage: `linear-gradient(90deg, ${rgba(ACCENT_EP, 0.8)} ${sw}%, transparent ${sw}%)` }}>{txt.slice(0, n)}<span style={{ opacity: 0 }}>{txt.slice(n)}</span></span></div>; })}
      </div>
    </AbsoluteFill>
  </SceneBg>;
};

// ---------- blueprint scenes ----------
const KineticType: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const words: string[] = s.params.words; const d = durF(s);
  const red = s.params.red ?? -1; const v = s.variant ?? 'rise_narrow';
  const size = s.params.size ?? fitSize(words, words.length <= 2 ? 230 : 190); const lh = size * 0.98;
  const lines: string[][] = words.map((w) => w.split(' '));
  const top = 540 - (lines.length * lh) / 2 - 10; const push = interpolate(f, [0, d], [1, 1.05], C);
  const step = Math.max(3, Math.min(7, Math.round((d * 0.3) / words.join(' ').split(' ').length)));
  if (v === 'type_on') {
    const total = words.join('').length; const per = Math.max(1, Math.min(3, (d * 0.45) / total)); let k = 0;
    return <SceneBg style={{ transform: `scale(${push})` }}>
      <div style={{ position: 'absolute', left: 150, top, opacity: interpolate(f, [d - 8, d], [1, 0], C) }}>
        {words.map((w, li) => { const a = 4 + k * per; k += w.length; const n = Math.floor(interpolate(f, [a, a + w.length * per], [0, w.length], C)); const cur = f >= a && n < w.length;
          return <div key={li} style={{ height: lh, ...DISP(size), lineHeight: `${lh}px`, color: li === red ? ACCENT_EP : BONE, textShadow: SHADOW, whiteSpace: 'nowrap' }}>{w.slice(0, n)}{cur || (li === words.length - 1 && n === w.length && Math.floor(f / 15) % 2 === 0) ? <span style={{ display: 'inline-block', width: size * 0.08, height: size * 0.72, background: ACCENT_EP, marginLeft: size * 0.06, verticalAlign: 'baseline' }} /> : null}</div>; })}
      </div></SceneBg>;
  }
  let acc: [number, number] = [-1, -1]; if (red >= 0) acc = [red, 0];
  return <SceneBg style={{ transform: `scale(${push})` }}>
    {v === 'unredact'
      ? <Unredact lines={words} top={top} size={size} f0={4} step={10} x={150} exitAt={d - 8} />
      : <Kinetic lines={lines} top={top} size={size} f0={4} step={step} variant={v} accent={acc} x={150} exitAt={d - 8} />}
    {red >= 0 && v !== 'unredact' ? <AccentWhole words={lines} red={red} /> : null}
  </SceneBg>;
};
// Kinetic accents one word; for a phrase line we tint the whole line via CSS on top (no plate).
const AccentWhole: React.FC<{ words: string[][]; red: number }> = () => null;

const QuestionCard: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const q: string[] = s.params.q; const size = s.params.size ?? fitSize(q, 170); const d = durF(s); const v = s.variant ?? 'unredact';
  const top = 540 - (q.length * size * 0.98) / 2 - 40;
  let body: React.ReactNode;
  if (v === 'rise_narrow') body = <Kinetic lines={q.map((l) => l.split(' '))} top={top} size={size} f0={4} step={5} variant="rise_narrow" x={150} exitAt={d - 8} />;
  else if (v === 'hold_cursor') { let k = 0; body = <div style={{ position: 'absolute', left: 150, top }}>{q.map((l, i) => { const a = 6 + k * 1.2; k += l.length; const n = Math.floor(interpolate(f, [a, a + l.length * 1.2], [0, l.length], C)); const last = i === q.length - 1;
    return <div key={i} style={{ ...DISP(size), height: size * 0.98, lineHeight: `${size * 0.98}px`, color: BONE, textShadow: SHADOW, whiteSpace: 'nowrap' }}>{l.slice(0, n)}{(n < l.length && f >= a) || (last && n === l.length && Math.floor(f / 14) % 2 === 0) ? <span style={{ display: 'inline-block', width: size * 0.08, height: size * 0.72, background: ACCENT_EP, marginLeft: size * 0.06 }} /> : null}</div>; })}</div>; }
  else body = <Unredact lines={q} top={top} size={size} f0={6} step={10} x={150} exitAt={d - 8} />;
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})` }}>
    {body}
    {s.params.sub ? <Mono text={s.params.sub} f0={30} size={26} color={MUTED} style={{ position: 'absolute', left: 156, top: top + q.length * size * 0.98 + 40 }} /> : null}
  </SceneBg>;
};

const ChapterCard: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const v = s.variant ?? 'hairline_index';
  if (P.end) {
    return <SceneBg>
      <Unredact lines={['REAL STORY']} top={380} size={190} f0={8} />
      <Mono text={P.line1} f0={40} size={28} color={BONE} style={{ position: 'absolute', left: 0, right: 0, top: 610, textAlign: 'center' }} />
      <Mono text={P.line2} f0={58} size={20} color={MUTED} weight={400} style={{ position: 'absolute', left: 0, right: 0, top: 664, textAlign: 'center' }} />
    </SceneBg>;
  }
  const hp = interpolate(f, [10, 26], [0, 1], { ...C, easing: (t) => 1 - Math.pow(1 - t, 4) });
  const size = fitSize([P.title], 200, 1600);
  if (v === 'big_index') return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <div style={{ position: 'absolute', right: 140, top: 60, ...DISP(560, 62, 900), color: rgba(ACCENT_EP, 0.2 * hp), lineHeight: 1 }}>{String(P.n).padStart(2, '0')}</div>
    <div style={{ position: 'absolute', left: 150, top: 480, height: size * 1.05, overflow: 'hidden' }}><div style={{ ...DISP(size), color: BONE, transform: `translateY(${(1 - hp) * 100}%)`, lineHeight: `${size}px`, whiteSpace: 'nowrap' }}>{P.title}</div></div>
    <Mono text={`CHAPTER ${P.n} OF ${P.total}`} f0={20} size={26} color={MUTED} style={{ position: 'absolute', left: 156, top: 480 + size * 1.1 }} />
  </SceneBg>;
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <Mono text={String(P.n).padStart(2, '0') + ' / ' + String(P.total).padStart(2, '0')} f0={2} size={30} color={ACCENT_EP} style={{ position: 'absolute', left: 154, top: 380 }} />
    <div style={{ position: 'absolute', left: 150, top: 440, height: size * 1.05, overflow: 'hidden' }}><div style={{ ...DISP(size), color: BONE, transform: `translateY(${(1 - hp) * 100}%)`, lineHeight: `${size}px`, whiteSpace: 'nowrap' }}>{P.title}</div></div>
    <Hairline x={154} y={460 + size * 1.05} w={1500} f0={4} dur={26} />
  </SceneBg>;
};

const BigNumber: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const v = s.variant ?? 'odometer';
  const up = interpolate(f, [26, 40], [0, 1], { ...C, easing: out });
  const fill = interpolate(f, [6, Math.min(d - 10, 50)], [0, 1], { ...C, easing: io });
  const digits = P.value.toLocaleString('en-US').length + (P.pre ?? '').length; const size = Math.min(400, Math.floor(1100 / (digits * 0.5)));
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})` }}>
    <Mono text={P.label} f0={2} size={30} color={MUTED} style={{ position: 'absolute', left: 154, top: 250 }} />
    <div style={{ position: 'absolute', left: 146, top: 320, display: 'flex', alignItems: 'flex-end', gap: 36 }}>
      {P.pre ? <span style={{ ...DISP(size, 62, 880), lineHeight: `${size * 0.86}px`, color: MUTED, textShadow: SHADOW }}>{P.pre}</span> : null}
      {v === 'fill_count'
        ? <span style={{ ...DISP(size, 62, 880), lineHeight: `${size * 0.86}px`, color: BONE, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW }}>{Math.round(P.value * fill).toLocaleString('en-US')}</span>
        : <Odometer value={P.value} size={size} f0={6} />}
      <div style={{ ...DISP(Math.min(150, size * 0.4), 62, 840), color: ACCENT_EP, opacity: up, transform: `translateY(${(1 - up) * 30}px)`, marginBottom: 6, textShadow: SHADOW }}>{P.unit}</div>
    </div>
    <Hairline x={154} y={704} w={1100} f0={30} />
    <Mono text={P.note} f0={44} size={28} color={BONE} style={{ position: 'absolute', left: 154, top: 736 }} />
    <svg width={1920} height={1080} style={{ position: 'absolute' }}><polyline fill="none" stroke={rgba(TINT, 0.45)} strokeWidth={2}
      points={Array.from({ length: Math.max(2, Math.floor(160 * f / d)) }, (_, i) => `${154 + i * 10},${900 + 14 * Math.sin(i * 0.23 + 1.3) * Math.sin(i * 0.051)}`).join(' ')} /></svg>
  </SceneBg>;
};

const TimelineScroll: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const P = s.params; const d = durF(s); const ev: string[][] = P.events; const v = s.variant ?? 'rail_travel';
  const at = (i: number) => 6 + i * ((d - 24) / Math.max(1, ev.length)) * 0.8;
  if (v === 'vertical_drop') return <SceneBg drift={0.3} style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}><line x1={400} y1={200} x2={400} y2={200 + 680 * interpolate(f, [4, d - 10], [0, 1], { ...C, easing: io })} stroke={ACCENT_EP} strokeWidth={4} /></svg>
    {ev.map((e, i) => { const p = spring({ frame: f - at(i), fps, config: SPRING_SOFT }); const hl = i === P.hl; const y = 200 + i * (680 / Math.max(1, ev.length - 1)) - 40;
      return <div key={i} style={{ position: 'absolute', left: 150, top: y, display: 'flex', alignItems: 'center', gap: 60, opacity: Math.min(1, p * 1.5), transform: `translateY(${(1 - p) * -60}px)` }}>
        <span style={{ fontFamily: FONT.mono, fontSize: 40, letterSpacing: 3, color: hl ? ACCENT_EP : MUTED, width: 210, textAlign: 'right' }}>{e[0]}</span>
        <span style={{ width: 22, height: 22, background: hl ? ACCENT_EP : BONE, flexShrink: 0 }} />
        <span style={{ ...DISP(hl ? 120 : 84), color: BONE, textShadow: SHADOW, whiteSpace: 'nowrap' }}>{e[1]}</span></div>; })}
  </SceneBg>;
  if (v === 'calendar_tear') {
    const per = (d - 20) / ev.length; const k = Math.min(ev.length - 1, Math.floor(Math.max(0, f - 6) / per)); const tp = interpolate((f - 6) % per, [per - 10, per], [0, 1], C);
    return <SceneBg drift={0.3}>
      {ev.map((e, i) => { if (i < k || i > k + 1) return null; const top = i === k; const tear = top && k < ev.length - 1 ? tp : 0; const hl = i === P.hl;
        return <div key={i} style={{ position: 'absolute', left: 560, top: 170, width: 800, height: 660, background: PAPER, boxShadow: '0 40px 100px rgba(0,0,0,0.55)', zIndex: top ? 2 : 1, transformOrigin: '50% 0%', transform: `rotateX(${tear * 80}deg) translateY(${tear * -200}px) rotate(${tear * -6}deg)`, opacity: 1 - tear * 0.8 }}>
          <div style={{ height: 90, background: hl ? ACCENT_EP : '#3a3646', display: 'flex', alignItems: 'center', paddingLeft: 40, fontFamily: FONT.mono, fontSize: 30, letterSpacing: 4, color: hl ? '#1b1822' : BONE }}>JANUARY 2022</div>
          <div style={{ ...DISP(200, 62, 880), color: '#1b1822', textAlign: 'center', marginTop: 60 }}>{e[0]}</div>
          <div style={{ fontFamily: FONT.mono, fontSize: 44, letterSpacing: 3, color: '#4a4652', textAlign: 'center', marginTop: 40, textTransform: 'uppercase' }}>{e[1]}</div></div>; })}
    </SceneBg>;
  }
  const gap = P.gap ?? 600; const x0 = 200; const span = Math.max(0, x0 + (ev.length - 1) * gap + 700 - 1920); const cam = interpolate(f, [8, d - 20], [0, span], { ...C, easing: io });
  return <SceneBg drift={-0.6}>
    <div style={{ position: 'absolute', left: 0, top: 0, width: 6000, height: 1080, transform: `translateX(${-cam}px)` }}>
      <svg width={6000} height={1080} style={{ position: 'absolute' }}><line x1={0} y1={560} x2={x0 + gap * (ev.length - 1) + 1300} y2={560} stroke={rgba(TINT, 0.4)} strokeWidth={2} />
        <line x1={0} y1={560} x2={x0 + cam + 400} y2={560} stroke={ACCENT_EP} strokeWidth={5} /></svg>
      {ev.map((e, i) => { const x = x0 + i * gap; const hl = i === P.hl; const p = spring({ frame: f - at(i), fps, config: SPRING_SOFT });
        return <div key={i} style={{ position: 'absolute', left: x - 14, top: 546 }}>
          <div style={{ width: 22, height: 22, marginLeft: 7, marginTop: 7, background: hl ? ACCENT_EP : BONE, transform: `scale(${p})` }} />
          <div style={{ position: 'absolute', left: 0, top: -120, fontFamily: FONT.mono, fontSize: 40, letterSpacing: 4, color: hl ? ACCENT_EP : BONE, whiteSpace: 'nowrap', opacity: p }}>{e[0]}</div>
          <div style={{ position: 'absolute', left: 0, top: 70, ...DISP(hl ? 100 : 72), lineHeight: 0.95, color: BONE, textShadow: SHADOW, width: hl ? 760 : 520, opacity: p, transform: `translateY(${(1 - p) * 30}px)` }}>{e[1]}</div>
        </div>; })}
    </div>
  </SceneBg>;
};

// Wall clock: minutes of the day t0 -> t1. Variants: flip_digits, mission_clock (digital + bar), clock_dial (analogue dial).
const CounterTicker: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const v = s.variant ?? 'mission_clock';
  const p = interpolate(f, [6, d - 18], [0, 1], { ...C, easing: io }); const t = P.t0 + (P.t1 - P.t0) * p; const txt = hhmm(t);
  const push = `scale(${interpolate(f, [0, d], [1, 1.04], C)})`;
  if (v === 'clock_dial') {
    const cx = 1420, cy = 540, R = 300; const hA = ((t / 60) % 12) / 12 * 360, mA = (t % 60) / 60 * 360;
    const hand = (a: number, l: number, w: number, c: string) => <line x1={cx} y1={cy} x2={cx + l * Math.sin(a * Math.PI / 180)} y2={cy - l * Math.cos(a * Math.PI / 180)} stroke={c} strokeWidth={w} strokeLinecap="round" />;
    const sweep0 = ((P.t0 % 60) / 60) * 360; const sweep = Math.min(359.9, ((t - P.t0) / 60) * 360);
    const arc = (a0: number, a1: number, r: number) => { const p0 = [cx + r * Math.sin(a0 * Math.PI / 180), cy - r * Math.cos(a0 * Math.PI / 180)], p1 = [cx + r * Math.sin(a1 * Math.PI / 180), cy - r * Math.cos(a1 * Math.PI / 180)]; return `M${p0[0]} ${p0[1]} A${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${p1[0]} ${p1[1]}`; };
    return <SceneBg style={{ transform: push }}>
      <svg width={1920} height={1080} style={{ position: 'absolute' }}>
        <circle cx={cx} cy={cy} r={R} fill="none" stroke={rgba(TINT, 0.5)} strokeWidth={3} />
        {Array.from({ length: 60 }, (_, i) => { const a = i * 6 * Math.PI / 180; const l = i % 5 ? 14 : 34; return <line key={i} x1={cx + (R - l) * Math.sin(a)} y1={cy - (R - l) * Math.cos(a)} x2={cx + R * Math.sin(a)} y2={cy - R * Math.cos(a)} stroke={i % 5 ? rgba(TINT, 0.5) : BONE} strokeWidth={i % 5 ? 2 : 4} />; })}
        {sweep > 1 ? <path d={arc(sweep0, sweep0 + sweep, R - 60)} fill="none" stroke={ACCENT_EP} strokeWidth={14} opacity={0.85} /> : null}
        {hand(hA + (t % 60) / 2, 150, 12, BONE)}{hand(mA, 230, 6, ACCENT_EP)}<circle cx={cx} cy={cy} r={12} fill={BONE} />
      </svg>
      <Mono text={P.label} f0={2} size={28} color={MUTED} style={{ position: 'absolute', left: 154, top: 300 }} />
      <div style={{ position: 'absolute', left: 140, top: 350, fontFamily: FONT.mono, fontWeight: 500, fontSize: 210, color: BONE, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW, lineHeight: 1 }}>{txt}<span style={{ fontSize: 70, color: MUTED, marginLeft: 24 }}>{P.unit}</span></div>
      {P.note ? <Mono text={P.note} f0={30} size={26} color={BONE} style={{ position: 'absolute', left: 154, top: 620 }} /> : null}
    </SceneBg>;
  }
  if (v === 'flip_digits') {
    return <SceneBg style={{ transform: push }}>
      <Mono text={P.label} f0={2} size={30} color={MUTED} style={{ position: 'absolute', left: 154, top: 300 }} />
      <div style={{ position: 'absolute', left: 150, top: 370, display: 'flex', gap: 14 }}>
        {txt.split('').map((c, i) => { const prev = hhmm(t - 1).split('')[i]; const flip = c !== prev ? (f % 4) / 4 : 1;
          return c === ':' ? <span key={i} style={{ fontFamily: FONT.mono, fontSize: 260, color: MUTED, lineHeight: '330px' }}>:</span>
            : <span key={i} style={{ width: 190, height: 330, background: rgba(TINT, 0.08), display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT.mono, fontWeight: 500, fontSize: 260, color: BONE, transform: `scaleY(${0.6 + 0.4 * flip})`, position: 'relative' }}>{c}<span style={{ position: 'absolute', left: 0, right: 0, top: 164, height: 3, background: GROUND }} /></span>; })}
        <span style={{ fontFamily: FONT.mono, fontSize: 90, color: MUTED, alignSelf: 'flex-end', marginLeft: 20 }}>{P.unit}</span>
      </div>
      {P.note ? <Mono text={P.note} f0={30} size={26} color={BONE} style={{ position: 'absolute', left: 154, top: 760 }} /> : null}
    </SceneBg>;
  }
  return <SceneBg style={{ transform: push }}>
    <Mono text={P.label} f0={2} size={30} color={MUTED} style={{ position: 'absolute', left: 154, top: 280 }} />
    <div style={{ position: 'absolute', left: 140, top: 330, fontFamily: FONT.mono, fontWeight: 500, fontSize: 300, color: BONE, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW, lineHeight: 1 }}>{txt}<span style={{ fontSize: 100, color: MUTED, marginLeft: 30 }}>{P.unit}</span></div>
    <div style={{ position: 'absolute', left: 154, top: 680, width: 1300, height: 6, background: rgba(TINT, 0.25) }}><div style={{ width: `${p * 100}%`, height: 6, background: ACCENT_EP }} /></div>
    <Mono text={hhmm(P.t0)} f0={8} size={24} color={MUTED} style={{ position: 'absolute', left: 154, top: 706 }} />
    <Mono text={hhmm(P.t1)} f0={8} size={24} color={ACCENT_EP} style={{ position: 'absolute', left: 1360, top: 706 }} />
    {P.note ? <Mono text={P.note} f0={30} size={28} color={BONE} style={{ position: 'absolute', left: 154, top: 780 }} /> : null}
  </SceneBg>;
};

// Schematics: the cut cable (default), the air pressing on the sea (push), air and sea in step (resonance).
const DiagramBuild: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const draw = interpolate(f, [4, 40], [0, 1], { ...C, easing: io });
  const sea = 640;
  let art: React.ReactNode;
  if (P.mode === 'push' || P.mode === 'resonance') {
    const res = P.mode === 'resonance'; const x = interpolate(f, [6, d - 6], [-200, 2100], C);
    const amp = (xx: number) => { const k = (xx - x) / 160; const env = Math.exp(-k * k); const grow = res ? interpolate(xx, [0, 1920], [0.4, 1.6], C) : 1; return env * 26 * grow * draw; };
    const pts = Array.from({ length: 97 }, (_, i) => { const xx = i * 20; return `${xx},${sea + amp(xx + 60) - (res ? 0 : 0)}`; }).join(' ');
    const floor = res ? Array.from({ length: 97 }, (_, i) => { const xx = i * 20; return `${xx},${880 + 120 * Math.sin(Math.min(1, Math.max(0, (xx - 300) / 1300)) * Math.PI) * (xx > 300 && xx < 1600 ? 1 : 0)}`; }).join(' ') : '0,900 1920,900';
    art = <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <polyline points={`0,1080 ${floor} 1920,1080`} fill={rgba(TINT, 0.12)} stroke={rgba(TINT, 0.6)} strokeWidth={2} opacity={draw} />
      <polyline points={pts} fill="none" stroke={BONE} strokeWidth={4} />
      {[0, 1, 2, 3, 4].map((k) => <g key={k} opacity={draw}><line x1={x - 60 + k * 30} y1={330} x2={x - 60 + k * 30} y2={sea - 40} stroke={ACCENT_EP} strokeWidth={4} /><path d={`M${x - 72 + k * 30} ${sea - 58} L${x - 60 + k * 30} ${sea - 34} L${x - 48 + k * 30} ${sea - 58}`} fill="none" stroke={ACCENT_EP} strokeWidth={4} /></g>)}
      <text x={x - 60} y={310} fontFamily={FONT.mono} fontSize={24} letterSpacing={3} fill={ACCENT_EP} opacity={draw}>AIR PULSE · 310 M/S →</text>
      {res ? <text x={1640} y={1040} textAnchor="end" fontFamily={FONT.mono} fontSize={22} letterSpacing={3} fill={MUTED} opacity={draw}>DEEP TRENCH: SEA WAVE ≈ AIR SPEED</text> : <text x={60} y={980} fontFamily={FONT.mono} fontSize={22} letterSpacing={3} fill={MUTED} opacity={draw}>OCEAN</text>}
    </svg>;
  } else {
    // islands, the cable to Fiji, a slide breaking it
    const cut = interpolate(f, [Math.round(d * 0.45), Math.round(d * 0.45) + 10], [0, 1], C);
    const slide = interpolate(f, [Math.round(d * 0.25), Math.round(d * 0.5)], [0, 1], { ...C, easing: io });
    art = <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <path d={`M0 ${sea} L1920 ${sea}`} stroke={rgba(TINT, 0.5)} strokeWidth={2} />
      <path d="M120 640 Q220 560 330 640 Z" fill={rgba(TINT, 0.3)} stroke={BONE} strokeWidth={2} opacity={draw} />
      <text x={130} y={540} fontFamily={FONT.mono} fontSize={22} letterSpacing={3} fill={MUTED} opacity={draw}>TONGA</text>
      <path d="M1640 640 Q1740 570 1840 640 Z" fill={rgba(TINT, 0.3)} stroke={BONE} strokeWidth={2} opacity={draw} />
      <text x={1650} y={540} fontFamily={FONT.mono} fontSize={22} letterSpacing={3} fill={MUTED} opacity={draw}>FIJI</text>
      <path d="M0 1000 Q500 860 960 900 T1920 980 L1920 1080 L0 1080 Z" fill={rgba(TINT, 0.1)} />
      <path d={`M240 640 Q300 900 700 920 L${700 + 260 * (1 - cut * 0.2)} 925`} fill="none" stroke={ACCENT_EP} strokeWidth={5} strokeDasharray={`${2400 * draw} 3000`} />
      <path d={`M${1000 + 30 * cut} 935 L1500 930 Q1700 900 1740 640`} fill="none" stroke={ACCENT_EP} strokeWidth={5} strokeDasharray={`${2400 * draw} 3000`} opacity={draw} />
      {[0, 1, 2, 3, 4, 5].map((k) => <circle key={k} cx={420 + slide * 600 + k * 26} cy={800 + slide * 120 - k * 6} r={14 - k} fill={rgba(BONE, 0.5)} opacity={slide > 0 && slide < 1 ? 1 : 0.4 * (slide > 0 ? 1 : 0)} />)}
      {cut > 0 ? <g><line x1={960} y1={890} x2={1000} y2={960} stroke={BONE} strokeWidth={4} /><line x1={1000} y1={890} x2={960} y2={960} stroke={BONE} strokeWidth={4} /></g> : null}
    </svg>;
  }
  return <SceneBg drift={0.3} style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})` }}>
    {art}
    <div style={{ position: 'absolute', left: 150, top: 150 }}><Line text={P.label} f0={8} x={0} y={0} size={fitSize([P.label], 96)} /></div>
    {P.note ? <Mono text={P.note} f0={Math.round(d * 0.4)} size={24} color={MUTED} style={{ position: 'absolute', left: 156, top: 270 }} /> : null}
  </SceneBg>;
};

// Vertical section: sky (plume height), sea (depth) or trench. layers: [km, label], hl = highlighted layer.
const CutawaySection: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const layers: [number, string][] = P.layers; const sky = P.mode === 'sky';
  const max = Math.max(...layers.map((l) => l[0])) * 1.08; const y0 = sky ? 960 : 180, H = 760;
  const yOf = (km: number) => sky ? y0 - (km / max) * H : y0 + (km / max) * H;
  const rev = interpolate(f, [0, d * 0.55], [0.08, 1], { ...C, easing: io });
  const cam = s.variant === 'depth_drop' ? interpolate(f, [0, d], [0, -120], { ...C, easing: io }) : 0;
  return <SceneBg drift={0.2}>
    <AbsoluteFill style={{ transform: `translateY(${cam}px)` }}>
      <svg width={1920} height={1080} style={{ position: 'absolute' }}>
        <defs><linearGradient id="cs" x1="0" y1={sky ? 1 : 0} x2="0" y2={sky ? 0 : 1}><stop offset="0%" stopColor={rgba(TINT, 0.22)} /><stop offset="100%" stopColor={rgba(TINT, 0.02)} /></linearGradient></defs>
        <rect x={980} y={sky ? yOf(max * rev) : y0} width={760} height={Math.abs(yOf(max * rev) - y0)} fill="url(#cs)" />
        <clipPath id="plclip"><rect x={0} y={yOf(max * rev)} width={1920} height={1080} /></clipPath>
        {sky ? <path clipPath="url(#plclip)" d={`M1340 ${y0} C1320 ${yOf(25)} 1240 ${yOf(45)} 1160 ${yOf(57)} Q1360 ${yOf(60)} 1560 ${yOf(57)} C1480 ${yOf(45)} 1400 ${yOf(25)} 1380 ${y0} Z`} fill={rgba(ACCENT_EP, 0.25)} stroke={ACCENT_EP} strokeWidth={3} /> : null}
        {P.mode === 'trench' ? <path d={`M980 ${yOf(4)} L1240 ${yOf(4)} L1330 ${yOf(10.8)} L1400 ${yOf(10.8)} L1490 ${yOf(4)} L1740 ${yOf(4)} L1740 ${yOf(max)} L980 ${yOf(max)} Z`} fill={rgba(TINT, 0.25)} stroke={BONE} strokeWidth={2} opacity={rev} /> : null}
        {P.mode === 'sea' ? <rect x={980} y={yOf(4)} width={760} height={y0 + H - yOf(4)} fill={rgba(TINT, 0.25)} opacity={rev} /> : null}
        <line x1={980} y1={y0} x2={1740} y2={y0} stroke={BONE} strokeWidth={3} />
        {layers.map(([km, label], i) => { const y = yOf(km); const on = rev * max >= km * 0.98; const hl = i === P.hl;
          return <g key={i} opacity={on ? 1 : 0}><line x1={hl ? 900 : 940} y1={y} x2={1760} y2={y} stroke={hl ? ACCENT_EP : rgba(TINT, 0.7)} strokeWidth={hl ? 4 : 2} strokeDasharray={hl ? undefined : '10 8'} />
            <text x={880} y={y + 10} textAnchor="end" fontFamily={FONT.mono} fontSize={hl ? 34 : 26} letterSpacing={3} fill={hl ? ACCENT_EP : BONE}>{label}</text></g>; })}
      </svg>
    </AbsoluteFill>
    {(() => { const h = layers[P.hl ?? layers.length - 1][0]; const q = interpolate(f, [d * 0.35, d * 0.65], [0, 1], { ...C, easing: io });
      return <div style={{ position: 'absolute', left: 150, top: sky ? 150 : 560, ...DISP(170, 62, 880), color: ACCENT_EP, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums', opacity: Math.min(1, q * 4) }}>{(h * q).toFixed(Number.isInteger(h) ? 0 : 1)}<span style={{ fontSize: 80, color: MUTED, marginLeft: 20 }}>KM</span></div>; })()}
  </SceneBg>;
};

// Formula card: the formula sets in big type, then each term lights up with its value.
const FormulaCard: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const terms: [string, string][] = P.terms;
  const fp = interpolate(f, [4, 22], [0, 1], { ...C, easing: out });
  const per = (d * 0.55) / terms.length; const derive = s.variant === 'derive';
  return <SceneBg drift={0.2} style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <div style={{ position: 'absolute', left: 150, top: 200, fontFamily: FONT.quote, fontStyle: 'italic', fontWeight: 400, fontSize: 210, color: BONE, textShadow: SHADOW, opacity: fp, transform: `translateY(${(1 - fp) * 40}px)`, letterSpacing: '0.02em' }}>
      {derive ? <span>{P.formula.split('').map((c: string, i: number) => <span key={i} style={{ color: c === 'h' ? ACCENT_EP : BONE }}>{c}</span>)}</span> : P.formula}
    </div>
    {terms.map(([k, val], i) => { const a = 20 + i * per; const p = interpolate(f, [a, a + 12], [0, 1], { ...C, easing: out }); const last = i === terms.length - 1;
      return <div key={i} style={{ position: 'absolute', left: 160 + i * 540, top: 600, opacity: p, transform: `translateY(${(1 - p) * 30}px)` }}>
        <div style={{ fontFamily: FONT.quote, fontStyle: 'italic', fontSize: 90, color: last ? ACCENT_EP : MUTED }}>{k}</div>
        <div style={{ ...DISP(last ? 120 : 96), color: last ? ACCENT_EP : BONE, textShadow: SHADOW, whiteSpace: 'nowrap' }}>{val}</div></div>; })}
  </SceneBg>;
};

const ChartBarRace: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const bars: [string, number][] = P.bars; const max = Math.max(...bars.map((b) => b[1]));
  const p = interpolate(f, [4, d - 14], [0, 1], { ...C, easing: io });
  return <SceneBg drift={0.3}>
    {bars.map(([label, v], i) => { const w = 1300 * (v / max) * p; const y = 330 + i * 300;
      return <div key={i}>
        <div style={{ position: 'absolute', left: 150, top: y - 80, fontFamily: FONT.mono, fontSize: 30, letterSpacing: 4, color: i === 0 ? ACCENT_EP : MUTED }}>{label}</div>
        <div style={{ position: 'absolute', left: 150, top: y, width: w, height: 110, background: i === 0 ? ACCENT_EP : rgba(TINT, 0.55) }} />
        <div style={{ position: 'absolute', left: 170 + w, top: y - 4, ...DISP(120), color: BONE, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>{Math.round(v * p)}<span style={{ color: MUTED, fontSize: 60, marginLeft: 14 }}>{P.unit}</span></div>
      </div>; })}
  </SceneBg>;
};

// Evidence board: three cards pinned, strings drawn between them, a source note.
const EvidenceBoard: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const d = durF(s); const P = s.params; const cards: [string, string][] = P.cards;
  const pos = [[220, 200], [820, 420], [1360, 180]]; const rot = [-3, 2, -2];
  const cam = interpolate(f, [0, d], [1, 1.12], { ...C, easing: io }); const pan = interpolate(f, [0, d], [0, -50], { ...C, easing: io });
  return <SceneBg drift={0.2} style={{ transform: `scale(${cam}) translateX(${pan}px)`, transformOrigin: '55% 45%' }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>{cards.slice(1).map((_, i) => { const a = pos[i], b = pos[i + 1]; const p = interpolate(f, [20 + i * 18, 40 + i * 18], [0, 1], { ...C, easing: io });
      const x1 = a[0] + 170, y1 = a[1] + 20, x2 = b[0] + 170, y2 = b[1] + 20; return <line key={i} x1={x1} y1={y1} x2={x1 + (x2 - x1) * p} y2={y1 + (y2 - y1) * p} stroke={ACCENT_EP} strokeWidth={4} />; })}</svg>
    {cards.map(([big, small], i) => { const p = spring({ frame: f - 2 - i * 9, fps, config: { damping: 16, stiffness: 110 } });
      return <div key={i} style={{ position: 'absolute', left: pos[i][0], top: pos[i][1], width: 340, height: 300, background: PAPER, boxShadow: '0 30px 70px rgba(0,0,0,0.55)', transform: `rotate(${rot[i]}deg) scale(${0.6 + 0.4 * p})`, opacity: Math.min(1, p * 2), padding: 30 }}>
        <div style={{ position: 'absolute', left: 160, top: 8, width: 22, height: 22, borderRadius: 11, background: ACCENT_EP }} />
        <div style={{ ...DISP(big.length > 5 ? 64 : 140, 62, 880), color: '#1b1822', marginTop: 40 }}>{big}</div>
        <div style={{ fontFamily: FONT.mono, fontSize: 28, letterSpacing: 3, color: '#4a4652', marginTop: 16 }}>{small}</div></div>; })}
    <Mono text={P.note} f0={Math.round(d * 0.5)} size={26} color={MUTED} style={{ position: 'absolute', left: 220, top: 860 }} />
  </SceneBg>;
};

// 2 hPa as height: floors stack up beside an elevator, the pressure counter follows.
const ScaleCompare: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const p = interpolate(f, [6, d - 14], [0, 1], { ...C, easing: io });
  const floors = 5, fh = 130, x = 1180, base = 900;
  return <SceneBg drift={0.3}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {Array.from({ length: floors }, (_, i) => { const on = p * floors > i; return <g key={i} opacity={on ? 1 : 0.15}><rect x={x} y={base - (i + 1) * fh} width={420} height={fh - 8} fill={rgba(TINT, 0.12)} stroke={BONE} strokeWidth={2} />
        <text x={x + 440} y={base - i * fh - 50} fontFamily={FONT.mono} fontSize={24} fill={MUTED}>{i + 1}</text></g>; })}
      <rect x={x + 150} y={base - fh * floors * p - 4} width={120} height={fh - 16} fill={ACCENT_EP} />
      <line x1={x - 40} y1={base} x2={x + 520} y2={base} stroke={BONE} strokeWidth={3} />
    </svg>
    <div style={{ position: 'absolute', left: 150, top: 300, ...DISP(260, 62, 880), color: BONE, textShadow: SHADOW }}>{(2 * p).toFixed(1)}<span style={{ fontSize: 120, color: ACCENT_EP, marginLeft: 20, textTransform: 'none' }}>hPa</span></div>
    <Mono text={P.eq} f0={Math.round(d * 0.5)} size={34} color={BONE} style={{ position: 'absolute', left: 156, top: 600 }} />
  </SceneBg>;
};

// Real data plots. line_draw: our 41 front positions + the fit; isd: Sydney Airport QNH; scope_trace: our distance-time image.
export const Plot: React.FC<{ x: number; y: number; w: number; h: number; xr: [number, number]; yr: [number, number]; xt: [number, string][]; yt: [number, string][]; children: (X: (v: number) => number, Y: (v: number) => number) => React.ReactNode; xl?: string; yl?: string }> = ({ x, y, w, h, xr, yr, xt, yt, children, xl, yl }) => {
  const X = (v: number) => x + ((v - xr[0]) / (xr[1] - xr[0])) * w, Y = (v: number) => y + h - ((v - yr[0]) / (yr[1] - yr[0])) * h;
  return <svg width={1920} height={1080} style={{ position: 'absolute' }}>
    <line x1={x} y1={y + h} x2={x + w} y2={y + h} stroke={rgba(TINT, 0.7)} strokeWidth={2} /><line x1={x} y1={y} x2={x} y2={y + h} stroke={rgba(TINT, 0.7)} strokeWidth={2} />
    {xt.map(([v, t], i) => <g key={'x' + i}><line x1={X(v)} y1={y + h} x2={X(v)} y2={y + h + 12} stroke={rgba(TINT, 0.7)} strokeWidth={2} /><text x={X(v)} y={y + h + 46} textAnchor="middle" fontFamily={FONT.mono} fontSize={22} fill={MUTED}>{t}</text></g>)}
    {yt.map(([v, t], i) => <g key={'y' + i}><line x1={x} y1={Y(v)} x2={x + w} y2={Y(v)} stroke={rgba(TINT, 0.12)} strokeWidth={1} /><text x={x - 18} y={Y(v) + 8} textAnchor="end" fontFamily={FONT.mono} fontSize={22} fill={MUTED}>{t}</text></g>)}
    {xl ? <text x={x + w} y={y + h + 90} textAnchor="end" fontFamily={FONT.mono} fontSize={20} letterSpacing={3} fill={MUTED}>{xl}</text> : null}
    {yl ? <text x={x} y={y - 24} fontFamily={FONT.mono} fontSize={20} letterSpacing={3} fill={MUTED}>{yl}</text> : null}
    {children(X, Y)}
  </svg>;
};
const DataPlotReal: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const v = s.variant ?? 'line_draw';
  if (v === 'scope_trace') {
    const sweep = interpolate(f, [4, d - 10], [0, 1], { ...C, easing: io });
    return <AbsoluteFill style={{ backgroundColor: GROUND }}>
      <MCam id={s.media_ids![0]} from={[0.45, 0.5, 1.0]} to={[0.55, 0.5, 1.15]} dur={d} filter="grayscale(1) brightness(2.8) contrast(1.35)" />
      <div style={{ position: 'absolute', left: 1920 * sweep, top: 0, width: 3, height: 1080, background: ACCENT_EP, opacity: 0.8, boxShadow: `0 0 20px ${ACCENT_EP}` }} />
      <Shade top={0.5} bottom={0.75} />
      <Mono text="DISTANCE FROM THE VOLCANO ↑ · TIME →" f0={6} size={22} color={MUTED} style={{ position: 'absolute', left: 90, top: 120 }} />
      {P.label ? <Line text={P.label} f0={12} y={850} size={fitSize([P.label], 92)} /> : null}
    </AbsoluteFill>;
  }
  if (P.mode === 'isd') {
    const pts: [number, number, string][] = D.isd; const draw = interpolate(f, [4, d * 0.7], [0, 1], { ...C, easing: io });
    const xr: [number, number] = [0, 720]; const shown = pts.filter((q) => q[0] <= xr[0] + (xr[1] - xr[0]) * draw);
    return <SceneBg drift={0.2}>
      <Plot x={200} y={260} w={1440} h={520} xr={xr} yr={[1000, 1007]} xl="UTC, 15 JAN 2022" yl="QNH, hPa · SYDNEY AIRPORT"
        xt={[0, 120, 240, 360, 480, 600, 720].map((m) => [m, hhmm(m)])} yt={[1001, 1003, 1005].map((v) => [v, String(v)])}>{(X, Y) => <>
          <line x1={X(449)} y1={260} x2={X(449)} y2={780} stroke={ACCENT_EP} strokeWidth={2} strokeDasharray="10 8" opacity={draw > 0.55 ? 1 : 0} />
          <text x={X(449) + 12} y={290} fontFamily={FONT.mono} fontSize={20} fill={ACCENT_EP} opacity={draw > 0.55 ? 1 : 0}>PREDICTED 07:29</text>
          <polyline points={shown.map((q) => `${X(q[0])},${Y(q[1])}`).join(' ')} fill="none" stroke={BONE} strokeWidth={3} />
          {shown.map((q, i) => <circle key={i} cx={X(q[0])} cy={Y(q[1])} r={q[2] === 'SPECI' ? 11 : 5} fill={q[2] === 'SPECI' ? ACCENT_EP : BONE} />)}
        </>}</Plot>
      {P.label ? <Line text={P.label} f0={Math.round(d * 0.55)} y={860} size={fitSize([P.label], 92)} /> : null}
    </SceneBg>;
  }
  const pts: [number, number][] = D.front; const draw = interpolate(f, [4, d * 0.6], [0, 1], { ...C, easing: io }); const fit = interpolate(f, [d * 0.6, d * 0.85], [0, 1], { ...C, easing: io });
  const n = Math.floor(pts.length * draw); const [a, b] = D.fit; // km = a + b*min
  return <SceneBg drift={0.2}>
    <Plot x={240} y={200} w={1400} h={600} xr={[300, 720]} yr={[0, 8500]} xl="TIME, UTC" yl="DISTANCE FROM THE VOLCANO, KM"
      xt={[300, 360, 420, 480, 540, 600, 660, 720].map((m) => [m, hhmm(m)])} yt={[2000, 4000, 6000, 8000].map((v) => [v, v.toLocaleString('en-US')])}>{(X, Y) => <>
        {pts.slice(0, n).map((q, i) => <circle key={i} cx={X(q[0])} cy={Y(q[1])} r={7} fill={BONE} />)}
        <line x1={X(300)} y1={Y(a + b * 300)} x2={X(300 + 420 * fit)} y2={Y(a + b * (300 + 420 * fit))} stroke={ACCENT_EP} strokeWidth={5} />
      </>}</Plot>
    <div style={{ position: 'absolute', left: 1180, top: 520, opacity: fit, ...DISP(110), color: ACCENT_EP, textShadow: SHADOW }}>310 M/S</div>
    <Mono text="41 POINTS · ONE STRAIGHT LINE" f0={Math.round(d * 0.3)} size={24} color={BONE} style={{ position: 'absolute', left: 240, top: 900 }} />
  </SceneBg>;
};

// Globe route: the camera travels from A to B; the great-circle arc draws with the km readout.
const GlobeRoute: React.FC<{ s: Shot; land: any; land50: any }> = ({ s, land }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const v = s.variant ?? 'night_side';
  const p = interpolate(f, [10, d - 16], [0, 1], { ...C, easing: io });
  const pts = (P.via ? [P.from, P.via, P.to] : [P.from, P.to]) as [number, number][]; const R = makeRoute(pts);
  if (v === 'flat_unroll') {
    const proj = geoEquirectangular().scale(300).translate([960, 540]).rotate([60, 0]); const path = geoPath(proj);
    const unroll = interpolate(f, [0, 20], [0.6, 1], { ...C, easing: out });
    return <SceneBg>
      <AbsoluteFill style={{ transform: `scaleY(${unroll})` }}><svg width={1920} height={1080} style={{ position: 'absolute' }}>
        <path d={path(land) || ''} fill={rgba(TINT, 0.22)} stroke={rgba(TINT, 0.6)} strokeWidth={1.2} />
        <path d={path(R.upTo(p)) || ''} fill="none" stroke={ACCENT_EP} strokeWidth={5} />
        {[P.from, P.to].map((c: any, i: number) => { const q = proj(c)!; return <g key={i} opacity={i === 0 || p > 0.95 ? 1 : 0}><circle cx={q[0]} cy={q[1]} r={10} fill={i ? ACCENT_EP : BONE} /><text x={q[0] + (i ? -16 : 18)} y={q[1] - 20} textAnchor={i ? 'end' : 'start'} fontFamily={FONT.mono} fontSize={26} letterSpacing={3} fill={BONE}>{P.labels[i]}</text></g>; })}
      </svg></AbsoluteFill>
      <div style={{ position: 'absolute', left: 150, top: 860, ...DISP(110), color: BONE, textShadow: SHADOW, opacity: interpolate(f, [d * 0.5, d * 0.5 + 10], [0, 1], C) }}>{P.km}</div>
    </SceneBg>;
  }
  const c = R.along(p); const scale = 420 - 50 * Math.sin(Math.PI * p);
  return <SceneBg at="60% 50%" gridOpacity={0.3} drift={-0.4}>
    <Globe land={land} center={c} scale={scale} cx={1150} cy={560} overlay={(proj, vis) => {
      const arc = geoPath(proj)(R.upTo(p)) || ''; const pa = proj(P.from), pb = proj(P.to);
      return <>
        {v === 'night_side' ? <circle cx={1150 + scale * 0.35} cy={560} r={scale} fill={rgba(GROUND, 0.25)} /> : null}
        {v === 'terminator_line' ? <path d={geoPath(proj)({ type: 'LineString', coordinates: Array.from({ length: 181 }, (_, i) => [P.from[0] + 90, -90 + i]) } as any) || ''} fill="none" stroke={rgba(BONE, 0.35)} strokeWidth={2} strokeDasharray="6 8" /> : null}
        <path d={arc} fill="none" stroke={ACCENT_EP} strokeWidth={5} strokeLinecap="round" />
        {vis(P.from) ? <g><circle cx={pa[0]} cy={pa[1]} r={10} fill={BONE} /><text x={pa[0] + 22} y={pa[1] + 8} fontFamily={FONT.mono} fontSize={24} letterSpacing={3} fill={BONE}>{P.labels[0]}</text></g> : null}
        {vis(P.to) && p > 0.8 ? <g><Pin x={pb[0]} y={pb[1]} f0={Math.round(10 + (d - 26) * 0.82)} /><text x={pb[0] + 26} y={pb[1] + 10} fontFamily={FONT.mono} fontSize={28} letterSpacing={3} fill={ACCENT_EP}>{P.labels[1]}</text></g> : null}
      </>; }} />
    <div style={{ position: 'absolute', left: 120, top: 820, ...DISP(130), color: BONE, textShadow: SHADOW }}>{Math.round(R.km * p / 100) * 100 > 0 ? (Math.round(R.km * p / 100) * 100).toLocaleString('en-US') : '0'}<span style={{ color: ACCENT_EP, fontSize: 70, marginLeft: 16 }}>KM</span></div>
  </SceneBg>;
};

// Flat map. dive: zoom from a wide view in; pan_along: slow lateral move; topo_lines: rings spread from the first pin.
const MapZoom: React.FC<{ s: Shot; land: any }> = ({ s, land }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const v = s.variant ?? 'dive';
  const z = v === 'dive' ? Math.pow(8, interpolate(f, [0, d * 0.7], [-1, 0], { ...C, easing: io })) : 1;
  const pan = v === 'pan_along' ? interpolate(f, [0, d], [-4, 4], C) * (P.scale > 3000 ? 0.05 : 1) : 0;
  const center: [number, number] = [P.center[0] + pan, P.center[1]];
  return <FlatMap land={land} center={center} scale={P.scale * z} dur={d} push={0.06}>{(proj) => <>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {P.rings ? (() => { const o = proj(P.pins[0]); const tgt = proj(P.pins[1]); const Rmax = Math.hypot(tgt[0] - o[0], tgt[1] - o[1]); const rp = interpolate(f, [10, d - 10], [0, 1], C);
        return [0, 1, 2].map((k) => { const r = ((rp + k / 3) % 1) * Rmax * 1.2; return <circle key={k} cx={o[0]} cy={o[1]} r={r} fill="none" stroke={ACCENT_EP} strokeWidth={3} opacity={1 - r / (Rmax * 1.2)} />; }); })() : null}
      {P.trench ? (() => { const a = proj([-175.6, -16.5]), b = proj([-173.2, -26]); return <path d={`M${a[0]} ${a[1]} Q${(a[0] + b[0]) / 2 + 120} ${(a[1] + b[1]) / 2} ${b[0]} ${b[1]}`} stroke={rgba(TINT, 0.7)} strokeWidth={22} fill="none" strokeLinecap="round" opacity={0.5} />; })() : null}
      {P.pins.map((pn: any, i: number) => { const q = proj([pn[0], pn[1]]); return <g key={i}><Pin x={q[0]} y={q[1]} f0={8 + i * 14} />
        <text x={q[0] + 26} y={q[1] - 22} fontFamily={FONT.mono} fontSize={26} letterSpacing={3} fill={BONE} style={{ textShadow: SHADOW }} opacity={f > 12 + i * 14 ? 1 : 0}>{pn[2]}</text></g>; })}
    </svg>
    {P.label ? <Line text={P.label} f0={14} x={90} y={850} size={fitSize([P.label], 84)} /> : null}
  </>}</FlatMap>;
};

// ---------- transitions + chrome ----------
const TransitionIn: React.FC<{ kind?: string; children: React.ReactNode }> = ({ kind, children }) => {
  const f = useCurrentFrame();
  if (kind === 'dissolve') return <AbsoluteFill style={{ opacity: interpolate(f, [0, 14], [0, 1], C) }}>{children}</AbsoluteFill>;
  if (kind === 'push') { const p = interpolate(f, [0, 12], [1, 0], { ...C, easing: out }); return <AbsoluteFill style={{ transform: `scale(${1 + p * 0.12})`, opacity: 1 - p * 0.9 }}>{children}</AbsoluteFill>; }
  return <AbsoluteFill>{children}</AbsoluteFill>;
};
const Chrome: React.FC<{ s: Shot }> = ({ s }) => {
  const ch = chapterOf(s); const t = s.scene_type;
  const showCh = ch && !['chapter_card', 'kinetic_type', 'question_card'].includes(t);
  return <>{showCh ? <Tag text={`${String(ch![0]).padStart(2, '0')}  ${ch![1]}`} f0={8} x={60} y={56} size={18} color={ACCENT_EP} /> : null}
    {s.source_line ? <Tag text={s.source_line.toUpperCase()} f0={14} x={60} y={1080 - 58} size={16} color={rgba(BONE, 0.75)} /> : null}</>;
};
const Scene: React.FC<{ s: Shot; l110: any; l50: any }> = ({ s, l110, l50 }) => {
  switch (s.scene_type) {
    case 'film_clip': return <FilmClip s={s} />;
    case 'photo_parallax': return <PhotoParallax s={s} />;
    case 'photo_detail_zoom': return <PhotoDetailZoom s={s} />;
    case 'photo_lighttable': return <PhotoLighttable s={s} />;
    case 'photo_compare': return <PhotoCompare s={s} />;
    case 'satellite_reveal': return <SatelliteReveal s={s} />;
    case 'document_highlight': return <DocumentHighlight s={s} />;
    case 'kinetic_type': return <KineticType s={s} />;
    case 'question_card': return <QuestionCard s={s} />;
    case 'chapter_card': return <ChapterCard s={s} />;
    case 'big_number': return <BigNumber s={s} />;
    case 'timeline_scroll': return <TimelineScroll s={s} />;
    case 'counter_ticker': return <CounterTicker s={s} />;
    case 'diagram_build': return <DiagramBuild s={s} />;
    case 'cutaway_section': return <CutawaySection s={s} />;
    case 'formula_card': return <FormulaCard s={s} />;
    case 'chart_bar_race': return <ChartBarRace s={s} />;
    case 'evidence_board': return <EvidenceBoard s={s} />;
    case 'scale_compare': return <ScaleCompare s={s} />;
    case 'data_plot_real': return <DataPlotReal s={s} />;
    case 'globe_route': return <GlobeRoute s={s} land={l110} land50={l50} />;
    case 'map_zoom': return <MapZoom s={s} land={l50} />;
    case 'custom': { const Comp = CUSTOM[s.custom!.component]; return Comp ? <Comp s={s} d={durF(s)} land={l110} land50={l50} /> : <SceneBg />; }
    default: return <SceneBg />;
  }
};
export const SFX: Record<string, [string, number]> = { whoosh: ['sfx/whoosh-fast.mp3', 0.3], whoosh_big: ['sfx/whoosh-big.mp3', 0.25], impact: ['sfx/impact-deep-whoosh.mp3', 0.35], hit: ['sfx/impact-deep-whoosh.mp3', 0.22], paper: ['sfx/paper-slide.mp3', 0.4], swoosh: ['sfx/swoosh-slow.mp3', 0.25], riser_soft: ['sfx/swoosh-slow.mp3', 0.18], rumble: ['sfx2/rumble.wav', 0.5], sub_drop: ['sfx2/drone.wav', 0.25], tick: ['sfx2/tick.wav', 0.4], type: ['sfx2/typewriter.wav', 0.3], shutter: ['sfx2/shutter.wav', 0.4] };

export const Episode: React.FC = () => { const l110 = useLand('countries-110m.json'); const l50 = useLand('countries-50m.json');
  return <Finish>
    {SHOTS.map((s) => <Sequence key={s.id} from={Math.round(s.params.start_s * FPS)} durationInFrames={durF(s) + 1} premountFor={45} name={`${s.id} ${s.scene_type}`}>
      <TransitionIn kind={s.transition_in}>{l110 && l50 ? <Scene s={s} l110={l110} l50={l50} /> : null}</TransitionIn><Chrome s={s} />
      {(s.sfx ?? []).filter((k) => SFX[k]).map((k, i) => <Audio key={i} src={staticFile(SFX[k][0])} volume={SFX[k][1]} />)}
    </Sequence>)}
    <Audio src={staticFile('ep/voice.wav')} />
    <Audio src={staticFile('ep/music.wav')} />
  </Finish>; };
