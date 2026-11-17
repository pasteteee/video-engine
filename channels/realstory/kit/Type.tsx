// Real Story motion typography. No plates, no frames: the words are the animation.
import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { ACCENT_EP, BONE, C, DISP, FONT, MUTED, SHADOW, SIGNAL, TINT, exitE, io, out } from './tokens';

const ease4 = (t: number) => 1 - Math.pow(1 - t, 4);

// The stop block that ends the wordmark: signal red, 0.34em × 0.7em on the baseline.
export const StopBlock: React.FC<{ size: number; p?: number }> = ({ size, p = 1 }) =>
  <span style={{ display: 'inline-block', width: 0.3 * size * p, height: 0.68 * size, marginLeft: 0.07 * size, background: SIGNAL, verticalAlign: 'baseline', transform: 'translateY(0.02em)' }} />;

// Unredact: a red bar covers each line, then slides off to the right; on the last line it
// stays as the stop block. f0: start frame. Lines are left-aligned at x, or centred when x is undefined.
export const Unredact: React.FC<{ lines: string[]; top: number; size: number; f0: number; x?: number; colors?: string[]; step?: number; stop?: boolean; exitAt?: number }> =
  ({ lines, top, size, f0, x, colors = [], step = 6, stop = true, exitAt }) => {
    const f = useCurrentFrame(); const lh = size * 0.98;
    const ex = exitAt ? interpolate(f, [exitAt, exitAt + 8], [0, 1], { ...C, easing: exitE }) : 0;
    return <div style={{ position: 'absolute', left: x ?? 0, right: x === undefined ? 0 : undefined, top, textAlign: x === undefined ? 'center' : 'left', opacity: 1 - ex, transform: `translateY(${-ex * 30}px)` }}>
      {lines.map((t, i) => {
        const a = f0 + i * step; const last = i === lines.length - 1 && stop;
        const cover = interpolate(f, [a, a + 9], [0, 1], { ...C, easing: out });
        const lift = interpolate(f, [a + 13, a + 25], [0, 1], { ...C, easing: io });
        const shown = f >= a + 9;
        const gap = 0.07, sw = 0.3;
        const left = `calc(${lift * 100}% + ${lift * gap}em)`;
        const width = last ? `calc(${(cover - lift) * 100}% + ${lift * sw}em)` : `calc(${Math.max(0, cover - lift) * 100}%)`;
        return <div key={i} style={{ height: lh, lineHeight: `${lh}px` }}>
          <span style={{ position: 'relative', display: 'inline-block', ...DISP(size), lineHeight: `${lh}px`, color: colors[i] ?? BONE, textShadow: SHADOW }}>
            <span style={{ opacity: shown ? 1 : 0 }}>{t}</span>
            <span style={{ position: 'absolute', top: '0.13em', height: '0.68em', left, width, background: SIGNAL }} />
          </span>
          {last ? <span style={{ display: 'inline-block', width: (gap + sw) * size }} /> : null}
        </div>;
      })}
    </div>;
  };

// Kinetic words. Variants:
//  rise_narrow   — each word rises from a mask and narrows from wdth 100 to 62
//  stagger_weight — words land light (wght 200, wide tracking) and settle heavy
export const Kinetic: React.FC<{ lines: string[][]; top: number; size: number; f0: number; variant: string; accent?: [number, number]; step?: number; x?: number; exitAt?: number }> =
  ({ lines, top, size, f0, variant, accent, step = 4, x, exitAt }) => {
    const f = useCurrentFrame(); const lh = size * 0.98; let k = 0;
    const ex = exitAt ? interpolate(f, [exitAt, exitAt + 8], [0, 1], { ...C, easing: exitE }) : 0;
    return <div style={{ position: 'absolute', left: x ?? 0, right: x === undefined ? 0 : undefined, top, opacity: 1 - ex, transform: `translateY(${-ex * 40}px)` }}>
      {lines.map((ws, li) => <div key={li} style={{ display: 'flex', justifyContent: x === undefined ? 'center' : 'flex-start', gap: size * 0.2, height: lh }}>
        {ws.map((w, wi) => {
          const a = f0 + (k++) * step; const p = interpolate(f, [a, a + 16], [0, 1], { ...C, easing: ease4 });
          const col = accent && accent[0] === li && accent[1] === wi ? ACCENT_EP : BONE;
          if (variant === 'stagger_weight') {
            const wg = 200 + 660 * p; const tr = 0.18 * (1 - p);
            return <span key={wi} style={{ ...DISP(size, 62 + 20 * (1 - p), wg), lineHeight: `${lh}px`, letterSpacing: `${tr}em`, color: col, opacity: Math.min(1, p * 3), textShadow: SHADOW }}>{w}</span>;
          }
          return <span key={wi} style={{ display: 'inline-block', overflow: 'hidden', height: lh + size * 0.08 }}>
            <span style={{ display: 'inline-block', ...DISP(size, 100 - 38 * p), lineHeight: `${lh}px`, color: col, transform: `translateY(${(1 - p) * 105}%)`, textShadow: SHADOW }}>{w}</span>
          </span>;
        })}
      </div>)}
    </div>;
  };

