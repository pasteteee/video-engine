// Vertical (9:16) versions of the A23a custom scenes, composed for 1080x1920 (text column on the left edge).
import React, { useMemo } from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { geoMercator, geoPath } from 'd3-geo';
import { ACCENT_EP, C, DISP, FG, FG_MUTED, FONT, GROUND, SHADOW, TINT, io, out, rgba } from '../kit/tokens';
import { Mono } from '../kit/Type';
import { SceneBg } from '../kit/Brand';
import { BERG, useSG } from './Iceberg';

type P = { s: any; d: number };
const W = 1080, H = 1920, X0 = 80;
const poly = (pts: [number, number][], cx: number, cy: number, sx: number, sy: number, rot = 0) => {
  const c = Math.cos(rot), s = Math.sin(rot);
  return pts.map(([x, y]) => `${cx + (x * sx) * c - (y * sy) * s},${cy + (x * sx) * s + (y * sy) * c}`).join(' ');
};
const Big: React.FC<{ text: string; f0: number; y: number; size: number; accent?: string }> = ({ text, f0, y, size, accent }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [f0, f0 + 14], [0, 1], { ...C, easing: out });
  return <div style={{ position: 'absolute', left: X0, right: 120, top: y, ...DISP(size, 62, 880), lineHeight: `${size * 0.94}px`, color: FG, textShadow: SHADOW, opacity: p, transform: `translateY(${(1 - p) * 30}px)` }}>
    {text.split(' ').map((w, i) => <span key={i} style={{ color: accent && w === accent ? ACCENT_EP : undefined }}>{i ? ' ' : ''}{w}</span>)}</div>;
};

export const VTaylor: React.FC<P> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params; const cx = 540, cy = 1150;
  const day0 = P.day0 ?? 0, day1 = P.day1 ?? 240, rate = P.rate ?? 15;
  const day = day0 + (day1 - day0) * interpolate(f, [0, d], [0, 1], { ...C, easing: io });
  const ang = (day * rate * Math.PI) / 180; const draw = interpolate(f, [0, 20], [0, 1], { ...C, easing: out });
  const path = (y0: number) => { const pts: string[] = []; for (let x = -40; x <= W + 40; x += 16) { const dx = x - cx; const g = Math.exp(-(dx * dx) / (2 * 260 * 260));
    pts.push(`${x},${cy + y0 + Math.sign(y0) * 150 * g * Math.exp(-Math.abs(y0) / 380)}`); } return 'M' + pts.join(' L'); };
  return <SceneBg drift={0.15}>
    <svg width={W} height={H} style={{ position: 'absolute', opacity: draw }}>
      {[300, 240, 180, 120, 64].map((r, i) => <ellipse key={i} cx={cx + 8} cy={cy + 8} rx={r * 1.08} ry={r * 0.94} fill={rgba(TINT, 0.06 + i * 0.03)} stroke={rgba(TINT, 0.55)} strokeWidth={1.5} strokeDasharray={i % 2 ? '2 8' : undefined} />)}
      {[-560, -460, -360, 360, 460, 560].map((y, i) => <path key={i} d={path(y)} fill="none" stroke={rgba(ACCENT_EP, 0.45)} strokeWidth={2.2} strokeDasharray="26 22" strokeDashoffset={-f * 3.2 * (1.2 + Math.abs(y) / 600)} />)}
      {[110, 170, 230, 290].map((r, i) => <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={rgba(ACCENT_EP, 0.7 - i * 0.12)} strokeWidth={3 - i * 0.4} strokeDasharray="40 30" strokeDashoffset={-f * (5 - i)} />)}
      <polygon points={poly(BERG, cx, cy, 290, 260, -ang)} fill="#ffffff" stroke={FG} strokeWidth={3} style={{ filter: `drop-shadow(0 10px 18px ${rgba(FG, 0.25)})` }} />
      <line x1={cx} y1={cy} x2={cx + Math.cos(-ang) * 120} y2={cy + Math.sin(-ang) * 120} stroke={ACCENT_EP} strokeWidth={5} />
      <circle cx={cx} cy={cy} r={7} fill={ACCENT_EP} />
      <text x={X0} y={cy + 470} fontFamily={FONT.mono} fontSize={26} letterSpacing={3} fill={FG_MUTED}>PIRIE BANK · SEAMOUNT</text>
      <text x={X0} y={cy - 640} fontFamily={FONT.mono} fontSize={26} letterSpacing={3} fill={ACCENT_EP}>CURRENT →</text>
    </svg>
    <Mono text="DAY" f0={2} size={32} style={{ position: 'absolute', left: X0, top: 250 }} />
    <div style={{ position: 'absolute', left: X0 - 8, top: 290, ...DISP(200, 62, 860), color: FG, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW }}>{String(Math.round(day)).padStart(3, '0')}</div>
    <Mono text={`FULL TURNS: ${Math.floor((day * rate) / 360)}`} f0={8} size={32} color={ACCENT_EP} style={{ position: 'absolute', left: X0 + 420, top: 330 }} />
    <Mono text={`≈ ${rate}° A DAY`} f0={12} size={32} style={{ position: 'absolute', left: X0 + 420, top: 380 }} />
    <Mono text="SCHEMATIC · NOT TO SCALE" f0={16} size={22} style={{ position: 'absolute', left: X0, top: 1700 }} />
  </SceneBg>;
};

