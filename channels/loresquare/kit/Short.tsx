// LoreShort: shots from props + always-on layer (progress, logo, credit, claim chip, word captions).
import React, { useEffect, useState } from 'react';
import { AbsoluteFill, Sequence, continueRender, delayRender, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { Scene, Shot } from './scenes';
import { CLAIM, CREDIT, FONT, INK, PAPER, RED, W, YELLOW, strokeText } from './tokens';

export type Word = { w: string; s: number; e: number; l: string };
export type ShortProps = { w: number; h: number; fps: number; duration: number; shots: Shot[]; words: Word[]; credit: string };

const useFonts = () => {
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const l = document.createElement('link');
    l.rel = 'stylesheet';
    l.href = staticFile('fonts/fonts.css');
    l.onload = () => {
      Promise.all([
        document.fonts.load('400 100px "Dela Gothic One"', 'ABC0123%?ドンゴ'),
        document.fonts.load('900 60px "Inter"', 'ABC'),
        document.fonts.load('800 60px "Inter"', 'ABC'),
        document.fonts.load('700 40px "JetBrains Mono"', 'ABC·'),
      ]).then(() => document.fonts.ready).then(() => continueRender(h));
    };
    l.onerror = () => continueRender(h);
    document.head.appendChild(l);
  }, [h]);
};

/** Caption chunks: up to 3 words, broken at punctuation, never across lines. */
const chunks = (words: Word[]) => {
  const out: Word[][] = [];
  let g: Word[] = [];
  words.forEach((x, i) => {
    g.push(x);
    const next = words[i + 1];
    if (g.length === 3 || /[.,?!:;]$/.test(x.w) || !next || next.l !== x.l) { out.push(g); g = []; }
  });
  return out;
};

const Captions: React.FC<{ words: Word[] }> = ({ words }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  const cs = chunks(words);
  const i = cs.findIndex((g, k) => t >= g[0].s && t < (cs[k + 1] && cs[k + 1][0].l === g[0].l ? cs[k + 1][0].s : g[g.length - 1].e + 0.2));
  if (i < 0) return null;
  const g = cs[i];
  const pop = spring({ frame: f - Math.round(g[0].s * fps), fps, config: { damping: 12, stiffness: 300, mass: 0.5 } });
  return (
    <div style={{ position: 'absolute', left: 50, right: 50, top: 1250, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', columnGap: 36, rowGap: 0, transform: `scale(${0.8 + 0.2 * pop})` }}>
      {g.map((x, k) => {
        const on = t >= x.s && t < x.e;
        return (
          <span key={k} style={{
            display: 'inline-block', fontFamily: FONT.ui, fontWeight: 900, fontSize: 78, lineHeight: 1.15, textTransform: 'uppercase',
            color: on ? YELLOW : PAPER, transform: `scale(${on ? 1.06 : 1}) rotate(${on ? -2 : 0}deg)`, ...strokeText(14), textShadow: `6px 6px 0 ${INK}`,
          }}>{x.w.replace(/[,.;:]$/, '')}</span>
        );
      })}
    </div>
  );
};

const Chrome: React.FC<{ p: ShortProps }> = ({ p }) => {
  const f = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = f / fps;
  const shot = p.shots.find((s) => t >= s.from && t < s.from + s.dur) || p.shots[p.shots.length - 1];
  const sf = Math.round(shot.from * fps);
  const meta = shot.claim ? CLAIM[shot.claim] : null;
  const ch = shot.params.media_chapter ? `CH. ${shot.params.media_chapter}` : shot.params.media_volume ? `VOL. ${shot.params.media_volume}` : '';
  const chip = spring({ frame: f - sf - 4, fps, config: { damping: 12, stiffness: 260 } });
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <div style={{ position: 'absolute', left: 0, top: 0, height: 10, width: (W * f) / durationInFrames, background: RED }} />
      <div style={{ position: 'absolute', left: 44, top: 60, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ alignSelf: 'flex-start', background: INK, padding: '8px 16px', fontFamily: FONT.slam, fontSize: 34, color: PAPER, boxShadow: `5px 5px 0 ${YELLOW}` }}>
          LORE<span style={{ color: YELLOW }}>SQUARE</span></div>
        <div style={{ fontFamily: FONT.mono, fontWeight: 700, fontSize: 24, color: PAPER, opacity: 0.9, textShadow: `2px 2px 0 ${INK}` }}>
          {CREDIT}{ch ? ` · ${ch}` : ''}</div>
      </div>
      {meta && (
        <div style={{ position: 'absolute', left: 0, right: 0, top: 1175, display: 'flex', justifyContent: 'center' }}>
          <div style={{ transform: `scale(${chip})`, background: meta.color, color: PAPER, fontFamily: FONT.mono, fontWeight: 700, fontSize: 30, letterSpacing: 4,
            padding: '6px 18px', border: `4px solid ${INK}`, boxShadow: `5px 5px 0 ${INK}` }}>
            {meta.label}{shot.chapters && shot.chapters.length ? ` · CH. ${shot.chapters.join(', ')}` : ''}</div>
        </div>
      )}
      <Captions words={p.words} />
    </AbsoluteFill>
  );
};

export const LoreShort: React.FC<ShortProps> = (p) => {
  useFonts();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: INK }}>
      {p.shots.map((s) => {
        const from = Math.round(s.from * fps);
        const d = Math.max(1, Math.round((s.from + s.dur) * fps) - from);
        return (
          <Sequence key={s.id} from={from} durationInFrames={d}>
            <Scene s={s} d={d} />
          </Sequence>
        );
      })}
      <Chrome p={p} />
    </AbsoluteFill>
  );
};
