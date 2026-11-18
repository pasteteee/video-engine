// Bloop — the real waveform of NOAA's 10-second file, then stretched 16x onto a 2 min 45 s ruler.
import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import BD from '../ep/bloopdata.json';
import { SceneBg } from '../kit/Brand';
import { ACCENT_EP, BONE, C, DISP, FONT, MUTED, SHADOW, TINT, io, out, rgba } from '../kit/tokens';
import { Mono } from '../kit/Type';

export const SpeedStretch: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params; const env = (BD as any).env as number[]; const file = (BD as any).file_s as number;
  const X0 = 160, X1 = 1760, Y = 560; const sAt = (P.stretch_at ?? 2) * 30;
  const st = interpolate(f, [sAt, sAt + 50], [0, 1], { ...C, easing: io });
  const w0 = (X1 - X0) / 16; const w = w0 + (X1 - X0 - w0) * st;
  const draw = interpolate(f, [2, 22], [0, 1], { ...C, easing: out });
  const real = file * 16; const tick = (sec: number) => X0 + w * sec / real;
  return <SceneBg drift={0.3}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {env.slice(0, Math.round(env.length * draw)).map((v, i) => { const x = X0 + w * i / env.length; return <line key={i} x1={x} y1={Y - v * 200} x2={x} y2={Y + v * 200} stroke={st > 0.02 ? ACCENT_EP : BONE} strokeWidth={Math.max(2, w / env.length * 0.6)} />; })}
      <line x1={X0} y1={Y + 260} x2={X0 + w} y2={Y + 260} stroke={rgba(TINT, 0.7)} strokeWidth={2} />
      {(st > 0.5 ? [0, 30, 60, 90, 120, 150] : [0]).map((sec) => <g key={sec} opacity={st > 0.5 ? interpolate(f, [sAt + 40, sAt + 56], [0, 1], C) : 1}><line x1={tick(sec)} y1={Y + 250} x2={tick(sec)} y2={Y + 272} stroke={rgba(TINT, 0.8)} strokeWidth={2} /><text x={tick(sec)} y={Y + 310} textAnchor="middle" fontFamily={FONT.mono} fontSize={22} fill={MUTED}>{`${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`}</text></g>)}
    </svg>
    <div style={{ position: 'absolute', left: X0, top: 150, ...DISP(96), color: BONE, textShadow: SHADOW }}>{st < 0.5 ? 'THE FILE: 10 SECONDS' : 'IN THE OCEAN: ~2:45'}</div>
    <Mono text={st < 0.5 ? 'NOAA PUBLIC RECORDING · PLAYED 16× FAST' : '× 16 · OWN CALCULATION'} f0={6} size={24} color={ACCENT_EP} style={{ position: 'absolute', left: X0 + 4, top: 270 }} />
  </SceneBg>;
};
