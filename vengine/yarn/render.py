"""Yarn renderer for crochet-growth shots (numba, CPU).

The yarn is a chain of nodes drawn as a swept soft tube with a plied twist.  Everything that is not geometry is made so
that it does not change from one frame to the next unless the yarn or the camera really moved:

* texture (plies, fibres, unevenness) lives on the yarn, in (arc length, angle round the yarn), never in screen pixels;
* the colour of a pixel is read from the arc length of the hit point, so a colour change sits exactly where the
  stitch changes colour and does not crawl along the yarn when the camera moves;
* texture detail finer than about two pixels fades to its mean (no moire on a toy seen from afar);
* ambient occlusion and the fibre halo use fixed sample patterns, not per-pixel random ones;
* the shadow map is centred on the whole scene and snapped to its texels, so shadows do not swim;
* the supersampled image is reduced with a Gaussian, not a 2x2 box, so edges move smoothly by sub-pixel steps.

It descends from crochetsim/render.py (engine-v3), minus the hook, which growth shots do not show.
"""
from __future__ import annotations

import math

import numpy as np
from numba import njit, prange

TAU = 6.283185307179586


def look_at(pos, target, up=(0.0, 1.0, 0.0)):
    pos = np.asarray(pos, float)
    f = np.asarray(target, float) - pos
    f /= np.linalg.norm(f)
    r = np.cross(f, np.asarray(up, float))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return np.stack([r, u, f])


class Camera:
    def __init__(self, pos, target, up=(0.0, 1.0, 0.0), fov=30.0):
        self.pos = np.asarray(pos, float)
        self.target = np.asarray(target, float)
        self.up = np.asarray(up, float)
        self.fov = float(fov)

    def basis(self):
        return look_at(self.pos, self.target, self.up)


@njit(cache=True)
def _samples(X, D, RS, n, sub, h, P, T, DD, SS, RR):
    """Catmull-Rom samples along the chain: position, tangent, director, arc length, radius scale."""
    m = 0
    for i in range(n - 1):
        i0 = i - 1 if i > 0 else i
        i3 = i + 2 if i + 2 < n else i + 1
        for k in range(sub):
            u = k / sub
            u2 = u * u
            u3 = u2 * u
            for c in range(3):
                p0 = X[i0, c]
                p1 = X[i, c]
                p2 = X[i + 1, c]
                p3 = X[i3, c]
                P[m, c] = 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2
                                 + (-p0 + 3 * p1 - 3 * p2 + p3) * u3)
                T[m, c] = 0.5 * ((-p0 + p2) + 2 * (2 * p0 - 5 * p1 + 4 * p2 - p3) * u
                                 + 3 * (-p0 + 3 * p1 - 3 * p2 + p3) * u2)
            tl = math.sqrt(T[m, 0] ** 2 + T[m, 1] ** 2 + T[m, 2] ** 2) + 1e-30
            T[m, 0] /= tl
            T[m, 1] /= tl
            T[m, 2] /= tl
            j = i + 1 if i + 1 < n - 1 else i
            dx = D[i, 0] * (1 - u) + D[j, 0] * u
            dy = D[i, 1] * (1 - u) + D[j, 1] * u
            dz = D[i, 2] * (1 - u) + D[j, 2] * u
            dn = dx * T[m, 0] + dy * T[m, 1] + dz * T[m, 2]
            dx -= dn * T[m, 0]
            dy -= dn * T[m, 1]
            dz -= dn * T[m, 2]
            dl = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dl < 1e-6:
                dx, dy, dz = D[i, 0], D[i, 1], D[i, 2]
                dl = math.sqrt(dx * dx + dy * dy + dz * dz) + 1e-30
            DD[m, 0] = dx / dl
            DD[m, 1] = dy / dl
            DD[m, 2] = dz / dl
            SS[m] = (i + u) * h
            RR[m] = RS[i] * (1 - u) + RS[i + 1] * u
            m += 1
    return m


