"""Management charts from validated Phase 1 and sensitivity outputs."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.paths import OUTPUTS_DIR, REPO_ROOT
from src.sensitivity import CHANNEL_ORDER, SCENARIOS


CHARTS_DIR = OUTPUTS_DIR / "charts"
CASE_CHARTS_DIR = REPO_ROOT / "case-study" / "charts"

SHORT = {
    "Meta Ads": "Meta",
    "Google Ads - Search": "Search",
    "Google Ads - YouTube": "YouTube",
}
COLORS = {
    "Meta Ads": "#1B4F72",
    "Google Ads - Search": "#7B8A99",
    "Google Ads - YouTube": "#2E6B8A",
}
NAVY = "#1A2332"
MUTED = "#5B6775"
GRID = "#E6E8EB"


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "axes.axisbelow": True,
            "axes.facecolor": "white",
            "figure.facecolor": "white",
            "axes.edgecolor": "#C5C9CE",
            "text.color": NAVY,
            "axes.labelcolor": MUTED,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "axes.titlecolor": NAVY,
            "figure.dpi": 150,
        }
    )


def _save(fig: plt.Figure, name: str) -> Path:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    CASE_CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHARTS_DIR / name
    fig.savefig(path, bbox_inches="tight", facecolor="white", pad_inches=0.2)
    fig.savefig(CASE_CHARTS_DIR / name, bbox_inches="tight", facecolor="white", pad_inches=0.2)
    plt.close(fig)
    return path


def _ordered(df: pd.DataFrame) -> pd.DataFrame:
    out = df.set_index("channel").loc[CHANNEL_ORDER].reset_index()
    out["label"] = out["channel"].map(SHORT)
    return out


def generate_charts(alloc: pd.DataFrame, sensitivity: pd.DataFrame, retention: pd.DataFrame) -> list[str]:
    _style()
    alloc = _ordered(alloc)
    written: list[Path] = []
    written.append(_spend_mix(alloc))
    written.append(_bar(alloc, "blended_cac", "Blended CAC by channel", "Blended CAC (USD)", "blended_cac.png", "${:,.0f}"))
    written.append(
        _bar(
            alloc,
            "platform_attributed_roas",
            "Platform-attributed ROAS by channel",
            "Platform-attributed ROAS",
            "attributed_roas.png",
            "{:.2f}x",
        )
    )
    written.append(_cm_cac(alloc))
    written.append(_payback(alloc))
    written.append(_sensitivity_matrix(sensitivity))
    written.append(_retention(retention))
    return [str(p.relative_to(REPO_ROOT)).replace("\\", "/") for p in written]


def _spend_mix(alloc: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(4.6, 2.2))
    labels = list(alloc["label"][::-1])
    vals = list((alloc["total_spend"] / 1_000_000)[::-1])
    colors = [COLORS[c] for c in alloc["channel"][::-1]]
    spends = list(alloc["total_spend"][::-1])
    mixes = list(alloc["spend_mix_pct"][::-1])
    bars = ax.barh(labels, vals, color=colors, height=0.58)
    ax.set_xlabel("Spend ($ millions)")
    ax.set_title("Channel spend mix")
    ax.set_xlim(0, max(vals) * 1.45)
    ax.grid(axis="y")
    for bar, spend, mix in zip(bars, spends, mixes):
        ax.text(
            bar.get_width() + 0.05,
            bar.get_y() + bar.get_height() / 2,
            f"${spend/1e6:.2f}M ({100*mix:.1f}%)",
            va="center",
            fontsize=8,
            color=NAVY,
        )
    fig.tight_layout()
    return _save(fig, "spend_mix.png")


def _bar(alloc: pd.DataFrame, col: str, title: str, ylabel: str, filename: str, fmt: str) -> Path:
    fig, ax = plt.subplots(figsize=(4.6, 2.2))
    colors = [COLORS[c] for c in alloc["channel"]]
    bars = ax.bar(list(alloc["label"]), list(alloc[col]), color=colors, width=0.58)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ymax = float(max(alloc[col])) * 1.28
    ax.set_ylim(0, ymax)
    for bar, val in zip(bars, alloc[col]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + ymax * 0.04,
            fmt.format(val),
            ha="center",
            va="bottom",
            fontsize=8,
            color=NAVY,
        )
    fig.tight_layout()
    return _save(fig, filename)


def _cm_cac(alloc: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(4.6, 2.2))
    colors = [COLORS[c] for c in alloc["channel"]]
    vals = list(alloc["modeled_lifetime_contribution_to_cac_weighted"])
    bars = ax.bar(list(alloc["label"]), vals, color=colors, width=0.58)
    ax.axhline(1.0, color="#8B3A3A", linewidth=1.0, linestyle="--")
    ax.set_ylabel("Weighted modeled lifetime CM / CAC")
    ax.set_title("Weighted modeled lifetime contribution / CAC")
    ymax = max(vals) * 1.28
    ax.set_ylim(0, ymax)
    for bar, val in zip(bars, vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + ymax * 0.04,
            f"{val:.2f}x",
            ha="center",
            va="bottom",
            fontsize=8,
            color=NAVY,
        )
    ax.text(0.02, 0.95, "Dashed line = 1.0x", transform=ax.transAxes, ha="left", va="top", fontsize=7, color=MUTED)
    fig.tight_layout()
    return _save(fig, "weighted_cm_cac.png")


def _payback(alloc: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(4.6, 2.2))
    colors = [COLORS[c] for c in alloc["channel"]]
    vals = [int(v) for v in alloc["modeled_payback_month_index"]]
    bars = ax.bar(list(alloc["label"]), vals, color=colors, width=0.58)
    ax.set_ylabel("Modeled payback month")
    ax.set_title("Modeled payback (0 = acquisition month)")
    ymax = max(vals) * 1.35
    ax.set_ylim(0, ymax)
    for bar, val in zip(bars, vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + ymax * 0.04,
            str(val),
            ha="center",
            va="bottom",
            fontsize=8,
            color=NAVY,
        )
    fig.tight_layout()
    return _save(fig, "payback.png")


def _sensitivity_matrix(sensitivity: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(6.8, 2.85))
    scen_ids = [s[0] for s in SCENARIOS]
    scen_labels = [s[1] for s in SCENARIOS]
    ch_labels = [SHORT[c] for c in CHANNEL_ORDER]
    matrix = np.zeros((len(scen_ids), len(CHANNEL_ORDER)))
    for i, sid in enumerate(scen_ids):
        for j, ch in enumerate(CHANNEL_ORDER):
            val = sensitivity.loc[
                (sensitivity["scenario_id"] == sid) & (sensitivity["channel"] == ch),
                "weighted_lifetime_contribution_to_cac",
            ]
            matrix[i, j] = float(val.iloc[0])

    im = ax.imshow(matrix, cmap="Blues", vmin=0.8, vmax=3.5, aspect="auto")
    ax.set_xticks(range(len(ch_labels)), ch_labels, fontsize=9)
    ax.set_yticks(range(len(scen_labels)), scen_labels, fontsize=8)
    ax.set_title("Sensitivity: weighted modeled lifetime contribution / CAC")
    ax.grid(False)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            color = "white" if matrix[i, j] > 2.3 else NAVY
            ax.text(j, i, f"{matrix[i, j]:.2f}x", ha="center", va="center", fontsize=8, color=color, fontweight="bold")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cbar.ax.tick_params(labelsize=7)
    fig.tight_layout()
    return _save(fig, "sensitivity_cm_cac.png")


def _retention(retention: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(4.6, 2.0))
    ax.plot(retention["month_index"], retention["retention_rate_t"], color="#1B4F72", linewidth=1.8, label="Baseline assumption")
    down = retention["retention_rate_t"].copy()
    down.iloc[1:] = down.iloc[1:] * 0.80
    ax.plot(retention["month_index"], down, color="#7B8A99", linewidth=1.5, linestyle="--", label="Downside (m>=1 x 0.80)")
    ax.set_xlabel("Month index (0 = acquisition)")
    ax.set_ylabel("Assumed retention rate")
    ax.set_title("Modeled retention curve (shared across channels)")
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False, fontsize=7, loc="upper right")
    fig.tight_layout()
    return _save(fig, "retention_assumption.png")