export const VIsland: React.FC<P> = ({ s, d }) => {
  const f = useCurrentFrame(); const sg = useSG();
  const proj = useMemo(() => sg ? geoMercator().fitExtent([[X0, 520], [W - X0, 980]], sg) : null, [sg]);
  if (!sg || !proj) return <SceneBg />;
  const path = geoPath(proj); const b = path.bounds(sg);
  const p0 = proj([-36.5, -54.3])!, p1 = proj([-36.5, -55.3])!; const pxPerKm = Math.abs(p1[1] - p0[1]) / 111.2;
  const bw = 64 * pxPerKm, bh = 54 * pxPerKm;
  const drawI = interpolate(f, [2, 34], [0, 1], { ...C, easing: io }); const bIn = interpolate(f, [14, 36], [0, 1], { ...C, easing: out });
  const slide = interpolate(f, [d * 0.5, d * 0.75], [0, 1], { ...C, easing: io });
  const icx = (b[0][0] + b[1][0]) / 2, icy = (b[0][1] + b[1][1]) / 2;
  const bx = 540 + (icx - 540) * slide, by = 1360 + (icy - 1360) * slide;
  const nA = Math.round(3528 * interpolate(f, [6, 40], [0, 1], { ...C, easing: out })), nB = Math.round(3460 * interpolate(f, [18, 52], [0, 1], { ...C, easing: out }));
  const L = 6000; const end = f > d * 0.76;
  return <SceneBg drift={0.1}>
    <svg width={W} height={H} style={{ position: 'absolute' }}>
      <path d={path(sg) ?? ''} fill={rgba(TINT, 0.22)} stroke={FG} strokeWidth={3} strokeDasharray={`${L * drawI} ${L}`} />
      <polygon points={poly(BERG, bx, by, bw, bh, 0.12)} fill={rgba('#ffffff', 0.8 * bIn)} stroke={ACCENT_EP} strokeWidth={4} opacity={bIn} />
      <line x1={X0} y1={1080} x2={X0 + 50 * pxPerKm} y2={1080} stroke={FG} strokeWidth={3} />
      <text x={X0} y={1120} fontFamily={FONT.mono} fontSize={24} letterSpacing={3} fill={FG_MUTED}>50 KM</text>
    </svg>
    <div style={{ position: 'absolute', left: X0, top: 260, opacity: drawI }}>
      <div style={{ ...DISP(80), color: FG, textShadow: SHADOW }}>SOUTH GEORGIA</div>
      <div style={{ fontFamily: FONT.mono, fontSize: 48, color: FG, letterSpacing: '0.06em', marginTop: 10, fontVariantNumeric: 'tabular-nums' }}>{nA.toLocaleString('en-US')} KM²</div>
    </div>
    {!end ? <div style={{ position: 'absolute', left: X0, top: 1580, opacity: bIn }}>
      <div style={{ ...DISP(80), color: ACCENT_EP, textShadow: SHADOW }}>ICEBERG A23a</div>
      <div style={{ fontFamily: FONT.mono, fontSize: 48, color: FG, letterSpacing: '0.06em', marginTop: 10, fontVariantNumeric: 'tabular-nums' }}>{nB.toLocaleString('en-US')} KM²</div>
    </div> : <Big text="98 PER CENT OF THE ISLAND" f0={Math.round(d * 0.76)} y={1500} size={110} accent="98" />}
  </SceneBg>;
};

