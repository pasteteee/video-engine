// Real Story episode renderer (Mars Landing build + Bloop library types): reads the shot list and maps each scene_type to a component.
import React from 'react';
import { AbsoluteFill, Audio, Freeze, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { geoMercator, geoPath } from 'd3-geo';
import SL from './ep/shotlist.json';
import WORDS from './ep/words.json';
import LINES from './ep/lines.json';
import MEDIA_JSON from './ep/media.json';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, GROUND2, INK, MUTED, RED, SHADOW, SIGNAL, SPRING_SOFT, TINT, io, out, rgba, rng } from './kit/tokens';
import { Callout, Hairline, Kinetic, Mono, Odometer, StopBlock, Unredact } from './kit/Type';
import { CUSTOM } from './custom';
import { Finish, Grain, SceneBg, Tag } from './kit/Brand';
import { CircleCallout, Pin, useLand } from './kit/Geo';
import { DataPlotReal, DayCounter, EvidenceBoard, GlobeRoute, MapPins, ScaleStack, StockBroll } from './kit/Extra';

export type Shot = { id: string; line_ids: string[]; scene_type: string; duration_s: number; params: any; variant?: string; custom?: { component: string; brief: string; register?: string }; media_ids?: string[]; source_line?: string; transition_in?: string; sfx?: string[]; on_screen_text?: string[] };
export const FPS = 30;
const SHOTS = (SL as any).shots as Shot[];
const END_S = SHOTS[SHOTS.length - 1].params.start_s + SHOTS[SHOTS.length - 1].duration_s;
export const EP_FRAMES = Math.round(END_S * FPS) + 15;
export const MEDIA: Record<string, { src: string; w: number; h: number }> = MEDIA_JSON as any;
export const med = (id?: string) => staticFile('ep/' + MEDIA[id!].src);
const AMBER = ACCENT_EP;
const CHAPTERS: Record<string, [number, string] | null> = (SL as any).chapters ?? {};
const chapterOf = (s: Shot) => CHAPTERS[(LINES as any[]).find((l) => l.id === s.line_ids[0])?.chapter ?? 'cold'] ?? null;
export const durF = (s: Shot) => Math.round(s.duration_s * FPS);
const N_CH = new Set(Object.values(CHAPTERS).filter(Boolean).map((c) => c![0])).size;

// ---------- shared pieces ----------
export const BottomShade: React.FC<{ k?: number }> = ({ k = 1 }) => <AbsoluteFill style={{ background: `linear-gradient(180deg, ${rgba(GROUND, 0.35 * k)} 0%, ${rgba(GROUND, 0)} 22%, ${rgba(GROUND, 0)} 55%, ${rgba(GROUND, 0.85 * k)} 100%)` }} />;
export const Label: React.FC<{ text: string; f0: number; x?: number; y?: number; red?: boolean; size?: number; align?: 'left' | 'right'; color?: string }> = ({ text, f0, x = 90, y = 820, red, size = 60, align = 'left', color = BONE }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const p = spring({ frame: f - f0, fps, config: SPRING_SOFT });
  if (f < f0) return null;
  return <div style={{ position: 'absolute', left: align === 'left' ? x : undefined, right: align === 'right' ? x : undefined, top: y, transform: `translateY(${(1 - p) * 30}px)`, opacity: Math.min(1, p * 1.5) }}>
    <div style={{ ...DISP(size * 1.25, 70, 800), color, whiteSpace: 'nowrap', textShadow: SHADOW }}>{text}{red ? <StopBlock size={size * 1.25} p={Math.min(1, Math.max(0, (f - f0 - 6) / 8))} /> : null}</div>
  </div>;
};
const cover = (iw: number, ih: number, bw: number, bh: number) => { const s = Math.max(bw / iw, bh / ih); return { s, w: iw * s, h: ih * s }; };
export const ImageCam: React.FC<{ id: string; from: number[]; to: number[]; dur: number; filter?: string; children?: (map: (x: number, y: number) => [number, number]) => React.ReactNode }> = ({ id, from, to, dur, filter, children }) => {
  const f = useCurrentFrame(); const { width: W, height: H } = useVideoConfig(); const m = MEDIA[id];
  const p = interpolate(f, [0, dur], [0, 1], { ...C, easing: io });
  const cx = from[0] + (to[0] - from[0]) * p, cy = from[1] + (to[1] - from[1]) * p, z = from[2] * Math.pow(to[2] / from[2], p);
  const cv = cover(m.w, m.h, W, H);
  const px = Math.min(Math.max(cx * cv.w, W / 2 / z), cv.w - W / 2 / z), py = Math.min(Math.max(cy * cv.h, H / 2 / z), cv.h - H / 2 / z);
  const map = (x: number, y: number): [number, number] => [W / 2 + (x * cv.w - px) * z, H / 2 + (y * cv.h - py) * z];
  return <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: '#000' }}>
    <Img src={med(id)} style={{ position: 'absolute', left: 0, top: 0, width: cv.w, height: cv.h, transformOrigin: '0 0', transform: `translate(${W / 2}px, ${H / 2}px) scale(${z}) translate(${-px}px, ${-py}px)`, filter }} />
    {children ? children(map) : null}
  </AbsoluteFill>;
};
const DUST = (() => { const r = rng(7); return Array.from({ length: 60 }, () => ({ x: r() * 1920, y: r() * 1080, z: 0.3 + r() * 1.4, a: 0.05 + r() * 0.22, ph: r() * 6 })); })();
export const Dust: React.FC<{ dir?: number }> = ({ dir = 1 }) => { const f = useCurrentFrame(); return <svg width={1920} height={1080} style={{ position: 'absolute' }}>{DUST.map((d, i) => { const x = (d.x + f * d.z * 0.9 * dir + 1920 * 4) % 1920; const y = (d.y - f * d.z * 0.35 + Math.sin(f / 30 + d.ph) * 6 + 1080 * 4) % 1080; return <circle key={i} cx={x} cy={y} r={d.z * 1.8} fill={rgba(BONE, d.a)} />; })}</svg>; };
const Video: React.FC<{ id: string; trim?: number; style?: React.CSSProperties; volume?: number }> = ({ id, trim = 0, style, volume }) =>
  <OffthreadVideo src={med(id)} startFrom={Math.round(trim * FPS)} muted={!volume} volume={volume} style={{ width: '100%', height: '100%', objectFit: 'cover', ...style }} />;
