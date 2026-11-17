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
import { VCUSTOM } from './custom';

const FPS = 30, W = 1080, H = 1920, X0 = 80;
// size that fits the longest line into the 9:16 text column (Archivo at wdth 62 ≈ 0.5 em per capital)
const fit = (lines: string[], max: number) => Math.min(max, Math.floor(900 / (Math.max(...lines.map((l) => l.length)) * 0.5)));
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
// ---- layouts ----
const VPhotoPan: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const P = s.params ?? {}; const f = useCurrentFrame();
  const b0 = s.start_s < 0.3 ? 68 : 2; // the hook owns the first two seconds
  const big = P.big ? interpolate(f, [b0, b0 + 10], [0, 1], { ...C, easing: out }) : 0;
  return <AbsoluteFill>
    <VPhoto id={s.media_ids![0]} from={P.from ?? [0.5, 0.5, 1]} to={P.to ?? [0.5, 0.5, 1.1]} d={d} filter={P.illustration ? 'sepia(0.15) contrast(1.05)' : 'contrast(1.06)'} />
    <Shade />
    {P.big ? <div style={{ position: 'absolute', left: 0, right: 0, top: 560, textAlign: 'center', ...DISP(360, 62, 880), color: ACCENT_EP, textShadow: SHADOW, transform: `scale(${0.85 + 0.15 * big})`, opacity: big }}>{P.big}</div> : null}
    {P.illustration ? <Mono text="ILLUSTRATION · AI-GENERATED" f0={4} size={20} style={{ position: 'absolute', left: X0, top: 250 }} /> : null}
  </AbsoluteFill>;
};
const VFilm: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params ?? {}; const z = 1 + 0.06 * interpolate(f, [0, d], [0, 1], C);
  const m = MEDIA[s.media_ids![0]]; const h = H * 1.0, w = (h * m.w) / m.h * 1.335; // 4:3 film inside 16:9: scale off the pillarbox
  const x = (P.x ?? 0.5) * (w - W);
  return <AbsoluteFill style={{ background: '#000', overflow: 'hidden' }}>
    <div style={{ position: 'absolute', left: -x, top: 0, width: w, height: h, transform: `scale(${z})`, transformOrigin: `${x + W / 2}px 50%` }}>
      <OffthreadVideo src={med(s.media_ids![0])} startFrom={Math.round((P.trim ?? 1) * FPS)} muted style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'contrast(1.06)' }} /></div>
    <Shade />
  </AbsoluteFill>;
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
    <div style={{ position: 'absolute', left: X0 - 10, top: 570 }}><Odometer value={P.value} size={String(P.value).length > 3 ? 330 : 400} f0={2} dur={22} /></div>
    <div style={{ position: 'absolute', left: X0, top: 920, ...DISP(170), color: BONE, opacity: up }}>{P.unit}</div>
    <Mono text={P.note} f0={24} size={28} color={rgba(BONE, 0.7)} style={{ position: 'absolute', left: X0, top: 1110 }} />
  </Bg>;
};
const VQuote: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  const P = s.params; const f = useCurrentFrame(); const words = P.quote.split(' '); const per = Math.max(5, Math.floor((d - 30) / words.length));
  return <Bg>
    <Mono text={P.name} f0={0} size={26} style={{ position: 'absolute', left: X0, top: 470 }} />
    <div style={{ position: 'absolute', left: X0, right: 120, top: 530, fontFamily: FONT.quote, fontStyle: 'italic', fontWeight: 420, fontSize: 124, lineHeight: 1.04, color: BONE, textShadow: SHADOW }}>
      {words.map((w: string, i: number) => { const p = interpolate(f, [4 + i * per, 12 + i * per], [0, 1], C); return <span key={i} style={{ opacity: p, filter: `blur(${(1 - p) * 6}px)`, color: P.accent && w.replace(/[^\w]/g, '').toLowerCase() === String(P.accent).toLowerCase() ? ACCENT_EP : BONE }}>{w} </span>; })}
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
const Layout: React.FC<{ s: VShot; d: number }> = ({ s, d }) => {
  switch (s.layout) {
    case 'v_photo_pan': return <VPhotoPan s={s} d={d} />;
    case 'v_film_crop': return <VFilm s={s} d={d} />;
    case 'v_type': return <VType s={s} d={d} />;
    case 'v_number': return <VNumber s={s} d={d} />;
    case 'v_quote': return <VQuote s={s} d={d} />;
    case 'v_doc': return <VDoc s={s} d={d} />;
    case 'v_custom': { const V = VCUSTOM[s.params.component]; return V ? <V s={s} d={d} /> : <Bg><div style={{ color: SIGNAL, fontSize: 60 }}>NO CUSTOM {s.params.component}</div></Bg>; }
    default: return <Bg><div style={{ color: SIGNAL, fontSize: 60 }}>NO LAYOUT {s.layout}</div></Bg>;
  }
};

