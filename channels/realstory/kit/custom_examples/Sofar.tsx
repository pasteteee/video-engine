// Bloop — the SOFAR channel as a cutaway: depth axis, the sound-speed curve with its minimum near 1 km,
// and rays from a source bending back toward the axis while they run to the right.
import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { SceneBg } from '../kit/Brand';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND2, MUTED, SHADOW, TINT, io, out, rgba } from '../kit/tokens';
import { Mono } from '../kit/Type';

const TOP = 240, BOT = 960, AX = 520; // sea surface, floor, channel axis (px)
export const Sofar: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params; const phase = P.phase ?? 'trap';
  const intro = interpolate(f, [0, 16], [0, 1], { ...C, easing: out });
  const curve = interpolate(f, [8, 40], [0, 1], { ...C, easing: io });
  const rays = phase === 'rays' ? interpolate(f, [4, d - 10], [0, 1], { ...C, easing: io }) : interpolate(f, [40, d], [0, 0.35], C);
  // sound speed profile x(depth): fast near surface (warm), slow at axis, fast deep (pressure)
  const prof = Array.from({ length: 60 }, (_, i) => { const y = TOP + (BOT - TOP) * i / 59; const dz = (y - AX) / (y < AX ? AX - TOP : BOT - AX); return [180 + 150 * dz * dz, y]; });
  const ray = (amp: number, per: number, ph: number) => Array.from({ length: 120 }, (_, i) => { const x = 380 + 1440 * i / 119; return [x, AX + amp * Math.sin((x - 380) / per + ph)]; });
  const R = [[110, 120, 0], [190, 150, 0.4], [260, 170, -0.3]];
  const n = Math.max(2, Math.round(120 * rays));
  return <SceneBg drift={0.2}>
    <svg width={1920} height={1080} style={{ position: 'absolute', opacity: intro }}>
      <defs><linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={rgba(ACCENT_EP, 0.18)} /><stop offset="0.4" stopColor={rgba(GROUND2, 0.2)} /><stop offset="1" stopColor={rgba('#000000', 0.4)} /></linearGradient></defs>
      <rect x={340} y={TOP} width={1500} height={BOT - TOP} fill="url(#sea)" />
      <line x1={340} y1={TOP} x2={1840} y2={TOP} stroke={BONE} strokeWidth={3} />
      <line x1={340} y1={BOT} x2={1840} y2={BOT} stroke={rgba(TINT, 0.6)} strokeWidth={3} />
      <line x1={340} y1={AX} x2={1840} y2={AX} stroke={ACCENT_EP} strokeWidth={2} strokeDasharray="10 10" opacity={curve} />
      <path d={'M' + prof.slice(0, Math.max(2, Math.round(60 * curve))).map((p) => p.join(' ')).join(' L')} fill="none" stroke={BONE} strokeWidth={4} />
      {R.map(([a, p, ph], i) => <path key={i} d={'M' + ray(a, p, ph).slice(0, n).map((q) => q.join(' ')).join(' L')} fill="none" stroke={ACCENT_EP} strokeWidth={4 - i} opacity={0.9 - i * 0.2} />)}
      <circle cx={380} cy={AX} r={14} fill={ACCENT_EP} />
      {[0, 1, 2].map((k) => { const q = ((f / 24 + k / 3) % 1); return <circle key={k} cx={380} cy={AX} r={14 + q * 60} fill="none" stroke={rgba(ACCENT_EP, 1 - q)} strokeWidth={2} />; })}
      <text x={320} y={TOP + 8} textAnchor="end" fontFamily={FONT.mono} fontSize={22} fill={MUTED}>0 KM</text>
      <text x={320} y={AX + 8} textAnchor="end" fontFamily={FONT.mono} fontSize={22} fill={ACCENT_EP}>~1 KM</text>
      <text x={320} y={BOT + 8} textAnchor="end" fontFamily={FONT.mono} fontSize={22} fill={MUTED}>DEEP</text>
    </svg>
    <Mono text="WARMER WATER: SOUND FASTER" f0={24} size={22} color={BONE} style={{ position: 'absolute', left: 560, top: TOP + 30 }} />
    <Mono text="HIGHER PRESSURE: SOUND FASTER" f0={34} size={22} color={BONE} style={{ position: 'absolute', left: 560, top: BOT - 60 }} />
    <div style={{ position: 'absolute', left: 90, top: 100, ...DISP(84), color: BONE, textShadow: SHADOW, opacity: interpolate(f, [6, 20], [0, 1], C) }}>{P.label}</div>
    <Mono text="DIAGRAM · NOT TO SCALE" f0={10} size={20} color={MUTED} style={{ position: 'absolute', right: 90, top: 128 }} />
  </SceneBg>;
};
