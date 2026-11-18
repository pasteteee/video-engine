// Ink primitives shared by every LoreSquare scene: claim stamp, chapter stamp,
// credit line and the panel callout (the only way a manga panel reaches the screen).
import React from 'react';
import { AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, CLAIM, CREDIT, FONT, INK, PAPER, STAMP, YELLOW, out, rgba, type Claim } from './tokens';

// Rubber stamp that slams in (scale 1.6 → 1, slight overshoot) at frame f0.
export const Stamp: React.FC<{ text: string; color?: string; f0?: number; rotate?: number; size?: number; style?: React.CSSProperties }> = ({ text, color = STAMP.red, f0 = 0, rotate = -8, size = 64, style }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const p = spring({ frame: frame - f0, fps, config: { damping: 12, stiffness: 180 } });
  return (
    <div style={{ display: 'inline-block', padding: '6px 18px', border: `6px solid ${color}`, color, fontFamily: FONT.slam, fontWeight: 700, fontSize: size, letterSpacing: 2,
      transform: `rotate(${rotate}deg) scale(${interpolate(p, [0, 1], [1.6, 1])})`, opacity: Math.min(1, p * 2), mixBlendMode: 'multiply', ...style }}>{text}</div>
  );
};

export const ChapterStamp: React.FC<{ chapter: number; page?: number; f0?: number; style?: React.CSSProperties }> = ({ chapter, page, f0, style }) =>
  <Stamp text={`CH. ${chapter}${page ? ` P. ${page}` : ''}`} f0={f0} rotate={6} size={48} style={style} />;

// Epistemic chip: every claim on screen says whether it is canon, inference, theory or community.
export const ClaimChip: React.FC<{ claim: Claim; chapter?: number; f0?: number }> = ({ claim, chapter, f0 = 0 }) => {
  const frame = useCurrentFrame();
  const a = interpolate(frame, [f0, f0 + 8], [0, 1], C);
  const { color, label } = CLAIM[claim];
  return (
    <div style={{ display: 'inline-flex', gap: 12, alignItems: 'center', padding: '6px 14px', background: color, color: claim === 'inference' ? INK : PAPER,
      fontFamily: FONT.mono, fontSize: 26, letterSpacing: 3, opacity: a, transform: `translateY(${(1 - a) * 12}px)` }}>
      {label}{chapter ? <span style={{ opacity: 0.85 }}>· CH. {chapter}</span> : null}
    </div>
  );
};

export const Credit: React.FC = () => {
  const { width, height } = useVideoConfig();
  return <div style={{ position: 'absolute', left: width < 1200 ? 60 : 48, top: height - (width < 1200 ? 90 : 46), fontFamily: FONT.mono, fontSize: 16, color: rgba(PAPER, 0.7) }}>{CREDIT}</div>;
};

// A manga panel the legal way: cropped to `focus`, slow push-in, our note on top, credit line.
// focus: crop box in panel pixels. The director keeps the shot at 3-5 s (variety group manga_panels).
export const PanelCallout: React.FC<{ src: string; panelW: number; panelH: number; focus: { x: number; y: number; w: number; h: number };
  note: string; chapter: number; page?: number; claim?: Claim; noteAt?: number; duotone?: string }> = ({ src, panelW, panelH, focus, note, chapter, page, claim = 'canon', noteAt = 18, duotone }) => {
  const frame = useCurrentFrame(); const { width, height, durationInFrames } = useVideoConfig();
  const fit = Math.min(width * 0.78 / focus.w, height * 0.7 / focus.h);
  const z = interpolate(frame, [0, durationInFrames], [1, 1.08], C);
  const s = fit * z;
  const n = interpolate(frame, [noteAt, noteAt + 10], [0, 1], { ...C, easing: out });
  return (
    <AbsoluteFill style={{ background: INK }}>
      <div style={{ position: 'absolute', left: width / 2 - (focus.x + focus.w / 2) * s, top: height * 0.42 - (focus.y + focus.h / 2) * s, width: panelW * s, height: panelH * s, overflow: 'hidden' }}>
        <Img src={src} style={{ width: '100%', height: '100%', filter: duotone ? 'grayscale(1) contrast(1.2)' : undefined }} />
        {duotone ? <AbsoluteFill style={{ background: duotone, mixBlendMode: 'multiply' }} /> : null}
      </div>
      {/* our ring on the detail */}
      <svg width={width} height={height} style={{ position: 'absolute', inset: 0 }}>
        <ellipse cx={width / 2} cy={height * 0.42} rx={focus.w * s * 0.42} ry={focus.h * s * 0.42} fill="none" stroke={YELLOW} strokeWidth={8}
          strokeDasharray={4000} strokeDashoffset={4000 * (1 - n)} />
      </svg>
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: height * 0.1, textAlign: 'center', opacity: n }}>
        <div style={{ fontFamily: FONT.slam, fontWeight: 700, fontSize: width < 1200 ? 64 : 56, color: PAPER, textShadow: `0 4px 18px ${rgba(INK, 0.8)}` }}>{note}</div>
        <div style={{ marginTop: 14 }}><ClaimChip claim={claim} chapter={chapter} f0={noteAt + 4} /></div>
      </div>
      <div style={{ position: 'absolute', right: 48, top: 48 }}><ChapterStamp chapter={chapter} page={page} f0={6} /></div>
      <Credit />
    </AbsoluteFill>
  );
};
