// Two clocks: what happens on Mars and what Earth knows. Mars runs entry -> touchdown in ~7 min,
// Earth hears each event 11 min 22 s later. Time is compressed; the gap is the point.
import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { ACCENT_EP, BONE, C, DISP, FONT, MUTED, SHADOW, SIGNAL, TINT, io, rgba } from '../kit/tokens';
import { SceneBg } from '../kit/Brand';
import { Mono, StopBlock } from '../kit/Type';
const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
export const DelayClock: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const T = interpolate(f, [10, d - 20], [0, 690], { ...C, easing: io }); // seconds since entry on Mars
  const DELAY = 682; const ev: [number, string][] = [[0, 'ENTRY'], [240, 'PARACHUTE'], [420, 'TOUCHDOWN']];
  const mars = ev.filter((e) => T >= e[0]).pop()!; const earthT = T - DELAY; const earth = earthT >= 0 ? ev.filter((e) => earthT >= e[0]).pop() : null;
  const col = (x: number, title: string, clock: string, state: string, hot: boolean, i: number) => <div style={{ position: 'absolute', left: x, top: 230 }}>
    <Mono text={title} f0={2 + i * 8} size={26} color={ACCENT_EP} />
    <div style={{ ...DISP(220, 62, 860), color: BONE, marginTop: 20, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>{clock}</div>
    <div style={{ ...DISP(84, 70, 800), color: hot ? BONE : rgba(BONE, 0.45), marginTop: 30, textShadow: SHADOW, whiteSpace: 'nowrap' }}>{state}{hot && i === 1 ? <StopBlock size={84} /> : null}</div>
  </div>;
  const landed = T >= 420; const gapP = interpolate(T, [420, 690], [0, 1], C);
  return <SceneBg drift={0.3}>
    {col(164, 'ON MARS · SINCE ENTRY', fmt(Math.min(T, 420)), landed ? 'ON THE GROUND' : mars[1], true, 0)}
    {col(1040, 'ON EARTH · WHAT THE TEAM KNOWS', earthT < 0 ? '—:—' : fmt(earthT), earth ? earth[1] + ' SIGNAL' : 'NOTHING YET', !!earth, 1)}
    <svg width={1920} height={1080} style={{ position: 'absolute' }}><line x1={960} y1={220} x2={960} y2={760} stroke={rgba(TINT, 0.5)} strokeWidth={2} />
      <line x1={164} y1={860} x2={164 + 1600 * gapP} y2={860} stroke={SIGNAL} strokeWidth={5} /></svg>
    <div style={{ position: 'absolute', left: 164, top: 884, fontFamily: FONT.mono, fontSize: 24, letterSpacing: 3, color: MUTED, opacity: gapP > 0 ? 1 : 0 }}>RADIO DELAY ON LANDING DAY: MORE THAN 11 MINUTES · TIME COMPRESSED</div>
  </SceneBg>;
};
