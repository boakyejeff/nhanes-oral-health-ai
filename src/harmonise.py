#!/usr/bin/env python3
"""Harmonise NHANES 1999-2020 (1999-2000 .. 2017-Mar 2020) into two analytic files.

Outputs (gitignored data/, see DATA.md):
  data/harmonised/toothloss.csv      one row per adult 30+ with a dentition exam
  data/harmonised/periodontitis.csv  one row per adult 30+ with a COMPLETE full-mouth
                                     periodontal exam (2009-2010, 2011-2012, 2013-2014 only)
  data/harmonised/harmonisation.json variable mappings + per-cycle flow counts

Outcomes
  * tooth_loss: <20 remaining natural teeth (functional-dentition threshold),
    counting tooth-count codes 1 (primary present) and 2 (permanent present)
    over teeth 02-15 and 18-31 (28 teeth; third molars excluded).
    edentulous = 0 remaining teeth (secondary descriptor, not the outcome).
  * severe_periodontitis: CDC/AAP surveillance case definition (Eke et al.,
    J Periodontol 2012;83:1449-1454): >=2 interproximal sites with clinical
    attachment loss (CAL) >=6 mm, not on the same tooth, AND >=1 interproximal
    site with probing depth (PD) >=5 mm. Interproximal sites per tooth:
    distofacial (D), mesiofacial (S), distolingual (P), mesiolingual (A).
    A 4-level CDC/AAP category (none/mild/moderate/severe) is also derived.
    Only full-mouth exams (2009-2014) can support this definition: 1999-2004
    used a partial-mouth protocol (known to underestimate prevalence by >=50%)
    and 2005-2008 had no periodontal exam at all; 2015+ cycled periodontal
    health status out. Partial-mouth files were therefore not used.

Predictors are NON-dental only (no periodontal or caries variables as inputs).

Run: ~/workspace/venvs/crop-disease/bin/python src/harmonise.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "harmonised"
OUT.mkdir(parents=True, exist_ok=True)

# (cycle label, raw dir, file-stem suffix used in that cycle)
CYCLES = [
    ("1999-2000", "1999-2000", ""),
    ("2001-2002", "2001-2002", "_B"),
    ("2003-2004", "2003-2004", "_C"),
    ("2005-2006", "2005-2006", "_D"),
    ("2007-2008", "2007-2008", "_E"),
    ("2009-2010", "2009-2010", "_F"),
    ("2011-2012", "2011-2012", "_G"),
    ("2013-2014", "2013-2014", "_H"),
    ("2015-2016", "2015-2016", "_I"),
    # 2017-2018 (_J) is intentionally NOT pooled: its participants are included
    # in the 2017-Mar 2020 pre-pandemic file, so pooling would double-count.
    ("2017-Mar2020", "2017-Mar2020", "P_"),
]

TEETH_28 = [f"{i:02d}" for i in list(range(2, 16)) + list(range(18, 32))]
# interproximal site suffixes (see OHXPER_F.htm labels):
# D = distofacial, S = mesiofacial, P = distolingual, A = mesiolingual.
# Mid sites M (midfacial) and L (midlingual) are NOT interproximal.
INTERPROX = ["D", "S", "P", "A"]

# --- per-cycle raw file stems -------------------------------------------------
def stems(cycle, suffix):
    """Return {component: stem} for a cycle. suffix '' / '_B'..'_I' / 'P_'."""
    if suffix == "P_":
        pre = "P_"
        return {
            "demo": "P_DEMO", "dent": "P_OHXDEN", "diq": "P_DIQ", "smq": "P_SMQ",
            "diet": "P_DR1TOT", "bmx": "P_BMX", "ghb": "P_GHB", "crp": "P_HSCRP",
        }
    s = suffix
    d = {
        "demo": f"DEMO{s}", "diq": f"DIQ{s}", "smq": f"SMQ{s}",
        "bmx": f"BMX{s}",
    }
    if cycle == "1999-2000":
        d.update({"dent": "OHXDENT", "diet": "DRXTOT", "ghb": "LAB10", "crp": "LAB11"})
    elif cycle == "2001-2002":
        d.update({"dent": "OHXDEN_B", "diet": "DRXTOT_B", "ghb": "L10_B", "crp": "L11_B"})
    elif cycle == "2003-2004":
        d.update({"dent": "OHXDEN_C", "diet": "DR1TOT_C", "ghb": "L10_C", "crp": "L11_C"})
    elif cycle in ("2005-2006", "2007-2008"):
        d.update({"dent": f"OHX{s}", "diet": f"DR1TOT{s}", "ghb": f"GHB{s}", "crp": f"CRP{s}"})
    elif cycle in ("2009-2010",):
        d.update({"dent": "OHXDEN_F", "perio": "OHXPER_F", "diet": "DR1TOT_F",
                  "ghb": "GHB_F", "crp": "CRP_F"})
    elif cycle in ("2011-2012", "2013-2014"):
        # No CRP file was released for 2011-2014.
        d.update({"dent": f"OHXDEN{s}", "perio": f"OHXPER{s}", "diet": f"DR1TOT{s}",
                  "ghb": f"GHB{s}"})
    elif cycle in ("2015-2016", "2017-2018"):
        d.update({"dent": f"OHXDEN{s}", "diet": f"DR1TOT{s}", "ghb": f"GHB{s}",
                  "crp": f"HSCRP{s}"})
    return d


def read(cycle_dir, stem, usecols=None):
    p = RAW / cycle_dir / f"{stem}.XPT"
    df = pd.read_sas(p, format="xport")
    if usecols is not None:
        df = df[[c for c in usecols if c in df.columns]]
    # pandas renders SAS special-missing values as ~5.4e-79 denormals; treat as NaN.
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].mask(df[c].abs() < 1e-70)
    df.columns = [c.upper() for c in df.columns]
    return df


def tooth_count(df, prefix):
    """Number of remaining natural teeth (codes 1/2) over the 28 non-third-molar teeth.

    prefix: 'OHX' (most cycles), 'OHD' (2001-2002), 'OHX' with 'HTC' suffix
    (2005-2008 basic screening exam files use OHXxxHTC).
    Returns (n_teeth Series, n_measured Series)."""
    cols = {}
    for t in TEETH_28:
        for cand in (f"{prefix}{t}TC", f"{prefix}{t}HTC"):
            if cand in df.columns:
                cols[t] = cand
                break
    present = pd.DataFrame({t: df[c].isin([1, 2]) for t, c in cols.items()})
    measured = pd.DataFrame({t: df[c].notna() for t, c in cols.items()})
    return present.sum(axis=1), measured.sum(axis=1)


def cdc_aap_category(perio):
    """CDC/AAP 4-level category from a full-mouth OHXPER frame.

    Uses pre-calculated CAL (OHXxxLA*) and pocket depth (OHXxxPC*) at the four
    interproximal sites per tooth. Values >=90 (99 = could not assess) and <=0
    are treated as missing. Returns (category, severe) with category in
    {'none','mild','moderate','severe'}."""
    cal_sites, pd_sites = [], []
    for t in TEETH_28:
        for s in INTERPROX:
            la = f"OHX{t}LA{s}"
            pc = f"OHX{t}PC{s}"
            if la in perio.columns:
                v = pd.to_numeric(perio[la], errors="coerce")
                cal_sites.append(v.mask((v >= 90) | (v <= 0)))
            if pc in perio.columns:
                v = pd.to_numeric(perio[pc], errors="coerce")
                pd_sites.append(v.mask((v >= 90) | (v <= 0)))
    cal = pd.concat(cal_sites, axis=1)
    pdp = pd.concat(pd_sites, axis=1)
    # number of distinct teeth carrying a qualifying site
    n_teeth = len(TEETH_28)
    def teeth_with(mat, thr):
        hit = (mat >= thr)
        # rebuild per-tooth: columns are ordered tooth-major (4 sites per tooth)
        counts = []
        for i in range(n_teeth):
            block = hit.iloc[:, i * 4:(i + 1) * 4]
            counts.append(block.any(axis=1))
        return pd.concat(counts, axis=1).sum(axis=1)
    n_cal6 = teeth_with(cal, 6)
    n_cal4 = teeth_with(cal, 4)
    n_cal3 = teeth_with(cal, 3)
    n_pd5 = teeth_with(pdp, 5)
    n_pd4 = teeth_with(pdp, 4)
    n_cal6_sites = (cal >= 6).sum(axis=1)
    n_pd5_sites = (pdp >= 5).sum(axis=1)
    severe = (n_cal6_sites >= 2) & (n_cal6 >= 2) & (n_pd5_sites >= 1)
    moderate = (~severe) & (((n_cal4 >= 2)) | ((n_pd5 >= 2)))
    mild = (~severe) & (~moderate) & (
        ((n_cal3 >= 2) & (n_pd4 >= 2)) | (n_pd5_sites >= 1))
    cat = pd.Series("none", index=perio.index)
    cat = cat.mask(mild, "mild").mask(moderate, "moderate").mask(severe, "severe")
    return cat, severe


def build_cycle(cycle, cdir, suffix):
    st = stems(cycle, suffix)
    log = {"cycle": cycle, "files": st}
    demo = read(cdir, st["demo"])
    log["demo_n"] = int(len(demo))
    demo = demo[demo["RIDAGEYR"] >= 30].copy()
    log["demo_30plus"] = int(len(demo))
    demo = demo[["SEQN", "RIDAGEYR", "RIAGENDR", "RIDRETH1",
                 "DMDEDUC2", "INDFMPIR"] + (["RIDRETH3"] if "RIDRETH3" in demo.columns else [])]
    # --- dentition / tooth count -------------------------------------------
    dent = read(cdir, st["dent"])
    prefix = "OHD" if cycle == "2001-2002" else "OHX"
    n_teeth, n_meas = tooth_count(dent, prefix)
    dent = pd.DataFrame({"SEQN": dent["SEQN"], "n_teeth": n_teeth, "n_teeth_measured": n_meas})
    dent = dent[dent["n_teeth_measured"] > 0]
    log["dentition_n"] = int(len(dent))
    base = demo.merge(dent, on="SEQN", how="inner")
    log["base_30plus_with_dentition"] = int(len(base))
    base["cycle"] = cycle
    # --- predictors ---------------------------------------------------------
    diq = read(cdir, st["diq"], usecols=["SEQN", "DIQ010"])
    base = base.merge(diq, on="SEQN", how="left")
    smq = read(cdir, st["smq"], usecols=["SEQN", "SMQ020", "SMQ040"])
    base = base.merge(smq, on="SEQN", how="left")
    bmx = read(cdir, st["bmx"], usecols=["SEQN", "BMXBMI"])
    base = base.merge(bmx, on="SEQN", how="left")
    ghb = read(cdir, st["ghb"], usecols=["SEQN", "LBXGH"])
    base = base.merge(ghb, on="SEQN", how="left")
    if "crp" in st:
        crp = read(cdir, st["crp"])
        if "LBXCRP" in crp.columns:      # mg/dL in 1999-2010 files
            crp["CRP_MG_L"] = crp["LBXCRP"] * 10
        else:                            # LBXHSCRP, mg/L, 2015+
            crp["CRP_MG_L"] = crp["LBXHSCRP"]
        base = base.merge(crp[["SEQN", "CRP_MG_L"]], on="SEQN", how="left")
        log["crp_source"] = "LBXCRP x10 (mg/dL->mg/L)" if "LBXCRP" in crp.columns else "LBXHSCRP (mg/L)"
    else:
        base["CRP_MG_L"] = np.nan
        log["crp_source"] = "not released in this cycle"
    diet = read(cdir, st["diet"])
    dmap = {}
    if cycle in ("1999-2000", "2001-2002"):
        dmap = {"DRXTKCAL": "kcal", "DRXTPROT": "protein_g", "DRXTCARB": "carb_g",
                "DRXTFIBE": "fiber_g", "DRXTCHOL": "chol_mg", "DRDTSODI": "sodium_mg"}
    else:
        dmap = {"DR1TKCAL": "kcal", "DR1TPROT": "protein_g", "DR1TCARB": "carb_g",
                "DR1TFIBE": "fiber_g", "DR1TCHOL": "chol_mg", "DR1TSODI": "sodium_mg"}
    dcols = ["SEQN"] + [c for c in dmap if c in diet.columns]
    base = base.merge(diet[dcols].rename(columns=dmap), on="SEQN", how="left")
    log["diet_vars"] = [dmap[c] for c in dcols if c != "SEQN"]
    # --- harmonised predictors ---------------------------------------------
    base["age"] = base["RIDAGEYR"]
    base["sex"] = base["RIAGENDR"].map({1: "male", 2: "female"})
    reth = base["RIDRETH3"] if "RIDRETH3" in base.columns else base["RIDRETH1"]
    base["race_eth"] = reth.map({1: "Mexican American", 2: "Other Hispanic",
                                 3: "NH White", 4: "NH Black", 5: "Other/Multiracial",
                                 6: "NH Asian", 7: "Other/Multiracial"})
    base["education"] = base["DMDEDUC2"].map(
        {1: "<9th grade", 2: "9-11th grade", 3: "HS/GED",
         4: "Some college/AA", 5: "College grad+"})
    base["pir"] = base["INDFMPIR"]
    base["smoking"] = pd.Series(pd.NA, index=base.index, dtype="object")
    base.loc[base["SMQ020"] == 2, "smoking"] = "never"
    base.loc[(base["SMQ020"] == 1) & (base["SMQ040"] == 3), "smoking"] = "former"
    base.loc[(base["SMQ020"] == 1) & (base["SMQ040"].isin([1, 2])), "smoking"] = "current"
    base["diabetes"] = base["DIQ010"].map({1: "diabetes", 2: "no", 3: "borderline"})
    base["hba1c"] = base["LBXGH"]
    base["bmi"] = base["BMXBMI"]
    base["crp_mg_l"] = base["CRP_MG_L"]
    # --- outcomes -----------------------------------------------------------
    base["tooth_loss"] = (base["n_teeth"] < 20).astype(int)
    base["edentulous"] = (base["n_teeth"] == 0).astype(int)
    tl = base[["SEQN", "cycle", "age", "sex", "race_eth", "education", "pir",
               "smoking", "diabetes", "hba1c", "bmi", "crp_mg_l",
               "kcal", "protein_g", "carb_g", "fiber_g", "chol_mg", "sodium_mg",
               "n_teeth", "tooth_loss", "edentulous"]].copy()
    log["toothloss_n"] = int(len(tl))
    log["toothloss_prev"] = float(tl["tooth_loss"].mean())
    log["edentulous_prev"] = float(tl["edentulous"].mean())
    # --- periodontitis (full-mouth cycles only) -----------------------------
    perio = None
    if "perio" in st:
        pf = read(cdir, st["perio"])
        pf = pf[pf["OHDPDSTS"] == 1].copy()   # complete FMPE only
        log["perio_complete_n"] = int(len(pf))
        cat, severe = cdc_aap_category(pf)
        pf = pd.DataFrame({"SEQN": pf["SEQN"], "perio_category": cat,
                           "severe_periodontitis": severe.astype(int)})
        # CDC/AAP prevalence is reported among DENTATE adults: edentulous
        # participants (n_teeth == 0) can carry a "complete" exam status with
        # no measured sites, so they are excluded from the perio sample.
        dentate = base[base["n_teeth"] >= 1]
        log["perio_dentate_n"] = int(len(dentate))
        perio = dentate.merge(pf, on="SEQN", how="inner")
        log["periodontitis_n"] = int(len(perio))
        log["severe_prev"] = float(perio["severe_periodontitis"].mean())
        log["perio_category_counts"] = perio["perio_category"].value_counts().to_dict()
        perio = perio[["SEQN", "cycle", "age", "sex", "race_eth", "education", "pir",
                       "smoking", "diabetes", "hba1c", "bmi", "crp_mg_l",
                       "kcal", "protein_g", "carb_g", "fiber_g", "chol_mg", "sodium_mg",
                       "n_teeth", "perio_category", "severe_periodontitis"]].copy()
    return tl, perio, log


def main():
    tl_all, per_all, logs = [], [], []
    for cycle, cdir, suffix in CYCLES:
        print(f"--- {cycle} ---", flush=True)
        tl, per, log = build_cycle(cycle, cdir, suffix)
        print({k: log[k] for k in ("base_30plus_with_dentition", "toothloss_n",
                                    "toothloss_prev", "periodontitis_n") if k in log}, flush=True)
        tl_all.append(tl)
        if per is not None:
            per_all.append(per)
        logs.append(log)
    tl_df = pd.concat(tl_all, ignore_index=True)
    per_df = pd.concat(per_all, ignore_index=True)
    tl_df.to_csv(OUT / "toothloss.csv", index=False)
    per_df.to_csv(OUT / "periodontitis.csv", index=False)
    json.dump(logs, open(OUT / "harmonisation.json", "w"), indent=1)
    print(f"toothloss: n={len(tl_df)} prev={tl_df['tooth_loss'].mean():.4f} "
          f"edentulous={tl_df['edentulous'].mean():.4f}")
    print(f"periodontitis: n={len(per_df)} severe prev={per_df['severe_periodontitis'].mean():.4f}")
    print("cycles toothloss:", tl_df.groupby("cycle").size().to_dict())
    print("cycles periodontitis:", per_df.groupby("cycle").size().to_dict())


if __name__ == "__main__":
    main()