@njit(cache=True, parallel=True)
def _splat(P, T, DD, SS, RR, QQ, CC, m, r, cam_pos, B, fpx, W, H, zb, nb, sb, pb, idb, nband, tb, spread):
    """Perspective splat of soft-tube samples with exact ray depth.  The section is an ellipse pressed to CC[k] of its
    radius along QQ[k]; RR[k] scales the radius (the growing tip tapers in)."""
    cx = 0.5 * W
    cy = 0.5 * H
    for band in prange(nband):
        y0b = band * H // nband
        y1b = (band + 1) * H // nband
        for k in range(m):
            rk = r * RR[k]
            if rk < 1e-3:
                continue
            vx = P[k, 0] - cam_pos[0]
            vy = P[k, 1] - cam_pos[1]
            vz = P[k, 2] - cam_pos[2]
            xr = B[0, 0] * vx + B[0, 1] * vy + B[0, 2] * vz
            yu = B[1, 0] * vx + B[1, 1] * vy + B[1, 2] * vz
            zf = B[2, 0] * vx + B[2, 1] * vy + B[2, 2] * vz
            if zf < 1.0:
                continue
            sx = cx + fpx * xr / zf
            sy = cy - fpx * yu / zf
            sq = 1.0 / CC[k] - 1.0
            wd = CC[k] ** spread
            sw = wd - 1.0
            wx_ = T[k, 1] * QQ[k, 2] - T[k, 2] * QQ[k, 1]
            wy_ = T[k, 2] * QQ[k, 0] - T[k, 0] * QQ[k, 2]
            wz_ = T[k, 0] * QQ[k, 1] - T[k, 1] * QQ[k, 0]
            rp = fpx * rk / wd / zf * 1.03 + 1.5
            ya = int(max(y0b, math.floor(sy - rp)))
            yb = int(min(y1b - 1, math.ceil(sy + rp)))
            if ya > yb:
                continue
            xa = int(max(0, math.floor(sx - rp)))
            xb = int(min(W - 1, math.ceil(sx + rp)))
            vq = vx * QQ[k, 0] + vy * QQ[k, 1] + vz * QQ[k, 2]
            vw = vx * wx_ + vy * wy_ + vz * wz_
            ux = vx + sq * vq * QQ[k, 0] + sw * vw * wx_
            uy = vy + sq * vq * QQ[k, 1] + sw * vw * wy_
            uz = vz + sq * vq * QQ[k, 2] + sw * vw * wz_
            cc = ux * ux + uy * uy + uz * uz - rk * rk
            for py in range(ya, yb + 1):
                for px in range(xa, xb + 1):
                    dxv = (px + 0.5 - cx) / fpx
                    dyv = -(py + 0.5 - cy) / fpx
                    il = 1.0 / math.sqrt(dxv * dxv + dyv * dyv + 1.0)
                    rx = (B[0, 0] * dxv + B[1, 0] * dyv + B[2, 0]) * il
                    ry = (B[0, 1] * dxv + B[1, 1] * dyv + B[2, 1]) * il
                    rz = (B[0, 2] * dxv + B[1, 2] * dyv + B[2, 2]) * il
                    rq = rx * QQ[k, 0] + ry * QQ[k, 1] + rz * QQ[k, 2]
                    rw = rx * wx_ + ry * wy_ + rz * wz_
                    sx_ = rx + sq * rq * QQ[k, 0] + sw * rw * wx_
                    sy_ = ry + sq * rq * QQ[k, 1] + sw * rw * wy_
                    sz_ = rz + sq * rq * QQ[k, 2] + sw * rw * wz_
                    aa = sx_ * sx_ + sy_ * sy_ + sz_ * sz_
                    b = sx_ * ux + sy_ * uy + sz_ * uz
                    disc = b * b - aa * cc
                    if disc <= 0.0:
                        continue
                    t = (b - math.sqrt(disc)) / aa
                    if t < zb[py, px]:
                        zb[py, px] = t
                        nx = (sx_ * t - ux) / rk
                        ny = (sy_ * t - uy) / rk
                        nz = (sz_ * t - uz) / rk
                        nq = nx * QQ[k, 0] + ny * QQ[k, 1] + nz * QQ[k, 2]
                        nw = nx * wx_ + ny * wy_ + nz * wz_
                        nx += sq * nq * QQ[k, 0] + sw * nw * wx_
                        ny += sq * nq * QQ[k, 1] + sw * nw * wy_
                        nz += sq * nq * QQ[k, 2] + sw * nw * wz_
                        nl = math.sqrt(nx * nx + ny * ny + nz * nz)
                        nx /= nl
                        ny /= nl
                        nz /= nl
                        tn = nx * T[k, 0] + ny * T[k, 1] + nz * T[k, 2]
                        ax = nx - tn * T[k, 0]
                        ay = ny - tn * T[k, 1]
                        az = nz - tn * T[k, 2]
                        al = math.sqrt(ax * ax + ay * ay + az * az)
                        if al > 0.2:
                            ax /= al
                            ay /= al
                            az /= al
                        else:
                            ax, ay, az = nx, ny, nz
                        nb[py, px, 0] = ax
                        nb[py, px, 1] = ay
                        nb[py, px, 2] = az
                        ex = T[k, 1] * DD[k, 2] - T[k, 2] * DD[k, 1]
                        ey = T[k, 2] * DD[k, 0] - T[k, 0] * DD[k, 2]
                        ez = T[k, 0] * DD[k, 1] - T[k, 1] * DD[k, 0]
                        pb[py, px] = math.atan2(ax * ex + ay * ey + az * ez,
                                                ax * DD[k, 0] + ay * DD[k, 1] + az * DD[k, 2])
                        sb[py, px] = SS[k] + (rx * t - vx) * T[k, 0] + (ry * t - vy) * T[k, 1] + (rz * t - vz) * T[k, 2]
                        tb[py, px, 0] = T[k, 0]
                        tb[py, px, 1] = T[k, 1]
                        tb[py, px, 2] = T[k, 2]
                        idb[py, px] = 1


@njit(cache=True, parallel=True)
def _trace_spheres(S, cam_pos, B, fpx, W, H, zb, nb, idb, cb):
    """Glossy half-balls (safety eyes): rows cx, cy, cz, radius, colour index."""
    cx = 0.5 * W
    cy = 0.5 * H
    for py in prange(H):
        for px in range(W):
            dxv = (px + 0.5 - cx) / fpx
            dyv = -(py + 0.5 - cy) / fpx
            il = 1.0 / math.sqrt(dxv * dxv + dyv * dyv + 1.0)
            rx = (B[0, 0] * dxv + B[1, 0] * dyv + B[2, 0]) * il
            ry = (B[0, 1] * dxv + B[1, 1] * dyv + B[2, 1]) * il
            rz = (B[0, 2] * dxv + B[1, 2] * dyv + B[2, 2]) * il
            for k in range(S.shape[0]):
                if S[k, 3] <= 0.0:
                    continue
                ox = cam_pos[0] - S[k, 0]
                oy = cam_pos[1] - S[k, 1]
                oz = cam_pos[2] - S[k, 2]
                bq = ox * rx + oy * ry + oz * rz
                cq = ox * ox + oy * oy + oz * oz - S[k, 3] * S[k, 3]
                disc = bq * bq - cq
                if disc <= 0.0:
                    continue
                t = -bq - math.sqrt(disc)
                if t > 0.0 and t < zb[py, px]:
                    zb[py, px] = t
                    nb[py, px, 0] = (ox + rx * t) / S[k, 3]
                    nb[py, px, 1] = (oy + ry * t) / S[k, 3]
                    nb[py, px, 2] = (oz + rz * t) / S[k, 3]
                    idb[py, px] = 3
                    cb[py, px] = int(S[k, 4])


