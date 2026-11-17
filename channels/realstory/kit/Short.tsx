// Real Story Shorts: vertical-native 1080x1920 cuts of an episode (plan: src/ep/shorts.json, made by rs-shorts).
// Every layout is composed for 9:16. No landscape frame is ever placed in a vertical box.
import React from 'react';
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from 'remotion';
import PLAN from './ep/shorts.json';
import WORDS from './ep/words.json';
import { MEDIA } from './Episode';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, GROUND2, MUTED, PAPER, SHADOW, SIGNAL, TINT, io, out, rgba } from './kit/tokens';
import { Kinetic, Mono, Odometer, StopBlock, Unredact } from './kit/Type';
import { Grain } from './kit/Brand';

const FPS = 30, W = 1080, H = 1920;
type VShot = { id: string; layout: string; start_s: number; duration_s: number; media_ids?: string[]; params?: any };
type Short = { id: string; line_ids: string[]; start_s: number; end_s: number; hook_text: string; shots: VShot[] };
export const SHORTS = (PLAN as any).shorts as Short[];
export const shortFrames = (s: Short) => Math.round((s.shots[s.shots.length - 1].start_s + s.shots[s.shots.length - 1].duration_s) * FPS);
const med = (id: string) => staticFile('ep/' + MEDIA[id].src);
const Bg: React.FC<{ children?: React.ReactNode }> = ({ children }) =>
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 38%, ${GROUND2} 0%, ${GROUND} 75%)` }}>{children}</AbsoluteFill>;
const Shade = () => <AbsoluteFill style={{ background: `linear-gradient(180deg, ${rgba(GROUND, 0.55)} 0%, ${rgba(GROUND, 0)} 22%, ${rgba(GROUND, 0)} 55%, ${rgba(GROUND, 0.75)} 100%)` }} />;

// A 9:16 camera into a photo: the crop follows from→to ([x, y, zoom], image fractions), clamped inside the image.
const VPhoto: React.FC<{ id: string; from: number[]; to: number[]; d: number; filter?: string }> = ({ id, from, to, d, filter }) => {
  const f = useCurrentFrame(); const m = MEDIA[id]; const p = interpolate(f, [0, d], [0, 1], { ...C, easing: io });
  const z = from[2] * Math.pow(to[2] / from[2], p); const s = Math.max(W / m.w, H / m.h); const iw = m.w * s, ih = m.h * s;
  const cx = Math.min(Math.max((from[0] + (to[0] - from[0]) * p) * iw, W / 2 / z), iw - W / 2 / z);
  const cy = Math.min(Math.max((from[1] + (to[1] - from[1]) * p) * ih, H / 2 / z), ih - H / 2 / z);
  return <AbsoluteFill style={{ overflow: 'hidden', background: '#000' }}>
    <Img src={med(id)} style={{ position: 'absolute', left: 0, top: 0, width: iw, height: ih, transformOrigin: '0 0', transform: `translate(${W / 2}px,${H / 2}px) scale(${z}) translate(${-cx}px,${-cy}px)`, filter }} /></AbsoluteFill>;
};
const Label: React.FC<{ text: string; f0?: number }> = ({ text, f0 = 6 }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [f0, f0 + 12], [0, 1], { ...C, easing: out });
  return <div style={{ position: 'absolute', left: 70, right: 70, top: 1000, ...DISP(76, 70, 800), color: BONE, textShadow: SHADOW, opacity: p, transform: `translateY(${(1 - p) * 20}px)` }}>{text}</div>;
};

// ---- layouts ----
const VPhotoPan: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const P = s.params ?? {}; const f = useCurrentFrame();
  const big = P.big ? interpolate(f, [2, 12], [0, 1], { ...C, easing: out }) : 0;
  return <AbsoluteFill>
    <VPhoto id={s.media_ids![0]} from={P.from ?? [0.5, 0.5, 1]} to={P.to ?? [0.5, 0.5, 1.1]} d={d} filter={P.illustration ? 'sepia(0.15) contrast(1.05)' : 'contrast(1.06)'} />
    <Shade />
    {P.big ? <div style={{ position: 'absolute', left: 0, right: 0, top: 640, textAlign: 'center', ...DISP(330, 62, 880), color: ACCENT_EP, textShadow: SHADOW, transform: `scale(${0.85 + 0.15 * big})`, opacity: big }}>{P.big}</div> : null}
    {P.label ? <Label text={P.label} /> : null}
    {P.illustration ? <Mono text="ILLUSTRATION · AI-GENERATED" f0={4} size={20} style={{ position: 'absolute', left: 70, top: 1080 }} /> : null}
  </AbsoluteFill>;
};
const VFilm: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params ?? {}; const z = 1 + 0.06 * interpolate(f, [0, d], [0, 1], C);
  const m = MEDIA[s.media_ids![0]]; const h = H * 1.0, w = (h * m.w) / m.h * 1.335; // 4:3 film inside 16:9: scale off the pillarbox
  const x = (P.x ?? 0.5) * (w - W);
  return <AbsoluteFill style={{ background: '#000', overflow: 'hidden' }}>
    <div style={{ position: 'absolute', left: -x, top: 0, width: w, height: h, transform: `scale(${z})`, transformOrigin: `${x + W / 2}px 50%` }}>
      <OffthreadVideo src={med(s.media_ids![0])} startFrom={Math.round((P.trim ?? 1) * FPS)} muted style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'contrast(1.06)' }} /></div>
    <Shade />{P.label ? <Label text={P.label} /> : null}
  </AbsoluteFill>;
};
const VType: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const P = s.params; const n = P.lines.length; const size = Math.max(...P.lines.map((l: string) => l.length)) > 8 ? 170 : 230;
  const top = 760 - (n * size * 0.98) / 2;
  return <Bg>
    {P.variant === 'unredact'
      ? <Unredact lines={P.lines} top={top} size={size} f0={2} step={6} exitAt={d - 6} />
      : <Kinetic lines={P.lines.map((l: string) => [l])} top={top} size={size} f0={2} step={4} variant="rise_narrow" accent={P.accent !== undefined ? [P.accent, 0] : undefined} exitAt={d - 6} />}
    {P.sub ? <Mono text={P.sub} f0={10} size={30} style={{ position: 'absolute', left: 0, right: 0, textAlign: 'center', top: top + n * size * 0.98 + 40 }} /> : null}
  </Bg>;
};
const VNumber: React.FC<{ s: VShot; d: number }> = ({ s }) => {
  const P = s.params; const f = useCurrentFrame(); const up = interpolate(f, [20, 32], [0, 1], { ...C, easing: out });
  return <Bg>
    <Mono text={P.label} f0={0} size={34} style={{ position: 'absolute', left: 0, right: 0, textAlign: 'center', top: 470 }} />
    <div style={{ position: 'absolute', left: 0, right: 0, top: 540, display: 'flex', justifyContent: 'center' }}><Odometer value={P.value} size={380} f0={2} dur={22} /></div>
    <div style={{ position: 'absolute', left: 0, right: 0, top: 880, textAlign: 'center', ...DISP(150), color: ACCENT_EP, opacity: up }}>{P.unit}</div>
    <Mono text={P.note} f0={24} size={26} color={rgba(BONE, 0.7)} style={{ position: 'absolute', left: 0, right: 0, textAlign: 'center', top: 1060 }} />
  </Bg>;
};
const VQuote: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const P = s.params; const f = useCurrentFrame(); const words = P.quote.split(' '); const per = Math.max(5, Math.floor((d - 30) / words.length));
  return <Bg>
    <Mono text={P.name} f0={0} size={26} style={{ position: 'absolute', left: 90, top: 520 }} />
    <div style={{ position: 'absolute', left: 84, right: 84, top: 590, fontFamily: FONT.quote, fontStyle: 'italic', fontWeight: 420, fontSize: 112, lineHeight: 1.05, color: BONE, textShadow: SHADOW }}>
      {words.map((w: string, i: number) => { const p = interpolate(f, [4 + i * per, 12 + i * per], [0, 1], C); return <span key={i} style={{ opacity: p, filter: `blur(${(1 - p) * 6}px)`, color: /serious/i.test(w) ? ACCENT_EP : BONE }}>{w} </span>; })}
    </div>
  </Bg>;
};
const VDoc: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const P = s.params; const f = useCurrentFrame(); const i0 = P.text.indexOf(P.hl);
  const sweep = interpolate(f, [24, 70], [0, 1], C); const cam = interpolate(f, [0, d], [1, 1.1], { ...C, easing: io });
  return <Bg>
    <div style={{ position: 'absolute', left: 70, right: 70, top: 380, padding: '56px 56px 64px', background: PAPER, transform: `rotate(-1deg) scale(${cam})`, boxShadow: '0 40px 100px rgba(0,0,0,.55)' }}>
      <div style={{ fontFamily: FONT.mono, fontSize: 22, letterSpacing: '0.12em', color: '#5a5a55', paddingBottom: 18, borderBottom: '2px solid #bdb8aa' }}>{P.id}</div>
      <div style={{ fontFamily: FONT.mono, fontSize: 44, lineHeight: 1.5, color: '#2a2a28', marginTop: 26 }}>
        {P.text.slice(0, i0)}<span style={{ backgroundImage: `linear-gradient(90deg, ${rgba(ACCENT_EP, 0.85)} ${sweep * 100}%, transparent ${sweep * 100}%)` }}>{P.hl}</span>{P.text.slice(i0 + P.hl.length)}</div>
    </div>
  </Bg>;
};
// custom, re-laid for 9:16
const VClock: React.FC<{ d: number }> = ({ d }) => {
  const f = useCurrentFrame(); const CX = 540, CY = 640, R = 330;
  const pt = (deg: number, r: number) => [CX + r * Math.sin((deg * Math.PI) / 180), CY - r * Math.cos((deg * Math.PI) / 180)];
  const p = interpolate(f, [6, Math.min(d - 12, 70)], [0, 1], { ...C, easing: io }); const t = 600 + 101 * p;
  const hd = ((t / 60) * 30) % 360, md = (t % 60) * 6; const [x0, y0] = pt(300, R - 110), [x1, y1] = pt(hd, R - 110);
  return <Bg>
    <svg width={W} height={H} style={{ position: 'absolute' }}>
      <circle cx={CX} cy={CY} r={R} fill="none" stroke={rgba(TINT, 0.35)} strokeWidth={2} />
      {Array.from({ length: 60 }, (_, i) => { const b = i % 5 === 0; const [a, c] = pt(i * 6, R - (b ? 34 : 16)), [e, g] = pt(i * 6, R - 4); return <line key={i} x1={a} y1={c} x2={e} y2={g} stroke={b ? BONE : rgba(TINT, 0.6)} strokeWidth={b ? 4 : 2} />; })}
      <path d={`M${CX} ${CY} L${x0} ${y0} A${R - 110} ${R - 110} 0 0 1 ${x1} ${y1} Z`} fill={rgba(ACCENT_EP, 0.28)} stroke={ACCENT_EP} strokeWidth={3} />
      {(() => { const [x, y] = pt(md, R - 40); return <line x1={CX} y1={CY} x2={x} y2={y} stroke={BONE} strokeWidth={6} />; })()}
      {(() => { const [x, y] = pt(hd, R - 130); return <line x1={CX} y1={CY} x2={x} y2={y} stroke={ACCENT_EP} strokeWidth={14} />; })()}
      <circle cx={CX} cy={CY} r={12} fill={BONE} />
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
  const ax = 540, ay = 700; const tick = (x: number, y: number, dx: number, dy: number) => `M${x + dx * 40} ${y} L${x} ${y} L${x} ${y + dy * 40}`;
  return <AbsoluteFill style={{ background: '#000' }}>
    <AbsoluteFill style={{ transform: `translateY(${ay - H / 2}px)` }}><VPhoto id={ids[k]} from={[fr.at[0], fr.at[1], fr.z]} to={[fr.at[0], fr.at[1], fr.z * 1.05]} d={Math.round(seg)} filter={fr.filter} /></AbsoluteFill>
    <svg width={W} height={H} style={{ position: 'absolute', filter: 'drop-shadow(0 0 6px rgba(0,0,0,.7))' }}>
      <line x1={ax} y1={ay - rs - 140} x2={ax} y2={ay - 24} stroke={rgba(BONE, 0.55 * lock)} strokeWidth={2} /><line x1={ax} y1={ay + 24} x2={ax} y2={ay + rs + 140} stroke={rgba(BONE, 0.55 * lock)} strokeWidth={2} />
      <line x1={ax - rs - 120} y1={ay} x2={ax - 24} y2={ay} stroke={rgba(BONE, 0.55 * lock)} strokeWidth={2} /><line x1={ax + 24} y1={ay} x2={ax + rs + 120} y2={ay} stroke={rgba(BONE, 0.55 * lock)} strokeWidth={2} />
      <path d={[tick(ax - rs, ay - rs, 1, 1), tick(ax + rs, ay - rs, -1, 1), tick(ax - rs, ay + rs, 1, -1), tick(ax + rs, ay + rs, -1, -1)].join(' ')} fill="none" stroke={lock > 0.98 ? ACCENT_EP : BONE} strokeWidth={4} />
    </svg>
    <div style={{ position: 'absolute', left: 0, right: 0, top: 1000, textAlign: 'center' }}>
      <div style={{ fontFamily: FONT.mono, fontSize: 26, letterSpacing: '0.14em', color: MUTED, textShadow: SHADOW }}>RANGE TO AGENA · FRAME {k + 1}/3</div>
      <div style={{ ...DISP(200, 62, 860), color: BONE, textShadow: SHADOW }}>~{rv.toLocaleString('en-US')}<span style={{ ...DISP(100), color: ACCENT_EP, marginLeft: 14 }}>FT</span></div></div>
    <AbsoluteFill style={{ background: '#fff', opacity: k ? interpolate(lf, [0, 4], [0.85, 0], C) : 0 }} />
  </AbsoluteFill>;
};
const Layout: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  switch (s.layout) {
    case 'v_photo_pan': return <VPhotoPan s={s} d={d} />;
    case 'v_film_crop': return <VFilm s={s} d={d} />;
    case 'v_type': return <VType s={s} d={d} />;
    case 'v_number': return <VNumber s={s} d={d} />;
    case 'v_quote': return <VQuote s={s} d={d} />;
    case 'v_doc': return <VDoc s={s} d={d} />;
    case 'v_custom': return s.params.component === 'VClock' ? <VClock d={d} /> : <VDockingHud s={s} d={d} />;
    default: return <Bg><div style={{ color: SIGNAL, fontSize: 60 }}>NO LAYOUT {s.layout}</div></Bg>;
  }
};

// ---- captions: 1–3 words at a time, the spoken word in the accent ----
const Captions: React.FC<{ sh: Short }> = ({ sh }) => {
  const f = useCurrentFrame(); const t = sh.start_s + f / FPS;
  const ws = (WORDS as any).words.filter((w: any) => sh.line_ids.includes(w.line_id));
  const chunks: any[][] = []; let cur: any[] = [];
  ws.forEach((w: any, i: number) => { cur.push(w); const nx = ws[i + 1]; const len = cur.map((c) => c.w).join(' ').length + (nx ? nx.w.length + 1 : 0);
    const end = (/[.,?!:]$/.test(w.w) && !/^[A-Z]\.$/.test(w.w)) || cur.length === 3 || len > 15 || i === ws.length - 1; if (end) { chunks.push(cur); cur = []; } });
  const ch = chunks.find((c) => t >= c[0].start - 0.05 && t < c[c.length - 1].end + 0.12); if (!ch) return null;
  const pop = interpolate(t - ch[0].start, [0, 0.12], [0.9, 1], C);
  const n = ch.map((w) => w.w).join(' ').length; const size = Math.min(92, Math.round(92 * 14 / Math.max(14, n)));
  return <div style={{ position: 'absolute', left: 100, right: 160, top: 1240, textAlign: 'center', transform: `scale(${pop})`, whiteSpace: 'nowrap' }}>
    {ch.map((w, i) => <span key={i} style={{ ...DISP(size, 75, 820), lineHeight: 1.05, color: t >= w.start && t < w.end + 0.05 ? ACCENT_EP : BONE, textShadow: SHADOW, marginRight: i < ch.length - 1 ? size * 0.24 : 0 }}>{/^[A-Z]\.$/.test(w.w) ? w.w : w.w.replace(/[.,!:;]$/, '')}</span>)}
  </div>;
};
const Hook: React.FC<{ text: string }> = ({ text }) => {
  const f = useCurrentFrame(); const o = interpolate(f, [60, 70], [1, 0], C); if (o <= 0) return null;
  return <div style={{ position: 'absolute', left: 60, right: 60, top: 230, textAlign: 'center', opacity: o }}>
    <span style={{ ...DISP(112, 62, 880), color: BONE, textShadow: SHADOW, lineHeight: 0.95 }}>{text}<StopBlock size={112} /></span></div>;
};

export const ShortVideo: React.FC<{ id: string }> = ({ id }) => {
  const sh = SHORTS.find((x) => x.id === id)!; const total = shortFrames(sh);
  return <AbsoluteFill style={{ background: GROUND }}>
    {sh.shots.map((s) => { const from = Math.round(s.start_s * FPS), d = Math.round(s.duration_s * FPS);
      return <Sequence key={s.id} from={from} durationInFrames={d}><PunchIn><Layout s={s} d={d} /></PunchIn></Sequence>; })}
    <Captions sh={sh} />
    <Hook text={sh.hook_text} />
    <Grain opacity={0.07} />
    <Audio src={staticFile('ep/voice.wav')} startFrom={Math.round(sh.start_s * FPS)} endAt={Math.round(sh.start_s * FPS) + total} />
    <Audio src={staticFile('ep/music_raw.mp3')} startFrom={Math.round(sh.start_s * FPS)} volume={(fr) => 0.07 * interpolate(fr, [total - 20, total], [1, 0], C)} />
  </AbsoluteFill>;
};
const PunchIn: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const f = useCurrentFrame(); const z = interpolate(f, [0, 6], [1.06, 1], { ...C, easing: out });
  return <AbsoluteFill style={{ transform: `scale(${z})` }}>{children}</AbsoluteFill>;
};
