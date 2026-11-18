// Episode renderer (S1E04 Tornadoes): reads the shot list and maps each scene_type (and its variant) to a component.
import React from 'react';
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import SL from './ep/shotlist.json';
import LINES from './ep/lines.json';
import CH from './ep/chapters.json';
import MEDIA_RAW from './ep/media.json';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, GROUND2, MUTED, PAPER, SHADOW, SIGNAL, SPRING_SOFT, TINT, exitE, io, out, rgba, rng } from './kit/tokens';
import { Callout, Hairline, Kinetic, Mono, Odometer, StopBlock, Unredact } from './kit/Type';
import { Finish, Grain, HandNote, SceneBg, Tag } from './kit/Brand';
import { CUSTOM } from './custom';

export type Shot = { id: string; line_ids: string[]; scene_type: string; duration_s: number; params: any; variant?: string; custom?: { component: string; brief: string; register?: string }; media_ids?: string[]; source_line?: string; transition_in?: string; sfx?: string[] };
const FPS = 30;
const SHOTS = (SL as any).shots as Shot[];
const END_S = SHOTS[SHOTS.length - 1].params.start_s + SHOTS[SHOTS.length - 1].duration_s;
export const EP_FRAMES = Math.round(END_S * FPS) + 20;
export const MEDIA = MEDIA_RAW as Record<string, { src: string; w: number; h: number }>;
export const med = (id: string) => staticFile('ep/' + MEDIA[id].src);
export const durF = (s: Shot) => Math.round(s.duration_s * FPS);
const CHAPTERS: Record<string, [number, string] | null> = CH as any;
const N_CH = Object.values(CHAPTERS).filter(Boolean).length;
const chapterOf = (s: Shot) => CHAPTERS[(LINES as any[]).find((l) => l.id === s.line_ids[0])?.chapter ?? 'cold'];
const cover = (iw: number, ih: number, bw: number, bh: number) => { const k = Math.max(bw / iw, bh / ih); return { k, w: iw * k, h: ih * k }; };

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
    <div style={{ ...DISP(size, wdth), color, whiteSpace: 'nowrap', textShadow: SHADOW, transform: `translateY(${(1 - p) * 105}%)` }}>
      {text.split(' ').map((w, i) => <span key={i} style={{ color: accentWord && w.replace(/[^A-Z0-9.]/gi, '') === accentWord ? ACCENT_EP : undefined }}>{i ? ' ' : ''}{w}</span>)}
      {stop ? <StopBlock size={size} p={interpolate(f, [f0 + 10, f0 + 18], [0, 1], C)} /> : null}
    </div></div>;
};

// Camera into an image: centre (cx,cy as fractions) and zoom z, interpolated, clamped inside the image.
export const ImageCam: React.FC<{ id: string; from: number[]; to: number[]; dur: number; filter?: string; W?: number; H?: number; children?: (map: (x: number, y: number) => [number, number]) => React.ReactNode }> = ({ id, from, to, dur, filter, children, W: W0, H: H0 }) => {
  const f = useCurrentFrame(); const vc = useVideoConfig(); const W = W0 ?? vc.width, H = H0 ?? vc.height; const m = MEDIA[id];
  const p = interpolate(f, [0, dur], [0, 1], { ...C, easing: io });
  const cx = from[0] + (to[0] - from[0]) * p, cy = from[1] + (to[1] - from[1]) * p, z = from[2] * Math.pow(to[2] / from[2], p);
  const cv = cover(m.w, m.h, W, H);
  const px = Math.min(Math.max(cx * cv.w, W / 2 / z), cv.w - W / 2 / z), py = Math.min(Math.max(cy * cv.h, H / 2 / z), cv.h - H / 2 / z);
  const map = (x: number, y: number): [number, number] => [W / 2 + (x * cv.w - px) * z, H / 2 + (y * cv.h - py) * z];
  return <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: '#000', width: W, height: H }}>
    <Img src={med(id)} style={{ position: 'absolute', left: 0, top: 0, width: cv.w, height: cv.h, transformOrigin: '0 0', transform: `translate(${W / 2}px, ${H / 2}px) scale(${z}) translate(${-px}px, ${-py}px)`, filter }} />
    {children ? children(map) : null}
  </AbsoluteFill>;
};
const DUST = (() => { const r = rng(7); return Array.from({ length: 60 }, () => ({ x: r() * 1920, y: r() * 1080, z: 0.3 + r() * 1.4, a: 0.05 + r() * 0.2, ph: r() * 6 })); })();
export const Dust: React.FC<{ dir?: number }> = ({ dir = 1 }) => { const f = useCurrentFrame(); return <svg width={1920} height={1080} style={{ position: 'absolute' }}>{DUST.map((d, i) => { const x = (d.x + f * d.z * 0.9 * dir + 1920 * 4) % 1920; const y = (d.y - f * d.z * 0.35 + Math.sin(f / 30 + d.ph) * 6 + 1080 * 4) % 1080; return <circle key={i} cx={x} cy={y} r={d.z * 1.6} fill={`rgba(235,240,255,${d.a})`} />; })}</svg>; };

