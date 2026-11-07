# Predicting severe periodontitis and tooth loss from non-dental data: pooled NHANES 1999–2020 with temporal validation and a fairness audit

**Draft — parked, never submitted.** All numbers below are read back from
`results/metrics_toothloss.json` and `results/metrics_periodontitis.json`
(runs of 2026-11-07). No number is invented, estimated, or carried over from
the literature except where explicitly cited as published comparison values.

## Abstract

**Objective.** To test whether severe periodontitis and tooth loss can be
predicted from non-dental information alone — demographics, socioeconomic
position, smoking, diabetes/HbA1c, BMI, diet and CRP — in US adults, and
whether prediction holds up on later survey cycles and equally across
population groups.

**Methods.** Pooled National Health and Nutrition Examination Survey (NHANES)
1999–2020 public-use data. Analytic samples: 42,167 adults aged ≥30 years
with a dentition exam (tooth loss, defined as <20 remaining teeth) and 10,700
dentate adults aged ≥30 years with a complete full-mouth periodontal exam
(severe periodontitis by the CDC/AAP case definition; full-mouth exams exist
only in 2009–2014). Logistic regression and gradient boosting
(HistGradientBoosting) were trained on earlier cycles and tested once on later
cycles (tooth loss: train 1999–2014, test 2015–2016 + 2017–March 2020;
periodontitis: train 2009–2012, test 2013–2014). Outcomes were evaluated with
AUC, accuracy, sensitivity, specificity and calibration (ECE), and audited by
race/ethnicity, poverty-income-ratio band and smoking status.

**Results.** Tooth loss (test n = 11,227, prevalence 27.6%): gradient boosting
AUC 0.861, sensitivity 0.840, specificity 0.722, ECE 0.148; logistic
regression AUC 0.854, sensitivity 0.818, specificity 0.733, ECE 0.149.
Ranking was near-equal across groups (AUC 0.826–0.876), but sensitivity at a
fixed 0.5 threshold ranged from 0.542 (PIR ≥4) to 0.903 (PIR <1). Severe
periodontitis (test n = 3,621, prevalence 8.7%): logistic regression AUC
0.766, sensitivity 0.728, specificity 0.674, ECE 0.324 (severely
miscalibrated); gradient boosting AUC 0.739, sensitivity 0.456, specificity
0.846, ECE 0.158. Ranking also gapped by group (logistic AUC 0.700–0.701 for
NH Asian and NH Black adults vs 0.763 NH White and 0.830 Other Hispanic), and
boosting sensitivity fell to 0.147–0.272 in the lowest-prevalence strata.

**Conclusions.** Tooth loss can be ranked well years later from non-dental
data, but a single operating threshold does not screen groups equally.
Severe periodontitis is only modestly predictable without a dental exam, and
the interpretable model is too miscalibrated to use as a probability tool.
Both models are screening-rankers at best, not diagnostic substitutes.

## Background

Periodontitis affects 42.2% of US adults aged 30 years and older, with 7.8%
having severe disease (Eke et al., NHANES 2009–2014, weighted estimates), and
tooth loss remains common and socially patterned. Both conditions are usually
detected by a dental examination, which many adults — disproportionately
low-income and minoritised adults — do not receive regularly. A model that
ranks risk from information already present in medical records and surveys
could prioritise people for dental referral, but only if it works on later
data than it was trained on, and only if it does not work systematically
worse for the groups already worst served.

Most published NHANES periodontitis models use random splits, which flatter
performance when survey protocols and prevalence drift over time, and few
report calibration or subgroup performance at all. This study therefore uses
strictly temporal splits, reports calibration alongside discrimination, and
audits fairness on the test set. The question is deliberately narrow:
prediction from non-dental variables only. No periodontal, caries or
tooth-count variable is used as a predictor.

## Methods

