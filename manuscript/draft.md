# Predicting severe periodontitis and tooth loss from non-dental data: pooled NHANES 1999–2020 with temporal validation and a fairness audit

**Draft, parked, never submitted.** All numbers below are read back from
`results/metrics_toothloss.json` and `results/metrics_periodontitis.json`
(runs of 2026-11-07). No number is invented, estimated, or carried over from
the literature except where explicitly cited as published comparison values.

## Abstract

**Objectives.** To test whether severe periodontitis and tooth loss can be predicted from non-dental information alone in US adults, and whether it holds on later cycles and equally across groups.

**Materials and methods.** NHANES 1999–2020 data: 42,167 adults aged 30 or older with a dentition exam (tooth loss, <20 remaining teeth) and 10,700 dentate adults with a full-mouth periodontal exam (severe periodontitis, CDC/AAP definition, 2009–2014 only). Logistic regression and gradient boosting were trained on earlier cycles, tested on later cycles, and audited by race/ethnicity, poverty-income-ratio (PIR) band and smoking status; evaluation used AUC, sensitivity, specificity and calibration (ECE).

**Results.** Tooth loss (test n=11,227, prevalence 27.6%): boosting AUC 0.861 (95% CI 0.854–0.868), logistic regression 0.854 (0.847–0.861). Ranking differed little across groups (logistic AUC 0.826–0.876; boosting 0.839–0.885), but sensitivity at 0.5 ranged from 0.542 (PIR ≥4) to 0.903 (PIR <1). Severe periodontitis (test n=3,621, prevalence 8.7%): logistic regression AUC 0.766 (0.740–0.791), ECE 0.324; boosting AUC 0.739 (0.712–0.766), ECE 0.158. Ranking differed by group (logistic AUC 0.700–0.701 for NH Asian and NH Black adults vs 0.763 NH White); boosting sensitivity fell to 0.147–0.344 in low-prevalence strata.

**Conclusions.** Tooth loss ranks well years later from non-dental data, but one threshold does not screen groups equally. Severe periodontitis is only modestly predictable, and the interpretable model is unusable as a probability tool. Both models rank risk; neither replaces a dental examination.

**Clinical relevance.** Risk ranking from data already in medical records could prioritise dental referral, but only after recalibration, with group-specific thresholds.

**Keywords:** NHANES; periodontitis; tooth loss; prediction model; health equity; calibration.

## Introduction

Periodontitis affects 42.2% of US adults aged 30 years and older, with 7.8% having severe disease (NHANES 2009–2014, weighted estimates) [1], and tooth loss remains common [2] and socially patterned [3]. Both conditions are usually detected by a dental examination, which many adults, disproportionately low-income and minoritised adults, do not receive regularly [4]. A model that ranks risk from information already in medical records and surveys could prioritise people for dental referral. That holds only if it still works on later data, and only if it does not work worst for the groups already worst served.

Random splits can flatter performance when survey protocols and prevalence drift over time, so temporal validation is the honest test [5]. This study therefore uses strictly temporal splits, reports calibration alongside discrimination, and audits fairness on the test set. The question is deliberately narrow:
prediction from non-dental variables only. No periodontal, caries or
tooth-count variable is used as a predictor.

## Methods

### Data source and population
NHANES (CDC/NCHS) [6] public-use files, 1999–2000 through 2017–March 2020
(pre-pandemic combined file), 89 XPT files downloaded 2026-11-07
(`src/download_nhanes.py`; full file list and per-cycle datapage verification
in DATA.md). The analytic population is adults aged ≥30 years with a
dentition exam. Age 30+ matches periodontal-exam eligibility and keeps both
outcomes on one base population. Analyses are unweighted (prediction, not population estimation) [7].