@njit(cache=True, parallel=True)
def _raster_details(V, N, U, F, FE, cam_pos, B, fpx, W, H, zb, nb, idb, cb, ub, nband):
    """Detail meshes (felt, satin, threads, appliques: details.py) by exact ray-triangle hits, depth-tested against
    the yarn.  Writes idb 4, the element in cb and the detail's own coordinates (u, v, rho) in ub."""
    cx = 0.5 * W
    cy = 0.5 * H
    nv = V.shape[0]
    S = np.empty((nv, 3))
    for i in range(nv):
        vx = V[i, 0] - cam_pos[0]
        vy = V[i, 1] - cam_pos[1]
        vz = V[i, 2] - cam_pos[2]
        xr = B[0, 0] * vx + B[0, 1] * vy + B[0, 2] * vz
        yu = B[1, 0] * vx + B[1, 1] * vy + B[1, 2] * vz
        zf = B[2, 0] * vx + B[2, 1] * vy + B[2, 2] * vz
        S[i, 2] = zf
        if zf > 1e-6:
            S[i, 0] = cx + fpx * xr / zf
            S[i, 1] = cy - fpx * yu / zf
    for band in prange(nband):
        y0b = band * H // nband
        y1b = (band + 1) * H // nband
        for f in range(F.shape[0]):
            a = F[f, 0]
            b = F[f, 1]
            c = F[f, 2]
            if S[a, 2] < 1.0 or S[b, 2] < 1.0 or S[c, 2] < 1.0:
                continue
            ya = int(max(y0b, math.floor(min(S[a, 1], min(S[b, 1], S[c, 1])))))
            yb = int(min(y1b - 1, math.ceil(max(S[a, 1], max(S[b, 1], S[c, 1])))))
            if ya > yb:
                continue
            xa = int(max(0, math.floor(min(S[a, 0], min(S[b, 0], S[c, 0])))))
            xb = int(min(W - 1, math.ceil(max(S[a, 0], max(S[b, 0], S[c, 0])))))
            if xa > xb:
                continue
            e1x = V[b, 0] - V[a, 0]
            e1y = V[b, 1] - V[a, 1]
            e1z = V[b, 2] - V[a, 2]
            e2x = V[c, 0] - V[a, 0]
            e2y = V[c, 1] - V[a, 1]
            e2z = V[c, 2] - V[a, 2]
            tx = cam_pos[0] - V[a, 0]
            ty = cam_pos[1] - V[a, 1]
            tz = cam_pos[2] - V[a, 2]
            qx = ty * e1z - tz * e1y
            qy = tz * e1x - tx * e1z
            qz = tx * e1y - ty * e1x
            for py in range(ya, yb + 1):
                for px in range(xa, xb + 1):
                    dxv = (px + 0.5 - cx) / fpx
                    dyv = -(py + 0.5 - cy) / fpx
                    il = 1.0 / math.sqrt(dxv * dxv + dyv * dyv + 1.0)
                    rx = (B[0, 0] * dxv + B[1, 0] * dyv + B[2, 0]) * il
                    ry = (B[0, 1] * dxv + B[1, 1] * dyv + B[2, 1]) * il
                    rz = (B[0, 2] * dxv + B[1, 2] * dyv + B[2, 2]) * il
                    pxv = ry * e2z - rz * e2y
                    pyv = rz * e2x - rx * e2z
                    pzv = rx * e2y - ry * e2x
                    det = e1x * pxv + e1y * pyv + e1z * pzv
                    if abs(det) < 1e-12:
                        continue
                    inv = 1.0 / det
                    u = (tx * pxv + ty * pyv + tz * pzv) * inv
                    if u < -1e-5 or u > 1.00001:
                        continue
                    v = (rx * qx + ry * qy + rz * qz) * inv
                    if v < -1e-5 or u + v > 1.00001:
                        continue
                    t = (e2x * qx + e2y * qy + e2z * qz) * inv
                    if t <= 0.0 or t >= zb[py, px]:
                        continue
                    w = 1.0 - u - v
                    zb[py, px] = t
                    nx = w * N[a, 0] + u * N[b, 0] + v * N[c, 0]
                    ny = w * N[a, 1] + u * N[b, 1] + v * N[c, 1]
                    nz = w * N[a, 2] + u * N[b, 2] + v * N[c, 2]
                    nl = math.sqrt(nx * nx + ny * ny + nz * nz) + 1e-12
                    nb[py, px, 0] = nx / nl
                    nb[py, px, 1] = ny / nl
                    nb[py, px, 2] = nz / nl
                    for q in range(3):
                        ub[py, px, q] = w * U[a, q] + u * U[b, q] + v * U[c, q]
                    idb[py, px] = 4
                    cb[py, px] = FE[f]


@njit(cache=True)
def _shadow_splat(P, RR, m, r, LB, lo, scale, SM, sm):
    """Orthographic depth map from the light.  LB rows: right, up, towards the light."""
    for k in range(m):
        rk = r * RR[k]
        if rk < 1e-3:
            continue
        x = (LB[0, 0] * P[k, 0] + LB[0, 1] * P[k, 1] + LB[0, 2] * P[k, 2] - lo[0]) * scale
        y = (LB[1, 0] * P[k, 0] + LB[1, 1] * P[k, 1] + LB[1, 2] * P[k, 2] - lo[1]) * scale
        z = LB[2, 0] * P[k, 0] + LB[2, 1] * P[k, 1] + LB[2, 2] * P[k, 2]
        rp = rk * scale
        xa = int(max(0, math.floor(x - rp)))
        xb = int(min(sm - 1, math.ceil(x + rp)))
        ya = int(max(0, math.floor(y - rp)))
        yb = int(min(sm - 1, math.ceil(y + rp)))
        for py in range(ya, yb + 1):
            for px in range(xa, xb + 1):
                ddx = (px + 0.5 - x) / scale
                ddy = (py + 0.5 - y) / scale
                q = rk * rk - ddx * ddx - ddy * ddy
                if q > 0.0:
                    zz = z + math.sqrt(q)
                    if zz > SM[py, px]:
                        SM[py, px] = zz


@njit(cache=True)
def _hash(a, b):
    v = math.sin(a * 127.1 + b * 311.7) * 43758.5453
    return v - math.floor(v)


@njit(cache=True)
def _vnoise(x, row):
    """1D value noise along x (smooth), one independent row per integer `row`."""
    i = math.floor(x)
    f = x - i
    f = f * f * (3.0 - 2.0 * f)
    return _hash(i, row) * (1.0 - f) + _hash(i + 1.0, row) * f - 0.5


@njit(cache=True)
def _lod(period_world, foot):
    """1 while a texture period covers 5+ pixels, 0 below 2 pixels: finer detail fades to its mean."""
    q = period_world / max(foot, 1e-9)
    return min(1.0, max(0.0, (q - 2.0) / 3.0))


@njit(cache=True)
def _shoulder(x):
    """Linear up to 0.86, then a soft roll-off to 1: highlights keep their colour instead of clipping."""
    if x < 0.86:
        return x
    return 0.86 + 0.14 * (1.0 - math.exp(-(x - 0.86) / 0.14))


