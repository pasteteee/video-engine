// Gemini 8 — the approach, frame by frame, from the real window photos.
// Each photo cuts in on a shutter flash; a reticle tightens on the Agena and the range counts down.
import React from 'react';
import { AbsoluteFill, Img, interpolate, useCurrentFrame } from 'remotion';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, MUTED, SHADOW, SIGNAL, io, out, rgba } from '../kit/tokens';
import { Mono } from '../kit/Type';

// Agena position in each photo (image fractions), zoom and grade.
const FR: Record<string, { at: [number, number]; z: number; filter?: string }> = {
  m_a1000: { at: [0.608, 0.743], z: 2.6, filter: 'brightness(2.2) contrast(1.15) saturate(0.3)' },
  m_a260: { at: [0.338, 0.5], z: 1.55 },
  m_a210: { at: [0.324, 0.6], z: 1.5 },
};

export const DockingHud: React.FC<{ s: any; d: number; med: (id: string) => string; media: Record<string, { w: number; h: number }> }> = ({ s, d, med, media }) => {
  const f = useCurrentFrame(); const ids: string[] = s.media_ids; const ranges: number[] = s.params.ranges;
  const seg = d / ids.length; const k = Math.min(ids.length - 1, Math.floor(f / seg)); const lf = f - k * seg;
  const id = ids[k]; const m = media[id]; const fr = FR[id];
  // camera: cover the frame, centre on the Agena (clamped), slow push
  const sc = Math.max(1920 / m.w, 1080 / m.h); const W = m.w * sc, H = m.h * sc;
  const z = fr.z * (1 + 0.06 * interpolate(lf, [0, seg], [0, 1], C));
  const cx = Math.min(Math.max(fr.at[0] * W, 960 / z), W - 960 / z), cy = Math.min(Math.max(fr.at[1] * H, 540 / z), H - 540 / z);
  const ax = 960 + (fr.at[0] * W - cx) * z, ay = 540 + (fr.at[1] * H - cy) * z;
  // reticle
  const lock = interpolate(lf, [4, 22], [0, 1], { ...C, easing: out });
  const rs = 220 - 90 * lock; const gap = 26;
  const flash = interpolate(lf, [0, 4], [0.9, 0], C);
  // range readout counts from the previous range to this one
  const prev = k ? ranges[k - 1] : 1400; const rv = Math.round(interpolate(lf, [2, 20], [prev, ranges[k]], { ...C, easing: io }));
  const tick = (x: number, y: number, dx: number, dy: number) => `M${x + dx * 40} ${y} L${x} ${y} L${x} ${y + dy * 40}`;
  return <AbsoluteFill style={{ backgroundColor: '#000' }}>
    <Img src={med(id)} style={{ position: 'absolute', left: 0, top: 0, width: W, height: H, transformOrigin: '0 0', transform: `translate(960px,540px) scale(${z}) translate(${-cx}px,${-cy}px)`, filter: fr.filter }} />
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 45%, ${rgba(GROUND, 0.75)} 100%)` }} />
    <svg width={1920} height={1080} style={{ position: 'absolute', filter: 'drop-shadow(0 0 6px rgba(0,0,0,0.7))' }}>
      {/* crosshair through the target, broken at the centre */}
      <line x1={ax - rs - 160} y1={ay} x2={ax - gap} y2={ay} stroke={rgba(BONE, 0.55 * lock)} strokeWidth={2} />
      <line x1={ax + gap} y1={ay} x2={ax + rs + 160} y2={ay} stroke={rgba(BONE, 0.55 * lock)} strokeWidth={2} />
      <line x1={ax} y1={ay - rs - 120} x2={ax} y2={ay - gap} stroke={rgba(BONE, 0.55 * lock)} strokeWidth={2} />
      <line x1={ax} y1={ay + gap} x2={ax} y2={ay + rs + 120} stroke={rgba(BONE, 0.55 * lock)} strokeWidth={2} />
      <path d={[tick(ax - rs, ay - rs, 1, 1), tick(ax + rs, ay - rs, -1, 1), tick(ax - rs, ay + rs, 1, -1), tick(ax + rs, ay + rs, -1, -1)].join(' ')} fill="none" stroke={lock > 0.98 ? ACCENT_EP : BONE} strokeWidth={4} opacity={0.4 + 0.6 * lock} />
      {/* range marks on the right edge: where we are on the way in */}
      {[1000, 500, 260, 210, 0].map((r, i) => { const y = 260 + (1 - r / 1000) * 560; return <g key={i}><line x1={1830} y1={y} x2={1860} y2={y} stroke={rgba(BONE, 0.5)} strokeWidth={2} />
        <text x={1820} y={y + 8} textAnchor="end" fontFamily={FONT.mono} fontSize={18} letterSpacing={2} fill={MUTED}>{r}</text></g>; })}
      <rect x={1866} y={260 + (1 - rv / 1000) * 560 - 6} width={22} height={12} fill={SIGNAL} />
    </svg>
    <Mono text="GEMINI 8 · WINDOW CAMERA" f0={2} size={22} color={MUTED} style={{ position: 'absolute', left: 60, top: 104 }} />
    <div style={{ position: 'absolute', left: 60, top: 144, fontFamily: FONT.mono, fontSize: 22, letterSpacing: '0.12em', color: BONE, textShadow: SHADOW }}>FRAME {k + 1} / {ids.length}</div>
    <div style={{ position: 'absolute', right: 260, bottom: 150, textAlign: 'right' }}>
      <div style={{ fontFamily: FONT.mono, fontSize: 24, letterSpacing: '0.14em', color: MUTED, textShadow: SHADOW }}>RANGE TO AGENA</div>
      <div style={{ ...DISP(220, 62, 860), color: BONE, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW, marginTop: 8 }}>~{rv.toLocaleString('en-US')}<span style={{ ...DISP(110), color: ACCENT_EP, marginLeft: 18 }}>FT</span></div>
    </div>
    <AbsoluteFill style={{ backgroundColor: '#fff', opacity: k ? flash : 0 }} />
  </AbsoluteFill>;
};
