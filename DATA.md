# DATA.md — NHANES pooled oral health, 1999–2020

Source: CDC/NCHS National Health and Nutrition Examination Survey (NHANES),
public-use files, https://wwwn.cdc.gov/nchs/nhanes/. No login, no IRB (public-use,
de-identified). Raw XPT files live in `data/raw/<cycle>/` (gitignored, never
pushed). This document records every filename, every harmonisation mapping,
and every scope decision that affects the numbers.

## What was downloaded

89 XPT files, ~400 MB, all HTTP 200 (see `results/download_log.json`).
Downloaded 2026-11-07 with `src/download_nhanes.py`.

| Cycle | Year dir | Files (stems) |
|---|---|---|
| 1999–2000 | 1999 | DEMO, OHXDENT, DIQ, SMQ, DRXTOT, BMX, LAB10, LAB11 |
| 2001–2002 | 2001 | DEMO_B, OHXDEN_B, DIQ_B, SMQ_B, DRXTOT_B, BMX_B, L10_B, L11_B |
| 2003–2004 | 2003 | DEMO_C, OHXDEN_C, DIQ_C, SMQ_C, DR1TOT_C, BMX_C, L10_C, L11_C |
| 2005–2006 | 2005 | DEMO_D, OHX_D, DIQ_D, SMQ_D, DR1TOT_D, BMX_D, GHB_D, CRP_D |
| 2007–2008 | 2007 | DEMO_E, OHX_E, DIQ_E, SMQ_E, DR1TOT_E, BMX_E, GHB_E, CRP_E |
| 2009–2010 | 2009 | DEMO_F, OHXDEN_F, OHXPER_F, DIQ_F, SMQ_F, DR1TOT_F, BMX_F, GHB_F, CRP_F |
| 2011–2012 | 2011 | DEMO_G, OHXDEN_G, OHXPER_G, DIQ_G, SMQ_G, DR1TOT_G, BMX_G, GHB_G |
| 2013–2014 | 2013 | DEMO_H, OHXDEN_H, OHXPER_H, DIQ_H, SMQ_H, DR1TOT_H, BMX_H, GHB_H |
| 2015–2016 | 2015 | DEMO_I, OHXDEN_I, DIQ_I, SMQ_I, DR1TOT_I, BMX_I, GHB_I, HSCRP_I |
| 2017–2018 | 2017 | DEMO_J, OHXDEN_J, DIQ_J, SMQ_J, DR1TOT_J, BMX_J, GHB_J, HSCRP_J |
| 2017–Mar 2020 (pre-pandemic) | 2017 | P_DEMO, P_OHXDEN, P_DIQ, P_SMQ, P_DR1TOT, P_BMX, P_GHB, P_HSCRP |

Filenames were verified against CDC's per-cycle datapages before download
(the index is kept outside the repo at `~/workspace/nhanes_index.json`).

## Scope decisions (read before reusing the numbers)

1. **2017–2018 (`_J`) is downloaded but NOT used in any model.** The
   2017–March 2020 pre-pandemic file (`P_*`) combines the 2017–2018 sample
   with the 2019–March 2020 sample (fieldwork stopped March 2020 after 18 of
   30 locations; the combined file carries special weights and is the only
   nationally representative 2017–2020 release). Pooling `_J` and `P_*` would
   double-count the 2017–2018 participants. (SEQN values are not comparable
   across the two releases — 0 overlapping SEQN between DEMO_J and P_DEMO —
   so the overlap cannot be removed by de-duplication; the `_J` files are
   kept only as a record of this check.)
2. **Severe periodontitis uses full-mouth exams only (2009–2014).** The
   full-mouth periodontal examination (FMPE, 6 sites per tooth, all teeth
   except third molars) ran in 2009–2010, 2011–2012 and 2013–2014 only.
   1999–2004 used a partial-mouth protocol (known to underestimate
   periodontitis prevalence by ≥50%; Eke et al.), 2005–2008 had no
   periodontal exam (basic screening exam only), and periodontal health
   status was cycled out from 2015–2016 on (OMB Supporting Statement A,
   Oct 2014: "Periodontal health status will be cycled out"). The
   partial-mouth files (OHXPERIO, OHXPRL/OHXPRU) were therefore not
   downloaded and not used. This is why the periodontitis analysis covers
   2009–2014 rather than 1999–2014.
3. **CRP is absent in 2011–2014.** No CRP file was released for those cycles
   (CRP: 1999–2010 as `LBXCRP` in mg/dL; 2015+ as `LBXHSCRP` in mg/L).
   CRP is harmonised to mg/L (`LBXCRP × 10` for 1999–2010; `LBXHSCRP` as-is
   for 2015+) and is missing for all 2011–2014 participants (66.7% missing
   in the periodontitis sample, 23.9% in the tooth-loss sample). Models carry
   an explicit `crp_mg_l_missing` indicator plus median imputation.
