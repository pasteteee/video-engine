// One component per scene type from vengine/scenes.py (Shorts, 1080x1920).
import React from 'react';
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame } from 'remotion';
import { Art, BlurFill, Flash, Halftone, P, Sfx, Slam, SpeedLines, Stamp, Tag, slamFrames } from './parts';
import { BLUE, C, CLAIM, Claim, FONT, H, INK, PAPER, POSTER, RED, W, YELLOW, fit, io, lin, shake, strokeText } from './tokens';

export type Shot = { id: string; type: string; variant?: string; from: number; dur: number; params: P; claim?: Claim; chapters: number[]; line: string };
type S = React.FC<{ s: Shot; d: number }>;

const ArtBackdrop: S = ({ s, d }) => {
  const f = useCurrentFrame();
  const p = s.params;
  const lines: string[] = p.slam || [];
  const hits = slamFrames(lines, 3, 6);
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ transform: shake(f, hits, 16) }}>
        <Art p={p} dur={d} variant={s.variant} />
        <Sfx text={p.sfx} at={hits[hits.length - 1] + 2} x={s.variant === 'parallax_cut' ? 520 : 40} y={170} />
        <Slam lines={lines} keyIdx={p.key} top={lines.length > 2 ? 560 : 660} start={3} />
        <Tag text={p.tag} at={hits[hits.length - 1] + 6} top={lines.length > 2 ? 430 : 530} bg={YELLOW} />
      </AbsoluteFill>
      <Flash len={5} />
    </AbsoluteFill>
  );
};

const KineticType: S = ({ s, d }) => {
  const f = useCurrentFrame();
  const p = s.params;
  const words: string[] = p.words || [];
  const red = p.bg === 'red';
  const hits = slamFrames(words, 2, 7);
  return (
    <AbsoluteFill style={{ background: red ? RED : INK }}>
      {p.media_src && <AbsoluteFill style={{ opacity: 0.45 }}><Art p={{ ...p, tint: red ? RED : '#222' }} dur={d} variant="halftone_duotone" /></AbsoluteFill>}
      <Halftone opacity={0.18} color="255,255,255" />
      <AbsoluteFill style={{ transform: shake(f, hits, 12) }}>
        {words.map((w, i) => {
          const at = hits[i];
          const sp = spring({ frame: f - at, fps: 30, config: { damping: 13, stiffness: 200 } });
          const big = i === words.length - 1;
          const size = fit(w, 960, big ? 230 : 150);
          return (
            <div key={i} style={{
              position: 'absolute', left: 60, right: 60, top: 430 + i * 230, textAlign: i % 2 ? 'right' : 'left',
              fontFamily: FONT.slam, fontSize: size, color: big ? YELLOW : PAPER, lineHeight: 1,
              transform: `translateX(${(1 - sp) * (i % 2 ? 600 : -600)}px) skewX(${(1 - sp) * -14}deg)`, opacity: f < at ? 0 : 1,
              textShadow: `10px 10px 0 ${INK}`, ...strokeText(8),
            }}>{w}</div>
          );
        })}
      </AbsoluteFill>
      <Flash len={4} />
    </AbsoluteFill>
  );
};

