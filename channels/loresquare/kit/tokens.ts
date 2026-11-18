// LoreSquare "Ink" for Shorts: palette, fonts, easings, small motion helpers.
import { Easing, interpolate } from 'remotion';

export const RED = '#e63946';
export const YELLOW = '#ffd43b';
export const BLUE = '#1f6feb';
export const INK = '#0b0b0b';
export const PAPER = '#ffffff';
export const POSTER = '#efe3c8';

export type Claim = 'canon' | 'inference' | 'speculation' | 'community';
export const CLAIM: Record<Claim, { color: string; label: string }> = {
  canon: { color: '#2f9e44', label: 'CANON' },
  inference: { color: '#f0b400', label: 'INFERENCE' },
  speculation: { color: '#e64980', label: 'THEORY' },
  community: { color: '#1f6feb', label: 'COMMUNITY' },
};

export const FONT = {
  slam: '"Dela Gothic One", sans-serif',
  ui: '"Inter", sans-serif',
  mono: '"JetBrains Mono", monospace',
} as const;

export const CREDIT = 'One Piece © Eiichiro Oda / Shueisha';
export const W = 1080;
export const H = 1920;

export const C = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
export const io = Easing.bezier(0.65, 0, 0.35, 1);
export const out = Easing.bezier(0.16, 1, 0.3, 1);
export const lin = (f: number, a: number, b: number, x: number, y: number, e = out) =>
  interpolate(f, [a, b], [x, y], { ...C, easing: e });

/** Camera shake after each impact frame; decays in ~10 frames. */
export const shake = (f: number, impacts: number[], amp = 22) => {
  let x = 0, y = 0;
  for (const i of impacts) {
    const d = f - i;
    if (d < 0 || d > 14) continue;
    const k = amp * Math.exp(-d / 3.5);
    x += k * Math.sin(d * 2.7 + i);
    y += k * Math.cos(d * 3.3 + i);
  }
  return `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
};

/** Font size that fits a word of `len` characters into `width` px of Dela Gothic One. */
export const fit = (text: string, width: number, max: number) =>
  Math.min(max, Math.floor(width / (Math.max(text.length, 1) * 0.94)));

export const strokeText = (px: number, color = INK): React.CSSProperties => ({
  WebkitTextStroke: `${px}px ${color}`,
  paintOrder: 'stroke fill',
});