### Data source and population
NHANES (CDC/NCHS) public-use files, 1999–2000 through 2017–March 2020
(pre-pandemic combined file), 89 XPT files downloaded 2026-11-07
(`src/download_nhanes.py`; full file list and per-cycle datapage verification
in DATA.md). The analytic population is adults aged ≥30 years with a
dentition exam. Age 30+ matches periodontal-exam eligibility and keeps both
outcomes on one base population. Analyses are unweighted (prediction, not
population estimation).

### Outcomes
**Tooth loss.** Remaining natural teeth were counted from the dentition exam
(tooth-count codes 1 = primary present, 2 = permanent present, over teeth
02–15 and 18–31; third molars excluded; implants and root fragments not
counted). Tooth loss = <20 remaining teeth (functional-dentition threshold).
Edentulous (0 teeth) is reported as a descriptor only. Pooled n = 42,167;
prevalence of tooth loss 30.0%, edentulous 10.0%.

**Severe periodontitis.** CDC/AAP surveillance case definition (Eke et al.,
J Periodontol 2012;83:1449–1454): ≥2 interproximal sites with clinical
attachment loss ≥6 mm, not on the same tooth, AND ≥1 interproximal site with
probing depth ≥5 mm, implemented on the pre-calculated CAL (`OHXxxLA*`) and
pocket-depth (`OHXxxPC*`) variables at the four interproximal sites per tooth
(distofacial, mesiofacial, distolingual, mesiolingual). The 4-level CDC/AAP
category was also derived (none 48.8%, mild 4.7%, moderate 35.3%, severe
11.2%). The full-mouth periodontal examination ran only in 2009–2010,
2011–2012 and 2013–2014 (partial-mouth 1999–2004, no exam 2005–2008,
periodontal status cycled out from 2015–2016), so the periodontitis sample is
2009–2014 by necessity, not choice. Sample: dentate adults 30+ with a
complete exam (`OHDPDSTS == 1`); 1,053 edentulous participants carrying a
"complete" exam status with no measured sites were excluded. Pooled n =
10,700; severe prevalence 11.2% (unweighted; the published weighted figure
for 2009–2014 is 7.8%, the gap reflecting NHANES oversampling of higher-risk
groups in unweighted data).

### Predictors (non-dental only)
Age, sex, race/ethnicity (harmonised RIDRETH3/RIDRETH1: Mexican American,
Other Hispanic, NH White, NH Black, NH Asian from 2011+, Other/Multiracial),
education, poverty income ratio (PIR), smoking (never/former/current from
SMQ020/SMQ040), diabetes status (DIQ010: no/borderline/diabetes), HbA1c,
BMI, day-1 dietary intakes (energy, protein, carbohydrate, fibre,
cholesterol, sodium), and CRP (mg/L; `LBXCRP`×10 for 1999–2010,
`LBXHSCRP` for 2015+; no CRP file exists for 2011–2014). Total sugars were
excluded because the 1999–2000 diet file has no total-sugars variable.
Every mapping is documented in DATA.md and
`data/harmonised/harmonisation.json`. Missingness was handled with median
imputation (numerics) and most-frequent imputation (categoricals), plus
explicit missing indicators for HbA1c, CRP and PIR; continuous variables were
winsorised at fixed clinical caps (e.g. BMI 12–70, HbA1c 3–15, CRP 0–100
mg/L). In the tooth-loss sample, missingness was: PIR 9.9%, CRP 23.9%,
HbA1c 4.0%, BMI 1.7%, diet ~5.1–5.5%; in the periodontitis sample CRP was
66.7% missing (entire 2011–2014 cycles).