const ChapterCard: S = ({ s, d }) => {
  const f = useCurrentFrame();
  const p = s.params;
  const hair = s.variant === 'hairline_index';
  const sp = spring({ frame: f - 2, fps: 30, config: { damping: 10, stiffness: 240, mass: 0.6 } });
  const lineW = lin(f, 0, 10, 0, 960, io);
  return (
    <AbsoluteFill style={{ background: hair ? INK : RED, overflow: 'hidden' }}>
      {!hair && <SpeedLines opacity={0.35} color="0,0,0" />}
      {p.media_src && (
        <div style={{ position: 'absolute', right: -40, top: 380, width: 560, height: 820, transform: `rotate(5deg) translateX(${(1 - sp) * 500}px)`,
          border: `12px solid ${PAPER}`, boxShadow: `16px 16px 0 ${INK}`, overflow: 'hidden', background: INK }}>
          <Img src={staticFile(p.media_src)} style={{ width: '100%', height: '100%', objectFit: 'cover', filter: hair ? 'grayscale(1) contrast(1.3)' : 'none' }} />
          {hair && <AbsoluteFill style={{ background: BLUE, mixBlendMode: 'color', opacity: 0.8 }} />}
        </div>
      )}
      {hair && [0, 1, 2, 3].map((i) => <div key={i} style={{ position: 'absolute', left: 60, top: 330 + i * 300, width: lineW, height: 3, background: YELLOW, opacity: 0.6 }} />)}
      <div style={{ position: 'absolute', left: 50, top: 260, fontFamily: FONT.mono, fontWeight: 700, fontSize: 56, color: hair ? YELLOW : INK, letterSpacing: 6 }}>NUMBER</div>
      <div style={{
        position: 'absolute', left: 30, top: 250, fontFamily: FONT.slam, fontSize: 980, lineHeight: 1.1,
        color: hair ? 'transparent' : YELLOW, ...(hair ? { WebkitTextStroke: `10px ${YELLOW}` } : strokeText(18)),
        textShadow: hair ? 'none' : `22px 22px 0 ${INK}`, transform: `scale(${interpolate(sp, [0, 1], [3, 1])})`, transformOrigin: '30% 50%',
      }}>{p.n}</div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 1110, background: INK, padding: '22px 60px', transform: `translateX(${lin(f, 6, 14, -1100, 0)}px)` }}>
        <div style={{ fontFamily: FONT.slam, fontSize: fit(p.title || '', 960, 96), color: PAPER }}>{p.title}</div>
      </div>
      <Flash len={4} />
    </AbsoluteFill>
  );
};

const ClaimCard: S = ({ s, d }) => {
  const f = useCurrentFrame();
  const p = s.params;
  const meta = CLAIM[(s.claim || 'speculation') as Claim];
  const enter = spring({ frame: f, fps: 30, config: { damping: 14 } });
  const words = String(p.text).split(' ');
  return (
    <AbsoluteFill style={{ background: RED, overflow: 'hidden' }}>
      {p.media_src ? <BlurFill src={p.media_src} dark={0.45} /> : <SpeedLines opacity={0.4} color="0,0,0" />}
      <AbsoluteFill style={{ transform: shake(f, [12], 18) }}>
        <div style={{ position: 'absolute', left: 70, right: 70, top: 300, padding: '70px 60px 60px', background: POSTER, boxShadow: `20px 20px 0 ${INK}`,
          transform: `translateY(${(1 - enter) * 1400}px) rotate(${-2 + (1 - enter) * -10}deg)` }}>
          <Halftone opacity={0.08} />
          <div style={{ fontFamily: FONT.mono, fontWeight: 700, fontSize: 34, color: RED, letterSpacing: 4, marginBottom: 28 }}>{p.src}</div>
          <div style={{ fontFamily: FONT.slam, fontSize: 104, lineHeight: 1.08, color: INK }}>
            {words.map((w, i) => (
              <span key={i} style={{ display: 'inline-block', marginRight: 26, opacity: f < 4 + i * 2 ? 0 : 1, transform: `translateY(${lin(f, 4 + i * 2, 10 + i * 2, 40, 0)}px)` }}>{w}</span>
            ))}
          </div>
          <div style={{ marginTop: 40, display: 'flex', justifyContent: 'flex-end' }}><Stamp text={meta.label} color={meta.color} at={12} size={100} style={{ mixBlendMode: 'normal' }} /></div>
        </div>
      </AbsoluteFill>
      <Flash len={3} />
    </AbsoluteFill>
  );
};

const QuestionCard: S = ({ s }) => {
  const f = useCurrentFrame();
  const p = s.params;
  const words = String(p.q).replace(/<br>/g, ' ').split(' ');
  return (
    <AbsoluteFill style={{ background: YELLOW, overflow: 'hidden' }}>
      <Halftone opacity={0.22} size={12} />
      <div style={{ position: 'absolute', left: 60, top: 300, fontFamily: FONT.slam, fontSize: 900, color: RED, opacity: 0.18, lineHeight: 1 }}>?</div>
      <div style={{ position: 'absolute', left: 60, right: 60, top: 380 }}>
        {words.map((w, i) => {
          const at = 2 + i * 4;
          const fs = Math.min(fit(w, 960, 190), Math.floor(640 / (words.length * 1.12)));
          return (
            <div key={i} style={{ overflow: 'hidden', height: fs * 1.12 }}>
              <div style={{ fontFamily: FONT.slam, fontSize: fs, lineHeight: 1.12, color: INK, transform: `translateY(${lin(f, at, at + 8, 110, 0)}%)` }}>{w}</div>
            </div>
          );
        })}
      </div>
      {p.sub && <div style={{ position: 'absolute', left: 60, top: 1060, background: INK, color: YELLOW, fontFamily: FONT.mono, fontWeight: 700, fontSize: 42, padding: '14px 24px',
        letterSpacing: 3, transform: `translateX(${lin(f, 14, 22, -900, 0)}px)` }}>{p.sub}</div>}
      <Flash len={4} />
    </AbsoluteFill>
  );
};