### Outcomes
**Tooth loss.** Remaining natural teeth were counted from the dentition exam
(tooth-count codes 1 = primary present, 2 = permanent present, over teeth
02–15 and 18–31; third molars excluded; implants and root fragments not
counted). Tooth loss = <20 remaining teeth (functional-dentition threshold) [8].
Edentulous participants (0 teeth) are included in the <20-teeth outcome; edentulism is reported as a descriptor only and was not modelled as a separate outcome. Pooled n = 42,167;
prevalence of tooth loss 30.0%, edentulous 10.0%.

**Severe periodontitis.** CDC/AAP surveillance case definition [9]: ≥2 interproximal sites with clinical
attachment loss ≥6 mm, not on the same tooth, AND ≥1 interproximal site with
probing depth ≥5 mm, implemented on the pre-calculated CAL (`OHXxxLA*`) and
pocket-depth (`OHXxxPC*`) variables at the four interproximal sites per tooth
(distofacial, mesiofacial, distolingual, mesiolingual). The 4-level CDC/AAP
category was also derived (none 48.8%, mild 4.7%, moderate 35.3%, severe
11.2%). The full-mouth periodontal examination ran only in 2009–2010,
2011–2012 and 2013–2014 (partial-mouth 1999–2004, no exam 2005–2008,
periodontal status cycled out from 2015–2016), so the periodontitis sample is 2009–2014 by necessity, not choice [1]. Sample: dentate adults 30+ with a
complete exam (`OHDPDSTS == 1`); 1,053 edentulous participants carrying a
"complete" exam status with no measured sites were excluded. Pooled n =
10,700; severe prevalence 11.2% (unweighted; the published weighted figure for 2009–2014 is 7.8% [1], the gap reflecting NHANES oversampling of higher-risk
groups in unweighted data).

### Predictors (non-dental only)
Age, sex, race/ethnicity (harmonised RIDRETH3/RIDRETH1: Mexican American,
Other Hispanic, NH White, NH Black, NH Asian from 2011+, Other/Multiracial),
education, poverty income ratio (PIR), smoking (never/former/current from
SMQ020/SMQ040), diabetes status (DIQ010: no/borderline/diabetes), HbA1c,
BMI, day-1 dietary intakes (energy, protein, carbohydrate, fibre,
cholesterol, sodium), and CRP (mg/L; `LBXCRP`×10 for 1999–2010,
`LBXHSCRP` for 2015+; no CRP file exists for 2011–2014) [10]. Total sugars were
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
Logistic regression (standardised, class-weight balanced) and HistGradientBoosting [11,12] (300 iterations, learning rate 0.05, 31 leaves,
class-weight balanced). Temporal splits: tooth loss, fit 1999–2012
(n = 26,625, prevalence 31.2%), validation 2013–2014 (n = 4,315, prevalence
29.0%), refit 1999–2014, test 2015–2016 + 2017–March 2020 (n = 11,227,
prevalence 27.6%); periodontitis, fit 2009–2010 (n = 3,744, prevalence
11.7%), validation 2011–2012 (n = 3,335, prevalence 13.2%), refit 2009–2012,
test 2013–2014 (n = 3,621, prevalence 8.7%). The validation split was used only to pick a Youden threshold [13], reported alongside the primary 0.5 threshold. Metrics: AUC [14], accuracy, sensitivity, specificity, PPV, NPV, Brier score [15] and ECE [16] (10 equal-width bins). Fairness audit: AUC, sensitivity, specificity and ECE on the test set, stratified by race/ethnicity, PIR band (<1, 1–<2, 2–<4, ≥4) and smoking status [17]. One-hot encoding retained all levels (no reference level dropped), so each coefficient is a level indicator rather than a contrast against a reference category. Permutation importance was computed on the test set with 5 repeats (ROC AUC scoring). There are 33 features after one-hot encoding. Code: `src/train.py`,
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
11,663, current 8,329; diabetes 6,125, borderline 1,013, no diabetes 35,002 (35 participants missing smoking status; 27 missing diabetes status).
Median CRP 2.20 mg/L (IQR 0.90–5.00), mean HbA1c 5.82% (SD 1.13), mean BMI
29.3 kg/m² (SD 6.7). Severe periodontitis prevalence by cycle was 11.7% (2009–2010), 13.2% (2011–2012) and 8.7% (2013–2014). The test cycle is the lowest-prevalence cycle, which matters for calibration (below).

