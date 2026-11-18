// Godwit Shorts customs, laid out for 9:16.
import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { geoMercator, geoPath } from 'd3-geo';
import { ACCENT_EP, BONE, C, DISP, GROUND, GROUND2, MUTED, SHADOW, TINT, io, rgba, travel } from '../kit/tokens';
import { Mono } from '../kit/Type';
import { makeRoute, useLand } from '../kit/Geo';
const PTS: [number, number][] = [[160.2, -29], [157.8, -34], [156.4, -41.4], [148.35, -41.05]];
const R = makeRoute(PTS);
// The Tasman Sea turn, tall: track comes down from the top, bends west; wind arrows show the model wind.
export const VTurn: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const land = useLand('countries-50m.json'); const f = useCurrentFrame(); if (!land) return null; const mode = s.params.mode;
  const proj = geoMercator().center([153, -36]).scale(2300).translate([560, 860]); const path = geoPath(proj as any);
  const p = mode === 'turn' ? interpolate(f, [4, d - 6], [0, 1], { ...C, easing: travel }) : 1; const pos = proj(R.along(p) as any) as any;
  const wa = (mode === 'ne' ? interpolate(f, [6, d * 0.6], [90, 135], C) : 90) * Math.PI / 180;
  return <AbsoluteFill style={{ background: '#211810' }}>
    <svg width={1080} height={1920} style={{ position: 'absolute' }}>
      <path d={path(land) || ''} fill="#4b3b2b" stroke={rgba(TINT, 0.55)} strokeWidth={2} />
      {mode !== 'turn' ? Array.from({ length: 24 }, (_, i) => { const x = 140 + (i % 4) * 260, y = 420 + Math.floor(i / 4) * 200; const o = ((f * 2 + i * 23) % 60) - 30;
        return <line key={i} x1={x + Math.cos(wa) * (o - 30)} y1={y + Math.sin(wa) * (o - 30)} x2={x + Math.cos(wa) * (o + 30)} y2={y + Math.sin(wa) * (o + 30)} stroke={rgba(BONE, 0.7)} strokeWidth={4} strokeLinecap="round" />; }) : null}
      <path d={path(R.upTo(p)) || ''} fill="none" stroke={ACCENT_EP} strokeWidth={8} strokeLinecap="round" />
      <circle cx={pos[0]} cy={pos[1]} r={30} fill={rgba(ACCENT_EP, 0.25)} /><circle cx={pos[0]} cy={pos[1]} r={12} fill={BONE} />
    </svg>
    <div style={{ position: 'absolute', left: 80, top: 260, ...DISP(110, 62, 860), color: BONE, textShadow: SHADOW }}>{mode === 'turn' ? 'OCT 23: TURNS WEST' : mode === 'north' ? 'WIND FROM THE NORTH' : 'THEN NORTHEAST'}</div>
    <Mono text="ROUTE APPROXIMATE · NOAA GFS, OUR CHECK" f0={6} size={24} color={MUTED} style={{ position: 'absolute', left: 80, top: 390 }} />
  </AbsoluteFill>;
};
// Tailwind gauge, tall.
export const VTailwind: React.FC<{ s: any; d: number }> = ({ d }) => {
  const f = useCurrentFrame(); const g = interpolate(f, [6, d - 10], [0, 0.9], { ...C, easing: io });
  return <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 38%, ${GROUND2} 0%, ${GROUND} 75%)` }}>
    <Mono text="HOURS OF TAILWIND" f0={2} size={34} color={ACCENT_EP} style={{ position: 'absolute', left: 80, top: 500 }} />
    <div style={{ position: 'absolute', left: 70, top: 560, ...DISP(400, 62, 880), color: BONE, textShadow: SHADOW }}>{Math.round(g * 10)}<span style={{ color: MUTED, fontSize: 200 }}>/10</span></div>
    <div style={{ position: 'absolute', left: 80, top: 1000, width: 900, height: 20, background: rgba(TINT, 0.25) }}><div style={{ width: 900 * g, height: 20, background: ACCENT_EP }} /></div>
  </AbsoluteFill>;
};
