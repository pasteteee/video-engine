// Scenes made for the Hunga Tonga episode (shot list: scene_type "custom", custom.component).
import React from 'react';
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from 'remotion';
import { geoCircle, geoMercator, geoPath } from 'd3-geo';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, MUTED, PAPER, SHADOW, TINT, io, out, rgba } from '../kit/tokens';
import { Mono } from '../kit/Type';
import { SceneBg } from '../kit/Brand';
import { Globe, Pin } from '../kit/Geo';
import { D, Plot, hhmm } from '../Episode';

const TONGA: [number, number] = [-175.39, -20.55];
const FRAMES: number[] = (() => { const a: number[] = []; for (let m = 290; m <= 750; m += 10) a.push(m); return a; })();
const ringSrc = (m: number) => staticFile(`ep/goes/ringT_${hhmm(m).replace(':', '')}.jpg`);

// GOES-17 difference frames play as a sequence on the right; clock, distance and our distance-time points on the left.
export const RingTracker: React.FC<{ s: any; d: number }> = ({ d }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [4, d - 10], [0, 1], { ...C, easing: io });
  const t = 290 + (750 - 290) * p; const k = Math.min(FRAMES.length - 1, Math.floor((t - 290) / 10)); const [a, b] = D.fit;
  const km = Math.max(0, a + b * t);
  return <SceneBg drift={0.2}>
    <div style={{ position: 'absolute', left: 900, top: 40, width: 1000, height: 1000, overflow: 'hidden', borderRadius: '50%' }}>
      <Img src={ringSrc(FRAMES[k])} style={{ width: 1000, height: 1000, transform: `scale(${1.02 + 0.05 * p})` }} />
    </div>
    <Mono text="GOES-17 · BAND 10 · DIFFERENCE" f0={2} size={22} color={MUTED} style={{ position: 'absolute', left: 120, top: 150 }} />
    <div style={{ position: 'absolute', left: 110, top: 190, fontFamily: FONT.mono, fontWeight: 500, fontSize: 150, color: BONE, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>{hhmm(FRAMES[k])}<span style={{ fontSize: 50, color: MUTED, marginLeft: 16 }}>UTC</span></div>
    <div style={{ position: 'absolute', left: 120, top: 380, ...DISP(96), color: ACCENT_EP, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>{(Math.round(km / 25) * 25).toLocaleString('en-US')} KM</div>
    <Mono text="FRONT FROM THE VOLCANO" f0={8} size={20} color={MUTED} style={{ position: 'absolute', left: 124, top: 480 }} />
    <div style={{ position: 'absolute', left: 0, top: 0, width: 900, height: 1080 }}>
      <svg width={900} height={1080} style={{ position: 'absolute' }}>
        {(() => { const x0 = 130, y0 = 560, w = 620, h = 330; const X = (m: number) => x0 + ((m - 290) / 460) * w, Y = (v: number) => y0 + h - (v / 8500) * h;
          return <g><line x1={x0} y1={y0 + h} x2={x0 + w} y2={y0 + h} stroke={rgba(TINT, 0.6)} strokeWidth={2} /><line x1={x0} y1={y0} x2={x0} y2={y0 + h} stroke={rgba(TINT, 0.6)} strokeWidth={2} />
            <text x={x0} y={y0 + h + 36} fontFamily={FONT.mono} fontSize={18} fill={MUTED}>04:50</text><text x={x0 + w} y={y0 + h + 36} textAnchor="end" fontFamily={FONT.mono} fontSize={18} fill={MUTED}>12:30</text>
            <text x={x0 + 10} y={y0 + 20} fontFamily={FONT.mono} fontSize={18} fill={MUTED}>8,500 KM</text>
            {(D.front as [number, number][]).filter((q) => q[0] <= t).map((q, i) => <circle key={i} cx={X(q[0])} cy={Y(q[1])} r={5} fill={BONE} />)}</g>; })()}
      </svg>
    </div>
  </SceneBg>;
};

// Pen recorder: Sydney Airport QNH (NOAA ISD, METAR + SPECI) 06:00-09:00 UTC; our prediction 07:29 as a dashed line.
export const SydneyLog: React.FC<{ s: any; d: number }> = ({ d }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [4, d - 16], [0, 1], { ...C, easing: io });
  const pts: [number, number, string][] = (D.isd as [number, number, string][]).filter((q) => q[0] >= 360 && q[0] <= 540);
  const t = 360 + 180 * p; const x0 = 140, w = 1640, X = (m: number) => x0 + ((m - 360) / 180) * w, Y = (v: number) => 640 - (v - 1001) * 90;
  // step trace: pressure holds until the next report
  const path: string[] = []; pts.forEach((q, i) => { if (q[0] > t) return; const nx = Math.min(t, pts[i + 1]?.[0] ?? t); path.push(`${i ? 'L' : 'M'}${X(q[0])} ${Y(q[1])} L${X(nx)} ${Y(q[1])}`); });
  const pen = pts.filter((q) => q[0] <= t).slice(-1)[0];
  return <AbsoluteFill style={{ background: PAPER }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      {Array.from({ length: 19 }, (_, i) => <line key={i} x1={X(360 + i * 10)} y1={240} x2={X(360 + i * 10)} y2={860} stroke={i % 3 ? 'rgba(80,70,90,0.12)' : 'rgba(80,70,90,0.3)'} strokeWidth={i % 3 ? 1 : 2} />)}
      {[1001, 1002, 1003, 1004, 1005].map((v) => <g key={v}><line x1={x0} y1={Y(v)} x2={x0 + w} y2={Y(v)} stroke="rgba(80,70,90,0.2)" /><text x={x0 - 14} y={Y(v) + 8} textAnchor="end" fontFamily={FONT.mono} fontSize={22} fill="#5a5560">{v}</text></g>)}
      {[360, 420, 480, 540].map((m) => <text key={m} x={X(m)} y={900} textAnchor="middle" fontFamily={FONT.mono} fontSize={22} fill="#5a5560">{hhmm(m)}</text>)}
      <line x1={X(449)} y1={240} x2={X(449)} y2={860} stroke="#8a6d00" strokeWidth={3} strokeDasharray="12 8" opacity={t > 430 ? 1 : 0} />
      <text x={X(449) - 12} y={270} textAnchor="end" fontFamily={FONT.mono} fontSize={22} letterSpacing={2} fill="#6b5500" opacity={t > 430 ? 1 : 0}>OUR PREDICTION 07:29</text>
      <path d={path.join(' ')} fill="none" stroke="#2a2433" strokeWidth={4} />
      {pts.filter((q) => q[0] <= t && q[2] === 'SPECI').map((q, i) => <g key={i}><circle cx={X(q[0])} cy={Y(q[1])} r={13} fill="none" stroke="#8a6d00" strokeWidth={4} />
        <text x={X(q[0]) + 20} y={Y(q[1]) - 18} fontFamily={FONT.mono} fontSize={22} fill="#2a2433">SPECI {hhmm(q[0])} · {q[1].toFixed(1)}</text></g>)}
      {pen ? <circle cx={X(t)} cy={Y(pen[1])} r={7} fill="#2a2433" /> : null}
    </svg>
    <div style={{ position: 'absolute', left: 140, top: 110, ...DISP(84), color: '#2a2433' }}>SYDNEY AIRPORT · QNH</div>
    <Mono text="NOAA NCEI ISD · 15 JAN 2022 · UTC" f0={4} size={22} color="#5a5560" style={{ position: 'absolute', left: 144, top: 196, textShadow: 'none' }} />
  </AbsoluteFill>;
};

// Night globe: the pressure ring grows from Tonga, closes at the antipode (~18 h), comes back; passes counted over six days.
export const RingGlobe: React.FC<{ s: any; d: number; land: any }> = ({ d, land }) => {
  const f = useCurrentFrame(); const lap = interpolate(f, [6, d * 0.62], [0, 1], { ...C, easing: io });
  const hours = lap * 36; const ang = hours <= 18 ? (hours / 18) * 180 : 360 - (hours / 18) * 180;
  const anti: [number, number] = [TONGA[0] + 180, -TONGA[1]];
  const cam: [number, number] = [TONGA[0] + 180 * Math.min(1, hours / 18) * 0.85 + (hours > 18 ? -(hours - 18) / 18 * 120 : 0), TONGA[1] + (anti[1] - TONGA[1]) * Math.min(1, hours / 18) * 0.85];
  const passes = Math.min(7, Math.floor(interpolate(f, [d * 0.6, d - 12], [1, 7.99], C)));
  const day = interpolate(f, [d * 0.6, d - 12], [1.5, 6], C);
  return <SceneBg at="62% 50%" drift={-0.3}>
    <Globe land={land} center={cam} scale={420} cx={1200} cy={560} overlay={(proj) => {
      const ring = geoCircle().center(TONGA).radius(Math.max(0.5, Math.min(179.5, ang)))(); const pth = geoPath(proj)(ring as any) || '';
      const a = proj(anti), tg = proj(TONGA);
      return <><path d={pth} fill="none" stroke={ACCENT_EP} strokeWidth={6} style={{ filter: `drop-shadow(0 0 10px ${rgba(ACCENT_EP, 0.7)})` }} />
        {tg ? <g><circle cx={tg[0]} cy={tg[1]} r={9} fill={BONE} /><text x={tg[0] + 18} y={tg[1] + 8} fontFamily={FONT.mono} fontSize={22} fill={BONE}>TONGA</text></g> : null}
        {a && hours > 14 ? <g><circle cx={a[0]} cy={a[1]} r={9} fill={ACCENT_EP} /><text x={a[0] + 18} y={a[1] + 8} fontFamily={FONT.mono} fontSize={22} fill={ACCENT_EP}>FAR SIDE · SAHARA</text></g> : null}</>; }} />
    <Mono text="HOURS AFTER THE BLAST" f0={4} size={22} color={MUTED} style={{ position: 'absolute', left: 120, top: 240 }} />
    <div style={{ position: 'absolute', left: 110, top: 280, ...DISP(220), color: BONE, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>{lap < 1 ? Math.round(hours) : Math.round(day * 24)}<span style={{ fontSize: 90, color: MUTED, marginLeft: 16 }}>H</span></div>
    <Mono text="PASSES RECORDED" f0={Math.round(d * 0.55)} size={22} color={MUTED} style={{ position: 'absolute', left: 120, top: 600 }} />
    <div style={{ position: 'absolute', left: 116, top: 640, display: 'flex', gap: 18, opacity: interpolate(f, [d * 0.55, d * 0.6], [0, 1], C) }}>
      {Array.from({ length: 7 }, (_, i) => <div key={i} style={{ width: 52, height: 90, background: i < passes ? ACCENT_EP : rgba(TINT, 0.18) }} />)}</div>
    <Mono text="4 ONE WAY · 3 THE OTHER · OVER 6 DAYS" f0={Math.round(d * 0.7)} size={22} color={BONE} style={{ position: 'absolute', left: 120, top: 770 }} />
  </SceneBg>;
};

// Two fronts leave Tonga together: the air wave (310 m/s) and a free tsunami (200 m/s). The air reaches Amami first.
export const AirVsSea: React.FC<{ s: any; d: number; land50: any }> = ({ d, land50 }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [6, d - 20], [0, 1], { ...C, easing: (x) => x });
  const hrs = 7.4 * p; const air = (310 * 3.6 * hrs) / 111.2, sea = (200 * 3.6 * hrs) / 111.2; // degrees
  const proj = geoMercator().rotate([-163, 0]).center([0, 4]).scale(520).translate([1000, 560]); const path = geoPath(proj);
  const amami: [number, number] = [129.5, 28.4]; const am = proj(amami)!, tg = proj(TONGA)!;
  const hit = hrs >= 7.17; const jst = 13 * 60 + 15 + hrs * 60;
  return <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, ${rgba(TINT, 0.12)} 0%, ${GROUND} 80%)` }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <path d={path(land50) || ''} fill={rgba(TINT, 0.22)} stroke={rgba(TINT, 0.55)} strokeWidth={1.2} />
      <path d={path(geoCircle().center(TONGA).radius(Math.max(0.2, sea))() as any) || ''} fill={rgba(TINT, 0.08)} stroke={TINT} strokeWidth={4} strokeDasharray="14 10" />
      <path d={path(geoCircle().center(TONGA).radius(Math.max(0.2, air))() as any) || ''} fill="none" stroke={ACCENT_EP} strokeWidth={6} />
      <circle cx={tg[0]} cy={tg[1]} r={10} fill={BONE} /><text x={tg[0] + 18} y={tg[1] + 36} fontFamily={FONT.mono} fontSize={24} fill={BONE}>TONGA</text>
      <Pin x={am[0]} y={am[1]} f0={10} /><text x={am[0] - 20} y={am[1] - 26} textAnchor="end" fontFamily={FONT.mono} fontSize={24} fill={BONE}>AMAMI</text>
    </svg>
    <div style={{ position: 'absolute', left: 90, top: 120, fontFamily: FONT.mono, fontWeight: 500, fontSize: 110, color: BONE, textShadow: SHADOW, fontVariantNumeric: 'tabular-nums' }}>{hhmm(jst)}<span style={{ fontSize: 40, color: MUTED, marginLeft: 14 }}>JST</span></div>
    <div style={{ position: 'absolute', left: 96, top: 260, fontFamily: FONT.mono, fontSize: 24, letterSpacing: 3, color: ACCENT_EP }}>━━ AIR WAVE · 310 M/S</div>
    <div style={{ position: 'absolute', left: 96, top: 300, fontFamily: FONT.mono, fontSize: 24, letterSpacing: 3, color: TINT }}>╌╌ TSUNAMI · ~200 M/S</div>
    <div style={{ position: 'absolute', left: 90, top: 860, ...DISP(130), color: ACCENT_EP, textShadow: SHADOW, opacity: hit ? interpolate(f, [d - 20, d - 10], [0, 1], { ...C, easing: out }) : 0 }}>HOURS AHEAD</div>
  </AbsoluteFill>;
};

// ---- vertical (9:16) versions for the Shorts ----
const VBg: React.FC<{ children?: React.ReactNode }> = ({ children }) => <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 38%, ${rgba(TINT, 0.14)} 0%, ${GROUND} 75%)` }}>{children}</AbsoluteFill>;
// The ring frames fill a disk at the top; UTC clock and front distance under it, left edge.
export const VRing: React.FC<{ s: any; d: number }> = ({ d }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [2, d - 4], [0, 1], { ...C, easing: io });
  const t = 290 + 460 * p; const k = Math.min(FRAMES.length - 1, Math.floor((t - 290) / 10)); const [a, b] = D.fit;
  return <VBg>
    <div style={{ position: 'absolute', left: 40, top: 260, width: 1000, height: 1000, borderRadius: '50%', overflow: 'hidden' }}><Img src={ringSrc(FRAMES[k])} style={{ width: 1000, height: 1000 }} /></div>
    <div style={{ position: 'absolute', left: 80, top: 1290, fontFamily: FONT.mono, fontWeight: 500, fontSize: 110, color: BONE, textShadow: SHADOW }}>{hhmm(FRAMES[k])}<span style={{ fontSize: 40, color: MUTED, marginLeft: 12 }}>UTC</span></div>
    <div style={{ position: 'absolute', left: 80, top: 1420, ...DISP(90), color: ACCENT_EP, textShadow: SHADOW }}>{(Math.round(Math.max(0, a + b * t) / 25) * 25).toLocaleString('en-US')} KM</div>
  </VBg>;
};
// Sydney QNH as a tall chart: time runs down the frame is unnatural, so time runs across a 920 px plot, pressure up.
export const VQnh: React.FC<{ s: any; d: number }> = ({ d }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [2, d - 8], [0, 1], { ...C, easing: io });
  const pts: [number, number, string][] = (D.isd as [number, number, string][]).filter((q) => q[0] >= 390 && q[0] <= 510);
  const t = 390 + 120 * p; const x0 = 90, w = 900, X = (m: number) => x0 + ((m - 390) / 120) * w, Y = (v: number) => 900 - (v - 1001) * 110;
  const path: string[] = []; pts.forEach((q, i) => { if (q[0] > t) return; const nx = Math.min(t, pts[i + 1]?.[0] ?? t); path.push(`${i ? 'L' : 'M'}${X(q[0])} ${Y(q[1])} L${X(nx)} ${Y(q[1])}`); });
  return <VBg>
    <div style={{ position: 'absolute', left: 80, top: 300, display: 'flex', alignItems: 'center', gap: 16 }}><div style={{ width: 36, height: 4, background: ACCENT_EP }} /><Mono text="SYDNEY AIRPORT · PRESSURE" f0={0} size={32} weight={600} color={BONE} /></div>
    <svg width={1080} height={1920} style={{ position: 'absolute' }}>
      {[1002, 1003, 1004].map((v) => <g key={v}><line x1={x0} y1={Y(v)} x2={x0 + w} y2={Y(v)} stroke={rgba(TINT, 0.2)} /><text x={x0 + w} y={Y(v) - 10} textAnchor="end" fontFamily={FONT.mono} fontSize={24} fill={MUTED}>{v} hPa</text></g>)}
      <line x1={X(449)} y1={480} x2={X(449)} y2={1100} stroke={ACCENT_EP} strokeWidth={3} strokeDasharray="12 8" />
      <text x={X(449) + 12} y={520} fontFamily={FONT.mono} fontSize={26} fill={ACCENT_EP}>PREDICTED 07:29</text>
      <path d={path.join(' ')} fill="none" stroke={BONE} strokeWidth={6} />
      {pts.filter((q) => q[0] <= t && q[2] === 'SPECI').map((q, i) => <circle key={i} cx={X(q[0])} cy={Y(q[1])} r={14} fill={ACCENT_EP} />)}
      {[420, 480].map((m) => <text key={m} x={X(m)} y={1150} textAnchor="middle" fontFamily={FONT.mono} fontSize={26} fill={MUTED}>{hhmm(m)} UTC</text>)}
    </svg>
  </VBg>;
};