const ArgumentDuel: S = ({ s }) => {
  const f = useCurrentFrame();
  const p = s.params;
  const a = spring({ frame: f, fps: 30, config: { damping: 15 } });
  const b = spring({ frame: f - 14, fps: 30, config: { damping: 15 } });
  const card = (label: string, text: string, color: string, k: number, dir: number, top: number) => (
    <div style={{ position: 'absolute', left: 60, right: 60, top, background: POSTER, borderLeft: `26px solid ${color}`, padding: '40px 48px', boxShadow: `16px 16px 0 ${INK}`,
      transform: `translateX(${(1 - k) * 1200 * dir}px) rotate(${dir * -1.5}deg)` }}>
      <div style={{ fontFamily: FONT.mono, fontWeight: 700, fontSize: 38, color, letterSpacing: 6, marginBottom: 14 }}>{label}</div>
      <div style={{ fontFamily: FONT.slam, fontSize: fit(text.split(' ').reduce((x, y) => (y.length > x.length ? y : x), ''), 820, 92), lineHeight: 1.08, color: INK }}>{text}</div>
    </div>
  );
  const vs = spring({ frame: f - 10, fps: 30, config: { damping: 8, stiffness: 260 } });
  return (
    <AbsoluteFill style={{ background: INK }}>
      <SpeedLines opacity={0.18} cy={52} />
      <AbsoluteFill style={{ transform: shake(f, [12, 26], 14) }}>
        {card('FOR', p.for, '#2f9e44', a, -1, 260)}
        {card('AGAINST', p.against, RED, b, 1, 760)}
        <div style={{ position: 'absolute', left: W / 2 - 100, top: 590, width: 200, height: 200, borderRadius: 100, background: YELLOW, border: `10px solid ${INK}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT.slam, fontSize: 92, color: INK, transform: `scale(${vs}) rotate(-10deg)` }}>VS</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Meter: S = ({ s, d }) => {
  const f = useCurrentFrame();
  const p = s.params;
  const was: number = p.was, now: number = p.now;
  const k = lin(f, 4, Math.min(d - 6, 36), 0, 1, io);
  const v = Math.round(was + (now - was) * k);
  const big = (
    <div style={{ fontFamily: FONT.slam, fontSize: 330, color: YELLOW, lineHeight: 1, ...strokeText(12), textShadow: `16px 16px 0 ${INK}` }}>
      {v}<span style={{ fontSize: 170 }}>%</span>
    </div>
  );
  const label = (
    <div style={{ fontFamily: FONT.mono, fontWeight: 700, fontSize: 40, color: PAPER, letterSpacing: 5 }}>COMMUNITY CONFIDENCE</div>
  );
  let body: React.ReactNode;
  if (s.variant === 'history_line') {
    const hist: number[] = p.hist || [was, now];
    const x0 = 80, x1 = 1000, y0 = 1130, y1 = 760;
    const lo = Math.min(...hist) - 6, hi = Math.max(...hist) + 4;
    const pts = hist.map((h, i) => [x0 + ((x1 - x0) * i) / (hist.length - 1), y0 - ((h - lo) / (hi - lo)) * (y0 - y1)]);
    const path = pts.map((q, i) => `${i ? 'L' : 'M'}${q[0].toFixed(1)},${q[1].toFixed(1)}`).join(' ');
    const len = 2400;
    const last = pts[pts.length - 1];
    body = (
      <>
        <div style={{ position: 'absolute', left: 70, top: 260 }}>{label}<div style={{ marginTop: 10 }}>{big}</div></div>
        <svg width={W} height={H} style={{ position: 'absolute', inset: 0 }}>
          {[0, 1, 2, 3].map((i) => <line key={i} x1={x0} x2={x1} y1={y1 + i * 123} y2={y1 + i * 123} stroke="rgba(255,255,255,0.15)" strokeWidth={2} />)}
          <path d={path} fill="none" stroke={INK} strokeWidth={26} strokeLinejoin="round" strokeDasharray={len} strokeDashoffset={len * (1 - k)} transform="translate(8 8)" />
          <path d={path} fill="none" stroke={YELLOW} strokeWidth={18} strokeLinejoin="round" strokeLinecap="round" strokeDasharray={len} strokeDashoffset={len * (1 - k)} />
          {k > 0.98 && <circle cx={last[0]} cy={last[1]} r={26 * spring({ frame: f - 36, fps: 30 })} fill={RED} stroke={INK} strokeWidth={8} />}
          <text x={x0} y={y0 + 70} fill={PAPER} fontFamily="JetBrains Mono" fontWeight={700} fontSize={34}>LAUNCH {hist[0]}%</text>
          <text x={x1} y={y0 + 70} fill={YELLOW} fontFamily="JetBrains Mono" fontWeight={700} fontSize={34} textAnchor="end">NOW {now}%</text>
        </svg>
      </>
    );
  } else if (s.variant === 'gauge') {
    const r = 380, cx = W / 2, cy = 860;
    const arc = Math.PI * r;
    const ang = -180 + 180 * (v / 100);
    body = (
      <>
        <div style={{ position: 'absolute', left: 0, right: 0, top: 250, textAlign: 'center' }}>{label}</div>
        <svg width={W} height={H} style={{ position: 'absolute', inset: 0 }}>
          <path d={`M${cx - r},${cy} A${r},${r} 0 0 1 ${cx + r},${cy}`} fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth={70} />
          <path d={`M${cx - r},${cy} A${r},${r} 0 0 1 ${cx + r},${cy}`} fill="none" stroke={YELLOW} strokeWidth={70} strokeDasharray={arc} strokeDashoffset={arc * (1 - v / 100)} />
          <line x1={cx} y1={cy} x2={cx + (r - 70) * Math.cos((ang * Math.PI) / 180)} y2={cy + (r - 70) * Math.sin((ang * Math.PI) / 180)} stroke={RED} strokeWidth={18} strokeLinecap="round" />
          <circle cx={cx} cy={cy} r={34} fill={RED} stroke={INK} strokeWidth={8} />
        </svg>
        <div style={{ position: 'absolute', left: 0, right: 0, top: 860, display: 'flex', justifyContent: 'center', transform: 'scale(0.82)' }}>{big}</div>
        {k > 0.97 && <div style={{ position: 'absolute', left: 0, right: 0, top: 330, display: 'flex', justifyContent: 'center' }}><Stamp text="TOP OF THE BOARD" color={YELLOW} at={Math.min(d - 6, 36)} size={52} rot={-6} style={{ mixBlendMode: 'normal' }} /></div>}
      </>
    );
  } else {
    const bar = lin(f, 4, Math.min(d - 4, 30), was, now, io);
    body = (
      <>
        <div style={{ position: 'absolute', left: 0, right: 0, top: 330, textAlign: 'center' }}>{label}</div>
        <div style={{ position: 'absolute', left: 0, right: 0, top: 440, display: 'flex', justifyContent: 'center' }}>{big}</div>
        <div style={{ position: 'absolute', left: 80, right: 80, top: 900, height: 80, border: `8px solid ${PAPER}`, boxShadow: `10px 10px 0 ${RED}` }}>
          <div style={{ width: `${bar}%`, height: '100%', background: YELLOW }} />
          {p.peak && <div style={{ position: 'absolute', left: `${p.peak}%`, top: -40, bottom: -40, width: 6, background: RED }} />}
        </div>
        <div style={{ position: 'absolute', left: 80, right: 80, top: 1010, display: 'flex', justifyContent: 'space-between', fontFamily: FONT.mono, fontWeight: 700, fontSize: 34, color: PAPER }}>
          <span>WAS {was}%</span>{p.peak && <span style={{ color: RED }}>PEAK {p.peak}%</span>}
        </div>
      </>
    );
  }
  return (
    <AbsoluteFill style={{ background: BLUE, overflow: 'hidden' }}>
      <Halftone opacity={0.25} size={14} />
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, rgba(0,0,0,0) 30%, rgba(0,0,0,0.6) 100%)' }} />
      {body}
    </AbsoluteFill>
  );
};

const PanelCallout: S = ({ s, d }) => {
  const f = useCurrentFrame();
  const p = s.params;
  const wh: [number, number] = p.media_wh || [800, 1200];
  const [fx, fy, fw, fh] = p.focus || [0, 0, 1, 1];
  const boxW = 940, boxH = 1000;
  const sc = Math.min(boxW / wh[0], boxH / wh[1]);
  const cw = wh[0] * sc, ch = wh[1] * sc;
  const zoomTo = s.variant === 'crop_zoom' ? Math.min(2.0, 1 / Math.max(fw, fh * (ch / cw) * (cw / ch))) : 1.12;
  const z = lin(f, 8, Math.min(d - 4, 50), 1, zoomTo, io);
  const cx = (fx + fw / 2) * cw, cy = (fy + fh / 2) * ch;
  const tx = (cw / 2 - cx) * (z - 1) / z * (s.variant === 'crop_zoom' ? 1 : 0);
  const ty = (ch / 2 - cy) * (z - 1) / z * (s.variant === 'crop_zoom' ? 1 : 0);
  const enter = spring({ frame: f, fps: 30, config: { damping: 14 } });
  const ring = lin(f, 14, 30, 0, 1, io);
  const rr = 2 * Math.PI * 300;
  return (
    <AbsoluteFill>
      <BlurFill src={p.media_src} dark={0.6} />
      <Halftone opacity={0.2} />
      <div style={{ position: 'absolute', left: (W - cw) / 2, top: 180 + (boxH - ch) / 2, width: cw, height: ch, border: `12px solid ${PAPER}`, boxShadow: `18px 18px 0 ${INK}`,
        overflow: 'hidden', background: PAPER, transform: `translateY(${(1 - enter) * 900}px) rotate(${-2.5 + (1 - enter) * -12}deg)` }}>
        <div style={{ width: cw, height: ch, transform: `scale(${z}) translate(${tx}px, ${ty}px)`, transformOrigin: '50% 50%' }}>
          <Img src={staticFile(p.media_src)} style={{ width: cw, height: ch, objectFit: 'cover' }} />
        </div>
        {s.variant === 'circle_note' && (
          <svg width={cw} height={ch} style={{ position: 'absolute', inset: 0 }}>
            <ellipse cx={cw / 2} cy={ch / 2} rx={Math.min(300, cw * 0.42)} ry={Math.min(300, ch * 0.4)} fill="none" stroke={RED} strokeWidth={14}
              strokeDasharray={rr} strokeDashoffset={rr * (1 - ring)} transform={`rotate(-80 ${cw / 2} ${ch / 2})`} />
          </svg>
        )}
        {s.variant === 'crop_zoom' && <div style={{ position: 'absolute', inset: 30, border: `10px solid ${RED}`, opacity: ring, transform: `scale(${1.15 - 0.15 * ring})` }} />}
      </div>
      <div style={{ position: 'absolute', left: 60, top: 1060, transform: `rotate(-3deg) scale(${spring({ frame: f - 20, fps: 30, config: { damping: 10 } })})`, transformOrigin: 'left center',
        background: YELLOW, color: INK, fontFamily: FONT.slam, fontSize: fit(String(p.note), 900, 76), padding: '14px 28px', boxShadow: `10px 10px 0 ${INK}` }}>{p.note}</div>
    </AbsoluteFill>
  );
};

const Phone: React.FC<{ s: Shot; d: number }> = ({ s, d }) => {
  const f = useCurrentFrame();
  const p = s.params;
  const pw = 640, ph = 980, bez = 16;
  const iw = pw - bez * 2;
  const wh: [number, number] = p.media_wh || [780, 1688];
  const ih = (wh[1] * iw) / wh[0];
  const crop: number[] = p.crop || [0, 0, wh[0], wh[1]];
  const maxScroll = Math.max(0, Math.min(ih, (crop[3] * iw) / wh[0]) - (ph - bez * 2));
  const scroll = s.variant === 'scroll_highlight' ? lin(f, 8, d - 8, 0, maxScroll, io) : 0;
  const enter = spring({ frame: f, fps: 30, config: { damping: 15, mass: 0.8 } });
  const cur = s.variant === 'cursor_click';
  const click = Math.round(d * 0.5);
  const cx = lin(f, 4, click, 900, 520, io), cy = lin(f, 4, click, 1300, 640, io);
  const rip = lin(f, click, click + 12, 0, 1);
  return (
    <AbsoluteFill>
      <BlurFill src={p.bg_src || p.media_src} dark={0.5} tint={RED} />
      <Halftone opacity={0.25} />
      <div style={{ position: 'absolute', left: (W - pw) / 2, top: 190, width: pw, height: ph, perspective: 1600 }}>
        <div style={{ width: pw, height: ph, borderRadius: 72, background: '#161616', border: `4px solid #3a3a3a`, padding: bez, boxShadow: `24px 24px 0 ${INK}, 0 40px 120px rgba(0,0,0,0.6)`,
          transform: `translateY(${(1 - enter) * 900}px) rotateX(${(1 - enter) * 28}deg) rotateZ(${-2 + (1 - enter) * -6}deg)` }}>
          <div style={{ width: iw, height: ph - bez * 2, borderRadius: 58, overflow: 'hidden', position: 'relative', background: INK }}>
            <Img src={staticFile(p.media_src)} style={{ width: iw, height: ih, transform: `translateY(${-scroll}px)` }} />
            {cur && f > click && <div style={{ position: 'absolute', left: cx - 190 - 60 * rip, top: cy - 190 - 60 * rip, width: 120 + 120 * rip, height: 120 + 120 * rip,
              borderRadius: '50%', border: `8px solid ${YELLOW}`, opacity: 1 - rip }} />}
          </div>
        </div>
      </div>
      {cur && <svg width={90} height={110} style={{ position: 'absolute', left: cx, top: cy, transform: `scale(${f > click && f < click + 4 ? 0.85 : 1})` }}>
        <path d="M5 5 L5 85 L28 64 L44 100 L60 93 L44 58 L76 58 Z" fill={PAPER} stroke={INK} strokeWidth={6} strokeLinejoin="round" />
      </svg>}
      <div style={{ position: 'absolute', left: 50, top: 1060, transform: `translateX(${lin(f, 10, 18, -900, 0)}px) rotate(-2deg)`, background: YELLOW, color: INK,
        fontFamily: FONT.slam, fontSize: fit(String(p.hl), 920, 72), padding: '12px 26px', boxShadow: `10px 10px 0 ${INK}` }}>{p.hl}</div>
    </AbsoluteFill>
  );
};

