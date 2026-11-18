// Geography: land loader, route maths, a lit 3D globe that follows a subject, and a flat close-up map.
// Data: world-atlas TopoJSON copied to public/ (countries-110m.json for globes, countries-50m.json for close-ups).
// Online tiles (MapLibre etc.) are blocked in our cloud — always use d3-geo + local TopoJSON.
import React, { useEffect, useMemo, useState } from 'react';
import { AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useDelayRender, useVideoConfig } from 'remotion';
import { geoDistance, geoGraticule10, geoInterpolate, geoMercator, geoOrthographic, geoPath } from 'd3-geo';
import { feature } from 'topojson-client';
import { AMBER, BIRD, C, FONT, GROUND, GROUND2, LAND, LINE, MUTED, NAVY2, RED, ROUTE, SPRING_PIN, TINT, io, out, rgba } from './tokens';
import { Grid } from './Brand';

export type LonLat = [number, number];
export const useLand = (file: 'countries-110m.json' | 'countries-50m.json') => {
  const [land, setLand] = useState<any>(null); const { delayRender, continueRender } = useDelayRender(); const [h] = useState(() => delayRender(file));
  useEffect(() => { fetch(staticFile(file)).then((r) => r.json()).then((t) => { setLand(feature(t, t.objects.land)); continueRender(h); }); }, []);
  return land;
};

// Route helper: great-circle segments, uniform-speed position along the route (0..1), partial LineString.
export const makeRoute = (pts: LonLat[]) => {
  const seg = pts.slice(1).map((p, i) => geoDistance(pts[i], p)); const total = seg.reduce((a, b) => a + b, 0);
  const along = (f: number): LonLat => { let d = Math.max(0, Math.min(1, f)) * total; for (let i = 0; i < seg.length; i++) { if (d <= seg[i] || i === seg.length - 1) return geoInterpolate(pts[i], pts[i + 1])(Math.min(1, d / seg[i])) as LonLat; d -= seg[i]; } return pts[pts.length - 1]; };
  const upTo = (f: number, f0 = 0) => { const c: LonLat[] = []; for (let k = 0; k <= 160; k++) c.push(along(f0 + ((f - f0) * k) / 160)); return { type: 'LineString', coordinates: c } as any; };
  return { pts, along, upTo, km: total * 6371 };
};

// Glowing route stroke (RED glow + bright core). Use inside an <svg> that defines no filter — it brings its own.
export const RoutePath: React.FC<{ d: string; width?: number; id?: string }> = ({ d, width = 3.5, id = 'rg' }) => (
  <g><defs><filter id={id} x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
    <path d={d} fill="none" stroke={RED} strokeWidth={width * 2.6} strokeLinecap="round" opacity={0.25} filter={`url(#${id})`} />
    <path d={d} fill="none" stroke={ROUTE} strokeWidth={width} strokeLinecap="round" /></g>
);

// The lit globe. Camera centre and zoom are props, so the scene drives them (follow a subject, orbit, push in).
// overlay(proj, visible) draws anything on top (pins, wind, labels) in the same projection.
export const Globe: React.FC<{ land: any; center: LonLat; scale: number; cx?: number; cy?: number; route?: { d: any }; overlay?: (proj: any, vis: (c: LonLat) => boolean) => React.ReactNode; underlay?: (proj: any, vis: (c: LonLat) => boolean) => React.ReactNode }> = ({ land, center, scale, cx = 760, cy = 560, route, overlay, underlay }) => {
  const { width, height } = useVideoConfig();
  const proj = geoOrthographic().scale(scale).translate([cx, cy]).rotate([-center[0], -center[1], 0]).clipAngle(90).precision(0.3);
  const path = geoPath(proj); const grat = useMemo(() => geoGraticule10(), []);
  const vis = (c: LonLat) => geoDistance(c, center) < Math.PI / 2 - 0.05;
  return (
    <svg width={width} height={height} style={{ position: 'absolute' }}>
      <defs>
        <radialGradient id="ps-sea" cx="38%" cy="32%" r="80%"><stop offset="0%" stopColor={GROUND2} /><stop offset="60%" stopColor={GROUND2} stopOpacity={0.85} /><stop offset="100%" stopColor={GROUND} /></radialGradient>
        <radialGradient id="ps-atmo" cx="50%" cy="50%" r="50%"><stop offset="84%" stopColor={rgba(TINT, 0)} /><stop offset="87.5%" stopColor={rgba(TINT, 0.22)} /><stop offset="100%" stopColor={rgba(TINT, 0)} /></radialGradient>
        <radialGradient id="ps-shade" cx="35%" cy="30%" r="85%"><stop offset="55%" stopColor="rgba(0,0,0,0)" /><stop offset="100%" stopColor={rgba(GROUND, 0.55)} /></radialGradient>
      </defs>
      <circle cx={cx} cy={cy} r={scale * 1.14} fill="url(#ps-atmo)" />
      <path d={path({ type: 'Sphere' } as any) || ''} fill="url(#ps-sea)" />
      <path d={path(grat) || ''} fill="none" stroke={rgba(TINT, 0.13)} strokeWidth={1} />
      {underlay ? underlay(proj, vis) : null}
      <path d={path(land) || ''} fill={LAND} stroke={LINE} strokeWidth={1.4} />
      <path d={path({ type: 'Sphere' } as any) || ''} fill="url(#ps-shade)" />
      {route ? <RoutePath d={path(route.d) || ''} id="ps-rg-globe" /> : null}
      {overlay ? overlay(proj, vis) : null}
    </svg>
  );
};

