#!/usr/bin/env python3
"""ROC + calibration figures from the anonymous test-set predictions saved by train.py.

Reads results/test_predictions_<outcome>.csv and writes
results/figures/roc_<outcome>.png and results/figures/calibration_<outcome>.png.

Run: ~/workspace/venvs/crop-disease/bin/python src/figures.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import auc, roc_curve

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
FIG = RES / "figures"
FIG.mkdir(parents=True, exist_ok=True)

MODELS = {"logistic_regression": ("Logistic regression", "tab:blue"),
          "hist_gbm": ("HistGradientBoosting", "tab:orange")}
TITLES = {"toothloss": "Tooth loss (<20 teeth), temporal test 2015-2016 + 2017-Mar 2020",
          "periodontitis": "Severe periodontitis (CDC/AAP), temporal test 2013-2014"}


def roc_fig(name):
    d = pd.read_csv(RES / f"test_predictions_{name}.csv")
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="Chance")
    for col, (label, color) in MODELS.items():
        fpr, tpr, _ = roc_curve(d["y"], d[f"p_{col}"])
        ax.plot(fpr, tpr, color=color, lw=2, label=f"{label} (AUC {auc(fpr, tpr):.3f})")
    ax.set_xlabel("1 - specificity")
    ax.set_ylabel("Sensitivity")
    ax.set_title(f"ROC — {TITLES[name]}\n(n={len(d)}, prevalence {d['y'].mean():.3f})")
    ax.legend(loc="lower right")
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(FIG / f"roc_{name}.png", dpi=150)
    plt.close(fig)


def calib_fig(name):
    d = pd.read_csv(RES / f"test_predictions_{name}.csv")
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="Perfect calibration")
    edges = np.linspace(0, 1, 11)
    for col, (label, color) in MODELS.items():
        p = d[f"p_{col}"].values
        y = d["y"].values
        xs, ys = [], []
        for i in range(10):
            m = (p >= edges[i]) & (p < edges[i + 1] if i < 9 else p <= edges[i + 1])
            if m.sum() > 0:
                xs.append(p[m].mean())
                ys.append(y[m].mean())
        ax.plot(xs, ys, "o-", color=color, lw=2, label=label)
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed frequency")
    ax.set_title(f"Calibration — {TITLES[name]}\n(n={len(d)}, 10 equal-width bins)")
    ax.legend(loc="upper left")
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(FIG / f"calibration_{name}.png", dpi=150)
    plt.close(fig)


def main():
    for name in TITLES:
        roc_fig(name)
        calib_fig(name)
        print("wrote figures for", name)
    print("figures in", FIG)


if __name__ == "__main__":
    main()