// ---- custom scenes ----
const CountdownCrown: S = ({ s, d }) => {
  const f = useCurrentFrame();
  const p = s.params;
  const sp = spring({ frame: f - 2, fps: 30, config: { damping: 9, stiffness: 240, mass: 0.6 } });
  const crown = spring({ frame: f - 12, fps: 30, config: { damping: 8, stiffness: 300, mass: 0.5 } });
  return (
    <AbsoluteFill style={{ transform: shake(f, [3, 13], 22) }}>
      <BlurFill src={p.media_src} dark={0.25} tint={YELLOW} />
      <SpeedLines opacity={0.7} cy={50} color="255,212,59" />
      <div style={{ position: 'absolute', left: 0, right: 0, top: 380, textAlign: 'center', fontFamily: FONT.slam, fontSize: 1000, lineHeight: 1, color: PAPER,
        ...strokeText(20), textShadow: `24px 24px 0 ${RED}`, transform: `scale(${interpolate(sp, [0, 1], [3.2, 1])})` }}>{p.n}</div>
      <svg width={520} height={300} viewBox="0 0 520 300" style={{ position: 'absolute', left: (W - 520) / 2, top: 180, transform: `translateY(${(1 - crown) * -500}px) rotate(-8deg)` }}>
        <path d="M20 280 L50 60 L160 170 L260 20 L360 170 L470 60 L500 280 Z" fill={YELLOW} stroke={INK} strokeWidth={16} strokeLinejoin="round" />
        {[50, 260, 470].map((x, i) => <circle key={i} cx={x} cy={i === 1 ? 20 : 60} r={22} fill={RED} stroke={INK} strokeWidth={8} />)}
      </svg>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 1160, textAlign: 'center', fontFamily: FONT.mono, fontWeight: 700, fontSize: 48, color: INK, letterSpacing: 10 }}>
        <span style={{ background: YELLOW, padding: '8px 20px' }}>NUMBER ONE</span></div>
      <Flash len={5} />
    </AbsoluteFill>
  );
};

