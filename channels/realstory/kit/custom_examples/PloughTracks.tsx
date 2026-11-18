// Ghost octopus — DISCOL 1989 from above: a circle of seafloor ~11 km², 78 plough tracks 8 m wide
// draw one after another while a counter runs, then the year counter jumps 1989 → 2015.
import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { SceneBg } from '../kit/Brand';
import { ACCENT_EP, BONE, C, DISP, FONT, MUTED, SHADOW, TINT, io, out, rgba, rng } from '../kit/tokens';
import { Mono, Odometer } from '../kit/Type';

const CX = 640, CY = 560, R = 360;
const TR = (() => { const r = rng(19); return Array.from({ length: 78 }, () => { const a = r() * Math.PI; const off = (r() - 0.5) * R * 1.2; return { a, off }; }); })();
export const PloughTracks: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const mode: string = s.params?.mode ?? 'plough'; // plough | years
  const n = mode === 'plough' ? interpolate(f, [8, Math.max(30, d - 20)], [0, 78], C) : 78;
  const fade = mode === 'years' ? interpolate(f, [20, 60], [1, 0.55], C) : 1;
  return <SceneBg>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <defs><clipPath id="disc"><circle cx={CX} cy={CY} r={R} /></clipPath></defs>
      <circle cx={CX} cy={CY} r={R} fill={rgba(TINT, 0.12)} stroke={rgba(TINT, 0.6)} strokeWidth={2} />
      <g clipPath="url(#disc)">{TR.map((t, i) => { const p = Math.max(0, Math.min(1, n - i)); if (p <= 0) return null; const dx = Math.cos(t.a), dy = Math.sin(t.a); const nx = -dy, ny = dx;
        const x0 = CX + nx * t.off - dx * R, y0 = CY + ny * t.off - dy * R; return <line key={i} x1={x0} y1={y0} x2={x0 + dx * 2 * R * p} y2={y0 + dy * 2 * R * p} stroke={rgba(ACCENT_EP, 0.55 * fade)} strokeWidth={5} />; })}</g>
    </svg>
    <Mono text="DISCOL · PERU BASIN · ~4,150 M · DIAGRAM" f0={4} size={22} style={{ position: 'absolute', left: CX - R, top: CY + R + 30 }} />
    <div style={{ position: 'absolute', left: 1160, top: 290 }}>
      {mode === 'plough' ? <>
        <Mono text="PLOUGH-HARROW, 8 M WIDE · TOWS" f0={4} size={26} />
        <div style={{ ...DISP(300, 62, 880), color: BONE, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>{Math.floor(n)}</div>
        <Mono text="AREA ≈ 11 KM²" f0={20} size={28} color={ACCENT_EP} />
      </> : <>
        <Mono text="SURVEYED AGAIN" f0={4} size={26} />
        <div style={{ ...DISP(260, 62, 880), color: BONE, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>{Math.round(interpolate(f, [10, 40], [1989, 2015], { ...C, easing: out }))}</div>
        <div style={{ ...DISP(110), color: ACCENT_EP, textShadow: SHADOW, opacity: interpolate(f, [42, 52], [0, 1], C) }}>TRACKS STILL THERE</div>
      </>}
    </div>
  </SceneBg>;
};
