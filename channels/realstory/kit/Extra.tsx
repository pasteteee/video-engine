// Library scene types first built for the Bloop episode: globe_route, map_zoom with pins, map_compare_scale,
// stock_broll, data_plot_real, evidence_board. All colours come from the episode look (tokens), no plates behind text.
import React from 'react';
import { AbsoluteFill, Img, OffthreadVideo, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { geoDistance, geoEquirectangular, geoGraticule10, geoInterpolate, geoMercator, geoOrthographic, geoPath } from 'd3-geo';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, GROUND2, MUTED, SHADOW, SPRING_PIN, SPRING_SOFT, TINT, io, out, rgba } from './tokens';
import { Hairline, Mono } from './Type';
import { SceneBg } from './Brand';

type LL = [number, number];
type S = { s: any; d: number; med: (id?: string) => string; media: Record<string, { src: string; w: number; h: number }>; fps?: number };

const Title: React.FC<{ text?: string; note?: string; f0?: number; x?: number; y?: number; size?: number }> = ({ text, note, f0 = 6, x = 90, y = 118, size = 64 }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [f0, f0 + 16], [0, 1], { ...C, easing: out });
  if (!text) return null;
  return <div style={{ position: 'absolute', left: x, top: y }}>
    <div style={{ overflow: 'hidden', paddingBottom: 6 }}><div style={{ ...DISP(size, 70, 820), color: BONE, textShadow: SHADOW, transform: `translateY(${(1 - p) * 105}%)`, whiteSpace: 'nowrap' }}>{text}</div></div>
    {note ? <Mono text={note} f0={f0 + 14} size={22} color={ACCENT_EP} style={{ marginTop: 10 }} /> : null}
  </div>;
};

// Pin with a label: ring (the disputed pin), dot (a place). Label slides out of the pin.
const MapPin: React.FC<{ x: number; y: number; f0: number; label?: string; kind?: string; anchor?: string; dy?: number; color?: string }> = ({ x, y, f0, label, kind = 'dot', anchor = 'start', dy = 0, color = ACCENT_EP }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const p = spring({ frame: f - f0, fps, config: SPRING_PIN }); const q = interpolate(f, [f0 + 6, f0 + 20], [0, 1], { ...C, easing: out });
  if (f < f0) return null;
  const end = anchor === 'end';
  return <g>
    <g transform={`translate(${x} ${y}) scale(${p})`}>
      {kind === 'ring' ? <><circle r={22} fill="none" stroke={color} strokeWidth={4} /><circle r={5} fill={color} /></> : <><circle r={9} fill={color} /><circle r={26} fill="none" stroke={color} strokeWidth={2} opacity={1 - Math.min(1, (f - f0) / 30)} /></>}
    </g>
    {label ? <text x={x + (end ? -34 : 34)} y={y + 9 + dy} textAnchor={end ? 'end' : 'start'} fontFamily={FONT.mono} fontWeight={500} fontSize={26} letterSpacing={3} fill={BONE} opacity={q}
      style={{ filter: `drop-shadow(0 2px 8px ${rgba(GROUND, 0.9)})` } as any}>{label}</text> : null}
  </g>;
};

const Land: React.FC<{ path: any; land: any }> = ({ path, land }) => <path d={path(land) || ''} fill={rgba(TINT, 0.2)} stroke={rgba(TINT, 0.75)} strokeWidth={1.5} />;
const seaBg = () => `radial-gradient(ellipse at 50% 45%, ${GROUND2} 0%, ${GROUND} 82%)`;