const Big: React.FC<{ text: string; f0: number; size: number; x: number; y: number; color?: string; stop?: boolean; flow?: boolean }> = ({ text, f0, size, x, y, color = BONE, stop, flow }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [f0, f0 + 14], [0, 1], { ...C, easing: out });
  return <div style={{ position: flow ? 'relative' : 'absolute', left: x, top: y, overflow: 'hidden', paddingBottom: 8 }}><div style={{ ...DISP(size), color, textShadow: SHADOW, transform: `translateY(${(1 - p) * 100}%)`, whiteSpace: 'nowrap' }}>{text}{stop ? <StopBlock size={size} p={interpolate(f, [f0 + 10, f0 + 18], [0, 1], C)} /> : null}</div></div>;
};

// ---------- archival scenes ----------
const FilmClip: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const z = (P.zoom ?? 1) + (P.push ?? 0.05) * interpolate(f, [0, d], [0, 1], C);
  const reel = s.variant === 'split_reel';
  return <AbsoluteFill style={{ backgroundColor: '#000' }}>
    <AbsoluteFill style={{ transform: `scale(${z})`, transformOrigin: P.origin ?? '50% 50%' }}><Video id={s.media_ids![0]} trim={P.trim} volume={P.volume} style={{ filter: 'contrast(1.05) saturate(1.02)' }} /></AbsoluteFill>
    {reel ? <AbsoluteFill style={{ background: `linear-gradient(90deg, ${rgba(GROUND, 0.75)} 0%, ${rgba(GROUND, 0)} 30%)` }} /> : null}
    <BottomShade k={P.shade ?? 0.8} />
    {P.tag ? <Tag text={P.tag} f0={6} x={1860} y={64} size={22} color={AMBER} align="right" /> : null}
    {P.label ? <Label text={P.label} f0={P.label_at ? Math.round(P.label_at * FPS) : 10} y={P.label_y ?? 840} size={P.label_size ?? 56} red={P.red} /> : null}
  </AbsoluteFill>;
};

const FilmFreeze: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const fz = Math.round((P.freeze ?? 1.5) * FPS);
  const frozen = f >= fz; const flash = interpolate(f, [fz, fz + 6], [0.5, 0], C);
  return <AbsoluteFill style={{ backgroundColor: '#000' }}>
    <AbsoluteFill style={{ transform: `scale(${1 + 0.04 * interpolate(f, [0, d], [0, 1], C)})` }}>
      <Freeze frame={fz} active={(fr) => fr >= fz}><Video id={s.media_ids![0]} trim={P.trim} /></Freeze>
    </AbsoluteFill>
    {frozen ? <AbsoluteFill style={{ background: rgba(GROUND, 0.25) }} /> : null}
    <AbsoluteFill style={{ backgroundColor: '#fff', opacity: flash }} />
    <BottomShade k={0.8} />
    {frozen ? <Mono text={P.stamp ?? 'FRAME HELD'} f0={fz + 2} size={22} color={AMBER} style={{ position: 'absolute', right: 70, top: 64 }} /> : null}
    {frozen && s.variant === 'freeze_trace' && P.trace ? <svg width={1920} height={1080} style={{ position: 'absolute' }}><path d={P.trace} fill="none" stroke={AMBER} strokeWidth={5} strokeLinecap="round" strokeDasharray="3000" strokeDashoffset={3000 * (1 - interpolate(f, [fz + 4, fz + 34], [0, 1], { ...C, easing: io }))} /></svg> : null}
    {frozen ? (P.callouts ?? []).map((c: any, i: number) => <Callout key={i} text={c.text} sub={c.sub} at={c.at} label={c.label} f0={fz + 6 + i * 12} size={54} color={BONE} />) : null}
    {P.label ? <Label text={P.label} f0={fz + 8} y={860} size={52} /> : null}
  </AbsoluteFill>;
};

const PhotoDetailZoom: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const v = s.variant ?? 'circle_lands'; const at = Math.round(d * (P.circle_at ?? 0.5));
  return <AbsoluteFill>
    <ImageCam id={s.media_ids![0]} from={P.from} to={P.to} dur={d} filter={P.filter}>{(map) => P.circle ? (() => { const [x, y] = map(P.circle[0], P.circle[1]); const cl = interpolate(f, [at, at + 16], [0, 1], { ...C, easing: io });
      return <svg width={1920} height={1080} style={{ position: 'absolute' }}>
        {v === 'crop_marks'
          ? <g opacity={cl} stroke={AMBER} strokeWidth={3}><line x1={x - 2000} y1={y} x2={x - 60} y2={y} /><line x1={x + 60} y1={y} x2={x + 2000} y2={y} /><line x1={x} y1={y - 2000} x2={x} y2={y - 60} /><line x1={x} y1={y + 60} x2={x} y2={y + 2000} /></g>
          : <CircleCallout x={x} y={y} r={v === 'magnifier' ? 190 : (P.r ?? 120)} f0={at} dir={P.dir ?? [1, -0.5]} />}
      </svg>; })() : null}</ImageCam>
    <BottomShade />
    {P.label ? <Label text={P.label} f0={P.label_at ? Math.round(P.label_at * FPS) : at + 14} x={P.lx ?? 90} y={P.ly ?? 840} size={P.size ?? 56} red={P.red} /> : null}
    {P.sub ? <Mono text={P.sub} f0={(P.label_at ? Math.round(P.label_at * FPS) : at + 14) + 12} size={24} color={AMBER} style={{ position: 'absolute', left: (P.lx ?? 90) + 4, top: (P.ly ?? 840) + (P.size ?? 56) * 1.25 + 12 }} /> : null}
  </AbsoluteFill>;
};

const PhotoParallax: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const p = interpolate(f, [0, d], [0, 1], { ...C, easing: io }); const v = s.variant ?? 'push_in';
  const tr = v === 'lateral_drift' ? `scale(1.14) translateX(${-50 + 100 * p}px)` : v === 'rack_focus' ? `scale(${1.08 + 0.05 * p})` : `rotateY(${-3 + 6 * p}deg) rotateX(${1.5 - 3 * p}deg) scale(${1.1 + 0.1 * p})`;
  const blur = v === 'rack_focus' ? interpolate(f, [0, 24], [8, 0], C) : 0;
  const P = s.params;
  return <AbsoluteFill style={{ backgroundColor: '#000', perspective: 1400 }}>
    <AbsoluteFill style={{ transform: tr, transformOrigin: P.origin ?? '50% 50%' }}><Img src={med(s.media_ids![0])} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: P.pos ?? '50% 50%', filter: blur ? `blur(${blur}px)` : undefined }} /></AbsoluteFill>
    <Dust dir={1} />
    <AbsoluteFill style={{ background: `linear-gradient(${100 + 40 * p}deg, ${rgba(BONE, 0)} 30%, ${rgba(BONE, 0.07)} 50%, ${rgba(BONE, 0)} 70%)`, mixBlendMode: 'screen' }} />
    <BottomShade />
    {P.label ? <Label text={P.label} f0={P.label_at ? Math.round(P.label_at * FPS) : 8} y={P.ly ?? 840} size={P.size ?? 56} red={P.red} /> : null}
    {P.sub ? <Mono text={P.sub} f0={20} size={24} color={AMBER} style={{ position: 'absolute', left: 94, top: (P.ly ?? 840) + (P.size ?? 56) * 1.25 + 12 }} /> : null}
  </AbsoluteFill>;
};

