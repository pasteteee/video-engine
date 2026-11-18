// Tornado episode scenes built from the NOAA SPC record itself: every track on one map,
// the yearly count split by rating, the calendar of bursts, the damage ruler and the shift of deaths.
import React, { useLayoutEffect, useRef } from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { SceneBg } from '../kit/Brand';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, GROUND2, MUTED, SHADOW, SIGNAL, TINT, io, out, rgba } from '../kit/tokens';
import { Hairline, Mono, Odometer } from '../kit/Type';
import { Data, PL, SE, Track, fmt, useData } from './tdata';

const lerp = (a: number, b: number, p: number) => a + (b - a) * p;
// Rising display line, no plate (same look as the episode's Line).
const Rise: React.FC<{ text: string; f0: number; x: number; y: number; size?: number; accent?: string; color?: string }> = ({ text, f0, x, y, size = 84, accent, color = BONE }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [f0, f0 + 16], [0, 1], { ...C, easing: out });
  if (f < f0) return null;
  return <div style={{ position: 'absolute', left: x, top: y, overflow: 'hidden', paddingBottom: size * 0.08 }}>
    <div style={{ ...DISP(size), color, whiteSpace: 'nowrap', textShadow: SHADOW, transform: `translateY(${(1 - p) * 105}%)` }}>
      {text.split(' ').map((w, i) => <span key={i} style={{ color: accent && w.replace(/[^A-Z0-9%.]/gi, '') === accent ? ACCENT_EP : undefined }}>{i ? ' ' : ''}{w}</span>)}</div></div>;
};

// ---------------- map ----------------
export type Layer = { id: string; filter: (t: Track) => boolean; color: string; alpha?: number; width?: (t: Track) => number; upTo?: number; opacity?: number };
export const tYear = (t: Track) => t[0] + (t[7] - 1) / 12 + (t[9] - 1) / 365;
const CACHE = new Map<string, { c: HTMLCanvasElement; list: Track[]; idx: number }>();
const drawTrack = (g: CanvasRenderingContext2D, t: Track, k: number) => {
  g.beginPath();
  if (Math.abs(t[2] - t[4]) < 0.5 && Math.abs(t[3] - t[5]) < 0.5) { g.moveTo(t[2] * k - 0.9, t[3] * k); g.lineTo(t[2] * k + 0.9, t[3] * k); }
  else { g.moveTo(t[2] * k, t[3] * k); g.lineTo(t[4] * k, t[5] * k); }
  g.stroke();
};
const layerCanvas = (data: Data, L: Layer, w: number, h: number, k: number) => {
  const key = `${L.id}@${w}`; let E = CACHE.get(key);
  if (!E) { const c = document.createElement('canvas'); c.width = w; c.height = h; E = { c, list: data.T.filter(L.filter), idx: 0 }; CACHE.set(key, E); }
  const g = E.c.getContext('2d')!; g.lineCap = 'round'; g.globalAlpha = L.alpha ?? 0.5; g.globalCompositeOperation = 'lighter'; g.strokeStyle = L.color;
  let n = E.list.length; if (L.upTo !== undefined) { n = 0; while (n < E.list.length && tYear(E.list[n]) <= L.upTo) n++; }
  if (n < E.idx) { g.clearRect(0, 0, w, h); E.idx = 0; }
  for (let i = E.idx; i < n; i++) { const t = E.list[i]; g.lineWidth = L.width ? L.width(t) : 1.3; drawTrack(g, t, k); }
  E.idx = n; return E;
};
export const MapBase: React.FC<{ data: Data; w: number; layers: Layer[]; fills?: { names: string[]; fill: string; opacity: number }[]; overlay?: (k: number) => React.ReactNode; fresh?: { upTo: number; filter: (t: Track) => boolean } }> = ({ data, w, layers, fills = [], overlay, fresh }) => {
  const { W, H, nation, states } = data.geo; const k = w / W; const h = H * k; const ref = useRef<HTMLCanvasElement>(null);
  useLayoutEffect(() => {
    const c = ref.current; if (!c) return; const g = c.getContext('2d')!; g.clearRect(0, 0, c.width, c.height);
    for (const L of layers) { if ((L.opacity ?? 1) <= 0.001) continue; const E = layerCanvas(data, L, Math.round(w), Math.round(h), k); g.globalAlpha = L.opacity ?? 1; g.globalCompositeOperation = 'source-over'; g.drawImage(E.c, 0, 0); }
    if (fresh) { // tracks of the last ~0.6 year flash in bone
      g.globalCompositeOperation = 'lighter'; g.strokeStyle = BONE; g.lineCap = 'round'; g.lineWidth = 2.4;
      const E = CACHE.get(`${layers[0].id}@${Math.round(w)}`); if (E) for (let i = E.idx - 1; i >= 0; i--) { const t = E.list[i]; const age = fresh.upTo - tYear(t); if (age > 0.6) break; if (age < 0) continue; g.globalAlpha = (1 - age / 0.6) * 0.85; drawTrack(g, t, k); }
    }
  });
  return <div style={{ position: 'absolute', left: 0, top: 0, width: w, height: h }}>
    <svg viewBox={`0 0 ${W} ${H}`} width={w} height={h} style={{ position: 'absolute', inset: 0, overflow: 'visible' }}>
      <path d={nation} fill={rgba(GROUND2, 0.9)} />
      {fills.map((s, i) => <g key={i} opacity={s.opacity}>{s.names.map((n) => <path key={n} d={states[n]} fill={s.fill} />)}</g>)}
      <g fill="none" stroke={rgba(TINT, 0.22)} strokeWidth={1.2}>{Object.values(states).map((d, i) => <path key={i} d={d} />)}</g>
      <path d={nation} fill="none" stroke={rgba(TINT, 0.7)} strokeWidth={2} />
    </svg>
    <canvas ref={ref} width={Math.round(w)} height={Math.round(h)} style={{ position: 'absolute', inset: 0, width: w, height: h }} />
    {overlay ? <svg viewBox={`0 0 ${W} ${H}`} width={w} height={h} style={{ position: 'absolute', inset: 0, overflow: 'visible' }}>{overlay(k)}</svg> : null}
  </div>;
};
export const widthBy = (t: Track) => (t[1] >= 3 ? 2.6 : t[1] >= 1 ? 1.5 : 1.0);
const MW = 1500, MX = 300, MY = 90;