// ---------- archival scenes ----------
const FilmClip: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const v = s.variant ?? 'full_frame';
  const z = (P.zoom ?? 1) * (1 + (P.push ?? 0.05) * interpolate(f, [0, d], [0, 1], C));
  const flick = v === 'projector_flicker' ? 0.9 + 0.1 * Math.abs(Math.sin(f * 2.3) * Math.sin(f * 0.7)) : 1;
  const weave = v === 'projector_flicker' ? Math.sin(f * 1.7) * 1.5 : 0;
  const vid = <OffthreadVideo src={med(s.media_ids![0])} startFrom={Math.round(P.trim * FPS)} muted={!P.snd} volume={P.snd ?? 0} style={{ width: '100%', height: '100%', objectFit: 'cover', filter: `contrast(1.08) saturate(${P.sat ?? 0.9}) brightness(${flick * (P.bright ?? 1)})` }} />;
  return <AbsoluteFill style={{ backgroundColor: '#000' }}>
    <AbsoluteFill style={{ transform: `scale(${z}) translateY(${weave}px)`, transformOrigin: P.origin ?? '50% 50%' }}>{vid}</AbsoluteFill>
    <Shade top={0.25} bottom={P.label ? 0.85 : 0.5} />
    {v === 'projector_flicker' ? <Grain opacity={0.16} /> : null}
    {P.label ? <Line text={P.label} f0={P.label_at ? Math.round(P.label_at * FPS) : 10} y={P.label_y ?? 820} size={P.size ?? 88} stop={P.stop} accentWord={P.accent} /> : null}
    {P.tag ? <Tag text={P.tag} f0={6} x={1860} y={64} size={22} color={ACCENT_EP} align="right" /> : null}
  </AbsoluteFill>;
};

const PhotoParallax: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const p = interpolate(f, [0, d], [0, 1], { ...C, easing: io });
  const v = s.variant ?? 'push_in';
  const tr = v === 'lateral_drift' ? `scale(1.16) translateX(${(P.dir ?? 1) * (-50 + 100 * p)}px) rotate(${(P.dir ?? 1) * (-0.6 + 1.2 * p)}deg)` : `scale(${1.04 + 0.12 * p}) translateY(${-14 * p}px)`;
  const m = MEDIA[s.media_ids![0]]; const fit = P.fit ?? (m.h > m.w * 1.1 ? 'top' : 'center');
  return <AbsoluteFill style={{ backgroundColor: '#000', perspective: 1400 }}>
    <AbsoluteFill style={{ transform: tr, transformOrigin: P.origin ?? '50% 40%' }}>
      <Img src={med(s.media_ids![0])} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: fit === 'top' ? `50% ${P.pos ?? 30}%` : '50% 50%', filter: P.filter }} />
    </AbsoluteFill>
    {P.dust ? <Dust dir={v === 'lateral_drift' ? (P.dir ?? 1) : 1} /> : null}
    <Shade left={P.label ? 0.35 : 0} bottom={P.label ? 0.85 : 0.45} />
    {P.label ? <Line text={P.label} f0={10} y={P.label_y ?? 820} size={P.size ?? 88} stop={P.stop} accentWord={P.accent} /> : null}
    {P.sub ? <Mono text={P.sub} f0={24} size={24} color={BONE} style={{ position: 'absolute', left: 94, top: (P.label_y ?? 820) + (P.size ?? 88) + 22 }} /> : null}
  </AbsoluteFill>;
};

const PhotoDetailZoom: React.FC<{ s: Shot }> = ({ s }) => {
  const d = durF(s); const P = s.params; const v = s.variant ?? 'circle_lands'; const f = useCurrentFrame();
  const at = Math.round(d * (P.at ?? 0.45));
  return <AbsoluteFill>
    <ImageCam id={s.media_ids![0]} from={P.from} to={P.to} dur={d} filter={P.filter}>{(map) => {
      if (!P.mark) return null; const [x, y] = map(P.mark[0], P.mark[1]);
      if (v === 'crop_marks') { const r = P.r ?? 120; const p = interpolate(f, [at, at + 12], [0, 1], { ...C, easing: out }); const o = (1 - p) * 60;
        return <svg width={1920} height={1080} style={{ position: 'absolute', opacity: p }}>{[[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([sx, sy], i) => <path key={i} d={`M${x + sx * (r + o)} ${y + sy * (r + o) - sy * 34} L${x + sx * (r + o)} ${y + sy * (r + o)} L${x + sx * (r + o) - sx * 34} ${y + sy * (r + o)}`} stroke={ACCENT_EP} strokeWidth={5} fill="none" />)}</svg>; }
      return <Callout text={P.callout ?? ''} sub={P.callout_sub} at={[x, y]} label={P.label_at ?? [x + 160, y - 200]} f0={at} size={P.csize ?? 58} color={BONE} />;
    }}</ImageCam>
    <Shade bottom={P.label ? 0.85 : 0.4} />
    {P.label ? <Line text={P.label} f0={8} y={P.label_y ?? 820} size={P.size ?? 80} stop={P.stop} accentWord={P.accent} /> : null}
  </AbsoluteFill>;
};

const PhotoLighttable: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const d = durF(s); const P = s.params; const v = s.variant ?? 'single_print';
  const ids = s.media_ids!;
  const prints = v === 'contact_strip' ? ids : [ids[0]];
  const z = 1 + 0.05 * interpolate(f, [0, d], [0, 1], { ...C, easing: io });
  return <SceneBg drift={0.2}>
    <Img src={med(ids[0])} style={{ position: 'absolute', inset: -60, width: 2040, height: 1200, objectFit: 'cover', filter: 'blur(30px) brightness(0.28) saturate(0.7)' }} />
    {prints.map((id, i) => { const m = MEDIA[id]; const n = prints.length; const ch = n > 1 ? 520 : 820; const cw = Math.min(n > 1 ? 560 : 1000, (ch * m.w) / m.h);
      const p = spring({ frame: f - 2 - i * 7, fps, config: { damping: 20, stiffness: 90 } });
      const x0 = n > 1 ? 760 + i * 380 - cw / 2 : 1840 - cw; const y0 = n > 1 ? 210 + (i % 2) * 120 : 120; const rot = n > 1 ? [-3, 2, -1.5][i % 3] : 1.2;
      return <div key={id} style={{ position: 'absolute', left: x0, top: y0, width: cw, height: ch, transform: `translateY(${(1 - p) * 500}px) rotate(${(1 - p) * 8 + rot}deg) scale(${z})`, opacity: Math.min(1, p * 2), boxShadow: '0 30px 80px rgba(0,0,0,0.65)', outline: `12px solid ${PAPER}` }}>
        <Img src={med(id)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} /></div>; })}
    <div style={{ position: 'absolute', left: 90, top: v === 'contact_strip' ? 820 : 430, width: v === 'contact_strip' ? 1500 : 640 }}>
      <Line text={P.label} f0={14} x={0} y={0} size={P.size ?? 86} accentWord={P.accent} />
      {P.sub ? <Mono text={P.sub} f0={28} size={24} color={BONE} style={{ position: 'absolute', left: 4, top: (P.size ?? 86) + 30 }} /> : null}
    </div>
  </SceneBg>;
};