const PhotoLighttable: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const d = durF(s); const m = MEDIA[s.media_ids![0]];
  const p = spring({ frame: f - 2, fps, config: { damping: 20, stiffness: 90 } });
  const z = 1 + (s.params.push ?? 0.06) * interpolate(f, [0, d], [0, 1], { ...C, easing: io });
  const ch = Math.min(860, 1100 * m.h / m.w), cw = Math.min(1100, (ch * m.w) / m.h); const rot = s.variant === 'contact_strip' ? -1.8 : s.variant === 'stack_shuffle' ? 2.2 : 1.2;
  return <AbsoluteFill style={{ backgroundColor: GROUND }}>
    <Img src={med(s.media_ids![0])} style={{ position: 'absolute', inset: -60, width: 2040, height: 1200, objectFit: 'cover', filter: 'blur(28px) brightness(0.32) saturate(0.8)', transform: `scale(${1.05 + (z - 1)})` }} />
    {s.variant === 'stack_shuffle' && s.media_ids![1] ? <Img src={med(s.media_ids![1])} style={{ position: 'absolute', left: 1880 - cw - 90, top: 150, width: cw, height: ch, objectFit: 'cover', transform: `rotate(-5deg)`, opacity: 0.55, boxShadow: '0 30px 80px rgba(0,0,0,0.6)' }} /> : null}
    <div style={{ position: 'absolute', left: 1880 - cw - 30, top: 540 - ch / 2, width: cw, height: ch, transform: `translateX(${(1 - p) * 500}px) rotate(${(1 - p) * 6 + rot}deg) scale(${z})`, opacity: Math.min(1, p * 2), boxShadow: '0 30px 80px rgba(0,0,0,0.6)' }}>
      <Img src={med(s.media_ids![0])} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
    </div>
    <div style={{ position: 'absolute', left: 90, top: 400, width: Math.max(560, 1880 - cw - 200) }}>
      <RevealWords text={s.params.label} f0={14} size={s.params.label.length > 34 ? 46 : 60} />
    </div>
  </AbsoluteFill>;
};
const RevealWords: React.FC<{ text: string; f0: number; size: number; color?: string }> = ({ text, f0, size, color = INK }) => {
  const f = useCurrentFrame(); const parts = text.split(' · ');
  return <>{parts.map((t, i) => { const p = interpolate(f, [f0 + i * 10, f0 + i * 10 + 16], [0, 1], { ...C, easing: out });
    return <div key={i} style={{ overflow: 'hidden', paddingBottom: 6 }}><div style={{ ...(i === 0 ? DISP(size * 1.3, 70, 820) : { fontFamily: FONT.mono, fontWeight: 500, fontSize: size * 0.42, letterSpacing: '0.12em', marginTop: 22 }), lineHeight: 1.0, color: i === 0 ? color : AMBER, transform: `translateY(${(1 - p) * 100}%)`, textShadow: SHADOW }}>{t}</div></div>; })}
    <div style={{ height: 2, width: 420 * interpolate(f, [f0 + 10, f0 + 30], [0, 1], { ...C, easing: io }), background: TINT, opacity: 0.8, marginTop: 30 }} /></>;
};

const PhotoCompare: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const d = durF(s); const ids = s.media_ids!; const st = Math.round((s.params.stagger ?? 1) * FPS);
  const bw = 820, bh = 600;
  return <SceneBg drift={0.4}>{ids.map((id, i) => { const f0 = i === 0 ? 0 : st; const p = spring({ frame: f - f0, fps, config: { damping: 18, stiffness: 110 } }); if (f < f0) return null;
    const zz = interpolate(f, [f0, d], [1, 1.08], C); const x = i === 0 ? 110 : 990;
    return <div key={id} style={{ position: 'absolute', left: x, top: 150, width: bw, height: bh, transform: `translateX(${(1 - p) * (i === 0 ? -300 : 400)}px)`, opacity: Math.min(1, p * 2) }}>
      <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', backgroundColor: '#000' }}><Img src={med(id)} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: (s.params.pos ?? [])[i] ?? '50% 50%', transform: `scale(${zz})` }} /></div>
      <div style={{ position: 'absolute', left: 0, top: bh + 30, ...DISP(84), color: i === 1 ? AMBER : INK, textShadow: SHADOW }}>{s.params.labels[i]}</div>
      <Mono text={(s.params.subs ?? [])[i] ?? ''} f0={f0 + 16} size={22} color={MUTED} style={{ position: 'absolute', left: 2, top: bh + 130 }} />
    </div>; })}</SceneBg>;
};

const SatelliteReveal: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params;
  const tiles = s.variant === 'tile_assemble';
  return <AbsoluteFill style={{ background: GROUND }}>
    <ImageCam id={s.media_ids![0]} from={P.from} to={P.to} dur={d} filter={P.filter}>{(map) => <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {(P.marks ?? []).map((m: any, i: number) => { const [x, y] = map(m[0], m[1]); const a = Math.round((m[3] ?? 0.4 + i * 0.12) * d); const q = interpolate(f, [a, a + 12], [0, 1], C);
        return <g key={i} opacity={q}><circle cx={x} cy={y} r={14 + 10 * (1 - q)} fill="none" stroke={AMBER} strokeWidth={3} /><text x={x + 26} y={y + 8} fontFamily={FONT.mono} fontSize={24} letterSpacing={3} fill={BONE} style={{ textShadow: SHADOW } as any}>{m[2]}</text></g>; })}
    </svg>}</ImageCam>
    {tiles ? <svg width={1920} height={1080} style={{ position: 'absolute' }}>{Array.from({ length: 48 }, (_, i) => { const x = (i % 8) * 240, y = Math.floor(i / 8) * 180; const r = (Math.sin(i * 91.7) * 43758.5) % 1; const t0 = 2 + Math.abs(r) * 26; return <rect key={i} x={x} y={y} width={241} height={181} fill={GROUND} opacity={interpolate(f, [t0, t0 + 6], [1, 0], C)} />; })}</svg> : null}
    <BottomShade />
    {P.label ? <Label text={P.label} f0={P.label_at ? Math.round(P.label_at * FPS) : 20} y={P.ly ?? 840} size={56} /> : null}
    {P.sub ? <Mono text={P.sub} f0={32} size={24} color={AMBER} style={{ position: 'absolute', left: 94, top: (P.ly ?? 840) + 82 }} /> : null}
  </AbsoluteFill>;
};