const VoteCard: S = ({ s, d }) => {
  const f = useCurrentFrame();
  const p = s.params;
  const rows: [string, string, number][] = p.rows || [];
  return (
    <AbsoluteFill>
      <BlurFill src={p.media_src} dark={0.55} />
      <div style={{ position: 'absolute', left: 60, top: 190, fontFamily: FONT.slam, fontSize: 96, color: PAPER, lineHeight: 1.08, ...strokeText(8), textShadow: `8px 8px 0 ${INK}` }}>
        WHICH ONE<br /><span style={{ color: YELLOW }}>BREAKS</span><br /><span style={{ color: YELLOW }}>FIRST?</span></div>
      {rows.map(([n, t, v], i) => {
        const k = spring({ frame: f - 6 - i * 6, fps: 30, config: { damping: 14 } });
        return (
          <div key={i} style={{ position: 'absolute', left: 60, right: 60, top: 540 + i * 165, height: 140, background: i === 2 ? YELLOW : POSTER, display: 'flex', alignItems: 'center',
            boxShadow: `12px 12px 0 ${INK}`, transform: `translateX(${(1 - k) * (i % 2 ? 1200 : -1200)}px)` }}>
            <div style={{ width: 150, height: '100%', background: INK, color: YELLOW, fontFamily: FONT.slam, fontSize: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{n}</div>
            <div style={{ flex: 1, padding: '0 30px', fontFamily: FONT.slam, fontSize: fit(t, 560, 64), color: INK }}>{t}</div>
            <div style={{ padding: '0 34px', fontFamily: FONT.slam, fontSize: 84, color: RED }}>{Math.round(v * lin(f, 10 + i * 6, 30 + i * 6, 0, 1))}%</div>
          </div>
        );
      })}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 1040, display: 'flex', justifyContent: 'center' }}>
        <Stamp text="VOTE" color={RED} at={30} size={90} rot={-6} style={{ background: PAPER, mixBlendMode: 'normal' }} />
      </div>
    </AbsoluteFill>
  );
};

