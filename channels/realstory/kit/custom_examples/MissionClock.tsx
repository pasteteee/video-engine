// Gemini 8 — 101 minutes between the two launches, told by a clock face.
// The hour hand sweeps 10:00 → 11:41, the swept wedge fills with the episode accent,
// the minute hand runs one full turn and 41 minutes more, the count lands on 101.
import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { SceneBg } from '../kit/Brand';
import { ACCENT_EP, BONE, C, DISP, FONT, MUTED, SHADOW, SIGNAL, TINT, io, out, rgba } from '../kit/tokens';
import { Mono, Odometer } from '../kit/Type';

const CX = 760, CY = 560, R = 320;
const pt = (deg: number, r: number) => [CX + r * Math.sin((deg * Math.PI) / 180), CY - r * Math.cos((deg * Math.PI) / 180)];
const wedge = (a0: number, a1: number, r: number) => { const [x0, y0] = pt(a0, r), [x1, y1] = pt(a1, r); return `M${CX} ${CY} L${x0} ${y0} A${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1} ${y1} Z`; };

export const MissionClock: React.FC<{ s: any; d: number }> = ({ d }) => {
  const f = useCurrentFrame();
  const intro = interpolate(f, [0, 14], [0, 1], { ...C, easing: out });
  const p = interpolate(f, [12, Math.min(d - 18, 76)], [0, 1], { ...C, easing: io });
  const mins = 101 * p; const t = 600 + mins; // minutes after midnight
  const hourDeg = (t / 60) * 30 % 360, minDeg = (t % 60) * 6;
  const h0 = 300; // 10:00 on the dial
  const hh = Math.floor(t / 60), mm = Math.floor(t % 60);
  const end = f > Math.min(d - 18, 76);
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <svg width={1920} height={1080} style={{ position: 'absolute', opacity: intro, transform: `scale(${0.94 + 0.06 * intro})`, transformOrigin: `${CX}px ${CY}px` }}>
      <circle cx={CX} cy={CY} r={R} fill="none" stroke={rgba(TINT, 0.35)} strokeWidth={2} />
      {Array.from({ length: 60 }, (_, i) => { const big = i % 5 === 0; const [x0, y0] = pt(i * 6, R - (big ? 34 : 16)), [x1, y1] = pt(i * 6, R - 4);
        return <line key={i} x1={x0} y1={y0} x2={x1} y2={y1} stroke={big ? BONE : rgba(TINT, 0.6)} strokeWidth={big ? 4 : 2} />; })}
      {Array.from({ length: 12 }, (_, i) => { const [x, y] = pt(i * 30, R - 76); return <text key={i} x={x} y={y + 11} textAnchor="middle" fontFamily={FONT.mono} fontSize={28} fill={i === 10 || i === 11 ? BONE : rgba(TINT, 0.7)}>{i === 0 ? 12 : i}</text>; })}
      <path d={wedge(h0, h0 + Math.max(0.01, hourDeg - h0), R - 110)} fill={rgba(ACCENT_EP, 0.28)} stroke={ACCENT_EP} strokeWidth={3} />
      {/* launch ticks */}
      {[[h0, 'ATLAS-AGENA  10:00', 1], [h0 + 50.5, 'TITAN II  11:41', end ? 1 : 0]].map(([a, label, on], k) => { const [x0, y0] = pt(a as number, R + 10), [x1, y1] = pt(a as number, R + 46);
        return <g key={k} opacity={on as number}><line x1={x0} y1={y0} x2={x1} y2={y1} stroke={k ? SIGNAL : ACCENT_EP} strokeWidth={6} />
          <text x={x1 + (k ? 18 : -14)} y={y1 - 10} textAnchor={k ? 'start' : 'end'} fontFamily={FONT.mono} fontWeight={500} fontSize={24} letterSpacing={3} fill={BONE} style={{ textShadow: SHADOW }}>{label as string}</text></g>; })}
      {/* hands */}
      {(() => { const [x, y] = pt(minDeg, R - 40); return <line x1={CX} y1={CY} x2={x} y2={y} stroke={BONE} strokeWidth={6} strokeLinecap="square" />; })()}
      {(() => { const [x, y] = pt(hourDeg, R - 130); return <line x1={CX} y1={CY} x2={x} y2={y} stroke={ACCENT_EP} strokeWidth={14} strokeLinecap="square" />; })()}
      <circle cx={CX} cy={CY} r={12} fill={BONE} />
    </svg>
    <Mono text="BETWEEN THE TWO LAUNCHES" f0={6} size={28} style={{ position: 'absolute', left: 1200, top: 320 }} />
    <div style={{ position: 'absolute', left: 1192, top: 370, display: 'flex', alignItems: 'flex-end', gap: 30 }}>
      <Odometer value={101} size={290} f0={12} dur={Math.min(d - 30, 62)} />
      <div style={{ ...DISP(110), color: ACCENT_EP, marginBottom: 4, opacity: intro }}>MIN</div>
    </div>
    <div style={{ position: 'absolute', left: 1200, top: 650, fontFamily: FONT.mono, fontSize: 40, letterSpacing: '0.1em', color: BONE, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW }}>
      {String(hh).padStart(2, '0')}:{String(mm).padStart(2, '0')} <span style={{ color: MUTED, fontSize: 24 }}>EST · MARCH 16, 1966</span></div>
  </SceneBg>;
};
