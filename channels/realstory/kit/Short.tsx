// Real Story Shorts: vertical-native 1080x1920 cuts of an episode (plan: src/ep/shorts.json, made by rs-shorts).
// Every layout is composed for 9:16. No landscape frame is ever placed in a vertical box.
import React from 'react';
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from 'remotion';
import PLAN from './ep/shorts.json';
import WORDS from './ep/words.json';
import { MEDIA } from './Episode';
import { ACCENT_EP, BONE, C, FG, FG_MUTED, SCRIM, INK_PHOTO, OnPhoto, DISP, FONT, GROUND, GROUND2, MUTED, PAPER, SHADOW, SIGNAL, TINT, io, out, rgba } from './kit/tokens';
import { Kinetic, Mono, Odometer, StopBlock, Unredact } from './kit/Type';
import { Grain } from './kit/Brand';
import { FlatMap, Pin, useLand } from './kit/Geo';
import { VCUSTOM } from './custom';

const FPS = 30, W = 1080, H = 1920, X0 = 80;
// size that fits the longest line into the 9:16 text column (Archivo at wdth 62 ≈ 0.5 em per capital)
const fit = (lines: string[], max: number) => Math.min(max, Math.floor(900 / (Math.max(...lines.map((l) => l.length)) * 0.5)));
type VShot = { id: string; layout: string; start_s: number; duration_s: number; media_ids?: string[]; params?: any };
type Short = { id: string; line_ids: string[]; start_s: number; end_s: number; hook_text: string; shots: VShot[] };
const SOUNDS: { media_id: string; start: number; seconds: number; from_s: number; gain?: number }[] = (WORDS as any).sounds ?? [];
export const SHORTS = (PLAN as any).shorts as Short[];
export const shortFrames = (s: Short) => Math.round((s.shots[s.shots.length - 1].start_s + s.shots[s.shots.length - 1].duration_s) * FPS);
const med = (id: string) => staticFile('ep/' + MEDIA[id].src);
const Bg: React.FC<{ children?: React.ReactNode }> = ({ children }) =>
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 38%, ${GROUND2} 0%, ${GROUND} 75%)` }}>{children}</AbsoluteFill>;
const Shade = () => <AbsoluteFill style={{ background: `linear-gradient(180deg, ${rgba(SCRIM, 0.55)} 0%, ${rgba(SCRIM, 0)} 22%, ${rgba(SCRIM, 0)} 55%, ${rgba(SCRIM, 0.75)} 100%)` }} />;

// A 9:16 camera into a photo: the crop follows from→to ([x, y, zoom], image fractions), clamped inside the image.
const VPhoto: React.FC<{ id: string; from: number[]; to: number[]; d: number; filter?: string }> = ({ id, from, to, d, filter }) => {
  const f = useCurrentFrame(); const m = MEDIA[id]; const p = interpolate(f, [0, d], [0, 1], { ...C, easing: io });
  const z = from[2] * Math.pow(to[2] / from[2], p); const s = Math.max(W / m.w, H / m.h); const iw = m.w * s, ih = m.h * s;
  const cx = Math.min(Math.max((from[0] + (to[0] - from[0]) * p) * iw, W / 2 / z), iw - W / 2 / z);
  const cy = Math.min(Math.max((from[1] + (to[1] - from[1]) * p) * ih, H / 2 / z), ih - H / 2 / z);
  return <AbsoluteFill style={{ overflow: 'hidden', background: '#000' }}>
    <Img src={med(id)} style={{ position: 'absolute', left: 0, top: 0, width: iw, height: ih, transformOrigin: '0 0', transform: `translate(${W / 2}px,${H / 2}px) scale(${z}) translate(${-cx}px,${-cy}px)`, filter }} /></AbsoluteFill>;
};
// ---- layouts ----
const VPhotoPan: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const P = s.params ?? {}; const f = useCurrentFrame();
  const b0 = s.start_s < 0.3 ? 68 : 2; // the hook owns the first two seconds
  const big = P.big ? interpolate(f, [b0, b0 + 10], [0, 1], { ...C, easing: out }) : 0;
  return <OnPhoto.Provider value={true}><AbsoluteFill>
    <VPhoto id={s.media_ids![0]} from={P.from ?? [0.5, 0.5, 1]} to={P.to ?? [0.5, 0.5, 1.1]} d={d} filter={P.illustration ? 'sepia(0.15) contrast(1.05)' : 'contrast(1.06)'} />
    <Shade />
    {P.big ? <div style={{ position: 'absolute', left: 0, right: 0, top: 640, textAlign: 'center', ...DISP(fit([P.big], 300), 62, 880), color: INK_PHOTO.accent, textShadow: INK_PHOTO.shadow, transform: `scale(${0.85 + 0.15 * big})`, opacity: big }}>{P.big}</div> : null}
    {P.illustration ? <Mono text="ILLUSTRATION · AI-GENERATED" f0={4} size={20} style={{ position: 'absolute', left: X0, top: 250 }} /> : null}
  </AbsoluteFill></OnPhoto.Provider>;
};
const VFilm: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params ?? {}; const z = 1 + 0.06 * interpolate(f, [0, d], [0, 1], C);
  const m = MEDIA[s.media_ids![0]]; const k = P.unpillar ?? (P.pillar43 ? 1.335 : undefined) ?? (PLAN as any).unpillar ?? 1; // 1.335 for 4:3 film inside a 16:9 file
  const h = H * 1.0, w = (h * m.w) / m.h * k; // a 9:16 window travels across the clip
  const x = (P.x ?? 0.5) * (w - W);
  return <OnPhoto.Provider value={true}><AbsoluteFill style={{ background: '#000', overflow: 'hidden' }}>
    <div style={{ position: 'absolute', left: -x, top: 0, width: w, height: h, transform: `scale(${z})`, transformOrigin: `${x + W / 2}px 50%` }}>
      <OffthreadVideo src={med(s.media_ids![0])} startFrom={Math.round((P.trim ?? 1) * FPS)} muted style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'contrast(1.06)' }} /></div>
    <Shade />
  </AbsoluteFill></OnPhoto.Provider>;
};
const VType: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const P = s.params; const n = P.lines.length; const size = fit(P.lines, 250);
  const top = 840 - (n * size * 0.98) / 2;
  return <Bg>
    {P.variant === 'unredact'
      ? <Unredact lines={P.lines} top={top} size={size} x={X0} f0={2} step={6} exitAt={d - 6} />
      : <Kinetic lines={P.lines.map((l: string) => [l])} top={top} size={size} x={X0} f0={2} step={4} variant="rise_narrow" accent={P.accent !== undefined ? [P.accent, 0] : undefined} exitAt={d - 6} />}
    {P.sub ? <Mono text={P.sub} f0={10} size={30} color={ACCENT_EP} style={{ position: 'absolute', left: X0, top: top + n * size * 0.98 + 36 }} /> : null}
  </Bg>;
};
const VNumber: React.FC<{ s: VShot; d: number }> = ({ s }) => {
  const P = s.params; const f = useCurrentFrame(); const up = interpolate(f, [20, 32], [0, 1], { ...C, easing: out });
  return <Bg>
    <Mono text={P.label} f0={0} size={34} color={ACCENT_EP} style={{ position: 'absolute', left: X0, top: 500 }} />
    <div style={{ position: 'absolute', left: X0 - 10, top: 570 }}><Odometer value={P.value} size={String(P.value).length > 4 ? 250 : String(P.value).length > 3 ? 330 : 400} f0={2} dur={22} /></div>
    <div style={{ position: 'absolute', left: X0, top: 920, ...DISP(170), color: FG, opacity: up }}>{P.unit}</div>
    <Mono text={P.note} f0={24} size={28} color={FG_MUTED} style={{ position: 'absolute', left: X0, top: 1110 }} />
  </Bg>;
};
const VQuote: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const P = s.params; const f = useCurrentFrame(); const words = P.quote.split(' '); const per = Math.max(5, Math.floor((d - 30) / words.length));
  return <Bg>
    <Mono text={P.name} f0={0} size={26} style={{ position: 'absolute', left: X0, top: 470 }} />
    <div style={{ position: 'absolute', left: X0, right: 120, top: 530, fontFamily: FONT.quote, fontStyle: 'italic', fontWeight: 420, fontSize: P.quote.length > 110 ? 90 : 124, lineHeight: 1.04, color: FG, textShadow: SHADOW }}>
      {words.map((w: string, i: number) => { const p = interpolate(f, [4 + i * per, 12 + i * per], [0, 1], C); return <span key={i} style={{ opacity: p, filter: `blur(${(1 - p) * 6}px)`, color: (P.hl && w.toLowerCase().includes(P.hl)) || (P.accent && w.replace(/[^\w]/g, '').toLowerCase() === String(P.accent).toLowerCase()) ? ACCENT_EP : FG }}>{w} </span>; })}
    </div>
  </Bg>;
};
const VDoc: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const P = s.params; const f = useCurrentFrame(); const i0 = P.text.indexOf(P.hl);
  const sweep = interpolate(f, [24, 70], [0, 1], C); const cam = interpolate(f, [0, d], [1, 1.1], { ...C, easing: io });
  return <Bg>
    <div style={{ position: 'absolute', left: 70, right: 70, top: 560, padding: '56px 56px 64px', background: PAPER, transform: `rotate(-1deg) scale(${cam})`, boxShadow: '0 40px 100px rgba(0,0,0,.55)' }}>
      <div style={{ fontFamily: FONT.mono, fontSize: 22, letterSpacing: '0.12em', color: '#5a5a55', paddingBottom: 18, borderBottom: '2px solid #bdb8aa' }}>{P.id}</div>
      <div style={{ fontFamily: FONT.mono, fontSize: 44, lineHeight: 1.5, color: '#2a2a28', marginTop: 26 }}>
        {P.text.slice(0, i0)}<span style={{ backgroundImage: `linear-gradient(90deg, ${rgba(ACCENT_EP, 0.85)} ${sweep * 100}%, transparent ${sweep * 100}%)` }}>{P.hl}</span>{P.text.slice(i0 + P.hl.length)}</div>
    </div>
  </Bg>;
};
// VDelay: a signal crawling from one body to another (radio delay), the delay in big type under it
const VDelay: React.FC<{ d: number; s: VShot }> = ({ d, s }) => {
  const f = useCurrentFrame(); const P = s.params; const y0 = 330, y1 = 1000, X = 540;
  const p = interpolate(f, [8, d - 10], [0, 1], { ...C, easing: io }); const yp = y0 + (y1 - y0) * p;
  const arrive = interpolate(f, [d - 14, d - 6], [0, 1], C); const up = interpolate(f, [4, 16], [0, 1], { ...C, easing: out });
  return <Bg>
    <svg width={W} height={H} style={{ position: 'absolute' }}>
      <line x1={X} y1={y0} x2={X} y2={y1} stroke={rgba(TINT, 0.35)} strokeWidth={3} strokeDasharray="4 14" />
      <line x1={X} y1={y0} x2={X} y2={yp} stroke={ACCENT_EP} strokeWidth={5} />
      <circle cx={X} cy={yp} r={14} fill={ACCENT_EP} opacity={1 - arrive} />
      <circle cx={X} cy={y0} r={46} fill="#b4552c" /><circle cx={X} cy={y1} r={46} fill="#3d6f9e" stroke={rgba(FG, arrive)} strokeWidth={6} />
    </svg>
    <Mono text="MARS" f0={2} size={30} color={FG} style={{ position: 'absolute', left: X + 80, top: y0 - 16 }} />
    <Mono text="EARTH" f0={2} size={30} color={FG} style={{ position: 'absolute', left: X + 80, top: y1 - 16 }} />
    <div style={{ position: 'absolute', left: X0, top: 1110, opacity: up, ...DISP(230, 62, 880), color: FG, textShadow: SHADOW }}>{P.big}</div>
    <Mono text={P.note} f0={10} size={28} color={ACCENT_EP} style={{ position: 'absolute', left: X0, top: 1360 }} />
  </Bg>;
};
const VClock: React.FC<{ d: number }> = ({ d }) => {
  const f = useCurrentFrame(); const CX = 540, CY = 640, R = 330;
  const pt = (deg: number, r: number) => [CX + r * Math.sin((deg * Math.PI) / 180), CY - r * Math.cos((deg * Math.PI) / 180)];
  const p = interpolate(f, [6, Math.min(d - 12, 70)], [0, 1], { ...C, easing: io }); const t = 600 + 101 * p;
  const hd = ((t / 60) * 30) % 360, md = (t % 60) * 6; const [x0, y0] = pt(300, R - 110), [x1, y1] = pt(hd, R - 110);
  return <Bg>
    <svg width={W} height={H} style={{ position: 'absolute' }}>
      <circle cx={CX} cy={CY} r={R} fill="none" stroke={rgba(TINT, 0.35)} strokeWidth={2} />
      {Array.from({ length: 60 }, (_, i) => { const b = i % 5 === 0; const [a, c] = pt(i * 6, R - (b ? 34 : 16)), [e, g] = pt(i * 6, R - 4); return <line key={i} x1={a} y1={c} x2={e} y2={g} stroke={b ? FG : rgba(TINT, 0.6)} strokeWidth={b ? 4 : 2} />; })}
      <path d={`M${CX} ${CY} L${x0} ${y0} A${R - 110} ${R - 110} 0 0 1 ${x1} ${y1} Z`} fill={rgba(ACCENT_EP, 0.28)} stroke={ACCENT_EP} strokeWidth={3} />
      {(() => { const [x, y] = pt(md, R - 40); return <line x1={CX} y1={CY} x2={x} y2={y} stroke={FG} strokeWidth={6} />; })()}
      {(() => { const [x, y] = pt(hd, R - 130); return <line x1={CX} y1={CY} x2={x} y2={y} stroke={ACCENT_EP} strokeWidth={14} />; })()}
      <circle cx={CX} cy={CY} r={12} fill={FG} />
    </svg>
    <div style={{ position: 'absolute', left: 0, right: 0, top: 1010, display: 'flex', justifyContent: 'center', alignItems: 'flex-end', gap: 24 }}>
      <Odometer value={101} size={230} f0={6} dur={Math.min(d - 20, 60)} /><div style={{ ...DISP(100), color: ACCENT_EP }}>MIN</div></div>
  </Bg>;
};
const FR: Record<string, { at: [number, number]; z: number; filter?: string }> = {
  m_a1000: { at: [0.608, 0.743], z: 3.4, filter: 'brightness(2.2) contrast(1.15) saturate(0.3)' }, m_a260: { at: [0.338, 0.5], z: 1.6 }, m_a210: { at: [0.324, 0.6], z: 1.5 } };
const VDockingHud: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const ids = s.media_ids!; const seg = d / ids.length; const k = Math.min(ids.length - 1, Math.floor(f / seg)); const lf = f - k * seg;
  const fr = FR[ids[k]]; const lock = interpolate(lf, [3, 18], [0, 1], { ...C, easing: out }); const rs = 200 - 80 * lock;
  const prev = k ? s.params.ranges[k - 1] : 1400; const rv = Math.round(interpolate(lf, [2, 18], [prev, s.params.ranges[k]], { ...C, easing: io }));
  const ax = 540, ay = 760; const tick = (x: number, y: number, dx: number, dy: number) => `M${x + dx * 40} ${y} L${x} ${y} L${x} ${y + dy * 40}`;
  return <AbsoluteFill style={{ background: '#000' }}>
    <AbsoluteFill style={{ transform: `translateY(${ay - H / 2}px) scale(1.3)` }}><VPhoto id={ids[k]} from={[fr.at[0], fr.at[1], fr.z]} to={[fr.at[0], fr.at[1], fr.z * 1.05]} d={Math.round(seg)} filter={fr.filter} /></AbsoluteFill>
    <svg width={W} height={H} style={{ position: 'absolute', filter: 'drop-shadow(0 0 6px rgba(0,0,0,.7))' }}>
      <line x1={ax} y1={ay - rs - 140} x2={ax} y2={ay - 24} stroke={rgba(BONE, 0.55 * lock)} strokeWidth={2} /><line x1={ax} y1={ay + 24} x2={ax} y2={ay + rs + 140} stroke={rgba(BONE, 0.55 * lock)} strokeWidth={2} />
      <line x1={ax - rs - 120} y1={ay} x2={ax - 24} y2={ay} stroke={rgba(BONE, 0.55 * lock)} strokeWidth={2} /><line x1={ax + 24} y1={ay} x2={ax + rs + 120} y2={ay} stroke={rgba(BONE, 0.55 * lock)} strokeWidth={2} />
      <path d={[tick(ax - rs, ay - rs, 1, 1), tick(ax + rs, ay - rs, -1, 1), tick(ax - rs, ay + rs, 1, -1), tick(ax + rs, ay + rs, -1, -1)].join(' ')} fill="none" stroke={lock > 0.98 ? ACCENT_EP : BONE} strokeWidth={4} />
    </svg>
    <div style={{ position: 'absolute', left: 0, right: 0, top: 1180, textAlign: 'center' }}>
      <div style={{ fontFamily: FONT.mono, fontSize: 26, letterSpacing: '0.14em', color: MUTED, textShadow: INK_PHOTO.shadow }}>RANGE TO AGENA · FRAME {k + 1}/3</div>
      <div style={{ ...DISP(200, 62, 860), color: BONE, textShadow: INK_PHOTO.shadow }}>~{rv.toLocaleString('en-US')}<span style={{ ...DISP(100), color: INK_PHOTO.accent, marginLeft: 14 }}>FT</span></div></div>
    <AbsoluteFill style={{ background: '#fff', opacity: k ? interpolate(lf, [0, 4], [0.85, 0], C) : 0 }} />
  </AbsoluteFill>;
};
// ---- vertical-native data layouts ----
// A crop of a spectrogram's plot area (image fractions [x0,y0,x1,y1]) scaled to `boxH` px tall, panned so `head` (0-1 of plot width) stays centred.
const PlotStrip: React.FC<{ id: string; plot: number[]; top: number; boxH: number; head: number; playing: number }> = ({ id, plot, top, boxH, head, playing }) => {
  const m = MEDIA[id]; const [x0, y0, x1, y1] = plot; const k = boxH / ((y1 - y0) * m.h); const iw = m.w * k, ih = m.h * k;
  const pl = x0 * iw, pw = (x1 - x0) * iw; const hx = pl + head * pw;
  const bw = Math.min(W, pw), bl = (W - bw) / 2; // the box never shows the image's axes or margins
  const camL = pw <= W ? pl : Math.min(Math.max(hx - W / 2, pl), pl + pw - W);
  return <div style={{ position: 'absolute', left: bl, top, width: bw, height: boxH, overflow: 'hidden' }}>
    <Img src={med(id)} style={{ position: 'absolute', left: -camL, top: -y0 * ih, width: iw, height: ih, filter: 'contrast(1.08)' }} />
    <div style={{ position: 'absolute', left: hx - camL - 2, top: 0, width: 4, height: boxH, background: ACCENT_EP, opacity: playing, boxShadow: `0 0 18px ${ACCENT_EP}` }} />
  </div>;
};
const VSpectro: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const P = s.params; const f = useCurrentFrame(); const m = MEDIA[s.media_ids![0]];
  const play = P.play_at !== undefined; const a = (P.play_at ?? 0) * FPS, b = a + (P.play_dur ?? 0) * FPS;
  const head = play ? interpolate(f, [a, b], [P.ph0, P.ph1], C) : interpolate(f, [0, d], [P.pan0 ?? 0.15, P.pan1 ?? 0.45], { ...C, easing: io });
  const on = play ? interpolate(f, [a - 4, a + 2, b, b + 8], [0, 1, 1, 0], C) : 0;
  const boxH = Math.min(1000, P.box_h ?? 1000); const top = 860 - boxH / 2;
  return <Bg>
    <PlotStrip id={s.media_ids![0]} plot={P.plot} top={top} boxH={boxH} head={head} playing={on} />
    <div style={{ position: 'absolute', left: X0, top: top - 92, display: 'flex', alignItems: 'center', gap: 16 }}>
      <div style={{ width: 36, height: 4, background: ACCENT_EP }} />
      <Mono text={P.label} f0={2} size={34} weight={600} color={FG} /></div>
    <Mono text={play && f >= a - 4 ? P.listen : (P.sub ?? '')} f0={play ? Math.round(a) : 8} size={26} color={FG_MUTED} style={{ position: 'absolute', left: X0, top: top + boxH + 40 }} />
    {P.axes ? <><Mono text="TIME →" f0={10} size={22} style={{ position: 'absolute', right: 80, top: top + boxH + 40 }} /></> : null}
  </Bg>;
};
// Two plots stacked: the vertical frame's natural side-by-side.
const VStack: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const P = s.params; const f = useCurrentFrame(); const ids = s.media_ids!;
  return <Bg>{ids.map((id, i) => { const top = 330 + i * 760; const o = interpolate(f, [i * 10, i * 10 + 10], [0, 1], C);
    return <div key={id} style={{ opacity: o }}>
      <div style={{ position: 'absolute', left: X0, top: top - 80, display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ width: 36, height: 4, background: i ? ACCENT_EP : FG }} /><Mono text={P.labels[i]} f0={i * 10} size={34} weight={600} color={FG} /></div>
      <PlotStrip id={id} plot={P.plots[i]} top={top} boxH={560} head={P.heads[i]} playing={0} />
      <Mono text={P.subs[i]} f0={i * 10 + 6} size={24} style={{ position: 'absolute', left: X0, top: top + 580 }} /></div>; })}
  </Bg>;
};
const VMap: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const land = useLand('countries-50m.json'); const f = useCurrentFrame(); const P = s.params;
  if (!land) return null;
  return <FlatMap land={land} center={P.center} scale={P.scale} dur={d} push={0.08}>{(proj: any) => {
    const pins = P.pins as { at: [number, number]; label: string; t: number; kind?: string; anchor?: string; dy?: number }[];
    const lk = P.link ? interpolate(f, [P.link.t * FPS, P.link.t * FPS + 36], [0, 1], { ...C, easing: io }) : 0;
    const A = P.link ? proj(pins[P.link.a].at) : null, B = P.link ? proj(pins[P.link.b].at) : null;
    return <><svg width={W} height={H} style={{ position: 'absolute' }}>
      {A && B ? <line x1={A[0]} y1={A[1]} x2={A[0] + (B[0] - A[0]) * lk} y2={A[1] + (B[1] - A[1]) * lk} stroke={ACCENT_EP} strokeWidth={5} strokeDasharray="16 12" /> : null}
      {pins.map((p, i) => { const q = proj(p.at); const f0 = Math.round(p.t * FPS); if (f < f0) return null; return <g key={i}>
        {p.kind === 'ring' ? <circle cx={q[0]} cy={q[1]} r={70 + 6 * Math.sin(f / 6)} fill={rgba(SIGNAL, 0.12)} stroke={SIGNAL} strokeWidth={3} strokeDasharray="8 8" /> : <Pin x={q[0]} y={q[1]} f0={f0} />}
        <text x={q[0] + (p.anchor === 'end' ? -28 : p.anchor === 'middle' ? 0 : 28)} y={q[1] + (p.dy ?? 60)} fontFamily={FONT.mono} fontSize={30} letterSpacing={3} fill={FG} textAnchor={(p.anchor as any) ?? 'start'} style={{ textShadow: SHADOW } as any}>{p.label}</text></g>; })}
    </svg>
      {P.link?.label && A && B ? <div style={{ position: 'absolute', left: 0, right: 0, top: Math.min(A[1], B[1]) - 330, textAlign: 'center', ...DISP(170, 62, 900), color: ACCENT_EP, textShadow: SHADOW, opacity: interpolate(f, [P.link.t * FPS + 30, P.link.t * FPS + 40], [0, 1], C) }}>{P.link.label}</div> : null}
      {P.title ? <div style={{ position: 'absolute', left: X0, top: 300, display: 'flex', alignItems: 'center', gap: 16 }}><div style={{ width: 36, height: 4, background: ACCENT_EP }} /><Mono text={P.title} f0={4} size={34} weight={600} color={FG} /></div> : null}
    </>; }}</FlatMap>;
};
const Layout: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  switch (s.layout) {
    case 'v_photo_pan': return <VPhotoPan s={s} d={d} />;
    case 'v_film_crop': return <VFilm s={s} d={d} />;
    case 'v_type': return <VType s={s} d={d} />;
    case 'v_number': return <VNumber s={s} d={d} />;
    case 'v_quote': return <VQuote s={s} d={d} />;
    case 'v_doc': return <VDoc s={s} d={d} />;
    case 'v_custom': { const c = s.params.component; const V = (VCUSTOM as any)[c]; if (V) return <V s={s} d={d} />; return c === 'VDelay' ? <VDelay s={s} d={d} /> : c === 'VClock' ? <VClock d={d} /> : c === 'VDockingHud' ? <VDockingHud s={s} d={d} /> : <VSpectro s={s} d={d} />; }
    case 'v_photo_stack': return <VStack s={s} d={d} />;
    case 'v_map': return <VMap s={s} d={d} />;
    default: return <Bg><div style={{ color: SIGNAL, fontSize: 60 }}>NO LAYOUT {s.layout}</div></Bg>;
  }
};

// ---- one text layer at a time ----
// Picture shots get a bottom-left block: mono kicker (what we see) + the spoken phrase, built word by word.
// Type, number, quote, doc and custom shots carry their own words, so captions step aside there.
const TEXT_LAYOUTS = new Set(['v_type', 'v_number', 'v_quote', 'v_doc', 'v_custom', 'v_photo_stack', 'v_map']);
const WEAK = /^(the|a|an|of|in|at|on|to|and|but|or|was|were|is|with|for|from|about|what|their|his|her|its|that|this|by|as|into|than|then)$/i;
const phrases = (ws: any[]) => {
  const out: any[][] = []; let cur: any[] = [];
  ws.forEach((w, i) => {
    cur.push(w); const nx = ws[i + 1]; const len = cur.map((c) => c.w).join(' ').length;
    const punct = /[.,?!:;]$/.test(w.w) && !/^[A-Z]\.$/.test(w.w);
    const full = len + (nx ? nx.w.length + 1 : 0) > 22 || cur.length >= 4;
    if (!nx || punct || (full && !WEAK.test(w.w.replace(/[^\w]/g, '')))) { out.push(cur); cur = []; }
  });
  return out;
};
const clean = (w: string) => (/^[A-Z]\.$/.test(w) ? w : w.replace(/[.,!:;]$/, ''));
const Captions: React.FC<{ sh: Short }> = ({ sh }) => {
  const f = useCurrentFrame(); const t = sh.start_s + f / FPS; const ts = f / FPS;
  const shot = sh.shots.find((s) => ts >= s.start_s && ts < s.start_s + s.duration_s);
  if (!shot || TEXT_LAYOUTS.has(shot.layout) || (shot.params?.big && shot.start_s > 0.3)) return null;
  if (f < hookEnd(sh)) return null; // one text layer: the hook owns the opening
  const ws = (WORDS as any).words.filter((w: any) => sh.line_ids.includes(w.line_id));
  const ch = phrases(ws).find((c) => t >= c[0].start - 0.04 && t < c[c.length - 1].end + 0.2);
  const label = shot.params?.label; const lf = f - Math.round(shot.start_s * FPS);
  const lp = interpolate(lf, [3, 13], [0, 1], { ...C, easing: out });
  return <div style={{ position: 'absolute', left: X0, right: 170, bottom: 470, display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 22 }}>
    {label ? <div style={{ display: 'flex', alignItems: 'center', gap: 16, opacity: lp, transform: `translateX(${(1 - lp) * -16}px)` }}>
      <div style={{ width: 36, height: 4, background: INK_PHOTO.accent }} />
      <div style={{ fontFamily: FONT.mono, fontWeight: 600, fontSize: 34, letterSpacing: '0.1em', textTransform: 'uppercase', color: BONE, textShadow: INK_PHOTO.shadow }}>{label}</div></div> : null}
    {ch ? <div style={{ ...DISP(104, 70, 820), lineHeight: '98px', color: BONE, textShadow: INK_PHOTO.shadow }}>
      {ch.map((w, i) => { const on = interpolate(t, [w.start - 0.04, w.start + 0.06], [0, 1], C);
        return <span key={i} style={{ display: 'inline-block', marginRight: '0.22em', opacity: on, transform: `translateY(${(1 - on) * 14}px)` }}>{clean(w.w)}</span>; })}
    </div> : null}
  </div>;
};
const hookEnd = (sh: Short) => { const firstText = sh.shots.find((s) => s.start_s > 0.3 && (TEXT_LAYOUTS.has(s.layout) || s.params?.big));
  return Math.min(66, firstText ? Math.round(firstText.start_s * FPS) - 2 : 66); };
const Hook: React.FC<{ sh: Short }> = ({ sh }) => {
  const f = useCurrentFrame(); const endF = hookEnd(sh);
  const o = interpolate(f, [endF - 8, endF], [1, 0], C); if (o <= 0) return null;
  const words = sh.hook_text.split(' '); const size = fit([sh.hook_text.length > 14 ? sh.hook_text.slice(0, Math.ceil(sh.hook_text.length / 2)) : sh.hook_text], 150);
  return <div style={{ position: 'absolute', left: X0, right: 120, top: 210, opacity: o, textWrap: 'balance' as any, ...DISP(size, 62, 880), lineHeight: `${size * 0.94}px`, color: BONE, textShadow: INK_PHOTO.shadow }}>
    {words.slice(0, -1).join(' ')} <span style={{ whiteSpace: 'nowrap' }}>{words[words.length - 1]}<StopBlock size={size} /></span></div>;
};

export const ShortVideo: React.FC<{ id: string }> = ({ id }) => {
  const sh = SHORTS.find((x) => x.id === id)!; const total = shortFrames(sh);
  return <AbsoluteFill style={{ background: GROUND }}>
    {sh.shots.map((s) => { const from = Math.round(s.start_s * FPS), d = Math.round(s.duration_s * FPS);
      return <Sequence key={s.id} from={from} durationInFrames={d}><PunchIn d={d}><Layout s={s} d={d} /></PunchIn></Sequence>; })}
    <Captions sh={sh} />
    <Hook sh={sh} />
    <Grain opacity={0.07} />
    <Audio src={staticFile('ep/voice.wav')} startFrom={Math.round(sh.start_s * FPS)} endAt={Math.round(sh.start_s * FPS) + total} volume={(fr) => interpolate(fr, [total - 8, total], [1, 0], C)} />
    {/* the episode music bed (music_kit); plan.music overrides the file, plan.music_volume the gain */}
    <Audio src={staticFile((PLAN as any).music ?? 'ep/bed.wav')} startFrom={Math.round(sh.start_s * FPS)} endAt={Math.round(sh.start_s * FPS) + total} volume={(fr) => ((PLAN as any).music_volume ?? 1) * interpolate(fr, [0, 12, total - 24, total], [0, 1, 1, 0], C)} />
    {SOUNDS.filter((x) => x.start >= sh.start_s - 0.05 && x.start < sh.start_s + total / FPS).map((x, i) => { const fr = Math.round((x.start - sh.start_s) * FPS), n = Math.round(x.seconds * FPS);
      return <Sequence key={'snd' + i} from={fr} durationInFrames={n}><Audio src={med(x.media_id)} startFrom={Math.round(x.from_s * FPS)} volume={(q) => (x.gain ?? 1) * interpolate(q, [0, 6, n - 12, n], [0, 1, 1, 0], C)} /></Sequence>; })}
  </AbsoluteFill>;
};
const PunchIn: React.FC<{ children: React.ReactNode; d: number }> = ({ children, d }) => {
  const f = useCurrentFrame(); const z = interpolate(f, [0, 6], [1.06, 1], { ...C, easing: out }) * interpolate(f, [6, d], [1, 1.045], C);
  return <AbsoluteFill style={{ transform: `scale(${z})` }}>{children}</AbsoluteFill>;
};
