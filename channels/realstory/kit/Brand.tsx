// Brand primitives: corner brackets, typed mono tags, blueprint grid, vignette, grain, underline, hand note, frame.
import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import { AMBER, C, DISP, FONT, GROUND, INK, MUTED, NAVY, NAVY2, RED, TINT, io, rgba } from './tokens';

// Amber corner brackets. p: 0→1 (use a spring). Brackets fly in from outside the box.
export const Corners: React.FC<{ x: number; y: number; w: number; h: number; p: number; len?: number; color?: string; width?: number }> = ({ x, y, w, h, p, len = 46, color = AMBER, width = 6 }) => {
  if (true) return null; // Real Story: no brackets or frames (brand book, 'no plates')
  const o = (1 - p) * 60; const a = Math.min(1, p * 2);
  const d = `M${x - o} ${y - o + len} L${x - o} ${y - o} L${x - o + len} ${y - o} M${x + w + o - len} ${y - o} L${x + w + o} ${y - o} L${x + w + o} ${y - o + len} M${x + w + o} ${y + h + o - len} L${x + w + o} ${y + h + o} L${x + w + o - len} ${y + h + o} M${x - o + len} ${y + h + o} L${x - o} ${y + h + o} L${x - o} ${y + h + o - len}`;
  return <path d={d} fill="none" stroke={color} strokeWidth={width} strokeLinecap="square" opacity={a} />;
};
// Same, as a standalone overlay layer.
export const CornersLayer: React.FC<React.ComponentProps<typeof Corners>> = (p) => {
  const { width, height } = useVideoConfig();
  return <svg width={width} height={height} style={{ position: 'absolute', inset: 0 }}><Corners {...p} /></svg>;
};

// Typed IBM Plex Mono tag (2 chars/frame + block cursor). align='right' → x is the right edge.
export const Tag: React.FC<{ text: string; f0: number; x: number; y: number; size?: number; color?: string; align?: 'left' | 'right' }> = ({ text, f0, x, y, size = 22, color = MUTED, align = 'left' }) => {
  const frame = useCurrentFrame(); const { width } = useVideoConfig();
  const n = Math.floor(interpolate(frame, [f0, f0 + text.length * 0.5], [0, text.length], C));
  return <div style={{ position: 'absolute', left: align === 'left' ? x : undefined, right: align === 'right' ? width - x : undefined, top: y, fontFamily: FONT.mono, fontSize: size, letterSpacing: 3, color, whiteSpace: 'pre' }}>{text.slice(0, n)}{n < text.length && n > 0 ? '▍' : ''}</div>;
};
// Chapter tag top-left ("02  THE CROSSING") and the source line bottom-left. Use BOTH in every scene.
export const ChapterTag: React.FC<{ n: number; title: string; f0?: number }> = ({ n, title, f0 = 10 }) => { const { width } = useVideoConfig(); const m = width < 1200 ? 70 : 60; return <Tag text={`${String(n).padStart(2, '0')}  ${title.toUpperCase()}`} f0={f0} x={m} y={width < 1200 ? 230 : 60} size={20} color={AMBER} />; };
export const SourceLine: React.FC<{ text: string; f0?: number }> = ({ text, f0 = 20 }) => { const { width, height } = useVideoConfig(); return <Tag text={text.toUpperCase()} f0={f0} x={width < 1200 ? 70 : 60} y={width < 1200 ? height - 470 : height - 60} size={17} />; };

export const Grid: React.FC<{ opacity?: number; shift?: number }> = ({ opacity = 1, shift = 0 }) => {
  const { width, height } = useVideoConfig();
  return (
    <svg width={width} height={height} style={{ position: 'absolute', opacity }}>
      <defs><pattern id="psg1" width="40" height="40" patternUnits="userSpaceOnUse" x={shift} y={shift * 0.4}><path d="M40 0 L0 0 0 40" fill="none" stroke={rgba(TINT, 0.06)} strokeWidth={1} /></pattern>
        <pattern id="psg2" width="200" height="200" patternUnits="userSpaceOnUse" x={shift} y={shift * 0.4}><path d="M200 0 L0 0 0 200" fill="none" stroke={rgba(TINT, 0.12)} strokeWidth={1.2} /></pattern></defs>
      <rect width={width} height={height} fill="url(#psg1)" /><rect width={width} height={height} fill="url(#psg2)" />
    </svg>
  );
};
export const Vignette = () => <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 55%, ${rgba(GROUND, 0.7)} 100%)`, pointerEvents: 'none' }} />;
export const Grain: React.FC<{ opacity?: number }> = ({ opacity = 0.06 }) => { const f = useCurrentFrame(); return <AbsoluteFill style={{ pointerEvents: 'none', opacity, mixBlendMode: 'overlay', backgroundImage: `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' seed='${f % 12}'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>")` }} />; };