export const VShrink: React.FC<P> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params; const R: [string, number][] = P.readings; const n = R.length;
  const max = Math.max(...R.map((r) => r[1])); const t = interpolate(f, [6, d - 24], [0, n - 1], C);
  const i = Math.min(n - 2, Math.floor(t)); const u = io(Math.min(1, Math.max(0, t - i) * 1.4));
  const area = R[i][1] + (R[i + 1][1] - R[i][1]) * u; const cur = t >= n - 1 ? n - 1 : u > 0.5 ? i + 1 : i;
  const S = 720, k = Math.sqrt(area / max), cx = 540, cy = 1080; const x1 = W - X0 - 40;
  const a10 = Math.round(area / 10) * 10;
  return <SceneBg drift={0.1}>
    <svg width={W} height={H} style={{ position: 'absolute' }}>
      <polygon points={poly(BERG, cx, cy, S, S * 0.88, 0.1)} fill="none" stroke={rgba(TINT, 0.8)} strokeWidth={2} strokeDasharray="8 10" />
      <polygon points={poly(BERG, cx, cy, S * k, S * 0.88 * k, 0.1 + (1 - k) * 0.5)} fill="#ffffff" stroke={ACCENT_EP} strokeWidth={4} style={{ filter: `drop-shadow(0 12px 20px ${rgba(FG, 0.2)})` }} />
      <line x1={X0} y1={1560} x2={x1} y2={1560} stroke={rgba(TINT, 0.6)} strokeWidth={2} />
      <line x1={X0} y1={1560} x2={X0 + (x1 - X0) * (t / (n - 1))} y2={1560} stroke={ACCENT_EP} strokeWidth={5} />
      {R.map((r, j) => <circle key={j} cx={X0 + ((x1 - X0) * j) / (n - 1)} cy={1560} r={j <= cur ? 11 : 7} fill={j <= cur ? ACCENT_EP : GROUND} stroke={ACCENT_EP} strokeWidth={2} />)}
    </svg>
    <Mono text={P.label ?? 'SURFACE AREA'} f0={2} size={32} style={{ position: 'absolute', left: X0, top: 250 }} />
    <div style={{ position: 'absolute', left: X0 - 6, top: 300, display: 'flex', alignItems: 'flex-end', gap: 22 }}>
      <span style={{ ...DISP(220, 62, 880), color: FG, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW, lineHeight: 0.86 }}>{a10 >= 1000 ? a10.toLocaleString('en-US') : a10}</span>
      <span style={{ ...DISP(90), color: ACCENT_EP }}>KM²</span></div>
    <Mono text={R[cur][0]} f0={4} size={40} color={ACCENT_EP} style={{ position: 'absolute', left: X0, top: 1610 }} />
    <Mono text="DASHED = SIZE AT GROUNDING" f0={20} size={22} style={{ position: 'absolute', left: X0, top: 1680 }} />
  </SceneBg>;
};

export const ICEBERG_V: Record<string, any> = { VTaylor, VIsland, VShrink };
