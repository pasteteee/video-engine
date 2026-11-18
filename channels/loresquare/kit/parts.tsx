// Shared building blocks: art layer, slam words, katakana SFX, stamps, flash.
import React from 'react';
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, FONT, H, INK, PAPER, RED, W, YELLOW, fit, lin, out, strokeText } from './tokens';

export type P = Record<string, any>;

/** Image positioned to cover the frame at `zoom`, with focus point (fx, fy) in 0..1. */
const cover = (wh: [number, number], zoom: number, fx: number, fy: number, box = [W, H]) => {
  const [w, h] = wh;
  const s = Math.max(box[0] / w, box[1] / h) * zoom;
  const iw = w * s, ih = h * s;
  const left = Math.min(0, Math.max(box[0] - iw, box[0] / 2 - iw * fx));
  const top = Math.min(0, Math.max(box[1] - ih, box[1] / 2 - ih * fy));
  return { position: 'absolute' as const, width: iw, height: ih, left, top };
};

/** Blurred, darkened fill behind any image (never an empty frame). */
export const BlurFill: React.FC<{ src: string; dark?: number; tint?: string }> = ({ src, dark = 0.55, tint }) => (
  <AbsoluteFill style={{ overflow: 'hidden', background: INK }}>
    <Img src={staticFile(src)} style={{ position: 'absolute', inset: -120, width: W + 240, height: H + 240, objectFit: 'cover', filter: 'blur(38px) saturate(1.3)' }} />
    {tint && <AbsoluteFill style={{ background: tint, mixBlendMode: 'color', opacity: 0.8 }} />}
    <AbsoluteFill style={{ background: `rgba(0,0,0,${dark})` }} />
  </AbsoluteFill>
);

export const Halftone: React.FC<{ opacity?: number; size?: number; color?: string }> = ({ opacity = 0.35, size = 9, color = '0,0,0' }) => (
  <AbsoluteFill style={{
    backgroundImage: `radial-gradient(circle, rgba(${color},1) 28%, transparent 31%)`,
    backgroundSize: `${size}px ${size}px`, opacity, mixBlendMode: 'multiply',
  }} />
);

export const SpeedLines: React.FC<{ cy?: number; opacity?: number; color?: string }> = ({ cy = 42, opacity = 0.9, color = '255,255,255' }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{
      backgroundImage: `repeating-conic-gradient(from ${f * 0.6}deg at 50% ${cy}%, rgba(${color},0.95) 0deg 0.9deg, transparent 0.9deg 5.5deg)`,
      WebkitMaskImage: `radial-gradient(circle at 50% ${cy}%, transparent 24%, black 62%)`,
      opacity: opacity * (0.85 + 0.15 * Math.sin(f * 1.7)),
    }} />
  );
};

