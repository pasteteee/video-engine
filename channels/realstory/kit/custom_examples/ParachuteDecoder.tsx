// The real parachute frame; the gore rings are traced one by one and the bits become the three words.
import React from 'react';
import { AbsoluteFill, Img, interpolate, useCurrentFrame } from 'remotion';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, MUTED, SHADOW, io, out, rgba } from '../kit/tokens';
import { StopBlock } from '../kit/Type';
export const ParachuteDecoder: React.FC<{ s: any; d: number; med: (id: string) => string }> = ({ s, d, med }) => {
  const f = useCurrentFrame(); const P = s.params; const [cx, cy, R] = P.canopy; // canopy centre and radius in screen px (1920x1080 cover)
  const z = interpolate(f, [0, d], [1, 1.06], C); const words = ['DARE', 'MIGHTY', 'THINGS'];
  const bits = '0000000100'; const bp = Math.floor(interpolate(f, [70, 100], [0, 10], C));
  return <AbsoluteFill style={{ background: '#000' }}>
    <AbsoluteFill style={{ transform: `scale(${z})`, transformOrigin: `${cx}px ${cy}px` }}>
      <Img src={med(s.media_ids[0])} style={{ width: '100%', height: '100%', objectFit: 'cover', filter: `brightness(${interpolate(f, [0, 20], [1, 0.75], C)})` }} />
      <svg width={1920} height={1080} style={{ position: 'absolute' }}>
        {[0.42, 0.62, 0.8].map((r, i) => { const a = 10 + i * 16; const q = interpolate(f, [a, a + 18], [0, 1], { ...C, easing: io }); const rr = R * r;
          return <circle key={i} cx={cx} cy={cy} r={rr} fill="none" stroke={ACCENT_EP} strokeWidth={5} strokeDasharray={`${2 * Math.PI * rr * q} 9999`} transform={`rotate(-90 ${cx} ${cy})`} />; })}
        <circle cx={cx} cy={cy} r={R * 0.97} fill="none" stroke={rgba(BONE, 0.7)} strokeWidth={3} strokeDasharray="10 12" opacity={interpolate(f, [56, 66], [0, 1], C)} />
      </svg>
    </AbsoluteFill>
    <AbsoluteFill style={{ background: `linear-gradient(90deg, ${rgba(GROUND, 0)} 40%, ${rgba(GROUND, 0.92)} 62%)` }} />
    <div style={{ position: 'absolute', left: 1180, top: 210 }}>
      {words.map((w, i) => { const a = 14 + i * 16; const p = interpolate(f, [a + 8, a + 22], [0, 1], { ...C, easing: out });
        return <div key={i} style={{ overflow: 'hidden', height: 168 }}><div style={{ ...DISP(170), color: i === 1 ? ACCENT_EP : BONE, textShadow: SHADOW, transform: `translateY(${(1 - p) * 100}%)`, whiteSpace: 'nowrap' }}>{w}{i === 2 ? <StopBlock size={170} p={interpolate(f, [a + 22, a + 30], [0, 1], C)} /> : null}</div></div>; })}
      <div style={{ marginTop: 40, fontFamily: FONT.mono, fontSize: 30, letterSpacing: 4, color: BONE, opacity: f > 66 ? 1 : 0 }}>{bits.slice(0, bp)}<span style={{ opacity: 0.2 }}>{bits.slice(bp)}</span>{bp >= 10 ? <span style={{ color: ACCENT_EP }}>  = 4 → +64 → D</span> : null}</div>
      <div style={{ marginTop: 16, fontFamily: FONT.mono, fontSize: 20, letterSpacing: 3, color: MUTED, opacity: f > 66 ? 1 : 0 }}>ORANGE = 1 · WHITE = 0 · TEN BITS A LETTER</div>
    </div>
  </AbsoluteFill>;
};
