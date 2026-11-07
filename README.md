# Predicting severe periodontitis and tooth loss from non-dental data: NHANES 1999–2020

Can severe periodontitis and tooth loss be predicted from demographics,
socioeconomics, smoking, diabetes/HbA1c, BMI, diet and CRP — with no dental
examination at all — and does the prediction hold up years later, and equally
across groups? Pooled NHANES, temporal validation, fairness audit.

## Question
Two outcomes, non-dental predictors only:
1. **Severe periodontitis** (CDC/AAP case definition) — adults 30+ with a
   full-mouth periodontal exam, 2009–2014 only (the FMPE ran in those cycles
   only; see DATA.md).
2. **Tooth loss** (<20 remaining teeth, functional-dentition threshold) —
   adults 30+ with a dentition exam, 1999–2020.

## Datasets
See [DATA.md](DATA.md). In short: CDC/NCHS NHANES public-use files,
1999–2000 through 2017–March 2020 (pre-pandemic combined file). 89 XPT files,
~400 MB, in `data/raw/` (gitignored). Pooled analytic samples actually
achieved: **42,167** adults 30+ for tooth loss (30.0% with <20 teeth, 10.0%
edentulous) and **10,700** dentate adults 30+ for periodontitis (11.2% severe;
CDC/AAP categories: none 48.8%, mild 4.7%, moderate 35.3%, severe 11.2%).
The often-cited ~37,668 pooled figure refers to a different sample
definition; ours is larger because it includes the 2015–2016 and 2017–Mar
2020 cycles and adults 30+ throughout.

## What is novel here
1. **Temporal validation as the headline**, not a random split: tooth-loss
   models train on 1999–2014 and test on 2015–2020; periodontitis models
   train on 2009–2012 and test on 2013–2014.
2. **Non-dental predictors only** — the point is screening without a dental
   visit: age, sex, race/ethnicity, PIR, education, smoking, diabetes/HbA1c,
   BMI, diet, CRP.
3. **Fairness audit** on the test set by race/ethnicity, PIR band and smoking
   status — reported as findings, including where the models fail a group.
4. **Calibration reported honestly** (ECE + curves), including a badly
   miscalibrated model — not hidden behind AUC.

## Pipeline
```
src/download_nhanes.py  CDC XPT downloads (89 files) -> data/raw/, results/download_log.json
src/harmonise.py        per-cycle harmonisation, tooth count, CDC/AAP case definition
                        -> data/harmonised/toothloss.csv, periodontitis.csv, harmonisation.json
src/train.py            logistic regression + HistGradientBoosting, temporal splits,
                        validation-split Youden thresholds, fairness audit
                        -> results/metrics_{toothloss,periodontitis}.json, lr_coefficients_*.json,
                           hgb_importance_*.json, test_predictions_*.csv
src/figures.py          ROC + calibration curves -> results/figures/*.png
```

## Reproduce
```bash
# 1. Download (CDC public-use, no login; ~400 MB)
python3 src/download_nhanes.py
# 2. Harmonise (CPU, ~10 s)
~/workspace/venvs/crop-disease/bin/python src/harmonise.py
# 3. Train + evaluate (CPU-only box, ~2 min)
~/workspace/venvs/crop-disease/bin/python src/train.py
# 4. Figures
~/workspace/venvs/crop-disease/bin/python src/figures.py
```
Environment: Python 3.12, pandas 3.0.6, scikit-learn 1.9.1
(`~/workspace/venvs/crop-disease`). No GPU needed; no GPU used. No survey
weights (prediction, not population estimation — see DATA.md).

## Results (actual runs on this box, 2026-11-07 — no invented metrics)

### Tooth loss — temporal test 2015–2016 + 2017–Mar 2020 (n=11,227, prev 27.6%)
Full files: `results/metrics_toothloss.json`, `results/figures/roc_toothloss.png`,
`results/figures/calibration_toothloss.png`.

| Model | AUC | Sens / spec @0.5 | Accuracy | ECE | Brier |
|---|---|---|---|---|---|
| Logistic regression | 0.854 | 0.818 / 0.733 | 0.757 | 0.149 | 0.165 |
| HistGradientBoosting | **0.861** | 0.840 / 0.722 | 0.754 | 0.148 | 0.161 |

Validation (2013–2014, fit-only models): LR AUC 0.848, HGB 0.853 — ranking
transfers across time with almost no loss. Both models are moderately
miscalibrated on the test set (ECE ~0.15, overestimating risk), a cost of the
balanced class weights. Age dominates both models (LR standardised coef 1.36;
HGB permutation importance 0.223 AUC drop), then education, smoking, PIR and
race/ethnicity; diet, CRP and BMI add almost nothing once those are in.

