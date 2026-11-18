// Flight 1549 scenes made from the subject itself: the departure-frequency tape (AtcTape), the height budget
// (GlideBudget) and the controller's offers on a schematic map of New York (OffersMap).
import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { SceneBg } from '../kit/Brand';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, MUTED, SHADOW, SIGNAL, TINT, io, out, rgba } from '../kit/tokens';
import { Mono, Odometer, StopBlock } from '../kit/Type';
import ENV from '../ep/radio_env.json';

const FPS = 30;
type Tx = [string, string]; // [stamp · speaker, words]
// Split a clip's frames between its transmissions by the loudness envelope: each transmission starts at a burst.
const txWindows = (env: number[], txs: Tx[], d: number) => {
  const n = txs.length; const total = txs.reduce((a, t) => a + t[1].length, 0); let acc = 0;
  return txs.map((t) => { const a = acc / total; acc += t[1].length; return [Math.round(a * env.length), Math.round((acc / total) * env.length)] as [number, number]; });
};
const Wave: React.FC<{ env: number[]; f: number; x: number; y: number; w: number; h: number; color?: string; bars?: number }> = ({ env, f, x, y, w, h, color = ACCENT_EP, bars = 96 }) => {
  const max = Math.max(0.02, ...env);
  return <svg width={1920} height={1080} style={{ position: 'absolute', left: 0, top: 0 }}>
    {Array.from({ length: bars }, (_, i) => { const k = f - (bars - 1 - i); const v = k >= 0 && k < env.length ? env[k] / max : 0; const hh = 3 + v * h;
      return <rect key={i} x={x + (i * w) / bars} y={y - hh / 2} width={Math.max(2, w / bars - 4)} height={hh} fill={i === bars - 1 ? BONE : rgba(color, 0.35 + 0.65 * (i / bars))} />; })}
  </svg>;
};