const PromoEnd: S = ({ s, d }) => {
  const f = useCurrentFrame();
  const p = s.params;
  const hits = slamFrames(['POST', 'YOUR', 'THEORY'], 14, 6);
  const logo = spring({ frame: f - 2, fps: 30, config: { damping: 11 } });
  return (
    <AbsoluteFill style={{ transform: shake(f, hits, 14) }}>
      <Art p={p} dur={d} variant="halftone_duotone" />
      <div style={{ position: 'absolute', left: 0, right: 0, top: 230, display: 'flex', justifyContent: 'center', transform: `scale(${logo})` }}>
        <div style={{ background: INK, padding: '20px 36px', boxShadow: `12px 12px 0 ${YELLOW}`, fontFamily: FONT.slam, fontSize: 110, color: PAPER }}>LORE<span style={{ color: YELLOW }}>SQUARE</span></div>
      </div>
      <Slam lines={['POST', 'YOUR', 'THEORY']} keyIdx={2} top={480} start={14} max={170} />
      <div style={{ position: 'absolute', left: 0, right: 0, top: 1090, textAlign: 'center', opacity: lin(f, 34, 42, 0, 1) }}>
        <span style={{ background: PAPER, color: INK, fontFamily: FONT.mono, fontWeight: 700, fontSize: 56, padding: '10px 26px', boxShadow: `8px 8px 0 ${INK}` }}>loresquare.com</span>
      </div>
      <Flash len={4} />
    </AbsoluteFill>
  );
};

const CUSTOM: Record<string, S> = { CountdownCrown, VoteCard, PromoEnd };

export const Scene: S = (props) => {
  const { s } = props;
  switch (s.type) {
    case 'art_backdrop': return <ArtBackdrop {...props} />;
    case 'kinetic_type': return <KineticType {...props} />;
    case 'chapter_card': return <ChapterCard {...props} />;
    case 'claim_card': return <ClaimCard {...props} />;
    case 'question_card': return <QuestionCard {...props} />;
    case 'argument_duel': return <ArgumentDuel {...props} />;
    case 'confidence_meter': return <Meter {...props} />;
    case 'panel_callout': return <PanelCallout {...props} />;
    case 'site_screen': return <Phone {...props} />;
    case 'custom': { const K = CUSTOM[s.params.component]; return K ? <K {...props} /> : <AbsoluteFill style={{ background: RED }} />; }
    default: return <AbsoluteFill style={{ background: RED }} />;
  }
};