### Models and validation
Logistic regression (standardised, class-weight balanced) and
HistGradientBoosting (300 iterations, learning rate 0.05, 31 leaves,
class-weight balanced). Temporal splits: tooth loss — fit 1999–2012
(n = 26,625, prevalence 31.2%), validation 2013–2014 (n = 4,315, prevalence
29.0%), refit 1999–2014, test 2015–2016 + 2017–March 2020 (n = 11,227,
prevalence 27.6%); periodontitis — fit 2009–2010 (n = 3,744, prevalence
11.7%), validation 2011–2012 (n = 3,335, prevalence 13.2%), refit 2009–2012,
test 2013–2014 (n = 3,621, prevalence 8.7%). The validation split was used
only to pick a Youden threshold, reported alongside the primary 0.5
threshold. Metrics: AUC, accuracy, sensitivity, specificity, PPV, NPV,
Brier score and ECE (10 equal-width bins). Fairness audit: AUC, sensitivity,
specificity and ECE on the test set, stratified by race/ethnicity, PIR band
(<1, 1–<2, 2–<4, ≥4) and smoking status. Code: `src/train.py`,
`src/figures.py` (Python 3.12, scikit-learn 1.9.1, CPU only).

## Results

### Cohort flow
Per-cycle tooth-loss samples ranged from 3,379 (1999–2000) to 6,933
(2017–March 2020); tooth-loss prevalence fell from 33.9% (1999–2000) and
36.7% (2003–2004) to 26.5% (2015–2016) and 28.2% (2017–March 2020), and
edentulous prevalence from 12.4% to 8.4% over the same span. Mean age in the
pooled tooth-loss sample was 54.9 years (SD 15.4). Composition: NH White
19,082, NH Black 9,065, Mexican American 6,660, Other Hispanic 3,505,
NH Asian 2,310, Other/Multiracial 1,545; never-smokers 22,140, former
11,663, current 8,329; diabetes 6,125, borderline 1,013, no diabetes 35,002.
Median CRP 2.20 mg/L (IQR 0.90–5.00), mean HbA1c 5.82% (SD 1.13), mean BMI
29.3 kg/m² (SD 6.7). Severe periodontitis prevalence by cycle was 11.7%
(2009–2010), 13.2% (2011–2012) and 8.7% (2013–2014) — the test cycle is the
lowest-prevalence cycle, which matters for calibration (below).

### Tooth loss — temporal test (n = 11,227)
| Model | AUC | Accuracy | Sens / spec @0.5 | PPV / NPV | Brier | ECE |
|---|---|---|---|---|---|---|
| Logistic regression | 0.854 | 0.757 | 0.818 / 0.733 | 0.539 / 0.914 | 0.165 | 0.149 |
| HistGradientBoosting | 0.861 | 0.754 | 0.840 / 0.722 | 0.535 / 0.922 | 0.161 | 0.148 |

Validation (2013–2014) AUCs were 0.848 (logistic) and 0.853 (boosting), so
ranking transferred across time with almost no loss. At the
validation-Youden threshold (logistic 0.435), test sensitivity rose to 0.864
with specificity 0.679; boosting's Youden threshold (0.497) was effectively
0.5 (sensitivity 0.841, specificity 0.719). Both models are moderately
miscalibrated on the test set (ECE ~0.15), overestimating risk — a cost of
the balanced class weights. Age dominates both models (logistic standardised
coefficient 1.36; boosting permutation importance 0.223 AUC drop), followed
by education (college graduate −0.36; <9th grade +0.22), PIR (−0.37),
smoking (current +0.29, never −0.25) and race/ethnicity (NH Black +0.21,
Mexican American −0.24). Diet (carbohydrate +0.33, fibre −0.25), CRP and BMI
contribute little once those are in (boosting importance: fibre 0.006,
carbohydrate 0.005, CRP 0.002, BMI 0.001).

### Severe periodontitis — temporal test (n = 3,621)
| Model | AUC | Accuracy | Sens / spec @0.5 | PPV / NPV | Brier | ECE |
|---|---|---|---|---|---|---|
| Logistic regression | 0.766 | 0.679 | 0.728 / 0.674 | 0.176 / 0.963 | 0.206 | 0.324 |
| HistGradientBoosting | 0.739 | 0.812 | 0.456 / 0.846 | 0.221 / 0.942 | 0.128 | 0.158 |