@njit(cache=True)
def _shadow_at(SM, sm, LB, lo, scale, wx, wy, wz, bias, step, rad):
    lx = (LB[0, 0] * wx + LB[0, 1] * wy + LB[0, 2] * wz - lo[0]) * scale
    ly = (LB[1, 0] * wx + LB[1, 1] * wy + LB[1, 2] * wz - lo[1]) * scale
    lz = LB[2, 0] * wx + LB[2, 1] * wy + LB[2, 2] * wz
    acc = 0.0
    cnt = 0.0
    # bilinear-weighted PCF: the result moves continuously with the point (no texel steps)
    fx = lx - 0.5
    fy = ly - 0.5
    ix0 = int(math.floor(fx))
    iy0 = int(math.floor(fy))
    ax = fx - ix0
    ay = fy - iy0
    for oy in range(-rad, rad + 2):
        wy_ = (1.0 - ay) if oy == -rad else (ay if oy == rad + 1 else 1.0)
        for ox in range(-rad, rad + 2):
            wx_ = (1.0 - ax) if ox == -rad else (ax if ox == rad + 1 else 1.0)
            w = wx_ * wy_
            ix = ix0 + ox * step
            iy = iy0 + oy * step
            if 0 <= ix < sm and 0 <= iy < sm:
                if SM[iy, ix] > lz + bias:
                    acc += w
            cnt += w
    return 1.0 - acc / max(cnt, 1e-9)


@njit(cache=True, parallel=True)
def _shade(zb, nb, sb, pb, idb, cb, tb, colnode, ncol, h, cam_pos, B, fpx, W, H, LB, lo, scale, SM, sm, ldir,
           palette, bg_top, bg_bot, plane_p, plane_n, r, rvis, pitch, nply, out, ao_r_px, fuzz_amt, sheen, halo_amt,
           shadow_floor, exposure, ao_amt):
    cx = 0.5 * W
    cy = 0.5 * H
    for py in prange(H):
        for px in range(W):
            dxv = (px + 0.5 - cx) / fpx
            dyv = -(py + 0.5 - cy) / fpx
            il = 1.0 / math.sqrt(dxv * dxv + dyv * dyv + 1.0)
            rx = (B[0, 0] * dxv + B[1, 0] * dyv + B[2, 0]) * il
            ry = (B[0, 1] * dxv + B[1, 1] * dyv + B[2, 1]) * il
            rz = (B[0, 2] * dxv + B[1, 2] * dyv + B[2, 2]) * il
            ident = idb[py, px]
            t = zb[py, px]
            v = py / H
            if ident == 0:
                c0 = bg_top[0] * (1 - v) + bg_bot[0] * v
                c1 = bg_top[1] * (1 - v) + bg_bot[1] * v
                c2 = bg_top[2] * (1 - v) + bg_bot[2] * v
                den = rx * plane_n[0] + ry * plane_n[1] + rz * plane_n[2]
                if shadow_floor > 0.0 and abs(den) > 1e-6:
                    tp = ((plane_p[0] - cam_pos[0]) * plane_n[0] + (plane_p[1] - cam_pos[1]) * plane_n[1]
                          + (plane_p[2] - cam_pos[2]) * plane_n[2]) / den
                    if tp > 0:
                        sh = _shadow_at(SM, sm, LB, lo, scale, cam_pos[0] + rx * tp, cam_pos[1] + ry * tp,
                                        cam_pos[2] + rz * tp, 0.5, 4, 3)
                        f = 1.0 - shadow_floor * (1.0 - sh)
                        c0 *= f
                        c1 *= f
                        c2 *= f
                # the fuzz round the yarn: a soft glow of its colour that fades with the distance to the outline,
                # read from fixed directions (no per-pixel randomness to crawl from frame to frame)
                if halo_amt > 0.0:
                    hit = 0.0
                    ar = 0.0
                    ag = 0.0
                    ab = 0.0
                    for k in range(12):
                        ang = 0.5235988 * k
                        for ring in range(2):
                            rad = ao_r_px * (0.07 + 0.08 * ring)
                            ix = int(px + 0.5 + math.cos(ang) * rad)
                            iy = int(py + 0.5 + math.sin(ang) * rad)
                            if 0 <= ix < W and 0 <= iy < H and idb[iy, ix] == 1:
                                w = 1.0 if ring == 0 else 0.5
                                kk = int(sb[iy, ix] / h)
                                ci = colnode[min(max(kk, 0), ncol - 1)]
                                hit += w
                                ar += w * palette[ci, 0]
                                ag += w * palette[ci, 1]
                                ab += w * palette[ci, 2]
                    if hit > 0.0:
                        al = halo_amt * min(1.0, hit / 9.0)
                        c0 = c0 * (1 - al) + 0.92 * ar / hit * al
                        c1 = c1 * (1 - al) + 0.92 * ag / hit * al
                        c2 = c2 * (1 - al) + 0.92 * ab / hit * al
                out[py, px, 0] = c0
                out[py, px, 1] = c1
                out[py, px, 2] = c2
                continue
            wx = cam_pos[0] + rx * t
            wy = cam_pos[1] + ry * t
            wz = cam_pos[2] + rz * t
            nx = nb[py, px, 0]
            ny = nb[py, px, 1]
            nz = nb[py, px, 2]
            lit = _shadow_at(SM, sm, LB, lo, scale, wx, wy, wz, 0.35 * r, 1, 1)
            # ambient occlusion from the depth buffer, a fixed golden-angle spiral
            occ = 0.0
            ns = 0
            for k in range(16):
                ang = 2.399963 * k
                rad = ao_r_px * math.sqrt((k + 0.5) / 16.0)
                ix = int(px + 0.5 + math.cos(ang) * rad)
                iy = int(py + 0.5 + math.sin(ang) * rad)
                if 0 <= ix < W and 0 <= iy < H:
                    dz = t - zb[iy, ix]
                    if dz > 0.15 * r and dz < 6.0 * r:
                        occ += min(1.0, dz / (1.2 * r)) * (1.0 - dz / (6.0 * r))
                    ns += 1
            ao = max(0.0, 1.0 - 1.05 * ao_amt * occ / max(ns, 1))
            ndv = min(1.0, max(0.0, -(nx * rx + ny * ry + nz * rz)))   # <= 1: (1 - ndv) ** 2.5 must not go NaN
            if ident == 3:
                ci = cb[py, px]
                ndl = max(0.0, nx * ldir[0] + ny * ldir[1] + nz * ldir[2])
                hx = ldir[0] - rx
                hy = ldir[1] - ry
                hz = ldir[2] - rz
                hl = math.sqrt(hx * hx + hy * hy + hz * hz) + 1e-9
                ndh = max(0.0, (nx * hx + ny * hy + nz * hz) / hl)
                spec = (ndh ** 300 * 2.2 + ndh ** 30 * 0.18) * (0.3 + 0.7 * lit)
                env = 0.04 + 0.07 * max(0.0, ny)
                fres = (1.0 - ndv) ** 4 * 0.28
                for ch in range(3):
                    out[py, px, ch] = _shoulder(palette[ci, ch] * (0.25 + 0.35 * ndl) * (0.5 + 0.5 * ao) + env + fres + spec)
                continue
            kk = int(sb[py, px] / h)
            ci = colnode[min(max(kk, 0), ncol - 1)]
            foot = t / fpx                                   # world size of one (supersampled) pixel at the hit
            tx = tb[py, px, 0]
            ty = tb[py, px, 1]
            tz = tb[py, px, 2]
            kx = ny * tz - nz * ty
            ky = nz * tx - nx * tz
            kz = nx * ty - ny * tx
            kl = math.sqrt(kx * kx + ky * ky + kz * kz) + 1e-9
            kx /= kl
            ky /= kl
            kz /= kl
            tanth = TAU * rvis / pitch                       # helix angle of the plies on the drawn surface
            cth = 1.0 / math.sqrt(1.0 + tanth * tanth)
            sth = tanth * cth
            hx = cth * tx + sth * kx                         # along the ply
            hy = cth * ty + sth * ky
            hz = cth * tz + sth * kz
            qx = -sth * tx + cth * kx                        # across the ply
            qy = -sth * ty + cth * ky
            qz = -sth * tz + cth * kz
            # texture levels of detail: a ply is TAU*rvis/nply wide, a fibre lane a ninth of that, streaks 0.4 mm long
            l_ply = _lod(TAU * rvis / nply * cth, foot)
            l_fib = _lod(TAU * rvis / nply / 9.0, foot)
            l_str = _lod(0.42, foot)
            psi = nply * (pb[py, px] - TAU * sb[py, px] / pitch)
            f = psi / TAU
            f = f - math.floor(f)
            u = 2.0 * f - 1.0
            bump = math.sqrt(max(0.0, 1.0 - u * u))
            slope = -u / max(bump, 0.25)
            slope = max(-1.6, min(1.6, slope)) * 0.22 * l_ply
            mx = nx + slope * qx
            my = ny + slope * qy
            mz = nz + slope * qz
            ml = math.sqrt(mx * mx + my * my + mz * mz)
            mx /= ml
            my /= ml
            mz /= ml
            plyi = math.floor(psi / TAU)
            along = sb[py, px] * cth + pb[py, px] * rvis * sth
            lane = math.floor(f * 9.0) + 17.0 * plyi
            fib = _vnoise(along * 2.4 + _hash(lane, 3.0) * 7.0, lane) * l_fib * l_str
            fib2 = _vnoise(along * 0.45 + _hash(plyi, 5.0) * 3.0, plyi + 101.0) * l_ply
            slub = _vnoise(sb[py, px] * 0.11, 7.0)          # the spun yarn is a little uneven along its length
            crev = 1.0 - (0.24 * (1.0 - bump ** 1.3)) * l_ply - 0.24 * 0.55 * (1.0 - l_ply)
            alb = (1.0 + 0.11 * fib + 0.07 * fib2 + 0.05 * slub) * crev
            ndl = mx * ldir[0] + my * ldir[1] + mz * ldir[2]
            wrap = max(0.0, (ndl + 0.35) / 1.35)
            sky = 0.5 + 0.5 * my                             # light from above the set, darker from below
            amb = 0.30 + 0.16 * sky + 0.14 * ndv
            li = (amb * ao * ao + 0.72 * wrap * lit * (0.5 + 0.5 * ao)) * exposure
            # Kajiya-Kay sheen along the fibres of each ply
            vx_ = ldir[0] - rx
            vy_ = ldir[1] - ry
            vz_ = ldir[2] - rz
            vl = math.sqrt(vx_ * vx_ + vy_ * vy_ + vz_ * vz_) + 1e-9
            th_ = (hx * vx_ + hy * vy_ + hz * vz_) / vl
            kk2 = math.sqrt(max(0.0, 1.0 - th_ * th_)) ** 20 * sheen * lit * (0.4 + 0.6 * bump)
            fz = (1.0 - ndv) ** 2.5 * 0.16 * fuzz_amt * (0.75 + 0.25 * sky)
            lum = 0.30 * palette[ci, 0] + 0.55 * palette[ci, 1] + 0.15 * palette[ci, 2] + 1e-3
            dk = max(0.0, 1.0 - li)
            for ch in range(3):
                pc = palette[ci, ch]
                tint = (pc / lum) ** (0.5 * dk)              # shadows deepen in the dye colour, not towards grey
                val = pc * alb * li * tint + kk2 * (0.55 + 0.45 * pc) + fz * (0.55 + 0.45 * pc)
                out[py, px, ch] = _shoulder(val)


