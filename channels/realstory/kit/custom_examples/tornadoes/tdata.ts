// Tornado episode data: NOAA SPC tornado file 1950-2022, projected (Albers USA) by build_data.mjs.
import { useEffect, useState } from 'react';
import { delayRender, continueRender, staticFile } from 'remotion';

// Track row: [yr, mag, x1, y1, x2, y2, fat, mo, st, dy, wid] in map space (W x H).
export type Track = [number, number, number, number, number, number, number, number, string, number, number];
export type Geo = { W: number; H: number; nation: string; states: Record<string, string>; places: Record<string, [number, number]>; cen: [number, number, number][] };
export type Stats = { years: number[]; all: number[]; f0: number[]; f1p: number[]; f3p: number[]; ndays: number[]; top10: number[]; deaths: number[]; deathshare: Record<string, [number, number]> };
export type Data = { T: Track[]; geo: Geo; stats: Stats; days: Record<string, number[]> };

let cache: Data | null = null; let pending: Promise<Data> | null = null;
const load = () => pending ?? (pending = Promise.all(['tracks', 'geo', 'stats', 'days'].map((n) => fetch(staticFile(`data/${n}.json`)).then((r) => r.json())))
  .then(([t, geo, stats, days]) => (cache = { T: t.T, geo, stats, days })));

export const useData = (): Data | null => {
  const [d, setD] = useState<Data | null>(cache);
  const [h] = useState(() => (cache ? null : delayRender('tornado data')));
  useEffect(() => { if (cache) { if (h !== null) continueRender(h); return; } load().then((x) => { setD(x); if (h !== null) continueRender(h); }); }, []);
  return d;
};
export const SE = ['Alabama', 'Mississippi', 'Tennessee', 'Arkansas', 'Louisiana', 'Georgia', 'Kentucky'];
export const PL = ['Texas', 'Oklahoma', 'Kansas', 'Nebraska'];
export const fmt = (n: number) => Math.round(n).toLocaleString('en-US');