### Tooth loss, temporal test (n = 11,227)

**Table 1.** Tooth loss, temporal test (n=11,227, prevalence 27.6%). AUC with 95% percentile-bootstrap confidence interval (2,000 resamples); sensitivity/specificity at 0.5.

| Model | AUC (95% CI) | Accuracy | Sens / spec @0.5 | PPV / NPV | Brier | ECE |
|---|---|---|---|---|---|---|
| Logistic regression | 0.854 (0.847-0.861) | 0.757 | 0.818 / 0.733 | 0.539 / 0.914 | 0.165 | 0.149 |
| HistGradientBoosting | 0.861 (0.854-0.868) | 0.754 | 0.840 / 0.722 | 0.535 / 0.922 | 0.161 | 0.148 |

Validation (2013–2014) AUCs were 0.848 (logistic) and 0.853 (boosting) (Table 1, Figure 1), so ranking transferred across time with almost no loss. At the
validation-Youden threshold (logistic 0.435), test sensitivity rose to 0.864
with specificity 0.679; boosting's Youden threshold (0.497) was effectively
0.5 (sensitivity 0.841, specificity 0.719). Both models are moderately miscalibrated on the test set (ECE ~0.15), overestimating risk (Figure 2), consistent with the balanced class weights. No unweighted control run was fitted, so this mechanism is inferred, not tested. Age dominates both models (logistic standardised coefficient 1.36; boosting permutation importance [18] 0.223 AUC drop), followed
by education (college graduate −0.36; <9th grade +0.22), PIR (−0.37),
smoking (current +0.29, never −0.25) and race/ethnicity (NH Black +0.21,
Mexican American −0.24). In the logistic model, diet carries some of the largest coefficients (carbohydrate +0.33, fibre −0.25). In the boosting model the same variables contribute almost nothing (permutation importance: fibre 0.006, carbohydrate 0.005, CRP 0.002, BMI 0.001), so the two models disagree about diet, CRP, and BMI.

**Figure 1.** ROC curves, tooth loss, temporal test (n=11,227, prevalence 27.6%). Logistic regression AUC 0.854 (95% CI 0.847–0.861); gradient boosting AUC 0.861 (0.854–0.868).

**Figure 2.** Calibration curves, tooth loss, temporal test (n=11,227, prevalence 27.6%). Both models overestimate risk (ECE 0.149 logistic, 0.148 boosting).

### Severe periodontitis, temporal test (n = 3,621)

**Table 2.** Severe periodontitis, temporal test (n=3,621, prevalence 8.7%). AUC with 95% percentile-bootstrap confidence interval (2,000 resamples); sensitivity/specificity at 0.5.

| Model | AUC (95% CI) | Accuracy | Sens / spec @0.5 | PPV / NPV | Brier | ECE |
|---|---|---|---|---|---|---|
| Logistic regression | 0.766 (0.740-0.791) | 0.679 | 0.728 / 0.674 | 0.176 / 0.963 | 0.206 | 0.324 |
| HistGradientBoosting | 0.739 (0.712-0.766) | 0.812 | 0.456 / 0.846 | 0.221 / 0.942 | 0.128 | 0.158 |

Discrimination is modest (AUC 0.74–0.77; validation AUCs 0.749 logistic, 0.734 boosting) (Table 2, Figure 3). The logistic model is severely miscalibrated (Figure 4): ECE 0.324 on test and 0.411 on validation. Balanced weighting against an 8.7% prevalence, compounded by prevalence falling from 13.2% (validation) to 8.7% (test), is consistent with predicted risks running far above observed frequencies. No unweighted control run was fitted, so this mechanism is inferred, not tested. Its
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

**Figure 3.** ROC curves, severe periodontitis, temporal test (n=3,621, prevalence 8.7%). Logistic regression AUC 0.766 (95% CI 0.740–0.791); gradient boosting AUC 0.739 (0.712–0.766).

