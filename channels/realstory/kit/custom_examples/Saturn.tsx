// Saturn's rings 1612: scenes made for this episode.
import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, MUTED, SHADOW, TINT, io, out, rgba } from '../kit/tokens';
import { Mono } from '../kit/Type';
import { SceneBg } from '../kit/Brand';

type P = { s: any; d: number };
const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
const lerpSeries = (ser: number[][], x: number) => { if (x <= ser[0][0]) return ser[0][1]; for (let i = 1; i < ser.length; i++) if (ser[i][0] >= x) { const a = ser[i - 1], b = ser[i]; return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]); } return ser[ser.length - 1][1]; };

// Saturn drawn from the ring opening angle B (deg): back half of the rings, globe, front half.
const Planet: React.FC<{ B: number; Bs: number; cx: number; cy: number; R: number; tone?: number }> = ({ B, Bs, cx, cy, R, tone = 1 }) => {
  const k = Math.sin((B * Math.PI) / 180); const lit = Math.min(1, 0.12 + Math.abs(Math.sin((Bs * Math.PI) / 180)) * 6); // edge-lit rings are dim
  const bands = [[1.24, 1.53, 0.35], [1.53, 1.95, 0.95], [2.03, 2.27, 0.7]];
  const ring = (half: 'back' | 'front') => bands.map(([a, b, op], i) => {
    const ro = R * b, ri = R * a, yo = Math.max(0.6, ro * Math.abs(k)), yi = Math.max(0.4, ri * Math.abs(k));
    const sweepTop = (k >= 0) === (half === 'back');
    const outer = `M${cx - ro} ${cy} A ${ro} ${yo} 0 0 ${sweepTop ? 1 : 0} ${cx + ro} ${cy}`;
    const inner = `L${cx + ri} ${cy} A ${ri} ${yi} 0 0 ${sweepTop ? 0 : 1} ${cx - ri} ${cy} Z`;
    return <path key={half + i} d={outer + ' ' + inner} fill={rgba('#e9d9b0', op * lit * tone)} stroke={Math.abs(k) < 0.02 ? rgba('#e9d9b0', lit * 0.8) : 'none'} strokeWidth={1.5} />;
  });
  return <g>
    {ring('back')}
    <defs><radialGradient id="globe" cx="40%" cy="38%" r="70%"><stop offset="0%" stopColor="#efdcab" /><stop offset="60%" stopColor="#c9a868" /><stop offset="100%" stopColor="#6d5530" /></radialGradient>
      <clipPath id="gclip"><circle cx={cx} cy={cy} r={R} /></clipPath></defs>
    <circle cx={cx} cy={cy} r={R} fill="url(#globe)" opacity={tone} />
    <g clipPath="url(#gclip)">{[-0.5, -0.2, 0.15, 0.42].map((y, i) => <rect key={i} x={cx - R} y={cy + y * R} width={2 * R} height={R * 0.07} fill={rgba('#8a6a3c', 0.25 * tone)} />)}
      {/* ring shadow on the globe */}
      <ellipse cx={cx} cy={cy - Math.sign(Bs || 1) * R * 0.1} rx={R * 1.9} ry={Math.max(1, R * 1.9 * Math.abs(Math.sin((Bs * Math.PI) / 180)) * 0.5)} fill={rgba('#2a1d0e', 0.35 * tone)} /></g>
    {ring('front')}
  </g>;
};

