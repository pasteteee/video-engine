// A23a custom scenes: the Taylor column spin, the island-sized berg, the shrinking outline.
import React, { useEffect, useMemo, useState } from 'react';
import { AbsoluteFill, interpolate, staticFile, useCurrentFrame, useDelayRender } from 'remotion';
import { geoMercator, geoPath } from 'd3-geo';
import { feature } from 'topojson-client';
import { ACCENT_EP, C, DISP, FG, FG_MUTED, FONT, GROUND, GROUND2, SHADOW, TINT, io, out, rgba } from '../kit/tokens';
import { Hairline, Mono } from '../kit/Type';
import { SceneBg } from '../kit/Brand';

type P = { s: any; d: number };
// A23a's plan shape, roughly as in the 2024 MODIS frames (unit square, centred on 0,0).
export const BERG: [number, number][] = [[-0.5, -0.36], [-0.12, -0.5], [0.46, -0.42], [0.5, 0.06], [0.38, 0.5], [-0.2, 0.44], [-0.48, 0.18]];
const poly = (pts: [number, number][], cx: number, cy: number, sx: number, sy: number, rot = 0) => {
  const c = Math.cos(rot), s = Math.sin(rot);
  return pts.map(([x, y]) => `${cx + (x * sx) * c - (y * sy) * s},${cy + (x * sx) * s + (y * sy) * c}`).join(' ');
};
const Title: React.FC<{ text: string; f0: number; x?: number; y: number; size?: number; accent?: string }> = ({ text, f0, x = 150, y, size = 84, accent }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [f0, f0 + 16], [0, 1], { ...C, easing: out });
  return <div style={{ position: 'absolute', left: x, top: y, overflow: 'hidden', paddingBottom: size * 0.08 }}>
    <div style={{ ...DISP(size), color: FG, textShadow: SHADOW, transform: `translateY(${(1 - p) * 105}%)`, whiteSpace: 'nowrap' }}>
      {text.split(' ').map((w, i) => <span key={i} style={{ color: accent && w === accent ? ACCENT_EP : undefined }}>{i ? ' ' : ''}{w}</span>)}</div></div>;
};

// ---------- 1. Taylor column: current runs past a seamount, the column turns, the berg turns with it ----------
export const TaylorColumn: React.FC<P> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params; const cx = 1180, cy = 540;
  const days0 = P.day0 ?? 0, days1 = P.day1 ?? 240; const rate = P.rate ?? 15;
  const k = interpolate(f, [0, d], [0, 1], { ...C, easing: io });
  const day = days0 + (days1 - days0) * k;
  const esc = P.escape ? interpolate(f, [d * 0.45, d], [0, 1], { ...C, easing: io }) : 0;
  const ang = (day * rate * Math.PI) / 180;
  const bx = cx + esc * 620, by = cy - esc * 330;
  const draw = interpolate(f, [0, 26], [0, 1], { ...C, easing: out });
  // streamlines: deflect around the bank, faster outside
  const lines = Array.from({ length: 11 }, (_, i) => -500 + i * 100);
  const path = (y0: number) => { const pts: string[] = []; for (let x = 300; x <= 1920; x += 20) { const dx = x - cx; const g = Math.exp(-(dx * dx) / (2 * 330 * 330)); const dy = y0 + Math.sign(y0 || 1) * 180 * g * Math.exp(-Math.abs(y0) / 400); pts.push(`${x},${cy + dy}`); } return 'M' + pts.join(' L'); };
  const flow = -f * 3.2;
  return <SceneBg drift={0.15}>
    <svg width={1920} height={1080} style={{ position: 'absolute', opacity: draw }}>
      {/* seamount contours */}
      {[300, 240, 180, 120, 64].map((r, i) => <ellipse key={i} cx={cx + 10} cy={cy + 8} rx={r * 1.12} ry={r * 0.92} fill={rgba(TINT, 0.06 + i * 0.03)} stroke={rgba(TINT, 0.55)} strokeWidth={1.5} strokeDasharray={i % 2 ? '2 8' : undefined} />)}
      {/* far-field current */}
      {lines.filter((y) => Math.abs(y) > 120).map((y, i) => <path key={i} d={path(y)} fill="none" stroke={rgba(ACCENT_EP, 0.45)} strokeWidth={2.2} strokeDasharray="26 22" strokeDashoffset={flow * (1.2 + Math.abs(y) / 600)} />)}
      {/* trapped rotating water */}
      {[110, 170, 230, 290].map((r, i) => <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={rgba(ACCENT_EP, 0.7 - i * 0.12)} strokeWidth={3 - i * 0.4} strokeDasharray="40 30" strokeDashoffset={(-f * (5 - i)) * (P.escape ? 1 - esc : 1)} transform={`rotate(${-f * 0.6} ${cx} ${cy})`} />)}
      {/* the berg (ice: white with an ink edge) */}
      <polygon points={poly(BERG, bx, by, 300, 270, -ang)} fill="#ffffff" stroke={FG} strokeWidth={3} style={{ filter: `drop-shadow(0 10px 18px ${rgba(FG, 0.25)})` }} />
      <line x1={bx} y1={by} x2={bx + Math.cos(-ang) * 120} y2={by + Math.sin(-ang) * 120} stroke={ACCENT_EP} strokeWidth={4} />
      <circle cx={bx} cy={by} r={6} fill={ACCENT_EP} />
      <text x={cx + 330} y={cy + 300} fontFamily={FONT.mono} fontSize={20} letterSpacing={3} fill={FG_MUTED}>PIRIE BANK · SEAMOUNT</text>
      <text x={330} y={cy - 430} fontFamily={FONT.mono} fontSize={20} letterSpacing={3} fill={ACCENT_EP}>CURRENT →</text>
    </svg>
    <Mono text="DAY" f0={4} size={24} style={{ position: 'absolute', left: 154, top: 300 }} />
    <div style={{ position: 'absolute', left: 146, top: 330, ...DISP(170, 62, 860), color: FG, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW }}>{String(Math.round(day)).padStart(3, '0')}</div>
    <Mono text={`ROTATION ≈ ${rate}° A DAY`} f0={10} size={24} color={ACCENT_EP} style={{ position: 'absolute', left: 154, top: 520 }} />
    <Mono text={`FULL TURNS: ${Math.floor((day * rate) / 360)}`} f0={16} size={24} color={FG} style={{ position: 'absolute', left: 154, top: 566 }} />
    {P.label ? <Title text={P.label} f0={Math.round(d * 0.25)} x={150} y={800} size={92} accent={P.accent} /> : null}
    <Mono text="SCHEMATIC · NOT TO SCALE" f0={20} size={16} style={{ position: 'absolute', left: 1420, top: 60 }} />
  </SceneBg>;
};