// ---------- globe_route: orthographic globe turns from A to B, the link draws, labels at both ends ----------
export const GlobeRoute: React.FC<S & { land: any }> = ({ s, d, land }) => {
  const f = useCurrentFrame(); const P = s.params; const v = s.variant ?? 'night_side';
  const A: LL = P.from, B: LL = P.to; const mid = geoInterpolate(A, B)(0.5) as LL;
  const p = interpolate(f, [0, d], [0, 1], { ...C, easing: io });
  const draw = interpolate(f, [d * 0.18, d * 0.62], [0, 1], { ...C, easing: io });
  const line = { type: 'LineString', coordinates: Array.from({ length: 81 }, (_, k) => geoInterpolate(A, B)((k / 80) * draw)) } as any;
  if (v === 'flat_unroll') {
    // the globe "unrolls" into a flat world map: scale up and pan from A to B
    const proj = geoEquirectangular().scale(P.scale ?? 360).rotate([-(A[0] + (mid[0] - A[0]) * p), 0]).center([0, (A[1] + (B[1] - A[1]) * p) * 0.6]).translate([960, 520]);
    const path = geoPath(proj); const a = proj(A) as LL, b = proj(B) as LL;
    return <AbsoluteFill style={{ background: seaBg() }}>
      <svg width={1920} height={1080} style={{ position: 'absolute' }}>
        <path d={path(geoGraticule10()) || ''} fill="none" stroke={rgba(TINT, 0.12)} strokeWidth={1} />
        <Land path={path} land={land} />
        <path d={path(line) || ''} fill="none" stroke={ACCENT_EP} strokeWidth={4} strokeLinecap="round" />
        <MapPin x={a[0]} y={a[1]} f0={4} label={P.labels?.[0]} />
        <MapPin x={b[0]} y={b[1]} f0={Math.round(d * 0.6)} label={P.labels?.[1]} anchor="end" />
      </svg>
      <Title text={P.title} />
    </AbsoluteFill>;
  }
  const c0: LL = v === 'terminator_line' ? A : [A[0] - 25, A[1] + 8];
  const center: LL = [c0[0] + (mid[0] - c0[0]) * p, c0[1] + (mid[1] - c0[1]) * p];
  const sc = (P.scale ?? 400) * (1 + 0.12 * p); const cx = 1060, cy = 560;
  const proj = geoOrthographic().scale(sc).translate([cx, cy]).rotate([-center[0], -center[1], 0]).clipAngle(90).precision(0.3);
  const path = geoPath(proj); const vis = (c: LL) => geoDistance(c, center) < Math.PI / 2 - 0.04;
  const a = proj(A) as LL, b = proj(B) as LL;
  // night side: a soft shadow from one side of the disc; terminator_line: a moving day/night edge
  const sh = v === 'terminator_line' ? interpolate(f, [0, d], [-0.25, 0.15], C) : 0.1;
  return <AbsoluteFill style={{ background: seaBg() }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <defs>
        <radialGradient id="gr-sea" cx="40%" cy="35%" r="78%"><stop offset="0%" stopColor={GROUND2} /><stop offset="100%" stopColor={GROUND} /></radialGradient>
        <linearGradient id="gr-night" x1={`${30 + sh * 100}%`} y1="0%" x2={`${75 + sh * 100}%`} y2="20%"><stop offset="0%" stopColor="rgba(0,0,0,0)" /><stop offset="100%" stopColor={rgba(GROUND, 0.82)} /></linearGradient>
      </defs>
      <circle cx={cx} cy={cy} r={sc * 1.06} fill="none" stroke={rgba(ACCENT_EP, 0.18)} strokeWidth={10} />
      <path d={path({ type: 'Sphere' } as any) || ''} fill="url(#gr-sea)" />
      <path d={path(geoGraticule10()) || ''} fill="none" stroke={rgba(TINT, 0.14)} strokeWidth={1} />
      <Land path={path} land={land} />
      <path d={path({ type: 'Sphere' } as any) || ''} fill="url(#gr-night)" />
      {P.noline ? null : <path d={path(line) || ''} fill="none" stroke={ACCENT_EP} strokeWidth={4} strokeLinecap="round" />}
      {vis(A) ? <MapPin x={a[0]} y={a[1]} f0={4} label={P.labels?.[0]} anchor={a[0] > b[0] ? 'start' : 'end'} /> : null}
      {vis(B) ? <MapPin x={b[0]} y={b[1]} f0={Math.round(d * (P.noline ? 0.4 : 0.6))} label={P.labels?.[1]} anchor={a[0] > b[0] ? 'end' : 'start'} /> : null}
    </svg>
    <Title text={P.title} />
  </AbsoluteFill>;
};

// ---------- map_zoom / map_compare_scale with pins, a measured link and zones ----------
export const MapPins: React.FC<S & { land: any }> = ({ s, d, land }) => {
  const f = useCurrentFrame(); const P = s.params; const v = s.variant;
  const k = v === 'dive' ? interpolate(f, [0, d], [0.55, 1.12], { ...C, easing: io }) : v === 'pan_along' ? 1.04 : interpolate(f, [0, d], [1, 1.07], { ...C, easing: io });
  const pan = v === 'pan_along' ? interpolate(f, [0, d], [-6, 6], { ...C, easing: io }) : 0;
  const proj = geoMercator().rotate([-(P.center[0] + pan), 0]).center([0, P.center[1]]).scale((P.scale ?? 900) * k).translate([960, 580]);
  const path = geoPath(proj); const pins = (P.pins ?? []) as any[];
  const pt = (i: number) => proj(pins[i].at) as LL;
  const L = P.link; let link: any = null;
  if (L) {
    const a = pt(L.a), b = pt(L.b); const t0 = Math.round(L.t * 30); const q = interpolate(f, [t0, t0 + 20], [0, 1], { ...C, easing: io });
    const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
    link = <g><line x1={a[0]} y1={a[1]} x2={a[0] + (b[0] - a[0]) * q} y2={a[1] + (b[1] - a[1]) * q} stroke={ACCENT_EP} strokeWidth={3} strokeDasharray="14 10" />
      <text x={mx} y={my - 30} textAnchor="middle" fontFamily={FONT.display} fontWeight={820} fontSize={64} fill={BONE} opacity={interpolate(f, [t0 + 14, t0 + 26], [0, 1], C)}
        style={{ fontStretch: '70%', filter: `drop-shadow(0 3px 10px ${rgba(GROUND, 0.9)})` } as any}>{L.label}</text></g>;
  }
  return <AbsoluteFill style={{ background: seaBg() }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <path d={path(geoGraticule10()) || ''} fill="none" stroke={rgba(TINT, 0.12)} strokeWidth={1} />
      <Land path={path} land={land} />
      {(P.zones ?? []).map((z: any, i: number) => { const c = proj(z.at) as LL; const t0 = Math.round(z.t * 30); const q = interpolate(f, [t0, t0 + 24], [0, 1], { ...C, easing: out });
        return <g key={i} opacity={q}><ellipse cx={c[0]} cy={c[1]} rx={z.rx * (0.85 + 0.15 * q)} ry={z.ry * (0.85 + 0.15 * q)} transform={`rotate(${z.rot ?? 0} ${c[0]} ${c[1]})`} fill={rgba(ACCENT_EP, 0.14)} stroke={ACCENT_EP} strokeWidth={2.5} strokeDasharray="10 8" />
          <text x={c[0]} y={c[1] + (z.dy ?? 0)} textAnchor="middle" fontFamily={FONT.mono} fontWeight={500} fontSize={26} letterSpacing={3} fill={ACCENT_EP} style={{ filter: `drop-shadow(0 2px 8px ${rgba(GROUND, 0.9)})` } as any}>{z.label}</text></g>; })}
      {link}
      {pins.map((p, i) => { const [x, y] = pt(i); return <MapPin key={i} x={x} y={y} f0={Math.round(p.t * 30)} label={p.label} kind={p.kind} anchor={p.anchor} dy={p.dy} color={p.kind === 'ring' ? BONE : ACCENT_EP} />; })}
    </svg>
    <Title text={P.title} note={P.note} />
  </AbsoluteFill>;
};

// ---------- stock_broll: real footage, graded to the episode look, slow push ----------
export const StockBroll: React.FC<S> = ({ s, d, med }) => {
  const f = useCurrentFrame(); const P = s.params; const v = s.variant ?? 'graded';
  const z = (P.zoom ?? 1.04) + (P.push ?? 0.05) * interpolate(f, [0, d], [0, 1], C);
  const filter = v === 'split_tone' ? 'contrast(1.08) saturate(0.85) brightness(0.95)' : 'contrast(1.05) saturate(0.95)';
  return <AbsoluteFill style={{ backgroundColor: '#000' }}>
    <AbsoluteFill style={{ transform: `scale(${z})`, transformOrigin: P.origin ?? '50% 50%' }}>
      <OffthreadVideo src={med(s.media_ids[0])} startFrom={Math.round((P.trim ?? 0) * 30)} muted style={{ width: '100%', height: '100%', objectFit: 'cover', filter }} />
    </AbsoluteFill>
    {v === 'split_tone' ? <AbsoluteFill style={{ background: `linear-gradient(180deg, ${rgba(ACCENT_EP, 0.10)} 0%, ${rgba(GROUND, 0.25)} 100%)`, mixBlendMode: 'soft-light' }} />
      : <AbsoluteFill style={{ background: rgba(GROUND2, 0.18), mixBlendMode: 'multiply' }} />}
    <AbsoluteFill style={{ background: `linear-gradient(180deg, ${rgba(GROUND, 0.3)} 0%, ${rgba(GROUND, 0)} 25%, ${rgba(GROUND, 0)} 60%, ${rgba(GROUND, 0.8)} 100%)` }} />
    {P.label ? <div style={{ position: 'absolute', left: 90, top: P.ly ?? 860 }}><Mono text={P.label} f0={10} size={30} color={BONE} style={{ textShadow: SHADOW }} /></div> : null}
  </AbsoluteFill>;
};

// ---------- data_plot_real: our own measurement plotted (spectrum of the real recording) ----------
// params.curve: [[hz, 0..1], ...] (log power, normalised), params.median_hz, params.hear_hz (20), variant line_draw | scope_trace
export const DataPlotReal: React.FC<S> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params; const v = s.variant ?? 'line_draw';
  const X0 = 200, X1 = 1560, Y0 = 860, Y1 = 260; const fmax = P.fmax ?? 60;
  const xs = (hz: number) => X0 + (X1 - X0) * hz / fmax; const ys = (a: number) => Y0 - (Y0 - Y1) * a;
  const curve: [number, number][] = P.curve; const draw = interpolate(f, [6, Math.min(d * 0.55, 70)], [0, 1], { ...C, easing: io });
  const n = Math.max(2, Math.round(curve.length * draw)); const pts = curve.slice(0, n).map(([h, a]) => `${xs(h).toFixed(1)},${ys(a).toFixed(1)}`).join(' ');
  const area = `${xs(curve[0][0])},${Y0} ` + pts + ` ${xs(curve[n - 1][0])},${Y0}`;
  const med = P.median_hz ?? 15; const hear = P.hear_hz ?? 20;
  const tm = Math.round((P.mark_at ?? (v === 'line_draw' ? 0.5 : 0.25)) * d); const qm = interpolate(f, [tm, tm + 18], [0, 1], { ...C, easing: out });
  const scan = v === 'scope_trace' ? (f % 60) / 60 : -1;
  return <SceneBg drift={0.3}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {[0, 10, 20, 30, 40, 50, 60].filter((h) => h <= fmax).map((h) => <g key={h}><line x1={xs(h)} y1={Y1 - 20} x2={xs(h)} y2={Y0} stroke={rgba(TINT, 0.16)} strokeWidth={1} />
        <text x={xs(h)} y={Y0 + 44} textAnchor="middle" fontFamily={FONT.mono} fontSize={24} fill={MUTED}>{h}</text></g>)}
      <text x={X1} y={Y0 + 90} textAnchor="end" fontFamily={FONT.mono} fontSize={22} letterSpacing={3} fill={MUTED}>HERTZ (REAL SPEED)</text>
      <line x1={X0} y1={Y0} x2={X1} y2={Y0} stroke={rgba(TINT, 0.6)} strokeWidth={2} />
      {v === 'scope_trace' ? <g opacity={qm}><rect x={X0} y={Y1 - 20} width={xs(hear) - X0} height={Y0 - Y1 + 20} fill={rgba(GROUND, 0.55)} />
        <line x1={xs(hear)} y1={Y1 - 40} x2={xs(hear)} y2={Y0} stroke={BONE} strokeWidth={3} />
        <text x={xs(hear) + 18} y={Y1 - 10} fontFamily={FONT.mono} fontWeight={500} fontSize={26} letterSpacing={3} fill={BONE}>HUMAN HEARING STARTS ≈ {hear} HZ</text>
        <text x={X0 + 16} y={Y1 - 10} fontFamily={FONT.mono} fontWeight={500} fontSize={26} letterSpacing={3} fill={ACCENT_EP}>FELT, NOT HEARD</text></g> : null}
      <polygon points={area} fill={rgba(ACCENT_EP, 0.16)} />
      <polyline points={pts} fill="none" stroke={ACCENT_EP} strokeWidth={4} strokeLinejoin="round" />
      {scan >= 0 ? <line x1={X0 + (X1 - X0) * scan} y1={Y1 - 20} x2={X0 + (X1 - X0) * scan} y2={Y0} stroke={rgba(BONE, 0.25)} strokeWidth={2} /> : null}
      {v === 'line_draw' ? <g opacity={qm}><line x1={xs(med)} y1={Y1 - 40} x2={xs(med)} y2={Y0} stroke={BONE} strokeWidth={3} strokeDasharray="10 8" />
        <text x={xs(med) + 18} y={Y1 - 10} fontFamily={FONT.mono} fontWeight={500} fontSize={26} letterSpacing={3} fill={BONE}>HALF THE ENERGY BELOW ≈ {med} HZ</text></g> : null}
    </svg>
    <Title text={P.title ?? 'THE BLOOP, MEASURED'} x={200} y={90} size={58} />
  </SceneBg>;
};

// ---------- evidence_board: several records pinned side by side, a thread links them ----------
export const EvidenceBoard: React.FC<S> = ({ s, d, med, media }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const ids: string[] = s.media_ids; const P = s.params; const n = ids.length;
  const W = 520, H = 360, gap = 70; const x0 = (1920 - (n * W + (n - 1) * gap)) / 2; const push = interpolate(f, [0, d], [1, 1.05], C);
  const cards = ids.map((id, i) => ({ id, x: x0 + i * (W + gap), y: 300 + (i % 2 ? 60 : 0), rot: [-2.2, 1.6, -1.2, 2][i % 4], f0: 4 + i * 9 }));
  const thread = interpolate(f, [n * 9 + 6, n * 9 + 30], [0, 1], { ...C, easing: io });
  return <SceneBg drift={0.3} style={{ transform: `scale(${push})` }}>
    {cards.map((c, i) => { const p = spring({ frame: f - c.f0, fps, config: SPRING_SOFT }); if (f < c.f0) return null; const m = media[c.id];
      return <div key={c.id} style={{ position: 'absolute', left: c.x, top: c.y, width: W, transform: `translateY(${(1 - p) * 80}px) rotate(${c.rot}deg)`, opacity: Math.min(1, p * 1.6) }}>
        <Img src={med(c.id)} style={{ width: W, height: H, objectFit: 'cover', boxShadow: `0 20px 50px ${rgba(GROUND, 0.7)}` }} />
        <div style={{ ...DISP(70, 70, 820), color: i === 0 ? ACCENT_EP : BONE, marginTop: 22, textShadow: SHADOW }}>{P.labels?.[i]}</div>
      </div>; })}
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {cards.slice(1).map((c, i) => { const a = cards[i]; const x1 = a.x + W / 2, y1 = a.y + 6, x2 = c.x + W / 2, y2 = c.y + 6;
        return <path key={i} d={`M${x1},${y1} Q${(x1 + x2) / 2},${Math.min(y1, y2) - 70} ${x2},${y2}`} fill="none" stroke={ACCENT_EP} strokeWidth={3} strokeDasharray={`${thread * 900} 2000`} />; })}
      {cards.map((c, i) => f >= c.f0 + 6 ? <circle key={i} cx={c.x + W / 2} cy={c.y + 6} r={9} fill={ACCENT_EP} /> : null)}
    </svg>
  </SceneBg>;
};

// ---------- scale_compare / stack_up: a known size as a bar, the needed size grows past the frame ----------
// params: known [label, value_m], need_label, kicker
export const ScaleStack: React.FC<S> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params; const x0 = 200, Y = 470;
  const kb = interpolate(f, [6, 26], [0, 1], { ...C, easing: out }); const grow = interpolate(f, [30, Math.min(d - 10, 110)], [0, 1], { ...C, easing: io });
  const kw = 420; const nw = kw + (2400 - kw) * grow;
  return <SceneBg drift={0.25} style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <Title text={P.label} x={x0} y={150} size={72} />
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <rect x={x0} y={Y} width={kw * kb} height={70} fill={rgba(BONE, 0.85)} />
      <rect x={x0} y={Y + 200} width={nw} height={70} fill={ACCENT_EP} opacity={grow > 0 ? 1 : 0} />
      <line x1={x0} y1={Y - 30} x2={x0} y2={Y + 300} stroke={rgba(TINT, 0.6)} strokeWidth={2} />
    </svg>
    <div style={{ position: 'absolute', left: x0, top: Y + 86, opacity: kb }}><Mono text={P.known ?? 'BLUE WHALE · LARGEST ANIMAL KNOWN'} f0={8} size={26} color={BONE} /></div>
    <div style={{ position: 'absolute', left: x0, top: Y + 286 }}><Mono text={P.need ?? 'AN ANIMAL LOUD ENOUGH FOR THE BLOOP'} f0={34} size={26} color={ACCENT_EP} /></div>
    <div style={{ position: 'absolute', left: 1180, top: Y + 86, ...DISP(92, 70, 840), color: BONE, textShadow: SHADOW, opacity: interpolate(f, [d * 0.55, d * 0.55 + 12], [0, 1], C) }}>{P.verdict ?? 'NONE KNOWN'}</div>
  </SceneBg>;
};

