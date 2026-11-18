// LoreSquare "Ink" — design tokens. Fixed palette (no per-episode look).
// Scenes import colours, fonts and easings from here; never hard-code them.
import { Easing } from 'remotion';

export const RED = '#e63946';
export const YELLOW = '#ffd43b';
export const BLUE = '#1f6feb';
export const INK = '#0b0b0b';
export const PAPER = '#ffffff';
export const POSTER = '#e9dcc0';
export const WOOD = '#1d120c';

export const STAMP = { red: '#b3121f', green: '#1b6b2a', navy: '#1b3a8a' } as const;

// Epistemic status of a claim: script line `claim` → stamp colour and label.
export type Claim = 'canon' | 'inference' | 'speculation' | 'community';
export const CLAIM: Record<Claim, { color: string; label: string }> = {
  canon: { color: '#2f9e44', label: 'CANON' },
  inference: { color: '#f0b400', label: 'INFERENCE' },
  speculation: { color: '#e64980', label: 'THEORY' },
  community: { color: '#1f6feb', label: 'COMMUNITY' },
};

export const FONT = {
  slam: '"Oswald", "Rubik", sans-serif',
  poster: '"Playfair Display SC", serif',
  mono: '"PT Mono", monospace',
  caption: '"Rubik", sans-serif',
} as const;

export const CREDIT = 'One Piece © Eiichiro Oda / Shueisha';

export const C = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
export const io = Easing.bezier(0.65, 0, 0.35, 1);
export const out = Easing.bezier(0.16, 1, 0.3, 1);
export const rgba = (h: string, a: number) =>
  `rgba(${[1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)).join(',')},${a})`;