### Severe periodontitis — temporal test 2013–2014 (n=3,621, prev 8.7%)
Full files: `results/metrics_periodontitis.json`,
`results/figures/roc_periodontitis.png`,
`results/figures/calibration_periodontitis.png`.

| Model | AUC | Sens / spec @0.5 | Accuracy | ECE | Brier |
|---|---|---|---|---|---|
| Logistic regression | **0.766** | 0.728 / 0.674 | 0.679 | **0.324** | 0.206 |
| HistGradientBoosting | 0.739 | 0.456 / 0.846 | 0.812 | 0.158 | 0.128 |

The honest failure: the logistic model is **severely miscalibrated**
(ECE 0.324 on test, 0.411 on validation) — balanced weighting against an
8.7% prevalence, compounded by prevalence falling from 13.2% (validation) to
8.7% (test), pushes predicted risks far above observed frequencies. Its
0.5-threshold sensitivity/specificity also swings wildly between validation
(0.914/0.377) and test (0.728/0.674). The boosting model is better calibrated
(ECE 0.158) but at 0.5 it catches only 45.6% of severe cases; at its
validation-Youden threshold (0.173) sensitivity rises to 0.785 at the cost of
specificity 0.550. Neither model is deployment-ready as a probability tool;
as a ranking tool (AUC ~0.74–0.77) both are modest. Top drivers: age, current
smoking, male sex, lower PIR, higher HbA1c.

### Fairness audit (test set, @0.5 threshold)
- **Tooth loss:** ranking is near-equal — AUC 0.838–0.876 (LR) across
  race/ethnicity, 0.833–0.843 across PIR bands, 0.826–0.854 across smoking
  groups. But the fixed 0.5 threshold is not equal: sensitivity is 0.903 for
  PIR <1 vs 0.542 for PIR ≥4 (LR), and 0.665 for NH Asian vs 0.849 for NH
  Black — the same threshold screens the poorest group aggressively and the
  richest group weakly, mostly tracking prevalence (39.2% vs 11.4%).
- **Severe periodontitis:** ranking itself gaps — LR AUC 0.701 NH Black and
  0.700 NH Asian vs 0.763 NH White and 0.830 Other Hispanic; 0.685 for
  PIR <1 vs 0.790 for PIR ≥4. At 0.5, boosting sensitivity collapses in
  low-prevalence strata: NH White 0.272, PIR ≥4 0.147, never-smokers 0.344,
  vs 0.700 Mexican American and 0.569 current smokers. A single threshold
  cannot serve all groups here.

## Run notes (what went wrong, fixed or documented)
- 2017–2018 (`_J`) files are downloaded but excluded from all models: the
  2017–Mar 2020 pre-pandemic file already contains those participants.
- 1,053 edentulous participants carried a "complete" periodontal-exam status
  with no measured sites; they were excluded from the periodontitis sample
  (dentate only), which moved severe prevalence from 10.2% to 11.2%.
- CRP has no file for 2011–2014 (66.7% missing in the periodontitis sample);
  handled with a missing indicator + median imputation, not dropped.
- The 1999–2000 diet file has no total-sugars variable, so sugars were
  excluded from the harmonised diet features rather than imputed for a whole
  cycle.
- SAS special-missing values surface in pandas as ~5.4e-79 denormals and are
  coerced to NaN in `src/harmonise.py`.
- Tooth-count variables are `OHDxxTC` in 2001–2002 and `OHXxxHTC` in the
  2005–2008 screening-exam files, not `OHXxxTC`.

Manuscript draft: `manuscript/draft.md`, targeting *Clinical Oral
Investigations* (Springer hybrid, Q1 dentistry; $0-APC via the Mizzou GWLA
deal is **unverified** — the title could not be confirmed as "Library
Supported" in the Mizzou Open Journal Finder, so verify at acceptance; the
journal also has a subscription route at no author cost). Draft only — never
submitted.

## Limitations (stated in the manuscript)
- Unweighted analyses; prevalences are not nationally representative
  estimates (severe periodontitis 11.2% unweighted vs 7.8% weighted, Eke
  et al. 2018).
- Periodontitis is 2009–2014 only — no full-mouth exam exists before or after,
  so the temporal test is a single cycle (2013–2014) and prevalence shifted
  between validation and test.
- CRP missing for all of 2011–2014; HbA1c and diet have item missingness.
- Cross-sectional prediction, not causation; no dental-visit or
  self-reported oral-health predictors were used by design.
- Calibration is poor for the periodontitis logistic model (ECE 0.324) and
  moderate for tooth loss (ECE ~0.15); no recalibration was applied.
- Single-threshold operating points do not transfer equally across subgroups.