// ---------- counter_ticker / flip_digits: days between two dated records ----------
export const DayCounter: React.FC<S> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params; const n = Math.round(interpolate(f, [12, Math.min(d - 20, 80)], [0, P.days], { ...C, easing: io }));
  const q = interpolate(f, [4, 18], [0, 1], { ...C, easing: out });
  return <SceneBg drift={0.3}>
    <Mono text={P.label} f0={2} size={28} color={MUTED} style={{ position: 'absolute', left: 164, top: 230 }} />
    <div style={{ position: 'absolute', left: 156, top: 290, display: 'flex', alignItems: 'flex-end', gap: 36 }}>
      <div style={{ ...DISP(380, 62, 860), color: BONE, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>{n}</div>
      <div style={{ ...DISP(150, 62, 840), color: ACCENT_EP, marginBottom: 20 }}>DAYS</div>
    </div>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <line x1={164} y1={790} x2={164 + 1300 * q} y2={790} stroke={rgba(TINT, 0.7)} strokeWidth={2} />
      {Array.from({ length: P.days + 1 }, (_, i) => <line key={i} x1={164 + 1300 * i / P.days} y1={i <= n ? 770 : 782} x2={164 + 1300 * i / P.days} y2={810} stroke={i <= n ? ACCENT_EP : rgba(TINT, 0.4)} strokeWidth={i === 0 || i === P.days ? 4 : 2} />)}
    </svg>
    <Mono text={P.from_label} f0={8} size={26} color={BONE} style={{ position: 'absolute', left: 164, top: 836 }} />
    <Mono text={P.to_label} f0={Math.min(d - 30, 80)} size={26} color={ACCENT_EP} style={{ position: 'absolute', left: 164 + 1300 - 260, top: 836, width: 260, textAlign: 'right' }} />
  </SceneBg>;
};