4. **No survey weights.** Analyses are unweighted (prediction, not population
   estimation). Unweighted prevalences therefore run higher than CDC's
   weighted estimates (e.g. severe periodontitis 11.2% unweighted here vs
   7.8% weighted in Eke et al. 2018 for 2009–2014) because NHANES oversamples
   higher-risk groups. Stated as a limitation in the manuscript.

## Outcomes

### Tooth loss — `<20 remaining teeth`
`n_teeth` = count of tooth-count codes 1 (primary tooth present) or 2
(permanent tooth present) over teeth 02–15 and 18–31 (28 teeth; third molars
01, 16, 17, 32 excluded). Code 3 = dental implant, 4 = tooth not present,
5 = root fragment, 9 = could not assess (per the OHXDEN codebooks). Outcome
`tooth_loss = 1` if `n_teeth < 20` (functional-dentition threshold);
`edentulous = 1` if `n_teeth == 0` (secondary descriptor only).
Per-cycle tooth-count variables: `OHXxxTC` (most cycles), `OHDxxTC`
(2001–2002), `OHXxxHTC` (2005–2008 basic screening exam files).

### Severe periodontitis — CDC/AAP surveillance case definition
Eke PI et al. *Update of the case definitions for population-based
surveillance of periodontitis.* J Periodontol. 2012;83(12):1449–1454:
**≥2 interproximal sites with clinical attachment loss (CAL) ≥6 mm, not on
the same tooth, AND ≥1 interproximal site with probing depth (PD) ≥5 mm.**
Implemented on the pre-calculated CAL variables (`OHXxxLA*`) and pocket-depth
variables (`OHXxxPC*`) in `OHXPER_F/G/H`. Interproximal sites per tooth, from
the OHXPER codebook labels: D = distofacial, S = mesiofacial, P =
distolingual, A = mesiolingual. Mid sites M (midfacial) and L (midlingual)
are excluded. Values ≥90 (99 = could not assess) and ≤0 are treated as
missing. A 4-level CDC/AAP category is also derived (none / mild / moderate /
severe): moderate = ≥2 interproximal sites with CAL ≥4 mm (not same tooth) OR
≥2 interproximal sites with PD ≥5 mm (not same tooth); mild = ≥2
interproximal sites with CAL ≥3 mm and ≥2 with PD ≥4 mm (not same tooth) OR
≥1 site with PD ≥5 mm. Sample: dentate adults 30+ with a **complete** FMPE
(`OHDPDSTS == 1`); edentulous participants are excluded (CDC/AAP prevalence
is reported among dentate adults — 1,053 edentulous participants carried a
"complete" exam status with no measured sites and were removed). Spot-check:
SEQN 51645 (2009–2010) meets the definition (CAL 6 mm on tooth 02-ML and
7 mm on tooth 03-DL; PD 7 mm on tooth 02-ML).

## Analytic population

Adults **age ≥30** with a dentition exam (≥1 tooth-count variable
non-missing). Age 30+ matches periodontal-exam eligibility and keeps both
outcomes on one base population.

| Cycle | DEMO n | Age 30+ | With dentition | Tooth-loss prev | Edentulous | Perio complete | Perio dentate | Perio analytic n | Severe prev |
|---|---|---|---|---|---|---|---|---|---|
| 1999–2000 | 9,965 | 4,009 | 3,379 | 33.9% | 12.4% | – | – | – | – |
| 2001–2002 | 11,039 | 4,393 | 3,736 | 30.5% | 11.4% | – | – | – | – |
| 2003–2004 | 10,122 | 4,131 | 3,545 | 36.7% | 13.9% | – | – | – | – |
| 2005–2006 | 10,348 | 3,912 | 3,417 | 29.3% | 10.3% | – | – | – | – |
| 2007–2008 | 10,149 | 5,037 | 4,372 | 32.4% | 11.6% | – | – | – | – |
| 2009–2010 | 10,537 | 5,177 | 4,126 | 27.5% | 8.3% | 4,086 | 3,784 | 3,744 | 11.7% |
| 2011–2012 | 9,756 | 4,566 | 4,050 | 28.8% | 9.2% | 3,685 | 3,677 | 3,335 | 13.2% |
| 2013–2014 | 10,175 | 4,813 | 4,315 | 29.0% | 8.9% | 3,982 | 3,932 | 3,621 | 8.7% |
| 2015–2016 | 9,971 | 4,745 | 4,294 | 26.5% | 8.0% | – | – | – | – |
| 2017–Mar 2020 | 15,560 | 7,854 | 6,933 | 28.2% | 8.4% | – | – | – | – |
| **Pooled** | | | **42,167** | **30.0%** | **10.0%** | | | **10,700** | **11.2%** |