// TrackMap: one map, several modes.
//  grow     tracks appear year by year (y0→y1), year and running count in the corner
//  rating   all tracks, then only F0 or only F1+ (hl), with counts
//  decades  F1+ tracks decade by decade, the decade centre moves east and leaves a trail
//  regions  Southeast vs Plains states filled; shares count from a→b
//  place    a single day's tracks lit, pin and name, camera dives in
export const TrackMap: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const data = useData(); const f = useCurrentFrame(); const P = s.params; const mode = P.mode ?? 'grow';
  if (!data) return <SceneBg />;
  const p = interpolate(f, [8, d - 14], [0, 1], { ...C, easing: io });
  const plc = mode === 'place' ? data.geo.places[P.place] : null;
  const cam: number[][] = P.cam ?? (plc ? [[0.5, 0.5, 1.0], [plc[0] / data.geo.W, plc[1] / data.geo.H, P.zoom ?? 2.2]] : [[0.5, 0.5, 1.0], [0.5, 0.5, 1.06]]);
  const cp = interpolate(f, [0, d], [0, 1], { ...C, easing: io });
  const cx = lerp(cam[0][0], cam[1][0], cp), cy = lerp(cam[0][1], cam[1][1], cp), z = cam[0][2] * Math.pow(cam[1][2] / cam[0][2], cp);
  const mh = data.geo.H * (MW / data.geo.W);
  let layers: Layer[] = []; let fills: any[] = []; let overlay: ((k: number) => React.ReactNode) | undefined; let fresh: any; let side: React.ReactNode = null;
  if (mode === 'grow') {
    const y0 = P.y0 ?? 1950, y1 = P.y1 ?? 2023; const upTo = lerp(y0, y1, p);
    layers = [{ id: 'all-grow', filter: () => true, color: ACCENT_EP, alpha: 0.42, width: widthBy, upTo }];
    fresh = { upTo };
    let n = 0; for (const t of data.T) { if (tYear(t) <= upTo) n++; else break; }
    side = <>
      <div style={{ position: 'absolute', left: 120, top: 150, fontFamily: FONT.mono, fontSize: 30, letterSpacing: 4, color: MUTED }}>TORNADOES ON RECORD</div>
      <div style={{ position: 'absolute', left: 112, top: 190, ...DISP(170, 62, 860), color: BONE, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW }}>{fmt(n)}</div>
      <div style={{ position: 'absolute', left: 120, top: 360, fontFamily: FONT.mono, fontSize: 64, color: ACCENT_EP, fontVariantNumeric: 'tabular-nums' }}>{Math.min(Math.floor(upTo), 2022)}</div>
    </>;
  } else if (mode === 'rating') {
    const hl = P.hl ?? 'f0'; const sw = interpolate(f, [Math.round(d * 0.3), Math.round(d * 0.3) + 20], [0, 1], C);
    const isHl = (t: Track) => (hl === 'f0' ? t[1] === 0 : hl === 'f3p' ? t[1] >= 3 : t[1] >= 1);
    layers = [{ id: `r-rest-${hl}`, filter: (t) => !isHl(t), color: TINT, alpha: 0.35, width: widthBy, opacity: 1 - 0.75 * sw },
      { id: `r-hl-${hl}`, filter: isHl, color: ACCENT_EP, alpha: 0.5, width: widthBy, opacity: 0.35 + 0.65 * sw }];
    side = <><Rise text={P.label} f0={Math.round(d * 0.3)} x={120} y={150} size={92} accent={P.accent} />
      {P.sub ? <Mono text={P.sub} f0={Math.round(d * 0.3) + 14} size={26} color={BONE} style={{ position: 'absolute', left: 124, top: 260 }} /> : null}</>;
  } else if (mode === 'decades') {
    const decs = [1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020]; const pos = p * (decs.length - 1); const i0 = Math.floor(pos), fr = pos - i0;
    layers = decs.map((dc, i) => ({ id: `dec-${dc}`, filter: (t: Track) => t[1] >= 1 && t[0] >= dc && t[0] < dc + 10, color: ACCENT_EP, alpha: 0.6, width: widthBy, opacity: Math.max(0, 1 - Math.abs(pos - i) * 1.2) }));
    const cen = data.geo.cen; const at = (q: number) => { const a = cen[Math.min(Math.floor(q), cen.length - 1)], b = cen[Math.min(Math.floor(q) + 1, cen.length - 1)]; const t = q - Math.floor(q); return [lerp(a[1], b[1], t), lerp(a[2], b[2], t)]; };
    overlay = (k) => { const [x, y] = at(pos); const r = 14 / z; const trail = cen.slice(0, i0 + 1).map((c) => `${c[1]},${c[2]}`).join(' ') + ` ${x},${y}`;
      return <g><polyline points={trail} fill="none" stroke={BONE} strokeWidth={3 / z} strokeDasharray={`${6 / z} ${5 / z}`} />
        {cen.slice(0, i0 + 1).map((c, i) => <circle key={i} cx={c[1]} cy={c[2]} r={4.5 / z} fill={BONE} opacity={0.6} />)}
        <circle cx={x} cy={y} r={r * 2.4} fill="none" stroke={ACCENT_EP} strokeWidth={2.5 / z} opacity={0.5 + 0.5 * Math.sin(f / 4)} />
        <circle cx={x} cy={y} r={r} fill={BONE} /></g>; };
    side = <><div style={{ position: 'absolute', left: 120, top: 150, fontFamily: FONT.mono, fontSize: 28, letterSpacing: 4, color: MUTED }}>RATED 1 OR HIGHER · CENTRE OF THE DECADE</div>
      <div style={{ position: 'absolute', left: 112, top: 192, ...DISP(190, 62, 860), color: BONE, textShadow: SHADOW }}>{decs[Math.round(pos)]}s</div>
      {P.note ? <Mono text={P.note} f0={Math.round(d * 0.75)} size={30} color={ACCENT_EP} style={{ position: 'absolute', left: 124, top: 400 }} /> : null}</>;
  } else if (mode === 'regions') {
    const a: number[] = P.from, b: number[] = P.to; const q = interpolate(f, [Math.round(d * 0.35), Math.round(d * 0.8)], [0, 1], { ...C, easing: io });
    const fi = interpolate(f, [6, 26], [0, 1], C);
    layers = [{ id: 'f1p-all', filter: (t) => t[1] >= 1, color: TINT, alpha: 0.18, width: widthBy, opacity: 0.6 }];
    fills = [{ names: SE, fill: ACCENT_EP, opacity: 0.42 * fi }, { names: PL, fill: TINT, opacity: 0.3 * fi }];
    side = <><div style={{ position: 'absolute', left: 120, top: 140, fontFamily: FONT.mono, fontSize: 28, letterSpacing: 4, color: MUTED }}>{P.label ?? 'SHARE OF TORNADOES RATED 1+'}</div>
      <div style={{ position: 'absolute', left: 120, top: 180, fontFamily: FONT.mono, fontSize: 40, color: BONE }}>{q < 0.5 ? P.years?.[0] ?? '1950s' : P.years?.[1] ?? '2020s'}</div>
      {[['SOUTHEAST', 0, ACCENT_EP], ['PLAINS', 1, BONE]].map(([n, i, col]: any) => <div key={n} style={{ position: 'absolute', left: 116, top: 250 + i * 190 }}>
        <div style={{ ...DISP(150, 62, 860), color: col, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW, lineHeight: 1 }}>{Math.round(lerp(a[i], b[i], q))}%</div>
        <div style={{ fontFamily: FONT.mono, fontSize: 24, letterSpacing: 4, color: MUTED, marginTop: 4 }}>{n}</div></div>)}</>;
  } else if (mode === 'place') {
    const [yy, mo, dy] = P.date as number[]; const pl = data.geo.places[P.place];
    const on = interpolate(f, [10, 30], [0, 1], C);
    layers = [{ id: 'dim-all', filter: () => true, color: TINT, alpha: 0.2, width: widthBy, opacity: 0.9 },
      { id: `day-${yy}-${mo}-${dy}`, filter: (t) => t[0] === yy && t[7] === mo && t[9] === dy, color: ACCENT_EP, alpha: 1, width: (t) => (t[1] >= 3 ? 6 : 3.5), opacity: on }];
    overlay = (k) => { const pin = interpolate(f, [16, 30], [0, 1], { ...C, easing: out }); return pl ? <g opacity={pin}>
      <circle cx={pl[0]} cy={pl[1]} r={(10 + 30 * (1 - pin)) / z} fill="none" stroke={ACCENT_EP} strokeWidth={3 / z} />
      <circle cx={pl[0]} cy={pl[1]} r={4 / z} fill={BONE} /></g> : null; };
    side = <><Rise text={P.label} f0={14} x={120} y={150} size={96} accent={P.accent} />
      {P.sub ? <Mono text={P.sub} f0={28} size={26} color={BONE} style={{ position: 'absolute', left: 124, top: 262 }} /> : null}</>;
  }
  return <SceneBg drift={0.15}>
    <AbsoluteFill>
      <div style={{ position: 'absolute', left: MX, top: MY, width: MW, height: mh, transformOrigin: `${cx * 100}% ${cy * 100}%`, transform: `scale(${z})` }}>
        <MapBase data={data} w={MW} layers={layers} fills={fills} overlay={overlay} fresh={fresh} />
      </div>
    </AbsoluteFill>
    {P.bare ? null : <AbsoluteFill style={{ background: `linear-gradient(90deg, ${rgba(GROUND, 0.75)} 0%, ${rgba(GROUND, 0)} 34%)` }} />}
    {P.bare ? null : side}
  </SceneBg>;
};