**Figure 4.** Calibration curves, severe periodontitis, temporal test (n=3,621, prevalence 8.7%). The logistic model severely overestimates risk (ECE 0.324); gradient boosting is better calibrated (ECE 0.158).

### Fairness audit (test set, 0.5 threshold)
**Tooth loss.** Ranking is near-equal: logistic AUC 0.838–0.876 across
race/ethnicity, 0.833–0.843 across PIR bands, 0.826–0.854 across smoking
groups (boosting: 0.841–0.885, 0.841–0.849, 0.839–0.857). The fixed threshold
is not equal: logistic sensitivity is 0.903 for PIR <1 vs 0.542 for PIR ≥4,
and 0.665 for NH Asian vs 0.849 for NH Black adults; never-smokers 0.724 vs
current smokers 0.880. The gradient tracks prevalence (tooth loss 39.2% at
PIR <1 vs 11.4% at PIR ≥4; 14.4% NH Asian vs 35.6% NH Black) more than
ranking ability.

**Severe periodontitis.** Here the ranking itself differs by group. Logistic AUC: NH Black
0.701 and NH Asian 0.700 vs NH White 0.763, Mexican American 0.772 and Other
Hispanic 0.830; PIR <1 0.685 vs PIR ≥4 0.790; current smokers 0.719 vs never
0.765 (boosting shows the same pattern: NH Black 0.685, PIR <1 0.671,
PIR ≥4 0.752). At 0.5, boosting sensitivity collapses in low-prevalence
strata: NH White 0.272, PIR ≥4 0.147, never-smokers 0.344, against 0.700
Mexican American and 0.569 current smokers; logistic sensitivity in the same
strata is 0.565, 0.441 and 0.582. A single threshold cannot serve all groups
for this outcome.

## Discussion

Three findings stand out. First, tooth loss is predictable years later from
non-dental data alone (test AUC 0.85–0.86), driven overwhelmingly by age and
socioeconomic position, which is also why it is predictable: tooth loss is
the accumulated record of a lifetime of access, smoking and disease. Second,
severe periodontitis is only modestly predictable (AUC 0.74–0.77) and the
interpretable model fails as a probability tool (ECE 0.324). The failure is consistent with balanced class weights against an 8.7% prevalence, compounded by prevalence falling from 13.2% in validation to 8.7% in test. No unweighted control run was fitted, so this mechanism is inferred, not tested. It shows only because calibration was reported. Any deployment claim built on the logistic model's AUC alone would be wrong [19].
Third, the fairness failures differ by outcome. For tooth loss they are operating-point failures more than ranking failures, but for periodontitis the ranking itself is worst in NH Black and NH Asian adults and in the poorest group, the groups with the highest prevalence (NH Black 14.9% and PIR <1 14.2% in the test set, against NH White 5.9% and PIR ≥4 3.4%). That is the opposite of
what a screening tool should do, and it argues against deploying either model without group-specific thresholds and recalibration [20], or, more honestly,
against deploying the periodontitis model at all in its current form.

Comparison with the literature: Eke et al.'s self-report model (demographics plus five questions) reached AUROCC 0.81 for periodontitis of mild or greater severity [21]. That is a broader outcome than our severe-periodontitis target, so the numbers are not directly comparable, but the comparison suggests our extra laboratory and dietary variables add little beyond age, smoking, sex, PIR and HbA1c, which suggests that our extra laboratory and dietary variables add little beyond age, smoking, sex, PIR and HbA1c, consistent with the permutation importances, where diet, CRP and BMI contribute almost nothing. What this paper adds is the temporal test, the calibration accounting, and the audit. The AUCs themselves are not better than published self-report models.

## Conclusion
Tooth loss ranks well years later from non-dental data, but a single threshold does not transfer across groups. Severe periodontitis is only modestly predictable, and the logistic model is unusable as a probability tool. Neither model is deployable without recalibration and group-specific thresholds.