Discrimination is modest (AUC 0.74–0.77; validation AUCs 0.749 logistic,
0.734 boosting). The logistic model is severely miscalibrated: ECE 0.324 on
test and 0.411 on validation — balanced weighting against an 8.7%
prevalence, compounded by prevalence falling from 13.2% (validation) to
8.7% (test), pushes predicted risks far above observed frequencies. Its
operating point is also unstable: at 0.5, sensitivity/specificity were
0.914/0.377 on validation but 0.728/0.674 on test. At its validation-Youden
threshold (0.691), test sensitivity falls to 0.440 with specificity 0.868.
Boosting is better calibrated (ECE 0.158) but at 0.5 catches only 45.6% of
severe cases; at its Youden threshold (0.173) sensitivity rises to 0.785 at
the cost of specificity 0.550. Top drivers: age (logistic coefficient 0.54;
boosting importance 0.084), current smoking (+0.28), male sex (female −0.27),
lower PIR (−0.24), higher HbA1c (+0.23), NH White (−0.22), college education
(−0.22). Notably, the diabetes indicator itself carries almost no coefficient
(−0.02) once HbA1c is in the model.

### Fairness audit (test set, 0.5 threshold)
**Tooth loss.** Ranking is near-equal: logistic AUC 0.838–0.876 across
race/ethnicity, 0.833–0.843 across PIR bands, 0.826–0.854 across smoking
groups (boosting: 0.841–0.885, 0.841–0.849, 0.839–0.857). The fixed threshold
is not equal: logistic sensitivity is 0.903 for PIR <1 vs 0.542 for PIR ≥4,
and 0.665 for NH Asian vs 0.849 for NH Black adults; never-smokers 0.724 vs
current smokers 0.880. The gradient tracks prevalence (tooth loss 39.2% at
PIR <1 vs 11.4% at PIR ≥4; 14.4% NH Asian vs 35.6% NH Black) more than
ranking ability.

**Severe periodontitis.** Here ranking itself gaps. Logistic AUC: NH Black
0.701 and NH Asian 0.700 vs NH White 0.763, Mexican American 0.772 and Other
Hispanic 0.830; PIR <1 0.685 vs PIR ≥4 0.790; current smokers 0.719 vs never
0.765 (boosting shows the same pattern: NH Black 0.685, PIR <1 0.671,
PIR ≥4 0.752). At 0.5, boosting sensitivity collapses in low-prevalence
strata: NH White 0.272, PIR ≥4 0.147, never-smokers 0.344, against 0.700
Mexican American and 0.569 current smokers; logistic sensitivity in the same
strata is 0.565, 0.441 and 0.582. A single threshold cannot serve all groups
for this outcome.

## Discussion

Three findings stand. First, tooth loss is predictable years later from
non-dental data alone (test AUC 0.85–0.86), driven overwhelmingly by age and
socioeconomic position — which is also why it is predictable: tooth loss is
the accumulated record of a lifetime of access, smoking and disease. Second,
severe periodontitis is only modestly predictable (AUC 0.74–0.77) and the
interpretable model fails as a probability tool (ECE 0.324). The failure is
instructive rather than incidental: it is what balanced class weights plus a
prevalence shift between validation (13.2%) and test (8.7%) does to
calibration, and it is visible only because calibration was reported. Any
deployment claim built on the logistic model's AUC alone would be wrong.
Third, fairness failures here are operating-point failures more than ranking
failures for tooth loss, but genuine ranking failures for periodontitis in NH
Black and NH Asian adults and in the poorest group — the groups with the
highest prevalence (NH Black 14.9%, PIR <1 14.2% vs NH White 5.9%,
PIR ≥4 3.4% in the test set) get the worst ranking. That is the opposite of
what a screening tool should do, and it argues against deploying either model
without group-specific thresholds and recalibration — or, more honestly,
against deploying the periodontitis model at all in its current form.

Comparison with the literature: Eke et al.'s self-report-based periodontitis
scores reach similar discrimination with far fewer inputs, which suggests
that our extra laboratory and dietary variables add little beyond age,
smoking, sex, PIR and HbA1c — consistent with the permutation importances,
where diet, CRP and BMI contribute almost nothing. The contribution here is
not a better AUC but the temporal test, the calibration accounting, and the
audit.