// YearBars: 73 yearly bars. mode all | split (F0 on top of F1+) | jump (F0 only, radar decade lit) | strong (F3+)
export const YearBars: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const data = useData(); const f = useCurrentFrame(); const P = s.params; const mode = P.mode ?? 'all';
  if (!data) return <SceneBg />;
  const st = data.stats; const N = st.years.length; const x0 = 200, bw = 1500 / N, base = 900;
  const max = mode === 'strong' ? 140 : 1900; const sc = (mode === 'strong' ? 480 : 560) / max;
  const grow = interpolate(f, [6, Math.max(30, d * 0.55)], [0, 1], { ...C, easing: io });
  const split = mode === 'split' ? interpolate(f, [Math.round(d * 0.45), Math.round(d * 0.45) + 24], [0, 1], { ...C, easing: io }) : 0;
  const hl: number[] = P.hl ?? [];
  const push = interpolate(f, [0, d], [1, 1.04], C);
  return <SceneBg drift={0.2} style={{ transform: `scale(${push})` }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {[0, 500, 1000, 1500].filter((v) => v <= max).concat(mode === 'strong' ? [50, 100] : []).filter((v) => mode !== 'strong' || v <= 100).map((v) => <g key={v}><line x1={x0} x2={x0 + 1500} y1={base - v * sc} y2={base - v * sc} stroke={rgba(TINT, 0.16)} strokeWidth={1.5} />
        <text x={x0 - 18} y={base - v * sc + 8} textAnchor="end" fontFamily={FONT.mono} fontSize={22} fill={MUTED}>{v}</text></g>)}
      {st.years.map((y, i) => { const vis = Math.max(0, Math.min(1, grow * N - i)); if (vis <= 0) return null;
        const inHl = hl.length === 2 && y >= hl[0] && y <= hl[1];
        const x = x0 + i * bw + 2; const w = bw - 4;
        if (mode === 'strong') { const v = st.f3p[i] * vis; return <rect key={y} x={x} y={base - v * sc} width={w} height={v * sc} fill={ACCENT_EP} opacity={0.9} />; }
        if (mode === 'jump') { const v = st.f0[i] * vis; return <rect key={y} x={x} y={base - v * sc} width={w} height={v * sc} fill={inHl ? ACCENT_EP : rgba(TINT, 0.55)} />; }
        const lo = st.f1p[i] * vis, hi = st.f0[i] * vis; const unk = (st.all[i] - st.f0[i] - st.f1p[i]) * vis;
        return <g key={y}>
          <rect x={x} y={base - lo * sc} width={w} height={lo * sc} fill={split ? rgba(TINT, 0.45 + 0.2 * (1 - split)) : BONE} opacity={0.92} />
          <rect x={x} y={base - (lo + hi + Math.max(0, unk)) * sc} width={w} height={(hi + Math.max(0, unk)) * sc} fill={split ? ACCENT_EP : BONE} opacity={split ? 0.6 + 0.4 * split : 0.92} />
        </g>; })}
      {[1950, 1970, 1990, 2010, 2022].map((y) => <text key={y} x={x0 + (y - 1950) * bw + bw / 2} y={base + 40} textAnchor="middle" fontFamily={FONT.mono} fontSize={24} fill={MUTED}>{y}</text>)}
      {hl.length === 2 && mode === 'jump' ? <g opacity={interpolate(f, [d * 0.5, d * 0.5 + 12], [0, 1], C)}>
        <line x1={x0 + (hl[0] - 1950) * bw} x2={x0 + (hl[1] - 1950 + 1) * bw} y1={base + 70} y2={base + 70} stroke={ACCENT_EP} strokeWidth={4} />
        <text x={x0 + (hl[0] - 1950) * bw} y={base + 110} fontFamily={FONT.mono} fontSize={24} letterSpacing={3} fill={ACCENT_EP}>{P.hlLabel ?? ''}</text></g> : null}
    </svg>
    <Rise text={P.label} f0={8} x={200} y={130} size={84} accent={P.accent} />
    {mode === 'split' ? <div style={{ position: 'absolute', left: 204, top: 240, display: 'flex', gap: 50, opacity: split }}>
      <Mono text="■ RATED 0, THE WEAKEST" f0={Math.round(d * 0.45)} size={26} color={ACCENT_EP} />
      <Mono text="■ RATED 1 AND ABOVE" f0={Math.round(d * 0.45) + 8} size={26} color={BONE} /></div> : null}
    {P.sub ? <Mono text={P.sub} f0={20} size={26} color={BONE} style={{ position: 'absolute', left: 204, top: 240 }} /> : null}
  </SceneBg>;
};