## Limitations
- Unweighted analyses; prevalences are not nationally representative estimates (severe periodontitis 11.2% unweighted vs 7.8% weighted) [7].
- Periodontitis covers 2009–2014 only; the temporal test is a single cycle
  whose prevalence (8.7%) is the lowest of the three, which penalises
  calibration.
- CRP is missing for all of 2011–2014 (66.7% missing in the periodontitis
  sample); HbA1c and diet have item missingness; median imputation plus a
  missing indicator is a crude fix.
- Cross-sectional prediction, not causation; no dental-visit or self-reported
  oral-health predictors were used by design, which caps achievable
  discrimination for periodontitis.
- No recalibration (e.g. Platt/isotonic on the validation split) was applied; the reported ECEs are the unrecalibrated values [20].
- Single-threshold operating points do not transfer equally across subgroups;
- Generalisation beyond NHANES is untested; the temporal test is still within one survey.
- Self-reported predictors (smoking, diabetes status) carry reporting bias.
  no group-specific thresholds were fitted (that would need a pre-registered
  fairness criterion, not a post-hoc tweak).
- The 2017–March 2020 pre-pandemic file combines two cycles with special
  weights; treating it as the test cycle is a pragmatic choice, documented
  in DATA.md, and its 2017–2018 participants cannot be separated from the 2019–March 2020 participants [22].