## Limitations
- Unweighted analyses; prevalences are not nationally representative
  estimates (severe periodontitis 11.2% unweighted vs 7.8% weighted).
- Periodontitis covers 2009–2014 only; the temporal test is a single cycle
  whose prevalence (8.7%) is the lowest of the three, which penalises
  calibration.
- CRP is missing for all of 2011–2014 (66.7% missing in the periodontitis
  sample); HbA1c and diet have item missingness; median imputation plus a
  missing indicator is a crude fix.
- Cross-sectional prediction, not causation; no dental-visit or self-reported
  oral-health predictors were used by design, which caps achievable
  discrimination for periodontitis.
- No recalibration (e.g. Platt/isotonic on the validation split) was applied;
  the reported ECEs are the unrecalibrated values.
- Single-threshold operating points do not transfer equally across subgroups;
  no group-specific thresholds were fitted (that would need a pre-registered
  fairness criterion, not a post-hoc tweak).
- The 2017–March 2020 pre-pandemic file combines two cycles with special
  weights; treating it as the test cycle is a pragmatic choice, documented
  in DATA.md, and its 2017–2018 participants cannot be separated from the
  2019–March 2020 participants.

## Target journal
*Clinical Oral Investigations* (Springer, hybrid, Q1 dentistry, SJR ~1.0;
covers periodontology, epidemiology and preventive dentistry, matching both
outcomes). **$0-APC status: UNVERIFIED.** The journal is confirmed hybrid
(list price APC ~$3,299 / €3,190), which makes it in principle eligible for
Mizzou's GWLA Springer hybrid deal, but the title could not be confirmed as
"Library Supported" in the Mizzou Open Journal Finder
(https://mizzoulibraries.openjournalfinder.com/) — the finder is
JavaScript-rendered and the title's entry could not be verified there on
2026-11-07. Verify the "Library Supported" flag at acceptance; note the
journal also publishes subscription (non-OA) articles at no author cost, so
$0 publication does not depend on the deal. Fully-OA BMC titles (e.g. BMC
Oral Health) are NOT covered by the GWLA deal and were not chosen. **Draft
only — never submitted.**

## References
1. Eke PI, Page RC, Wei L, Thornton-Evans G, Genco RJ. Update of the case
   definitions for population-based surveillance of periodontitis.
   J Periodontol. 2012;83(12):1449–1454. doi:10.1902/jop.2012.110664
2. Eke PI, Dye BA, Wei L, et al. Update on prevalence of periodontitis in
   adults in the United States: NHANES 2009 to 2012. J Periodontol.
   2015;86(5):611–622. doi:10.1902/jop.2015.140520
3. Eke PI, Thornton-Evans GO, Wei L, Borgnakke WS, Dye BA, Genco RJ.
   Periodontitis in US adults: NHANES 2009–2014. J Am Dent Assoc.
   2018;149(7):576–588.e6. doi:10.1016/j.adaj.2018.04.023
4. Dye BA, Thornton-Evans G, Li X, Iafolla TJ. Dental caries and tooth loss
   in adults in the United States, 2011–2012. NCHS Data Brief. 2015;(197).
5. Centers for Disease Control and Prevention, National Center for Health
   Statistics. National Health and Nutrition Examination Survey data,
   1999–2020. https://wwwn.cdc.gov/nchs/nhanes/
6. Centers for Disease Control and Prevention, National Center for Health
   Statistics. NHANES 2017–March 2020 pre-pandemic data: analytic guidance
   and brief overview. https://wwwn.cdc.gov/nchs/nhanes/

## Data and code availability
NHANES public-use data: CDC/NCHS (see DATA.md for the exact file list).
Analysis code and results: this repository (`src/`, `results/`). Raw XPT
files are gitignored and are re-downloadable with `src/download_nhanes.py`.
No individual-level predictions are shared (test predictions in `results/`
contain no SEQN or identifiers).
