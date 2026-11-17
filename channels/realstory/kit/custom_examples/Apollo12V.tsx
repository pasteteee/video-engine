// Apollo 12 instruments re-laid for 9:16 Shorts (1080x1920). Same data as the 16:9 scenes, composed for a tall frame.
import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { ACCENT_EP, BONE, C, DISP, FONT, GROUND, GROUND2, MUTED, SHADOW, SIGNAL, TINT, io, rgba, rng } from '../kit/tokens';
import { Mono } from '../kit/Type';
import { AMBERL, GOOD, LAMPS, ORDER, PATTERN, ROWS } from './Apollo12';

const X0 = 80;
const Bg: React.FC<{ children?: React.ReactNode; z?: number }> = ({ children, z = 1 }) =>
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 38%, ${GROUND2} 0%, ${GROUND} 75%)` }}>
    <AbsoluteFill style={{ transform: `scale(${z})` }}>{children}</AbsoluteFill></AbsoluteFill>;

export const VCaution: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params ?? {};
  const t0 = Math.round((P.at ?? 0.1) * d); const step = Math.max(2, Math.round((d * 0.45) / ORDER.length));
  const cols = 4, cw = 230, chh = 104, x0 = 540 - (cols * cw) / 2, y0 = 420;
  const blink = f > t0 && Math.floor(f / 8) % 2 === 0;
  return <Bg z={interpolate(f, [0, d], [1, 1.05], C)}>
    <Mono text="CAUTION & WARNING · COMMAND MODULE" f0={2} size={24} color={MUTED} style={{ position: 'absolute', left: x0, top: 360 }} />
    {LAMPS.map((n, i) => { const k = ORDER.indexOf(i); const on = P.all ? f > t0 : (k >= 0 && f >= t0 + k * step); const x = x0 + (i % cols) * cw, y = y0 + Math.floor(i / cols) * chh;
      const fl = on ? 0.85 + 0.15 * Math.sin(f * 1.3 + i) : 0;
      return <div key={n} style={{ position: 'absolute', left: x + 6, top: y + 6, width: cw - 12, height: chh - 12, background: on ? rgba(AMBERL, 0.22 + 0.5 * fl) : rgba(TINT, 0.06), boxShadow: on ? `0 0 34px ${rgba(AMBERL, 0.55 * fl)}` : 'none',
        display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center', fontFamily: FONT.mono, fontWeight: 500, fontSize: 22, letterSpacing: '0.05em', color: on ? '#1b1206' : rgba(BONE, 0.32), lineHeight: 1.1, padding: 8 }}>{n}</div>; })}
    <div style={{ position: 'absolute', left: x0, top: y0 + 6 * chh + 50, display: 'flex', alignItems: 'center', gap: 28 }}>
      <div style={{ width: 120, height: 70, background: blink ? SIGNAL : rgba(SIGNAL, 0.15), boxShadow: blink ? `0 0 50px ${rgba(SIGNAL, 0.8)}` : 'none' }} />
      <div style={{ ...DISP(80, 70, 820), color: blink ? BONE : MUTED, textShadow: SHADOW }}>MASTER ALARM</div></div>
  </Bg>;
};

export const VScreen: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const P = s.params ?? {}; const mode = P.mode ?? 'garble';
  const flip = Math.round((P.at ?? 0.35) * d); const r = rng(Math.floor(f / 3) + 3);
  const val = (i: number) => mode === 'restore' ? (f < flip ? (r() * 99).toFixed(1) : GOOD[i])
    : mode === 'pattern' ? (f < flip ? (r() * 99).toFixed(1) : PATTERN[i]) : (f < flip ? GOOD[i] : (r() < 0.3 ? '###' : (r() * 999).toFixed(1)));
  const bad = (mode === 'garble' && f >= flip) || (mode !== 'garble' && f < flip);
  return <Bg z={interpolate(f, [0, d], [1.0, 1.05], C)}>
    <div style={{ position: 'absolute', left: 60, top: 360, width: 960, height: 980, background: 'radial-gradient(ellipse at 50% 50%, #0d1a14 0%, #050b08 90%)', boxShadow: 'inset 0 0 120px rgba(0,0,0,0.9)', borderRadius: 40, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', left: 56, top: 50, fontFamily: FONT.mono, fontSize: 24, letterSpacing: 3, color: '#79d38f' }}>EECOM · {P.stamp ?? 'GET 000:00:38'}</div>
      {ROWS.map((n, i) => { const v = val(i); const hl = mode === 'pattern' && f >= flip && (v === '6.7' || v === '12.3');
        return <div key={n} style={{ position: 'absolute', left: 56, top: 130 + i * 82, width: 848, display: 'flex', justifyContent: 'space-between', fontFamily: FONT.mono, fontSize: 40, color: hl ? ACCENT_EP : bad ? '#b8f5c4' : '#79d38f', textShadow: '0 0 12px rgba(120,230,150,0.55)' }}>
          <span>{n}</span><span style={{ fontVariantNumeric: 'tabular-nums' }}>{v}</span></div>; })}
      <div style={{ position: 'absolute', left: 0, right: 0, top: (f * 11) % 980, height: 100, background: 'linear-gradient(180deg, rgba(120,230,150,0) 0%, rgba(120,230,150,0.07) 50%, rgba(120,230,150,0) 100%)' }} />
      <div style={{ position: 'absolute', inset: 0, backgroundImage: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.25) 0px, rgba(0,0,0,0.25) 2px, transparent 2px, transparent 5px)' }} />
    </div>
    {P.label ? <div style={{ position: 'absolute', left: X0, right: 60, top: 1390, ...DISP(84, 70, 820), lineHeight: 0.95, color: bad ? SIGNAL : BONE, textShadow: SHADOW, opacity: f > flip + 6 ? 1 : 0 }}>{P.label}</div> : null}
  </Bg>;
};

export const VSwitch: React.FC<{ s: any; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig(); const P = s.params ?? {};
  const at = Math.round((P.at ?? 0.5) * d); const p = spring({ frame: f - at, fps, config: { damping: 11, stiffness: 220 } });
  const ang = -38 + 76 * (f >= at ? p : 0);
  return <Bg z={interpolate(f, [0, d], [1.0, 1.1], { ...C, easing: io })}>
    <div style={{ position: 'absolute', left: 90, top: 520, width: 900, height: 820, background: 'linear-gradient(160deg, #5d6166 0%, #3c3f43 100%)', boxShadow: '0 40px 120px rgba(0,0,0,0.6)' }}>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 70, textAlign: 'center', fontFamily: FONT.mono, fontSize: 46, letterSpacing: 8, color: '#f1efe6' }}>SCE POWER</div>
      <div style={{ position: 'absolute', left: 110, top: 210, fontFamily: FONT.mono, fontSize: 50, letterSpacing: 6, color: f >= at ? 'rgba(241,239,230,0.45)' : '#f1efe6' }}>NORM</div>
      <div style={{ position: 'absolute', right: 110, top: 210, fontFamily: FONT.mono, fontSize: 50, letterSpacing: 6, color: f >= at ? ACCENT_EP : 'rgba(241,239,230,0.45)' }}>AUX</div>
      <div style={{ position: 'absolute', left: 380, top: 460, width: 140, height: 140, borderRadius: 70, background: 'radial-gradient(circle at 40% 35%, #c9ccd0 0%, #6c7075 70%)', boxShadow: '0 10px 30px rgba(0,0,0,0.6)' }} />
      <div style={{ position: 'absolute', left: 432, top: 210, width: 36, height: 320, transformOrigin: '50% 100%', transform: `rotate(${ang}deg)`, background: 'linear-gradient(90deg, #8d9196 0%, #e8eaec 45%, #8d9196 100%)', borderRadius: 18, boxShadow: '6px 8px 14px rgba(0,0,0,0.5)' }} />
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 50, textAlign: 'center', fontFamily: FONT.mono, fontSize: 24, letterSpacing: 4, color: 'rgba(241,239,230,0.6)' }}>RECONSTRUCTION · NOT TO SCALE</div>
    </div>
    {P.stamp ? <Mono text={P.stamp} f0={at + 6} size={40} color={ACCENT_EP} style={{ position: 'absolute', left: 90, top: 1400 }} /> : null}
  </Bg>;
};
export const VCUSTOM: Record<string, React.FC<{ s: any; d: number }>> = { VCaution, VScreen, VSwitch };
