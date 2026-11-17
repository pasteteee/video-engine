// NASA's own hazard map of Jezero: the camera moves over it while the legend types on; the landing oval draws.
import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, MUTED, SHADOW, io, rgba } from '../kit/tokens';
import { Mono } from '../kit/Type';
import { ImageCam } from '../Episode';
export const HazardMap: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params; const leg: [string, string][] = P.legend ?? [['#e8463c', 'DANGER'], ['#3d7be0', 'SAFER']];
  return <AbsoluteFill style={{ background: GROUND }}>
    <ImageCam id={s.media_ids[0]} from={P.from} to={P.to} dur={d}>{(map) => { if (!P.oval) return null; const [x, y] = map(P.oval[0], P.oval[1]); const [x2] = map(P.oval[0] + P.oval[2], P.oval[1]); const r = x2 - x;
      const q = interpolate(f, [P.oval_at ?? 30, (P.oval_at ?? 30) + 26], [0, 1], { ...C, easing: io });
      return <svg width={1920} height={1080} style={{ position: 'absolute' }}><circle cx={x} cy={y} r={r} fill="none" stroke={BONE} strokeWidth={5} strokeDasharray={`${2 * Math.PI * r * q} 99999`} transform={`rotate(-90 ${x} ${y})`} />
        {P.dot ? (() => { const [dx, dy] = map(P.dot[0], P.dot[1]); const dq = interpolate(f, [P.dot_at ?? 40, (P.dot_at ?? 40) + 10], [0, 1], C); return <g opacity={dq}><circle cx={dx} cy={dy} r={14} fill={BONE} /><circle cx={dx} cy={dy} r={14 + 40 * ((f % 30) / 30)} fill="none" stroke={BONE} strokeWidth={3} opacity={1 - (f % 30) / 30} /></g>; })() : null}</svg>; }}</ImageCam>
    <AbsoluteFill style={{ background: `linear-gradient(90deg, ${rgba(GROUND, 0.9)} 0%, ${rgba(GROUND, 0)} 34%)` }} />
    <div style={{ position: 'absolute', left: 90, top: 300 }}>{leg.map(([c, t], i) => { const q = interpolate(f, [8 + i * 12, 18 + i * 12], [0, 1], C); return <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 26, marginBottom: 34, opacity: q, transform: `translateX(${(1 - q) * -30}px)` }}>
      <div style={{ width: 46, height: 46, borderRadius: 23, background: c }} /><div style={{ ...DISP(96, 70, 800), color: BONE, textShadow: SHADOW }}>{t}</div></div>; })}
      {P.note ? <Mono text={P.note} f0={40} size={22} color={MUTED} style={{ marginTop: 20 }} /> : null}</div>
  </AbsoluteFill>;
};