const DocumentHighlight: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const P = s.params; const d = durF(s);
  const i0 = P.text.indexOf(P.hl); const before = P.text.slice(0, i0); const after = P.text.slice(i0 + P.hl.length); const hlw = P.hl.split(' ');
  const cam = interpolate(f, [10, d - 10], [0, 1], { ...C, easing: io });
  const sweep = interpolate(f, [18, 18 + hlw.length * 4], [0, hlw.length], C);
  const pin = spring({ frame: f - 2, fps, config: SPRING_SOFT });
  return <SceneBg drift={0.3}>
    <AbsoluteFill style={{ transform: `scale(${1 + 0.14 * cam}) translateY(${-40 * cam}px)`, transformOrigin: '50% 55%' }}>
      <div style={{ position: 'absolute', left: 300, top: 150, width: 1320, padding: '56px 80px 64px', background: '#EEEAE0', boxShadow: '0 40px 120px rgba(0,0,0,0.55)', transform: `rotate(-0.8deg) translateY(${(1 - pin) * 80}px)`, opacity: pin }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: FONT.mono, fontSize: 22, letterSpacing: 3, color: '#5A5A55', borderBottom: '2px solid #BDB8AA', paddingBottom: 16 }}><span>{P.head}</span><span>{P.id}</span></div>
        <div style={{ fontFamily: FONT.mono, fontSize: 32, lineHeight: 1.55, color: '#2A2A28', marginTop: 28 }}>
          {before}{hlw.map((w: string, i: number) => { const a = Math.max(0, Math.min(1, sweep - i)); return <span key={i} style={{ backgroundImage: `linear-gradient(90deg, ${rgba(ACCENT_EP, 0.9)} ${a * 100}%, transparent ${a * 100}%)`, color: a > 0.5 ? '#111' : '#2A2A28' }}>{w}{i < hlw.length - 1 ? ' ' : ''}</span>; })}{after}
        </div>
      </div>
    </AbsoluteFill>
  </SceneBg>;
};

const QuoteCard: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const words: string[] = P.quote.split(' ');
  const a0 = Math.round((P.at ?? 0.3) * FPS); const per = P.per ?? 7; const side = s.variant === 'portrait_side';
  const W0 = side ? 1060 : 1500;
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    {side && s.media_ids?.[0] ? <AbsoluteFill style={{ left: 1180 }}><Img src={med(s.media_ids[0])} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: P.pos ?? '40% 40%', opacity: interpolate(f, [0, 12], [0, 0.9], C), maskImage: 'linear-gradient(90deg, transparent 0%, #000 35%)', WebkitMaskImage: 'linear-gradient(90deg, transparent 0%, #000 35%)' }} /></AbsoluteFill> : null}
    <Mono text={P.name} f0={4} size={30} color={BONE} style={{ position: 'absolute', left: 164, top: 230 }} />
    <Mono text={P.role} f0={14} size={22} color={MUTED} weight={400} style={{ position: 'absolute', left: 164, top: 278 }} />
    <div style={{ position: 'absolute', left: 156, top: 370, width: W0, fontFamily: FONT.quote, fontStyle: 'italic', fontWeight: 420, fontVariationSettings: "'opsz' 72", fontSize: P.size ?? 104, lineHeight: 1.08, color: INK, textShadow: SHADOW }}>
      {words.map((w, i) => { const p = interpolate(f, [a0 + i * per, a0 + i * per + 10], [0, 1], C); return <span key={i} style={{ opacity: p, filter: `blur(${(1 - p) * 6}px)`, color: (P.hl ?? []).includes(w.replace(/[^A-Za-z]/g, '').toLowerCase()) ? AMBER : INK }}>{w} </span>; })}
    </div>
  </SceneBg>;
};

// Real audio with its waveform (envelope precomputed from the clip) and the transcript typed in sync.
const TranscriptWaveform: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const env: number[] = P.env ?? []; const t = f / FPS;
  const a0 = P.audio_at ?? 0; const reel = s.variant === 'reel_to_reel';
  const k = Math.max(0, Math.floor((t - a0) * 20)); const N = 140;
  return <AbsoluteFill style={{ background: GROUND }}>
    {s.media_ids?.[0] ? (MEDIA[s.media_ids[0]].src.endsWith('.mp4')
      ? <AbsoluteFill style={{ opacity: 0.38 }}><Video id={s.media_ids[0]} trim={P.trim ?? 0} /></AbsoluteFill>
      : <AbsoluteFill style={{ opacity: 0.3 }}><Img src={med(s.media_ids[0])} style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(3px)' }} /></AbsoluteFill>) : null}
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 55%, ${rgba(GROUND2, 0.4)} 0%, ${rgba(GROUND, 0.9)} 80%)` }} />
    <Mono text={P.who} f0={4} size={24} color={AMBER} style={{ position: 'absolute', left: 164, top: 200 }} />
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {Array.from({ length: N }, (_, i) => { const j = k - (N - 1 - i); const v = j >= 0 && j < env.length ? env[j] : 0.02; const h = 6 + v * 300;
        return <rect key={i} x={164 + i * 11.4} y={(reel ? 760 : 560) - h / 2} width={5} height={h} fill={i > N - 4 ? AMBER : rgba(BONE, 0.25 + 0.6 * (i / N))} />; })}
      {reel ? [560, 1360].map((cx, i) => <g key={i} transform={`rotate(${f * (i ? 5 : 6)} ${cx} 400)`}><circle cx={cx} cy={400} r={150} fill="none" stroke={rgba(TINT, 0.6)} strokeWidth={3} />{[0, 120, 240].map((a) => <line key={a} x1={cx} y1={400} x2={cx + 140 * Math.cos(a * Math.PI / 180)} y2={400 + 140 * Math.sin(a * Math.PI / 180)} stroke={rgba(TINT, 0.6)} strokeWidth={3} />)}</g>) : null}
    </svg>
    {(P.lines ?? []).map((l: any, i: number) => { const s0 = Math.round(l[0] * FPS); const s1 = Math.round((l[1] ?? 99) * FPS); if (f < s0) return null; const n = Math.floor(interpolate(f, [s0, s0 + l[2].length * 0.9], [0, l[2].length], C)); const o = interpolate(f, [s1, s1 + 8], [1, 0], C);
      return <div key={i} style={{ position: 'absolute', left: 164, top: reel ? 900 : 700, width: 1580, opacity: o, fontFamily: FONT.quote, fontStyle: 'italic', fontSize: 64, lineHeight: 1.12, color: BONE, textShadow: SHADOW }}>“{l[2].slice(0, n)}<span style={{ opacity: 0 }}>{l[2].slice(n)}</span>”</div>; })}
  </AbsoluteFill>;
};

// ---------- blueprint scenes ----------
const KineticType: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const words: string[] = s.params.words; const n = words.length; const d = durF(s);
  const red = s.params.red < 0 ? n - 1 : s.params.red; const v = s.variant ?? 'rise_narrow';
  const size = s.params.size ?? (n <= 2 ? 250 : n === 3 ? 200 : 170); const lh = size * 0.98;
  const lines: string[][] = s.params.lines ?? (n <= 3 ? words.map((w) => [w]) : [words.slice(0, Math.ceil(n / 2)), words.slice(Math.ceil(n / 2))]);
  let acc: [number, number] = [-1, -1]; { let k = 0; lines.forEach((l, li) => l.forEach((_, wi) => { if (k++ === red) acc = [li, wi]; })); }
  const top = 540 - (lines.length * lh) / 2 - 10; const push = interpolate(f, [0, d], [1, 1.05], C);
  const step = Math.max(3, Math.min(7, Math.round((d * 0.35) / n)));
  return <SceneBg style={{ transform: `scale(${push})` }}>
    {v === 'unredact'
      ? <Unredact lines={lines.map((l) => l.join(' '))} top={top} size={size} f0={4} step={8} x={160} exitAt={d - 8} />
      : <Kinetic lines={lines} top={top} size={size} f0={4} step={step} variant={v} accent={acc} x={160} exitAt={d - 8} />}
  </SceneBg>;
};

const QuestionCard: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const q: string[] = s.params.q; const size = s.params.size ?? 190; const d = durF(s); const v = s.variant ?? 'unredact';
  const top = 540 - (q.length * size * 0.98) / 2 - 50;
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})` }}>
    {v === 'unredact' ? <Unredact lines={q} top={top} size={size} f0={6} step={10} x={160} exitAt={d - 8} />
      : <Kinetic lines={q.map((l) => [l])} top={top} size={size} f0={4} step={6} variant="rise_narrow" accent={[q.length - 1, 0]} x={160} exitAt={d - 8} />}
    {v === 'hold_cursor' ? <div style={{ position: 'absolute', left: 164, top: top + q.length * size * 0.98 + 48, width: 16, height: 34, background: AMBER, opacity: Math.floor(f / 15) % 2 ? 0 : 1 }} /> : null}
    {s.params.sub ? <Mono text={s.params.sub} f0={40} size={28} color={MUTED} style={{ position: 'absolute', left: v === 'hold_cursor' ? 200 : 164, top: top + q.length * size * 0.98 + 50 }} /> : null}
  </SceneBg>;
};