/** Manga art layer. Small images become a framed card over their own blurred fill. */
export const Art: React.FC<{ p: P; k?: string; dur: number; variant?: string }> = ({ p, k = 'media', dur, variant = 'ken_burns' }) => {
  const f = useCurrentFrame();
  const src: string = p[k + '_src'];
  const wh: [number, number] = p[k + '_wh'] || [1000, 1400];
  const tint: string | undefined = p.tint;
  const t = f / Math.max(dur, 1);
  if (!src) return <AbsoluteFill style={{ background: INK }} />;
  const small = wh[0] < 700;
  const duo = variant === 'halftone_duotone';
  const imgFilter = duo ? 'grayscale(1) contrast(1.35) brightness(1.05)' : 'saturate(1.15) contrast(1.05)';
  if (small) {
    const cardH = 1180, cardW = Math.min(900, (cardH * wh[0]) / wh[1]);
    const s = interpolate(t, [0, 1], [1.0, 1.08]);
    const enter = spring({ frame: f, fps: 30, config: { damping: 14, mass: 0.7 } });
    return (
      <AbsoluteFill>
        <BlurFill src={src} tint={tint} dark={0.35} />
        <SpeedLines opacity={0.25} />
        <div style={{
          position: 'absolute', left: (W - cardW) / 2, top: 170, width: cardW, height: cardH,
          transform: `translateY(${(1 - enter) * 260}px) rotate(${-2.5 + (1 - enter) * 8}deg) scale(${s})`,
          border: `12px solid ${PAPER}`, boxShadow: `18px 18px 0 ${INK}`, overflow: 'hidden', background: INK,
        }}>
          <Img src={staticFile(src)} style={{ width: '100%', height: '100%', objectFit: 'cover', filter: imgFilter }} />
          {duo && <AbsoluteFill style={{ background: tint || RED, mixBlendMode: 'color', opacity: 0.85 }} />}
          {duo && <Halftone opacity={0.3} />}
        </div>
      </AbsoluteFill>
    );
  }
  const land = wh[0] > wh[1];
  let zoom = 1.04 + 0.16 * t, fx = land ? 0.3 + 0.4 * t : 0.5, fy = 0.38 - 0.06 * t;
  if (variant === 'speed_burst') zoom = 1.06 + 0.5 * Math.exp(-f / 4) + 0.08 * t;
  if (variant === 'parallax_cut') { zoom = 1.12; fx = land ? 0.65 - 0.3 * t : 0.5; }
  return (
    <AbsoluteFill style={{ overflow: 'hidden', background: INK }}>
      <Img src={staticFile(src)} style={{ ...cover(wh, zoom, fx, fy), filter: imgFilter }} />
      {duo && <AbsoluteFill style={{ background: tint || BLUE_DEF, mixBlendMode: 'color', opacity: 0.85 }} />}
      {duo && <Halftone opacity={0.32} />}
      {!duo && tint && <AbsoluteFill style={{ background: tint, mixBlendMode: 'multiply', opacity: 0.45 }} />}
      {variant === 'speed_burst' && <SpeedLines opacity={0.75} />}
      {variant === 'parallax_cut' && <ParallaxSlab p={p} k={k} dur={dur} />}
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.05) 30%, rgba(0,0,0,0.25) 55%, rgba(0,0,0,0.85) 100%)' }} />
    </AbsoluteFill>
  );
};
const BLUE_DEF = '#1f6feb';

/** Diagonal slab of the same art sliding against the backdrop (2.5D cut). */
const ParallaxSlab: React.FC<{ p: P; k: string; dur: number }> = ({ p, k, dur }) => {
  const f = useCurrentFrame();
  const x = lin(f, 0, 14, 900, 0) - (f / dur) * 60;
  const wh: [number, number] = p[k + '_wh'];
  return (
    <AbsoluteFill style={{ transform: `translateX(${x}px)` }}>
      <div style={{ position: 'absolute', inset: 0, clipPath: 'polygon(38% 0, 100% 0, 100% 100%, 8% 100%)', overflow: 'hidden', borderLeft: `10px solid ${YELLOW}` }}>
        <Img src={staticFile(p[k + '_src'])} style={{ ...cover(wh, 1.45, 0.55, 0.35), filter: 'grayscale(0.2) contrast(1.2)' }} />
        <AbsoluteFill style={{ background: p.tint || RED, mixBlendMode: 'multiply', opacity: 0.35 }} />
      </div>
      <div style={{ position: 'absolute', top: 0, bottom: 0, left: '35%', width: 26, background: YELLOW, transform: 'skewX(-17deg)', transformOrigin: 'top' }} />
    </AbsoluteFill>
  );
};

/** White flash on a cut. */
export const Flash: React.FC<{ at?: number; len?: number; color?: string }> = ({ at = 0, len = 5, color = PAPER }) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [at, at + len], [0.95, 0], C);
  return <AbsoluteFill style={{ background: color, opacity: f < at ? 0 : o, pointerEvents: 'none' }} />;
};

/** Stacked slam words; each lands with a spring and a hard ink shadow. Returns impact frames via callback. */
export const slamFrames = (lines: string[], start = 2, gap = 6) => lines.map((_, i) => start + i * gap);