// Odometer: each digit column rolls through 0–9 and lands; higher columns roll more.
export const Odometer: React.FC<{ value: number; size: number; f0: number; dur?: number; color?: string }> = ({ value, size, f0, dur = 26, color = BONE }) => {
  const f = useCurrentFrame(); const s = value.toLocaleString('en-US'); const lh = size * 0.86;
  const digits = s.split(''); let col = 0; const nd = digits.filter((c) => /\d/.test(c)).length;
  return <span style={{ display: 'inline-flex', ...DISP(size, 62, 880), lineHeight: `${lh}px`, height: lh, overflow: 'hidden', color, fontVariantNumeric: 'tabular-nums', textShadow: SHADOW }}>
    {digits.map((c, i) => {
      if (!/\d/.test(c)) return <span key={i}>{c}</span>;
      const d = +c; const turns = nd - col; const a = f0 + col * 3; col++;
      const p = interpolate(f, [a, a + dur], [0, 1], { ...C, easing: out });
      const pos = (turns * 10 + d) * p; const base = Math.floor(pos);
      const show = [base, base + 1].map((n) => n % 10);
      return <span key={i} style={{ display: 'inline-block', height: lh, overflow: 'hidden' }}>
        <span style={{ display: 'flex', flexDirection: 'column', transform: `translateY(${-(pos - base) * lh}px)`, filter: p < 1 ? `blur(${Math.min(3, (1 - p) * 6)}px)` : undefined }}>
          {show.map((n, j) => <span key={j} style={{ height: lh }}>{n}</span>)}</span></span>;
    })}
  </span>;
};

// Mono line typed on (2 chars/frame). Used for stamps and sources.
export const Mono: React.FC<{ text: string; f0: number; size?: number; color?: string; style?: React.CSSProperties; weight?: number }> = ({ text, f0, size = 26, color = MUTED, style, weight = 500 }) => {
  const f = useCurrentFrame(); const n = Math.floor(interpolate(f, [f0, f0 + text.length / 2], [0, text.length], C));
  return <div style={{ fontFamily: FONT.mono, fontWeight: weight, fontSize: size, letterSpacing: '0.12em', textTransform: 'uppercase', color, whiteSpace: 'pre', textShadow: SHADOW, ...style }}>{text.slice(0, n)}<span style={{ opacity: 0 }}>{text.slice(n)}</span></div>;
};

// Hairline that draws left→right (chapter baselines, rules).
export const Hairline: React.FC<{ x: number; y: number; w: number; f0: number; color?: string; dur?: number; h?: number }> = ({ x, y, w, f0, color = TINT, dur = 22, h = 2 }) => {
  const f = useCurrentFrame(); const p = interpolate(f, [f0, f0 + dur], [0, 1], { ...C, easing: io });
  return <div style={{ position: 'absolute', left: x, top: y, width: w * p, height: h, background: color, opacity: 0.8 }} />;
};

// Callout on a photo: a leader line from the detail to the label. No plate.
export const Callout: React.FC<{ text: string; sub?: string; at: [number, number]; label: [number, number]; f0: number; size?: number; color?: string }> = ({ text, sub, at, label, f0, size = 58, color = BONE }) => {
  const f = useCurrentFrame();
  const dot = interpolate(f, [f0, f0 + 8], [0, 1], { ...C, easing: out });
  const line = interpolate(f, [f0 + 4, f0 + 20], [0, 1], { ...C, easing: io });
  const tp = interpolate(f, [f0 + 14, f0 + 28], [0, 1], { ...C, easing: out });
  const elbow: [number, number] = [label[0] + (at[0] > label[0] ? 40 : -40), label[1] + size * 0.95 + 14];
  const pts = [at, [elbow[0], elbow[1]], [label[0], elbow[1]]];
  const len = Math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]) + Math.abs(pts[2][0] - pts[1][0]);
  return <>
    <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0, filter: `drop-shadow(0 0 6px rgba(0,0,0,0.6))` }}>
      <circle cx={at[0]} cy={at[1]} r={9 * dot} fill="none" stroke={color} strokeWidth={3} />
      <polyline points={pts.map((p) => p.join(',')).join(' ')} fill="none" stroke={color} strokeWidth={2.5} strokeDasharray={len} strokeDashoffset={len * (1 - line)} />
    </svg>
    <div style={{ position: 'absolute', left: Math.min(label[0], elbow[0] < label[0] ? elbow[0] : label[0]), top: label[1], opacity: tp, transform: `translateY(${(1 - tp) * 14}px)` }}>
      <div style={{ ...DISP(size, 75, 760), color, textShadow: SHADOW }}>{text}</div>
      {sub ? <div style={{ fontFamily: FONT.mono, fontSize: 22, letterSpacing: '0.12em', color: MUTED, marginTop: 30, textShadow: SHADOW }}>{sub}</div> : null}
    </div>
  </>;
};