const PhotoCompare: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const d = durF(s); const ids = s.media_ids!; const P = s.params;
  const bw = 820, bh = 600;
  return <SceneBg drift={0.3}>{ids.map((id, i) => { const f0 = i * Math.round((P.stagger ?? 0.8) * FPS); const p = spring({ frame: f - f0, fps, config: { damping: 18, stiffness: 110 } });
    if (f < f0) return null; const zz = interpolate(f, [f0, d], [1, 1.07], C); const x = i === 0 ? 110 : 990;
    return <div key={id} style={{ position: 'absolute', left: x, top: 150, width: bw, height: bh, transform: `translateX(${(1 - p) * (i === 0 ? -300 : 400)}px)`, opacity: Math.min(1, p * 2) }}>
      <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', backgroundColor: '#000' }}><Img src={med(id)} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: P.pos?.[i] ?? '50% 50%', transform: `scale(${zz})` }} /></div>
      <div style={{ position: 'absolute', left: 0, top: bh + 30, ...DISP(84), color: i === 1 ? ACCENT_EP : BONE, textShadow: SHADOW }}>{P.labels[i]}</div>
      {P.subs ? <Mono text={P.subs[i]} f0={f0 + 16} size={22} style={{ position: 'absolute', left: 2, top: bh + 130 }} /> : null}
    </div>; })}</SceneBg>;
};

// Transcript page, typed on; one row highlighted.
const DocumentHighlight: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const P = s.params; const d = durF(s); const rows: string[][] = P.rows;
  const cam = interpolate(f, [6, d], [0, 1], { ...C, easing: io }); const pin = spring({ frame: f - 2, fps, config: SPRING_SOFT });
  const per = Math.max(8, Math.min(18, Math.round((d * 0.55) / rows.length)));
  return <SceneBg drift={0.25}>
    <AbsoluteFill style={{ transform: `scale(${1 + 0.12 * cam}) translateY(${-20 * cam}px)`, transformOrigin: `50% ${30 + (P.hl ?? 0) * 12}%` }}>
      <div style={{ position: 'absolute', left: 250, top: 120, width: 1420, padding: '54px 80px 70px', background: PAPER, boxShadow: '0 40px 120px rgba(0,0,0,0.55)', transform: `rotate(-0.6deg) translateY(${(1 - pin) * 80}px)`, opacity: pin }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: FONT.mono, fontSize: 22, letterSpacing: 3, color: '#5A5A55', borderBottom: '2px solid #BDB8AA', paddingBottom: 16 }}><span>{P.head}</span><span>{P.ref}</span></div>
        {rows.map((r, i) => { const a = 8 + i * per; const n = Math.floor(interpolate(f, [a, a + r[2].length / 2.2], [0, r[2].length], C)); const hl = i === P.hl;
          const sw = hl ? interpolate(f, [a + r[2].length / 2.2 + 4, a + r[2].length / 2.2 + 20], [0, 100], C) : 0;
          return <div key={i} style={{ display: 'flex', gap: 30, marginTop: 26, fontFamily: FONT.mono, fontSize: 34, lineHeight: 1.45, color: '#26261f', opacity: f >= a ? 1 : 0 }}>
            <span style={{ color: '#7a776d', width: 210, flexShrink: 0 }}>{r[0]}</span><span style={{ width: 230, flexShrink: 0, color: '#4a4840' }}>{r[1]}</span>
            <span style={{ backgroundImage: `linear-gradient(90deg, ${rgba(ACCENT_EP, 0.75)} ${sw}%, transparent ${sw}%)` }}>{r[2].slice(0, n)}<span style={{ opacity: 0 }}>{r[2].slice(n)}</span></span></div>; })}
      </div>
    </AbsoluteFill>
  </SceneBg>;
};

