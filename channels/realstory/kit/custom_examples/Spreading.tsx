// Bloop — balloon vs ripple: open-water (spherical) spreading against channel (flat, cylindrical) spreading.
import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { SceneBg } from '../kit/Brand';
import { ACCENT_EP, BONE, C, DISP, MUTED, SHADOW, TINT, io, rgba } from '../kit/tokens';
import { Mono } from '../kit/Type';

export const Spreading: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params; const t = (f % 60) / 60;
  const b = interpolate(f, [P.second_at * 30, P.second_at * 30 + 14], [0, 1], C);
  return <SceneBg drift={0.2}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {[0, 1, 2, 3].map((k) => { const q = (t + k / 4) % 1; return <g key={k}>
        <circle cx={520} cy={560} r={30 + q * 300} fill="none" stroke={rgba(BONE, 0.85 * (1 - q) * (1 - q))} strokeWidth={3} />
        <ellipse cx={520} cy={560} rx={30 + q * 300} ry={(30 + q * 300) * 0.3} fill="none" stroke={rgba(BONE, 0.35 * (1 - q) * (1 - q))} strokeWidth={2} />
        <ellipse cx={1400} cy={600} rx={30 + q * 380} ry={(30 + q * 380) * 0.22} fill="none" stroke={rgba(ACCENT_EP, 0.95 * (1 - q * 0.6) * b)} strokeWidth={4} />
      </g>; })}
      <circle cx={520} cy={560} r={10} fill={BONE} /><circle cx={1400} cy={600} r={10} fill={ACCENT_EP} opacity={b} />
      <line x1={1000} y1={560 - 130} x2={1800} y2={560 - 130} stroke={rgba(TINT, 0.4 * b)} strokeWidth={2} strokeDasharray="8 8" />
      <line x1={1000} y1={600 + 130} x2={1800} y2={600 + 130} stroke={rgba(TINT, 0.4 * b)} strokeWidth={2} strokeDasharray="8 8" />
    </svg>
    <div style={{ position: 'absolute', left: 300, top: 900, ...DISP(70), color: BONE, textShadow: SHADOW }}>OPEN WATER</div>
    <Mono text="SPREADS IN EVERY DIRECTION" f0={6} size={22} color={MUTED} style={{ position: 'absolute', left: 304, top: 985 }} />
    <div style={{ position: 'absolute', left: 1180, top: 900, ...DISP(70), color: ACCENT_EP, textShadow: SHADOW, opacity: b }}>IN THE CHANNEL</div>
    <Mono text="SPREADS FLAT, FADES SLOWER" f0={P.second_at * 30 + 6} size={22} color={MUTED} style={{ position: 'absolute', left: 1184, top: 985 }} />
  </SceneBg>;
};