const ChapterCard: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s);
  if (P.end) {
    return <SceneBg style={{ background: '#0e0f11' }}>
      <Unredact lines={['REAL STORY']} top={380} size={190} f0={8} />
      <Mono text={P.line1} f0={40} size={24} color={MUTED} style={{ position: 'absolute', left: 0, right: 0, top: 600, textAlign: 'center' }} />
      <Mono text={P.line2} f0={58} size={18} color={rgba(BONE, 0.55)} weight={400} style={{ position: 'absolute', left: 0, right: 0, top: 650, textAlign: 'center' }} />
    </SceneBg>;
  }
  const hp = interpolate(f, [8, 24], [0, 1], { ...C, easing: (t) => 1 - Math.pow(1 - t, 4) }); const big = s.variant === 'big_index';
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    {big ? <div style={{ position: 'absolute', right: 120, top: 120, ...DISP(560, 62, 880), color: rgba(ACCENT_EP, 0.16) }}>{String(P.n).padStart(2, '0')}</div> : null}
    <Mono text={String(P.n).padStart(2, '0') + ' / ' + String(N_CH).padStart(2, '0')} f0={2} size={30} color={AMBER} style={{ position: 'absolute', left: 164, top: 360 }} />
    <div style={{ position: 'absolute', left: 160, top: 420, height: 230, overflow: 'hidden' }}>
      <div style={{ ...DISP(220), color: BONE, transform: `translateY(${(1 - hp) * 100}%)`, lineHeight: '230px', whiteSpace: 'nowrap' }}>{P.title}</div></div>
    <Hairline x={164} y={672} w={1500} f0={4} dur={26} />
  </SceneBg>;
};