// Onboard tape: the quote in big type over a live waveform; timestamp and speaker in mono.
const TranscriptWaveform: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const words = (P.quote as string).split(' ');
  const a0 = Math.round((P.at ?? 0.3) * FPS); const per = Math.max(4, Math.min(9, Math.round((d * 0.5) / words.length)));
  const N = 120; const talk = f > a0 && f < a0 + words.length * per + 12;
  const bars = Array.from({ length: N }, (_, i) => { const r = Math.sin(i * 12.9898) * 43758.5453; const b = r - Math.floor(r); return 4 + b * (talk ? 70 * (0.45 + 0.55 * Math.abs(Math.sin(f / 2.2 + i * 0.7))) : 10); });
  const head = Math.min(1, f / d);
  const size = P.size ?? (P.quote.length > 34 ? 104 : 140);
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <Mono text={P.time} f0={2} size={34} color={ACCENT_EP} style={{ position: 'absolute', left: 150, top: 200 }} />
    <Mono text={P.who} f0={10} size={24} color={MUTED} style={{ position: 'absolute', left: 150, top: 252 }} />
    <div style={{ position: 'absolute', left: 140, top: 330, width: 1560, ...DISP(size, 70, 820), lineHeight: 1.0, textShadow: SHADOW }}>
      {words.map((w, i) => { const p = interpolate(f, [a0 + i * per, a0 + i * per + 8], [0, 1], C); return <span key={i} style={{ opacity: p, color: P.accent && w.toUpperCase().includes(P.accent) ? ACCENT_EP : BONE, display: 'inline-block', transform: `translateY(${(1 - p) * 20}px)`, marginRight: size * 0.22 }}>{w}</span>; })}
    </div>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>{bars.map((h, i) => <rect key={i} x={150 + i * 13} y={900 - h / 2} width={5} height={h} fill={i / N < head ? ACCENT_EP : rgba(BONE, 0.2)} />)}</svg>
  </SceneBg>;
};

const QuoteCard: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const words = (P.quote as string).split(' ');
  const a0 = Math.round((P.at ?? 0.4) * FPS); const per = Math.max(4, Math.min(9, Math.round((d * 0.5) / words.length)));
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    {P.photo ? <Img src={med(P.photo)} style={{ position: 'absolute', right: 0, top: 0, height: 1080, width: 760, objectFit: 'cover', opacity: 0.55, WebkitMaskImage: 'linear-gradient(90deg, transparent 0%, #000 60%)', maskImage: 'linear-gradient(90deg, transparent 0%, #000 60%)', filter: 'grayscale(0.3)' }} /> : null}
    <Mono text={P.name} f0={4} size={32} color={BONE} style={{ position: 'absolute', left: 160, top: 250 }} />
    <Mono text={P.role} f0={16} size={22} color={MUTED} weight={400} style={{ position: 'absolute', left: 160, top: 298 }} />
    <div style={{ position: 'absolute', left: 150, top: 390, width: P.photo ? 1180 : 1560, fontFamily: FONT.quote, fontStyle: 'italic', fontWeight: 420, fontVariationSettings: "'opsz' 72", fontSize: P.size ?? 120, lineHeight: 1.06, color: BONE, textShadow: SHADOW }}>
      {words.map((w, i) => { const p = interpolate(f, [a0 + i * per, a0 + i * per + 10], [0, 1], C); return <span key={i} style={{ opacity: p, filter: `blur(${(1 - p) * 6}px)`, color: P.accent && w.toLowerCase().includes(P.accent) ? ACCENT_EP : BONE }}>{w} </span>; })}
    </div>
  </SceneBg>;
};

// ---------- blueprint scenes ----------
const KineticType: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const words: string[] = s.params.words; const n = words.length; const d = durF(s);
  const red = s.params.red ?? -1; const v = s.variant ?? 'rise_narrow';
  const longest = Math.max(...words.map((w) => w.length));
  const size = s.params.size ?? (n <= 2 ? (longest > 8 ? 210 : 250) : n === 3 ? 190 : 160); const lh = size * 0.98;
  const lines: string[][] = s.params.lines ?? (n <= 3 ? words.map((w) => [w]) : [words.slice(0, Math.ceil(n / 2)), words.slice(Math.ceil(n / 2))]);
  let acc: [number, number] = [-1, -1]; { let k = 0; lines.forEach((l, li) => l.forEach((_, wi) => { if (k++ === red) acc = [li, wi]; })); }
  const top = 540 - (lines.length * lh) / 2 - 10; const push = interpolate(f, [0, d], [1, 1.05], C);
  const step = Math.max(3, Math.min(7, Math.round((d * 0.3) / n)));
  return <SceneBg style={{ transform: `scale(${push})` }}>
    {v === 'unredact'
      ? <Unredact lines={lines.map((l) => l.join(' '))} top={top} size={size} f0={4} step={8} x={150} exitAt={d - 8} />
      : <Kinetic lines={lines} top={top} size={size} f0={4} step={step} variant={v} accent={acc} x={150} exitAt={d - 8} />}
    {s.params.sub ? <Mono text={s.params.sub} f0={20} size={26} color={MUTED} style={{ position: 'absolute', left: 156, top: top + lines.length * lh + 30 }} /> : null}
  </SceneBg>;
};