// ---------- 2. Island vs berg, drawn to the same scale ----------
export const useSG = () => {
  const [g, setG] = useState<any>(null); const { delayRender, continueRender } = useDelayRender(); const [h] = useState(() => delayRender('sg'));
  useEffect(() => { fetch(staticFile('countries-50m.json')).then((r) => r.json()).then((t) => {
    const fc: any = feature(t, t.objects.countries); const sg = fc.features.find((x: any) => x.properties.name === 'S. Geo. and the Is.');
    const polys = sg.geometry.type === 'MultiPolygon' ? sg.geometry.coordinates : [sg.geometry.coordinates];
    const main = polys.filter((p: any) => p[0].some((c: number[]) => c[0] < -35 && c[0] > -39 && c[1] < -53.8 && c[1] > -55)).sort((a: any, b: any) => b[0].length - a[0].length)[0];
    setG({ type: 'Polygon', coordinates: main }); continueRender(h); }); }, []);
  return g;
};
export const IslandMatch: React.FC<P> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params; const sg = useSG();
  const proj = useMemo(() => sg ? geoMercator().fitExtent([[150, 230], [930, 820]], sg) : null, [sg]);
  if (!sg || !proj) return <SceneBg />;
  const path = geoPath(proj); const b = path.bounds(sg);
  // km per pixel at the island's latitude
  const p0 = proj([-36.5, -54.3])!, p1 = proj([-36.5, -55.3])!; const pxPerKm = Math.abs(p1[1] - p0[1]) / 111.2;
  const bw = 64 * pxPerKm, bh = 54 * pxPerKm; // ≈ 3,460 km² footprint
  const drawI = interpolate(f, [4, 40], [0, 1], { ...C, easing: io });
  const bIn = interpolate(f, [20, 44], [0, 1], { ...C, easing: out });
  const slide = interpolate(f, [d * 0.55, d * 0.8], [0, 1], { ...C, easing: io });
  const icx = (b[0][0] + b[1][0]) / 2, icy = (b[0][1] + b[1][1]) / 2;
  const bx = 1420 + (icx - 1420) * slide, by = 520 + (icy - 520) * slide;
  const nA = Math.round(3528 * interpolate(f, [10, 46], [0, 1], { ...C, easing: out })), nB = Math.round(3460 * interpolate(f, [24, 60], [0, 1], { ...C, easing: out }));
  const L = 6000;
  return <SceneBg drift={0.1}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <path d={path(sg) ?? ''} fill={rgba(TINT, 0.22)} stroke={FG} strokeWidth={3} strokeDasharray={`${L * drawI} ${L}`} />
      <polygon points={poly(BERG, bx, by, bw, bh, 0.12)} fill={rgba('#ffffff', 0.8 * bIn)} stroke={ACCENT_EP} strokeWidth={4} opacity={bIn} />
      <line x1={180} y1={900} x2={180 + 50 * pxPerKm} y2={900} stroke={FG} strokeWidth={3} />
      <text x={180} y={936} fontFamily={FONT.mono} fontSize={20} letterSpacing={3} fill={FG_MUTED}>50 KM</text>
    </svg>
    <div style={{ position: 'absolute', left: 150, top: 120, opacity: drawI }}>
      <div style={{ ...DISP(64), color: FG, textShadow: SHADOW }}>SOUTH GEORGIA</div>
      <div style={{ fontFamily: FONT.mono, fontSize: 40, color: FG, letterSpacing: '0.06em', marginTop: 10, fontVariantNumeric: 'tabular-nums' }}>{nA.toLocaleString('en-US')} KM²</div>
    </div>
    <div style={{ position: 'absolute', left: 1240, top: 120, opacity: bIn }}>
      <div style={{ ...DISP(64), color: ACCENT_EP, textShadow: SHADOW }}>ICEBERG A23a</div>
      <div style={{ fontFamily: FONT.mono, fontSize: 40, color: FG, letterSpacing: '0.06em', marginTop: 10, fontVariantNumeric: 'tabular-nums' }}>{nB.toLocaleString('en-US')} KM²</div>
    </div>
    {f > d * 0.78 ? <Title text="98 PER CENT OF THE ISLAND" f0={Math.round(d * 0.78)} x={1060} y={860} size={70} accent="98" /> : null}
    <Mono text="SAME SCALE · AREAS: ESA, 5 APR 2025 · BERG OUTLINE SIMPLIFIED" f0={30} size={16} style={{ position: 'absolute', left: 1060, top: 990 }} />
  </SceneBg>;
};

