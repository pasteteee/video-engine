// Ghost octopus — the nursery as a chain: mud floor, nodule, sponge stalk, eggs, mother.
// mode 'build' draws it bottom-up; mode 'break' removes the nodule and the chain falls link by link.
import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { SceneBg } from '../kit/Brand';
import { ACCENT_EP, BONE, C, DISP, FONT, MUTED, SHADOW, SIGNAL, TINT, io, out, rgba } from '../kit/tokens';
import { Mono } from '../kit/Type';

const FLOOR = 820;
export const NurseryChain: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const mode: string = s.params?.mode ?? 'build';
  const st = (a: number, b = 14) => interpolate(f, [a, a + b], [0, 1], { ...C, easing: out });
  const links = [st(4), st(18), st(32, 20), st(52), st(66)];
  const gone = mode === 'break' ? [0, 1, 2, 3].map((i) => interpolate(f, [20 + i * 26, 40 + i * 26], [0, 1], { ...C, easing: io })) : [0, 0, 0, 0];
  const L = mode === 'break' ? [1, 1, 1, 1, 1] : links;
  const labels: [string, number, number][] = mode === 'break' ? [] : [['NODULE', 1040, 790], ['SPONGE STALK (DEAD)', 1080, 600], ['EGGS · ~30 × 2-2.7 CM', 1080, 470], ['MOTHER, BROODING', 1080, 330]];
  const ox = 820;
  return <SceneBg>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <rect x={0} y={FLOOR} width={1920} height={260} fill={rgba(TINT, 0.12)} opacity={L[0]} />
      <path d={`M0 ${FLOOR} Q480 ${FLOOR - 8} 960 ${FLOOR} T1920 ${FLOOR}`} stroke={rgba(TINT, 0.6)} strokeWidth={2} fill="none" opacity={L[0]} />
      <g opacity={L[1] * (1 - gone[0])}><ellipse cx={ox} cy={FLOOR - 18} rx={90} ry={44} fill={rgba(BONE, 0.18)} stroke={BONE} strokeWidth={3} /></g>
      <g opacity={L[2] * (1 - gone[1])} transform={`translate(0 ${gone[1] * 120})`}><path d={`M${ox} ${FLOOR - 50} C ${ox + 10} ${FLOOR - 200}, ${ox - 20} ${FLOOR - 300}, ${ox + 6} ${FLOOR - 400 * L[2]}`} stroke={BONE} strokeWidth={6} fill="none" /></g>
      <g opacity={L[3] * (1 - gone[2])} transform={`translate(0 ${gone[2] * 160})`}>{Array.from({ length: 9 }, (_, i) => <ellipse key={i} cx={ox - 30 + (i % 3) * 30} cy={FLOOR - 400 + 40 + Math.floor(i / 3) * 36} rx={13} ry={17} fill={rgba(ACCENT_EP, 0.35)} stroke={ACCENT_EP} strokeWidth={2.5} />)}</g>
      <g opacity={L[4] * (1 - gone[3])} transform={`translate(0 ${gone[3] * 200})`}>
        <path d={`M${ox - 70} ${FLOOR - 450} Q${ox} ${FLOOR - 600} ${ox + 70} ${FLOOR - 450}`} fill={rgba(BONE, 0.85)} />
        {[-60, -30, 0, 30, 60].map((dx, i) => <path key={i} d={`M${ox + dx * 0.9} ${FLOOR - 455} q ${dx * 0.6} 60 ${dx * 1.1} 110`} stroke={rgba(BONE, 0.8)} strokeWidth={9} fill="none" strokeLinecap="round" />)}
      </g>
      {labels.map(([t, x, y], i) => { const o = (mode === 'break' ? 1 : L[i + 1]) * (1 - gone[i]); return <g key={i} opacity={o}><line x1={ox + 100} y1={y + 2} x2={x - 16} y2={y + 2} stroke={rgba(BONE, 0.5)} strokeWidth={2} /><text x={x} y={y + 12} fontFamily={FONT.mono} fontSize={30} letterSpacing={3} fill={BONE} style={{ textShadow: SHADOW }}>{t}</text></g>; })}
      {mode === 'break' ? gone.map((g, i) => g > 0.3 ? <text key={i} x={1300} y={340 + i * 110} fontFamily={FONT.display} fontWeight={820} style={{ fontVariationSettings: "'wdth' 62", textShadow: SHADOW }} fontSize={78} fill={i === 3 ? ACCENT_EP : BONE} opacity={Math.min(1, (g - 0.3) * 3)}>{['NO NODULE', 'NO SPONGE', 'NO NEST', 'NO NEXT BROOD?'][i]}</text> : null) : null}
    </svg>
    <Mono text="DRAWING AFTER PURSER ET AL. 2016 · NOT TO SCALE" f0={10} size={18} style={{ position: 'absolute', left: 60, top: 1080 - 100 }} />
  </SceneBg>;
};
