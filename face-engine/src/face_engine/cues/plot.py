"""Timeline PNG of the behaviour map for a quick visual check."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def plot(behavior: dict[str, Any], path: str | Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tl = behavior["timeline"]
    t = np.array(tl["t"], float)
    chans = list(tl["channels"])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(14, 2.2 + 0.35 * len(chans)), sharex=True,
                                 gridspec_kw={"height_ratios": [1, max(1.5, 0.35 * len(chans))]})
    a1.plot(t, np.array(tl["pressure"], float), color="#E8322B", lw=1.4)
    a1.set_ylabel("pressure")
    a1.set_ylim(0, 100)
    m = np.array([[np.nan if v is None else v for v in tl["channels"][c]] for c in chans], float)
    im = a2.imshow(np.clip(m, 0, 4), aspect="auto", cmap="magma", vmin=0, vmax=4,
                   extent=[t[0], t[-1] if len(t) > 1 else t[0] + 1, len(chans) - 0.5, -0.5])
    a2.set_yticks(range(len(chans)), chans)
    off = behavior["meta"].get("time_offset_s", 0.0)
    for h in behavior["hotspots"]:
        for ax in (a1, a2):
            ax.axvspan(h["start_s"] + off, h["end_s"] + off, color="#F2B33D", alpha=0.18, lw=0)
    for q in behavior.get("questions", []):
        a1.axvline(q["end_s"] + off, color="#8A8F98", lw=0.6, ls=":")
    a2.set_xlabel("seconds")
    fig.colorbar(im, ax=a2, label="SD from own baseline", fraction=0.02)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
