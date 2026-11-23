"""Recreate the README figure. From the repository root run python3 -m examples.plot_comparison."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from surgical.analysis import build_cases, compare
from surgical.fixture import make_fixture
from surgical.prices import load_catalog

ROOT = Path(__file__).resolve().parents[1]


def main():
    cases = build_cases(make_fixture(), load_catalog(ROOT / "data/device_prices.csv"))
    panels = [
        ("Index surgery cost", "USD per case", compare(cases, lambda case: case.cost), 1),
        ("Recorded recurrence at one year", "Percentage points", compare(cases, lambda case: case.outcome), 100),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.5), sharey=True)
    fig.subplots_adjust(left=.21, right=.97, top=.69, bottom=.26, wspace=.27)
    fig.text(.025, .91, "How case mix changes the comparison", fontsize=20, weight="bold", color="#20323c")
    fig.text(.025, .82, "Fictional MESH-B minus MESH-A  ·  Dots show differences. Lines show 95% bootstrap intervals.",
             fontsize=10, color="#3b525c")
    for ax, (title, unit, contrast, scale) in zip(axes, panels):
        ax.axvline(0, color="#74868c", linestyle="--", linewidth=1)
        for y, estimate in zip([2, 1, 0], [contrast.crude, contrast.overlap_crude, contrast.adjusted]):
            if estimate is None:
                continue
            value = estimate.difference * scale
            low, high = (bound * scale for bound in estimate.interval)
            color = "#21635f" if y == 0 else "#526a79"
            ax.hlines(y, low, high, color=color, linewidth=2)
            ax.plot(value, y, "o", markersize=7, color=color)
        ax.set_title(title, fontsize=12, fontweight="bold", loc="left")
        ax.set_xlabel(unit, fontsize=10)
        ax.set_ylim(-.5, 2.5)
        ax.spines[["left", "right", "top"]].set_visible(False)
        ax.spines["bottom"].set_color("#9eacb1")
        ax.tick_params(axis="y", length=0, pad=12)
        ax.tick_params(axis="x", color="#9eacb1")
    axes[0].set_yticks([2, 1, 0], labels=["All eligible cases", "Comparable strata", "Standardized case mix"])
    fig.text(.025, .065, "Each endpoint uses its own eligible cases. Standardization weights the shared preoperative strata.",
             color="#3b525c", fontsize=9)
    output = ROOT / "docs/case-comparison.png"
    output.parent.mkdir(exist_ok=True)
    fig.savefig(output, dpi=160, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