// Scene background: radial navy + drifting grid. Put scene content as children.
export const SceneBg: React.FC<{ children?: React.ReactNode; at?: string; core?: string; gridOpacity?: number; drift?: number; style?: React.CSSProperties }> = ({ children, at = '50% 45%', core = NAVY, gridOpacity = 0, drift = 0.3, style }) => {
  const f = useCurrentFrame();
  return <AbsoluteFill style={{ background: `radial-gradient(ellipse at ${at}, ${core} 0%, ${NAVY2} 78%)`, ...style }}><Grid opacity={gridOpacity} shift={f * drift} />{children}</AbsoluteFill>;
};
// Wrap the whole composition: vignette + grain on top of everything.
export const Finish: React.FC<{ children: React.ReactNode }> = ({ children }) => <AbsoluteFill style={{ backgroundColor: NAVY2 }}>{children}<Vignette /><Grain /></AbsoluteFill>;

// Red "underlined in the document" stroke. Draws from left over [f0, f0+20].
export const Underline: React.FC<{ x: number; y: number; w: number; f0: number; width?: number; color?: string }> = ({ x, y, w, f0, width = 8, color = RED }) => {
  const f = useCurrentFrame(); const { width: W, height: H } = useVideoConfig(); const p = interpolate(f, [f0, f0 + 20], [0, 1], { ...C, easing: io });
  return <svg width={W} height={H} style={{ position: 'absolute', inset: 0 }}><line x1={x} y1={y} x2={x + w * p} y2={y} stroke={color} strokeWidth={width} strokeLinecap="round" /></svg>;
};

// Handwritten Caveat note revealed left→right like writing.
// WHY THE PADDING: Caveat glyphs overhang their own box (the swash of "e", "f", ascenders). clip-path is
// measured against the element's border box, so without padding the "fully revealed" state still cuts
// the last letter and the tops. Keep the padding (or bigger) whenever you change size/rotation.
export const HandNote: React.FC<{ lines: string[]; x: number; y: number; f0: number; dur?: number; size?: number; color?: string; rotate?: number; align?: 'left' | 'right' }> = ({ lines, x, y, f0, dur, size = 58, color = AMBER, rotate = -4, align = 'left' }) => {
  const f = useCurrentFrame(); const { width } = useVideoConfig();
  const chars = lines.join('').length; const d = dur ?? Math.max(20, Math.round(chars * 1.3));
  const w = interpolate(f, [f0, f0 + d], [0, 1], C);
  const pad = Math.round(size * 0.35);
  return <div style={{ position: 'absolute', left: align === 'left' ? x - pad * 0.5 : undefined, right: align === 'right' ? width - x - pad : undefined, top: y - pad * 0.4, padding: `${pad * 0.4}px ${pad}px ${pad * 0.5}px ${pad * 0.5}px`, lineHeight: 0.95, textAlign: align, fontFamily: FONT.hand, fontWeight: 700, fontSize: size, color, clipPath: `inset(0 ${100 - w * 100}% 0 0)`, transform: `rotate(${rotate}deg)`, transformOrigin: 'left center', whiteSpace: 'nowrap' }}>{lines.map((l, i) => <div key={i}>{l}</div>)}</div>;
};

// Masked line reveal for big Oswald headlines (each line slides up from behind a mask).
export const RevealLines: React.FC<{ lines: string[]; top: number; f0: number; size?: number; gap?: number; colors?: string[]; step?: number; letterSpacing?: number }> = ({ lines, top, f0, size = 150, gap, colors = [], step = 9, letterSpacing = 8 }) => {
  const f = useCurrentFrame(); const lh = gap ?? size;
  return <>{lines.map((w, i) => { const p = interpolate(f, [f0 + i * step, f0 + 18 + i * step], [0, 1], { ...C, easing: (t) => 1 - Math.pow(1 - t, 4) }); return (
    <div key={i} style={{ position: 'absolute', left: 0, right: 0, top: top + i * lh, height: lh, overflow: 'hidden', textAlign: 'center' }}>
      <div style={{ ...DISP(size), lineHeight: `${lh}px`, color: colors[i] ?? INK, transform: `translateY(${(1 - p) * lh}px)` }}>{w}</div>
    </div>); })}</>;
};
