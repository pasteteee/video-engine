// Terrain-relative navigation, shown on the real pieces: the live down-look camera frame searches the
// onboard hazard map, locks on, and the position is found.
import React from 'react';
import { AbsoluteFill, Img, OffthreadVideo, interpolate, useCurrentFrame } from 'remotion';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, MUTED, SHADOW, io, out, rgba } from '../kit/tokens';
import { Mono, StopBlock } from '../kit/Type';
export const TRNMatch: React.FC<{ s: any; d: number; med: (id: string) => string }> = ({ s, d, med }) => {
  const f = useCurrentFrame(); const P = s.params;
  const path: number[][] = [[1320, 300], [880, 640], [1500, 720], [1130, 460]]; const lockAt = Math.round(d * 0.62);
  const p = interpolate(f, [10, lockAt], [0, path.length - 1], { ...C, easing: io }); const i = Math.min(path.length - 2, Math.floor(p)); const t = p - i;
  const bx = path[i][0] + (path[i + 1][0] - path[i][0]) * t, by = path[i][1] + (path[i + 1][1] - path[i][1]) * t; const locked = f >= lockAt;
  const lk = interpolate(f, [lockAt, lockAt + 10], [0, 1], { ...C, easing: out }); const sz = 240 - 40 * lk;
  return <AbsoluteFill style={{ background: GROUND }}>
    <Img src={med(s.media_ids[0])} style={{ position: 'absolute', left: 640, top: 0, width: 1280, height: 1080, objectFit: 'cover', filter: 'grayscale(0.85) brightness(0.75) contrast(1.1)' }} />
    <AbsoluteFill style={{ background: `linear-gradient(90deg, ${GROUND} 33%, ${rgba(GROUND, 0)} 52%)` }} />
    <div style={{ position: 'absolute', left: 90, top: 210, width: 480, height: 480, overflow: 'hidden' }}><OffthreadVideo src={med(s.media_ids[1])} startFrom={Math.round((P.trim ?? 40) * 30)} muted style={{ width: '100%', height: '100%', objectFit: 'cover' }} /></div>
    <Mono text="LIVE · DOWN-LOOK CAMERA" f0={4} size={20} color={ACCENT_EP} style={{ position: 'absolute', left: 92, top: 170 }} />
    <Mono text="ONBOARD MAP" f0={10} size={20} color={ACCENT_EP} style={{ position: 'absolute', right: 120, top: 60 }} />
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <path d={`M570 450 L${bx - sz / 2} ${by}`} stroke={rgba(BONE, 0.35)} strokeWidth={2} strokeDasharray="8 10" />
      <rect x={bx - sz / 2} y={by - sz / 2} width={sz} height={sz} fill={rgba(ACCENT_EP, locked ? 0.18 : 0.06)} stroke={locked ? BONE : ACCENT_EP} strokeWidth={locked ? 5 : 3} strokeDasharray={locked ? undefined : '14 10'} />
      {locked ? <><line x1={bx - 40} y1={by} x2={bx + 40} y2={by} stroke={BONE} strokeWidth={3} /><line x1={bx} y1={by - 40} x2={bx} y2={by + 40} stroke={BONE} strokeWidth={3} /></> : null}
    </svg>
    <div style={{ position: 'absolute', left: 90, top: 760, opacity: lk, transform: `translateY(${(1 - lk) * 20}px)` }}>
      <div style={{ ...DISP(110, 70, 820), color: BONE, textShadow: SHADOW, whiteSpace: 'nowrap' }}>POSITION FOUND<StopBlock size={110} /></div>
      <div style={{ fontFamily: FONT.mono, fontSize: 22, letterSpacing: 3, color: MUTED, marginTop: 18 }}>SCHEMATIC OF THE MATCH · REAL CAMERA, REAL MAP</div></div>
  </AbsoluteFill>;
};