// AtcTape: the real FAA recording plays; its words appear with it.
// mode 'quote' = the transmission on air in big type; 'strip' = transcript rows like the FAA pages; 'scope' = radar sweep + the line.
export const AtcTape: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params ?? {}; const txs: Tx[] = P.txs ?? []; const env: number[] = (ENV as any)[s.line_ids[0]] ?? [];
  const win = txWindows(env, txs, d); const cur = Math.max(0, win.findIndex(([a, b]) => f >= a && f < b)); const mode = P.mode ?? 'quote';
  const cam = interpolate(f, [0, d], [1, 1.05], C);
  const key = (P.key ?? 'HUDSON') as string;
  const wordsOf = (t: string) => t.split(' ');
  const isPilot = (st: string) => st.includes('1549') && !st.includes('DEPARTURE');
  if (mode === 'strip') {
    const top = 210; const row = 118;
    return <SceneBg drift={0.2} style={{ transform: `scale(${cam})` }}>
      <Mono text="FAA · N90 TRACON · DEPARTURE FREQUENCY · REAL RECORDING" f0={2} size={22} color={MUTED} style={{ position: 'absolute', left: 150, top: 130 }} />
      {txs.map(([st, t], i) => { const [a] = win[i]; const p = interpolate(f, [a, a + 8], [0, 1], { ...C, easing: out }); const on = i === cur; const n = Math.floor(interpolate(f, [a, win[i][1]], [0, t.length], C));
        return <div key={i} style={{ position: 'absolute', left: 150, top: top + i * row + (1 - p) * 30, opacity: f < a ? 0 : on ? 1 : 0.42, display: 'flex', gap: 40, width: 1500 }}>
          <div style={{ width: 300, flexShrink: 0, fontFamily: FONT.mono, fontSize: 26, letterSpacing: '0.08em', color: isPilot(st) ? ACCENT_EP : MUTED, paddingTop: 10 }}>{st}</div>
          <div style={{ ...DISP(t.length > 60 ? 50 : 60, 72, 760), textTransform: 'none', color: BONE, textShadow: SHADOW, lineHeight: 1.0 }}>{t.slice(0, n)}<span style={{ opacity: 0 }}>{t.slice(n)}</span></div></div>; })}
      <Wave env={env} f={f} x={150} y={980} w={1300} h={70} />
    </SceneBg>;
  }
  if (mode === 'scope') {
    const cx = 1380, cy = 520, R = 380; const ang = (f * 4) % 360; const lost = P.lost ? interpolate(f, [d * 0.25, d * 0.55], [1, 0], C) : 1;
    const [st, t] = txs[cur] ?? ['', '']; const [a, b] = win[cur] ?? [0, 1]; const ws = wordsOf(t); const k = Math.floor(interpolate(f, [a, b], [0, ws.length + 0.99], C));
    return <SceneBg drift={0.15}>
      <svg width={1920} height={1080} style={{ position: 'absolute' }}>
        {[1, 0.66, 0.33].map((r) => <circle key={r} cx={cx} cy={cy} r={R * r} fill="none" stroke={rgba(TINT, 0.35)} strokeWidth={2} />)}
        <line x1={cx - R} y1={cy} x2={cx + R} y2={cy} stroke={rgba(TINT, 0.2)} /><line x1={cx} y1={cy - R} x2={cx} y2={cy + R} stroke={rgba(TINT, 0.2)} />
        <defs><linearGradient id="sw" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor={rgba(ACCENT_EP, 0)} /><stop offset="1" stopColor={rgba(ACCENT_EP, 0.45)} /></linearGradient></defs>
        <path d={`M${cx} ${cy} L${cx + R * Math.cos(((ang - 28) * Math.PI) / 180)} ${cy + R * Math.sin(((ang - 28) * Math.PI) / 180)} A${R} ${R} 0 0 1 ${cx + R * Math.cos((ang * Math.PI) / 180)} ${cy + R * Math.sin((ang * Math.PI) / 180)} Z`} fill="url(#sw)" />
        <circle cx={cx - 120} cy={cy + 60} r={12} fill={ACCENT_EP} opacity={lost * (0.6 + 0.4 * Math.abs(Math.sin(f / 6)))} />
        <text x={cx - 96} y={cy + 52} fontFamily={FONT.mono} fontSize={22} fill={rgba(BONE, lost)} letterSpacing={2}>AWE1549</text>
        {P.lost ? <text x={cx - 96} y={cy + 86} fontFamily={FONT.mono} fontSize={22} fill={ACCENT_EP} opacity={1 - lost} letterSpacing={2}>NO RADAR RETURN</text> : null}
      </svg>
      <Mono text={st} f0={a + 2} size={28} color={isPilot(st) ? ACCENT_EP : MUTED} style={{ position: 'absolute', left: 150, top: 300 }} />
      <div style={{ position: 'absolute', left: 140, top: 360, width: 860, ...DISP(84, 70, 800), textTransform: 'none', lineHeight: 1.02, textShadow: SHADOW }}>
        {ws.map((w, i) => <span key={i} style={{ color: BONE, opacity: i < k ? 1 : 0.0 }}>{w} </span>)}</div>
      <Wave env={env} f={f} x={150} y={900} w={760} h={60} bars={60} />
    </SceneBg>;
  }
  // quote: the transmission on the air, word by word, large
  const [st, t] = txs[cur] ?? ['', '']; const [a, b] = win[cur] ?? [0, 1]; const ws = wordsOf(t); const k = interpolate(f, [a, b - 4], [0, ws.length], C);
  const size = t.length > 70 ? 88 : t.length > 40 ? 112 : 150;
  return <SceneBg drift={0.25} style={{ transform: `scale(${cam})` }}>
    <Mono text="REAL RECORDING · FAA NEW YORK TRACON" f0={2} size={22} color={MUTED} style={{ position: 'absolute', left: 150, top: 170 }} />
    <Mono text={st} f0={a + 2} size={32} color={isPilot(st) ? ACCENT_EP : BONE} style={{ position: 'absolute', left: 150, top: 230 }} />
    <div style={{ position: 'absolute', left: 140, top: 310, width: 1560, ...DISP(size, 68, 820), lineHeight: 0.98, textShadow: SHADOW }}>
      {ws.map((w, i) => { const p = interpolate(k, [i, i + 1], [0, 1], C); const hot = w.toUpperCase().replace(/[^A-Z]/g, '') === key;
        return <span key={`${cur}-${i}`} style={{ display: 'inline-block', marginRight: size * 0.22, opacity: p, transform: `translateY(${(1 - p) * 24}px)`, color: hot ? ACCENT_EP : isPilot(st) ? BONE : rgba(BONE, 0.82) }}>{w}{hot && P.stop ? <StopBlock size={size} p={interpolate(f, [a + 8, a + 18], [0, 1], C)} /> : null}</span>; })}
    </div>
    <Wave env={env} f={f} x={150} y={930} w={1500} h={80} />
  </SceneBg>;
};

