#!/usr/bin/env python3
"""Download NHANES 1999-2020 public-use XPT files used by this project.

Source: CDC/NCHS, https://wwwn.cdc.gov/nchs/nhanes/ (public-use, no login).
Filenames were verified against CDC's per-cycle datapages before download
(see DATA.md for the filename table and the 2017-March 2020 pre-pandemic note).

Files land in data/raw/<cycle>/ and are gitignored (see .gitignore).
Re-run is safe: existing files with matching size are skipped.
"""
import json
import urllib.request
from pathlib import Path

BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{year}/DataFiles/{fname}.XPT"
ROOT = Path(__file__).resolve().parent.parent / "data" / "raw"

# (cycle label, year dir, [file stems without .XPT])
MANIFEST = [
    ("1999-2000", "1999", ["DEMO", "OHXDENT", "DIQ", "SMQ", "DRXTOT", "BMX", "LAB10", "LAB11"]),
    ("2001-2002", "2001", ["DEMO_B", "OHXDEN_B", "DIQ_B", "SMQ_B", "DRXTOT_B", "BMX_B", "L10_B", "L11_B"]),
    ("2003-2004", "2003", ["DEMO_C", "OHXDEN_C", "DIQ_C", "SMQ_C", "DR1TOT_C", "BMX_C", "L10_C", "L11_C"]),
    ("2005-2006", "2005", ["DEMO_D", "OHX_D", "DIQ_D", "SMQ_D", "DR1TOT_D", "BMX_D", "GHB_D", "CRP_D"]),
    ("2007-2008", "2007", ["DEMO_E", "OHX_E", "DIQ_E", "SMQ_E", "DR1TOT_E", "BMX_E", "GHB_E", "CRP_E"]),
    ("2009-2010", "2009", ["DEMO_F", "OHXDEN_F", "OHXPER_F", "DIQ_F", "SMQ_F", "DR1TOT_F", "BMX_F", "GHB_F", "CRP_F"]),
    ("2011-2012", "2011", ["DEMO_G", "OHXDEN_G", "OHXPER_G", "DIQ_G", "SMQ_G", "DR1TOT_G", "BMX_G", "GHB_G"]),
    ("2013-2014", "2013", ["DEMO_H", "OHXDEN_H", "OHXPER_H", "DIQ_H", "SMQ_H", "DR1TOT_H", "BMX_H", "GHB_H"]),
    ("2015-2016", "2015", ["DEMO_I", "OHXDEN_I", "DIQ_I", "SMQ_I", "DR1TOT_I", "BMX_I", "GHB_I", "HSCRP_I"]),
    # 2017-2018 (_J) is downloaded ONLY to verify it overlaps the pre-pandemic
    # file (same participants); it is not used in any model (see DATA.md).
    ("2017-2018", "2017", ["DEMO_J", "OHXDEN_J", "DIQ_J", "SMQ_J", "DR1TOT_J", "BMX_J", "GHB_J", "HSCRP_J"]),
    # 2017-March 2020 pre-pandemic combined file (P_ prefix, same /2017/ dir).
    ("2017-Mar2020", "2017", ["P_DEMO", "P_OHXDEN", "P_DIQ", "P_SMQ", "P_DR1TOT", "P_BMX", "P_GHB", "P_HSCRP"]),
]


def fetch(url, dest, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            dest.write_bytes(data)
            return len(data)
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"  retry {attempt + 1} for {url}: {e}")


def main():
    log = []
    for cycle, year, files in MANIFEST:
        cdir = ROOT / cycle
        cdir.mkdir(parents=True, exist_ok=True)
        for fname in files:
            url = BASE.format(year=year, fname=fname)
            dest = cdir / f"{fname}.XPT"
            if dest.exists() and dest.stat().st_size > 0:
                print(f"skip {cycle}/{fname} ({dest.stat().st_size} bytes)")
                log.append({"cycle": cycle, "file": fname, "status": "skipped-existing",
                            "bytes": dest.stat().st_size})
                continue
            try:
                n = fetch(url, dest)
                print(f"OK   {cycle}/{fname} ({n} bytes)")
                log.append({"cycle": cycle, "file": fname, "status": "downloaded", "bytes": n})
            except Exception as e:
                print(f"FAIL {cycle}/{fname}: {e}")
                log.append({"cycle": cycle, "file": fname, "status": "FAILED", "error": str(e)})
    out = Path(__file__).resolve().parent.parent / "results" / "download_log.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(log, open(out, "w"), indent=1)
    n_ok = sum(1 for r in log if r["status"] in ("downloaded", "skipped-existing"))
    print(f"\n{n_ok}/{len(log)} files present; log -> {out}")


if __name__ == "__main__":
    main()