Full per-cycle flow counts: `data/harmonised/harmonisation.json`.

## Harmonisation mappings

| Harmonised variable | Source(s) | Mapping |
|---|---|---|
| `age` | `RIDAGEYR` (all DEMO files) | Numeric; top-coded at 85 (80 in the pre-pandemic file) |
| `sex` | `RIAGENDR` | 1 male, 2 female |
| `race_eth` | `RIDRETH3` (2011+), else `RIDRETH1` | 1 Mexican American; 2 Other Hispanic; 3 NH White; 4 NH Black; 6 NH Asian (2011+ only — earlier cycles fold Asian into Other); 5/7 Other/Multiracial |
| `education` | `DMDEDUC2` (adults) | 1 <9th grade; 2 9–11th grade; 3 HS/GED; 4 some college/AA; 5 college grad+; 7/9 refused/don't know → missing |
| `pir` | `INDFMPIR` | Poverty income ratio, numeric, top-coded at 5.0; 9.9% missing (tooth-loss sample) |
| `smoking` | `SMQ020`, `SMQ040` | never = SMQ020 2 (never 100 cigarettes); former = SMQ020 1 and SMQ040 3 (not at all); current = SMQ020 1 and SMQ040 1/2 (every day / some days) |
| `diabetes` | `DIQ010` | 1 diabetes; 2 no; 3 borderline; 7/9 → missing |
| `hba1c` | `LBXGH` in LAB10 / L10_B / L10_C / GHB_D…J / P_GHB | Glycohemoglobin, % |
| `bmi` | `BMXBMI` | kg/m² |
| `crp_mg_l` | `LBXCRP` (LAB11 / L11_B / L11_C / CRP_D/E/F) ×10; `LBXHSCRP` (HSCRP_I/J, P_HSCRP) as-is | mg/L; absent 2011–2014 (see §3) |
| `kcal`, `protein_g`, `carb_g`, `fiber_g`, `chol_mg`, `sodium_mg` | Day-1 total nutrient intakes: `DRXT*` (DRXTOT, DRXTOT_B) / `DR1T*` (DR1TOT_C…J, P_DR1TOT); sodium `DRDTSODI` (1999, 2001) else `DR1TSODI` | Total sugars excluded: the 1999–2000 file has no total-sugars variable |
| `cycle` | File of origin | e.g. `1999-2000`, `2017-Mar2020` |

Predictors are **non-dental only** — no periodontal, caries or tooth-count
variables are model inputs (tooth count is an outcome, not a predictor).

### Data quirks handled in code
- pandas `read_sas` renders SAS special-missing values as ~5.4e-79 denormal
  floats; any float with |x| < 1e-70 is set to NaN (`src/harmonise.py`).
- Fixed clinical winsorisation caps before modelling (`src/train.py`):
  age 30–85, PIR 0–5, HbA1c 3–15, BMI 12–70, CRP 0–100 mg/L, energy
  0–8,000 kcal, protein 0–400 g, carbohydrate 0–1,000 g, fibre 0–150 g,
  cholesterol 0–2,000 mg, sodium 0–15,000 mg.
- Missingness: median imputation (fit on train) for numerics, most-frequent
  for categoricals, plus explicit missing indicators for HbA1c, CRP and PIR.

## Temporal splits

- **Tooth loss:** fit 1999–2012 (n=26,625; prev 31.2%), validation 2013–2014
  (n=4,315; prev 29.0%), refit 1999–2014, test 2015–2016 + 2017–Mar 2020
  (n=11,227; prev 27.6%).
- **Severe periodontitis:** fit 2009–2010 (n=3,744; prev 11.7%), validation
  2011–2012 (n=3,335; prev 13.2%), refit 2009–2012, test 2013–2014
  (n=3,621; prev 8.7%).

## Outputs

- `data/harmonised/toothloss.csv` (42,167 rows), `data/harmonised/periodontitis.csv`
  (10,700 rows) — person-level, gitignored (derived from raw XPTs).
- `data/harmonised/harmonisation.json` — per-cycle flow counts + file map.
- `results/metrics_toothloss.json`, `results/metrics_periodontitis.json` —
  test metrics, validation metrics, Youden thresholds, fairness strata.
- `results/test_predictions_<outcome>.csv` — anonymous test predictions
  (no SEQN) used by `src/figures.py`.
- `results/figures/roc_*.png`, `results/figures/calibration_*.png`.
- `results/lr_coefficients_<outcome>.json`, `results/hgb_importance_<outcome>.json`.