## Target journal
*Clinical Oral Investigations* (Springer, hybrid, Q1 dentistry, SJR ~1.0;
covers periodontology, epidemiology and preventive dentistry, matching both
outcomes). **$0-APC status: UNVERIFIED.** The journal is confirmed hybrid
(list price APC ~$3,299 / €3,190), which makes it in principle eligible for
Mizzou's GWLA Springer hybrid deal, but the title could not be confirmed as
"Library Supported" in the Mizzou Open Journal Finder
(https://mizzoulibraries.openjournalfinder.com/), the finder is
JavaScript-rendered and the title's entry could not be verified there on
2026-11-07. Verify the "Library Supported" flag at acceptance; note the
journal also publishes subscription (non-OA) articles at no author cost, so
$0 publication does not depend on the deal. Fully-OA BMC titles (e.g. BMC
Oral Health) are NOT covered by the GWLA deal and were not chosen. **Draft
only, never submitted.**

## Declarations

**Funding.** None.

**Competing interests.** The author declares no competing interests.

**Ethics approval.** This study used de-identified public-use NHANES data; no ethics approval was required.

**Consent to participate.** Not applicable (de-identified public-use data).

**Data and code availability.** NHANES public-use data: CDC/NCHS (see DATA.md for the exact file list). Analysis code and results: this repository (`src/`, `results/`). Raw XPT files are gitignored and are re-downloadable with `src/download_nhanes.py`. No individual-level predictions are shared (test predictions in `results/` contain no SEQN or identifiers).

**Authors' contributions.** Jeffrey Appiagyei is the sole author of this draft; the byline is to be confirmed before submission.

**Acknowledgments.** The author thanks the National Center for Health Statistics for making the NHANES public-use data available.

## References
1. Eke PI, Thornton-Evans GO, Wei L, Borgnakke WS, Dye BA, Genco RJ. Periodontitis in US adults: NHANES 2009-2014. J Am Dent Assoc. 2018;149(7):576-588.e6. doi:10.1016/j.adaj.2018.04.023
2. Dye BA, Thornton-Evans G, Li X, Iafolla TJ. Dental caries and tooth loss in adults in the United States, 2011-2012. NCHS Data Brief. 2015;(197). Hyattsville, MD: National Center for Health Statistics.
3. Dye BA, Li X, Thornton-Evans G. Oral health disparities as determined by selected Healthy People 2020 oral health objectives for the United States, 2009-2010. NCHS Data Brief. 2012;(104). Hyattsville, MD: National Center for Health Statistics.
4. Vujicic M, Buchmueller T, Klein R. Dental care presents the highest level of financial barriers, compared with other types of health care services. Health Aff. 2016;35(12):2176-2182. doi:10.1377/hlthaff.2016.0800
5. Steyerberg EW, Harrell FE Jr. Prediction models need appropriate internal, internal-external, and external validation. J Clin Epidemiol. 2016;69:245-247. doi:10.1016/j.jclinepi.2015.04.005
6. Centers for Disease Control and Prevention, National Center for Health Statistics. National Health and Nutrition Examination Survey data, 1999-2020. https://wwwn.cdc.gov/nchs/nhanes/
7. Johnson CL, Paulose-Ram R, Ogden CL, et al. National Health and Nutrition Examination Survey: analytic guidelines, 1999-2010. Vital Health Stat 2. 2013;(161). Hyattsville, MD: National Center for Health Statistics.
8. Petersen PE, Yamamoto T. Improving the oral health of older people: the approach of the WHO Global Oral Health Programme. Community Dent Oral Epidemiol. 2005;33(2):81-92. doi:10.1111/j.1600-0528.2004.00219.x
9. Eke PI, Page RC, Wei L, Thornton-Evans G, Genco RJ. Update of the case definitions for population-based surveillance of periodontitis. J Periodontol. 2012;83(12):1449-1454. doi:10.1902/jop.2012.110664
10. Genco RJ, Borgnakke WS. Risk factors for periodontal disease. Periodontol 2000. 2013;62(1):59-94. doi:10.1111/j.1600-0757.2012.00457.x
11. Friedman JH. Greedy function approximation: a gradient boosting machine. Ann Stat. 2001;29(5):1189-1232. doi:10.1214/aos/1013203451
12. Pedregosa F, Varoquaux G, Gramfort A, Michel V, Thirion B, Grisel O, et al. Scikit-learn: machine learning in Python. J Mach Learn Res. 2011;12:2825-2830. doi:10.5555/1953048.2078195
13. Youden WJ. Index for rating diagnostic tests. Cancer. 1950;3(1):32-35. doi:10.1002/1097-0142(1950)3:1<32::AID-CNCR2820030106>3.0.CO;2-3
14. Hanley JA, McNeil BJ. The meaning and use of the area under a receiver operating characteristic (ROC) curve. Radiology. 1982;143(1):29-36. doi:10.1148/radiology.143.1.7063747
15. Brier GW. Verification of forecasts expressed in terms of probability. Mon Weather Rev. 1950;78(1):1-3. doi:10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2
16. Guo C, Pleiss G, Sun Y, Weinberger KQ. On calibration of modern neural networks. In: Proceedings of the 34th International Conference on Machine Learning. Proceedings of Machine Learning Research. 2017;70:1321-1330. arXiv:1706.04599.
17. Obermeyer Z, Powers B, Vogeli C, Mullainathan S. Dissecting racial bias in an algorithm used to manage the health of populations. Science. 2019;366(6464):447-453. doi:10.1126/science.aax2342
18. Breiman L. Random forests. Mach Learn. 2001;45:5-32. doi:10.1023/A:1010933404324
19. Van Calster B, McLernon DJ, van Smeden M, Wynants L, Steyerberg EW. Calibration: the Achilles heel of predictive analytics. BMC Med. 2019;17:230. doi:10.1186/s12916-019-1466-7
20. Platt JC. Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. In: Smola AJ, Bartlett P, Scholkopf B, Schuurmans D, editors. Advances in large margin classifiers. Cambridge, MA: MIT Press; 1999:61-74.
21. Eke PI, Dye BA, Wei L, Slade GD, Thornton-Evans GO, Beck JD, et al. Self-reported measures for surveillance of periodontitis. J Dent Res. 2013;92(11):1041-1047. doi:10.1177/0022034513505621
22. Centers for Disease Control and Prevention, National Center for Health Statistics. NHANES 2017-March 2020 pre-pandemic data: analytic guidance and brief overview. https://wwwn.cdc.gov/nchs/nhanes/