const QuestionCard: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const q: string[] = s.params.q; const size = s.params.size ?? 150; const d = durF(s);
  const top = 540 - (q.length * size * 0.98) / 2 - 40;
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})` }}>
    <Unredact lines={q} top={top} size={size} f0={6} step={10} x={150} exitAt={d - 8} />
    {s.params.sub ? <Mono text={s.params.sub} f0={44} size={26} color={MUTED} style={{ position: 'absolute', left: 156, top: top + q.length * size * 0.98 + 40 }} /> : null}
  </SceneBg>;
};

const ChapterCard: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const v = s.variant ?? 'hairline_index';
  if (P.end) {
    return <SceneBg style={{ background: '#0e0f11' }}>
      <Unredact lines={['REAL STORY']} top={380} size={190} f0={8} />
      <Mono text={P.line1} f0={40} size={24} color={MUTED} style={{ position: 'absolute', left: 0, right: 0, top: 600, textAlign: 'center' }} />
      <Mono text={P.line2} f0={58} size={18} color={rgba(BONE, 0.55)} weight={400} style={{ position: 'absolute', left: 0, right: 0, top: 650, textAlign: 'center' }} />
    </SceneBg>;
  }
  const hp = interpolate(f, [10, 26], [0, 1], { ...C, easing: (t) => 1 - Math.pow(1 - t, 4) });
  if (v === 'big_index') return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <div style={{ position: 'absolute', right: 120, top: 120, ...DISP(560, 62, 900), color: rgba(ACCENT_EP, 0.22 * hp), lineHeight: 1 }}>{String(P.n).padStart(2, '0')}</div>
    <div style={{ position: 'absolute', left: 150, top: 470, height: 230, overflow: 'hidden' }}><div style={{ ...DISP(220), color: BONE, transform: `translateY(${(1 - hp) * 100}%)`, lineHeight: '220px' }}>{P.title}</div></div>
    <Mono text={P.sub ?? ''} f0={24} size={26} color={MUTED} style={{ position: 'absolute', left: 156, top: 720 }} />
  </SceneBg>;
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <Mono text={String(P.n).padStart(2, '0') + ' / ' + String(N_CH).padStart(2, '0')} f0={2} size={30} color={ACCENT_EP} style={{ position: 'absolute', left: 154, top: 360 }} />
    <div style={{ position: 'absolute', left: 150, top: 420, height: 230, overflow: 'hidden' }}><div style={{ ...DISP(230), color: BONE, transform: `translateY(${(1 - hp) * 100}%)`, lineHeight: '230px' }}>{P.title}</div></div>
    <Hairline x={154} y={672} w={1500} f0={4} dur={26} />
    {P.sub ? <Mono text={P.sub} f0={24} size={26} color={MUTED} style={{ position: 'absolute', left: 156, top: 700 }} /> : null}
  </SceneBg>;
};

const BigNumber: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const v = s.variant ?? 'odometer';
  const up = interpolate(f, [26, 40], [0, 1], { ...C, easing: out });
  const fill = interpolate(f, [6, Math.min(d - 10, 50)], [0, 1], { ...C, easing: io });
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})` }}>
    <Mono text={P.label} f0={2} size={30} color={MUTED} style={{ position: 'absolute', left: 154, top: 250 }} />
    <div style={{ position: 'absolute', left: 146, top: 320, display: 'flex', alignItems: 'flex-end', gap: 36 }}>
      {v === 'fill_count'
        ? <span style={{ ...DISP(400, 62, 880), lineHeight: '344px', color: BONE, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW }}>{(P.value * fill).toFixed(P.decimals ?? 0)}</span>
        : <Odometer value={P.value} size={400} f0={6} />}
      <div style={{ ...DISP(150, 62, 840), color: ACCENT_EP, opacity: up, transform: `translateY(${(1 - up) * 30}px)`, marginBottom: 6 }}>{P.unit}</div>
    </div>
    <Hairline x={154} y={704} w={1100} f0={30} />
    <Mono text={P.note} f0={44} size={28} color={BONE} style={{ position: 'absolute', left: 154, top: 736 }} />
  </SceneBg>;
};

const TimelineScroll: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const P = s.params; const d = durF(s); const ev: string[][] = P.events;
  const gap = P.gap ?? 640; const x0 = 200; const need = x0 + (ev.length - 1) * gap + 560 - 1920; const span = need > 0 ? Math.min(need, x0 - 90) : 0;
  // A timeline that fits never sits still: it drifts 60 px so no frame holds longer than the brief allows.
  const cam = span > 0 ? interpolate(f, [8, d - 20], [0, span], { ...C, easing: io }) : interpolate(f, [0, d], [-30, 30], C);
  return <SceneBg drift={-0.6}>
    <div style={{ position: 'absolute', left: 0, top: 0, width: 6000, height: 1080, transform: `translateX(${-cam}px)` }}>
      <svg width={6000} height={1080} style={{ position: 'absolute' }}><line x1={0} y1={560} x2={x0 + gap * (ev.length - 1) + 1300} y2={560} stroke={rgba(TINT, 0.4)} strokeWidth={2} />
        <line x1={0} y1={560} x2={x0 + cam + 300} y2={560} stroke={ACCENT_EP} strokeWidth={5} /></svg>
      {ev.map((e, i) => { const x = x0 + i * gap; const hl = i === P.hl; const p = spring({ frame: f - (6 + i * ((d - 30) / Math.max(1, ev.length - 1)) * 0.55), fps, config: SPRING_SOFT });
        return <div key={i} style={{ position: 'absolute', left: x - 14, top: 546 }}>
          <div style={{ width: 22, height: 22, marginLeft: 7, marginTop: 7, background: ACCENT_EP, transform: `scale(${p * (hl ? 1.5 : 1)})` }} />
          <div style={{ position: 'absolute', left: 0, top: -140, fontFamily: FONT.mono, fontSize: 44, letterSpacing: 4, color: hl ? ACCENT_EP : BONE, whiteSpace: 'nowrap', opacity: p }}>{e[0]}</div>
          <div style={{ position: 'absolute', left: 0, top: 70, ...DISP(hl ? 104 : 72), lineHeight: 0.95, color: BONE, textShadow: SHADOW, width: hl ? 760 : 540, opacity: p, transform: `translateY(${(1 - p) * 30}px)` }}>{e[1]}</div>
        </div>; })}
    </div>
  </SceneBg>;
};