// DayStrips: one cell per day of the year, height = tornadoes rated 1+ that day; the ten busiest days lit.
export const DayStrips: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const data = useData(); const f = useCurrentFrame(); const P = s.params; if (!data) return <SceneBg />;
  const rows: string[] = P.rows ?? ['1975', '2022']; const labels: string[] = P.labels ?? rows; const notes: string[] = P.notes ?? [];
  const x0 = 200, cw = 1500 / 366; const rh = rows.length === 1 ? 520 : 250; const maxv = P.max ?? 64;
  return <SceneBg drift={0.2} style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {rows.map((r, ri) => { const arr = data.days[r]; const top10 = [...arr].sort((a, b) => b - a)[9]; const base = (rows.length === 1 ? 860 : 520 + ri * 330);
        const sweep = interpolate(f, [6 + ri * 10, Math.min(d - 20, 70) + ri * 10], [0, 366], { ...C, easing: io }); const lit = interpolate(f, [Math.min(d - 20, 70) + ri * 10, Math.min(d - 20, 70) + ri * 10 + 16], [0, 1], C);
        return <g key={r}>
          <line x1={x0} x2={x0 + 1500} y1={base} y2={base} stroke={rgba(TINT, 0.35)} strokeWidth={1.5} />
          {arr.map((v, i) => { if (i > sweep || !v) return null; const h = Math.min(rh, (v / maxv) * rh); const big = v >= top10 && v > 0;
            return <rect key={i} x={x0 + i * cw} y={base - h} width={Math.max(1.6, cw - 0.8)} height={h} fill={big ? (lit ? ACCENT_EP : BONE) : rgba(TINT, 0.6)} opacity={big ? 0.6 + 0.4 * lit : 0.85} />; })}
          {(P.months ?? true) ? ['JAN', 'APR', 'JUL', 'OCT'].map((m, i) => <text key={m} x={x0 + [0, 90, 181, 273][i] * cw} y={base + 30} fontFamily={FONT.mono} fontSize={20} fill={MUTED}>{m}</text>) : null}
          <text x={x0} y={base - rh - 20 + (rows.length === 1 ? 0 : 0)} fontFamily={FONT.mono} fontSize={30} letterSpacing={3} fill={BONE}>{labels[ri]}</text>
          {notes[ri] ? <text x={x0 + 1500} y={base - rh - 20} textAnchor="end" fontFamily={FONT.mono} fontSize={30} letterSpacing={3} fill={ACCENT_EP} opacity={lit}>{notes[ri]}</text> : null}
        </g>; })}
    </svg>
    <Rise text={P.label} f0={8} x={200} y={100} size={80} accent={P.accent} />
  </SceneBg>;
};

