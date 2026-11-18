import React from 'react';
import { Composition } from 'remotion';
import { LoreShort, ShortProps } from './Short';

// Props come from the episode: `python shorts.py props` writes props/<slug>.json
// (shots with from/dur/params, words with start/end). Render with --props=props/<slug>.json.
const empty: ShortProps = { w: 1080, h: 1920, fps: 30, duration: 1, shots: [], words: [], credit: 'One Piece © Eiichiro Oda / Shueisha' };

export const Root: React.FC = () => (
  <Composition
    id="LoreShort"
    component={LoreShort as any}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={30}
    defaultProps={empty}
    calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.ceil((props as ShortProps).duration * 30)) })}
  />
);