const BigNumber: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s);
  const up = interpolate(f, [26, 40], [0, 1], { ...C, easing: out }); const size = P.size ?? 380;
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})` }}>
    <Mono text={P.label} f0={2} size={28} color={MUTED} style={{ position: 'absolute', left: 164, top: 250 }} />
    <div style={{ position: 'absolute', left: 156, top: 320, display: 'flex', alignItems: 'flex-end', gap: 36 }}>
      {typeof P.value === 'number' ? <Odometer value={P.value} size={size} f0={6} /> : <Big text={P.value} f0={6} size={size} x={0} y={0} flow />}
      <div style={{ ...DISP(150, 62, 840), color: AMBER, opacity: up, transform: `translateY(${(1 - up) * 30}px)`, marginBottom: typeof P.value === 'number' ? 6 : 14 }}>{P.unit}</div>
    </div>
    <Hairline x={164} y={704} w={1100} f0={30} />
    <Mono text={P.note} f0={44} size={26} color={BONE} style={{ position: 'absolute', left: 164, top: 736 }} />
  </SceneBg>;
};

const TimelineScroll: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const P = s.params; const d = durF(s); const ev: string[][] = P.events;
  const gap = 560; const target = P.hl * gap; const cam = interpolate(f, [8, d - 20], [0, target], { ...C, easing: io }); const x0 = 260;
  return <SceneBg drift={-0.6}>
    <div style={{ position: 'absolute', left: 0, top: 0, width: 6000, height: 1080, transform: `translateX(${-cam}px)` }}>
      <svg width={6000} height={1080} style={{ position: 'absolute' }}><line x1={0} y1={560} x2={x0 + gap * (ev.length - 1) + 1200} y2={560} stroke={rgba(TINT, 0.4)} strokeWidth={2} />
        <line x1={0} y1={560} x2={x0 + cam + 200} y2={560} stroke={AMBER} strokeWidth={5} /></svg>
      {ev.map((e, i) => { const x = x0 + i * gap; const hl = i === P.hl; const p = spring({ frame: f - (4 + i * 5), fps, config: SPRING_SOFT });
        const edge = interpolate(x - cam, [-260, 120], [0, 1], C);
        return <div key={i} style={{ position: 'absolute', left: x - 14, top: 546, opacity: edge }}>
          <div style={{ width: 22, height: 22, marginLeft: 7, marginTop: 7, borderRadius: 11, background: hl ? AMBER : TINT, transform: `scale(${p})` }} />
          <div style={{ position: 'absolute', left: 0, top: -120, fontFamily: FONT.mono, fontSize: 30, letterSpacing: 4, color: hl ? AMBER : MUTED, whiteSpace: 'nowrap', opacity: p }}>{e[0]}</div>
          <div style={{ position: 'absolute', left: 0, top: 70, ...DISP(hl ? 120 : 70), lineHeight: 0.95, color: hl ? BONE : rgba(BONE, 0.6), textShadow: SHADOW, width: 520, opacity: p, transform: `translateY(${(1 - p) * 30}px)` }}>{e[1]}</div>
        </div>; })}
    </div>
  </SceneBg>;
};

// Our calculation: a dot crosses a 45 km bar in the real number of seconds.
const ScaleCompare: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const x0 = 200, x1 = 1720; const T = P.seconds ?? 8;
  const t0 = 14; const p = interpolate(f, [t0, t0 + Math.min(T * FPS, d - t0 - 10)], [0, 1], C); const secs = p * T;
  return <SceneBg drift={0.2}>
    <Mono text={P.kicker} f0={2} size={26} color={AMBER} style={{ position: 'absolute', left: x0, top: 230 }} />
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <ellipse cx={(x0 + x1) / 2} cy={560} rx={(x1 - x0) / 2} ry={150} fill={rgba(GROUND2, 0.6)} stroke={rgba(TINT, 0.7)} strokeWidth={3} strokeDasharray="10 10" />
      <line x1={x0} y1={760} x2={x1} y2={760} stroke={TINT} strokeWidth={2} /><line x1={x0} y1={745} x2={x0} y2={775} stroke={TINT} strokeWidth={2} /><line x1={x1} y1={745} x2={x1} y2={775} stroke={TINT} strokeWidth={2} />
      <line x1={x0} y1={560} x2={x0 + (x1 - x0) * p} y2={560} stroke={AMBER} strokeWidth={4} />
      <circle cx={x0 + (x1 - x0) * p} cy={560} r={14} fill={BONE} />
    </svg>
    <Mono text={P.span} f0={8} size={26} color={BONE} style={{ position: 'absolute', left: 0, right: 0, textAlign: 'center', top: 790 }} />
    <div style={{ position: 'absolute', left: x0, top: 300, ...DISP(170), color: BONE, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>{secs.toFixed(1)} S</div>
  </SceneBg>;
};

// Altitude / speed readouts that step through the values mission control called out.
const CounterTicker: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s); const steps: any[] = P.steps; const t = f / FPS;
  let k = 0; steps.forEach((st, i) => { if (t >= st[0]) k = i; }); const st = steps[k]; const flip = interpolate(f - Math.round(st[0] * FPS), [0, 6], [1, 0], C);
  return <AbsoluteFill style={{ background: GROUND }}>
    {s.media_ids?.[0] ? <AbsoluteFill style={{ opacity: 0.3 }}><Video id={s.media_ids[0]} trim={P.trim ?? 0} /></AbsoluteFill> : null}
    <AbsoluteFill style={{ background: `linear-gradient(90deg, ${rgba(GROUND, 0.95)} 0%, ${rgba(GROUND, 0.6)} 60%, ${rgba(GROUND, 0.3)} 100%)` }} />
    {[['ALTITUDE', st[1]], ['SPEED', st[2]]].map(([lab, val], i) => <div key={i} style={{ position: 'absolute', left: 164, top: 230 + i * 330 }}>
      <Mono text={lab as string} f0={2 + i * 6} size={26} color={AMBER} />
      <div style={{ ...DISP(230, 62, 860), color: BONE, marginTop: 18, textShadow: SHADOW, transform: `translateY(${flip * -24}px)`, opacity: 1 - flip * 0.6, fontVariantNumeric: 'tabular-nums' }}>{val as string}</div>
    </div>)}
    <Mono text={P.note ?? 'VALUES CALLED OUT ON THE MISSION-CONTROL LOOP'} f0={20} size={20} color={MUTED} style={{ position: 'absolute', left: 168, top: 930 }} />
    <div style={{ position: 'absolute', right: 120, top: 260, ...DISP(64, 75, 760), color: AMBER, textShadow: SHADOW, textAlign: 'right' }}>{st[3] ?? ''}</div>
  </AbsoluteFill>;
};

const DiagramBuild: React.FC<{ s: Shot }> = ({ s }) => {
  const f = useCurrentFrame(); const d = durF(s); const P = s.params; const v = s.variant ?? 'part_by_part';
  const st = (a: number, b: number) => interpolate(f, [a, b], [0, 1], { ...C, easing: io });
  if (v === 'trace_flow') {
    const nodes: string[][] = P.nodes; const xs = [260, 860, 1460];
    return <SceneBg drift={0.3}>
      <svg width={1920} height={1080} style={{ position: 'absolute' }}>{nodes.slice(1).map((_, i) => { const q = st(18 + i * 26, 34 + i * 26); return <g key={i}><line x1={xs[i] + 260} y1={540} x2={xs[i] + 260 + (xs[i + 1] - xs[i] - 260) * q} y2={540} stroke={AMBER} strokeWidth={4} />{q > 0.95 ? <path d={`M${xs[i + 1] - 22} 528 L${xs[i + 1] - 4} 540 L${xs[i + 1] - 22} 552`} fill="none" stroke={AMBER} strokeWidth={4} /> : null}</g>; })}</svg>
      {nodes.map((n, i) => { const q = st(4 + i * 26, 18 + i * 26); return <div key={i} style={{ position: 'absolute', left: xs[i], top: 440, width: 260, opacity: q, transform: `translateY(${(1 - q) * 20}px)` }}>
        <div style={{ fontFamily: FONT.mono, fontSize: 22, letterSpacing: 3, color: AMBER }}>{n[0]}</div>
        <div style={{ ...DISP(66, 70, 800), color: BONE, marginTop: 14, textShadow: SHADOW }}>{n[1]}</div>
        <div style={{ fontFamily: FONT.mono, fontSize: 20, letterSpacing: 2, color: MUTED, marginTop: 14 }}>{n[2]}</div></div>; })}
    </SceneBg>;
  }
  // exploded: the sky crane, side view (not to scale)
  const lower = st(36, 80); const ry = 470 + 230 * lower; const plume = 0.6 + 0.4 * Math.sin(f / 2.5);
  return <SceneBg drift={0.3}>
    <svg width={1920} height={1080} style={{ position: 'absolute', transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})`, transformOrigin: '960px 600px' }}>
      <line x1={300} y1={900} x2={1620} y2={900} stroke={rgba(TINT, 0.8)} strokeWidth={3} strokeDasharray={`${1400 * st(0, 16)} 2000`} />
      {[700, 1220].map((x, i) => <path key={i} d={`M${x} 360 L${x - 30 - 12 * plume} ${430 + 60 * plume} L${x + 30 + 12 * plume} ${430 + 60 * plume} Z`} fill={rgba(ACCENT_EP, 0.35 * st(10, 20))} />)}
      <g opacity={st(4, 18)}><rect x={640} y={250} width={640} height={110} rx={8} fill={rgba(TINT, 0.15)} stroke={BONE} strokeWidth={4} />
        {[680, 760, 1160, 1240].map((x) => <rect key={x} x={x - 14} y={350} width={28} height={26} fill={GROUND} stroke={AMBER} strokeWidth={3} />)}</g>
      {[860, 960, 1060].map((x) => <line key={x} x1={x} y1={360} x2={x} y2={ry} stroke={AMBER} strokeWidth={3} opacity={st(30, 40)} />)}
      <g transform={`translate(0 ${ry - 470})`} opacity={st(20, 34)}><rect x={760} y={470} width={400} height={120} rx={10} fill={rgba(TINT, 0.18)} stroke={BONE} strokeWidth={4} />
        {[790, 960, 1130].map((x) => <circle key={x} cx={x} cy={610} r={34} fill={GROUND} stroke={BONE} strokeWidth={4} />)}</g>
      <line x1={1420} y1={360} x2={1420} y2={900} stroke={MUTED} strokeWidth={2} opacity={st(46, 60)} /><line x1={1400} y1={360} x2={1440} y2={360} stroke={MUTED} strokeWidth={2} opacity={st(46, 60)} /><line x1={1400} y1={900} x2={1440} y2={900} stroke={MUTED} strokeWidth={2} opacity={st(46, 60)} />
    </svg>
    <div style={{ position: 'absolute', left: 1460, top: 590, opacity: st(50, 62) }}><div style={{ ...DISP(84, 70, 800), color: BONE, textShadow: SHADOW }}>{P.alt}</div><div style={{ fontFamily: FONT.mono, fontSize: 20, letterSpacing: 3, color: MUTED, marginTop: 10 }}>{P.alt_note}</div></div>
    <div style={{ position: 'absolute', left: 300, top: 440, opacity: st(40, 52) }}><div style={{ ...DISP(72, 70, 800), color: AMBER, textShadow: SHADOW }}>{P.cords}</div><div style={{ fontFamily: FONT.mono, fontSize: 20, letterSpacing: 3, color: MUTED, marginTop: 10 }}>{P.cords_note}</div></div>
    <Mono text={P.title} f0={4} size={26} color={AMBER} style={{ position: 'absolute', left: 164, top: 120 }} />
    <Mono text="DIAGRAM · NOT TO SCALE" f0={10} size={18} color={MUTED} style={{ position: 'absolute', left: 164, top: 162 }} />
  </SceneBg>;
};

