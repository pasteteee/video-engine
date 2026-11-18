// Ghost octopus — the episode's calculation: a nodule cross-section grows ring by ring,
// then age = radius / rate lands, odometer to 2.5 million years, and a bar compares it with our species.
import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { SceneBg } from '../kit/Brand';
import { ACCENT_EP, BONE, C, DISP, FONT, MUTED, SHADOW, SIGNAL, TINT, io, out, rgba, rng } from '../kit/tokens';
import { Mono, Odometer, Hairline } from '../kit/Type';

const CX = 560, CY = 560;
const RINGS = (() => { const r = rng(5); return Array.from({ length: 26 }, (_, i) => ({ r: 40 + i * 11 + r() * 4, w: 1.5 + r() * 3, a: 0.25 + r() * 0.5, j: r() * 6 })); })();
const blob = (R: number, j: number) => { const n = 48; let d = ''; for (let i = 0; i <= n; i++) { const a = (i / n) * Math.PI * 2; const rr = R * (1 + 0.06 * Math.sin(a * 3 + j) + 0.03 * Math.sin(a * 7 + j * 2)); d += (i ? 'L' : 'M') + (CX + rr * Math.cos(a)).toFixed(1) + ' ' + (CY + rr * Math.sin(a) * 0.92).toFixed(1); } return d + 'Z'; };

export const NoduleRings: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params ?? {}; const mode: string = P.mode ?? 'formula'; // formula | compare
  const grow = interpolate(f, [4, Math.min(70, d * 0.5)], [0, RINGS.length], C);
  const rad = interpolate(f, [30, 50], [0, 1], { ...C, easing: io });
  const Rmax = RINGS[RINGS.length - 1].r;
  return <SceneBg>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <path d={blob(Rmax + 14, 1)} fill={rgba(TINT, 0.12)} stroke={rgba(TINT, 0.5)} strokeWidth={3} opacity={Math.min(1, grow / 4)} />
      {RINGS.map((g, i) => i < grow ? <path key={i} d={blob(g.r, g.j)} fill="none" stroke={i === Math.floor(grow) - 1 ? ACCENT_EP : rgba(BONE, g.a)} strokeWidth={g.w} /> : null)}
      <circle cx={CX} cy={CY} r={22} fill={rgba(BONE, 0.6)} />
      <line x1={CX} y1={CY} x2={CX + (Rmax + 14) * rad} y2={CY} stroke={ACCENT_EP} strokeWidth={5} />
      {rad > 0.95 ? <text x={CX + Rmax / 2} y={CY - 22} textAnchor="middle" fontFamily={FONT.mono} fontSize={28} letterSpacing={3} fill={ACCENT_EP} style={{ textShadow: SHADOW }}>r = 25 MM</text> : null}
    </svg>
    <Mono text="SCHEMATIC · NOT TO SCALE" f0={10} size={18} style={{ position: 'absolute', left: 300, top: 930 }} />
    <div style={{ position: 'absolute', left: 1040, top: 230, width: 800 }}>
      {mode === 'formula' ? <>
        <Mono text="AGE = RADIUS ÷ GROWTH RATE" f0={8} size={34} color={BONE} />
        <Mono text="25 MM ÷ 10 MM PER MILLION YEARS" f0={30} size={28} color={MUTED} style={{ marginTop: 26 }} />
        <Hairline x={0} y={170} w={760} f0={46} />
        <div style={{ position: 'absolute', top: 200, display: 'flex', alignItems: 'flex-end', gap: 22 }}>
          <span style={{ ...DISP(230, 62, 880), color: BONE, textShadow: SHADOW, opacity: interpolate(f, [56, 66], [0, 1], C) }}>2.5</span>
          <span style={{ ...DISP(90), color: ACCENT_EP, marginBottom: 14, opacity: interpolate(f, [62, 72], [0, 1], C) }}>MILLION YEARS</span></div>
        <Mono text="AT THE FASTEST RATE. SLOWER = OLDER." f0={78} size={24} color={MUTED} style={{ position: 'absolute', top: 440 }} />
      </> : (() => { const b = interpolate(f, [10, 40], [0, 1], { ...C, easing: io }); const W = 760;
        return <>
          <Mono text="NODULE · AT LEAST" f0={4} size={26} />
          <div style={{ height: 46, width: W * b, background: ACCENT_EP, marginTop: 14 }} />
          <div style={{ ...DISP(84), color: BONE, marginTop: 12, textShadow: SHADOW }}>2,500,000 YEARS</div>
          <Mono text="HOMO SAPIENS" f0={30} size={26} style={{ marginTop: 50 }} />
          <div style={{ height: 46, width: W * 0.12 * b, background: BONE, marginTop: 14 }} />
          <div style={{ ...DISP(84), color: BONE, marginTop: 12, textShadow: SHADOW, opacity: interpolate(f, [34, 44], [0, 1], C) }}>~300,000 YEARS</div>
          <div style={{ ...DISP(120), color: ACCENT_EP, marginTop: 40, opacity: interpolate(f, [56, 68], [0, 1], C), textShadow: SHADOW }}>8× OLDER</div>
        </>; })()}
    </div>
  </SceneBg>;
};
