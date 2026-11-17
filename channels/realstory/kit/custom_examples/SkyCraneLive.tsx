// The last seconds in real time: three onboard cameras side by side, the mission-control call-outs
// as captions at their real times, and the altitude the team read out.
import React from 'react';
import { AbsoluteFill, OffthreadVideo, interpolate, useCurrentFrame } from 'remotion';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, MUTED, SHADOW, rgba } from '../kit/tokens';
import { Mono } from '../kit/Type';
export const SkyCraneLive: React.FC<{ s: any; d: number; med: (id: string) => string }> = ({ s, d, med }) => {
  const f = useCurrentFrame(); const P = s.params; const t = f / 30; const trim = P.trim ?? 0; // seconds into the crane clips
  const V = (id: string, st: React.CSSProperties) => <div style={{ position: 'absolute', overflow: 'hidden', background: '#000', ...st }}><OffthreadVideo src={med(id)} startFrom={Math.round(trim * 30)} muted style={{ width: '100%', height: '100%', objectFit: 'cover' }} /></div>;
  const cap = (P.captions as [number, number, string][]).find((c) => t >= c[0] && t < c[1]);
  return <AbsoluteFill style={{ background: GROUND }}>
    {V(s.media_ids[0], { left: 60, top: 110, width: 1180, height: 664 })}
    {V(s.media_ids[1], { left: 1270, top: 110, width: 590, height: 332 })}
    {V(s.media_ids[2], { left: 1270, top: 442, width: 590, height: 332 })}
    <Mono text="DESCENT STAGE LOOKING DOWN" f0={4} size={18} color={ACCENT_EP} style={{ position: 'absolute', left: 62, top: 76 }} />
    <Mono text="ROVER LOOKING UP · ROVER LOOKING DOWN" f0={10} size={18} color={ACCENT_EP} style={{ position: 'absolute', left: 1272, top: 76 }} />
    <Mono text="REAL TIME" f0={2} size={22} color={BONE} style={{ position: 'absolute', right: 62, top: 30 }} />
    {cap ? <div style={{ position: 'absolute', left: 62, top: 820, width: 1700, fontFamily: FONT.quote, fontStyle: 'italic', fontSize: 60, lineHeight: 1.1, color: BONE, textShadow: SHADOW, opacity: interpolate(t, [cap[0], cap[0] + 0.2], [0, 1], C) }}>“{cap[2]}”</div> : null}
    <Mono text="MISSION CONTROL, FEB 18, 2021" f0={20} size={18} color={MUTED} style={{ position: 'absolute', left: 64, top: 960 }} />
  </AbsoluteFill>;
};
