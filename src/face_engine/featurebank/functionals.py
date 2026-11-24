"""Statistical functionals applied to every (signal, condition) pair.

Each functional maps a 1-D float array (NaN = missing) sampled at ``fps`` to one number.
Everything is a plain quantity of this one person; interpretation happens downstream.
"""

from __future__ import annotations

import numpy as np


def _finite(x: np.ndarray) -> np.ndarray:
    return x[np.isfinite(x)]


def _runs(mask: np.ndarray) -> list[int]:
    out, n = [], 0
    for m in mask:
        if m:
            n += 1
        elif n:
            out.append(n)
            n = 0
    if n:
        out.append(n)
    return out


def compute(x: np.ndarray, fps: float, ref_mu: float, ref_sd: float) -> dict[str, float]:
    """All functionals for one series. ``ref_mu``/``ref_sd`` are the person's whole-clip
    baseline for this signal, so threshold features mean 'unusual for this person'."""
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError("fps must be finite and positive")
    x = np.asarray(x, dtype=float).copy()
    x[~np.isfinite(x)] = np.nan
    n_all = len(x)
    v = _finite(x)
    res: dict[str, float] = {"valid_share": len(v) / n_all if n_all else 0.0}
    if len(v) < max(5, int(0.5 * fps)):
        return res
    mu, sd = float(np.mean(v)), float(np.std(v))
    q = np.quantile(v, [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95])
    res.update(
        mean=mu, std=sd, min=float(v.min()), max=float(v.max()),
        p05=q[0], p10=q[1], p25=q[2], median=q[3], p75=q[4], p90=q[5], p95=q[6],
        iqr=q[4] - q[2], range_p95_p05=q[6] - q[0],
        cv=sd / abs(mu) if abs(mu) > 1e-9 else np.nan,
    )
    if sd > 1e-12:
        z = (v - mu) / sd
        res["skew"] = float(np.mean(z**3))
        res["kurtosis"] = float(np.mean(z**4) - 3)
    # time structure (uses the raw series with gaps so deltas never jump across holes)
    d = np.diff(x)
    d = d[np.isfinite(d)]
    if len(d):
        res["mean_abs_delta_per_s"] = float(np.mean(np.abs(d)) * fps)
        res["std_delta_per_s"] = float(np.std(d) * fps)
        res["max_abs_delta_per_s"] = float(np.max(np.abs(d)) * fps)
    idx = np.where(np.isfinite(x))[0]
    if len(idx) > 2:
        t_min = idx / fps / 60
        res["slope_per_min"] = float(np.polyfit(t_min, x[idx], 1)[0])
    rs = ref_sd if ref_sd and ref_sd > 1e-9 else sd
    if rs > 1e-9:
        hi = np.isfinite(x) & (x > ref_mu + rs)
        lo = np.isfinite(x) & (x < ref_mu - rs)
        res["share_above_baseline_1sd"] = float(hi.sum() / len(v))
        res["share_below_baseline_1sd"] = float(lo.sum() / len(v))
        res["z_mean_vs_person"] = (mu - ref_mu) / rs
        runs = _runs(hi)
        res["longest_high_run_s"] = max(runs) / fps if runs else 0.0
        res["high_episodes_per_min"] = len([r for r in runs if r >= 2]) / (len(v) / fps / 60)
        # local peaks above baseline+1sd, at least 0.25 s apart
        xx = np.nan_to_num(x, nan=-np.inf)
        pk = np.where((xx[1:-1] > xx[:-2]) & (xx[1:-1] >= xx[2:]) & (xx[1:-1] > ref_mu + rs))[0]
        keep, last = 0, -1e9
        for p in pk:
            if p - last >= 0.25 * fps:
                keep += 1
                last = p
        res["peaks_per_min"] = keep / (len(v) / fps / 60)
    lag = max(1, int(round(fps)))
    if len(v) > 3 * lag and sd > 1e-9:
        pairs = np.isfinite(x[:-lag]) & np.isfinite(x[lag:])
        if pairs.sum() >= 3:
            a, b = x[:-lag][pairs], x[lag:][pairs]
            if np.std(a) > 1e-9 and np.std(b) > 1e-9:
                res["autocorr_1s"] = float(np.corrcoef(a, b)[0, 1])
    return res


NAMES = (
    "valid_share mean std min max p05 p10 p25 median p75 p90 p95 iqr range_p95_p05 cv skew kurtosis "
    "mean_abs_delta_per_s std_delta_per_s max_abs_delta_per_s slope_per_min share_above_baseline_1sd "
    "share_below_baseline_1sd z_mean_vs_person longest_high_run_s high_episodes_per_min peaks_per_min "
    "autocorr_1s"
).split()