// DamageRuler: the 0-5 rating as damage, not wind. mode scale | elreno (measured wind runs off the ruler, rating stays 3)
const DMG = ['BRANCHES, SIGNS', 'ROOF SURFACES PEELED', 'ROOFS TORN OFF', 'WALLS DOWN', 'HOUSES LEVELLED', 'HOUSE SWEPT AWAY'];
const WIND = [65, 86, 111, 136, 166, 200];
export const DamageRuler: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const P = s.params; const mode = P.mode ?? 'scale';
  const x0 = 200, gap = 255, base = 760;
  const needle = mode === 'elreno' ? interpolate(f, [Math.round(d * 0.25), Math.round(d * 0.6)], [0, 295], { ...C, easing: io }) : 0;
  const nx = (mph: number) => x0 + (mph < 65 ? mph / 65 * 0 : mph >= 200 ? 5 * gap + (mph - 200) * 2.4 : (() => { let i = 0; while (i < 5 && mph >= WIND[i + 1]) i++; return i * gap + (mph - WIND[i]) / (WIND[i + 1] - WIND[i]) * gap; })());
  const hlR = mode === 'elreno' ? 3 : P.hl ?? -1;
  return <SceneBg drift={0.2} style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})` }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <line x1={x0 - 40} x2={x0 + 5 * gap + 300} y1={base} y2={base} stroke={rgba(TINT, 0.5)} strokeWidth={2} />
      {DMG.map((t, i) => { const p = spring({ frame: f - 4 - i * 5, fps, config: { damping: 18, stiffness: 120 } }); const hl = i === hlR;
        return <g key={i} opacity={p} transform={`translate(0 ${(1 - p) * 40})`}>
          <rect x={x0 + i * gap - 4} y={base - 40 - i * 46} width={8} height={40 + i * 46} fill={hl ? ACCENT_EP : rgba(BONE, 0.75)} />
          <text x={x0 + i * gap - 18} y={base - 70 - i * 46} fontFamily={FONT.display} fontWeight={860} fontSize={hl ? 120 : 92} style={{ fontVariationSettings: "'wdth' 62" }} fill={hl ? ACCENT_EP : BONE}>{i}</text>
          <text x={x0 + i * gap - 4} y={base + 44} fontFamily={FONT.mono} fontSize={19} letterSpacing={1.5} fill={hl ? ACCENT_EP : MUTED}>{t}</text>
          {mode === 'elreno' ? <text x={x0 + i * gap - 4} y={base + 78} fontFamily={FONT.mono} fontSize={19} fill={rgba(MUTED, 0.8)}>{WIND[i]}+ MPH</text> : null}
        </g>; })}
      {mode === 'elreno' && needle > 0 ? <g>
        <line x1={x0} x2={nx(needle)} y1={base - 470} y2={base - 470} stroke={ACCENT_EP} strokeWidth={6} />
        <circle cx={nx(needle)} cy={base - 470} r={11} fill={ACCENT_EP} />
        <text x={nx(needle) - 10} y={base - 500} textAnchor="end" fontFamily={FONT.mono} fontSize={34} fill={BONE}>{Math.round(needle)} MPH MEASURED</text></g> : null}
    </svg>
    <Rise text={P.label} f0={mode === 'elreno' ? Math.round(d * 0.62) : 20} x={200} y={130} size={88} accent={P.accent} />
    {P.sub ? <Mono text={P.sub} f0={mode === 'elreno' ? Math.round(d * 0.7) : 34} size={26} color={BONE} style={{ position: 'absolute', left: 204, top: 240 }} /> : null}
  </SceneBg>;
};

// DeathShift: share of US tornado deaths by decade, Southeast vs Plains vs everyone else, bars build left to right.
export const DeathShift: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const data = useData(); const f = useCurrentFrame(); const P = s.params; if (!data) return <SceneBg />;
  const ds = data.stats.deathshare; const keys = Object.keys(ds).sort(); const x0 = 260, bw = 150, gap = 40, top = 300, H = 560;
  return <SceneBg drift={0.2} style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {keys.map((k, i) => { const p = interpolate(f, [8 + i * 6, 26 + i * 6], [0, 1], { ...C, easing: out }); const [se, pl] = ds[k]; const x = x0 + i * (bw + gap);
        const hse = (se / 100) * H * p, hpl = (pl / 100) * H * p, hrest = ((100 - se - pl) / 100) * H * p; const last = i === keys.length - 1;
        return <g key={k}>
          <rect x={x} y={top + H - hse} width={bw} height={hse} fill={ACCENT_EP} opacity={0.92} />
          <rect x={x} y={top + H - hse - hrest} width={bw} height={hrest} fill={rgba(TINT, 0.22)} />
          <rect x={x} y={top + H - hse - hrest - hpl} width={bw} height={hpl} fill={rgba(BONE, 0.85)} />
          <text x={x + bw / 2} y={top + H + 40} textAnchor="middle" fontFamily={FONT.mono} fontSize={24} fill={MUTED}>{k === '2020' ? '2020-22' : k + 's'}</text>
          {p > 0.9 && (i === 0 || i === keys.length - 2 || last) ? <text x={x + bw / 2} y={top + H - hse + 50} textAnchor="middle" fontFamily={FONT.display} fontWeight={860} fontSize={56} style={{ fontVariationSettings: "'wdth' 62" }} fill={GROUND}>{se}%</text> : null}
        </g>; })}
    </svg>
    <Rise text={P.label} f0={8} x={260} y={120} size={84} accent={P.accent} />
    <div style={{ position: 'absolute', left: 264, top: 222, display: 'flex', gap: 46 }}>
      <Mono text="■ SOUTHEAST" f0={20} size={24} color={ACCENT_EP} /><Mono text="■ PLAINS: TX OK KS NE" f0={26} size={24} color={BONE} /><Mono text="■ REST OF US" f0={32} size={24} color={TINT} /></div>
    <Hairline x={260} y={top + H} w={8 * (bw + gap) - gap} f0={6} />
  </SceneBg>;
};

// RadarSweep: a Doppler PPI scope: the beam sweeps, a hook echo and a rotation couplet appear (illustration of what radar sees).
export const RadarSweep: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params; const cx = 1180, cy = 560, R = 420; const ang = (f * 4) % 360;
  const found = interpolate(f, [Math.round(d * 0.45), Math.round(d * 0.45) + 12], [0, 1], C);
  const echo = Array.from({ length: 140 }, (_, i) => { const t = i / 140; const a = -0.4 + t * 2.6; const r = 150 + 90 * t + 30 * Math.sin(i * 1.7); return [cx + 140 + Math.cos(a) * r * 0.55 - 40, cy - 60 + Math.sin(a) * r * 0.5, 10 + 14 * Math.abs(Math.sin(i * 2.3))]; });
  return <SceneBg drift={0.2} style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})` }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {[1, 2, 3, 4].map((k) => <circle key={k} cx={cx} cy={cy} r={(R * k) / 4} fill="none" stroke={rgba(TINT, 0.25)} strokeWidth={1.5} />)}
      <line x1={cx - R} x2={cx + R} y1={cy} y2={cy} stroke={rgba(TINT, 0.18)} /><line x1={cx} x2={cx} y1={cy - R} y2={cy + R} stroke={rgba(TINT, 0.18)} />
      {echo.map(([x, y, r], i) => { const a = (Math.atan2(y - cy, x - cx) * 180) / Math.PI; const since = ((ang - a + 720) % 360); const vis = f > 8 ? Math.max(0.25, 1 - since / 360) : 0;
        return <circle key={i} cx={x} cy={y} r={r} fill={i % 3 ? ACCENT_EP : BONE} opacity={vis * 0.35} />; })}
      <path d={`M${cx} ${cy} L${cx + Math.cos((ang * Math.PI) / 180) * R} ${cy + Math.sin((ang * Math.PI) / 180) * R}`} stroke={ACCENT_EP} strokeWidth={4} opacity={0.9} />
      <g opacity={found}><circle cx={cx + 120} cy={cy + 20} r={46} fill="none" stroke={ACCENT_EP} strokeWidth={4} />
        <path d={`M${cx + 96} ${cy + 20} a24 24 0 0 1 48 0`} fill="none" stroke={BONE} strokeWidth={4} /><path d={`M${cx + 144} ${cy + 20} a24 24 0 0 1 -48 0`} fill="none" stroke={ACCENT_EP} strokeWidth={4} />
        <text x={cx + 190} y={cy + 30} fontFamily={FONT.mono} fontSize={26} letterSpacing={3} fill={BONE}>ROTATION</text></g>
    </svg>
    <Rise text={P.label} f0={10} x={140} y={150} size={92} accent={P.accent} />
    {P.sub ? <Mono text={P.sub} f0={26} size={26} color={BONE} style={{ position: 'absolute', left: 144, top: 262 }} /> : null}
    <Mono text="SCHEMATIC, NOT A REAL SCAN" f0={30} size={20} color={MUTED} style={{ position: 'absolute', left: 144, top: 960 }} />
  </SceneBg>;
};