// Mission clock: the elapsed-time readout runs from a to b; events stamp in as the clock passes them.
const CounterTicker: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s);
  const p = interpolate(f, [6, d - (P.hold ?? 20)], [0, 1], { ...C, easing: P.ease === 'linear' ? undefined : io });
  const t = P.from + (P.to - P.from) * p; const mm = Math.floor(t / 60), ss = t - mm * 60;
  const wall = !!P.clock; const cnt = !!P.count; const hh = Math.floor(t / 3600), wm = Math.floor((t % 3600) / 60), ws = Math.floor(t % 60);
  const txt = cnt ? (P.decimals ? t.toFixed(P.decimals) : Math.round(t).toLocaleString('en-US')) : wall ? `${String(hh).padStart(2, '0')}:${String(wm).padStart(2, '0')}:${String(ws).padStart(2, '0')}` : `${String(mm).padStart(2, '0')}:${ss.toFixed(1).padStart(4, '0')}`;
  const ev: [number, string][] = P.events ?? [];
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <Mono text={P.label ?? 'MISSION ELAPSED TIME'} f0={2} size={28} color={MUTED} style={{ position: 'absolute', left: 154, top: 280 }} />
    <div style={{ position: 'absolute', left: 140, top: 330, fontFamily: FONT.mono, fontWeight: 500, fontSize: 300, letterSpacing: '0.02em', color: BONE, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW, lineHeight: 1 }}>
      {wall || cnt ? null : <span style={{ color: MUTED, fontSize: 140, verticalAlign: 'top', marginRight: 20 }}>T+</span>}{txt}{cnt ? <span style={{ color: ACCENT_EP, fontSize: 110, marginLeft: 30 }}>{P.unit ?? ''}</span> : null}{wall ? <span style={{ color: MUTED, fontSize: 110, marginLeft: 30 }}>{P.suffix ?? ''}</span> : null}</div>
    {ev.map(([at, label], i) => { const on = t >= at; const k = interpolate(f, [0, 1], [0, 1]); return on ? <div key={i} style={{ position: 'absolute', left: 154, top: 720 + i * 70, display: 'flex', gap: 30, alignItems: 'baseline' }}>
      <span style={{ fontFamily: FONT.mono, fontSize: 30, color: ACCENT_EP, letterSpacing: '0.1em' }}>{(Math.floor(at / 60)).toString().padStart(2, '0')}:{(at % 60).toFixed(1).padStart(4, '0')}</span>
      <span style={{ ...DISP(58, 70, 800), color: BONE, textShadow: SHADOW, opacity: k }}>{label}</span></div> : null; })}
  </SceneBg>;
};