// ---- one text layer at a time ----
// Picture shots get a bottom-left block: mono kicker (what we see) + the spoken phrase, built word by word.
// Type, number, quote, doc and custom shots carry their own words, so captions step aside there.
const TEXT_LAYOUTS = new Set(['v_type', 'v_number', 'v_quote', 'v_doc', 'v_custom']);
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
  const ws = (WORDS as any).words.filter((w: any) => sh.line_ids.includes(w.line_id));
  const ch = phrases(ws).find((c) => t >= c[0].start - 0.04 && t < c[c.length - 1].end + 0.2);
  const label = shot.params?.label; const lf = f - Math.round(shot.start_s * FPS);
  const lp = interpolate(lf, [3, 13], [0, 1], { ...C, easing: out });
  return <div style={{ position: 'absolute', left: X0, right: 170, bottom: 470, display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 22 }}>
    {label ? <div style={{ display: 'flex', alignItems: 'center', gap: 16, opacity: lp, transform: `translateX(${(1 - lp) * -16}px)` }}>
      <div style={{ width: 36, height: 4, background: ACCENT_EP }} />
      <div style={{ fontFamily: FONT.mono, fontWeight: 600, fontSize: 34, letterSpacing: '0.1em', textTransform: 'uppercase', color: BONE, textShadow: SHADOW }}>{label}</div></div> : null}
    {ch ? <div style={{ ...DISP(104, 70, 820), lineHeight: '98px', color: BONE, textShadow: SHADOW }}>
      {ch.map((w, i) => { const on = interpolate(t, [w.start - 0.04, w.start + 0.06], [0, 1], C);
        return <span key={i} style={{ display: 'inline-block', marginRight: '0.22em', opacity: on, transform: `translateY(${(1 - on) * 14}px)` }}>{clean(w.w)}</span>; })}
    </div> : null}
  </div>;
};
const Hook: React.FC<{ sh: Short }> = ({ sh }) => {
  const f = useCurrentFrame();
  const firstText = sh.shots.find((s) => s.start_s > 0.3 && (TEXT_LAYOUTS.has(s.layout) || s.params?.big));
  const endF = Math.min(66, firstText ? Math.round(firstText.start_s * FPS) - 2 : 66);
  const o = interpolate(f, [endF - 8, endF], [1, 0], C); if (o <= 0) return null;
  const words = sh.hook_text.split(' '); const size = fit([sh.hook_text.length > 14 ? sh.hook_text.slice(0, Math.ceil(sh.hook_text.length / 2)) : sh.hook_text], 150);
  return <div style={{ position: 'absolute', left: X0, right: 120, top: 210, opacity: o, textWrap: 'balance' as any, ...DISP(size, 62, 880), lineHeight: `${size * 0.94}px`, color: BONE, textShadow: SHADOW }}>
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
    <Audio src={staticFile('ep/voice.wav')} startFrom={Math.round(sh.start_s * FPS)} endAt={Math.round(sh.start_s * FPS) + total} />
    <Audio src={staticFile('ep/music.wav')} startFrom={Math.round(sh.start_s * FPS)} volume={(fr) => interpolate(fr, [0, 6, total - 20, total], [0, 1, 1, 0], C)} />
  </AbsoluteFill>;
};
const PunchIn: React.FC<{ children: React.ReactNode; d: number }> = ({ children, d }) => {
  const f = useCurrentFrame(); const z = interpolate(f, [0, 6], [1.06, 1], { ...C, easing: out }) * interpolate(f, [6, d], [1, 1.045], C);
  return <AbsoluteFill style={{ transform: `scale(${z})` }}>{children}</AbsoluteFill>;
};