// GlideBudget: the only fuel left is height. ~2,800 ft over ~210 s: a column drains, the seconds count, cost per second lands.
export const GlideBudget: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params ?? {}; const mode = P.mode ?? 'drain';
  const H0 = 2800, T = 210; const run = interpolate(f, [8, d - 14], [0, 1], { ...C, easing: (x) => x });
  const colX = 1250, colY = 150, colH = 760, colW = 170;
  if (mode === 'cost') {
    const lost = 780; const p = interpolate(f, [10, 40], [0, 1], { ...C, easing: out });
    return <SceneBg drift={0.2} style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.04], C)})` }}>
      <svg width={1920} height={1080} style={{ position: 'absolute' }}>
        <rect x={colX} y={colY} width={colW} height={colH} fill={rgba(TINT, 0.10)} stroke={rgba(TINT, 0.5)} strokeWidth={2} />
        <rect x={colX} y={colY} width={colW} height={colH * (lost / H0) * p} fill={rgba(ACCENT_EP, 0.85)} />
        {[0, 700, 1400, 2100, 2800].map((v) => <text key={v} x={colX + colW + 24} y={colY + colH - (v / H0) * colH + 8} fontFamily={FONT.mono} fontSize={22} fill={MUTED}>{v} FT</text>)}
      </svg>
      <Mono text="ONE MINUTE OF TALKING IT OVER" f0={4} size={28} color={MUTED} style={{ position: 'absolute', left: 150, top: 300 }} />
      <div style={{ position: 'absolute', left: 140, top: 350, display: 'flex', alignItems: 'flex-end', gap: 30 }}><Odometer value={780} size={300} f0={10} /><span style={{ ...DISP(130), color: ACCENT_EP }}>FT</span></div>
      <div style={{ position: 'absolute', left: 150, top: 700, ...DISP(96, 70, 820), color: BONE, textShadow: SHADOW, opacity: interpolate(f, [40, 52], [0, 1], C) }}>= 28% OF ALL THE HEIGHT</div>
      <Mono text="OUR ARITHMETIC · 60 S × ~13 FT/S, OF ~2,800 FT" f0={56} size={22} color={MUTED} style={{ position: 'absolute', left: 154, top: 820 }} />
    </SceneBg>;
  }
  const alt = H0 * (1 - run); const sec = T * run;
  return <SceneBg drift={0.2}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <rect x={colX} y={colY} width={colW} height={colH} fill={rgba(TINT, 0.08)} stroke={rgba(TINT, 0.5)} strokeWidth={2} />
      <rect x={colX} y={colY + colH * (1 - alt / H0)} width={colW} height={colH * (alt / H0)} fill={rgba(ACCENT_EP, 0.8)} />
      <line x1={colX - 30} y1={colY + colH} x2={colX + colW + 30} y2={colY + colH} stroke={BONE} strokeWidth={3} />
      <text x={colX + colW + 24} y={colY + 12} fontFamily={FONT.mono} fontSize={24} fill={MUTED}>2,800 FT</text>
      <text x={colX + colW + 24} y={colY + colH + 8} fontFamily={FONT.mono} fontSize={24} fill={BONE}>THE RIVER</text>
      {/* altitude vs time trace */}
      <polyline points={Array.from({ length: 60 }, (_, i) => { const q = (i / 59) * run; return `${150 + q * 900},${860 - 520 * (1 - q)}`; }).join(' ')} fill="none" stroke={ACCENT_EP} strokeWidth={5} />
      <line x1={150} y1={860} x2={1050} y2={860} stroke={rgba(TINT, 0.5)} strokeWidth={2} /><line x1={150} y1={330} x2={150} y2={860} stroke={rgba(TINT, 0.5)} strokeWidth={2} />
      <text x={150} y={900} fontFamily={FONT.mono} fontSize={22} fill={MUTED}>0 S</text><text x={1050} y={900} textAnchor="end" fontFamily={FONT.mono} fontSize={22} fill={MUTED}>≈ 210 S</text>
    </svg>
    <div style={{ position: 'absolute', left: 150, top: 150, fontFamily: FONT.mono, fontWeight: 500, fontSize: 120, color: BONE, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW }}>{String(Math.round(alt)).padStart(4, ' ')}<span style={{ fontSize: 50, color: MUTED }}> FT</span></div>
    <div style={{ position: 'absolute', left: 640, top: 190, fontFamily: FONT.mono, fontSize: 60, color: MUTED, fontVariantNumeric: 'tabular-nums' }}>T+{Math.round(sec)} S</div>
    <div style={{ position: 'absolute', left: 150, top: 940, ...DISP(64, 70, 820), color: ACCENT_EP, textShadow: SHADOW, opacity: interpolate(f, [d * 0.55, d * 0.55 + 10], [0, 1], C) }}>≈ 13 FEET EVERY SECOND</div>
    <Mono text="ABOUT 2,800 FT · ABOUT 3.5 MIN · NTSB HEARING, 2009 · OUR ARITHMETIC" f0={10} size={18} color={rgba(BONE, 0.6)} style={{ position: 'absolute', left: 154, top: 92 }} />
  </SceneBg>;
};

// OffersMap: schematic New York; each runway the controller offered appears and is answered.
const LON0 = -73.99, LAT0 = 40.79, KX = 84.3, KY = 111.0; // km per degree
export const proj = (lat: number, lon: number, sc: number, cx: number, cy: number): [number, number] => [cx + (lon - LON0) * KX * sc, cy - (lat - LAT0) * KY * sc];
const MANH: [number, number][] = [[40.7003, -74.015], [40.709, -74.0185], [40.728, -74.011], [40.748, -74.009], [40.764, -73.999], [40.78, -73.988], [40.8, -73.973], [40.82, -73.96], [40.8517, -73.947], [40.87, -73.931], [40.878, -73.922], [40.873, -73.91], [40.834, -73.934], [40.801, -73.929], [40.79, -73.942], [40.776, -73.942], [40.758, -73.959], [40.74, -73.972], [40.727, -73.972], [40.71, -73.978], [40.704, -73.999]];
const HUDSON: [number, number][] = [[40.69, -74.03], [40.71, -74.026], [40.74, -74.019], [40.765, -74.008], [40.79, -73.991], [40.82, -73.972], [40.851, -73.955], [40.88, -73.938], [40.92, -73.92]];
const TRACK: [number, number][] = [[40.777, -73.874], [40.795, -73.862], [40.82, -73.875], [40.84, -73.9], [40.86, -73.925], [40.862, -73.945], [40.851, -73.956], [40.82, -73.974], [40.79, -73.991], [40.769, -74.004]];
export const PLACES: Record<string, [number, number, string]> = { LGA: [40.777, -73.874, 'LAGUARDIA'], TEB: [40.8501, -74.0608, 'TETERBORO'], EWR: [40.6895, -74.1745, 'NEWARK'], GWB: [40.8517, -73.9527, 'G. WASHINGTON BRIDGE'], DITCH: [40.769, -74.004, 'TOUCHDOWN'], STRIKE: [40.84, -73.9, 'BIRDS · ~2,800 FT'] };
export const OffersMap: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const P = s.params ?? {};
  const offers: [string, string, string, string][] = P.offers ?? []; // [place, label, stamp, answer]
  const sc = P.scale ?? 52; const cx = P.cx ?? 1060, cy = P.cy ?? 470;
  const cam = interpolate(f, [0, d], [1, P.zoom ?? 1.08], { ...C, easing: io });
  const pts = (a: [number, number][]) => a.map(([la, lo]) => proj(la, lo, sc, cx, cy).join(',')).join(' ');
  const trackP = interpolate(f, [0, d * (P.trackEnd ?? 0.9)], [P.trackFrom ?? 0, P.trackTo ?? 1], C);
  const tr = TRACK.map(([la, lo]) => proj(la, lo, sc, cx, cy)); let L = 0; const seg = tr.slice(1).map((p, i) => { const l = Math.hypot(p[0] - tr[i][0], p[1] - tr[i][1]); L += l; return l; });
  const per = Math.max(10, Math.round((d * 0.7) / Math.max(1, offers.length)));
  return <SceneBg drift={0.15}>
    <AbsoluteFill style={{ transform: `scale(${cam})`, transformOrigin: `${P.ox ?? 55}% ${P.oy ?? 45}%` }}>
      <svg width={1920} height={1080} style={{ position: 'absolute' }}>
        <polyline points={pts(HUDSON)} fill="none" stroke={rgba(TINT, 0.28)} strokeWidth={1.2 * sc} strokeLinejoin="round" strokeLinecap="round" />
        <polygon points={pts(MANH)} fill={rgba(TINT, 0.10)} stroke={rgba(TINT, 0.55)} strokeWidth={2} />
        <polyline points={tr.map((p) => p.join(',')).join(' ')} fill="none" stroke={ACCENT_EP} strokeWidth={5} strokeDasharray={`${L * trackP} ${L}`} strokeLinecap="round" />
        {Object.entries(PLACES).filter(([k]) => (P.places ?? ['LGA', 'TEB', 'EWR', 'GWB', 'DITCH']).includes(k)).map(([k, [la, lo, name]]) => { const [x, y] = proj(la, lo, sc, cx, cy); const ok = k === 'DITCH';
          return <g key={k}><circle cx={x} cy={y} r={ok ? 12 : 10} fill={ok ? ACCENT_EP : BONE} /><text x={x + 18} y={y - 14} fontFamily={FONT.mono} fontSize={22} letterSpacing={2} fill={ok ? ACCENT_EP : BONE}>{name}</text></g>; })}
      </svg>
    </AbsoluteFill>
    {offers.map(([place, label, stamp, ans], i) => { const a = 8 + i * per; const p = spring({ frame: f - a, fps, config: { damping: 18, stiffness: 120 } }); const no = f > a + per * 0.55;
      return f < a ? null : <div key={i} style={{ position: 'absolute', left: 120, top: 200 + i * 112, opacity: Math.min(1, p * 1.5), transform: `translateX(${(1 - p) * -40}px)` }}>
        <div style={{ fontFamily: FONT.mono, fontSize: 22, letterSpacing: '0.1em', color: MUTED }}>{stamp}</div>
        <div style={{ display: 'flex', gap: 22, alignItems: 'baseline' }}><span style={{ ...DISP(62, 70, 820), color: no ? rgba(BONE, 0.5) : BONE, textShadow: SHADOW, textDecoration: no ? `line-through ${rgba(BONE, 0.6)}` : 'none' }}>{label}</span>
          {no ? <span style={{ ...DISP(46, 70, 820), color: ACCENT_EP, textShadow: SHADOW }}>{ans}</span> : null}</div></div>; })}
    <Mono text="SCHEMATIC · TRACK APPROXIMATE · TIMES FROM THE FAA TRANSCRIPT (LOCAL)" f0={6} size={18} color={rgba(BONE, 0.6)} style={{ position: 'absolute', left: 120, top: 120 }} />
  </SceneBg>;
};