@njit(cache=True)
def _noise2(x, y):
    j = math.floor(y)
    f = y - j
    f = f * f * (3.0 - 2.0 * f)
    return _vnoise(x, j) * (1.0 - f) + _vnoise(x + 0.37, j + 1.0) * f


@njit(cache=True, parallel=True)
def _shade_details(zb, nb, idb, cb, ub, cam_pos, B, fpx, W, H, LB, lo, scale, SM, sm, ldir, palette, EL, r, exposure,
                   out):
    """Shades the detail pixels (idb 4) from their own coordinates: felt fibres and a cut edge; satin strands with a
    soft thread sheen; crocheted appliques with stitches radiating from the centre and faint round lines; plied
    threads; glossy plastic.  Detail finer than about two pixels fades to its mean (_lod), as on the yarn."""
    cx = 0.5 * W
    cy = 0.5 * H
    for py in prange(H):
        for px in range(W):
            if idb[py, px] != 4:
                continue
            dxv = (px + 0.5 - cx) / fpx
            dyv = -(py + 0.5 - cy) / fpx
            il = 1.0 / math.sqrt(dxv * dxv + dyv * dyv + 1.0)
            rx = (B[0, 0] * dxv + B[1, 0] * dyv + B[2, 0]) * il
            ry = (B[0, 1] * dxv + B[1, 1] * dyv + B[2, 1]) * il
            rz = (B[0, 2] * dxv + B[1, 2] * dyv + B[2, 2]) * il
            t = zb[py, px]
            wx = cam_pos[0] + rx * t
            wy = cam_pos[1] + ry * t
            wz = cam_pos[2] + rz * t
            nx = nb[py, px, 0]
            ny = nb[py, px, 1]
            nz = nb[py, px, 2]
            if nx * rx + ny * ry + nz * rz > 0.0:           # seen from behind (a thin rim): face the viewer
                nx, ny, nz = -nx, -ny, -nz
            e = cb[py, px]
            ci = int(EL[e, 0])
            mat = int(EL[e, 1])
            gloss = EL[e, 4]
            e1x, e1y, e1z = EL[e, 6], EL[e, 7], EL[e, 8]
            e2x, e2y, e2z = EL[e, 9], EL[e, 10], EL[e, 11]
            u = ub[py, px, 0]
            v = ub[py, px, 1]
            rho = ub[py, px, 2]
            foot = t / fpx
            alb = 1.0
            # the direction of the fibres (for the thread sheen); none: an isotropic soft highlight
            fx, fy, fz = 0.0, 0.0, 0.0
            if mat == 0:                                     # felt: fine matted fibres, a slightly darker cut edge
                lf = _lod(0.35, foot)
                alb = 1.0 + 0.07 * _noise2(u * 2.8, v * 2.8) * lf + 0.04 * _noise2(u * 0.7 + 3.1, v * 0.7)
                alb *= 1.0 - 0.10 * min(1.0, max(0.0, (rho - 0.86) / 0.14))
            elif mat == 1:                                   # satin: parallel strands along e1
                sp = max(EL[e, 2], 1e-3)
                a = v / sp
                f = a - math.floor(a)
                q = 2.0 * f - 1.0
                bump = math.sqrt(max(0.0, 1.0 - q * q))
                l1 = _lod(sp, foot)
                slope = max(-1.4, min(1.4, -q / max(bump, 0.3))) * 0.35 * l1
                nx += slope * e2x
                ny += slope * e2y
                nz += slope * e2z
                lane = math.floor(f * 6.0) + 13.0 * math.floor(a)
                alb = (0.60 - 0.22 * (1.0 - bump ** 1.2) * l1 - 0.06 * (1.0 - l1)) * \
                      (1.0 + 0.08 * _vnoise(u * 1.3 + _hash(lane, 2.0) * 9.0, lane) * _lod(sp / 6.0, foot))
                fx, fy, fz = e1x, e1y, e1z
            elif mat == 2:                                   # a crocheted applique: stitches radiate from its centre
                nsp = EL[e, 2]
                nrd = EL[e, 3]
                rr = math.sqrt(u * u + v * v) + 1e-9
                th = math.atan2(v, u)
                s = th / TAU * nsp
                f = s - math.floor(s)
                q = 2.0 * f - 1.0
                bump = math.sqrt(max(0.0, 1.0 - q * q))
                l1 = _lod(TAU * rr / nsp, foot)
                ctx = -math.sin(th) * e1x + math.cos(th) * e2x  # across the spokes
                cty = -math.sin(th) * e1y + math.cos(th) * e2y
                ctz = -math.sin(th) * e1z + math.cos(th) * e2z
                slope = max(-1.4, min(1.4, -q / max(bump, 0.3))) * 0.30 * l1
                nx += slope * ctx
                ny += slope * cty
                nz += slope * ctz
                alb = 1.0 - 0.22 * (1.0 - bump ** 1.2) * l1 - 0.05 * (1.0 - l1)
                for k in range(1, int(nrd)):                 # the line where one round is worked into the last
                    dk = (rho - k / nrd) / 0.035
                    alb *= 1.0 - 0.16 * math.exp(-dk * dk)
                alb *= 1.0 - 0.22 * math.exp(-(rr / 0.7) ** 2)  # the closed magic ring
                alb *= 1.0 + 0.05 * _vnoise(rr * 1.7, math.floor(s) + 31.0)
                fx = math.cos(th) * e1x + math.sin(th) * e2x
                fy = math.cos(th) * e1y + math.sin(th) * e2y
                fz = math.cos(th) * e1z + math.sin(th) * e2z
            elif mat == 3:                                   # a plied thread: twist along its length
                pitch = max(EL[e, 2], 1e-3)
                nply = EL[e, 3]
                psi = nply * (v - TAU * u / pitch)
                f = psi / TAU
                f = f - math.floor(f)
                bump = math.sqrt(max(0.0, 1.0 - (2.0 * f - 1.0) ** 2))
                l1 = _lod(TAU * EL[e, 5] * 0.5 / nply, foot)
                alb = 1.0 - 0.25 * (1.0 - bump ** 1.3) * l1 - 0.07 * (1.0 - l1)
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) + 1e-12
            nx /= nl
            ny /= nl
            nz /= nl
            lit = _shadow_at(SM, sm, LB, lo, scale, wx, wy, wz, 0.35 * r, 1, 1)
            ndl = nx * ldir[0] + ny * ldir[1] + nz * ldir[2]
            ndv = min(1.0, max(0.0, -(nx * rx + ny * ry + nz * rz)))
            hx = ldir[0] - rx
            hy = ldir[1] - ry
            hz = ldir[2] - rz
            hl = math.sqrt(hx * hx + hy * hy + hz * hz) + 1e-9
            if mat == 4:                                     # glossy plastic, like the safety eyes
                ndh = max(0.0, (nx * hx + ny * hy + nz * hz) / hl)
                spec = (ndh ** 300 * 2.2 + ndh ** 30 * 0.18) * (0.3 + 0.7 * lit)
                env = 0.04 + 0.07 * max(0.0, ny)
                fres = (1.0 - ndv) ** 4 * 0.28
                for ch in range(3):
                    out[py, px, ch] = _shoulder(palette[ci, ch] * (0.25 + 0.35 * max(0.0, ndl)) + env + fres + spec)
                continue
            wrap = max(0.0, (ndl + 0.35) / 1.35)
            sky = 0.5 + 0.5 * ny
            amb = 0.30 + 0.16 * sky + 0.14 * ndv
            li = (1.0 * amb + 0.42 * wrap * lit) * exposure    # soft studio light: a lit face at about 1, a strong fill
            if fx != 0.0 or fy != 0.0 or fz != 0.0:          # Kajiya-Kay along the fibres
                th_ = (fx * hx + fy * hy + fz * hz) / hl
                spec = math.sqrt(max(0.0, 1.0 - th_ * th_)) ** 24 * gloss * lit
            else:
                ndh = max(0.0, (nx * hx + ny * hy + nz * hz) / hl)
                spec = (ndh ** 40 * 0.8 + ndh ** 8 * 0.2) * gloss * lit
            lum = 0.30 * palette[ci, 0] + 0.55 * palette[ci, 1] + 0.15 * palette[ci, 2] + 1e-3
            dk = max(0.0, 1.0 - li)
            for ch in range(3):
                pc = palette[ci, ch]
                tint = (pc / lum) ** (0.6 * dk)              # shade deepens in the dye colour, as on the yarn
                out[py, px, ch] = _shoulder(pc * alb * li * tint + spec * (0.35 + 0.65 * pc))


