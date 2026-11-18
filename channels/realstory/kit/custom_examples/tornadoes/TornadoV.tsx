// Vertical (9:16) tornado scenes for the Shorts: the SPC map re-laid for the phone, text above it at the left edge.
import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, GROUND2, MUTED, SHADOW, SIGNAL, TINT, io, out, rgba } from '../kit/tokens';
import { Layer, MapBase, tYear, widthBy } from './Tornado';
import { PL, SE, fmt, useData } from './tdata';

const X0 = 80;
const Bg: React.FC<{ children?: React.ReactNode }> = ({ children }) => <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 45%, ${GROUND2} 0%, ${GROUND} 75%)` }}>{children}</AbsoluteFill>;
const Title: React.FC<{ text: string; f0: number; size?: number; accent?: string; top?: number }> = ({ text, f0, size = 104, accent, top = 330 }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [f0, f0 + 14], [0, 1], { ...C, easing: out });
  return <div style={{ position: 'absolute', left: X0, right: 120, top, ...DISP(size, 62, 860), lineHeight: `${size * 0.95}px`, color: BONE, textShadow: SHADOW, opacity: p, transform: `translateY(${(1 - p) * 30}px)` }}>
    {text.split(' ').map((w, i) => <span key={i} style={{ color: accent && w.replace(/[^A-Z0-9%.]/gi, '') === accent ? ACCENT_EP : undefined }}>{i ? ' ' : ''}{w}</span>)}</div>;
};
export const VTrackMap: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const data = useData(); const f = useCurrentFrame(); const P = s.params ?? {}; const mode = P.mode ?? 'grow';
  if (!data) return <Bg />;
  const MW = 1180, mx = -60, my = 760; const p = interpolate(f, [4, d - 10], [0, 1], { ...C, easing: io });
  const z = interpolate(f, [0, d], [1, P.zoom ?? 1.12], C);
  let layers: Layer[] = []; let fills: any[] = []; let fresh: any; let top: React.ReactNode = null;
  if (mode === 'grow') {
    const upTo = 1950 + 73 * p; layers = [{ id: 'all-grow', filter: () => true, color: ACCENT_EP, alpha: 0.42, width: widthBy, upTo }]; fresh = { upTo };
    let n = 0; for (const t of data.T) { if (tYear(t) <= upTo) n++; else break; }
    top = <><div style={{ position: 'absolute', left: X0, top: 330, fontFamily: FONT.mono, fontSize: 32, letterSpacing: 4, color: MUTED }}>TORNADOES ON RECORD · {Math.min(Math.floor(upTo), 2022)}</div>
      <div style={{ position: 'absolute', left: X0 - 6, top: 380, ...DISP(220, 62, 860), color: BONE, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW }}>{fmt(n)}</div></>;
  } else if (mode === 'f0') {
    const sw = interpolate(f, [10, 30], [0, 1], C);
    layers = [{ id: 'r-rest-f0', filter: (t) => t[1] !== 0, color: TINT, alpha: 0.35, width: widthBy, opacity: 1 - 0.75 * sw }, { id: 'r-hl-f0', filter: (t) => t[1] === 0, color: ACCENT_EP, alpha: 0.5, width: widthBy, opacity: 0.35 + 0.65 * sw }];
    top = <Title text={P.label ?? 'THE GROWTH IS RATED ZERO'} f0={8} accent={P.accent} />;
  } else if (mode === 'regions') {
    const a: number[] = P.from, b: number[] = P.to; const q = interpolate(f, [Math.round(d * 0.3), Math.round(d * 0.75)], [0, 1], { ...C, easing: io });
    layers = [{ id: 'f1p-all', filter: (t) => t[1] >= 1, color: TINT, alpha: 0.18, width: widthBy, opacity: 0.6 }];
    fills = [{ names: SE, fill: ACCENT_EP, opacity: 0.45 }, { names: PL, fill: TINT, opacity: 0.3 }];
    top = <><div style={{ position: 'absolute', left: X0, top: 300, fontFamily: FONT.mono, fontSize: 30, letterSpacing: 4, color: MUTED }}>{P.label} · {q < 0.5 ? P.years[0] : P.years[1]}</div>
      {[['SOUTHEAST', 0, ACCENT_EP], ['PLAINS', 1, BONE]].map(([n, i, col]: any) => <div key={n} style={{ position: 'absolute', left: X0 + i * 470, top: 350 }}>
        <div style={{ ...DISP(190, 62, 860), color: col, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW, lineHeight: 1 }}>{Math.round(a[i] + (b[i] - a[i]) * q)}%</div>
        <div style={{ fontFamily: FONT.mono, fontSize: 28, letterSpacing: 4, color: MUTED, marginTop: 6 }}>{n}</div></div>)}</>;
  } else if (mode === 'place') {
    const [yy, mo, dy] = P.date as number[]; const pl = data.geo.places[P.place]; const on = interpolate(f, [6, 24], [0, 1], C);
    layers = [{ id: 'dim-all', filter: () => true, color: TINT, alpha: 0.12, width: widthBy, opacity: 0.8 }, { id: `day-${yy}-${mo}-${dy}`, filter: (t) => t[0] === yy && t[7] === mo && t[9] === dy, color: ACCENT_EP, alpha: 0.95, width: (t) => (t[1] >= 3 ? 4 : 2.4), opacity: on }];
    const overlay = () => pl ? <g opacity={on}><circle cx={pl[0]} cy={pl[1]} r={14} fill="none" stroke={ACCENT_EP} strokeWidth={4} /><circle cx={pl[0]} cy={pl[1]} r={5} fill={BONE} /></g> : null;
    return <Bg><div style={{ position: 'absolute', left: mx, top: my, transformOrigin: `${(P.ox ?? 0.55) * 100}% ${(P.oy ?? 0.6) * 100}%`, transform: `scale(${interpolate(f, [0, d], [1.2, P.zoom ?? 2.2], { ...C, easing: io })})` }}>
      <MapBase data={data} w={MW} layers={layers} overlay={overlay} /></div><Title text={P.label} f0={8} accent={P.accent} /></Bg>;
  }
  return <Bg>
    <div style={{ position: 'absolute', left: mx, top: my, transformOrigin: '55% 60%', transform: `scale(${z})` }}><MapBase data={data} w={MW} layers={layers} fills={fills} fresh={fresh} /></div>
    {top}
  </Bg>;
};
export const VCUSTOM: Record<string, any> = { VTrackMap };