// Subject marker: glowing dot or the amber bird glyph heading along `angle` (deg). flap = sin(frame*0.9).
export const Subject: React.FC<{ x: number; y: number; angle?: number; kind?: 'dot' | 'bird'; flap?: number }> = ({ x, y, angle = 0, kind = 'dot', flap = 0 }) => (
  <g transform={`translate(${x} ${y}) rotate(${angle})`}><circle r={30} fill="rgba(255,226,160,0.14)" />
    {kind === 'dot' ? <circle r={10} fill={BIRD} /> : <>
      <path d="M16 0 L34 1.5 L16 3 C8 5 -6 5 -16 2 L-26 6 L-22 0 L-26 -6 L-16 -2 C-6 -5 8 -5 16 0 Z" fill={BIRD} />
      <path d={`M4 -2 L-8 ${-20 - 8 * flap} L-14 ${-18 - 8 * flap} L-6 -2 Z M4 2 L-8 ${20 + 8 * flap} L-14 ${18 + 8 * flap} L-6 2 Z`} fill={AMBER} /></>}
  </g>
);
// Stop/day marker on a route.
export const Waypoint: React.FC<{ x: number; y: number }> = ({ x, y }) => <circle cx={x} cy={y} r={6} fill={NAVY2} stroke={AMBER} strokeWidth={2.5} />;
// Place label (mono, muted). Use for countries/regions; Oswald 46 for THE place of the story.
export const PlaceLabel: React.FC<{ x: number; y: number; text: string; anchor?: 'start' | 'middle' | 'end' }> = ({ x, y, text, anchor = 'middle' }) => <text x={x} y={y} fontFamily={FONT.mono} fontSize={20} letterSpacing={3} fill={MUTED} textAnchor={anchor}>{text}</text>;
// Spring pin with a ripple. f0 = frame it drops.
export const Pin: React.FC<{ x: number; y: number; f0: number }> = ({ x, y, f0 }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const p = spring({ frame: f - f0, fps, config: SPRING_PIN });
  if (f < f0) return null;
  return <g transform={`translate(${x} ${y})`}><g transform={`scale(${p})`}><circle r={12} fill={AMBER} /><circle r={30} fill="none" stroke={AMBER} strokeWidth={2} opacity={1 - Math.min(1, (f - f0) / 30)} /></g></g>;
};
// Hand-drawn amber circle + leader line around a point (draws over [f0, f0+30]). dir = where the note sits.
export const CircleCallout: React.FC<{ x: number; y: number; r?: number; f0: number; dir?: [number, number] }> = ({ x, y, r = 78, f0, dir = [1, 0.6] }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [f0, f0 + 30], [0, 1], { ...C, easing: io });
  const n = Math.hypot(dir[0], dir[1]); const ux = dir[0] / n, uy = dir[1] / n;
  return <g><circle cx={x} cy={y} r={r} fill="none" stroke={AMBER} strokeWidth={4} strokeDasharray={`${2 * Math.PI * r * p} 2000`} transform={`rotate(-110 ${x} ${y})`} />
    <line x1={x + ux * r} y1={y + uy * r} x2={x + ux * (r + 95 * p)} y2={y + uy * (r + 95 * p)} stroke={AMBER} strokeWidth={3} /></g>;
};

// Flat close-up map scene shell: Mercator, punch-in on entry, slow push. Children get the projection.
export const FlatMap: React.FC<{ land: any; center: LonLat; scale: number; push?: number; dur?: number; children?: (proj: any, path: any) => React.ReactNode }> = ({ land, center, scale, push = 0.08, dur = 240, children }) => {
  const f = useCurrentFrame(); const { width, height } = useVideoConfig();
  const zoom = interpolate(f, [0, dur], [1, 1 + push], { ...C, easing: io });
  const proj = geoMercator().center(center).scale(scale * zoom).translate([width / 2 - 60, height / 2 - 20]);
  const path = geoPath(proj);
  const punch = 1.25 - 0.25 * interpolate(f, [0, 30], [0, 1], { ...C, easing: out });
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, ${GROUND2} 0%, ${GROUND} 80%)` }}>
      <Grid opacity={0.8} shift={f * 0.2} />
      <AbsoluteFill style={{ transform: `scale(${punch})`, transformOrigin: `${width / 2 - 60}px ${height / 2 - 20}px` }}>
        <svg width={width} height={height} style={{ position: 'absolute' }}><path d={path(land) || ''} fill={LAND} stroke={LINE} strokeWidth={1.6} /></svg>
        {children ? children(proj, path) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
