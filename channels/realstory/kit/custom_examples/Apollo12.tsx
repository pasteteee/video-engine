// Apollo 12 scenes made from the subject itself: the caution & warning panel, the main bus voltmeter,
// the EECOM telemetry screen and the SCE switch.
import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { SceneBg } from '../kit/Brand';
import { ACCENT_EP, BONE, C, DISP, FONT, MUTED, SHADOW, SIGNAL, TINT, io, out, rgba, rng } from '../kit/tokens';
import { Mono } from '../kit/Type';

export const AMBERL = '#f2b33a';

// Caution & warning panel: lamps light in the order Conrad read them; the master alarm blinks.
export const LAMPS = ['FC 1', 'FC 2', 'FC 3', 'FC BUS DISCONNECT', 'AC BUS 1', 'AC BUS 1 OVERLOAD', 'AC BUS 2 OVERLOAD', 'MAIN BUS A UNDERVOLT', 'MAIN BUS B UNDERVOLT', 'CRYO PRESS', 'GLYCOL TEMP', 'SM RCS A', 'SM RCS B', 'SPS PRESS', 'CM RCS 1', 'CM RCS 2', 'O2 FLOW HI', 'SUIT COMP', 'CO2 PP HI', 'ISS', 'CMC', 'GIMBAL LOCK', 'PITCH GMBL', 'YAW GMBL'];
export const ORDER = [0, 1, 2, 3, 4, 5, 6, 7, 8, 19, 20, 21];
export const CautionPanel: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params ?? {};
  const t0 = Math.round((P.at ?? 0.15) * d); const step = Math.max(2, Math.round((d * 0.45) / ORDER.length));
  const all = P.all ? f > t0 : false;
  const cols = 6, cw = 250, chh = 96, x0 = 960 - (cols * cw) / 2, y0 = 300;
  const blink = f > t0 && Math.floor(f / 8) % 2 === 0;
  const cam = interpolate(f, [0, d], [1, 1.07], C);
  return <SceneBg style={{ transform: `scale(${cam})` }}>
    <Mono text="CAUTION AND WARNING PANEL  ·  COMMAND MODULE" f0={2} size={22} color={MUTED} style={{ position: 'absolute', left: x0, top: 230 }} />
    {LAMPS.map((n, i) => { const k = ORDER.indexOf(i); const on = all || (k >= 0 && f >= t0 + k * step); const x = x0 + (i % cols) * cw, y = y0 + Math.floor(i / cols) * chh;
      const flick = on ? 0.85 + 0.15 * Math.sin(f * 1.3 + i) : 0;
      return <div key={n} style={{ position: 'absolute', left: x + 6, top: y + 6, width: cw - 12, height: chh - 12, background: on ? rgba(AMBERL, 0.22 + 0.5 * flick) : rgba(TINT, 0.06), boxShadow: on ? `0 0 34px ${rgba(AMBERL, 0.55 * flick)}` : 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
        fontFamily: FONT.mono, fontWeight: 500, fontSize: 20, letterSpacing: '0.06em', color: on ? '#1b1206' : rgba(BONE, 0.32), lineHeight: 1.1, padding: 8 }}>{n}</div>; })}
    <div style={{ position: 'absolute', left: x0, top: y0 + 4 * chh + 40, display: 'flex', alignItems: 'center', gap: 28 }}>
      <div style={{ width: 120, height: 64, background: blink ? SIGNAL : rgba(SIGNAL, 0.15), boxShadow: blink ? `0 0 50px ${rgba(SIGNAL, 0.8)}` : 'none' }} />
      <div style={{ ...DISP(64, 70, 820), color: blink ? BONE : MUTED, textShadow: SHADOW }}>MASTER ALARM</div>
    </div>
    {P.note ? <Mono text={P.note} f0={Math.round(d * 0.6)} size={24} color={BONE} style={{ position: 'absolute', left: x0, top: y0 + 4 * chh + 140 }} /> : null}
  </SceneBg>;
};

