// Flight 1549 instruments re-laid for 9:16 Shorts (1080x1920): the radio tape and the height budget.
// Same data as the 16:9 scenes; text stays left, clear of the right-hand UI and the bottom caption zone.
import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, GROUND2, MUTED, SHADOW, TINT, out, rgba } from '../kit/tokens';
import { Mono, Odometer, StopBlock } from '../kit/Type';
import ENV from '../ep/radio_env.json';

const X0 = 80;
const Bg: React.FC<{ children?: React.ReactNode; z?: number }> = ({ children, z = 1 }) =>
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 38%, ${GROUND2} 0%, ${GROUND} 75%)` }}>
    <AbsoluteFill style={{ transform: `scale(${z})` }}>{children}</AbsoluteFill></AbsoluteFill>;

const Wave: React.FC<{ env: number[]; f: number; y: number; h: number }> = ({ env, f, y, h }) => {
  const bars = 48; const w = 1080 - 2 * X0; const max = Math.max(0.02, ...env);
  return <svg width={1080} height={1920} style={{ position: 'absolute', left: 0, top: 0 }}>
    {Array.from({ length: bars }, (_, i) => { const k = f - (bars - 1 - i); const v = k >= 0 && k < env.length ? env[k] / max : 0; const hh = 4 + v * h;
      return <rect key={i} x={X0 + (i * w) / bars} y={y - hh / 2} width={w / bars - 6} height={hh} fill={i === bars - 1 ? BONE : rgba(ACCENT_EP, 0.35 + 0.65 * (i / bars))} />; })}
  </svg>;
};

// VAtcTape: params {line (episode line id for the loudness envelope), offset_s (where this shot starts inside that line), txs [[stamp, words, from_s, to_s]], key, stop}
export const VAtcTape: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params ?? {}; const env: number[] = ((ENV as any)[P.line] ?? []).slice(Math.round((P.offset_s ?? 0) * 30));
  const txs: [string, string, number, number][] = P.txs ?? []; const t = f / 30;
  const cur = Math.max(0, txs.findIndex(([, , a, b]) => t >= a && t < b)); const [st, words, a, b] = txs[cur] ?? ['', '', 0, 1];
  const ws = words.split(' '); const k = interpolate(t, [a, Math.max(a + 0.2, b - 0.15)], [0, ws.length], C);
  const pilot = st.includes('1549'); const key = (P.key ?? 'HUDSON') as string;
  const size = words.length > 70 ? 92 : words.length > 40 ? 112 : 140;
  return <Bg z={interpolate(f, [0, d], [1, 1.04], C)}>
    <Mono text="REAL RECORDING · FAA NEW YORK TRACON" f0={2} size={26} color={MUTED} style={{ position: 'absolute', left: X0, top: 330 }} />
    <Mono text={st} f0={Math.round(a * 30) + 2} size={34} color={pilot ? ACCENT_EP : BONE} style={{ position: 'absolute', left: X0, top: 390 }} />
    <div style={{ position: 'absolute', left: X0, top: 470, width: 1080 - X0 - 120, ...DISP(size, 68, 820), lineHeight: 0.98, textShadow: SHADOW }}>
      {ws.map((w, i) => { const p = interpolate(k, [i, i + 1], [0, 1], C); const hot = w.toUpperCase().replace(/[^A-Z]/g, '') === key;
        return <span key={`${cur}-${i}`} style={{ display: 'inline-block', marginRight: size * 0.22, opacity: p, transform: `translateY(${(1 - p) * 20}px)`, color: hot ? ACCENT_EP : pilot ? BONE : rgba(BONE, 0.82) }}>{w}{hot && P.stop ? <StopBlock size={size} p={interpolate(f, [a * 30 + 8, a * 30 + 18], [0, 1], C)} /> : null}</span>; })}
    </div>
    <Wave env={env} f={f} y={1300} h={110} />
  </Bg>;
};

// VGlide: mode 'drain' = height column empties over ~210 s with T+ seconds; 'cost' = one minute = 780 ft = 28%.
export const VGlide: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params ?? {}; const H0 = 2800, T = 210;
  const colX = 760, colY = 560, colW = 150, colH = 760;
  if (P.mode === 'cost') {
    const p = interpolate(f, [10, 40], [0, 1], { ...C, easing: out });
    return <Bg z={interpolate(f, [0, d], [1, 1.04], C)}>
      <svg width={1080} height={1920} style={{ position: 'absolute' }}>
        <rect x={colX} y={colY} width={colW} height={colH} fill={rgba(TINT, 0.1)} stroke={rgba(TINT, 0.5)} strokeWidth={2} />
        <rect x={colX} y={colY} width={colW} height={colH * (780 / H0) * p} fill={rgba(ACCENT_EP, 0.85)} />
      </svg>
      <Mono text="ONE MINUTE OF TALKING IT OVER" f0={4} size={28} color={MUTED} style={{ position: 'absolute', left: X0, top: 380 }} />
      <div style={{ position: 'absolute', left: X0, top: 560, display: 'flex', flexDirection: 'column' }}><Odometer value={780} size={250} f0={10} /><span style={{ ...DISP(120), color: ACCENT_EP }}>FT</span></div>
      <div style={{ position: 'absolute', left: X0, top: 1000, width: 620, ...DISP(96, 70, 820), color: BONE, textShadow: SHADOW, opacity: interpolate(f, [40, 52], [0, 1], C) }}>= 28% OF ALL THE HEIGHT</div>
      <Mono text="OUR ARITHMETIC · 60 S × ~13 FT/S" f0={56} size={24} color={MUTED} style={{ position: 'absolute', left: X0, top: 1240 }} />
    </Bg>;
  }
  const run = interpolate(f, [8, d - 10], [0, 1], C); const alt = H0 * (1 - run);
  return <Bg>
    <svg width={1080} height={1920} style={{ position: 'absolute' }}>
      <rect x={colX} y={colY} width={colW} height={colH} fill={rgba(TINT, 0.08)} stroke={rgba(TINT, 0.5)} strokeWidth={2} />
      <rect x={colX} y={colY + colH * (1 - alt / H0)} width={colW} height={colH * (alt / H0)} fill={rgba(ACCENT_EP, 0.8)} />
      <line x1={colX - 24} y1={colY + colH} x2={colX + colW + 24} y2={colY + colH} stroke={BONE} strokeWidth={3} />
    </svg>
    <Mono text="ABOUT 2,800 FT · ABOUT 3.5 MIN · NTSB HEARING" f0={4} size={24} color={MUTED} style={{ position: 'absolute', left: X0, top: 380 }} />
    <div style={{ position: 'absolute', left: X0, top: 560, fontFamily: FONT.mono, fontWeight: 500, fontSize: 150, color: BONE, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW }}>{Math.round(alt)}</div>
    <div style={{ position: 'absolute', left: X0, top: 740, fontFamily: FONT.mono, fontSize: 56, color: MUTED }}>FT · T+{Math.round(T * run)} S</div>
    <div style={{ position: 'absolute', left: X0, top: 1000, width: 620, ...DISP(110, 70, 840), color: ACCENT_EP, textShadow: SHADOW, opacity: interpolate(f, [d * 0.35, d * 0.35 + 10], [0, 1], C) }}>13 FEET EVERY SECOND</div>
  </Bg>;
};