def soft_shape(X, r_vis, h, cmin=0.62):
    """How the soft yarn is pressed at every node: (Q, c), the direction it is flattened along and how much (1: round).
    It is flattened just enough to lie against the yarn it touches instead of running through it."""
    from scipy.spatial import cKDTree
    n = len(X)
    T = np.gradient(X, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None] + 1e-30
    A = np.zeros((n, 3, 3))
    Wt = np.zeros(n)
    pairs = cKDTree(X).query_pairs(2.0 * r_vis, output_type='ndarray')
    if len(pairs):
        skip = int(math.ceil(2.6 * r_vis / h))
        pairs = pairs[np.abs(pairs[:, 0] - pairs[:, 1]) > skip]
    if len(pairs):
        i, j = pairs[:, 0], pairs[:, 1]
        d = X[j] - X[i]
        dist = np.linalg.norm(d, axis=1) + 1e-30
        dep = 1.0 - dist / (2.0 * r_vis)
        for a, sg in ((i, 1.0), (j, -1.0)):
            nn = sg * d / dist[:, None]
            nn = nn - (nn * T[a]).sum(1)[:, None] * T[a]
            ln = np.linalg.norm(nn, axis=1)
            ok = ln > 0.5
            nn = nn[ok] / ln[ok, None]
            np.add.at(A, a[ok], (dep[ok] ** 3)[:, None, None] * nn[:, :, None] * nn[:, None, :])
            np.add.at(Wt, a[ok], dep[ok] ** 2)
        A /= np.maximum(Wt, 1e-9)[:, None, None]
    ker = np.array([1, 2, 3, 2, 1], float)
    ker /= ker.sum()
    Ap = np.pad(A, ((2, 2), (0, 0), (0, 0)), mode='edge')
    A = sum(ker[k] * Ap[k:k + n] for k in range(5))
    w, v = np.linalg.eigh(A)
    Q = v[:, :, 2]
    c = np.clip(1.0 - w[:, 2], cmin, 1.0)
    Q = Q - (Q * T).sum(1)[:, None] * T
    ql = np.linalg.norm(Q, axis=1)
    bad = ql < 0.3
    Q[bad] = np.cross(T[bad], np.array([0.3, 0.5, 0.8]))
    c[bad] = 1.0
    Q /= np.linalg.norm(Q, axis=1)[:, None] + 1e-30
    # one sign along the chain (an eigenvector's sign is arbitrary; flips would twist the section between nodes)
    for k in range(1, n):
        if Q[k] @ Q[k - 1] < 0:
            Q[k] = -Q[k]
    return Q, c


