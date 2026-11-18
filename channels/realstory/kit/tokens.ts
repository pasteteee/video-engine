// Real Story — design tokens. Channel neutrals are fixed; ground and accent come from the episode
import React from 'react';
// (`shotlist.look`, made by `vengine look`). Never hard-code colours or easings in a scene.
import { Easing } from 'remotion';
import SL from '../ep/shotlist.json';

const LOOK = { ground: '#0e0f11', ground_2: '#1b1d21', accent: '#e8b430', tint: '#a4a199', ...((SL as any).look ?? {}) };
const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const mix = (a: string, b: string, t: number) => '#' + hex(a).map((v, i) => Math.round(v + (hex(b)[i] - v) * t).toString(16).padStart(2, '0')).join('');
export const rgba = (h: string, a: number) => `rgba(${hex(h).join(',')},${a})`;

// channel (never change per episode)
export const INK_BLACK = '#0e0f11';
export const BONE = '#f2efe8';
export const PAPER = '#ece8df';
export const SIGNAL = '#e2231a';
export const MUTED = '#a4a199';
// episode
export const GROUND = LOOK.ground;
export const GROUND2 = LOOK.ground_2;
export const ACCENT_EP = LOOK.accent;
export const TINT = LOOK.tint;

// legacy names used by the scene library, mapped onto the new system
export const NAVY = GROUND2;
export const NAVY2 = GROUND;
export const SEA = mix(GROUND, GROUND2, 0.5);
export const LAND = mix(GROUND2, TINT, 0.18);
export const LINE = rgba(TINT, 0.7);
export const AMBER = ACCENT_EP;
export const RED = SIGNAL;
export const ROUTE = ACCENT_EP;
export const ACCENT = {} as Record<string, string>;

export const C = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
export const io = Easing.bezier(0.65, 0, 0.35, 1);
export const out = Easing.bezier(0.2, 0.8, 0.1, 1);
export const exitE = Easing.bezier(0.7, 0, 0.84, 0);
export const travel = Easing.bezier(0.45, 0, 0.55, 1);
export const SPRING_SOFT = { damping: 18, stiffness: 120 };
export const SPRING_PIN = { damping: 9, stiffness: 140 };

export const FONT = { display: 'Archivo', mono: 'Plex', hand: 'Caveat', quote: 'Newsreader' } as const;
// Display style: Archivo condensed heavy, uppercase. wdth can be animated (62 = channel width).
export const DISP = (size: number, wdth = 62, wght = 840): React.CSSProperties => ({
  fontFamily: FONT.display, fontSize: size, fontWeight: wght, fontStretch: `${wdth}%`, fontVariationSettings: `'wdth' ${wdth}`,
  textTransform: 'uppercase', letterSpacing: '-0.005em', lineHeight: 0.9,
});
// Legibility without plates: a soft shadow in the ground colour.
const SHADOW_OF = (c: string) => `0 2px 28px ${rgba(c, 0.85)}, 0 0 4px ${rgba(c, 0.5)}`;
// Light episodes (look.mode = "light"): graphics are set in ink on the pale episode ground; real media keep
// bone type over a dark scrim taken from the photos (look.scrim). Dark episodes: both are the old bone-on-ground.
export const LIGHT = LOOK.mode === 'light';
export const SCRIM: string = LIGHT ? (LOOK.scrim ?? '#0d1620') : GROUND;
export type Ink = { fg: string; muted: string; shadow: string; accent: string; scrim: string };
export const INK_GROUND: Ink = LIGHT
  ? { fg: LOOK.fg ?? '#111a24', muted: LOOK.muted ?? '#56636f', shadow: `0 0 26px ${rgba(GROUND, 0.95)}, 0 0 6px ${rgba(GROUND, 0.7)}`, accent: ACCENT_EP, scrim: GROUND }
  : { fg: BONE, muted: MUTED, shadow: SHADOW_OF(GROUND), accent: ACCENT_EP, scrim: GROUND };
export const INK_PHOTO: Ink = { fg: BONE, muted: LIGHT ? '#c3cad1' : MUTED, shadow: SHADOW_OF(SCRIM), accent: LOOK.accent_on_photo ?? ACCENT_EP, scrim: SCRIM };
export const OnPhoto = React.createContext(false);
export const useInk = (): Ink => (React.useContext(OnPhoto) ? INK_PHOTO : INK_GROUND);
export const FG = INK_GROUND.fg;
export const FG_MUTED = INK_GROUND.muted;
export const SHADOW = INK_GROUND.shadow;
export const rng = (s: number) => () => { s |= 0; s = (s + 0x6d2b79f5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };

// legacy names that depend on the ink (defined after it)
export const INK = INK_GROUND.fg;
export const BIRD = INK_GROUND.fg;
