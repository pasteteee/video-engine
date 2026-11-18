// Ghost octopus — the dive told as a depth column: 0 → 4,290 m, Titanic mark at 3,800 m,
// light fades out with depth, pressure readout counts up at the bottom.
import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { SceneBg } from '../kit/Brand';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, MUTED, SHADOW, SIGNAL, TINT, io, out, rgba } from '../kit/tokens';
import { Mono, Odometer } from '../kit/Type';

const X = 640, TOP = 120, BOT = 960, MAX = 4500;
const y = (m: number) => TOP + (BOT - TOP) * (m / MAX);

export const DepthColumn: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params ?? {};
  const mode: string = P.mode ?? 'dive'; // dive | pressure
  const p = mode === 'dive' ? interpolate(f, [6, Math.max(20, d - 30)], [0, 1], { ...C, easing: io }) : 1;
  const depth = 4290 * p; const yy = y(depth);
  const light = interpolate(depth, [0, 200, 1000], [1, 0.35, 0], C);
  const tit = interpolate(f, [mode === 'dive' ? d * 0.55 : 6, mode === 'dive' ? d * 0.55 + 14 : 20], [0, 1], { ...C, easing: out });
  const pr = interpolate(f, [8, 24], [0, 1], { ...C, easing: out });
  return <SceneBg style={{ background: `linear-gradient(180deg, ${rgba(ACCENT_EP, 0.25 * light + 0.04)} 0%, ${GROUND} 70%)` }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <line x1={X} y1={TOP} x2={X} y2={BOT} stroke={rgba(TINT, 0.35)} strokeWidth={2} />
      {Array.from({ length: 10 }, (_, i) => i * 500).map((m) => <g key={m}>
        <line x1={X - 18} y1={y(m)} x2={X} y2={y(m)} stroke={rgba(TINT, 0.6)} strokeWidth={2} />
        <text x={X - 34} y={y(m) + 9} textAnchor="end" fontFamily={FONT.mono} fontSize={24} fill={rgba(TINT, 0.8)}>{m.toLocaleString('en-US')} M</text></g>)}
      <line x1={X} y1={TOP} x2={X} y2={yy} stroke={ACCENT_EP} strokeWidth={6} />
      <circle cx={X} cy={yy} r={14} fill={BONE} />
      <circle cx={X} cy={yy} r={30 + 8 * Math.sin(f / 5)} fill="none" stroke={rgba(BONE, 0.4)} strokeWidth={2} />
      <g opacity={tit}><line x1={X} y1={y(3800)} x2={X + 520} y2={y(3800)} stroke={rgba(BONE, 0.55)} strokeWidth={2} strokeDasharray="10 8" />
        <text x={X + 540} y={y(3800) + 9} fontFamily={FONT.mono} fontSize={26} letterSpacing={3} fill={MUTED}>TITANIC WRECK · ~3,800 M</text></g>
      {p > 0.98 ? <g><line x1={X} y1={y(4290)} x2={X + 520} y2={y(4290)} stroke={ACCENT_EP} strokeWidth={3} />
        <text x={X + 540} y={y(4290) + 9} fontFamily={FONT.mono} fontSize={26} letterSpacing={3} fill={ACCENT_EP}>CASPER · 4,290 M</text></g> : null}
    </svg>
    <div style={{ position: 'absolute', left: X + 120, top: 200 }}>
      {mode === 'dive'
        ? <><Mono text="DEPTH" f0={4} size={28} />
            <div style={{ ...DISP(260, 62, 880), color: BONE, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>{Math.round(depth).toLocaleString('en-US')}<span style={{ color: ACCENT_EP, fontSize: 120 }}> M</span></div>
            <Mono text={light > 0.02 ? 'SUNLIGHT FADING' : 'NO SUNLIGHT'} f0={10} size={26} color={light > 0.02 ? MUTED : ACCENT_EP} style={{ marginTop: 20 }} /></>
        : <div style={{ opacity: pr, transform: `translateY(${(1 - pr) * 20}px)` }}>
            <Mono text="PRESSURE AT 4,290 M · OUR CALCULATION" f0={4} size={26} />
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 26, marginTop: 10 }}><Odometer value={440} size={300} f0={8} />
              <div style={{ ...DISP(110), color: ACCENT_EP, marginBottom: 10, textShadow: SHADOW }}>KG / CM²</div></div>
            <Mono text="ρ·g·h = 1027 × 9.81 × 4290 ≈ 43 MPa" f0={40} size={26} color={BONE} style={{ marginTop: 26 }} />
          </div>}
    </div>
  </SceneBg>;
};