// The hero scene: a date runs; the rings close to a line and open again. Right: what a 20x lens shows.
export const RingTilt: React.FC<P> = ({ s, d }) => {
  const f = useCurrentFrame(); const p = s.params; const ser: number[][] = p.series; const sun: number[][] = p.sun;
  const run = interpolate(f, [p.hold0 ?? 10, d - (p.hold1 ?? 24)], [0, 1], { ...C, easing: io });
  const t = p.from + (p.to - p.from) * run; const B = lerpSeries(ser, t); const Bs = lerpSeries(sun, t);
  const yr = Math.floor(t), mo = Math.min(11, Math.floor((t - yr) * 12));
  const scope = p.scope !== false;
  const enter = interpolate(f, [0, 16], [0, 1], { ...C, easing: out });
  return <SceneBg drift={0.15}>
    <svg width={1920} height={1080} style={{ position: 'absolute', opacity: enter }}>
      <Planet B={B} Bs={Bs} cx={scope ? 700 : 960} cy={560} R={scope ? 150 : 190} />
    </svg>
    {scope ? <div style={{ position: 'absolute', left: 1330, top: 330, width: 460, height: 460, borderRadius: '50%', overflow: 'hidden', background: '#0b0906', opacity: enter, boxShadow: `0 0 0 2px ${rgba(TINT, 0.35)}` }}>
      <svg width={460} height={460} style={{ filter: 'blur(5px)' }}><Planet B={B} Bs={Bs} cx={230} cy={230} R={46} /></svg>
    </div> : null}
    {scope ? <Mono text="ABOUT 20x · WHAT GALILEO COULD SEE" f0={18} size={20} color={MUTED} style={{ position: 'absolute', left: 1330, top: 812 }} /> : null}
    <div style={{ position: 'absolute', left: 150, top: 120, fontFamily: FONT.mono, fontWeight: 500, fontSize: 92, color: BONE, letterSpacing: '0.04em', textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>
      <span style={{ color: ACCENT_EP }}>{MONTHS[mo]}</span> {yr}</div>
    <Mono text={`RING TILT TO EARTH  ${B >= 0 ? '+' : '−'}${Math.abs(B).toFixed(1)}°`} f0={4} size={28} color={BONE} style={{ position: 'absolute', left: 156, top: 240 }} />
    <Mono text={`SUNLIGHT ON RINGS  ${Math.abs(Bs).toFixed(1)}°`} f0={10} size={22} color={MUTED} style={{ position: 'absolute', left: 156, top: 284 }} />
    {Math.abs(B) < 1.2 || Math.abs(Bs) < 0.6 ? <div style={{ position: 'absolute', left: 150, top: 860, ...DISP(96), color: ACCENT_EP, textShadow: SHADOW }}>{p.edgeLabel ?? 'EDGE-ON'}</div> : null}
  </SceneBg>;
};

// Top view of the two orbits. The ring plane keeps its direction in space; when its line passes the Sun or Earth, the rings are edge-on.
export const OrbitPlane: React.FC<P> = ({ s, d }) => {
  const f = useCurrentFrame(); const p = s.params; const pos: number[][] = p.pos; // [year, ex, ey, sx, sy] in AU, ecliptic
  const run = interpolate(f, [8, d - 16], [0, 1], { ...C, easing: p.ease === 'linear' ? undefined : io });
  const i = Math.min(pos.length - 1, Math.floor(run * (pos.length - 1))); const q = pos[i];
  const cx = 960, cy = 560; const sc = (r: number) => (r < 1.2 ? r * 110 : 110 + (r - 1) * 38); // not to scale: inner orbit enlarged
  const P2 = (x: number, y: number): [number, number] => { const r = Math.hypot(x, y); const k = sc(r) / (r || 1); return [cx + x * k, cy - y * k]; };
  const [ex, ey] = P2(q[1], q[2]); const [sx, sy] = P2(q[3], q[4]);
  const node = (p.node * Math.PI) / 180; const ux = Math.cos(node), uy = -Math.sin(node);
  // distance of Earth and Sun from the ring-plane line through Saturn (screen space)
  const distTo = (x: number, y: number) => Math.abs((x - sx) * uy - (y - sy) * ux);
  const onE = distTo(ex, ey) < 10, onS = distTo(cx, cy) < 10;
  const trail = pos.slice(0, i + 1).filter((_, k) => k % 2 === 0).map((r) => P2(r[3], r[4]));
  return <SceneBg drift={0.1}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <circle cx={cx} cy={cy} r={sc(1)} fill="none" stroke={rgba(TINT, 0.35)} strokeWidth={1.5} />
      <circle cx={cx} cy={cy} r={sc(9.55)} fill="none" stroke={rgba(TINT, 0.35)} strokeWidth={1.5} strokeDasharray="3 8" />
      <polyline points={trail.map((t) => t.join(',')).join(' ')} fill="none" stroke={rgba(ACCENT_EP, 0.5)} strokeWidth={3} />
      <line x1={sx - ux * 1400} y1={sy - uy * 1400} x2={sx + ux * 1400} y2={sy + uy * 1400} stroke={onE || onS ? ACCENT_EP : rgba(BONE, 0.45)} strokeWidth={onE || onS ? 3.5 : 1.5} strokeDasharray={onE || onS ? undefined : '10 10'} />
      <circle cx={cx} cy={cy} r={22} fill="#f4d78a" style={{ filter: 'drop-shadow(0 0 18px rgba(244,215,138,0.8))' }} />
      <circle cx={ex} cy={ey} r={11} fill="#9fc3d8" />
      <g transform={`translate(${sx} ${sy}) rotate(${(-p.node)})`}><ellipse cx={0} cy={0} rx={34} ry={6} fill={rgba('#e9d9b0', 0.9)} /><circle cx={0} cy={0} r={13} fill="#d8b878" /></g>
      <text x={cx + 30} y={cy + 8} fontFamily={FONT.mono} fontSize={22} fill={MUTED}>SUN</text>
      <text x={ex + 18} y={ey + 30} fontFamily={FONT.mono} fontSize={22} fill={BONE}>EARTH</text>
      <text x={sx + 40} y={sy - 26} fontFamily={FONT.mono} fontSize={22} fill={BONE}>SATURN</text>
    </svg>
    <div style={{ position: 'absolute', left: 150, top: 110, fontFamily: FONT.mono, fontWeight: 500, fontSize: 64, color: BONE, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW }}>{Math.floor(q[0])}</div>
    <Mono text="RING PLANE, SEEN FROM ABOVE · NOT TO SCALE" f0={6} size={22} color={MUTED} style={{ position: 'absolute', left: 156, top: 196 }} />
    <div style={{ position: 'absolute', left: 150, top: 880, ...DISP(84), color: onE || onS ? ACCENT_EP : rgba(BONE, 0), textShadow: SHADOW }}>{onS ? 'SUN ON THE EDGE' : 'EARTH ON THE EDGE'}</div>
  </SceneBg>;
};

// Galileo's 37 scrambled letters fly into the sentence they hide.
export const Anagram: React.FC<P> = ({ s, d }) => {
  const f = useCurrentFrame(); const p = s.params;
  const src: string = p.scrambled; const lines: string[] = p.lines; const target = lines.join('');
  const norm = (c: string) => (c === 'V' ? 'U' : c);
  const used = new Set<number>(); const map: number[] = [];
  for (const c of target) { if (c === ' ') { map.push(-1); continue; } const j = [...src].findIndex((x, k) => !used.has(k) && norm(x) === norm(c)); used.add(j); map.push(j); }
  const cw = p.cw ?? 64, size = p.size ?? 92; const per = p.perRow ?? 40, rows = Math.ceil(src.length / per), inRow = Math.min(per, src.length);
  const srcX = (k: number) => 960 - (inRow * 40) / 2 + (k % per) * 40; const srcY = (k: number) => 330 - (rows - 1) * 56 + Math.floor(k / per) * 56;
  const lineOf: [number, number][] = []; lines.forEach((ln, li) => [...ln].forEach((_, ci) => lineOf.push([li, ci])));
  const solveAt = Math.round(d * (p.at ?? 0.35));
  return <SceneBg drift={0.2}>
    {[...target].map((c, n) => {
      const [li, ci] = lineOf[n]; const k = map[n]; if (k < 0) return null;
      const pr = interpolate(f, [solveAt + n * 0.7, solveAt + n * 0.7 + 22], [0, 1], { ...C, easing: io });
      const x0 = srcX(k), y0 = srcY(k); const x1 = 160 + ci * cw, y1 = 470 + li * (size * 1.02);
      const x = x0 + (x1 - x0) * pr, y = y0 + (y1 - y0) * pr - Math.sin(pr * Math.PI) * 60; const sz = 52 + (size - 52) * pr;
      const show = interpolate(f, [2 + k * 0.6, 8 + k * 0.6], [0, 1], C);
      return <div key={n} style={{ position: 'absolute', left: x, top: y, width: cw, ...DISP(sz, 70, 820), color: pr > 0.98 && li === (p.accentLine ?? 2) ? ACCENT_EP : BONE, opacity: show, textShadow: SHADOW, textAlign: 'center' }}>{pr > 0.5 ? c : src[k]}</div>;
    })}
    <Mono text={p.head ?? 'GALILEO · 1610 · 37 LETTERS'} f0={2} size={26} color={MUTED} style={{ position: 'absolute', left: 160, top: 240 - (rows - 1) * 56 }} />
    {p.note ? <Mono text={p.note} f0={solveAt + 50} size={28} color={BONE} style={{ position: 'absolute', left: 160, top: 470 + lines.length * size * 1.02 + 30 }} /> : null}
  </SceneBg>;
};

// ---- vertical (9:16) versions for the Shorts ----
export const VRingTilt: React.FC<P> = ({ s, d }) => {
  const f = useCurrentFrame(); const p = s.params; const ser: number[][] = p.series; const sun: number[][] = p.sun;
  const run = interpolate(f, [6, d - 18], [0, 1], { ...C, easing: io });
  const t = p.from + (p.to - p.from) * run; const B = lerpSeries(ser, t); const Bs = lerpSeries(sun, t);
  const yr = Math.floor(t), mo = Math.min(11, Math.floor((t - yr) * 12));
  return <SceneBg drift={0.15}>
    <div style={{ position: 'absolute', left: 80, top: 300, fontFamily: FONT.mono, fontWeight: 500, fontSize: 110, color: BONE, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}><span style={{ color: ACCENT_EP }}>{MONTHS[mo]}</span> {yr}</div>
    <Mono text={`RING TILT ${B >= 0 ? '+' : '−'}${Math.abs(B).toFixed(1)}° · SUN ${Math.abs(Bs).toFixed(1)}°`} f0={2} size={30} color={BONE} style={{ position: 'absolute', left: 84, top: 430 }} />
    <svg width={1080} height={1920} style={{ position: 'absolute' }}><Planet B={B} Bs={Bs} cx={540} cy={760} R={150} /></svg>
    <div style={{ position: 'absolute', left: 290, top: 1010, width: 500, height: 500, borderRadius: '50%', overflow: 'hidden', background: '#0b0906', boxShadow: `0 0 0 2px ${rgba(TINT, 0.35)}` }}>
      <svg width={500} height={500} style={{ filter: 'blur(5px)' }}><Planet B={B} Bs={Bs} cx={250} cy={250} R={50} /></svg></div>
    <Mono text="ABOUT 20x · WHAT GALILEO SAW" f0={8} size={26} color={MUTED} style={{ position: 'absolute', left: 84, top: 1540 }} />
  </SceneBg>;
};
export const VAnagram: React.FC<P> = ({ s, d }) => {
  const f = useCurrentFrame(); const p = s.params; const src: string = p.scrambled; const lines: string[] = p.lines; const target = lines.join('');
  const norm = (c: string) => (c === 'V' ? 'U' : c); const used = new Set<number>(); const map: number[] = [];
  for (const c of target) { const j = [...src].findIndex((x, k) => !used.has(k) && norm(x) === norm(c)); used.add(j); map.push(j); }
  const lineOf: [number, number][] = []; lines.forEach((ln, li) => [...ln].forEach((_, ci) => lineOf.push([li, ci])));
  const solveAt = Math.round(d * (p.at ?? 0.35)); const cw = 84, size = 120;
  return <SceneBg drift={0.2}>
    {[...target].map((c, n) => { const [li, ci] = lineOf[n]; const k = map[n];
      const pr = interpolate(f, [solveAt + n * 0.7, solveAt + n * 0.7 + 22], [0, 1], { ...C, easing: io });
      const x0 = 80 + (k % 10) * 92, y0 = 420 + Math.floor(k / 10) * 110; const x1 = 80 + ci * cw, y1 = 760 + li * size * 1.05;
      const x = x0 + (x1 - x0) * pr, y = y0 + (y1 - y0) * pr; const show = interpolate(f, [2 + k * 0.6, 8 + k * 0.6], [0, 1], C);
      return <div key={n} style={{ position: 'absolute', left: x, top: y, width: cw, ...DISP(70 + 50 * pr, 70, 820), color: pr > 0.98 && li === (p.accentLine ?? 2) ? ACCENT_EP : BONE, opacity: show, textShadow: SHADOW, textAlign: 'center' }}>{pr > 0.5 ? c : src[k]}</div>; })}
    <Mono text={p.head ?? 'GALILEO · 1610 · 37 LETTERS'} f0={2} size={30} color={MUTED} style={{ position: 'absolute', left: 84, top: 330 }} />
    {(p.notes ?? (p.note ? [p.note] : [])).map((t: string, i: number) => <Mono key={i} text={t} f0={solveAt + 50 + i * 8} size={32} color={BONE} style={{ position: 'absolute', left: 84, top: 760 + lines.length * size * 1.05 + 30 + i * 48 }} />)}
  </SceneBg>;
};