// ---------- 3. Shrink meter: the berg outline at each measured area, same scale ----------
export const ShrinkMeter: React.FC<P> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params; const R: [string, number][] = P.readings; const n = R.length;
  const max = Math.max(...R.map((r) => r[1]));
  const t = interpolate(f, [8, d - 30], [0, n - 1], { ...C });
  const i = Math.min(n - 2, Math.floor(t)); const u = io(Math.min(1, Math.max(0, t - i) * 1.4));
  const area = R[i][1] + (R[i + 1][1] - R[i][1]) * u;
  const cur = t >= n - 1 ? n - 1 : u > 0.5 ? i + 1 : i;
  const S = 560; const k = Math.sqrt(area / max);
  const cx = 1360, cy = 540;
  return <SceneBg drift={0.1}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <polygon points={poly(BERG, cx, cy, S, S * 0.88, 0.1)} fill="none" stroke={rgba(TINT, 0.8)} strokeWidth={2} strokeDasharray="8 10" />
      <polygon points={poly(BERG, cx, cy, S * k, S * 0.88 * k, 0.1 + (1 - k) * 0.5)} fill="#ffffff" stroke={ACCENT_EP} strokeWidth={4} style={{ filter: `drop-shadow(0 12px 20px ${rgba(FG, 0.2)})` }} />
      {/* rail of readings */}
      <line x1={150} y1={880} x2={900} y2={880} stroke={rgba(TINT, 0.6)} strokeWidth={2} />
      <line x1={150} y1={880} x2={150 + 750 * (t / (n - 1))} y2={880} stroke={ACCENT_EP} strokeWidth={4} />
      {R.map((r, j) => <g key={j}><circle cx={150 + (750 * j) / (n - 1)} cy={880} r={j <= cur ? 9 : 6} fill={j <= cur ? ACCENT_EP : GROUND} stroke={ACCENT_EP} strokeWidth={2} />
        <text x={150 + (750 * j) / (n - 1)} y={930} textAnchor="middle" fontFamily={FONT.mono} fontSize={17} letterSpacing={2} fill={j === cur ? FG : FG_MUTED}>{r[0]}</text></g>)}
    </svg>
    <Mono text={P.label ?? 'SURFACE AREA'} f0={2} size={26} style={{ position: 'absolute', left: 154, top: 250 }} />
    <div style={{ position: 'absolute', left: 146, top: 300, display: 'flex', alignItems: 'flex-end', gap: 26 }}>
      <span style={{ ...DISP(250, 62, 880), color: FG, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW, lineHeight: 0.86 }}>{Math.round(area / 10) * 10 >= 1000 ? (Math.round(area / 10) * 10).toLocaleString('en-US') : Math.round(area / 10) * 10}</span>
      <span style={{ ...DISP(90), color: ACCENT_EP }}>KM²</span>
    </div>
    <Mono text={R[cur][0]} f0={6} size={34} color={ACCENT_EP} style={{ position: 'absolute', left: 154, top: 540 }} />
    {P.note && f > d * (P.note_at ?? 0.82) ? <Mono text={P.note} f0={Math.round(d * (P.note_at ?? 0.82))} size={26} color={FG} style={{ position: 'absolute', left: 154, top: 640 }} /> : null}
    <Hairline x={154} y={620} w={700} f0={20} />
    <Mono text="SOURCES: USNIC VIA NASA · COPERNICUS SENTINEL-3 · DASHED = NOV 2023 SIZE" f0={30} size={16} style={{ position: 'absolute', left: 1000, top: 990 }} />
  </SceneBg>;
};

export const ICEBERG_CUSTOM = { TaylorColumn, IslandMatch, ShrinkMeter };