export const Slam: React.FC<{ lines: string[]; keyIdx?: number; top?: number; start?: number; gap?: number; width?: number; max?: number; color?: string; keyColor?: string; align?: 'center' | 'left' }> =
  ({ lines, keyIdx = -1, top = 520, start = 2, gap = 6, width = 960, max = 210, color = PAPER, keyColor = YELLOW, align = 'center' }) => {
    const f = useCurrentFrame();
    const { fps } = useVideoConfig();
    return (
      <div style={{ position: 'absolute', left: (W - width) / 2, width, top, display: 'flex', flexDirection: 'column', alignItems: align === 'center' ? 'center' : 'flex-start', gap: 4 }}>
        {lines.map((w, i) => {
          const at = start + i * gap;
          const s = spring({ frame: f - at, fps, config: { damping: 11, stiffness: 220, mass: 0.6 } });
          const size = fit(w, width, max);
          const isKey = i === keyIdx;
          const rot = (i % 2 ? 2.5 : -3) * (isKey ? 1.4 : 1);
          return (
            <div key={i} style={{
              fontFamily: FONT.slam, fontSize: size, lineHeight: 1.02, color: isKey ? INK : color, whiteSpace: 'nowrap',
              opacity: f < at ? 0 : 1, transform: `scale(${interpolate(s, [0, 1], [2.6, 1])}) rotate(${rot}deg)`,
              textShadow: isKey ? 'none' : `8px 8px 0 ${INK}`, ...strokeText(isKey ? 0 : 10),
              background: isKey ? keyColor : 'transparent', padding: isKey ? '6px 26px 14px' : 0,
              boxShadow: isKey ? `10px 10px 0 ${INK}` : 'none',
            }}>{w}</div>
          );
        })}
      </div>
    );
  };

/** Huge outlined katakana sound effect behind the type. */
export const Sfx: React.FC<{ text?: string; at?: number; x?: number; y?: number; size?: number; color?: string }> = ({ text, at = 0, x = 60, y = 160, size = 360, color = YELLOW }) => {
  const f = useCurrentFrame();
  if (!text) return null;
  const s = spring({ frame: f - at, fps: 30, config: { damping: 9, stiffness: 180 } });
  return (
    <div style={{
      position: 'absolute', left: x, top: y, fontFamily: FONT.slam, fontSize: size, lineHeight: 1, color: 'transparent',
      WebkitTextStroke: `7px ${color}`, transform: `rotate(-12deg) scale(${interpolate(s, [0, 1], [0.3, 1])})`, opacity: f < at ? 0 : 0.9,
      textShadow: `0 0 0 ${INK}`, filter: `drop-shadow(8px 8px 0 ${INK})`, letterSpacing: -20,
    }}>{text}</div>
  );
};

/** Mono tag chip, e.g. theory author. */
export const Tag: React.FC<{ text?: string; at?: number; top?: number; bg?: string; color?: string }> = ({ text, at = 10, top = 300, bg = PAPER, color = INK }) => {
  const f = useCurrentFrame();
  if (!text) return null;
  const x = lin(f, at, at + 9, -700, 0);
  return (
    <div style={{ position: 'absolute', left: 60, top, transform: `translateX(${x}px) rotate(-2deg)`, background: bg, color, fontFamily: FONT.mono, fontWeight: 700,
      fontSize: 44, padding: '12px 26px', boxShadow: `8px 8px 0 ${INK}`, letterSpacing: 2 }}>{text}</div>
  );
};

/** Rubber stamp that lands rotated. */
export const Stamp: React.FC<{ text: string; color: string; at?: number; size?: number; rot?: number; style?: React.CSSProperties }> = ({ text, color, at = 8, size = 96, rot = -9, style }) => {
  const f = useCurrentFrame();
  const s = spring({ frame: f - at, fps: 30, config: { damping: 12, stiffness: 260, mass: 0.5 } });
  return (
    <div style={{
      fontFamily: FONT.slam, fontSize: size, color, border: `${Math.round(size / 10)}px solid ${color}`, padding: `${size * 0.08}px ${size * 0.3}px`,
      borderRadius: 14, transform: `rotate(${rot}deg) scale(${interpolate(s, [0, 1], [2.4, 1])})`, opacity: f < at ? 0 : 0.92,
      mixBlendMode: 'multiply', letterSpacing: 4, lineHeight: 1.05, whiteSpace: 'nowrap', ...style,
    }}>{text}</div>
  );
};

export const out_ = out;
