#!/usr/bin/env python3
"""Train + temporally validate both NHANES oral-health models.

Outcomes (see src/harmonise.py for definitions):
  * tooth_loss:          <20 remaining teeth, adults 30+
                         fit 1999-2012 | validation 2013-2014 | refit 1999-2014 | test 2015-2016 + 2017-Mar2020
  * severe_periodontitis: CDC/AAP severe, dentate adults 30+, full-mouth cycles only
                         fit 2009-2010 | validation 2011-2012 | refit 2009-2012 | test 2013-2014

Models (CPU only): logistic regression (interpretable baseline) and
HistGradientBoostingClassifier. Predictors are NON-dental only.
Metrics: AUC, accuracy, sensitivity, specificity, PPV, NPV, Brier score and
ECE (10 equal-width bins) at the 0.5 threshold, plus sensitivity/specificity at
the Youden threshold fitted on the validation split. Fairness audit: the same
metrics stratified by race/ethnicity, PIR band and smoking status on the test set.

Outputs: results/metrics_toothloss.json, results/metrics_periodontitis.json,
results/lr_coefficients_<outcome>.json, results/hgb_importance_<outcome>.json
(and per-model predicted probabilities are NOT saved: SEQN-level predictions
stay out of the pushable tree).

Run: ~/workspace/venvs/crop-disease/bin/python src/train.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, brier_score_loss, confusion_matrix,
                             roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "harmonised"
RES = ROOT / "results"
RES.mkdir(parents=True, exist_ok=True)

NUM = ["age", "pir", "hba1c", "bmi", "crp_mg_l", "kcal", "protein_g",
       "carb_g", "fiber_g", "chol_mg", "sodium_mg"]
CAT = ["sex", "race_eth", "education", "smoking", "diabetes"]
# Fixed clinical caps (winsorisation) applied before modelling; documented in DATA.md.
CAPS = {"age": (30, 85), "pir": (0, 5), "hba1c": (3.0, 15.0), "bmi": (12.0, 70.0),
        "crp_mg_l": (0.0, 100.0), "kcal": (0.0, 8000.0), "protein_g": (0.0, 400.0),
        "carb_g": (0.0, 1000.0), "fiber_g": (0.0, 150.0), "chol_mg": (0.0, 2000.0),
        "sodium_mg": (0.0, 15000.0)}
MISS_IND = ["hba1c", "crp_mg_l", "pir"]  # missingness indicators (clinically meaningful)


def add_missing_indicators(df):
    df = df.copy()
    for c in MISS_IND:
        df[f"{c}_missing"] = df[c].isna().astype(int)
    return df


def clip(df):
    df = df.copy()
    for c, (lo, hi) in CAPS.items():
        if c in df.columns:
            df[c] = df[c].clip(lo, hi)
    return df


def make_models():
    num_pipe = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    cat_pipe = Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                         ("onehot", OneHotEncoder(handle_unknown="ignore"))])
    pre = ColumnTransformer([
        ("num", num_pipe, NUM + [f"{c}_missing" for c in MISS_IND]),
        ("cat", cat_pipe, CAT)])
    lr = Pipeline([("pre", pre),
                   ("scaler", StandardScaler()),
                   ("clf", LogisticRegression(max_iter=2000, class_weight="balanced",
                                              random_state=42))])
    hgb = Pipeline([("pre", pre),
                    ("clf", HistGradientBoostingClassifier(
                        max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                        min_samples_leaf=40, l2_regularization=1.0,
                        class_weight="balanced", random_state=42))])
    return {"logistic_regression": lr, "hist_gbm": hgb}


def ece(y, p, n_bins=10):
    edges = np.linspace(0, 1, n_bins + 1)
    tot = 0.0
    for i in range(n_bins):
        m = (p > edges[i]) & (p <= edges[i] if i == n_bins - 1 else p < edges[i + 1])
        if i == 0:
            m = (p >= edges[0]) & (p < edges[1])
        if m.sum() == 0:
            continue
        tot += abs(p[m].mean() - y[m].mean()) * m.mean()
    return float(tot)


def metrics(y, p, thr=0.5):
    pred = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "n": int(len(y)), "n_positive": int(y.sum()),
        "prevalence": float(y.mean()),
        "threshold": float(thr),
        "auc": float(roc_auc_score(y, p)) if y.nunique() > 1 else None,
        "accuracy": float(accuracy_score(y, pred)),
        "sensitivity": float(tp / (tp + fn)) if tp + fn else None,
        "specificity": float(tn / (tn + fp)) if tn + fp else None,
        "ppv": float(tp / (tp + fp)) if tp + fp else None,
        "npv": float(tn / (tn + fn)) if tn + fn else None,
        "brier": float(brier_score_loss(y, p)),
        "ece_10bin": ece(y.values, p),
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
    }


def youden_threshold(y, p):
    from sklearn.metrics import roc_curve
    fpr, tpr, thr = roc_curve(y, p)
    return float(thr[int(np.argmax(tpr - fpr))])


def fairness(df_test, y, models_proba, outcome):
    """Stratified test metrics by race/ethnicity, PIR band, smoking status."""
    out = {}
    df = df_test.copy()
    df["pir_band"] = pd.cut(df["pir"], [-np.inf, 1, 2, 4, np.inf],
                            labels=["<1", "1-<2", "2-<4", ">=4"])
    for col in ["race_eth", "pir_band", "smoking"]:
        out[col] = {}
        for level, idx in df.groupby(col, observed=True).groups.items():
            idx = list(idx)
            yy = y.loc[idx]
            entry = {"n": int(len(yy)), "n_positive": int(yy.sum()),
                     "prevalence": float(yy.mean()) if len(yy) else None}
            for name, p in models_proba.items():
                pp = p.loc[idx]
                m = metrics(yy, pp)
                entry[name] = {"auc": m["auc"], "sensitivity": m["sensitivity"],
                               "specificity": m["specificity"], "accuracy": m["accuracy"],
                               "ece_10bin": m["ece_10bin"]}
            out[col][str(level)] = entry
    return out


def run_outcome(name, csv, target, fit_cycles, val_cycles, test_cycles):
    df = pd.read_csv(DATA / csv)
    df = add_missing_indicators(clip(df))
    y_all = df[target]
    feat = NUM + [f"{c}_missing" for c in MISS_IND] + CAT
    X_all = df[feat]
    fit_m = df["cycle"].isin(fit_cycles)
    val_m = df["cycle"].isin(val_cycles)
    test_m = df["cycle"].isin(test_cycles)
    result = {"outcome": name, "target": target,
              "splits": {"fit": fit_cycles, "validation": val_cycles, "test": test_cycles,
                         "n_fit": int(fit_m.sum()), "n_validation": int(val_m.sum()),
                         "n_test": int(test_m.sum()),
                         "prev_fit": float(y_all[fit_m].mean()),
                         "prev_validation": float(y_all[val_m].mean()),
                         "prev_test": float(y_all[test_m].mean())},
              "models": {}}
    models = make_models()
    for mname, model in models.items():
        model.fit(X_all[fit_m], y_all[fit_m])
        p_val = pd.Series(model.predict_proba(X_all[val_m])[:, 1], index=df.index[val_m])
        thr_y = youden_threshold(y_all[val_m], p_val)
        # refit on fit + validation, evaluate once on the untouched test set
        model.fit(X_all[fit_m | val_m], y_all[fit_m | val_m])
        p_test = pd.Series(model.predict_proba(X_all[test_m])[:, 1], index=df.index[test_m])
        y_test = y_all[test_m]
        entry = {
            "validation_fit_only": metrics(y_all[val_m], p_val),
            "youden_threshold_from_validation": thr_y,
            "test_at_0.5": metrics(y_test, p_test, 0.5),
            "test_at_youden": metrics(y_test, p_test, thr_y),
        }
        # LR coefficients / HGB permutation importance (test set, 5 repeats)
        if mname == "logistic_regression":
            pre = model.named_steps["pre"]
            names = pre.get_feature_names_out()
            coefs = model.named_steps["clf"].coef_[0]
            entry["coefficients"] = {str(n): float(c) for n, c in
                                     sorted(zip(names, coefs), key=lambda t: -abs(t[1]))}
            json.dump(entry["coefficients"],
                      open(RES / f"lr_coefficients_{name}.json", "w"), indent=1)
        else:
            pi = permutation_importance(model, X_all[test_m], y_test, n_repeats=5,
                                        random_state=42, scoring="roc_auc")
            entry["permutation_importance_auc"] = {
                str(f): float(v) for f, v in
                sorted(zip(feat, pi.importances_mean), key=lambda t: -t[1])}
            json.dump(entry["permutation_importance_auc"],
                      open(RES / f"hgb_importance_{name}.json", "w"), indent=1)
        result["models"][mname] = entry
        t = entry["test_at_0.5"]
        print(f"{name} | {mname}: test AUC={t['auc']:.3f} sens={t['sensitivity']:.3f} "
              f"spec={t['specificity']:.3f} ECE={t['ece_10bin']:.3f} "
              f"(n={t['n']}, prev={t['prevalence']:.3f})", flush=True)
    # fairness audit on the test set (refit models already fitted above)
    proba = {}
    for mname, model in models.items():
        proba[mname] = pd.Series(model.predict_proba(X_all[test_m])[:, 1],
                                 index=df.index[test_m])
    # anonymous test-set predictions (no SEQN) for the figures script
    pred_df = pd.DataFrame({"cycle": df.loc[test_m, "cycle"].values,
                            "y": y_all[test_m].values})
    for mname, p in proba.items():
        pred_df[f"p_{mname}"] = p.values
    pred_df.to_csv(RES / f"test_predictions_{name}.csv", index=False)
    result["fairness_test"] = fairness(df[test_m], y_all[test_m], proba, name)
    json.dump(result, open(RES / f"metrics_{name}.json", "w"), indent=1)
    return result


def main():
    run_outcome("toothloss", "toothloss.csv", "tooth_loss",
                fit_cycles=["1999-2000", "2001-2002", "2003-2004", "2005-2006",
                            "2007-2008", "2009-2010", "2011-2012"],
                val_cycles=["2013-2014"],
                test_cycles=["2015-2016", "2017-Mar2020"])
    run_outcome("periodontitis", "periodontitis.csv", "severe_periodontitis",
                fit_cycles=["2009-2010"],
                val_cycles=["2011-2012"],
                test_cycles=["2013-2014"])
    print("done.")


if __name__ == "__main__":
    main()