class Renderer:
    """Renders a yarn chain (plus optional glossy eyes) to an RGB uint8 image.

    Call `set_scene(X)` once with the whole finished yarn: the soft section shapes and the shadow map frame are then
    taken from the finished toy, so the part already made never changes shape or shadow while new yarn is added.
    """

    def __init__(self, W=1080, H=1920, ss=3, r=0.8, h=0.5, palette=None, light=(-0.45, 0.70, 0.55),
                 bg_top=(0.975, 0.955, 0.93), bg_bot=(0.935, 0.905, 0.87), soft=1.2, nply=2, pitch=None,
                 fuzz=0.6, sheen=0.04, halo=0.10, shadow_floor=0.0, sm=2048, aa=0.5, exposure=1.32,
                 backdrop_y=1e5, ao=1.0, dense=1):
        self.W, self.H, self.ss = int(W), int(H), int(ss)
        self.r, self.h, self.soft = float(r), float(h), float(soft)
        self.palette = np.array(palette if palette is not None else [[0.93, 0.52, 0.42]], float)
        l = np.asarray(light, float)
        self.ldir = l / np.linalg.norm(l)
        self.bg_top = np.asarray(bg_top, float)
        self.bg_bot = np.asarray(bg_bot, float)
        self.nply = float(nply)
        self.pitch = float(pitch) if pitch else 7.0 * self.r * self.soft / 1.2
        self.fuzz, self.sheen, self.halo = float(fuzz), float(sheen), float(halo)
        self.shadow_floor = float(shadow_floor)
        self.exposure = float(exposure)
        self.ao_amt = float(ao)
        self.aa = float(aa)
        self.plane_p = np.array([0.0, backdrop_y, 0.0])
        self.plane_n = np.array([0.0, -1.0, 0.0])
        self.sm = int(sm)
        self.cmin = min(0.62, 0.95 / max(self.soft, 1e-6))
        self.spread = 0.3
        self.sub = int(dense) * max(2, int(math.ceil(self.h / (0.32 * self.r))))
        w, hh = self.W * self.ss, self.H * self.ss
        self.zb = np.zeros((hh, w), np.float32)
        self.nb = np.zeros((hh, w, 3), np.float32)
        self.tb = np.zeros((hh, w, 3), np.float32)
        self.sb = np.zeros((hh, w), np.float32)
        self.pb = np.zeros((hh, w), np.float32)
        self.idb = np.zeros((hh, w), np.uint8)
        self.cb = np.zeros((hh, w), np.int32)
        self.out = np.zeros((hh, w, 3), np.float32)
        self.SM = np.zeros((self.sm, self.sm), np.float32)
        self._shape = None
        self.center = None
        self.extent = 70.0

    def set_scene(self, X):
        X = np.asarray(X, float)
        self._shape = soft_shape(X, self.r * self.soft, self.h, self.cmin)
        self._shape_n = len(X)
        lo, hi = X.min(0), X.max(0)
        self.center = 0.5 * (lo + hi)
        self.extent = 0.55 * float(np.linalg.norm(hi - lo)) + 4 * self.r

    def render(self, X, D, cam, colnode=None, radius=None, spheres=None, gap=2.0, shape_idx=None, details=None,
               details_t=1.0):
        """X, D: the nodes drawn and their directors.  colnode: palette index per node.  radius: per-node radius
        scale (the growing tip tapers in).  spheres: rows cx, cy, cz, radius, colour index.  shape_idx: for each node
        drawn, its index in the scene given to set_scene (default: the first len(X) nodes).  details: a
        details.Details (face, felt, appliques), shown as it is at reveal time details_t (0..1)."""
        import time
        tm = [time.perf_counter()]
        n = len(X)
        X = np.ascontiguousarray(X, np.float64)
        D = np.ascontiguousarray(D, np.float64)
        colnode = np.zeros(n, np.int32) if colnode is None else np.ascontiguousarray(colnode, np.int32)
        RS = np.ones(n) if radius is None else np.ascontiguousarray(radius, np.float64)
        sub = self.sub
        m_max = (n - 1) * sub + 1
        P = np.zeros((m_max, 3))
        T = np.zeros((m_max, 3))
        DD = np.zeros((m_max, 3))
        SS = np.zeros(m_max)
        RR = np.zeros(m_max)
        m = _samples(X, D, RS, n, sub, self.h, P, T, DD, SS, RR)
        w, hh = self.W * self.ss, self.H * self.ss
        B = cam.basis()
        fpx = 0.5 * w / math.tan(math.radians(cam.fov) / 2)
        self.zb.fill(1e30)
        self.idb.fill(0)
        rv = self.r * self.soft
        if self._shape is not None:
            idx = np.arange(n) if shape_idx is None else np.asarray(shape_idx)
            Qn, cn = self._shape[0][idx], self._shape[1][idx]
        else:
            Qn, cn = soft_shape(X, rv, self.h, self.cmin)
        ii = np.minimum(np.arange(m) // sub, n - 2)
        uu = ((np.arange(m) % sub) / sub)[:, None]
        q0, q1 = Qn[ii], Qn[ii + 1]
        q1 = q1 * np.sign((q0 * q1).sum(1) + 1e-12)[:, None]
        QQ = q0 * (1 - uu) + q1 * uu
        QQ -= (QQ * T[:m]).sum(1)[:, None] * T[:m]
        QQ /= np.linalg.norm(QQ, axis=1)[:, None] + 1e-30
        CC = cn[ii] * (1 - uu[:, 0]) + cn[ii + 1] * uu[:, 0]
        if gap is not None:
            seg = np.linalg.norm(np.diff(X, axis=0), axis=1)
            keep = seg[ii] <= gap
            keep &= seg[np.maximum(ii - 1, 0)] <= gap
            keep &= seg[np.minimum(ii + 1, n - 2)] <= gap
            P, T, DD, SS, RR = [np.ascontiguousarray(a[:m][keep]) for a in (P, T, DD, SS, RR)]
            QQ, CC = QQ[keep], CC[keep]
            m = int(keep.sum())
        tm.append(time.perf_counter())
        _splat(P, T, DD, SS, RR, np.ascontiguousarray(QQ), np.ascontiguousarray(CC), m, rv, cam.pos, B, fpx, w, hh,
               self.zb, self.nb, self.sb, self.pb, self.idb, 16, self.tb, self.spread)
        if spheres is not None and len(spheres):
            _trace_spheres(np.ascontiguousarray(np.asarray(spheres, np.float64)), cam.pos, B, fpx, w, hh,
                           self.zb, self.nb, self.idb, self.cb)
        dmesh = details.frame(details_t) if details is not None else None
        if dmesh is not None:
            if getattr(self, 'ub', None) is None:
                self.ub = np.zeros((hh, w, 3), np.float32)
            dV, dN, dU, dF, dE, dEL = dmesh
            _raster_details(dV, dN, dU, dF, dE, cam.pos, B, fpx, w, hh, self.zb, self.nb, self.idb, self.cb, self.ub, 16)
        tm.append(time.perf_counter())
        # shadow map: the frame is fixed on the whole scene and snapped to whole texels
        l = self.ldir
        up = np.array([0.0, 0.0, 1.0]) if abs(l[2]) < 0.95 else np.array([0.0, 1.0, 0.0])
        lr = np.cross(up, l)
        lr /= np.linalg.norm(lr)
        lu = np.cross(l, lr)
        LB = np.stack([lr, lu, l])
        ctr = self.center if self.center is not None else cam.target
        ext = self.extent
        scale = self.sm / (2 * ext)
        lo = np.array([LB[0] @ ctr - ext, LB[1] @ ctr - ext])
        lo = np.floor(lo * scale) / scale
        self.SM.fill(-1e30)
        _shadow_splat(P, RR, m, rv, LB, lo, scale, self.SM, self.sm)
        if spheres is not None and len(spheres):
            S = np.asarray(spheres, float)
            S = S[S[:, 3] > 0]
            if len(S):
                _shadow_splat(np.ascontiguousarray(S[:, :3]), np.ascontiguousarray(S[:, 3]), len(S), 1.0, LB, lo,
                              scale, self.SM, self.sm)
        tm.append(time.perf_counter())
        ao_r = fpx * 2.8 * self.r / max(1.0, float(np.linalg.norm(cam.target - cam.pos)))
        _shade(self.zb, self.nb, self.sb, self.pb, self.idb, self.cb, self.tb, colnode, n, self.h, cam.pos, B, fpx, w,
               hh, LB, lo, scale, self.SM, self.sm, self.ldir, self.palette, self.bg_top, self.bg_bot, self.plane_p,
               self.plane_n, self.r, rv, self.pitch, self.nply, self.out, ao_r, self.fuzz, self.sheen, self.halo,
               self.shadow_floor, self.exposure, self.ao_amt)
        if dmesh is not None:
            _shade_details(self.zb, self.nb, self.idb, self.cb, self.ub, cam.pos, B, fpx, w, hh, LB, lo, scale, self.SM,
                           self.sm, self.ldir, self.palette, dEL, self.r, self.exposure, self.out)
        tm.append(time.perf_counter())
        img = self.out
        if self.ss > 1 or self.aa > 0:
            img = downsample(img, self.ss, self.aa)
        tm.append(time.perf_counter())
        self.times = dict(zip(('prep', 'splat', 'shadow', 'shade', 'down'), np.diff(tm).round(3)))
        return (np.clip(np.nan_to_num(img), 0, 1) * 255 + 0.5).astype(np.uint8)


def downsample(img, ss, aa=0.6):
    """Gaussian reconstruction (sigma = aa output pixels), then decimation by ss.  A plain ss x ss box lets an edge
    jump by a whole pixel when it crosses a sample; the Gaussian makes it move by sub-pixel steps."""
    from scipy.ndimage import gaussian_filter
    if aa > 0:
        sig = aa * ss
        img = gaussian_filter(img, (sig, sig, 0), mode='nearest')
    if ss > 1:
        H, W = img.shape[0] // ss, img.shape[1] // ss
        img = img[:H * ss, :W * ss].reshape(H, ss, W, ss, 3).mean(axis=(1, 3))
    return img