// Main bus voltmeter: the needle falls from 28 to ~24 V; three fuel-cell flags drop to OFF.
export const BusMeter: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const P = s.params ?? {};
  const hit = Math.round((P.at ?? 0.25) * d);
  const v = f < hit ? 28 + 0.1 * Math.sin(f / 3) : f < hit + 2 ? 18.5 : interpolate(f, [hit + 2, hit + 16], [18.5, 24], { ...C, easing: out }) + 0.15 * Math.sin(f / 2);
  const ang = interpolate(v, [0, 35], [-120, 120]); const CX = 640, CY = 640, R = 330;
  const pt = (a: number, r: number) => [CX + r * Math.sin((a * Math.PI) / 180), CY - r * Math.cos((a * Math.PI) / 180)];
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1, 1.05], C)})` }}>
    <svg width={1920} height={1080} style={{ position: 'absolute' }}>
      <path d={`M${pt(-120, R).join(' ')} A${R} ${R} 0 1 1 ${pt(120, R).join(' ')}`} fill="none" stroke={rgba(TINT, 0.45)} strokeWidth={3} />
      <path d={`M${pt(interpolate(26, [0, 35], [-120, 120]), R).join(' ')} A${R} ${R} 0 0 1 ${pt(interpolate(30, [0, 35], [-120, 120]), R).join(' ')}`} fill="none" stroke={ACCENT_EP} strokeWidth={14} opacity={0.6} />
      {Array.from({ length: 36 }, (_, i) => { const a = interpolate(i, [0, 35], [-120, 120]); const big = i % 5 === 0; const [x0, y0] = pt(a, R - (big ? 40 : 18)), [x1, y1] = pt(a, R - 4);
        return <g key={i}><line x1={x0} y1={y0} x2={x1} y2={y1} stroke={big ? BONE : rgba(TINT, 0.6)} strokeWidth={big ? 4 : 2} />
          {big ? (() => { const [tx, ty] = pt(a, R - 80); return <text x={tx} y={ty + 10} textAnchor="middle" fontFamily={FONT.mono} fontSize={28} fill={BONE}>{i}</text>; })() : null}</g>; })}
      {(() => { const [x, y] = pt(ang, R - 30); return <line x1={CX} y1={CY} x2={x} y2={y} stroke={f >= hit ? SIGNAL : BONE} strokeWidth={8} strokeLinecap="square" />; })()}
      <circle cx={CX} cy={CY} r={16} fill={BONE} />
      <text x={CX} y={CY + 130} textAnchor="middle" fontFamily={FONT.mono} fontSize={26} letterSpacing={4} fill={MUTED}>MAIN BUS · VOLTS DC</text>
    </svg>
    <div style={{ position: 'absolute', left: 1180, top: 300 }}>
      <Mono text="FUEL CELLS" f0={4} size={26} color={MUTED} />
      {[0, 1, 2].map((i) => { const off = f >= hit + i * 2; const p = spring({ frame: f - hit - i * 2, fps, config: { damping: 12, stiffness: 160 } });
        return <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 30, marginTop: 34 }}>
          <span style={{ ...DISP(84, 70, 820), color: BONE, width: 160 }}>FC {i + 1}</span>
          <span style={{ width: 150, height: 66, background: off ? rgba(SIGNAL, 0.85) : rgba(TINT, 0.25), transform: `rotateX(${off ? (1 - p) * 90 : 0}deg)`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT.mono, fontSize: 28, color: BONE, letterSpacing: 4 }}>{off ? 'OFF' : 'ON'}</span></div>; })}
      <div style={{ marginTop: 60, display: 'flex', alignItems: 'baseline', gap: 18 }}>
        <span style={{ ...DISP(150, 62, 880), color: f >= hit ? ACCENT_EP : BONE, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW }}>{v.toFixed(1)}</span><span style={{ ...DISP(70), color: MUTED }}>V</span></div>
      <Mono text={P.note ?? 'ON ENTRY BATTERIES A + B'} f0={hit + 12} size={24} color={BONE} style={{ marginTop: 10 }} />
    </div>
  </SceneBg>;
};

// EECOM screen: parameter rows read normally, then garble; 'pattern' freezes on 6.7 / 12.3; 'restore' snaps back.
export const ROWS = ['MAIN BUS A VOLTS', 'MAIN BUS B VOLTS', 'FC 1 CURRENT', 'FC 2 CURRENT', 'FC 3 CURRENT', 'BAT A CURRENT', 'O2 TANK 1 PRESS', 'H2 TANK 1 PRESS', 'CABIN PRESS', 'SUIT TEMP'];
export const GOOD = ['28.1', '28.0', '24.6', '25.1', '23.9', '0.4', '898', '238', '14.6', '54.2'];
export const PATTERN = ['6.7', '12.3', '0.0', '6.7', '31.9', '12.3', '0.0', '6.7', '12.3', '0.0'];
export const TelemetryScreen: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params ?? {}; const mode = P.mode ?? 'garble';
  const flip = Math.round((P.at ?? 0.35) * d); const r = rng(Math.floor(f / 3) + 3);
  const val = (i: number) => {
    if (mode === 'restore') return f < flip ? String((r() * 99).toFixed(1)) : GOOD[i];
    if (mode === 'pattern') return f < flip ? String((r() * 99).toFixed(1)) : PATTERN[i];
    return f < flip ? GOOD[i] : (r() < 0.3 ? '###' : (r() * 999).toFixed(1));
  };
  const bad = (mode === 'garble' && f >= flip) || (mode !== 'garble' && f < flip);
  const scan = (f * 9) % 1080;
  return <SceneBg style={{ transform: `scale(${interpolate(f, [0, d], [1.02, 1.08], C)})` }}>
    <div style={{ position: 'absolute', left: 300, top: 150, width: 1320, height: 780, background: 'radial-gradient(ellipse at 50% 50%, #0d1a14 0%, #050b08 90%)', boxShadow: 'inset 0 0 120px rgba(0,0,0,0.9)', borderRadius: 40, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', left: 70, top: 50, fontFamily: FONT.mono, fontSize: 24, letterSpacing: 4, color: '#79d38f' }}>EECOM · CSM ELECTRICAL · {P.stamp ?? 'GET 000:00:38'}</div>
      {ROWS.map((n, i) => { const v = val(i); const hl = mode === 'pattern' && f >= flip && (v === '6.7' || v === '12.3');
        return <div key={n} style={{ position: 'absolute', left: 70, top: 120 + i * 62, width: 1180, display: 'flex', justifyContent: 'space-between', fontFamily: FONT.mono, fontSize: 38, color: hl ? ACCENT_EP : bad ? '#b8f5c4' : '#79d38f', textShadow: '0 0 12px rgba(120,230,150,0.55)' }}>
          <span>{n}</span><span style={{ fontVariantNumeric: 'tabular-nums' }}>{v}</span></div>; })}
      <div style={{ position: 'absolute', left: 0, right: 0, top: scan, height: 90, background: 'linear-gradient(180deg, rgba(120,230,150,0) 0%, rgba(120,230,150,0.07) 50%, rgba(120,230,150,0) 100%)' }} />
      <div style={{ position: 'absolute', inset: 0, backgroundImage: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.25) 0px, rgba(0,0,0,0.25) 2px, transparent 2px, transparent 5px)' }} />
    </div>
    {P.label ? <div style={{ position: 'absolute', left: 300, top: 960, ...DISP(64, 70, 820), color: bad ? SIGNAL : BONE, textShadow: SHADOW, opacity: f > flip + 6 ? 1 : 0 }}>{P.label}</div> : null}
  </SceneBg>;
};

// SCE switch: a toggle on a grey panel throws from NORM to AUX on the sync frame.
export const SceSwitch: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const P = s.params ?? {};
  const at = Math.round((P.at ?? 0.5) * d); const p = spring({ frame: f - at, fps, config: { damping: 11, stiffness: 220 } });
  const ang = -38 + 76 * (f >= at ? p : 0);
  const cam = interpolate(f, [0, d], [1.0, 1.12], { ...C, easing: io });
  return <SceneBg style={{ transform: `scale(${cam})`, transformOrigin: '50% 55%' }}>
    <div style={{ position: 'absolute', left: 560, top: 180, width: 800, height: 720, background: 'linear-gradient(160deg, #5d6166 0%, #3c3f43 100%)', boxShadow: '0 40px 120px rgba(0,0,0,0.6)' }}>
      {[[40, 40], [720, 40], [40, 640], [720, 640]].map(([x, y], i) => <div key={i} style={{ position: 'absolute', left: x, top: y, width: 34, height: 34, borderRadius: 17, background: '#2b2d30', boxShadow: 'inset 0 2px 4px rgba(255,255,255,0.15)' }} />)}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 70, textAlign: 'center', fontFamily: FONT.mono, fontSize: 40, letterSpacing: 8, color: '#f1efe6' }}>SCE POWER</div>
      <div style={{ position: 'absolute', left: 120, top: 200, fontFamily: FONT.mono, fontSize: 44, letterSpacing: 6, color: f >= at ? 'rgba(241,239,230,0.45)' : '#f1efe6' }}>NORM</div>
      <div style={{ position: 'absolute', right: 120, top: 200, fontFamily: FONT.mono, fontSize: 44, letterSpacing: 6, color: f >= at ? ACCENT_EP : 'rgba(241,239,230,0.45)' }}>AUX</div>
      <div style={{ position: 'absolute', left: 340, top: 400, width: 120, height: 120, borderRadius: 60, background: 'radial-gradient(circle at 40% 35%, #c9ccd0 0%, #6c7075 70%)', boxShadow: '0 10px 30px rgba(0,0,0,0.6)' }} />
      <div style={{ position: 'absolute', left: 384, top: 180, width: 32, height: 280, transformOrigin: '50% 100%', transform: `rotate(${ang}deg)`, background: 'linear-gradient(90deg, #8d9196 0%, #e8eaec 45%, #8d9196 100%)', borderRadius: 16, boxShadow: '6px 8px 14px rgba(0,0,0,0.5)' }} />
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 60, textAlign: 'center', fontFamily: FONT.mono, fontSize: 22, letterSpacing: 4, color: 'rgba(241,239,230,0.6)' }}>RECONSTRUCTION · NOT TO SCALE</div>
    </div>
    {P.stamp ? <Mono text={P.stamp} f0={at + 6} size={34} color={ACCENT_EP} style={{ position: 'absolute', left: 1420, top: 480 }} /> : null}
  </SceneBg>;
};