// Southern California map, pin on the coordinates written in the parachute.
const MapZoom: React.FC<{ s: Shot; land: any }> = ({ s, land }) => {
  const f = useCurrentFrame(); const P = s.params; const d = durF(s);
  const z = interpolate(f, [0, d], [P.scale0 ?? 1800, P.scale1 ?? 9000], { ...C, easing: io });
  const proj = geoMercator().center(P.center).scale(z).translate([960, 540]); const path = geoPath(proj); const pt = proj(P.pt) as [number, number];
  return <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, ${GROUND2} 0%, ${GROUND} 80%)` }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}><path d={path(land) || ''} fill={rgba(TINT, 0.16)} stroke={rgba(TINT, 0.7)} strokeWidth={1.6} />
      <Pin x={pt[0]} y={pt[1]} f0={Math.round(d * 0.35)} /></svg>
    <Mono text={P.coords} f0={Math.round(d * 0.35) + 6} size={30} color={BONE} style={{ position: 'absolute', left: pt[0] + 40, top: pt[1] - 60 }} />
    <Mono text={P.place} f0={Math.round(d * 0.35) + 30} size={22} color={AMBER} style={{ position: 'absolute', left: pt[0] + 40, top: pt[1] - 14 }} />
  </AbsoluteFill>;
};

// ---------- chrome, transitions ----------
const TransitionIn: React.FC<{ kind?: string; children: React.ReactNode }> = ({ kind, children }) => {
  const f = useCurrentFrame();
  if (kind === 'dissolve') return <AbsoluteFill style={{ opacity: interpolate(f, [0, 14], [0, 1], C) }}>{children}</AbsoluteFill>;
  if (kind === 'whip') { const p = interpolate(f, [0, 8], [1, 0], { ...C, easing: out }); return <AbsoluteFill style={{ transform: `translateX(${p * 420}px)`, filter: p > 0.02 ? `blur(${p * 30}px)` : undefined }}>{children}</AbsoluteFill>; }
  if (kind === 'push') { const p = interpolate(f, [0, 12], [1, 0], { ...C, easing: out }); return <AbsoluteFill style={{ transform: `scale(${1 + p * 0.12})`, opacity: 1 - p * 0.9 }}>{children}</AbsoluteFill>; }
  if (kind === 'flash') return <AbsoluteFill>{children}<AbsoluteFill style={{ backgroundColor: '#fff', opacity: interpolate(f, [0, 7], [0.7, 0], C) }} /></AbsoluteFill>;
  return <AbsoluteFill>{children}</AbsoluteFill>;
};
const Chrome: React.FC<{ s: Shot }> = ({ s }) => {
  const ch = chapterOf(s); const t = s.scene_type;
  const showCh = ch && !['chapter_card', 'kinetic_type', 'question_card', 'big_number'].includes(t) && !s.params.no_chapter;
  return <>{showCh ? <Tag text={`${String(ch![0]).padStart(2, '0')}  ${ch![1]}`} f0={8} x={60} y={56} size={18} color={AMBER} /> : null}
    {s.source_line ? <Tag text={s.source_line.toUpperCase()} f0={14} x={60} y={1080 - 58} size={16} color="rgba(236,226,214,0.78)" /> : null}</>;
};

// a slow push so drawn graphics never hold still after they finish building
const SlowPush: React.FC<{ children: React.ReactNode }> = ({ children }) => { const f = useCurrentFrame(); return <AbsoluteFill style={{ transform: `scale(${1 + f * 0.0006})`, transformOrigin: '45% 50%' }}>{children}</AbsoluteFill>; };
const Scene: React.FC<{ s: Shot; land: any }> = ({ s, land }) => {
  switch (s.scene_type) {
    case 'film_clip': return <FilmClip s={s} />;
    case 'film_freeze_annotate': return <FilmFreeze s={s} />;
    case 'kinetic_type': return <KineticType s={s} />;
    case 'photo_detail_zoom': return <PhotoDetailZoom s={s} />;
    case 'photo_lighttable': return <PhotoLighttable s={s} />;
    case 'photo_compare': return <PhotoCompare s={s} />;
    case 'photo_parallax': return <PhotoParallax s={s} />;
    case 'satellite_reveal': return <SatelliteReveal s={s} />;
    case 'question_card': return <QuestionCard s={s} />;
    case 'chapter_card': return <ChapterCard s={s} />;
    case 'big_number': return <BigNumber s={s} />;
    case 'document_highlight': return <DocumentHighlight s={s} />;
    case 'quote_card': return <QuoteCard s={s} />;
    case 'transcript_waveform': return <TranscriptWaveform s={s} />;
    case 'timeline_scroll': return <TimelineScroll s={s} />;
    case 'scale_compare': return s.variant === 'stack_up' ? <ScaleStack s={s} d={durF(s)} med={med} media={MEDIA} /> : <ScaleCompare s={s} />;
    case 'counter_ticker': return s.variant === 'flip_digits' ? <DayCounter s={s} d={durF(s)} med={med} media={MEDIA} /> : <CounterTicker s={s} />;
    case 'diagram_build': return <SlowPush><DiagramBuild s={s} /></SlowPush>;
    case 'map_zoom': return s.params.pins ? <MapPins s={s} d={durF(s)} med={med} media={MEDIA} land={land} /> : <MapZoom s={s} land={land} />;
    case 'map_compare_scale': return <MapPins s={s} d={durF(s)} med={med} media={MEDIA} land={land} />;
    case 'globe_route': return <GlobeRoute s={s} d={durF(s)} med={med} media={MEDIA} land={land} />;
    case 'stock_broll': return <StockBroll s={s} d={durF(s)} med={med} media={MEDIA} />;
    case 'data_plot_real': return <SlowPush><DataPlotReal s={s} d={durF(s)} med={med} media={MEDIA} /></SlowPush>;
    case 'evidence_board': return <EvidenceBoard s={s} d={durF(s)} med={med} media={MEDIA} />;
    case 'custom': { const Comp = CUSTOM[s.custom?.component ?? '']; return Comp ? <Comp s={s} d={durF(s)} med={med} media={MEDIA} /> : <SceneBg><div style={{ color: RED, fontSize: 60 }}>MISSING custom {s.custom?.component}</div></SceneBg>; }
    default: return <SceneBg><div style={{ color: RED, fontSize: 60 }}>MISSING {s.scene_type}</div></SceneBg>;
  }
};

// ---------- sound ----------
const SFX: Record<string, [string, number]> = {
  whoosh: ['sfx/whoosh-fast.mp3', 0.3], whoosh_big: ['sfx/whoosh-big.mp3', 0.32], impact: ['sfx/impact-cine-big.mp3', 0.22], sub_drop: ['sfx/impact-deep-whoosh.mp3', 0.32],
  hit: ['sfx/impact-deep-whoosh.mp3', 0.26], paper: ['sfx/paper-slide.mp3', 0.3], riser_soft: ['sfx/swoosh-slow.mp3', 0.2],
  shutter: ['sfx2/shutter.wav', 0.4], tick: ['sfx2/tick.wav', 0.35], rumble: ['sfx2/rumble.wav', 0.4], hiss: ['sfx2/hiss.wav', 0.18],
  drone: ['sfx2/drone.wav', 0.3], typewriter: ['sfx2/typewriter.wav', 0.3], pin: ['sfx2/tick.wav', 0.35],
};
const W_ = WORDS as any;
const VOICE: [number, number][] = W_.lines.map((l: any) => [l.start, l.end]);
const QUIET: [number, number][] = (W_.inserts ?? []).map((x: any) => [x.start, x.end]);
const LEVEL = [0, 0.09, 0.13, 0.17, 0.22];
const cues = ((SL as any).music_cues as { at_shot: string; level: number }[]).map((c) => ({ t: SHOTS.find((s) => s.id === c.at_shot)!.params.start_s, level: c.level }));
const musicVol = (frame: number) => {
  const t = frame / FPS; let lvl = LEVEL[1];
  for (let i = 0; i < cues.length; i++) { if (t >= cues[i].t) { const prev = i ? LEVEL[cues[i - 1].level] : 0; lvl = prev + (LEVEL[cues[i].level] - prev) * Math.min(1, (t - cues[i].t) / 1.5); } }
  const speaking = VOICE.some(([a, b]) => t > a - 0.15 && t < b + 0.1);
  const near = VOICE.reduce((m, [a, b]) => Math.min(m, t < a ? a - t : t > b ? t - b : 0), 99);
  const duck = speaking ? 0.5 : 0.5 + 0.5 * Math.min(1, near / 0.4);
  const archive = QUIET.some(([a, b]) => t > a - 0.3 && t < b + 0.3) ? 0.35 : 1;
  const tail = interpolate(t, [END_S - 2.5, END_S + 0.4], [1, 0], C);
  return lvl * duck * archive * tail * (t > END_S - 3.3 ? 1.5 : 1);
};

export const Episode: React.FC = () => {
  const land = useLand('countries-50m.json');
  if (!land) return null;
  return <Finish>
    {SHOTS.map((s, i) => { const from = Math.round(s.params.start_s * FPS); const next = SHOTS[i + 1]; const tail = next && next.transition_in === 'dissolve' ? 16 : 1;
      return <Sequence key={s.id} from={from} durationInFrames={durF(s) + tail} name={`${s.id} ${s.scene_type}`}>
        <TransitionIn kind={s.transition_in}><Scene s={s} land={land} /><Chrome s={s} /></TransitionIn>
      </Sequence>; })}
    <Audio src={staticFile('ep/voice.wav')} volume={1} />
    <Audio src={staticFile('ep/bed.wav')} volume={1} />
    {/* archival records listed in words.json "sounds" play from their own files (the voice stem stays narration only) */}
    {((W_.sounds ?? []) as any[]).map((x, i) => { const fr = Math.round(x.start * FPS); const n = Math.round(x.seconds * FPS);
      return <Sequence key={'rec' + i} from={fr} durationInFrames={n}><Audio src={med(x.media_id)} startFrom={Math.round(x.from_s * FPS)} volume={(q) => (x.gain ?? 1) * interpolate(q, [0, 6, n - 10, n], [0, 1, 1, 0], C)} /></Sequence>; })}
    {SHOTS.flatMap((s) => (s.sfx ?? []).map((k, j) => { const m = SFX[k]; if (!m) return null; const from = Math.max(0, Math.round(s.params.start_s * FPS) - (k.startsWith('whoosh') || k === 'riser_soft' ? 8 : 0) + j * 12);
      return <Sequence key={s.id + k + j} from={from} durationInFrames={150}><Audio src={staticFile(m[0])} volume={m[1]} /></Sequence>; }))}
    <Grain opacity={0.05} />
  </Finish>;
};
