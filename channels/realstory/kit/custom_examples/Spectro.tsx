// Bloop — reading a real NOAA spectrogram: the record fills the frame on paper, a playhead runs with the sound,
// optional axis callouts explain how to read it.
import React from 'react';
import { Img, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { SceneBg } from '../kit/Brand';
import { ACCENT_EP, BONE, C, DISP, FONT, MUTED, SHADOW, SPRING_SOFT, io, out, rgba } from '../kit/tokens';
import { Mono } from '../kit/Type';

export const Spectro: React.FC<{ s: any; d: number; med: (id: string) => string; media: any }> = ({ s, d, med, media }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const P = s.params; const id = s.media_ids[0]; const m = media[id];
  const BW = P.box?.[0] ?? 1300, BH = P.box?.[1] ?? 800; const k = Math.min(BW / m.w, BH / m.h); const w = m.w * k, h = m.h * k;
  const x = P.left ?? 1920 - 90 - w, y = (1080 - h) / 2 + 20;
  const pin = spring({ frame: f - 1, fps, config: SPRING_SOFT }); const z = interpolate(f, [0, d], [1, 1.04], C);
  const [px0, py0, px1, py1] = P.plot ?? [0.1, 0.05, 0.97, 0.85];
  const a = (P.play_at ?? 0) * fps, b = a + (P.play_dur ?? 0) * fps;
  const ph = P.play_dur ? interpolate(f, [a, b], [P.ph0 ?? 0, P.ph1 ?? 1], C) : -1;
  const hx = x + w * (px0 + (px1 - px0) * ph);
  const ex = (t0: number) => interpolate(f, [t0, t0 + 12], [0, 1], { ...C, easing: out });
  return <SceneBg drift={0.25}>
    <div style={{ position: 'absolute', left: x, top: y, width: w, height: h, background: '#fff', boxShadow: '0 40px 120px rgba(0,0,0,0.55)', transform: `translateY(${(1 - pin) * 60}px) scale(${z})`, opacity: pin, transformOrigin: '50% 50%' }}>
      <Img src={med(id)} style={{ width: w, height: h }} />
      {ph >= 0 && f >= a ? <div style={{ position: 'absolute', left: hx - x - 2, top: h * py0, width: 4, height: h * (py1 - py0), background: ACCENT_EP, boxShadow: `0 0 18px ${ACCENT_EP}` }} /> : null}
      {ph >= 0 && f >= a ? <div style={{ position: 'absolute', left: w * px0, top: h * py0, width: hx - x - w * px0, height: h * (py1 - py0), background: rgba(ACCENT_EP, 0.10) }} /> : null}
    </div>
    <div style={{ position: 'absolute', left: 90, top: 300, width: Math.max(300, x - 140) }}>
      <div style={{ ...DISP(P.label_size ?? 92), color: BONE, textShadow: SHADOW, opacity: ex(8) }}>{P.label}</div>
      {P.sub ? <Mono text={P.sub} f0={18} size={24} color={ACCENT_EP} style={{ marginTop: 24 }} /> : null}
      {P.play_dur ? <div style={{ marginTop: 40, display: 'flex', gap: 6, alignItems: 'center', height: 70, opacity: ex(a - 6) }}>{Array.from({ length: 22 }, (_, i) => { const on = f >= a && f <= b; const v = on ? 0.3 + 0.7 * Math.abs(Math.sin(f / 3 + i * 1.7)) : 0.12; return <div key={i} style={{ width: 8, height: 70 * v, background: on ? ACCENT_EP : rgba(BONE, 0.3) }} />; })}</div> : null}
      {P.play_dur ? <Mono text={P.listen ?? 'LISTEN'} f0={a} size={22} color={MUTED} style={{ marginTop: 16 }} /> : null}
    </div>
    {P.explain ? <>
      <div style={{ position: 'absolute', left: x + w * px0, top: y + h + 26, ...DISP(54), color: ACCENT_EP, opacity: ex(P.explain[0] * fps), textShadow: SHADOW }}>TIME →</div>
      <div style={{ position: 'absolute', left: x - 78, top: y + h * py0, transform: 'rotate(-90deg) translateX(-100%)', transformOrigin: '0 0', ...DISP(54), color: ACCENT_EP, opacity: ex(P.explain[1] * fps), textShadow: SHADOW, whiteSpace: 'nowrap' }}>PITCH →</div>
      <div style={{ position: 'absolute', left: 90, top: 760, ...DISP(64), color: BONE, opacity: ex(P.explain[2] * fps), textShadow: SHADOW }}>BRIGHT = LOUD</div>
    </> : null}
  </SceneBg>;
};