// Two flows drawn as a schematic: the telemetry chain (sce) or the lightning path through rocket and plume (trigger).
const DiagramBuild: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params;
  const draw = interpolate(f, [4, 40], [0, 1], { ...C, easing: io });
  if (P.kind === 'trigger') {
    const bolt = interpolate(f, [Math.round(d * 0.45), Math.round(d * 0.45) + 6], [0, 1], C); const flash = bolt > 0 ? Math.max(0, 1 - (f - Math.round(d * 0.45)) / 12) : 0;
    const L = 3000; const climb = interpolate(f, [0, d], [40, -40], C);
    return <SceneBg drift={0.2}>
      <AbsoluteFill style={{ background: `rgba(220,235,255,${0.35 * flash})` }} />
      <svg width={1920} height={1080} style={{ position: 'absolute' }}>
        {/* cloud base */}
        {[0, 1, 2, 3, 4, 5].map((i) => <ellipse key={i} cx={260 + i * 300} cy={130 + (i % 2) * 30} rx={240} ry={90} fill={rgba(TINT, 0.12)} stroke={rgba(TINT, 0.35)} strokeWidth={2} opacity={draw} />)}
        {['+', '+', '−', '+', '−', '+', '+'].map((c, i) => <text key={i} x={200 + i * 240} y={150} fontFamily={FONT.mono} fontSize={34} fill={rgba(BONE, 0.6)} opacity={draw}>{c}</text>)}
        <g transform={`translate(0 ${climb})`}>
          {/* rocket */}
          <path d="M940 330 L960 290 L980 330 L980 640 L940 640 Z" fill={rgba(TINT, 0.18)} stroke={BONE} strokeWidth={3} strokeDasharray={`${L * draw} ${L}`} />
          {/* plume */}
          <path d="M945 640 Q930 760 900 1100 L1020 1100 Q990 760 975 640 Z" fill={rgba(ACCENT_EP, 0.18)} stroke={ACCENT_EP} strokeWidth={2} strokeDasharray="10 10" opacity={draw} />
          <text x={1020} y={470} fontFamily={FONT.mono} fontSize={24} letterSpacing={3} fill={BONE} opacity={draw}>363 FT METAL BODY</text>
          <text x={1040} y={900} fontFamily={FONT.mono} fontSize={24} letterSpacing={3} fill={ACCENT_EP} opacity={draw}>HOT EXHAUST, CONDUCTING</text>
        </g>
        <path d={`M960 210 L940 260 L975 290 L955 ${330 + climb} M960 ${640 + climb} L930 820 L985 900 L950 1080`} fill="none" stroke="#eaf3ff" strokeWidth={7} strokeLinejoin="bevel" strokeDasharray={`${L * bolt} ${L}`} style={{ filter: 'drop-shadow(0 0 14px rgba(160,200,255,0.95))' }} />
      </svg>
      <div style={{ position: 'absolute', left: 120, top: 760 }}><Line text={P.label} f0={Math.round(d * 0.5)} x={0} y={0} size={84} accentWord={P.accent} /></div>
    </SceneBg>;
  }
  // telemetry chain
  const nodes: [string, string][] = P.nodes ?? [['SENSORS', 'HUNDREDS'], ['SCE', '0–5 V'], ['PCM', 'DIGITS'], ['S-BAND', 'RADIO'], ['HOUSTON', 'SCREENS']];
  const broken = P.broken ?? -1; const gx = 180, gw = 1560 / (nodes.length - 1);
  const pkt = (f / 3) % 1; const bad = f > Math.round(d * 0.4);
  return <SceneBg drift={0.3} style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.08], C)})` }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {nodes.slice(1).map((_, i) => { const x1 = gx + i * gw, x2 = gx + (i + 1) * gw; const after = broken >= 0 && i >= broken && bad;
        return <g key={i}><line x1={x1 + 70} y1={540} x2={x1 + 70 + (x2 - x1 - 140) * Math.min(1, Math.max(0, draw * nodes.length - i))} y2={540} stroke={after ? SIGNAL : rgba(TINT, 0.8)} strokeWidth={4} strokeDasharray={after ? '6 12' : undefined} />
          {draw > 0.95 ? [0, 1, 2].map((k) => { const q = (pkt + k / 3) % 1; return <text key={k} x={x1 + 70 + (x2 - x1 - 140) * q} y={520} fontFamily={FONT.mono} fontSize={22} fill={after ? SIGNAL : ACCENT_EP} textAnchor="middle">{after ? ['#', '?', '%', '&', '!'][(Math.floor(f / 4) + k + i) % 5] : ['1', '0', '1'][k]}</text>; }) : null}</g>; })}
      {nodes.map(([n, sub], i) => { const x = gx + i * gw; const on = draw * nodes.length > i; const isB = i === broken && bad;
        return <g key={n} opacity={on ? 1 : 0}><rect x={x - 70} y={470} width={140} height={140} fill={isB ? rgba(SIGNAL, 0.25) : rgba(TINT, 0.12)} stroke={isB ? SIGNAL : BONE} strokeWidth={3} />
          <text x={x} y={680} textAnchor="middle" fontFamily={FONT.display} fontWeight={820} fontSize={52} style={{ fontVariationSettings: "'wdth' 70" }} fill={isB ? SIGNAL : BONE}>{n}</text>
          <text x={x} y={720} textAnchor="middle" fontFamily={FONT.mono} fontSize={22} letterSpacing={3} fill={MUTED}>{sub}</text></g>; })}
    </svg>
    <div style={{ position: 'absolute', left: 150, top: 180 }}><Line text={P.label} f0={10} x={0} y={0} size={88} accentWord={P.accent} /></div>
    {P.note ? <Mono text={P.note} f0={Math.round(d * 0.45)} size={26} color={bad ? SIGNAL : MUTED} style={{ position: 'absolute', left: 156, top: 820 }} /> : null}
  </SceneBg>;
};

// 535 ft laid out against Saturn V lengths.
const ScaleCompare: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s);
  const px = 1400 / P.total; const run = interpolate(f, [10, Math.min(d - 20, 70)], [0, 1], { ...C, easing: io });
  const units = P.total / P.unit;
  return <SceneBg drift={0.3} style={{ transform: `scale(${interpolate(f, [0, durF(s)], [1, 1.07], C)})` }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <line x1={260} y1={640} x2={260 + 1400 * run} y2={640} stroke={ACCENT_EP} strokeWidth={6} />
      <circle cx={260} cy={640} r={14} fill={BONE} /><circle cx={260 + 1400 * run} cy={640} r={14} fill={run > 0.98 ? ACCENT_EP : BONE} />
      {Array.from({ length: Math.ceil(units) }, (_, i) => { const w = Math.min(P.unit, P.total - i * P.unit) * px; const shown = run * P.total > i * P.unit; if (!shown) return null; const vis = Math.min(1, (run * P.total - i * P.unit) / P.unit);
        return <g key={i}><path d={`M${260 + i * P.unit * px} 560 L${260 + i * P.unit * px + w * vis - 28} 560 L${260 + i * P.unit * px + w * vis} 540 L${260 + i * P.unit * px + w * vis - 28} 520 L${260 + i * P.unit * px} 520 Z`} fill={rgba(TINT, 0.18)} stroke={BONE} strokeWidth={2.5} />
          {vis > 0.6 && i === 0 ? <text x={270 + i * P.unit * px} y={500} fontFamily={FONT.mono} fontSize={24} letterSpacing={3} fill={MUTED}>{P.unitLabel}</text> : null}</g>; })}
      <text x={260} y={700} fontFamily={FONT.mono} fontSize={26} letterSpacing={3} fill={BONE}>{P.a}</text>
      <text x={1660} y={700} textAnchor="end" fontFamily={FONT.mono} fontSize={26} letterSpacing={3} fill={BONE} opacity={run > 0.9 ? 1 : 0}>{P.b}</text>
    </svg>
    <div style={{ position: 'absolute', left: 254, top: 220, display: 'flex', alignItems: 'flex-end', gap: 30 }}><Odometer value={P.total} size={240} f0={8} /><span style={{ ...DISP(110), color: ACCENT_EP }}>FT</span></div>
    <Mono text={P.note} f0={Math.min(d - 30, 72)} size={30} color={BONE} style={{ position: 'absolute', left: 260, top: 780 }} />
  </SceneBg>;
};

// ---------- transitions + chrome ----------
const TransitionIn: React.FC<{ kind?: string; children: React.ReactNode }> = ({ kind, children }) => {
  const f = useCurrentFrame();
  if (kind === 'dissolve') return <AbsoluteFill style={{ opacity: interpolate(f, [0, 14], [0, 1], C) }}>{children}</AbsoluteFill>;
  if (kind === 'whip') { const p = interpolate(f, [0, 8], [1, 0], { ...C, easing: out }); return <AbsoluteFill style={{ transform: `translateX(${p * 420}px)`, filter: p > 0.02 ? `blur(${p * 30}px)` : undefined }}>{children}</AbsoluteFill>; }
  if (kind === 'push') { const p = interpolate(f, [0, 12], [1, 0], { ...C, easing: out }); return <AbsoluteFill style={{ transform: `scale(${1 + p * 0.12})`, opacity: 1 - p * 0.9 }}>{children}</AbsoluteFill>; }
  if (kind === 'flash') return <AbsoluteFill>{children}<AbsoluteFill style={{ backgroundColor: '#eef4ff', opacity: interpolate(f, [0, 8], [0.9, 0], C) }} /></AbsoluteFill>;
  if (kind === 'mask') { const p = interpolate(f, [0, 12], [0, 100], { ...C, easing: out }); return <AbsoluteFill style={{ clipPath: `inset(0 ${100 - p}% 0 0)` }}>{children}</AbsoluteFill>; }
  return <AbsoluteFill>{children}</AbsoluteFill>;
};
const Chrome: React.FC<{ s: Shot }> = ({ s }) => {
  const ch = chapterOf(s); const t = s.scene_type;
  const showCh = ch && !['chapter_card', 'kinetic_type', 'question_card'].includes(t);
  return <>{showCh ? <Tag text={`${String(ch![0]).padStart(2, '0')}  ${ch![1]}`} f0={8} x={60} y={56} size={18} color={ACCENT_EP} /> : null}
    {s.source_line ? <Tag text={s.source_line.toUpperCase()} f0={14} x={60} y={1080 - 58} size={16} color={rgba(BONE, 0.72)} /> : null}</>;
};
const Scene: React.FC<{ s: Shot }> = ({ s }) => {
  switch (s.scene_type) {
    case 'film_clip': return <FilmClip s={s} />;
    case 'photo_parallax': return <PhotoParallax s={s} />;
    case 'photo_detail_zoom': return <PhotoDetailZoom s={s} />;
    case 'photo_lighttable': return <PhotoLighttable s={s} />;
    case 'photo_compare': return <PhotoCompare s={s} />;
    case 'document_highlight': return <DocumentHighlight s={s} />;
    case 'transcript_waveform': return <TranscriptWaveform s={s} />;
    case 'quote_card': return <QuoteCard s={s} />;
    case 'kinetic_type': return <KineticType s={s} />;
    case 'question_card': return <QuestionCard s={s} />;
    case 'chapter_card': return <ChapterCard s={s} />;
    case 'big_number': return <BigNumber s={s} />;
    case 'timeline_scroll': return <TimelineScroll s={s} />;
    case 'counter_ticker': return <CounterTicker s={s} />;
    case 'diagram_build': return <DiagramBuild s={s} />;
    case 'scale_compare': return <ScaleCompare s={s} />;
    case 'custom': { const Comp = CUSTOM[s.custom!.component]; return Comp ? <Comp s={s} d={durF(s)} /> : <SceneBg />; }
    default: return <SceneBg />;
  }
};
const SFX: Record<string, [string, number]> = { whoosh: ['sfx/whoosh-fast.mp3', 0.35], whoosh_big: ['sfx/whoosh-big.mp3', 0.3], impact: ['sfx/impact-deep-whoosh.mp3', 0.45], boom: ['sfx/impact-cine-big.mp3', 0.4], paper: ['sfx/paper-slide.mp3', 0.5], swoosh: ['sfx/swoosh-slow.mp3', 0.3], thunder: ['sfx2/rumble.wav', 0.7], tick: ['sfx2/tick.wav', 0.5], type: ['sfx2/typewriter.wav', 0.35], shutter: ['sfx2/shutter.wav', 0.5], hiss: ['sfx2/hiss.wav', 0.25], drone: ['sfx2/drone.wav', 0.3] };

export const Episode: React.FC = () => <Finish>
  {SHOTS.map((s) => <Sequence key={s.id} from={Math.round(s.params.start_s * FPS)} durationInFrames={durF(s) + 1} premountFor={45}>
    <TransitionIn kind={s.transition_in}><Scene s={s} /></TransitionIn><Chrome s={s} />
    {(s.sfx ?? []).filter((k) => SFX[k]).map((k, i) => <Audio key={i} src={staticFile(SFX[k][0])} volume={SFX[k][1]} />)}
  </Sequence>)}
  <Audio src={staticFile('ep/voice.wav')} />
  <Audio src={staticFile('ep/music.wav')} />
</Finish>;
